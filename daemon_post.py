__filename__ = "daemon_post.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import time
import errno
import json
import os
import urllib.parse
from socket import error as SocketError
from utils import dangerous_markup
from utils import binary_is_image
from utils import get_image_extension_from_mime_type
from utils import remove_post_from_cache
from utils import get_cached_post_filename
from utils import text_in_file
from utils import load_json
from utils import save_json
from utils import locate_post
from utils import get_full_domain
from utils import get_domain_from_actor
from utils import is_editor
from utils import get_config_param
from utils import decoded_host
from utils import get_new_post_endpoints
from utils import local_actor_url
from utils import contains_invalid_chars
from utils import remove_id_ending
from utils import check_bad_path
from utils import get_instance_url
from utils import acct_dir
from utils import get_nickname_from_actor
from blocking import is_blocked_hashtag
from blocking import contains_military_domain
from crawlers import blocked_user_agent
from session import get_session_for_domain
from session import establish_session
from fitnessFunctions import fitness_performance
from shares import update_shared_item_federation_token
from inbox import populate_replies
from inbox import inbox_message_has_params
from inbox import inbox_permitted_message
from httpsig import getheader_signature_input
from content import extract_text_fields_in_post
from filters import is_filtered
from categories import set_hashtag_category
from httpcodes import http_200
from httpcodes import http_404
from httpcodes import http_400
from httpcodes import http_503
from httpheaders import redirect_headers
from daemon_utils import get_user_agent
from daemon_utils import post_to_outbox
from daemon_utils import update_inbox_queue
from daemon_utils import is_authorized
from theme import reset_theme_designer_settings
from theme import set_theme
from theme import set_theme_from_designer
from languages import get_understood_languages
from city import get_spoofed_city
from posts import create_direct_message_post
from daemon_post_login import post_login_screen
from daemon_post_receive import receive_new_post
from daemon_post_profile import profile_edit
from daemon_post_person_options import person_options2
from daemon_post_search import receive_search_query
from daemon_post_moderator import moderator_actions
from daemon_post_confirm import follow_confirm2
from daemon_post_confirm import unfollow_confirm
from daemon_post_confirm import block_confirm2
from daemon_post_confirm import unblock_confirm
from daemon_post_newswire import newswire_update
from daemon_post_newswire import citations_update
from daemon_post_newswire import news_post_edit
from daemon_post_remove import remove_reading_status
from daemon_post_remove import remove_share
from daemon_post_remove import remove_wanted
from daemon_post_remove import receive_remove_post

# maximum number of posts in a hashtag feed
MAX_POSTS_IN_HASHTAG_FEED = 6

# maximum number of posts to list in outbox feed
MAX_POSTS_IN_FEED = 12


def daemon_http_post(self) -> None:
    """HTTP POST handler
    """
    if self.server.starting_daemon:
        return
    if check_bad_path(self.path):
        http_400(self)
        return

    proxy_type = self.server.proxy_type
    postreq_start_time = time.time()

    if self.server.debug:
        print('DEBUG: POST to ' + self.server.base_dir +
              ' path: ' + self.path + ' busy: ' +
              str(self.server.postreq_busy))

    calling_domain = self.server.domain_full
    if self.headers.get('Host'):
        calling_domain = decoded_host(self.headers['Host'])
        if self.server.onion_domain:
            if calling_domain not in (self.server.domain,
                                      self.server.domain_full,
                                      self.server.onion_domain):
                print('POST domain blocked: ' + calling_domain)
                http_400(self)
                return
        elif self.server.i2p_domain:
            if calling_domain not in (self.server.domain,
                                      self.server.domain_full,
                                      self.server.i2p_domain):
                print('POST domain blocked: ' + calling_domain)
                http_400(self)
                return
        else:
            if calling_domain not in (self.server.domain,
                                      self.server.domain_full):
                print('POST domain blocked: ' + calling_domain)
                http_400(self)
                return

    curr_time_postreq = int(time.time() * 1000)
    if self.server.postreq_busy:
        if curr_time_postreq - self.server.last_postreq < 500:
            self.send_response(429)
            self.end_headers()
            return
    self.server.postreq_busy = True
    self.server.last_postreq = curr_time_postreq

    ua_str = get_user_agent(self)

    block, self.server.blocked_cache_last_updated = \
        blocked_user_agent(calling_domain, ua_str,
                           self.server.news_instance,
                           self.server.debug,
                           self.server.user_agents_blocked,
                           self.server.blocked_cache_last_updated,
                           self.server.base_dir,
                           self.server.blocked_cache,
                           self.server.block_federated,
                           self.server.blocked_cache_update_secs,
                           self.server.crawlers_allowed,
                           self.server.known_bots,
                           self.path, self.server.block_military)
    if block:
        http_400(self)
        self.server.postreq_busy = False
        return

    if not self.headers.get('Content-type'):
        print('Content-type header missing')
        http_400(self)
        self.server.postreq_busy = False
        return

    curr_session, proxy_type = \
        get_session_for_domain(self.server, calling_domain)

    curr_session = \
        establish_session("POST", curr_session,
                          proxy_type, self.server)
    if not curr_session:
        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', 'create_session',
                            self.server.debug)
        http_404(self, 152)
        self.server.postreq_busy = False
        return

    # returns after this point should set postreq_busy to False

    # remove any trailing slashes from the path
    if not self.path.endswith('confirm'):
        self.path = self.path.replace('/outbox/', '/outbox')
        self.path = self.path.replace('/tlblogs/', '/tlblogs')
        self.path = self.path.replace('/inbox/', '/inbox')
        self.path = self.path.replace('/shares/', '/shares')
        self.path = self.path.replace('/wanted/', '/wanted')
        self.path = self.path.replace('/sharedInbox/', '/sharedInbox')

    if self.path == '/inbox':
        if not self.server.enable_shared_inbox:
            http_503(self)
            self.server.postreq_busy = False
            return

    cookie = None
    if self.headers.get('Cookie'):
        cookie = self.headers['Cookie']

    # check authorization
    authorized = is_authorized(self)
    if not authorized and self.server.debug:
        print('POST Not authorized')
        print(str(self.headers))

    # if this is a POST to the outbox then check authentication
    self.outbox_authenticated = False
    self.post_to_nickname = None

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'start',
                        self.server.debug)

    # POST to login screen, containing credentials
    if self.path.startswith('/login'):
        post_login_screen(self, calling_domain, cookie,
                          self.server.base_dir,
                          self.server.http_prefix,
                          self.server.domain,
                          self.server.port,
                          ua_str, self.server.debug,
                          self.server.registration)
        self.server.postreq_busy = False
        return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', '_login_screen',
                        self.server.debug)

    if authorized and self.path.endswith('/sethashtagcategory'):
        _set_hashtag_category2(self, calling_domain, cookie,
                               self.path,
                               self.server.base_dir,
                               self.server.domain,
                               self.server.debug,
                               self.server.system_language)
        self.server.postreq_busy = False
        return

    # update of profile/avatar from web interface,
    # after selecting Edit button then Submit
    if authorized and self.path.endswith('/profiledata'):
        profile_edit(self, calling_domain, cookie, self.path,
                     self.server.base_dir, self.server.http_prefix,
                     self.server.domain,
                     self.server.domain_full,
                     self.server.onion_domain,
                     self.server.i2p_domain, self.server.debug,
                     self.server.allow_local_network_access,
                     self.server.system_language,
                     self.server.content_license_url,
                     curr_session,
                     proxy_type)
        self.server.postreq_busy = False
        return

    if authorized and self.path.endswith('/linksdata'):
        _links_update(self, calling_domain, cookie, self.path,
                      self.server.base_dir, self.server.debug,
                      self.server.default_timeline,
                      self.server.allow_local_network_access)
        self.server.postreq_busy = False
        return

    if authorized and self.path.endswith('/newswiredata'):
        newswire_update(self, calling_domain, cookie,
                        self.path,
                        self.server.base_dir,
                        self.server.domain, self.server.debug,
                        self.server.default_timeline)
        self.server.postreq_busy = False
        return

    if authorized and self.path.endswith('/citationsdata'):
        citations_update(self, calling_domain, cookie,
                         self.path,
                         self.server.base_dir,
                         self.server.domain,
                         self.server.debug,
                         self.server.newswire)
        self.server.postreq_busy = False
        return

    if authorized and self.path.endswith('/newseditdata'):
        news_post_edit(self, calling_domain, cookie, self.path,
                       self.server.base_dir,
                       self.server.domain,
                       self.server.debug)
        self.server.postreq_busy = False
        return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', '_news_post_edit',
                        self.server.debug)

    users_in_path = False
    if '/users/' in self.path:
        users_in_path = True

    # moderator action buttons
    if authorized and users_in_path and \
       self.path.endswith('/moderationaction'):
        moderator_actions(self,
                          self.path, calling_domain, cookie,
                          self.server.base_dir,
                          self.server.http_prefix,
                          self.server.domain,
                          self.server.port,
                          self.server.debug)
        self.server.postreq_busy = False
        return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', '_moderator_actions',
                        self.server.debug)

    search_for_emoji = False
    if self.path.endswith('/searchhandleemoji'):
        search_for_emoji = True
        self.path = self.path.replace('/searchhandleemoji',
                                      '/searchhandle')
        if self.server.debug:
            print('DEBUG: searching for emoji')
            print('authorized: ' + str(authorized))

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'searchhandleemoji',
                        self.server.debug)

    # a search was made
    if ((authorized or search_for_emoji) and
        (self.path.endswith('/searchhandle') or
         '/searchhandle?page=' in self.path)):
        receive_search_query(self, calling_domain, cookie,
                             authorized, self.path,
                             self.server.base_dir,
                             self.server.http_prefix,
                             self.server.domain,
                             self.server.domain_full,
                             self.server.port,
                             search_for_emoji,
                             self.server.onion_domain,
                             self.server.i2p_domain,
                             postreq_start_time,
                             self.server.debug,
                             curr_session,
                             proxy_type, MAX_POSTS_IN_HASHTAG_FEED,
                             MAX_POSTS_IN_FEED)
        self.server.postreq_busy = False
        return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'receive_search_query',
                        self.server.debug)

    if not authorized:
        if self.path.endswith('/rmpost'):
            print('ERROR: attempt to remove post was not authorized. ' +
                  self.path)
            http_400(self)
            self.server.postreq_busy = False
            return
    else:
        # a vote/question/poll is posted
        if self.path.endswith('/question') or \
           '/question?page=' in self.path or \
           '/question?firstpost=' in self.path or \
           '/question?lastpost=' in self.path:
            _receive_vote(self, calling_domain, cookie,
                          self.path,
                          self.server.http_prefix,
                          self.server.domain,
                          self.server.domain_full,
                          self.server.port,
                          self.server.onion_domain,
                          self.server.i2p_domain,
                          curr_session,
                          proxy_type,
                          self.server.base_dir,
                          self.server.city,
                          self.server.person_cache,
                          self.server.debug,
                          self.server.system_language,
                          self.server.low_bandwidth,
                          self.server.dm_license_url,
                          self.server.content_license_url,
                          self.server.translate,
                          self.server.max_replies,
                          self.server.project_version,
                          self.server.recent_posts_cache)
            self.server.postreq_busy = False
            return

        # removes a shared item
        if self.path.endswith('/rmshare'):
            remove_share(self, calling_domain, cookie,
                         authorized, self.path,
                         self.server.base_dir,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain,
                         curr_session, proxy_type)
            self.server.postreq_busy = False
            return

        # removes a wanted item
        if self.path.endswith('/rmwanted'):
            remove_wanted(self, calling_domain, cookie,
                          authorized, self.path,
                          self.server.base_dir,
                          self.server.http_prefix,
                          self.server.domain_full,
                          self.server.onion_domain,
                          self.server.i2p_domain)
            self.server.postreq_busy = False
            return

        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', 'remove_wanted',
                            self.server.debug)

        # removes a post
        if self.path.endswith('/rmpost'):
            if '/users/' not in self.path:
                print('ERROR: attempt to remove post ' +
                      'was not authorized. ' + self.path)
                http_400(self)
                self.server.postreq_busy = False
                return
        if self.path.endswith('/rmpost'):
            receive_remove_post(self, calling_domain, cookie,
                                self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domain_full,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                curr_session, proxy_type)
            self.server.postreq_busy = False
            return

        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', '_remove_post',
                            self.server.debug)

        # decision to follow in the web interface is confirmed
        if self.path.endswith('/followconfirm'):
            follow_confirm2(self, calling_domain, cookie,
                            self.path,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.domain_full,
                            self.server.port,
                            self.server.onion_domain,
                            self.server.i2p_domain,
                            self.server.debug,
                            curr_session,
                            proxy_type)
            self.server.postreq_busy = False
            return

        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', 'follow_confirm2',
                            self.server.debug)

        # remove a reading status from the profile screen
        if self.path.endswith('/removereadingstatus'):
            remove_reading_status(self, calling_domain, cookie,
                                  self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain_full,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  self.server.debug,
                                  self.server.books_cache)
            self.server.postreq_busy = False
            return

        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', 'remove_reading_status',
                            self.server.debug)

        # decision to unfollow in the web interface is confirmed
        if self.path.endswith('/unfollowconfirm'):
            unfollow_confirm(self, calling_domain, cookie,
                             self.path,
                             self.server.base_dir,
                             self.server.http_prefix,
                             self.server.domain,
                             self.server.domain_full,
                             self.server.port,
                             self.server.onion_domain,
                             self.server.i2p_domain,
                             self.server.debug,
                             curr_session, proxy_type)
            self.server.postreq_busy = False
            return

        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', 'unfollow_confirm',
                            self.server.debug)

        # decision to unblock in the web interface is confirmed
        if self.path.endswith('/unblockconfirm'):
            unblock_confirm(self, calling_domain, cookie,
                            self.path,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.domain_full,
                            self.server.port,
                            self.server.onion_domain,
                            self.server.i2p_domain,
                            self.server.debug)
            self.server.postreq_busy = False
            return

        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', 'unblock_confirm',
                            self.server.debug)

        # decision to block in the web interface is confirmed
        if self.path.endswith('/blockconfirm'):
            block_confirm2(self, calling_domain, cookie,
                           self.path,
                           self.server.base_dir,
                           self.server.http_prefix,
                           self.server.domain,
                           self.server.domain_full,
                           self.server.port,
                           self.server.onion_domain,
                           self.server.i2p_domain,
                           self.server.debug)
            self.server.postreq_busy = False
            return

        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', 'block_confirm2',
                            self.server.debug)

        # an option was chosen from person options screen
        # view/follow/block/report
        if self.path.endswith('/personoptions'):
            person_options2(self, self.path,
                            calling_domain, cookie,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.domain_full,
                            self.server.port,
                            self.server.onion_domain,
                            self.server.i2p_domain,
                            self.server.debug,
                            curr_session,
                            authorized)
            self.server.postreq_busy = False
            return

        # Change the key shortcuts
        if users_in_path and \
           self.path.endswith('/changeAccessKeys'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            if not self.server.key_shortcuts.get(nickname):
                access_keys = self.server.access_keys
                self.server.key_shortcuts[nickname] = access_keys.copy()
            access_keys = self.server.key_shortcuts[nickname]

            _key_shortcuts(self, calling_domain, cookie,
                           self.server.base_dir,
                           self.server.http_prefix,
                           nickname,
                           self.server.domain,
                           self.server.domain_full,
                           self.server.onion_domain,
                           self.server.i2p_domain,
                           access_keys,
                           self.server.default_timeline)
            self.server.postreq_busy = False
            return

        # theme designer submit/cancel button
        if users_in_path and \
           self.path.endswith('/changeThemeSettings'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            if not self.server.key_shortcuts.get(nickname):
                access_keys = self.server.access_keys
                self.server.key_shortcuts[nickname] = access_keys.copy()
            access_keys = self.server.key_shortcuts[nickname]
            allow_local_network_access = \
                self.server.allow_local_network_access

            _theme_designer_edit(self, calling_domain, cookie,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 nickname,
                                 self.server.domain,
                                 self.server.domain_full,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 self.server.default_timeline,
                                 self.server.theme_name,
                                 allow_local_network_access,
                                 self.server.system_language,
                                 self.server.dyslexic_font)
            self.server.postreq_busy = False
            return

    # update the shared item federation token for the calling domain
    # if it is within the permitted federation
    if self.headers.get('Origin') and \
       self.headers.get('SharesCatalog'):
        if self.server.debug:
            print('SharesCatalog header: ' + self.headers['SharesCatalog'])
        if not self.server.shared_items_federated_domains:
            si_domains_str = \
                get_config_param(self.server.base_dir,
                                 'sharedItemsFederatedDomains')
            if si_domains_str:
                if self.server.debug:
                    print('Loading shared items federated domains list')
                si_domains_list = si_domains_str.split(',')
                domains_list = self.server.shared_items_federated_domains
                for si_domain in si_domains_list:
                    domains_list.append(si_domain.strip())
        origin_domain = self.headers.get('Origin')
        if origin_domain != self.server.domain_full and \
           origin_domain != self.server.onion_domain and \
           origin_domain != self.server.i2p_domain and \
           origin_domain in self.server.shared_items_federated_domains:
            if self.server.debug:
                print('DEBUG: ' +
                      'POST updating shared item federation ' +
                      'token for ' + origin_domain + ' to ' +
                      self.server.domain_full)
            shared_item_tokens = self.server.shared_item_federation_tokens
            shares_token = self.headers['SharesCatalog']
            self.server.shared_item_federation_tokens = \
                update_shared_item_federation_token(self.server.base_dir,
                                                    origin_domain,
                                                    shares_token,
                                                    self.server.debug,
                                                    shared_item_tokens)
        elif self.server.debug:
            fed_domains = self.server.shared_items_federated_domains
            if origin_domain not in fed_domains:
                print('origin_domain is not in federated domains list ' +
                      origin_domain)
            else:
                print('origin_domain is not a different instance. ' +
                      origin_domain + ' ' + self.server.domain_full + ' ' +
                      str(fed_domains))

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'SharesCatalog',
                        self.server.debug)

    # receive different types of post created by html_new_post
    new_post_endpoints = get_new_post_endpoints()
    for curr_post_type in new_post_endpoints:
        if not authorized:
            if self.server.debug:
                print('POST was not authorized')
            break

        post_redirect = self.server.default_timeline
        if curr_post_type == 'newshare':
            post_redirect = 'tlshares'
        elif curr_post_type == 'newwanted':
            post_redirect = 'tlwanted'

        page_number = \
            receive_new_post(self, curr_post_type, self.path,
                             calling_domain, cookie,
                             self.server.content_license_url,
                             curr_session, proxy_type)
        if page_number:
            print(curr_post_type + ' post received')
            nickname = self.path.split('/users/')[1]
            if '?' in nickname:
                nickname = nickname.split('?')[0]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                actor_path_str = \
                    local_actor_url('http', nickname,
                                    self.server.onion_domain) + \
                    '/' + post_redirect + \
                    '?page=' + str(page_number)
                redirect_headers(self, actor_path_str, cookie,
                                 calling_domain)
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                actor_path_str = \
                    local_actor_url('http', nickname,
                                    self.server.i2p_domain) + \
                    '/' + post_redirect + \
                    '?page=' + str(page_number)
                redirect_headers(self, actor_path_str, cookie,
                                 calling_domain)
            else:
                actor_path_str = \
                    local_actor_url(self.server.http_prefix, nickname,
                                    self.server.domain_full) + \
                    '/' + post_redirect + '?page=' + str(page_number)
                redirect_headers(self, actor_path_str, cookie,
                                 calling_domain)
            self.server.postreq_busy = False
            return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'receive post',
                        self.server.debug)

    if self.path.endswith('/outbox') or \
       self.path.endswith('/wanted') or \
       self.path.endswith('/shares'):
        if users_in_path:
            if authorized:
                self.outbox_authenticated = True
                path_users_section = self.path.split('/users/')[1]
                self.post_to_nickname = path_users_section.split('/')[0]
        if not self.outbox_authenticated:
            self.send_response(405)
            self.end_headers()
            self.server.postreq_busy = False
            return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'authorized',
                        self.server.debug)

    # check that the post is to an expected path
    if not (self.path.endswith('/outbox') or
            self.path.endswith('/inbox') or
            self.path.endswith('/wanted') or
            self.path.endswith('/shares') or
            self.path.endswith('/moderationaction') or
            self.path == '/sharedInbox'):
        print('Attempt to POST to invalid path ' + self.path)
        http_400(self)
        self.server.postreq_busy = False
        return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'check path',
                        self.server.debug)

    if self.headers['Content-length'] is None or \
       self.headers['Content-type'] is None:
        http_400(self)
        self.server.postreq_busy = False
        return

    is_media_content = False
    if self.headers['Content-type'].startswith('image/') or \
       self.headers['Content-type'].startswith('video/') or \
       self.headers['Content-type'].startswith('audio/'):
        is_media_content = True

    # check that the content length string is not too long
    if isinstance(self.headers['Content-length'], str):
        if not is_media_content:
            max_content_size = len(str(self.server.maxMessageLength))
        else:
            max_content_size = len(str(self.server.maxMediaSize))
        if len(self.headers['Content-length']) > max_content_size:
            http_400(self)
            self.server.postreq_busy = False
            return

    # read the message and convert it into a python dictionary
    length = int(self.headers['Content-length'])
    if self.server.debug:
        print('DEBUG: content-length: ' + str(length))
    if not is_media_content:
        if length > self.server.maxMessageLength:
            print('Maximum message length exceeded ' + str(length))
            http_400(self)
            self.server.postreq_busy = False
            return
    else:
        if length > self.server.maxMediaSize:
            print('Maximum media size exceeded ' + str(length))
            http_400(self)
            self.server.postreq_busy = False
            return

    # receive images to the outbox
    if self.headers['Content-type'].startswith('image/') and \
       users_in_path:
        _receive_image(self, length, self.path,
                       self.server.base_dir,
                       self.server.domain,
                       self.server.debug)
        self.server.postreq_busy = False
        return

    # refuse to receive non-json content
    content_type_str = self.headers['Content-type']
    if not content_type_str.startswith('application/json') and \
       not content_type_str.startswith('application/activity+json') and \
       not content_type_str.startswith('application/ld+json'):
        print("POST is not json: " + self.headers['Content-type'])
        if self.server.debug:
            print(str(self.headers))
            length = int(self.headers['Content-length'])
            if length < self.server.max_post_length:
                try:
                    unknown_post = self.rfile.read(length).decode('utf-8')
                except SocketError as ex:
                    if ex.errno == errno.ECONNRESET:
                        print('EX: POST unknown_post ' +
                              'connection reset by peer')
                    else:
                        print('EX: POST unknown_post socket error')
                    self.send_response(400)
                    self.end_headers()
                    self.server.postreq_busy = False
                    return
                except ValueError as ex:
                    print('EX: POST unknown_post rfile.read failed, ' +
                          str(ex))
                    self.send_response(400)
                    self.end_headers()
                    self.server.postreq_busy = False
                    return
                print(str(unknown_post))
        http_400(self)
        self.server.postreq_busy = False
        return

    if self.server.debug:
        print('DEBUG: Reading message')

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'check content type',
                        self.server.debug)

    # check content length before reading bytes
    if self.path in ('/sharedInbox', '/inbox'):
        length = 0
        if self.headers.get('Content-length'):
            length = int(self.headers['Content-length'])
        elif self.headers.get('Content-Length'):
            length = int(self.headers['Content-Length'])
        elif self.headers.get('content-length'):
            length = int(self.headers['content-length'])
        if length > 10240:
            print('WARN: post to shared inbox is too long ' +
                  str(length) + ' bytes')
            http_400(self)
            self.server.postreq_busy = False
            return

    try:
        message_bytes = self.rfile.read(length)
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('WARN: POST message_bytes ' +
                  'connection reset by peer')
        else:
            print('WARN: POST message_bytes socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST message_bytes rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    # check content length after reading bytes
    if self.path in ('/sharedInbox', '/inbox'):
        len_message = len(message_bytes)
        if len_message > 10240:
            print('WARN: post to shared inbox is too long ' +
                  str(len_message) + ' bytes')
            http_400(self)
            self.server.postreq_busy = False
            return

    decoded_message_bytes = message_bytes.decode("utf-8")
    if contains_invalid_chars(decoded_message_bytes):
        http_400(self)
        self.server.postreq_busy = False
        return

    if users_in_path:
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if self.server.block_military.get(nickname):
            if contains_military_domain(decoded_message_bytes):
                http_400(self)
                print('BLOCK: blocked military domain')
                self.server.postreq_busy = False
                return

    # convert the raw bytes to json
    try:
        message_json = json.loads(message_bytes)
    except json.decoder.JSONDecodeError as ex:
        http_400(self)
        print('EX: json decode error ' + str(ex) +
              ' from POST ' + str(message_bytes))
        self.server.postreq_busy = False
        return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'load json',
                        self.server.debug)

    # https://www.w3.org/TR/activitypub/#object-without-create
    if self.outbox_authenticated:
        if post_to_outbox(self, message_json,
                          self.server.project_version, None,
                          curr_session, proxy_type):
            if message_json.get('id'):
                locn_str = remove_id_ending(message_json['id'])
                self.headers['Location'] = locn_str
            self.send_response(201)
            self.end_headers()
            self.server.postreq_busy = False
            return
        else:
            if self.server.debug:
                print('Failed to post to outbox')
            self.send_response(403)
            self.end_headers()
            self.server.postreq_busy = False
            return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'post_to_outbox',
                        self.server.debug)

    # check the necessary properties are available
    if self.server.debug:
        print('DEBUG: Check message has params')

    if not message_json:
        self.send_response(403)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if self.path.endswith('/inbox') or \
       self.path == '/sharedInbox':
        if not inbox_message_has_params(message_json):
            if self.server.debug:
                print("DEBUG: inbox message doesn't have the " +
                      "required parameters")
            self.send_response(403)
            self.end_headers()
            self.server.postreq_busy = False
            return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'inbox_message_has_params',
                        self.server.debug)

    header_signature = getheader_signature_input(self.headers)

    if header_signature:
        if 'keyId=' not in header_signature:
            if self.server.debug:
                print('DEBUG: POST to inbox has no keyId in ' +
                      'header signature parameter')
            self.send_response(403)
            self.end_headers()
            self.server.postreq_busy = False
            return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'keyId check',
                        self.server.debug)

    if not self.server.unit_test:
        if not inbox_permitted_message(self.server.domain,
                                       message_json,
                                       self.server.federation_list):
            if self.server.debug:
                # https://www.youtube.com/watch?v=K3PrSj9XEu4
                print('DEBUG: Ah Ah Ah')
            self.send_response(403)
            self.end_headers()
            self.server.postreq_busy = False
            return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', 'inbox_permitted_message',
                        self.server.debug)

    if self.server.debug:
        print('INBOX: POST saving to inbox queue')
    if users_in_path:
        path_users_section = self.path.split('/users/')[1]
        if '/' not in path_users_section:
            if self.server.debug:
                print('INBOX: This is not a users endpoint')
        else:
            self.post_to_nickname = path_users_section.split('/')[0]
            if self.post_to_nickname:
                queue_status = \
                    update_inbox_queue(self, self.post_to_nickname,
                                       message_json, message_bytes,
                                       self.server.debug)
                if queue_status in range(0, 4):
                    self.server.postreq_busy = False
                    return
                if self.server.debug:
                    print('INBOX: update_inbox_queue exited ' +
                          'without doing anything')
            else:
                if self.server.debug:
                    print('INBOX: self.post_to_nickname is None')
        self.send_response(403)
        self.end_headers()
        self.server.postreq_busy = False
        return
    if self.path in ('/sharedInbox', '/inbox'):
        if self.server.debug:
            print('INBOX: POST to shared inbox')
        queue_status = \
            update_inbox_queue(self, 'inbox', message_json,
                               message_bytes,
                               self.server.debug)
        if queue_status in range(0, 4):
            self.server.postreq_busy = False
            return
    http_200(self)
    self.server.postreq_busy = False


def _key_shortcuts(self, calling_domain: str, cookie: str,
                   base_dir: str, http_prefix: str, nickname: str,
                   domain: str, domain_full: str,
                   onion_domain: str, i2p_domain: str,
                   access_keys: {}, default_timeline: str) -> None:
    """Receive POST from webapp_accesskeys
    """
    users_path = '/users/' + nickname
    origin_path_str = \
        http_prefix + '://' + domain_full + users_path + '/' + \
        default_timeline
    length = int(self.headers['Content-length'])

    try:
        access_keys_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST access_keys_params ' +
                  'connection reset by peer')
        else:
            print('EX: POST access_keys_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST access_keys_params rfile.read failed, ' +
              str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    access_keys_params = \
        urllib.parse.unquote_plus(access_keys_params)

    # key shortcuts screen, back button
    # See html_access_keys
    if 'submitAccessKeysCancel=' in access_keys_params or \
       'submitAccessKeys=' not in access_keys_params:
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str = \
                'http://' + onion_domain + users_path + '/' + \
                default_timeline
        elif calling_domain.endswith('.i2p') and i2p_domain:
            origin_path_str = \
                'http://' + i2p_domain + users_path + \
                '/' + default_timeline
        redirect_headers(self, origin_path_str, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    save_keys = False
    access_keys_template = self.server.access_keys
    for variable_name, _ in access_keys_template.items():
        if not access_keys.get(variable_name):
            access_keys[variable_name] = \
                access_keys_template[variable_name]

        variable_name2 = variable_name.replace(' ', '_')
        if variable_name2 + '=' in access_keys_params:
            new_key = access_keys_params.split(variable_name2 + '=')[1]
            if '&' in new_key:
                new_key = new_key.split('&')[0]
            if new_key:
                if len(new_key) > 1:
                    new_key = new_key[0]
                if new_key != access_keys[variable_name]:
                    access_keys[variable_name] = new_key
                    save_keys = True

    if save_keys:
        access_keys_filename = \
            acct_dir(base_dir, nickname, domain) + '/access_keys.json'
        save_json(access_keys, access_keys_filename)
        if not self.server.key_shortcuts.get(nickname):
            self.server.key_shortcuts[nickname] = access_keys.copy()

    # redirect back from key shortcuts screen
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = \
            'http://' + onion_domain + users_path + '/' + default_timeline
    elif calling_domain.endswith('.i2p') and i2p_domain:
        origin_path_str = \
            'http://' + i2p_domain + users_path + '/' + default_timeline
    redirect_headers(self, origin_path_str, cookie, calling_domain)
    self.server.postreq_busy = False
    return


def _theme_designer_edit(self, calling_domain: str, cookie: str,
                         base_dir: str, http_prefix: str, nickname: str,
                         domain: str, domain_full: str,
                         onion_domain: str, i2p_domain: str,
                         default_timeline: str, theme_name: str,
                         allow_local_network_access: bool,
                         system_language: str,
                         dyslexic_font: bool) -> None:
    """Receive POST from webapp_theme_designer
    """
    users_path = '/users/' + nickname
    origin_path_str = \
        http_prefix + '://' + domain_full + users_path + '/' + \
        default_timeline
    length = int(self.headers['Content-length'])

    try:
        theme_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST theme_params ' +
                  'connection reset by peer')
        else:
            print('EX: POST theme_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST theme_params rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    theme_params = \
        urllib.parse.unquote_plus(theme_params)

    # theme designer screen, reset button
    # See html_theme_designer
    if 'submitThemeDesignerReset=' in theme_params or \
       'submitThemeDesigner=' not in theme_params:
        if 'submitThemeDesignerReset=' in theme_params:
            reset_theme_designer_settings(base_dir)
            self.server.css_cache = {}
            set_theme(base_dir, theme_name, domain,
                      allow_local_network_access, system_language,
                      dyslexic_font, True)

        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str = \
                'http://' + onion_domain + users_path + '/' + \
                default_timeline
        elif calling_domain.endswith('.i2p') and i2p_domain:
            origin_path_str = \
                'http://' + i2p_domain + users_path + \
                '/' + default_timeline
        redirect_headers(self, origin_path_str, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    fields = {}
    fields_list = theme_params.split('&')
    for field_str in fields_list:
        if '=' not in field_str:
            continue
        field_value = field_str.split('=')[1].strip()
        if not field_value:
            continue
        if field_value == 'on':
            field_value = 'True'
        fields_index = field_str.split('=')[0]
        fields[fields_index] = field_value

    # Check for boolean values which are False.
    # These don't come through via theme_params,
    # so need to be checked separately
    theme_filename = base_dir + '/theme/' + theme_name + '/theme.json'
    theme_json = load_json(theme_filename)
    if theme_json:
        for variable_name, value in theme_json.items():
            variable_name = 'themeSetting_' + variable_name
            if value.lower() == 'false' or value.lower() == 'true':
                if variable_name not in fields:
                    fields[variable_name] = 'False'

    # get the parameters from the theme designer screen
    theme_designer_params = {}
    for variable_name, key in fields.items():
        if variable_name.startswith('themeSetting_'):
            variable_name = variable_name.replace('themeSetting_', '')
            theme_designer_params[variable_name] = key

    self.server.css_cache = {}
    set_theme_from_designer(base_dir, theme_name, domain,
                            theme_designer_params,
                            allow_local_network_access,
                            system_language, dyslexic_font)

    # set boolean values
    if 'rss-icon-at-top' in theme_designer_params:
        if theme_designer_params['rss-icon-at-top'].lower() == 'true':
            self.server.rss_icon_at_top = True
        else:
            self.server.rss_icon_at_top = False
    if 'publish-button-at-top' in theme_designer_params:
        publish_button_at_top_str = \
            theme_designer_params['publish-button-at-top'].lower()
        if publish_button_at_top_str == 'true':
            self.server.publish_button_at_top = True
        else:
            self.server.publish_button_at_top = False
    if 'newswire-publish-icon' in theme_designer_params:
        newswire_publish_icon_str = \
            theme_designer_params['newswire-publish-icon'].lower()
        if newswire_publish_icon_str == 'true':
            self.server.show_publish_as_icon = True
        else:
            self.server.show_publish_as_icon = False
    if 'icons-as-buttons' in theme_designer_params:
        if theme_designer_params['icons-as-buttons'].lower() == 'true':
            self.server.icons_as_buttons = True
        else:
            self.server.icons_as_buttons = False
    if 'full-width-timeline-buttons' in theme_designer_params:
        theme_value = theme_designer_params['full-width-timeline-buttons']
        if theme_value.lower() == 'true':
            self.server.full_width_tl_button_header = True
        else:
            self.server.full_width_tl_button_header = False

    # redirect back from theme designer screen
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = \
            'http://' + onion_domain + users_path + '/' + default_timeline
    elif calling_domain.endswith('.i2p') and i2p_domain:
        origin_path_str = \
            'http://' + i2p_domain + users_path + '/' + default_timeline
    redirect_headers(self, origin_path_str, cookie, calling_domain)
    self.server.postreq_busy = False
    return


def _send_reply_to_question(self, base_dir: str,
                            http_prefix: str,
                            nickname: str, domain: str,
                            domain_full: str,
                            port: int,
                            message_id: str,
                            answer: str,
                            curr_session, proxy_type: str,
                            city_name: str,
                            person_cache: {},
                            debug: bool,
                            system_language: str,
                            low_bandwidth: bool,
                            dm_license_url: str,
                            content_license_url: str,
                            translate: {},
                            max_replies: int,
                            project_version: str,
                            recent_posts_cache: {}) -> None:
    """Sends a reply to a question
    """
    votes_filename = \
        acct_dir(base_dir, nickname, domain) + \
        '/questions.txt'

    if os.path.isfile(votes_filename):
        # have we already voted on this?
        if text_in_file(message_id, votes_filename):
            print('Already voted on message ' + message_id)
            return

    print('Voting on message ' + message_id)
    print('Vote for: ' + answer)
    comments_enabled = True
    attach_image_filename = None
    media_type = None
    image_description = None
    video_transcript = None
    in_reply_to = message_id
    in_reply_to_atom_uri = message_id
    subject = None
    schedule_post = False
    event_date = None
    event_time = None
    event_end_time = None
    location = None
    conversation_id = None
    buy_url = ''
    chat_url = ''
    city = get_spoofed_city(city_name, base_dir, nickname, domain)
    languages_understood = \
        get_understood_languages(base_dir, http_prefix,
                                 nickname, domain_full,
                                 person_cache)
    reply_to_nickname = get_nickname_from_actor(in_reply_to)
    reply_to_domain, reply_to_port = get_domain_from_actor(in_reply_to)
    message_json = None
    if reply_to_nickname and reply_to_domain:
        reply_to_domain_full = \
            get_full_domain(reply_to_domain, reply_to_port)
        mentions_str = '@' + reply_to_nickname + '@' + reply_to_domain_full

        message_json = \
            create_direct_message_post(base_dir, nickname, domain,
                                       port, http_prefix,
                                       mentions_str + ' ' + answer,
                                       False, False,
                                       comments_enabled,
                                       attach_image_filename,
                                       media_type, image_description,
                                       video_transcript, city,
                                       in_reply_to, in_reply_to_atom_uri,
                                       subject, debug,
                                       schedule_post,
                                       event_date, event_time,
                                       event_end_time,
                                       location,
                                       system_language,
                                       conversation_id,
                                       low_bandwidth,
                                       dm_license_url,
                                       content_license_url, '',
                                       languages_understood, False,
                                       translate, buy_url,
                                       chat_url,
                                       self.server.auto_cw_cache)
    if message_json:
        # NOTE: content and contentMap are not required, but we will keep
        # them in there so that the post does not get filtered out by
        # inbox processing.
        # name field contains the answer
        message_json['object']['name'] = answer
        if post_to_outbox(self, message_json,
                          project_version, nickname,
                          curr_session, proxy_type):
            post_filename = \
                locate_post(base_dir, nickname, domain, message_id)
            if post_filename:
                post_json_object = load_json(post_filename)
                if post_json_object:
                    populate_replies(base_dir,
                                     http_prefix,
                                     domain_full,
                                     post_json_object,
                                     max_replies,
                                     debug)
                    # record the vote
                    try:
                        with open(votes_filename, 'a+',
                                  encoding='utf-8') as votes_file:
                            votes_file.write(message_id + '\n')
                    except OSError:
                        print('EX: unable to write vote ' +
                              votes_filename)

                    # ensure that the cached post is removed if it exists,
                    # so that it then will be recreated
                    cached_post_filename = \
                        get_cached_post_filename(base_dir,
                                                 nickname, domain,
                                                 post_json_object)
                    if cached_post_filename:
                        if os.path.isfile(cached_post_filename):
                            try:
                                os.remove(cached_post_filename)
                            except OSError:
                                print('EX: _send_reply_to_question ' +
                                      'unable to delete ' +
                                      cached_post_filename)
                    # remove from memory cache
                    remove_post_from_cache(post_json_object,
                                           recent_posts_cache)
        else:
            print('ERROR: unable to post vote to outbox')
    else:
        print('ERROR: unable to create vote')


def _receive_image(self, length: int, path: str, base_dir: str,
                   domain: str, debug: bool) -> None:
    """Receives an image via POST
    """
    if not self.outbox_authenticated:
        if debug:
            print('DEBUG: unauthenticated attempt to ' +
                  'post image to outbox')
        self.send_response(403)
        self.end_headers()
        self.server.postreq_busy = False
        return
    path_users_section = path.split('/users/')[1]
    if '/' not in path_users_section:
        http_404(self, 12)
        self.server.postreq_busy = False
        return
    self.post_from_nickname = path_users_section.split('/')[0]
    accounts_dir = acct_dir(base_dir, self.post_from_nickname, domain)
    if not os.path.isdir(accounts_dir):
        http_404(self, 13)
        self.server.postreq_busy = False
        return

    try:
        media_bytes = self.rfile.read(length)
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST media_bytes ' +
                  'connection reset by peer')
        else:
            print('EX: POST media_bytes socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST media_bytes rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    media_filename_base = accounts_dir + '/upload'
    media_filename = \
        media_filename_base + '.' + \
        get_image_extension_from_mime_type(self.headers['Content-type'])
    if not binary_is_image(media_filename, media_bytes):
        print('WARN: _receive_image image binary is not recognized ' +
              media_filename)
    try:
        with open(media_filename, 'wb') as av_file:
            av_file.write(media_bytes)
    except OSError:
        print('EX: unable to write ' + media_filename)
    if debug:
        print('DEBUG: image saved to ' + media_filename)
    self.send_response(201)
    self.end_headers()
    self.server.postreq_busy = False


def _links_update(self, calling_domain: str, cookie: str,
                  path: str, base_dir: str, debug: bool,
                  default_timeline: str,
                  allow_local_network_access: bool) -> None:
    """Updates the left links column of the timeline
    """
    users_path = path.replace('/linksdata', '')
    users_path = users_path.replace('/editlinks', '')
    actor_str = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        users_path

    boundary = None
    if ' boundary=' in self.headers['Content-type']:
        boundary = self.headers['Content-type'].split('boundary=')[1]
        if ';' in boundary:
            boundary = boundary.split(';')[0]

    # get the nickname
    nickname = get_nickname_from_actor(actor_str)
    editor = None
    if nickname:
        editor = is_editor(base_dir, nickname)
    if not nickname or not editor:
        if not nickname:
            print('WARN: nickname not found in ' + actor_str)
        else:
            print('WARN: nickname is not a moderator' + actor_str)
        redirect_headers(self, actor_str, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    if self.headers.get('Content-length'):
        length = int(self.headers['Content-length'])

        # check that the POST isn't too large
        if length > self.server.max_post_length:
            print('Maximum links data length exceeded ' + str(length))
            redirect_headers(self, actor_str, cookie, calling_domain)
            self.server.postreq_busy = False
            return

    try:
        # read the bytes of the http form POST
        post_bytes = self.rfile.read(length)
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: connection was reset while ' +
                  'reading bytes from http form POST')
        else:
            print('EX: error while reading bytes ' +
                  'from http form POST')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: failed to read bytes for POST, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    links_filename = base_dir + '/accounts/links.txt'
    about_filename = base_dir + '/accounts/about.md'
    tos_filename = base_dir + '/accounts/tos.md'
    specification_filename = base_dir + '/accounts/activitypub.md'

    if not boundary:
        if b'--LYNX' in post_bytes:
            boundary = '--LYNX'

    if boundary:
        # extract all of the text fields into a dict
        fields = \
            extract_text_fields_in_post(post_bytes, boundary, debug, None)

        if fields.get('editedLinks'):
            links_str = fields['editedLinks']
            if fields.get('newColLink'):
                if links_str:
                    if not links_str.endswith('\n'):
                        links_str += '\n'
                links_str += fields['newColLink'] + '\n'
            try:
                with open(links_filename, 'w+',
                          encoding='utf-8') as linksfile:
                    linksfile.write(links_str)
            except OSError:
                print('EX: _links_update unable to write ' +
                      links_filename)
        else:
            if fields.get('newColLink'):
                # the text area is empty but there is a new link added
                links_str = fields['newColLink'] + '\n'
                try:
                    with open(links_filename, 'w+',
                              encoding='utf-8') as linksfile:
                        linksfile.write(links_str)
                except OSError:
                    print('EX: _links_update unable to write ' +
                          links_filename)
            else:
                if os.path.isfile(links_filename):
                    try:
                        os.remove(links_filename)
                    except OSError:
                        print('EX: _links_update unable to delete ' +
                              links_filename)

        admin_nickname = \
            get_config_param(base_dir, 'admin')
        if nickname == admin_nickname:
            if fields.get('editedAbout'):
                about_str = fields['editedAbout']
                if not dangerous_markup(about_str,
                                        allow_local_network_access, []):
                    try:
                        with open(about_filename, 'w+',
                                  encoding='utf-8') as aboutfile:
                            aboutfile.write(about_str)
                    except OSError:
                        print('EX: unable to write about ' +
                              about_filename)
            else:
                if os.path.isfile(about_filename):
                    try:
                        os.remove(about_filename)
                    except OSError:
                        print('EX: _links_update unable to delete ' +
                              about_filename)

            if fields.get('editedTOS'):
                tos_str = fields['editedTOS']
                if not dangerous_markup(tos_str,
                                        allow_local_network_access, []):
                    try:
                        with open(tos_filename, 'w+',
                                  encoding='utf-8') as tosfile:
                            tosfile.write(tos_str)
                    except OSError:
                        print('EX: unable to write TOS ' + tos_filename)
            else:
                if os.path.isfile(tos_filename):
                    try:
                        os.remove(tos_filename)
                    except OSError:
                        print('EX: _links_update unable to delete ' +
                              tos_filename)

            if fields.get('editedSpecification'):
                specification_str = fields['editedSpecification']
                try:
                    with open(specification_filename, 'w+',
                              encoding='utf-8') as specificationfile:
                        specificationfile.write(specification_str)
                except OSError:
                    print('EX: unable to write specification ' +
                          specification_filename)
            else:
                if os.path.isfile(specification_filename):
                    try:
                        os.remove(specification_filename)
                    except OSError:
                        print('EX: _links_update unable to delete ' +
                              specification_filename)

    # redirect back to the default timeline
    redirect_headers(self, actor_str + '/' + default_timeline,
                     cookie, calling_domain)
    self.server.postreq_busy = False


def _set_hashtag_category2(self, calling_domain: str, cookie: str,
                           path: str, base_dir: str,
                           domain: str, debug: bool,
                           system_language: str) -> None:
    """On the screen after selecting a hashtag from the swarm, this sets
    the category for that tag
    """
    users_path = path.replace('/sethashtagcategory', '')
    hashtag = ''
    if '/tags/' not in users_path:
        # no hashtag is specified within the path
        http_404(self, 14)
        return
    hashtag = users_path.split('/tags/')[1].strip()
    hashtag = urllib.parse.unquote_plus(hashtag)
    if not hashtag:
        # no hashtag was given in the path
        http_404(self, 15)
        return
    hashtag_filename = base_dir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtag_filename):
        # the hashtag does not exist
        http_404(self, 16)
        return
    users_path = users_path.split('/tags/')[0]
    actor_str = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        users_path
    tag_screen_str = actor_str + '/tags/' + hashtag

    boundary = None
    if ' boundary=' in self.headers['Content-type']:
        boundary = self.headers['Content-type'].split('boundary=')[1]
        if ';' in boundary:
            boundary = boundary.split(';')[0]

    # get the nickname
    nickname = get_nickname_from_actor(actor_str)
    editor = None
    if nickname:
        editor = is_editor(base_dir, nickname)
    if not hashtag or not editor:
        if not nickname:
            print('WARN: nickname not found in ' + actor_str)
        else:
            print('WARN: nickname is not a moderator' + actor_str)
        redirect_headers(self, tag_screen_str, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    if self.headers.get('Content-length'):
        length = int(self.headers['Content-length'])

        # check that the POST isn't too large
        if length > self.server.max_post_length:
            print('Maximum links data length exceeded ' + str(length))
            redirect_headers(self, tag_screen_str, cookie, calling_domain)
            self.server.postreq_busy = False
            return

    try:
        # read the bytes of the http form POST
        post_bytes = self.rfile.read(length)
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: connection was reset while ' +
                  'reading bytes from http form POST')
        else:
            print('EX: error while reading bytes ' +
                  'from http form POST')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: failed to read bytes for POST, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if not boundary:
        if b'--LYNX' in post_bytes:
            boundary = '--LYNX'

    if boundary:
        # extract all of the text fields into a dict
        fields = \
            extract_text_fields_in_post(post_bytes, boundary, debug, None)

        if fields.get('hashtagCategory'):
            category_str = fields['hashtagCategory'].lower()
            if not is_blocked_hashtag(base_dir, category_str) and \
               not is_filtered(base_dir, nickname, domain, category_str,
                               system_language):
                set_hashtag_category(base_dir, hashtag,
                                     category_str, False)
        else:
            category_filename = base_dir + '/tags/' + hashtag + '.category'
            if os.path.isfile(category_filename):
                try:
                    os.remove(category_filename)
                except OSError:
                    print('EX: _set_hashtag_category unable to delete ' +
                          category_filename)

    # redirect back to the default timeline
    redirect_headers(self, tag_screen_str,
                     cookie, calling_domain)
    self.server.postreq_busy = False


def _receive_vote(self, calling_domain: str, cookie: str,
                  path: str, http_prefix: str,
                  domain: str, domain_full: str, port: int,
                  onion_domain: str, i2p_domain: str,
                  curr_session, proxy_type: str,
                  base_dir: str, city: str,
                  person_cache: {}, debug: bool,
                  system_language: str,
                  low_bandwidth: bool,
                  dm_license_url: str,
                  content_license_url: str,
                  translate: {}, max_replies: int,
                  project_version: str,
                  recent_posts_cache: {}) -> None:
    """Receive a vote on a question via POST
    """
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        path = path.split('?firstpost=')[0]
    if ';firstpost=' in path:
        first_post_id = path.split(';firstpost=')[1]
        path = path.split(';firstpost=')[0]
    if first_post_id:
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        if ';' in first_post_id:
            first_post_id = first_post_id.split(';')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')

    last_post_id = ''
    if '?lastpost=' in path:
        last_post_id = path.split('?lastpost=')[1]
        path = path.split('?lastpost=')[0]
    if ';lastpost=' in path:
        last_post_id = path.split(';lastpost=')[1]
        path = path.split(';lastpost=')[0]
    if last_post_id:
        if '?' in last_post_id:
            last_post_id = last_post_id.split('?')[0]
        if ';' in last_post_id:
            last_post_id = last_post_id.split(';')[0]
        last_post_id = last_post_id.replace('/', '--')
        last_post_id = ';lastpost=' + last_post_id.replace('#', '--')

    page_number = 1
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)

    # the actor who votes
    users_path = path.replace('/question', '')
    actor = http_prefix + '://' + domain_full + users_path
    nickname = get_nickname_from_actor(actor)
    if not nickname:
        if calling_domain.endswith('.onion') and onion_domain:
            actor = 'http://' + onion_domain + users_path
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            actor = 'http://' + i2p_domain + users_path
        actor_path_str = \
            actor + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, actor_path_str,
                         cookie, calling_domain)
        self.server.postreq_busy = False
        return

    # get the parameters
    length = int(self.headers['Content-length'])

    try:
        question_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST question_params connection was reset')
        else:
            print('EX: POST question_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST question_params rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    question_params = question_params.replace('+', ' ')
    question_params = question_params.replace('%3F', '')
    question_params = \
        urllib.parse.unquote_plus(question_params.strip())

    # post being voted on
    message_id = None
    if 'messageId=' in question_params:
        message_id = question_params.split('messageId=')[1]
        if '&' in message_id:
            message_id = message_id.split('&')[0]

    answer = None
    if 'answer=' in question_params:
        answer = question_params.split('answer=')[1]
        if '&' in answer:
            answer = answer.split('&')[0]

    _send_reply_to_question(self, base_dir, http_prefix,
                            nickname, domain, domain_full, port,
                            message_id, answer,
                            curr_session, proxy_type, city,
                            person_cache, debug,
                            system_language,
                            low_bandwidth,
                            dm_license_url,
                            content_license_url,
                            translate, max_replies,
                            project_version,
                            recent_posts_cache)
    if calling_domain.endswith('.onion') and onion_domain:
        actor = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        actor = 'http://' + i2p_domain + users_path
    actor_path_str = \
        actor + '/' + self.server.default_timeline + \
        '?page=' + str(page_number) + first_post_id + last_post_id
    redirect_headers(self, actor_path_str, cookie,
                     calling_domain)
    self.server.postreq_busy = False
    return
