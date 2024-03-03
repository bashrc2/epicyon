__filename__ = "daemon_post.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import time
import copy
import errno
import json
import os
import urllib.parse
from socket import error as SocketError
from utils import is_float
from utils import get_base_content_from_post
from utils import is_image_file
from utils import remove_avatar_from_cache
from utils import is_memorial_account
from utils import save_reverse_timeline
from utils import set_minimize_all_images
from utils import get_occupation_name
from utils import set_occupation_name
from utils import set_account_timezone
from utils import get_account_timezone
from utils import set_memorials
from utils import get_memorials
from utils import license_link_from_name
from utils import resembles_url
from utils import set_config_param
from utils import set_reply_interval_hours
from utils import remove_html
from utils import get_url_from_post
from utils import is_artist
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
from utils import refresh_newswire
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
from utils import valid_password
from utils import get_instance_url
from utils import acct_dir
from utils import get_nickname_from_actor
from blocking import save_block_federated_endpoints
from blocking import import_blocking_file
from blocking import add_account_blocks
from blocking import save_blocked_military
from blocking import set_broch_mode
from blocking import is_blocked_hashtag
from blocking import contains_military_domain
from blocking import add_global_block
from blocking import update_blocked_cache
from blocking import remove_global_block
from blocking import allowed_announce_add
from blocking import allowed_announce_remove
from blocking import remove_block
from blocking import add_block
from crawlers import blocked_user_agent
from session import site_is_verified
from session import get_session_for_domain
from session import establish_session
from fitnessFunctions import fitness_performance
from shares import add_share
from shares import merge_shared_item_tokens
from shares import add_shares_to_actor
from shares import remove_shared_item2
from shares import update_shared_item_federation_token
from inbox import update_edited_post
from inbox import populate_replies
from inbox import inbox_message_has_params
from inbox import inbox_permitted_message
from httpsig import getheader_signature_input
from person import deactivate_account
from person import get_actor_move_json
from person import add_actor_update_timestamp
from person import randomize_actor_images
from person import get_default_person_context
from person import get_featured_hashtags
from person import set_featured_hashtags
from person import update_memorial_flags
from person import get_actor_update_json
from person import person_snooze
from person import person_unsnooze
from auth import store_basic_credentials
from content import get_price_from_string
from content import replace_emoji_from_tags
from content import add_name_emojis_to_tags
from content import add_html_tags
from content import save_media_in_form_post
from content import extract_media_in_form_post
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
from httpheaders import clear_login_details
from httpheaders import set_headers
from daemon_utils import get_user_agent
from daemon_utils import show_person_options
from daemon_utils import post_to_outbox
from daemon_utils import update_inbox_queue
from daemon_utils import is_authorized
from posts import create_reading_post
from posts import create_question_post
from posts import create_report_post
from posts import create_followers_only_post
from posts import create_unlisted_post
from posts import create_blog_post
from posts import pin_post2
from posts import create_public_post
from posts import undo_pinned_post
from posts import get_post_expiry_keep_dms
from posts import set_post_expiry_keep_dms
from posts import set_max_profile_posts
from posts import get_max_profile_posts
from posts import set_post_expiry_days
from posts import get_post_expiry_days
from posts import is_moderator
from webapp_moderation import html_account_info
from webapp_moderation import html_moderation_info
from person import suspend_account
from person import reenable_account
from person import remove_account
from person import can_remove_post
from person import set_person_notes
from cache import store_person_in_cache
from cache import remove_person_from_cache
from cache import get_person_from_cache
from cache import clear_actor_cache
from theme import enable_grayscale
from theme import disable_grayscale
from theme import get_theme
from theme import is_news_theme_name
from theme import set_news_avatar
from theme import get_text_mode_banner
from theme import export_theme
from theme import import_theme
from theme import reset_theme_designer_settings
from theme import set_theme
from theme import set_theme_from_designer
from webapp_profile import html_profile_after_search
from webapp_search import html_hashtag_search
from petnames import set_pet_name
from followingCalendar import add_person_to_calendar
from followingCalendar import remove_person_from_calendar
from webapp_person_options import person_minimize_images
from webapp_person_options import person_undo_minimize_images
from notifyOnPost import add_notify_on_post
from notifyOnPost import remove_notify_on_post
from webapp_confirm import html_confirm_block
from webapp_confirm import html_confirm_unblock
from webapp_confirm import html_confirm_follow
from webapp_confirm import html_confirm_unfollow
from languages import set_default_post_language
from languages import set_actor_languages
from languages import get_actor_languages
from languages import get_understood_languages
from webapp_create_post import html_new_post
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
from media import replace_you_tube
from media import replace_twitter
from media import attach_media
from media import convert_image_to_low_bandwidth
from media import process_meta_data
from webapp_welcome import welcome_screen_is_complete
from skills import no_of_actor_skills
from skills import actor_has_skill
from skills import actor_skill_value
from skills import set_actor_skill_level
from pgp import set_pgp_fingerprint
from pgp import get_pgp_fingerprint
from pgp import set_pgp_pub_key
from pgp import get_pgp_pub_key
from pgp import get_email_address
from pgp import set_email_address
from xmpp import get_xmpp_address
from xmpp import set_xmpp_address
from matrix import get_matrix_address
from matrix import set_matrix_address
from ssb import get_ssb_address
from ssb import set_ssb_address
from blog import get_blog_address
from webapp_utils import set_blog_address
from tox import get_tox_address
from tox import set_tox_address
from briar import get_briar_address
from briar import set_briar_address
from cwtch import get_cwtch_address
from cwtch import set_cwtch_address
from enigma import get_enigma_pub_key
from enigma import set_enigma_pub_key
from donate import get_donation_url
from donate import set_donation_url
from donate import get_website
from donate import set_website
from donate import get_gemini_link
from donate import set_gemini_link
from roles import set_roles_from_list
from schedule import remove_scheduled_posts
from cwlists import get_cw_list_variable
from webfinger import webfinger_update
from webapp_column_right import html_citations
from daemon_post_login import post_login_screen

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
        _profile_edit(self, calling_domain, cookie, self.path,
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
            _person_options2(self, self.path,
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
            _receive_new_post(self, curr_post_type, self.path,
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


def _person_options2(self, path: str,
                     calling_domain: str, cookie: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domain_full: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     debug: bool, curr_session,
                     authorized: bool) -> None:
    """Receive POST from person options screen
    """
    page_number = 1
    users_path = path.split('/personoptions')[0]
    origin_path_str = http_prefix + '://' + domain_full + users_path

    chooser_nickname = get_nickname_from_actor(origin_path_str)
    if not chooser_nickname:
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str = 'http://' + onion_domain + users_path
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            origin_path_str = 'http://' + i2p_domain + users_path
        print('WARN: unable to find nickname in ' + origin_path_str)
        redirect_headers(self, origin_path_str, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    length = int(self.headers['Content-length'])

    try:
        options_confirm_params = self.rfile.read(length).decode('utf-8')
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: POST options_confirm_params ' +
                  'connection reset by peer')
        else:
            print('EX: POST options_confirm_params socket error')
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    except ValueError as ex:
        print('EX: ' +
              'POST options_confirm_params rfile.read failed, ' + str(ex))
        self.send_response(400)
        self.end_headers()
        self.server.postreq_busy = False
        return
    options_confirm_params = \
        urllib.parse.unquote_plus(options_confirm_params)

    # page number to return to
    if 'pageNumber=' in options_confirm_params:
        page_number_str = options_confirm_params.split('pageNumber=')[1]
        if '&' in page_number_str:
            page_number_str = page_number_str.split('&')[0]
        if len(page_number_str) < 5:
            if page_number_str.isdigit():
                page_number = int(page_number_str)

    # actor for the person
    options_actor = options_confirm_params.split('actor=')[1]
    if '&' in options_actor:
        options_actor = options_actor.split('&')[0]

    # actor for the movedTo
    options_actor_moved = None
    if 'movedToActor=' in options_confirm_params:
        options_actor_moved = \
            options_confirm_params.split('movedToActor=')[1]
        if '&' in options_actor_moved:
            options_actor_moved = options_actor_moved.split('&')[0]

    # url of the avatar
    options_avatar_url = options_confirm_params.split('avatarUrl=')[1]
    if '&' in options_avatar_url:
        options_avatar_url = options_avatar_url.split('&')[0]

    # link to a post, which can then be included in reports
    post_url = None
    if 'postUrl' in options_confirm_params:
        post_url = options_confirm_params.split('postUrl=')[1]
        if '&' in post_url:
            post_url = post_url.split('&')[0]

    # petname for this person
    petname = None
    if 'optionpetname' in options_confirm_params:
        petname = options_confirm_params.split('optionpetname=')[1]
        if '&' in petname:
            petname = petname.split('&')[0]
        # Limit the length of the petname
        if len(petname) > 20 or \
           ' ' in petname or '/' in petname or \
           '?' in petname or '#' in petname:
            petname = None

    # notes about this person
    person_notes = None
    if 'optionnotes' in options_confirm_params:
        person_notes = options_confirm_params.split('optionnotes=')[1]
        if '&' in person_notes:
            person_notes = person_notes.split('&')[0]
        person_notes = urllib.parse.unquote_plus(person_notes.strip())
        # Limit the length of the notes
        if len(person_notes) > 64000:
            person_notes = None

    # get the nickname
    options_nickname = get_nickname_from_actor(options_actor)
    if not options_nickname:
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str = 'http://' + onion_domain + users_path
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            origin_path_str = 'http://' + i2p_domain + users_path
        print('WARN: unable to find nickname in ' + options_actor)
        redirect_headers(self, origin_path_str, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    options_domain, options_port = get_domain_from_actor(options_actor)
    if not options_domain:
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str = 'http://' + onion_domain + users_path
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            origin_path_str = 'http://' + i2p_domain + users_path
        print('WARN: unable to find domain in ' + options_actor)
        redirect_headers(self, origin_path_str, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    options_domain_full = get_full_domain(options_domain, options_port)
    if chooser_nickname == options_nickname and \
       options_domain == domain and \
       options_port == port:
        if debug:
            print('You cannot perform an option action on yourself')

    # person options screen, view button
    # See html_person_options
    if '&submitView=' in options_confirm_params:
        if debug:
            print('Viewing ' + options_actor)

        show_published_date_only = \
            self.server.show_published_date_only
        allow_local_network_access = \
            self.server.allow_local_network_access

        access_keys = self.server.access_keys
        if self.server.key_shortcuts.get(chooser_nickname):
            access_keys = self.server.key_shortcuts[chooser_nickname]

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
        if self.server.account_timezone.get(chooser_nickname):
            timezone = \
                self.server.account_timezone.get(chooser_nickname)

        profile_handle = remove_eol(options_actor).strip()

        # establish the session
        curr_proxy_type = self.server.proxy_type
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
        if self.server.bold_reading.get(chooser_nickname):
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
                                      users_path,
                                      http_prefix,
                                      chooser_nickname,
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
        redirect_headers(self, options_actor,
                         cookie, calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, petname submit button
    # See html_person_options
    if '&submitPetname=' in options_confirm_params and petname:
        if debug:
            print('Change petname to ' + petname)
        handle = options_nickname + '@' + options_domain_full
        set_pet_name(base_dir,
                     chooser_nickname,
                     domain,
                     handle, petname)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, person notes submit button
    # See html_person_options
    if '&submitPersonNotes=' in options_confirm_params:
        if debug:
            print('Change person notes')
        handle = options_nickname + '@' + options_domain_full
        if not person_notes:
            person_notes = ''
        set_person_notes(base_dir,
                         chooser_nickname,
                         domain,
                         handle, person_notes)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, on calendar checkbox
    # See html_person_options
    if '&submitOnCalendar=' in options_confirm_params:
        on_calendar = None
        if 'onCalendar=' in options_confirm_params:
            on_calendar = options_confirm_params.split('onCalendar=')[1]
            if '&' in on_calendar:
                on_calendar = on_calendar.split('&')[0]
        if on_calendar == 'on':
            add_person_to_calendar(base_dir,
                                   chooser_nickname,
                                   domain,
                                   options_nickname,
                                   options_domain_full)
        else:
            remove_person_from_calendar(base_dir,
                                        chooser_nickname,
                                        domain,
                                        options_nickname,
                                        options_domain_full)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, minimize images checkbox
    # See html_person_options
    if '&submitMinimizeImages=' in options_confirm_params:
        minimize_images = None
        if 'minimizeImages=' in options_confirm_params:
            minimize_images = \
                options_confirm_params.split('minimizeImages=')[1]
            if '&' in minimize_images:
                minimize_images = minimize_images.split('&')[0]
        if minimize_images == 'on':
            person_minimize_images(base_dir,
                                   chooser_nickname,
                                   domain,
                                   options_nickname,
                                   options_domain_full)
        else:
            person_undo_minimize_images(base_dir,
                                        chooser_nickname,
                                        domain,
                                        options_nickname,
                                        options_domain_full)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, allow announces checkbox
    # See html_person_options
    if '&submitAllowAnnounce=' in options_confirm_params:
        allow_announce = None
        if 'allowAnnounce=' in options_confirm_params:
            allow_announce = \
                options_confirm_params.split('allowAnnounce=')[1]
            if '&' in allow_announce:
                allow_announce = allow_announce.split('&')[0]
        if allow_announce == 'on':
            allowed_announce_add(base_dir,
                                 chooser_nickname,
                                 domain,
                                 options_nickname,
                                 options_domain_full)
        else:
            allowed_announce_remove(base_dir,
                                    chooser_nickname,
                                    domain,
                                    options_nickname,
                                    options_domain_full)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, on notify checkbox
    # See html_person_options
    if '&submitNotifyOnPost=' in options_confirm_params:
        notify = None
        if 'notifyOnPost=' in options_confirm_params:
            notify = options_confirm_params.split('notifyOnPost=')[1]
            if '&' in notify:
                notify = notify.split('&')[0]
        if notify == 'on':
            add_notify_on_post(base_dir,
                               chooser_nickname,
                               domain,
                               options_nickname,
                               options_domain_full)
        else:
            remove_notify_on_post(base_dir,
                                  chooser_nickname,
                                  domain,
                                  options_nickname,
                                  options_domain_full)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, permission to post to newswire
    # See html_person_options
    if '&submitPostToNews=' in options_confirm_params:
        admin_nickname = get_config_param(self.server.base_dir, 'admin')
        if (chooser_nickname != options_nickname and
            (chooser_nickname == admin_nickname or
             (is_moderator(self.server.base_dir, chooser_nickname) and
              not is_moderator(self.server.base_dir, options_nickname)))):
            posts_to_news = None
            if 'postsToNews=' in options_confirm_params:
                posts_to_news = \
                    options_confirm_params.split('postsToNews=')[1]
                if '&' in posts_to_news:
                    posts_to_news = posts_to_news.split('&')[0]
            account_dir = acct_dir(self.server.base_dir,
                                   options_nickname, options_domain)
            newswire_blocked_filename = account_dir + '/.nonewswire'
            if posts_to_news == 'on':
                if os.path.isfile(newswire_blocked_filename):
                    try:
                        os.remove(newswire_blocked_filename)
                    except OSError:
                        print('EX: _person_options unable to delete ' +
                              newswire_blocked_filename)
                    refresh_newswire(self.server.base_dir)
            else:
                if os.path.isdir(account_dir):
                    nw_filename = newswire_blocked_filename
                    nw_written = False
                    try:
                        with open(nw_filename, 'w+',
                                  encoding='utf-8') as nofile:
                            nofile.write('\n')
                            nw_written = True
                    except OSError as ex:
                        print('EX: unable to write ' + nw_filename +
                              ' ' + str(ex))
                    if nw_written:
                        refresh_newswire(self.server.base_dir)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, permission to post to featured articles
    # See html_person_options
    if '&submitPostToFeatures=' in options_confirm_params:
        admin_nickname = get_config_param(self.server.base_dir, 'admin')
        if (chooser_nickname != options_nickname and
            (chooser_nickname == admin_nickname or
             (is_moderator(self.server.base_dir, chooser_nickname) and
              not is_moderator(self.server.base_dir, options_nickname)))):
            posts_to_features = None
            if 'postsToFeatures=' in options_confirm_params:
                posts_to_features = \
                    options_confirm_params.split('postsToFeatures=')[1]
                if '&' in posts_to_features:
                    posts_to_features = posts_to_features.split('&')[0]
            account_dir = acct_dir(self.server.base_dir,
                                   options_nickname, options_domain)
            features_blocked_filename = account_dir + '/.nofeatures'
            if posts_to_features == 'on':
                if os.path.isfile(features_blocked_filename):
                    try:
                        os.remove(features_blocked_filename)
                    except OSError:
                        print('EX: _person_options unable to delete ' +
                              features_blocked_filename)
                    refresh_newswire(self.server.base_dir)
            else:
                if os.path.isdir(account_dir):
                    feat_filename = features_blocked_filename
                    feat_written = False
                    try:
                        with open(feat_filename, 'w+',
                                  encoding='utf-8') as nofile:
                            nofile.write('\n')
                            feat_written = True
                    except OSError as ex:
                        print('EX: unable to write ' + feat_filename +
                              ' ' + str(ex))
                    if feat_written:
                        refresh_newswire(self.server.base_dir)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, permission to post to newswire
    # See html_person_options
    if '&submitModNewsPosts=' in options_confirm_params:
        admin_nickname = get_config_param(self.server.base_dir, 'admin')
        if (chooser_nickname != options_nickname and
            (chooser_nickname == admin_nickname or
             (is_moderator(self.server.base_dir, chooser_nickname) and
              not is_moderator(self.server.base_dir, options_nickname)))):
            mod_posts_to_news = None
            if 'modNewsPosts=' in options_confirm_params:
                mod_posts_to_news = \
                    options_confirm_params.split('modNewsPosts=')[1]
                if '&' in mod_posts_to_news:
                    mod_posts_to_news = mod_posts_to_news.split('&')[0]
            account_dir = acct_dir(self.server.base_dir,
                                   options_nickname, options_domain)
            newswire_mod_filename = account_dir + '/.newswiremoderated'
            if mod_posts_to_news != 'on':
                if os.path.isfile(newswire_mod_filename):
                    try:
                        os.remove(newswire_mod_filename)
                    except OSError:
                        print('EX: _person_options unable to delete ' +
                              newswire_mod_filename)
            else:
                if os.path.isdir(account_dir):
                    nw_filename = newswire_mod_filename
                    try:
                        with open(nw_filename, 'w+',
                                  encoding='utf-8') as modfile:
                            modfile.write('\n')
                    except OSError:
                        print('EX: unable to write ' + nw_filename)
        users_path_str = \
            users_path + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        redirect_headers(self, users_path_str, cookie,
                         calling_domain)
        self.server.postreq_busy = False
        return

    # person options screen, block button
    # See html_person_options
    if '&submitBlock=' in options_confirm_params:
        if debug:
            print('Blocking ' + options_actor)
        msg = \
            html_confirm_block(self.server.translate,
                               base_dir,
                               users_path,
                               options_actor,
                               options_avatar_url).encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        self.server.postreq_busy = False
        return

    # person options screen, unblock button
    # See html_person_options
    if '&submitUnblock=' in options_confirm_params:
        if debug:
            print('Unblocking ' + options_actor)
        msg = \
            html_confirm_unblock(self.server.translate,
                                 base_dir,
                                 users_path,
                                 options_actor,
                                 options_avatar_url).encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        self.server.postreq_busy = False
        return

    # person options screen, follow button
    # See html_person_options followStr
    if '&submitFollow=' in options_confirm_params or \
       '&submitJoin=' in options_confirm_params:
        if debug:
            print('Following ' + options_actor)
        msg = \
            html_confirm_follow(self.server.translate,
                                base_dir,
                                users_path,
                                options_actor,
                                options_avatar_url,
                                chooser_nickname,
                                domain).encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        self.server.postreq_busy = False
        return

    # person options screen, move button
    # See html_person_options followStr
    if '&submitMove=' in options_confirm_params and options_actor_moved:
        if debug:
            print('Moving ' + options_actor_moved)
        msg = \
            html_confirm_follow(self.server.translate,
                                base_dir,
                                users_path,
                                options_actor_moved,
                                options_avatar_url,
                                chooser_nickname,
                                domain).encode('utf-8')
        if msg:
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        self.server.postreq_busy = False
        return

    # person options screen, unfollow button
    # See html_person_options followStr
    if '&submitUnfollow=' in options_confirm_params or \
       '&submitLeave=' in options_confirm_params:
        print('Unfollowing ' + options_actor)
        msg = \
            html_confirm_unfollow(self.server.translate,
                                  base_dir,
                                  users_path,
                                  options_actor,
                                  options_avatar_url).encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        self.server.postreq_busy = False
        return

    # person options screen, DM button
    # See html_person_options
    if '&submitDM=' in options_confirm_params:
        if debug:
            print('Sending DM to ' + options_actor)
        report_path = path.replace('/personoptions', '') + '/newdm'

        access_keys = self.server.access_keys
        if '/users/' in path:
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]

        custom_submit_text = get_config_param(base_dir, 'customSubmitText')
        conversation_id = None
        reply_is_chat = False

        bold_reading = False
        if self.server.bold_reading.get(chooser_nickname):
            bold_reading = True

        languages_understood = \
            get_understood_languages(base_dir,
                                     http_prefix,
                                     chooser_nickname,
                                     self.server.domain_full,
                                     self.server.person_cache)

        default_post_language = self.server.system_language
        if self.server.default_post_language.get(nickname):
            default_post_language = \
                self.server.default_post_language[nickname]
        default_buy_site = ''
        msg = \
            html_new_post({}, False, self.server.translate,
                          base_dir,
                          http_prefix,
                          report_path, None,
                          [options_actor], None, None,
                          page_number, '',
                          chooser_nickname,
                          domain,
                          domain_full,
                          self.server.default_timeline,
                          self.server.newswire,
                          self.server.theme_name,
                          True, access_keys,
                          custom_submit_text,
                          conversation_id,
                          self.server.recent_posts_cache,
                          self.server.max_recent_posts,
                          curr_session,
                          self.server.cached_webfingers,
                          self.server.person_cache,
                          self.server.port,
                          None,
                          self.server.project_version,
                          self.server.yt_replace_domain,
                          self.server.twitter_replacement_domain,
                          self.server.show_published_date_only,
                          self.server.peertube_instances,
                          self.server.allow_local_network_access,
                          self.server.system_language,
                          languages_understood,
                          self.server.max_like_count,
                          self.server.signing_priv_key_pem,
                          self.server.cw_lists,
                          self.server.lists_enabled,
                          self.server.default_timeline,
                          reply_is_chat,
                          bold_reading,
                          self.server.dogwhistles,
                          self.server.min_images_for_accounts,
                          None, None, default_post_language,
                          self.server.buy_sites,
                          default_buy_site,
                          self.server.auto_cw_cache)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        self.server.postreq_busy = False
        return

    # person options screen, Info button
    # See html_person_options
    if '&submitPersonInfo=' in options_confirm_params:
        if is_moderator(self.server.base_dir, chooser_nickname):
            if debug:
                print('Showing info for ' + options_actor)
            signing_priv_key_pem = self.server.signing_priv_key_pem
            msg = \
                html_account_info(self.server.translate,
                                  base_dir,
                                  http_prefix,
                                  chooser_nickname,
                                  domain,
                                  options_actor,
                                  self.server.debug,
                                  self.server.system_language,
                                  signing_priv_key_pem,
                                  None,
                                  self.server.block_federated)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
            self.server.postreq_busy = False
            return
        http_404(self, 11)
        return

    # person options screen, snooze button
    # See html_person_options
    if '&submitSnooze=' in options_confirm_params:
        users_path = path.split('/personoptions')[0]
        this_actor = http_prefix + '://' + domain_full + users_path
        if debug:
            print('Snoozing ' + options_actor + ' ' + this_actor)
        if '/users/' in this_actor:
            nickname = this_actor.split('/users/')[1]
            person_snooze(base_dir, nickname,
                          domain, options_actor)
            if calling_domain.endswith('.onion') and onion_domain:
                this_actor = 'http://' + onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                this_actor = 'http://' + i2p_domain + users_path
            actor_path_str = \
                this_actor + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            redirect_headers(self, actor_path_str, cookie,
                             calling_domain)
            self.server.postreq_busy = False
            return

    # person options screen, unsnooze button
    # See html_person_options
    if '&submitUnsnooze=' in options_confirm_params:
        users_path = path.split('/personoptions')[0]
        this_actor = http_prefix + '://' + domain_full + users_path
        if debug:
            print('Unsnoozing ' + options_actor + ' ' + this_actor)
        if '/users/' in this_actor:
            nickname = this_actor.split('/users/')[1]
            person_unsnooze(base_dir, nickname,
                            domain, options_actor)
            if calling_domain.endswith('.onion') and onion_domain:
                this_actor = 'http://' + onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                this_actor = 'http://' + i2p_domain + users_path
            actor_path_str = \
                this_actor + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            redirect_headers(self, actor_path_str, cookie,
                             calling_domain)
            self.server.postreq_busy = False
            return

    # person options screen, report button
    # See html_person_options
    if '&submitReport=' in options_confirm_params:
        if debug:
            print('Reporting ' + options_actor)
        report_path = \
            path.replace('/personoptions', '') + '/newreport'

        access_keys = self.server.access_keys
        if '/users/' in path:
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]

        custom_submit_text = get_config_param(base_dir, 'customSubmitText')
        conversation_id = None
        reply_is_chat = False

        bold_reading = False
        if self.server.bold_reading.get(chooser_nickname):
            bold_reading = True

        languages_understood = \
            get_understood_languages(base_dir,
                                     http_prefix,
                                     chooser_nickname,
                                     self.server.domain_full,
                                     self.server.person_cache)

        default_post_language = self.server.system_language
        if self.server.default_post_language.get(nickname):
            default_post_language = \
                self.server.default_post_language[nickname]
        default_buy_site = ''
        msg = \
            html_new_post({}, False, self.server.translate,
                          base_dir,
                          http_prefix,
                          report_path, None, [],
                          None, post_url, page_number, '',
                          chooser_nickname,
                          domain,
                          domain_full,
                          self.server.default_timeline,
                          self.server.newswire,
                          self.server.theme_name,
                          True, access_keys,
                          custom_submit_text,
                          conversation_id,
                          self.server.recent_posts_cache,
                          self.server.max_recent_posts,
                          curr_session,
                          self.server.cached_webfingers,
                          self.server.person_cache,
                          self.server.port,
                          None,
                          self.server.project_version,
                          self.server.yt_replace_domain,
                          self.server.twitter_replacement_domain,
                          self.server.show_published_date_only,
                          self.server.peertube_instances,
                          self.server.allow_local_network_access,
                          self.server.system_language,
                          languages_understood,
                          self.server.max_like_count,
                          self.server.signing_priv_key_pem,
                          self.server.cw_lists,
                          self.server.lists_enabled,
                          self.server.default_timeline,
                          reply_is_chat,
                          bold_reading,
                          self.server.dogwhistles,
                          self.server.min_images_for_accounts,
                          None, None, default_post_language,
                          self.server.buy_sites,
                          default_buy_site,
                          self.server.auto_cw_cache)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        self.server.postreq_busy = False
        return

    # redirect back from person options screen
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str = 'http://' + onion_domain + users_path
    elif calling_domain.endswith('.i2p') and i2p_domain:
        origin_path_str = 'http://' + i2p_domain + users_path
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


def _profile_edit(self, calling_domain: str, cookie: str,
                  path: str, base_dir: str, http_prefix: str,
                  domain: str, domain_full: str,
                  onion_domain: str, i2p_domain: str,
                  debug: bool, allow_local_network_access: bool,
                  system_language: str,
                  content_license_url: str,
                  curr_session, proxy_type: str) -> None:
    """Updates your user profile after editing via the Edit button
    on the profile screen
    """
    users_path = path.replace('/profiledata', '')
    users_path = users_path.replace('/editprofile', '')
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
    if not nickname:
        print('WARN: nickname not found in ' + actor_str)
        redirect_headers(self, actor_str, cookie, calling_domain)
        self.server.postreq_busy = False
        return

    if self.headers.get('Content-length'):
        length = int(self.headers['Content-length'])

        # check that the POST isn't too large
        if length > self.server.max_post_length:
            print('Maximum profile data length exceeded ' +
                  str(length))
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

    admin_nickname = get_config_param(self.server.base_dir, 'admin')

    if not boundary:
        if b'--LYNX' in post_bytes:
            boundary = '--LYNX'

    if debug:
        print('post_bytes: ' + str(post_bytes))

    if boundary:
        # get the various avatar, banner and background images
        actor_changed = True
        send_move_activity = False
        profile_media_types = (
            'avatar', 'image',
            'banner', 'search_banner',
            'instanceLogo',
            'left_col_image', 'right_col_image',
            'importFollows',
            'importTheme'
        )
        profile_media_types_uploaded = {}
        for m_type in profile_media_types:
            # some images can only be changed by the admin
            if m_type == 'instanceLogo':
                if nickname != admin_nickname:
                    print('WARN: only the admin can change ' +
                          'instance logo')
                    continue

            if debug:
                print('DEBUG: profile update extracting ' + m_type +
                      ' image, zip, csv or font from POST')
            media_bytes, post_bytes = \
                extract_media_in_form_post(post_bytes, boundary, m_type)
            if media_bytes:
                if debug:
                    print('DEBUG: profile update ' + m_type +
                          ' image, zip, csv or font was found. ' +
                          str(len(media_bytes)) + ' bytes')
            else:
                if debug:
                    print('DEBUG: profile update, no ' + m_type +
                          ' image, zip, csv or font was found in POST')
                continue

            # Note: a .temp extension is used here so that at no
            # time is an image with metadata publicly exposed,
            # even for a few mS
            if m_type == 'instanceLogo':
                filename_base = \
                    base_dir + '/accounts/login.temp'
            elif m_type == 'importTheme':
                if not os.path.isdir(base_dir + '/imports'):
                    os.mkdir(base_dir + '/imports')
                filename_base = \
                    base_dir + '/imports/newtheme.zip'
                if os.path.isfile(filename_base):
                    try:
                        os.remove(filename_base)
                    except OSError:
                        print('EX: _profile_edit unable to delete ' +
                              filename_base)
            elif m_type == 'importFollows':
                filename_base = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/import_following.csv'
            else:
                filename_base = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/' + m_type + '.temp'

            filename, _ = \
                save_media_in_form_post(media_bytes, debug,
                                        filename_base)
            if filename:
                print('Profile update POST ' + m_type +
                      ' media, zip, csv or font filename is ' + filename)
            else:
                print('Profile update, no ' + m_type +
                      ' media, zip, csv or font filename in POST')
                continue

            if m_type == 'importFollows':
                if os.path.isfile(filename_base):
                    print(nickname + ' imported follows csv')
                else:
                    print('WARN: failed to import follows from csv for ' +
                          nickname)
                continue

            if m_type == 'importTheme':
                if nickname == admin_nickname or \
                   is_artist(base_dir, nickname):
                    if import_theme(base_dir, filename):
                        print(nickname + ' uploaded a theme')
                else:
                    print('Only admin or artist can import a theme')
                continue

            post_image_filename = filename.replace('.temp', '')
            if debug:
                print('DEBUG: POST ' + m_type +
                      ' media removing metadata')
            # remove existing etag
            if os.path.isfile(post_image_filename + '.etag'):
                try:
                    os.remove(post_image_filename + '.etag')
                except OSError:
                    print('EX: _profile_edit unable to delete ' +
                          post_image_filename + '.etag')

            city = get_spoofed_city(self.server.city,
                                    base_dir, nickname, domain)

            if self.server.low_bandwidth:
                convert_image_to_low_bandwidth(filename)
            process_meta_data(base_dir, nickname, domain,
                              filename, post_image_filename, city,
                              content_license_url)
            if os.path.isfile(post_image_filename):
                print('profile update POST ' + m_type +
                      ' image, zip or font saved to ' +
                      post_image_filename)
                if m_type != 'instanceLogo':
                    last_part_of_image_filename = \
                        post_image_filename.split('/')[-1]
                    profile_media_types_uploaded[m_type] = \
                        last_part_of_image_filename
                    actor_changed = True
            else:
                print('ERROR: profile update POST ' + m_type +
                      ' image or font could not be saved to ' +
                      post_image_filename)

        post_bytes_str = post_bytes.decode('utf-8')
        redirect_path = ''
        check_name_and_bio = False
        on_final_welcome_screen = False
        if 'name="previewAvatar"' in post_bytes_str:
            redirect_path = '/welcome_profile'
        elif 'name="initialWelcomeScreen"' in post_bytes_str:
            redirect_path = '/welcome'
        elif 'name="finalWelcomeScreen"' in post_bytes_str:
            check_name_and_bio = True
            redirect_path = '/welcome_final'
        elif 'name="welcomeCompleteButton"' in post_bytes_str:
            redirect_path = '/' + self.server.default_timeline
            welcome_screen_is_complete(self.server.base_dir, nickname,
                                       self.server.domain)
            on_final_welcome_screen = True
        elif 'name="submitExportTheme"' in post_bytes_str:
            print('submitExportTheme')
            theme_download_path = actor_str
            if export_theme(self.server.base_dir,
                            self.server.theme_name):
                theme_download_path += \
                    '/exports/' + self.server.theme_name + '.zip'
            print('submitExportTheme path=' + theme_download_path)
            redirect_headers(self, theme_download_path,
                             cookie, calling_domain)
            self.server.postreq_busy = False
            return
        elif 'name="submitExportBlocks"' in post_bytes_str:
            print('submitExportBlocks')
            blocks_download_path = actor_str + '/exports/blocks.csv'
            print('submitExportBlocks path=' + blocks_download_path)
            redirect_headers(self, blocks_download_path,
                             cookie, calling_domain)
            self.server.postreq_busy = False
            return

        # extract all of the text fields into a dict
        fields = \
            extract_text_fields_in_post(post_bytes, boundary, debug, None)
        if debug:
            if fields:
                print('DEBUG: profile update text ' +
                      'field extracted from POST ' + str(fields))
            else:
                print('WARN: profile update, no text ' +
                      'fields could be extracted from POST')

        # load the json for the actor for this user
        actor_filename = \
            acct_dir(base_dir, nickname, domain) + '.json'
        if os.path.isfile(actor_filename):
            actor_json = load_json(actor_filename)
            if actor_json:
                if not actor_json.get('discoverable'):
                    # discoverable in profile directory
                    # which isn't implemented in Epicyon
                    actor_json['discoverable'] = True
                    actor_changed = True
                if actor_json.get('capabilityAcquisitionEndpoint'):
                    del actor_json['capabilityAcquisitionEndpoint']
                    actor_changed = True
                # update the avatar/image url file extension
                uploads = profile_media_types_uploaded.items()
                for m_type, last_part in uploads:
                    rep_str = '/' + last_part
                    if m_type == 'avatar':
                        url_str = \
                            get_url_from_post(actor_json['icon']['url'])
                        actor_url = remove_html(url_str)
                        last_part_of_url = actor_url.split('/')[-1]
                        srch_str = '/' + last_part_of_url
                        actor_url = actor_url.replace(srch_str, rep_str)
                        actor_json['icon']['url'] = actor_url
                        print('actor_url: ' + actor_url)
                        if '.' in actor_url:
                            img_ext = actor_url.split('.')[-1]
                            if img_ext == 'jpg':
                                img_ext = 'jpeg'
                            actor_json['icon']['mediaType'] = \
                                'image/' + img_ext
                    elif m_type == 'image':
                        url_str = \
                            get_url_from_post(actor_json['image']['url'])
                        im_url = \
                            remove_html(url_str)
                        last_part_of_url = im_url.split('/')[-1]
                        srch_str = '/' + last_part_of_url
                        actor_json['image']['url'] = \
                            im_url.replace(srch_str, rep_str)
                        if '.' in im_url:
                            img_ext = im_url.split('.')[-1]
                            if img_ext == 'jpg':
                                img_ext = 'jpeg'
                            actor_json['image']['mediaType'] = \
                                'image/' + img_ext

                # set skill levels
                skill_ctr = 1
                actor_skills_ctr = no_of_actor_skills(actor_json)
                while skill_ctr < 10:
                    skill_name = \
                        fields.get('skillName' + str(skill_ctr))
                    if not skill_name:
                        skill_ctr += 1
                        continue
                    if is_filtered(base_dir, nickname, domain, skill_name,
                                   system_language):
                        skill_ctr += 1
                        continue
                    skill_value = \
                        fields.get('skillValue' + str(skill_ctr))
                    if not skill_value:
                        skill_ctr += 1
                        continue
                    if not actor_has_skill(actor_json, skill_name):
                        actor_changed = True
                    else:
                        if actor_skill_value(actor_json, skill_name) != \
                           int(skill_value):
                            actor_changed = True
                    set_actor_skill_level(actor_json,
                                          skill_name, int(skill_value))
                    skills_str = self.server.translate['Skills']
                    skills_str = skills_str.lower()
                    set_hashtag_category(base_dir, skill_name,
                                         skills_str, False)
                    skill_ctr += 1
                if no_of_actor_skills(actor_json) != \
                   actor_skills_ctr:
                    actor_changed = True

                # change password
                if fields.get('password') and \
                   fields.get('passwordconfirm'):
                    fields['password'] = \
                        remove_eol(fields['password']).strip()
                    fields['passwordconfirm'] = \
                        remove_eol(fields['passwordconfirm']).strip()
                    if valid_password(fields['password']) and \
                       fields['password'] == fields['passwordconfirm']:
                        # set password
                        store_basic_credentials(base_dir, nickname,
                                                fields['password'])

                # reply interval in hours
                if fields.get('replyhours'):
                    if fields['replyhours'].isdigit():
                        set_reply_interval_hours(base_dir,
                                                 nickname, domain,
                                                 fields['replyhours'])

                # change city
                if fields.get('cityDropdown'):
                    city_filename = \
                        acct_dir(base_dir, nickname, domain) + '/city.txt'
                    try:
                        with open(city_filename, 'w+',
                                  encoding='utf-8') as fp_city:
                            fp_city.write(fields['cityDropdown'])
                    except OSError:
                        print('EX: unable to write city ' + city_filename)

                # change displayed name
                if fields.get('displayNickname'):
                    if fields['displayNickname'] != actor_json['name']:
                        display_name = \
                            remove_html(fields['displayNickname'])
                        if not is_filtered(base_dir,
                                           nickname, domain,
                                           display_name,
                                           system_language):
                            actor_json['name'] = display_name
                        else:
                            actor_json['name'] = nickname
                            if check_name_and_bio:
                                redirect_path = '/welcome_profile'
                        actor_changed = True
                else:
                    if check_name_and_bio:
                        redirect_path = '/welcome_profile'

                # change the theme from edit profile screen
                if nickname == admin_nickname or \
                   is_artist(base_dir, nickname):
                    if fields.get('themeDropdown'):
                        if self.server.theme_name != \
                           fields['themeDropdown']:
                            self.server.theme_name = \
                                fields['themeDropdown']
                            set_theme(base_dir, self.server.theme_name,
                                      domain, allow_local_network_access,
                                      system_language,
                                      self.server.dyslexic_font, True)
                            self.server.text_mode_banner = \
                                get_text_mode_banner(self.server.base_dir)
                            self.server.iconsCache = {}
                            self.server.fontsCache = {}
                            self.server.css_cache = {}
                            self.server.show_publish_as_icon = \
                                get_config_param(self.server.base_dir,
                                                 'showPublishAsIcon')
                            self.server.full_width_tl_button_header = \
                                get_config_param(self.server.base_dir,
                                                 'fullWidthTlButtonHeader')
                            self.server.icons_as_buttons = \
                                get_config_param(self.server.base_dir,
                                                 'iconsAsButtons')
                            self.server.rss_icon_at_top = \
                                get_config_param(self.server.base_dir,
                                                 'rssIconAtTop')
                            self.server.publish_button_at_top = \
                                get_config_param(self.server.base_dir,
                                                 'publishButtonAtTop')
                            set_news_avatar(base_dir,
                                            fields['themeDropdown'],
                                            http_prefix,
                                            domain, domain_full)

                if nickname == admin_nickname:
                    # change media instance status
                    if fields.get('mediaInstance'):
                        self.server.media_instance = False
                        self.server.default_timeline = 'inbox'
                        if fields['mediaInstance'] == 'on':
                            self.server.media_instance = True
                            self.server.blogs_instance = False
                            self.server.news_instance = False
                            self.server.default_timeline = 'tlmedia'
                        set_config_param(base_dir, "mediaInstance",
                                         self.server.media_instance)
                        set_config_param(base_dir, "blogsInstance",
                                         self.server.blogs_instance)
                        set_config_param(base_dir, "newsInstance",
                                         self.server.news_instance)
                    else:
                        if self.server.media_instance:
                            self.server.media_instance = False
                            self.server.default_timeline = 'inbox'
                            set_config_param(base_dir, "mediaInstance",
                                             self.server.media_instance)

                    # is this a news theme?
                    if is_news_theme_name(self.server.base_dir,
                                          self.server.theme_name):
                        fields['newsInstance'] = 'on'

                    # change news instance status
                    if fields.get('newsInstance'):
                        self.server.news_instance = False
                        self.server.default_timeline = 'inbox'
                        if fields['newsInstance'] == 'on':
                            self.server.news_instance = True
                            self.server.blogs_instance = False
                            self.server.media_instance = False
                            self.server.default_timeline = 'tlfeatures'
                        set_config_param(base_dir, "mediaInstance",
                                         self.server.media_instance)
                        set_config_param(base_dir, "blogsInstance",
                                         self.server.blogs_instance)
                        set_config_param(base_dir, "newsInstance",
                                         self.server.news_instance)
                    else:
                        if self.server.news_instance:
                            self.server.news_instance = False
                            self.server.default_timeline = 'inbox'
                            set_config_param(base_dir, "newsInstance",
                                             self.server.media_instance)

                    # change blog instance status
                    if fields.get('blogsInstance'):
                        self.server.blogs_instance = False
                        self.server.default_timeline = 'inbox'
                        if fields['blogsInstance'] == 'on':
                            self.server.blogs_instance = True
                            self.server.media_instance = False
                            self.server.news_instance = False
                            self.server.default_timeline = 'tlblogs'
                        set_config_param(base_dir, "blogsInstance",
                                         self.server.blogs_instance)
                        set_config_param(base_dir, "mediaInstance",
                                         self.server.media_instance)
                        set_config_param(base_dir, "newsInstance",
                                         self.server.news_instance)
                    else:
                        if self.server.blogs_instance:
                            self.server.blogs_instance = False
                            self.server.default_timeline = 'inbox'
                            set_config_param(base_dir, "blogsInstance",
                                             self.server.blogs_instance)

                    # change instance title
                    if fields.get('instanceTitle'):
                        curr_instance_title = \
                            get_config_param(base_dir, 'instanceTitle')
                        if fields['instanceTitle'] != curr_instance_title:
                            set_config_param(base_dir, 'instanceTitle',
                                             fields['instanceTitle'])

                    # change YouTube alternate domain
                    if fields.get('ytdomain'):
                        curr_yt_domain = self.server.yt_replace_domain
                        if fields['ytdomain'] != curr_yt_domain:
                            new_yt_domain = fields['ytdomain']
                            if '://' in new_yt_domain:
                                new_yt_domain = \
                                    new_yt_domain.split('://')[1]
                            if '/' in new_yt_domain:
                                new_yt_domain = new_yt_domain.split('/')[0]
                            if '.' in new_yt_domain:
                                set_config_param(base_dir, 'youtubedomain',
                                                 new_yt_domain)
                                self.server.yt_replace_domain = \
                                    new_yt_domain
                    else:
                        set_config_param(base_dir, 'youtubedomain', '')
                        self.server.yt_replace_domain = None

                    # change twitter alternate domain
                    if fields.get('twitterdomain'):
                        curr_twitter_domain = \
                            self.server.twitter_replacement_domain
                        if fields['twitterdomain'] != curr_twitter_domain:
                            new_twitter_domain = fields['twitterdomain']
                            if '://' in new_twitter_domain:
                                new_twitter_domain = \
                                    new_twitter_domain.split('://')[1]
                            if '/' in new_twitter_domain:
                                new_twitter_domain = \
                                    new_twitter_domain.split('/')[0]
                            if '.' in new_twitter_domain:
                                set_config_param(base_dir, 'twitterdomain',
                                                 new_twitter_domain)
                                self.server.twitter_replacement_domain = \
                                    new_twitter_domain
                    else:
                        set_config_param(base_dir, 'twitterdomain', '')
                        self.server.twitter_replacement_domain = None

                    # change custom post submit button text
                    curr_custom_submit_text = \
                        get_config_param(base_dir, 'customSubmitText')
                    if fields.get('customSubmitText'):
                        if fields['customSubmitText'] != \
                           curr_custom_submit_text:
                            custom_text = fields['customSubmitText']
                            set_config_param(base_dir, 'customSubmitText',
                                             custom_text)
                    else:
                        if curr_custom_submit_text:
                            set_config_param(base_dir, 'customSubmitText',
                                             '')

                    # change registrations open status
                    registrations_open = False
                    if self.server.registration or \
                       get_config_param(base_dir,
                                        "registration") == 'open':
                        registrations_open = True
                    if fields.get('regOpen'):
                        if fields['regOpen'] != registrations_open:
                            registrations_open = fields['regOpen']
                            set_config_param(base_dir, 'registration',
                                             'open')
                            remaining = \
                                get_config_param(base_dir,
                                                 'registrationsRemaining')
                            if not remaining:
                                set_config_param(base_dir,
                                                 'registrationsRemaining',
                                                 10)
                            self.server.registration = True
                    else:
                        if registrations_open:
                            set_config_param(base_dir, 'registration',
                                             'closed')
                            self.server.registration = False

                    # change public replies unlisted
                    pub_replies_unlisted = False
                    if self.server.public_replies_unlisted or \
                       get_config_param(base_dir,
                                        "publicRepliesUnlisted") is True:
                        pub_replies_unlisted = True
                    if fields.get('publicRepliesUnlisted'):
                        if fields['publicRepliesUnlisted'] != \
                           pub_replies_unlisted:
                            pub_replies_unlisted = \
                                fields['publicRepliesUnlisted']
                            set_config_param(base_dir,
                                             'publicRepliesUnlisted',
                                             True)
                            self.server.public_replies_unlisted = \
                                pub_replies_unlisted
                    else:
                        if pub_replies_unlisted:
                            set_config_param(base_dir,
                                             'publicRepliesUnlisted',
                                             False)
                            self.server.public_replies_unlisted = False

                    # change registrations remaining
                    reg_str = "registrationsRemaining"
                    remaining = get_config_param(base_dir, reg_str)
                    if fields.get('regRemaining'):
                        if fields['regRemaining'] != remaining:
                            remaining = int(fields['regRemaining'])
                            if remaining < 0:
                                remaining = 0
                            elif remaining > 10:
                                remaining = 10
                            set_config_param(base_dir, reg_str,
                                             remaining)

                    # libretranslate URL
                    curr_libretranslate_url = \
                        get_config_param(base_dir,
                                         'libretranslateUrl')
                    if fields.get('libretranslateUrl'):
                        if fields['libretranslateUrl'] != \
                           curr_libretranslate_url:
                            lt_url = fields['libretranslateUrl']
                            if resembles_url(lt_url):
                                set_config_param(base_dir,
                                                 'libretranslateUrl',
                                                 lt_url)
                    else:
                        if curr_libretranslate_url:
                            set_config_param(base_dir,
                                             'libretranslateUrl', '')

                    # libretranslate API Key
                    curr_libretranslate_api_key = \
                        get_config_param(base_dir,
                                         'libretranslateApiKey')
                    if fields.get('libretranslateApiKey'):
                        if fields['libretranslateApiKey'] != \
                           curr_libretranslate_api_key:
                            lt_api_key = fields['libretranslateApiKey']
                            set_config_param(base_dir,
                                             'libretranslateApiKey',
                                             lt_api_key)
                    else:
                        if curr_libretranslate_api_key:
                            set_config_param(base_dir,
                                             'libretranslateApiKey', '')

                    # change instance content license
                    if fields.get('contentLicenseUrl'):
                        if fields['contentLicenseUrl'] != \
                           self.server.content_license_url:
                            license_str = fields['contentLicenseUrl']
                            if '://' not in license_str:
                                license_str = \
                                    license_link_from_name(license_str)
                            set_config_param(base_dir,
                                             'contentLicenseUrl',
                                             license_str)
                            self.server.content_license_url = \
                                license_str
                    else:
                        license_str = \
                            'https://creativecommons.org/' + \
                            'licenses/by-nc/4.0'
                        set_config_param(base_dir,
                                         'contentLicenseUrl',
                                         license_str)
                        self.server.content_license_url = license_str

                    # change instance short description
                    curr_instance_description_short = \
                        get_config_param(base_dir,
                                         'instanceDescriptionShort')
                    if fields.get('instanceDescriptionShort'):
                        if fields['instanceDescriptionShort'] != \
                           curr_instance_description_short:
                            idesc = fields['instanceDescriptionShort']
                            set_config_param(base_dir,
                                             'instanceDescriptionShort',
                                             idesc)
                    else:
                        if curr_instance_description_short:
                            set_config_param(base_dir,
                                             'instanceDescriptionShort',
                                             '')

                    # change instance description
                    curr_instance_description = \
                        get_config_param(base_dir, 'instanceDescription')
                    if fields.get('instanceDescription'):
                        if fields['instanceDescription'] != \
                           curr_instance_description:
                            set_config_param(base_dir,
                                             'instanceDescription',
                                             fields['instanceDescription'])
                    else:
                        if curr_instance_description:
                            set_config_param(base_dir,
                                             'instanceDescription', '')

                    # change memorial accounts
                    curr_memorial = get_memorials(base_dir)
                    if fields.get('memorialAccounts'):
                        if fields['memorialAccounts'] != \
                           curr_memorial:
                            set_memorials(base_dir, self.server.domain,
                                          fields['memorialAccounts'])
                            update_memorial_flags(base_dir,
                                                  self.server.person_cache)
                    else:
                        if curr_memorial:
                            set_memorials(base_dir,
                                          self.server.domain, '')
                            update_memorial_flags(base_dir,
                                                  self.server.person_cache)

                # change email address
                current_email_address = get_email_address(actor_json)
                if fields.get('email'):
                    if fields['email'] != current_email_address:
                        set_email_address(actor_json, fields['email'])
                        actor_changed = True
                else:
                    if current_email_address:
                        set_email_address(actor_json, '')
                        actor_changed = True

                # change xmpp address
                current_xmpp_address = get_xmpp_address(actor_json)
                if fields.get('xmppAddress'):
                    if fields['xmppAddress'] != current_xmpp_address:
                        set_xmpp_address(actor_json,
                                         fields['xmppAddress'])
                        actor_changed = True
                else:
                    if current_xmpp_address:
                        set_xmpp_address(actor_json, '')
                        actor_changed = True

                # change matrix address
                current_matrix_address = get_matrix_address(actor_json)
                if fields.get('matrixAddress'):
                    if fields['matrixAddress'] != current_matrix_address:
                        set_matrix_address(actor_json,
                                           fields['matrixAddress'])
                        actor_changed = True
                else:
                    if current_matrix_address:
                        set_matrix_address(actor_json, '')
                        actor_changed = True

                # change SSB address
                current_ssb_address = get_ssb_address(actor_json)
                if fields.get('ssbAddress'):
                    if fields['ssbAddress'] != current_ssb_address:
                        set_ssb_address(actor_json,
                                        fields['ssbAddress'])
                        actor_changed = True
                else:
                    if current_ssb_address:
                        set_ssb_address(actor_json, '')
                        actor_changed = True

                # change blog address
                current_blog_address = get_blog_address(actor_json)
                if fields.get('blogAddress'):
                    if fields['blogAddress'] != current_blog_address:
                        set_blog_address(actor_json,
                                         fields['blogAddress'])
                        actor_changed = True
                    site_is_verified(curr_session,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     nickname, domain,
                                     fields['blogAddress'],
                                     True,
                                     self.server.debug)
                else:
                    if current_blog_address:
                        set_blog_address(actor_json, '')
                        actor_changed = True

                # change Languages address
                current_show_languages = get_actor_languages(actor_json)
                if fields.get('showLanguages'):
                    if fields['showLanguages'] != current_show_languages:
                        set_actor_languages(actor_json,
                                            fields['showLanguages'])
                        actor_changed = True
                else:
                    if current_show_languages:
                        set_actor_languages(actor_json, '')
                        actor_changed = True

                # change time zone
                timezone = \
                    get_account_timezone(base_dir, nickname, domain)
                if fields.get('timeZone'):
                    if fields['timeZone'] != timezone:
                        set_account_timezone(base_dir,
                                             nickname, domain,
                                             fields['timeZone'])
                        self.server.account_timezone[nickname] = \
                            fields['timeZone']
                        actor_changed = True
                else:
                    if timezone:
                        set_account_timezone(base_dir,
                                             nickname, domain, '')
                        del self.server.account_timezone[nickname]
                        actor_changed = True

                # set post expiry period in days
                post_expiry_period_days = \
                    get_post_expiry_days(base_dir, nickname, domain)
                if fields.get('postExpiryPeriod'):
                    if fields['postExpiryPeriod'] != \
                       str(post_expiry_period_days):
                        post_expiry_period_days = \
                            fields['postExpiryPeriod']
                        set_post_expiry_days(base_dir, nickname, domain,
                                             post_expiry_period_days)
                        actor_changed = True
                else:
                    if post_expiry_period_days > 0:
                        set_post_expiry_days(base_dir, nickname, domain, 0)
                        actor_changed = True

                # set maximum preview posts on profile screen
                max_profile_posts = \
                    get_max_profile_posts(base_dir, nickname, domain,
                                          20)
                if fields.get('maxRecentProfilePosts'):
                    if fields['maxRecentProfilePosts'] != \
                       str(max_profile_posts):
                        max_profile_posts = \
                            fields['maxRecentProfilePosts']
                        set_max_profile_posts(base_dir, nickname, domain,
                                              max_profile_posts)
                else:
                    set_max_profile_posts(base_dir, nickname, domain,
                                          20)

                # birthday on edit profile screen
                birth_date = ''
                if actor_json.get('vcard:bday'):
                    birth_date = actor_json['vcard:bday']
                if fields.get('birthDate'):
                    if fields['birthDate'] != birth_date:
                        new_birth_date = fields['birthDate']
                        if '-' in new_birth_date and \
                           len(new_birth_date.split('-')) == 3:
                            # set birth date
                            actor_json['vcard:bday'] = new_birth_date
                            actor_changed = True
                else:
                    # set birth date
                    if birth_date:
                        actor_json['vcard:bday'] = ''
                        actor_changed = True

                # change tox address
                current_tox_address = get_tox_address(actor_json)
                if fields.get('toxAddress'):
                    if fields['toxAddress'] != current_tox_address:
                        set_tox_address(actor_json,
                                        fields['toxAddress'])
                        actor_changed = True
                else:
                    if current_tox_address:
                        set_tox_address(actor_json, '')
                        actor_changed = True

                # change briar address
                current_briar_address = get_briar_address(actor_json)
                if fields.get('briarAddress'):
                    if fields['briarAddress'] != current_briar_address:
                        set_briar_address(actor_json,
                                          fields['briarAddress'])
                        actor_changed = True
                else:
                    if current_briar_address:
                        set_briar_address(actor_json, '')
                        actor_changed = True

                # change cwtch address
                current_cwtch_address = get_cwtch_address(actor_json)
                if fields.get('cwtchAddress'):
                    if fields['cwtchAddress'] != current_cwtch_address:
                        set_cwtch_address(actor_json,
                                          fields['cwtchAddress'])
                        actor_changed = True
                else:
                    if current_cwtch_address:
                        set_cwtch_address(actor_json, '')
                        actor_changed = True

                # change ntfy url
                if fields.get('ntfyUrl'):
                    ntfy_url_file = \
                        base_dir + '/accounts/' + \
                        nickname + '@' + domain + '/.ntfy_url'
                    try:
                        with open(ntfy_url_file, 'w+',
                                  encoding='utf-8') as fp_ntfy:
                            fp_ntfy.write(fields['ntfyUrl'])
                    except OSError:
                        print('EX: unable to save ntfy url ' +
                              ntfy_url_file)

                # change ntfy topic
                if fields.get('ntfyTopic'):
                    ntfy_topic_file = \
                        base_dir + '/accounts/' + \
                        nickname + '@' + domain + '/.ntfy_topic'
                    try:
                        with open(ntfy_topic_file, 'w+',
                                  encoding='utf-8') as fp_ntfy:
                            fp_ntfy.write(fields['ntfyTopic'])
                    except OSError:
                        print('EX: unable to save ntfy topic ' +
                              ntfy_topic_file)

                # change Enigma public key
                currentenigma_pub_key = get_enigma_pub_key(actor_json)
                if fields.get('enigmapubkey'):
                    if fields['enigmapubkey'] != currentenigma_pub_key:
                        set_enigma_pub_key(actor_json,
                                           fields['enigmapubkey'])
                        actor_changed = True
                else:
                    if currentenigma_pub_key:
                        set_enigma_pub_key(actor_json, '')
                        actor_changed = True

                # change PGP public key
                currentpgp_pub_key = get_pgp_pub_key(actor_json)
                if fields.get('pgp'):
                    if fields['pgp'] != currentpgp_pub_key:
                        set_pgp_pub_key(actor_json,
                                        fields['pgp'])
                        actor_changed = True
                else:
                    if currentpgp_pub_key:
                        set_pgp_pub_key(actor_json, '')
                        actor_changed = True

                # change PGP fingerprint
                currentpgp_fingerprint = get_pgp_fingerprint(actor_json)
                if fields.get('openpgp'):
                    if fields['openpgp'] != currentpgp_fingerprint:
                        set_pgp_fingerprint(actor_json,
                                            fields['openpgp'])
                        actor_changed = True
                else:
                    if currentpgp_fingerprint:
                        set_pgp_fingerprint(actor_json, '')
                        actor_changed = True

                # change donation link
                current_donate_url = get_donation_url(actor_json)
                if fields.get('donateUrl'):
                    if fields['donateUrl'] != current_donate_url:
                        set_donation_url(actor_json,
                                         fields['donateUrl'])
                        actor_changed = True
                else:
                    if current_donate_url:
                        set_donation_url(actor_json, '')
                        actor_changed = True

                # change website
                current_website = \
                    get_website(actor_json, self.server.translate)
                if fields.get('websiteUrl'):
                    if fields['websiteUrl'] != current_website:
                        set_website(actor_json,
                                    fields['websiteUrl'],
                                    self.server.translate)
                        actor_changed = True
                    site_is_verified(curr_session,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     nickname, domain,
                                     fields['websiteUrl'],
                                     True,
                                     self.server.debug)
                else:
                    if current_website:
                        set_website(actor_json, '', self.server.translate)
                        actor_changed = True

                # change gemini link
                current_gemini_link = \
                    get_gemini_link(actor_json)
                if fields.get('geminiLink'):
                    if fields['geminiLink'] != current_gemini_link:
                        set_gemini_link(actor_json,
                                        fields['geminiLink'])
                        actor_changed = True
                else:
                    if current_gemini_link:
                        set_gemini_link(actor_json, '')
                        actor_changed = True

                # account moved to new address
                moved_to = ''
                if actor_json.get('movedTo'):
                    moved_to = actor_json['movedTo']
                if fields.get('movedTo'):
                    if fields['movedTo'] != moved_to and \
                       resembles_url(fields['movedTo']):
                        actor_json['movedTo'] = fields['movedTo']
                        send_move_activity = True
                        actor_changed = True
                else:
                    if moved_to:
                        del actor_json['movedTo']
                        actor_changed = True

                # occupation on edit profile screen
                occupation_name = get_occupation_name(actor_json)
                if fields.get('occupationName'):
                    fields['occupationName'] = \
                        remove_html(fields['occupationName'])
                    if occupation_name != \
                       fields['occupationName']:
                        set_occupation_name(actor_json,
                                            fields['occupationName'])
                        actor_changed = True
                else:
                    if occupation_name:
                        set_occupation_name(actor_json, '')
                        actor_changed = True

                # featured hashtags on edit profile screen
                featured_hashtags = get_featured_hashtags(actor_json)
                if fields.get('featuredHashtags'):
                    fields['featuredHashtags'] = \
                        remove_html(fields['featuredHashtags'])
                    if featured_hashtags != \
                       fields['featuredHashtags']:
                        set_featured_hashtags(actor_json,
                                              fields['featuredHashtags'])
                        actor_changed = True
                else:
                    if featured_hashtags:
                        set_featured_hashtags(actor_json, '')
                        actor_changed = True

                # Other accounts (alsoKnownAs)
                also_known_as = []
                if actor_json.get('alsoKnownAs'):
                    also_known_as = actor_json['alsoKnownAs']
                if fields.get('alsoKnownAs'):
                    also_known_as_str = ''
                    also_known_as_ctr = 0
                    for alt_actor in also_known_as:
                        if also_known_as_ctr > 0:
                            also_known_as_str += ', '
                        also_known_as_str += alt_actor
                        also_known_as_ctr += 1
                    if fields['alsoKnownAs'] != also_known_as_str and \
                       '://' in fields['alsoKnownAs'] and \
                       '@' not in fields['alsoKnownAs'] and \
                       '.' in fields['alsoKnownAs']:
                        if ';' in fields['alsoKnownAs']:
                            fields['alsoKnownAs'] = \
                                fields['alsoKnownAs'].replace(';', ',')
                        new_also_known_as = \
                            fields['alsoKnownAs'].split(',')
                        also_known_as = []
                        for alt_actor in new_also_known_as:
                            alt_actor = alt_actor.strip()
                            if resembles_url(alt_actor):
                                if alt_actor not in also_known_as:
                                    also_known_as.append(alt_actor)
                        actor_json['alsoKnownAs'] = also_known_as
                        actor_changed = True
                else:
                    if also_known_as:
                        del actor_json['alsoKnownAs']
                        actor_changed = True

                # change user bio
                featured_tags = get_featured_hashtags(actor_json) + ' '
                actor_json['tag'] = []
                if fields.get('bio'):
                    if fields['bio'] != actor_json['summary']:
                        bio_str = remove_html(fields['bio'])
                        if not is_filtered(base_dir,
                                           nickname, domain, bio_str,
                                           system_language):
                            actor_tags = {}
                            actor_json['summary'] = \
                                add_html_tags(base_dir,
                                              http_prefix,
                                              nickname,
                                              domain_full,
                                              bio_str, [], actor_tags,
                                              self.server.translate)
                            if actor_tags:
                                for _, tag in actor_tags.items():
                                    if tag['name'] + ' ' in featured_tags:
                                        continue
                                    actor_json['tag'].append(tag)
                            actor_changed = True
                        else:
                            if check_name_and_bio:
                                redirect_path = '/welcome_profile'
                else:
                    if check_name_and_bio:
                        redirect_path = '/welcome_profile'
                set_featured_hashtags(actor_json, featured_tags, True)

                admin_nickname = \
                    get_config_param(base_dir, 'admin')

                if admin_nickname:
                    # whether to require jsonld signatures
                    # on all incoming posts
                    if path.startswith('/users/' +
                                       admin_nickname + '/'):
                        show_node_info_accounts = False
                        if fields.get('showNodeInfoAccounts'):
                            if fields['showNodeInfoAccounts'] == 'on':
                                show_node_info_accounts = True
                        self.server.show_node_info_accounts = \
                            show_node_info_accounts
                        set_config_param(base_dir,
                                         "showNodeInfoAccounts",
                                         show_node_info_accounts)

                        show_node_info_version = False
                        if fields.get('showNodeInfoVersion'):
                            if fields['showNodeInfoVersion'] == 'on':
                                show_node_info_version = True
                        self.server.show_node_info_version = \
                            show_node_info_version
                        set_config_param(base_dir,
                                         "showNodeInfoVersion",
                                         show_node_info_version)

                        verify_all_signatures = False
                        if fields.get('verifyallsignatures'):
                            if fields['verifyallsignatures'] == 'on':
                                verify_all_signatures = True
                        self.server.verify_all_signatures = \
                            verify_all_signatures
                        set_config_param(base_dir, "verifyAllSignatures",
                                         verify_all_signatures)

                        broch_mode = False
                        if fields.get('brochMode'):
                            if fields['brochMode'] == 'on':
                                broch_mode = True
                        curr_broch_mode = \
                            get_config_param(base_dir, "brochMode")
                        if broch_mode != curr_broch_mode:
                            set_broch_mode(self.server.base_dir,
                                           self.server.domain_full,
                                           broch_mode)
                            set_config_param(base_dir, 'brochMode',
                                             broch_mode)

                        # shared item federation domains
                        si_domain_updated = False
                        fed_domains_variable = \
                            "sharedItemsFederatedDomains"
                        fed_domains_str = \
                            get_config_param(base_dir,
                                             fed_domains_variable)
                        if not fed_domains_str:
                            fed_domains_str = ''
                        shared_items_form_str = ''
                        if fields.get('shareDomainList'):
                            shared_it_list = \
                                fed_domains_str.split(',')
                            for shared_federated_domain in shared_it_list:
                                shared_items_form_str += \
                                    shared_federated_domain.strip() + '\n'

                            share_domain_list = fields['shareDomainList']
                            if share_domain_list != \
                               shared_items_form_str:
                                shared_items_form_str2 = \
                                    share_domain_list.replace('\n', ',')
                                shared_items_field = \
                                    "sharedItemsFederatedDomains"
                                set_config_param(base_dir,
                                                 shared_items_field,
                                                 shared_items_form_str2)
                                si_domain_updated = True
                        else:
                            if fed_domains_str:
                                shared_items_field = \
                                    "sharedItemsFederatedDomains"
                                set_config_param(base_dir,
                                                 shared_items_field,
                                                 '')
                                si_domain_updated = True
                        if si_domain_updated:
                            si_domains = shared_items_form_str.split('\n')
                            si_tokens = \
                                self.server.shared_item_federation_tokens
                            self.server.shared_items_federated_domains = \
                                si_domains
                            domain_full = self.server.domain_full
                            base_dir = \
                                self.server.base_dir
                            self.server.shared_item_federation_tokens = \
                                merge_shared_item_tokens(base_dir,
                                                         domain_full,
                                                         si_domains,
                                                         si_tokens)

                    # change moderators list
                    set_roles_from_list(base_dir, domain, admin_nickname,
                                        'moderators', 'moderator', fields,
                                        path, 'moderators.txt')

                    # change site editors list
                    set_roles_from_list(base_dir, domain, admin_nickname,
                                        'editors', 'editor', fields,
                                        path, 'editors.txt')

                    # change site devops list
                    set_roles_from_list(base_dir, domain, admin_nickname,
                                        'devopslist', 'devops', fields,
                                        path, 'devops.txt')

                    # change site counselors list
                    set_roles_from_list(base_dir, domain, admin_nickname,
                                        'counselors', 'counselor', fields,
                                        path, 'counselors.txt')

                    # change site artists list
                    set_roles_from_list(base_dir, domain, admin_nickname,
                                        'artists', 'artist', fields,
                                        path, 'artists.txt')

                # remove scheduled posts
                if fields.get('removeScheduledPosts'):
                    if fields['removeScheduledPosts'] == 'on':
                        remove_scheduled_posts(base_dir,
                                               nickname, domain)

                # approve followers
                if on_final_welcome_screen:
                    # Default setting created via the welcome screen
                    actor_json['manuallyApprovesFollowers'] = True
                    actor_changed = True
                else:
                    approve_followers = False
                    if fields.get('approveFollowers'):
                        if fields['approveFollowers'] == 'on':
                            approve_followers = True
                    if approve_followers != \
                       actor_json['manuallyApprovesFollowers']:
                        actor_json['manuallyApprovesFollowers'] = \
                            approve_followers
                        actor_changed = True

                # reject spam actors
                reject_spam_actors = False
                if fields.get('rejectSpamActors'):
                    if fields['rejectSpamActors'] == 'on':
                        reject_spam_actors = True
                curr_reject_spam_actors = False
                actor_spam_filter_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.reject_spam_actors'
                if os.path.isfile(actor_spam_filter_filename):
                    curr_reject_spam_actors = True
                if reject_spam_actors != curr_reject_spam_actors:
                    if reject_spam_actors:
                        try:
                            with open(actor_spam_filter_filename, 'w+',
                                      encoding='utf-8') as fp_spam:
                                fp_spam.write('\n')
                        except OSError:
                            print('EX: unable to write reject spam actors')
                    else:
                        try:
                            os.remove(actor_spam_filter_filename)
                        except OSError:
                            print('EX: ' +
                                  'unable to remove reject spam actors')

                # keep DMs during post expiry
                expire_keep_dms = False
                if fields.get('expiryKeepDMs'):
                    if fields['expiryKeepDMs'] == 'on':
                        expire_keep_dms = True
                curr_keep_dms = \
                    get_post_expiry_keep_dms(base_dir, nickname, domain)
                if curr_keep_dms != expire_keep_dms:
                    set_post_expiry_keep_dms(base_dir, nickname, domain,
                                             expire_keep_dms)
                    actor_changed = True

                # remove a custom font
                if fields.get('removeCustomFont'):
                    if (fields['removeCustomFont'] == 'on' and
                        (is_artist(base_dir, nickname) or
                         path.startswith('/users/' +
                                         admin_nickname + '/'))):
                        font_ext = ('woff', 'woff2', 'otf', 'ttf')
                        for ext in font_ext:
                            if os.path.isfile(base_dir +
                                              '/fonts/custom.' + ext):
                                try:
                                    os.remove(base_dir +
                                              '/fonts/custom.' + ext)
                                except OSError:
                                    print('EX: _profile_edit ' +
                                          'unable to delete ' +
                                          base_dir +
                                          '/fonts/custom.' + ext)
                            if os.path.isfile(base_dir +
                                              '/fonts/custom.' + ext +
                                              '.etag'):
                                try:
                                    os.remove(base_dir +
                                              '/fonts/custom.' + ext +
                                              '.etag')
                                except OSError:
                                    print('EX: _profile_edit ' +
                                          'unable to delete ' +
                                          base_dir + '/fonts/custom.' +
                                          ext + '.etag')
                        curr_theme = get_theme(base_dir)
                        if curr_theme:
                            self.server.theme_name = curr_theme
                            allow_local_network_access = \
                                self.server.allow_local_network_access
                            set_theme(base_dir, curr_theme, domain,
                                      allow_local_network_access,
                                      system_language,
                                      self.server.dyslexic_font, False)
                            self.server.text_mode_banner = \
                                get_text_mode_banner(base_dir)
                            self.server.iconsCache = {}
                            self.server.fontsCache = {}
                            self.server.show_publish_as_icon = \
                                get_config_param(base_dir,
                                                 'showPublishAsIcon')
                            self.server.full_width_tl_button_header = \
                                get_config_param(base_dir,
                                                 'fullWidthTimeline' +
                                                 'ButtonHeader')
                            self.server.icons_as_buttons = \
                                get_config_param(base_dir,
                                                 'iconsAsButtons')
                            self.server.rss_icon_at_top = \
                                get_config_param(base_dir,
                                                 'rssIconAtTop')
                            self.server.publish_button_at_top = \
                                get_config_param(base_dir,
                                                 'publishButtonAtTop')

                # only receive DMs from accounts you follow
                follow_dms_filename = \
                    acct_dir(base_dir, nickname, domain) + '/.followDMs'
                if on_final_welcome_screen:
                    # initial default setting created via
                    # the welcome screen
                    try:
                        with open(follow_dms_filename, 'w+',
                                  encoding='utf-8') as ffile:
                            ffile.write('\n')
                    except OSError:
                        print('EX: unable to write follow DMs ' +
                              follow_dms_filename)
                    actor_changed = True
                else:
                    follow_dms_active = False
                    if fields.get('followDMs'):
                        if fields['followDMs'] == 'on':
                            follow_dms_active = True
                            try:
                                with open(follow_dms_filename, 'w+',
                                          encoding='utf-8') as ffile:
                                    ffile.write('\n')
                            except OSError:
                                print('EX: unable to write follow DMs 2 ' +
                                      follow_dms_filename)
                    if not follow_dms_active:
                        if os.path.isfile(follow_dms_filename):
                            try:
                                os.remove(follow_dms_filename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      follow_dms_filename)

                # remove Twitter retweets
                remove_twitter_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.removeTwitter'
                remove_twitter_active = False
                if fields.get('removeTwitter'):
                    if fields['removeTwitter'] == 'on':
                        remove_twitter_active = True
                        try:
                            with open(remove_twitter_filename, 'w+',
                                      encoding='utf-8') as rfile:
                                rfile.write('\n')
                        except OSError:
                            print('EX: unable to write remove twitter ' +
                                  remove_twitter_filename)
                if not remove_twitter_active:
                    if os.path.isfile(remove_twitter_filename):
                        try:
                            os.remove(remove_twitter_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  remove_twitter_filename)

                # hide Like button
                hide_like_button_file = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.hideLikeButton'
                notify_likes_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.notifyLikes'
                hide_like_button_active = False
                if fields.get('hideLikeButton'):
                    if fields['hideLikeButton'] == 'on':
                        hide_like_button_active = True
                        try:
                            with open(hide_like_button_file, 'w+',
                                      encoding='utf-8') as rfil:
                                rfil.write('\n')
                        except OSError:
                            print('EX: unable to write hide like ' +
                                  hide_like_button_file)
                        # remove notify likes selection
                        if os.path.isfile(notify_likes_filename):
                            try:
                                os.remove(notify_likes_filename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      notify_likes_filename)
                if not hide_like_button_active:
                    if os.path.isfile(hide_like_button_file):
                        try:
                            os.remove(hide_like_button_file)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  hide_like_button_file)

                # Minimize all images from edit profile screen
                minimize_all_images = False
                if fields.get('minimizeAllImages'):
                    if fields['minimizeAllImages'] == 'on':
                        minimize_all_images = True
                        min_img_acct = self.server.min_images_for_accounts
                        set_minimize_all_images(base_dir,
                                                nickname, domain,
                                                True, min_img_acct)
                        print('min_images_for_accounts: ' +
                              str(min_img_acct))
                if not minimize_all_images:
                    min_img_acct = self.server.min_images_for_accounts
                    set_minimize_all_images(base_dir,
                                            nickname, domain,
                                            False, min_img_acct)
                    print('min_images_for_accounts: ' +
                          str(min_img_acct))

                # hide Reaction button
                hide_reaction_button_file = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.hideReactionButton'
                notify_reactions_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.notifyReactions'
                hide_reaction_button_active = False
                if fields.get('hideReactionButton'):
                    if fields['hideReactionButton'] == 'on':
                        hide_reaction_button_active = True
                        try:
                            with open(hide_reaction_button_file, 'w+',
                                      encoding='utf-8') as rfile:
                                rfile.write('\n')
                        except OSError:
                            print('EX: unable to write hide reaction ' +
                                  hide_reaction_button_file)
                        # remove notify Reaction selection
                        if os.path.isfile(notify_reactions_filename):
                            try:
                                os.remove(notify_reactions_filename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      notify_reactions_filename)
                if not hide_reaction_button_active:
                    if os.path.isfile(hide_reaction_button_file):
                        try:
                            os.remove(hide_reaction_button_file)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  hide_reaction_button_file)

                # bold reading checkbox
                bold_reading_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.boldReading'
                bold_reading = False
                if fields.get('boldReading'):
                    if fields['boldReading'] == 'on':
                        bold_reading = True
                        self.server.bold_reading[nickname] = True
                        try:
                            with open(bold_reading_filename, 'w+',
                                      encoding='utf-8') as rfile:
                                rfile.write('\n')
                        except OSError:
                            print('EX: unable to write bold reading ' +
                                  bold_reading_filename)
                if not bold_reading:
                    if self.server.bold_reading.get(nickname):
                        del self.server.bold_reading[nickname]
                    if os.path.isfile(bold_reading_filename):
                        try:
                            os.remove(bold_reading_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  bold_reading_filename)

                # reverse timelines checkbox
                reverse = False
                if fields.get('reverseTimelines'):
                    if fields['reverseTimelines'] == 'on':
                        reverse = True
                        if nickname not in self.server.reverse_sequence:
                            self.server.reverse_sequence.append(nickname)
                        save_reverse_timeline(base_dir,
                                              self.server.reverse_sequence)
                if not reverse:
                    if nickname in self.server.reverse_sequence:
                        self.server.reverse_sequence.remove(nickname)
                        save_reverse_timeline(base_dir,
                                              self.server.reverse_sequence)

                # show poll/vote/question posts checkbox
                show_vote_posts = False
                if fields.get('showVotes'):
                    if fields['showVotes'] == 'on':
                        show_vote_posts = True
                account_dir = acct_dir(self.server.base_dir,
                                       nickname, self.server.domain)
                show_vote_file = account_dir + '/.noVotes'
                if os.path.isfile(show_vote_file):
                    if show_vote_posts:
                        try:
                            os.remove(show_vote_file)
                        except OSError:
                            print('EX: unable to remove noVotes file ' +
                                  show_vote_file)
                else:
                    if not show_vote_posts:
                        try:
                            with open(show_vote_file, 'w+',
                                      encoding='utf-8') as fp_votes:
                                fp_votes.write('\n')
                        except OSError:
                            print('EX: unable to write noVotes file ' +
                                  show_vote_file)

                # show replies only from followers checkbox
                show_replies_followers = False
                if fields.get('repliesFromFollowersOnly'):
                    if fields['repliesFromFollowersOnly'] == 'on':
                        show_replies_followers = True
                show_replies_followers_file = \
                    account_dir + '/.repliesFromFollowersOnly'
                if os.path.isfile(show_replies_followers_file):
                    if not show_replies_followers:
                        try:
                            os.remove(show_replies_followers_file)
                        except OSError:
                            print('EX: unable to remove ' +
                                  'repliesFromFollowersOnly file ' +
                                  show_replies_followers_file)
                else:
                    if show_replies_followers:
                        try:
                            with open(show_replies_followers_file, 'w+',
                                      encoding='utf-8') as fp_replies:
                                fp_replies.write('\n')
                        except OSError:
                            print('EX: unable to write ' +
                                  'repliesFromFollowersOnly file ' +
                                  show_replies_followers_file)

                # show replies only from mutuals checkbox
                show_replies_mutuals = False
                if fields.get('repliesFromMutualsOnly'):
                    if fields['repliesFromMutualsOnly'] == 'on':
                        show_replies_mutuals = True
                show_replies_mutuals_file = \
                    account_dir + '/.repliesFromMutualsOnly'
                if os.path.isfile(show_replies_mutuals_file):
                    if not show_replies_mutuals:
                        try:
                            os.remove(show_replies_mutuals_file)
                        except OSError:
                            print('EX: unable to remove ' +
                                  'repliesFromMutualsOnly file ' +
                                  show_replies_mutuals_file)
                else:
                    if show_replies_mutuals:
                        try:
                            with open(show_replies_mutuals_file, 'w+',
                                      encoding='utf-8') as fp_replies:
                                fp_replies.write('\n')
                        except OSError:
                            print('EX: unable to write ' +
                                  'repliesFromMutualsOnly file ' +
                                  show_replies_mutuals_file)

                # hide follows checkbox
                hide_follows_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.hideFollows'
                hide_follows = False
                if fields.get('hideFollows'):
                    if fields['hideFollows'] == 'on':
                        hide_follows = True
                        self.server.hide_follows[nickname] = True
                        actor_json['hideFollows'] = True
                        actor_changed = True
                        try:
                            with open(hide_follows_filename, 'w+',
                                      encoding='utf-8') as rfile:
                                rfile.write('\n')
                        except OSError:
                            print('EX: unable to write hideFollows ' +
                                  hide_follows_filename)
                if not hide_follows:
                    actor_json['hideFollows'] = False
                    if self.server.hide_follows.get(nickname):
                        del self.server.hide_follows[nickname]
                        actor_changed = True
                    if os.path.isfile(hide_follows_filename):
                        try:
                            os.remove(hide_follows_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  hide_follows_filename)

                # block military instances
                block_mil_instances = False
                if fields.get('blockMilitary'):
                    if fields['blockMilitary'] == 'on':
                        block_mil_instances = True
                if block_mil_instances:
                    if not self.server.block_military.get(nickname):
                        self.server.block_military[nickname] = True
                        save_blocked_military(self.server.base_dir,
                                              self.server.block_military)
                else:
                    if self.server.block_military.get(nickname):
                        del self.server.block_military[nickname]
                        save_blocked_military(self.server.base_dir,
                                              self.server.block_military)

                # notify about new Likes
                if on_final_welcome_screen:
                    # default setting from welcome screen
                    try:
                        with open(notify_likes_filename, 'w+',
                                  encoding='utf-8') as rfile:
                            rfile.write('\n')
                    except OSError:
                        print('EX: unable to write notify likes ' +
                              notify_likes_filename)
                    actor_changed = True
                else:
                    notify_likes_active = False
                    if fields.get('notifyLikes'):
                        if fields['notifyLikes'] == 'on' and \
                           not hide_like_button_active:
                            notify_likes_active = True
                            try:
                                with open(notify_likes_filename, 'w+',
                                          encoding='utf-8') as rfile:
                                    rfile.write('\n')
                            except OSError:
                                print('EX: unable to write notify likes ' +
                                      notify_likes_filename)
                    if not notify_likes_active:
                        if os.path.isfile(notify_likes_filename):
                            try:
                                os.remove(notify_likes_filename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      notify_likes_filename)

                notify_reactions_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/.notifyReactions'
                if on_final_welcome_screen:
                    # default setting from welcome screen
                    notify_react_filename = notify_reactions_filename
                    try:
                        with open(notify_react_filename, 'w+',
                                  encoding='utf-8') as rfile:
                            rfile.write('\n')
                    except OSError:
                        print('EX: unable to write notify reactions ' +
                              notify_reactions_filename)
                    actor_changed = True
                else:
                    notify_reactions_active = False
                    if fields.get('notifyReactions'):
                        if fields['notifyReactions'] == 'on' and \
                           not hide_reaction_button_active:
                            notify_reactions_active = True
                            try:
                                with open(notify_reactions_filename, 'w+',
                                          encoding='utf-8') as rfile:
                                    rfile.write('\n')
                            except OSError:
                                print('EX: unable to write ' +
                                      'notify reactions ' +
                                      notify_reactions_filename)
                    if not notify_reactions_active:
                        if os.path.isfile(notify_reactions_filename):
                            try:
                                os.remove(notify_reactions_filename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      notify_reactions_filename)

                # this account is a bot
                if fields.get('isBot'):
                    if fields['isBot'] == 'on' and \
                       actor_json.get('type'):
                        if actor_json['type'] != 'Service':
                            actor_json['type'] = 'Service'
                            actor_changed = True
                else:
                    # this account is a group
                    if fields.get('isGroup'):
                        if fields['isGroup'] == 'on' and \
                           actor_json.get('type'):
                            if actor_json['type'] != 'Group':
                                # only allow admin to create groups
                                if path.startswith('/users/' +
                                                   admin_nickname + '/'):
                                    actor_json['type'] = 'Group'
                                    actor_changed = True
                    else:
                        # this account is a person (default)
                        if actor_json.get('type'):
                            if actor_json['type'] != 'Person':
                                actor_json['type'] = 'Person'
                                actor_changed = True

                # grayscale theme
                if path.startswith('/users/' + admin_nickname + '/') or \
                   is_artist(base_dir, nickname):
                    grayscale = False
                    if fields.get('grayscale'):
                        if fields['grayscale'] == 'on':
                            grayscale = True
                    if grayscale:
                        enable_grayscale(base_dir)
                    else:
                        disable_grayscale(base_dir)

                # dyslexic font
                if path.startswith('/users/' + admin_nickname + '/') or \
                   is_artist(base_dir, nickname):
                    dyslexic_font = False
                    if fields.get('dyslexicFont'):
                        if fields['dyslexicFont'] == 'on':
                            dyslexic_font = True
                    if dyslexic_font != self.server.dyslexic_font:
                        self.server.dyslexic_font = dyslexic_font
                        set_config_param(base_dir, 'dyslexicFont',
                                         self.server.dyslexic_font)
                        set_theme(base_dir,
                                  self.server.theme_name,
                                  self.server.domain,
                                  self.server.allow_local_network_access,
                                  self.server.system_language,
                                  self.server.dyslexic_font, False)

                # low bandwidth images checkbox
                if path.startswith('/users/' + admin_nickname + '/') or \
                   is_artist(base_dir, nickname):
                    curr_low_bandwidth = \
                        get_config_param(base_dir, 'lowBandwidth')
                    low_bandwidth = False
                    if fields.get('lowBandwidth'):
                        if fields['lowBandwidth'] == 'on':
                            low_bandwidth = True
                    if curr_low_bandwidth != low_bandwidth:
                        set_config_param(base_dir, 'lowBandwidth',
                                         low_bandwidth)
                        self.server.low_bandwidth = low_bandwidth

                # save filtered words list
                filter_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/filters.txt'
                if fields.get('filteredWords'):
                    try:
                        with open(filter_filename, 'w+',
                                  encoding='utf-8') as filterfile:
                            filterfile.write(fields['filteredWords'])
                    except OSError:
                        print('EX: unable to write filter ' +
                              filter_filename)
                else:
                    if os.path.isfile(filter_filename):
                        try:
                            os.remove(filter_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete filter ' +
                                  filter_filename)

                # save filtered words within bio list
                filter_bio_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/filters_bio.txt'
                if fields.get('filteredWordsBio'):
                    try:
                        with open(filter_bio_filename, 'w+',
                                  encoding='utf-8') as filterfile:
                            filterfile.write(fields['filteredWordsBio'])
                    except OSError:
                        print('EX: unable to write bio filter ' +
                              filter_bio_filename)
                else:
                    if os.path.isfile(filter_bio_filename):
                        try:
                            os.remove(filter_bio_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete bio filter ' +
                                  filter_bio_filename)

                # word replacements
                switch_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/replacewords.txt'
                if fields.get('switchwords'):
                    try:
                        with open(switch_filename, 'w+',
                                  encoding='utf-8') as switchfile:
                            switchfile.write(fields['switchwords'])
                    except OSError:
                        print('EX: unable to write switches ' +
                              switch_filename)
                else:
                    if os.path.isfile(switch_filename):
                        try:
                            os.remove(switch_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  switch_filename)

                # autogenerated tags
                auto_tags_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/autotags.txt'
                if fields.get('autoTags'):
                    try:
                        with open(auto_tags_filename, 'w+',
                                  encoding='utf-8') as autofile:
                            autofile.write(fields['autoTags'])
                    except OSError:
                        print('EX: unable to write auto tags ' +
                              auto_tags_filename)
                else:
                    if os.path.isfile(auto_tags_filename):
                        try:
                            os.remove(auto_tags_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  auto_tags_filename)

                # autogenerated content warnings
                auto_cw_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/autocw.txt'
                if fields.get('autoCW'):
                    try:
                        with open(auto_cw_filename, 'w+',
                                  encoding='utf-8') as auto_cw_file:
                            auto_cw_file.write(fields['autoCW'])
                    except OSError:
                        print('EX: unable to write auto CW ' +
                              auto_cw_filename)
                    self.server.auto_cw_cache[nickname] = \
                        fields['autoCW'].split('\n')
                else:
                    if os.path.isfile(auto_cw_filename):
                        try:
                            os.remove(auto_cw_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  auto_cw_filename)
                        self.server.auto_cw_cache[nickname] = []

                # save blocked accounts list
                if fields.get('blocked'):
                    add_account_blocks(base_dir,
                                       nickname, domain,
                                       fields['blocked'])
                else:
                    add_account_blocks(base_dir,
                                       nickname, domain, '')
                # import blocks from csv file
                if fields.get('importBlocks'):
                    blocks_str = fields['importBlocks']
                    while blocks_str.startswith('\n'):
                        blocks_str = blocks_str[1:]
                    blocks_lines = blocks_str.split('\n')
                    if import_blocking_file(base_dir, nickname, domain,
                                            blocks_lines):
                        print('blocks imported for ' + nickname)
                    else:
                        print('blocks not imported for ' + nickname)

                if fields.get('importFollows'):
                    filename_base = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/import_following.csv'
                    follows_str = fields['importFollows']
                    while follows_str.startswith('\n'):
                        follows_str = follows_str[1:]
                    try:
                        with open(filename_base, 'w+',
                                  encoding='utf-8') as fp_foll:
                            fp_foll.write(follows_str)
                    except OSError:
                        print('EX: unable to write imported follows ' +
                              filename_base)

                if fields.get('importTheme'):
                    if not os.path.isdir(base_dir + '/imports'):
                        os.mkdir(base_dir + '/imports')
                    filename_base = \
                        base_dir + '/imports/newtheme.zip'
                    if os.path.isfile(filename_base):
                        try:
                            os.remove(filename_base)
                        except OSError:
                            print('EX: _profile_edit unable to delete ' +
                                  filename_base)
                    if nickname == admin_nickname or \
                       is_artist(base_dir, nickname):
                        if import_theme(base_dir, filename_base):
                            print(nickname + ' uploaded a theme')
                    else:
                        print('Only admin or artist can import a theme')

                # Save DM allowed instances list.
                # The allow list for incoming DMs,
                # if the .followDMs flag file exists
                dm_allowed_instances_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/dmAllowedInstances.txt'
                if fields.get('dmAllowedInstances'):
                    try:
                        with open(dm_allowed_instances_filename, 'w+',
                                  encoding='utf-8') as afile:
                            afile.write(fields['dmAllowedInstances'])
                    except OSError:
                        print('EX: unable to write allowed DM instances ' +
                              dm_allowed_instances_filename)
                else:
                    if os.path.isfile(dm_allowed_instances_filename):
                        try:
                            os.remove(dm_allowed_instances_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  dm_allowed_instances_filename)

                # save allowed instances list
                # This is the account level allow list
                allowed_instances_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/allowedinstances.txt'
                if fields.get('allowedInstances'):
                    inst_filename = allowed_instances_filename
                    try:
                        with open(inst_filename, 'w+',
                                  encoding='utf-8') as afile:
                            afile.write(fields['allowedInstances'])
                    except OSError:
                        print('EX: unable to write allowed instances ' +
                              allowed_instances_filename)
                else:
                    if os.path.isfile(allowed_instances_filename):
                        try:
                            os.remove(allowed_instances_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  allowed_instances_filename)

                if is_moderator(self.server.base_dir, nickname):
                    # set selected content warning lists
                    new_lists_enabled = ''
                    for name, _ in self.server.cw_lists.items():
                        list_var_name = get_cw_list_variable(name)
                        if fields.get(list_var_name):
                            if fields[list_var_name] == 'on':
                                if new_lists_enabled:
                                    new_lists_enabled += ', ' + name
                                else:
                                    new_lists_enabled += name
                    if new_lists_enabled != self.server.lists_enabled:
                        self.server.lists_enabled = new_lists_enabled
                        set_config_param(self.server.base_dir,
                                         "listsEnabled",
                                         new_lists_enabled)

                    # save blocked user agents
                    user_agents_blocked = []
                    if fields.get('userAgentsBlockedStr'):
                        user_agents_blocked_str = \
                            fields['userAgentsBlockedStr']
                        user_agents_blocked_list = \
                            user_agents_blocked_str.split('\n')
                        for uagent in user_agents_blocked_list:
                            if uagent in user_agents_blocked:
                                continue
                            user_agents_blocked.append(uagent.strip())
                    if str(self.server.user_agents_blocked) != \
                       str(user_agents_blocked):
                        self.server.user_agents_blocked = \
                            user_agents_blocked
                        user_agents_blocked_str = ''
                        for uagent in user_agents_blocked:
                            if user_agents_blocked_str:
                                user_agents_blocked_str += ','
                            user_agents_blocked_str += uagent
                        set_config_param(base_dir, 'userAgentsBlocked',
                                         user_agents_blocked_str)

                    # save allowed web crawlers
                    crawlers_allowed = []
                    if fields.get('crawlersAllowedStr'):
                        crawlers_allowed_str = \
                            fields['crawlersAllowedStr']
                        crawlers_allowed_list = \
                            crawlers_allowed_str.split('\n')
                        for uagent in crawlers_allowed_list:
                            if uagent in crawlers_allowed:
                                continue
                            crawlers_allowed.append(uagent.strip())
                    if str(self.server.crawlers_allowed) != \
                       str(crawlers_allowed):
                        self.server.crawlers_allowed = \
                            crawlers_allowed
                        crawlers_allowed_str = ''
                        for uagent in crawlers_allowed:
                            if crawlers_allowed_str:
                                crawlers_allowed_str += ','
                            crawlers_allowed_str += uagent
                        set_config_param(base_dir, 'crawlersAllowed',
                                         crawlers_allowed_str)

                    # save allowed buy domains
                    buy_sites = {}
                    if fields.get('buySitesStr'):
                        buy_sites_str = \
                            fields['buySitesStr']
                        buy_sites_list = \
                            buy_sites_str.split('\n')
                        for site_url in buy_sites_list:
                            if ' ' in site_url:
                                site_url = site_url.split(' ')[-1]
                                buy_icon_text = \
                                    site_url.replace(site_url, '').strip()
                                if not buy_icon_text:
                                    buy_icon_text = site_url
                            else:
                                buy_icon_text = site_url
                            if buy_sites.get(buy_icon_text):
                                continue
                            if '<' in site_url:
                                continue
                            if not site_url.strip():
                                continue
                            buy_sites[buy_icon_text] = site_url.strip()
                    if str(self.server.buy_sites) != \
                       str(buy_sites):
                        self.server.buy_sites = buy_sites
                        buy_sites_filename = \
                            base_dir + '/accounts/buy_sites.json'
                        if buy_sites:
                            save_json(buy_sites, buy_sites_filename)
                        else:
                            if os.path.isfile(buy_sites_filename):
                                try:
                                    os.remove(buy_sites_filename)
                                except OSError:
                                    print('EX: unable to delete ' +
                                          buy_sites_filename)

                    # save blocking API endpoints
                    block_ep_new = []
                    if fields.get('blockFederated'):
                        block_federated_str = \
                            fields['blockFederated']
                        block_ep_new = \
                            block_federated_str.split('\n')
                    if str(self.server.block_federated_endpoints) != \
                       str(block_ep_new):
                        base_dir = self.server.base_dir
                        self.server.block_federated_endpoints = \
                            save_block_federated_endpoints(base_dir,
                                                           block_ep_new)
                        if not block_ep_new:
                            self.server.block_federated = []

                    # save peertube instances list
                    peertube_instances_file = \
                        base_dir + '/accounts/peertube.txt'
                    if fields.get('ptInstances'):
                        self.server.peertube_instances.clear()
                        try:
                            with open(peertube_instances_file, 'w+',
                                      encoding='utf-8') as afile:
                                afile.write(fields['ptInstances'])
                        except OSError:
                            print('EX: unable to write peertube ' +
                                  peertube_instances_file)
                        pt_instances_list = \
                            fields['ptInstances'].split('\n')
                        if pt_instances_list:
                            for url in pt_instances_list:
                                url = url.strip()
                                if not url:
                                    continue
                                if url in self.server.peertube_instances:
                                    continue
                                self.server.peertube_instances.append(url)
                    else:
                        if os.path.isfile(peertube_instances_file):
                            try:
                                os.remove(peertube_instances_file)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      peertube_instances_file)
                        self.server.peertube_instances.clear()

                # save git project names list
                git_projects_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/gitprojects.txt'
                if fields.get('gitProjects'):
                    try:
                        with open(git_projects_filename, 'w+',
                                  encoding='utf-8') as afile:
                            afile.write(fields['gitProjects'].lower())
                    except OSError:
                        print('EX: unable to write git ' +
                              git_projects_filename)
                else:
                    if os.path.isfile(git_projects_filename):
                        try:
                            os.remove(git_projects_filename)
                        except OSError:
                            print('EX: _profile_edit ' +
                                  'unable to delete ' +
                                  git_projects_filename)

                # change memorial status
                if is_memorial_account(base_dir, nickname):
                    if not actor_json.get('memorial'):
                        actor_json['memorial'] = True
                        actor_changed = True
                elif actor_json.get('memorial'):
                    actor_json['memorial'] = False
                    actor_changed = True

                # save actor json file within accounts
                if actor_changed:
                    add_name_emojis_to_tags(base_dir, http_prefix,
                                            domain, self.server.port,
                                            actor_json)
                    # update the context for the actor
                    actor_json['@context'] = [
                        'https://www.w3.org/ns/activitystreams',
                        'https://w3id.org/security/v1',
                        get_default_person_context()
                    ]
                    if actor_json.get('nomadicLocations'):
                        del actor_json['nomadicLocations']
                    if not actor_json.get('featured'):
                        actor_json['featured'] = \
                            actor_json['id'] + '/collections/featured'
                    if not actor_json.get('featuredTags'):
                        actor_json['featuredTags'] = \
                            actor_json['id'] + '/collections/tags'
                    randomize_actor_images(actor_json)
                    add_actor_update_timestamp(actor_json)
                    # save the actor
                    save_json(actor_json, actor_filename)
                    webfinger_update(base_dir,
                                     nickname, domain,
                                     onion_domain, i2p_domain,
                                     self.server.cached_webfingers)
                    # also copy to the actors cache and
                    # person_cache in memory
                    store_person_in_cache(base_dir,
                                          actor_json['id'], actor_json,
                                          self.server.person_cache,
                                          True)
                    # clear any cached images for this actor
                    id_str = actor_json['id'].replace('/', '-')
                    remove_avatar_from_cache(base_dir, id_str)
                    # save the actor to the cache
                    actor_cache_filename = \
                        base_dir + '/cache/actors/' + \
                        actor_json['id'].replace('/', '#') + '.json'
                    save_json(actor_json, actor_cache_filename)
                    # send profile update to followers
                    update_actor_json = get_actor_update_json(actor_json)
                    print('Sending actor update: ' +
                          str(update_actor_json))
                    post_to_outbox(self, update_actor_json,
                                   self.server.project_version,
                                   nickname,
                                   curr_session, proxy_type)
                    # send move activity if necessary
                    if send_move_activity:
                        move_actor_json = get_actor_move_json(actor_json)
                        print('Sending Move activity: ' +
                              str(move_actor_json))
                        post_to_outbox(self, move_actor_json,
                                       self.server.project_version,
                                       nickname,
                                       curr_session, proxy_type)

                # deactivate the account
                if fields.get('deactivateThisAccount'):
                    if fields['deactivateThisAccount'] == 'on':
                        deactivate_account(base_dir,
                                           nickname, domain)
                        clear_login_details(self, nickname,
                                            calling_domain)
                        self.server.postreq_busy = False
                        return

    # redirect back to the profile screen
    redirect_headers(self, actor_str + redirect_path,
                     cookie, calling_domain)
    self.server.postreq_busy = False


def _receive_new_post(self, post_type: str, path: str,
                      calling_domain: str, cookie: str,
                      content_license_url: str,
                      curr_session, proxy_type: str) -> int:
    """A new post has been created
    This creates a thread to send the new post
    """
    page_number = 1
    original_path = path

    if '/users/' not in path:
        print('Not receiving new post for ' + path +
              ' because /users/ not in path')
        return None

    if '?' + post_type + '?' not in path:
        print('Not receiving new post for ' + path +
              ' because ?' + post_type + '? not in path')
        return None

    print('New post begins: ' + post_type + ' ' + path)

    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
            path = path.split('?page=')[0]

    # get the username who posted
    new_post_thread_name = None
    if '/users/' in path:
        new_post_thread_name = path.split('/users/')[1]
        if '/' in new_post_thread_name:
            new_post_thread_name = new_post_thread_name.split('/')[0]
    if not new_post_thread_name:
        new_post_thread_name = '*'

    if self.server.new_post_thread.get(new_post_thread_name):
        print('Waiting for previous new post thread to end')
        wait_ctr = 0
        np_thread = self.server.new_post_thread[new_post_thread_name]
        while np_thread.is_alive() and wait_ctr < 8:
            time.sleep(1)
            wait_ctr += 1
        if wait_ctr >= 8:
            print('Killing previous new post thread for ' +
                  new_post_thread_name)
            np_thread.kill()

    # make a copy of self.headers
    headers = copy.deepcopy(self.headers)
    headers_without_cookie = copy.deepcopy(headers)
    if 'cookie' in headers_without_cookie:
        del headers_without_cookie['cookie']
    if 'Cookie' in headers_without_cookie:
        del headers_without_cookie['Cookie']
    print('New post headers: ' + str(headers_without_cookie))

    length = int(headers['Content-Length'])
    if length > self.server.max_post_length:
        print('POST size too large')
        return None

    if not headers.get('Content-Type'):
        if headers.get('Content-type'):
            headers['Content-Type'] = headers['Content-type']
        elif headers.get('content-type'):
            headers['Content-Type'] = headers['content-type']
    if headers.get('Content-Type'):
        if ' boundary=' in headers['Content-Type']:
            boundary = headers['Content-Type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            try:
                post_bytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: POST post_bytes ' +
                          'connection reset by peer')
                else:
                    print('WARN: POST post_bytes socket error')
                return None
            except ValueError as ex:
                print('EX: POST post_bytes rfile.read failed, ' +
                      str(ex))
                return None

            # second length check from the bytes received
            # since Content-Length could be untruthful
            length = len(post_bytes)
            if length > self.server.max_post_length:
                print('POST size too large')
                return None

            # Note sending new posts needs to be synchronous,
            # otherwise any attachments can get mangled if
            # other events happen during their decoding
            print('Creating new post from: ' + new_post_thread_name)
            _receive_new_post_process(self, post_type,
                                      original_path,
                                      headers, length,
                                      post_bytes, boundary,
                                      calling_domain, cookie,
                                      content_license_url,
                                      curr_session, proxy_type)
    return page_number


def _receive_new_post_process(self, post_type: str, path: str, headers: {},
                              length: int, post_bytes, boundary: str,
                              calling_domain: str, cookie: str,
                              content_license_url: str,
                              curr_session, proxy_type: str) -> int:
    # Note: this needs to happen synchronously
    # 0=this is not a new post
    # 1=new post success
    # -1=new post failed
    # 2=new post canceled
    if self.server.debug:
        print('DEBUG: receiving POST')

    if ' boundary=' in headers['Content-Type']:
        if self.server.debug:
            print('DEBUG: receiving POST headers ' +
                  headers['Content-Type'] +
                  ' path ' + path)
        nickname = None
        nickname_str = path.split('/users/')[1]
        if '?' in nickname_str:
            nickname_str = nickname_str.split('?')[0]
        if '/' in nickname_str:
            nickname = nickname_str.split('/')[0]
        else:
            nickname = nickname_str
        if self.server.debug:
            print('DEBUG: POST nickname ' + str(nickname))
        if not nickname:
            print('WARN: no nickname found when receiving ' + post_type +
                  ' path ' + path)
            return -1

        # get the message id of an edited post
        edited_postid = None
        print('DEBUG: edited_postid path ' + path)
        if '?editid=' in path:
            edited_postid = path.split('?editid=')[1]
            if '?' in edited_postid:
                edited_postid = edited_postid.split('?')[0]
            print('DEBUG: edited_postid ' + edited_postid)

        # get the published date of an edited post
        edited_published = None
        if '?editpub=' in path:
            edited_published = path.split('?editpub=')[1]
            if '?' in edited_published:
                edited_published = \
                    edited_published.split('?')[0]
            print('DEBUG: edited_published ' +
                  edited_published)

        length = int(headers['Content-Length'])
        if length > self.server.max_post_length:
            print('POST size too large')
            return -1

        boundary = headers['Content-Type'].split('boundary=')[1]
        if ';' in boundary:
            boundary = boundary.split(';')[0]

        # Note: we don't use cgi here because it's due to be deprecated
        # in Python 3.8/3.10
        # Instead we use the multipart mime parser from the email module
        if self.server.debug:
            print('DEBUG: extracting media from POST')
        media_bytes, post_bytes = \
            extract_media_in_form_post(post_bytes, boundary, 'attachpic')
        if self.server.debug:
            if media_bytes:
                print('DEBUG: media was found. ' +
                      str(len(media_bytes)) + ' bytes')
            else:
                print('DEBUG: no media was found in POST')

        # Note: a .temp extension is used here so that at no time is
        # an image with metadata publicly exposed, even for a few mS
        filename_base = \
            acct_dir(self.server.base_dir,
                     nickname, self.server.domain) + '/upload.temp'

        filename, attachment_media_type = \
            save_media_in_form_post(media_bytes, self.server.debug,
                                    filename_base)
        if self.server.debug:
            if filename:
                print('DEBUG: POST media filename is ' + filename)
            else:
                print('DEBUG: no media filename in POST')

        if filename:
            if is_image_file(filename):
                post_image_filename = filename.replace('.temp', '')
                print('Removing metadata from ' + post_image_filename)
                city = get_spoofed_city(self.server.city,
                                        self.server.base_dir,
                                        nickname, self.server.domain)
                if self.server.low_bandwidth:
                    convert_image_to_low_bandwidth(filename)
                process_meta_data(self.server.base_dir,
                                  nickname, self.server.domain,
                                  filename, post_image_filename, city,
                                  content_license_url)
                if os.path.isfile(post_image_filename):
                    print('POST media saved to ' + post_image_filename)
                else:
                    print('ERROR: POST media could not be saved to ' +
                          post_image_filename)
            else:
                if os.path.isfile(filename):
                    new_filename = filename.replace('.temp', '')
                    os.rename(filename, new_filename)
                    filename = new_filename

        fields = \
            extract_text_fields_in_post(post_bytes, boundary,
                                        self.server.debug, None)
        if self.server.debug:
            if fields:
                print('DEBUG: text field extracted from POST ' +
                      str(fields))
            else:
                print('WARN: no text fields could be extracted from POST')

        # was the citations button pressed on the newblog screen?
        citations_button_press = False
        if post_type == 'newblog' and fields.get('submitCitations'):
            if fields['submitCitations'] == \
               self.server.translate['Citations']:
                citations_button_press = True

        if not citations_button_press:
            # process the received text fields from the POST
            if not fields.get('message') and \
               not fields.get('imageDescription') and \
               not fields.get('pinToProfile'):
                print('WARN: no message, image description or pin')
                return -1
            submit_text1 = self.server.translate['Publish']
            submit_text2 = self.server.translate['Send']
            submit_text3 = submit_text2
            custom_submit_text = \
                get_config_param(self.server.base_dir, 'customSubmitText')
            if custom_submit_text:
                submit_text3 = custom_submit_text
            if fields.get('submitPost'):
                if fields['submitPost'] != submit_text1 and \
                   fields['submitPost'] != submit_text2 and \
                   fields['submitPost'] != submit_text3:
                    print('WARN: no submit field ' + fields['submitPost'])
                    return -1
            else:
                print('WARN: no submitPost')
                return 2

        if not fields.get('imageDescription'):
            fields['imageDescription'] = None
        if not fields.get('videoTranscript'):
            fields['videoTranscript'] = None
        if not fields.get('subject'):
            fields['subject'] = None
        if not fields.get('replyTo'):
            fields['replyTo'] = None

        if not fields.get('schedulePost'):
            fields['schedulePost'] = False
        else:
            fields['schedulePost'] = True
        print('DEBUG: shedulePost ' + str(fields['schedulePost']))

        if not fields.get('eventDate'):
            fields['eventDate'] = None
        if not fields.get('eventTime'):
            fields['eventTime'] = None
        if not fields.get('eventEndTime'):
            fields['eventEndTime'] = None
        if not fields.get('location'):
            fields['location'] = None
        if not fields.get('languagesDropdown'):
            fields['languagesDropdown'] = self.server.system_language
        set_default_post_language(self.server.base_dir, nickname,
                                  self.server.domain,
                                  fields['languagesDropdown'])
        self.server.default_post_language[nickname] = \
            fields['languagesDropdown']

        if not citations_button_press:
            # Store a file which contains the time in seconds
            # since epoch when an attempt to post something was made.
            # This is then used for active monthly users counts
            last_used_filename = \
                acct_dir(self.server.base_dir,
                         nickname, self.server.domain) + '/.lastUsed'
            try:
                with open(last_used_filename, 'w+',
                          encoding='utf-8') as lastfile:
                    lastfile.write(str(int(time.time())))
            except OSError:
                print('EX: _receive_new_post_process unable to write ' +
                      last_used_filename)

        mentions_str = ''
        if fields.get('mentions'):
            mentions_str = fields['mentions'].strip() + ' '
        if not fields.get('commentsEnabled'):
            comments_enabled = False
        else:
            comments_enabled = True

        buy_url = ''
        if fields.get('buyUrl'):
            buy_url = fields['buyUrl']

        chat_url = ''
        if fields.get('chatUrl'):
            chat_url = fields['chatUrl']

        if post_type == 'newpost':
            if not fields.get('pinToProfile'):
                pin_to_profile = False
            else:
                pin_to_profile = True
                # is the post message empty?
                if not fields['message']:
                    # remove the pinned content from profile screen
                    undo_pinned_post(self.server.base_dir,
                                     nickname, self.server.domain)
                    return 1

            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname, self.server.domain)

            conversation_id = None
            if fields.get('conversationId'):
                conversation_id = fields['conversationId']

            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)

            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_public_post(self.server.base_dir,
                                   nickname,
                                   self.server.domain,
                                   self.server.port,
                                   self.server.http_prefix,
                                   mentions_str + fields['message'],
                                   False, False, comments_enabled,
                                   filename, attachment_media_type,
                                   fields['imageDescription'],
                                   video_transcript,
                                   city,
                                   fields['replyTo'], fields['replyTo'],
                                   fields['subject'],
                                   fields['schedulePost'],
                                   fields['eventDate'],
                                   fields['eventTime'],
                                   fields['eventEndTime'],
                                   fields['location'], False,
                                   fields['languagesDropdown'],
                                   conversation_id,
                                   self.server.low_bandwidth,
                                   self.server.content_license_url,
                                   media_license_url, media_creator,
                                   languages_understood,
                                   self.server.translate, buy_url,
                                   chat_url,
                                   self.server.auto_cw_cache)
            if message_json:
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited public post ' +
                          str(message_json))
                if fields['schedulePost']:
                    return 1
                if pin_to_profile:
                    sys_language = self.server.system_language
                    content_str = \
                        get_base_content_from_post(message_json,
                                                   sys_language)
                    pin_post2(self.server.base_dir,
                              nickname, self.server.domain, content_str)
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'newblog':
            # citations button on newblog screen
            if citations_button_press:
                message_json = \
                    html_citations(self.server.base_dir,
                                   nickname,
                                   self.server.domain,
                                   self.server.translate,
                                   self.server.newswire,
                                   fields['subject'],
                                   fields['message'],
                                   self.server.theme_name)
                if message_json:
                    message_json = message_json.encode('utf-8')
                    message_json_len = len(message_json)
                    set_headers(self, 'text/html',
                                message_json_len,
                                cookie, calling_domain, False)
                    write2(self, message_json)
                    return 1
                else:
                    return -1
            if not fields['subject']:
                print('WARN: blog posts must have a title')
                return -1
            if not fields['message']:
                print('WARN: blog posts must have content')
                return -1
            # submit button on newblog screen
            save_to_file = False
            client_to_server = False
            city = None
            conversation_id = None
            if fields.get('conversationId'):
                conversation_id = fields['conversationId']
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_blog_post(self.server.base_dir, nickname,
                                 self.server.domain, self.server.port,
                                 self.server.http_prefix,
                                 fields['message'],
                                 save_to_file,
                                 client_to_server, comments_enabled,
                                 filename, attachment_media_type,
                                 fields['imageDescription'],
                                 video_transcript,
                                 city,
                                 fields['replyTo'], fields['replyTo'],
                                 fields['subject'],
                                 fields['schedulePost'],
                                 fields['eventDate'],
                                 fields['eventTime'],
                                 fields['eventEndTime'],
                                 fields['location'],
                                 fields['languagesDropdown'],
                                 conversation_id,
                                 self.server.low_bandwidth,
                                 self.server.content_license_url,
                                 media_license_url, media_creator,
                                 languages_understood,
                                 self.server.translate, buy_url,
                                 chat_url)
            if message_json:
                if fields['schedulePost']:
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    refresh_newswire(self.server.base_dir)
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'editblogpost':
            print('Edited blog post received')
            post_filename = \
                locate_post(self.server.base_dir,
                            nickname, self.server.domain,
                            fields['postUrl'])
            if os.path.isfile(post_filename):
                post_json_object = load_json(post_filename)
                if post_json_object:
                    cached_filename = \
                        acct_dir(self.server.base_dir,
                                 nickname, self.server.domain) + \
                        '/postcache/' + \
                        fields['postUrl'].replace('/', '#') + '.html'
                    if os.path.isfile(cached_filename):
                        print('Edited blog post, removing cached html')
                        try:
                            os.remove(cached_filename)
                        except OSError:
                            print('EX: _receive_new_post_process ' +
                                  'unable to delete ' + cached_filename)
                    # remove from memory cache
                    remove_post_from_cache(post_json_object,
                                           self.server.recent_posts_cache)
                    # change the blog post title
                    post_json_object['object']['summary'] = \
                        fields['subject']
                    # format message
                    tags = []
                    hashtags_dict = {}
                    mentioned_recipients = []
                    fields['message'] = \
                        add_html_tags(self.server.base_dir,
                                      self.server.http_prefix,
                                      nickname, self.server.domain,
                                      fields['message'],
                                      mentioned_recipients,
                                      hashtags_dict,
                                      self.server.translate,
                                      True)
                    # replace emoji with unicode
                    tags = []
                    for _, tag in hashtags_dict.items():
                        tags.append(tag)
                    # get list of tags
                    fields['message'] = \
                        replace_emoji_from_tags(curr_session,
                                                self.server.base_dir,
                                                fields['message'],
                                                tags, 'content',
                                                self.server.debug,
                                                True)

                    post_json_object['object']['content'] = \
                        fields['message']
                    content_map = post_json_object['object']['contentMap']
                    content_map[self.server.system_language] = \
                        fields['message']

                    img_description = ''
                    if fields.get('imageDescription'):
                        img_description = fields['imageDescription']
                    video_transcript = ''
                    if fields.get('videoTranscript'):
                        video_transcript = fields['videoTranscript']

                    if filename:
                        city = get_spoofed_city(self.server.city,
                                                self.server.base_dir,
                                                nickname,
                                                self.server.domain)
                        license_url = self.server.content_license_url
                        if fields.get('mediaLicense'):
                            license_url = fields['mediaLicense']
                            if '://' not in license_url:
                                license_url = \
                                    license_link_from_name(license_url)
                        creator = ''
                        if fields.get('mediaCreator'):
                            creator = fields['mediaCreator']
                        post_json_object['object'] = \
                            attach_media(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain,
                                         self.server.port,
                                         post_json_object['object'],
                                         filename,
                                         attachment_media_type,
                                         img_description,
                                         video_transcript,
                                         city,
                                         self.server.low_bandwidth,
                                         license_url, creator,
                                         fields['languagesDropdown'])

                    replace_you_tube(post_json_object,
                                     self.server.yt_replace_domain,
                                     self.server.system_language)
                    replace_twitter(post_json_object,
                                    self.server.twitter_replacement_domain,
                                    self.server.system_language)
                    save_json(post_json_object, post_filename)
                    # also save to the news actor
                    if nickname != 'news':
                        post_filename = \
                            post_filename.replace('#users#' +
                                                  nickname + '#',
                                                  '#users#news#')
                        save_json(post_json_object, post_filename)
                    print('Edited blog post, resaved ' + post_filename)
                    return 1
                else:
                    print('Edited blog post, unable to load json for ' +
                          post_filename)
            else:
                print('Edited blog post not found ' +
                      str(fields['postUrl']))
            return -1
        elif post_type == 'newunlisted':
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            save_to_file = False
            client_to_server = False

            conversation_id = None
            if fields.get('conversationId'):
                conversation_id = fields['conversationId']

            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_unlisted_post(self.server.base_dir,
                                     nickname,
                                     self.server.domain, self.server.port,
                                     self.server.http_prefix,
                                     mentions_str + fields['message'],
                                     save_to_file,
                                     client_to_server, comments_enabled,
                                     filename, attachment_media_type,
                                     fields['imageDescription'],
                                     video_transcript,
                                     city,
                                     fields['replyTo'],
                                     fields['replyTo'],
                                     fields['subject'],
                                     fields['schedulePost'],
                                     fields['eventDate'],
                                     fields['eventTime'],
                                     fields['eventEndTime'],
                                     fields['location'],
                                     fields['languagesDropdown'],
                                     conversation_id,
                                     self.server.low_bandwidth,
                                     self.server.content_license_url,
                                     media_license_url, media_creator,
                                     languages_understood,
                                     self.server.translate, buy_url,
                                     chat_url,
                                     self.server.auto_cw_cache)
            if message_json:
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited unlisted post ' +
                          str(message_json))

                if fields['schedulePost']:
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'newfollowers':
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            save_to_file = False
            client_to_server = False

            conversation_id = None
            if fields.get('conversationId'):
                conversation_id = fields['conversationId']

            mentions_message = mentions_str + fields['message']
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_followers_only_post(self.server.base_dir,
                                           nickname,
                                           self.server.domain,
                                           self.server.port,
                                           self.server.http_prefix,
                                           mentions_message,
                                           save_to_file,
                                           client_to_server,
                                           comments_enabled,
                                           filename, attachment_media_type,
                                           fields['imageDescription'],
                                           video_transcript,
                                           city,
                                           fields['replyTo'],
                                           fields['replyTo'],
                                           fields['subject'],
                                           fields['schedulePost'],
                                           fields['eventDate'],
                                           fields['eventTime'],
                                           fields['eventEndTime'],
                                           fields['location'],
                                           fields['languagesDropdown'],
                                           conversation_id,
                                           self.server.low_bandwidth,
                                           self.server.content_license_url,
                                           media_license_url,
                                           media_creator,
                                           languages_understood,
                                           self.server.translate,
                                           buy_url, chat_url,
                                           self.server.auto_cw_cache)
            if message_json:
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited followers post ' +
                          str(message_json))

                if fields['schedulePost']:
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'newdm':
            message_json = None
            print('A DM was posted')
            if '@' in mentions_str:
                city = get_spoofed_city(self.server.city,
                                        self.server.base_dir,
                                        nickname,
                                        self.server.domain)
                save_to_file = False
                client_to_server = False

                conversation_id = None
                if fields.get('conversationId'):
                    conversation_id = fields['conversationId']
                content_license_url = self.server.content_license_url

                languages_understood = \
                    get_understood_languages(self.server.base_dir,
                                             self.server.http_prefix,
                                             nickname,
                                             self.server.domain_full,
                                             self.server.person_cache)

                reply_is_chat = False
                if fields.get('replychatmsg'):
                    reply_is_chat = fields['replychatmsg']

                dm_license_url = self.server.dm_license_url
                media_license_url = content_license_url
                if fields.get('mediaLicense'):
                    media_license_url = fields['mediaLicense']
                    if '://' not in media_license_url:
                        media_license_url = \
                            license_link_from_name(media_license_url)
                media_creator = ''
                if fields.get('mediaCreator'):
                    media_creator = fields['mediaCreator']
                video_transcript = ''
                if fields.get('videoTranscript'):
                    video_transcript = fields['videoTranscript']
                message_json = \
                    create_direct_message_post(self.server.base_dir,
                                               nickname,
                                               self.server.domain,
                                               self.server.port,
                                               self.server.http_prefix,
                                               mentions_str +
                                               fields['message'],
                                               save_to_file,
                                               client_to_server,
                                               comments_enabled,
                                               filename,
                                               attachment_media_type,
                                               fields['imageDescription'],
                                               video_transcript,
                                               city,
                                               fields['replyTo'],
                                               fields['replyTo'],
                                               fields['subject'],
                                               True,
                                               fields['schedulePost'],
                                               fields['eventDate'],
                                               fields['eventTime'],
                                               fields['eventEndTime'],
                                               fields['location'],
                                               fields['languagesDropdown'],
                                               conversation_id,
                                               self.server.low_bandwidth,
                                               dm_license_url,
                                               media_license_url,
                                               media_creator,
                                               languages_understood,
                                               reply_is_chat,
                                               self.server.translate,
                                               buy_url, chat_url,
                                               self.server.auto_cw_cache)
            if message_json:
                print('DEBUG: posting DM edited_postid ' +
                      str(edited_postid))
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited dm post ' +
                          str(message_json))

                if fields['schedulePost']:
                    return 1
                print('Sending new DM to ' +
                      str(message_json['object']['to']))
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'newreminder':
            message_json = None
            handle = nickname + '@' + self.server.domain_full
            print('A reminder was posted for ' + handle)
            if '@' + handle not in mentions_str:
                mentions_str = '@' + handle + ' ' + mentions_str
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            save_to_file = False
            client_to_server = False
            comments_enabled = False
            conversation_id = None
            mentions_message = mentions_str + fields['message']
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_direct_message_post(self.server.base_dir,
                                           nickname,
                                           self.server.domain,
                                           self.server.port,
                                           self.server.http_prefix,
                                           mentions_message,
                                           save_to_file,
                                           client_to_server,
                                           comments_enabled,
                                           filename, attachment_media_type,
                                           fields['imageDescription'],
                                           video_transcript,
                                           city,
                                           None, None,
                                           fields['subject'],
                                           True, fields['schedulePost'],
                                           fields['eventDate'],
                                           fields['eventTime'],
                                           fields['eventEndTime'],
                                           fields['location'],
                                           fields['languagesDropdown'],
                                           conversation_id,
                                           self.server.low_bandwidth,
                                           self.server.dm_license_url,
                                           media_license_url,
                                           media_creator,
                                           languages_understood,
                                           False, self.server.translate,
                                           buy_url, chat_url,
                                           self.server.auto_cw_cache)
            if message_json:
                if fields['schedulePost']:
                    return 1
                print('DEBUG: new reminder to ' +
                      str(message_json['object']['to']) + ' ' +
                      str(edited_postid))
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'dm',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited reminder post ' +
                          str(message_json))
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    return 1
                return -1
        elif post_type == 'newreport':
            if attachment_media_type:
                if attachment_media_type != 'image':
                    return -1
            # So as to be sure that this only goes to moderators
            # and not accounts being reported we disable any
            # included fediverse addresses by replacing '@' with '-at-'
            fields['message'] = fields['message'].replace('@', '-at-')
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_report_post(self.server.base_dir,
                                   nickname,
                                   self.server.domain, self.server.port,
                                   self.server.http_prefix,
                                   mentions_str + fields['message'],
                                   False, False, True,
                                   filename, attachment_media_type,
                                   fields['imageDescription'],
                                   video_transcript,
                                   city,
                                   self.server.debug, fields['subject'],
                                   fields['languagesDropdown'],
                                   self.server.low_bandwidth,
                                   self.server.content_license_url,
                                   media_license_url, media_creator,
                                   languages_understood,
                                   self.server.translate,
                                   self.server.auto_cw_cache)
            if message_json:
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    return 1
                return -1
        elif post_type == 'newquestion':
            if not fields.get('duration'):
                return -1
            if not fields.get('message'):
                return -1
            q_options = []
            for question_ctr in range(8):
                if fields.get('questionOption' + str(question_ctr)):
                    q_options.append(fields['questionOption' +
                                            str(question_ctr)])
            if not q_options:
                return -1
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            if isinstance(fields['duration'], str):
                if len(fields['duration']) > 5:
                    return -1
            int_duration_days = int(fields['duration'])
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_question_post(self.server.base_dir,
                                     nickname,
                                     self.server.domain,
                                     self.server.port,
                                     self.server.http_prefix,
                                     fields['message'], q_options,
                                     False, False,
                                     comments_enabled,
                                     filename, attachment_media_type,
                                     fields['imageDescription'],
                                     video_transcript,
                                     city,
                                     fields['subject'],
                                     int_duration_days,
                                     fields['languagesDropdown'],
                                     self.server.low_bandwidth,
                                     self.server.content_license_url,
                                     media_license_url, media_creator,
                                     languages_understood,
                                     self.server.translate,
                                     self.server.auto_cw_cache)
            if message_json:
                if self.server.debug:
                    print('DEBUG: new Question')
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    return 1
            return -1
        elif post_type in ('newreadingstatus'):
            if not fields.get('readingupdatetype'):
                print(post_type + ' no readingupdatetype')
                return -1
            if fields['readingupdatetype'] not in ('readingupdatewant',
                                                   'readingupdateread',
                                                   'readingupdatefinished',
                                                   'readingupdaterating'):
                print(post_type + ' not recognised ' +
                      fields['readingupdatetype'])
                return -1
            if not fields.get('booktitle'):
                print(post_type + ' no booktitle')
                return -1
            if not fields.get('bookurl'):
                print(post_type + ' no bookurl')
                return -1
            book_rating = 0.0
            if fields.get('bookrating'):
                if isinstance(fields['bookrating'], float) or \
                   isinstance(fields['bookrating'], int):
                    book_rating = fields['bookrating']
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            conversation_id = None
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname, self.server.domain)
            msg_str = fields['readingupdatetype']
            # reading status
            message_json = \
                create_reading_post(self.server.base_dir,
                                    nickname,
                                    self.server.domain,
                                    self.server.port,
                                    self.server.http_prefix,
                                    mentions_str, msg_str,
                                    fields['booktitle'],
                                    fields['bookurl'],
                                    book_rating,
                                    False, False, comments_enabled,
                                    filename, attachment_media_type,
                                    fields['imageDescription'],
                                    video_transcript,
                                    city, None, None,
                                    fields['subject'],
                                    fields['schedulePost'],
                                    fields['eventDate'],
                                    fields['eventTime'],
                                    fields['eventEndTime'],
                                    fields['location'], False,
                                    fields['languagesDropdown'],
                                    conversation_id,
                                    self.server.low_bandwidth,
                                    self.server.content_license_url,
                                    media_license_url, media_creator,
                                    languages_understood,
                                    self.server.translate, buy_url,
                                    chat_url,
                                    self.server.auto_cw_cache)
            if message_json:
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited reading status post ' +
                          str(message_json))
                if fields['schedulePost']:
                    return 1
                if not fields.get('pinToProfile'):
                    pin_to_profile = False
                else:
                    pin_to_profile = True
                if pin_to_profile:
                    sys_language = self.server.system_language
                    content_str = \
                        get_base_content_from_post(message_json,
                                                   sys_language)
                    pin_post2(self.server.base_dir,
                              nickname, self.server.domain, content_str)
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type in ('newshare', 'newwanted'):
            if not fields.get('itemQty'):
                print(post_type + ' no itemQty')
                return -1
            if not fields.get('itemType'):
                print(post_type + ' no itemType')
                return -1
            if 'itemPrice' not in fields:
                print(post_type + ' no itemPrice')
                return -1
            if 'itemCurrency' not in fields:
                print(post_type + ' no itemCurrency')
                return -1
            if not fields.get('category'):
                print(post_type + ' no category')
                return -1
            if not fields.get('duration'):
                print(post_type + ' no duratio')
                return -1
            if attachment_media_type:
                if attachment_media_type != 'image':
                    print('Attached media is not an image')
                    return -1
            duration_str = fields['duration']
            if duration_str:
                if ' ' not in duration_str:
                    duration_str = duration_str + ' days'
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            item_qty = 1
            if fields['itemQty']:
                if is_float(fields['itemQty']):
                    item_qty = float(fields['itemQty'])
            item_price = "0.00"
            item_currency = "EUR"
            if fields['itemPrice']:
                item_price, item_currency = \
                    get_price_from_string(fields['itemPrice'])
            if fields['itemCurrency']:
                item_currency = fields['itemCurrency']
            if post_type == 'newshare':
                print('Adding shared item')
                shares_file_type = 'shares'
            else:
                print('Adding wanted item')
                shares_file_type = 'wanted'
            share_on_profile = False
            if fields.get('shareOnProfile'):
                if fields['shareOnProfile'] == 'on':
                    share_on_profile = True
            add_share(self.server.base_dir,
                      self.server.http_prefix,
                      nickname,
                      self.server.domain, self.server.port,
                      fields['subject'],
                      fields['message'],
                      filename,
                      item_qty, fields['itemType'],
                      fields['category'],
                      fields['location'],
                      duration_str,
                      self.server.debug,
                      city, item_price, item_currency,
                      fields['languagesDropdown'],
                      self.server.translate, shares_file_type,
                      self.server.low_bandwidth,
                      self.server.content_license_url,
                      share_on_profile,
                      self.server.block_federated)
            if post_type == 'newshare':
                # add shareOnProfile items to the actor attachments
                # https://codeberg.org/fediverse/fep/src/branch/main/fep/0837/fep-0837.md
                actor = \
                    get_instance_url(calling_domain,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     self.server.onion_domain,
                                     self.server.i2p_domain) + \
                    '/users/' + nickname
                person_cache = self.server.person_cache
                actor_json = get_person_from_cache(self.server.base_dir,
                                                   actor, person_cache)
                if not actor_json:
                    actor_filename = \
                        acct_dir(self.server.base_dir, nickname,
                                 self.server.domain) + '.json'
                    if os.path.isfile(actor_filename):
                        actor_json = load_json(actor_filename, 1, 1)
                if actor_json:
                    max_shares_on_profile = \
                        self.server.max_shares_on_profile
                    if add_shares_to_actor(self.server.base_dir,
                                           nickname, self.server.domain,
                                           actor_json,
                                           max_shares_on_profile):
                        remove_person_from_cache(self.server.base_dir,
                                                 actor, person_cache)
                        store_person_in_cache(self.server.base_dir, actor,
                                              actor_json, person_cache,
                                              True)
                        actor_filename = \
                            acct_dir(self.server.base_dir,
                                     nickname,
                                     self.server.domain) + '.json'
                        save_json(actor_json, actor_filename)
                        # send profile update to followers
                        update_actor_json = \
                            get_actor_update_json(actor_json)
                        print('Sending actor update ' +
                              'after change to attached shares: ' +
                              str(update_actor_json))
                        post_to_outbox(self, update_actor_json,
                                       self.server.project_version,
                                       nickname,
                                       curr_session, proxy_type)

            if filename:
                if os.path.isfile(filename):
                    try:
                        os.remove(filename)
                    except OSError:
                        print('EX: _receive_new_post_process ' +
                              'unable to delete ' + filename)
            self.post_to_nickname = nickname
            return 1
    return -1


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
