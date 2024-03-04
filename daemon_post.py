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
import urllib.parse
from socket import error as SocketError
from utils import save_json
from utils import get_config_param
from utils import decoded_host
from utils import get_new_post_endpoints
from utils import local_actor_url
from utils import contains_invalid_chars
from utils import remove_id_ending
from utils import check_bad_path
from utils import acct_dir
from blocking import contains_military_domain
from crawlers import blocked_user_agent
from session import get_session_for_domain
from session import establish_session
from fitnessFunctions import fitness_performance
from shares import update_shared_item_federation_token
from inbox import inbox_message_has_params
from inbox import inbox_permitted_message
from httpsig import getheader_signature_input
from httpcodes import http_200
from httpcodes import http_404
from httpcodes import http_400
from httpcodes import http_503
from httpheaders import redirect_headers
from daemon_utils import get_user_agent
from daemon_utils import post_to_outbox
from daemon_utils import update_inbox_queue
from daemon_utils import is_authorized
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
from daemon_post_question import receive_vote
from daemon_post_theme import theme_designer_edit
from daemon_post_hashtags import set_hashtag_category2
from daemon_post_links import links_update
from daemon_post_image import receive_image_attachment

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
        set_hashtag_category2(self, calling_domain, cookie,
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
        links_update(self, calling_domain, cookie, self.path,
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
            receive_vote(self, calling_domain, cookie,
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

            theme_designer_edit(self, calling_domain, cookie,
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
        receive_image_attachment(self, length, self.path,
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
