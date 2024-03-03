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
from utils import clear_from_post_caches
from utils import first_paragraph_from_string
from utils import date_from_string_format
from utils import dangerous_markup
from utils import binary_is_image
from utils import get_image_extension_from_mime_type
from utils import remove_post_from_cache
from utils import get_cached_post_filename
from utils import text_in_file
from utils import has_users_path
from utils import has_group_type
from utils import get_status_number
from utils import remove_eol
from utils import load_json
from utils import save_json
from utils import delete_post
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
from blocking import add_global_block
from blocking import update_blocked_cache
from blocking import remove_global_block
from blocking import remove_block
from blocking import add_block
from crawlers import blocked_user_agent
from session import get_session_for_domain
from session import establish_session
from fitnessFunctions import fitness_performance
from shares import add_shares_to_actor
from shares import remove_shared_item2
from shares import update_shared_item_federation_token
from inbox import populate_replies
from inbox import inbox_message_has_params
from inbox import inbox_permitted_message
from httpsig import getheader_signature_input
from person import get_actor_update_json
from content import load_dogwhistles
from content import extract_text_fields_in_post
from filters import is_filtered
from filters import add_global_filter
from filters import remove_global_filter
from categories import set_hashtag_category
from httpcodes import write2
from httpcodes import http_200
from httpcodes import http_404
from httpcodes import http_400
from httpcodes import http_503
from httpheaders import login_headers
from httpheaders import redirect_headers
from daemon_utils import get_user_agent
from daemon_utils import show_person_options
from daemon_utils import post_to_outbox
from daemon_utils import update_inbox_queue
from daemon_utils import is_authorized
from posts import is_moderator
from webapp_moderation import html_account_info
from webapp_moderation import html_moderation_info
from person import suspend_account
from person import reenable_account
from person import remove_account
from person import can_remove_post
from cache import store_person_in_cache
from cache import remove_person_from_cache
from cache import get_person_from_cache
from cache import clear_actor_cache
from theme import reset_theme_designer_settings
from theme import set_theme
from theme import set_theme_from_designer
from webapp_profile import html_profile_after_search
from webapp_search import html_hashtag_search
from languages import get_understood_languages
from follow import send_follow_request
from follow import unfollow_account
from follow import remove_follower
from follow import is_follower_of_person
from follow import is_following_actor
from daemon_utils import post_to_outbox_thread
from reading import remove_reading_event
from webapp_search import html_skills_search
from webapp_search import html_history_search
from webapp_search import html_search_emoji
from webapp_search import html_search_shared_items
from webapp_utils import get_avatar_image_url
from city import get_spoofed_city
from posts import create_direct_message_post
from happening import remove_calendar_event
from daemon_post_login import post_login_screen
from daemon_post_receive import receive_new_post
from daemon_post_profile import profile_edit
from daemon_post_person_options import person_options2

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
        _newswire_update(self, calling_domain, cookie,
                         self.path,
                         self.server.base_dir,
                         self.server.domain, self.server.debug,
                         self.server.default_timeline)
        self.server.postreq_busy = False
        return

    if authorized and self.path.endswith('/citationsdata'):
        _citations_update(self, calling_domain, cookie,
                          self.path,
                          self.server.base_dir,
                          self.server.domain,
                          self.server.debug,
                          self.server.newswire)
        self.server.postreq_busy = False
        return

    if authorized and self.path.endswith('/newseditdata'):
        _news_post_edit(self, calling_domain, cookie, self.path,
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
        _moderator_actions(self,
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
        _receive_search_query(self, calling_domain, cookie,
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
                              proxy_type)
        self.server.postreq_busy = False
        return

    fitness_performance(postreq_start_time, self.server.fitness,
                        '_POST', '_receive_search_query',
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
            _remove_share(self, calling_domain, cookie,
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
            _remove_wanted(self, calling_domain, cookie,
                           authorized, self.path,
                           self.server.base_dir,
                           self.server.http_prefix,
                           self.server.domain_full,
                           self.server.onion_domain,
                           self.server.i2p_domain)
            self.server.postreq_busy = False
            return

        fitness_performance(postreq_start_time, self.server.fitness,
                            '_POST', '_remove_wanted',
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
            _receive_remove_post(self, calling_domain, cookie,
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
            _follow_confirm(self, calling_domain, cookie,
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
                            '_POST', '_follow_confirm',
                            self.server.debug)

        # remove a reading status from the profile screen
        if self.path.endswith('/removereadingstatus'):
            _remove_reading_status(self, calling_domain, cookie,
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
                            '_POST', '_remove_reading_status',
                            self.server.debug)

        # decision to unfollow in the web interface is confirmed
        if self.path.endswith('/unfollowconfirm'):
            _unfollow_confirm(self, calling_domain, cookie,
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
                            '_POST', '_unfollow_confirm',
                            self.server.debug)

        # decision to unblock in the web interface is confirmed
        if self.path.endswith('/unblockconfirm'):
            _unblock_confirm(self, calling_domain, cookie,
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
                            '_POST', '_unblock_confirm',
                            self.server.debug)

        # decision to block in the web interface is confirmed
        if self.path.endswith('/blockconfirm'):
            _block_confirm(self, calling_domain, cookie,
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
                            '_POST', '_block_confirm',
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


def _moderator_actions(self, path: str, calling_domain: str, cookie: str,
                       base_dir: str, http_prefix: str,
                       domain: str, port: int, debug: bool) -> None:
    """Actions on the moderator screen
    """
    users_path = path.replace('/moderationaction', '')
    nickname = users_path.replace('/users/', '')
    actor_str = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        users_path
    if not is_moderator(self.server.base_dir, nickname):
        redirect_headers(self, actor_str + '/moderation',
                         cookie, calling_domain)
        self.server.postreq_busy = False
        return

    length = int(self.headers['Content-length'])

    try:
        moderation_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST moderation_params connection was reset')
        else:
            print('EX: POST moderation_params ' +
                  'rfile.read socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST moderation_params rfile.read failed, ' +
              str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if '&' in moderation_params:
        moderation_text = None
        moderation_button = None
        # get the moderation text first
        act_str = 'moderationAction='
        for moderation_str in moderation_params.split('&'):
            if moderation_str.startswith(act_str):
                if act_str in moderation_str:
                    moderation_text = \
                        moderation_str.split(act_str)[1].strip()
                    mod_text = moderation_text.replace('+', ' ')
                    moderation_text = \
                        urllib.parse.unquote_plus(mod_text.strip())
        # which button was pressed?
        for moderation_str in moderation_params.split('&'):
            if moderation_str.startswith('submitInfo='):
                if not moderation_text and \
                   'submitInfo=' in moderation_str:
                    moderation_text = \
                        moderation_str.split('submitInfo=')[1].strip()
                    mod_text = moderation_text.replace('+', ' ')
                    moderation_text = \
                        urllib.parse.unquote_plus(mod_text.strip())
                search_handle = moderation_text
                if search_handle:
                    if '/@' in search_handle and \
                       '/@/' not in search_handle:
                        search_nickname = \
                            get_nickname_from_actor(search_handle)
                        if search_nickname:
                            search_domain, _ = \
                                get_domain_from_actor(search_handle)
                            if search_domain:
                                search_handle = \
                                    search_nickname + '@' + search_domain
                            else:
                                search_handle = ''
                        else:
                            search_handle = ''
                    if '@' not in search_handle or \
                       '/@/' in search_handle:
                        if search_handle.startswith('http') or \
                           search_handle.startswith('ipfs') or \
                           search_handle.startswith('ipns'):
                            search_nickname = \
                                get_nickname_from_actor(search_handle)
                            if search_nickname:
                                search_domain, _ = \
                                    get_domain_from_actor(search_handle)
                                if search_domain:
                                    search_handle = \
                                        search_nickname + '@' + \
                                        search_domain
                                else:
                                    search_handle = ''
                            else:
                                search_handle = ''
                    if '@' not in search_handle:
                        # is this a local nickname on this instance?
                        local_handle = \
                            search_handle + '@' + self.server.domain
                        if os.path.isdir(self.server.base_dir +
                                         '/accounts/' + local_handle):
                            search_handle = local_handle
                        else:
                            search_handle = ''
                if search_handle is None:
                    search_handle = ''
                if '@' in search_handle:
                    msg = \
                        html_account_info(self.server.translate,
                                          base_dir, http_prefix,
                                          nickname,
                                          self.server.domain,
                                          search_handle,
                                          self.server.debug,
                                          self.server.system_language,
                                          self.server.signing_priv_key_pem,
                                          None,
                                          self.server.block_federated)
                else:
                    msg = \
                        html_moderation_info(self.server.translate,
                                             base_dir, nickname,
                                             self.server.domain,
                                             self.server.theme_name,
                                             self.server.access_keys)
                if msg:
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    login_headers(self, 'text/html',
                                  msglen, calling_domain)
                    write2(self, msg)
                self.server.postreq_busy = False
                return
            if moderation_str.startswith('submitBlock'):
                moderation_button = 'block'
            elif moderation_str.startswith('submitUnblock'):
                moderation_button = 'unblock'
            elif moderation_str.startswith('submitFilter'):
                moderation_button = 'filter'
            elif moderation_str.startswith('submitUnfilter'):
                moderation_button = 'unfilter'
            elif moderation_str.startswith('submitClearCache'):
                moderation_button = 'clearcache'
            elif moderation_str.startswith('submitSuspend'):
                moderation_button = 'suspend'
            elif moderation_str.startswith('submitUnsuspend'):
                moderation_button = 'unsuspend'
            elif moderation_str.startswith('submitRemove'):
                moderation_button = 'remove'
        if moderation_button and moderation_text:
            if debug:
                print('moderation_button: ' + moderation_button)
                print('moderation_text: ' + moderation_text)
            nickname = moderation_text
            if nickname.startswith('http') or \
               nickname.startswith('ipfs') or \
               nickname.startswith('ipns') or \
               nickname.startswith('hyper'):
                nickname = get_nickname_from_actor(nickname)
            if '@' in nickname:
                nickname = nickname.split('@')[0]
            if moderation_button == 'suspend':
                suspend_account(base_dir, nickname, domain)
            if moderation_button == 'unsuspend':
                reenable_account(base_dir, nickname)
            if moderation_button == 'filter':
                add_global_filter(base_dir, moderation_text)
            if moderation_button == 'unfilter':
                remove_global_filter(base_dir, moderation_text)
            if moderation_button == 'clearcache':
                clear_actor_cache(base_dir,
                                  self.server.person_cache,
                                  moderation_text)
            if moderation_button == 'block':
                full_block_domain = None
                moderation_text = moderation_text.strip()
                moderation_reason = None
                if ' ' in moderation_text:
                    moderation_domain = moderation_text.split(' ', 1)[0]
                    moderation_reason = moderation_text.split(' ', 1)[1]
                else:
                    moderation_domain = moderation_text
                if moderation_domain.startswith('http') or \
                   moderation_domain.startswith('ipfs') or \
                   moderation_domain.startswith('ipns') or \
                   moderation_domain.startswith('hyper'):
                    # https://domain
                    block_domain, block_port = \
                        get_domain_from_actor(moderation_domain)
                    if block_domain:
                        full_block_domain = \
                            get_full_domain(block_domain, block_port)
                if '@' in moderation_domain:
                    # nick@domain or *@domain
                    full_block_domain = \
                        moderation_domain.split('@')[1]
                else:
                    # assume the text is a domain name
                    if not full_block_domain and '.' in moderation_domain:
                        nickname = '*'
                        full_block_domain = \
                            moderation_domain.strip()
                if full_block_domain or nickname.startswith('#'):
                    if nickname.startswith('#') and ' ' in nickname:
                        nickname = nickname.split(' ')[0]
                    add_global_block(base_dir, nickname,
                                     full_block_domain, moderation_reason)
                    blocked_cache_last_updated = \
                        self.server.blocked_cache_last_updated
                    self.server.blocked_cache_last_updated = \
                        update_blocked_cache(self.server.base_dir,
                                             self.server.blocked_cache,
                                             blocked_cache_last_updated, 0)
            if moderation_button == 'unblock':
                full_block_domain = None
                if ' ' in moderation_text:
                    moderation_domain = moderation_text.split(' ', 1)[0]
                else:
                    moderation_domain = moderation_text
                if moderation_domain.startswith('http') or \
                   moderation_domain.startswith('ipfs') or \
                   moderation_domain.startswith('ipns') or \
                   moderation_domain.startswith('hyper'):
                    # https://domain
                    block_domain, block_port = \
                        get_domain_from_actor(moderation_domain)
                    if block_domain:
                        full_block_domain = \
                            get_full_domain(block_domain, block_port)
                if '@' in moderation_domain:
                    # nick@domain or *@domain
                    full_block_domain = moderation_domain.split('@')[1]
                else:
                    # assume the text is a domain name
                    if not full_block_domain and '.' in moderation_domain:
                        nickname = '*'
                        full_block_domain = moderation_domain.strip()
                if full_block_domain or nickname.startswith('#'):
                    if nickname.startswith('#') and ' ' in nickname:
                        nickname = nickname.split(' ')[0]
                    remove_global_block(base_dir, nickname,
                                        full_block_domain)
                    blocked_cache_last_updated = \
                        self.server.blocked_cache_last_updated
                    self.server.blocked_cache_last_updated = \
                        update_blocked_cache(self.server.base_dir,
                                             self.server.blocked_cache,
                                             blocked_cache_last_updated, 0)
            if moderation_button == 'remove':
                if '/statuses/' not in moderation_text:
                    remove_account(base_dir, nickname, domain, port)
                else:
                    # remove a post or thread
                    post_filename = \
                        locate_post(base_dir, nickname, domain,
                                    moderation_text)
                    if post_filename:
                        if can_remove_post(base_dir, domain, port,
                                           moderation_text):
                            delete_post(base_dir,
                                        http_prefix,
                                        nickname, domain,
                                        post_filename,
                                        debug,
                                        self.server.recent_posts_cache,
                                        True)
                    if nickname != 'news':
                        # if this is a local blog post then also remove it
                        # from the news actor
                        post_filename = \
                            locate_post(base_dir, 'news', domain,
                                        moderation_text)
                        if post_filename:
                            if can_remove_post(base_dir, domain, port,
                                               moderation_text):
                                delete_post(base_dir,
                                            http_prefix,
                                            'news', domain,
                                            post_filename,
                                            debug,
                                            self.server.recent_posts_cache,
                                            True)

    redirect_headers(self, actor_str + '/moderation',
                     cookie, calling_domain)
    self.server.postreq_busy = False
    return


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


def _unfollow_confirm(self, calling_domain: str, cookie: str,
                      path: str, base_dir: str, http_prefix: str,
                      domain: str, domain_full: str, port: int,
                      onion_domain: str, i2p_domain: str,
                      debug: bool,
                      curr_session, proxy_type: str) -> None:
    """Confirm to unfollow
    """
    users_path = path.split('/unfollowconfirm')[0]
    origin_path_str = http_prefix + '://' + domain_full + users_path
    follower_nickname = get_nickname_from_actor(origin_path_str)
    if not follower_nickname:
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    length = int(self.headers['Content-length'])

    try:
        follow_confirm_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST follow_confirm_params ' +
                  'connection was reset')
        else:
            print('EX: POST follow_confirm_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST follow_confirm_params rfile.read failed, ' +
              str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if '&submitYes=' in follow_confirm_params:
        following_actor = \
            urllib.parse.unquote_plus(follow_confirm_params)
        following_actor = following_actor.split('actor=')[1]
        if '&' in following_actor:
            following_actor = following_actor.split('&')[0]
        following_nickname = get_nickname_from_actor(following_actor)
        following_domain, following_port = \
            get_domain_from_actor(following_actor)
        if not following_nickname or not following_domain:
            self.send_response(400)
            self.end_headers()
            self.server.postreq_busy = False
            return
        following_domain_full = \
            get_full_domain(following_domain, following_port)
        if follower_nickname == following_nickname and \
           following_domain == domain and \
           following_port == port:
            if debug:
                print('You cannot unfollow yourself!')
        else:
            if debug:
                print(follower_nickname + ' stops following ' +
                      following_actor)
            follow_actor = \
                local_actor_url(http_prefix,
                                follower_nickname, domain_full)
            status_number, _ = get_status_number()
            follow_id = follow_actor + '/statuses/' + str(status_number)
            unfollow_json = {
                '@context': 'https://www.w3.org/ns/activitystreams',
                'id': follow_id + '/undo',
                'type': 'Undo',
                'actor': follow_actor,
                'object': {
                    'id': follow_id,
                    'type': 'Follow',
                    'actor': follow_actor,
                    'object': following_actor
                }
            }
            path_users_section = path.split('/users/')[1]
            self.post_to_nickname = path_users_section.split('/')[0]
            group_account = has_group_type(base_dir, following_actor,
                                           self.server.person_cache)
            unfollow_account(self.server.base_dir, self.post_to_nickname,
                             self.server.domain,
                             following_nickname, following_domain_full,
                             self.server.debug, group_account,
                             'following.txt')
            post_to_outbox_thread(self, unfollow_json,
                                  curr_session, proxy_type)

    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str = 'http://' + i2p_domain + users_path
    redirect_headers(self, origin_path_str, cookie, calling_domain)
    self.server.postreq_busy = False


def _follow_confirm(self, calling_domain: str, cookie: str,
                    path: str, base_dir: str, http_prefix: str,
                    domain: str, domain_full: str, port: int,
                    onion_domain: str, i2p_domain: str,
                    debug: bool,
                    curr_session, proxy_type: str) -> None:
    """Confirm to follow
    """
    users_path = path.split('/followconfirm')[0]
    origin_path_str = http_prefix + '://' + domain_full + users_path
    follower_nickname = get_nickname_from_actor(origin_path_str)
    if not follower_nickname:
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    length = int(self.headers['Content-length'])

    try:
        follow_confirm_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST follow_confirm_params ' +
                  'connection was reset')
        else:
            print('EX: POST follow_confirm_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST follow_confirm_params rfile.read failed, ' +
              str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if '&submitView=' in follow_confirm_params:
        following_actor = \
            urllib.parse.unquote_plus(follow_confirm_params)
        following_actor = following_actor.split('actor=')[1]
        if '&' in following_actor:
            following_actor = following_actor.split('&')[0]
        redirect_headers(self, following_actor, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    if '&submitInfo=' in follow_confirm_params:
        following_actor = \
            urllib.parse.unquote_plus(follow_confirm_params)
        following_actor = following_actor.split('actor=')[1]
        if '&' in following_actor:
            following_actor = following_actor.split('&')[0]
        if is_moderator(base_dir, follower_nickname):
            msg = \
                html_account_info(self.server.translate,
                                  base_dir, http_prefix,
                                  follower_nickname,
                                  self.server.domain,
                                  following_actor,
                                  self.server.debug,
                                  self.server.system_language,
                                  self.server.signing_priv_key_pem,
                                  users_path,
                                  self.server.block_federated)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
        redirect_headers(self, following_actor, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    if '&submitYes=' in follow_confirm_params:
        following_actor = \
            urllib.parse.unquote_plus(follow_confirm_params)
        following_actor = following_actor.split('actor=')[1]
        if '&' in following_actor:
            following_actor = following_actor.split('&')[0]
        following_nickname = get_nickname_from_actor(following_actor)
        following_domain, following_port = \
            get_domain_from_actor(following_actor)
        if not following_nickname or not following_domain:
            self.send_response(400)
            self.end_headers()
            self.server.postreq_busy = False
            return
        if follower_nickname == following_nickname and \
           following_domain == domain and \
           following_port == port:
            if debug:
                print('You cannot follow yourself!')
        elif (following_nickname == 'news' and
              following_domain == domain and
              following_port == port):
            if debug:
                print('You cannot follow the news actor')
        else:
            print('Sending follow request from ' +
                  follower_nickname + ' to ' + following_actor)
            if not self.server.signing_priv_key_pem:
                print('Sending follow request with no signing key')

            curr_domain = domain
            curr_port = port
            curr_http_prefix = http_prefix
            curr_proxy_type = proxy_type
            if onion_domain:
                if not curr_domain.endswith('.onion') and \
                   following_domain.endswith('.onion'):
                    curr_session = self.server.session_onion
                    curr_domain = onion_domain
                    curr_port = 80
                    following_port = 80
                    curr_http_prefix = 'http'
                    curr_proxy_type = 'tor'
            if i2p_domain:
                if not curr_domain.endswith('.i2p') and \
                   following_domain.endswith('.i2p'):
                    curr_session = self.server.session_i2p
                    curr_domain = i2p_domain
                    curr_port = 80
                    following_port = 80
                    curr_http_prefix = 'http'
                    curr_proxy_type = 'i2p'

            curr_session = \
                establish_session("follow request",
                                  curr_session,
                                  curr_proxy_type,
                                  self.server)

            send_follow_request(curr_session,
                                base_dir, follower_nickname,
                                domain, curr_domain, curr_port,
                                curr_http_prefix,
                                following_nickname,
                                following_domain,
                                following_actor,
                                following_port, curr_http_prefix,
                                False, self.server.federation_list,
                                self.server.send_threads,
                                self.server.postLog,
                                self.server.cached_webfingers,
                                self.server.person_cache, debug,
                                self.server.project_version,
                                self.server.signing_priv_key_pem,
                                self.server.domain,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                self.server.sites_unavailable,
                                self.server.system_language)

    if '&submitUnblock=' in follow_confirm_params:
        blocking_actor = \
            urllib.parse.unquote_plus(follow_confirm_params)
        blocking_actor = blocking_actor.split('actor=')[1]
        if '&' in blocking_actor:
            blocking_actor = blocking_actor.split('&')[0]
        blocking_nickname = get_nickname_from_actor(blocking_actor)
        blocking_domain, blocking_port = \
            get_domain_from_actor(blocking_actor)
        if not blocking_nickname or not blocking_domain:
            if calling_domain.endswith('.onion') and onion_domain:
                origin_path_str = 'http://' + onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                origin_path_str = 'http://' + i2p_domain + users_path
            print('WARN: unable to find blocked nickname or domain in ' +
                  blocking_actor)
            redirect_headers(self, origin_path_str,
                             cookie, calling_domain)
            self.server.postreq_busy = False
            return
        blocking_domain_full = \
            get_full_domain(blocking_domain, blocking_port)
        if follower_nickname == blocking_nickname and \
           blocking_domain == domain and \
           blocking_port == port:
            if debug:
                print('You cannot unblock yourself!')
        else:
            if debug:
                print(follower_nickname + ' stops blocking ' +
                      blocking_actor)
            remove_block(base_dir,
                         follower_nickname, domain,
                         blocking_nickname, blocking_domain_full)
            if is_moderator(base_dir, follower_nickname):
                remove_global_block(base_dir,
                                    blocking_nickname,
                                    blocking_domain_full)
                blocked_cache_last_updated = \
                    self.server.blocked_cache_last_updated
                self.server.blocked_cache_last_updated = \
                    update_blocked_cache(self.server.base_dir,
                                         self.server.blocked_cache,
                                         blocked_cache_last_updated, 0)

    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str = 'http://' + i2p_domain + users_path
    redirect_headers(self, origin_path_str, cookie, calling_domain)
    self.server.postreq_busy = False


def _remove_reading_status(self, calling_domain: str, cookie: str,
                           path: str, base_dir: str, http_prefix: str,
                           domain_full: str,
                           onion_domain: str, i2p_domain: str,
                           debug: bool,
                           books_cache: {}) -> None:
    """Remove a reading status from the profile screen
    """
    users_path = path.split('/removereadingstatus')[0]
    origin_path_str = http_prefix + '://' + domain_full + users_path
    reader_nickname = get_nickname_from_actor(origin_path_str)
    if not reader_nickname:
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    length = int(self.headers['Content-length'])

    try:
        remove_reading_status_params = \
            self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST remove_reading_status_params ' +
                  'connection was reset')
        else:
            print('EX: POST remove_reading_status_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST remove_reading_status_params rfile.read failed, ' +
              str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if '&submitRemoveReadingStatus=' in remove_reading_status_params:
        reading_actor = \
            urllib.parse.unquote_plus(remove_reading_status_params)
        reading_actor = reading_actor.split('actor=')[1]
        if '&' in reading_actor:
            reading_actor = reading_actor.split('&')[0]

        if reading_actor == origin_path_str:
            post_secs_since_epoch = \
                urllib.parse.unquote_plus(remove_reading_status_params)
            post_secs_since_epoch = \
                post_secs_since_epoch.split('publishedtimesec=')[1]
            if '&' in post_secs_since_epoch:
                post_secs_since_epoch = post_secs_since_epoch.split('&')[0]

            book_event_type = \
                urllib.parse.unquote_plus(remove_reading_status_params)
            book_event_type = \
                book_event_type.split('bookeventtype=')[1]
            if '&' in book_event_type:
                book_event_type = book_event_type.split('&')[0]

            remove_reading_event(base_dir,
                                 reading_actor, post_secs_since_epoch,
                                 book_event_type, books_cache, debug)

    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str = 'http://' + i2p_domain + users_path
    redirect_headers(self, origin_path_str, cookie, calling_domain)
    self.server.postreq_busy = False


def _block_confirm(self, calling_domain: str, cookie: str,
                   path: str, base_dir: str, http_prefix: str,
                   domain: str, domain_full: str, port: int,
                   onion_domain: str, i2p_domain: str,
                   debug: bool) -> None:
    """Confirms a block from the person options screen
    """
    users_path = path.split('/blockconfirm')[0]
    origin_path_str = http_prefix + '://' + domain_full + users_path
    blocker_nickname = get_nickname_from_actor(origin_path_str)
    if not blocker_nickname:
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str = 'http://' + onion_domain + users_path
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            origin_path_str = 'http://' + i2p_domain + users_path
        print('WARN: unable to find nickname in ' + origin_path_str)
        redirect_headers(self, origin_path_str,
                         cookie, calling_domain)
        self.server.postreq_busy = False
        return

    length = int(self.headers['Content-length'])

    try:
        block_confirm_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST block_confirm_params ' +
                  'connection was reset')
        else:
            print('EX: POST block_confirm_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST block_confirm_params rfile.read failed, ' +
              str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if '&submitYes=' in block_confirm_params:
        blocking_confirm_str = \
            urllib.parse.unquote_plus(block_confirm_params)
        block_reason = blocking_confirm_str.split('blockReason=')[1]
        if '&' in block_reason:
            block_reason = block_reason.split('&')[0]
        blocking_actor = blocking_confirm_str.split('actor=')[1]
        if '&' in blocking_actor:
            blocking_actor = blocking_actor.split('&')[0]
        blocking_nickname = get_nickname_from_actor(blocking_actor)
        blocking_domain, blocking_port = \
            get_domain_from_actor(blocking_actor)
        if not blocking_nickname or not blocking_domain:
            if calling_domain.endswith('.onion') and onion_domain:
                origin_path_str = 'http://' + onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                origin_path_str = 'http://' + i2p_domain + users_path
            print('WARN: unable to find nickname or domain in ' +
                  blocking_actor)
            redirect_headers(self, origin_path_str,
                             cookie, calling_domain)
            self.server.postreq_busy = False
            return
        blocking_domain_full = \
            get_full_domain(blocking_domain, blocking_port)
        if blocker_nickname == blocking_nickname and \
           blocking_domain == domain and \
           blocking_port == port:
            if debug:
                print('You cannot block yourself!')
        else:
            print('Adding block by ' + blocker_nickname +
                  ' of ' + blocking_actor)
            add_block(base_dir, blocker_nickname,
                      domain, blocking_nickname,
                      blocking_domain_full, block_reason)
            remove_follower(base_dir, blocker_nickname,
                            domain,
                            blocking_nickname,
                            blocking_domain_full)
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str = 'http://' + i2p_domain + users_path
    redirect_headers(self, origin_path_str, cookie, calling_domain)
    self.server.postreq_busy = False


def _unblock_confirm(self, calling_domain: str, cookie: str,
                     path: str, base_dir: str, http_prefix: str,
                     domain: str, domain_full: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     debug: bool) -> None:
    """Confirms a unblock
    """
    users_path = path.split('/unblockconfirm')[0]
    origin_path_str = http_prefix + '://' + domain_full + users_path
    blocker_nickname = get_nickname_from_actor(origin_path_str)
    if not blocker_nickname:
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str = 'http://' + onion_domain + users_path
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            origin_path_str = 'http://' + i2p_domain + users_path
        print('WARN: unable to find nickname in ' + origin_path_str)
        redirect_headers(self, origin_path_str,
                         cookie, calling_domain)
        self.server.postreq_busy = False
        return

    length = int(self.headers['Content-length'])

    try:
        block_confirm_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST block_confirm_params ' +
                  'connection was reset')
        else:
            print('EX: POST block_confirm_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST block_confirm_params rfile.read failed, ' +
              str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if '&submitYes=' in block_confirm_params:
        blocking_actor = \
            urllib.parse.unquote_plus(block_confirm_params)
        blocking_actor = blocking_actor.split('actor=')[1]
        if '&' in blocking_actor:
            blocking_actor = blocking_actor.split('&')[0]
        blocking_nickname = get_nickname_from_actor(blocking_actor)
        blocking_domain, blocking_port = \
            get_domain_from_actor(blocking_actor)
        if not blocking_nickname or not blocking_domain:
            if calling_domain.endswith('.onion') and onion_domain:
                origin_path_str = 'http://' + onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                origin_path_str = 'http://' + i2p_domain + users_path
            print('WARN: unable to find nickname in ' + blocking_actor)
            redirect_headers(self, origin_path_str,
                             cookie, calling_domain)
            self.server.postreq_busy = False
            return
        blocking_domain_full = \
            get_full_domain(blocking_domain, blocking_port)
        if blocker_nickname == blocking_nickname and \
           blocking_domain == domain and \
           blocking_port == port:
            if debug:
                print('You cannot unblock yourself!')
        else:
            if debug:
                print(blocker_nickname + ' stops blocking ' +
                      blocking_actor)
            remove_block(base_dir,
                         blocker_nickname, domain,
                         blocking_nickname, blocking_domain_full)
            if is_moderator(base_dir, blocker_nickname):
                remove_global_block(base_dir,
                                    blocking_nickname,
                                    blocking_domain_full)
                blocked_cache_last_updated = \
                    self.server.blocked_cache_last_updated
                self.server.blocked_cache_last_updated = \
                    update_blocked_cache(self.server.base_dir,
                                         self.server.blocked_cache,
                                         blocked_cache_last_updated, 0)
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str = 'http://' + i2p_domain + users_path
    redirect_headers(self, origin_path_str,
                     cookie, calling_domain)
    self.server.postreq_busy = False


def _receive_search_query(self, calling_domain: str, cookie: str,
                          authorized: bool, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str,
                          port: int, search_for_emoji: bool,
                          onion_domain: str, i2p_domain: str,
                          getreq_start_time, debug: bool,
                          curr_session, proxy_type: str) -> None:
    """Receive a search query
    """
    # get the page number
    page_number = 1
    if '/searchhandle?page=' in path:
        page_number_str = path.split('/searchhandle?page=')[1]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
        path = path.split('?page=')[0]

    users_path = path.replace('/searchhandle', '')
    actor_str = \
        get_instance_url(calling_domain,
                         http_prefix,
                         domain_full,
                         onion_domain,
                         i2p_domain) + \
        users_path
    length = int(self.headers['Content-length'])
    try:
        search_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST search_params connection was reset')
        else:
            print('EX: POST search_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST search_params rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    if 'submitBack=' in search_params:
        # go back on search screen
        redirect_headers(self, actor_str + '/' +
                         self.server.default_timeline,
                         cookie, calling_domain)
        self.server.postreq_busy = False
        return
    if 'searchtext=' in search_params:
        search_str = search_params.split('searchtext=')[1]
        if '&' in search_str:
            search_str = search_str.split('&')[0]
        search_str = \
            urllib.parse.unquote_plus(search_str.strip())
        search_str = search_str.strip()
        print('search_str: ' + search_str)
        if search_for_emoji:
            search_str = ':' + search_str + ':'
        if search_str.startswith('#'):
            nickname = get_nickname_from_actor(actor_str)
            if not nickname:
                self.send_response(400)
                self.end_headers()
                self.server.postreq_busy = False
                return

            # hashtag search
            timezone = None
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
            bold_reading = False
            if self.server.bold_reading.get(nickname):
                bold_reading = True
            hashtag_str = \
                html_hashtag_search(nickname, domain, port,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    base_dir,
                                    search_str[1:], 1,
                                    MAX_POSTS_IN_HASHTAG_FEED,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    http_prefix,
                                    self.server.project_version,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    self.server.signing_priv_key_pem,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, bold_reading,
                                    self.server.dogwhistles,
                                    self.server.map_format,
                                    self.server.access_keys,
                                    'search',
                                    self.server.min_images_for_accounts,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
            if hashtag_str:
                msg = hashtag_str.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
        elif (search_str.startswith('*') or
              search_str.endswith(' skill')):
            possible_endings = (
                ' skill'
            )
            for poss_ending in possible_endings:
                if search_str.endswith(poss_ending):
                    search_str = search_str.replace(poss_ending, '')
                    break
            # skill search
            search_str = search_str.replace('*', '').strip()
            nickname = get_nickname_from_actor(actor_str)
            skill_str = \
                html_skills_search(actor_str,
                                   self.server.translate,
                                   base_dir,
                                   search_str,
                                   self.server.instance_only_skills_search,
                                   64, nickname, domain,
                                   self.server.theme_name,
                                   self.server.access_keys)
            if skill_str:
                msg = skill_str.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
        elif (search_str.startswith("'") or
              search_str.endswith(' history') or
              search_str.endswith(' in sent') or
              search_str.endswith(' in outbox') or
              search_str.endswith(' in outgoing') or
              search_str.endswith(' in sent items') or
              search_str.endswith(' in sent posts') or
              search_str.endswith(' in outgoing posts') or
              search_str.endswith(' in my history') or
              search_str.endswith(' in my outbox') or
              search_str.endswith(' in my posts')):
            possible_endings = (
                ' in my posts',
                ' in my history',
                ' in my outbox',
                ' in sent posts',
                ' in outgoing posts',
                ' in sent items',
                ' in history',
                ' in outbox',
                ' in outgoing',
                ' in sent',
                ' history'
            )
            for poss_ending in possible_endings:
                if search_str.endswith(poss_ending):
                    search_str = search_str.replace(poss_ending, '')
                    break
            # your post history search
            nickname = get_nickname_from_actor(actor_str)
            if not nickname:
                self.send_response(400)
                self.end_headers()
                self.server.postreq_busy = False
                return
            search_str = search_str.replace("'", '', 1).strip()
            timezone = None
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
            bold_reading = False
            if self.server.bold_reading.get(nickname):
                bold_reading = True
            history_str = \
                html_history_search(self.server.translate,
                                    base_dir,
                                    http_prefix,
                                    nickname,
                                    domain,
                                    search_str,
                                    MAX_POSTS_IN_FEED,
                                    page_number,
                                    self.server.project_version,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    port,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name, 'outbox',
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    self.server.signing_priv_key_pem,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, bold_reading,
                                    self.server.dogwhistles,
                                    self.server.access_keys,
                                    self.server.min_images_for_accounts,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
            if history_str:
                msg = history_str.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
        elif (search_str.startswith('-') or
              search_str.endswith(' in my saved items') or
              search_str.endswith(' in my saved posts') or
              search_str.endswith(' in my bookmarks') or
              search_str.endswith(' in my saved') or
              search_str.endswith(' in my saves') or
              search_str.endswith(' in saved posts') or
              search_str.endswith(' in saved items') or
              search_str.endswith(' in bookmarks') or
              search_str.endswith(' in saved') or
              search_str.endswith(' in saves') or
              search_str.endswith(' bookmark')):
            possible_endings = (
                ' in my bookmarks'
                ' in my saved posts'
                ' in my saved items'
                ' in my saved'
                ' in my saves'
                ' in saved posts'
                ' in saved items'
                ' in saved'
                ' in saves'
                ' in bookmarks'
                ' bookmark'
            )
            for poss_ending in possible_endings:
                if search_str.endswith(poss_ending):
                    search_str = search_str.replace(poss_ending, '')
                    break
            # bookmark search
            nickname = get_nickname_from_actor(actor_str)
            if not nickname:
                self.send_response(400)
                self.end_headers()
                self.server.postreq_busy = False
                return
            search_str = search_str.replace('-', '', 1).strip()
            timezone = None
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
            bold_reading = False
            if self.server.bold_reading.get(nickname):
                bold_reading = True
            bookmarks_str = \
                html_history_search(self.server.translate,
                                    base_dir,
                                    http_prefix,
                                    nickname,
                                    domain,
                                    search_str,
                                    MAX_POSTS_IN_FEED,
                                    page_number,
                                    self.server.project_version,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    port,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name, 'bookmarks',
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    self.server.signing_priv_key_pem,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, bold_reading,
                                    self.server.dogwhistles,
                                    self.server.access_keys,
                                    self.server.min_images_for_accounts,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
            if bookmarks_str:
                msg = bookmarks_str.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
        elif ('@' in search_str or
              ('://' in search_str and
               has_users_path(search_str))):
            remote_only = False
            if search_str.endswith(';remote'):
                search_str = search_str.replace(';remote', '')
                remote_only = True
            if search_str.endswith(':') or \
               search_str.endswith(';') or \
               search_str.endswith('.'):
                actor_str = \
                    get_instance_url(calling_domain, http_prefix,
                                     domain_full, onion_domain,
                                     i2p_domain) + \
                    users_path
                redirect_headers(self, actor_str + '/search',
                                 cookie, calling_domain)
                self.server.postreq_busy = False
                return
            # profile search
            nickname = get_nickname_from_actor(actor_str)
            if not nickname:
                self.send_response(400)
                self.end_headers()
                self.server.postreq_busy = False
                return
            profile_path_str = path.replace('/searchhandle', '')

            # are we already following or followed by the searched
            # for handle?
            search_nickname = get_nickname_from_actor(search_str)
            search_domain, search_port = \
                get_domain_from_actor(search_str)
            search_follower = \
                is_follower_of_person(base_dir, nickname, domain,
                                      search_nickname, search_domain)
            search_following = \
                is_following_actor(base_dir, nickname, domain, search_str)
            if not remote_only and (search_follower or search_following):
                # get the actor
                if not has_users_path(search_str):
                    if not search_nickname or not search_domain:
                        self.send_response(400)
                        self.end_headers()
                        self.server.postreq_busy = False
                        return
                    search_domain_full = \
                        get_full_domain(search_domain, search_port)
                    actor = \
                        local_actor_url(http_prefix, search_nickname,
                                        search_domain_full)
                else:
                    actor = search_str

                # establish the session
                curr_proxy_type = proxy_type
                if '.onion/' in actor:
                    curr_proxy_type = 'tor'
                    curr_session = self.server.session_onion
                elif '.i2p/' in actor:
                    curr_proxy_type = 'i2p'
                    curr_session = self.server.session_i2p

                curr_session = \
                    establish_session("handle search",
                                      curr_session,
                                      curr_proxy_type,
                                      self.server)
                if not curr_session:
                    self.server.postreq_busy = False
                    return

                # get the avatar url for the actor
                avatar_url = \
                    get_avatar_image_url(curr_session,
                                         base_dir, http_prefix,
                                         actor,
                                         self.server.person_cache,
                                         None, True,
                                         self.server.signing_priv_key_pem)
                profile_path_str += \
                    '?options=' + actor + ';1;' + avatar_url

                show_person_options(self, calling_domain, profile_path_str,
                                    base_dir,
                                    domain, domain_full,
                                    getreq_start_time,
                                    cookie, debug, authorized,
                                    curr_session)
                return
            else:
                show_published_date_only = \
                    self.server.show_published_date_only
                allow_local_network_access = \
                    self.server.allow_local_network_access

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = self.server.key_shortcuts[nickname]

                signing_priv_key_pem = \
                    self.server.signing_priv_key_pem
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                peertube_instances = \
                    self.server.peertube_instances
                yt_replace_domain = \
                    self.server.yt_replace_domain
                cached_webfingers = \
                    self.server.cached_webfingers
                recent_posts_cache = \
                    self.server.recent_posts_cache
                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)

                profile_handle = remove_eol(search_str).strip()

                # establish the session
                curr_proxy_type = proxy_type
                if '.onion/' in profile_handle or \
                   profile_handle.endswith('.onion'):
                    curr_proxy_type = 'tor'
                    curr_session = self.server.session_onion
                elif ('.i2p/' in profile_handle or
                      profile_handle.endswith('.i2p')):
                    curr_proxy_type = 'i2p'
                    curr_session = self.server.session_i2p

                curr_session = \
                    establish_session("handle search",
                                      curr_session,
                                      curr_proxy_type,
                                      self.server)
                if not curr_session:
                    self.server.postreq_busy = False
                    return

                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True

                min_images_for_accounts = \
                    self.server.min_images_for_accounts
                max_shares_on_profile = \
                    self.server.max_shares_on_profile
                profile_str = \
                    html_profile_after_search(authorized,
                                              recent_posts_cache,
                                              self.server.max_recent_posts,
                                              self.server.translate,
                                              base_dir,
                                              profile_path_str,
                                              http_prefix,
                                              nickname,
                                              domain,
                                              port,
                                              profile_handle,
                                              curr_session,
                                              cached_webfingers,
                                              self.server.person_cache,
                                              self.server.debug,
                                              self.server.project_version,
                                              yt_replace_domain,
                                              twitter_replacement_domain,
                                              show_published_date_only,
                                              self.server.default_timeline,
                                              peertube_instances,
                                              allow_local_network_access,
                                              self.server.theme_name,
                                              access_keys,
                                              self.server.system_language,
                                              self.server.max_like_count,
                                              signing_priv_key_pem,
                                              self.server.cw_lists,
                                              self.server.lists_enabled,
                                              timezone,
                                              self.server.onion_domain,
                                              self.server.i2p_domain,
                                              bold_reading,
                                              self.server.dogwhistles,
                                              min_images_for_accounts,
                                              self.server.buy_sites,
                                              max_shares_on_profile,
                                              self.server.no_of_books,
                                              self.server.auto_cw_cache)
            if profile_str:
                msg = profile_str.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
            actor_str = \
                get_instance_url(calling_domain,
                                 http_prefix, domain_full,
                                 onion_domain, i2p_domain) + \
                users_path
            redirect_headers(self, actor_str + '/search',
                             cookie, calling_domain)
            self.server.postreq_busy = False
            return
        elif (search_str.startswith(':') or
              search_str.endswith(' emoji')):
            # eg. "cat emoji"
            if search_str.endswith(' emoji'):
                search_str = \
                    search_str.replace(' emoji', '')
            # emoji search
            nickname = get_nickname_from_actor(actor_str)
            emoji_str = \
                html_search_emoji(self.server.translate,
                                  base_dir, search_str,
                                  nickname, domain,
                                  self.server.theme_name,
                                  self.server.access_keys)
            if emoji_str:
                msg = emoji_str.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
        elif search_str.startswith('.'):
            # wanted items search
            shared_items_federated_domains = \
                self.server.shared_items_federated_domains
            nickname = get_nickname_from_actor(actor_str)
            wanted_items_str = \
                html_search_shared_items(self.server.translate,
                                         base_dir,
                                         search_str[1:], page_number,
                                         MAX_POSTS_IN_FEED,
                                         http_prefix,
                                         domain_full,
                                         actor_str, calling_domain,
                                         shared_items_federated_domains,
                                         'wanted', nickname, domain,
                                         self.server.theme_name,
                                         self.server.access_keys)
            if wanted_items_str:
                msg = wanted_items_str.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
        else:
            # shared items search
            shared_items_federated_domains = \
                self.server.shared_items_federated_domains
            nickname = get_nickname_from_actor(actor_str)
            shared_items_str = \
                html_search_shared_items(self.server.translate,
                                         base_dir,
                                         search_str, page_number,
                                         MAX_POSTS_IN_FEED,
                                         http_prefix,
                                         domain_full,
                                         actor_str, calling_domain,
                                         shared_items_federated_domains,
                                         'shares', nickname, domain,
                                         self.server.theme_name,
                                         self.server.access_keys)
            if shared_items_str:
                msg = shared_items_str.encode('utf-8')
                msglen = len(msg)
                login_headers(self, 'text/html',
                              msglen, calling_domain)
                write2(self, msg)
                self.server.postreq_busy = False
                return
    actor_str = \
        get_instance_url(calling_domain, http_prefix,
                         domain_full, onion_domain, i2p_domain) + \
        users_path
    redirect_headers(self, actor_str + '/' +
                     self.server.default_timeline,
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
    """Receive a vote via POST
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


def _remove_share(self, calling_domain: str, cookie: str,
                  authorized: bool, path: str,
                  base_dir: str, http_prefix: str, domain_full: str,
                  onion_domain: str, i2p_domain: str,
                  curr_session, proxy_type: str) -> None:
    """Removes a shared item
    """
    users_path = path.split('/rmshare')[0]
    origin_path_str = http_prefix + '://' + domain_full + users_path

    length = int(self.headers['Content-length'])

    try:
        remove_share_confirm_params = \
            self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST remove_share_confirm_params ' +
                  'connection was reset')
        else:
            print('EX: POST remove_share_confirm_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST remove_share_confirm_params ' +
              'rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if '&submitYes=' in remove_share_confirm_params and authorized:
        remove_share_confirm_params = \
            remove_share_confirm_params.replace('+', ' ').strip()
        remove_share_confirm_params = \
            urllib.parse.unquote_plus(remove_share_confirm_params)
        share_actor = remove_share_confirm_params.split('actor=')[1]
        if '&' in share_actor:
            share_actor = share_actor.split('&')[0]
        admin_nickname = get_config_param(base_dir, 'admin')
        admin_actor = \
            local_actor_url(http_prefix, admin_nickname, domain_full)
        actor = origin_path_str
        actor_nickname = get_nickname_from_actor(actor)
        if not actor_nickname:
            self.send_response(400)
            self.end_headers()
            self.server.postreq_busy = False
            return
        if actor == share_actor or actor == admin_actor or \
           is_moderator(base_dir, actor_nickname):
            item_id = remove_share_confirm_params.split('itemID=')[1]
            if '&' in item_id:
                item_id = item_id.split('&')[0]
            share_nickname = get_nickname_from_actor(share_actor)
            share_domain, _ = \
                get_domain_from_actor(share_actor)
            if share_nickname and share_domain:
                remove_shared_item2(base_dir,
                                    share_nickname, share_domain, item_id,
                                    'shares')
                # remove shared items from the actor attachments
                # https://codeberg.org/fediverse/fep/
                # src/branch/main/fep/0837/fep-0837.md
                actor = \
                    get_instance_url(calling_domain,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     self.server.onion_domain,
                                     self.server.i2p_domain) + \
                    '/users/' + share_nickname
                person_cache = self.server.person_cache
                actor_json = get_person_from_cache(base_dir,
                                                   actor, person_cache)
                if not actor_json:
                    actor_filename = \
                        acct_dir(base_dir, share_nickname,
                                 share_domain) + '.json'
                    if os.path.isfile(actor_filename):
                        actor_json = load_json(actor_filename, 1, 1)
                if actor_json:
                    max_shares_on_profile = \
                        self.server.max_shares_on_profile
                    if add_shares_to_actor(base_dir,
                                           share_nickname, share_domain,
                                           actor_json,
                                           max_shares_on_profile):
                        remove_person_from_cache(base_dir, actor,
                                                 person_cache)
                        store_person_in_cache(base_dir, actor,
                                              actor_json,
                                              person_cache, True)
                        actor_filename = acct_dir(base_dir, share_nickname,
                                                  share_domain) + '.json'
                        save_json(actor_json, actor_filename)
                        # send profile update to followers

                        update_actor_json = \
                            get_actor_update_json(actor_json)
                        print('Sending actor update ' +
                              'after change to attached shares 2: ' +
                              str(update_actor_json))
                        post_to_outbox(self, update_actor_json,
                                       self.server.project_version,
                                       share_nickname,
                                       curr_session,
                                       proxy_type)

    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str = 'http://' + i2p_domain + users_path
    redirect_headers(self, origin_path_str + '/tlshares',
                     cookie, calling_domain)
    self.server.postreq_busy = False


def _remove_wanted(self, calling_domain: str, cookie: str,
                   authorized: bool, path: str,
                   base_dir: str, http_prefix: str,
                   domain_full: str,
                   onion_domain: str, i2p_domain: str) -> None:
    """Removes a wanted item
    """
    users_path = path.split('/rmwanted')[0]
    origin_path_str = http_prefix + '://' + domain_full + users_path

    length = int(self.headers['Content-length'])

    try:
        remove_share_confirm_params = \
            self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST remove_share_confirm_params ' +
                  'connection was reset')
        else:
            print('EX: POST remove_share_confirm_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST remove_share_confirm_params ' +
              'rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return

    if '&submitYes=' in remove_share_confirm_params and authorized:
        remove_share_confirm_params = \
            remove_share_confirm_params.replace('+', ' ').strip()
        remove_share_confirm_params = \
            urllib.parse.unquote_plus(remove_share_confirm_params)
        share_actor = remove_share_confirm_params.split('actor=')[1]
        if '&' in share_actor:
            share_actor = share_actor.split('&')[0]
        admin_nickname = get_config_param(base_dir, 'admin')
        admin_actor = \
            local_actor_url(http_prefix, admin_nickname, domain_full)
        actor = origin_path_str
        actor_nickname = get_nickname_from_actor(actor)
        if not actor_nickname:
            self.send_response(400)
            self.end_headers()
            self.server.postreq_busy = False
            return
        if actor == share_actor or actor == admin_actor or \
           is_moderator(base_dir, actor_nickname):
            item_id = remove_share_confirm_params.split('itemID=')[1]
            if '&' in item_id:
                item_id = item_id.split('&')[0]
            share_nickname = get_nickname_from_actor(share_actor)
            share_domain, _ = \
                get_domain_from_actor(share_actor)
            if share_nickname and share_domain:
                remove_shared_item2(base_dir,
                                    share_nickname, share_domain, item_id,
                                    'wanted')

    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str = 'http://' + i2p_domain + users_path
    redirect_headers(self, origin_path_str + '/tlwanted',
                     cookie, calling_domain)
    self.server.postreq_busy = False


def _receive_remove_post(self, calling_domain: str, cookie: str,
                         path: str, base_dir: str, http_prefix: str,
                         domain: str, domain_full: str,
                         onion_domain: str, i2p_domain: str,
                         curr_session, proxy_type: str) -> None:
    """Endpoint for removing posts after confirmation
    """
    page_number = 1
    users_path = path.split('/rmpost')[0]
    origin_path_str = \
        http_prefix + '://' + \
        domain_full + users_path

    length = int(self.headers['Content-length'])

    try:
        remove_post_confirm_params = \
            self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST remove_post_confirm_params ' +
                  'connection was reset')
        else:
            print('EX: POST remove_post_confirm_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: POST remove_post_confirm_params ' +
              'rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    if '&submitYes=' in remove_post_confirm_params:
        remove_post_confirm_params = \
            urllib.parse.unquote_plus(remove_post_confirm_params)
        if 'messageId=' in remove_post_confirm_params:
            remove_message_id = \
                remove_post_confirm_params.split('messageId=')[1]
        elif 'eventid=' in remove_post_confirm_params:
            remove_message_id = \
                remove_post_confirm_params.split('eventid=')[1]
        else:
            self.send_response(400)
            self.end_headers()
            self.server.postreq_busy = False
            return
        if '&' in remove_message_id:
            remove_message_id = remove_message_id.split('&')[0]
        print('remove_message_id: ' + remove_message_id)
        if 'pageNumber=' in remove_post_confirm_params:
            page_number_str = \
                remove_post_confirm_params.split('pageNumber=')[1]
            if '&' in page_number_str:
                page_number_str = page_number_str.split('&')[0]
            if len(page_number_str) > 5:
                page_number_str = "1"
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        year_str = None
        if 'year=' in remove_post_confirm_params:
            year_str = remove_post_confirm_params.split('year=')[1]
            if '&' in year_str:
                year_str = year_str.split('&')[0]
        month_str = None
        if 'month=' in remove_post_confirm_params:
            month_str = remove_post_confirm_params.split('month=')[1]
            if '&' in month_str:
                month_str = month_str.split('&')[0]
        if '/statuses/' in remove_message_id:
            remove_post_actor = remove_message_id.split('/statuses/')[0]
        print('origin_path_str: ' + origin_path_str)
        print('remove_post_actor: ' + remove_post_actor)
        if origin_path_str in remove_post_actor:
            to_list = [
                'https://www.w3.org/ns/activitystreams#Public',
                remove_post_actor
            ]
            delete_json = {
                "@context": "https://www.w3.org/ns/activitystreams",
                'actor': remove_post_actor,
                'object': remove_message_id,
                'to': to_list,
                'cc': [remove_post_actor + '/followers'],
                'type': 'Delete'
            }
            self.post_to_nickname = \
                get_nickname_from_actor(remove_post_actor)
            if self.post_to_nickname:
                if month_str and year_str:
                    if len(month_str) <= 3 and \
                       len(year_str) <= 3 and \
                       month_str.isdigit() and \
                       year_str.isdigit():
                        year_int = int(year_str)
                        month_int = int(month_str)
                        remove_calendar_event(base_dir,
                                              self.post_to_nickname,
                                              domain, year_int,
                                              month_int,
                                              remove_message_id)
                post_to_outbox_thread(self, delete_json,
                                      curr_session, proxy_type)
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str = 'http://' + i2p_domain + users_path
    if page_number == 1:
        redirect_headers(self, origin_path_str + '/outbox', cookie,
                         calling_domain)
    else:
        page_number_str = str(page_number)
        actor_path_str = \
            origin_path_str + '/outbox?page=' + page_number_str
        redirect_headers(self, actor_path_str,
                         cookie, calling_domain)
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


def _newswire_update(self, calling_domain: str, cookie: str,
                     path: str, base_dir: str,
                     domain: str, debug: bool,
                     default_timeline: str) -> None:
    """Updates the right newswire column of the timeline
    """
    users_path = path.replace('/newswiredata', '')
    users_path = users_path.replace('/editnewswire', '')
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
    moderator = None
    if nickname:
        moderator = is_moderator(base_dir, nickname)
    if not nickname or not moderator:
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
            print('Maximum newswire data length exceeded ' + str(length))
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

    newswire_filename = base_dir + '/accounts/newswire.txt'

    if not boundary:
        if b'--LYNX' in post_bytes:
            boundary = '--LYNX'

    if boundary:
        # extract all of the text fields into a dict
        fields = \
            extract_text_fields_in_post(post_bytes, boundary, debug, None)
        if fields.get('editedNewswire'):
            newswire_str = fields['editedNewswire']
            # append a new newswire entry
            if fields.get('newNewswireFeed'):
                if newswire_str:
                    if not newswire_str.endswith('\n'):
                        newswire_str += '\n'
                newswire_str += fields['newNewswireFeed'] + '\n'
            try:
                with open(newswire_filename, 'w+',
                          encoding='utf-8') as newsfile:
                    newsfile.write(newswire_str)
            except OSError:
                print('EX: unable to write ' + newswire_filename)
        else:
            if fields.get('newNewswireFeed'):
                # the text area is empty but there is a new feed added
                newswire_str = fields['newNewswireFeed'] + '\n'
                try:
                    with open(newswire_filename, 'w+',
                              encoding='utf-8') as newsfile:
                        newsfile.write(newswire_str)
                except OSError:
                    print('EX: unable to write ' + newswire_filename)
            else:
                # text area has been cleared and there is no new feed
                if os.path.isfile(newswire_filename):
                    try:
                        os.remove(newswire_filename)
                    except OSError:
                        print('EX: _newswire_update unable to delete ' +
                              newswire_filename)

        # save filtered words list for the newswire
        filter_newswire_filename = \
            base_dir + '/accounts/' + \
            'news@' + domain + '/filters.txt'
        if fields.get('filteredWordsNewswire'):
            try:
                with open(filter_newswire_filename, 'w+',
                          encoding='utf-8') as filterfile:
                    filterfile.write(fields['filteredWordsNewswire'])
            except OSError:
                print('EX: unable to write ' + filter_newswire_filename)
        else:
            if os.path.isfile(filter_newswire_filename):
                try:
                    os.remove(filter_newswire_filename)
                except OSError:
                    print('EX: _newswire_update unable to delete ' +
                          filter_newswire_filename)

        # save dogwhistle words list
        dogwhistles_filename = base_dir + '/accounts/dogwhistles.txt'
        if fields.get('dogwhistleWords'):
            try:
                with open(dogwhistles_filename, 'w+',
                          encoding='utf-8') as fp_dogwhistles:
                    fp_dogwhistles.write(fields['dogwhistleWords'])
            except OSError:
                print('EX: unable to write ' + dogwhistles_filename)
            self.server.dogwhistles = \
                load_dogwhistles(dogwhistles_filename)
        else:
            # save an empty file
            try:
                with open(dogwhistles_filename, 'w+',
                          encoding='utf-8') as fp_dogwhistles:
                    fp_dogwhistles.write('')
            except OSError:
                print('EX: unable to write ' + dogwhistles_filename)
            self.server.dogwhistles = {}

        # save news tagging rules
        hashtag_rules_filename = \
            base_dir + '/accounts/hashtagrules.txt'
        if fields.get('hashtagRulesList'):
            try:
                with open(hashtag_rules_filename, 'w+',
                          encoding='utf-8') as rulesfile:
                    rulesfile.write(fields['hashtagRulesList'])
            except OSError:
                print('EX: unable to write ' + hashtag_rules_filename)
        else:
            if os.path.isfile(hashtag_rules_filename):
                try:
                    os.remove(hashtag_rules_filename)
                except OSError:
                    print('EX: _newswire_update unable to delete ' +
                          hashtag_rules_filename)

        newswire_tusted_filename = \
            base_dir + '/accounts/newswiretrusted.txt'
        if fields.get('trustedNewswire'):
            newswire_trusted = fields['trustedNewswire']
            if not newswire_trusted.endswith('\n'):
                newswire_trusted += '\n'
            try:
                with open(newswire_tusted_filename, 'w+',
                          encoding='utf-8') as trustfile:
                    trustfile.write(newswire_trusted)
            except OSError:
                print('EX: unable to write ' + newswire_tusted_filename)
        else:
            if os.path.isfile(newswire_tusted_filename):
                try:
                    os.remove(newswire_tusted_filename)
                except OSError:
                    print('EX: _newswire_update unable to delete ' +
                          newswire_tusted_filename)

    # redirect back to the default timeline
    redirect_headers(self, actor_str + '/' + default_timeline,
                     cookie, calling_domain)
    self.server.postreq_busy = False


def _citations_update(self, calling_domain: str, cookie: str,
                      path: str, base_dir: str,
                      domain: str, debug: bool,
                      newswire: {}) -> None:
    """Updates the citations for a blog post after hitting
    update button on the citations screen
    """
    users_path = path.replace('/citationsdata', '')
    actor_str = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        users_path
    nickname = get_nickname_from_actor(actor_str)
    if not nickname:
        self.server.postreq_busy = False
        return

    citations_filename = \
        acct_dir(base_dir, nickname, domain) + '/.citations.txt'
    # remove any existing citations file
    if os.path.isfile(citations_filename):
        try:
            os.remove(citations_filename)
        except OSError:
            print('EX: _citations_update unable to delete ' +
                  citations_filename)

    if newswire and \
       ' boundary=' in self.headers['Content-type']:
        boundary = self.headers['Content-type'].split('boundary=')[1]
        if ';' in boundary:
            boundary = boundary.split(';')[0]

        length = int(self.headers['Content-length'])

        # check that the POST isn't too large
        if length > self.server.max_post_length:
            print('Maximum citations data length exceeded ' + str(length))
            redirect_headers(self, actor_str, cookie, calling_domain)
            self.server.postreq_busy = False
            return

        try:
            # read the bytes of the http form POST
            post_bytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('EX: connection was reset while ' +
                      'reading bytes from http form ' +
                      'citation screen POST')
            else:
                print('EX: error while reading bytes ' +
                      'from http form citations screen POST')
            self.send_response(400)
            self.end_headers()
            self.server.postreq_busy = False
            return
        except ValueError as ex:
            print('EX: failed to read bytes for ' +
                  'citations screen POST, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.postreq_busy = False
            return

        # extract all of the text fields into a dict
        fields = \
            extract_text_fields_in_post(post_bytes, boundary, debug, None)
        print('citationstest: ' + str(fields))
        citations = []
        for ctr in range(0, 128):
            field_name = 'newswire' + str(ctr)
            if not fields.get(field_name):
                continue
            citations.append(fields[field_name])

        if citations:
            citations_str = ''
            for citation_date in citations:
                citations_str += citation_date + '\n'
            # save citations dates, so that they can be added when
            # reloading the newblog screen
            try:
                with open(citations_filename, 'w+',
                          encoding='utf-8') as citfile:
                    citfile.write(citations_str)
            except OSError:
                print('EX: unable to write ' + citations_filename)

    # redirect back to the default timeline
    redirect_headers(self, actor_str + '/newblog',
                     cookie, calling_domain)
    self.server.postreq_busy = False


def _news_post_edit(self, calling_domain: str, cookie: str,
                    path: str, base_dir: str,
                    domain: str, debug: bool) -> None:
    """edits a news post after receiving POST
    """
    users_path = path.replace('/newseditdata', '')
    users_path = users_path.replace('/editnewspost', '')
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
    editor_role = None
    if nickname:
        editor_role = is_editor(base_dir, nickname)
    if not nickname or not editor_role:
        if not nickname:
            print('WARN: nickname not found in ' + actor_str)
        else:
            print('WARN: nickname is not an editor' + actor_str)
        if self.server.news_instance:
            redirect_headers(self, actor_str + '/tlfeatures',
                             cookie, calling_domain)
        else:
            redirect_headers(self, actor_str + '/tlnews',
                             cookie, calling_domain)
        self.server.postreq_busy = False
        return

    if self.headers.get('Content-length'):
        length = int(self.headers['Content-length'])

        # check that the POST isn't too large
        if length > self.server.max_post_length:
            print('Maximum news data length exceeded ' + str(length))
            if self.server.news_instance:
                redirect_headers(self, actor_str + '/tlfeatures',
                                 cookie, calling_domain)
            else:
                redirect_headers(self, actor_str + '/tlnews',
                                 cookie, calling_domain)
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
        news_post_url = None
        news_post_title = None
        news_post_content = None
        if fields.get('newsPostUrl'):
            news_post_url = fields['newsPostUrl']
        if fields.get('newsPostTitle'):
            news_post_title = fields['newsPostTitle']
        if fields.get('editedNewsPost'):
            news_post_content = fields['editedNewsPost']

        if news_post_url and news_post_content and news_post_title:
            # load the post
            post_filename = \
                locate_post(base_dir, nickname, domain,
                            news_post_url)
            if post_filename:
                post_json_object = load_json(post_filename)
                # update the content and title
                post_json_object['object']['summary'] = \
                    news_post_title
                post_json_object['object']['content'] = \
                    news_post_content
                content_map = post_json_object['object']['contentMap']
                content_map[self.server.system_language] = \
                    news_post_content
                # update newswire
                pub_date = post_json_object['object']['published']
                published_date = \
                    date_from_string_format(pub_date,
                                            ["%Y-%m-%dT%H:%M:%S%z"])
                if self.server.newswire.get(str(published_date)):
                    self.server.newswire[published_date][0] = \
                        news_post_title
                    self.server.newswire[published_date][4] = \
                        first_paragraph_from_string(news_post_content)
                    # save newswire
                    newswire_state_filename = \
                        base_dir + '/accounts/.newswirestate.json'
                    try:
                        save_json(self.server.newswire,
                                  newswire_state_filename)
                    except BaseException as ex:
                        print('EX: saving newswire state, ' + str(ex))

                # remove any previous cached news posts
                news_id = \
                    remove_id_ending(post_json_object['object']['id'])
                news_id = news_id.replace('/', '#')
                clear_from_post_caches(base_dir,
                                       self.server.recent_posts_cache,
                                       news_id)

                # save the news post
                save_json(post_json_object, post_filename)

    # redirect back to the default timeline
    if self.server.news_instance:
        redirect_headers(self, actor_str + '/tlfeatures',
                         cookie, calling_domain)
    else:
        redirect_headers(self, actor_str + '/tlnews',
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
