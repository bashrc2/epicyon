__filename__ = "daemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer, HTTPServer
import sys
import json
import time
import urllib.parse
import datetime
from socket import error as SocketError
import errno
from functools import partial
import pyqrcode
# for saving images
from hashlib import sha256
from hashlib import md5
from shutil import copyfile
from session import create_session
from webfinger import webfinger_meta
from webfinger import webfinger_node_info
from webfinger import webfinger_lookup
from webfinger import webfinger_update
from mastoapiv1 import masto_api_v1_response
from metadata import meta_data_node_info
from metadata import metadata_custom_emoji
from enigma import get_enigma_pub_key
from enigma import set_enigma_pub_key
from pgp import get_email_address
from pgp import set_email_address
from pgp import get_pgp_pub_key
from pgp import get_pgp_fingerprint
from pgp import set_pgp_pub_key
from pgp import set_pgp_fingerprint
from xmpp import get_xmpp_address
from xmpp import set_xmpp_address
from ssb import get_ssb_address
from ssb import set_ssb_address
from tox import get_tox_address
from tox import set_tox_address
from briar import get_briar_address
from briar import set_briar_address
from jami import get_jami_address
from jami import set_jami_address
from cwtch import get_cwtch_address
from cwtch import set_cwtch_address
from matrix import get_matrix_address
from matrix import set_matrix_address
from donate import get_donation_url
from donate import set_donation_url
from donate import get_website
from donate import set_website
from person import add_actor_update_timestamp
from person import set_person_notes
from person import get_default_person_context
from person import get_actor_update_json
from person import save_person_qrcode
from person import randomize_actor_images
from person import person_upgrade_actor
from person import activate_account
from person import deactivate_account
from person import register_account
from person import person_lookup
from person import person_box_json
from person import create_shared_inbox
from person import create_news_inbox
from person import suspend_account
from person import reenable_account
from person import remove_account
from person import can_remove_post
from person import person_snooze
from person import person_unsnooze
from posts import get_original_post_from_announce_url
from posts import save_post_to_box
from posts import get_instance_actor_key
from posts import remove_post_interactions
from posts import outbox_message_create_wrap
from posts import get_pinned_post_as_json
from posts import pin_post
from posts import json_pin_post
from posts import undo_pinned_post
from posts import is_moderator
from posts import create_question_post
from posts import create_public_post
from posts import create_blog_post
from posts import create_report_post
from posts import create_unlisted_post
from posts import create_followers_only_post
from posts import create_direct_message_post
from posts import populate_replies_json
from posts import add_to_field
from posts import expire_cache
from inbox import clear_queue_items
from inbox import inbox_permitted_message
from inbox import inbox_message_has_params
from inbox import run_inbox_queue
from inbox import run_inbox_queue_watchdog
from inbox import save_post_to_inbox_queue
from inbox import populate_replies
from follow import follower_approval_active
from follow import is_following_actor
from follow import get_following_feed
from follow import send_follow_request
from follow import unfollow_account
from follow import create_initial_last_seen
from skills import get_skills_from_list
from skills import no_of_actor_skills
from skills import actor_has_skill
from skills import actor_skill_value
from skills import set_actor_skill_level
from auth import record_login_failure
from auth import authorize
from auth import create_password
from auth import create_basic_auth_header
from auth import authorize_basic
from auth import store_basic_credentials
from threads import thread_with_trace
from threads import remove_dormant_threads
from media import process_meta_data
from media import convert_image_to_low_bandwidth
from media import replace_you_tube
from media import replace_twitter
from media import attach_media
from media import path_is_video
from media import path_is_audio
from blocking import get_cw_list_variable
from blocking import load_cw_lists
from blocking import update_blocked_cache
from blocking import mute_post
from blocking import unmute_post
from blocking import set_broch_mode
from blocking import broch_mode_is_active
from blocking import add_block
from blocking import remove_block
from blocking import add_global_block
from blocking import remove_global_block
from blocking import is_blocked_hashtag
from blocking import is_blocked_domain
from blocking import get_domain_blocklist
from roles import get_actor_roles_list
from roles import set_role
from roles import clear_moderator_status
from roles import clear_editor_status
from roles import clear_counselor_status
from roles import clear_artist_status
from blog import path_contains_blog_link
from blog import html_blog_page_rss2
from blog import html_blog_page_rss3
from blog import html_blog_view
from blog import html_blog_page
from blog import html_blog_post
from blog import html_edit_blog
from blog import get_blog_address
from webapp_theme_designer import html_theme_designer
from webapp_minimalbutton import set_minimal
from webapp_minimalbutton import is_minimal
from webapp_utils import get_avatar_image_url
from webapp_utils import html_hashtag_blocked
from webapp_utils import html_following_list
from webapp_utils import set_blog_address
from webapp_utils import html_show_share
from webapp_calendar import html_calendar_delete_confirm
from webapp_calendar import html_calendar
from webapp_about import html_about
from webapp_accesskeys import html_access_keys
from webapp_accesskeys import load_access_keys_for_accounts
from webapp_confirm import html_confirm_delete
from webapp_confirm import html_confirm_remove_shared_item
from webapp_confirm import html_confirm_unblock
from webapp_person_options import html_person_options
from webapp_timeline import html_shares
from webapp_timeline import html_wanted
from webapp_timeline import html_inbox
from webapp_timeline import html_bookmarks
from webapp_timeline import html_inbox_d_ms
from webapp_timeline import html_inbox_replies
from webapp_timeline import html_inbox_media
from webapp_timeline import html_inbox_blogs
from webapp_timeline import html_inbox_news
from webapp_timeline import html_inbox_features
from webapp_timeline import html_outbox
from webapp_media import load_peertube_instances
from webapp_moderation import html_account_info
from webapp_moderation import html_moderation
from webapp_moderation import html_moderation_info
from webapp_create_post import html_new_post
from webapp_login import html_login
from webapp_login import html_get_login_credentials
from webapp_suspended import html_suspended
from webapp_tos import html_terms_of_service
from webapp_confirm import html_confirm_follow
from webapp_confirm import html_confirm_unfollow
from webapp_post import html_emoji_reaction_picker
from webapp_post import html_post_replies
from webapp_post import html_individual_post
from webapp_post import individual_post_as_html
from webapp_profile import html_edit_profile
from webapp_profile import html_profile_after_search
from webapp_profile import html_profile
from webapp_column_left import html_links_mobile
from webapp_column_left import html_edit_links
from webapp_column_right import html_newswire_mobile
from webapp_column_right import html_edit_newswire
from webapp_column_right import html_citations
from webapp_column_right import html_edit_news_post
from webapp_search import html_skills_search
from webapp_search import html_history_search
from webapp_search import html_hashtag_search
from webapp_search import rss_hashtag_search
from webapp_search import html_search_emoji
from webapp_search import html_search_shared_items
from webapp_search import html_search_emoji_text_entry
from webapp_search import html_search
from webapp_hashtagswarm import get_hashtag_categories_feed
from webapp_hashtagswarm import html_search_hashtag_category
from webapp_welcome import welcome_screen_is_complete
from webapp_welcome import html_welcome_screen
from webapp_welcome import is_welcome_screen_complete
from webapp_welcome_profile import html_welcome_profile
from webapp_welcome_final import html_welcome_final
from shares import merge_shared_item_tokens
from shares import run_federated_shares_daemon
from shares import run_federated_shares_watchdog
from shares import update_shared_item_federation_token
from shares import create_shared_item_federation_token
from shares import authorize_shared_items
from shares import generate_shared_item_federation_tokens
from shares import get_shares_feed_for_person
from shares import add_share
from shares import remove_shared_item
from shares import expire_shares
from shares import shares_catalog_endpoint
from shares import shares_catalog_account_endpoint
from shares import shares_catalog_csv_endpoint
from categories import set_hashtag_category
from categories import update_hashtag_categories
from languages import get_actor_languages
from languages import set_actor_languages
from like import update_likes_collection
from reaction import update_reaction_collection
from utils import undo_reaction_collection_entry
from utils import get_new_post_endpoints
from utils import has_actor
from utils import set_reply_interval_hours
from utils import can_reply_to
from utils import is_dm
from utils import replace_users_with_at
from utils import local_actor_url
from utils import is_float
from utils import valid_password
from utils import remove_line_endings
from utils import get_base_content_from_post
from utils import acct_dir
from utils import get_image_extension_from_mime_type
from utils import get_image_mime_type
from utils import has_object_dict
from utils import user_agent_domain
from utils import is_local_network_address
from utils import permitted_dir
from utils import is_account_dir
from utils import get_occupation_skills
from utils import get_occupation_name
from utils import set_occupation_name
from utils import load_translations_from_file
from utils import get_local_network_addresses
from utils import decoded_host
from utils import is_public_post
from utils import get_locked_account
from utils import has_users_path
from utils import get_full_domain
from utils import remove_html
from utils import is_editor
from utils import is_artist
from utils import get_image_extensions
from utils import media_file_mime_type
from utils import get_css
from utils import first_paragraph_from_string
from utils import clear_from_post_caches
from utils import contains_invalid_chars
from utils import is_system_account
from utils import set_config_param
from utils import get_config_param
from utils import remove_id_ending
from utils import undo_likes_collection_entry
from utils import delete_post
from utils import is_blog_post
from utils import remove_avatar_from_cache
from utils import locate_post
from utils import get_cached_post_filename
from utils import remove_post_from_cache
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import get_status_number
from utils import url_permitted
from utils import load_json
from utils import save_json
from utils import is_suspended
from utils import dangerous_markup
from utils import refresh_newswire
from utils import is_image_file
from utils import has_group_type
from manualapprove import manual_deny_follow_request_thread
from manualapprove import manual_approve_follow_request_thread
from announce import create_announce
from content import contains_invalid_local_links
from content import get_price_from_string
from content import replace_emoji_from_tags
from content import add_html_tags
from content import extract_media_in_form_post
from content import save_media_in_form_post
from content import extract_text_fields_in_post
from cache import check_for_changed_actor
from cache import store_person_in_cache
from cache import get_person_from_cache
from cache import get_person_pub_key
from httpsig import verify_post_headers
from theme import reset_theme_designer_settings
from theme import set_theme_from_designer
from theme import scan_themes_for_scripts
from theme import import_theme
from theme import export_theme
from theme import is_news_theme_name
from theme import get_text_mode_banner
from theme import set_news_avatar
from theme import set_theme
from theme import get_theme
from theme import enable_grayscale
from theme import disable_grayscale
from schedule import run_post_schedule
from schedule import run_post_schedule_watchdog
from schedule import remove_scheduled_posts
from outbox import post_message_to_outbox
from happening import remove_calendar_event
from bookmarks import bookmark_post
from bookmarks import undo_bookmark_post
from petnames import set_pet_name
from followingCalendar import add_person_to_calendar
from followingCalendar import remove_person_from_calendar
from notifyOnPost import add_notify_on_post
from notifyOnPost import remove_notify_on_post
from devices import e2e_edevices_collection
from devices import e2e_evalid_device
from devices import e2e_eadd_device
from newswire import get_rs_sfrom_dict
from newswire import rss2header
from newswire import rss2footer
from newswire import load_hashtag_categories
from newsdaemon import run_newswire_watchdog
from newsdaemon import run_newswire_daemon
from filters import is_filtered
from filters import add_global_filter
from filters import remove_global_filter
from context import has_valid_context
from context import get_individual_post_context
from speaker import get_ssm_lbox
from city import get_spoofed_city
from fitnessFunctions import fitness_performance
from fitnessFunctions import fitness_thread
from fitnessFunctions import sorted_watch_points
from fitnessFunctions import html_watch_points_graph
import os


# maximum number of posts to list in outbox feed
max_posts_in_feed = 12

# maximum number of posts in a hashtag feed
max_posts_in_hashtag_feed = 6

# reduced posts for media feed because it can take a while
max_posts_in_media_feed = 6

# Blogs can be longer, so don't show many per page
max_posts_in_blogs_feed = 4

max_posts_in_news_feed = 10

# Maximum number of entries in returned rss.xml
max_posts_in_rss_feed = 10

# number of follows/followers per page
follows_per_page = 6

# number of item shares per page
shares_per_page = 12


def save_domain_qrcode(base_dir: str, http_prefix: str,
                       domain_full: str, scale=6) -> None:
    """Saves a qrcode image for the domain name
    This helps to transfer onion or i2p domains to a mobile device
    """
    qrcode_filename = base_dir + '/accounts/qrcode.png'
    url = pyqrcode.create(http_prefix + '://' + domain_full)
    url.png(qrcode_filename, scale)


class PubServer(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _update_known_crawlers(self, ua_str: str) -> None:
        """Updates a dictionary of known crawlers accessing nodeinfo
        or the masto API
        """
        if not ua_str:
            return

        curr_time = int(time.time())
        if self.server.known_crawlers.get(ua_str):
            self.server.known_crawlers[ua_str]['hits'] += 1
            self.server.known_crawlers[ua_str]['lastseen'] = curr_time
        else:
            self.server.known_crawlers[ua_str] = {
                "lastseen": curr_time,
                "hits": 1
            }

        if curr_time - self.server.last_known_crawler >= 30:
            # remove any old observations
            remove_crawlers = []
            for uagent, item in self.server.known_crawlers.items():
                if curr_time - item['lastseen'] >= 60 * 60 * 24 * 30:
                    remove_crawlers.append(uagent)
            for uagent in remove_crawlers:
                del self.server.known_crawlers[uagent]
            # save the list of crawlers
            save_json(self.server.known_crawlers,
                      self.server.base_dir + '/accounts/knownCrawlers.json')
        self.server.last_known_crawler = curr_time

    def _get_instance_url(self, calling_domain: str) -> str:
        """Returns the URL for this instance
        """
        if calling_domain.endswith('.onion') and \
           self.server.onion_domain:
            instance_url = 'http://' + self.server.onion_domain
        elif (calling_domain.endswith('.i2p') and
              self.server.i2p_domain):
            instance_url = 'http://' + self.server.i2p_domain
        else:
            instance_url = \
                self.server.http_prefix + '://' + self.server.domain_full
        return instance_url

    def _getheader_signature_input(self):
        """There are different versions of http signatures with
        different header styles
        """
        if self.headers.get('Signature-Input'):
            # https://tools.ietf.org/html/
            # draft-ietf-httpbis-message-signatures-01
            return self.headers['Signature-Input']
        if self.headers.get('signature-input'):
            return self.headers['signature-input']
        if self.headers.get('signature'):
            # Ye olde Masto http sig
            return self.headers['signature']
        return None

    def handle_error(self, request, client_address):
        print('ERROR: http server error: ' + str(request) + ', ' +
              str(client_address))
        pass

    def _send_reply_to_question(self, nickname: str, message_id: str,
                                answer: str) -> None:
        """Sends a reply to a question
        """
        votes_filename = \
            acct_dir(self.server.base_dir, nickname, self.server.domain) + \
            '/questions.txt'

        if os.path.isfile(votes_filename):
            # have we already voted on this?
            if message_id in open(votes_filename).read():
                print('Already voted on message ' + message_id)
                return

        print('Voting on message ' + message_id)
        print('Vote for: ' + answer)
        comments_enabled = True
        attach_image_filename = None
        media_type = None
        image_description = None
        in_reply_to = message_id
        in_reply_to_atom_uri = message_id
        subject = None
        schedule_post = False
        event_date = None
        event_time = None
        location = None
        conversation_id = None
        city = get_spoofed_city(self.server.city,
                                self.server.base_dir,
                                nickname, self.server.domain)

        message_json = \
            create_public_post(self.server.base_dir,
                               nickname,
                               self.server.domain, self.server.port,
                               self.server.http_prefix,
                               answer, False, False, False,
                               comments_enabled,
                               attach_image_filename, media_type,
                               image_description, city,
                               in_reply_to,
                               in_reply_to_atom_uri,
                               subject,
                               schedule_post,
                               event_date,
                               event_time,
                               location, False,
                               self.server.system_language,
                               conversation_id,
                               self.server.low_bandwidth,
                               self.server.content_license_url)
        if message_json:
            # name field contains the answer
            message_json['object']['name'] = answer
            if self._post_to_outbox(message_json,
                                    self.server.project_version, nickname):
                post_filename = \
                    locate_post(self.server.base_dir, nickname,
                                self.server.domain, message_id)
                if post_filename:
                    post_json_object = load_json(post_filename)
                    if post_json_object:
                        populate_replies(self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain_full,
                                         post_json_object,
                                         self.server.max_replies,
                                         self.server.debug)
                        # record the vote
                        try:
                            with open(votes_filename, 'a+') as votes_file:
                                votes_file.write(message_id + '\n')
                        except OSError:
                            print('EX: unable to write vote ' +
                                  votes_filename)

                        # ensure that the cached post is removed if it exists,
                        # so that it then will be recreated
                        cached_post_filename = \
                            get_cached_post_filename(self.server.base_dir,
                                                     nickname,
                                                     self.server.domain,
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
                                               self.server.recent_posts_cache)
            else:
                print('ERROR: unable to post vote to outbox')
        else:
            print('ERROR: unable to create vote')

    def _blocked_user_agent(self, calling_domain: str, agent_str: str) -> bool:
        """Should a GET or POST be blocked based upon its user agent?
        """
        if not agent_str:
            return False

        agent_str_lower = agent_str.lower()
        default_agent_blocks = [
            'fedilist'
        ]
        for ua_block in default_agent_blocks:
            if ua_block in agent_str_lower:
                print('Blocked User agent: ' + ua_block)
                return True

        agent_domain = None

        if agent_str:
            # is this a web crawler? If so the block it
            if 'bot/' in agent_str_lower or 'bot-' in agent_str_lower:
                if self.server.news_instance:
                    return False
                print('Blocked Crawler: ' + agent_str)
                return True
            # get domain name from User-Agent
            agent_domain = user_agent_domain(agent_str, self.server.debug)
        else:
            # no User-Agent header is present
            return True

        # is the User-Agent type blocked? eg. "Mastodon"
        if self.server.user_agents_blocked:
            blocked_ua = False
            for agentName in self.server.user_agents_blocked:
                if agentName in agent_str:
                    blocked_ua = True
                    break
            if blocked_ua:
                return True

        if not agent_domain:
            return False

        # is the User-Agent domain blocked
        blocked_ua = False
        if not agent_domain.startswith(calling_domain):
            self.server.blocked_cache_last_updated = \
                update_blocked_cache(self.server.base_dir,
                                     self.server.blocked_cache,
                                     self.server.blocked_cache_last_updated,
                                     self.server.blocked_cache_update_secs)

            blocked_ua = is_blocked_domain(self.server.base_dir, agent_domain,
                                           self.server.blocked_cache)
            # if self.server.debug:
            if blocked_ua:
                print('Blocked User agent: ' + agent_domain)
        return blocked_ua

    def _request_csv(self) -> bool:
        """Should a csv response be given?
        """
        if not self.headers.get('Accept'):
            return False
        accept_str = self.headers['Accept']
        if 'text/csv' in accept_str:
            return True
        return False

    def _request_http(self) -> bool:
        """Should a http response be given?
        """
        if not self.headers.get('Accept'):
            return False
        accept_str = self.headers['Accept']
        if self.server.debug:
            print('ACCEPT: ' + accept_str)
        if 'application/ssml' in accept_str:
            if 'text/html' not in accept_str:
                return False
        if 'image/' in accept_str:
            if 'text/html' not in accept_str:
                return False
        if 'video/' in accept_str:
            if 'text/html' not in accept_str:
                return False
        if 'audio/' in accept_str:
            if 'text/html' not in accept_str:
                return False
        if accept_str.startswith('*'):
            if self.headers.get('User-Agent'):
                if 'ELinks' in self.headers['User-Agent'] or \
                   'Lynx' in self.headers['User-Agent']:
                    return True
            return False
        if 'json' in accept_str:
            return False
        return True

    def _signed_ge_tkey_id(self) -> str:
        """Returns the actor from the signed GET key_id
        """
        signature = None
        if self.headers.get('signature'):
            signature = self.headers['signature']
        elif self.headers.get('Signature'):
            signature = self.headers['Signature']

        # check that the headers are signed
        if not signature:
            if self.server.debug:
                print('AUTH: secure mode actor, ' +
                      'GET has no signature in headers')
            return None

        # get the key_id, which is typically the instance actor
        key_id = None
        signature_params = signature.split(',')
        for signature_item in signature_params:
            if signature_item.startswith('keyId='):
                if '"' in signature_item:
                    key_id = signature_item.split('"')[1]
                    # remove #main-key
                    if '#' in key_id:
                        key_id = key_id.split('#')[0]
                    return key_id
        return None

    def _establish_session(self, calling_function: str) -> bool:
        """Recreates session if needed
        """
        if self.server.session:
            return True
        print('DEBUG: creating new session during ' + calling_function)
        self.server.session = create_session(self.server.proxy_type)
        if self.server.session:
            return True
        print('ERROR: GET failed to create session during ' +
              calling_function)
        return False

    def _secure_mode(self, force: bool = False) -> bool:
        """http authentication of GET requests for json
        """
        if not self.server.secure_mode and not force:
            return True

        key_id = self._signed_ge_tkey_id()
        if not key_id:
            if self.server.debug:
                print('AUTH: secure mode, ' +
                      'failed to obtain key_id from signature')
            return False

        # is the key_id (actor) valid?
        if not url_permitted(key_id, self.server.federation_list):
            if self.server.debug:
                print('AUTH: Secure mode GET request not permitted: ' + key_id)
            return False

        if not self._establish_session("secure mode"):
            return False

        # obtain the public key
        pubKey = \
            get_person_pub_key(self.server.base_dir,
                               self.server.session, key_id,
                               self.server.person_cache, self.server.debug,
                               self.server.project_version,
                               self.server.http_prefix,
                               self.server.domain, self.server.onion_domain,
                               self.server.signing_priv_key_pem)
        if not pubKey:
            if self.server.debug:
                print('AUTH: secure mode failed to ' +
                      'obtain public key for ' + key_id)
            return False

        # verify the GET request without any digest
        if verify_post_headers(self.server.http_prefix,
                               self.server.domain_full,
                               pubKey, self.headers,
                               self.path, True, None, '', self.server.debug):
            return True

        if self.server.debug:
            print('AUTH: secure mode authorization failed for ' + key_id)
        return False

    def _login_headers(self, fileFormat: str, length: int,
                       calling_domain: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        self.send_header('Host', calling_domain)
        self.send_header('WWW-Authenticate',
                         'title="Login to Epicyon", Basic realm="epicyon"')
        self.end_headers()

    def _logout_headers(self, fileFormat: str, length: int,
                        calling_domain: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        self.send_header('Set-Cookie', 'epicyon=; SameSite=Strict')
        self.send_header('Host', calling_domain)
        self.send_header('WWW-Authenticate',
                         'title="Login to Epicyon", Basic realm="epicyon"')
        self.end_headers()

    def _quoted_redirect(self, redirect: str) -> str:
        """hashtag screen urls sometimes contain non-ascii characters which
        need to be url encoded
        """
        if '/tags/' not in redirect:
            return redirect
        lastStr = redirect.split('/')[-1]
        return redirect.replace('/' + lastStr, '/' +
                                urllib.parse.quote_plus(lastStr))

    def _logout_redirect(self, redirect: str, cookie: str,
                         calling_domain: str) -> None:
        if '://' not in redirect:
            print('REDIRECT ERROR: redirect is not an absolute url ' +
                  redirect)

        self.send_response(303)
        self.send_header('Set-Cookie', 'epicyon=; SameSite=Strict')
        self.send_header('Location', self._quoted_redirect(redirect))
        self.send_header('Host', calling_domain)
        self.send_header('X-AP-Instance-ID', self.server.instance_id)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _set_headers_base(self, fileFormat: str, length: int, cookie: str,
                          calling_domain: str, permissive: bool) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        if 'image/' in fileFormat or \
           'audio/' in fileFormat or \
           'video/' in fileFormat:
            cache_control = 'public, max-age=84600, immutable'
            self.send_header('Cache-Control', cache_control)
        else:
            self.send_header('Cache-Control', 'public')
        self.send_header('Origin', self.server.domain_full)
        if length > -1:
            self.send_header('Content-Length', str(length))
        if calling_domain:
            self.send_header('Host', calling_domain)
        if permissive:
            self.send_header('Access-Control-Allow-Origin', '*')
            return
        self.send_header('X-AP-Instance-ID', self.server.instance_id)
        self.send_header('X-Clacks-Overhead', 'GNU Natalie Nguyen')
        if cookie:
            cookieStr = cookie
            if 'HttpOnly;' not in cookieStr:
                if self.server.http_prefix == 'https':
                    cookieStr += '; Secure'
                cookieStr += '; HttpOnly; SameSite=Strict'
            self.send_header('Cookie', cookieStr)

    def _set_headers(self, fileFormat: str, length: int, cookie: str,
                     calling_domain: str, permissive: bool) -> None:
        self._set_headers_base(fileFormat, length, cookie, calling_domain,
                               permissive)
        self.end_headers()

    def _set_headers_head(self, fileFormat: str, length: int, etag: str,
                          calling_domain: str, permissive: bool) -> None:
        self._set_headers_base(fileFormat, length, None, calling_domain,
                               permissive)
        if etag:
            self.send_header('ETag', '"' + etag + '"')
        self.end_headers()

    def _set_headers_etag(self, media_filename: str, fileFormat: str,
                          data, cookie: str, calling_domain: str,
                          permissive: bool, lastModified: str) -> None:
        datalen = len(data)
        self._set_headers_base(fileFormat, datalen, cookie, calling_domain,
                               permissive)
        etag = None
        if os.path.isfile(media_filename + '.etag'):
            try:
                with open(media_filename + '.etag', 'r') as etagFile:
                    etag = etagFile.read()
            except OSError:
                print('EX: _set_headers_etag ' +
                      'unable to read ' + media_filename + '.etag')
        if not etag:
            etag = md5(data).hexdigest()  # nosec
            try:
                with open(media_filename + '.etag', 'w+') as etagFile:
                    etagFile.write(etag)
            except OSError:
                print('EX: _set_headers_etag ' +
                      'unable to write ' + media_filename + '.etag')
        # if etag:
        #     self.send_header('ETag', '"' + etag + '"')
        if lastModified:
            self.send_header('last-modified', lastModified)
        self.end_headers()

    def _etag_exists(self, media_filename: str) -> bool:
        """Does an etag header exist for the given file?
        """
        etagHeader = 'If-None-Match'
        if not self.headers.get(etagHeader):
            etagHeader = 'if-none-match'
            if not self.headers.get(etagHeader):
                etagHeader = 'If-none-match'

        if self.headers.get(etagHeader):
            oldEtag = self.headers[etagHeader].replace('"', '')
            if os.path.isfile(media_filename + '.etag'):
                # load the etag from file
                currEtag = ''
                try:
                    with open(media_filename + '.etag', 'r') as etagFile:
                        currEtag = etagFile.read()
                except OSError:
                    print('EX: _etag_exists unable to read ' +
                          str(media_filename))
                if currEtag and oldEtag == currEtag:
                    # The file has not changed
                    return True
        return False

    def _redirect_headers(self, redirect: str, cookie: str,
                          calling_domain: str) -> None:
        if '://' not in redirect:
            print('REDIRECT ERROR: redirect is not an absolute url ' +
                  redirect)

        self.send_response(303)

        if cookie:
            cookieStr = cookie.replace('SET:', '').strip()
            if 'HttpOnly;' not in cookieStr:
                if self.server.http_prefix == 'https':
                    cookieStr += '; Secure'
                cookieStr += '; HttpOnly; SameSite=Strict'
            if not cookie.startswith('SET:'):
                self.send_header('Cookie', cookieStr)
            else:
                self.send_header('Set-Cookie', cookieStr)
        self.send_header('Location', self._quoted_redirect(redirect))
        self.send_header('Host', calling_domain)
        self.send_header('X-AP-Instance-ID', self.server.instance_id)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _http_return_code(self, httpCode: int, httpDescription: str,
                          longDescription: str) -> None:
        msg = \
            '<html><head><title>' + str(httpCode) + '</title></head>' \
            '<body bgcolor="linen" text="black">' \
            '<div style="font-size: 400px; ' \
            'text-align: center;">' + str(httpCode) + '</div>' \
            '<div style="font-size: 128px; ' \
            'text-align: center; font-variant: ' \
            'small-caps;"><p role="alert">' + httpDescription + '</p></div>' \
            '<div style="text-align: center;">' + longDescription + '</div>' \
            '</body></html>'
        msg = msg.encode('utf-8')
        self.send_response(httpCode)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        msgLenStr = str(len(msg))
        self.send_header('Content-Length', msgLenStr)
        self.end_headers()
        if not self._write(msg):
            print('Error when showing ' + str(httpCode))

    def _200(self) -> None:
        if self.server.translate:
            ok_str = self.server.translate['This is nothing ' +
                                           'less than an utter triumph']
            self._http_return_code(200, self.server.translate['Ok'], ok_str)
        else:
            self._http_return_code(200, 'Ok',
                                   'This is nothing less ' +
                                   'than an utter triumph')

    def _403(self) -> None:
        if self.server.translate:
            self._http_return_code(403, self.server.translate['Forbidden'],
                                   self.server.translate["You're not allowed"])
        else:
            self._http_return_code(403, 'Forbidden',
                                   "You're not allowed")

    def _404(self) -> None:
        if self.server.translate:
            self._http_return_code(404, self.server.translate['Not Found'],
                                   self.server.translate['These are not the ' +
                                                         'droids you are ' +
                                                         'looking for'])
        else:
            self._http_return_code(404, 'Not Found',
                                   'These are not the ' +
                                   'droids you are ' +
                                   'looking for')

    def _304(self) -> None:
        if self.server.translate:
            self._http_return_code(304, self.server.translate['Not changed'],
                                   self.server.translate['The contents of ' +
                                                         'your local cache ' +
                                                         'are up to date'])
        else:
            self._http_return_code(304, 'Not changed',
                                   'The contents of ' +
                                   'your local cache ' +
                                   'are up to date')

    def _400(self) -> None:
        if self.server.translate:
            self._http_return_code(400, self.server.translate['Bad Request'],
                                   self.server.translate['Better luck ' +
                                                         'next time'])
        else:
            self._http_return_code(400, 'Bad Request',
                                   'Better luck next time')

    def _503(self) -> None:
        if self.server.translate:
            busy_str = \
                self.server.translate['The server is busy. ' +
                                      'Please try again later']
            self._http_return_code(503, self.server.translate['Unavailable'],
                                   busy_str)
        else:
            self._http_return_code(503, 'Unavailable',
                                   'The server is busy. Please try again ' +
                                   'later')

    def _write(self, msg) -> bool:
        tries = 0
        while tries < 5:
            try:
                self.wfile.write(msg)
                return True
            except BrokenPipeError as ex:
                if self.server.debug:
                    print('ERROR: _write error ' + str(tries) + ' ' + str(ex))
                break
            except Exception as ex:
                print('ERROR: _write error ' + str(tries) + ' ' + str(ex))
                time.sleep(0.5)
            tries += 1
        return False

    def _has_accept(self, calling_domain: str) -> bool:
        """Do the http headers have an Accept field?
        """
        if not self.headers.get('Accept'):
            if self.headers.get('accept'):
                print('Upper case Accept')
                self.headers['Accept'] = self.headers['accept']

        if self.headers.get('Accept') or calling_domain.endswith('.b32.i2p'):
            if not self.headers.get('Accept'):
                self.headers['Accept'] = \
                    'text/html,application/xhtml+xml,' \
                    'application/xml;q=0.9,image/webp,*/*;q=0.8'
            return True
        return False

    def _masto_api_v1(self, path: str, calling_domain: str,
                      ua_str: str,
                      authorized: bool,
                      http_prefix: str,
                      base_dir: str, nickname: str, domain: str,
                      domain_full: str,
                      onion_domain: str, i2p_domain: str,
                      translate: {},
                      registration: bool,
                      system_language: str,
                      project_version: str,
                      customEmoji: [],
                      show_node_info_accounts: bool) -> bool:
        """This is a vestigil mastodon API for the purpose
        of returning an empty result to sites like
        https://mastopeek.app-dist.eu
        """
        if not path.startswith('/api/v1/'):
            return False
        print('mastodon api v1: ' + path)
        print('mastodon api v1: authorized ' + str(authorized))
        print('mastodon api v1: nickname ' + str(nickname))
        self._update_known_crawlers(ua_str)

        broch_mode = broch_mode_is_active(base_dir)
        sendJson, sendJsonStr = \
            masto_api_v1_response(path,
                                  calling_domain,
                                  ua_str,
                                  authorized,
                                  http_prefix,
                                  base_dir,
                                  nickname, domain,
                                  domain_full,
                                  onion_domain,
                                  i2p_domain,
                                  translate,
                                  registration,
                                  system_language,
                                  project_version,
                                  customEmoji,
                                  show_node_info_accounts,
                                  broch_mode)

        if sendJson is not None:
            msg = json.dumps(sendJson).encode('utf-8')
            msglen = len(msg)
            if self._has_accept(calling_domain):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json', msglen,
                                      None, calling_domain, True)
                else:
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, True)
            else:
                self._set_headers('application/ld+json', msglen,
                                  None, calling_domain, True)
            self._write(msg)
            if sendJsonStr:
                print(sendJsonStr)
            return True

        # no api endpoints were matched
        self._404()
        return True

    def _masto_api(self, path: str, calling_domain: str,
                   ua_str: str,
                   authorized: bool, http_prefix: str,
                   base_dir: str, nickname: str, domain: str,
                   domain_full: str,
                   onion_domain: str, i2p_domain: str,
                   translate: {},
                   registration: bool,
                   system_language: str,
                   project_version: str,
                   customEmoji: [],
                   show_node_info_accounts: bool) -> bool:
        return self._masto_api_v1(path, calling_domain, ua_str, authorized,
                                  http_prefix, base_dir, nickname, domain,
                                  domain_full, onion_domain, i2p_domain,
                                  translate, registration, system_language,
                                  project_version, customEmoji,
                                  show_node_info_accounts)

    def _nodeinfo(self, ua_str: str, calling_domain: str) -> bool:
        if not self.path.startswith('/nodeinfo/2.0'):
            return False
        if self.server.debug:
            print('DEBUG: nodeinfo ' + self.path)
        self._update_known_crawlers(ua_str)

        # If we are in broch mode then don't show potentially
        # sensitive metadata.
        # For example, if this or allied instances are being attacked
        # then numbers of accounts may be changing as people
        # migrate, and that information may be useful to an adversary
        broch_mode = broch_mode_is_active(self.server.base_dir)

        nodeInfoVersion = self.server.project_version
        if not self.server.show_node_info_version or broch_mode:
            nodeInfoVersion = '0.0.0'

        show_node_info_accounts = self.server.show_node_info_accounts
        if broch_mode:
            show_node_info_accounts = False

        instance_url = self._get_instance_url(calling_domain)
        aboutUrl = instance_url + '/about'
        termsOfServiceUrl = instance_url + '/terms'
        info = meta_data_node_info(self.server.base_dir,
                                   aboutUrl, termsOfServiceUrl,
                                   self.server.registration,
                                   nodeInfoVersion,
                                   show_node_info_accounts)
        if info:
            msg = json.dumps(info).encode('utf-8')
            msglen = len(msg)
            if self._has_accept(calling_domain):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json', msglen,
                                      None, calling_domain, True)
                else:
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, True)
            else:
                self._set_headers('application/ld+json', msglen,
                                  None, calling_domain, True)
            self._write(msg)
            print('nodeinfo sent to ' + calling_domain)
            return True
        self._404()
        return True

    def _webfinger(self, calling_domain: str) -> bool:
        if not self.path.startswith('/.well-known'):
            return False
        if self.server.debug:
            print('DEBUG: WEBFINGER well-known')

        if self.server.debug:
            print('DEBUG: WEBFINGER host-meta')
        if self.path.startswith('/.well-known/host-meta'):
            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                wfResult = \
                    webfinger_meta('http', self.server.onion_domain)
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                wfResult = \
                    webfinger_meta('http', self.server.i2p_domain)
            else:
                wfResult = \
                    webfinger_meta(self.server.http_prefix,
                                   self.server.domain_full)
            if wfResult:
                msg = wfResult.encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/xrd+xml', msglen,
                                  None, calling_domain, True)
                self._write(msg)
                return True
            self._404()
            return True
        if self.path.startswith('/api/statusnet') or \
           self.path.startswith('/api/gnusocial') or \
           self.path.startswith('/siteinfo') or \
           self.path.startswith('/poco') or \
           self.path.startswith('/friendi'):
            self._404()
            return True
        if self.path.startswith('/.well-known/nodeinfo') or \
           self.path.startswith('/.well-known/x-nodeinfo'):
            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                wfResult = \
                    webfinger_node_info('http', self.server.onion_domain)
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                wfResult = \
                    webfinger_node_info('http', self.server.i2p_domain)
            else:
                wfResult = \
                    webfinger_node_info(self.server.http_prefix,
                                        self.server.domain_full)
            if wfResult:
                msg = json.dumps(wfResult).encode('utf-8')
                msglen = len(msg)
                if self._has_accept(calling_domain):
                    if 'application/ld+json' in self.headers['Accept']:
                        self._set_headers('application/ld+json', msglen,
                                          None, calling_domain, True)
                    else:
                        self._set_headers('application/json', msglen,
                                          None, calling_domain, True)
                else:
                    self._set_headers('application/ld+json', msglen,
                                      None, calling_domain, True)
                self._write(msg)
                return True
            self._404()
            return True

        if self.server.debug:
            print('DEBUG: WEBFINGER lookup ' + self.path + ' ' +
                  str(self.server.base_dir))
        wfResult = \
            webfinger_lookup(self.path, self.server.base_dir,
                             self.server.domain, self.server.onion_domain,
                             self.server.port, self.server.debug)
        if wfResult:
            msg = json.dumps(wfResult).encode('utf-8')
            msglen = len(msg)
            self._set_headers('application/jrd+json', msglen,
                              None, calling_domain, True)
            self._write(msg)
        else:
            if self.server.debug:
                print('DEBUG: WEBFINGER lookup 404 ' + self.path)
            self._404()
        return True

    def _post_to_outbox(self, message_json: {}, version: str,
                        post_to_nickname: str) -> bool:
        """post is received by the outbox
        Client to server message post
        https://www.w3.org/TR/activitypub/#client-to-server-outbox-delivery
        """
        city = self.server.city

        if post_to_nickname:
            print('Posting to nickname ' + post_to_nickname)
            self.post_to_nickname = post_to_nickname
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    post_to_nickname, self.server.domain)

        shared_items_federated_domains = \
            self.server.shared_items_federated_domains
        return post_message_to_outbox(self.server.session,
                                      self.server.translate,
                                      message_json, self.post_to_nickname,
                                      self.server, self.server.base_dir,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.domain_full,
                                      self.server.onion_domain,
                                      self.server.i2p_domain,
                                      self.server.port,
                                      self.server.recent_posts_cache,
                                      self.server.followers_threads,
                                      self.server.federation_list,
                                      self.server.send_threads,
                                      self.server.postLog,
                                      self.server.cached_webfingers,
                                      self.server.person_cache,
                                      self.server.allow_deletion,
                                      self.server.proxy_type, version,
                                      self.server.debug,
                                      self.server.yt_replace_domain,
                                      self.server.twitter_replacement_domain,
                                      self.server.show_published_date_only,
                                      self.server.allow_local_network_access,
                                      city, self.server.system_language,
                                      shared_items_federated_domains,
                                      self.server.sharedItemFederationTokens,
                                      self.server.low_bandwidth,
                                      self.server.signing_priv_key_pem,
                                      self.server.peertube_instances,
                                      self.server.theme_name,
                                      self.server.max_like_count,
                                      self.server.max_recent_posts,
                                      self.server.cw_lists,
                                      self.server.lists_enabled,
                                      self.server.content_license_url)

    def _get_outbox_thread_index(self, nickname: str,
                                 maxOutboxThreadsPerAccount: int) -> int:
        """Returns the outbox thread index for the given account
        This is a ring buffer used to store the thread objects which
        are sending out posts
        """
        accountOutboxThreadName = nickname
        if not accountOutboxThreadName:
            accountOutboxThreadName = '*'

        # create the buffer for the given account
        if not self.server.outboxThread.get(accountOutboxThreadName):
            self.server.outboxThread[accountOutboxThreadName] = \
                [None] * maxOutboxThreadsPerAccount
            self.server.outbox_thread_index[accountOutboxThreadName] = 0
            return 0

        # increment the ring buffer index
        index = self.server.outbox_thread_index[accountOutboxThreadName] + 1
        if index >= maxOutboxThreadsPerAccount:
            index = 0

        self.server.outbox_thread_index[accountOutboxThreadName] = index

        # remove any existing thread from the current index in the buffer
        if self.server.outboxThread.get(accountOutboxThreadName):
            acct = accountOutboxThreadName
            if self.server.outboxThread[acct][index].is_alive():
                self.server.outboxThread[acct][index].kill()
        return index

    def _post_to_outbox_thread(self, message_json: {}) -> bool:
        """Creates a thread to send a post
        """
        accountOutboxThreadName = self.post_to_nickname
        if not accountOutboxThreadName:
            accountOutboxThreadName = '*'

        index = self._get_outbox_thread_index(accountOutboxThreadName, 8)

        print('Creating outbox thread ' +
              accountOutboxThreadName + '/' +
              str(self.server.outbox_thread_index[accountOutboxThreadName]))
        self.server.outboxThread[accountOutboxThreadName][index] = \
            thread_with_trace(target=self._post_to_outbox,
                              args=(message_json.copy(),
                                    self.server.project_version, None),
                              daemon=True)
        print('Starting outbox thread')
        self.server.outboxThread[accountOutboxThreadName][index].start()
        return True

    def _update_inbox_queue(self, nickname: str, message_json: {},
                            messageBytes: str) -> int:
        """Update the inbox queue
        """
        if self.server.restartInboxQueueInProgress:
            self._503()
            print('Message arrived but currently restarting inbox queue')
            self.server.POSTbusy = False
            return 2

        # check that the incoming message has a fully recognized
        # linked data context
        if not has_valid_context(message_json):
            print('Message arriving at inbox queue has no valid context')
            self._400()
            self.server.POSTbusy = False
            return 3

        # check for blocked domains so that they can be rejected early
        messageDomain = None
        if not has_actor(message_json, self.server.debug):
            print('Message arriving at inbox queue has no actor')
            self._400()
            self.server.POSTbusy = False
            return 3

        # actor should be a string
        if not isinstance(message_json['actor'], str):
            self._400()
            self.server.POSTbusy = False
            return 3

        # check that some additional fields are strings
        stringFields = ('id', 'type', 'published')
        for checkField in stringFields:
            if not message_json.get(checkField):
                continue
            if not isinstance(message_json[checkField], str):
                self._400()
                self.server.POSTbusy = False
                return 3

        # check that to/cc fields are lists
        listFields = ('to', 'cc')
        for checkField in listFields:
            if not message_json.get(checkField):
                continue
            if not isinstance(message_json[checkField], list):
                self._400()
                self.server.POSTbusy = False
                return 3

        if has_object_dict(message_json):
            stringFields = (
                'id', 'actor', 'type', 'content', 'published',
                'summary', 'url', 'attributedTo'
            )
            for checkField in stringFields:
                if not message_json['object'].get(checkField):
                    continue
                if not isinstance(message_json['object'][checkField], str):
                    self._400()
                    self.server.POSTbusy = False
                    return 3
            # check that some fields are lists
            listFields = ('to', 'cc', 'attachment')
            for checkField in listFields:
                if not message_json['object'].get(checkField):
                    continue
                if not isinstance(message_json['object'][checkField], list):
                    self._400()
                    self.server.POSTbusy = False
                    return 3

        # actor should look like a url
        if '://' not in message_json['actor'] or \
           '.' not in message_json['actor']:
            print('POST actor does not look like a url ' +
                  message_json['actor'])
            self._400()
            self.server.POSTbusy = False
            return 3

        # sent by an actor on a local network address?
        if not self.server.allow_local_network_access:
            localNetworkPatternList = get_local_network_addresses()
            for localNetworkPattern in localNetworkPatternList:
                if localNetworkPattern in message_json['actor']:
                    print('POST actor contains local network address ' +
                          message_json['actor'])
                    self._400()
                    self.server.POSTbusy = False
                    return 3

        messageDomain, messagePort = \
            get_domain_from_actor(message_json['actor'])

        self.server.blocked_cache_last_updated = \
            update_blocked_cache(self.server.base_dir,
                                 self.server.blocked_cache,
                                 self.server.blocked_cache_last_updated,
                                 self.server.blocked_cache_update_secs)

        if is_blocked_domain(self.server.base_dir, messageDomain,
                             self.server.blocked_cache):
            print('POST from blocked domain ' + messageDomain)
            self._400()
            self.server.POSTbusy = False
            return 3

        # if the inbox queue is full then return a busy code
        if len(self.server.inbox_queue) >= self.server.max_queue_length:
            if messageDomain:
                print('Queue: Inbox queue is full. Incoming post from ' +
                      message_json['actor'])
            else:
                print('Queue: Inbox queue is full')
            self._503()
            clear_queue_items(self.server.base_dir, self.server.inbox_queue)
            if not self.server.restartInboxQueueInProgress:
                self.server.restartInboxQueue = True
            self.server.POSTbusy = False
            return 2

        # Convert the headers needed for signature verification to dict
        headersDict = {}
        headersDict['host'] = self.headers['host']
        headersDict['signature'] = self.headers['signature']
        if self.headers.get('Date'):
            headersDict['Date'] = self.headers['Date']
        elif self.headers.get('date'):
            headersDict['Date'] = self.headers['date']
        if self.headers.get('digest'):
            headersDict['digest'] = self.headers['digest']
        if self.headers.get('Collection-Synchronization'):
            headersDict['Collection-Synchronization'] = \
                self.headers['Collection-Synchronization']
        if self.headers.get('Content-type'):
            headersDict['Content-type'] = self.headers['Content-type']
        if self.headers.get('Content-Length'):
            headersDict['Content-Length'] = self.headers['Content-Length']
        elif self.headers.get('content-length'):
            headersDict['content-length'] = self.headers['content-length']

        originalMessageJson = message_json.copy()

        # whether to add a 'to' field to the message
        add_to_fieldTypes = (
            'Follow', 'Like', 'EmojiReact', 'Add', 'Remove', 'Ignore'
        )
        for addToType in add_to_fieldTypes:
            message_json, toFieldExists = \
                add_to_field(addToType, message_json, self.server.debug)

        beginSaveTime = time.time()
        # save the json for later queue processing
        messageBytesDecoded = messageBytes.decode('utf-8')

        if contains_invalid_local_links(messageBytesDecoded):
            print('WARN: post contains invalid local links ' +
                  str(originalMessageJson))
            return 5

        self.server.blocked_cache_last_updated = \
            update_blocked_cache(self.server.base_dir,
                                 self.server.blocked_cache,
                                 self.server.blocked_cache_last_updated,
                                 self.server.blocked_cache_update_secs)

        queueFilename = \
            save_post_to_inbox_queue(self.server.base_dir,
                                     self.server.http_prefix,
                                     nickname,
                                     self.server.domain_full,
                                     message_json, originalMessageJson,
                                     messageBytesDecoded,
                                     headersDict,
                                     self.path,
                                     self.server.debug,
                                     self.server.blocked_cache,
                                     self.server.system_language)
        if queueFilename:
            # add json to the queue
            if queueFilename not in self.server.inbox_queue:
                self.server.inbox_queue.append(queueFilename)
            if self.server.debug:
                time_diff = int((time.time() - beginSaveTime) * 1000)
                if time_diff > 200:
                    print('SLOW: slow save of inbox queue item ' +
                          queueFilename + ' took ' + str(time_diff) + ' mS')
            self.send_response(201)
            self.end_headers()
            self.server.POSTbusy = False
            return 0
        self._503()
        self.server.POSTbusy = False
        return 1

    def _is_authorized(self) -> bool:
        self.authorizedNickname = None

        notAuthPaths = (
            '/icons/', '/avatars/', '/favicons/',
            '/system/accounts/avatars/',
            '/system/accounts/headers/',
            '/system/media_attachments/files/',
            '/accounts/avatars/', '/accounts/headers/',
            '/favicon.ico', '/newswire.xml',
            '/newswire_favicon.ico', '/categories.xml'
        )
        for notAuthStr in notAuthPaths:
            if self.path.startswith(notAuthStr):
                return False

        # token based authenticated used by the web interface
        if self.headers.get('Cookie'):
            if self.headers['Cookie'].startswith('epicyon='):
                tokenStr = self.headers['Cookie'].split('=', 1)[1].strip()
                if ';' in tokenStr:
                    tokenStr = tokenStr.split(';')[0].strip()
                if self.server.tokens_lookup.get(tokenStr):
                    nickname = self.server.tokens_lookup[tokenStr]
                    if not is_system_account(nickname):
                        self.authorizedNickname = nickname
                        # default to the inbox of the person
                        if self.path == '/':
                            self.path = '/users/' + nickname + '/inbox'
                        # check that the path contains the same nickname
                        # as the cookie otherwise it would be possible
                        # to be authorized to use an account you don't own
                        if '/' + nickname + '/' in self.path:
                            return True
                        elif '/' + nickname + '?' in self.path:
                            return True
                        elif self.path.endswith('/' + nickname):
                            return True
                        if self.server.debug:
                            print('AUTH: nickname ' + nickname +
                                  ' was not found in path ' + self.path)
                    return False
                print('AUTH: epicyon cookie ' +
                      'authorization failed, header=' +
                      self.headers['Cookie'].replace('epicyon=', '') +
                      ' tokenStr=' + tokenStr + ' tokens=' +
                      str(self.server.tokens_lookup))
                return False
            print('AUTH: Header cookie was not authorized')
            return False
        # basic auth for c2s
        if self.headers.get('Authorization'):
            if authorize(self.server.base_dir, self.path,
                         self.headers['Authorization'],
                         self.server.debug):
                return True
            print('AUTH: C2S Basic auth did not authorize ' +
                  self.headers['Authorization'])
        return False

    def _clear_login_details(self, nickname: str, calling_domain: str) -> None:
        """Clears login details for the given account
        """
        # remove any token
        if self.server.tokens.get(nickname):
            del self.server.tokens_lookup[self.server.tokens[nickname]]
            del self.server.tokens[nickname]
        self._redirect_headers(self.server.http_prefix + '://' +
                               self.server.domain_full + '/login',
                               'epicyon=; SameSite=Strict',
                               calling_domain)

    def _show_login_screen(self, path: str, calling_domain: str, cookie: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domain_full: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           debug: bool) -> None:
        """Shows the login screen
        """
        # ensure that there is a minimum delay between failed login
        # attempts, to mitigate brute force
        if int(time.time()) - self.server.last_login_failure < 5:
            self._503()
            self.server.POSTbusy = False
            return

        # get the contents of POST containing login credentials
        length = int(self.headers['Content-length'])
        if length > 512:
            print('Login failed - credentials too long')
            self.send_response(401)
            self.end_headers()
            self.server.POSTbusy = False
            return

        try:
            loginParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST login read ' +
                      'connection reset by peer')
            else:
                print('WARN: POST login read socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST login read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        loginNickname, loginPassword, register = \
            html_get_login_credentials(loginParams,
                                       self.server.last_login_time,
                                       self.server.domain)
        if loginNickname:
            if is_system_account(loginNickname):
                print('Invalid username login: ' + loginNickname +
                      ' (system account)')
                self._clear_login_details(loginNickname, calling_domain)
                self.server.POSTbusy = False
                return
            self.server.last_login_time = int(time.time())
            if register:
                if not valid_password(loginPassword):
                    self.server.POSTbusy = False
                    if calling_domain.endswith('.onion') and onion_domain:
                        self._redirect_headers('http://' + onion_domain +
                                               '/login', cookie,
                                               calling_domain)
                    elif (calling_domain.endswith('.i2p') and i2p_domain):
                        self._redirect_headers('http://' + i2p_domain +
                                               '/login', cookie,
                                               calling_domain)
                    else:
                        self._redirect_headers(http_prefix + '://' +
                                               domain_full + '/login',
                                               cookie, calling_domain)
                    return

                if not register_account(base_dir, http_prefix, domain, port,
                                        loginNickname, loginPassword,
                                        self.server.manual_follower_approval):
                    self.server.POSTbusy = False
                    if calling_domain.endswith('.onion') and onion_domain:
                        self._redirect_headers('http://' + onion_domain +
                                               '/login', cookie,
                                               calling_domain)
                    elif (calling_domain.endswith('.i2p') and i2p_domain):
                        self._redirect_headers('http://' + i2p_domain +
                                               '/login', cookie,
                                               calling_domain)
                    else:
                        self._redirect_headers(http_prefix + '://' +
                                               domain_full + '/login',
                                               cookie, calling_domain)
                    return
            authHeader = \
                create_basic_auth_header(loginNickname, loginPassword)
            if self.headers.get('X-Forward-For'):
                ipAddress = self.headers['X-Forward-For']
            elif self.headers.get('X-Forwarded-For'):
                ipAddress = self.headers['X-Forwarded-For']
            else:
                ipAddress = self.client_address[0]
            if not domain.endswith('.onion'):
                if not is_local_network_address(ipAddress):
                    print('Login attempt from IP: ' + str(ipAddress))
            if not authorize_basic(base_dir, '/users/' +
                                   loginNickname + '/outbox',
                                   authHeader, False):
                print('Login failed: ' + loginNickname)
                self._clear_login_details(loginNickname, calling_domain)
                failTime = int(time.time())
                self.server.last_login_failure = failTime
                if not domain.endswith('.onion'):
                    if not is_local_network_address(ipAddress):
                        record_login_failure(base_dir, ipAddress,
                                             self.server.login_failure_count,
                                             failTime,
                                             self.server.log_login_failures)
                self.server.POSTbusy = False
                return
            else:
                if self.server.login_failure_count.get(ipAddress):
                    del self.server.login_failure_count[ipAddress]
                if is_suspended(base_dir, loginNickname):
                    msg = \
                        html_suspended(self.server.css_cache,
                                       base_dir).encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                # login success - redirect with authorization
                print('Login success: ' + loginNickname)
                # re-activate account if needed
                activate_account(base_dir, loginNickname, domain)
                # This produces a deterministic token based
                # on nick+password+salt
                saltFilename = \
                    acct_dir(base_dir, loginNickname, domain) + '/.salt'
                salt = create_password(32)
                if os.path.isfile(saltFilename):
                    try:
                        with open(saltFilename, 'r') as fp:
                            salt = fp.read()
                    except OSError as ex:
                        print('EX: Unable to read salt for ' +
                              loginNickname + ' ' + str(ex))
                else:
                    try:
                        with open(saltFilename, 'w+') as fp:
                            fp.write(salt)
                    except OSError as ex:
                        print('EX: Unable to save salt for ' +
                              loginNickname + ' ' + str(ex))

                tokenText = loginNickname + loginPassword + salt
                token = sha256(tokenText.encode('utf-8')).hexdigest()
                self.server.tokens[loginNickname] = token
                loginHandle = loginNickname + '@' + domain
                tokenFilename = \
                    base_dir + '/accounts/' + \
                    loginHandle + '/.token'
                try:
                    with open(tokenFilename, 'w+') as fp:
                        fp.write(token)
                except OSError as ex:
                    print('EX: Unable to save token for ' +
                          loginNickname + ' ' + str(ex))

                person_upgrade_actor(base_dir, None, loginHandle,
                                     base_dir + '/accounts/' +
                                     loginHandle + '.json')

                index = self.server.tokens[loginNickname]
                self.server.tokens_lookup[index] = loginNickname
                cookieStr = 'SET:epicyon=' + \
                    self.server.tokens[loginNickname] + '; SameSite=Strict'
                if calling_domain.endswith('.onion') and onion_domain:
                    self._redirect_headers('http://' +
                                           onion_domain +
                                           '/users/' +
                                           loginNickname + '/' +
                                           self.server.default_timeline,
                                           cookieStr, calling_domain)
                elif (calling_domain.endswith('.i2p') and i2p_domain):
                    self._redirect_headers('http://' +
                                           i2p_domain +
                                           '/users/' +
                                           loginNickname + '/' +
                                           self.server.default_timeline,
                                           cookieStr, calling_domain)
                else:
                    self._redirect_headers(http_prefix + '://' +
                                           domain_full + '/users/' +
                                           loginNickname + '/' +
                                           self.server.default_timeline,
                                           cookieStr, calling_domain)
                self.server.POSTbusy = False
                return
        self._200()
        self.server.POSTbusy = False

    def _moderator_actions(self, path: str, calling_domain: str, cookie: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domain_full: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           debug: bool) -> None:
        """Actions on the moderator screen
        """
        usersPath = path.replace('/moderationaction', '')
        nickname = usersPath.replace('/users/', '')
        actorStr = self._get_instance_url(calling_domain) + usersPath
        if not is_moderator(self.server.base_dir, nickname):
            self._redirect_headers(actorStr + '/moderation',
                                   cookie, calling_domain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            moderationParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST moderationParams connection was reset')
            else:
                print('WARN: POST moderationParams ' +
                      'rfile.read socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST moderationParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&' in moderationParams:
            moderationText = None
            moderationButton = None
            for moderationStr in moderationParams.split('&'):
                if moderationStr.startswith('moderationAction'):
                    if '=' in moderationStr:
                        moderationText = \
                            moderationStr.split('=')[1].strip()
                        modText = moderationText.replace('+', ' ')
                        moderationText = \
                            urllib.parse.unquote_plus(modText.strip())
                elif moderationStr.startswith('submitInfo'):
                    searchHandle = moderationText
                    if searchHandle:
                        if '/@' in searchHandle:
                            searchNickname = \
                                get_nickname_from_actor(searchHandle)
                            searchDomain, searchPort = \
                                get_domain_from_actor(searchHandle)
                            searchHandle = \
                                searchNickname + '@' + searchDomain
                        if '@' not in searchHandle:
                            if searchHandle.startswith('http'):
                                searchNickname = \
                                    get_nickname_from_actor(searchHandle)
                                searchDomain, searchPort = \
                                    get_domain_from_actor(searchHandle)
                                searchHandle = \
                                    searchNickname + '@' + searchDomain
                        if '@' not in searchHandle:
                            # is this a local nickname on this instance?
                            localHandle = \
                                searchHandle + '@' + self.server.domain
                            if os.path.isdir(self.server.base_dir +
                                             '/accounts/' + localHandle):
                                searchHandle = localHandle
                            else:
                                searchHandle = None
                    if searchHandle:
                        msg = \
                            html_account_info(self.server.css_cache,
                                              self.server.translate,
                                              base_dir, http_prefix,
                                              nickname,
                                              self.server.domain,
                                              self.server.port,
                                              searchHandle,
                                              self.server.debug,
                                              self.server.system_language,
                                              self.server.signing_priv_key_pem)
                    else:
                        msg = \
                            html_moderation_info(self.server.css_cache,
                                                 self.server.translate,
                                                 base_dir, http_prefix,
                                                 nickname)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                elif moderationStr.startswith('submitBlock'):
                    moderationButton = 'block'
                elif moderationStr.startswith('submitUnblock'):
                    moderationButton = 'unblock'
                elif moderationStr.startswith('submitFilter'):
                    moderationButton = 'filter'
                elif moderationStr.startswith('submitUnfilter'):
                    moderationButton = 'unfilter'
                elif moderationStr.startswith('submitSuspend'):
                    moderationButton = 'suspend'
                elif moderationStr.startswith('submitUnsuspend'):
                    moderationButton = 'unsuspend'
                elif moderationStr.startswith('submitRemove'):
                    moderationButton = 'remove'
            if moderationButton and moderationText:
                if debug:
                    print('moderationButton: ' + moderationButton)
                    print('moderationText: ' + moderationText)
                nickname = moderationText
                if nickname.startswith('http') or \
                   nickname.startswith('hyper'):
                    nickname = get_nickname_from_actor(nickname)
                if '@' in nickname:
                    nickname = nickname.split('@')[0]
                if moderationButton == 'suspend':
                    suspend_account(base_dir, nickname, domain)
                if moderationButton == 'unsuspend':
                    reenable_account(base_dir, nickname)
                if moderationButton == 'filter':
                    add_global_filter(base_dir, moderationText)
                if moderationButton == 'unfilter':
                    remove_global_filter(base_dir, moderationText)
                if moderationButton == 'block':
                    fullBlockDomain = None
                    if moderationText.startswith('http') or \
                       moderationText.startswith('hyper'):
                        # https://domain
                        block_domain, blockPort = \
                            get_domain_from_actor(moderationText)
                        fullBlockDomain = \
                            get_full_domain(block_domain, blockPort)
                    if '@' in moderationText:
                        # nick@domain or *@domain
                        fullBlockDomain = moderationText.split('@')[1]
                    else:
                        # assume the text is a domain name
                        if not fullBlockDomain and '.' in moderationText:
                            nickname = '*'
                            fullBlockDomain = moderationText.strip()
                    if fullBlockDomain or nickname.startswith('#'):
                        add_global_block(base_dir, nickname, fullBlockDomain)
                if moderationButton == 'unblock':
                    fullBlockDomain = None
                    if moderationText.startswith('http') or \
                       moderationText.startswith('hyper'):
                        # https://domain
                        block_domain, blockPort = \
                            get_domain_from_actor(moderationText)
                        fullBlockDomain = \
                            get_full_domain(block_domain, blockPort)
                    if '@' in moderationText:
                        # nick@domain or *@domain
                        fullBlockDomain = moderationText.split('@')[1]
                    else:
                        # assume the text is a domain name
                        if not fullBlockDomain and '.' in moderationText:
                            nickname = '*'
                            fullBlockDomain = moderationText.strip()
                    if fullBlockDomain or nickname.startswith('#'):
                        remove_global_block(base_dir, nickname,
                                            fullBlockDomain)
                if moderationButton == 'remove':
                    if '/statuses/' not in moderationText:
                        remove_account(base_dir, nickname, domain, port)
                    else:
                        # remove a post or thread
                        post_filename = \
                            locate_post(base_dir, nickname, domain,
                                        moderationText)
                        if post_filename:
                            if can_remove_post(base_dir,
                                               nickname, domain, port,
                                               moderationText):
                                delete_post(base_dir,
                                            http_prefix,
                                            nickname, domain,
                                            post_filename,
                                            debug,
                                            self.server.recent_posts_cache)
                        if nickname != 'news':
                            # if this is a local blog post then also remove it
                            # from the news actor
                            post_filename = \
                                locate_post(base_dir, 'news', domain,
                                            moderationText)
                            if post_filename:
                                if can_remove_post(base_dir,
                                                   'news', domain, port,
                                                   moderationText):
                                    delete_post(base_dir,
                                                http_prefix,
                                                'news', domain,
                                                post_filename,
                                                debug,
                                                self.server.recent_posts_cache)

        self._redirect_headers(actorStr + '/moderation',
                               cookie, calling_domain)
        self.server.POSTbusy = False
        return

    def _key_shortcuts(self, path: str,
                       calling_domain: str, cookie: str,
                       base_dir: str, http_prefix: str, nickname: str,
                       domain: str, domain_full: str, port: int,
                       onion_domain: str, i2p_domain: str,
                       debug: bool, access_keys: {},
                       default_timeline: str) -> None:
        """Receive POST from webapp_accesskeys
        """
        usersPath = '/users/' + nickname
        originPathStr = \
            http_prefix + '://' + domain_full + usersPath + '/' + \
            default_timeline
        length = int(self.headers['Content-length'])

        try:
            access_keys_params = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST access_keys_params ' +
                      'connection reset by peer')
            else:
                print('WARN: POST access_keys_params socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST access_keys_params rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        access_keys_params = \
            urllib.parse.unquote_plus(access_keys_params)

        # key shortcuts screen, back button
        # See html_access_keys
        if 'submitAccessKeysCancel=' in access_keys_params or \
           'submitAccessKeys=' not in access_keys_params:
            if calling_domain.endswith('.onion') and onion_domain:
                originPathStr = \
                    'http://' + onion_domain + usersPath + '/' + \
                    default_timeline
            elif calling_domain.endswith('.i2p') and i2p_domain:
                originPathStr = \
                    'http://' + i2p_domain + usersPath + '/' + default_timeline
            self._redirect_headers(originPathStr, cookie, calling_domain)
            self.server.POSTbusy = False
            return

        saveKeys = False
        access_keysTemplate = self.server.access_keys
        for variableName, key in access_keysTemplate.items():
            if not access_keys.get(variableName):
                access_keys[variableName] = access_keysTemplate[variableName]

            variableName2 = variableName.replace(' ', '_')
            if variableName2 + '=' in access_keys_params:
                newKey = access_keys_params.split(variableName2 + '=')[1]
                if '&' in newKey:
                    newKey = newKey.split('&')[0]
                if newKey:
                    if len(newKey) > 1:
                        newKey = newKey[0]
                    if newKey != access_keys[variableName]:
                        access_keys[variableName] = newKey
                        saveKeys = True

        if saveKeys:
            access_keysFilename = \
                acct_dir(base_dir, nickname, domain) + '/access_keys.json'
            save_json(access_keys, access_keysFilename)
            if not self.server.keyShortcuts.get(nickname):
                self.server.keyShortcuts[nickname] = access_keys.copy()

        # redirect back from key shortcuts screen
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = \
                'http://' + onion_domain + usersPath + '/' + default_timeline
        elif calling_domain.endswith('.i2p') and i2p_domain:
            originPathStr = \
                'http://' + i2p_domain + usersPath + '/' + default_timeline
        self._redirect_headers(originPathStr, cookie, calling_domain)
        self.server.POSTbusy = False
        return

    def _theme_designer_edit(self, path: str,
                             calling_domain: str, cookie: str,
                             base_dir: str, http_prefix: str, nickname: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             debug: bool, access_keys: {},
                             default_timeline: str, theme_name: str,
                             allow_local_network_access: bool,
                             system_language: str) -> None:
        """Receive POST from webapp_theme_designer
        """
        usersPath = '/users/' + nickname
        originPathStr = \
            http_prefix + '://' + domain_full + usersPath + '/' + \
            default_timeline
        length = int(self.headers['Content-length'])

        try:
            themeParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST themeParams ' +
                      'connection reset by peer')
            else:
                print('WARN: POST themeParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST themeParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        themeParams = \
            urllib.parse.unquote_plus(themeParams)

        # theme designer screen, reset button
        # See html_theme_designer
        if 'submitThemeDesignerReset=' in themeParams or \
           'submitThemeDesigner=' not in themeParams:
            if 'submitThemeDesignerReset=' in themeParams:
                reset_theme_designer_settings(base_dir, theme_name, domain,
                                              allow_local_network_access,
                                              system_language)
                set_theme(base_dir, theme_name, domain,
                          allow_local_network_access, system_language)

            if calling_domain.endswith('.onion') and onion_domain:
                originPathStr = \
                    'http://' + onion_domain + usersPath + '/' + \
                    default_timeline
            elif calling_domain.endswith('.i2p') and i2p_domain:
                originPathStr = \
                    'http://' + i2p_domain + usersPath + '/' + default_timeline
            self._redirect_headers(originPathStr, cookie, calling_domain)
            self.server.POSTbusy = False
            return

        fields = {}
        fieldsList = themeParams.split('&')
        for fieldStr in fieldsList:
            if '=' not in fieldStr:
                continue
            fieldValue = fieldStr.split('=')[1].strip()
            if not fieldValue:
                continue
            if fieldValue == 'on':
                fieldValue = 'True'
            fields[fieldStr.split('=')[0]] = fieldValue

        # Check for boolean values which are False.
        # These don't come through via themeParams,
        # so need to be checked separately
        themeFilename = base_dir + '/theme/' + theme_name + '/theme.json'
        themeJson = load_json(themeFilename)
        if themeJson:
            for variableName, value in themeJson.items():
                variableName = 'themeSetting_' + variableName
                if value.lower() == 'false' or value.lower() == 'true':
                    if variableName not in fields:
                        fields[variableName] = 'False'

        # get the parameters from the theme designer screen
        themeDesignerParams = {}
        for variableName, key in fields.items():
            if variableName.startswith('themeSetting_'):
                variableName = variableName.replace('themeSetting_', '')
                themeDesignerParams[variableName] = key

        set_theme_from_designer(base_dir, theme_name, domain,
                                themeDesignerParams,
                                allow_local_network_access,
                                system_language)

        # set boolean values
        if 'rss-icon-at-top' in themeDesignerParams:
            if themeDesignerParams['rss-icon-at-top'].lower() == 'true':
                self.server.rss_icon_at_top = True
            else:
                self.server.rss_icon_at_top = False
        if 'publish-button-at-top' in themeDesignerParams:
            if themeDesignerParams['publish-button-at-top'].lower() == 'true':
                self.server.publish_button_at_top = True
            else:
                self.server.publish_button_at_top = False
        if 'newswire-publish-icon' in themeDesignerParams:
            if themeDesignerParams['newswire-publish-icon'].lower() == 'true':
                self.server.show_publish_as_icon = True
            else:
                self.server.show_publish_as_icon = False
        if 'icons-as-buttons' in themeDesignerParams:
            if themeDesignerParams['icons-as-buttons'].lower() == 'true':
                self.server.icons_as_buttons = True
            else:
                self.server.icons_as_buttons = False
        if 'full-width-timeline-buttons' in themeDesignerParams:
            themeValue = themeDesignerParams['full-width-timeline-buttons']
            if themeValue.lower() == 'true':
                self.server.full_width_tl_button_header = True
            else:
                self.server.full_width_tl_button_header = False

        # redirect back from theme designer screen
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = \
                'http://' + onion_domain + usersPath + '/' + default_timeline
        elif calling_domain.endswith('.i2p') and i2p_domain:
            originPathStr = \
                'http://' + i2p_domain + usersPath + '/' + default_timeline
        self._redirect_headers(originPathStr, cookie, calling_domain)
        self.server.POSTbusy = False
        return

    def _person_options(self, path: str,
                        calling_domain: str, cookie: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domain_full: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        debug: bool) -> None:
        """Receive POST from person options screen
        """
        page_number = 1
        usersPath = path.split('/personoptions')[0]
        originPathStr = http_prefix + '://' + domain_full + usersPath

        chooserNickname = get_nickname_from_actor(originPathStr)
        if not chooserNickname:
            if calling_domain.endswith('.onion') and onion_domain:
                originPathStr = 'http://' + onion_domain + usersPath
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                originPathStr = 'http://' + i2p_domain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr, cookie, calling_domain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            optionsConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST optionsConfirmParams ' +
                      'connection reset by peer')
            else:
                print('WARN: POST optionsConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: ' +
                  'POST optionsConfirmParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        optionsConfirmParams = \
            urllib.parse.unquote_plus(optionsConfirmParams)

        # page number to return to
        if 'pageNumber=' in optionsConfirmParams:
            page_number_str = optionsConfirmParams.split('pageNumber=')[1]
            if '&' in page_number_str:
                page_number_str = page_number_str.split('&')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)

        # actor for the person
        optionsActor = optionsConfirmParams.split('actor=')[1]
        if '&' in optionsActor:
            optionsActor = optionsActor.split('&')[0]

        # url of the avatar
        optionsAvatarUrl = optionsConfirmParams.split('avatarUrl=')[1]
        if '&' in optionsAvatarUrl:
            optionsAvatarUrl = optionsAvatarUrl.split('&')[0]

        # link to a post, which can then be included in reports
        postUrl = None
        if 'postUrl' in optionsConfirmParams:
            postUrl = optionsConfirmParams.split('postUrl=')[1]
            if '&' in postUrl:
                postUrl = postUrl.split('&')[0]

        # petname for this person
        petname = None
        if 'optionpetname' in optionsConfirmParams:
            petname = optionsConfirmParams.split('optionpetname=')[1]
            if '&' in petname:
                petname = petname.split('&')[0]
            # Limit the length of the petname
            if len(petname) > 20 or \
               ' ' in petname or '/' in petname or \
               '?' in petname or '#' in petname:
                petname = None

        # notes about this person
        personNotes = None
        if 'optionnotes' in optionsConfirmParams:
            personNotes = optionsConfirmParams.split('optionnotes=')[1]
            if '&' in personNotes:
                personNotes = personNotes.split('&')[0]
            personNotes = urllib.parse.unquote_plus(personNotes.strip())
            # Limit the length of the notes
            if len(personNotes) > 64000:
                personNotes = None

        # get the nickname
        optionsNickname = get_nickname_from_actor(optionsActor)
        if not optionsNickname:
            if calling_domain.endswith('.onion') and onion_domain:
                originPathStr = 'http://' + onion_domain + usersPath
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                originPathStr = 'http://' + i2p_domain + usersPath
            print('WARN: unable to find nickname in ' + optionsActor)
            self._redirect_headers(originPathStr, cookie, calling_domain)
            self.server.POSTbusy = False
            return

        optionsDomain, optionsPort = get_domain_from_actor(optionsActor)
        optionsDomainFull = get_full_domain(optionsDomain, optionsPort)
        if chooserNickname == optionsNickname and \
           optionsDomain == domain and \
           optionsPort == port:
            if debug:
                print('You cannot perform an option action on yourself')

        # person options screen, view button
        # See html_person_options
        if '&submitView=' in optionsConfirmParams:
            if debug:
                print('Viewing ' + optionsActor)
            self._redirect_headers(optionsActor,
                                   cookie, calling_domain)
            self.server.POSTbusy = False
            return

        # person options screen, petname submit button
        # See html_person_options
        if '&submitPetname=' in optionsConfirmParams and petname:
            if debug:
                print('Change petname to ' + petname)
            handle = optionsNickname + '@' + optionsDomainFull
            set_pet_name(base_dir,
                         chooserNickname,
                         domain,
                         handle, petname)
            usersPathStr = \
                usersPath + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            self._redirect_headers(usersPathStr, cookie,
                                   calling_domain)
            self.server.POSTbusy = False
            return

        # person options screen, person notes submit button
        # See html_person_options
        if '&submitPersonNotes=' in optionsConfirmParams:
            if debug:
                print('Change person notes')
            handle = optionsNickname + '@' + optionsDomainFull
            if not personNotes:
                personNotes = ''
            set_person_notes(base_dir,
                             chooserNickname,
                             domain,
                             handle, personNotes)
            usersPathStr = \
                usersPath + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            self._redirect_headers(usersPathStr, cookie,
                                   calling_domain)
            self.server.POSTbusy = False
            return

        # person options screen, on calendar checkbox
        # See html_person_options
        if '&submitOnCalendar=' in optionsConfirmParams:
            onCalendar = None
            if 'onCalendar=' in optionsConfirmParams:
                onCalendar = optionsConfirmParams.split('onCalendar=')[1]
                if '&' in onCalendar:
                    onCalendar = onCalendar.split('&')[0]
            if onCalendar == 'on':
                add_person_to_calendar(base_dir,
                                       chooserNickname,
                                       domain,
                                       optionsNickname,
                                       optionsDomainFull)
            else:
                remove_person_from_calendar(base_dir,
                                            chooserNickname,
                                            domain,
                                            optionsNickname,
                                            optionsDomainFull)
            usersPathStr = \
                usersPath + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            self._redirect_headers(usersPathStr, cookie,
                                   calling_domain)
            self.server.POSTbusy = False
            return

        # person options screen, on notify checkbox
        # See html_person_options
        if '&submitNotifyOnPost=' in optionsConfirmParams:
            notify = None
            if 'notifyOnPost=' in optionsConfirmParams:
                notify = optionsConfirmParams.split('notifyOnPost=')[1]
                if '&' in notify:
                    notify = notify.split('&')[0]
            if notify == 'on':
                add_notify_on_post(base_dir,
                                   chooserNickname,
                                   domain,
                                   optionsNickname,
                                   optionsDomainFull)
            else:
                remove_notify_on_post(base_dir,
                                      chooserNickname,
                                      domain,
                                      optionsNickname,
                                      optionsDomainFull)
            usersPathStr = \
                usersPath + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            self._redirect_headers(usersPathStr, cookie,
                                   calling_domain)
            self.server.POSTbusy = False
            return

        # person options screen, permission to post to newswire
        # See html_person_options
        if '&submitPostToNews=' in optionsConfirmParams:
            admin_nickname = get_config_param(self.server.base_dir, 'admin')
            if (chooserNickname != optionsNickname and
                (chooserNickname == admin_nickname or
                 (is_moderator(self.server.base_dir, chooserNickname) and
                  not is_moderator(self.server.base_dir, optionsNickname)))):
                postsToNews = None
                if 'postsToNews=' in optionsConfirmParams:
                    postsToNews = optionsConfirmParams.split('postsToNews=')[1]
                    if '&' in postsToNews:
                        postsToNews = postsToNews.split('&')[0]
                accountDir = acct_dir(self.server.base_dir,
                                      optionsNickname, optionsDomain)
                newswireBlockedFilename = accountDir + '/.nonewswire'
                if postsToNews == 'on':
                    if os.path.isfile(newswireBlockedFilename):
                        try:
                            os.remove(newswireBlockedFilename)
                        except OSError:
                            print('EX: _person_options unable to delete ' +
                                  newswireBlockedFilename)
                        refresh_newswire(self.server.base_dir)
                else:
                    if os.path.isdir(accountDir):
                        nwFilename = newswireBlockedFilename
                        nwWritten = False
                        try:
                            with open(nwFilename, 'w+') as noNewswireFile:
                                noNewswireFile.write('\n')
                                nwWritten = True
                        except OSError as ex:
                            print('EX: unable to write ' + nwFilename +
                                  ' ' + str(ex))
                        if nwWritten:
                            refresh_newswire(self.server.base_dir)
            usersPathStr = \
                usersPath + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            self._redirect_headers(usersPathStr, cookie,
                                   calling_domain)
            self.server.POSTbusy = False
            return

        # person options screen, permission to post to featured articles
        # See html_person_options
        if '&submitPostToFeatures=' in optionsConfirmParams:
            admin_nickname = get_config_param(self.server.base_dir, 'admin')
            if (chooserNickname != optionsNickname and
                (chooserNickname == admin_nickname or
                 (is_moderator(self.server.base_dir, chooserNickname) and
                  not is_moderator(self.server.base_dir, optionsNickname)))):
                postsToFeatures = None
                if 'postsToFeatures=' in optionsConfirmParams:
                    postsToFeatures = \
                        optionsConfirmParams.split('postsToFeatures=')[1]
                    if '&' in postsToFeatures:
                        postsToFeatures = postsToFeatures.split('&')[0]
                accountDir = acct_dir(self.server.base_dir,
                                      optionsNickname, optionsDomain)
                featuresBlockedFilename = accountDir + '/.nofeatures'
                if postsToFeatures == 'on':
                    if os.path.isfile(featuresBlockedFilename):
                        try:
                            os.remove(featuresBlockedFilename)
                        except OSError:
                            print('EX: _person_options unable to delete ' +
                                  featuresBlockedFilename)
                        refresh_newswire(self.server.base_dir)
                else:
                    if os.path.isdir(accountDir):
                        featFilename = featuresBlockedFilename
                        featWritten = False
                        try:
                            with open(featFilename, 'w+') as noFeaturesFile:
                                noFeaturesFile.write('\n')
                                featWritten = True
                        except OSError as ex:
                            print('EX: unable to write ' + featFilename +
                                  ' ' + str(ex))
                        if featWritten:
                            refresh_newswire(self.server.base_dir)
            usersPathStr = \
                usersPath + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            self._redirect_headers(usersPathStr, cookie,
                                   calling_domain)
            self.server.POSTbusy = False
            return

        # person options screen, permission to post to newswire
        # See html_person_options
        if '&submitModNewsPosts=' in optionsConfirmParams:
            admin_nickname = get_config_param(self.server.base_dir, 'admin')
            if (chooserNickname != optionsNickname and
                (chooserNickname == admin_nickname or
                 (is_moderator(self.server.base_dir, chooserNickname) and
                  not is_moderator(self.server.base_dir, optionsNickname)))):
                modPostsToNews = None
                if 'modNewsPosts=' in optionsConfirmParams:
                    modPostsToNews = \
                        optionsConfirmParams.split('modNewsPosts=')[1]
                    if '&' in modPostsToNews:
                        modPostsToNews = modPostsToNews.split('&')[0]
                accountDir = acct_dir(self.server.base_dir,
                                      optionsNickname, optionsDomain)
                newswireModFilename = accountDir + '/.newswiremoderated'
                if modPostsToNews != 'on':
                    if os.path.isfile(newswireModFilename):
                        try:
                            os.remove(newswireModFilename)
                        except OSError:
                            print('EX: _person_options unable to delete ' +
                                  newswireModFilename)
                else:
                    if os.path.isdir(accountDir):
                        nwFilename = newswireModFilename
                        try:
                            with open(nwFilename, 'w+') as modNewswireFile:
                                modNewswireFile.write('\n')
                        except OSError:
                            print('EX: unable to write ' + nwFilename)
            usersPathStr = \
                usersPath + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            self._redirect_headers(usersPathStr, cookie,
                                   calling_domain)
            self.server.POSTbusy = False
            return

        # person options screen, block button
        # See html_person_options
        if '&submitBlock=' in optionsConfirmParams:
            print('Adding block by ' + chooserNickname +
                  ' of ' + optionsActor)
            if add_block(base_dir, chooserNickname,
                         domain,
                         optionsNickname, optionsDomainFull):
                # send block activity
                self._send_block(http_prefix,
                                 chooserNickname, domain_full,
                                 optionsNickname, optionsDomainFull)

        # person options screen, unblock button
        # See html_person_options
        if '&submitUnblock=' in optionsConfirmParams:
            if debug:
                print('Unblocking ' + optionsActor)
            msg = \
                html_confirm_unblock(self.server.css_cache,
                                     self.server.translate,
                                     base_dir,
                                     usersPath,
                                     optionsActor,
                                     optionsAvatarUrl).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # person options screen, follow button
        # See html_person_options followStr
        if '&submitFollow=' in optionsConfirmParams or \
           '&submitJoin=' in optionsConfirmParams:
            if debug:
                print('Following ' + optionsActor)
            msg = \
                html_confirm_follow(self.server.css_cache,
                                    self.server.translate,
                                    base_dir,
                                    usersPath,
                                    optionsActor,
                                    optionsAvatarUrl).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # person options screen, unfollow button
        # See html_person_options followStr
        if '&submitUnfollow=' in optionsConfirmParams or \
           '&submitLeave=' in optionsConfirmParams:
            print('Unfollowing ' + optionsActor)
            msg = \
                html_confirm_unfollow(self.server.css_cache,
                                      self.server.translate,
                                      base_dir,
                                      usersPath,
                                      optionsActor,
                                      optionsAvatarUrl).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # person options screen, DM button
        # See html_person_options
        if '&submitDM=' in optionsConfirmParams:
            if debug:
                print('Sending DM to ' + optionsActor)
            reportPath = path.replace('/personoptions', '') + '/newdm'

            access_keys = self.server.access_keys
            if '/users/' in path:
                nickname = path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                if self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.keyShortcuts[nickname]

            customSubmitText = get_config_param(base_dir, 'customSubmitText')
            conversation_id = None
            msg = html_new_post(self.server.css_cache,
                                False, self.server.translate,
                                base_dir,
                                http_prefix,
                                reportPath, None,
                                [optionsActor], None, None,
                                page_number, '',
                                chooserNickname,
                                domain,
                                domain_full,
                                self.server.default_timeline,
                                self.server.newswire,
                                self.server.theme_name,
                                True, access_keys,
                                customSubmitText,
                                conversation_id,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.session,
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
                                self.server.max_like_count,
                                self.server.signing_priv_key_pem,
                                self.server.cw_lists,
                                self.server.lists_enabled,
                                self.server.default_timeline).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # person options screen, Info button
        # See html_person_options
        if '&submitPersonInfo=' in optionsConfirmParams:
            if is_moderator(self.server.base_dir, chooserNickname):
                if debug:
                    print('Showing info for ' + optionsActor)
                signing_priv_key_pem = self.server.signing_priv_key_pem
                msg = \
                    html_account_info(self.server.css_cache,
                                      self.server.translate,
                                      base_dir,
                                      http_prefix,
                                      chooserNickname,
                                      domain,
                                      self.server.port,
                                      optionsActor,
                                      self.server.debug,
                                      self.server.system_language,
                                      signing_priv_key_pem).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
                self.server.POSTbusy = False
                return
            else:
                self._404()
                return

        # person options screen, snooze button
        # See html_person_options
        if '&submitSnooze=' in optionsConfirmParams:
            usersPath = path.split('/personoptions')[0]
            thisActor = http_prefix + '://' + domain_full + usersPath
            if debug:
                print('Snoozing ' + optionsActor + ' ' + thisActor)
            if '/users/' in thisActor:
                nickname = thisActor.split('/users/')[1]
                person_snooze(base_dir, nickname,
                              domain, optionsActor)
                if calling_domain.endswith('.onion') and onion_domain:
                    thisActor = 'http://' + onion_domain + usersPath
                elif (calling_domain.endswith('.i2p') and i2p_domain):
                    thisActor = 'http://' + i2p_domain + usersPath
                actorPathStr = \
                    thisActor + '/' + self.server.default_timeline + \
                    '?page=' + str(page_number)
                self._redirect_headers(actorPathStr, cookie,
                                       calling_domain)
                self.server.POSTbusy = False
                return

        # person options screen, unsnooze button
        # See html_person_options
        if '&submitUnSnooze=' in optionsConfirmParams:
            usersPath = path.split('/personoptions')[0]
            thisActor = http_prefix + '://' + domain_full + usersPath
            if debug:
                print('Unsnoozing ' + optionsActor + ' ' + thisActor)
            if '/users/' in thisActor:
                nickname = thisActor.split('/users/')[1]
                person_unsnooze(base_dir, nickname,
                                domain, optionsActor)
                if calling_domain.endswith('.onion') and onion_domain:
                    thisActor = 'http://' + onion_domain + usersPath
                elif (calling_domain.endswith('.i2p') and i2p_domain):
                    thisActor = 'http://' + i2p_domain + usersPath
                actorPathStr = \
                    thisActor + '/' + self.server.default_timeline + \
                    '?page=' + str(page_number)
                self._redirect_headers(actorPathStr, cookie,
                                       calling_domain)
                self.server.POSTbusy = False
                return

        # person options screen, report button
        # See html_person_options
        if '&submitReport=' in optionsConfirmParams:
            if debug:
                print('Reporting ' + optionsActor)
            reportPath = \
                path.replace('/personoptions', '') + '/newreport'

            access_keys = self.server.access_keys
            if '/users/' in path:
                nickname = path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                if self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.keyShortcuts[nickname]

            customSubmitText = get_config_param(base_dir, 'customSubmitText')
            conversation_id = None
            msg = html_new_post(self.server.css_cache,
                                False, self.server.translate,
                                base_dir,
                                http_prefix,
                                reportPath, None, [],
                                None, postUrl, page_number, '',
                                chooserNickname,
                                domain,
                                domain_full,
                                self.server.default_timeline,
                                self.server.newswire,
                                self.server.theme_name,
                                True, access_keys,
                                customSubmitText,
                                conversation_id,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.session,
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
                                self.server.max_like_count,
                                self.server.signing_priv_key_pem,
                                self.server.cw_lists,
                                self.server.lists_enabled,
                                self.server.default_timeline).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # redirect back from person options screen
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif calling_domain.endswith('.i2p') and i2p_domain:
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr, cookie, calling_domain)
        self.server.POSTbusy = False
        return

    def _unfollow_confirm(self, calling_domain: str, cookie: str,
                          authorized: bool, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          debug: bool) -> None:
        """Confirm to unfollow
        """
        usersPath = path.split('/unfollowconfirm')[0]
        originPathStr = http_prefix + '://' + domain_full + usersPath
        followerNickname = get_nickname_from_actor(originPathStr)

        length = int(self.headers['Content-length'])

        try:
            followConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST followConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST followConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST followConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in followConfirmParams:
            followingActor = \
                urllib.parse.unquote_plus(followConfirmParams)
            followingActor = followingActor.split('actor=')[1]
            if '&' in followingActor:
                followingActor = followingActor.split('&')[0]
            followingNickname = get_nickname_from_actor(followingActor)
            followingDomain, followingPort = \
                get_domain_from_actor(followingActor)
            followingDomainFull = \
                get_full_domain(followingDomain, followingPort)
            if followerNickname == followingNickname and \
               followingDomain == domain and \
               followingPort == port:
                if debug:
                    print('You cannot unfollow yourself!')
            else:
                if debug:
                    print(followerNickname + ' stops following ' +
                          followingActor)
                followActor = \
                    local_actor_url(http_prefix, followerNickname, domain_full)
                statusNumber, published = get_status_number()
                followId = followActor + '/statuses/' + str(statusNumber)
                unfollowJson = {
                    '@context': 'https://www.w3.org/ns/activitystreams',
                    'id': followId + '/undo',
                    'type': 'Undo',
                    'actor': followActor,
                    'object': {
                        'id': followId,
                        'type': 'Follow',
                        'actor': followActor,
                        'object': followingActor
                    }
                }
                pathUsersSection = path.split('/users/')[1]
                self.post_to_nickname = pathUsersSection.split('/')[0]
                group_account = has_group_type(self.server.base_dir,
                                               followingActor,
                                               self.server.person_cache)
                unfollow_account(self.server.base_dir, self.post_to_nickname,
                                 self.server.domain,
                                 followingNickname, followingDomainFull,
                                 self.server.debug, group_account)
                self._post_to_outbox_thread(unfollowJson)

        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr, cookie, calling_domain)
        self.server.POSTbusy = False

    def _follow_confirm(self, calling_domain: str, cookie: str,
                        authorized: bool, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domain_full: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        debug: bool) -> None:
        """Confirm to follow
        """
        usersPath = path.split('/followconfirm')[0]
        originPathStr = http_prefix + '://' + domain_full + usersPath
        followerNickname = get_nickname_from_actor(originPathStr)

        length = int(self.headers['Content-length'])

        try:
            followConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST followConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST followConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST followConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitView=' in followConfirmParams:
            followingActor = \
                urllib.parse.unquote_plus(followConfirmParams)
            followingActor = followingActor.split('actor=')[1]
            if '&' in followingActor:
                followingActor = followingActor.split('&')[0]
            self._redirect_headers(followingActor, cookie, calling_domain)
            self.server.POSTbusy = False
            return

        if '&submitYes=' in followConfirmParams:
            followingActor = \
                urllib.parse.unquote_plus(followConfirmParams)
            followingActor = followingActor.split('actor=')[1]
            if '&' in followingActor:
                followingActor = followingActor.split('&')[0]
            followingNickname = get_nickname_from_actor(followingActor)
            followingDomain, followingPort = \
                get_domain_from_actor(followingActor)
            if followerNickname == followingNickname and \
               followingDomain == domain and \
               followingPort == port:
                if debug:
                    print('You cannot follow yourself!')
            elif (followingNickname == 'news' and
                  followingDomain == domain and
                  followingPort == port):
                if debug:
                    print('You cannot follow the news actor')
            else:
                print('Sending follow request from ' +
                      followerNickname + ' to ' + followingActor)
                if not self.server.signing_priv_key_pem:
                    print('Sending follow request with no signing key')
                send_follow_request(self.server.session,
                                    base_dir, followerNickname,
                                    domain, port,
                                    http_prefix,
                                    followingNickname,
                                    followingDomain,
                                    followingActor,
                                    followingPort, http_prefix,
                                    False, self.server.federation_list,
                                    self.server.send_threads,
                                    self.server.postLog,
                                    self.server.cached_webfingers,
                                    self.server.person_cache, debug,
                                    self.server.project_version,
                                    self.server.signing_priv_key_pem)
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr, cookie, calling_domain)
        self.server.POSTbusy = False

    def _block_confirm(self, calling_domain: str, cookie: str,
                       authorized: bool, path: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domain_full: str, port: int,
                       onion_domain: str, i2p_domain: str,
                       debug: bool) -> None:
        """Confirms a block
        """
        usersPath = path.split('/blockconfirm')[0]
        originPathStr = http_prefix + '://' + domain_full + usersPath
        blockerNickname = get_nickname_from_actor(originPathStr)
        if not blockerNickname:
            if calling_domain.endswith('.onion') and onion_domain:
                originPathStr = 'http://' + onion_domain + usersPath
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                originPathStr = 'http://' + i2p_domain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr,
                                   cookie, calling_domain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            blockConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST blockConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST blockConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST blockConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in blockConfirmParams:
            blockingActor = \
                urllib.parse.unquote_plus(blockConfirmParams)
            blockingActor = blockingActor.split('actor=')[1]
            if '&' in blockingActor:
                blockingActor = blockingActor.split('&')[0]
            blockingNickname = get_nickname_from_actor(blockingActor)
            if not blockingNickname:
                if calling_domain.endswith('.onion') and onion_domain:
                    originPathStr = 'http://' + onion_domain + usersPath
                elif (calling_domain.endswith('.i2p') and i2p_domain):
                    originPathStr = 'http://' + i2p_domain + usersPath
                print('WARN: unable to find nickname in ' + blockingActor)
                self._redirect_headers(originPathStr,
                                       cookie, calling_domain)
                self.server.POSTbusy = False
                return
            blockingDomain, blockingPort = \
                get_domain_from_actor(blockingActor)
            blockingDomainFull = get_full_domain(blockingDomain, blockingPort)
            if blockerNickname == blockingNickname and \
               blockingDomain == domain and \
               blockingPort == port:
                if debug:
                    print('You cannot block yourself!')
            else:
                print('Adding block by ' + blockerNickname +
                      ' of ' + blockingActor)
                if add_block(base_dir, blockerNickname,
                             domain,
                             blockingNickname,
                             blockingDomainFull):
                    # send block activity
                    self._send_block(http_prefix,
                                     blockerNickname, domain_full,
                                     blockingNickname, blockingDomainFull)
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr, cookie, calling_domain)
        self.server.POSTbusy = False

    def _unblock_confirm(self, calling_domain: str, cookie: str,
                         authorized: bool, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         debug: bool) -> None:
        """Confirms a unblock
        """
        usersPath = path.split('/unblockconfirm')[0]
        originPathStr = http_prefix + '://' + domain_full + usersPath
        blockerNickname = get_nickname_from_actor(originPathStr)
        if not blockerNickname:
            if calling_domain.endswith('.onion') and onion_domain:
                originPathStr = 'http://' + onion_domain + usersPath
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                originPathStr = 'http://' + i2p_domain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr,
                                   cookie, calling_domain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            blockConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST blockConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST blockConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST blockConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in blockConfirmParams:
            blockingActor = \
                urllib.parse.unquote_plus(blockConfirmParams)
            blockingActor = blockingActor.split('actor=')[1]
            if '&' in blockingActor:
                blockingActor = blockingActor.split('&')[0]
            blockingNickname = get_nickname_from_actor(blockingActor)
            if not blockingNickname:
                if calling_domain.endswith('.onion') and onion_domain:
                    originPathStr = 'http://' + onion_domain + usersPath
                elif (calling_domain.endswith('.i2p') and i2p_domain):
                    originPathStr = 'http://' + i2p_domain + usersPath
                print('WARN: unable to find nickname in ' + blockingActor)
                self._redirect_headers(originPathStr,
                                       cookie, calling_domain)
                self.server.POSTbusy = False
                return
            blockingDomain, blockingPort = \
                get_domain_from_actor(blockingActor)
            blockingDomainFull = get_full_domain(blockingDomain, blockingPort)
            if blockerNickname == blockingNickname and \
               blockingDomain == domain and \
               blockingPort == port:
                if debug:
                    print('You cannot unblock yourself!')
            else:
                if debug:
                    print(blockerNickname + ' stops blocking ' +
                          blockingActor)
                remove_block(base_dir,
                             blockerNickname, domain,
                             blockingNickname, blockingDomainFull)
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr,
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _receive_search_query(self, calling_domain: str, cookie: str,
                              authorized: bool, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str,
                              port: int, searchForEmoji: bool,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime, GETtimings: {},
                              debug: bool) -> None:
        """Receive a search query
        """
        # get the page number
        page_number = 1
        if '/searchhandle?page=' in path:
            page_number_str = path.split('/searchhandle?page=')[1]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
            path = path.split('?page=')[0]

        usersPath = path.replace('/searchhandle', '')
        actorStr = self._get_instance_url(calling_domain) + usersPath
        length = int(self.headers['Content-length'])
        try:
            searchParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST searchParams connection was reset')
            else:
                print('WARN: POST searchParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST searchParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        if 'submitBack=' in searchParams:
            # go back on search screen
            self._redirect_headers(actorStr + '/' +
                                   self.server.default_timeline,
                                   cookie, calling_domain)
            self.server.POSTbusy = False
            return
        if 'searchtext=' in searchParams:
            searchStr = searchParams.split('searchtext=')[1]
            if '&' in searchStr:
                searchStr = searchStr.split('&')[0]
            searchStr = \
                urllib.parse.unquote_plus(searchStr.strip())
            searchStr = searchStr.lower().strip()
            print('searchStr: ' + searchStr)
            if searchForEmoji:
                searchStr = ':' + searchStr + ':'
            if searchStr.startswith('#'):
                nickname = get_nickname_from_actor(actorStr)
                # hashtag search
                hashtagStr = \
                    html_hashtag_search(self.server.css_cache,
                                        nickname, domain, port,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        base_dir,
                                        searchStr[1:], 1,
                                        max_posts_in_hashtag_feed,
                                        self.server.session,
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
                                        self.server.lists_enabled)
                if hashtagStr:
                    msg = hashtagStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif (searchStr.startswith('*') or
                  searchStr.endswith(' skill')):
                possibleEndings = (
                    ' skill'
                )
                for possEnding in possibleEndings:
                    if searchStr.endswith(possEnding):
                        searchStr = searchStr.replace(possEnding, '')
                        break
                # skill search
                searchStr = searchStr.replace('*', '').strip()
                skillStr = \
                    html_skills_search(actorStr,
                                       self.server.css_cache,
                                       self.server.translate,
                                       base_dir,
                                       http_prefix,
                                       searchStr,
                                       self.server.instance_only_skills_search,
                                       64)
                if skillStr:
                    msg = skillStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif (searchStr.startswith("'") or
                  searchStr.endswith(' history') or
                  searchStr.endswith(' in sent') or
                  searchStr.endswith(' in outbox') or
                  searchStr.endswith(' in outgoing') or
                  searchStr.endswith(' in sent items') or
                  searchStr.endswith(' in sent posts') or
                  searchStr.endswith(' in outgoing posts') or
                  searchStr.endswith(' in my history') or
                  searchStr.endswith(' in my outbox') or
                  searchStr.endswith(' in my posts')):
                possibleEndings = (
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
                for possEnding in possibleEndings:
                    if searchStr.endswith(possEnding):
                        searchStr = searchStr.replace(possEnding, '')
                        break
                # your post history search
                nickname = get_nickname_from_actor(actorStr)
                searchStr = searchStr.replace("'", '', 1).strip()
                historyStr = \
                    html_history_search(self.server.css_cache,
                                        self.server.translate,
                                        base_dir,
                                        http_prefix,
                                        nickname,
                                        domain,
                                        searchStr,
                                        max_posts_in_feed,
                                        page_number,
                                        self.server.project_version,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.session,
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
                                        self.server.lists_enabled)
                if historyStr:
                    msg = historyStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif (searchStr.startswith('-') or
                  searchStr.endswith(' in my saved items') or
                  searchStr.endswith(' in my saved posts') or
                  searchStr.endswith(' in my bookmarks') or
                  searchStr.endswith(' in my saved') or
                  searchStr.endswith(' in my saves') or
                  searchStr.endswith(' in saved posts') or
                  searchStr.endswith(' in saved items') or
                  searchStr.endswith(' in bookmarks') or
                  searchStr.endswith(' in saved') or
                  searchStr.endswith(' in saves') or
                  searchStr.endswith(' bookmark')):
                possibleEndings = (
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
                for possEnding in possibleEndings:
                    if searchStr.endswith(possEnding):
                        searchStr = searchStr.replace(possEnding, '')
                        break
                # bookmark search
                nickname = get_nickname_from_actor(actorStr)
                searchStr = searchStr.replace('-', '', 1).strip()
                bookmarksStr = \
                    html_history_search(self.server.css_cache,
                                        self.server.translate,
                                        base_dir,
                                        http_prefix,
                                        nickname,
                                        domain,
                                        searchStr,
                                        max_posts_in_feed,
                                        page_number,
                                        self.server.project_version,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.session,
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
                                        self.server.lists_enabled)
                if bookmarksStr:
                    msg = bookmarksStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif ('@' in searchStr or
                  ('://' in searchStr and
                   has_users_path(searchStr))):
                if searchStr.endswith(':') or \
                   searchStr.endswith(';') or \
                   searchStr.endswith('.'):
                    actorStr = \
                        self._get_instance_url(calling_domain) + usersPath
                    self._redirect_headers(actorStr + '/search',
                                           cookie, calling_domain)
                    self.server.POSTbusy = False
                    return
                # profile search
                nickname = get_nickname_from_actor(actorStr)
                if not self._establish_session("handle search"):
                    self.server.POSTbusy = False
                    return
                profilePathStr = path.replace('/searchhandle', '')

                # are we already following the searched for handle?
                if is_following_actor(base_dir, nickname, domain, searchStr):
                    if not has_users_path(searchStr):
                        searchNickname = get_nickname_from_actor(searchStr)
                        searchDomain, searchPort = \
                            get_domain_from_actor(searchStr)
                        searchDomainFull = \
                            get_full_domain(searchDomain, searchPort)
                        actor = \
                            local_actor_url(http_prefix, searchNickname,
                                            searchDomainFull)
                    else:
                        actor = searchStr
                    avatarUrl = \
                        get_avatar_image_url(self.server.session,
                                             base_dir, http_prefix,
                                             actor,
                                             self.server.person_cache,
                                             None, True,
                                             self.server.signing_priv_key_pem)
                    profilePathStr += \
                        '?options=' + actor + ';1;' + avatarUrl

                    self._show_person_options(calling_domain, profilePathStr,
                                              base_dir, http_prefix,
                                              domain, domain_full,
                                              GETstartTime,
                                              onion_domain, i2p_domain,
                                              cookie, debug, authorized)
                    return
                else:
                    show_published_date_only = \
                        self.server.show_published_date_only
                    allow_local_network_access = \
                        self.server.allow_local_network_access

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = self.server.keyShortcuts[nickname]

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
                    profileStr = \
                        html_profile_after_search(self.server.css_cache,
                                                  recent_posts_cache,
                                                  self.server.max_recent_posts,
                                                  self.server.translate,
                                                  base_dir,
                                                  profilePathStr,
                                                  http_prefix,
                                                  nickname,
                                                  domain,
                                                  port,
                                                  searchStr,
                                                  self.server.session,
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
                                                  self.server.lists_enabled)
                if profileStr:
                    msg = profileStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                else:
                    actorStr = \
                        self._get_instance_url(calling_domain) + usersPath
                    self._redirect_headers(actorStr + '/search',
                                           cookie, calling_domain)
                    self.server.POSTbusy = False
                    return
            elif (searchStr.startswith(':') or
                  searchStr.endswith(' emoji')):
                # eg. "cat emoji"
                if searchStr.endswith(' emoji'):
                    searchStr = \
                        searchStr.replace(' emoji', '')
                # emoji search
                emojiStr = \
                    html_search_emoji(self.server.css_cache,
                                      self.server.translate,
                                      base_dir,
                                      http_prefix,
                                      searchStr)
                if emojiStr:
                    msg = emojiStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif searchStr.startswith('.'):
                # wanted items search
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                wantedItemsStr = \
                    html_search_shared_items(self.server.css_cache,
                                             self.server.translate,
                                             base_dir,
                                             searchStr[1:], page_number,
                                             max_posts_in_feed,
                                             http_prefix,
                                             domain_full,
                                             actorStr, calling_domain,
                                             shared_items_federated_domains,
                                             'wanted')
                if wantedItemsStr:
                    msg = wantedItemsStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            else:
                # shared items search
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                sharedItemsStr = \
                    html_search_shared_items(self.server.css_cache,
                                             self.server.translate,
                                             base_dir,
                                             searchStr, page_number,
                                             max_posts_in_feed,
                                             http_prefix,
                                             domain_full,
                                             actorStr, calling_domain,
                                             shared_items_federated_domains,
                                             'shares')
                if sharedItemsStr:
                    msg = sharedItemsStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, calling_domain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
        actorStr = self._get_instance_url(calling_domain) + usersPath
        self._redirect_headers(actorStr + '/' +
                               self.server.default_timeline,
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _receive_vote(self, calling_domain: str, cookie: str,
                      authorized: bool, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domain_full: str,
                      onion_domain: str, i2p_domain: str,
                      debug: bool) -> None:
        """Receive a vote via POST
        """
        page_number = 1
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
            path = path.split('?page=')[0]

        # the actor who votes
        usersPath = path.replace('/question', '')
        actor = http_prefix + '://' + domain_full + usersPath
        nickname = get_nickname_from_actor(actor)
        if not nickname:
            if calling_domain.endswith('.onion') and onion_domain:
                actor = 'http://' + onion_domain + usersPath
            elif (calling_domain.endswith('.i2p') and i2p_domain):
                actor = 'http://' + i2p_domain + usersPath
            actorPathStr = \
                actor + '/' + self.server.default_timeline + \
                '?page=' + str(page_number)
            self._redirect_headers(actorPathStr,
                                   cookie, calling_domain)
            self.server.POSTbusy = False
            return

        # get the parameters
        length = int(self.headers['Content-length'])

        try:
            questionParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST questionParams connection was reset')
            else:
                print('WARN: POST questionParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST questionParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        questionParams = questionParams.replace('+', ' ')
        questionParams = questionParams.replace('%3F', '')
        questionParams = \
            urllib.parse.unquote_plus(questionParams.strip())

        # post being voted on
        message_id = None
        if 'messageId=' in questionParams:
            message_id = questionParams.split('messageId=')[1]
            if '&' in message_id:
                message_id = message_id.split('&')[0]

        answer = None
        if 'answer=' in questionParams:
            answer = questionParams.split('answer=')[1]
            if '&' in answer:
                answer = answer.split('&')[0]

        self._send_reply_to_question(nickname, message_id, answer)
        if calling_domain.endswith('.onion') and onion_domain:
            actor = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            actor = 'http://' + i2p_domain + usersPath
        actorPathStr = \
            actor + '/' + self.server.default_timeline + \
            '?page=' + str(page_number)
        self._redirect_headers(actorPathStr, cookie,
                               calling_domain)
        self.server.POSTbusy = False
        return

    def _receive_image(self, length: int,
                       calling_domain: str, cookie: str,
                       authorized: bool, path: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domain_full: str,
                       onion_domain: str, i2p_domain: str,
                       debug: bool) -> None:
        """Receives an image via POST
        """
        if not self.outboxAuthenticated:
            if debug:
                print('DEBUG: unauthenticated attempt to ' +
                      'post image to outbox')
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy = False
            return
        pathUsersSection = path.split('/users/')[1]
        if '/' not in pathUsersSection:
            self._404()
            self.server.POSTbusy = False
            return
        self.postFromNickname = pathUsersSection.split('/')[0]
        accountsDir = acct_dir(base_dir, self.postFromNickname, domain)
        if not os.path.isdir(accountsDir):
            self._404()
            self.server.POSTbusy = False
            return

        try:
            mediaBytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST mediaBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST mediaBytes socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST mediaBytes rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        media_filenameBase = accountsDir + '/upload'
        media_filename = \
            media_filenameBase + '.' + \
            get_image_extension_from_mime_type(self.headers['Content-type'])
        try:
            with open(media_filename, 'wb') as avFile:
                avFile.write(mediaBytes)
        except OSError:
            print('EX: unable to write ' + media_filename)
        if debug:
            print('DEBUG: image saved to ' + media_filename)
        self.send_response(201)
        self.end_headers()
        self.server.POSTbusy = False

    def _remove_share(self, calling_domain: str, cookie: str,
                      authorized: bool, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domain_full: str,
                      onion_domain: str, i2p_domain: str,
                      debug: bool) -> None:
        """Removes a shared item
        """
        usersPath = path.split('/rmshare')[0]
        originPathStr = http_prefix + '://' + domain_full + usersPath

        length = int(self.headers['Content-length'])

        try:
            removeShareConfirmParams = \
                self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST removeShareConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST removeShareConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST removeShareConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in removeShareConfirmParams and authorized:
            removeShareConfirmParams = \
                removeShareConfirmParams.replace('+', ' ').strip()
            removeShareConfirmParams = \
                urllib.parse.unquote_plus(removeShareConfirmParams)
            shareActor = removeShareConfirmParams.split('actor=')[1]
            if '&' in shareActor:
                shareActor = shareActor.split('&')[0]
            admin_nickname = get_config_param(base_dir, 'admin')
            adminActor = \
                local_actor_url(http_prefix, admin_nickname, domain_full)
            actor = originPathStr
            actorNickname = get_nickname_from_actor(actor)
            if actor == shareActor or actor == adminActor or \
               is_moderator(base_dir, actorNickname):
                item_id = removeShareConfirmParams.split('itemID=')[1]
                if '&' in item_id:
                    item_id = item_id.split('&')[0]
                shareNickname = get_nickname_from_actor(shareActor)
                if shareNickname:
                    shareDomain, sharePort = get_domain_from_actor(shareActor)
                    remove_shared_item(base_dir,
                                       shareNickname, shareDomain, item_id,
                                       http_prefix, domain_full, 'shares')

        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr + '/tlshares',
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _remove_wanted(self, calling_domain: str, cookie: str,
                       authorized: bool, path: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domain_full: str,
                       onion_domain: str, i2p_domain: str,
                       debug: bool) -> None:
        """Removes a wanted item
        """
        usersPath = path.split('/rmwanted')[0]
        originPathStr = http_prefix + '://' + domain_full + usersPath

        length = int(self.headers['Content-length'])

        try:
            removeShareConfirmParams = \
                self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST removeShareConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST removeShareConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST removeShareConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in removeShareConfirmParams and authorized:
            removeShareConfirmParams = \
                removeShareConfirmParams.replace('+', ' ').strip()
            removeShareConfirmParams = \
                urllib.parse.unquote_plus(removeShareConfirmParams)
            shareActor = removeShareConfirmParams.split('actor=')[1]
            if '&' in shareActor:
                shareActor = shareActor.split('&')[0]
            admin_nickname = get_config_param(base_dir, 'admin')
            adminActor = \
                local_actor_url(http_prefix, admin_nickname, domain_full)
            actor = originPathStr
            actorNickname = get_nickname_from_actor(actor)
            if actor == shareActor or actor == adminActor or \
               is_moderator(base_dir, actorNickname):
                item_id = removeShareConfirmParams.split('itemID=')[1]
                if '&' in item_id:
                    item_id = item_id.split('&')[0]
                shareNickname = get_nickname_from_actor(shareActor)
                if shareNickname:
                    shareDomain, sharePort = get_domain_from_actor(shareActor)
                    remove_shared_item(base_dir,
                                       shareNickname, shareDomain, item_id,
                                       http_prefix, domain_full, 'wanted')

        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr + '/tlwanted',
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _receive_remove_post(self, calling_domain: str, cookie: str,
                             authorized: bool, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str,
                             onion_domain: str, i2p_domain: str,
                             debug: bool) -> None:
        """Endpoint for removing posts after confirmation
        """
        page_number = 1
        usersPath = path.split('/rmpost')[0]
        originPathStr = \
            http_prefix + '://' + \
            domain_full + usersPath

        length = int(self.headers['Content-length'])

        try:
            removePostConfirmParams = \
                self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST removePostConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST removePostConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST removePostConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        if '&submitYes=' in removePostConfirmParams:
            removePostConfirmParams = \
                urllib.parse.unquote_plus(removePostConfirmParams)
            removeMessageId = \
                removePostConfirmParams.split('messageId=')[1]
            if '&' in removeMessageId:
                removeMessageId = removeMessageId.split('&')[0]
            if 'pageNumber=' in removePostConfirmParams:
                page_number_str = \
                    removePostConfirmParams.split('pageNumber=')[1]
                if '&' in page_number_str:
                    page_number_str = page_number_str.split('&')[0]
                if page_number_str.isdigit():
                    page_number = int(page_number_str)
            yearStr = None
            if 'year=' in removePostConfirmParams:
                yearStr = removePostConfirmParams.split('year=')[1]
                if '&' in yearStr:
                    yearStr = yearStr.split('&')[0]
            monthStr = None
            if 'month=' in removePostConfirmParams:
                monthStr = removePostConfirmParams.split('month=')[1]
                if '&' in monthStr:
                    monthStr = monthStr.split('&')[0]
            if '/statuses/' in removeMessageId:
                removePostActor = removeMessageId.split('/statuses/')[0]
            if originPathStr in removePostActor:
                toList = ['https://www.w3.org/ns/activitystreams#Public',
                          removePostActor]
                deleteJson = {
                    "@context": "https://www.w3.org/ns/activitystreams",
                    'actor': removePostActor,
                    'object': removeMessageId,
                    'to': toList,
                    'cc': [removePostActor + '/followers'],
                    'type': 'Delete'
                }
                self.post_to_nickname = \
                    get_nickname_from_actor(removePostActor)
                if self.post_to_nickname:
                    if monthStr and yearStr:
                        if monthStr.isdigit() and yearStr.isdigit():
                            yearInt = int(yearStr)
                            monthInt = int(monthStr)
                            remove_calendar_event(base_dir,
                                                  self.post_to_nickname,
                                                  domain,
                                                  yearInt,
                                                  monthInt,
                                                  removeMessageId)
                    self._post_to_outbox_thread(deleteJson)
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        if page_number == 1:
            self._redirect_headers(originPathStr + '/outbox', cookie,
                                   calling_domain)
        else:
            page_number_str = str(page_number)
            actorPathStr = originPathStr + '/outbox?page=' + page_number_str
            self._redirect_headers(actorPathStr,
                                   cookie, calling_domain)
        self.server.POSTbusy = False

    def _links_update(self, calling_domain: str, cookie: str,
                      authorized: bool, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domain_full: str,
                      onion_domain: str, i2p_domain: str, debug: bool,
                      default_timeline: str,
                      allow_local_network_access: bool) -> None:
        """Updates the left links column of the timeline
        """
        usersPath = path.replace('/linksdata', '')
        usersPath = usersPath.replace('/editlinks', '')
        actorStr = self._get_instance_url(calling_domain) + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = get_nickname_from_actor(actorStr)
            editor = None
            if nickname:
                editor = is_editor(base_dir, nickname)
            if not nickname or not editor:
                if not nickname:
                    print('WARN: nickname not found in ' + actorStr)
                else:
                    print('WARN: nickname is not a moderator' + actorStr)
                self._redirect_headers(actorStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.max_post_length:
                print('Maximum links data length exceeded ' + str(length))
                self._redirect_headers(actorStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            linksFilename = base_dir + '/accounts/links.txt'
            aboutFilename = base_dir + '/accounts/about.md'
            TOSFilename = base_dir + '/accounts/tos.md'

            # extract all of the text fields into a dict
            fields = \
                extract_text_fields_in_post(postBytes, boundary, debug)

            if fields.get('editedLinks'):
                linksStr = fields['editedLinks']
                if fields.get('newColLink'):
                    if linksStr:
                        if not linksStr.endswith('\n'):
                            linksStr += '\n'
                    linksStr += fields['newColLink'] + '\n'
                try:
                    with open(linksFilename, 'w+') as linksFile:
                        linksFile.write(linksStr)
                except OSError:
                    print('EX: _links_update unable to write ' + linksFilename)
            else:
                if fields.get('newColLink'):
                    # the text area is empty but there is a new link added
                    linksStr = fields['newColLink'] + '\n'
                    try:
                        with open(linksFilename, 'w+') as linksFile:
                            linksFile.write(linksStr)
                    except OSError:
                        print('EX: _links_update unable to write ' +
                              linksFilename)
                else:
                    if os.path.isfile(linksFilename):
                        try:
                            os.remove(linksFilename)
                        except OSError:
                            print('EX: _links_update unable to delete ' +
                                  linksFilename)

            admin_nickname = \
                get_config_param(base_dir, 'admin')
            if nickname == admin_nickname:
                if fields.get('editedAbout'):
                    aboutStr = fields['editedAbout']
                    if not dangerous_markup(aboutStr,
                                            allow_local_network_access):
                        try:
                            with open(aboutFilename, 'w+') as aboutFile:
                                aboutFile.write(aboutStr)
                        except OSError:
                            print('EX: unable to write about ' + aboutFilename)
                else:
                    if os.path.isfile(aboutFilename):
                        try:
                            os.remove(aboutFilename)
                        except OSError:
                            print('EX: _links_update unable to delete ' +
                                  aboutFilename)

                if fields.get('editedTOS'):
                    TOSStr = fields['editedTOS']
                    if not dangerous_markup(TOSStr,
                                            allow_local_network_access):
                        try:
                            with open(TOSFilename, 'w+') as TOSFile:
                                TOSFile.write(TOSStr)
                        except OSError:
                            print('EX: unable to write TOS ' + TOSFilename)
                else:
                    if os.path.isfile(TOSFilename):
                        try:
                            os.remove(TOSFilename)
                        except OSError:
                            print('EX: _links_update unable to delete ' +
                                  TOSFilename)

        # redirect back to the default timeline
        self._redirect_headers(actorStr + '/' + default_timeline,
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _set_hashtag_category(self, calling_domain: str, cookie: str,
                              authorized: bool, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str,
                              onion_domain: str, i2p_domain: str, debug: bool,
                              default_timeline: str,
                              allow_local_network_access: bool) -> None:
        """On the screen after selecting a hashtag from the swarm, this sets
        the category for that tag
        """
        usersPath = path.replace('/sethashtagcategory', '')
        hashtag = ''
        if '/tags/' not in usersPath:
            # no hashtag is specified within the path
            self._404()
            return
        hashtag = usersPath.split('/tags/')[1].strip()
        hashtag = urllib.parse.unquote_plus(hashtag)
        if not hashtag:
            # no hashtag was given in the path
            self._404()
            return
        hashtagFilename = base_dir + '/tags/' + hashtag + '.txt'
        if not os.path.isfile(hashtagFilename):
            # the hashtag does not exist
            self._404()
            return
        usersPath = usersPath.split('/tags/')[0]
        actorStr = self._get_instance_url(calling_domain) + usersPath
        tagScreenStr = actorStr + '/tags/' + hashtag
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = get_nickname_from_actor(actorStr)
            editor = None
            if nickname:
                editor = is_editor(base_dir, nickname)
            if not hashtag or not editor:
                if not nickname:
                    print('WARN: nickname not found in ' + actorStr)
                else:
                    print('WARN: nickname is not a moderator' + actorStr)
                self._redirect_headers(tagScreenStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.max_post_length:
                print('Maximum links data length exceeded ' + str(length))
                self._redirect_headers(tagScreenStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            # extract all of the text fields into a dict
            fields = \
                extract_text_fields_in_post(postBytes, boundary, debug)

            if fields.get('hashtagCategory'):
                categoryStr = fields['hashtagCategory'].lower()
                if not is_blocked_hashtag(base_dir, categoryStr) and \
                   not is_filtered(base_dir, nickname, domain, categoryStr):
                    set_hashtag_category(base_dir, hashtag, categoryStr, False)
            else:
                categoryFilename = base_dir + '/tags/' + hashtag + '.category'
                if os.path.isfile(categoryFilename):
                    try:
                        os.remove(categoryFilename)
                    except OSError:
                        print('EX: _set_hashtag_category unable to delete ' +
                              categoryFilename)

        # redirect back to the default timeline
        self._redirect_headers(tagScreenStr,
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _newswire_update(self, calling_domain: str, cookie: str,
                         authorized: bool, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str,
                         onion_domain: str, i2p_domain: str, debug: bool,
                         default_timeline: str) -> None:
        """Updates the right newswire column of the timeline
        """
        usersPath = path.replace('/newswiredata', '')
        usersPath = usersPath.replace('/editnewswire', '')
        actorStr = self._get_instance_url(calling_domain) + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = get_nickname_from_actor(actorStr)
            moderator = None
            if nickname:
                moderator = is_moderator(base_dir, nickname)
            if not nickname or not moderator:
                if not nickname:
                    print('WARN: nickname not found in ' + actorStr)
                else:
                    print('WARN: nickname is not a moderator' + actorStr)
                self._redirect_headers(actorStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.max_post_length:
                print('Maximum newswire data length exceeded ' + str(length))
                self._redirect_headers(actorStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            newswireFilename = base_dir + '/accounts/newswire.txt'

            # extract all of the text fields into a dict
            fields = \
                extract_text_fields_in_post(postBytes, boundary, debug)
            if fields.get('editedNewswire'):
                newswireStr = fields['editedNewswire']
                # append a new newswire entry
                if fields.get('newNewswireFeed'):
                    if newswireStr:
                        if not newswireStr.endswith('\n'):
                            newswireStr += '\n'
                    newswireStr += fields['newNewswireFeed'] + '\n'
                try:
                    with open(newswireFilename, 'w+') as newswireFile:
                        newswireFile.write(newswireStr)
                except OSError:
                    print('EX: unable to write ' + newswireFilename)
            else:
                if fields.get('newNewswireFeed'):
                    # the text area is empty but there is a new feed added
                    newswireStr = fields['newNewswireFeed'] + '\n'
                    try:
                        with open(newswireFilename, 'w+') as newswireFile:
                            newswireFile.write(newswireStr)
                    except OSError:
                        print('EX: unable to write ' + newswireFilename)
                else:
                    # text area has been cleared and there is no new feed
                    if os.path.isfile(newswireFilename):
                        try:
                            os.remove(newswireFilename)
                        except OSError:
                            print('EX: _newswire_update unable to delete ' +
                                  newswireFilename)

            # save filtered words list for the newswire
            filterNewswireFilename = \
                base_dir + '/accounts/' + \
                'news@' + domain + '/filters.txt'
            if fields.get('filteredWordsNewswire'):
                try:
                    with open(filterNewswireFilename, 'w+') as filterfile:
                        filterfile.write(fields['filteredWordsNewswire'])
                except OSError:
                    print('EX: unable to write ' + filterNewswireFilename)
            else:
                if os.path.isfile(filterNewswireFilename):
                    try:
                        os.remove(filterNewswireFilename)
                    except OSError:
                        print('EX: _newswire_update unable to delete ' +
                              filterNewswireFilename)

            # save news tagging rules
            hashtagRulesFilename = \
                base_dir + '/accounts/hashtagrules.txt'
            if fields.get('hashtagRulesList'):
                try:
                    with open(hashtagRulesFilename, 'w+') as rulesfile:
                        rulesfile.write(fields['hashtagRulesList'])
                except OSError:
                    print('EX: unable to write ' + hashtagRulesFilename)
            else:
                if os.path.isfile(hashtagRulesFilename):
                    try:
                        os.remove(hashtagRulesFilename)
                    except OSError:
                        print('EX: _newswire_update unable to delete ' +
                              hashtagRulesFilename)

            newswireTrustedFilename = \
                base_dir + '/accounts/newswiretrusted.txt'
            if fields.get('trustedNewswire'):
                newswireTrusted = fields['trustedNewswire']
                if not newswireTrusted.endswith('\n'):
                    newswireTrusted += '\n'
                try:
                    with open(newswireTrustedFilename, 'w+') as trustFile:
                        trustFile.write(newswireTrusted)
                except OSError:
                    print('EX: unable to write ' + newswireTrustedFilename)
            else:
                if os.path.isfile(newswireTrustedFilename):
                    try:
                        os.remove(newswireTrustedFilename)
                    except OSError:
                        print('EX: _newswire_update unable to delete ' +
                              newswireTrustedFilename)

        # redirect back to the default timeline
        self._redirect_headers(actorStr + '/' + default_timeline,
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _citations_update(self, calling_domain: str, cookie: str,
                          authorized: bool, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str,
                          onion_domain: str, i2p_domain: str, debug: bool,
                          default_timeline: str,
                          newswire: {}) -> None:
        """Updates the citations for a blog post after hitting
        update button on the citations screen
        """
        usersPath = path.replace('/citationsdata', '')
        actorStr = self._get_instance_url(calling_domain) + usersPath
        nickname = get_nickname_from_actor(actorStr)

        citationsFilename = \
            acct_dir(base_dir, nickname, domain) + '/.citations.txt'
        # remove any existing citations file
        if os.path.isfile(citationsFilename):
            try:
                os.remove(citationsFilename)
            except OSError:
                print('EX: _citations_update unable to delete ' +
                      citationsFilename)

        if newswire and \
           ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.max_post_length:
                print('Maximum citations data length exceeded ' + str(length))
                self._redirect_headers(actorStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form ' +
                          'citation screen POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form citations screen POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for ' +
                      'citations screen POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            # extract all of the text fields into a dict
            fields = \
                extract_text_fields_in_post(postBytes, boundary, debug)
            print('citationstest: ' + str(fields))
            citations = []
            for ctr in range(0, 128):
                fieldName = 'newswire' + str(ctr)
                if not fields.get(fieldName):
                    continue
                citations.append(fields[fieldName])

            if citations:
                citationsStr = ''
                for citationDate in citations:
                    citationsStr += citationDate + '\n'
                # save citations dates, so that they can be added when
                # reloading the newblog screen
                try:
                    with open(citationsFilename, 'w+') as citationsFile:
                        citationsFile.write(citationsStr)
                except OSError:
                    print('EX: unable to write ' + citationsFilename)

        # redirect back to the default timeline
        self._redirect_headers(actorStr + '/newblog',
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _news_post_edit(self, calling_domain: str, cookie: str,
                        authorized: bool, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domain_full: str,
                        onion_domain: str, i2p_domain: str, debug: bool,
                        default_timeline: str) -> None:
        """edits a news post after receiving POST
        """
        usersPath = path.replace('/newseditdata', '')
        usersPath = usersPath.replace('/editnewspost', '')
        actorStr = self._get_instance_url(calling_domain) + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = get_nickname_from_actor(actorStr)
            editorRole = None
            if nickname:
                editorRole = is_editor(base_dir, nickname)
            if not nickname or not editorRole:
                if not nickname:
                    print('WARN: nickname not found in ' + actorStr)
                else:
                    print('WARN: nickname is not an editor' + actorStr)
                if self.server.news_instance:
                    self._redirect_headers(actorStr + '/tlfeatures',
                                           cookie, calling_domain)
                else:
                    self._redirect_headers(actorStr + '/tlnews',
                                           cookie, calling_domain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.max_post_length:
                print('Maximum news data length exceeded ' + str(length))
                if self.server.news_instance:
                    self._redirect_headers(actorStr + '/tlfeatures',
                                           cookie, calling_domain)
                else:
                    self._redirect_headers(actorStr + '/tlnews',
                                           cookie, calling_domain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            # extract all of the text fields into a dict
            fields = \
                extract_text_fields_in_post(postBytes, boundary, debug)
            newsPostUrl = None
            newsPostTitle = None
            newsPostContent = None
            if fields.get('newsPostUrl'):
                newsPostUrl = fields['newsPostUrl']
            if fields.get('newsPostTitle'):
                newsPostTitle = fields['newsPostTitle']
            if fields.get('editedNewsPost'):
                newsPostContent = fields['editedNewsPost']

            if newsPostUrl and newsPostContent and newsPostTitle:
                # load the post
                post_filename = \
                    locate_post(base_dir, nickname, domain,
                                newsPostUrl)
                if post_filename:
                    post_json_object = load_json(post_filename)
                    # update the content and title
                    post_json_object['object']['summary'] = \
                        newsPostTitle
                    post_json_object['object']['content'] = \
                        newsPostContent
                    contentMap = post_json_object['object']['contentMap']
                    contentMap[self.server.system_language] = newsPostContent
                    # update newswire
                    pubDate = post_json_object['object']['published']
                    publishedDate = \
                        datetime.datetime.strptime(pubDate,
                                                   "%Y-%m-%dT%H:%M:%SZ")
                    if self.server.newswire.get(str(publishedDate)):
                        self.server.newswire[publishedDate][0] = \
                            newsPostTitle
                        self.server.newswire[publishedDate][4] = \
                            first_paragraph_from_string(newsPostContent)
                        # save newswire
                        newswireStateFilename = \
                            base_dir + '/accounts/.newswirestate.json'
                        try:
                            save_json(self.server.newswire,
                                      newswireStateFilename)
                        except Exception as ex:
                            print('ERROR: saving newswire state, ' + str(ex))

                    # remove any previous cached news posts
                    newsId = remove_id_ending(post_json_object['object']['id'])
                    newsId = newsId.replace('/', '#')
                    clear_from_post_caches(base_dir,
                                           self.server.recent_posts_cache,
                                           newsId)

                    # save the news post
                    save_json(post_json_object, post_filename)

        # redirect back to the default timeline
        if self.server.news_instance:
            self._redirect_headers(actorStr + '/tlfeatures',
                                   cookie, calling_domain)
        else:
            self._redirect_headers(actorStr + '/tlnews',
                                   cookie, calling_domain)
        self.server.POSTbusy = False

    def _profile_edit(self, calling_domain: str, cookie: str,
                      authorized: bool, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domain_full: str,
                      onion_domain: str, i2p_domain: str,
                      debug: bool, allow_local_network_access: bool,
                      system_language: str,
                      content_license_url: str) -> None:
        """Updates your user profile after editing via the Edit button
        on the profile screen
        """
        usersPath = path.replace('/profiledata', '')
        usersPath = usersPath.replace('/editprofile', '')
        actorStr = self._get_instance_url(calling_domain) + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = get_nickname_from_actor(actorStr)
            if not nickname:
                print('WARN: nickname not found in ' + actorStr)
                self._redirect_headers(actorStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.max_post_length:
                print('Maximum profile data length exceeded ' +
                      str(length))
                self._redirect_headers(actorStr, cookie, calling_domain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            admin_nickname = get_config_param(self.server.base_dir, 'admin')

            # get the various avatar, banner and background images
            actorChanged = True
            profileMediaTypes = (
                'avatar', 'image',
                'banner', 'search_banner',
                'instanceLogo',
                'left_col_image', 'right_col_image',
                'submitImportTheme'
            )
            profileMediaTypesUploaded = {}
            for mType in profileMediaTypes:
                # some images can only be changed by the admin
                if mType == 'instanceLogo':
                    if nickname != admin_nickname:
                        print('WARN: only the admin can change ' +
                              'instance logo')
                        continue

                if debug:
                    print('DEBUG: profile update extracting ' + mType +
                          ' image, zip or font from POST')
                mediaBytes, postBytes = \
                    extract_media_in_form_post(postBytes, boundary, mType)
                if mediaBytes:
                    if debug:
                        print('DEBUG: profile update ' + mType +
                              ' image, zip or font was found. ' +
                              str(len(mediaBytes)) + ' bytes')
                else:
                    if debug:
                        print('DEBUG: profile update, no ' + mType +
                              ' image, zip or font was found in POST')
                    continue

                # Note: a .temp extension is used here so that at no
                # time is an image with metadata publicly exposed,
                # even for a few mS
                if mType == 'instanceLogo':
                    filenameBase = \
                        base_dir + '/accounts/login.temp'
                elif mType == 'submitImportTheme':
                    if not os.path.isdir(base_dir + '/imports'):
                        os.mkdir(base_dir + '/imports')
                    filenameBase = \
                        base_dir + '/imports/newtheme.zip'
                    if os.path.isfile(filenameBase):
                        try:
                            os.remove(filenameBase)
                        except OSError:
                            print('EX: _profile_edit unable to delete ' +
                                  filenameBase)
                else:
                    filenameBase = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/' + mType + '.temp'

                filename, attachment_media_type = \
                    save_media_in_form_post(mediaBytes, debug,
                                            filenameBase)
                if filename:
                    print('Profile update POST ' + mType +
                          ' media, zip or font filename is ' + filename)
                else:
                    print('Profile update, no ' + mType +
                          ' media, zip or font filename in POST')
                    continue

                if mType == 'submitImportTheme':
                    if nickname == admin_nickname or \
                       is_artist(base_dir, nickname):
                        if import_theme(base_dir, filename):
                            print(nickname + ' uploaded a theme')
                    else:
                        print('Only admin or artist can import a theme')
                    continue

                post_imageFilename = filename.replace('.temp', '')
                if debug:
                    print('DEBUG: POST ' + mType +
                          ' media removing metadata')
                # remove existing etag
                if os.path.isfile(post_imageFilename + '.etag'):
                    try:
                        os.remove(post_imageFilename + '.etag')
                    except OSError:
                        print('EX: _profile_edit unable to delete ' +
                              post_imageFilename + '.etag')

                city = get_spoofed_city(self.server.city,
                                        base_dir, nickname, domain)

                if self.server.low_bandwidth:
                    convert_image_to_low_bandwidth(filename)
                process_meta_data(base_dir, nickname, domain,
                                  filename, post_imageFilename, city,
                                  content_license_url)
                if os.path.isfile(post_imageFilename):
                    print('profile update POST ' + mType +
                          ' image, zip or font saved to ' +
                          post_imageFilename)
                    if mType != 'instanceLogo':
                        lastPartOfImageFilename = \
                            post_imageFilename.split('/')[-1]
                        profileMediaTypesUploaded[mType] = \
                            lastPartOfImageFilename
                        actorChanged = True
                else:
                    print('ERROR: profile update POST ' + mType +
                          ' image or font could not be saved to ' +
                          post_imageFilename)

            postBytesStr = postBytes.decode('utf-8')
            redirectPath = ''
            checkNameAndBio = False
            onFinalWelcomeScreen = False
            if 'name="previewAvatar"' in postBytesStr:
                redirectPath = '/welcome_profile'
            elif 'name="initialWelcomeScreen"' in postBytesStr:
                redirectPath = '/welcome'
            elif 'name="finalWelcomeScreen"' in postBytesStr:
                checkNameAndBio = True
                redirectPath = '/welcome_final'
            elif 'name="welcomeCompleteButton"' in postBytesStr:
                redirectPath = '/' + self.server.default_timeline
                welcome_screen_is_complete(self.server.base_dir, nickname,
                                           self.server.domain)
                onFinalWelcomeScreen = True
            elif 'name="submitExportTheme"' in postBytesStr:
                print('submitExportTheme')
                themeDownloadPath = actorStr
                if export_theme(self.server.base_dir,
                                self.server.theme_name):
                    themeDownloadPath += \
                        '/exports/' + self.server.theme_name + '.zip'
                print('submitExportTheme path=' + themeDownloadPath)
                self._redirect_headers(themeDownloadPath,
                                       cookie, calling_domain)
                self.server.POSTbusy = False
                return

            # extract all of the text fields into a dict
            fields = \
                extract_text_fields_in_post(postBytes, boundary, debug)
            if debug:
                if fields:
                    print('DEBUG: profile update text ' +
                          'field extracted from POST ' + str(fields))
                else:
                    print('WARN: profile update, no text ' +
                          'fields could be extracted from POST')

            # load the json for the actor for this user
            actorFilename = \
                acct_dir(base_dir, nickname, domain) + '.json'
            if os.path.isfile(actorFilename):
                actor_json = load_json(actorFilename)
                if actor_json:
                    if not actor_json.get('discoverable'):
                        # discoverable in profile directory
                        # which isn't implemented in Epicyon
                        actor_json['discoverable'] = True
                        actorChanged = True
                    if actor_json.get('capabilityAcquisitionEndpoint'):
                        del actor_json['capabilityAcquisitionEndpoint']
                        actorChanged = True
                    # update the avatar/image url file extension
                    uploads = profileMediaTypesUploaded.items()
                    for mType, lastPart in uploads:
                        repStr = '/' + lastPart
                        if mType == 'avatar':
                            actorUrl = actor_json['icon']['url']
                            lastPartOfUrl = actorUrl.split('/')[-1]
                            srchStr = '/' + lastPartOfUrl
                            actorUrl = actorUrl.replace(srchStr, repStr)
                            actor_json['icon']['url'] = actorUrl
                            print('actorUrl: ' + actorUrl)
                            if '.' in actorUrl:
                                imgExt = actorUrl.split('.')[-1]
                                if imgExt == 'jpg':
                                    imgExt = 'jpeg'
                                actor_json['icon']['mediaType'] = \
                                    'image/' + imgExt
                        elif mType == 'image':
                            lastPartOfUrl = \
                                actor_json['image']['url'].split('/')[-1]
                            srchStr = '/' + lastPartOfUrl
                            actor_json['image']['url'] = \
                                actor_json['image']['url'].replace(srchStr,
                                                                   repStr)
                            if '.' in actor_json['image']['url']:
                                imgExt = \
                                    actor_json['image']['url'].split('.')[-1]
                                if imgExt == 'jpg':
                                    imgExt = 'jpeg'
                                actor_json['image']['mediaType'] = \
                                    'image/' + imgExt

                    # set skill levels
                    skillCtr = 1
                    actorSkillsCtr = no_of_actor_skills(actor_json)
                    while skillCtr < 10:
                        skillName = \
                            fields.get('skillName' + str(skillCtr))
                        if not skillName:
                            skillCtr += 1
                            continue
                        if is_filtered(base_dir, nickname, domain, skillName):
                            skillCtr += 1
                            continue
                        skillValue = \
                            fields.get('skillValue' + str(skillCtr))
                        if not skillValue:
                            skillCtr += 1
                            continue
                        if not actor_has_skill(actor_json, skillName):
                            actorChanged = True
                        else:
                            if actor_skill_value(actor_json, skillName) != \
                               int(skillValue):
                                actorChanged = True
                        set_actor_skill_level(actor_json,
                                              skillName, int(skillValue))
                        skillsStr = self.server.translate['Skills']
                        skillsStr = skillsStr.lower()
                        set_hashtag_category(base_dir, skillName,
                                             skillsStr, False)
                        skillCtr += 1
                    if no_of_actor_skills(actor_json) != \
                       actorSkillsCtr:
                        actorChanged = True

                    # change password
                    if fields.get('password') and \
                       fields.get('passwordconfirm'):
                        fields['password'] = \
                            remove_line_endings(fields['password'])
                        fields['passwordconfirm'] = \
                            remove_line_endings(fields['passwordconfirm'])
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
                        cityFilename = \
                            acct_dir(base_dir, nickname, domain) + '/city.txt'
                        try:
                            with open(cityFilename, 'w+') as fp:
                                fp.write(fields['cityDropdown'])
                        except OSError:
                            print('EX: unable to write city ' + cityFilename)

                    # change displayed name
                    if fields.get('displayNickname'):
                        if fields['displayNickname'] != actor_json['name']:
                            displayName = \
                                remove_html(fields['displayNickname'])
                            if not is_filtered(base_dir,
                                               nickname, domain,
                                               displayName):
                                actor_json['name'] = displayName
                            else:
                                actor_json['name'] = nickname
                                if checkNameAndBio:
                                    redirectPath = 'previewAvatar'
                            actorChanged = True
                    else:
                        if checkNameAndBio:
                            redirectPath = 'previewAvatar'

                    if nickname == admin_nickname or \
                       is_artist(base_dir, nickname):
                        # change theme
                        if fields.get('themeDropdown'):
                            self.server.theme_name = fields['themeDropdown']
                            set_theme(base_dir, self.server.theme_name, domain,
                                      allow_local_network_access,
                                      system_language)
                            self.server.text_mode_banner = \
                                get_text_mode_banner(self.server.base_dir)
                            self.server.iconsCache = {}
                            self.server.fontsCache = {}
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
                                            domain,
                                            domain_full)

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
                            currInstanceTitle = \
                                get_config_param(base_dir, 'instanceTitle')
                            if fields['instanceTitle'] != currInstanceTitle:
                                set_config_param(base_dir, 'instanceTitle',
                                                 fields['instanceTitle'])

                        # change YouTube alternate domain
                        if fields.get('ytdomain'):
                            currYTDomain = self.server.yt_replace_domain
                            if fields['ytdomain'] != currYTDomain:
                                newYTDomain = fields['ytdomain']
                                if '://' in newYTDomain:
                                    newYTDomain = newYTDomain.split('://')[1]
                                if '/' in newYTDomain:
                                    newYTDomain = newYTDomain.split('/')[0]
                                if '.' in newYTDomain:
                                    set_config_param(base_dir, 'youtubedomain',
                                                     newYTDomain)
                                    self.server.yt_replace_domain = \
                                        newYTDomain
                        else:
                            set_config_param(base_dir, 'youtubedomain', '')
                            self.server.yt_replace_domain = None

                        # change twitter alternate domain
                        if fields.get('twitterdomain'):
                            currTwitterDomain = \
                                self.server.twitter_replacement_domain
                            if fields['twitterdomain'] != currTwitterDomain:
                                newTwitterDomain = fields['twitterdomain']
                                if '://' in newTwitterDomain:
                                    newTwitterDomain = \
                                        newTwitterDomain.split('://')[1]
                                if '/' in newTwitterDomain:
                                    newTwitterDomain = \
                                        newTwitterDomain.split('/')[0]
                                if '.' in newTwitterDomain:
                                    set_config_param(base_dir, 'twitterdomain',
                                                     newTwitterDomain)
                                    self.server.twitter_replacement_domain = \
                                        newTwitterDomain
                        else:
                            set_config_param(base_dir, 'twitterdomain', '')
                            self.server.twitter_replacement_domain = None

                        # change custom post submit button text
                        currCustomSubmitText = \
                            get_config_param(base_dir, 'customSubmitText')
                        if fields.get('customSubmitText'):
                            if fields['customSubmitText'] != \
                               currCustomSubmitText:
                                customText = fields['customSubmitText']
                                set_config_param(base_dir, 'customSubmitText',
                                                 customText)
                        else:
                            if currCustomSubmitText:
                                set_config_param(base_dir, 'customSubmitText',
                                                 '')

                        # libretranslate URL
                        currLibretranslateUrl = \
                            get_config_param(base_dir,
                                             'libretranslateUrl')
                        if fields.get('libretranslateUrl'):
                            if fields['libretranslateUrl'] != \
                               currLibretranslateUrl:
                                ltUrl = fields['libretranslateUrl']
                                if '://' in ltUrl and \
                                   '.' in ltUrl:
                                    set_config_param(base_dir,
                                                     'libretranslateUrl',
                                                     ltUrl)
                        else:
                            if currLibretranslateUrl:
                                set_config_param(base_dir,
                                                 'libretranslateUrl', '')

                        # libretranslate API Key
                        currLibretranslateApiKey = \
                            get_config_param(base_dir,
                                             'libretranslateApiKey')
                        if fields.get('libretranslateApiKey'):
                            if fields['libretranslateApiKey'] != \
                               currLibretranslateApiKey:
                                ltApiKey = fields['libretranslateApiKey']
                                set_config_param(base_dir,
                                                 'libretranslateApiKey',
                                                 ltApiKey)
                        else:
                            if currLibretranslateApiKey:
                                set_config_param(base_dir,
                                                 'libretranslateApiKey', '')

                        # change instance short description
                        if fields.get('contentLicenseUrl'):
                            if fields['contentLicenseUrl'] != \
                               self.server.content_license_url:
                                licenseStr = fields['contentLicenseUrl']
                                set_config_param(base_dir,
                                                 'contentLicenseUrl',
                                                 licenseStr)
                                self.server.content_license_url = \
                                    licenseStr
                        else:
                            licenseStr = \
                                'https://creativecommons.org/licenses/by/4.0'
                            set_config_param(base_dir,
                                             'contentLicenseUrl',
                                             licenseStr)
                            self.server.content_license_url = licenseStr

                        # change instance short description
                        currInstanceDescriptionShort = \
                            get_config_param(base_dir,
                                             'instanceDescriptionShort')
                        if fields.get('instanceDescriptionShort'):
                            if fields['instanceDescriptionShort'] != \
                               currInstanceDescriptionShort:
                                iDesc = fields['instanceDescriptionShort']
                                set_config_param(base_dir,
                                                 'instanceDescriptionShort',
                                                 iDesc)
                        else:
                            if currInstanceDescriptionShort:
                                set_config_param(base_dir,
                                                 'instanceDescriptionShort',
                                                 '')

                        # change instance description
                        currInstanceDescription = \
                            get_config_param(base_dir, 'instanceDescription')
                        if fields.get('instanceDescription'):
                            if fields['instanceDescription'] != \
                               currInstanceDescription:
                                set_config_param(base_dir,
                                                 'instanceDescription',
                                                 fields['instanceDescription'])
                        else:
                            if currInstanceDescription:
                                set_config_param(base_dir,
                                                 'instanceDescription', '')

                    # change email address
                    currentEmailAddress = get_email_address(actor_json)
                    if fields.get('email'):
                        if fields['email'] != currentEmailAddress:
                            set_email_address(actor_json, fields['email'])
                            actorChanged = True
                    else:
                        if currentEmailAddress:
                            set_email_address(actor_json, '')
                            actorChanged = True

                    # change xmpp address
                    currentXmppAddress = get_xmpp_address(actor_json)
                    if fields.get('xmppAddress'):
                        if fields['xmppAddress'] != currentXmppAddress:
                            set_xmpp_address(actor_json,
                                             fields['xmppAddress'])
                            actorChanged = True
                    else:
                        if currentXmppAddress:
                            set_xmpp_address(actor_json, '')
                            actorChanged = True

                    # change matrix address
                    currentMatrixAddress = get_matrix_address(actor_json)
                    if fields.get('matrixAddress'):
                        if fields['matrixAddress'] != currentMatrixAddress:
                            set_matrix_address(actor_json,
                                               fields['matrixAddress'])
                            actorChanged = True
                    else:
                        if currentMatrixAddress:
                            set_matrix_address(actor_json, '')
                            actorChanged = True

                    # change SSB address
                    currentSSBAddress = get_ssb_address(actor_json)
                    if fields.get('ssbAddress'):
                        if fields['ssbAddress'] != currentSSBAddress:
                            set_ssb_address(actor_json,
                                            fields['ssbAddress'])
                            actorChanged = True
                    else:
                        if currentSSBAddress:
                            set_ssb_address(actor_json, '')
                            actorChanged = True

                    # change blog address
                    currentBlogAddress = get_blog_address(actor_json)
                    if fields.get('blogAddress'):
                        if fields['blogAddress'] != currentBlogAddress:
                            set_blog_address(actor_json,
                                             fields['blogAddress'])
                            actorChanged = True
                    else:
                        if currentBlogAddress:
                            set_blog_address(actor_json, '')
                            actorChanged = True

                    # change Languages address
                    currentShowLanguages = get_actor_languages(actor_json)
                    if fields.get('showLanguages'):
                        if fields['showLanguages'] != currentShowLanguages:
                            set_actor_languages(base_dir, actor_json,
                                                fields['showLanguages'])
                            actorChanged = True
                    else:
                        if currentShowLanguages:
                            set_actor_languages(base_dir, actor_json, '')
                            actorChanged = True

                    # change tox address
                    currentToxAddress = get_tox_address(actor_json)
                    if fields.get('toxAddress'):
                        if fields['toxAddress'] != currentToxAddress:
                            set_tox_address(actor_json,
                                            fields['toxAddress'])
                            actorChanged = True
                    else:
                        if currentToxAddress:
                            set_tox_address(actor_json, '')
                            actorChanged = True

                    # change briar address
                    currentBriarAddress = get_briar_address(actor_json)
                    if fields.get('briarAddress'):
                        if fields['briarAddress'] != currentBriarAddress:
                            set_briar_address(actor_json,
                                              fields['briarAddress'])
                            actorChanged = True
                    else:
                        if currentBriarAddress:
                            set_briar_address(actor_json, '')
                            actorChanged = True

                    # change jami address
                    currentJamiAddress = get_jami_address(actor_json)
                    if fields.get('jamiAddress'):
                        if fields['jamiAddress'] != currentJamiAddress:
                            set_jami_address(actor_json,
                                             fields['jamiAddress'])
                            actorChanged = True
                    else:
                        if currentJamiAddress:
                            set_jami_address(actor_json, '')
                            actorChanged = True

                    # change cwtch address
                    currentCwtchAddress = get_cwtch_address(actor_json)
                    if fields.get('cwtchAddress'):
                        if fields['cwtchAddress'] != currentCwtchAddress:
                            set_cwtch_address(actor_json,
                                              fields['cwtchAddress'])
                            actorChanged = True
                    else:
                        if currentCwtchAddress:
                            set_cwtch_address(actor_json, '')
                            actorChanged = True

                    # change Enigma public key
                    currentenigma_pub_key = get_enigma_pub_key(actor_json)
                    if fields.get('enigmapubkey'):
                        if fields['enigmapubkey'] != currentenigma_pub_key:
                            set_enigma_pub_key(actor_json,
                                               fields['enigmapubkey'])
                            actorChanged = True
                    else:
                        if currentenigma_pub_key:
                            set_enigma_pub_key(actor_json, '')
                            actorChanged = True

                    # change PGP public key
                    currentpgp_pub_key = get_pgp_pub_key(actor_json)
                    if fields.get('pgp'):
                        if fields['pgp'] != currentpgp_pub_key:
                            set_pgp_pub_key(actor_json,
                                            fields['pgp'])
                            actorChanged = True
                    else:
                        if currentpgp_pub_key:
                            set_pgp_pub_key(actor_json, '')
                            actorChanged = True

                    # change PGP fingerprint
                    currentpgp_fingerprint = get_pgp_fingerprint(actor_json)
                    if fields.get('openpgp'):
                        if fields['openpgp'] != currentpgp_fingerprint:
                            set_pgp_fingerprint(actor_json,
                                                fields['openpgp'])
                            actorChanged = True
                    else:
                        if currentpgp_fingerprint:
                            set_pgp_fingerprint(actor_json, '')
                            actorChanged = True

                    # change donation link
                    currentDonateUrl = get_donation_url(actor_json)
                    if fields.get('donateUrl'):
                        if fields['donateUrl'] != currentDonateUrl:
                            set_donation_url(actor_json,
                                             fields['donateUrl'])
                            actorChanged = True
                    else:
                        if currentDonateUrl:
                            set_donation_url(actor_json, '')
                            actorChanged = True

                    # change website
                    currentWebsite = \
                        get_website(actor_json, self.server.translate)
                    if fields.get('websiteUrl'):
                        if fields['websiteUrl'] != currentWebsite:
                            set_website(actor_json,
                                        fields['websiteUrl'],
                                        self.server.translate)
                            actorChanged = True
                    else:
                        if currentWebsite:
                            set_website(actor_json, '', self.server.translate)
                            actorChanged = True

                    # account moved to new address
                    movedTo = ''
                    if actor_json.get('movedTo'):
                        movedTo = actor_json['movedTo']
                    if fields.get('movedTo'):
                        if fields['movedTo'] != movedTo and \
                           '://' in fields['movedTo'] and \
                           '.' in fields['movedTo']:
                            actor_json['movedTo'] = movedTo
                            actorChanged = True
                    else:
                        if movedTo:
                            del actor_json['movedTo']
                            actorChanged = True

                    # Other accounts (alsoKnownAs)
                    occupationName = get_occupation_name(actor_json)
                    if fields.get('occupationName'):
                        fields['occupationName'] = \
                            remove_html(fields['occupationName'])
                        if occupationName != \
                           fields['occupationName']:
                            set_occupation_name(actor_json,
                                                fields['occupationName'])
                            actorChanged = True
                    else:
                        if occupationName:
                            set_occupation_name(actor_json, '')
                            actorChanged = True

                    # Other accounts (alsoKnownAs)
                    alsoKnownAs = []
                    if actor_json.get('alsoKnownAs'):
                        alsoKnownAs = actor_json['alsoKnownAs']
                    if fields.get('alsoKnownAs'):
                        alsoKnownAsStr = ''
                        alsoKnownAsCtr = 0
                        for altActor in alsoKnownAs:
                            if alsoKnownAsCtr > 0:
                                alsoKnownAsStr += ', '
                            alsoKnownAsStr += altActor
                            alsoKnownAsCtr += 1
                        if fields['alsoKnownAs'] != alsoKnownAsStr and \
                           '://' in fields['alsoKnownAs'] and \
                           '@' not in fields['alsoKnownAs'] and \
                           '.' in fields['alsoKnownAs']:
                            if ';' in fields['alsoKnownAs']:
                                fields['alsoKnownAs'] = \
                                    fields['alsoKnownAs'].replace(';', ',')
                            newAlsoKnownAs = fields['alsoKnownAs'].split(',')
                            alsoKnownAs = []
                            for altActor in newAlsoKnownAs:
                                altActor = altActor.strip()
                                if '://' in altActor and '.' in altActor:
                                    if altActor not in alsoKnownAs:
                                        alsoKnownAs.append(altActor)
                            actor_json['alsoKnownAs'] = alsoKnownAs
                            actorChanged = True
                    else:
                        if alsoKnownAs:
                            del actor_json['alsoKnownAs']
                            actorChanged = True

                    # change user bio
                    if fields.get('bio'):
                        if fields['bio'] != actor_json['summary']:
                            bioStr = remove_html(fields['bio'])
                            if not is_filtered(base_dir,
                                               nickname, domain, bioStr):
                                actorTags = {}
                                actor_json['summary'] = \
                                    add_html_tags(base_dir,
                                                  http_prefix,
                                                  nickname,
                                                  domain_full,
                                                  bioStr, [], actorTags)
                                if actorTags:
                                    actor_json['tag'] = []
                                    for tagName, tag in actorTags.items():
                                        actor_json['tag'].append(tag)
                                actorChanged = True
                            else:
                                if checkNameAndBio:
                                    redirectPath = 'previewAvatar'
                    else:
                        if checkNameAndBio:
                            redirectPath = 'previewAvatar'

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
                            currBrochMode = \
                                get_config_param(base_dir, "brochMode")
                            if broch_mode != currBrochMode:
                                set_broch_mode(self.server.base_dir,
                                               self.server.domain_full,
                                               broch_mode)
                                set_config_param(base_dir, 'brochMode',
                                                 broch_mode)

                            # shared item federation domains
                            siDomainUpdated = False
                            fed_domains_variable = \
                                "sharedItemsFederatedDomains"
                            fed_domains_str = \
                                get_config_param(base_dir,
                                                 fed_domains_variable)
                            if not fed_domains_str:
                                fed_domains_str = ''
                            sharedItemsFormStr = ''
                            if fields.get('shareDomainList'):
                                sharedItemsList = \
                                    fed_domains_str.split(',')
                                for sharedFederatedDomain in sharedItemsList:
                                    sharedItemsFormStr += \
                                        sharedFederatedDomain.strip() + '\n'

                                shareDomainList = fields['shareDomainList']
                                if shareDomainList != \
                                   sharedItemsFormStr:
                                    sharedItemsFormStr2 = \
                                        shareDomainList.replace('\n', ',')
                                    sharedItemsField = \
                                        "sharedItemsFederatedDomains"
                                    set_config_param(base_dir,
                                                     sharedItemsField,
                                                     sharedItemsFormStr2)
                                    siDomainUpdated = True
                            else:
                                if fed_domains_str:
                                    sharedItemsField = \
                                        "sharedItemsFederatedDomains"
                                    set_config_param(base_dir,
                                                     sharedItemsField,
                                                     '')
                                    siDomainUpdated = True
                            if siDomainUpdated:
                                siDomains = sharedItemsFormStr.split('\n')
                                siTokens = \
                                    self.server.sharedItemFederationTokens
                                self.server.shared_items_federated_domains = \
                                    siDomains
                                domain_full = self.server.domain_full
                                base_dir = \
                                    self.server.base_dir
                                self.server.sharedItemFederationTokens = \
                                    merge_shared_item_tokens(base_dir,
                                                             domain_full,
                                                             siDomains,
                                                             siTokens)

                        # change moderators list
                        if fields.get('moderators'):
                            if path.startswith('/users/' +
                                               admin_nickname + '/'):
                                moderatorsFile = \
                                    base_dir + \
                                    '/accounts/moderators.txt'
                                clear_moderator_status(base_dir)
                                if ',' in fields['moderators']:
                                    # if the list was given as comma separated
                                    mods = fields['moderators'].split(',')
                                    try:
                                        with open(moderatorsFile,
                                                  'w+') as modFile:
                                            for modNick in mods:
                                                modNick = modNick.strip()
                                                modDir = base_dir + \
                                                    '/accounts/' + modNick + \
                                                    '@' + domain
                                                if os.path.isdir(modDir):
                                                    modFile.write(modNick +
                                                                  '\n')
                                    except OSError:
                                        print('EX: ' +
                                              'unable to write moderators ' +
                                              moderatorsFile)

                                    for modNick in mods:
                                        modNick = modNick.strip()
                                        modDir = base_dir + \
                                            '/accounts/' + modNick + \
                                            '@' + domain
                                        if os.path.isdir(modDir):
                                            set_role(base_dir,
                                                     modNick, domain,
                                                     'moderator')
                                else:
                                    # nicknames on separate lines
                                    mods = fields['moderators'].split('\n')
                                    try:
                                        with open(moderatorsFile,
                                                  'w+') as modFile:
                                            for modNick in mods:
                                                modNick = modNick.strip()
                                                modDir = \
                                                    base_dir + \
                                                    '/accounts/' + modNick + \
                                                    '@' + domain
                                                if os.path.isdir(modDir):
                                                    modFile.write(modNick +
                                                                  '\n')
                                    except OSError:
                                        print('EX: ' +
                                              'unable to write moderators 2 ' +
                                              moderatorsFile)

                                    for modNick in mods:
                                        modNick = modNick.strip()
                                        modDir = \
                                            base_dir + \
                                            '/accounts/' + \
                                            modNick + '@' + \
                                            domain
                                        if os.path.isdir(modDir):
                                            set_role(base_dir,
                                                     modNick, domain,
                                                     'moderator')

                        # change site editors list
                        if fields.get('editors'):
                            if path.startswith('/users/' +
                                               admin_nickname + '/'):
                                editorsFile = \
                                    base_dir + \
                                    '/accounts/editors.txt'
                                clear_editor_status(base_dir)
                                if ',' in fields['editors']:
                                    # if the list was given as comma separated
                                    eds = fields['editors'].split(',')
                                    try:
                                        with open(editorsFile, 'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: unable to write editors ' +
                                              editorsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = base_dir + \
                                            '/accounts/' + edNick + \
                                            '@' + domain
                                        if os.path.isdir(edDir):
                                            set_role(base_dir,
                                                     edNick, domain,
                                                     'editor')
                                else:
                                    # nicknames on separate lines
                                    eds = fields['editors'].split('\n')
                                    try:
                                        with open(editorsFile,
                                                  'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = \
                                                    base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: unable to write editors ' +
                                              editorsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = \
                                            base_dir + \
                                            '/accounts/' + \
                                            edNick + '@' + \
                                            domain
                                        if os.path.isdir(edDir):
                                            set_role(base_dir,
                                                     edNick, domain,
                                                     'editor')

                        # change site counselors list
                        if fields.get('counselors'):
                            if path.startswith('/users/' +
                                               admin_nickname + '/'):
                                counselorsFile = \
                                    base_dir + \
                                    '/accounts/counselors.txt'
                                clear_counselor_status(base_dir)
                                if ',' in fields['counselors']:
                                    # if the list was given as comma separated
                                    eds = fields['counselors'].split(',')
                                    try:
                                        with open(counselorsFile,
                                                  'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: ' +
                                              'unable to write counselors ' +
                                              counselorsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = base_dir + \
                                            '/accounts/' + edNick + \
                                            '@' + domain
                                        if os.path.isdir(edDir):
                                            set_role(base_dir,
                                                     edNick, domain,
                                                     'counselor')
                                else:
                                    # nicknames on separate lines
                                    eds = fields['counselors'].split('\n')
                                    try:
                                        with open(counselorsFile,
                                                  'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = \
                                                    base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: ' +
                                              'unable to write counselors ' +
                                              counselorsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = \
                                            base_dir + \
                                            '/accounts/' + \
                                            edNick + '@' + \
                                            domain
                                        if os.path.isdir(edDir):
                                            set_role(base_dir,
                                                     edNick, domain,
                                                     'counselor')

                        # change site artists list
                        if fields.get('artists'):
                            if path.startswith('/users/' +
                                               admin_nickname + '/'):
                                artistsFile = \
                                    base_dir + \
                                    '/accounts/artists.txt'
                                clear_artist_status(base_dir)
                                if ',' in fields['artists']:
                                    # if the list was given as comma separated
                                    eds = fields['artists'].split(',')
                                    try:
                                        with open(artistsFile, 'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: unable to write artists ' +
                                              artistsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = base_dir + \
                                            '/accounts/' + edNick + \
                                            '@' + domain
                                        if os.path.isdir(edDir):
                                            set_role(base_dir,
                                                     edNick, domain,
                                                     'artist')
                                else:
                                    # nicknames on separate lines
                                    eds = fields['artists'].split('\n')
                                    try:
                                        with open(artistsFile, 'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = \
                                                    base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: unable to write artists ' +
                                              artistsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = \
                                            base_dir + \
                                            '/accounts/' + \
                                            edNick + '@' + \
                                            domain
                                        if os.path.isdir(edDir):
                                            set_role(base_dir,
                                                     edNick, domain,
                                                     'artist')

                    # remove scheduled posts
                    if fields.get('removeScheduledPosts'):
                        if fields['removeScheduledPosts'] == 'on':
                            remove_scheduled_posts(base_dir,
                                                   nickname, domain)

                    # approve followers
                    if onFinalWelcomeScreen:
                        # Default setting created via the welcome screen
                        actor_json['manuallyApprovesFollowers'] = True
                        actorChanged = True
                    else:
                        approveFollowers = False
                        if fields.get('approveFollowers'):
                            if fields['approveFollowers'] == 'on':
                                approveFollowers = True
                        if approveFollowers != \
                           actor_json['manuallyApprovesFollowers']:
                            actor_json['manuallyApprovesFollowers'] = \
                                approveFollowers
                            actorChanged = True

                    # remove a custom font
                    if fields.get('removeCustomFont'):
                        if (fields['removeCustomFont'] == 'on' and
                            (is_artist(base_dir, nickname) or
                             path.startswith('/users/' +
                                             admin_nickname + '/'))):
                            fontExt = ('woff', 'woff2', 'otf', 'ttf')
                            for ext in fontExt:
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
                            currTheme = get_theme(base_dir)
                            if currTheme:
                                self.server.theme_name = currTheme
                                allow_local_network_access = \
                                    self.server.allow_local_network_access
                                set_theme(base_dir, currTheme, domain,
                                          allow_local_network_access,
                                          system_language)
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
                    followDMsFilename = \
                        acct_dir(base_dir, nickname, domain) + '/.followDMs'
                    if onFinalWelcomeScreen:
                        # initial default setting created via
                        # the welcome screen
                        try:
                            with open(followDMsFilename, 'w+') as fFile:
                                fFile.write('\n')
                        except OSError:
                            print('EX: unable to write follow DMs ' +
                                  followDMsFilename)
                        actorChanged = True
                    else:
                        followDMsActive = False
                        if fields.get('followDMs'):
                            if fields['followDMs'] == 'on':
                                followDMsActive = True
                                try:
                                    with open(followDMsFilename,
                                              'w+') as fFile:
                                        fFile.write('\n')
                                except OSError:
                                    print('EX: unable to write follow DMs 2 ' +
                                          followDMsFilename)
                        if not followDMsActive:
                            if os.path.isfile(followDMsFilename):
                                try:
                                    os.remove(followDMsFilename)
                                except OSError:
                                    print('EX: _profile_edit ' +
                                          'unable to delete ' +
                                          followDMsFilename)

                    # remove Twitter retweets
                    removeTwitterFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/.removeTwitter'
                    removeTwitterActive = False
                    if fields.get('removeTwitter'):
                        if fields['removeTwitter'] == 'on':
                            removeTwitterActive = True
                            try:
                                with open(removeTwitterFilename,
                                          'w+') as rFile:
                                    rFile.write('\n')
                            except OSError:
                                print('EX: unable to write remove twitter ' +
                                      removeTwitterFilename)
                    if not removeTwitterActive:
                        if os.path.isfile(removeTwitterFilename):
                            try:
                                os.remove(removeTwitterFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      removeTwitterFilename)

                    # hide Like button
                    hideLikeButtonFile = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/.hideLikeButton'
                    notifyLikesFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/.notifyLikes'
                    hideLikeButtonActive = False
                    if fields.get('hideLikeButton'):
                        if fields['hideLikeButton'] == 'on':
                            hideLikeButtonActive = True
                            try:
                                with open(hideLikeButtonFile, 'w+') as rFile:
                                    rFile.write('\n')
                            except OSError:
                                print('EX: unable to write hide like ' +
                                      hideLikeButtonFile)
                            # remove notify likes selection
                            if os.path.isfile(notifyLikesFilename):
                                try:
                                    os.remove(notifyLikesFilename)
                                except OSError:
                                    print('EX: _profile_edit ' +
                                          'unable to delete ' +
                                          notifyLikesFilename)
                    if not hideLikeButtonActive:
                        if os.path.isfile(hideLikeButtonFile):
                            try:
                                os.remove(hideLikeButtonFile)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      hideLikeButtonFile)

                    # hide Reaction button
                    hideReactionButtonFile = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/.hideReactionButton'
                    notifyReactionsFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/.notifyReactions'
                    hideReactionButtonActive = False
                    if fields.get('hideReactionButton'):
                        if fields['hideReactionButton'] == 'on':
                            hideReactionButtonActive = True
                            try:
                                with open(hideReactionButtonFile,
                                          'w+') as rFile:
                                    rFile.write('\n')
                            except OSError:
                                print('EX: unable to write hide reaction ' +
                                      hideReactionButtonFile)
                            # remove notify Reaction selection
                            if os.path.isfile(notifyReactionsFilename):
                                try:
                                    os.remove(notifyReactionsFilename)
                                except OSError:
                                    print('EX: _profile_edit ' +
                                          'unable to delete ' +
                                          notifyReactionsFilename)
                    if not hideReactionButtonActive:
                        if os.path.isfile(hideReactionButtonFile):
                            try:
                                os.remove(hideReactionButtonFile)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      hideReactionButtonFile)

                    # notify about new Likes
                    if onFinalWelcomeScreen:
                        # default setting from welcome screen
                        try:
                            with open(notifyLikesFilename, 'w+') as rFile:
                                rFile.write('\n')
                        except OSError:
                            print('EX: unable to write notify likes ' +
                                  notifyLikesFilename)
                        actorChanged = True
                    else:
                        notifyLikesActive = False
                        if fields.get('notifyLikes'):
                            if fields['notifyLikes'] == 'on' and \
                               not hideLikeButtonActive:
                                notifyLikesActive = True
                                try:
                                    with open(notifyLikesFilename,
                                              'w+') as rFile:
                                        rFile.write('\n')
                                except OSError:
                                    print('EX: unable to write notify likes ' +
                                          notifyLikesFilename)
                        if not notifyLikesActive:
                            if os.path.isfile(notifyLikesFilename):
                                try:
                                    os.remove(notifyLikesFilename)
                                except OSError:
                                    print('EX: _profile_edit ' +
                                          'unable to delete ' +
                                          notifyLikesFilename)

                    notifyReactionsFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/.notifyReactions'
                    if onFinalWelcomeScreen:
                        # default setting from welcome screen
                        try:
                            with open(notifyReactionsFilename, 'w+') as rFile:
                                rFile.write('\n')
                        except OSError:
                            print('EX: unable to write notify reactions ' +
                                  notifyReactionsFilename)
                        actorChanged = True
                    else:
                        notifyReactionsActive = False
                        if fields.get('notifyReactions'):
                            if fields['notifyReactions'] == 'on' and \
                               not hideReactionButtonActive:
                                notifyReactionsActive = True
                                try:
                                    with open(notifyReactionsFilename,
                                              'w+') as rFile:
                                        rFile.write('\n')
                                except OSError:
                                    print('EX: unable to write ' +
                                          'notify reactions ' +
                                          notifyReactionsFilename)
                        if not notifyReactionsActive:
                            if os.path.isfile(notifyReactionsFilename):
                                try:
                                    os.remove(notifyReactionsFilename)
                                except OSError:
                                    print('EX: _profile_edit ' +
                                          'unable to delete ' +
                                          notifyReactionsFilename)

                    # this account is a bot
                    if fields.get('isBot'):
                        if fields['isBot'] == 'on':
                            if actor_json['type'] != 'Service':
                                actor_json['type'] = 'Service'
                                actorChanged = True
                    else:
                        # this account is a group
                        if fields.get('isGroup'):
                            if fields['isGroup'] == 'on':
                                if actor_json['type'] != 'Group':
                                    # only allow admin to create groups
                                    if path.startswith('/users/' +
                                                       admin_nickname + '/'):
                                        actor_json['type'] = 'Group'
                                        actorChanged = True
                        else:
                            # this account is a person (default)
                            if actor_json['type'] != 'Person':
                                actor_json['type'] = 'Person'
                                actorChanged = True

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

                    # low bandwidth images checkbox
                    if path.startswith('/users/' + admin_nickname + '/') or \
                       is_artist(base_dir, nickname):
                        currLowBandwidth = \
                            get_config_param(base_dir, 'lowBandwidth')
                        low_bandwidth = False
                        if fields.get('lowBandwidth'):
                            if fields['lowBandwidth'] == 'on':
                                low_bandwidth = True
                        if currLowBandwidth != low_bandwidth:
                            set_config_param(base_dir, 'lowBandwidth',
                                             low_bandwidth)
                            self.server.low_bandwidth = low_bandwidth

                    # save filtered words list
                    filterFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/filters.txt'
                    if fields.get('filteredWords'):
                        try:
                            with open(filterFilename, 'w+') as filterfile:
                                filterfile.write(fields['filteredWords'])
                        except OSError:
                            print('EX: unable to write filter ' +
                                  filterFilename)
                    else:
                        if os.path.isfile(filterFilename):
                            try:
                                os.remove(filterFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete filter ' +
                                      filterFilename)

                    # save filtered words within bio list
                    filterBioFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/filters_bio.txt'
                    if fields.get('filteredWordsBio'):
                        try:
                            with open(filterBioFilename, 'w+') as filterfile:
                                filterfile.write(fields['filteredWordsBio'])
                        except OSError:
                            print('EX: unable to write bio filter ' +
                                  filterBioFilename)
                    else:
                        if os.path.isfile(filterBioFilename):
                            try:
                                os.remove(filterBioFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete bio filter ' +
                                      filterBioFilename)

                    # word replacements
                    switchFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/replacewords.txt'
                    if fields.get('switchwords'):
                        try:
                            with open(switchFilename, 'w+') as switchfile:
                                switchfile.write(fields['switchwords'])
                        except OSError:
                            print('EX: unable to write switches ' +
                                  switchFilename)
                    else:
                        if os.path.isfile(switchFilename):
                            try:
                                os.remove(switchFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      switchFilename)

                    # autogenerated tags
                    autoTagsFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/autotags.txt'
                    if fields.get('autoTags'):
                        try:
                            with open(autoTagsFilename, 'w+') as autoTagsFile:
                                autoTagsFile.write(fields['autoTags'])
                        except OSError:
                            print('EX: unable to write auto tags ' +
                                  autoTagsFilename)
                    else:
                        if os.path.isfile(autoTagsFilename):
                            try:
                                os.remove(autoTagsFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      autoTagsFilename)

                    # autogenerated content warnings
                    autoCWFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/autocw.txt'
                    if fields.get('autoCW'):
                        try:
                            with open(autoCWFilename, 'w+') as autoCWFile:
                                autoCWFile.write(fields['autoCW'])
                        except OSError:
                            print('EX: unable to write auto CW ' +
                                  autoCWFilename)
                    else:
                        if os.path.isfile(autoCWFilename):
                            try:
                                os.remove(autoCWFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      autoCWFilename)

                    # save blocked accounts list
                    blockedFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/blocking.txt'
                    if fields.get('blocked'):
                        try:
                            with open(blockedFilename, 'w+') as blockedfile:
                                blockedfile.write(fields['blocked'])
                        except OSError:
                            print('EX: unable to write blocked accounts ' +
                                  blockedFilename)
                    else:
                        if os.path.isfile(blockedFilename):
                            try:
                                os.remove(blockedFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      blockedFilename)

                    # Save DM allowed instances list.
                    # The allow list for incoming DMs,
                    # if the .followDMs flag file exists
                    dmAllowedInstancesFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/dmAllowedinstances.txt'
                    if fields.get('dmAllowedInstances'):
                        try:
                            with open(dmAllowedInstancesFilename,
                                      'w+') as aFile:
                                aFile.write(fields['dmAllowedInstances'])
                        except OSError:
                            print('EX: unable to write allowed DM instances ' +
                                  dmAllowedInstancesFilename)
                    else:
                        if os.path.isfile(dmAllowedInstancesFilename):
                            try:
                                os.remove(dmAllowedInstancesFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      dmAllowedInstancesFilename)

                    # save allowed instances list
                    # This is the account level allow list
                    allowedInstancesFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/allowedinstances.txt'
                    if fields.get('allowedInstances'):
                        try:
                            with open(allowedInstancesFilename, 'w+') as aFile:
                                aFile.write(fields['allowedInstances'])
                        except OSError:
                            print('EX: unable to write allowed instances ' +
                                  allowedInstancesFilename)
                    else:
                        if os.path.isfile(allowedInstancesFilename):
                            try:
                                os.remove(allowedInstancesFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      allowedInstancesFilename)

                    if is_moderator(self.server.base_dir, nickname):
                        # set selected content warning lists
                        newListsEnabled = ''
                        for name, item in self.server.cw_lists.items():
                            listVarName = get_cw_list_variable(name)
                            if fields.get(listVarName):
                                if fields[listVarName] == 'on':
                                    if newListsEnabled:
                                        newListsEnabled += ', ' + name
                                    else:
                                        newListsEnabled += name
                        if newListsEnabled != self.server.lists_enabled:
                            self.server.lists_enabled = newListsEnabled
                            set_config_param(self.server.base_dir,
                                             "listsEnabled",
                                             newListsEnabled)

                        # save blocked user agents
                        user_agents_blocked = []
                        if fields.get('userAgentsBlockedStr'):
                            user_agents_blockedStr = \
                                fields['userAgentsBlockedStr']
                            user_agents_blockedList = \
                                user_agents_blockedStr.split('\n')
                            for ua in user_agents_blockedList:
                                if ua in user_agents_blocked:
                                    continue
                                user_agents_blocked.append(ua.strip())
                        if str(self.server.user_agents_blocked) != \
                           str(user_agents_blocked):
                            self.server.user_agents_blocked = \
                                user_agents_blocked
                            user_agents_blockedStr = ''
                            for ua in user_agents_blocked:
                                if user_agents_blockedStr:
                                    user_agents_blockedStr += ','
                                user_agents_blockedStr += ua
                            set_config_param(base_dir, 'user_agents_blocked',
                                             user_agents_blockedStr)

                        # save peertube instances list
                        peertube_instancesFile = \
                            base_dir + '/accounts/peertube.txt'
                        if fields.get('ptInstances'):
                            self.server.peertube_instances.clear()
                            try:
                                with open(peertube_instancesFile,
                                          'w+') as aFile:
                                    aFile.write(fields['ptInstances'])
                            except OSError:
                                print('EX: unable to write peertube ' +
                                      peertube_instancesFile)
                            ptInstancesList = \
                                fields['ptInstances'].split('\n')
                            if ptInstancesList:
                                for url in ptInstancesList:
                                    url = url.strip()
                                    if not url:
                                        continue
                                    if url in self.server.peertube_instances:
                                        continue
                                    self.server.peertube_instances.append(url)
                        else:
                            if os.path.isfile(peertube_instancesFile):
                                try:
                                    os.remove(peertube_instancesFile)
                                except OSError:
                                    print('EX: _profile_edit ' +
                                          'unable to delete ' +
                                          peertube_instancesFile)
                            self.server.peertube_instances.clear()

                    # save git project names list
                    gitProjectsFilename = \
                        acct_dir(base_dir, nickname, domain) + \
                        '/gitprojects.txt'
                    if fields.get('gitProjects'):
                        try:
                            with open(gitProjectsFilename, 'w+') as aFile:
                                aFile.write(fields['gitProjects'].lower())
                        except OSError:
                            print('EX: unable to write git ' +
                                  gitProjectsFilename)
                    else:
                        if os.path.isfile(gitProjectsFilename):
                            try:
                                os.remove(gitProjectsFilename)
                            except OSError:
                                print('EX: _profile_edit ' +
                                      'unable to delete ' +
                                      gitProjectsFilename)

                    # save actor json file within accounts
                    if actorChanged:
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
                        save_json(actor_json, actorFilename)
                        webfinger_update(base_dir,
                                         nickname, domain,
                                         onion_domain,
                                         self.server.cached_webfingers)
                        # also copy to the actors cache and
                        # person_cache in memory
                        store_person_in_cache(base_dir,
                                              actor_json['id'], actor_json,
                                              self.server.person_cache,
                                              True)
                        # clear any cached images for this actor
                        idStr = actor_json['id'].replace('/', '-')
                        remove_avatar_from_cache(base_dir, idStr)
                        # save the actor to the cache
                        actorCacheFilename = \
                            base_dir + '/cache/actors/' + \
                            actor_json['id'].replace('/', '#') + '.json'
                        save_json(actor_json, actorCacheFilename)
                        # send profile update to followers
                        pubNumber, pubDate = get_status_number()
                        updateActorJson = get_actor_update_json(actor_json)
                        print('Sending actor update: ' + str(updateActorJson))
                        self._post_to_outbox(updateActorJson,
                                             self.server.project_version,
                                             nickname)

                    # deactivate the account
                    if fields.get('deactivateThisAccount'):
                        if fields['deactivateThisAccount'] == 'on':
                            deactivate_account(base_dir,
                                               nickname, domain)
                            self._clear_login_details(nickname,
                                                      calling_domain)
                            self.server.POSTbusy = False
                            return

        # redirect back to the profile screen
        self._redirect_headers(actorStr + redirectPath,
                               cookie, calling_domain)
        self.server.POSTbusy = False

    def _progressive_web_app_manifest(self, calling_domain: str,
                                      GETstartTime) -> None:
        """gets the PWA manifest
        """
        app1 = "https://f-droid.org/en/packages/eu.siacs.conversations"
        app2 = "https://staging.f-droid.org/en/packages/im.vector.app"
        manifest = {
            "name": "Epicyon",
            "short_name": "Epicyon",
            "start_url": "/index.html",
            "display": "standalone",
            "background_color": "black",
            "theme_color": "grey",
            "orientation": "portrait-primary",
            "categories": ["microblog", "fediverse", "activitypub"],
            "screenshots": [
                {
                    "src": "/mobile.jpg",
                    "sizes": "418x851",
                    "type": "image/jpeg"
                },
                {
                    "src": "/mobile_person.jpg",
                    "sizes": "429x860",
                    "type": "image/jpeg"
                },
                {
                    "src": "/mobile_search.jpg",
                    "sizes": "422x861",
                    "type": "image/jpeg"
                }
            ],
            "icons": [
                {
                    "src": "/logo72.png",
                    "type": "image/png",
                    "sizes": "72x72"
                },
                {
                    "src": "/logo96.png",
                    "type": "image/png",
                    "sizes": "96x96"
                },
                {
                    "src": "/logo128.png",
                    "type": "image/png",
                    "sizes": "128x128"
                },
                {
                    "src": "/logo144.png",
                    "type": "image/png",
                    "sizes": "144x144"
                },
                {
                    "src": "/logo150.png",
                    "type": "image/png",
                    "sizes": "150x150"
                },
                {
                    "src": "/apple-touch-icon.png",
                    "type": "image/png",
                    "sizes": "180x180"
                },
                {
                    "src": "/logo192.png",
                    "type": "image/png",
                    "sizes": "192x192"
                },
                {
                    "src": "/logo256.png",
                    "type": "image/png",
                    "sizes": "256x256"
                },
                {
                    "src": "/logo512.png",
                    "type": "image/png",
                    "sizes": "512x512"
                }
            ],
            "related_applications": [
                {
                    "platform": "fdroid",
                    "url": app1
                },
                {
                    "platform": "fdroid",
                    "url": app2
                }
            ]
        }
        msg = json.dumps(manifest,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json', msglen,
                          None, calling_domain, False)
        self._write(msg)
        if self.server.debug:
            print('Sent manifest: ' + calling_domain)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_progressive_web_app_manifest',
                            self.server.debug)

    def _browser_config(self, calling_domain: str, GETstartTime) -> None:
        """Used by MS Windows to put an icon on the desktop if you
        link to a website
        """
        xmlStr = \
            '<?xml version="1.0" encoding="utf-8"?>\n' + \
            '<browserconfig>\n' + \
            '  <msapplication>\n' + \
            '    <tile>\n' + \
            '      <square150x150logo src="/logo150.png"/>\n' + \
            '      <TileColor>#eeeeee</TileColor>\n' + \
            '    </tile>\n' + \
            '  </msapplication>\n' + \
            '</browserconfig>'

        msg = json.dumps(xmlStr,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/xrd+xml', msglen,
                          None, calling_domain, False)
        self._write(msg)
        if self.server.debug:
            print('Sent browserconfig: ' + calling_domain)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_browser_config',
                            self.server.debug)

    def _get_favicon(self, calling_domain: str,
                     base_dir: str, debug: bool,
                     favFilename: str) -> None:
        """Return the site favicon or default newswire favicon
        """
        favType = 'image/x-icon'
        if self._has_accept(calling_domain):
            if 'image/webp' in self.headers['Accept']:
                favType = 'image/webp'
                favFilename = favFilename.split('.')[0] + '.webp'
            if 'image/avif' in self.headers['Accept']:
                favType = 'image/avif'
                favFilename = favFilename.split('.')[0] + '.avif'
        if not self.server.theme_name:
            self.theme_name = get_config_param(base_dir, 'theme')
        if not self.server.theme_name:
            self.server.theme_name = 'default'
        # custom favicon
        faviconFilename = \
            base_dir + '/theme/' + self.server.theme_name + \
            '/icons/' + favFilename
        if not favFilename.endswith('.ico'):
            if not os.path.isfile(faviconFilename):
                if favFilename.endswith('.webp'):
                    favFilename = favFilename.replace('.webp', '.ico')
                elif favFilename.endswith('.avif'):
                    favFilename = favFilename.replace('.avif', '.ico')
        if not os.path.isfile(faviconFilename):
            # default favicon
            faviconFilename = \
                base_dir + '/theme/default/icons/' + favFilename
        if self._etag_exists(faviconFilename):
            # The file has not changed
            if debug:
                print('favicon icon has not changed: ' + calling_domain)
            self._304()
            return
        if self.server.iconsCache.get(favFilename):
            favBinary = self.server.iconsCache[favFilename]
            self._set_headers_etag(faviconFilename,
                                   favType,
                                   favBinary, None,
                                   self.server.domain_full,
                                   False, None)
            self._write(favBinary)
            if debug:
                print('Sent favicon from cache: ' + calling_domain)
            return
        else:
            if os.path.isfile(faviconFilename):
                favBinary = None
                try:
                    with open(faviconFilename, 'rb') as favFile:
                        favBinary = favFile.read()
                except OSError:
                    print('EX: unable to read favicon ' + faviconFilename)
                if favBinary:
                    self._set_headers_etag(faviconFilename,
                                           favType,
                                           favBinary, None,
                                           self.server.domain_full,
                                           False, None)
                    self._write(favBinary)
                    self.server.iconsCache[favFilename] = favBinary
                    if self.server.debug:
                        print('Sent favicon from file: ' + calling_domain)
                    return
        if debug:
            print('favicon not sent: ' + calling_domain)
        self._404()

    def _get_speaker(self, calling_domain: str, path: str,
                     base_dir: str, domain: str, debug: bool) -> None:
        """Returns the speaker file used for TTS and
        accessed via c2s
        """
        nickname = path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        speakerFilename = \
            acct_dir(base_dir, nickname, domain) + '/speaker.json'
        if not os.path.isfile(speakerFilename):
            self._404()
            return

        speakerJson = load_json(speakerFilename)
        msg = json.dumps(speakerJson,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json', msglen,
                          None, calling_domain, False)
        self._write(msg)

    def _get_exported_theme(self, calling_domain: str, path: str,
                            base_dir: str, domain_full: str,
                            debug: bool) -> None:
        """Returns an exported theme zip file
        """
        filename = path.split('/exports/', 1)[1]
        filename = base_dir + '/exports/' + filename
        if os.path.isfile(filename):
            exportBinary = None
            try:
                with open(filename, 'rb') as fp:
                    exportBinary = fp.read()
            except OSError:
                print('EX: unable to read theme export ' + filename)
            if exportBinary:
                exportType = 'application/zip'
                self._set_headers_etag(filename, exportType,
                                       exportBinary, None,
                                       domain_full, False, None)
                self._write(exportBinary)
        self._404()

    def _get_fonts(self, calling_domain: str, path: str,
                   base_dir: str, debug: bool,
                   GETstartTime) -> None:
        """Returns a font
        """
        fontStr = path.split('/fonts/')[1]
        if fontStr.endswith('.otf') or \
           fontStr.endswith('.ttf') or \
           fontStr.endswith('.woff') or \
           fontStr.endswith('.woff2'):
            if fontStr.endswith('.otf'):
                fontType = 'font/otf'
            elif fontStr.endswith('.ttf'):
                fontType = 'font/ttf'
            elif fontStr.endswith('.woff'):
                fontType = 'font/woff'
            else:
                fontType = 'font/woff2'
            fontFilename = \
                base_dir + '/fonts/' + fontStr
            if self._etag_exists(fontFilename):
                # The file has not changed
                self._304()
                return
            if self.server.fontsCache.get(fontStr):
                fontBinary = self.server.fontsCache[fontStr]
                self._set_headers_etag(fontFilename,
                                       fontType,
                                       fontBinary, None,
                                       self.server.domain_full, False, None)
                self._write(fontBinary)
                if debug:
                    print('font sent from cache: ' +
                          path + ' ' + calling_domain)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_get_fonts cache',
                                    self.server.debug)
                return
            else:
                if os.path.isfile(fontFilename):
                    fontBinary = None
                    try:
                        with open(fontFilename, 'rb') as fontFile:
                            fontBinary = fontFile.read()
                    except OSError:
                        print('EX: unable to load font ' + fontFilename)
                    if fontBinary:
                        self._set_headers_etag(fontFilename,
                                               fontType,
                                               fontBinary, None,
                                               self.server.domain_full,
                                               False, None)
                        self._write(fontBinary)
                        self.server.fontsCache[fontStr] = fontBinary
                    if debug:
                        print('font sent from file: ' +
                              path + ' ' + calling_domain)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', '_get_fonts',
                                        self.server.debug)
                    return
        if debug:
            print('font not found: ' + path + ' ' + calling_domain)
        self._404()

    def _get_rss2feed(self, authorized: bool,
                      calling_domain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, port: int, proxy_type: str,
                      GETstartTime,
                      debug: bool) -> None:
        """Returns an RSS2 feed for the blog
        """
        nickname = path.split('/blog/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not nickname.startswith('rss.'):
            accountDir = acct_dir(self.server.base_dir, nickname, domain)
            if os.path.isdir(accountDir):
                if not self._establish_session("RSS request"):
                    return

                msg = \
                    html_blog_page_rss2(authorized,
                                        self.server.session,
                                        base_dir,
                                        http_prefix,
                                        self.server.translate,
                                        nickname,
                                        domain,
                                        port,
                                        max_posts_in_rss_feed, 1,
                                        True,
                                        self.server.system_language)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/xml', msglen,
                                      None, calling_domain, True)
                    self._write(msg)
                    if debug:
                        print('Sent rss2 feed: ' +
                              path + ' ' + calling_domain)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', '_get_rss2feed',
                                        debug)
                    return
        if debug:
            print('Failed to get rss2 feed: ' +
                  path + ' ' + calling_domain)
        self._404()

    def _get_rss2site(self, authorized: bool,
                      calling_domain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain_full: str, port: int, proxy_type: str,
                      translate: {},
                      GETstartTime,
                      debug: bool) -> None:
        """Returns an RSS2 feed for all blogs on this instance
        """
        if not self._establish_session("get_rss2site"):
            self._404()
            return

        msg = ''
        for subdir, dirs, files in os.walk(base_dir + '/accounts'):
            for acct in dirs:
                if not is_account_dir(acct):
                    continue
                nickname = acct.split('@')[0]
                domain = acct.split('@')[1]
                msg += \
                    html_blog_page_rss2(authorized,
                                        self.server.session,
                                        base_dir,
                                        http_prefix,
                                        self.server.translate,
                                        nickname,
                                        domain,
                                        port,
                                        max_posts_in_rss_feed, 1,
                                        False,
                                        self.server.system_language)
            break
        if msg:
            msg = rss2header(http_prefix,
                             'news', domain_full,
                             'Site', translate) + msg + rss2footer()

            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/xml', msglen,
                              None, calling_domain, True)
            self._write(msg)
            if debug:
                print('Sent rss2 feed: ' +
                      path + ' ' + calling_domain)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_get_rss2site',
                                debug)
            return
        if debug:
            print('Failed to get rss2 feed: ' +
                  path + ' ' + calling_domain)
        self._404()

    def _get_newswire_feed(self, authorized: bool,
                           calling_domain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, port: int, proxy_type: str,
                           GETstartTime,
                           debug: bool) -> None:
        """Returns the newswire feed
        """
        if not self._establish_session("getNewswireFeed"):
            self._404()
            return

        msg = get_rs_sfrom_dict(self.server.base_dir, self.server.newswire,
                                self.server.http_prefix,
                                self.server.domain_full,
                                'Newswire', self.server.translate)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/xml', msglen,
                              None, calling_domain, True)
            self._write(msg)
            if debug:
                print('Sent rss2 newswire feed: ' +
                      path + ' ' + calling_domain)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_get_newswire_feed',
                                debug)
            return
        if debug:
            print('Failed to get rss2 newswire feed: ' +
                  path + ' ' + calling_domain)
        self._404()

    def _get_hashtag_categories_feed(self, authorized: bool,
                                     calling_domain: str, path: str,
                                     base_dir: str, http_prefix: str,
                                     domain: str, port: int, proxy_type: str,
                                     GETstartTime,
                                     debug: bool) -> None:
        """Returns the hashtag categories feed
        """
        if not self._establish_session("get_hashtag_categories_feed"):
            self._404()
            return

        hashtagCategories = None
        msg = \
            get_hashtag_categories_feed(base_dir, hashtagCategories)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/xml', msglen,
                              None, calling_domain, True)
            self._write(msg)
            if debug:
                print('Sent rss2 categories feed: ' +
                      path + ' ' + calling_domain)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_get_hashtag_categories_feed', debug)
            return
        if debug:
            print('Failed to get rss2 categories feed: ' +
                  path + ' ' + calling_domain)
        self._404()

    def _get_rss3feed(self, authorized: bool,
                      calling_domain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, port: int, proxy_type: str,
                      GETstartTime,
                      debug: bool, system_language: str) -> None:
        """Returns an RSS3 feed
        """
        nickname = path.split('/blog/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not nickname.startswith('rss.'):
            accountDir = acct_dir(base_dir, nickname, domain)
            if os.path.isdir(accountDir):
                if not self._establish_session("get_rss3Feed"):
                    self._404()
                    return
                msg = \
                    html_blog_page_rss3(authorized,
                                        self.server.session,
                                        base_dir, http_prefix,
                                        self.server.translate,
                                        nickname, domain, port,
                                        max_posts_in_rss_feed, 1,
                                        system_language)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/plain; charset=utf-8',
                                      msglen, None, calling_domain, True)
                    self._write(msg)
                    if self.server.debug:
                        print('Sent rss3 feed: ' +
                              path + ' ' + calling_domain)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', '_get_rss3feed', debug)
                    return
        if debug:
            print('Failed to get rss3 feed: ' +
                  path + ' ' + calling_domain)
        self._404()

    def _show_person_options(self, calling_domain: str, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str,
                             GETstartTime,
                             onion_domain: str, i2p_domain: str,
                             cookie: str, debug: bool,
                             authorized: bool) -> None:
        """Show person options screen
        """
        backToPath = ''
        optionsStr = path.split('?options=')[1]
        originPathStr = path.split('?options=')[0]
        if ';' in optionsStr and '/users/news/' not in path:
            page_number = 1
            optionsList = optionsStr.split(';')
            optionsActor = optionsList[0]
            optionsPageNumber = optionsList[1]
            optionsProfileUrl = optionsList[2]
            if '.' in optionsProfileUrl and \
               optionsProfileUrl.startswith('/members/'):
                ext = optionsProfileUrl.split('.')[-1]
                optionsProfileUrl = optionsProfileUrl.split('/members/')[1]
                optionsProfileUrl = optionsProfileUrl.replace('.' + ext, '')
                optionsProfileUrl = \
                    '/users/' + optionsProfileUrl + '/avatar.' + ext
                backToPath = 'moderation'
            if optionsPageNumber.isdigit():
                page_number = int(optionsPageNumber)
            optionsLink = None
            if len(optionsList) > 3:
                optionsLink = optionsList[3]
            isGroup = False
            donate_url = None
            website_url = None
            enigma_pub_key = None
            pgp_pub_key = None
            pgp_fingerprint = None
            xmpp_address = None
            matrix_address = None
            blog_address = None
            tox_address = None
            briar_address = None
            jami_address = None
            cwtch_address = None
            ssb_address = None
            email_address = None
            lockedAccount = False
            alsoKnownAs = None
            movedTo = ''
            actor_json = \
                get_person_from_cache(base_dir,
                                      optionsActor,
                                      self.server.person_cache,
                                      True)
            if actor_json:
                if actor_json.get('movedTo'):
                    movedTo = actor_json['movedTo']
                    if '"' in movedTo:
                        movedTo = movedTo.split('"')[1]
                if actor_json['type'] == 'Group':
                    isGroup = True
                lockedAccount = get_locked_account(actor_json)
                donate_url = get_donation_url(actor_json)
                website_url = get_website(actor_json, self.server.translate)
                xmpp_address = get_xmpp_address(actor_json)
                matrix_address = get_matrix_address(actor_json)
                ssb_address = get_ssb_address(actor_json)
                blog_address = get_blog_address(actor_json)
                tox_address = get_tox_address(actor_json)
                briar_address = get_briar_address(actor_json)
                jami_address = get_jami_address(actor_json)
                cwtch_address = get_cwtch_address(actor_json)
                email_address = get_email_address(actor_json)
                enigma_pub_key = get_enigma_pub_key(actor_json)
                pgp_pub_key = get_pgp_pub_key(actor_json)
                pgp_fingerprint = get_pgp_fingerprint(actor_json)
                if actor_json.get('alsoKnownAs'):
                    alsoKnownAs = actor_json['alsoKnownAs']

            if self.server.session:
                check_for_changed_actor(self.server.session,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain_full,
                                        optionsActor, optionsProfileUrl,
                                        self.server.person_cache, 5)

            access_keys = self.server.access_keys
            if '/users/' in path:
                nickname = path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                if self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.keyShortcuts[nickname]
            msg = \
                html_person_options(self.server.default_timeline,
                                    self.server.css_cache,
                                    self.server.translate,
                                    base_dir, domain,
                                    domain_full,
                                    originPathStr,
                                    optionsActor,
                                    optionsProfileUrl,
                                    optionsLink,
                                    page_number, donate_url, website_url,
                                    xmpp_address, matrix_address,
                                    ssb_address, blog_address,
                                    tox_address, briar_address,
                                    jami_address, cwtch_address,
                                    enigma_pub_key,
                                    pgp_pub_key, pgp_fingerprint,
                                    email_address,
                                    self.server.dormant_months,
                                    backToPath,
                                    lockedAccount,
                                    movedTo, alsoKnownAs,
                                    self.server.text_mode_banner,
                                    self.server.news_instance,
                                    authorized,
                                    access_keys, isGroup).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_show_person_options', debug)
            return

        if '/users/news/' in path:
            self._redirect_headers(originPathStr + '/tlfeatures',
                                   cookie, calling_domain)
            return

        if calling_domain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif calling_domain.endswith('.i2p') and i2p_domain:
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        else:
            originPathStrAbsolute = \
                http_prefix + '://' + domain_full + originPathStr
        self._redirect_headers(originPathStrAbsolute, cookie,
                               calling_domain)

    def _show_media(self, calling_domain: str,
                    path: str, base_dir: str,
                    GETstartTime) -> None:
        """Returns a media file
        """
        if is_image_file(path) or \
           path_is_video(path) or \
           path_is_audio(path):
            mediaStr = path.split('/media/')[1]
            media_filename = base_dir + '/media/' + mediaStr
            if os.path.isfile(media_filename):
                if self._etag_exists(media_filename):
                    # The file has not changed
                    self._304()
                    return

                mediaFileType = media_file_mime_type(media_filename)

                t = os.path.getmtime(media_filename)
                lastModifiedTime = datetime.datetime.fromtimestamp(t)
                lastModifiedTimeStr = \
                    lastModifiedTime.strftime('%a, %d %b %Y %H:%M:%S GMT')

                mediaBinary = None
                try:
                    with open(media_filename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                except OSError:
                    print('EX: unable to read media binary ' + media_filename)
                if mediaBinary:
                    self._set_headers_etag(media_filename, mediaFileType,
                                           mediaBinary, None,
                                           None, True,
                                           lastModifiedTimeStr)
                    self._write(mediaBinary)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_show_media', self.server.debug)
                return
        self._404()

    def _get_ontology(self, calling_domain: str,
                      path: str, base_dir: str,
                      GETstartTime) -> None:
        """Returns an ontology file
        """
        if '.owl' in path or '.rdf' in path or '.json' in path:
            if '/ontologies/' in path:
                ontologyStr = path.split('/ontologies/')[1].replace('#', '')
            else:
                ontologyStr = path.split('/data/')[1].replace('#', '')
            ontologyFilename = None
            ontologyFileType = 'application/rdf+xml'
            if ontologyStr.startswith('DFC_'):
                ontologyFilename = base_dir + '/ontology/DFC/' + ontologyStr
            else:
                ontologyStr = ontologyStr.replace('/data/', '')
                ontologyFilename = base_dir + '/ontology/' + ontologyStr
            if ontologyStr.endswith('.json'):
                ontologyFileType = 'application/ld+json'
            if os.path.isfile(ontologyFilename):
                ontologyFile = None
                try:
                    with open(ontologyFilename, 'r') as fp:
                        ontologyFile = fp.read()
                except OSError:
                    print('EX: unable to read ontology ' + ontologyFilename)
                if ontologyFile:
                    ontologyFile = \
                        ontologyFile.replace('static.datafoodconsortium.org',
                                             calling_domain)
                    if not calling_domain.endswith('.i2p') and \
                       not calling_domain.endswith('.onion'):
                        ontologyFile = \
                            ontologyFile.replace('http://' +
                                                 calling_domain,
                                                 'https://' +
                                                 calling_domain)
                    msg = ontologyFile.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers(ontologyFileType, msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_get_ontology', self.server.debug)
                return
        self._404()

    def _show_emoji(self, calling_domain: str, path: str,
                    base_dir: str, GETstartTime) -> None:
        """Returns an emoji image
        """
        if is_image_file(path):
            emojiStr = path.split('/emoji/')[1]
            emojiFilename = base_dir + '/emoji/' + emojiStr
            if not os.path.isfile(emojiFilename):
                emojiFilename = base_dir + '/emojicustom/' + emojiStr
            if os.path.isfile(emojiFilename):
                if self._etag_exists(emojiFilename):
                    # The file has not changed
                    self._304()
                    return

                mediaImageType = get_image_mime_type(emojiFilename)
                mediaBinary = None
                try:
                    with open(emojiFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                except OSError:
                    print('EX: unable to read emoji image ' + emojiFilename)
                if mediaBinary:
                    self._set_headers_etag(emojiFilename,
                                           mediaImageType,
                                           mediaBinary, None,
                                           self.server.domain_full,
                                           False, None)
                    self._write(mediaBinary)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_show_emoji', self.server.debug)
                return
        self._404()

    def _show_icon(self, calling_domain: str, path: str,
                   base_dir: str, GETstartTime) -> None:
        """Shows an icon
        """
        if not path.endswith('.png'):
            self._404()
            return
        mediaStr = path.split('/icons/')[1]
        if '/' not in mediaStr:
            if not self.server.theme_name:
                theme = 'default'
            else:
                theme = self.server.theme_name
            iconFilename = mediaStr
        else:
            theme = mediaStr.split('/')[0]
            iconFilename = mediaStr.split('/')[1]
        media_filename = \
            base_dir + '/theme/' + theme + '/icons/' + iconFilename
        if self._etag_exists(media_filename):
            # The file has not changed
            self._304()
            return
        if self.server.iconsCache.get(mediaStr):
            mediaBinary = self.server.iconsCache[mediaStr]
            mimeTypeStr = media_file_mime_type(media_filename)
            self._set_headers_etag(media_filename,
                                   mimeTypeStr,
                                   mediaBinary, None,
                                   self.server.domain_full,
                                   False, None)
            self._write(mediaBinary)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_show_icon', self.server.debug)
            return
        else:
            if os.path.isfile(media_filename):
                mediaBinary = None
                try:
                    with open(media_filename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                except OSError:
                    print('EX: unable to read icon image ' + media_filename)
                if mediaBinary:
                    mimeType = media_file_mime_type(media_filename)
                    self._set_headers_etag(media_filename,
                                           mimeType,
                                           mediaBinary, None,
                                           self.server.domain_full,
                                           False, None)
                    self._write(mediaBinary)
                    self.server.iconsCache[mediaStr] = mediaBinary
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_show_icon', self.server.debug)
                return
        self._404()

    def _show_help_screen_image(self, calling_domain: str, path: str,
                                base_dir: str, GETstartTime) -> None:
        """Shows a help screen image
        """
        if not is_image_file(path):
            return
        mediaStr = path.split('/helpimages/')[1]
        if '/' not in mediaStr:
            if not self.server.theme_name:
                theme = 'default'
            else:
                theme = self.server.theme_name
            iconFilename = mediaStr
        else:
            theme = mediaStr.split('/')[0]
            iconFilename = mediaStr.split('/')[1]
        media_filename = \
            base_dir + '/theme/' + theme + '/helpimages/' + iconFilename
        # if there is no theme-specific help image then use the default one
        if not os.path.isfile(media_filename):
            media_filename = \
                base_dir + '/theme/default/helpimages/' + iconFilename
        if self._etag_exists(media_filename):
            # The file has not changed
            self._304()
            return
        if os.path.isfile(media_filename):
            mediaBinary = None
            try:
                with open(media_filename, 'rb') as avFile:
                    mediaBinary = avFile.read()
            except OSError:
                print('EX: unable to read help image ' + media_filename)
            if mediaBinary:
                mimeType = media_file_mime_type(media_filename)
                self._set_headers_etag(media_filename,
                                       mimeType,
                                       mediaBinary, None,
                                       self.server.domain_full,
                                       False, None)
                self._write(mediaBinary)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_show_help_screen_image',
                                self.server.debug)
            return
        self._404()

    def _show_cached_favicon(self, refererDomain: str, path: str,
                             base_dir: str, GETstartTime) -> None:
        """Shows a favicon image obtained from the cache
        """
        favFile = path.replace('/favicons/', '')
        favFilename = base_dir + urllib.parse.unquote_plus(path)
        print('showCachedFavicon: ' + favFilename)
        if self.server.favicons_cache.get(favFile):
            mediaBinary = self.server.favicons_cache[favFile]
            mimeType = media_file_mime_type(favFilename)
            self._set_headers_etag(favFilename,
                                   mimeType,
                                   mediaBinary, None,
                                   refererDomain,
                                   False, None)
            self._write(mediaBinary)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_show_cached_favicon2',
                                self.server.debug)
            return
        if not os.path.isfile(favFilename):
            self._404()
            return
        if self._etag_exists(favFilename):
            # The file has not changed
            self._304()
            return
        mediaBinary = None
        try:
            with open(favFilename, 'rb') as avFile:
                mediaBinary = avFile.read()
        except OSError:
            print('EX: unable to read cached favicon ' + favFilename)
        if mediaBinary:
            mimeType = media_file_mime_type(favFilename)
            self._set_headers_etag(favFilename,
                                   mimeType,
                                   mediaBinary, None,
                                   refererDomain,
                                   False, None)
            self._write(mediaBinary)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_show_cached_favicon',
                                self.server.debug)
            self.server.favicons_cache[favFile] = mediaBinary
            return
        self._404()

    def _show_cached_avatar(self, refererDomain: str, path: str,
                            base_dir: str, GETstartTime) -> None:
        """Shows an avatar image obtained from the cache
        """
        media_filename = base_dir + '/cache' + path
        if os.path.isfile(media_filename):
            if self._etag_exists(media_filename):
                # The file has not changed
                self._304()
                return
            mediaBinary = None
            try:
                with open(media_filename, 'rb') as avFile:
                    mediaBinary = avFile.read()
            except OSError:
                print('EX: unable to read cached avatar ' + media_filename)
            if mediaBinary:
                mimeType = media_file_mime_type(media_filename)
                self._set_headers_etag(media_filename,
                                       mimeType,
                                       mediaBinary, None,
                                       refererDomain,
                                       False, None)
                self._write(mediaBinary)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_show_cached_avatar',
                                    self.server.debug)
                return
        self._404()

    def _hashtag_search(self, calling_domain: str,
                        path: str, cookie: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domain_full: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime) -> None:
        """Return the result of a hashtag search
        """
        page_number = 1
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        hashtag = path.split('/tags/')[1]
        if '?page=' in hashtag:
            hashtag = hashtag.split('?page=')[0]
        hashtag = urllib.parse.unquote_plus(hashtag)
        if is_blocked_hashtag(base_dir, hashtag):
            print('BLOCK: hashtag #' + hashtag)
            msg = html_hashtag_blocked(self.server.css_cache, base_dir,
                                       self.server.translate).encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, calling_domain)
            self._write(msg)
            return
        nickname = None
        if '/users/' in path:
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if '?' in nickname:
                nickname = nickname.split('?')[0]
        hashtagStr = \
            html_hashtag_search(self.server.css_cache,
                                nickname, domain, port,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.translate,
                                base_dir, hashtag, page_number,
                                max_posts_in_hashtag_feed, self.server.session,
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
                                self.server.lists_enabled)
        if hashtagStr:
            msg = hashtagStr.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
        else:
            originPathStr = path.split('/tags/')[0]
            originPathStrAbsolute = \
                http_prefix + '://' + domain_full + originPathStr
            if calling_domain.endswith('.onion') and onion_domain:
                originPathStrAbsolute = \
                    'http://' + onion_domain + originPathStr
            elif (calling_domain.endswith('.i2p') and onion_domain):
                originPathStrAbsolute = \
                    'http://' + i2p_domain + originPathStr
            self._redirect_headers(originPathStrAbsolute + '/search',
                                   cookie, calling_domain)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_hashtag_search',
                            self.server.debug)

    def _hashtag_search_rss2(self, calling_domain: str,
                             path: str, cookie: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime) -> None:
        """Return an RSS 2 feed for a hashtag
        """
        hashtag = path.split('/tags/rss2/')[1]
        if is_blocked_hashtag(base_dir, hashtag):
            self._400()
            return
        nickname = None
        if '/users/' in path:
            actor = \
                http_prefix + '://' + domain_full + path
            nickname = \
                get_nickname_from_actor(actor)
        hashtagStr = \
            rss_hashtag_search(nickname,
                               domain, port,
                               self.server.recent_posts_cache,
                               self.server.max_recent_posts,
                               self.server.translate,
                               base_dir, hashtag,
                               max_posts_in_feed, self.server.session,
                               self.server.cached_webfingers,
                               self.server.person_cache,
                               http_prefix,
                               self.server.project_version,
                               self.server.yt_replace_domain,
                               self.server.twitter_replacement_domain,
                               self.server.system_language)
        if hashtagStr:
            msg = hashtagStr.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/xml', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
        else:
            originPathStr = path.split('/tags/rss2/')[0]
            originPathStrAbsolute = \
                http_prefix + '://' + domain_full + originPathStr
            if calling_domain.endswith('.onion') and onion_domain:
                originPathStrAbsolute = \
                    'http://' + onion_domain + originPathStr
            elif (calling_domain.endswith('.i2p') and onion_domain):
                originPathStrAbsolute = \
                    'http://' + i2p_domain + originPathStr
            self._redirect_headers(originPathStrAbsolute + '/search',
                                   cookie, calling_domain)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_hashtag_search_rss2',
                            self.server.debug)

    def _announce_button(self, calling_domain: str, path: str,
                         base_dir: str,
                         cookie: str, proxy_type: str,
                         http_prefix: str,
                         domain: str, domain_full: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         GETstartTime,
                         repeatPrivate: bool,
                         debug: bool) -> None:
        """The announce/repeat button was pressed on a post
        """
        page_number = 1
        repeatUrl = path.split('?repeat=')[1]
        if '?' in repeatUrl:
            repeatUrl = repeatUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?repeat=')[0]
        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number)
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        if not self._establish_session("announceButton"):
            self._404()
            return
        self.server.actorRepeat = path.split('?actor=')[1]
        announceToStr = \
            local_actor_url(http_prefix, self.post_to_nickname,
                            domain_full) + \
            '/followers'
        if not repeatPrivate:
            announceToStr = 'https://www.w3.org/ns/activitystreams#Public'
        announceJson = \
            create_announce(self.server.session,
                            base_dir,
                            self.server.federation_list,
                            self.post_to_nickname,
                            domain, port,
                            announceToStr,
                            None, http_prefix,
                            repeatUrl, False, False,
                            self.server.send_threads,
                            self.server.postLog,
                            self.server.person_cache,
                            self.server.cached_webfingers,
                            debug,
                            self.server.project_version,
                            self.server.signing_priv_key_pem)
        announceFilename = None
        if announceJson:
            # save the announce straight to the outbox
            # This is because the subsequent send is within a separate thread
            # but the html still needs to be generated before this call ends
            announceId = remove_id_ending(announceJson['id'])
            announceFilename = \
                save_post_to_box(base_dir, http_prefix, announceId,
                                 self.post_to_nickname, domain_full,
                                 announceJson, 'outbox')

            # clear the icon from the cache so that it gets updated
            if self.server.iconsCache.get('repeat.png'):
                del self.server.iconsCache['repeat.png']

            # send out the announce within a separate thread
            self._post_to_outbox(announceJson,
                                 self.server.project_version,
                                 self.post_to_nickname)

            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_announce_button postToOutboxThread',
                                self.server.debug)

        # generate the html for the announce
        if announceJson and announceFilename:
            if debug:
                print('Generating html post for announce')
            cached_post_filename = \
                get_cached_post_filename(base_dir, self.post_to_nickname,
                                         domain, announceJson)
            if debug:
                print('Announced post json: ' + str(announceJson))
                print('Announced post nickname: ' +
                      self.post_to_nickname + ' ' + domain)
                print('Announced post cache: ' + str(cached_post_filename))
            showIndividualPostIcons = True
            manuallyApproveFollowers = \
                follower_approval_active(base_dir,
                                         self.post_to_nickname, domain)
            showRepeats = not is_dm(announceJson)
            individual_post_as_html(self.server.signing_priv_key_pem, False,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    self.server.session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    self.post_to_nickname, domain,
                                    self.server.port, announceJson,
                                    None, True,
                                    self.server.allow_deletion,
                                    http_prefix, self.server.project_version,
                                    timelineStr,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    showRepeats,
                                    showIndividualPostIcons,
                                    manuallyApproveFollowers,
                                    False, True, False,
                                    self.server.cw_lists,
                                    self.server.lists_enabled)

        actorAbsolute = self._get_instance_url(calling_domain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + '?page=' + \
            str(page_number) + timelineBookmark
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_announce_button',
                            self.server.debug)
        self._redirect_headers(actorPathStr, cookie, calling_domain)

    def _undo_announce_button(self, calling_domain: str, path: str,
                              base_dir: str,
                              cookie: str, proxy_type: str,
                              http_prefix: str,
                              domain: str, domain_full: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              repeatPrivate: bool, debug: bool,
                              recent_posts_cache: {}) -> None:
        """Undo announce/repeat button was pressed
        """
        page_number = 1

        # the post which was referenced by the announce post
        repeatUrl = path.split('?unrepeat=')[1]
        if '?' in repeatUrl:
            repeatUrl = repeatUrl.split('?')[0]

        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?unrepeat=')[0]
        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + '?page=' + \
                str(page_number)
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        if not self._establish_session("undoAnnounceButton"):
            self._404()
            return
        undoAnnounceActor = \
            http_prefix + '://' + domain_full + \
            '/users/' + self.post_to_nickname
        unRepeatToStr = 'https://www.w3.org/ns/activitystreams#Public'
        newUndoAnnounce = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'actor': undoAnnounceActor,
            'type': 'Undo',
            'cc': [undoAnnounceActor + '/followers'],
            'to': [unRepeatToStr],
            'object': {
                'actor': undoAnnounceActor,
                'cc': [undoAnnounceActor + '/followers'],
                'object': repeatUrl,
                'to': [unRepeatToStr],
                'type': 'Announce'
            }
        }
        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('repeat_inactive.png'):
            del self.server.iconsCache['repeat_inactive.png']

        # delete  the announce post
        if '?unannounce=' in path:
            announceUrl = path.split('?unannounce=')[1]
            if '?' in announceUrl:
                announceUrl = announceUrl.split('?')[0]
            post_filename = None
            nickname = get_nickname_from_actor(announceUrl)
            if nickname:
                if domain_full + '/users/' + nickname + '/' in announceUrl:
                    post_filename = \
                        locate_post(base_dir, nickname, domain, announceUrl)
            if post_filename:
                delete_post(base_dir, http_prefix,
                            nickname, domain, post_filename,
                            debug, recent_posts_cache)

        self._post_to_outbox(newUndoAnnounce,
                             self.server.project_version,
                             self.post_to_nickname)

        actorAbsolute = self._get_instance_url(calling_domain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + '?page=' + \
            str(page_number) + timelineBookmark
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_undo_announce_button',
                            self.server.debug)
        self._redirect_headers(actorPathStr, cookie, calling_domain)

    def _follow_approve_button(self, calling_domain: str, path: str,
                               cookie: str,
                               base_dir: str, http_prefix: str,
                               domain: str, domain_full: str, port: int,
                               onion_domain: str, i2p_domain: str,
                               GETstartTime,
                               proxy_type: str, debug: bool) -> None:
        """Follow approve button was pressed
        """
        originPathStr = path.split('/followapprove=')[0]
        followerNickname = originPathStr.replace('/users/', '')
        followingHandle = path.split('/followapprove=')[1]
        if '://' in followingHandle:
            handleNickname = get_nickname_from_actor(followingHandle)
            handleDomain, handlePort = get_domain_from_actor(followingHandle)
            followingHandle = \
                handleNickname + '@' + \
                get_full_domain(handleDomain, handlePort)
        if '@' in followingHandle:
            if not self._establish_session("followApproveButton"):
                self._404()
                return
            signing_priv_key_pem = \
                self.server.signing_priv_key_pem
            manual_approve_follow_request_thread(self.server.session,
                                                 base_dir, http_prefix,
                                                 followerNickname,
                                                 domain, port,
                                                 followingHandle,
                                                 self.server.federation_list,
                                                 self.server.send_threads,
                                                 self.server.postLog,
                                                 self.server.cached_webfingers,
                                                 self.server.person_cache,
                                                 debug,
                                                 self.server.project_version,
                                                 signing_priv_key_pem)
        originPathStrAbsolute = \
            http_prefix + '://' + domain_full + originPathStr
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_follow_approve_button',
                            self.server.debug)
        self._redirect_headers(originPathStrAbsolute,
                               cookie, calling_domain)

    def _newswire_vote(self, calling_domain: str, path: str,
                       cookie: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domain_full: str, port: int,
                       onion_domain: str, i2p_domain: str,
                       GETstartTime,
                       proxy_type: str, debug: bool,
                       newswire: {}):
        """Vote for a newswire item
        """
        originPathStr = path.split('/newswirevote=')[0]
        dateStr = \
            path.split('/newswirevote=')[1].replace('T', ' ')
        dateStr = dateStr.replace(' 00:00', '').replace('+00:00', '')
        dateStr = urllib.parse.unquote_plus(dateStr) + '+00:00'
        nickname = urllib.parse.unquote_plus(originPathStr.split('/users/')[1])
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        print('Newswire item date: ' + dateStr)
        if newswire.get(dateStr):
            if is_moderator(base_dir, nickname):
                newswireItem = newswire[dateStr]
                print('Voting on newswire item: ' + str(newswireItem))
                votesIndex = 2
                filenameIndex = 3
                if 'vote:' + nickname not in newswireItem[votesIndex]:
                    newswireItem[votesIndex].append('vote:' + nickname)
                    filename = newswireItem[filenameIndex]
                    newswireStateFilename = \
                        base_dir + '/accounts/.newswirestate.json'
                    try:
                        save_json(newswire, newswireStateFilename)
                    except Exception as ex:
                        print('ERROR: saving newswire state, ' + str(ex))
                    if filename:
                        save_json(newswireItem[votesIndex],
                                  filename + '.votes')
        else:
            print('No newswire item with date: ' + dateStr + ' ' +
                  str(newswire))

        originPathStrAbsolute = \
            http_prefix + '://' + domain_full + originPathStr + '/' + \
            self.server.default_timeline
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_newswire_vote',
                            self.server.debug)
        self._redirect_headers(originPathStrAbsolute,
                               cookie, calling_domain)

    def _newswire_unvote(self, calling_domain: str, path: str,
                         cookie: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         GETstartTime,
                         proxy_type: str, debug: bool,
                         newswire: {}):
        """Remove vote for a newswire item
        """
        originPathStr = path.split('/newswireunvote=')[0]
        dateStr = \
            path.split('/newswireunvote=')[1].replace('T', ' ')
        dateStr = dateStr.replace(' 00:00', '').replace('+00:00', '')
        dateStr = urllib.parse.unquote_plus(dateStr) + '+00:00'
        nickname = urllib.parse.unquote_plus(originPathStr.split('/users/')[1])
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if newswire.get(dateStr):
            if is_moderator(base_dir, nickname):
                votesIndex = 2
                filenameIndex = 3
                newswireItem = newswire[dateStr]
                if 'vote:' + nickname in newswireItem[votesIndex]:
                    newswireItem[votesIndex].remove('vote:' + nickname)
                    filename = newswireItem[filenameIndex]
                    newswireStateFilename = \
                        base_dir + '/accounts/.newswirestate.json'
                    try:
                        save_json(newswire, newswireStateFilename)
                    except Exception as ex:
                        print('ERROR: saving newswire state, ' + str(ex))
                    if filename:
                        save_json(newswireItem[votesIndex],
                                  filename + '.votes')
        else:
            print('No newswire item with date: ' + dateStr + ' ' +
                  str(newswire))

        originPathStrAbsolute = \
            http_prefix + '://' + domain_full + originPathStr + '/' + \
            self.server.default_timeline
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        self._redirect_headers(originPathStrAbsolute,
                               cookie, calling_domain)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_newswire_unvote',
                            self.server.debug)

    def _follow_deny_button(self, calling_domain: str, path: str,
                            cookie: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domain_full: str, port: int,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            proxy_type: str, debug: bool) -> None:
        """Follow deny button was pressed
        """
        originPathStr = path.split('/followdeny=')[0]
        followerNickname = originPathStr.replace('/users/', '')
        followingHandle = path.split('/followdeny=')[1]
        if '://' in followingHandle:
            handleNickname = get_nickname_from_actor(followingHandle)
            handleDomain, handlePort = get_domain_from_actor(followingHandle)
            followingHandle = \
                handleNickname + '@' + \
                get_full_domain(handleDomain, handlePort)
        if '@' in followingHandle:
            manual_deny_follow_request_thread(self.server.session,
                                              base_dir, http_prefix,
                                              followerNickname,
                                              domain, port,
                                              followingHandle,
                                              self.server.federation_list,
                                              self.server.send_threads,
                                              self.server.postLog,
                                              self.server.cached_webfingers,
                                              self.server.person_cache,
                                              debug,
                                              self.server.project_version,
                                              self.server.signing_priv_key_pem)
        originPathStrAbsolute = \
            http_prefix + '://' + domain_full + originPathStr
        if calling_domain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif calling_domain.endswith('.i2p') and i2p_domain:
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        self._redirect_headers(originPathStrAbsolute,
                               cookie, calling_domain)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_follow_deny_button',
                            self.server.debug)

    def _like_button(self, calling_domain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domain_full: str,
                     onion_domain: str, i2p_domain: str,
                     GETstartTime,
                     proxy_type: str, cookie: str,
                     debug: str) -> None:
        """Press the like button
        """
        page_number = 1
        likeUrl = path.split('?like=')[1]
        if '?' in likeUrl:
            likeUrl = likeUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        actor = path.split('?like=')[0]
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]

        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        if not self._establish_session("likeButton"):
            self._404()
            return
        likeActor = \
            local_actor_url(http_prefix, self.post_to_nickname, domain_full)
        actorLiked = path.split('?actor=')[1]
        if '?' in actorLiked:
            actorLiked = actorLiked.split('?')[0]

        # if this is an announce then send the like to the original post
        origActor, origPostUrl, origFilename = \
            get_original_post_from_announce_url(likeUrl, base_dir,
                                                self.post_to_nickname, domain)
        likeUrl2 = likeUrl
        likedPostFilename = origFilename
        if origActor and origPostUrl:
            actorLiked = origActor
            likeUrl2 = origPostUrl
            likedPostFilename = None

        likeJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Like',
            'actor': likeActor,
            'to': [actorLiked],
            'object': likeUrl2
        }

        # send out the like to followers
        self._post_to_outbox(likeJson, self.server.project_version, None)

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_like_button postToOutbox',
                            self.server.debug)

        print('Locating liked post ' + likeUrl)
        # directly like the post file
        if not likedPostFilename:
            likedPostFilename = \
                locate_post(base_dir, self.post_to_nickname, domain, likeUrl)
        if likedPostFilename:
            recent_posts_cache = self.server.recent_posts_cache
            likedPostJson = load_json(likedPostFilename, 0, 1)
            if origFilename and origPostUrl:
                update_likes_collection(recent_posts_cache,
                                        base_dir, likedPostFilename,
                                        likeUrl, likeActor,
                                        self.post_to_nickname,
                                        domain, debug, likedPostJson)
                likeUrl = origPostUrl
                likedPostFilename = origFilename
            if debug:
                print('Updating likes for ' + likedPostFilename)
            update_likes_collection(recent_posts_cache,
                                    base_dir, likedPostFilename, likeUrl,
                                    likeActor, self.post_to_nickname, domain,
                                    debug, None)
            if debug:
                print('Regenerating html post for changed likes collection')
            # clear the icon from the cache so that it gets updated
            if likedPostJson:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, self.post_to_nickname,
                                             domain, likedPostJson)
                if debug:
                    print('Liked post json: ' + str(likedPostJson))
                    print('Liked post nickname: ' +
                          self.post_to_nickname + ' ' + domain)
                    print('Liked post cache: ' + str(cached_post_filename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    follower_approval_active(base_dir,
                                             self.post_to_nickname, domain)
                showRepeats = not is_dm(likedPostJson)
                individual_post_as_html(self.server.signing_priv_key_pem,
                                        False,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, base_dir,
                                        self.server.session,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        self.post_to_nickname, domain,
                                        self.server.port, likedPostJson,
                                        None, True,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        timelineStr,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.theme_name,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        showRepeats,
                                        showIndividualPostIcons,
                                        manuallyApproveFollowers,
                                        False, True, False,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
            else:
                print('WARN: Liked post not found: ' + likedPostFilename)
            # clear the icon from the cache so that it gets updated
            if self.server.iconsCache.get('like.png'):
                del self.server.iconsCache['like.png']
        else:
            print('WARN: unable to locate file for liked post ' +
                  likeUrl)

        actorAbsolute = self._get_instance_url(calling_domain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(page_number) + timelineBookmark
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_like_button',
                            self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               calling_domain)

    def _undo_like_button(self, calling_domain: str, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str,
                          onion_domain: str, i2p_domain: str,
                          GETstartTime,
                          proxy_type: str, cookie: str,
                          debug: str) -> None:
        """A button is pressed to undo
        """
        page_number = 1
        likeUrl = path.split('?unlike=')[1]
        if '?' in likeUrl:
            likeUrl = likeUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?unlike=')[0]
        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number)
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        if not self._establish_session("undoLikeButton"):
            self._404()
            return
        undoActor = \
            local_actor_url(http_prefix, self.post_to_nickname, domain_full)
        actorLiked = path.split('?actor=')[1]
        if '?' in actorLiked:
            actorLiked = actorLiked.split('?')[0]

        # if this is an announce then send the like to the original post
        origActor, origPostUrl, origFilename = \
            get_original_post_from_announce_url(likeUrl, base_dir,
                                                self.post_to_nickname, domain)
        likeUrl2 = likeUrl
        likedPostFilename = origFilename
        if origActor and origPostUrl:
            actorLiked = origActor
            likeUrl2 = origPostUrl
            likedPostFilename = None

        undoLikeJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Undo',
            'actor': undoActor,
            'to': [actorLiked],
            'object': {
                'type': 'Like',
                'actor': undoActor,
                'to': [actorLiked],
                'object': likeUrl2
            }
        }

        # send out the undo like to followers
        self._post_to_outbox(undoLikeJson, self.server.project_version, None)

        # directly undo the like within the post file
        if not likedPostFilename:
            likedPostFilename = locate_post(base_dir, self.post_to_nickname,
                                            domain, likeUrl)
        if likedPostFilename:
            recent_posts_cache = self.server.recent_posts_cache
            likedPostJson = load_json(likedPostFilename, 0, 1)
            if origFilename and origPostUrl:
                undo_likes_collection_entry(recent_posts_cache,
                                            base_dir, likedPostFilename,
                                            likeUrl, undoActor,
                                            domain, debug,
                                            likedPostJson)
                likeUrl = origPostUrl
                likedPostFilename = origFilename
            if debug:
                print('Removing likes for ' + likedPostFilename)
            undo_likes_collection_entry(recent_posts_cache,
                                        base_dir,
                                        likedPostFilename, likeUrl,
                                        undoActor, domain, debug, None)
            if debug:
                print('Regenerating html post for changed likes collection')
            if likedPostJson:
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    follower_approval_active(base_dir,
                                             self.post_to_nickname, domain)
                showRepeats = not is_dm(likedPostJson)
                individual_post_as_html(self.server.signing_priv_key_pem,
                                        False,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, base_dir,
                                        self.server.session,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        self.post_to_nickname, domain,
                                        self.server.port, likedPostJson,
                                        None, True,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        timelineStr,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.theme_name,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        showRepeats,
                                        showIndividualPostIcons,
                                        manuallyApproveFollowers,
                                        False, True, False,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
            else:
                print('WARN: Unliked post not found: ' + likedPostFilename)
            # clear the icon from the cache so that it gets updated
            if self.server.iconsCache.get('like_inactive.png'):
                del self.server.iconsCache['like_inactive.png']
        actorAbsolute = self._get_instance_url(calling_domain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(page_number) + timelineBookmark
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_undo_like_button',
                            self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               calling_domain)

    def _reaction_button(self, calling_domain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str,
                         onion_domain: str, i2p_domain: str,
                         GETstartTime,
                         proxy_type: str, cookie: str,
                         debug: str) -> None:
        """Press an emoji reaction button
        Note that this is not the emoji reaction selection icon at the
        bottom of the post
        """
        page_number = 1
        reactionUrl = path.split('?react=')[1]
        if '?' in reactionUrl:
            reactionUrl = reactionUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        actor = path.split('?react=')[0]
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        emojiContentEncoded = None
        if '?emojreact=' in path:
            emojiContentEncoded = path.split('?emojreact=')[1]
            if '?' in emojiContentEncoded:
                emojiContentEncoded = emojiContentEncoded.split('?')[0]
        if not emojiContentEncoded:
            print('WARN: no emoji reaction ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        emojiContent = urllib.parse.unquote_plus(emojiContentEncoded)
        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        if not self._establish_session("reactionButton"):
            self._404()
            return
        reactionActor = \
            local_actor_url(http_prefix, self.post_to_nickname, domain_full)
        actorReaction = path.split('?actor=')[1]
        if '?' in actorReaction:
            actorReaction = actorReaction.split('?')[0]

        # if this is an announce then send the emoji reaction
        # to the original post
        origActor, origPostUrl, origFilename = \
            get_original_post_from_announce_url(reactionUrl, base_dir,
                                                self.post_to_nickname, domain)
        reactionUrl2 = reactionUrl
        reaction_postFilename = origFilename
        if origActor and origPostUrl:
            actorReaction = origActor
            reactionUrl2 = origPostUrl
            reaction_postFilename = None

        reactionJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'EmojiReact',
            'actor': reactionActor,
            'to': [actorReaction],
            'object': reactionUrl2,
            'content': emojiContent
        }

        # send out the emoji reaction to followers
        self._post_to_outbox(reactionJson, self.server.project_version, None)

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_reaction_button postToOutbox',
                            self.server.debug)

        print('Locating emoji reaction post ' + reactionUrl)
        # directly emoji reaction the post file
        if not reaction_postFilename:
            reaction_postFilename = \
                locate_post(base_dir, self.post_to_nickname, domain,
                            reactionUrl)
        if reaction_postFilename:
            recent_posts_cache = self.server.recent_posts_cache
            reaction_post_json = load_json(reaction_postFilename, 0, 1)
            if origFilename and origPostUrl:
                update_reaction_collection(recent_posts_cache,
                                           base_dir, reaction_postFilename,
                                           reactionUrl,
                                           reactionActor,
                                           self.post_to_nickname,
                                           domain, debug, reaction_post_json,
                                           emojiContent)
                reactionUrl = origPostUrl
                reaction_postFilename = origFilename
            if debug:
                print('Updating emoji reaction for ' + reaction_postFilename)
            update_reaction_collection(recent_posts_cache,
                                       base_dir, reaction_postFilename,
                                       reactionUrl,
                                       reactionActor,
                                       self.post_to_nickname, domain,
                                       debug, None, emojiContent)
            if debug:
                print('Regenerating html post for changed ' +
                      'emoji reaction collection')
            # clear the icon from the cache so that it gets updated
            if reaction_post_json:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, self.post_to_nickname,
                                             domain, reaction_post_json)
                if debug:
                    print('Reaction post json: ' + str(reaction_post_json))
                    print('Reaction post nickname: ' +
                          self.post_to_nickname + ' ' + domain)
                    print('Reaction post cache: ' + str(cached_post_filename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    follower_approval_active(base_dir,
                                             self.post_to_nickname, domain)
                showRepeats = not is_dm(reaction_post_json)
                individual_post_as_html(self.server.signing_priv_key_pem,
                                        False,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, base_dir,
                                        self.server.session,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        self.post_to_nickname, domain,
                                        self.server.port, reaction_post_json,
                                        None, True,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        timelineStr,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.theme_name,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        showRepeats,
                                        showIndividualPostIcons,
                                        manuallyApproveFollowers,
                                        False, True, False,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
            else:
                print('WARN: Emoji reaction post not found: ' +
                      reaction_postFilename)
        else:
            print('WARN: unable to locate file for emoji reaction post ' +
                  reactionUrl)

        actorAbsolute = self._get_instance_url(calling_domain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(page_number) + timelineBookmark
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_reaction_button',
                            self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               calling_domain)

    def _undo_reaction_button(self, calling_domain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> None:
        """A button is pressed to undo emoji reaction
        """
        page_number = 1
        reactionUrl = path.split('?unreact=')[1]
        if '?' in reactionUrl:
            reactionUrl = reactionUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?unreact=')[0]
        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number)
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        emojiContentEncoded = None
        if '?emojreact=' in path:
            emojiContentEncoded = path.split('?emojreact=')[1]
            if '?' in emojiContentEncoded:
                emojiContentEncoded = emojiContentEncoded.split('?')[0]
        if not emojiContentEncoded:
            print('WARN: no emoji reaction ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        emojiContent = urllib.parse.unquote_plus(emojiContentEncoded)
        if not self._establish_session("undoReactionButton"):
            self._404()
            return
        undoActor = \
            local_actor_url(http_prefix, self.post_to_nickname, domain_full)
        actorReaction = path.split('?actor=')[1]
        if '?' in actorReaction:
            actorReaction = actorReaction.split('?')[0]

        # if this is an announce then send the emoji reaction
        # to the original post
        origActor, origPostUrl, origFilename = \
            get_original_post_from_announce_url(reactionUrl, base_dir,
                                                self.post_to_nickname, domain)
        reactionUrl2 = reactionUrl
        reaction_postFilename = origFilename
        if origActor and origPostUrl:
            actorReaction = origActor
            reactionUrl2 = origPostUrl
            reaction_postFilename = None

        undoReactionJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Undo',
            'actor': undoActor,
            'to': [actorReaction],
            'object': {
                'type': 'EmojiReact',
                'actor': undoActor,
                'to': [actorReaction],
                'object': reactionUrl2
            }
        }

        # send out the undo emoji reaction to followers
        self._post_to_outbox(undoReactionJson,
                             self.server.project_version, None)

        # directly undo the emoji reaction within the post file
        if not reaction_postFilename:
            reaction_postFilename = \
                locate_post(base_dir, self.post_to_nickname, domain,
                            reactionUrl)
        if reaction_postFilename:
            recent_posts_cache = self.server.recent_posts_cache
            reaction_post_json = load_json(reaction_postFilename, 0, 1)
            if origFilename and origPostUrl:
                undo_reaction_collection_entry(recent_posts_cache,
                                               base_dir,
                                               reaction_postFilename,
                                               reactionUrl,
                                               undoActor, domain, debug,
                                               reaction_post_json,
                                               emojiContent)
                reactionUrl = origPostUrl
                reaction_postFilename = origFilename
            if debug:
                print('Removing emoji reaction for ' + reaction_postFilename)
            undo_reaction_collection_entry(recent_posts_cache,
                                           base_dir,
                                           reaction_postFilename, reactionUrl,
                                           undoActor, domain, debug,
                                           reaction_post_json, emojiContent)
            if debug:
                print('Regenerating html post for changed ' +
                      'emoji reaction collection')
            if reaction_post_json:
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    follower_approval_active(base_dir,
                                             self.post_to_nickname, domain)
                showRepeats = not is_dm(reaction_post_json)
                individual_post_as_html(self.server.signing_priv_key_pem,
                                        False,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, base_dir,
                                        self.server.session,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        self.post_to_nickname, domain,
                                        self.server.port, reaction_post_json,
                                        None, True,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        timelineStr,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.theme_name,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        showRepeats,
                                        showIndividualPostIcons,
                                        manuallyApproveFollowers,
                                        False, True, False,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
            else:
                print('WARN: Unreaction post not found: ' +
                      reaction_postFilename)

        actorAbsolute = self._get_instance_url(calling_domain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(page_number) + timelineBookmark
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_undo_reaction_button',
                            self.server.debug)
        self._redirect_headers(actorPathStr, cookie, calling_domain)

    def _reaction_picker(self, calling_domain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         GETstartTime,
                         proxy_type: str, cookie: str,
                         debug: str) -> None:
        """Press the emoji reaction picker icon at the bottom of the post
        """
        page_number = 1
        reactionUrl = path.split('?selreact=')[1]
        if '?' in reactionUrl:
            reactionUrl = reactionUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        actor = path.split('?selreact=')[0]
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie, calling_domain)
            return

        post_json_object = None
        reaction_postFilename = \
            locate_post(self.server.base_dir,
                        self.post_to_nickname, domain, reactionUrl)
        if reaction_postFilename:
            post_json_object = load_json(reaction_postFilename)
        if not reaction_postFilename or not post_json_object:
            print('WARN: unable to locate reaction post ' + reactionUrl)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie, calling_domain)
            return

        msg = \
            html_emoji_reaction_picker(self.server.css_cache,
                                       self.server.recent_posts_cache,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       self.server.base_dir,
                                       self.server.session,
                                       self.server.cached_webfingers,
                                       self.server.person_cache,
                                       self.post_to_nickname,
                                       domain, port, post_json_object,
                                       self.server.http_prefix,
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
                                       timelineStr, page_number)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        self._set_headers('text/html', msglen,
                          cookie, calling_domain, False)
        self._write(msg)
        fitness_performance(GETstartTime,
                            self.server.fitness,
                            '_GET', '_reaction_picker',
                            self.server.debug)

    def _bookmark_button(self, calling_domain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         GETstartTime,
                         proxy_type: str, cookie: str,
                         debug: str) -> None:
        """Bookmark button was pressed
        """
        page_number = 1
        bookmarkUrl = path.split('?bookmark=')[1]
        if '?' in bookmarkUrl:
            bookmarkUrl = bookmarkUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        actor = path.split('?bookmark=')[0]
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]

        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number)
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        if not self._establish_session("bookmarkButton"):
            self._404()
            return
        bookmarkActor = \
            local_actor_url(http_prefix, self.post_to_nickname, domain_full)
        ccList = []
        bookmark_post(self.server.recent_posts_cache,
                      self.server.session,
                      base_dir,
                      self.server.federation_list,
                      self.post_to_nickname,
                      domain, port,
                      ccList,
                      http_prefix,
                      bookmarkUrl, bookmarkActor, False,
                      self.server.send_threads,
                      self.server.postLog,
                      self.server.person_cache,
                      self.server.cached_webfingers,
                      self.server.debug,
                      self.server.project_version)
        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('bookmark.png'):
            del self.server.iconsCache['bookmark.png']
        bookmarkFilename = \
            locate_post(base_dir, self.post_to_nickname, domain, bookmarkUrl)
        if bookmarkFilename:
            print('Regenerating html post for changed bookmark')
            bookmarkPostJson = load_json(bookmarkFilename, 0, 1)
            if bookmarkPostJson:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, self.post_to_nickname,
                                             domain, bookmarkPostJson)
                print('Bookmarked post json: ' + str(bookmarkPostJson))
                print('Bookmarked post nickname: ' +
                      self.post_to_nickname + ' ' + domain)
                print('Bookmarked post cache: ' + str(cached_post_filename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    follower_approval_active(base_dir,
                                             self.post_to_nickname, domain)
                showRepeats = not is_dm(bookmarkPostJson)
                individual_post_as_html(self.server.signing_priv_key_pem,
                                        False,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, base_dir,
                                        self.server.session,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        self.post_to_nickname, domain,
                                        self.server.port, bookmarkPostJson,
                                        None, True,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        timelineStr,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.theme_name,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        showRepeats,
                                        showIndividualPostIcons,
                                        manuallyApproveFollowers,
                                        False, True, False,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
            else:
                print('WARN: Bookmarked post not found: ' + bookmarkFilename)
        # self._post_to_outbox(bookmarkJson, self.server.project_version, None)
        actorAbsolute = self._get_instance_url(calling_domain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(page_number) + timelineBookmark
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_bookmark_button',
                            self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               calling_domain)

    def _undo_bookmark_button(self, calling_domain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> None:
        """Button pressed to undo a bookmark
        """
        page_number = 1
        bookmarkUrl = path.split('?unbookmark=')[1]
        if '?' in bookmarkUrl:
            bookmarkUrl = bookmarkUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?unbookmark=')[0]
        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._get_instance_url(calling_domain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(page_number)
            self._redirect_headers(actorPathStr, cookie,
                                   calling_domain)
            return
        if not self._establish_session("undo_bookmarkButton"):
            self._404()
            return
        undoActor = \
            local_actor_url(http_prefix, self.post_to_nickname, domain_full)
        ccList = []
        undo_bookmark_post(self.server.recent_posts_cache,
                           self.server.session,
                           base_dir,
                           self.server.federation_list,
                           self.post_to_nickname,
                           domain, port,
                           ccList,
                           http_prefix,
                           bookmarkUrl, undoActor, False,
                           self.server.send_threads,
                           self.server.postLog,
                           self.server.person_cache,
                           self.server.cached_webfingers,
                           debug,
                           self.server.project_version)
        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('bookmark_inactive.png'):
            del self.server.iconsCache['bookmark_inactive.png']
        # self._post_to_outbox(undo_bookmarkJson,
        #                    self.server.project_version, None)
        bookmarkFilename = \
            locate_post(base_dir, self.post_to_nickname, domain, bookmarkUrl)
        if bookmarkFilename:
            print('Regenerating html post for changed unbookmark')
            bookmarkPostJson = load_json(bookmarkFilename, 0, 1)
            if bookmarkPostJson:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, self.post_to_nickname,
                                             domain, bookmarkPostJson)
                print('Unbookmarked post json: ' + str(bookmarkPostJson))
                print('Unbookmarked post nickname: ' +
                      self.post_to_nickname + ' ' + domain)
                print('Unbookmarked post cache: ' + str(cached_post_filename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    follower_approval_active(base_dir,
                                             self.post_to_nickname, domain)
                showRepeats = not is_dm(bookmarkPostJson)
                individual_post_as_html(self.server.signing_priv_key_pem,
                                        False,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, base_dir,
                                        self.server.session,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        self.post_to_nickname, domain,
                                        self.server.port, bookmarkPostJson,
                                        None, True,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        timelineStr,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.theme_name,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        showRepeats,
                                        showIndividualPostIcons,
                                        manuallyApproveFollowers,
                                        False, True, False,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
            else:
                print('WARN: Unbookmarked post not found: ' + bookmarkFilename)
        actorAbsolute = self._get_instance_url(calling_domain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(page_number) + timelineBookmark
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_undo_bookmark_button',
                            self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               calling_domain)

    def _delete_button(self, calling_domain: str, path: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domain_full: str, port: int,
                       onion_domain: str, i2p_domain: str,
                       GETstartTime,
                       proxy_type: str, cookie: str,
                       debug: str) -> None:
        """Delete button is pressed on a post
        """
        if not cookie:
            print('ERROR: no cookie given when deleting ' + path)
            self._400()
            return
        page_number = 1
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        deleteUrl = path.split('?delete=')[1]
        if '?' in deleteUrl:
            deleteUrl = deleteUrl.split('?')[0]
        timelineStr = self.server.default_timeline
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        usersPath = path.split('?delete=')[0]
        actor = \
            http_prefix + '://' + domain_full + usersPath
        if self.server.allow_deletion or \
           deleteUrl.startswith(actor):
            if self.server.debug:
                print('DEBUG: deleteUrl=' + deleteUrl)
                print('DEBUG: actor=' + actor)
            if actor not in deleteUrl:
                # You can only delete your own posts
                if calling_domain.endswith('.onion') and onion_domain:
                    actor = 'http://' + onion_domain + usersPath
                elif calling_domain.endswith('.i2p') and i2p_domain:
                    actor = 'http://' + i2p_domain + usersPath
                self._redirect_headers(actor + '/' + timelineStr,
                                       cookie, calling_domain)
                return
            self.post_to_nickname = get_nickname_from_actor(actor)
            if not self.post_to_nickname:
                print('WARN: unable to find nickname in ' + actor)
                if calling_domain.endswith('.onion') and onion_domain:
                    actor = 'http://' + onion_domain + usersPath
                elif calling_domain.endswith('.i2p') and i2p_domain:
                    actor = 'http://' + i2p_domain + usersPath
                self._redirect_headers(actor + '/' + timelineStr,
                                       cookie, calling_domain)
                return
            if not self._establish_session("deleteButton"):
                self._404()
                return

            deleteStr = \
                html_confirm_delete(self.server.css_cache,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate, page_number,
                                    self.server.session, base_dir,
                                    deleteUrl, http_prefix,
                                    self.server.project_version,
                                    self.server.cached_webfingers,
                                    self.server.person_cache, calling_domain,
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
                                    self.server.lists_enabled)
            if deleteStr:
                deleteStrLen = len(deleteStr)
                self._set_headers('text/html', deleteStrLen,
                                  cookie, calling_domain, False)
                self._write(deleteStr.encode('utf-8'))
                self.server.GETbusy = False
                return
        if calling_domain.endswith('.onion') and onion_domain:
            actor = 'http://' + onion_domain + usersPath
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            actor = 'http://' + i2p_domain + usersPath
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_delete_button',
                            self.server.debug)
        self._redirect_headers(actor + '/' + timelineStr,
                               cookie, calling_domain)

    def _mute_button(self, calling_domain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domain_full: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     GETstartTime,
                     proxy_type: str, cookie: str,
                     debug: str):
        """Mute button is pressed
        """
        muteUrl = path.split('?mute=')[1]
        if '?' in muteUrl:
            muteUrl = muteUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        timelineStr = self.server.default_timeline
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        page_number = 1
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        actor = \
            http_prefix + '://' + domain_full + path.split('?mute=')[0]
        nickname = get_nickname_from_actor(actor)
        mute_post(base_dir, nickname, domain, port,
                  http_prefix, muteUrl,
                  self.server.recent_posts_cache, debug)
        mute_filename = \
            locate_post(base_dir, nickname, domain, muteUrl)
        if mute_filename:
            print('mute_post: Regenerating html post for changed mute status')
            mute_post_json = load_json(mute_filename, 0, 1)
            if mute_post_json:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, nickname,
                                             domain, mute_post_json)
                print('mute_post: Muted post json: ' + str(mute_post_json))
                print('mute_post: Muted post nickname: ' +
                      nickname + ' ' + domain)
                print('mute_post: Muted post cache: ' +
                      str(cached_post_filename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    follower_approval_active(base_dir,
                                             nickname, domain)
                showRepeats = not is_dm(mute_post_json)
                showPublicOnly = False
                storeToCache = True
                useCacheOnly = False
                allowDownloads = False
                showAvatarOptions = True
                avatarUrl = None
                individual_post_as_html(self.server.signing_priv_key_pem,
                                        allowDownloads,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, base_dir,
                                        self.server.session,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        nickname, domain,
                                        self.server.port, mute_post_json,
                                        avatarUrl, showAvatarOptions,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        timelineStr,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.theme_name,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        showRepeats,
                                        showIndividualPostIcons,
                                        manuallyApproveFollowers,
                                        showPublicOnly, storeToCache,
                                        useCacheOnly,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
            else:
                print('WARN: Muted post not found: ' + mute_filename)

        if calling_domain.endswith('.onion') and onion_domain:
            actor = \
                'http://' + onion_domain + \
                path.split('?mute=')[0]
        elif (calling_domain.endswith('.i2p') and i2p_domain):
            actor = \
                'http://' + i2p_domain + \
                path.split('?mute=')[0]
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_mute_button', self.server.debug)
        self._redirect_headers(actor + '/' +
                               timelineStr + timelineBookmark,
                               cookie, calling_domain)

    def _undo_mute_button(self, calling_domain: str, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          GETstartTime,
                          proxy_type: str, cookie: str,
                          debug: str):
        """Undo mute button is pressed
        """
        muteUrl = path.split('?unmute=')[1]
        if '?' in muteUrl:
            muteUrl = muteUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        timelineStr = self.server.default_timeline
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        page_number = 1
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        actor = \
            http_prefix + '://' + domain_full + path.split('?unmute=')[0]
        nickname = get_nickname_from_actor(actor)
        unmute_post(base_dir, nickname, domain, port,
                    http_prefix, muteUrl,
                    self.server.recent_posts_cache, debug)
        mute_filename = \
            locate_post(base_dir, nickname, domain, muteUrl)
        if mute_filename:
            print('unmute_post: ' +
                  'Regenerating html post for changed unmute status')
            mute_post_json = load_json(mute_filename, 0, 1)
            if mute_post_json:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, nickname,
                                             domain, mute_post_json)
                print('unmute_post: Unmuted post json: ' + str(mute_post_json))
                print('unmute_post: Unmuted post nickname: ' +
                      nickname + ' ' + domain)
                print('unmute_post: Unmuted post cache: ' +
                      str(cached_post_filename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    follower_approval_active(base_dir, nickname, domain)
                showRepeats = not is_dm(mute_post_json)
                showPublicOnly = False
                storeToCache = True
                useCacheOnly = False
                allowDownloads = False
                showAvatarOptions = True
                avatarUrl = None
                individual_post_as_html(self.server.signing_priv_key_pem,
                                        allowDownloads,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, base_dir,
                                        self.server.session,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        nickname, domain,
                                        self.server.port, mute_post_json,
                                        avatarUrl, showAvatarOptions,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        timelineStr,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.theme_name,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        showRepeats,
                                        showIndividualPostIcons,
                                        manuallyApproveFollowers,
                                        showPublicOnly, storeToCache,
                                        useCacheOnly,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
            else:
                print('WARN: Unmuted post not found: ' + mute_filename)
        if calling_domain.endswith('.onion') and onion_domain:
            actor = \
                'http://' + onion_domain + path.split('?unmute=')[0]
        elif calling_domain.endswith('.i2p') and i2p_domain:
            actor = \
                'http://' + i2p_domain + path.split('?unmute=')[0]
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_undo_mute_button', self.server.debug)
        self._redirect_headers(actor + '/' + timelineStr +
                               timelineBookmark,
                               cookie, calling_domain)

    def _show_replies_to_post(self, authorized: bool,
                              calling_domain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> bool:
        """Shows the replies to a post
        """
        if not ('/statuses/' in path and '/users/' in path):
            return False

        namedStatus = path.split('/users/')[1]
        if '/' not in namedStatus:
            return False

        postSections = namedStatus.split('/')
        if len(postSections) < 4:
            return False

        if not postSections[3].startswith('replies'):
            return False
        nickname = postSections[0]
        statusNumber = postSections[2]
        if not (len(statusNumber) > 10 and statusNumber.isdigit()):
            return False

        boxname = 'outbox'
        # get the replies file
        postDir = \
            acct_dir(base_dir, nickname, domain) + '/' + boxname
        postRepliesFilename = \
            postDir + '/' + \
            http_prefix + ':##' + domain_full + '#users#' + \
            nickname + '#statuses#' + statusNumber + '.replies'
        if not os.path.isfile(postRepliesFilename):
            # There are no replies,
            # so show empty collection
            contextStr = \
                'https://www.w3.org/ns/activitystreams'

            firstStr = \
                local_actor_url(http_prefix, nickname, domain_full) + \
                '/statuses/' + statusNumber + '/replies?page=true'

            idStr = \
                local_actor_url(http_prefix, nickname, domain_full) + \
                '/statuses/' + statusNumber + '/replies'

            lastStr = \
                local_actor_url(http_prefix, nickname, domain_full) + \
                '/statuses/' + statusNumber + '/replies?page=true'

            repliesJson = {
                '@context': contextStr,
                'first': firstStr,
                'id': idStr,
                'last': lastStr,
                'totalItems': 0,
                'type': 'OrderedCollection'
            }

            if self._request_http():
                if not self._establish_session("showRepliesToPost"):
                    self._404()
                    return True
                recent_posts_cache = self.server.recent_posts_cache
                max_recent_posts = self.server.max_recent_posts
                translate = self.server.translate
                session = self.server.session
                cached_webfingers = self.server.cached_webfingers
                person_cache = self.server.person_cache
                project_version = self.server.project_version
                ytDomain = self.server.yt_replace_domain
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                peertube_instances = self.server.peertube_instances
                msg = \
                    html_post_replies(self.server.css_cache,
                                      recent_posts_cache,
                                      max_recent_posts,
                                      translate,
                                      base_dir,
                                      session,
                                      cached_webfingers,
                                      person_cache,
                                      nickname,
                                      domain,
                                      port,
                                      repliesJson,
                                      http_prefix,
                                      project_version,
                                      ytDomain,
                                      twitter_replacement_domain,
                                      self.server.show_published_date_only,
                                      peertube_instances,
                                      self.server.allow_local_network_access,
                                      self.server.theme_name,
                                      self.server.system_language,
                                      self.server.max_like_count,
                                      self.server.signing_priv_key_pem,
                                      self.server.cw_lists,
                                      self.server.lists_enabled)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_show_replies_to_post',
                                    self.server.debug)
            else:
                if self._secure_mode():
                    msg = json.dumps(repliesJson, ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    protocolStr = 'application/json'
                    msglen = len(msg)
                    self._set_headers(protocolStr, msglen, None,
                                      calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', '_show_replies_to_post json',
                                        self.server.debug)
                else:
                    self._404()
            return True
        else:
            # replies exist. Itterate through the
            # text file containing message ids
            contextStr = 'https://www.w3.org/ns/activitystreams'

            idStr = \
                local_actor_url(http_prefix, nickname, domain_full) + \
                '/statuses/' + statusNumber + '?page=true'

            partOfStr = \
                local_actor_url(http_prefix, nickname, domain_full) + \
                '/statuses/' + statusNumber

            repliesJson = {
                '@context': contextStr,
                'id': idStr,
                'orderedItems': [
                ],
                'partOf': partOfStr,
                'type': 'OrderedCollectionPage'
            }

            # populate the items list with replies
            populate_replies_json(base_dir, nickname, domain,
                                  postRepliesFilename,
                                  authorized, repliesJson)

            # send the replies json
            if self._request_http():
                if not self._establish_session("showRepliesToPost2"):
                    self._404()
                    return True
                recent_posts_cache = self.server.recent_posts_cache
                max_recent_posts = self.server.max_recent_posts
                translate = self.server.translate
                session = self.server.session
                cached_webfingers = self.server.cached_webfingers
                person_cache = self.server.person_cache
                project_version = self.server.project_version
                ytDomain = self.server.yt_replace_domain
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                peertube_instances = self.server.peertube_instances
                msg = \
                    html_post_replies(self.server.css_cache,
                                      recent_posts_cache,
                                      max_recent_posts,
                                      translate,
                                      base_dir,
                                      session,
                                      cached_webfingers,
                                      person_cache,
                                      nickname,
                                      domain,
                                      port,
                                      repliesJson,
                                      http_prefix,
                                      project_version,
                                      ytDomain,
                                      twitter_replacement_domain,
                                      self.server.show_published_date_only,
                                      peertube_instances,
                                      self.server.allow_local_network_access,
                                      self.server.theme_name,
                                      self.server.system_language,
                                      self.server.max_like_count,
                                      self.server.signing_priv_key_pem,
                                      self.server.cw_lists,
                                      self.server.lists_enabled)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_show_replies_to_post',
                                    self.server.debug)
            else:
                if self._secure_mode():
                    msg = json.dumps(repliesJson,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    protocolStr = 'application/json'
                    msglen = len(msg)
                    self._set_headers(protocolStr, msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', '_show_replies_to_post json',
                                        self.server.debug)
                else:
                    self._404()
            return True
        return False

    def _show_roles(self, authorized: bool,
                    calling_domain: str, path: str,
                    base_dir: str, http_prefix: str,
                    domain: str, domain_full: str, port: int,
                    onion_domain: str, i2p_domain: str,
                    GETstartTime,
                    proxy_type: str, cookie: str,
                    debug: str) -> bool:
        """Show roles within profile screen
        """
        namedStatus = path.split('/users/')[1]
        if '/' not in namedStatus:
            return False

        postSections = namedStatus.split('/')
        nickname = postSections[0]
        actorFilename = acct_dir(base_dir, nickname, domain) + '.json'
        if not os.path.isfile(actorFilename):
            return False

        actor_json = load_json(actorFilename)
        if not actor_json:
            return False

        if actor_json.get('hasOccupation'):
            if self._request_http():
                getPerson = \
                    person_lookup(domain, path.replace('/roles', ''),
                                  base_dir)
                if getPerson:
                    default_timeline = \
                        self.server.default_timeline
                    recent_posts_cache = \
                        self.server.recent_posts_cache
                    cached_webfingers = \
                        self.server.cached_webfingers
                    yt_replace_domain = \
                        self.server.yt_replace_domain
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    icons_as_buttons = \
                        self.server.icons_as_buttons

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = self.server.keyShortcuts[nickname]

                    rolesList = get_actor_roles_list(actor_json)
                    city = \
                        get_spoofed_city(self.server.city,
                                         base_dir, nickname, domain)
                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    msg = \
                        html_profile(self.server.signing_priv_key_pem,
                                     self.server.rss_icon_at_top,
                                     self.server.css_cache,
                                     icons_as_buttons,
                                     default_timeline,
                                     recent_posts_cache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     self.server.project_version,
                                     base_dir, http_prefix, True,
                                     getPerson, 'roles',
                                     self.server.session,
                                     cached_webfingers,
                                     self.server.person_cache,
                                     yt_replace_domain,
                                     twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.newswire,
                                     self.server.theme_name,
                                     self.server.dormant_months,
                                     self.server.peertube_instances,
                                     self.server.allow_local_network_access,
                                     self.server.text_mode_banner,
                                     self.server.debug,
                                     access_keys, city,
                                     self.server.system_language,
                                     self.server.max_like_count,
                                     shared_items_federated_domains,
                                     rolesList,
                                     None, None, self.server.cw_lists,
                                     self.server.lists_enabled,
                                     self.server.content_license_url)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', '_show_roles',
                                        self.server.debug)
            else:
                if self._secure_mode():
                    rolesList = get_actor_roles_list(actor_json)
                    msg = json.dumps(rolesList,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', '_show_roles json',
                                        self.server.debug)
                else:
                    self._404()
            return True
        return False

    def _show_skills(self, authorized: bool,
                     calling_domain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domain_full: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     GETstartTime,
                     proxy_type: str, cookie: str,
                     debug: str) -> bool:
        """Show skills on the profile screen
        """
        namedStatus = path.split('/users/')[1]
        if '/' in namedStatus:
            postSections = namedStatus.split('/')
            nickname = postSections[0]
            actorFilename = acct_dir(base_dir, nickname, domain) + '.json'
            if os.path.isfile(actorFilename):
                actor_json = load_json(actorFilename)
                if actor_json:
                    if no_of_actor_skills(actor_json) > 0:
                        if self._request_http():
                            getPerson = \
                                person_lookup(domain,
                                              path.replace('/skills', ''),
                                              base_dir)
                            if getPerson:
                                default_timeline =  \
                                    self.server.default_timeline
                                recent_posts_cache = \
                                    self.server.recent_posts_cache
                                cached_webfingers = \
                                    self.server.cached_webfingers
                                yt_replace_domain = \
                                    self.server.yt_replace_domain
                                twitter_replacement_domain = \
                                    self.server.twitter_replacement_domain
                                show_published_date_only = \
                                    self.server.show_published_date_only
                                icons_as_buttons = \
                                    self.server.icons_as_buttons
                                allow_local_network_access = \
                                    self.server.allow_local_network_access
                                access_keys = self.server.access_keys
                                if self.server.keyShortcuts.get(nickname):
                                    access_keys = \
                                        self.server.keyShortcuts[nickname]
                                actorSkillsList = \
                                    get_occupation_skills(actor_json)
                                skills = get_skills_from_list(actorSkillsList)
                                city = get_spoofed_city(self.server.city,
                                                        base_dir,
                                                        nickname, domain)
                                shared_items_fed_domains = \
                                    self.server.shared_items_federated_domains
                                signing_priv_key_pem = \
                                    self.server.signing_priv_key_pem
                                content_license_url = \
                                    self.server.content_license_url
                                peertube_instances = \
                                    self.server.peertube_instances
                                msg = \
                                    html_profile(signing_priv_key_pem,
                                                 self.server.rss_icon_at_top,
                                                 self.server.css_cache,
                                                 icons_as_buttons,
                                                 default_timeline,
                                                 recent_posts_cache,
                                                 self.server.max_recent_posts,
                                                 self.server.translate,
                                                 self.server.project_version,
                                                 base_dir, http_prefix, True,
                                                 getPerson, 'skills',
                                                 self.server.session,
                                                 cached_webfingers,
                                                 self.server.person_cache,
                                                 yt_replace_domain,
                                                 twitter_replacement_domain,
                                                 show_published_date_only,
                                                 self.server.newswire,
                                                 self.server.theme_name,
                                                 self.server.dormant_months,
                                                 peertube_instances,
                                                 allow_local_network_access,
                                                 self.server.text_mode_banner,
                                                 self.server.debug,
                                                 access_keys, city,
                                                 self.server.system_language,
                                                 self.server.max_like_count,
                                                 shared_items_fed_domains,
                                                 skills,
                                                 None, None,
                                                 self.server.cw_lists,
                                                 self.server.lists_enabled,
                                                 content_license_url)
                                msg = msg.encode('utf-8')
                                msglen = len(msg)
                                self._set_headers('text/html', msglen,
                                                  cookie, calling_domain,
                                                  False)
                                self._write(msg)
                                fitness_performance(GETstartTime,
                                                    self.server.fitness,
                                                    '_GET', '_show_skills',
                                                    self.server.debug)
                        else:
                            if self._secure_mode():
                                actorSkillsList = \
                                    get_occupation_skills(actor_json)
                                skills = get_skills_from_list(actorSkillsList)
                                msg = json.dumps(skills,
                                                 ensure_ascii=False)
                                msg = msg.encode('utf-8')
                                msglen = len(msg)
                                self._set_headers('application/json',
                                                  msglen, None,
                                                  calling_domain, False)
                                self._write(msg)
                                fitness_performance(GETstartTime,
                                                    self.server.fitness,
                                                    '_GET',
                                                    '_show_skills json',
                                                    self.server.debug)
                            else:
                                self._404()
                        return True
        actor = path.replace('/skills', '')
        actorAbsolute = self._get_instance_url(calling_domain) + actor
        self._redirect_headers(actorAbsolute, cookie, calling_domain)
        return True

    def _show_individual_at_post(self, authorized: bool,
                                 calling_domain: str, path: str,
                                 base_dir: str, http_prefix: str,
                                 domain: str, domain_full: str, port: int,
                                 onion_domain: str, i2p_domain: str,
                                 GETstartTime,
                                 proxy_type: str, cookie: str,
                                 debug: str) -> bool:
        """get an individual post from the path /@nickname/statusnumber
        """
        if '/@' not in path:
            return False

        likedBy = None
        if '?likedBy=' in path:
            likedBy = path.split('?likedBy=')[1].strip()
            if '?' in likedBy:
                likedBy = likedBy.split('?')[0]
            path = path.split('?likedBy=')[0]

        reactBy = None
        reactEmoji = None
        if '?reactBy=' in path:
            reactBy = path.split('?reactBy=')[1].strip()
            if ';' in reactBy:
                reactBy = reactBy.split(';')[0]
            if ';emoj=' in path:
                reactEmoji = path.split(';emoj=')[1].strip()
                if ';' in reactEmoji:
                    reactEmoji = reactEmoji.split(';')[0]
            path = path.split('?reactBy=')[0]

        namedStatus = path.split('/@')[1]
        if '/' not in namedStatus:
            # show actor
            nickname = namedStatus
            return False

        postSections = namedStatus.split('/')
        if len(postSections) != 2:
            return False
        nickname = postSections[0]
        statusNumber = postSections[1]
        if len(statusNumber) <= 10 or not statusNumber.isdigit():
            return False

        post_filename = \
            acct_dir(base_dir, nickname, domain) + '/outbox/' + \
            http_prefix + ':##' + domain_full + '#users#' + nickname + \
            '#statuses#' + statusNumber + '.json'

        includeCreateWrapper = False
        if postSections[-1] == 'activity':
            includeCreateWrapper = True

        result = self._show_post_from_file(post_filename, likedBy,
                                           reactBy, reactEmoji,
                                           authorized, calling_domain, path,
                                           base_dir, http_prefix, nickname,
                                           domain, domain_full, port,
                                           onion_domain, i2p_domain,
                                           GETstartTime,
                                           proxy_type, cookie, debug,
                                           includeCreateWrapper)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_show_individual_at_post',
                            self.server.debug)
        return result

    def _show_post_from_file(self, post_filename: str, likedBy: str,
                             reactBy: str, reactEmoji: str,
                             authorized: bool,
                             calling_domain: str, path: str,
                             base_dir: str, http_prefix: str, nickname: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime,
                             proxy_type: str, cookie: str,
                             debug: str, includeCreateWrapper: bool) -> bool:
        """Shows an individual post from its filename
        """
        if not os.path.isfile(post_filename):
            self._404()
            self.server.GETbusy = False
            return True

        post_json_object = load_json(post_filename)
        if not post_json_object:
            self.send_response(429)
            self.end_headers()
            self.server.GETbusy = False
            return True

        # Only authorized viewers get to see likes on posts
        # Otherwize marketers could gain more social graph info
        if not authorized:
            pjo = post_json_object
            if not is_public_post(pjo):
                self._404()
                self.server.GETbusy = False
                return True
            remove_post_interactions(pjo, True)
        if self._request_http():
            msg = \
                html_individual_post(self.server.css_cache,
                                     self.server.recent_posts_cache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     base_dir,
                                     self.server.session,
                                     self.server.cached_webfingers,
                                     self.server.person_cache,
                                     nickname, domain, port,
                                     authorized,
                                     post_json_object,
                                     http_prefix,
                                     self.server.project_version,
                                     likedBy, reactBy, reactEmoji,
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
                                     self.server.lists_enabled)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', '_show_post_from_file',
                                self.server.debug)
        else:
            if self._secure_mode():
                if not includeCreateWrapper and \
                   post_json_object['type'] == 'Create' and \
                   has_object_dict(post_json_object):
                    unwrappedJson = post_json_object['object']
                    unwrappedJson['@context'] = \
                        get_individual_post_context()
                    msg = json.dumps(unwrappedJson,
                                     ensure_ascii=False)
                else:
                    msg = json.dumps(post_json_object,
                                     ensure_ascii=False)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/json',
                                  msglen,
                                  None, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', '_show_post_from_file json',
                                    self.server.debug)
            else:
                self._404()
        self.server.GETbusy = False
        return True

    def _show_individual_post(self, authorized: bool,
                              calling_domain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> bool:
        """Shows an individual post
        """
        likedBy = None
        if '?likedBy=' in path:
            likedBy = path.split('?likedBy=')[1].strip()
            if '?' in likedBy:
                likedBy = likedBy.split('?')[0]
            path = path.split('?likedBy=')[0]

        reactBy = None
        reactEmoji = None
        if '?reactBy=' in path:
            reactBy = path.split('?reactBy=')[1].strip()
            if ';' in reactBy:
                reactBy = reactBy.split(';')[0]
            if ';emoj=' in path:
                reactEmoji = path.split(';emoj=')[1].strip()
                if ';' in reactEmoji:
                    reactEmoji = reactEmoji.split(';')[0]
            path = path.split('?reactBy=')[0]

        namedStatus = path.split('/users/')[1]
        if '/' not in namedStatus:
            return False
        postSections = namedStatus.split('/')
        if len(postSections) < 3:
            return False
        nickname = postSections[0]
        statusNumber = postSections[2]
        if len(statusNumber) <= 10 or (not statusNumber.isdigit()):
            return False

        post_filename = \
            acct_dir(base_dir, nickname, domain) + '/outbox/' + \
            http_prefix + ':##' + domain_full + '#users#' + nickname + \
            '#statuses#' + statusNumber + '.json'

        includeCreateWrapper = False
        if postSections[-1] == 'activity':
            includeCreateWrapper = True

        result = self._show_post_from_file(post_filename, likedBy,
                                           reactBy, reactEmoji,
                                           authorized, calling_domain, path,
                                           base_dir, http_prefix, nickname,
                                           domain, domain_full, port,
                                           onion_domain, i2p_domain,
                                           GETstartTime,
                                           proxy_type, cookie, debug,
                                           includeCreateWrapper)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_show_individual_post',
                            self.server.debug)
        return result

    def _show_notify_post(self, authorized: bool,
                          calling_domain: str, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          GETstartTime,
                          proxy_type: str, cookie: str,
                          debug: str) -> bool:
        """Shows an individual post from an account which you are following
        and where you have the notify checkbox set on person options
        """
        likedBy = None
        reactBy = None
        reactEmoji = None
        post_id = path.split('?notifypost=')[1].strip()
        post_id = post_id.replace('-', '/')
        path = path.split('?notifypost=')[0]
        nickname = path.split('/users/')[1]
        if '/' in nickname:
            return False
        replies = False

        post_filename = locate_post(base_dir, nickname, domain,
                                    post_id, replies)
        if not post_filename:
            return False

        includeCreateWrapper = False
        if path.endswith('/activity'):
            includeCreateWrapper = True

        result = self._show_post_from_file(post_filename, likedBy,
                                           reactBy, reactEmoji,
                                           authorized, calling_domain, path,
                                           base_dir, http_prefix, nickname,
                                           domain, domain_full, port,
                                           onion_domain, i2p_domain,
                                           GETstartTime,
                                           proxy_type, cookie, debug,
                                           includeCreateWrapper)
        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_show_notify_post',
                            self.server.debug)
        return result

    def _show_inbox(self, authorized: bool,
                    calling_domain: str, path: str,
                    base_dir: str, http_prefix: str,
                    domain: str, domain_full: str, port: int,
                    onion_domain: str, i2p_domain: str,
                    GETstartTime,
                    proxy_type: str, cookie: str,
                    debug: str,
                    recent_posts_cache: {}, session,
                    default_timeline: str,
                    max_recent_posts: int,
                    translate: {},
                    cached_webfingers: {},
                    person_cache: {},
                    allow_deletion: bool,
                    project_version: str,
                    yt_replace_domain: str,
                    twitter_replacement_domain: str) -> bool:
        """Shows the inbox timeline
        """
        if '/users/' in path:
            if authorized:
                inboxFeed = \
                    person_box_json(recent_posts_cache,
                                    session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_feed, 'inbox',
                                    authorized,
                                    0,
                                    self.server.positive_voting,
                                    self.server.voting_time_mins)
                if inboxFeed:
                    if GETstartTime:
                        fitness_performance(GETstartTime,
                                            self.server.fitness,
                                            '_GET', '_show_inbox',
                                            self.server.debug)
                    if self._request_http():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/inbox', '')
                        page_number = 1
                        if '?page=' in nickname:
                            page_number = nickname.split('?page=')[1]
                            nickname = nickname.split('?page=')[0]
                            if page_number.isdigit():
                                page_number = int(page_number)
                            else:
                                page_number = 1
                        if 'page=' not in path:
                            # if no page was specified then show the first
                            inboxFeed = \
                                person_box_json(recent_posts_cache,
                                                session,
                                                base_dir,
                                                domain,
                                                port,
                                                path + '?page=1',
                                                http_prefix,
                                                max_posts_in_feed, 'inbox',
                                                authorized,
                                                0,
                                                self.server.positive_voting,
                                                self.server.voting_time_mins)
                            if GETstartTime:
                                fitness_performance(GETstartTime,
                                                    self.server.fitness,
                                                    '_GET', '_show_inbox2',
                                                    self.server.debug)
                        full_width_tl_button_header = \
                            self.server.full_width_tl_button_header
                        minimalNick = is_minimal(base_dir, domain, nickname)

                        access_keys = self.server.access_keys
                        if self.server.keyShortcuts.get(nickname):
                            access_keys = \
                                self.server.keyShortcuts[nickname]
                        shared_items_federated_domains = \
                            self.server.shared_items_federated_domains
                        allow_local_network_access = \
                            self.server.allow_local_network_access
                        msg = html_inbox(self.server.css_cache,
                                         default_timeline,
                                         recent_posts_cache,
                                         max_recent_posts,
                                         translate,
                                         page_number, max_posts_in_feed,
                                         session,
                                         base_dir,
                                         cached_webfingers,
                                         person_cache,
                                         nickname,
                                         domain,
                                         port,
                                         inboxFeed,
                                         allow_deletion,
                                         http_prefix,
                                         project_version,
                                         minimalNick,
                                         yt_replace_domain,
                                         twitter_replacement_domain,
                                         self.server.show_published_date_only,
                                         self.server.newswire,
                                         self.server.positive_voting,
                                         self.server.show_publish_as_icon,
                                         full_width_tl_button_header,
                                         self.server.icons_as_buttons,
                                         self.server.rss_icon_at_top,
                                         self.server.publish_button_at_top,
                                         authorized,
                                         self.server.theme_name,
                                         self.server.peertube_instances,
                                         allow_local_network_access,
                                         self.server.text_mode_banner,
                                         access_keys,
                                         self.server.system_language,
                                         self.server.max_like_count,
                                         shared_items_federated_domains,
                                         self.server.signing_priv_key_pem,
                                         self.server.cw_lists,
                                         self.server.lists_enabled)
                        if GETstartTime:
                            fitness_performance(GETstartTime,
                                                self.server.fitness,
                                                '_GET', '_show_inbox3',
                                                self.server.debug)
                        if msg:
                            msg = msg.encode('utf-8')
                            msglen = len(msg)
                            self._set_headers('text/html', msglen,
                                              cookie, calling_domain, False)
                            self._write(msg)

                        if GETstartTime:
                            fitness_performance(GETstartTime,
                                                self.server.fitness,
                                                '_GET', '_show_inbox4',
                                                self.server.debug)
                    else:
                        # don't need authorized fetch here because
                        # there is already the authorization check
                        msg = json.dumps(inboxFeed, ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('application/json', msglen,
                                          None, calling_domain, False)
                        self._write(msg)
                        fitness_performance(GETstartTime,
                                            self.server.fitness,
                                            '_GET', '_show_inbox5',
                                            self.server.debug)
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/inbox', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/inbox':
            # not the shared inbox
            if debug:
                print('DEBUG: GET access to inbox is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _show_d_ms(self, authorized: bool,
                   calling_domain: str, path: str,
                   base_dir: str, http_prefix: str,
                   domain: str, domain_full: str, port: int,
                   onion_domain: str, i2p_domain: str,
                   GETstartTime,
                   proxy_type: str, cookie: str,
                   debug: str) -> bool:
        """Shows the DMs timeline
        """
        if '/users/' in path:
            if authorized:
                inboxDMFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_feed, 'dm',
                                    authorized,
                                    0, self.server.positive_voting,
                                    self.server.voting_time_mins)
                if inboxDMFeed:
                    if self._request_http():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/dm', '')
                        page_number = 1
                        if '?page=' in nickname:
                            page_number = nickname.split('?page=')[1]
                            nickname = nickname.split('?page=')[0]
                            if page_number.isdigit():
                                page_number = int(page_number)
                            else:
                                page_number = 1
                        if 'page=' not in path:
                            # if no page was specified then show the first
                            inboxDMFeed = \
                                person_box_json(self.server.recent_posts_cache,
                                                self.server.session,
                                                base_dir,
                                                domain,
                                                port,
                                                path + '?page=1',
                                                http_prefix,
                                                max_posts_in_feed, 'dm',
                                                authorized,
                                                0,
                                                self.server.positive_voting,
                                                self.server.voting_time_mins)
                        full_width_tl_button_header = \
                            self.server.full_width_tl_button_header
                        minimalNick = is_minimal(base_dir, domain, nickname)

                        access_keys = self.server.access_keys
                        if self.server.keyShortcuts.get(nickname):
                            access_keys = \
                                self.server.keyShortcuts[nickname]

                        shared_items_federated_domains = \
                            self.server.shared_items_federated_domains
                        allow_local_network_access = \
                            self.server.allow_local_network_access
                        twitter_replacement_domain = \
                            self.server.twitter_replacement_domain
                        show_published_date_only = \
                            self.server.show_published_date_only
                        msg = \
                            html_inbox_d_ms(self.server.css_cache,
                                            self.server.default_timeline,
                                            self.server.recent_posts_cache,
                                            self.server.max_recent_posts,
                                            self.server.translate,
                                            page_number, max_posts_in_feed,
                                            self.server.session,
                                            base_dir,
                                            self.server.cached_webfingers,
                                            self.server.person_cache,
                                            nickname,
                                            domain,
                                            port,
                                            inboxDMFeed,
                                            self.server.allow_deletion,
                                            http_prefix,
                                            self.server.project_version,
                                            minimalNick,
                                            self.server.yt_replace_domain,
                                            twitter_replacement_domain,
                                            show_published_date_only,
                                            self.server.newswire,
                                            self.server.positive_voting,
                                            self.server.show_publish_as_icon,
                                            full_width_tl_button_header,
                                            self.server.icons_as_buttons,
                                            self.server.rss_icon_at_top,
                                            self.server.publish_button_at_top,
                                            authorized, self.server.theme_name,
                                            self.server.peertube_instances,
                                            allow_local_network_access,
                                            self.server.text_mode_banner,
                                            access_keys,
                                            self.server.system_language,
                                            self.server.max_like_count,
                                            shared_items_federated_domains,
                                            self.server.signing_priv_key_pem,
                                            self.server.cw_lists,
                                            self.server.lists_enabled)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, calling_domain, False)
                        self._write(msg)
                        fitness_performance(GETstartTime,
                                            self.server.fitness,
                                            '_GET', '_show_d_ms',
                                            self.server.debug)
                    else:
                        # don't need authorized fetch here because
                        # there is already the authorization check
                        msg = json.dumps(inboxDMFeed, ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('application/json',
                                          msglen,
                                          None, calling_domain, False)
                        self._write(msg)
                        fitness_performance(GETstartTime,
                                            self.server.fitness,
                                            '_GET', '_show_d_ms json',
                                            self.server.debug)
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/dm', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/dm':
            # not the DM inbox
            if debug:
                print('DEBUG: GET access to DM timeline is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _show_replies(self, authorized: bool,
                      calling_domain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domain_full: str, port: int,
                      onion_domain: str, i2p_domain: str,
                      GETstartTime,
                      proxy_type: str, cookie: str,
                      debug: str) -> bool:
        """Shows the replies timeline
        """
        if '/users/' in path:
            if authorized:
                inboxRepliesFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_feed, 'tlreplies',
                                    True,
                                    0, self.server.positive_voting,
                                    self.server.voting_time_mins)
                if not inboxRepliesFeed:
                    inboxRepliesFeed = []
                if self._request_http():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlreplies', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inboxRepliesFeed = \
                            person_box_json(self.server.recent_posts_cache,
                                            self.server.session,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            max_posts_in_feed, 'tlreplies',
                                            True,
                                            0, self.server.positive_voting,
                                            self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = is_minimal(base_dir, domain, nickname)

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = \
                            self.server.keyShortcuts[nickname]

                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    msg = \
                        html_inbox_replies(self.server.css_cache,
                                           self.server.default_timeline,
                                           self.server.recent_posts_cache,
                                           self.server.max_recent_posts,
                                           self.server.translate,
                                           page_number, max_posts_in_feed,
                                           self.server.session,
                                           base_dir,
                                           self.server.cached_webfingers,
                                           self.server.person_cache,
                                           nickname,
                                           domain,
                                           port,
                                           inboxRepliesFeed,
                                           self.server.allow_deletion,
                                           http_prefix,
                                           self.server.project_version,
                                           minimalNick,
                                           self.server.yt_replace_domain,
                                           twitter_replacement_domain,
                                           show_published_date_only,
                                           self.server.newswire,
                                           self.server.positive_voting,
                                           self.server.show_publish_as_icon,
                                           full_width_tl_button_header,
                                           self.server.icons_as_buttons,
                                           self.server.rss_icon_at_top,
                                           self.server.publish_button_at_top,
                                           authorized, self.server.theme_name,
                                           self.server.peertube_instances,
                                           allow_local_network_access,
                                           self.server.text_mode_banner,
                                           access_keys,
                                           self.server.system_language,
                                           self.server.max_like_count,
                                           shared_items_federated_domains,
                                           self.server.signing_priv_key_pem,
                                           self.server.cw_lists,
                                           self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_replies',
                                        self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxRepliesFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_replies json',
                                        self.server.debug)
                return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlreplies', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlreplies':
            # not the replies inbox
            if debug:
                print('DEBUG: GET access to inbox is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _show_media_timeline(self, authorized: bool,
                             calling_domain: str, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime,
                             proxy_type: str, cookie: str,
                             debug: str) -> bool:
        """Shows the media timeline
        """
        if '/users/' in path:
            if authorized:
                inboxMediaFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_media_feed, 'tlmedia',
                                    True,
                                    0, self.server.positive_voting,
                                    self.server.voting_time_mins)
                if not inboxMediaFeed:
                    inboxMediaFeed = []
                if self._request_http():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlmedia', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inboxMediaFeed = \
                            person_box_json(self.server.recent_posts_cache,
                                            self.server.session,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            max_posts_in_media_feed, 'tlmedia',
                                            True,
                                            0, self.server.positive_voting,
                                            self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = is_minimal(base_dir, domain, nickname)

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = \
                            self.server.keyShortcuts[nickname]
                    fed_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    msg = \
                        html_inbox_media(self.server.css_cache,
                                         self.server.default_timeline,
                                         self.server.recent_posts_cache,
                                         self.server.max_recent_posts,
                                         self.server.translate,
                                         page_number, max_posts_in_media_feed,
                                         self.server.session,
                                         base_dir,
                                         self.server.cached_webfingers,
                                         self.server.person_cache,
                                         nickname,
                                         domain,
                                         port,
                                         inboxMediaFeed,
                                         self.server.allow_deletion,
                                         http_prefix,
                                         self.server.project_version,
                                         minimalNick,
                                         self.server.yt_replace_domain,
                                         twitter_replacement_domain,
                                         self.server.show_published_date_only,
                                         self.server.newswire,
                                         self.server.positive_voting,
                                         self.server.show_publish_as_icon,
                                         full_width_tl_button_header,
                                         self.server.icons_as_buttons,
                                         self.server.rss_icon_at_top,
                                         self.server.publish_button_at_top,
                                         authorized,
                                         self.server.theme_name,
                                         self.server.peertube_instances,
                                         allow_local_network_access,
                                         self.server.text_mode_banner,
                                         access_keys,
                                         self.server.system_language,
                                         self.server.max_like_count,
                                         fed_domains,
                                         self.server.signing_priv_key_pem,
                                         self.server.cw_lists,
                                         self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_media_timeline',
                                        self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxMediaFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_media_timeline json',
                                        self.server.debug)
                return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlmedia', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlmedia':
            # not the media inbox
            if debug:
                print('DEBUG: GET access to inbox is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _show_blogs_timeline(self, authorized: bool,
                             calling_domain: str, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime,
                             proxy_type: str, cookie: str,
                             debug: str) -> bool:
        """Shows the blogs timeline
        """
        if '/users/' in path:
            if authorized:
                inboxBlogsFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_blogs_feed, 'tlblogs',
                                    True,
                                    0, self.server.positive_voting,
                                    self.server.voting_time_mins)
                if not inboxBlogsFeed:
                    inboxBlogsFeed = []
                if self._request_http():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlblogs', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inboxBlogsFeed = \
                            person_box_json(self.server.recent_posts_cache,
                                            self.server.session,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            max_posts_in_blogs_feed, 'tlblogs',
                                            True,
                                            0, self.server.positive_voting,
                                            self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = is_minimal(base_dir, domain, nickname)

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = \
                            self.server.keyShortcuts[nickname]
                    fed_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    msg = \
                        html_inbox_blogs(self.server.css_cache,
                                         self.server.default_timeline,
                                         self.server.recent_posts_cache,
                                         self.server.max_recent_posts,
                                         self.server.translate,
                                         page_number, max_posts_in_blogs_feed,
                                         self.server.session,
                                         base_dir,
                                         self.server.cached_webfingers,
                                         self.server.person_cache,
                                         nickname,
                                         domain,
                                         port,
                                         inboxBlogsFeed,
                                         self.server.allow_deletion,
                                         http_prefix,
                                         self.server.project_version,
                                         minimalNick,
                                         self.server.yt_replace_domain,
                                         twitter_replacement_domain,
                                         self.server.show_published_date_only,
                                         self.server.newswire,
                                         self.server.positive_voting,
                                         self.server.show_publish_as_icon,
                                         full_width_tl_button_header,
                                         self.server.icons_as_buttons,
                                         self.server.rss_icon_at_top,
                                         self.server.publish_button_at_top,
                                         authorized,
                                         self.server.theme_name,
                                         self.server.peertube_instances,
                                         allow_local_network_access,
                                         self.server.text_mode_banner,
                                         access_keys,
                                         self.server.system_language,
                                         self.server.max_like_count,
                                         fed_domains,
                                         self.server.signing_priv_key_pem,
                                         self.server.cw_lists,
                                         self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_blogs_timeline',
                                        self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxBlogsFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_blogs_timeline json',
                                        self.server.debug)
                return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlblogs', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlblogs':
            # not the blogs inbox
            if debug:
                print('DEBUG: GET access to blogs is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _show_news_timeline(self, authorized: bool,
                            calling_domain: str, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domain_full: str, port: int,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            proxy_type: str, cookie: str,
                            debug: str) -> bool:
        """Shows the news timeline
        """
        if '/users/' in path:
            if authorized:
                inboxNewsFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_news_feed, 'tlnews',
                                    True,
                                    self.server.newswire_votes_threshold,
                                    self.server.positive_voting,
                                    self.server.voting_time_mins)
                if not inboxNewsFeed:
                    inboxNewsFeed = []
                if self._request_http():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlnews', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        newswire_votes_threshold = \
                            self.server.newswire_votes_threshold
                        # if no page was specified then show the first
                        inboxNewsFeed = \
                            person_box_json(self.server.recent_posts_cache,
                                            self.server.session,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            max_posts_in_blogs_feed, 'tlnews',
                                            True,
                                            newswire_votes_threshold,
                                            self.server.positive_voting,
                                            self.server.voting_time_mins)
                    currNickname = path.split('/users/')[1]
                    if '/' in currNickname:
                        currNickname = currNickname.split('/')[0]
                    moderator = is_moderator(base_dir, currNickname)
                    editor = is_editor(base_dir, currNickname)
                    artist = is_artist(base_dir, currNickname)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = is_minimal(base_dir, domain, nickname)

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = \
                            self.server.keyShortcuts[nickname]
                    fed_domains = \
                        self.server.shared_items_federated_domains

                    msg = \
                        html_inbox_news(self.server.css_cache,
                                        self.server.default_timeline,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, max_posts_in_news_feed,
                                        self.server.session,
                                        base_dir,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        nickname,
                                        domain,
                                        port,
                                        inboxNewsFeed,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        minimalNick,
                                        self.server.yt_replace_domain,
                                        self.server.twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.newswire,
                                        moderator, editor, artist,
                                        self.server.positive_voting,
                                        self.server.show_publish_as_icon,
                                        full_width_tl_button_header,
                                        self.server.icons_as_buttons,
                                        self.server.rss_icon_at_top,
                                        self.server.publish_button_at_top,
                                        authorized,
                                        self.server.theme_name,
                                        self.server.peertube_instances,
                                        self.server.allow_local_network_access,
                                        self.server.text_mode_banner,
                                        access_keys,
                                        self.server.system_language,
                                        self.server.max_like_count,
                                        fed_domains,
                                        self.server.signing_priv_key_pem,
                                        self.server.cw_lists,
                                        self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_news_timeline',
                                        self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxNewsFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_news_timeline json',
                                        self.server.debug)
                return True
            else:
                if debug:
                    nickname = 'news'
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlnews':
            # not the news inbox
            if debug:
                print('DEBUG: GET access to news is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _show_features_timeline(self, authorized: bool,
                                calling_domain: str, path: str,
                                base_dir: str, http_prefix: str,
                                domain: str, domain_full: str, port: int,
                                onion_domain: str, i2p_domain: str,
                                GETstartTime,
                                proxy_type: str, cookie: str,
                                debug: str) -> bool:
        """Shows the features timeline (all local blogs)
        """
        if '/users/' in path:
            if authorized:
                inboxFeaturesFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_news_feed, 'tlfeatures',
                                    True,
                                    self.server.newswire_votes_threshold,
                                    self.server.positive_voting,
                                    self.server.voting_time_mins)
                if not inboxFeaturesFeed:
                    inboxFeaturesFeed = []
                if self._request_http():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlfeatures', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        newswire_votes_threshold = \
                            self.server.newswire_votes_threshold
                        # if no page was specified then show the first
                        inboxFeaturesFeed = \
                            person_box_json(self.server.recent_posts_cache,
                                            self.server.session,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            max_posts_in_blogs_feed,
                                            'tlfeatures',
                                            True,
                                            newswire_votes_threshold,
                                            self.server.positive_voting,
                                            self.server.voting_time_mins)
                    currNickname = path.split('/users/')[1]
                    if '/' in currNickname:
                        currNickname = currNickname.split('/')[0]
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = is_minimal(base_dir, domain, nickname)

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = \
                            self.server.keyShortcuts[nickname]

                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    msg = \
                        html_inbox_features(self.server.css_cache,
                                            self.server.default_timeline,
                                            self.server.recent_posts_cache,
                                            self.server.max_recent_posts,
                                            self.server.translate,
                                            page_number,
                                            max_posts_in_blogs_feed,
                                            self.server.session,
                                            base_dir,
                                            self.server.cached_webfingers,
                                            self.server.person_cache,
                                            nickname,
                                            domain,
                                            port,
                                            inboxFeaturesFeed,
                                            self.server.allow_deletion,
                                            http_prefix,
                                            self.server.project_version,
                                            minimalNick,
                                            self.server.yt_replace_domain,
                                            twitter_replacement_domain,
                                            show_published_date_only,
                                            self.server.newswire,
                                            self.server.positive_voting,
                                            self.server.show_publish_as_icon,
                                            full_width_tl_button_header,
                                            self.server.icons_as_buttons,
                                            self.server.rss_icon_at_top,
                                            self.server.publish_button_at_top,
                                            authorized,
                                            self.server.theme_name,
                                            self.server.peertube_instances,
                                            allow_local_network_access,
                                            self.server.text_mode_banner,
                                            access_keys,
                                            self.server.system_language,
                                            self.server.max_like_count,
                                            shared_items_federated_domains,
                                            self.server.signing_priv_key_pem,
                                            self.server.cw_lists,
                                            self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_features_timeline',
                                        self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxFeaturesFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_features_timeline json',
                                        self.server.debug)
                return True
            else:
                if debug:
                    nickname = 'news'
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlfeatures':
            # not the features inbox
            if debug:
                print('DEBUG: GET access to features is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _show_shares_timeline(self, authorized: bool,
                              calling_domain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> bool:
        """Shows the shares timeline
        """
        if '/users/' in path:
            if authorized:
                if self._request_http():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlshares', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = \
                            self.server.keyShortcuts[nickname]
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header

                    msg = \
                        html_shares(self.server.css_cache,
                                    self.server.default_timeline,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, max_posts_in_feed,
                                    self.server.session,
                                    base_dir,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    nickname,
                                    domain,
                                    port,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.newswire,
                                    self.server.positive_voting,
                                    self.server.show_publish_as_icon,
                                    full_width_tl_button_header,
                                    self.server.icons_as_buttons,
                                    self.server.rss_icon_at_top,
                                    self.server.publish_button_at_top,
                                    authorized, self.server.theme_name,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.text_mode_banner,
                                    access_keys,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    self.server.shared_items_federated_domains,
                                    self.server.signing_priv_key_pem,
                                    self.server.cw_lists,
                                    self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_shares_timeline',
                                        self.server.debug)
                    return True
        # not the shares timeline
        if debug:
            print('DEBUG: GET access to shares timeline is unauthorized')
        self.send_response(405)
        self.end_headers()
        return True

    def _show_wanted_timeline(self, authorized: bool,
                              calling_domain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> bool:
        """Shows the wanted timeline
        """
        if '/users/' in path:
            if authorized:
                if self._request_http():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlwanted', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1

                    access_keys = self.server.access_keys
                    if self.server.keyShortcuts.get(nickname):
                        access_keys = \
                            self.server.keyShortcuts[nickname]
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    msg = \
                        html_wanted(self.server.css_cache,
                                    self.server.default_timeline,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, max_posts_in_feed,
                                    self.server.session,
                                    base_dir,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    nickname,
                                    domain,
                                    port,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.newswire,
                                    self.server.positive_voting,
                                    self.server.show_publish_as_icon,
                                    full_width_tl_button_header,
                                    self.server.icons_as_buttons,
                                    self.server.rss_icon_at_top,
                                    self.server.publish_button_at_top,
                                    authorized, self.server.theme_name,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.text_mode_banner,
                                    access_keys,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    self.server.shared_items_federated_domains,
                                    self.server.signing_priv_key_pem,
                                    self.server.cw_lists,
                                    self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_wanted_timeline',
                                        self.server.debug)
                    return True
        # not the shares timeline
        if debug:
            print('DEBUG: GET access to wanted timeline is unauthorized')
        self.send_response(405)
        self.end_headers()
        return True

    def _show_bookmarks_timeline(self, authorized: bool,
                                 calling_domain: str, path: str,
                                 base_dir: str, http_prefix: str,
                                 domain: str, domain_full: str, port: int,
                                 onion_domain: str, i2p_domain: str,
                                 GETstartTime,
                                 proxy_type: str, cookie: str,
                                 debug: str) -> bool:
        """Shows the bookmarks timeline
        """
        if '/users/' in path:
            if authorized:
                bookmarksFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_feed, 'tlbookmarks',
                                    authorized,
                                    0, self.server.positive_voting,
                                    self.server.voting_time_mins)
                if bookmarksFeed:
                    if self._request_http():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/tlbookmarks', '')
                        nickname = nickname.replace('/bookmarks', '')
                        page_number = 1
                        if '?page=' in nickname:
                            page_number = nickname.split('?page=')[1]
                            nickname = nickname.split('?page=')[0]
                            if page_number.isdigit():
                                page_number = int(page_number)
                            else:
                                page_number = 1
                        if 'page=' not in path:
                            # if no page was specified then show the first
                            bookmarksFeed = \
                                person_box_json(self.server.recent_posts_cache,
                                                self.server.session,
                                                base_dir,
                                                domain,
                                                port,
                                                path + '?page=1',
                                                http_prefix,
                                                max_posts_in_feed,
                                                'tlbookmarks',
                                                authorized,
                                                0, self.server.positive_voting,
                                                self.server.voting_time_mins)
                        full_width_tl_button_header = \
                            self.server.full_width_tl_button_header
                        minimalNick = is_minimal(base_dir, domain, nickname)

                        access_keys = self.server.access_keys
                        if self.server.keyShortcuts.get(nickname):
                            access_keys = \
                                self.server.keyShortcuts[nickname]

                        shared_items_federated_domains = \
                            self.server.shared_items_federated_domains
                        allow_local_network_access = \
                            self.server.allow_local_network_access
                        twitter_replacement_domain = \
                            self.server.twitter_replacement_domain
                        show_published_date_only = \
                            self.server.show_published_date_only
                        msg = \
                            html_bookmarks(self.server.css_cache,
                                           self.server.default_timeline,
                                           self.server.recent_posts_cache,
                                           self.server.max_recent_posts,
                                           self.server.translate,
                                           page_number, max_posts_in_feed,
                                           self.server.session,
                                           base_dir,
                                           self.server.cached_webfingers,
                                           self.server.person_cache,
                                           nickname,
                                           domain,
                                           port,
                                           bookmarksFeed,
                                           self.server.allow_deletion,
                                           http_prefix,
                                           self.server.project_version,
                                           minimalNick,
                                           self.server.yt_replace_domain,
                                           twitter_replacement_domain,
                                           show_published_date_only,
                                           self.server.newswire,
                                           self.server.positive_voting,
                                           self.server.show_publish_as_icon,
                                           full_width_tl_button_header,
                                           self.server.icons_as_buttons,
                                           self.server.rss_icon_at_top,
                                           self.server.publish_button_at_top,
                                           authorized,
                                           self.server.theme_name,
                                           self.server.peertube_instances,
                                           allow_local_network_access,
                                           self.server.text_mode_banner,
                                           access_keys,
                                           self.server.system_language,
                                           self.server.max_like_count,
                                           shared_items_federated_domains,
                                           self.server.signing_priv_key_pem,
                                           self.server.cw_lists,
                                           self.server.lists_enabled)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, calling_domain, False)
                        self._write(msg)
                        fitness_performance(GETstartTime,
                                            self.server.fitness,
                                            '_GET', '_show_bookmarks_timeline',
                                            self.server.debug)
                    else:
                        # don't need authorized fetch here because
                        # there is already the authorization check
                        msg = json.dumps(bookmarksFeed,
                                         ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('application/json', msglen,
                                          None, calling_domain, False)
                        self._write(msg)
                        fitness_performance(GETstartTime,
                                            self.server.fitness,
                                            '_GET',
                                            '_show_bookmarks_timeline json',
                                            self.server.debug)
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlbookmarks', '')
                    nickname = nickname.replace('/bookmarks', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if debug:
            print('DEBUG: GET access to bookmarks is unauthorized')
        self.send_response(405)
        self.end_headers()
        return True

    def _show_outbox_timeline(self, authorized: bool,
                              calling_domain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domain_full: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> bool:
        """Shows the outbox timeline
        """
        # get outbox feed for a person
        outboxFeed = \
            person_box_json(self.server.recent_posts_cache,
                            self.server.session,
                            base_dir, domain, port, path,
                            http_prefix, max_posts_in_feed, 'outbox',
                            authorized,
                            self.server.newswire_votes_threshold,
                            self.server.positive_voting,
                            self.server.voting_time_mins)
        if outboxFeed:
            nickname = \
                path.replace('/users/', '').replace('/outbox', '')
            page_number = 0
            if '?page=' in nickname:
                page_number = nickname.split('?page=')[1]
                nickname = nickname.split('?page=')[0]
                if page_number.isdigit():
                    page_number = int(page_number)
                else:
                    page_number = 1
            else:
                if self._request_http():
                    page_number = 1
            if authorized and page_number >= 1:
                # if a page wasn't specified then show the first one
                pageStr = '?page=' + str(page_number)
                outboxFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir, domain, port,
                                    path + pageStr,
                                    http_prefix,
                                    max_posts_in_feed, 'outbox',
                                    authorized,
                                    self.server.newswire_votes_threshold,
                                    self.server.positive_voting,
                                    self.server.voting_time_mins)
            else:
                page_number = 1

            if self._request_http():
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header
                minimalNick = is_minimal(base_dir, domain, nickname)

                access_keys = self.server.access_keys
                if self.server.keyShortcuts.get(nickname):
                    access_keys = \
                        self.server.keyShortcuts[nickname]

                msg = \
                    html_outbox(self.server.css_cache,
                                self.server.default_timeline,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.translate,
                                page_number, max_posts_in_feed,
                                self.server.session,
                                base_dir,
                                self.server.cached_webfingers,
                                self.server.person_cache,
                                nickname, domain, port,
                                outboxFeed,
                                self.server.allow_deletion,
                                http_prefix,
                                self.server.project_version,
                                minimalNick,
                                self.server.yt_replace_domain,
                                self.server.twitter_replacement_domain,
                                self.server.show_published_date_only,
                                self.server.newswire,
                                self.server.positive_voting,
                                self.server.show_publish_as_icon,
                                full_width_tl_button_header,
                                self.server.icons_as_buttons,
                                self.server.rss_icon_at_top,
                                self.server.publish_button_at_top,
                                authorized,
                                self.server.theme_name,
                                self.server.peertube_instances,
                                self.server.allow_local_network_access,
                                self.server.text_mode_banner,
                                access_keys,
                                self.server.system_language,
                                self.server.max_like_count,
                                self.server.shared_items_federated_domains,
                                self.server.signing_priv_key_pem,
                                self.server.cw_lists,
                                self.server.lists_enabled)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime,
                                    self.server.fitness,
                                    '_GET', '_show_outbox_timeline',
                                    self.server.debug)
            else:
                if self._secure_mode():
                    msg = json.dumps(outboxFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_outbox_timeline json',
                                        self.server.debug)
                else:
                    self._404()
            return True
        return False

    def _show_mod_timeline(self, authorized: bool,
                           calling_domain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domain_full: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime,
                           proxy_type: str, cookie: str,
                           debug: str) -> bool:
        """Shows the moderation timeline
        """
        if '/users/' in path:
            if authorized:
                moderationFeed = \
                    person_box_json(self.server.recent_posts_cache,
                                    self.server.session,
                                    base_dir,
                                    domain,
                                    port,
                                    path,
                                    http_prefix,
                                    max_posts_in_feed, 'moderation',
                                    True,
                                    0, self.server.positive_voting,
                                    self.server.voting_time_mins)
                if moderationFeed:
                    if self._request_http():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/moderation', '')
                        page_number = 1
                        if '?page=' in nickname:
                            page_number = nickname.split('?page=')[1]
                            nickname = nickname.split('?page=')[0]
                            if page_number.isdigit():
                                page_number = int(page_number)
                            else:
                                page_number = 1
                        if 'page=' not in path:
                            # if no page was specified then show the first
                            moderationFeed = \
                                person_box_json(self.server.recent_posts_cache,
                                                self.server.session,
                                                base_dir,
                                                domain,
                                                port,
                                                path + '?page=1',
                                                http_prefix,
                                                max_posts_in_feed,
                                                'moderation',
                                                True,
                                                0, self.server.positive_voting,
                                                self.server.voting_time_mins)
                        full_width_tl_button_header = \
                            self.server.full_width_tl_button_header
                        moderationActionStr = ''

                        access_keys = self.server.access_keys
                        if self.server.keyShortcuts.get(nickname):
                            access_keys = \
                                self.server.keyShortcuts[nickname]

                        shared_items_federated_domains = \
                            self.server.shared_items_federated_domains
                        twitter_replacement_domain = \
                            self.server.twitter_replacement_domain
                        allow_local_network_access = \
                            self.server.allow_local_network_access
                        show_published_date_only = \
                            self.server.show_published_date_only
                        msg = \
                            html_moderation(self.server.css_cache,
                                            self.server.default_timeline,
                                            self.server.recent_posts_cache,
                                            self.server.max_recent_posts,
                                            self.server.translate,
                                            page_number, max_posts_in_feed,
                                            self.server.session,
                                            base_dir,
                                            self.server.cached_webfingers,
                                            self.server.person_cache,
                                            nickname,
                                            domain,
                                            port,
                                            moderationFeed,
                                            True,
                                            http_prefix,
                                            self.server.project_version,
                                            self.server.yt_replace_domain,
                                            twitter_replacement_domain,
                                            show_published_date_only,
                                            self.server.newswire,
                                            self.server.positive_voting,
                                            self.server.show_publish_as_icon,
                                            full_width_tl_button_header,
                                            self.server.icons_as_buttons,
                                            self.server.rss_icon_at_top,
                                            self.server.publish_button_at_top,
                                            authorized, moderationActionStr,
                                            self.server.theme_name,
                                            self.server.peertube_instances,
                                            allow_local_network_access,
                                            self.server.text_mode_banner,
                                            access_keys,
                                            self.server.system_language,
                                            self.server.max_like_count,
                                            shared_items_federated_domains,
                                            self.server.signing_priv_key_pem,
                                            self.server.cw_lists,
                                            self.server.lists_enabled)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, calling_domain, False)
                        self._write(msg)
                        fitness_performance(GETstartTime,
                                            self.server.fitness,
                                            '_GET', '_show_mod_timeline',
                                            self.server.debug)
                    else:
                        # don't need authorized fetch here because
                        # there is already the authorization check
                        msg = json.dumps(moderationFeed,
                                         ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('application/json', msglen,
                                          None, calling_domain, False)
                        self._write(msg)
                        fitness_performance(GETstartTime,
                                            self.server.fitness,
                                            '_GET', '_show_mod_timeline json',
                                            self.server.debug)
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/moderation', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if debug:
            print('DEBUG: GET access to moderation feed is unauthorized')
        self.send_response(405)
        self.end_headers()
        return True

    def _show_shares_feed(self, authorized: bool,
                          calling_domain: str, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          GETstartTime,
                          proxy_type: str, cookie: str,
                          debug: str, shares_file_type: str) -> bool:
        """Shows the shares feed
        """
        shares = \
            get_shares_feed_for_person(base_dir, domain, port, path,
                                       http_prefix, shares_file_type,
                                       shares_per_page)
        if shares:
            if self._request_http():
                page_number = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of shares, not the summary
                    shares = \
                        get_shares_feed_for_person(base_dir, domain, port,
                                                   path + '?page=true',
                                                   http_prefix,
                                                   shares_file_type,
                                                   shares_per_page)
                else:
                    page_number_str = path.split('?page=')[1]
                    if '#' in page_number_str:
                        page_number_str = page_number_str.split('#')[0]
                    if page_number_str.isdigit():
                        page_number = int(page_number_str)
                    searchPath = path.split('?page=')[0]
                search_path2 = searchPath.replace('/' + shares_file_type, '')
                getPerson = person_lookup(domain, search_path2, base_dir)
                if getPerson:
                    if not self._establish_session("showSharesFeed"):
                        self._404()
                        self.server.GETbusy = False
                        return True

                    access_keys = self.server.access_keys
                    if '/users/' in path:
                        nickname = path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.keyShortcuts.get(nickname):
                            access_keys = \
                                self.server.keyShortcuts[nickname]

                    city = get_spoofed_city(self.server.city,
                                            base_dir, nickname, domain)
                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    msg = \
                        html_profile(self.server.signing_priv_key_pem,
                                     self.server.rss_icon_at_top,
                                     self.server.css_cache,
                                     self.server.icons_as_buttons,
                                     self.server.default_timeline,
                                     self.server.recent_posts_cache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     self.server.project_version,
                                     base_dir, http_prefix,
                                     authorized,
                                     getPerson, shares_file_type,
                                     self.server.session,
                                     self.server.cached_webfingers,
                                     self.server.person_cache,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.newswire,
                                     self.server.theme_name,
                                     self.server.dormant_months,
                                     self.server.peertube_instances,
                                     self.server.allow_local_network_access,
                                     self.server.text_mode_banner,
                                     self.server.debug,
                                     access_keys, city,
                                     self.server.system_language,
                                     self.server.max_like_count,
                                     shared_items_federated_domains,
                                     shares,
                                     page_number, shares_per_page,
                                     self.server.cw_lists,
                                     self.server.lists_enabled,
                                     self.server.content_license_url)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_shares_feed',
                                        self.server.debug)
                    self.server.GETbusy = False
                    return True
            else:
                if self._secure_mode():
                    msg = json.dumps(shares,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_shares_feed json',
                                        self.server.debug)
                else:
                    self._404()
                return True
        return False

    def _show_following_feed(self, authorized: bool,
                             calling_domain: str, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime,
                             proxy_type: str, cookie: str,
                             debug: str) -> bool:
        """Shows the following feed
        """
        following = \
            get_following_feed(base_dir, domain, port, path,
                               http_prefix, authorized, follows_per_page,
                               'following')
        if following:
            if self._request_http():
                page_number = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of following, not the summary
                    following = \
                        get_following_feed(base_dir,
                                           domain,
                                           port,
                                           path + '?page=true',
                                           http_prefix,
                                           authorized, follows_per_page)
                else:
                    page_number_str = path.split('?page=')[1]
                    if '#' in page_number_str:
                        page_number_str = page_number_str.split('#')[0]
                    if page_number_str.isdigit():
                        page_number = int(page_number_str)
                    searchPath = path.split('?page=')[0]
                getPerson = \
                    person_lookup(domain,
                                  searchPath.replace('/following', ''),
                                  base_dir)
                if getPerson:
                    if not self._establish_session("showFollowingFeed"):
                        self._404()
                        return True

                    access_keys = self.server.access_keys
                    city = None
                    if '/users/' in path:
                        nickname = path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.keyShortcuts.get(nickname):
                            access_keys = \
                                self.server.keyShortcuts[nickname]

                        city = get_spoofed_city(self.server.city,
                                                base_dir, nickname, domain)
                    content_license_url = \
                        self.server.content_license_url
                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    msg = \
                        html_profile(self.server.signing_priv_key_pem,
                                     self.server.rss_icon_at_top,
                                     self.server.css_cache,
                                     self.server.icons_as_buttons,
                                     self.server.default_timeline,
                                     self.server.recent_posts_cache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     self.server.project_version,
                                     base_dir, http_prefix,
                                     authorized,
                                     getPerson, 'following',
                                     self.server.session,
                                     self.server.cached_webfingers,
                                     self.server.person_cache,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.newswire,
                                     self.server.theme_name,
                                     self.server.dormant_months,
                                     self.server.peertube_instances,
                                     self.server.allow_local_network_access,
                                     self.server.text_mode_banner,
                                     self.server.debug,
                                     access_keys, city,
                                     self.server.system_language,
                                     self.server.max_like_count,
                                     shared_items_federated_domains,
                                     following,
                                     page_number,
                                     follows_per_page,
                                     self.server.cw_lists,
                                     self.server.lists_enabled,
                                     content_license_url).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html',
                                      msglen, cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_following_feed',
                                        self.server.debug)
                    return True
            else:
                if self._secure_mode():
                    msg = json.dumps(following,
                                     ensure_ascii=False).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_following_feed json',
                                        self.server.debug)
                else:
                    self._404()
                return True
        return False

    def _show_followers_feed(self, authorized: bool,
                             calling_domain: str, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime,
                             proxy_type: str, cookie: str,
                             debug: str) -> bool:
        """Shows the followers feed
        """
        followers = \
            get_following_feed(base_dir, domain, port, path, http_prefix,
                               authorized, follows_per_page, 'followers')
        if followers:
            if self._request_http():
                page_number = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of followers, not the summary
                    followers = \
                        get_following_feed(base_dir,
                                           domain,
                                           port,
                                           path + '?page=1',
                                           http_prefix,
                                           authorized, follows_per_page,
                                           'followers')
                else:
                    page_number_str = path.split('?page=')[1]
                    if '#' in page_number_str:
                        page_number_str = page_number_str.split('#')[0]
                    if page_number_str.isdigit():
                        page_number = int(page_number_str)
                    searchPath = path.split('?page=')[0]
                getPerson = \
                    person_lookup(domain,
                                  searchPath.replace('/followers', ''),
                                  base_dir)
                if getPerson:
                    if not self._establish_session("showFollowersFeed"):
                        self._404()
                        return True

                    access_keys = self.server.access_keys
                    city = None
                    if '/users/' in path:
                        nickname = path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.keyShortcuts.get(nickname):
                            access_keys = \
                                self.server.keyShortcuts[nickname]

                        city = get_spoofed_city(self.server.city,
                                                base_dir, nickname, domain)
                    content_license_url = \
                        self.server.content_license_url
                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    msg = \
                        html_profile(self.server.signing_priv_key_pem,
                                     self.server.rss_icon_at_top,
                                     self.server.css_cache,
                                     self.server.icons_as_buttons,
                                     self.server.default_timeline,
                                     self.server.recent_posts_cache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     self.server.project_version,
                                     base_dir,
                                     http_prefix,
                                     authorized,
                                     getPerson, 'followers',
                                     self.server.session,
                                     self.server.cached_webfingers,
                                     self.server.person_cache,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.newswire,
                                     self.server.theme_name,
                                     self.server.dormant_months,
                                     self.server.peertube_instances,
                                     self.server.allow_local_network_access,
                                     self.server.text_mode_banner,
                                     self.server.debug,
                                     access_keys, city,
                                     self.server.system_language,
                                     self.server.max_like_count,
                                     shared_items_federated_domains,
                                     followers,
                                     page_number,
                                     follows_per_page,
                                     self.server.cw_lists,
                                     self.server.lists_enabled,
                                     content_license_url).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_followers_feed',
                                        self.server.debug)
                    return True
            else:
                if self._secure_mode():
                    msg = json.dumps(followers,
                                     ensure_ascii=False).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET', '_show_followers_feed json',
                                        self.server.debug)
                else:
                    self._404()
            return True
        return False

    def _get_featured_collection(self, calling_domain: str,
                                 base_dir: str,
                                 path: str,
                                 http_prefix: str,
                                 nickname: str, domain: str,
                                 domain_full: str,
                                 system_language: str) -> None:
        """Returns the featured posts collections in
        actor/collections/featured
        """
        featuredCollection = \
            json_pin_post(base_dir, http_prefix,
                          nickname, domain, domain_full, system_language)
        msg = json.dumps(featuredCollection,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json', msglen,
                          None, calling_domain, False)
        self._write(msg)

    def _get_featured_tags_collection(self, calling_domain: str,
                                      path: str,
                                      http_prefix: str,
                                      domain_full: str):
        """Returns the featured tags collections in
        actor/collections/featuredTags
        TODO add ability to set a featured tags
        """
        postContext = get_individual_post_context()
        featuredTagsCollection = {
            '@context': postContext,
            'id': http_prefix + '://' + domain_full + path,
            'orderedItems': [],
            'totalItems': 0,
            'type': 'OrderedCollection'
        }
        msg = json.dumps(featuredTagsCollection,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json', msglen,
                          None, calling_domain, False)
        self._write(msg)

    def _show_person_profile(self, authorized: bool,
                             calling_domain: str, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime,
                             proxy_type: str, cookie: str,
                             debug: str) -> bool:
        """Shows the profile for a person
        """
        # look up a person
        actor_json = person_lookup(domain, path, base_dir)
        if not actor_json:
            return False
        if self._request_http():
            if not self._establish_session("showPersonProfile"):
                self._404()
                return True

            access_keys = self.server.access_keys
            city = None
            if '/users/' in path:
                nickname = path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                if self.server.keyShortcuts.get(nickname):
                    access_keys = \
                        self.server.keyShortcuts[nickname]

                city = get_spoofed_city(self.server.city,
                                        base_dir, nickname, domain)
            msg = \
                html_profile(self.server.signing_priv_key_pem,
                             self.server.rss_icon_at_top,
                             self.server.css_cache,
                             self.server.icons_as_buttons,
                             self.server.default_timeline,
                             self.server.recent_posts_cache,
                             self.server.max_recent_posts,
                             self.server.translate,
                             self.server.project_version,
                             base_dir,
                             http_prefix,
                             authorized,
                             actor_json, 'posts',
                             self.server.session,
                             self.server.cached_webfingers,
                             self.server.person_cache,
                             self.server.yt_replace_domain,
                             self.server.twitter_replacement_domain,
                             self.server.show_published_date_only,
                             self.server.newswire,
                             self.server.theme_name,
                             self.server.dormant_months,
                             self.server.peertube_instances,
                             self.server.allow_local_network_access,
                             self.server.text_mode_banner,
                             self.server.debug,
                             access_keys, city,
                             self.server.system_language,
                             self.server.max_like_count,
                             self.server.shared_items_federated_domains,
                             None, None, None,
                             self.server.cw_lists,
                             self.server.lists_enabled,
                             self.server.content_license_url).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime,
                                self.server.fitness,
                                '_GET', '_show_person_profile',
                                self.server.debug)
        else:
            if self._secure_mode():
                accept_str = self.headers['Accept']
                msgStr = json.dumps(actor_json, ensure_ascii=False)
                msg = msgStr.encode('utf-8')
                msglen = len(msg)
                if 'application/ld+json' in accept_str:
                    self._set_headers('application/ld+json', msglen,
                                      cookie, calling_domain, False)
                elif 'application/jrd+json' in accept_str:
                    self._set_headers('application/jrd+json', msglen,
                                      cookie, calling_domain, False)
                else:
                    self._set_headers('application/activity+json', msglen,
                                      cookie, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime,
                                    self.server.fitness,
                                    '_GET', '_show_person_profile json',
                                    self.server.debug)
            else:
                self._404()
        return True

    def _show_instance_actor(self, calling_domain: str, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime,
                             proxy_type: str, cookie: str,
                             debug: str,
                             enable_shared_inbox: bool) -> bool:
        """Shows the instance actor
        """
        if debug:
            print('Instance actor requested by ' + calling_domain)
        if self._request_http():
            self._404()
            return False
        actor_json = person_lookup(domain, path, base_dir)
        if not actor_json:
            print('ERROR: no instance actor found')
            self._404()
            return False
        accept_str = self.headers['Accept']
        if onion_domain and calling_domain.endswith('.onion'):
            actorDomainUrl = 'http://' + onion_domain
        elif i2p_domain and calling_domain.endswith('.i2p'):
            actorDomainUrl = 'http://' + i2p_domain
        else:
            actorDomainUrl = http_prefix + '://' + domain_full
        actorUrl = actorDomainUrl + '/users/Actor'
        removeFields = (
            'icon', 'image', 'tts', 'shares',
            'alsoKnownAs', 'hasOccupation', 'featured',
            'featuredTags', 'discoverable', 'published',
            'devices'
        )
        for r in removeFields:
            if r in actor_json:
                del actor_json[r]
        actor_json['endpoints'] = {}
        if enable_shared_inbox:
            actor_json['endpoints'] = {
                'sharedInbox': actorDomainUrl + '/inbox'
            }
        actor_json['name'] = 'ACTOR'
        actor_json['preferredUsername'] = domain_full
        actor_json['id'] = actorDomainUrl + '/actor'
        actor_json['type'] = 'Application'
        actor_json['summary'] = 'Instance Actor'
        actor_json['publicKey']['id'] = actorDomainUrl + '/actor#main-key'
        actor_json['publicKey']['owner'] = actorDomainUrl + '/actor'
        actor_json['url'] = actorDomainUrl + '/actor'
        actor_json['inbox'] = actorUrl + '/inbox'
        actor_json['followers'] = actorUrl + '/followers'
        actor_json['following'] = actorUrl + '/following'
        msgStr = json.dumps(actor_json, ensure_ascii=False)
        if onion_domain and calling_domain.endswith('.onion'):
            msgStr = msgStr.replace(http_prefix + '://' + domain_full,
                                    'http://' + onion_domain)
        elif i2p_domain and calling_domain.endswith('.i2p'):
            msgStr = msgStr.replace(http_prefix + '://' + domain_full,
                                    'http://' + i2p_domain)
        msg = msgStr.encode('utf-8')
        msglen = len(msg)
        if 'application/ld+json' in accept_str:
            self._set_headers('application/ld+json', msglen,
                              cookie, calling_domain, False)
        elif 'application/jrd+json' in accept_str:
            self._set_headers('application/jrd+json', msglen,
                              cookie, calling_domain, False)
        else:
            self._set_headers('application/activity+json', msglen,
                              cookie, calling_domain, False)
        self._write(msg)
        fitness_performance(GETstartTime,
                            self.server.fitness,
                            '_GET', '_show_instance_actor',
                            self.server.debug)
        return True

    def _show_blog_page(self, authorized: bool,
                        calling_domain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domain_full: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, cookie: str,
                        translate: {}, debug: str) -> bool:
        """Shows a blog page
        """
        page_number = 1
        nickname = path.split('/blog/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
                if page_number < 1:
                    page_number = 1
                elif page_number > 10:
                    page_number = 10
        if not self._establish_session("showBlogPage"):
            self._404()
            self.server.GETbusy = False
            return True
        msg = html_blog_page(authorized,
                             self.server.session,
                             base_dir,
                             http_prefix,
                             translate,
                             nickname,
                             domain, port,
                             max_posts_in_blogs_feed, page_number,
                             self.server.peertube_instances,
                             self.server.system_language,
                             self.server.person_cache,
                             self.server.debug)
        if msg is not None:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime,
                                self.server.fitness,
                                '_GET', '_show_blog_page',
                                self.server.debug)
            return True
        self._404()
        return True

    def _redirect_to_login_screen(self, calling_domain: str, path: str,
                                  http_prefix: str, domain_full: str,
                                  onion_domain: str, i2p_domain: str,
                                  GETstartTime,
                                  authorized: bool, debug: bool):
        """Redirects to the login screen if necessary
        """
        divertToLoginScreen = False
        if '/media/' not in path and \
           '/ontologies/' not in path and \
           '/data/' not in path and \
           '/sharefiles/' not in path and \
           '/statuses/' not in path and \
           '/emoji/' not in path and \
           '/tags/' not in path and \
           '/avatars/' not in path and \
           '/favicons/' not in path and \
           '/headers/' not in path and \
           '/fonts/' not in path and \
           '/icons/' not in path:
            divertToLoginScreen = True
            if path.startswith('/users/'):
                nickStr = path.split('/users/')[1]
                if '/' not in nickStr and '?' not in nickStr:
                    divertToLoginScreen = False
                else:
                    if path.endswith('/following') or \
                       path.endswith('/followers') or \
                       path.endswith('/skills') or \
                       path.endswith('/roles') or \
                       path.endswith('/wanted') or \
                       path.endswith('/shares'):
                        divertToLoginScreen = False

        if divertToLoginScreen and not authorized:
            divertPath = '/login'
            if self.server.news_instance:
                # for news instances if not logged in then show the
                # front page
                divertPath = '/users/news'
            # if debug:
            print('DEBUG: divertToLoginScreen=' +
                  str(divertToLoginScreen))
            print('DEBUG: authorized=' + str(authorized))
            print('DEBUG: path=' + path)
            if calling_domain.endswith('.onion') and onion_domain:
                self._redirect_headers('http://' +
                                       onion_domain + divertPath,
                                       None, calling_domain)
            elif calling_domain.endswith('.i2p') and i2p_domain:
                self._redirect_headers('http://' +
                                       i2p_domain + divertPath,
                                       None, calling_domain)
            else:
                self._redirect_headers(http_prefix + '://' +
                                       domain_full +
                                       divertPath, None, calling_domain)
            fitness_performance(GETstartTime,
                                self.server.fitness,
                                '_GET', '_redirect_to_login_screen',
                                self.server.debug)
            return True
        return False

    def _get_style_sheet(self, calling_domain: str, path: str,
                         GETstartTime) -> bool:
        """Returns the content of a css file
        """
        # get the last part of the path
        # eg. /my/path/file.css becomes file.css
        if '/' in path:
            path = path.split('/')[-1]
        if os.path.isfile(path):
            tries = 0
            while tries < 5:
                try:
                    css = get_css(self.server.base_dir, path,
                                  self.server.css_cache)
                    if css:
                        break
                except Exception as ex:
                    print('ERROR: _get_style_sheet ' +
                          str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            msg = css.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/css', msglen,
                              None, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime,
                                self.server.fitness,
                                '_GET', '_get_style_sheet',
                                self.server.debug)
            return True
        self._404()
        return True

    def _show_q_rcode(self, calling_domain: str, path: str,
                      base_dir: str, domain: str, port: int,
                      GETstartTime) -> bool:
        """Shows a QR code for an account
        """
        nickname = get_nickname_from_actor(path)
        save_person_qrcode(base_dir, nickname, domain, port)
        qrFilename = \
            acct_dir(base_dir, nickname, domain) + '/qrcode.png'
        if os.path.isfile(qrFilename):
            if self._etag_exists(qrFilename):
                # The file has not changed
                self._304()
                return

            tries = 0
            mediaBinary = None
            while tries < 5:
                try:
                    with open(qrFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        break
                except Exception as ex:
                    print('ERROR: _show_q_rcode ' + str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                mimeType = media_file_mime_type(qrFilename)
                self._set_headers_etag(qrFilename, mimeType,
                                       mediaBinary, None,
                                       self.server.domain_full,
                                       False, None)
                self._write(mediaBinary)
                fitness_performance(GETstartTime,
                                    self.server.fitness,
                                    '_GET', '_show_q_rcode',
                                    self.server.debug)
                return True
        self._404()
        return True

    def _search_screen_banner(self, calling_domain: str, path: str,
                              base_dir: str, domain: str, port: int,
                              GETstartTime) -> bool:
        """Shows a banner image on the search screen
        """
        nickname = get_nickname_from_actor(path)
        banner_filename = \
            acct_dir(base_dir, nickname, domain) + '/search_banner.png'
        if not os.path.isfile(banner_filename):
            if os.path.isfile(base_dir + '/theme/default/search_banner.png'):
                copyfile(base_dir + '/theme/default/search_banner.png',
                         banner_filename)
        if os.path.isfile(banner_filename):
            if self._etag_exists(banner_filename):
                # The file has not changed
                self._304()
                return True

            tries = 0
            mediaBinary = None
            while tries < 5:
                try:
                    with open(banner_filename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        break
                except Exception as ex:
                    print('ERROR: _search_screen_banner ' +
                          str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                mimeType = media_file_mime_type(banner_filename)
                self._set_headers_etag(banner_filename, mimeType,
                                       mediaBinary, None,
                                       self.server.domain_full,
                                       False, None)
                self._write(mediaBinary)
                fitness_performance(GETstartTime,
                                    self.server.fitness,
                                    '_GET', '_search_screen_banner',
                                    self.server.debug)
                return True
        self._404()
        return True

    def _column_image(self, side: str, calling_domain: str, path: str,
                      base_dir: str, domain: str, port: int,
                      GETstartTime) -> bool:
        """Shows an image at the top of the left/right column
        """
        nickname = get_nickname_from_actor(path)
        if not nickname:
            self._404()
            return True
        banner_filename = \
            acct_dir(base_dir, nickname, domain) + '/' + \
            side + '_col_image.png'
        if os.path.isfile(banner_filename):
            if self._etag_exists(banner_filename):
                # The file has not changed
                self._304()
                return True

            tries = 0
            mediaBinary = None
            while tries < 5:
                try:
                    with open(banner_filename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        break
                except Exception as ex:
                    print('ERROR: _column_image ' + str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                mimeType = media_file_mime_type(banner_filename)
                self._set_headers_etag(banner_filename, mimeType,
                                       mediaBinary, None,
                                       self.server.domain_full,
                                       False, None)
                self._write(mediaBinary)
                fitness_performance(GETstartTime,
                                    self.server.fitness,
                                    '_GET', '_column_image ' + side,
                                    self.server.debug)
                return True
        self._404()
        return True

    def _show_background_image(self, calling_domain: str, path: str,
                               base_dir: str, GETstartTime) -> bool:
        """Show a background image
        """
        imageExtensions = get_image_extensions()
        for ext in imageExtensions:
            for bg in ('follow', 'options', 'login', 'welcome'):
                # follow screen background image
                if path.endswith('/' + bg + '-background.' + ext):
                    bgFilename = \
                        base_dir + '/accounts/' + \
                        bg + '-background.' + ext
                    if os.path.isfile(bgFilename):
                        if self._etag_exists(bgFilename):
                            # The file has not changed
                            self._304()
                            return True

                        tries = 0
                        bgBinary = None
                        while tries < 5:
                            try:
                                with open(bgFilename, 'rb') as avFile:
                                    bgBinary = avFile.read()
                                    break
                            except Exception as ex:
                                print('ERROR: _show_background_image ' +
                                      str(tries) + ' ' + str(ex))
                                time.sleep(1)
                                tries += 1
                        if bgBinary:
                            if ext == 'jpg':
                                ext = 'jpeg'
                            self._set_headers_etag(bgFilename,
                                                   'image/' + ext,
                                                   bgBinary, None,
                                                   self.server.domain_full,
                                                   False, None)
                            self._write(bgBinary)
                            fitness_performance(GETstartTime,
                                                self.server.fitness,
                                                '_GET',
                                                '_show_background_image',
                                                self.server.debug)
                            return True
        self._404()
        return True

    def _show_default_profile_background(self, calling_domain: str, path: str,
                                         base_dir: str, theme_name: str,
                                         GETstartTime) -> bool:
        """If a background image is missing after searching for a handle
        then substitute this image
        """
        imageExtensions = get_image_extensions()
        for ext in imageExtensions:
            bgFilename = \
                base_dir + '/theme/' + theme_name + '/image.' + ext
            if os.path.isfile(bgFilename):
                if self._etag_exists(bgFilename):
                    # The file has not changed
                    self._304()
                    return True

                tries = 0
                bgBinary = None
                while tries < 5:
                    try:
                        with open(bgFilename, 'rb') as avFile:
                            bgBinary = avFile.read()
                            break
                    except Exception as ex:
                        print('ERROR: _show_default_profile_background ' +
                              str(tries) + ' ' + str(ex))
                        time.sleep(1)
                        tries += 1
                if bgBinary:
                    if ext == 'jpg':
                        ext = 'jpeg'
                    self._set_headers_etag(bgFilename,
                                           'image/' + ext,
                                           bgBinary, None,
                                           self.server.domain_full,
                                           False, None)
                    self._write(bgBinary)
                    fitness_performance(GETstartTime,
                                        self.server.fitness,
                                        '_GET',
                                        '_show_default_profile_background',
                                        self.server.debug)
                    return True
                break

        self._404()
        return True

    def _show_share_image(self, calling_domain: str, path: str,
                          base_dir: str, GETstartTime) -> bool:
        """Show a shared item image
        """
        if not is_image_file(path):
            self._404()
            return True

        mediaStr = path.split('/sharefiles/')[1]
        media_filename = base_dir + '/sharefiles/' + mediaStr
        if not os.path.isfile(media_filename):
            self._404()
            return True

        if self._etag_exists(media_filename):
            # The file has not changed
            self._304()
            return True

        mediaFileType = get_image_mime_type(media_filename)
        mediaBinary = None
        try:
            with open(media_filename, 'rb') as avFile:
                mediaBinary = avFile.read()
        except OSError:
            print('EX: unable to read binary ' + media_filename)
        if mediaBinary:
            self._set_headers_etag(media_filename,
                                   mediaFileType,
                                   mediaBinary, None,
                                   self.server.domain_full,
                                   False, None)
            self._write(mediaBinary)
        fitness_performance(GETstartTime,
                            self.server.fitness,
                            '_GET', '_show_share_image',
                            self.server.debug)
        return True

    def _show_avatar_or_banner(self, refererDomain: str, path: str,
                               base_dir: str, domain: str,
                               GETstartTime) -> bool:
        """Shows an avatar or banner or profile background image
        """
        if '/users/' not in path:
            if '/system/accounts/avatars/' not in path and \
               '/system/accounts/headers/' not in path and \
               '/accounts/avatars/' not in path and \
               '/accounts/headers/' not in path:
                return False
        if not is_image_file(path):
            return False
        if '/system/accounts/avatars/' in path:
            avatarStr = path.split('/system/accounts/avatars/')[1]
        elif '/accounts/avatars/' in path:
            avatarStr = path.split('/accounts/avatars/')[1]
        elif '/system/accounts/headers/' in path:
            avatarStr = path.split('/system/accounts/headers/')[1]
        elif '/accounts/headers/' in path:
            avatarStr = path.split('/accounts/headers/')[1]
        else:
            avatarStr = path.split('/users/')[1]
        if not ('/' in avatarStr and '.temp.' not in path):
            return False
        avatarNickname = avatarStr.split('/')[0]
        avatarFile = avatarStr.split('/')[1]
        avatarFileExt = avatarFile.split('.')[-1]
        # remove any numbers, eg. avatar123.png becomes avatar.png
        if avatarFile.startswith('avatar'):
            avatarFile = 'avatar.' + avatarFileExt
        elif avatarFile.startswith('banner'):
            avatarFile = 'banner.' + avatarFileExt
        elif avatarFile.startswith('search_banner'):
            avatarFile = 'search_banner.' + avatarFileExt
        elif avatarFile.startswith('image'):
            avatarFile = 'image.' + avatarFileExt
        elif avatarFile.startswith('left_col_image'):
            avatarFile = 'left_col_image.' + avatarFileExt
        elif avatarFile.startswith('right_col_image'):
            avatarFile = 'right_col_image.' + avatarFileExt
        avatarFilename = \
            acct_dir(base_dir, avatarNickname, domain) + '/' + avatarFile
        if not os.path.isfile(avatarFilename):
            originalExt = avatarFileExt
            originalAvatarFile = avatarFile
            altExt = get_image_extensions()
            altFound = False
            for alt in altExt:
                if alt == originalExt:
                    continue
                avatarFile = \
                    originalAvatarFile.replace('.' + originalExt,
                                               '.' + alt)
                avatarFilename = \
                    acct_dir(base_dir, avatarNickname, domain) + \
                    '/' + avatarFile
                if os.path.isfile(avatarFilename):
                    altFound = True
                    break
            if not altFound:
                return False
        if self._etag_exists(avatarFilename):
            # The file has not changed
            self._304()
            return True

        t = os.path.getmtime(avatarFilename)
        lastModifiedTime = datetime.datetime.fromtimestamp(t)
        lastModifiedTimeStr = \
            lastModifiedTime.strftime('%a, %d %b %Y %H:%M:%S GMT')

        mediaImageType = get_image_mime_type(avatarFile)
        mediaBinary = None
        try:
            with open(avatarFilename, 'rb') as avFile:
                mediaBinary = avFile.read()
        except OSError:
            print('EX: unable to read avatar ' + avatarFilename)
        if mediaBinary:
            self._set_headers_etag(avatarFilename, mediaImageType,
                                   mediaBinary, None,
                                   refererDomain, True,
                                   lastModifiedTimeStr)
            self._write(mediaBinary)
        fitness_performance(GETstartTime,
                            self.server.fitness,
                            '_GET', '_show_avatar_or_banner',
                            self.server.debug)
        return True

    def _confirm_delete_event(self, calling_domain: str, path: str,
                              base_dir: str, http_prefix: str, cookie: str,
                              translate: {}, domain_full: str,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime) -> bool:
        """Confirm whether to delete a calendar event
        """
        post_id = path.split('?eventid=')[1]
        if '?' in post_id:
            post_id = post_id.split('?')[0]
        postTime = path.split('?time=')[1]
        if '?' in postTime:
            postTime = postTime.split('?')[0]
        postYear = path.split('?year=')[1]
        if '?' in postYear:
            postYear = postYear.split('?')[0]
        postMonth = path.split('?month=')[1]
        if '?' in postMonth:
            postMonth = postMonth.split('?')[0]
        postDay = path.split('?day=')[1]
        if '?' in postDay:
            postDay = postDay.split('?')[0]
        # show the confirmation screen screen
        msg = html_calendar_delete_confirm(self.server.css_cache,
                                           translate,
                                           base_dir, path,
                                           http_prefix,
                                           domain_full,
                                           post_id, postTime,
                                           postYear, postMonth, postDay,
                                           calling_domain)
        if not msg:
            actor = \
                http_prefix + '://' + \
                domain_full + \
                path.split('/eventdelete')[0]
            if calling_domain.endswith('.onion') and onion_domain:
                actor = \
                    'http://' + onion_domain + \
                    path.split('/eventdelete')[0]
            elif calling_domain.endswith('.i2p') and i2p_domain:
                actor = \
                    'http://' + i2p_domain + \
                    path.split('/eventdelete')[0]
            self._redirect_headers(actor + '/calendar',
                                   cookie, calling_domain)
            fitness_performance(GETstartTime,
                                self.server.fitness,
                                '_GET', '_confirm_delete_event',
                                self.server.debug)
            return True
        msg = msg.encode('utf-8')
        msglen = len(msg)
        self._set_headers('text/html', msglen,
                          cookie, calling_domain, False)
        self._write(msg)
        return True

    def _show_new_post(self, calling_domain: str, path: str,
                       media_instance: bool, translate: {},
                       base_dir: str, http_prefix: str,
                       in_reply_to_url: str, reply_to_list: [],
                       share_description: str, reply_page_number: int,
                       reply_category: str,
                       domain: str, domain_full: str,
                       GETstartTime, cookie,
                       no_drop_down: bool, conversation_id: str) -> bool:
        """Shows the new post screen
        """
        isNewPostEndpoint = False
        if '/users/' in path and '/new' in path:
            # Various types of new post in the web interface
            newPostEndpoints = get_new_post_endpoints()
            for currPostType in newPostEndpoints:
                if path.endswith('/' + currPostType):
                    isNewPostEndpoint = True
                    break
        if isNewPostEndpoint:
            nickname = get_nickname_from_actor(path)

            if in_reply_to_url:
                replyIntervalHours = self.server.default_reply_interval_hrs
                if not can_reply_to(base_dir, nickname, domain,
                                    in_reply_to_url, replyIntervalHours):
                    print('Reply outside of time window ' + in_reply_to_url +
                          str(replyIntervalHours) + ' hours')
                    self._403()
                    return True
                elif self.server.debug:
                    print('Reply is within time interval: ' +
                          str(replyIntervalHours) + ' hours')

            access_keys = self.server.access_keys
            if self.server.keyShortcuts.get(nickname):
                access_keys = self.server.keyShortcuts[nickname]

            customSubmitText = get_config_param(base_dir, 'customSubmitText')

            post_json_object = None
            if in_reply_to_url:
                replyPostFilename = \
                    locate_post(base_dir, nickname, domain, in_reply_to_url)
                if replyPostFilename:
                    post_json_object = load_json(replyPostFilename)

            msg = html_new_post(self.server.css_cache,
                                media_instance,
                                translate,
                                base_dir,
                                http_prefix,
                                path, in_reply_to_url,
                                reply_to_list,
                                share_description, None,
                                reply_page_number,
                                reply_category,
                                nickname, domain,
                                domain_full,
                                self.server.default_timeline,
                                self.server.newswire,
                                self.server.theme_name,
                                no_drop_down, access_keys,
                                customSubmitText,
                                conversation_id,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.session,
                                self.server.cached_webfingers,
                                self.server.person_cache,
                                self.server.port,
                                post_json_object,
                                self.server.project_version,
                                self.server.yt_replace_domain,
                                self.server.twitter_replacement_domain,
                                self.server.show_published_date_only,
                                self.server.peertube_instances,
                                self.server.allow_local_network_access,
                                self.server.system_language,
                                self.server.max_like_count,
                                self.server.signing_priv_key_pem,
                                self.server.cw_lists,
                                self.server.lists_enabled,
                                self.server.default_timeline).encode('utf-8')
            if not msg:
                print('Error replying to ' + in_reply_to_url)
                self._404()
                return True
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime,
                                self.server.fitness,
                                '_GET', '_show_new_post',
                                self.server.debug)
            return True
        return False

    def _show_known_crawlers(self, calling_domain: str, path: str,
                             base_dir: str, known_crawlers: {}) -> bool:
        """Show a list of known web crawlers
        """
        if '/users/' not in path:
            return False
        if not path.endswith('/crawlers'):
            return False
        nickname = get_nickname_from_actor(path)
        if not nickname:
            return False
        if not is_moderator(base_dir, nickname):
            return False
        crawlersList = []
        curr_time = int(time.time())
        recentCrawlers = 60 * 60 * 24 * 30
        for ua_str, item in known_crawlers.items():
            if item['lastseen'] - curr_time < recentCrawlers:
                hitsStr = str(item['hits']).zfill(8)
                crawlersList.append(hitsStr + ' ' + ua_str)
        crawlersList.sort(reverse=True)
        msg = ''
        for lineStr in crawlersList:
            msg += lineStr + '\n'
        msg = msg.encode('utf-8')
        msglen = len(msg)
        self._set_headers('text/plain; charset=utf-8', msglen,
                          None, calling_domain, True)
        self._write(msg)
        return True

    def _edit_profile(self, calling_domain: str, path: str,
                      translate: {}, base_dir: str,
                      http_prefix: str, domain: str, port: int,
                      cookie: str) -> bool:
        """Show the edit profile screen
        """
        if '/users/' in path and path.endswith('/editprofile'):
            peertube_instances = self.server.peertube_instances
            nickname = get_nickname_from_actor(path)
            if nickname:
                city = get_spoofed_city(self.server.city,
                                        base_dir, nickname, domain)
            else:
                city = self.server.city

            access_keys = self.server.access_keys
            if '/users/' in path:
                if self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.keyShortcuts[nickname]

            default_reply_interval_hrs = self.server.default_reply_interval_hrs
            msg = html_edit_profile(self.server.css_cache,
                                    translate,
                                    base_dir,
                                    path, domain,
                                    port,
                                    http_prefix,
                                    self.server.default_timeline,
                                    self.server.theme_name,
                                    peertube_instances,
                                    self.server.text_mode_banner,
                                    city,
                                    self.server.user_agents_blocked,
                                    access_keys,
                                    default_reply_interval_hrs,
                                    self.server.cw_lists,
                                    self.server.lists_enabled).encode('utf-8')
            if msg:
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
            else:
                self._404()
            return True
        return False

    def _edit_links(self, calling_domain: str, path: str,
                    translate: {}, base_dir: str,
                    http_prefix: str, domain: str, port: int,
                    cookie: str, theme: str) -> bool:
        """Show the links from the left column
        """
        if '/users/' in path and path.endswith('/editlinks'):
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            access_keys = self.server.access_keys
            if self.server.keyShortcuts.get(nickname):
                access_keys = self.server.keyShortcuts[nickname]

            msg = html_edit_links(self.server.css_cache,
                                  translate,
                                  base_dir,
                                  path, domain,
                                  port,
                                  http_prefix,
                                  self.server.default_timeline,
                                  theme, access_keys).encode('utf-8')
            if msg:
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
            else:
                self._404()
            return True
        return False

    def _edit_newswire(self, calling_domain: str, path: str,
                       translate: {}, base_dir: str,
                       http_prefix: str, domain: str, port: int,
                       cookie: str) -> bool:
        """Show the newswire from the right column
        """
        if '/users/' in path and path.endswith('/editnewswire'):
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            access_keys = self.server.access_keys
            if self.server.keyShortcuts.get(nickname):
                access_keys = self.server.keyShortcuts[nickname]

            msg = html_edit_newswire(self.server.css_cache,
                                     translate,
                                     base_dir,
                                     path, domain,
                                     port,
                                     http_prefix,
                                     self.server.default_timeline,
                                     self.server.theme_name,
                                     access_keys).encode('utf-8')
            if msg:
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
            else:
                self._404()
            return True
        return False

    def _edit_news_post(self, calling_domain: str, path: str,
                        translate: {}, base_dir: str,
                        http_prefix: str, domain: str, port: int,
                        domain_full: str,
                        cookie: str) -> bool:
        """Show the edit screen for a news post
        """
        if '/users/' in path and '/editnewspost=' in path:
            postActor = 'news'
            if '?actor=' in path:
                postActor = path.split('?actor=')[1]
                if '?' in postActor:
                    postActor = postActor.split('?')[0]
            post_id = path.split('/editnewspost=')[1]
            if '?' in post_id:
                post_id = post_id.split('?')[0]
            postUrl = local_actor_url(http_prefix, postActor, domain_full) + \
                '/statuses/' + post_id
            path = path.split('/editnewspost=')[0]
            msg = html_edit_news_post(self.server.css_cache,
                                      translate, base_dir,
                                      path, domain, port,
                                      http_prefix,
                                      postUrl,
                                      self.server.system_language)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
            else:
                self._404()
            return True
        return False

    def _get_following_json(self, base_dir: str, path: str,
                            calling_domain: str,
                            http_prefix: str,
                            domain: str, port: int,
                            followingItemsPerPage: int,
                            debug: bool, listName='following') -> None:
        """Returns json collection for following.txt
        """
        followingJson = \
            get_following_feed(base_dir, domain, port, path, http_prefix,
                               True, followingItemsPerPage, listName)
        if not followingJson:
            if debug:
                print(listName + ' json feed not found for ' + path)
            self._404()
            return
        msg = json.dumps(followingJson,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json',
                          msglen, None, calling_domain, False)
        self._write(msg)

    def _send_block(self, http_prefix: str,
                    blockerNickname: str, blockerDomainFull: str,
                    blockingNickname: str, blockingDomainFull: str) -> bool:
        if blockerDomainFull == blockingDomainFull:
            if blockerNickname == blockingNickname:
                # don't block self
                return False
        blockActor = \
            local_actor_url(http_prefix, blockerNickname, blockerDomainFull)
        toUrl = 'https://www.w3.org/ns/activitystreams#Public'
        ccUrl = blockActor + '/followers'

        blockedUrl = \
            http_prefix + '://' + blockingDomainFull + \
            '/@' + blockingNickname
        blockJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Block',
            'actor': blockActor,
            'object': blockedUrl,
            'to': [toUrl],
            'cc': [ccUrl]
        }
        self._post_to_outbox(blockJson, self.server.project_version,
                             blockerNickname)
        return True

    def _get_referer_domain(self, ua_str: str) -> str:
        """Returns the referer domain
        Which domain is the GET request coming from?
        """
        refererDomain = None
        if self.headers.get('referer'):
            refererDomain, refererPort = \
                get_domain_from_actor(self.headers['referer'])
            refererDomain = get_full_domain(refererDomain, refererPort)
        elif self.headers.get('Referer'):
            refererDomain, refererPort = \
                get_domain_from_actor(self.headers['Referer'])
            refererDomain = get_full_domain(refererDomain, refererPort)
        elif self.headers.get('Signature'):
            if 'keyId="' in self.headers['Signature']:
                refererDomain = self.headers['Signature'].split('keyId="')[1]
                if '/' in refererDomain:
                    refererDomain = refererDomain.split('/')[0]
                elif '#' in refererDomain:
                    refererDomain = refererDomain.split('#')[0]
                elif '"' in refererDomain:
                    refererDomain = refererDomain.split('"')[0]
        elif ua_str:
            if '+https://' in ua_str:
                refererDomain = ua_str.split('+https://')[1]
                if '/' in refererDomain:
                    refererDomain = refererDomain.split('/')[0]
                elif ')' in refererDomain:
                    refererDomain = refererDomain.split(')')[0]
            elif '+http://' in ua_str:
                refererDomain = ua_str.split('+http://')[1]
                if '/' in refererDomain:
                    refererDomain = refererDomain.split('/')[0]
                elif ')' in refererDomain:
                    refererDomain = refererDomain.split(')')[0]
        return refererDomain

    def _get_user_agent(self) -> str:
        """Returns the user agent string from the headers
        """
        ua_str = None
        if self.headers.get('User-Agent'):
            ua_str = self.headers['User-Agent']
        elif self.headers.get('user-agent'):
            ua_str = self.headers['user-agent']
        elif self.headers.get('User-agent'):
            ua_str = self.headers['User-agent']
        return ua_str

    def _permitted_crawler_path(self, path: str) -> bool:
        """Is the given path permitted to be crawled by a search engine?
        this should only allow through basic information, such as nodeinfo
        """
        if path == '/' or path == '/about' or path == '/login' or \
           path.startswith('/blog/'):
            return True
        return False

    def do_GET(self):
        calling_domain = self.server.domain_full

        if self.headers.get('Host'):
            calling_domain = decoded_host(self.headers['Host'])
            if self.server.onion_domain:
                if calling_domain != self.server.domain and \
                   calling_domain != self.server.domain_full and \
                   calling_domain != self.server.onion_domain:
                    print('GET domain blocked: ' + calling_domain)
                    self._400()
                    return
            elif self.server.i2p_domain:
                if calling_domain != self.server.domain and \
                   calling_domain != self.server.domain_full and \
                   calling_domain != self.server.i2p_domain:
                    print('GET domain blocked: ' + calling_domain)
                    self._400()
                    return
            else:
                if calling_domain != self.server.domain and \
                   calling_domain != self.server.domain_full:
                    print('GET domain blocked: ' + calling_domain)
                    self._400()
                    return

        ua_str = self._get_user_agent()

        if not self._permitted_crawler_path(self.path):
            if self._blocked_user_agent(calling_domain, ua_str):
                self._400()
                return

        refererDomain = self._get_referer_domain(ua_str)

        GETstartTime = time.time()

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'start', self.server.debug)

        # Since fediverse crawlers are quite active,
        # make returning info to them high priority
        # get nodeinfo endpoint
        if self._nodeinfo(ua_str, calling_domain):
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_nodeinfo[calling_domain]',
                            self.server.debug)

        if self.path == '/logout':
            if not self.server.news_instance:
                msg = \
                    html_login(self.server.css_cache,
                               self.server.translate,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain_full,
                               self.server.system_language,
                               False).encode('utf-8')
                msglen = len(msg)
                self._logout_headers('text/html', msglen, calling_domain)
                self._write(msg)
            else:
                if calling_domain.endswith('.onion') and \
                   self.server.onion_domain:
                    self._logout_redirect('http://' +
                                          self.server.onion_domain +
                                          '/users/news', None,
                                          calling_domain)
                elif (calling_domain.endswith('.i2p') and
                      self.server.i2p_domain):
                    self._logout_redirect('http://' +
                                          self.server.i2p_domain +
                                          '/users/news', None,
                                          calling_domain)
                else:
                    self._logout_redirect(self.server.http_prefix +
                                          '://' +
                                          self.server.domain_full +
                                          '/users/news',
                                          None, calling_domain)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'logout',
                                self.server.debug)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show logout',
                            self.server.debug)

        # replace https://domain/@nick with https://domain/users/nick
        if self.path.startswith('/@'):
            self.path = self.path.replace('/@', '/users/')
            # replace https://domain/@nick/statusnumber
            # with https://domain/users/nick/statuses/statusnumber
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                statusNumberStr = nickname.split('/')[1]
                if statusNumberStr.isdigit():
                    nickname = nickname.split('/')[0]
                    self.path = \
                        self.path.replace('/users/' + nickname + '/',
                                          '/users/' + nickname + '/statuses/')

        # instance actor
        if self.path == '/actor' or \
           self.path == '/users/actor' or \
           self.path == '/Actor' or \
           self.path == '/users/Actor':
            self.path = '/users/inbox'
            if self._show_instance_actor(calling_domain, self.path,
                                         self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         self.server.domain_full,
                                         self.server.port,
                                         self.server.onion_domain,
                                         self.server.i2p_domain,
                                         GETstartTime,
                                         self.server.proxy_type,
                                         None, self.server.debug,
                                         self.server.enable_shared_inbox):
                return
            else:
                self._404()
                return

        # turn off dropdowns on new post screen
        no_drop_down = False
        if self.path.endswith('?nodropdown'):
            no_drop_down = True
            self.path = self.path.replace('?nodropdown', '')

        # redirect music to #nowplaying list
        if self.path == '/music' or self.path == '/nowplaying':
            self.path = '/tags/nowplaying'

        if self.server.debug:
            print('DEBUG: GET from ' + self.server.base_dir +
                  ' path: ' + self.path + ' busy: ' +
                  str(self.server.GETbusy))

        if self.server.debug:
            print(str(self.headers))

        cookie = None
        if self.headers.get('Cookie'):
            cookie = self.headers['Cookie']

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'get cookie',
                            self.server.debug)

        if '/manifest.json' in self.path:
            if self._has_accept(calling_domain):
                if not self._request_http():
                    self._progressive_web_app_manifest(calling_domain,
                                                       GETstartTime)
                    return
                else:
                    self.path = '/'

        if '/browserconfig.xml' in self.path:
            if self._has_accept(calling_domain):
                self._browser_config(calling_domain, GETstartTime)
                return

        # default newswire favicon, for links to sites which
        # have no favicon
        if not self.path.startswith('/favicons/'):
            if 'newswire_favicon.ico' in self.path:
                self._get_favicon(calling_domain, self.server.base_dir,
                                  self.server.debug,
                                  'newswire_favicon.ico')
                return

            # favicon image
            if 'favicon.ico' in self.path:
                self._get_favicon(calling_domain, self.server.base_dir,
                                  self.server.debug,
                                  'favicon.ico')
                return

        # check authorization
        authorized = self._is_authorized()
        if self.server.debug:
            if authorized:
                print('GET Authorization granted')
            else:
                print('GET Not authorized')

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'isAuthorized',
                            self.server.debug)

        # shared items catalog for this instance
        # this is only accessible to instance members or to
        # other instances which present an authorization token
        if self.path.startswith('/catalog') or \
           (self.path.startswith('/users/') and '/catalog' in self.path):
            catalogAuthorized = authorized
            if not catalogAuthorized:
                if self.server.debug:
                    print('Catalog access is not authorized. ' +
                          'Checking Authorization header')
                # Check the authorization token
                if self.headers.get('Origin') and \
                   self.headers.get('Authorization'):
                    permittedDomains = \
                        self.server.shared_items_federated_domains
                    sharedItemTokens = self.server.sharedItemFederationTokens
                    if authorize_shared_items(permittedDomains,
                                              self.server.base_dir,
                                              self.headers['Origin'],
                                              calling_domain,
                                              self.headers['Authorization'],
                                              self.server.debug,
                                              sharedItemTokens):
                        catalogAuthorized = True
                    elif self.server.debug:
                        print('Authorization token refused for ' +
                              'shared items federation')
                elif self.server.debug:
                    print('No Authorization header is available for ' +
                          'shared items federation')
            # show shared items catalog for federation
            if self._has_accept(calling_domain) and catalogAuthorized:
                catalogType = 'json'
                if self.path.endswith('.csv') or self._request_csv():
                    catalogType = 'csv'
                elif self.path.endswith('.json') or not self._request_http():
                    catalogType = 'json'
                if self.server.debug:
                    print('Preparing DFC catalog in format ' + catalogType)

                if catalogType == 'json':
                    # catalog as a json
                    if not self.path.startswith('/users/'):
                        if self.server.debug:
                            print('Catalog for the instance')
                        catalogJson = \
                            shares_catalog_endpoint(self.server.base_dir,
                                                    self.server.http_prefix,
                                                    self.server.domain_full,
                                                    self.path, 'shares')
                    else:
                        domain_full = self.server.domain_full
                        http_prefix = self.server.http_prefix
                        nickname = self.path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.debug:
                            print('Catalog for account: ' + nickname)
                        base_dir = self.server.base_dir
                        catalogJson = \
                            shares_catalog_account_endpoint(base_dir,
                                                            http_prefix,
                                                            nickname,
                                                            self.server.domain,
                                                            domain_full,
                                                            self.path,
                                                            self.server.debug,
                                                            'shares')
                    msg = json.dumps(catalogJson,
                                     ensure_ascii=False).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen, None, calling_domain, False)
                    self._write(msg)
                    return
                elif catalogType == 'csv':
                    # catalog as a CSV file for import into a spreadsheet
                    msg = \
                        shares_catalog_csv_endpoint(self.server.base_dir,
                                                    self.server.http_prefix,
                                                    self.server.domain_full,
                                                    self.path,
                                                    'shares').encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/csv',
                                      msglen, None, calling_domain, False)
                    self._write(msg)
                    return
                self._404()
                return
            self._400()
            return

        # wanted items catalog for this instance
        # this is only accessible to instance members or to
        # other instances which present an authorization token
        if self.path.startswith('/wantedItems') or \
           (self.path.startswith('/users/') and '/wantedItems' in self.path):
            catalogAuthorized = authorized
            if not catalogAuthorized:
                if self.server.debug:
                    print('Wanted catalog access is not authorized. ' +
                          'Checking Authorization header')
                # Check the authorization token
                if self.headers.get('Origin') and \
                   self.headers.get('Authorization'):
                    permittedDomains = \
                        self.server.shared_items_federated_domains
                    sharedItemTokens = self.server.sharedItemFederationTokens
                    if authorize_shared_items(permittedDomains,
                                              self.server.base_dir,
                                              self.headers['Origin'],
                                              calling_domain,
                                              self.headers['Authorization'],
                                              self.server.debug,
                                              sharedItemTokens):
                        catalogAuthorized = True
                    elif self.server.debug:
                        print('Authorization token refused for ' +
                              'wanted items federation')
                elif self.server.debug:
                    print('No Authorization header is available for ' +
                          'wanted items federation')
            # show wanted items catalog for federation
            if self._has_accept(calling_domain) and catalogAuthorized:
                catalogType = 'json'
                if self.path.endswith('.csv') or self._request_csv():
                    catalogType = 'csv'
                elif self.path.endswith('.json') or not self._request_http():
                    catalogType = 'json'
                if self.server.debug:
                    print('Preparing DFC wanted catalog in format ' +
                          catalogType)

                if catalogType == 'json':
                    # catalog as a json
                    if not self.path.startswith('/users/'):
                        if self.server.debug:
                            print('Wanted catalog for the instance')
                        catalogJson = \
                            shares_catalog_endpoint(self.server.base_dir,
                                                    self.server.http_prefix,
                                                    self.server.domain_full,
                                                    self.path, 'wanted')
                    else:
                        domain_full = self.server.domain_full
                        http_prefix = self.server.http_prefix
                        nickname = self.path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.debug:
                            print('Wanted catalog for account: ' + nickname)
                        base_dir = self.server.base_dir
                        catalogJson = \
                            shares_catalog_account_endpoint(base_dir,
                                                            http_prefix,
                                                            nickname,
                                                            self.server.domain,
                                                            domain_full,
                                                            self.path,
                                                            self.server.debug,
                                                            'wanted')
                    msg = json.dumps(catalogJson,
                                     ensure_ascii=False).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen, None, calling_domain, False)
                    self._write(msg)
                    return
                elif catalogType == 'csv':
                    # catalog as a CSV file for import into a spreadsheet
                    msg = \
                        shares_catalog_csv_endpoint(self.server.base_dir,
                                                    self.server.http_prefix,
                                                    self.server.domain_full,
                                                    self.path,
                                                    'wanted').encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/csv',
                                      msglen, None, calling_domain, False)
                    self._write(msg)
                    return
                self._404()
                return
            self._400()
            return

        # minimal mastodon api
        if self._masto_api(self.path, calling_domain, ua_str,
                           authorized,
                           self.server.http_prefix,
                           self.server.base_dir,
                           self.authorizedNickname,
                           self.server.domain,
                           self.server.domain_full,
                           self.server.onion_domain,
                           self.server.i2p_domain,
                           self.server.translate,
                           self.server.registration,
                           self.server.system_language,
                           self.server.project_version,
                           self.server.customEmoji,
                           self.server.show_node_info_accounts):
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_masto_api[calling_domain]',
                            self.server.debug)

        if not self._establish_session("GET"):
            self._404()
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'session fail',
                                self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'create session',
                            self.server.debug)

        # is this a html request?
        htmlGET = False
        if self._has_accept(calling_domain):
            if self._request_http():
                htmlGET = True
        else:
            if self.headers.get('Connection'):
                # https://developer.mozilla.org/en-US/
                # docs/Web/HTTP/Protocol_upgrade_mechanism
                if self.headers.get('Upgrade'):
                    print('HTTP Connection request: ' +
                          self.headers['Upgrade'])
                else:
                    print('HTTP Connection request: ' +
                          self.headers['Connection'])
                self._200()
            else:
                print('WARN: No Accept header ' + str(self.headers))
                self._400()
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'hasAccept',
                            self.server.debug)

        # cached favicon images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/favicons/'):
            if self.server.domain_full in self.path:
                # favicon for this instance
                self._get_favicon(calling_domain, self.server.base_dir,
                                  self.server.debug,
                                  'favicon.ico')
                return
            self._show_cached_favicon(refererDomain, self.path,
                                      self.server.base_dir,
                                      GETstartTime)
            return

        # get css
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.endswith('.css'):
            if self._get_style_sheet(calling_domain, self.path,
                                     GETstartTime):
                return

        if authorized and '/exports/' in self.path:
            self._get_exported_theme(calling_domain, self.path,
                                     self.server.base_dir,
                                     self.server.domain_full,
                                     self.server.debug)
            return

        # get fonts
        if '/fonts/' in self.path:
            self._get_fonts(calling_domain, self.path,
                            self.server.base_dir, self.server.debug,
                            GETstartTime)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'fonts',
                            self.server.debug)

        if self.path == '/sharedInbox' or \
           self.path == '/users/inbox' or \
           self.path == '/actor/inbox' or \
           self.path == '/users/' + self.server.domain:
            # if shared inbox is not enabled
            if not self.server.enable_shared_inbox:
                self._503()
                return

            self.path = '/inbox'

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'sharedInbox enabled',
                            self.server.debug)

        if self.path == '/categories.xml':
            self._get_hashtag_categories_feed(authorized,
                                              calling_domain, self.path,
                                              self.server.base_dir,
                                              self.server.http_prefix,
                                              self.server.domain,
                                              self.server.port,
                                              self.server.proxy_type,
                                              GETstartTime,
                                              self.server.debug)
            return

        if self.path == '/newswire.xml':
            self._get_newswire_feed(authorized,
                                    calling_domain, self.path,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.port,
                                    self.server.proxy_type,
                                    GETstartTime,
                                    self.server.debug)
            return

        # RSS 2.0
        if self.path.startswith('/blog/') and \
           self.path.endswith('/rss.xml'):
            if not self.path == '/blog/rss.xml':
                self._get_rss2feed(authorized,
                                   calling_domain, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.port,
                                   self.server.proxy_type,
                                   GETstartTime,
                                   self.server.debug)
            else:
                self._get_rss2site(authorized,
                                   calling_domain, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain_full,
                                   self.server.port,
                                   self.server.proxy_type,
                                   self.server.translate,
                                   GETstartTime,
                                   self.server.debug)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'rss2 done',
                            self.server.debug)

        # RSS 3.0
        if self.path.startswith('/blog/') and \
           self.path.endswith('/rss.txt'):
            self._get_rss3feed(authorized,
                               calling_domain, self.path,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.port,
                               self.server.proxy_type,
                               GETstartTime,
                               self.server.debug,
                               self.server.system_language)
            return

        usersInPath = False
        if '/users/' in self.path:
            usersInPath = True

        if authorized and not htmlGET and usersInPath:
            if '/following?page=' in self.path:
                self._get_following_json(self.server.base_dir,
                                         self.path,
                                         calling_domain,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         self.server.port,
                                         self.server.followingItemsPerPage,
                                         self.server.debug, 'following')
                return
            elif '/followers?page=' in self.path:
                self._get_following_json(self.server.base_dir,
                                         self.path,
                                         calling_domain,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         self.server.port,
                                         self.server.followingItemsPerPage,
                                         self.server.debug, 'followers')
                return
            elif '/followrequests?page=' in self.path:
                self._get_following_json(self.server.base_dir,
                                         self.path,
                                         calling_domain,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         self.server.port,
                                         self.server.followingItemsPerPage,
                                         self.server.debug,
                                         'followrequests')
                return

        # authorized endpoint used for TTS of posts
        # arriving in your inbox
        if authorized and usersInPath and \
           self.path.endswith('/speaker'):
            if 'application/ssml' not in self.headers['Accept']:
                # json endpoint
                self._get_speaker(calling_domain, self.path,
                                  self.server.base_dir,
                                  self.server.domain,
                                  self.server.debug)
            else:
                xmlStr = \
                    get_ssm_lbox(self.server.base_dir,
                                 self.path, self.server.domain,
                                 self.server.system_language,
                                 self.server.instanceTitle,
                                 'inbox')
                if xmlStr:
                    msg = xmlStr.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/xrd+xml', msglen,
                                      None, calling_domain, False)
                    self._write(msg)
            return

        # redirect to the welcome screen
        if htmlGET and authorized and usersInPath and \
           '/welcome' not in self.path:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if '?' in nickname:
                nickname = nickname.split('?')[0]
            if nickname == self.authorizedNickname and \
               self.path != '/users/' + nickname:
                if not is_welcome_screen_complete(self.server.base_dir,
                                                  nickname,
                                                  self.server.domain):
                    self._redirect_headers('/users/' + nickname + '/welcome',
                                           cookie, calling_domain)
                    return

        if not htmlGET and \
           usersInPath and self.path.endswith('/pinned'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            pinnedPostJson = \
                get_pinned_post_as_json(self.server.base_dir,
                                        self.server.http_prefix,
                                        nickname, self.server.domain,
                                        self.server.domain_full,
                                        self.server.system_language)
            message_json = {}
            if pinnedPostJson:
                post_id = remove_id_ending(pinnedPostJson['id'])
                message_json = \
                    outbox_message_create_wrap(self.server.http_prefix,
                                               nickname,
                                               self.server.domain,
                                               self.server.port,
                                               pinnedPostJson)
                message_json['id'] = post_id + '/activity'
                message_json['object']['id'] = post_id
                message_json['object']['url'] = replace_users_with_at(post_id)
                message_json['object']['atomUri'] = post_id
            msg = json.dumps(message_json,
                             ensure_ascii=False).encode('utf-8')
            msglen = len(msg)
            self._set_headers('application/json',
                              msglen, None, calling_domain, False)
            self._write(msg)
            return

        if not htmlGET and \
           usersInPath and self.path.endswith('/collections/featured'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            # return the featured posts collection
            self._get_featured_collection(calling_domain,
                                          self.server.base_dir,
                                          self.path,
                                          self.server.http_prefix,
                                          nickname, self.server.domain,
                                          self.server.domain_full,
                                          self.server.system_language)
            return

        if not htmlGET and \
           usersInPath and self.path.endswith('/collections/featuredTags'):
            self._get_featured_tags_collection(calling_domain,
                                               self.path,
                                               self.server.http_prefix,
                                               self.server.domain_full)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', '_get_featured_tags_collection done',
                            self.server.debug)

        # show a performance graph
        if authorized and '/performance?graph=' in self.path:
            graph = self.path.split('?graph=')[1]
            if htmlGET and not graph.endswith('.json'):
                if graph == 'post':
                    graph = '_POST'
                elif graph == 'get':
                    graph = '_GET'
                msg = \
                    html_watch_points_graph(self.server.base_dir,
                                            self.server.fitness,
                                            graph, 16).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'graph',
                                    self.server.debug)
                return
            else:
                graph = graph.replace('.json', '')
                if graph == 'post':
                    graph = '_POST'
                elif graph == 'get':
                    graph = '_GET'
                watchPointsJson = \
                    sorted_watch_points(self.server.fitness, graph)
                msg = json.dumps(watchPointsJson,
                                 ensure_ascii=False).encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/json', msglen,
                                  None, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'graph json',
                                    self.server.debug)
                return

        # show the main blog page
        if htmlGET and (self.path == '/blog' or
                        self.path == '/blog/' or
                        self.path == '/blogs' or
                        self.path == '/blogs/'):
            if '/rss.xml' not in self.path:
                if not self._establish_session("show the main blog page"):
                    self._404()
                    return
                msg = html_blog_view(authorized,
                                     self.server.session,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.translate,
                                     self.server.domain,
                                     self.server.port,
                                     max_posts_in_blogs_feed,
                                     self.server.peertube_instances,
                                     self.server.system_language,
                                     self.server.person_cache,
                                     self.server.debug)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, calling_domain, False)
                    self._write(msg)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', 'blog view',
                                        self.server.debug)
                    return
                self._404()
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'blog view done',
                            self.server.debug)

        # show a particular page of blog entries
        # for a particular account
        if htmlGET and self.path.startswith('/blog/'):
            if '/rss.xml' not in self.path:
                if self._show_blog_page(authorized,
                                        calling_domain, self.path,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domain_full,
                                        self.server.port,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        GETstartTime,
                                        self.server.proxy_type,
                                        cookie, self.server.translate,
                                        self.server.debug):
                    return

        # list of registered devices for e2ee
        # see https://github.com/tootsuite/mastodon/pull/13820
        if authorized and usersInPath:
            if self.path.endswith('/collections/devices'):
                nickname = self.path.split('/users/')
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                devJson = e2e_edevices_collection(self.server.base_dir,
                                                  nickname,
                                                  self.server.domain,
                                                  self.server.domain_full,
                                                  self.server.http_prefix)
                msg = json.dumps(devJson,
                                 ensure_ascii=False).encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/json',
                                  msglen,
                                  None, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'registered devices',
                                    self.server.debug)
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'registered devices done',
                            self.server.debug)

        if htmlGET and usersInPath:
            # show the person options screen with view/follow/block/report
            if '?options=' in self.path:
                self._show_person_options(calling_domain, self.path,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domain_full,
                                          GETstartTime,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          cookie, self.server.debug,
                                          authorized)
                return

            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'person options done',
                                self.server.debug)
            # show blog post
            blogFilename, nickname = \
                path_contains_blog_link(self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domain_full,
                                        self.path)
            if blogFilename and nickname:
                post_json_object = load_json(blogFilename)
                if is_blog_post(post_json_object):
                    msg = html_blog_post(self.server.session,
                                         authorized,
                                         self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.translate,
                                         nickname, self.server.domain,
                                         self.server.domain_full,
                                         post_json_object,
                                         self.server.peertube_instances,
                                         self.server.system_language,
                                         self.server.person_cache,
                                         self.server.debug,
                                         self.server.content_license_url)
                    if msg is not None:
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, calling_domain, False)
                        self._write(msg)
                        fitness_performance(GETstartTime, self.server.fitness,
                                            '_GET', 'blog post 2',
                                            self.server.debug)
                        return
                    self._404()
                    return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'blog post 2 done',
                            self.server.debug)

        # after selecting a shared item from the left column then show it
        if htmlGET and '?showshare=' in self.path and '/users/' in self.path:
            item_id = self.path.split('?showshare=')[1]
            if '?' in item_id:
                item_id = item_id.split('?')[0]
            category = ''
            if '?category=' in self.path:
                category = self.path.split('?category=')[1]
            if '?' in category:
                category = category.split('?')[0]
            usersPath = self.path.split('?showshare=')[0]
            nickname = usersPath.replace('/users/', '')
            item_id = urllib.parse.unquote_plus(item_id.strip())
            msg = \
                html_show_share(self.server.base_dir,
                                self.server.domain, nickname,
                                self.server.http_prefix,
                                self.server.domain_full,
                                item_id, self.server.translate,
                                self.server.shared_items_federated_domains,
                                self.server.default_timeline,
                                self.server.theme_name, 'shares', category)
            if not msg:
                if calling_domain.endswith('.onion') and \
                   self.server.onion_domain:
                    actor = 'http://' + self.server.onion_domain + usersPath
                elif (calling_domain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actor = 'http://' + self.server.i2p_domain + usersPath
                self._redirect_headers(actor + '/tlshares',
                                       cookie, calling_domain)
                return
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'html_show_share',
                                self.server.debug)
            return

        # after selecting a wanted item from the left column then show it
        if htmlGET and '?showwanted=' in self.path and '/users/' in self.path:
            item_id = self.path.split('?showwanted=')[1]
            if ';' in item_id:
                item_id = item_id.split(';')[0]
            category = self.path.split('?category=')[1]
            if ';' in category:
                category = category.split(';')[0]
            usersPath = self.path.split('?showwanted=')[0]
            nickname = usersPath.replace('/users/', '')
            item_id = urllib.parse.unquote_plus(item_id.strip())
            msg = \
                html_show_share(self.server.base_dir,
                                self.server.domain, nickname,
                                self.server.http_prefix,
                                self.server.domain_full,
                                item_id, self.server.translate,
                                self.server.shared_items_federated_domains,
                                self.server.default_timeline,
                                self.server.theme_name, 'wanted', category)
            if not msg:
                if calling_domain.endswith('.onion') and \
                   self.server.onion_domain:
                    actor = 'http://' + self.server.onion_domain + usersPath
                elif (calling_domain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actor = 'http://' + self.server.i2p_domain + usersPath
                self._redirect_headers(actor + '/tlwanted',
                                       cookie, calling_domain)
                return
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'htmlShowWanted',
                                self.server.debug)
            return

        # remove a shared item
        if htmlGET and '?rmshare=' in self.path:
            item_id = self.path.split('?rmshare=')[1]
            item_id = urllib.parse.unquote_plus(item_id.strip())
            usersPath = self.path.split('?rmshare=')[0]
            actor = \
                self.server.http_prefix + '://' + \
                self.server.domain_full + usersPath
            msg = html_confirm_remove_shared_item(self.server.css_cache,
                                                  self.server.translate,
                                                  self.server.base_dir,
                                                  actor, item_id,
                                                  calling_domain, 'shares')
            if not msg:
                if calling_domain.endswith('.onion') and \
                   self.server.onion_domain:
                    actor = 'http://' + self.server.onion_domain + usersPath
                elif (calling_domain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actor = 'http://' + self.server.i2p_domain + usersPath
                self._redirect_headers(actor + '/tlshares',
                                       cookie, calling_domain)
                return
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'remove shared item',
                                self.server.debug)
            return

        # remove a wanted item
        if htmlGET and '?rmwanted=' in self.path:
            item_id = self.path.split('?rmwanted=')[1]
            item_id = urllib.parse.unquote_plus(item_id.strip())
            usersPath = self.path.split('?rmwanted=')[0]
            actor = \
                self.server.http_prefix + '://' + \
                self.server.domain_full + usersPath
            msg = html_confirm_remove_shared_item(self.server.css_cache,
                                                  self.server.translate,
                                                  self.server.base_dir,
                                                  actor, item_id,
                                                  calling_domain, 'wanted')
            if not msg:
                if calling_domain.endswith('.onion') and \
                   self.server.onion_domain:
                    actor = 'http://' + self.server.onion_domain + usersPath
                elif (calling_domain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actor = 'http://' + self.server.i2p_domain + usersPath
                self._redirect_headers(actor + '/tlwanted',
                                       cookie, calling_domain)
                return
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, calling_domain, False)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'remove shared item',
                                self.server.debug)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'remove shared item done',
                            self.server.debug)

        if self.path.startswith('/terms'):
            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                msg = html_terms_of_service(self.server.css_cache,
                                            self.server.base_dir, 'http',
                                            self.server.onion_domain)
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                msg = html_terms_of_service(self.server.css_cache,
                                            self.server.base_dir, 'http',
                                            self.server.i2p_domain)
            else:
                msg = html_terms_of_service(self.server.css_cache,
                                            self.server.base_dir,
                                            self.server.http_prefix,
                                            self.server.domain_full)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, calling_domain)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'terms of service shown',
                                self.server.debug)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'terms of service done',
                            self.server.debug)

        # show a list of who you are following
        if htmlGET and authorized and usersInPath and \
           self.path.endswith('/followingaccounts'):
            nickname = get_nickname_from_actor(self.path)
            followingFilename = \
                acct_dir(self.server.base_dir,
                         nickname, self.server.domain) + '/following.txt'
            if not os.path.isfile(followingFilename):
                self._404()
                return
            msg = html_following_list(self.server.css_cache,
                                      self.server.base_dir, followingFilename)
            msglen = len(msg)
            self._login_headers('text/html', msglen, calling_domain)
            self._write(msg.encode('utf-8'))
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'following accounts shown',
                                self.server.debug)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'following accounts done',
                            self.server.debug)

        if self.path.endswith('/about'):
            if calling_domain.endswith('.onion'):
                msg = \
                    html_about(self.server.css_cache,
                               self.server.base_dir, 'http',
                               self.server.onion_domain,
                               None, self.server.translate,
                               self.server.system_language)
            elif calling_domain.endswith('.i2p'):
                msg = \
                    html_about(self.server.css_cache,
                               self.server.base_dir, 'http',
                               self.server.i2p_domain,
                               None, self.server.translate,
                               self.server.system_language)
            else:
                msg = \
                    html_about(self.server.css_cache,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain_full,
                               self.server.onion_domain,
                               self.server.translate,
                               self.server.system_language)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, calling_domain)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'show about screen',
                                self.server.debug)
            return

        if htmlGET and usersInPath and authorized and \
           self.path.endswith('/accesskeys'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            access_keys = self.server.access_keys
            if self.server.keyShortcuts.get(nickname):
                access_keys = \
                    self.server.keyShortcuts[nickname]

            msg = \
                html_access_keys(self.server.css_cache,
                                 self.server.base_dir,
                                 nickname, self.server.domain,
                                 self.server.translate,
                                 access_keys,
                                 self.server.access_keys,
                                 self.server.default_timeline)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, calling_domain)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'show accesskeys screen',
                                self.server.debug)
            return

        if htmlGET and usersInPath and authorized and \
           self.path.endswith('/themedesigner'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            if not is_artist(self.server.base_dir, nickname):
                self._403()
                return

            msg = \
                html_theme_designer(self.server.css_cache,
                                    self.server.base_dir,
                                    nickname, self.server.domain,
                                    self.server.translate,
                                    self.server.default_timeline,
                                    self.server.theme_name,
                                    self.server.access_keys)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, calling_domain)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'show theme designer screen',
                                self.server.debug)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show about screen done',
                            self.server.debug)

        # the initial welcome screen after first logging in
        if htmlGET and authorized and \
           '/users/' in self.path and self.path.endswith('/welcome'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not is_welcome_screen_complete(self.server.base_dir,
                                              nickname,
                                              self.server.domain):
                msg = \
                    html_welcome_screen(self.server.base_dir, nickname,
                                        self.server.system_language,
                                        self.server.translate,
                                        self.server.theme_name)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._login_headers('text/html', msglen, calling_domain)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'show welcome screen',
                                    self.server.debug)
                return
            else:
                self.path = self.path.replace('/welcome', '')

        # the welcome screen which allows you to set an avatar image
        if htmlGET and authorized and \
           '/users/' in self.path and self.path.endswith('/welcome_profile'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not is_welcome_screen_complete(self.server.base_dir,
                                              nickname,
                                              self.server.domain):
                msg = \
                    html_welcome_profile(self.server.base_dir, nickname,
                                         self.server.domain,
                                         self.server.http_prefix,
                                         self.server.domain_full,
                                         self.server.system_language,
                                         self.server.translate,
                                         self.server.theme_name)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._login_headers('text/html', msglen, calling_domain)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'show welcome profile screen',
                                    self.server.debug)
                return
            else:
                self.path = self.path.replace('/welcome_profile', '')

        # the final welcome screen
        if htmlGET and authorized and \
           '/users/' in self.path and self.path.endswith('/welcome_final'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not is_welcome_screen_complete(self.server.base_dir,
                                              nickname,
                                              self.server.domain):
                msg = \
                    html_welcome_final(self.server.base_dir, nickname,
                                       self.server.domain,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.system_language,
                                       self.server.translate,
                                       self.server.theme_name)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._login_headers('text/html', msglen, calling_domain)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'show welcome final screen',
                                    self.server.debug)
                return
            else:
                self.path = self.path.replace('/welcome_final', '')

        # if not authorized then show the login screen
        if htmlGET and self.path != '/login' and \
           not is_image_file(self.path) and \
           self.path != '/' and \
           self.path != '/users/news/linksmobile' and \
           self.path != '/users/news/newswiremobile':
            if self._redirect_to_login_screen(calling_domain, self.path,
                                              self.server.http_prefix,
                                              self.server.domain_full,
                                              self.server.onion_domain,
                                              self.server.i2p_domain,
                                              GETstartTime,
                                              authorized, self.server.debug):
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show login screen done',
                            self.server.debug)

        # manifest images used to create a home screen icon
        # when selecting "add to home screen" in browsers
        # which support progressive web apps
        if self.path == '/logo72.png' or \
           self.path == '/logo96.png' or \
           self.path == '/logo128.png' or \
           self.path == '/logo144.png' or \
           self.path == '/logo150.png' or \
           self.path == '/logo192.png' or \
           self.path == '/logo256.png' or \
           self.path == '/logo512.png' or \
           self.path == '/apple-touch-icon.png':
            media_filename = \
                self.server.base_dir + '/img' + self.path
            if os.path.isfile(media_filename):
                if self._etag_exists(media_filename):
                    # The file has not changed
                    self._304()
                    return

                tries = 0
                mediaBinary = None
                while tries < 5:
                    try:
                        with open(media_filename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as ex:
                        print('ERROR: manifest logo ' +
                              str(tries) + ' ' + str(ex))
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    mimeType = media_file_mime_type(media_filename)
                    self._set_headers_etag(media_filename, mimeType,
                                           mediaBinary, cookie,
                                           self.server.domain_full,
                                           False, None)
                    self._write(mediaBinary)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', 'manifest logo shown',
                                        self.server.debug)
                    return
            self._404()
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'manifest logo done',
                            self.server.debug)

        # manifest images used to show example screenshots
        # for use by app stores
        if self.path == '/screenshot1.jpg' or \
           self.path == '/screenshot2.jpg':
            screenFilename = \
                self.server.base_dir + '/img' + self.path
            if os.path.isfile(screenFilename):
                if self._etag_exists(screenFilename):
                    # The file has not changed
                    self._304()
                    return

                tries = 0
                mediaBinary = None
                while tries < 5:
                    try:
                        with open(screenFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as ex:
                        print('ERROR: manifest screenshot ' +
                              str(tries) + ' ' + str(ex))
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    mimeType = media_file_mime_type(screenFilename)
                    self._set_headers_etag(screenFilename, mimeType,
                                           mediaBinary, cookie,
                                           self.server.domain_full,
                                           False, None)
                    self._write(mediaBinary)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', 'show screenshot',
                                        self.server.debug)
                    return
            self._404()
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show screenshot done',
                            self.server.debug)

        # image on login screen or qrcode
        if (is_image_file(self.path) and
            (self.path.startswith('/login.') or
             self.path.startswith('/qrcode.png'))):
            iconFilename = \
                self.server.base_dir + '/accounts' + self.path
            if os.path.isfile(iconFilename):
                if self._etag_exists(iconFilename):
                    # The file has not changed
                    self._304()
                    return

                tries = 0
                mediaBinary = None
                while tries < 5:
                    try:
                        with open(iconFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as ex:
                        print('ERROR: login screen image ' +
                              str(tries) + ' ' + str(ex))
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    mimeTypeStr = media_file_mime_type(iconFilename)
                    self._set_headers_etag(iconFilename,
                                           mimeTypeStr,
                                           mediaBinary, cookie,
                                           self.server.domain_full,
                                           False, None)
                    self._write(mediaBinary)
                    fitness_performance(GETstartTime, self.server.fitness,
                                        '_GET', 'login screen logo',
                                        self.server.debug)
                    return
            self._404()
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'login screen logo done',
                            self.server.debug)

        # QR code for account handle
        if usersInPath and \
           self.path.endswith('/qrcode.png'):
            if self._show_q_rcode(calling_domain, self.path,
                                  self.server.base_dir,
                                  self.server.domain,
                                  self.server.port,
                                  GETstartTime):
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'account qrcode done',
                            self.server.debug)

        # search screen banner image
        if usersInPath:
            if self.path.endswith('/search_banner.png'):
                if self._search_screen_banner(calling_domain, self.path,
                                              self.server.base_dir,
                                              self.server.domain,
                                              self.server.port,
                                              GETstartTime):
                    return

            if self.path.endswith('/left_col_image.png'):
                if self._column_image('left', calling_domain, self.path,
                                      self.server.base_dir,
                                      self.server.domain,
                                      self.server.port,
                                      GETstartTime):
                    return

            if self.path.endswith('/right_col_image.png'):
                if self._column_image('right', calling_domain, self.path,
                                      self.server.base_dir,
                                      self.server.domain,
                                      self.server.port,
                                      GETstartTime):
                    return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'search screen banner done',
                            self.server.debug)

        if self.path.startswith('/defaultprofilebackground'):
            self._show_default_profile_background(calling_domain, self.path,
                                                  self.server.base_dir,
                                                  self.server.theme_name,
                                                  GETstartTime)
            return

        # show a background image on the login or person options page
        if '-background.' in self.path:
            if self._show_background_image(calling_domain, self.path,
                                           self.server.base_dir,
                                           GETstartTime):
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'background shown done',
                            self.server.debug)

        # emoji images
        if '/emoji/' in self.path:
            self._show_emoji(calling_domain, self.path,
                             self.server.base_dir,
                             GETstartTime)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show emoji done',
                            self.server.debug)

        # show media
        # Note that this comes before the busy flag to avoid conflicts
        # replace mastoson-style media path
        if '/system/media_attachments/files/' in self.path:
            self.path = self.path.replace('/system/media_attachments/files/',
                                          '/media/')
        if '/media/' in self.path:
            self._show_media(calling_domain,
                             self.path, self.server.base_dir,
                             GETstartTime)
            return

        if '/ontologies/' in self.path or \
           '/data/' in self.path:
            if not has_users_path(self.path):
                self._get_ontology(calling_domain,
                                   self.path, self.server.base_dir,
                                   GETstartTime)
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show media done',
                            self.server.debug)

        # show shared item images
        # Note that this comes before the busy flag to avoid conflicts
        if '/sharefiles/' in self.path:
            if self._show_share_image(calling_domain, self.path,
                                      self.server.base_dir,
                                      GETstartTime):
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'share image done',
                            self.server.debug)

        # icon images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/icons/'):
            self._show_icon(calling_domain, self.path,
                            self.server.base_dir, GETstartTime)
            return

        # help screen images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/helpimages/'):
            self._show_help_screen_image(calling_domain, self.path,
                                         self.server.base_dir, GETstartTime)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'help screen image done',
                            self.server.debug)

        # cached avatar images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/avatars/'):
            self._show_cached_avatar(refererDomain, self.path,
                                     self.server.base_dir,
                                     GETstartTime)
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'cached avatar done',
                            self.server.debug)

        # show avatar or background image
        # Note that this comes before the busy flag to avoid conflicts
        if self._show_avatar_or_banner(refererDomain, self.path,
                                       self.server.base_dir,
                                       self.server.domain,
                                       GETstartTime):
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'avatar or banner shown done',
                            self.server.debug)

        # This busy state helps to avoid flooding
        # Resources which are expected to be called from a web page
        # should be above this
        curr_timeGET = int(time.time() * 1000)
        if self.server.GETbusy:
            if curr_timeGET - self.server.lastGET < 500:
                if self.server.debug:
                    print('DEBUG: GET Busy')
                self.send_response(429)
                self.end_headers()
                return
        self.server.GETbusy = True
        self.server.lastGET = curr_timeGET

        # returns after this point should set GETbusy to False

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'GET busy time',
                            self.server.debug)

        if not permitted_dir(self.path):
            if self.server.debug:
                print('DEBUG: GET Not permitted')
            self._404()
            self.server.GETbusy = False
            return

        # get webfinger endpoint for a person
        if self._webfinger(calling_domain):
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'webfinger called',
                                self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'permitted directory',
                            self.server.debug)

        # show the login screen
        if (self.path.startswith('/login') or
            (self.path == '/' and
             not authorized and
             not self.server.news_instance)):
            # request basic auth
            msg = html_login(self.server.css_cache,
                             self.server.translate,
                             self.server.base_dir,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.system_language,
                             True).encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, calling_domain)
            self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'login shown',
                                self.server.debug)
            self.server.GETbusy = False
            return

        # show the news front page
        if self.path == '/' and \
           not authorized and \
           self.server.news_instance:
            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                self._logout_redirect('http://' +
                                      self.server.onion_domain +
                                      '/users/news', None,
                                      calling_domain)
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                self._logout_redirect('http://' +
                                      self.server.i2p_domain +
                                      '/users/news', None,
                                      calling_domain)
            else:
                self._logout_redirect(self.server.http_prefix +
                                      '://' +
                                      self.server.domain_full +
                                      '/users/news',
                                      None, calling_domain)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'news front page shown',
                                self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'login shown done',
                            self.server.debug)

        # the newswire screen on mobile
        if htmlGET and self.path.startswith('/users/') and \
           self.path.endswith('/newswiremobile'):
            if (authorized or
                (not authorized and
                 self.path.startswith('/users/news/') and
                 self.server.news_instance)):
                nickname = get_nickname_from_actor(self.path)
                if not nickname:
                    self._404()
                    self.server.GETbusy = False
                    return
                timeline_path = \
                    '/users/' + nickname + '/' + self.server.default_timeline
                show_publish_as_icon = self.server.show_publish_as_icon
                rss_icon_at_top = self.server.rss_icon_at_top
                icons_as_buttons = self.server.icons_as_buttons
                default_timeline = self.server.default_timeline
                access_keys = self.server.access_keys
                if self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.keyShortcuts[nickname]
                msg = \
                    html_newswire_mobile(self.server.css_cache,
                                         self.server.base_dir,
                                         nickname,
                                         self.server.domain,
                                         self.server.domain_full,
                                         self.server.http_prefix,
                                         self.server.translate,
                                         self.server.newswire,
                                         self.server.positive_voting,
                                         timeline_path,
                                         show_publish_as_icon,
                                         authorized,
                                         rss_icon_at_top,
                                         icons_as_buttons,
                                         default_timeline,
                                         self.server.theme_name,
                                         access_keys).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
                self.server.GETbusy = False
                return

        if htmlGET and self.path.startswith('/users/') and \
           self.path.endswith('/linksmobile'):
            if (authorized or
                (not authorized and
                 self.path.startswith('/users/news/') and
                 self.server.news_instance)):
                nickname = get_nickname_from_actor(self.path)
                if not nickname:
                    self._404()
                    self.server.GETbusy = False
                    return
                access_keys = self.server.access_keys
                if self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.keyShortcuts[nickname]
                timeline_path = \
                    '/users/' + nickname + '/' + self.server.default_timeline
                icons_as_buttons = self.server.icons_as_buttons
                default_timeline = self.server.default_timeline
                sharedItemsDomains = \
                    self.server.shared_items_federated_domains
                msg = \
                    html_links_mobile(self.server.css_cache,
                                      self.server.base_dir, nickname,
                                      self.server.domain_full,
                                      self.server.http_prefix,
                                      self.server.translate,
                                      timeline_path,
                                      authorized,
                                      self.server.rss_icon_at_top,
                                      icons_as_buttons,
                                      default_timeline,
                                      self.server.theme_name,
                                      access_keys,
                                      sharedItemsDomains).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen, cookie, calling_domain,
                                  False)
                self._write(msg)
                self.server.GETbusy = False
                return

        # hashtag search
        if self.path.startswith('/tags/') or \
           (authorized and '/tags/' in self.path):
            if self.path.startswith('/tags/rss2/'):
                self._hashtag_search_rss2(calling_domain,
                                          self.path, cookie,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domain_full,
                                          self.server.port,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          GETstartTime)
                self.server.GETbusy = False
                return
            self._hashtag_search(calling_domain,
                                 self.path, cookie,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domain_full,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'hashtag search done',
                            self.server.debug)

        # show or hide buttons in the web interface
        if htmlGET and usersInPath and \
           self.path.endswith('/minimal') and \
           authorized:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
                not_min = not is_minimal(self.server.base_dir,
                                         self.server.domain, nickname)
                set_minimal(self.server.base_dir,
                            self.server.domain, nickname, not_min)
                if not (self.server.media_instance or
                        self.server.blogs_instance):
                    self.path = '/users/' + nickname + '/inbox'
                else:
                    if self.server.blogs_instance:
                        self.path = '/users/' + nickname + '/tlblogs'
                    elif self.server.media_instance:
                        self.path = '/users/' + nickname + '/tlmedia'
                    else:
                        self.path = '/users/' + nickname + '/tlfeatures'

        # search for a fediverse address, shared item or emoji
        # from the web interface by selecting search icon
        if htmlGET and usersInPath:
            if self.path.endswith('/search') or \
               '/search?' in self.path:
                if '?' in self.path:
                    self.path = self.path.split('?')[0]

                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                access_keys = self.server.access_keys
                if self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.keyShortcuts[nickname]

                # show the search screen
                msg = html_search(self.server.css_cache,
                                  self.server.translate,
                                  self.server.base_dir, self.path,
                                  self.server.domain,
                                  self.server.default_timeline,
                                  self.server.theme_name,
                                  self.server.text_mode_banner,
                                  access_keys).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen, cookie, calling_domain,
                                  False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'search screen shown',
                                    self.server.debug)
                self.server.GETbusy = False
                return

        # show a hashtag category from the search screen
        if htmlGET and '/category/' in self.path:
            msg = html_search_hashtag_category(self.server.css_cache,
                                               self.server.translate,
                                               self.server.base_dir, self.path,
                                               self.server.domain,
                                               self.server.theme_name)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen, cookie, calling_domain,
                                  False)
                self._write(msg)
            fitness_performance(GETstartTime, self.server.fitness,
                                '_GET', 'hashtag category screen shown',
                                self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'search screen shown done',
                            self.server.debug)

        # Show the calendar for a user
        if htmlGET and usersInPath:
            if '/calendar' in self.path:
                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                access_keys = self.server.access_keys
                if self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.keyShortcuts[nickname]

                # show the calendar screen
                msg = html_calendar(self.server.person_cache,
                                    self.server.css_cache,
                                    self.server.translate,
                                    self.server.base_dir, self.path,
                                    self.server.http_prefix,
                                    self.server.domain_full,
                                    self.server.text_mode_banner,
                                    access_keys).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen, cookie, calling_domain,
                                  False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'calendar shown',
                                    self.server.debug)
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'calendar shown done',
                            self.server.debug)

        # Show confirmation for deleting a calendar event
        if htmlGET and usersInPath:
            if '/eventdelete' in self.path and \
               '?time=' in self.path and \
               '?eventid=' in self.path:
                if self._confirm_delete_event(calling_domain, self.path,
                                              self.server.base_dir,
                                              self.server.http_prefix,
                                              cookie,
                                              self.server.translate,
                                              self.server.domain_full,
                                              self.server.onion_domain,
                                              self.server.i2p_domain,
                                              GETstartTime):
                    self.server.GETbusy = False
                    return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'calendar delete shown done',
                            self.server.debug)

        # search for emoji by name
        if htmlGET and usersInPath:
            if self.path.endswith('/searchemoji'):
                # show the search screen
                msg = \
                    html_search_emoji_text_entry(self.server.css_cache,
                                                 self.server.translate,
                                                 self.server.base_dir,
                                                 self.path).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'emoji search shown',
                                    self.server.debug)
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'emoji search shown done',
                            self.server.debug)

        repeatPrivate = False
        if htmlGET and '?repeatprivate=' in self.path:
            repeatPrivate = True
            self.path = self.path.replace('?repeatprivate=', '?repeat=')
        # announce/repeat button was pressed
        if authorized and htmlGET and '?repeat=' in self.path:
            self._announce_button(calling_domain, self.path,
                                  self.server.base_dir,
                                  cookie, self.server.proxy_type,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domain_full,
                                  self.server.port,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  GETstartTime,
                                  repeatPrivate,
                                  self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show announce done',
                            self.server.debug)

        if authorized and htmlGET and '?unrepeatprivate=' in self.path:
            self.path = self.path.replace('?unrepeatprivate=', '?unrepeat=')

        # undo an announce/repeat from the web interface
        if authorized and htmlGET and '?unrepeat=' in self.path:
            self._undo_announce_button(calling_domain, self.path,
                                       self.server.base_dir,
                                       cookie, self.server.proxy_type,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domain_full,
                                       self.server.port,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       GETstartTime,
                                       repeatPrivate,
                                       self.server.debug,
                                       self.server.recent_posts_cache)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'unannounce done',
                            self.server.debug)

        # send a newswire moderation vote from the web interface
        if authorized and '/newswirevote=' in self.path and \
           self.path.startswith('/users/'):
            self._newswire_vote(calling_domain, self.path,
                                cookie,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domain_full,
                                self.server.port,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                GETstartTime,
                                self.server.proxy_type,
                                self.server.debug,
                                self.server.newswire)
            self.server.GETbusy = False
            return

        # send a newswire moderation unvote from the web interface
        if authorized and '/newswireunvote=' in self.path and \
           self.path.startswith('/users/'):
            self._newswire_unvote(calling_domain, self.path,
                                  cookie,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domain_full,
                                  self.server.port,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  GETstartTime,
                                  self.server.proxy_type,
                                  self.server.debug,
                                  self.server.newswire)
            self.server.GETbusy = False
            return

        # send a follow request approval from the web interface
        if authorized and '/followapprove=' in self.path and \
           self.path.startswith('/users/'):
            self._follow_approve_button(calling_domain, self.path,
                                        cookie,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domain_full,
                                        self.server.port,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        GETstartTime,
                                        self.server.proxy_type,
                                        self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'follow approve done',
                            self.server.debug)

        # deny a follow request from the web interface
        if authorized and '/followdeny=' in self.path and \
           self.path.startswith('/users/'):
            self._follow_deny_button(calling_domain, self.path,
                                     cookie,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domain_full,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     GETstartTime,
                                     self.server.proxy_type,
                                     self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'follow deny done',
                            self.server.debug)

        # like from the web interface icon
        if authorized and htmlGET and '?like=' in self.path:
            self._like_button(calling_domain, self.path,
                              self.server.base_dir,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.domain_full,
                              self.server.onion_domain,
                              self.server.i2p_domain,
                              GETstartTime,
                              self.server.proxy_type,
                              cookie,
                              self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'like button done',
                            self.server.debug)

        # undo a like from the web interface icon
        if authorized and htmlGET and '?unlike=' in self.path:
            self._undo_like_button(calling_domain, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domain_full,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   GETstartTime,
                                   self.server.proxy_type,
                                   cookie, self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'unlike button done',
                            self.server.debug)

        # emoji reaction from the web interface icon
        if authorized and htmlGET and \
           '?react=' in self.path and \
           '?actor=' in self.path:
            self._reaction_button(calling_domain, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domain_full,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  GETstartTime,
                                  self.server.proxy_type,
                                  cookie,
                                  self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'emoji reaction button done',
                            self.server.debug)

        # undo an emoji reaction from the web interface icon
        if authorized and htmlGET and \
           '?unreact=' in self.path and \
           '?actor=' in self.path:
            self._undo_reaction_button(calling_domain, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domain_full,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       GETstartTime,
                                       self.server.proxy_type,
                                       cookie, self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'unreaction button done',
                            self.server.debug)

        # bookmark from the web interface icon
        if authorized and htmlGET and '?bookmark=' in self.path:
            self._bookmark_button(calling_domain, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domain_full,
                                  self.server.port,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  GETstartTime,
                                  self.server.proxy_type,
                                  cookie, self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'bookmark shown done',
                            self.server.debug)

        # emoji recation from the web interface bottom icon
        if authorized and htmlGET and '?selreact=' in self.path:
            self._reaction_picker(calling_domain, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domain_full,
                                  self.server.port,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  GETstartTime,
                                  self.server.proxy_type,
                                  cookie, self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'bookmark shown done',
                            self.server.debug)

        # undo a bookmark from the web interface icon
        if authorized and htmlGET and '?unbookmark=' in self.path:
            self._undo_bookmark_button(calling_domain, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domain_full,
                                       self.server.port,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       GETstartTime,
                                       self.server.proxy_type, cookie,
                                       self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'unbookmark shown done',
                            self.server.debug)

        # delete button is pressed on a post
        if authorized and htmlGET and '?delete=' in self.path:
            self._delete_button(calling_domain, self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domain_full,
                                self.server.port,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                GETstartTime,
                                self.server.proxy_type, cookie,
                                self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'delete shown done',
                            self.server.debug)

        # The mute button is pressed
        if authorized and htmlGET and '?mute=' in self.path:
            self._mute_button(calling_domain, self.path,
                              self.server.base_dir,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.domain_full,
                              self.server.port,
                              self.server.onion_domain,
                              self.server.i2p_domain,
                              GETstartTime,
                              self.server.proxy_type, cookie,
                              self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'post muted done',
                            self.server.debug)

        # unmute a post from the web interface icon
        if authorized and htmlGET and '?unmute=' in self.path:
            self._undo_mute_button(calling_domain, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domain_full,
                                   self.server.port,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   GETstartTime,
                                   self.server.proxy_type, cookie,
                                   self.server.debug)
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'unmute activated done',
                            self.server.debug)

        # reply from the web interface icon
        in_reply_to_url = None
#        replyWithDM = False
        reply_to_list = []
        reply_page_number = 1
        reply_category = ''
        share_description = None
        conversation_id = None
#        replytoActor = None
        if htmlGET:
            if '?conversationId=' in self.path:
                conversation_id = self.path.split('?conversationId=')[1]
                if '?' in conversation_id:
                    conversation_id = conversation_id.split('?')[0]
            # public reply
            if '?replyto=' in self.path:
                in_reply_to_url = self.path.split('?replyto=')[1]
                if '?' in in_reply_to_url:
                    mentionsList = in_reply_to_url.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            reply_handle = m.replace('mention=', '')
                            if reply_handle not in reply_to_list:
                                reply_to_list.append(reply_handle)
                        if m.startswith('page='):
                            reply_page_str = m.replace('page=', '')
                            if reply_page_str.isdigit():
                                reply_page_number = int(reply_page_str)
#                        if m.startswith('actor='):
#                            replytoActor = m.replace('actor=', '')
                    in_reply_to_url = mentionsList[0]
                self.path = self.path.split('?replyto=')[0] + '/newpost'
                if self.server.debug:
                    print('DEBUG: replyto path ' + self.path)

            # reply to followers
            if '?replyfollowers=' in self.path:
                in_reply_to_url = self.path.split('?replyfollowers=')[1]
                if '?' in in_reply_to_url:
                    mentionsList = in_reply_to_url.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            reply_handle = m.replace('mention=', '')
                            if m.replace('mention=', '') not in reply_to_list:
                                reply_to_list.append(reply_handle)
                        if m.startswith('page='):
                            reply_page_str = m.replace('page=', '')
                            if reply_page_str.isdigit():
                                reply_page_number = int(reply_page_str)
#                        if m.startswith('actor='):
#                            replytoActor = m.replace('actor=', '')
                    in_reply_to_url = mentionsList[0]
                self.path = self.path.split('?replyfollowers=')[0] + \
                    '/newfollowers'
                if self.server.debug:
                    print('DEBUG: replyfollowers path ' + self.path)

            # replying as a direct message,
            # for moderation posts or the dm timeline
            if '?replydm=' in self.path:
                in_reply_to_url = self.path.split('?replydm=')[1]
                in_reply_to_url = urllib.parse.unquote_plus(in_reply_to_url)
                if '?' in in_reply_to_url:
                    # multiple parameters
                    mentionsList = in_reply_to_url.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            reply_handle = m.replace('mention=', '')
                            in_reply_to_url = reply_handle
                            if reply_handle not in reply_to_list:
                                reply_to_list.append(reply_handle)
                        elif m.startswith('page='):
                            reply_page_str = m.replace('page=', '')
                            if reply_page_str.isdigit():
                                reply_page_number = int(reply_page_str)
                        elif m.startswith('category='):
                            reply_category = m.replace('category=', '')
                        elif m.startswith('sharedesc:'):
                            # get the title for the shared item
                            share_description = \
                                m.replace('sharedesc:', '').strip()
                            share_description = \
                                share_description.replace('_', ' ')
                else:
                    # single parameter
                    if in_reply_to_url.startswith('mention='):
                        reply_handle = in_reply_to_url.replace('mention=', '')
                        in_reply_to_url = reply_handle
                        if reply_handle not in reply_to_list:
                            reply_to_list.append(reply_handle)
                    elif in_reply_to_url.startswith('sharedesc:'):
                        # get the title for the shared item
                        share_description = \
                            in_reply_to_url.replace('sharedesc:', '').strip()
                        share_description = \
                            share_description.replace('_', ' ')

                self.path = self.path.split('?replydm=')[0] + '/newdm'
                if self.server.debug:
                    print('DEBUG: replydm path ' + self.path)

            # Edit a blog post
            if authorized and \
               '/users/' in self.path and \
               '?editblogpost=' in self.path and \
               ';actor=' in self.path:
                message_id = self.path.split('?editblogpost=')[1]
                if ';' in message_id:
                    message_id = message_id.split(';')[0]
                actor = self.path.split(';actor=')[1]
                if ';' in actor:
                    actor = actor.split(';')[0]
                nickname = get_nickname_from_actor(self.path.split('?')[0])
                if nickname == actor:
                    postUrl = \
                        local_actor_url(self.server.http_prefix, nickname,
                                        self.server.domain_full) + \
                        '/statuses/' + message_id
                    msg = html_edit_blog(self.server.media_instance,
                                         self.server.translate,
                                         self.server.base_dir,
                                         self.server.http_prefix,
                                         self.path,
                                         reply_page_number,
                                         nickname, self.server.domain,
                                         postUrl,
                                         self.server.system_language)
                    if msg:
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, calling_domain, False)
                        self._write(msg)
                        self.server.GETbusy = False
                        return

            # list of known crawlers accessing nodeinfo or masto API
            if self._show_known_crawlers(calling_domain, self.path,
                                         self.server.base_dir,
                                         self.server.known_crawlers):
                self.server.GETbusy = False
                return

            # edit profile in web interface
            if self._edit_profile(calling_domain, self.path,
                                  self.server.translate,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.port,
                                  cookie):
                self.server.GETbusy = False
                return

            # edit links from the left column of the timeline in web interface
            if self._edit_links(calling_domain, self.path,
                                self.server.translate,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.port,
                                cookie,
                                self.server.theme_name):
                self.server.GETbusy = False
                return

            # edit newswire from the right column of the timeline
            if self._edit_newswire(calling_domain, self.path,
                                   self.server.translate,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.port,
                                   cookie):
                self.server.GETbusy = False
                return

            # edit news post
            if self._edit_news_post(calling_domain, self.path,
                                    self.server.translate,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.port,
                                    self.server.domain_full,
                                    cookie):
                self.server.GETbusy = False
                return

            if self._show_new_post(calling_domain, self.path,
                                   self.server.media_instance,
                                   self.server.translate,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   in_reply_to_url, reply_to_list,
                                   share_description, reply_page_number,
                                   reply_category,
                                   self.server.domain,
                                   self.server.domain_full,
                                   GETstartTime,
                                   cookie, no_drop_down, conversation_id):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'new post done',
                            self.server.debug)

        # get an individual post from the path /@nickname/statusnumber
        if self._show_individual_at_post(authorized,
                                         calling_domain, self.path,
                                         self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         self.server.domain_full,
                                         self.server.port,
                                         self.server.onion_domain,
                                         self.server.i2p_domain,
                                         GETstartTime,
                                         self.server.proxy_type,
                                         cookie, self.server.debug):
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'individual post done',
                            self.server.debug)

        # get replies to a post /users/nickname/statuses/number/replies
        if self.path.endswith('/replies') or '/replies?page=' in self.path:
            if self._show_replies_to_post(authorized,
                                          calling_domain, self.path,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domain_full,
                                          self.server.port,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          GETstartTime,
                                          self.server.proxy_type, cookie,
                                          self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'post replies done',
                            self.server.debug)

        # roles on profile screen
        if self.path.endswith('/roles') and usersInPath:
            if self._show_roles(authorized,
                                calling_domain, self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domain_full,
                                self.server.port,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                GETstartTime,
                                self.server.proxy_type,
                                cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show roles done',
                            self.server.debug)

        # show skills on the profile page
        if self.path.endswith('/skills') and usersInPath:
            if self._show_skills(authorized,
                                 calling_domain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domain_full,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 self.server.proxy_type,
                                 cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show skills done',
                            self.server.debug)

        if '?notifypost=' in self.path and usersInPath and authorized:
            if self._show_notify_post(authorized,
                                      calling_domain, self.path,
                                      self.server.base_dir,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.domain_full,
                                      self.server.port,
                                      self.server.onion_domain,
                                      self.server.i2p_domain,
                                      GETstartTime,
                                      self.server.proxy_type,
                                      cookie, self.server.debug):
                self.server.GETbusy = False
                return

        # get an individual post from the path
        # /users/nickname/statuses/number
        if '/statuses/' in self.path and usersInPath:
            if self._show_individual_post(authorized,
                                          calling_domain, self.path,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domain_full,
                                          self.server.port,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          GETstartTime,
                                          self.server.proxy_type,
                                          cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show status done',
                            self.server.debug)

        # get the inbox timeline for a given person
        if self.path.endswith('/inbox') or '/inbox?page=' in self.path:
            if self._show_inbox(authorized,
                                calling_domain, self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domain_full,
                                self.server.port,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                GETstartTime,
                                self.server.proxy_type,
                                cookie, self.server.debug,
                                self.server.recent_posts_cache,
                                self.server.session,
                                self.server.default_timeline,
                                self.server.max_recent_posts,
                                self.server.translate,
                                self.server.cached_webfingers,
                                self.server.person_cache,
                                self.server.allow_deletion,
                                self.server.project_version,
                                self.server.yt_replace_domain,
                                self.server.twitter_replacement_domain):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show inbox done',
                            self.server.debug)

        # get the direct messages timeline for a given person
        if self.path.endswith('/dm') or '/dm?page=' in self.path:
            if self._show_d_ms(authorized,
                               calling_domain, self.path,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.domain_full,
                               self.server.port,
                               self.server.onion_domain,
                               self.server.i2p_domain,
                               GETstartTime,
                               self.server.proxy_type,
                               cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show dms done',
                            self.server.debug)

        # get the replies timeline for a given person
        if self.path.endswith('/tlreplies') or '/tlreplies?page=' in self.path:
            if self._show_replies(authorized,
                                  calling_domain, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domain_full,
                                  self.server.port,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  GETstartTime,
                                  self.server.proxy_type,
                                  cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show replies 2 done',
                            self.server.debug)

        # get the media timeline for a given person
        if self.path.endswith('/tlmedia') or '/tlmedia?page=' in self.path:
            if self._show_media_timeline(authorized,
                                         calling_domain, self.path,
                                         self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         self.server.domain_full,
                                         self.server.port,
                                         self.server.onion_domain,
                                         self.server.i2p_domain,
                                         GETstartTime,
                                         self.server.proxy_type,
                                         cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show media 2 done',
                            self.server.debug)

        # get the blogs for a given person
        if self.path.endswith('/tlblogs') or '/tlblogs?page=' in self.path:
            if self._show_blogs_timeline(authorized,
                                         calling_domain, self.path,
                                         self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         self.server.domain_full,
                                         self.server.port,
                                         self.server.onion_domain,
                                         self.server.i2p_domain,
                                         GETstartTime,
                                         self.server.proxy_type,
                                         cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show blogs 2 done',
                            self.server.debug)

        # get the news for a given person
        if self.path.endswith('/tlnews') or '/tlnews?page=' in self.path:
            if self._show_news_timeline(authorized,
                                        calling_domain, self.path,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domain_full,
                                        self.server.port,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        GETstartTime,
                                        self.server.proxy_type,
                                        cookie, self.server.debug):
                self.server.GETbusy = False
                return

        # get features (local blogs) for a given person
        if self.path.endswith('/tlfeatures') or \
           '/tlfeatures?page=' in self.path:
            if self._show_features_timeline(authorized,
                                            calling_domain, self.path,
                                            self.server.base_dir,
                                            self.server.http_prefix,
                                            self.server.domain,
                                            self.server.domain_full,
                                            self.server.port,
                                            self.server.onion_domain,
                                            self.server.i2p_domain,
                                            GETstartTime,
                                            self.server.proxy_type,
                                            cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show news 2 done',
                            self.server.debug)

        # get the shared items timeline for a given person
        if self.path.endswith('/tlshares') or '/tlshares?page=' in self.path:
            if self._show_shares_timeline(authorized,
                                          calling_domain, self.path,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domain_full,
                                          self.server.port,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          GETstartTime,
                                          self.server.proxy_type,
                                          cookie, self.server.debug):
                self.server.GETbusy = False
                return

        # get the wanted items timeline for a given person
        if self.path.endswith('/tlwanted') or '/tlwanted?page=' in self.path:
            if self._show_wanted_timeline(authorized,
                                          calling_domain, self.path,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domain_full,
                                          self.server.port,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          GETstartTime,
                                          self.server.proxy_type,
                                          cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show shares 2 done',
                            self.server.debug)

        # block a domain from html_account_info
        if authorized and usersInPath and \
           '/accountinfo?blockdomain=' in self.path and \
           '?handle=' in self.path:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not is_moderator(self.server.base_dir, nickname):
                self._400()
                self.server.GETbusy = False
                return
            block_domain = self.path.split('/accountinfo?blockdomain=')[1]
            searchHandle = block_domain.split('?handle=')[1]
            searchHandle = urllib.parse.unquote_plus(searchHandle)
            block_domain = block_domain.split('?handle=')[0]
            block_domain = urllib.parse.unquote_plus(block_domain.strip())
            if '?' in block_domain:
                block_domain = block_domain.split('?')[0]
            add_global_block(self.server.base_dir, '*', block_domain)
            msg = \
                html_account_info(self.server.css_cache,
                                  self.server.translate,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  nickname,
                                  self.server.domain,
                                  self.server.port,
                                  searchHandle,
                                  self.server.debug,
                                  self.server.system_language,
                                  self.server.signing_priv_key_pem)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html',
                                msglen, calling_domain)
            self._write(msg)
            self.server.GETbusy = False
            return

        # unblock a domain from html_account_info
        if authorized and usersInPath and \
           '/accountinfo?unblockdomain=' in self.path and \
           '?handle=' in self.path:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not is_moderator(self.server.base_dir, nickname):
                self._400()
                self.server.GETbusy = False
                return
            block_domain = self.path.split('/accountinfo?unblockdomain=')[1]
            searchHandle = block_domain.split('?handle=')[1]
            searchHandle = urllib.parse.unquote_plus(searchHandle)
            block_domain = block_domain.split('?handle=')[0]
            block_domain = urllib.parse.unquote_plus(block_domain.strip())
            remove_global_block(self.server.base_dir, '*', block_domain)
            msg = \
                html_account_info(self.server.css_cache,
                                  self.server.translate,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  nickname,
                                  self.server.domain,
                                  self.server.port,
                                  searchHandle,
                                  self.server.debug,
                                  self.server.system_language,
                                  self.server.signing_priv_key_pem)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html',
                                msglen, calling_domain)
            self._write(msg)
            self.server.GETbusy = False
            return

        # get the bookmarks timeline for a given person
        if self.path.endswith('/tlbookmarks') or \
           '/tlbookmarks?page=' in self.path or \
           self.path.endswith('/bookmarks') or \
           '/bookmarks?page=' in self.path:
            if self._show_bookmarks_timeline(authorized,
                                             calling_domain, self.path,
                                             self.server.base_dir,
                                             self.server.http_prefix,
                                             self.server.domain,
                                             self.server.domain_full,
                                             self.server.port,
                                             self.server.onion_domain,
                                             self.server.i2p_domain,
                                             GETstartTime,
                                             self.server.proxy_type,
                                             cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show bookmarks 2 done',
                            self.server.debug)

        # outbox timeline
        if self.path.endswith('/outbox') or \
           '/outbox?page=' in self.path:
            if self._show_outbox_timeline(authorized,
                                          calling_domain, self.path,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domain_full,
                                          self.server.port,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          GETstartTime,
                                          self.server.proxy_type,
                                          cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show outbox done',
                            self.server.debug)

        # get the moderation feed for a moderator
        if self.path.endswith('/moderation') or \
           '/moderation?' in self.path:
            if self._show_mod_timeline(authorized,
                                       calling_domain, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domain_full,
                                       self.server.port,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       GETstartTime,
                                       self.server.proxy_type,
                                       cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show moderation done',
                            self.server.debug)

        if self._show_shares_feed(authorized,
                                  calling_domain, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domain_full,
                                  self.server.port,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  GETstartTime,
                                  self.server.proxy_type,
                                  cookie, self.server.debug, 'shares'):
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show profile 2 done',
                            self.server.debug)

        if self._show_following_feed(authorized,
                                     calling_domain, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domain_full,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     GETstartTime,
                                     self.server.proxy_type,
                                     cookie, self.server.debug):
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show profile 3 done',
                            self.server.debug)

        if self._show_followers_feed(authorized,
                                     calling_domain, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domain_full,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     GETstartTime,
                                     self.server.proxy_type,
                                     cookie, self.server.debug):
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show profile 4 done',
                            self.server.debug)

        # look up a person
        if self._show_person_profile(authorized,
                                     calling_domain, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domain_full,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     GETstartTime,
                                     self.server.proxy_type,
                                     cookie, self.server.debug):
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'show profile posts done',
                            self.server.debug)

        # check that a json file was requested
        if not self.path.endswith('.json'):
            if self.server.debug:
                print('DEBUG: GET Not json: ' + self.path +
                      ' ' + self.server.base_dir)
            self._404()
            self.server.GETbusy = False
            return

        if not self._secure_mode():
            if self.server.debug:
                print('WARN: Unauthorized GET')
            self._404()
            self.server.GETbusy = False
            return

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'authorized fetch',
                            self.server.debug)

        # check that the file exists
        filename = self.server.base_dir + self.path
        if os.path.isfile(filename):
            content = None
            try:
                with open(filename, 'r', encoding='utf-8') as rfile:
                    content = rfile.read()
            except OSError:
                print('EX: unable to read file ' + filename)
            if content:
                contentJson = json.loads(content)
                msg = json.dumps(contentJson,
                                 ensure_ascii=False).encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/json',
                                  msglen,
                                  None, calling_domain, False)
                self._write(msg)
                fitness_performance(GETstartTime, self.server.fitness,
                                    '_GET', 'arbitrary json',
                                    self.server.debug)
        else:
            if self.server.debug:
                print('DEBUG: GET Unknown file')
            self._404()
        self.server.GETbusy = False

        fitness_performance(GETstartTime, self.server.fitness,
                            '_GET', 'end benchmarks',
                            self.server.debug)

    def do_HEAD(self):
        calling_domain = self.server.domain_full
        if self.headers.get('Host'):
            calling_domain = decoded_host(self.headers['Host'])
            if self.server.onion_domain:
                if calling_domain != self.server.domain and \
                   calling_domain != self.server.domain_full and \
                   calling_domain != self.server.onion_domain:
                    print('HEAD domain blocked: ' + calling_domain)
                    self._400()
                    return
            else:
                if calling_domain != self.server.domain and \
                   calling_domain != self.server.domain_full:
                    print('HEAD domain blocked: ' + calling_domain)
                    self._400()
                    return

        checkPath = self.path
        etag = None
        fileLength = -1

        if '/media/' in self.path:
            if is_image_file(self.path) or \
               path_is_video(self.path) or \
               path_is_audio(self.path):
                mediaStr = self.path.split('/media/')[1]
                media_filename = \
                    self.server.base_dir + '/media/' + mediaStr
                if os.path.isfile(media_filename):
                    checkPath = media_filename
                    fileLength = os.path.getsize(media_filename)
                    media_tag_filename = media_filename + '.etag'
                    if os.path.isfile(media_tag_filename):
                        try:
                            with open(media_tag_filename, 'r') as etagFile:
                                etag = etagFile.read()
                        except OSError:
                            print('EX: do_HEAD unable to read ' +
                                  media_tag_filename)
                    else:
                        mediaBinary = None
                        try:
                            with open(media_filename, 'rb') as avFile:
                                mediaBinary = avFile.read()
                        except OSError:
                            print('EX: unable to read media binary ' +
                                  media_filename)
                        if mediaBinary:
                            etag = md5(mediaBinary).hexdigest()  # nosec
                            try:
                                with open(media_tag_filename, 'w+') as efile:
                                    efile.write(etag)
                            except OSError:
                                print('EX: do_HEAD unable to write ' +
                                      media_tag_filename)

        mediaFileType = media_file_mime_type(checkPath)
        self._set_headers_head(mediaFileType, fileLength,
                               etag, calling_domain, False)

    def _receive_new_post_process(self, postType: str, path: str, headers: {},
                                  length: int, postBytes, boundary: str,
                                  calling_domain: str, cookie: str,
                                  authorized: bool,
                                  content_license_url: str) -> int:
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
            nicknameStr = path.split('/users/')[1]
            if '?' in nicknameStr:
                nicknameStr = nicknameStr.split('?')[0]
            if '/' in nicknameStr:
                nickname = nicknameStr.split('/')[0]
            else:
                nickname = nicknameStr
            if self.server.debug:
                print('DEBUG: POST nickname ' + str(nickname))
            if not nickname:
                print('WARN: no nickname found when receiving ' + postType +
                      ' path ' + path)
                return -1
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
            mediaBytes, postBytes = \
                extract_media_in_form_post(postBytes, boundary, 'attachpic')
            if self.server.debug:
                if mediaBytes:
                    print('DEBUG: media was found. ' +
                          str(len(mediaBytes)) + ' bytes')
                else:
                    print('DEBUG: no media was found in POST')

            # Note: a .temp extension is used here so that at no time is
            # an image with metadata publicly exposed, even for a few mS
            filenameBase = \
                acct_dir(self.server.base_dir,
                         nickname, self.server.domain) + '/upload.temp'

            filename, attachment_media_type = \
                save_media_in_form_post(mediaBytes, self.server.debug,
                                        filenameBase)
            if self.server.debug:
                if filename:
                    print('DEBUG: POST media filename is ' + filename)
                else:
                    print('DEBUG: no media filename in POST')

            if filename:
                if is_image_file(filename):
                    post_imageFilename = filename.replace('.temp', '')
                    print('Removing metadata from ' + post_imageFilename)
                    city = get_spoofed_city(self.server.city,
                                            self.server.base_dir,
                                            nickname, self.server.domain)
                    if self.server.low_bandwidth:
                        convert_image_to_low_bandwidth(filename)
                    process_meta_data(self.server.base_dir,
                                      nickname, self.server.domain,
                                      filename, post_imageFilename, city,
                                      content_license_url)
                    if os.path.isfile(post_imageFilename):
                        print('POST media saved to ' + post_imageFilename)
                    else:
                        print('ERROR: POST media could not be saved to ' +
                              post_imageFilename)
                else:
                    if os.path.isfile(filename):
                        newFilename = filename.replace('.temp', '')
                        os.rename(filename, newFilename)
                        filename = newFilename

            fields = \
                extract_text_fields_in_post(postBytes, boundary,
                                            self.server.debug)
            if self.server.debug:
                if fields:
                    print('DEBUG: text field extracted from POST ' +
                          str(fields))
                else:
                    print('WARN: no text fields could be extracted from POST')

            # was the citations button pressed on the newblog screen?
            citationsButtonPress = False
            if postType == 'newblog' and fields.get('submitCitations'):
                if fields['submitCitations'] == \
                   self.server.translate['Citations']:
                    citationsButtonPress = True

            if not citationsButtonPress:
                # process the received text fields from the POST
                if not fields.get('message') and \
                   not fields.get('imageDescription') and \
                   not fields.get('pinToProfile'):
                    print('WARN: no message, image description or pin')
                    return -1
                submitText = self.server.translate['Submit']
                customSubmitText = \
                    get_config_param(self.server.base_dir, 'customSubmitText')
                if customSubmitText:
                    submitText = customSubmitText
                if fields.get('submitPost'):
                    if fields['submitPost'] != submitText:
                        print('WARN: no submit field ' + fields['submitPost'])
                        return -1
                else:
                    print('WARN: no submitPost')
                    return 2

            if not fields.get('imageDescription'):
                fields['imageDescription'] = None
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
            if not fields.get('location'):
                fields['location'] = None

            if not citationsButtonPress:
                # Store a file which contains the time in seconds
                # since epoch when an attempt to post something was made.
                # This is then used for active monthly users counts
                lastUsedFilename = \
                    acct_dir(self.server.base_dir,
                             nickname, self.server.domain) + '/.lastUsed'
                try:
                    with open(lastUsedFilename, 'w+') as lastUsedFile:
                        lastUsedFile.write(str(int(time.time())))
                except OSError:
                    print('EX: _receive_new_post_process unable to write ' +
                          lastUsedFilename)

            mentions_str = ''
            if fields.get('mentions'):
                mentions_str = fields['mentions'].strip() + ' '
            if not fields.get('commentsEnabled'):
                comments_enabled = False
            else:
                comments_enabled = True

            if postType == 'newpost':
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
                message_json = \
                    create_public_post(self.server.base_dir,
                                       nickname,
                                       self.server.domain,
                                       self.server.port,
                                       self.server.http_prefix,
                                       mentions_str + fields['message'],
                                       False, False, False, comments_enabled,
                                       filename, attachment_media_type,
                                       fields['imageDescription'],
                                       city,
                                       fields['replyTo'], fields['replyTo'],
                                       fields['subject'],
                                       fields['schedulePost'],
                                       fields['eventDate'],
                                       fields['eventTime'],
                                       fields['location'], False,
                                       self.server.system_language,
                                       conversation_id,
                                       self.server.low_bandwidth,
                                       self.server.content_license_url)
                if message_json:
                    if fields['schedulePost']:
                        return 1
                    if pin_to_profile:
                        sys_language = self.server.system_language
                        contentStr = \
                            get_base_content_from_post(message_json,
                                                       sys_language)
                        followers_only = False
                        pin_post(self.server.base_dir,
                                 nickname, self.server.domain, contentStr,
                                 followers_only)
                        return 1
                    if self._post_to_outbox(message_json,
                                            self.server.project_version,
                                            nickname):
                        populate_replies(self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain_full,
                                         message_json,
                                         self.server.max_replies,
                                         self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newblog':
                # citations button on newblog screen
                if citationsButtonPress:
                    message_json = \
                        html_citations(self.server.base_dir,
                                       nickname,
                                       self.server.domain,
                                       self.server.http_prefix,
                                       self.server.default_timeline,
                                       self.server.translate,
                                       self.server.newswire,
                                       self.server.css_cache,
                                       fields['subject'],
                                       fields['message'],
                                       filename, attachment_media_type,
                                       fields['imageDescription'],
                                       self.server.theme_name)
                    if message_json:
                        message_json = message_json.encode('utf-8')
                        message_jsonLen = len(message_json)
                        self._set_headers('text/html',
                                          message_jsonLen,
                                          cookie, calling_domain, False)
                        self._write(message_json)
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
                followers_only = False
                save_to_file = False
                client_to_server = False
                city = None
                conversation_id = None
                if fields.get('conversationId'):
                    conversation_id = fields['conversationId']
                message_json = \
                    create_blog_post(self.server.base_dir, nickname,
                                     self.server.domain, self.server.port,
                                     self.server.http_prefix,
                                     fields['message'],
                                     followers_only, save_to_file,
                                     client_to_server, comments_enabled,
                                     filename, attachment_media_type,
                                     fields['imageDescription'],
                                     city,
                                     fields['replyTo'], fields['replyTo'],
                                     fields['subject'],
                                     fields['schedulePost'],
                                     fields['eventDate'],
                                     fields['eventTime'],
                                     fields['location'],
                                     self.server.system_language,
                                     conversation_id,
                                     self.server.low_bandwidth,
                                     self.server.content_license_url)
                if message_json:
                    if fields['schedulePost']:
                        return 1
                    if self._post_to_outbox(message_json,
                                            self.server.project_version,
                                            nickname):
                        refresh_newswire(self.server.base_dir)
                        populate_replies(self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain_full,
                                         message_json,
                                         self.server.max_replies,
                                         self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'editblogpost':
                print('Edited blog post received')
                post_filename = \
                    locate_post(self.server.base_dir,
                                nickname, self.server.domain,
                                fields['postUrl'])
                if os.path.isfile(post_filename):
                    post_json_object = load_json(post_filename)
                    if post_json_object:
                        cachedFilename = \
                            acct_dir(self.server.base_dir,
                                     nickname, self.server.domain) + \
                            '/postcache/' + \
                            fields['postUrl'].replace('/', '#') + '.html'
                        if os.path.isfile(cachedFilename):
                            print('Edited blog post, removing cached html')
                            try:
                                os.remove(cachedFilename)
                            except OSError:
                                print('EX: _receive_new_post_process ' +
                                      'unable to delete ' + cachedFilename)
                        # remove from memory cache
                        remove_post_from_cache(post_json_object,
                                               self.server.recent_posts_cache)
                        # change the blog post title
                        post_json_object['object']['summary'] = \
                            fields['subject']
                        # format message
                        tags = []
                        hashtagsDict = {}
                        mentionedRecipients = []
                        fields['message'] = \
                            add_html_tags(self.server.base_dir,
                                          self.server.http_prefix,
                                          nickname, self.server.domain,
                                          fields['message'],
                                          mentionedRecipients,
                                          hashtagsDict, True)
                        # replace emoji with unicode
                        tags = []
                        for tagName, tag in hashtagsDict.items():
                            tags.append(tag)
                        # get list of tags
                        fields['message'] = \
                            replace_emoji_from_tags(self.server.session,
                                                    self.server.base_dir,
                                                    fields['message'],
                                                    tags, 'content',
                                                    self.server.debug)

                        post_json_object['object']['content'] = \
                            fields['message']
                        contentMap = post_json_object['object']['contentMap']
                        contentMap[self.server.system_language] = \
                            fields['message']

                        imgDescription = ''
                        if fields.get('imageDescription'):
                            imgDescription = fields['imageDescription']

                        if filename:
                            city = get_spoofed_city(self.server.city,
                                                    self.server.base_dir,
                                                    nickname,
                                                    self.server.domain)
                            post_json_object['object'] = \
                                attach_media(self.server.base_dir,
                                             self.server.http_prefix,
                                             nickname,
                                             self.server.domain,
                                             self.server.port,
                                             post_json_object['object'],
                                             filename,
                                             attachment_media_type,
                                             imgDescription,
                                             city,
                                             self.server.low_bandwidth,
                                             self.server.content_license_url)

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
            elif postType == 'newunlisted':
                city = get_spoofed_city(self.server.city,
                                        self.server.base_dir,
                                        nickname,
                                        self.server.domain)
                followers_only = False
                save_to_file = False
                client_to_server = False

                conversation_id = None
                if fields.get('conversationId'):
                    conversation_id = fields['conversationId']

                message_json = \
                    create_unlisted_post(self.server.base_dir,
                                         nickname,
                                         self.server.domain, self.server.port,
                                         self.server.http_prefix,
                                         mentions_str + fields['message'],
                                         followers_only, save_to_file,
                                         client_to_server, comments_enabled,
                                         filename, attachment_media_type,
                                         fields['imageDescription'],
                                         city,
                                         fields['replyTo'],
                                         fields['replyTo'],
                                         fields['subject'],
                                         fields['schedulePost'],
                                         fields['eventDate'],
                                         fields['eventTime'],
                                         fields['location'],
                                         self.server.system_language,
                                         conversation_id,
                                         self.server.low_bandwidth,
                                         self.server.content_license_url)
                if message_json:
                    if fields['schedulePost']:
                        return 1
                    if self._post_to_outbox(message_json,
                                            self.server.project_version,
                                            nickname):
                        populate_replies(self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         message_json,
                                         self.server.max_replies,
                                         self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newfollowers':
                city = get_spoofed_city(self.server.city,
                                        self.server.base_dir,
                                        nickname,
                                        self.server.domain)
                followers_only = True
                save_to_file = False
                client_to_server = False

                conversation_id = None
                if fields.get('conversationId'):
                    conversation_id = fields['conversationId']

                mentions_message = mentions_str + fields['message']
                message_json = \
                    create_followers_only_post(self.server.base_dir,
                                               nickname,
                                               self.server.domain,
                                               self.server.port,
                                               self.server.http_prefix,
                                               mentions_message,
                                               followers_only, save_to_file,
                                               client_to_server,
                                               comments_enabled,
                                               filename, attachment_media_type,
                                               fields['imageDescription'],
                                               city,
                                               fields['replyTo'],
                                               fields['replyTo'],
                                               fields['subject'],
                                               fields['schedulePost'],
                                               fields['eventDate'],
                                               fields['eventTime'],
                                               fields['location'],
                                               self.server.system_language,
                                               conversation_id,
                                               self.server.low_bandwidth,
                                               self.server.content_license_url)
                if message_json:
                    if fields['schedulePost']:
                        return 1
                    if self._post_to_outbox(message_json,
                                            self.server.project_version,
                                            nickname):
                        populate_replies(self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         message_json,
                                         self.server.max_replies,
                                         self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newdm':
                message_json = None
                print('A DM was posted')
                if '@' in mentions_str:
                    city = get_spoofed_city(self.server.city,
                                            self.server.base_dir,
                                            nickname,
                                            self.server.domain)
                    followers_only = True
                    save_to_file = False
                    client_to_server = False

                    conversation_id = None
                    if fields.get('conversationId'):
                        conversation_id = fields['conversationId']
                    content_license_url = self.server.content_license_url

                    message_json = \
                        create_direct_message_post(self.server.base_dir,
                                                   nickname,
                                                   self.server.domain,
                                                   self.server.port,
                                                   self.server.http_prefix,
                                                   mentions_str +
                                                   fields['message'],
                                                   followers_only,
                                                   save_to_file,
                                                   client_to_server,
                                                   comments_enabled,
                                                   filename,
                                                   attachment_media_type,
                                                   fields['imageDescription'],
                                                   city,
                                                   fields['replyTo'],
                                                   fields['replyTo'],
                                                   fields['subject'],
                                                   True,
                                                   fields['schedulePost'],
                                                   fields['eventDate'],
                                                   fields['eventTime'],
                                                   fields['location'],
                                                   self.server.system_language,
                                                   conversation_id,
                                                   self.server.low_bandwidth,
                                                   content_license_url)
                if message_json:
                    if fields['schedulePost']:
                        return 1
                    print('Sending new DM to ' +
                          str(message_json['object']['to']))
                    if self._post_to_outbox(message_json,
                                            self.server.project_version,
                                            nickname):
                        populate_replies(self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domain,
                                         message_json,
                                         self.server.max_replies,
                                         self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newreminder':
                message_json = None
                handle = nickname + '@' + self.server.domain_full
                print('A reminder was posted for ' + handle)
                if '@' + handle not in mentions_str:
                    mentions_str = '@' + handle + ' ' + mentions_str
                city = get_spoofed_city(self.server.city,
                                        self.server.base_dir,
                                        nickname,
                                        self.server.domain)
                followers_only = True
                save_to_file = False
                client_to_server = False
                comments_enabled = False
                conversation_id = None
                mentions_message = mentions_str + fields['message']
                message_json = \
                    create_direct_message_post(self.server.base_dir,
                                               nickname,
                                               self.server.domain,
                                               self.server.port,
                                               self.server.http_prefix,
                                               mentions_message,
                                               followers_only, save_to_file,
                                               client_to_server,
                                               comments_enabled,
                                               filename, attachment_media_type,
                                               fields['imageDescription'],
                                               city,
                                               None, None,
                                               fields['subject'],
                                               True, fields['schedulePost'],
                                               fields['eventDate'],
                                               fields['eventTime'],
                                               fields['location'],
                                               self.server.system_language,
                                               conversation_id,
                                               self.server.low_bandwidth,
                                               self.server.content_license_url)
                if message_json:
                    if fields['schedulePost']:
                        return 1
                    print('DEBUG: new reminder to ' +
                          str(message_json['object']['to']))
                    if self._post_to_outbox(message_json,
                                            self.server.project_version,
                                            nickname):
                        return 1
                    return -1
            elif postType == 'newreport':
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
                message_json = \
                    create_report_post(self.server.base_dir,
                                       nickname,
                                       self.server.domain, self.server.port,
                                       self.server.http_prefix,
                                       mentions_str + fields['message'],
                                       True, False, False, True,
                                       filename, attachment_media_type,
                                       fields['imageDescription'],
                                       city,
                                       self.server.debug, fields['subject'],
                                       self.server.system_language,
                                       self.server.low_bandwidth,
                                       self.server.content_license_url)
                if message_json:
                    if self._post_to_outbox(message_json,
                                            self.server.project_version,
                                            nickname):
                        return 1
                    return -1
            elif postType == 'newquestion':
                if not fields.get('duration'):
                    return -1
                if not fields.get('message'):
                    return -1
#                questionStr = fields['message']
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
                int_duration = int(fields['duration'])
                message_json = \
                    create_question_post(self.server.base_dir,
                                         nickname,
                                         self.server.domain,
                                         self.server.port,
                                         self.server.http_prefix,
                                         fields['message'], q_options,
                                         False, False, False,
                                         comments_enabled,
                                         filename, attachment_media_type,
                                         fields['imageDescription'],
                                         city,
                                         fields['subject'],
                                         int_duration,
                                         self.server.system_language,
                                         self.server.low_bandwidth,
                                         self.server.content_license_url)
                if message_json:
                    if self.server.debug:
                        print('DEBUG: new Question')
                    if self._post_to_outbox(message_json,
                                            self.server.project_version,
                                            nickname):
                        return 1
                return -1
            elif postType == 'newshare' or postType == 'newwanted':
                if not fields.get('itemQty'):
                    print(postType + ' no itemQty')
                    return -1
                if not fields.get('itemType'):
                    print(postType + ' no itemType')
                    return -1
                if 'itemPrice' not in fields:
                    print(postType + ' no itemPrice')
                    return -1
                if 'itemCurrency' not in fields:
                    print(postType + ' no itemCurrency')
                    return -1
                if not fields.get('category'):
                    print(postType + ' no category')
                    return -1
                if not fields.get('duration'):
                    print(postType + ' no duratio')
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
                if postType == 'newshare':
                    print('Adding shared item')
                    shares_file_type = 'shares'
                else:
                    print('Adding wanted item')
                    shares_file_type = 'wanted'
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
                          self.server.system_language,
                          self.server.translate, shares_file_type,
                          self.server.low_bandwidth,
                          self.server.content_license_url)
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

    def _receive_new_post(self, postType: str, path: str,
                          calling_domain: str, cookie: str,
                          authorized: bool,
                          content_license_url: str) -> int:
        """A new post has been created
        This creates a thread to send the new post
        """
        page_number = 1

        if '/users/' not in path:
            print('Not receiving new post for ' + path +
                  ' because /users/ not in path')
            return None

        if '?' + postType + '?' not in path:
            print('Not receiving new post for ' + path +
                  ' because ?' + postType + '? not in path')
            return None

        print('New post begins: ' + postType + ' ' + path)

        if '?page=' in path:
            page_number_str = path.split('?page=')[1]
            if '?' in page_number_str:
                page_number_str = page_number_str.split('?')[0]
            if '#' in page_number_str:
                page_number_str = page_number_str.split('#')[0]
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
            waitCtr = 0
            np_thread = self.server.new_post_thread[new_post_thread_name]
            while np_thread.is_alive() and waitCtr < 8:
                time.sleep(1)
                waitCtr += 1
            if waitCtr >= 8:
                print('Killing previous new post thread for ' +
                      new_post_thread_name)
                np_thread.kill()

        # make a copy of self.headers
        headers = {}
        headersWithoutCookie = {}
        for dictEntryName, headerLine in self.headers.items():
            headers[dictEntryName] = headerLine
            if dictEntryName.lower() != 'cookie':
                headersWithoutCookie[dictEntryName] = headerLine
        print('New post headers: ' + str(headersWithoutCookie))

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
                    postBytes = self.rfile.read(length)
                except SocketError as ex:
                    if ex.errno == errno.ECONNRESET:
                        print('WARN: POST postBytes ' +
                              'connection reset by peer')
                    else:
                        print('WARN: POST postBytes socket error')
                    return None
                except ValueError as ex:
                    print('ERROR: POST postBytes rfile.read failed, ' +
                          str(ex))
                    return None

                # second length check from the bytes received
                # since Content-Length could be untruthful
                length = len(postBytes)
                if length > self.server.max_post_length:
                    print('POST size too large')
                    return None

                # Note sending new posts needs to be synchronous,
                # otherwise any attachments can get mangled if
                # other events happen during their decoding
                print('Creating new post from: ' + new_post_thread_name)
                self._receive_new_post_process(postType,
                                               path, headers, length,
                                               postBytes, boundary,
                                               calling_domain, cookie,
                                               authorized,
                                               content_license_url)
        return page_number

    def _crypto_ap_iread_handle(self):
        """Reads handle
        """
        messageBytes = None
        maxDeviceIdLength = 2048
        length = int(self.headers['Content-length'])
        if length >= maxDeviceIdLength:
            print('WARN: handle post to crypto API is too long ' +
                  str(length) + ' bytes')
            return {}
        try:
            messageBytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: handle POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: handle POST messageBytes socket error')
            return {}
        except ValueError as ex:
            print('ERROR: handle POST messageBytes rfile.read failed ' +
                  str(ex))
            return {}

        lenMessage = len(messageBytes)
        if lenMessage > 2048:
            print('WARN: handle post to crypto API is too long ' +
                  str(lenMessage) + ' bytes')
            return {}

        handle = messageBytes.decode("utf-8")
        if not handle:
            return None
        if '@' not in handle:
            return None
        if '[' in handle:
            return json.loads(messageBytes)
        if handle.startswith('@'):
            handle = handle[1:]
        if '@' not in handle:
            return None
        return handle.strip()

    def _crypto_ap_iread_json(self) -> {}:
        """Obtains json from POST to the crypto API
        """
        messageBytes = None
        maxCryptoMessageLength = 10240
        length = int(self.headers['Content-length'])
        if length >= maxCryptoMessageLength:
            print('WARN: post to crypto API is too long ' +
                  str(length) + ' bytes')
            return {}
        try:
            messageBytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST messageBytes socket error')
            return {}
        except ValueError as ex:
            print('ERROR: POST messageBytes rfile.read failed, ' + str(ex))
            return {}

        lenMessage = len(messageBytes)
        if lenMessage > 10240:
            print('WARN: post to crypto API is too long ' +
                  str(lenMessage) + ' bytes')
            return {}

        return json.loads(messageBytes)

    def _crypto_api_query(self, calling_domain: str) -> bool:
        handle = self._crypto_ap_iread_handle()
        if not handle:
            return False
        if isinstance(handle, str):
            personDir = self.server.base_dir + '/accounts/' + handle
            if not os.path.isdir(personDir + '/devices'):
                return False
            devicesList = []
            for subdir, dirs, files in os.walk(personDir + '/devices'):
                for f in files:
                    deviceFilename = os.path.join(personDir + '/devices', f)
                    if not os.path.isfile(deviceFilename):
                        continue
                    contentJson = load_json(deviceFilename)
                    if contentJson:
                        devicesList.append(contentJson)
                break
            # return the list of devices for this handle
            msg = \
                json.dumps(devicesList,
                           ensure_ascii=False).encode('utf-8')
            msglen = len(msg)
            self._set_headers('application/json',
                              msglen,
                              None, calling_domain, False)
            self._write(msg)
            return True
        return False

    def _crypto_api(self, path: str, authorized: bool) -> None:
        """POST or GET with the crypto API
        """
        if authorized and path.startswith('/api/v1/crypto/keys/upload'):
            # register a device to an authorized account
            if not self.authorizedNickname:
                self._400()
                return
            deviceKeys = self._crypto_ap_iread_json()
            if not deviceKeys:
                self._400()
                return
            if isinstance(deviceKeys, dict):
                if not e2e_evalid_device(deviceKeys):
                    self._400()
                    return
                fingerprintKey = \
                    deviceKeys['fingerprintKey']['publicKeyBase64']
                e2e_eadd_device(self.server.base_dir,
                                self.authorizedNickname,
                                self.server.domain,
                                deviceKeys['deviceId'],
                                deviceKeys['name'],
                                deviceKeys['claim'],
                                fingerprintKey,
                                deviceKeys['identityKey']['publicKeyBase64'],
                                deviceKeys['fingerprintKey']['type'],
                                deviceKeys['identityKey']['type'])
                self._200()
                return
            self._400()
        elif path.startswith('/api/v1/crypto/keys/query'):
            # given a handle (nickname@domain) return a list of the devices
            # registered to that handle
            if not self._crypto_api_query():
                self._400()
        elif path.startswith('/api/v1/crypto/keys/claim'):
            # TODO
            self._200()
        elif authorized and path.startswith('/api/v1/crypto/delivery'):
            # TODO
            self._200()
        elif (authorized and
              path.startswith('/api/v1/crypto/encrypted_messages/clear')):
            # TODO
            self._200()
        elif path.startswith('/api/v1/crypto/encrypted_messages'):
            # TODO
            self._200()
        else:
            self._400()

    def do_POST(self):
        POSTstartTime = time.time()

        if not self._establish_session("POST"):
            fitness_performance(POSTstartTime, self.server.fitness,
                                '_POST', 'create_session',
                                self.server.debug)
            self._404()
            return

        if self.server.debug:
            print('DEBUG: POST to ' + self.server.base_dir +
                  ' path: ' + self.path + ' busy: ' +
                  str(self.server.POSTbusy))

        calling_domain = self.server.domain_full
        if self.headers.get('Host'):
            calling_domain = decoded_host(self.headers['Host'])
            if self.server.onion_domain:
                if calling_domain != self.server.domain and \
                   calling_domain != self.server.domain_full and \
                   calling_domain != self.server.onion_domain:
                    print('POST domain blocked: ' + calling_domain)
                    self._400()
                    return
            elif self.server.i2p_domain:
                if calling_domain != self.server.domain and \
                   calling_domain != self.server.domain_full and \
                   calling_domain != self.server.i2p_domain:
                    print('POST domain blocked: ' + calling_domain)
                    self._400()
                    return
            else:
                if calling_domain != self.server.domain and \
                   calling_domain != self.server.domain_full:
                    print('POST domain blocked: ' + calling_domain)
                    self._400()
                    return

        curr_timePOST = int(time.time() * 1000)
        if self.server.POSTbusy:
            if curr_timePOST - self.server.lastPOST < 500:
                self.send_response(429)
                self.end_headers()
                return
        self.server.POSTbusy = True
        self.server.lastPOST = curr_timePOST

        ua_str = self._get_user_agent()

        if self._blocked_user_agent(calling_domain, ua_str):
            self._400()
            self.server.POSTbusy = False
            return

        if not self.headers.get('Content-type'):
            print('Content-type header missing')
            self._400()
            self.server.POSTbusy = False
            return

        # returns after this point should set POSTbusy to False

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
                self._503()
                self.server.POSTbusy = False
                return

        cookie = None
        if self.headers.get('Cookie'):
            cookie = self.headers['Cookie']

        # check authorization
        authorized = self._is_authorized()
        if not authorized and self.server.debug:
            print('POST Not authorized')
            print(str(self.headers))

        if self.path.startswith('/api/v1/crypto/'):
            self._crypto_api(self.path, authorized)
            self.server.POSTbusy = False
            return

        # if this is a POST to the outbox then check authentication
        self.outboxAuthenticated = False
        self.post_to_nickname = None

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'start',
                            self.server.debug)

        # login screen
        if self.path.startswith('/login'):
            self._show_login_screen(self.path, calling_domain, cookie,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.domain_full,
                                    self.server.port,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    self.server.debug)
            self.server.POSTbusy = False
            return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', '_login_screen',
                            self.server.debug)

        if authorized and self.path.endswith('/sethashtagcategory'):
            self._set_hashtag_category(calling_domain, cookie,
                                       authorized, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domain_full,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       self.server.debug,
                                       self.server.default_timeline,
                                       self.server.allow_local_network_access)
            self.server.POSTbusy = False
            return

        # update of profile/avatar from web interface,
        # after selecting Edit button then Submit
        if authorized and self.path.endswith('/profiledata'):
            self._profile_edit(calling_domain, cookie, authorized, self.path,
                               self.server.base_dir, self.server.http_prefix,
                               self.server.domain,
                               self.server.domain_full,
                               self.server.onion_domain,
                               self.server.i2p_domain, self.server.debug,
                               self.server.allow_local_network_access,
                               self.server.system_language,
                               self.server.content_license_url)
            self.server.POSTbusy = False
            return

        if authorized and self.path.endswith('/linksdata'):
            self._links_update(calling_domain, cookie, authorized, self.path,
                               self.server.base_dir, self.server.http_prefix,
                               self.server.domain,
                               self.server.domain_full,
                               self.server.onion_domain,
                               self.server.i2p_domain, self.server.debug,
                               self.server.default_timeline,
                               self.server.allow_local_network_access)
            self.server.POSTbusy = False
            return

        if authorized and self.path.endswith('/newswiredata'):
            self._newswire_update(calling_domain, cookie,
                                  authorized, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domain_full,
                                  self.server.onion_domain,
                                  self.server.i2p_domain, self.server.debug,
                                  self.server.default_timeline)
            self.server.POSTbusy = False
            return

        if authorized and self.path.endswith('/citationsdata'):
            self._citations_update(calling_domain, cookie,
                                   authorized, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domain_full,
                                   self.server.onion_domain,
                                   self.server.i2p_domain, self.server.debug,
                                   self.server.default_timeline,
                                   self.server.newswire)
            self.server.POSTbusy = False
            return

        if authorized and self.path.endswith('/newseditdata'):
            self._news_post_edit(calling_domain, cookie, authorized, self.path,
                                 self.server.base_dir, self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domain_full,
                                 self.server.onion_domain,
                                 self.server.i2p_domain, self.server.debug,
                                 self.server.default_timeline)
            self.server.POSTbusy = False
            return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', '_news_post_edit',
                            self.server.debug)

        usersInPath = False
        if '/users/' in self.path:
            usersInPath = True

        # moderator action buttons
        if authorized and usersInPath and \
           self.path.endswith('/moderationaction'):
            self._moderator_actions(self.path, calling_domain, cookie,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.domain_full,
                                    self.server.port,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    self.server.debug)
            self.server.POSTbusy = False
            return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', '_moderator_actions',
                            self.server.debug)

        searchForEmoji = False
        if self.path.endswith('/searchhandleemoji'):
            searchForEmoji = True
            self.path = self.path.replace('/searchhandleemoji',
                                          '/searchhandle')
            if self.server.debug:
                print('DEBUG: searching for emoji')
                print('authorized: ' + str(authorized))

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'searchhandleemoji',
                            self.server.debug)

        # a search was made
        if ((authorized or searchForEmoji) and
            (self.path.endswith('/searchhandle') or
             '/searchhandle?page=' in self.path)):
            self._receive_search_query(calling_domain, cookie,
                                       authorized, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domain_full,
                                       self.server.port,
                                       searchForEmoji,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       POSTstartTime, {},
                                       self.server.debug)
            self.server.POSTbusy = False
            return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', '_receive_search_query',
                            self.server.debug)

        if not authorized:
            if self.path.endswith('/rmpost'):
                print('ERROR: attempt to remove post was not authorized. ' +
                      self.path)
                self._400()
                self.server.POSTbusy = False
                return
        else:
            # a vote/question/poll is posted
            if self.path.endswith('/question') or \
               '/question?page=' in self.path:
                self._receive_vote(calling_domain, cookie,
                                   authorized, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domain_full,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   self.server.debug)
                self.server.POSTbusy = False
                return

            # removes a shared item
            if self.path.endswith('/rmshare'):
                self._remove_share(calling_domain, cookie,
                                   authorized, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domain_full,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   self.server.debug)
                self.server.POSTbusy = False
                return

            # removes a wanted item
            if self.path.endswith('/rmwanted'):
                self._remove_wanted(calling_domain, cookie,
                                    authorized, self.path,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.domain_full,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    self.server.debug)
                self.server.POSTbusy = False
                return

            fitness_performance(POSTstartTime, self.server.fitness,
                                '_POST', '_remove_wanted',
                                self.server.debug)

            # removes a post
            if self.path.endswith('/rmpost'):
                if '/users/' not in self.path:
                    print('ERROR: attempt to remove post ' +
                          'was not authorized. ' + self.path)
                    self._400()
                    self.server.POSTbusy = False
                    return
            if self.path.endswith('/rmpost'):
                self._receive_remove_post(calling_domain, cookie,
                                          authorized, self.path,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domain_full,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          self.server.debug)
                self.server.POSTbusy = False
                return

            fitness_performance(POSTstartTime, self.server.fitness,
                                '_POST', '_remove_post',
                                self.server.debug)

            # decision to follow in the web interface is confirmed
            if self.path.endswith('/followconfirm'):
                self._follow_confirm(calling_domain, cookie,
                                     authorized, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domain_full,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     self.server.debug)
                self.server.POSTbusy = False
                return

            fitness_performance(POSTstartTime, self.server.fitness,
                                '_POST', '_follow_confirm',
                                self.server.debug)

            # decision to unfollow in the web interface is confirmed
            if self.path.endswith('/unfollowconfirm'):
                self._unfollow_confirm(calling_domain, cookie,
                                       authorized, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domain_full,
                                       self.server.port,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       self.server.debug)
                self.server.POSTbusy = False
                return

            fitness_performance(POSTstartTime, self.server.fitness,
                                '_POST', '_unfollow_confirm',
                                self.server.debug)

            # decision to unblock in the web interface is confirmed
            if self.path.endswith('/unblockconfirm'):
                self._unblock_confirm(calling_domain, cookie,
                                      authorized, self.path,
                                      self.server.base_dir,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.domain_full,
                                      self.server.port,
                                      self.server.onion_domain,
                                      self.server.i2p_domain,
                                      self.server.debug)
                self.server.POSTbusy = False
                return

            fitness_performance(POSTstartTime, self.server.fitness,
                                '_POST', '_unblock_confirm',
                                self.server.debug)

            # decision to block in the web interface is confirmed
            if self.path.endswith('/blockconfirm'):
                self._block_confirm(calling_domain, cookie,
                                    authorized, self.path,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.domain_full,
                                    self.server.port,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    self.server.debug)
                self.server.POSTbusy = False
                return

            fitness_performance(POSTstartTime, self.server.fitness,
                                '_POST', '_block_confirm',
                                self.server.debug)

            # an option was chosen from person options screen
            # view/follow/block/report
            if self.path.endswith('/personoptions'):
                self._person_options(self.path,
                                     calling_domain, cookie,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domain_full,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     self.server.debug)
                self.server.POSTbusy = False
                return

            # Change the key shortcuts
            if usersInPath and \
               self.path.endswith('/changeAccessKeys'):
                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                if not self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.access_keys
                    self.server.keyShortcuts[nickname] = access_keys.copy()
                access_keys = self.server.keyShortcuts[nickname]

                self._key_shortcuts(self.path,
                                    calling_domain, cookie,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    nickname,
                                    self.server.domain,
                                    self.server.domain_full,
                                    self.server.port,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    self.server.debug,
                                    access_keys,
                                    self.server.default_timeline)
                self.server.POSTbusy = False
                return

            # theme designer submit/cancel button
            if usersInPath and \
               self.path.endswith('/changeThemeSettings'):
                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                if not self.server.keyShortcuts.get(nickname):
                    access_keys = self.server.access_keys
                    self.server.keyShortcuts[nickname] = access_keys.copy()
                access_keys = self.server.keyShortcuts[nickname]
                allow_local_network_access = \
                    self.server.allow_local_network_access

                self._theme_designer_edit(self.path,
                                          calling_domain, cookie,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          nickname,
                                          self.server.domain,
                                          self.server.domain_full,
                                          self.server.port,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          self.server.debug,
                                          access_keys,
                                          self.server.default_timeline,
                                          self.server.theme_name,
                                          allow_local_network_access,
                                          self.server.system_language)
                self.server.POSTbusy = False
                return

        # update the shared item federation token for the calling domain
        # if it is within the permitted federation
        if self.headers.get('Origin') and \
           self.headers.get('SharesCatalog'):
            if self.server.debug:
                print('SharesCatalog header: ' + self.headers['SharesCatalog'])
            if not self.server.shared_items_federated_domains:
                siDomainsStr = \
                    get_config_param(self.server.base_dir,
                                     'sharedItemsFederatedDomains')
                if siDomainsStr:
                    if self.server.debug:
                        print('Loading shared items federated domains list')
                    siDomainsList = siDomainsStr.split(',')
                    domainsList = self.server.shared_items_federated_domains
                    for siDomain in siDomainsList:
                        domainsList.append(siDomain.strip())
            originDomain = self.headers.get('Origin')
            if originDomain != self.server.domain_full and \
               originDomain != self.server.onion_domain and \
               originDomain != self.server.i2p_domain and \
               originDomain in self.server.shared_items_federated_domains:
                if self.server.debug:
                    print('DEBUG: ' +
                          'POST updating shared item federation ' +
                          'token for ' + originDomain + ' to ' +
                          self.server.domain_full)
                sharedItemTokens = self.server.sharedItemFederationTokens
                sharesToken = self.headers['SharesCatalog']
                self.server.sharedItemFederationTokens = \
                    update_shared_item_federation_token(self.server.base_dir,
                                                        originDomain,
                                                        sharesToken,
                                                        self.server.debug,
                                                        sharedItemTokens)
            elif self.server.debug:
                fed_domains = self.server.shared_items_federated_domains
                if originDomain not in fed_domains:
                    print('originDomain is not in federated domains list ' +
                          originDomain)
                else:
                    print('originDomain is not a different instance. ' +
                          originDomain + ' ' + self.server.domain_full + ' ' +
                          str(fed_domains))

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'SharesCatalog',
                            self.server.debug)

        # receive different types of post created by html_new_post
        newPostEndpoints = get_new_post_endpoints()
        for currPostType in newPostEndpoints:
            if not authorized:
                if self.server.debug:
                    print('POST was not authorized')
                break

            postRedirect = self.server.default_timeline
            if currPostType == 'newshare':
                postRedirect = 'tlshares'
            elif currPostType == 'newwanted':
                postRedirect = 'tlwanted'

            page_number = \
                self._receive_new_post(currPostType, self.path,
                                       calling_domain, cookie,
                                       authorized,
                                       self.server.content_license_url)
            if page_number:
                print(currPostType + ' post received')
                nickname = self.path.split('/users/')[1]
                if '?' in nickname:
                    nickname = nickname.split('?')[0]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                if calling_domain.endswith('.onion') and \
                   self.server.onion_domain:
                    actorPathStr = \
                        local_actor_url('http', nickname,
                                        self.server.onion_domain) + \
                        '/' + postRedirect + \
                        '?page=' + str(page_number)
                    self._redirect_headers(actorPathStr, cookie,
                                           calling_domain)
                elif (calling_domain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actorPathStr = \
                        local_actor_url('http', nickname,
                                        self.server.i2p_domain) + \
                        '/' + postRedirect + \
                        '?page=' + str(page_number)
                    self._redirect_headers(actorPathStr, cookie,
                                           calling_domain)
                else:
                    actorPathStr = \
                        local_actor_url(self.server.http_prefix, nickname,
                                        self.server.domain_full) + \
                        '/' + postRedirect + '?page=' + str(page_number)
                    self._redirect_headers(actorPathStr, cookie,
                                           calling_domain)
                self.server.POSTbusy = False
                return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'receive post',
                            self.server.debug)

        if self.path.endswith('/outbox') or \
           self.path.endswith('/wanted') or \
           self.path.endswith('/shares'):
            if usersInPath:
                if authorized:
                    self.outboxAuthenticated = True
                    pathUsersSection = self.path.split('/users/')[1]
                    self.post_to_nickname = pathUsersSection.split('/')[0]
            if not self.outboxAuthenticated:
                self.send_response(405)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitness_performance(POSTstartTime, self.server.fitness,
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
            self._400()
            self.server.POSTbusy = False
            return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'check path',
                            self.server.debug)

        # read the message and convert it into a python dictionary
        length = int(self.headers['Content-length'])
        if self.server.debug:
            print('DEBUG: content-length: ' + str(length))
        if not self.headers['Content-type'].startswith('image/') and \
           not self.headers['Content-type'].startswith('video/') and \
           not self.headers['Content-type'].startswith('audio/'):
            if length > self.server.maxMessageLength:
                print('Maximum message length exceeded ' + str(length))
                self._400()
                self.server.POSTbusy = False
                return
        else:
            if length > self.server.maxMediaSize:
                print('Maximum media size exceeded ' + str(length))
                self._400()
                self.server.POSTbusy = False
                return

        # receive images to the outbox
        if self.headers['Content-type'].startswith('image/') and \
           usersInPath:
            self._receive_image(length, calling_domain, cookie,
                                authorized, self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domain_full,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                self.server.debug)
            self.server.POSTbusy = False
            return

        # refuse to receive non-json content
        content_typeStr = self.headers['Content-type']
        if not content_typeStr.startswith('application/json') and \
           not content_typeStr.startswith('application/activity+json') and \
           not content_typeStr.startswith('application/ld+json'):
            print("POST is not json: " + self.headers['Content-type'])
            if self.server.debug:
                print(str(self.headers))
                length = int(self.headers['Content-length'])
                if length < self.server.max_post_length:
                    try:
                        unknownPost = self.rfile.read(length).decode('utf-8')
                    except SocketError as ex:
                        if ex.errno == errno.ECONNRESET:
                            print('WARN: POST unknownPost ' +
                                  'connection reset by peer')
                        else:
                            print('WARN: POST unknownPost socket error')
                        self.send_response(400)
                        self.end_headers()
                        self.server.POSTbusy = False
                        return
                    except ValueError as ex:
                        print('ERROR: POST unknownPost rfile.read failed, ' +
                              str(ex))
                        self.send_response(400)
                        self.end_headers()
                        self.server.POSTbusy = False
                        return
                    print(str(unknownPost))
            self._400()
            self.server.POSTbusy = False
            return

        if self.server.debug:
            print('DEBUG: Reading message')

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'check content type',
                            self.server.debug)

        # check content length before reading bytes
        if self.path == '/sharedInbox' or self.path == '/inbox':
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
                self._400()
                self.server.POSTbusy = False
                return

        try:
            messageBytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST messageBytes socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST messageBytes rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        # check content length after reading bytes
        if self.path == '/sharedInbox' or self.path == '/inbox':
            lenMessage = len(messageBytes)
            if lenMessage > 10240:
                print('WARN: post to shared inbox is too long ' +
                      str(lenMessage) + ' bytes')
                self._400()
                self.server.POSTbusy = False
                return

        if contains_invalid_chars(messageBytes.decode("utf-8")):
            self._400()
            self.server.POSTbusy = False
            return

        # convert the raw bytes to json
        message_json = json.loads(messageBytes)

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'load json',
                            self.server.debug)

        # https://www.w3.org/TR/activitypub/#object-without-create
        if self.outboxAuthenticated:
            if self._post_to_outbox(message_json,
                                    self.server.project_version, None):
                if message_json.get('id'):
                    locnStr = remove_id_ending(message_json['id'])
                    self.headers['Location'] = locnStr
                self.send_response(201)
                self.end_headers()
                self.server.POSTbusy = False
                return
            else:
                if self.server.debug:
                    print('Failed to post to outbox')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', '_post_to_outbox',
                            self.server.debug)

        # check the necessary properties are available
        if self.server.debug:
            print('DEBUG: Check message has params')

        if not message_json:
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if self.path.endswith('/inbox') or \
           self.path == '/sharedInbox':
            if not inbox_message_has_params(message_json):
                if self.server.debug:
                    print("DEBUG: inbox message doesn't have the " +
                          "required parameters")
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'inbox_message_has_params',
                            self.server.debug)

        header_signature = self._getheader_signature_input()

        if header_signature:
            if 'keyId=' not in header_signature:
                if self.server.debug:
                    print('DEBUG: POST to inbox has no keyId in ' +
                          'header signature parameter')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitness_performance(POSTstartTime, self.server.fitness,
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
                self.server.POSTbusy = False
                return

        fitness_performance(POSTstartTime, self.server.fitness,
                            '_POST', 'inbox_permitted_message',
                            self.server.debug)

        if self.server.debug:
            print('DEBUG: POST saving to inbox queue')
        if usersInPath:
            pathUsersSection = self.path.split('/users/')[1]
            if '/' not in pathUsersSection:
                if self.server.debug:
                    print('DEBUG: This is not a users endpoint')
            else:
                self.post_to_nickname = pathUsersSection.split('/')[0]
                if self.post_to_nickname:
                    queueStatus = \
                        self._update_inbox_queue(self.post_to_nickname,
                                                 message_json, messageBytes)
                    if queueStatus >= 0 and queueStatus <= 3:
                        self.server.POSTbusy = False
                        return
                    if self.server.debug:
                        print('_update_inbox_queue exited ' +
                              'without doing anything')
                else:
                    if self.server.debug:
                        print('self.post_to_nickname is None')
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy = False
            return
        else:
            if self.path == '/sharedInbox' or self.path == '/inbox':
                if self.server.debug:
                    print('DEBUG: POST to shared inbox')
                queueStatus = \
                    self._update_inbox_queue('inbox', message_json,
                                             messageBytes)
                if queueStatus >= 0 and queueStatus <= 3:
                    self.server.POSTbusy = False
                    return
        self._200()
        self.server.POSTbusy = False


class PubServerUnitTest(PubServer):
    protocol_version = 'HTTP/1.0'


class EpicyonServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # surpress connection reset errors
        cls, e = sys.exc_info()[:2]
        if cls is ConnectionResetError:
            if e.errno != errno.ECONNRESET:
                print('ERROR: (EpicyonServer) ' + str(cls) + ", " + str(e))
            pass
        elif cls is BrokenPipeError:
            pass
        else:
            print('ERROR: (EpicyonServer) ' + str(cls) + ", " + str(e))
            return HTTPServer.handle_error(self, request, client_address)


def run_posts_queue(base_dir: str, send_threads: [], debug: bool,
                    timeoutMins: int) -> None:
    """Manages the threads used to send posts
    """
    while True:
        time.sleep(1)
        remove_dormant_threads(base_dir, send_threads, debug, timeoutMins)


def run_shares_expire(versionNumber: str, base_dir: str) -> None:
    """Expires shares as needed
    """
    while True:
        time.sleep(120)
        expire_shares(base_dir)


def run_posts_watchdog(project_version: str, httpd) -> None:
    """This tries to keep the posts thread running even if it dies
    """
    print('Starting posts queue watchdog')
    postsQueueOriginal = httpd.thrPostsQueue.clone(run_posts_queue)
    httpd.thrPostsQueue.start()
    while True:
        time.sleep(20)
        if httpd.thrPostsQueue.is_alive():
            continue
        httpd.thrPostsQueue.kill()
        httpd.thrPostsQueue = postsQueueOriginal.clone(run_posts_queue)
        httpd.thrPostsQueue.start()
        print('Restarting posts queue...')


def run_shares_expire_watchdog(project_version: str, httpd) -> None:
    """This tries to keep the shares expiry thread running even if it dies
    """
    print('Starting shares expiry watchdog')
    sharesExpireOriginal = httpd.thrSharesExpire.clone(run_shares_expire)
    httpd.thrSharesExpire.start()
    while True:
        time.sleep(20)
        if httpd.thrSharesExpire.is_alive():
            continue
        httpd.thrSharesExpire.kill()
        httpd.thrSharesExpire = sharesExpireOriginal.clone(run_shares_expire)
        httpd.thrSharesExpire.start()
        print('Restarting shares expiry...')


def load_tokens(base_dir: str, tokensDict: {}, tokens_lookup: {}) -> None:
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if '@' in handle:
                tokenFilename = base_dir + '/accounts/' + handle + '/.token'
                if not os.path.isfile(tokenFilename):
                    continue
                nickname = handle.split('@')[0]
                token = None
                try:
                    with open(tokenFilename, 'r') as fp:
                        token = fp.read()
                except Exception as ex:
                    print('WARN: Unable to read token for ' +
                          nickname + ' ' + str(ex))
                if not token:
                    continue
                tokensDict[nickname] = token
                tokens_lookup[token] = nickname
        break


def run_daemon(content_license_url: str,
               lists_enabled: str,
               default_reply_interval_hrs: int,
               low_bandwidth: bool,
               max_like_count: int,
               shared_items_federated_domains: [],
               user_agents_blocked: [],
               log_login_failures: bool,
               city: str,
               show_node_info_accounts: bool,
               show_node_info_version: bool,
               broch_mode: bool,
               verify_all_signatures: bool,
               send_threads_timeout_mins: int,
               dormant_months: int,
               max_newswire_posts: int,
               allow_local_network_access: bool,
               max_feed_item_size_kb: int,
               publish_button_at_top: bool,
               rss_icon_at_top: bool,
               icons_as_buttons: bool,
               full_width_tl_button_header: bool,
               show_publish_as_icon: bool,
               max_followers: int,
               max_news_posts: int,
               max_mirrored_articles: int,
               max_newswire_feed_size_kb: int,
               max_newswire_postsPerSource: int,
               show_published_date_only: bool,
               voting_time_mins: int,
               positive_voting: bool,
               newswire_votes_threshold: int,
               news_instance: bool,
               blogs_instance: bool,
               media_instance: bool,
               max_recent_posts: int,
               enable_shared_inbox: bool, registration: bool,
               language: str, project_version: str,
               instance_id: str, client_to_server: bool,
               base_dir: str, domain: str,
               onion_domain: str, i2p_domain: str,
               yt_replace_domain: str,
               twitter_replacement_domain: str,
               port: int = 80, proxy_port: int = 80,
               http_prefix: str = 'https',
               fed_list: [] = [],
               max_mentions: int = 10, max_emoji: int = 10,
               secure_mode: bool = False,
               proxy_type: str = None, max_replies: int = 64,
               domain_max_posts_per_day: int = 8640,
               account_max_posts_per_day: int = 864,
               allow_deletion: bool = False,
               debug: bool = False, unit_test: bool = False,
               instance_only_skills_search: bool = False,
               send_threads: [] = [],
               manual_follower_approval: bool = True) -> None:
    if len(domain) == 0:
        domain = 'localhost'
    if '.' not in domain:
        if domain != 'localhost':
            print('Invalid domain: ' + domain)
            return

    if unit_test:
        serverAddress = (domain, proxy_port)
        pubHandler = partial(PubServerUnitTest)
    else:
        serverAddress = ('', proxy_port)
        pubHandler = partial(PubServer)

    if not os.path.isdir(base_dir + '/accounts'):
        print('Creating accounts directory')
        os.mkdir(base_dir + '/accounts')

    try:
        httpd = EpicyonServer(serverAddress, pubHandler)
    except Exception as ex:
        if ex.errno == 98:
            print('ERROR: HTTP server address is already in use. ' +
                  str(serverAddress))
            return False

        print('ERROR: HTTP server failed to start. ' + str(ex))
        print('serverAddress: ' + str(serverAddress))
        return False

    # scan the theme directory for any svg files containing scripts
    assert not scan_themes_for_scripts(base_dir)

    # license for content of the instance
    if not content_license_url:
        content_license_url = 'https://creativecommons.org/licenses/by/4.0'
    httpd.content_license_url = content_license_url

    # fitness metrics
    fitness_filename = base_dir + '/accounts/fitness.json'
    httpd.fitness = {}
    if os.path.isfile(fitness_filename):
        httpd.fitness = load_json(fitness_filename)

    # initialize authorized fetch key
    httpd.signing_priv_key_pem = None

    httpd.show_node_info_accounts = show_node_info_accounts
    httpd.show_node_info_version = show_node_info_version

    # ASCII/ANSI text banner used in shell browsers, such as Lynx
    httpd.text_mode_banner = get_text_mode_banner(base_dir)

    # key shortcuts SHIFT + ALT + [key]
    httpd.access_keys = {
        'Page up': ',',
        'Page down': '.',
        'submitButton': 'y',
        'followButton': 'f',
        'blockButton': 'b',
        'infoButton': 'i',
        'snoozeButton': 's',
        'reportButton': '[',
        'viewButton': 'v',
        'enterPetname': 'p',
        'enterNotes': 'n',
        'menuTimeline': 't',
        'menuEdit': 'e',
        'menuThemeDesigner': 'z',
        'menuProfile': 'p',
        'menuInbox': 'i',
        'menuSearch': '/',
        'menuNewPost': 'n',
        'menuCalendar': 'c',
        'menuDM': 'd',
        'menuReplies': 'r',
        'menuOutbox': 's',
        'menuBookmarks': 'q',
        'menuShares': 'h',
        'menuWanted': 'w',
        'menuBlogs': 'b',
        'menuNewswire': 'u',
        'menuLinks': 'l',
        'menuMedia': 'm',
        'menuModeration': 'o',
        'menuFollowing': 'f',
        'menuFollowers': 'g',
        'menuRoles': 'o',
        'menuSkills': 'a',
        'menuLogout': 'x',
        'menuKeys': 'k',
        'Public': 'p',
        'Reminder': 'r'
    }

    # how many hours after a post was publushed can a reply be made
    default_reply_interval_hrs = 9999999
    httpd.default_reply_interval_hrs = default_reply_interval_hrs

    httpd.keyShortcuts = {}
    load_access_keys_for_accounts(base_dir, httpd.keyShortcuts,
                                  httpd.access_keys)

    # wheither to use low bandwidth images
    httpd.low_bandwidth = low_bandwidth

    # list of blocked user agent types within the User-Agent header
    httpd.user_agents_blocked = user_agents_blocked

    httpd.unit_test = unit_test
    httpd.allow_local_network_access = allow_local_network_access
    if unit_test:
        # unit tests are run on the local network with LAN addresses
        httpd.allow_local_network_access = True
    httpd.yt_replace_domain = yt_replace_domain
    httpd.twitter_replacement_domain = twitter_replacement_domain

    # newswire storing rss feeds
    httpd.newswire = {}

    # maximum number of posts to appear in the newswire on the right column
    httpd.max_newswire_posts = max_newswire_posts

    # whether to require that all incoming posts have valid jsonld signatures
    httpd.verify_all_signatures = verify_all_signatures

    # This counter is used to update the list of blocked domains in memory.
    # It helps to avoid touching the disk and so improves flooding resistance
    httpd.blocklistUpdateCtr = 0
    httpd.blocklistUpdateInterval = 100
    httpd.domainBlocklist = get_domain_blocklist(base_dir)

    httpd.manual_follower_approval = manual_follower_approval
    httpd.onion_domain = onion_domain
    httpd.i2p_domain = i2p_domain
    httpd.media_instance = media_instance
    httpd.blogs_instance = blogs_instance

    # load translations dictionary
    httpd.translate = {}
    httpd.system_language = 'en'
    if not unit_test:
        httpd.translate, httpd.system_language = \
            load_translations_from_file(base_dir, language)
        if not httpd.system_language:
            print('ERROR: no system language loaded')
            sys.exit()
        print('System language: ' + httpd.system_language)
        if not httpd.translate:
            print('ERROR: no translations were loaded')
            sys.exit()

    # spoofed city for gps location misdirection
    httpd.city = city

    # For moderated newswire feeds this is the amount of time allowed
    # for voting after the post arrives
    httpd.voting_time_mins = voting_time_mins
    # on the newswire, whether moderators vote positively for items
    # or against them (veto)
    httpd.positive_voting = positive_voting
    # number of votes needed to remove a newswire item from the news timeline
    # or if positive voting is anabled to add the item to the news timeline
    httpd.newswire_votes_threshold = newswire_votes_threshold
    # maximum overall size of an rss/atom feed read by the newswire daemon
    # If the feed is too large then this is probably a DoS attempt
    httpd.max_newswire_feed_size_kb = max_newswire_feed_size_kb

    # For each newswire source (account or rss feed)
    # this is the maximum number of posts to show for each.
    # This avoids one or two sources from dominating the news,
    # and also prevents big feeds from slowing down page load times
    httpd.max_newswire_postsPerSource = max_newswire_postsPerSource

    # Show only the date at the bottom of posts, and not the time
    httpd.show_published_date_only = show_published_date_only

    # maximum number of news articles to mirror
    httpd.max_mirrored_articles = max_mirrored_articles

    # maximum number of posts in the news timeline/outbox
    httpd.max_news_posts = max_news_posts

    # The maximum number of tags per post which can be
    # attached to RSS feeds pulled in via the newswire
    httpd.maxTags = 32

    # maximum number of followers per account
    httpd.max_followers = max_followers

    # whether to show an icon for publish on the
    # newswire, or a 'Publish' button
    httpd.show_publish_as_icon = show_publish_as_icon

    # Whether to show the timeline header containing inbox, outbox
    # calendar, etc as the full width of the screen or not
    httpd.full_width_tl_button_header = full_width_tl_button_header

    # whether to show icons in the header (eg calendar) as buttons
    httpd.icons_as_buttons = icons_as_buttons

    # whether to show the RSS icon at the top or the bottom of the timeline
    httpd.rss_icon_at_top = rss_icon_at_top

    # Whether to show the newswire publish button at the top,
    # above the header image
    httpd.publish_button_at_top = publish_button_at_top

    # maximum size of individual RSS feed items, in K
    httpd.max_feed_item_size_kb = max_feed_item_size_kb

    # maximum size of a hashtag category, in K
    httpd.maxCategoriesFeedItemSizeKb = 1024

    # how many months does a followed account need to be unseen
    # for it to be considered dormant?
    httpd.dormant_months = dormant_months

    # maximum number of likes to display on a post
    httpd.max_like_count = max_like_count
    if httpd.max_like_count < 0:
        httpd.max_like_count = 0
    elif httpd.max_like_count > 16:
        httpd.max_like_count = 16

    httpd.followingItemsPerPage = 12
    if registration == 'open':
        httpd.registration = True
    else:
        httpd.registration = False
    httpd.enable_shared_inbox = enable_shared_inbox
    httpd.outboxThread = {}
    httpd.outbox_thread_index = {}
    httpd.new_post_thread = {}
    httpd.project_version = project_version
    httpd.secure_mode = secure_mode
    # max POST size of 30M
    httpd.max_post_length = 1024 * 1024 * 30
    httpd.maxMediaSize = httpd.max_post_length
    # Maximum text length is 64K - enough for a blog post
    httpd.maxMessageLength = 64000
    # Maximum overall number of posts per box
    httpd.maxPostsInBox = 32000
    httpd.domain = domain
    httpd.port = port
    httpd.domain_full = get_full_domain(domain, port)
    save_domain_qrcode(base_dir, http_prefix, httpd.domain_full)
    httpd.http_prefix = http_prefix
    httpd.debug = debug
    httpd.federation_list = fed_list.copy()
    httpd.shared_items_federated_domains = \
        shared_items_federated_domains.copy()
    httpd.base_dir = base_dir
    httpd.instance_id = instance_id
    httpd.person_cache = {}
    httpd.cached_webfingers = {}
    httpd.favicons_cache = {}
    httpd.proxy_type = proxy_type
    httpd.session = None
    httpd.session_last_update = 0
    httpd.lastGET = 0
    httpd.lastPOST = 0
    httpd.GETbusy = False
    httpd.POSTbusy = False
    httpd.received_message = False
    httpd.inbox_queue = []
    httpd.send_threads = send_threads
    httpd.postLog = []
    httpd.max_queue_length = 64
    httpd.allow_deletion = allow_deletion
    httpd.last_login_time = 0
    httpd.last_login_failure = 0
    httpd.login_failure_count = {}
    httpd.log_login_failures = log_login_failures
    httpd.max_replies = max_replies
    httpd.tokens = {}
    httpd.tokens_lookup = {}
    load_tokens(base_dir, httpd.tokens, httpd.tokens_lookup)
    httpd.instance_only_skills_search = instance_only_skills_search
    # contains threads used to send posts to followers
    httpd.followers_threads = []

    # create a cache of blocked domains in memory.
    # This limits the amount of slow disk reads which need to be done
    httpd.blocked_cache = []
    httpd.blocked_cache_last_updated = 0
    httpd.blocked_cache_update_secs = 120
    httpd.blocked_cache_last_updated = \
        update_blocked_cache(base_dir, httpd.blocked_cache,
                             httpd.blocked_cache_last_updated,
                             httpd.blocked_cache_update_secs)

    # cache to store css files
    httpd.css_cache = {}

    # get the list of custom emoji, for use by the mastodon api
    httpd.customEmoji = \
        metadata_custom_emoji(base_dir, http_prefix, httpd.domain_full)

    # whether to enable broch mode, which locks down the instance
    set_broch_mode(base_dir, httpd.domain_full, broch_mode)

    if not os.path.isdir(base_dir + '/accounts/inbox@' + domain):
        print('Creating shared inbox: inbox@' + domain)
        create_shared_inbox(base_dir, 'inbox', domain, port, http_prefix)

    if not os.path.isdir(base_dir + '/accounts/news@' + domain):
        print('Creating news inbox: news@' + domain)
        create_news_inbox(base_dir, domain, port, http_prefix)
        set_config_param(base_dir, "listsEnabled", "Murdoch press")

    # dict of known web crawlers accessing nodeinfo or the masto API
    # and how many times they have been seen
    httpd.known_crawlers = {}
    known_crawlers_filename = base_dir + '/accounts/knownCrawlers.json'
    if os.path.isfile(known_crawlers_filename):
        httpd.known_crawlers = load_json(known_crawlers_filename)
    # when was the last crawler seen?
    httpd.last_known_crawler = 0

    if lists_enabled:
        httpd.lists_enabled = lists_enabled
    else:
        httpd.lists_enabled = get_config_param(base_dir, "listsEnabled")
    httpd.cw_lists = load_cw_lists(base_dir, True)

    # set the avatar for the news account
    httpd.theme_name = get_config_param(base_dir, 'theme')
    if not httpd.theme_name:
        httpd.theme_name = 'default'
    if is_news_theme_name(base_dir, httpd.theme_name):
        news_instance = True

    httpd.news_instance = news_instance
    httpd.default_timeline = 'inbox'
    if media_instance:
        httpd.default_timeline = 'tlmedia'
    if blogs_instance:
        httpd.default_timeline = 'tlblogs'
    if news_instance:
        httpd.default_timeline = 'tlfeatures'

    set_news_avatar(base_dir,
                    httpd.theme_name,
                    http_prefix,
                    domain,
                    httpd.domain_full)

    if not os.path.isdir(base_dir + '/cache'):
        os.mkdir(base_dir + '/cache')
    if not os.path.isdir(base_dir + '/cache/actors'):
        print('Creating actors cache')
        os.mkdir(base_dir + '/cache/actors')
    if not os.path.isdir(base_dir + '/cache/announce'):
        print('Creating announce cache')
        os.mkdir(base_dir + '/cache/announce')
    if not os.path.isdir(base_dir + '/cache/avatars'):
        print('Creating avatars cache')
        os.mkdir(base_dir + '/cache/avatars')

    archive_dir = base_dir + '/archive'
    if not os.path.isdir(archive_dir):
        print('Creating archive')
        os.mkdir(archive_dir)

    if not os.path.isdir(base_dir + '/sharefiles'):
        print('Creating shared item files directory')
        os.mkdir(base_dir + '/sharefiles')

    print('Creating fitness thread')
    httpd.thrFitness = \
        thread_with_trace(target=fitness_thread,
                          args=(base_dir, httpd.fitness), daemon=True)
    httpd.thrFitness.start()

    print('Creating cache expiry thread')
    httpd.thrCache = \
        thread_with_trace(target=expire_cache,
                          args=(base_dir, httpd.person_cache,
                                httpd.http_prefix,
                                archive_dir,
                                httpd.maxPostsInBox), daemon=True)
    httpd.thrCache.start()

    # number of mins after which sending posts or updates will expire
    httpd.send_threads_timeout_mins = send_threads_timeout_mins

    print('Creating posts queue')
    httpd.thrPostsQueue = \
        thread_with_trace(target=run_posts_queue,
                          args=(base_dir, httpd.send_threads, debug,
                                httpd.send_threads_timeout_mins), daemon=True)
    if not unit_test:
        httpd.thrPostsWatchdog = \
            thread_with_trace(target=run_posts_watchdog,
                              args=(project_version, httpd), daemon=True)
        httpd.thrPostsWatchdog.start()
    else:
        httpd.thrPostsQueue.start()

    print('Creating expire thread for shared items')
    httpd.thrSharesExpire = \
        thread_with_trace(target=run_shares_expire,
                          args=(project_version, base_dir), daemon=True)
    if not unit_test:
        httpd.thrSharesExpireWatchdog = \
            thread_with_trace(target=run_shares_expire_watchdog,
                              args=(project_version, httpd), daemon=True)
        httpd.thrSharesExpireWatchdog.start()
    else:
        httpd.thrSharesExpire.start()

    httpd.recent_posts_cache = {}
    httpd.max_recent_posts = max_recent_posts
    httpd.iconsCache = {}
    httpd.fontsCache = {}

    # create tokens used for shared item federation
    fed_domains = httpd.shared_items_federated_domains
    httpd.sharedItemFederationTokens = \
        generate_shared_item_federation_tokens(fed_domains,
                                               base_dir)
    httpd.sharedItemFederationTokens = \
        create_shared_item_federation_token(base_dir, httpd.domain_full, False,
                                            httpd.sharedItemFederationTokens)

    # load peertube instances from file into a list
    httpd.peertube_instances = []
    load_peertube_instances(base_dir, httpd.peertube_instances)

    create_initial_last_seen(base_dir, http_prefix)

    print('Creating inbox queue')
    httpd.thrInboxQueue = \
        thread_with_trace(target=run_inbox_queue,
                          args=(httpd.recent_posts_cache,
                                httpd.max_recent_posts,
                                project_version,
                                base_dir, http_prefix, httpd.send_threads,
                                httpd.postLog, httpd.cached_webfingers,
                                httpd.person_cache, httpd.inbox_queue,
                                domain, onion_domain, i2p_domain,
                                port, proxy_type,
                                httpd.federation_list,
                                max_replies,
                                domain_max_posts_per_day,
                                account_max_posts_per_day,
                                allow_deletion, debug,
                                max_mentions, max_emoji,
                                httpd.translate, unit_test,
                                httpd.yt_replace_domain,
                                httpd.twitter_replacement_domain,
                                httpd.show_published_date_only,
                                httpd.max_followers,
                                httpd.allow_local_network_access,
                                httpd.peertube_instances,
                                verify_all_signatures,
                                httpd.theme_name,
                                httpd.system_language,
                                httpd.max_like_count,
                                httpd.signing_priv_key_pem,
                                httpd.default_reply_interval_hrs,
                                httpd.cw_lists), daemon=True)

    print('Creating scheduled post thread')
    httpd.thrPostSchedule = \
        thread_with_trace(target=run_post_schedule,
                          args=(base_dir, httpd, 20), daemon=True)

    print('Creating newswire thread')
    httpd.thrNewswireDaemon = \
        thread_with_trace(target=run_newswire_daemon,
                          args=(base_dir, httpd,
                                http_prefix, domain, port,
                                httpd.translate), daemon=True)

    print('Creating federated shares thread')
    httpd.thrFederatedSharesDaemon = \
        thread_with_trace(target=run_federated_shares_daemon,
                          args=(base_dir, httpd,
                                http_prefix, httpd.domain_full,
                                proxy_type, debug,
                                httpd.system_language), daemon=True)

    # flags used when restarting the inbox queue
    httpd.restartInboxQueueInProgress = False
    httpd.restartInboxQueue = False

    update_hashtag_categories(base_dir)

    print('Adding hashtag categories for language ' + httpd.system_language)
    load_hashtag_categories(base_dir, httpd.system_language)

    # signing key used for authorized fetch
    # this is the instance actor private key
    httpd.signing_priv_key_pem = get_instance_actor_key(base_dir, domain)

    if not unit_test:
        print('Creating inbox queue watchdog')
        httpd.thrWatchdog = \
            thread_with_trace(target=run_inbox_queue_watchdog,
                              args=(project_version, httpd), daemon=True)
        httpd.thrWatchdog.start()

        print('Creating scheduled post watchdog')
        httpd.thrWatchdogSchedule = \
            thread_with_trace(target=run_post_schedule_watchdog,
                              args=(project_version, httpd), daemon=True)
        httpd.thrWatchdogSchedule.start()

        print('Creating newswire watchdog')
        httpd.thrNewswireWatchdog = \
            thread_with_trace(target=run_newswire_watchdog,
                              args=(project_version, httpd), daemon=True)
        httpd.thrNewswireWatchdog.start()

        print('Creating federated shares watchdog')
        httpd.thrFederatedSharesWatchdog = \
            thread_with_trace(target=run_federated_shares_watchdog,
                              args=(project_version, httpd), daemon=True)
        httpd.thrFederatedSharesWatchdog.start()
    else:
        print('Starting inbox queue')
        httpd.thrInboxQueue.start()
        print('Starting scheduled posts daemon')
        httpd.thrPostSchedule.start()
        print('Starting federated shares daemon')
        httpd.thrFederatedSharesDaemon.start()

    if client_to_server:
        print('Running ActivityPub client on ' +
              domain + ' port ' + str(proxy_port))
    else:
        print('Running ActivityPub server on ' +
              domain + ' port ' + str(proxy_port))
    httpd.serve_forever()
