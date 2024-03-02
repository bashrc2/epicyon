__filename__ = "daemon_get.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import time
import json
import datetime
import urllib.parse
from shutil import copyfile
from mastoapiv1 import masto_api_v1_response
from mastoapiv2 import masto_api_v2_response
from relationships import get_inactive_feed
from relationships import get_moved_feed
from skills import get_skills_from_list
from skills import no_of_actor_skills
from city import get_spoofed_city
from roles import get_actor_roles_list
from languages import get_understood_languages
from languages import get_reply_language
from bookmarks import undo_bookmark_post
from bookmarks import bookmark_post
from reaction import update_reaction_collection
from like import update_likes_collection
from manualapprove import manual_deny_follow_request_thread
from manualapprove import manual_approve_follow_request_thread
from announce import create_announce
from webfinger import webfinger_lookup
from webfinger import webfinger_node_info
from webfinger import webfinger_meta
from webfinger import wellknown_protocol_handler
from media import path_is_video
from media import path_is_transcript
from media import path_is_audio
from context import get_individual_post_context
from newswire import rss2header
from newswire import get_rs_sfrom_dict
from newswire import rss2footer
from pgp import actor_to_vcard
from pgp import actor_to_vcard_xml
from siteactive import referer_is_active
from metadata import meta_data_node_info
from maps import map_format_from_tagmaps_path
from blog import html_blog_page
from blog import html_blog_page_rss2
from blog import html_blog_page_rss3
from blog import html_edit_blog
from blog import html_blog_post
from blog import path_contains_blog_link
from blog import html_blog_view
from speaker import get_ssml_box
from follow import follower_approval_active
from follow import pending_followers_timeline_json
from follow import get_following_feed
from blocking import unmute_post
from blocking import mute_post
from blocking import is_blocked_hashtag
from blocking import export_blocking_file
from blocking import broch_mode_is_active
from blocking import remove_global_block
from blocking import update_blocked_cache
from blocking import add_global_block
from blocking import blocked_timeline_json
from cache import get_person_from_cache
from webapp_create_post import html_new_post
from webapp_profile import html_profile
from webapp_profile import html_edit_profile
from webapp_conversation import html_conversation_view
from webapp_pwa import pwa_manifest
from webapp_moderation import html_moderation
from webapp_moderation import html_account_info
from webapp_calendar import html_calendar_delete_confirm
from webapp_calendar import html_calendar
from webapp_hashtagswarm import get_hashtag_categories_feed
from webapp_hashtagswarm import html_search_hashtag_category
from webapp_minimalbutton import set_minimal
from webapp_minimalbutton import is_minimal
from webapp_search import hashtag_search_json
from webapp_search import html_hashtag_search
from webapp_search import hashtag_search_rss
from webapp_search import html_search_emoji_text_entry
from webapp_search import html_search
from webapp_search import html_hashtag_search_remote
from webapp_column_left import html_edit_links
from webapp_column_left import html_links_mobile
from webapp_column_right import html_edit_news_post
from webapp_column_right import html_edit_newswire
from webapp_column_right import html_newswire_mobile
from webapp_timeline import html_outbox
from webapp_timeline import html_bookmarks
from webapp_timeline import html_wanted
from webapp_timeline import html_shares
from webapp_timeline import html_inbox_features
from webapp_timeline import html_inbox_news
from webapp_timeline import html_inbox_blogs
from webapp_timeline import html_inbox_media
from webapp_timeline import html_inbox_replies
from webapp_timeline import html_inbox_dms
from webapp_timeline import html_inbox
from webapp_theme_designer import html_theme_designer
from webapp_accesskeys import html_access_keys
from webapp_manual import html_manual
from webapp_specification import html_specification
from webapp_about import html_about
from webapp_tos import html_terms_of_service
from webapp_confirm import html_confirm_delete
from webapp_confirm import html_confirm_remove_shared_item
from webapp_welcome_profile import html_welcome_profile
from webapp_welcome_final import html_welcome_final
from webapp_welcome import html_welcome_screen
from webapp_welcome import is_welcome_screen_complete
from webapp_podcast import html_podcast_episode
from webapp_utils import html_hashtag_blocked
from webapp_utils import get_default_path
from webapp_utils import csv_following_list
from webapp_utils import get_shares_collection
from webapp_utils import html_following_list
from webapp_utils import html_show_share
from webapp_likers import html_likers_of_post
from webapp_login import html_login
from webapp_post import html_individual_post
from webapp_post import html_post_replies
from webapp_post import html_emoji_reaction_picker
from webapp_post import individual_post_as_html
from followerSync import update_followers_sync_cache
from securemode import secure_mode
from fitnessFunctions import sorted_watch_points
from fitnessFunctions import fitness_performance
from fitnessFunctions import html_watch_points_graph
from session import establish_session
from session import get_session_for_domains
from crawlers import update_known_crawlers
from crawlers import blocked_user_agent
from daemon_utils import post_to_outbox
from daemon_utils import etag_exists
from daemon_utils import has_accept
from daemon_utils import show_person_options
from daemon_utils import is_authorized
from daemon_utils import get_user_agent
from httpheaders import set_headers_etag
from httpheaders import login_headers
from httpheaders import redirect_headers
from httprequests import request_icalendar
from httprequests import request_ssml
from httprequests import request_csv
from httprequests import request_http
from httpheaders import set_headers
from httpheaders import logout_headers
from httpheaders import logout_redirect
from httpcodes import http_200
from httpcodes import http_401
from httpcodes import http_402
from httpcodes import http_403
from httpcodes import http_404
from httpcodes import http_304
from httpcodes import http_400
from httpcodes import http_503
from httpcodes import write2
from utils import is_public_post
from utils import is_editor
from utils import get_occupation_skills
from utils import is_public_post_from_url
from utils import can_reply_to
from utils import get_new_post_endpoints
from utils import undo_reaction_collection_entry
from utils import undo_likes_collection_entry
from utils import get_full_domain
from utils import get_domain_from_actor
from utils import save_json
from utils import delete_post
from utils import locate_post
from utils import is_dm
from utils import get_cached_post_filename
from utils import get_image_mime_type
from utils import get_image_extensions
from utils import is_account_dir
from utils import get_css
from utils import binary_is_image
from utils import get_config_param
from utils import user_agent_domain
from utils import local_network_host
from utils import permitted_dir
from utils import has_users_path
from utils import media_file_mime_type
from utils import is_image_file
from utils import is_artist
from utils import is_blog_post
from utils import replace_users_with_at
from utils import remove_id_ending
from utils import local_actor_url
from utils import load_json
from utils import acct_dir
from utils import get_instance_url
from utils import convert_domains
from utils import get_nickname_from_actor
from utils import get_json_content_from_accept
from utils import check_bad_path
from utils import corp_servers
from utils import decoded_host
from utils import has_object_dict
from person import add_alternate_domains
from person import person_box_json
from person import save_person_qrcode
from person import person_lookup
from person import get_account_pub_key
from shares import get_shares_feed_for_person
from shares import actor_attached_shares
from shares import get_share_category
from shares import vf_proposal_from_id
from shares import authorize_shared_items
from shares import shares_catalog_endpoint
from shares import shares_catalog_account_endpoint
from shares import shares_catalog_csv_endpoint
from posts import remove_post_interactions
from posts import populate_replies_json
from posts import get_original_post_from_announce_url
from posts import save_post_to_box
from posts import json_pin_post
from posts import is_moderator
from posts import get_pinned_post_as_json
from posts import outbox_message_create_wrap

# Blogs can be longer, so don't show many per page
MAX_POSTS_IN_BLOGS_FEED = 4

# maximum number of posts to list in outbox feed
MAX_POSTS_IN_FEED = 12

# Maximum number of entries in returned rss.xml
MAX_POSTS_IN_RSS_FEED = 10

# reduced posts for media feed because it can take a while
MAX_POSTS_IN_MEDIA_FEED = 6

MAX_POSTS_IN_NEWS_FEED = 10

# number of item shares per page
SHARES_PER_PAGE = 12

# number of follows/followers per page
FOLLOWS_PER_PAGE = 6

# maximum number of posts in a hashtag feed
MAX_POSTS_IN_HASHTAG_FEED = 6


def daemon_http_get(self) -> None:
    """daemon handler for http GET
    """
    if self.server.starting_daemon:
        return
    if check_bad_path(self.path):
        http_400(self)
        return

    calling_domain = self.server.domain_full

    if self.headers.get('Server'):
        if self.headers['Server'] in corp_servers():
            if self.server.debug:
                print('Corporate leech bounced: ' + self.headers['Server'])
            http_402(self)
            return

    if self.headers.get('Host'):
        calling_domain = decoded_host(self.headers['Host'])
        if self.server.onion_domain:
            if calling_domain not in (self.server.domain,
                                      self.server.domain_full,
                                      self.server.onion_domain):
                print('GET domain blocked: ' + calling_domain)
                http_400(self)
                return
        elif self.server.i2p_domain:
            if calling_domain not in (self.server.domain,
                                      self.server.domain_full,
                                      self.server.i2p_domain):
                print('GET domain blocked: ' + calling_domain)
                http_400(self)
                return
        else:
            if calling_domain not in (self.server.domain,
                                      self.server.domain_full):
                print('GET domain blocked: ' + calling_domain)
                http_400(self)
                return

    ua_str = get_user_agent(self)

    if not _permitted_crawler_path(self, self.path):
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
            return

    referer_domain = _get_referer_domain(self, ua_str)

    curr_session, proxy_type = \
        get_session_for_domains(self.server,
                                calling_domain, referer_domain)

    getreq_start_time = time.time()

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'start', self.server.debug)

    if _show_vcard(self, self.server.base_dir,
                   self.path, calling_domain, referer_domain,
                   self.server.domain):
        return

    # getting the public key for an account
    acct_pub_key_json = \
        get_account_pub_key(self.path, self.server.person_cache,
                            self.server.base_dir,
                            self.server.domain, calling_domain,
                            self.server.http_prefix,
                            self.server.domain_full,
                            self.server.onion_domain,
                            self.server.i2p_domain)
    if acct_pub_key_json:
        msg_str = json.dumps(acct_pub_key_json, ensure_ascii=False)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        accept_str = self.headers['Accept']
        protocol_str = \
            get_json_content_from_accept(accept_str)
        set_headers(self, protocol_str, msglen,
                    None, calling_domain, False)
        write2(self, msg)
        return

    # Since fediverse crawlers are quite active,
    # make returning info to them high priority
    # get nodeinfo endpoint
    if _nodeinfo(self, ua_str, calling_domain, referer_domain,
                 self.server.http_prefix, 5, self.server.debug):
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_nodeinfo[calling_domain]',
                        self.server.debug)

    if _security_txt(self, ua_str, calling_domain, referer_domain,
                     self.server.http_prefix, 5, self.server.debug):
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_security_txt[calling_domain]',
                        self.server.debug)

    # followers synchronization request
    # See https://github.com/mastodon/mastodon/pull/14510
    # https://codeberg.org/fediverse/fep/src/branch/main/feps/fep-8fcf.md
    if self.path.startswith('/users/') and \
       self.path.endswith('/followers_synchronization'):
        if self.server.followers_synchronization:
            # only do one request at a time
            http_503(self)
            return
        self.server.followers_synchronization = True
        if self.server.debug:
            print('DEBUG: followers synchronization request ' +
                  self.path + ' ' + calling_domain)
        # check authorized fetch
        if secure_mode(curr_session, proxy_type, False,
                       self.server, self.headers, self.path):
            nickname = get_nickname_from_actor(self.path)
            sync_cache = self.server.followers_sync_cache
            sync_json, _ = \
                update_followers_sync_cache(self.server.base_dir,
                                            nickname,
                                            self.server.domain,
                                            self.server.http_prefix,
                                            self.server.domain_full,
                                            calling_domain,
                                            sync_cache)
            msg_str = json.dumps(sync_json, ensure_ascii=False)
            msg_str = convert_domains(calling_domain, referer_domain,
                                      msg_str,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.onion_domain,
                                      self.server.i2p_domain)
            msg = msg_str.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'application/json', msglen,
                        None, calling_domain, False)
            write2(self, msg)
            self.server.followers_synchronization = False
            return
        else:
            # request was not signed
            result_json = {
                "error": "Request not signed"
            }
            msg_str = json.dumps(result_json, ensure_ascii=False)
            msg = msg_str.encode('utf-8')
            msglen = len(msg)
            accept_str = self.headers['Accept']
            if 'json' in accept_str:
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                self.server.followers_synchronization = False
                return
        http_404(self, 110)
        self.server.followers_synchronization = False
        return

    if self.path == '/logout':
        if not self.server.news_instance:
            msg = \
                html_login(self.server.translate,
                           self.server.base_dir,
                           self.server.http_prefix,
                           self.server.domain_full,
                           self.server.system_language,
                           False, ua_str,
                           self.server.theme_name).encode('utf-8')
            msglen = len(msg)
            logout_headers(self, 'text/html', msglen, calling_domain)
            write2(self, msg)
        else:
            news_url = \
                get_instance_url(calling_domain,
                                 self.server.http_prefix,
                                 self.server.domain_full,
                                 self.server.onion_domain,
                                 self.server.i2p_domain) + \
                '/users/news'
            logout_redirect(self, news_url, calling_domain)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'logout',
                            self.server.debug)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show logout',
                        self.server.debug)

    # replace https://domain/@nick with https://domain/users/nick
    if self.path.startswith('/@'):
        self.path = self.path.replace('/@', '/users/')
        # replace https://domain/@nick/statusnumber
        # with https://domain/users/nick/statuses/statusnumber
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            status_number_str = nickname.split('/')[1]
            if status_number_str.isdigit():
                nickname = nickname.split('/')[0]
                self.path = \
                    self.path.replace('/users/' + nickname + '/',
                                      '/users/' + nickname + '/statuses/')

    # instance actor
    if self.path in ('/actor', '/users/instance.actor', '/users/actor',
                     '/Actor', '/users/Actor'):
        self.path = '/users/inbox'
        if _show_instance_actor(self, calling_domain, referer_domain,
                                self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domain_full,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                getreq_start_time,
                                None, self.server.debug,
                                self.server.enable_shared_inbox):
            return
        else:
            http_404(self, 111)
            return

    # turn off dropdowns on new post screen
    no_drop_down = False
    if self.path.endswith('?nodropdown'):
        no_drop_down = True
        self.path = self.path.replace('?nodropdown', '')

    # redirect music to #nowplaying list
    if self.path == '/music' or self.path == '/NowPlaying':
        self.path = '/tags/NowPlaying'

    if self.server.debug:
        print('DEBUG: GET from ' + self.server.base_dir +
              ' path: ' + self.path + ' busy: ' +
              str(self.server.getreq_busy))

    if self.server.debug:
        print(str(self.headers))

    cookie = None
    if self.headers.get('Cookie'):
        cookie = self.headers['Cookie']

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'get cookie',
                        self.server.debug)

    if '/manifest.json' in self.path:
        if has_accept(self, calling_domain):
            if not request_http(self.headers, self.server.debug):
                _progressive_web_app_manifest(self, self.server.base_dir,
                                              calling_domain,
                                              referer_domain,
                                              getreq_start_time)
                return
            else:
                self.path = '/'

    if '/browserconfig.xml' in self.path:
        if has_accept(self, calling_domain):
            _browser_config(self, calling_domain, referer_domain,
                            getreq_start_time)
            return

    # default newswire favicon, for links to sites which
    # have no favicon
    if not self.path.startswith('/favicons/'):
        if 'newswire_favicon.ico' in self.path:
            _get_favicon(self, calling_domain, self.server.base_dir,
                         self.server.debug,
                         'newswire_favicon.ico')
            return

        # favicon image
        if 'favicon.ico' in self.path:
            _get_favicon(self, calling_domain, self.server.base_dir,
                         self.server.debug, 'favicon.ico')
            return

    # check authorization
    authorized = is_authorized(self)
    if self.server.debug:
        if authorized:
            print('GET Authorization granted ' + self.path)
        else:
            print('GET Not authorized ' + self.path + ' ' +
                  str(self.headers))

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'isAuthorized',
                        self.server.debug)

    if authorized and self.path.endswith('/bots.txt'):
        known_bots_str = ''
        for bot_name in self.server.known_bots:
            known_bots_str += bot_name + '\n'
        msg = known_bots_str.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/plain; charset=utf-8',
                    msglen, None, calling_domain, True)
        write2(self, msg)
        if self.server.debug:
            print('Sent known bots: ' +
                  self.server.path + ' ' + calling_domain)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'get_known_bots',
                            self.server.debug)
        return

    if _show_conversation_thread(self, authorized,
                                 calling_domain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.port,
                                 self.server.debug,
                                 self.server.session,
                                 cookie):
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_conversation_thread',
                            self.server.debug)
        return

    # show a shared item if it is listed within actor attachment
    if self.path.startswith('/users/') and '/shareditems/' in self.path:
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        shared_item_display_name = self.path.split('/shareditems/')[1]
        if not nickname or not shared_item_display_name:
            http_404(self, 112)
            return
        if not has_accept(self, calling_domain):
            print('DEBUG: shareditems 1')
            http_404(self, 113)
            return
        # get the actor from the cache
        actor = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            '/users/' + nickname
        actor_json = get_person_from_cache(self.server.base_dir, actor,
                                           self.server.person_cache)
        if not actor_json:
            actor_filename = acct_dir(self.server.base_dir, nickname,
                                      self.server.domain) + '.json'
            if os.path.isfile(actor_filename):
                actor_json = load_json(actor_filename, 1, 1)
        if not actor_json:
            print('DEBUG: shareditems 2 ' + actor)
            http_404(self, 114)
            return
        attached_shares = actor_attached_shares(actor_json)
        if not attached_shares:
            print('DEBUG: shareditems 3 ' + str(actor_json['attachment']))
            http_404(self, 115)
            return
        # is the given shared item in the list?
        share_id = None
        for share_href in attached_shares:
            if not isinstance(share_href, str):
                continue
            if share_href.endswith(self.path):
                share_id = share_href.replace('://', '___')
                share_id = share_id.replace('/', '--')
                break
        if not share_id:
            print('DEBUG: shareditems 4')
            http_404(self, 116)
            return
        # show the shared item
        print('DEBUG: shareditems 5 ' + share_id)
        shares_file_type = 'shares'
        if request_http(self.headers, self.server.debug):
            # get the category for share_id
            share_category = \
                get_share_category(self.server.base_dir,
                                   nickname, self.server.domain,
                                   shares_file_type, share_id)
            msg = \
                html_show_share(self.server.base_dir,
                                self.server.domain, nickname,
                                self.server.http_prefix,
                                self.server.domain_full,
                                share_id, self.server.translate,
                                self.server.shared_items_federated_domains,
                                self.server.default_timeline,
                                self.server.theme_name, shares_file_type,
                                share_category, not authorized)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            None, calling_domain, True)
                write2(self, msg)
                return
            else:
                print('DEBUG: shareditems 6 ' + share_id)
        else:
            # get json for the shared item in ValueFlows format
            share_json = \
                vf_proposal_from_id(self.server.base_dir,
                                    nickname, self.server.domain,
                                    shares_file_type, share_id,
                                    actor)
            if share_json:
                msg_str = json.dumps(share_json)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'application/json', msglen,
                            None, calling_domain, True)
                write2(self, msg)
                return
            else:
                print('DEBUG: shareditems 7 ' + share_id)
        http_404(self, 117)
        return

    # shared items offers collection for this instance
    # this is only accessible to instance members or to
    # other instances which present an authorization token
    if self.path.startswith('/users/') and '/offers' in self.path:
        offers_collection_authorized = authorized
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        page_number = 1
        if '?page=' in self.path:
            page_number_str = self.path.split('?page=')[1]
            if ';' in page_number_str:
                page_number_str = page_number_str.split(';')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        if not offers_collection_authorized:
            if self.server.debug:
                print('Offers collection access is not authorized. ' +
                      'Checking Authorization header')
            # Check the authorization token
            if self.headers.get('Origin') and \
               self.headers.get('Authorization'):
                permitted_domains = \
                    self.server.shared_items_federated_domains
                shared_item_tokens = \
                    self.server.shared_item_federation_tokens
                if authorize_shared_items(permitted_domains,
                                          self.server.base_dir,
                                          self.headers['Origin'],
                                          calling_domain,
                                          self.headers['Authorization'],
                                          self.server.debug,
                                          shared_item_tokens):
                    offers_collection_authorized = True
                elif self.server.debug:
                    print('Authorization token refused for ' +
                          'offers collection federation')
        # show offers collection for federation
        offers_json = []
        if has_accept(self, calling_domain) and \
           offers_collection_authorized:
            if self.server.debug:
                print('Preparing offers collection')

            domain_full = self.server.domain_full
            http_prefix = self.server.http_prefix
            if self.server.debug:
                print('Offers collection for account: ' + nickname)
            base_dir = self.server.base_dir
            offers_items_per_page = 12
            max_shares_per_account = offers_items_per_page
            shared_items_federated_domains = \
                self.server.shared_items_federated_domains
            actor = \
                local_actor_url(http_prefix, nickname, domain_full) + \
                '/offers'
            offers_json = \
                get_shares_collection(actor, page_number,
                                      offers_items_per_page, base_dir,
                                      self.server.domain, nickname,
                                      max_shares_per_account,
                                      shared_items_federated_domains,
                                      'shares')
        msg_str = json.dumps(offers_json,
                             ensure_ascii=False)
        msg_str = convert_domains(calling_domain,
                                  referer_domain,
                                  msg_str,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        accept_str = self.headers['Accept']
        protocol_str = \
            get_json_content_from_accept(accept_str)
        set_headers(self, protocol_str, msglen,
                    None, calling_domain, False)
        write2(self, msg)
        return

    if self.path.startswith('/users/') and '/blocked' in self.path:
        blocked_collection_authorized = authorized
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        page_number = 1
        if '?page=' in self.path:
            page_number_str = self.path.split('?page=')[1]
            if ';' in page_number_str:
                page_number_str = page_number_str.split(';')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        # show blocked collection for the nickname
        actor = \
            local_actor_url(self.server.http_prefix,
                            nickname, self.server.domain_full)
        actor += '/blocked'
        blocked_json = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://purl.archive.org/socialweb/blocked"
            ],
            "id": actor,
            "type": "OrderedCollection",
            "name": nickname + "'s Blocked Collection",
            "orderedItems": []
        }
        if has_accept(self, calling_domain) and \
           blocked_collection_authorized:
            if self.server.debug:
                print('Preparing blocked collection')

            if self.server.debug:
                print('Blocked collection for account: ' + nickname)
            base_dir = self.server.base_dir
            blocked_items_per_page = 12
            blocked_json = \
                blocked_timeline_json(actor, page_number,
                                      blocked_items_per_page, base_dir,
                                      nickname, self.server.domain)
        msg_str = json.dumps(blocked_json,
                             ensure_ascii=False)
        msg_str = convert_domains(calling_domain,
                                  referer_domain,
                                  msg_str,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        accept_str = self.headers['Accept']
        protocol_str = \
            get_json_content_from_accept(accept_str)
        set_headers(self, protocol_str, msglen,
                    None, calling_domain, False)
        write2(self, msg)
        return

    if self.path.startswith('/users/') and \
       '/pendingFollowers' in self.path:
        pending_collection_authorized = authorized
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        page_number = 1
        if '?page=' in self.path:
            page_number_str = self.path.split('?page=')[1]
            if ';' in page_number_str:
                page_number_str = page_number_str.split(';')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        # show pending followers collection for the nickname
        actor = \
            local_actor_url(self.server.http_prefix,
                            nickname, self.server.domain_full)
        actor += '/pendingFollowers'
        pending_json = {
            "@context": [
                "https://www.w3.org/ns/activitystreams"
            ],
            "id": actor,
            "type": "OrderedCollection",
            "name": nickname + "'s Pending Followers",
            "orderedItems": []
        }
        if has_accept(self, calling_domain) and \
           pending_collection_authorized:
            if self.server.debug:
                print('Preparing pending followers collection')

            if self.server.debug:
                print('Pending followers collection for account: ' +
                      nickname)
            base_dir = self.server.base_dir
            pending_json = \
                pending_followers_timeline_json(actor, base_dir, nickname,
                                                self.server.domain)
        msg_str = json.dumps(pending_json,
                             ensure_ascii=False)
        msg_str = convert_domains(calling_domain,
                                  referer_domain,
                                  msg_str,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        accept_str = self.headers['Accept']
        protocol_str = \
            get_json_content_from_accept(accept_str)
        set_headers(self, protocol_str, msglen,
                    None, calling_domain, False)
        write2(self, msg)
        return

    # wanted items collection for this instance
    # this is only accessible to instance members or to
    # other instances which present an authorization token
    if self.path.startswith('/users/') and '/wanted' in self.path:
        wanted_collection_authorized = authorized
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        page_number = 1
        if '?page=' in self.path:
            page_number_str = self.path.split('?page=')[1]
            if ';' in page_number_str:
                page_number_str = page_number_str.split(';')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)
        if not wanted_collection_authorized:
            if self.server.debug:
                print('Wanted collection access is not authorized. ' +
                      'Checking Authorization header')
            # Check the authorization token
            if self.headers.get('Origin') and \
               self.headers.get('Authorization'):
                permitted_domains = \
                    self.server.shared_items_federated_domains
                shared_item_tokens = \
                    self.server.shared_item_federation_tokens
                if authorize_shared_items(permitted_domains,
                                          self.server.base_dir,
                                          self.headers['Origin'],
                                          calling_domain,
                                          self.headers['Authorization'],
                                          self.server.debug,
                                          shared_item_tokens):
                    wanted_collection_authorized = True
                elif self.server.debug:
                    print('Authorization token refused for ' +
                          'wanted collection federation')
        # show wanted collection for federation
        wanted_json = []
        if has_accept(self, calling_domain) and \
           wanted_collection_authorized:
            if self.server.debug:
                print('Preparing wanted collection')

            domain_full = self.server.domain_full
            http_prefix = self.server.http_prefix
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if self.server.debug:
                print('Wanted collection for account: ' + nickname)
            base_dir = self.server.base_dir
            wanted_items_per_page = 12
            max_shares_per_account = wanted_items_per_page
            shared_items_federated_domains = \
                self.server.shared_items_federated_domains
            actor = \
                local_actor_url(http_prefix, nickname, domain_full) + \
                '/wanted'
            wanted_json = \
                get_shares_collection(actor, page_number,
                                      wanted_items_per_page, base_dir,
                                      self.server.domain, nickname,
                                      max_shares_per_account,
                                      shared_items_federated_domains,
                                      'wanted')
        msg_str = json.dumps(wanted_json,
                             ensure_ascii=False)
        msg_str = convert_domains(calling_domain,
                                  referer_domain,
                                  msg_str,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        accept_str = self.headers['Accept']
        protocol_str = \
            get_json_content_from_accept(accept_str)
        set_headers(self, protocol_str, msglen,
                    None, calling_domain, False)
        write2(self, msg)
        return

    # shared items catalog for this instance
    # this is only accessible to instance members or to
    # other instances which present an authorization token
    if self.path.startswith('/catalog') or \
       (self.path.startswith('/users/') and '/catalog' in self.path):
        catalog_authorized = authorized
        if not catalog_authorized:
            if self.server.debug:
                print('Catalog access is not authorized. ' +
                      'Checking Authorization header')
            # Check the authorization token
            if self.headers.get('Origin') and \
               self.headers.get('Authorization'):
                permitted_domains = \
                    self.server.shared_items_federated_domains
                shared_item_tokens = \
                    self.server.shared_item_federation_tokens
                if authorize_shared_items(permitted_domains,
                                          self.server.base_dir,
                                          self.headers['Origin'],
                                          calling_domain,
                                          self.headers['Authorization'],
                                          self.server.debug,
                                          shared_item_tokens):
                    catalog_authorized = True
                elif self.server.debug:
                    print('Authorization token refused for ' +
                          'shared items federation')
            elif self.server.debug:
                print('No Authorization header is available for ' +
                      'shared items federation')
        # show shared items catalog for federation
        if has_accept(self, calling_domain) and catalog_authorized:
            catalog_type = 'json'
            headers = self.headers
            debug = self.server.debug
            if self.path.endswith('.csv') or request_csv(headers):
                catalog_type = 'csv'
            elif (self.path.endswith('.json') or
                  not request_http(headers, debug)):
                catalog_type = 'json'
            if self.server.debug:
                print('Preparing DFC catalog in format ' + catalog_type)

            if catalog_type == 'json':
                # catalog as a json
                if not self.path.startswith('/users/'):
                    if self.server.debug:
                        print('Catalog for the instance')
                    catalog_json = \
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
                    catalog_json = \
                        shares_catalog_account_endpoint(base_dir,
                                                        http_prefix,
                                                        nickname,
                                                        self.server.domain,
                                                        domain_full,
                                                        self.path,
                                                        self.server.debug,
                                                        'shares')
                msg_str = json.dumps(catalog_json,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                return
            elif catalog_type == 'csv':
                # catalog as a CSV file for import into a spreadsheet
                msg = \
                    shares_catalog_csv_endpoint(self.server.base_dir,
                                                self.server.http_prefix,
                                                self.server.domain_full,
                                                self.path,
                                                'shares').encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/csv',
                            msglen, None, calling_domain, False)
                write2(self, msg)
                return
            http_404(self, 118)
            return
        http_400(self)
        return

    # wanted items catalog for this instance
    # this is only accessible to instance members or to
    # other instances which present an authorization token
    if self.path.startswith('/wantedItems') or \
       (self.path.startswith('/users/') and '/wantedItems' in self.path):
        catalog_authorized = authorized
        if not catalog_authorized:
            if self.server.debug:
                print('Wanted catalog access is not authorized. ' +
                      'Checking Authorization header')
            # Check the authorization token
            if self.headers.get('Origin') and \
               self.headers.get('Authorization'):
                permitted_domains = \
                    self.server.shared_items_federated_domains
                shared_item_tokens = \
                    self.server.shared_item_federation_tokens
                if authorize_shared_items(permitted_domains,
                                          self.server.base_dir,
                                          self.headers['Origin'],
                                          calling_domain,
                                          self.headers['Authorization'],
                                          self.server.debug,
                                          shared_item_tokens):
                    catalog_authorized = True
                elif self.server.debug:
                    print('Authorization token refused for ' +
                          'wanted items federation')
            elif self.server.debug:
                print('No Authorization header is available for ' +
                      'wanted items federation')
        # show wanted items catalog for federation
        if has_accept(self, calling_domain) and catalog_authorized:
            catalog_type = 'json'
            headers = self.headers
            debug = self.server.debug
            if self.path.endswith('.csv') or request_csv(headers):
                catalog_type = 'csv'
            elif (self.path.endswith('.json') or
                  not request_http(headers, debug)):
                catalog_type = 'json'
            if self.server.debug:
                print('Preparing DFC wanted catalog in format ' +
                      catalog_type)

            if catalog_type == 'json':
                # catalog as a json
                if not self.path.startswith('/users/'):
                    if self.server.debug:
                        print('Wanted catalog for the instance')
                    catalog_json = \
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
                    catalog_json = \
                        shares_catalog_account_endpoint(base_dir,
                                                        http_prefix,
                                                        nickname,
                                                        self.server.domain,
                                                        domain_full,
                                                        self.path,
                                                        self.server.debug,
                                                        'wanted')
                msg_str = json.dumps(catalog_json,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                return
            elif catalog_type == 'csv':
                # catalog as a CSV file for import into a spreadsheet
                msg = \
                    shares_catalog_csv_endpoint(self.server.base_dir,
                                                self.server.http_prefix,
                                                self.server.domain_full,
                                                self.path,
                                                'wanted').encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/csv',
                            msglen, None, calling_domain, False)
                write2(self, msg)
                return
            http_404(self, 119)
            return
        http_400(self)
        return

    # minimal mastodon api
    if _masto_api(self, self.path, calling_domain, ua_str,
                  authorized,
                  self.server.http_prefix,
                  self.server.base_dir,
                  self.authorized_nickname,
                  self.server.domain,
                  self.server.domain_full,
                  self.server.onion_domain,
                  self.server.i2p_domain,
                  self.server.translate,
                  self.server.registration,
                  self.server.system_language,
                  self.server.project_version,
                  self.server.custom_emoji,
                  self.server.show_node_info_accounts,
                  referer_domain,
                  self.server.debug,
                  self.server.known_crawlers,
                  self.server.sites_unavailable):
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_masto_api[calling_domain]',
                        self.server.debug)

    curr_session = \
        establish_session("GET", curr_session,
                          proxy_type, self.server)
    if not curr_session:
        http_404(self, 120)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'session fail',
                            self.server.debug)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'create session',
                        self.server.debug)

    # is this a html/ssml/icalendar request?
    html_getreq = False
    csv_getreq = False
    ssml_getreq = False
    icalendar_getreq = False
    if has_accept(self, calling_domain):
        if request_http(self.headers, self.server.debug):
            html_getreq = True
        elif request_csv(self.headers):
            csv_getreq = True
        elif request_ssml(self.headers):
            ssml_getreq = True
        elif request_icalendar(self.headers):
            icalendar_getreq = True
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
            http_200(self)
        else:
            print('WARN: No Accept header ' + str(self.headers))
            http_400(self)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'hasAccept',
                        self.server.debug)

    # cached favicon images
    # Note that this comes before the busy flag to avoid conflicts
    if self.path.startswith('/favicons/'):
        if self.server.domain_full in self.path:
            # favicon for this instance
            _get_favicon(self, calling_domain, self.server.base_dir,
                         self.server.debug, 'favicon.ico')
            return
        _show_cached_favicon(self, referer_domain, self.path,
                             self.server.base_dir,
                             getreq_start_time)
        return

    # get css
    # Note that this comes before the busy flag to avoid conflicts
    if self.path.endswith('.css'):
        if _get_style_sheet(self, self.server.base_dir,
                            calling_domain, self.path,
                            getreq_start_time):
            return

    if authorized and '/exports/' in self.path:
        if 'blocks.csv' in self.path:
            _get_exported_blocks(self, self.path,
                                 self.server.base_dir,
                                 self.server.domain,
                                 calling_domain)
        else:
            _get_exported_theme(self, self.path,
                                self.server.base_dir,
                                self.server.domain_full)
        return

    # get fonts
    if '/fonts/' in self.path:
        _get_fonts(self, calling_domain, self.path,
                   self.server.base_dir, self.server.debug,
                   getreq_start_time)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'fonts',
                        self.server.debug)

    if self.path in ('/sharedInbox', '/users/inbox', '/actor/inbox',
                     '/users/' + self.server.domain):
        # if shared inbox is not enabled
        if not self.server.enable_shared_inbox:
            http_503(self)
            return

        self.path = '/inbox'

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'sharedInbox enabled',
                        self.server.debug)

    if self.path == '/categories.xml':
        _get_hashtag_categories_feed(self, calling_domain, self.path,
                                     self.server.base_dir,
                                     proxy_type,
                                     getreq_start_time,
                                     self.server.debug,
                                     curr_session)
        return

    if self.path == '/newswire.xml':
        _get_newswire_feed(self, calling_domain, self.path,
                           proxy_type,
                           getreq_start_time,
                           self.server.debug,
                           curr_session)
        return

    # RSS 2.0
    if self.path.startswith('/blog/') and \
       self.path.endswith('/rss.xml'):
        if not self.path == '/blog/rss.xml':
            _get_rss2feed(self, calling_domain, self.path,
                          self.server.base_dir,
                          self.server.http_prefix,
                          self.server.domain,
                          self.server.port,
                          proxy_type,
                          getreq_start_time,
                          self.server.debug,
                          curr_session)
        else:
            _get_rss2site(self, calling_domain, self.path,
                          self.server.base_dir,
                          self.server.http_prefix,
                          self.server.domain_full,
                          self.server.port,
                          proxy_type,
                          self.server.translate,
                          getreq_start_time,
                          self.server.debug,
                          curr_session)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'rss2 done',
                        self.server.debug)

    # RSS 3.0
    if self.path.startswith('/blog/') and \
       self.path.endswith('/rss.txt'):
        _get_rss3feed(self, calling_domain, self.path,
                      self.server.base_dir,
                      self.server.http_prefix,
                      self.server.domain,
                      self.server.port,
                      proxy_type,
                      getreq_start_time,
                      self.server.debug,
                      self.server.system_language,
                      curr_session)
        return

    users_in_path = False
    if '/users/' in self.path:
        users_in_path = True

    if authorized and not html_getreq and users_in_path:
        if '/following?page=' in self.path:
            _get_following_json(self, self.server.base_dir,
                                self.path,
                                calling_domain, referer_domain,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.port,
                                self.server.followingItemsPerPage,
                                self.server.debug, 'following')
            return
        if '/followers?page=' in self.path:
            _get_following_json(self, self.server.base_dir,
                                self.path,
                                calling_domain, referer_domain,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.port,
                                self.server.followingItemsPerPage,
                                self.server.debug, 'followers')
            return
        if '/followrequests?page=' in self.path:
            _get_following_json(self, self.server.base_dir,
                                self.path,
                                calling_domain, referer_domain,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.port,
                                self.server.followingItemsPerPage,
                                self.server.debug,
                                'followrequests')
            return

    # authorized endpoint used for TTS of posts
    # arriving in your inbox
    if authorized and users_in_path and \
       self.path.endswith('/speaker'):
        if 'application/ssml' not in self.headers['Accept']:
            # json endpoint
            _get_speaker(self, calling_domain, referer_domain,
                         self.path,
                         self.server.base_dir,
                         self.server.domain)
        else:
            xml_str = \
                get_ssml_box(self.server.base_dir,
                             self.path, self.server.domain,
                             self.server.system_language,
                             self.server.instanceTitle,
                             'inbox')
            if xml_str:
                msg = xml_str.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'application/xrd+xml', msglen,
                            None, calling_domain, False)
                write2(self, msg)
        return

    # show a podcast episode
    if authorized and users_in_path and html_getreq and \
       '?podepisode=' in self.path:
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        episode_timestamp = self.path.split('?podepisode=')[1].strip()
        episode_timestamp = episode_timestamp.replace('__', ' ')
        episode_timestamp = episode_timestamp.replace('aa', ':')
        if self.server.newswire.get(episode_timestamp):
            pod_episode = self.server.newswire[episode_timestamp]
            html_str = \
                html_podcast_episode(self.server.translate,
                                     self.server.base_dir,
                                     nickname,
                                     self.server.domain,
                                     pod_episode,
                                     self.server.text_mode_banner,
                                     self.server.session,
                                     self.server.session_onion,
                                     self.server.session_i2p,
                                     self.server.http_prefix,
                                     self.server.debug)
            if html_str:
                msg = html_str.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            None, calling_domain, False)
                write2(self, msg)
                return

    # redirect to the welcome screen
    if html_getreq and authorized and users_in_path and \
       '/welcome' not in self.path:
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
        if nickname == self.authorized_nickname and \
           self.path != '/users/' + nickname:
            if not is_welcome_screen_complete(self.server.base_dir,
                                              nickname,
                                              self.server.domain):
                redirect_headers(self, '/users/' + nickname + '/welcome',
                                 cookie, calling_domain)
                return

    if not html_getreq and \
       users_in_path and self.path.endswith('/pinned'):
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        pinned_post_json = \
            get_pinned_post_as_json(self.server.base_dir,
                                    self.server.http_prefix,
                                    nickname, self.server.domain,
                                    self.server.domain_full,
                                    self.server.system_language)
        message_json = {}
        if pinned_post_json:
            post_id = remove_id_ending(pinned_post_json['id'])
            message_json = \
                outbox_message_create_wrap(self.server.http_prefix,
                                           nickname,
                                           self.server.domain,
                                           self.server.port,
                                           pinned_post_json)
            message_json['id'] = post_id + '/activity'
            message_json['object']['id'] = post_id
            message_json['object']['url'] = replace_users_with_at(post_id)
            message_json['object']['atomUri'] = post_id
        msg_str = json.dumps(message_json,
                             ensure_ascii=False)
        msg_str = convert_domains(calling_domain,
                                  referer_domain,
                                  msg_str,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        accept_str = self.headers['Accept']
        protocol_str = \
            get_json_content_from_accept(accept_str)
        set_headers(self, protocol_str, msglen,
                    None, calling_domain, False)
        write2(self, msg)
        return

    if not html_getreq and \
       users_in_path and self.path.endswith('/collections/featured'):
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        # return the featured posts collection
        _get_featured_collection(self, calling_domain, referer_domain,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 nickname, self.server.domain,
                                 self.server.domain_full,
                                 self.server.system_language)
        return

    if not html_getreq and \
       users_in_path and self.path.endswith('/collections/featuredTags'):
        _get_featured_tags_collection(self, calling_domain, referer_domain,
                                      self.path,
                                      self.server.http_prefix,
                                      self.server.domain_full,
                                      self.server.domain)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_get_featured_tags_collection done',
                        self.server.debug)

    # show a performance graph
    if authorized and '/performance?graph=' in self.path:
        graph = self.path.split('?graph=')[1]
        if html_getreq and not graph.endswith('.json'):
            if graph == 'post':
                graph = '_POST'
            elif graph == 'inbox':
                graph = 'INBOX'
            elif graph == 'get':
                graph = '_GET'
            msg = \
                html_watch_points_graph(self.server.base_dir,
                                        self.server.fitness,
                                        graph, 16).encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', 'graph',
                                self.server.debug)
            return
        graph = graph.replace('.json', '')
        if graph == 'post':
            graph = '_POST'
        elif graph == 'inbox':
            graph = 'INBOX'
        elif graph == 'get':
            graph = '_GET'
        watch_points_json = \
            sorted_watch_points(self.server.fitness, graph)
        msg_str = json.dumps(watch_points_json,
                             ensure_ascii=False)
        msg_str = convert_domains(calling_domain,
                                  referer_domain,
                                  msg_str,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        accept_str = self.headers['Accept']
        protocol_str = \
            get_json_content_from_accept(accept_str)
        set_headers(self, protocol_str, msglen,
                    None, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'graph json',
                            self.server.debug)
        return

    # show the main blog page
    if html_getreq and \
       self.path in ('/blog', '/blog/', '/blogs', '/blogs/'):
        if '/rss.xml' not in self.path:
            curr_session = \
                establish_session("show the main blog page",
                                  curr_session,
                                  proxy_type, self.server)
            if not curr_session:
                http_404(self, 121)
                return
            msg = html_blog_view(authorized,
                                 curr_session,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.translate,
                                 self.server.domain,
                                 self.server.port,
                                 MAX_POSTS_IN_BLOGS_FEED,
                                 self.server.peertube_instances,
                                 self.server.system_language,
                                 self.server.person_cache,
                                 self.server.debug)
            if msg is not None:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', 'blog view',
                                    self.server.debug)
                return
            http_404(self, 122)
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'blog view done',
                        self.server.debug)

    # show a particular page of blog entries
    # for a particular account
    if html_getreq and self.path.startswith('/blog/'):
        if '/rss.xml' not in self.path:
            if _show_blog_page(self, authorized,
                               calling_domain, self.path,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.port,
                               getreq_start_time,
                               proxy_type,
                               cookie, self.server.translate,
                               self.server.debug,
                               curr_session):
                return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_show_blog_page',
                        self.server.debug)

    if html_getreq and users_in_path:
        # show the person options screen with view/follow/block/report
        if '?options=' in self.path:
            show_person_options(self, calling_domain, self.path,
                                self.server.base_dir,
                                self.server.domain,
                                self.server.domain_full,
                                getreq_start_time,
                                cookie, self.server.debug,
                                authorized,
                                curr_session)
            return

        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'person options done',
                            self.server.debug)
        # show blog post
        blog_filename, nickname = \
            path_contains_blog_link(self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.domain_full,
                                    self.path)
        if blog_filename and nickname:
            post_json_object = load_json(blog_filename)
            if is_blog_post(post_json_object):
                msg = html_blog_post(curr_session,
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
                    set_headers(self, 'text/html', msglen,
                                cookie, calling_domain, False)
                    write2(self, msg)
                    fitness_performance(getreq_start_time,
                                        self.server.fitness,
                                        '_GET', 'blog post 2',
                                        self.server.debug)
                    return
                http_404(self, 123)
                return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'blog post 2 done',
                        self.server.debug)

    # after selecting a shared item from the left column then show it
    if html_getreq and \
       '?showshare=' in self.path and '/users/' in self.path:
        item_id = self.path.split('?showshare=')[1]
        if '?' in item_id:
            item_id = item_id.split('?')[0]
        category = ''
        if '?category=' in self.path:
            category = self.path.split('?category=')[1]
        if '?' in category:
            category = category.split('?')[0]
        users_path = self.path.split('?showshare=')[0]
        nickname = users_path.replace('/users/', '')
        item_id = urllib.parse.unquote_plus(item_id.strip())
        msg = \
            html_show_share(self.server.base_dir,
                            self.server.domain, nickname,
                            self.server.http_prefix,
                            self.server.domain_full,
                            item_id, self.server.translate,
                            self.server.shared_items_federated_domains,
                            self.server.default_timeline,
                            self.server.theme_name, 'shares', category,
                            False)
        if not msg:
            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                actor = 'http://' + self.server.onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                actor = 'http://' + self.server.i2p_domain + users_path
            redirect_headers(self, actor + '/tlshares',
                             cookie, calling_domain)
            return
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'html_show_share',
                            self.server.debug)
        return

    # after selecting a wanted item from the left column then show it
    if html_getreq and \
       '?showwanted=' in self.path and '/users/' in self.path:
        item_id = self.path.split('?showwanted=')[1]
        if ';' in item_id:
            item_id = item_id.split(';')[0]
        category = self.path.split('?category=')[1]
        if ';' in category:
            category = category.split(';')[0]
        users_path = self.path.split('?showwanted=')[0]
        nickname = users_path.replace('/users/', '')
        item_id = urllib.parse.unquote_plus(item_id.strip())
        msg = \
            html_show_share(self.server.base_dir,
                            self.server.domain, nickname,
                            self.server.http_prefix,
                            self.server.domain_full,
                            item_id, self.server.translate,
                            self.server.shared_items_federated_domains,
                            self.server.default_timeline,
                            self.server.theme_name, 'wanted', category,
                            False)
        if not msg:
            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                actor = 'http://' + self.server.onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                actor = 'http://' + self.server.i2p_domain + users_path
            redirect_headers(self, actor + '/tlwanted',
                             cookie, calling_domain)
            return
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'htmlShowWanted',
                            self.server.debug)
        return

    # remove a shared item
    if html_getreq and '?rmshare=' in self.path:
        item_id = self.path.split('?rmshare=')[1]
        item_id = urllib.parse.unquote_plus(item_id.strip())
        users_path = self.path.split('?rmshare=')[0]
        actor = \
            self.server.http_prefix + '://' + \
            self.server.domain_full + users_path
        msg = html_confirm_remove_shared_item(self.server.translate,
                                              self.server.base_dir,
                                              actor, item_id,
                                              calling_domain, 'shares')
        if not msg:
            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                actor = 'http://' + self.server.onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                actor = 'http://' + self.server.i2p_domain + users_path
            redirect_headers(self, actor + '/tlshares',
                             cookie, calling_domain)
            return
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'remove shared item',
                            self.server.debug)
        return

    # remove a wanted item
    if html_getreq and '?rmwanted=' in self.path:
        item_id = self.path.split('?rmwanted=')[1]
        item_id = urllib.parse.unquote_plus(item_id.strip())
        users_path = self.path.split('?rmwanted=')[0]
        actor = \
            self.server.http_prefix + '://' + \
            self.server.domain_full + users_path
        msg = html_confirm_remove_shared_item(self.server.translate,
                                              self.server.base_dir,
                                              actor, item_id,
                                              calling_domain, 'wanted')
        if not msg:
            if calling_domain.endswith('.onion') and \
               self.server.onion_domain:
                actor = 'http://' + self.server.onion_domain + users_path
            elif (calling_domain.endswith('.i2p') and
                  self.server.i2p_domain):
                actor = 'http://' + self.server.i2p_domain + users_path
            redirect_headers(self, actor + '/tlwanted',
                             cookie, calling_domain)
            return
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'remove shared item',
                            self.server.debug)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'remove shared item done',
                        self.server.debug)

    if self.path.startswith('/terms'):
        if calling_domain.endswith('.onion') and \
           self.server.onion_domain:
            msg = html_terms_of_service(self.server.base_dir, 'http',
                                        self.server.onion_domain)
        elif (calling_domain.endswith('.i2p') and
              self.server.i2p_domain):
            msg = html_terms_of_service(self.server.base_dir, 'http',
                                        self.server.i2p_domain)
        else:
            msg = html_terms_of_service(self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain_full)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'terms of service shown',
                            self.server.debug)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'terms of service done',
                        self.server.debug)

    # show a list of who you are following
    if (authorized and users_in_path and
        (self.path.endswith('/followingaccounts') or
         self.path.endswith('/followingaccounts.csv'))):
        nickname = get_nickname_from_actor(self.path)
        if not nickname:
            http_404(self, 124)
            return
        following_filename = \
            acct_dir(self.server.base_dir,
                     nickname, self.server.domain) + '/following.txt'
        if not os.path.isfile(following_filename):
            http_404(self, 125)
            return
        if self.path.endswith('/followingaccounts.csv'):
            html_getreq = False
            csv_getreq = True
        if html_getreq:
            msg = html_following_list(self.server.base_dir,
                                      following_filename)
            msglen = len(msg)
            login_headers(self, 'text/html', msglen, calling_domain)
            write2(self, msg.encode('utf-8'))
        elif csv_getreq:
            msg = csv_following_list(following_filename,
                                     self.server.base_dir,
                                     nickname,
                                     self.server.domain)
            msglen = len(msg)
            login_headers(self, 'text/csv', msglen, calling_domain)
            write2(self, msg.encode('utf-8'))
        else:
            http_404(self, 126)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'following accounts shown',
                            self.server.debug)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'following accounts done',
                        self.server.debug)

    # show a list of who are your followers
    if authorized and users_in_path and \
       self.path.endswith('/followersaccounts'):
        nickname = get_nickname_from_actor(self.path)
        if not nickname:
            http_404(self, 127)
            return
        followers_filename = \
            acct_dir(self.server.base_dir,
                     nickname, self.server.domain) + '/followers.txt'
        if not os.path.isfile(followers_filename):
            http_404(self, 128)
            return
        if html_getreq:
            msg = html_following_list(self.server.base_dir,
                                      followers_filename)
            msglen = len(msg)
            login_headers(self, 'text/html', msglen, calling_domain)
            write2(self, msg.encode('utf-8'))
        elif csv_getreq:
            msg = csv_following_list(followers_filename,
                                     self.server.base_dir,
                                     nickname,
                                     self.server.domain)
            msglen = len(msg)
            login_headers(self, 'text/csv', msglen, calling_domain)
            write2(self, msg.encode('utf-8'))
        else:
            http_404(self, 129)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'followers accounts shown',
                            self.server.debug)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'followers accounts done',
                        self.server.debug)

    if self.path.endswith('/about'):
        if calling_domain.endswith('.onion'):
            msg = \
                html_about(self.server.base_dir, 'http',
                           self.server.onion_domain,
                           None, self.server.translate,
                           self.server.system_language)
        elif calling_domain.endswith('.i2p'):
            msg = \
                html_about(self.server.base_dir, 'http',
                           self.server.i2p_domain,
                           None, self.server.translate,
                           self.server.system_language)
        else:
            msg = \
                html_about(self.server.base_dir,
                           self.server.http_prefix,
                           self.server.domain_full,
                           self.server.onion_domain,
                           self.server.translate,
                           self.server.system_language)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'show about screen',
                            self.server.debug)
        return

    if self.path in ('/specification', '/protocol', '/activitypub'):
        if calling_domain.endswith('.onion'):
            msg = \
                html_specification(self.server.base_dir, 'http',
                                   self.server.onion_domain,
                                   None, self.server.translate,
                                   self.server.system_language)
        elif calling_domain.endswith('.i2p'):
            msg = \
                html_specification(self.server.base_dir, 'http',
                                   self.server.i2p_domain,
                                   None, self.server.translate,
                                   self.server.system_language)
        else:
            msg = \
                html_specification(self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain_full,
                                   self.server.onion_domain,
                                   self.server.translate,
                                   self.server.system_language)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'show specification screen',
                            self.server.debug)
        return

    if self.path in ('/manual', '/usermanual', '/userguide'):
        if calling_domain.endswith('.onion'):
            msg = \
                html_manual(self.server.base_dir, 'http',
                            self.server.onion_domain,
                            None, self.server.translate,
                            self.server.system_language)
        elif calling_domain.endswith('.i2p'):
            msg = \
                html_manual(self.server.base_dir, 'http',
                            self.server.i2p_domain,
                            None, self.server.translate,
                            self.server.system_language)
        else:
            msg = \
                html_manual(self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain_full,
                            self.server.onion_domain,
                            self.server.translate,
                            self.server.system_language)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'show user manual screen',
                            self.server.debug)
        return

    if html_getreq and users_in_path and authorized and \
       self.path.endswith('/accesskeys'):
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]

        access_keys = self.server.access_keys
        if self.server.key_shortcuts.get(nickname):
            access_keys = \
                self.server.key_shortcuts[nickname]

        msg = \
            html_access_keys(self.server.base_dir,
                             nickname, self.server.domain,
                             self.server.translate,
                             access_keys,
                             self.server.access_keys,
                             self.server.default_timeline,
                             self.server.theme_name)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'show accesskeys screen',
                            self.server.debug)
        return

    if html_getreq and users_in_path and authorized and \
       self.path.endswith('/themedesigner'):
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]

        if not is_artist(self.server.base_dir, nickname):
            http_403(self)
            return

        msg = \
            html_theme_designer(self.server.base_dir,
                                nickname, self.server.domain,
                                self.server.translate,
                                self.server.default_timeline,
                                self.server.theme_name,
                                self.server.access_keys)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'show theme designer screen',
                            self.server.debug)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show about screen done',
                        self.server.debug)

    # the initial welcome screen after first logging in
    if html_getreq and authorized and \
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
            login_headers(self, 'text/html', msglen, calling_domain)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', 'show welcome screen',
                                self.server.debug)
            return
        self.path = self.path.replace('/welcome', '')

    # the welcome screen which allows you to set an avatar image
    if html_getreq and authorized and \
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
            login_headers(self, 'text/html', msglen, calling_domain)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', 'show welcome profile screen',
                                self.server.debug)
            return
        self.path = self.path.replace('/welcome_profile', '')

    # the final welcome screen
    if html_getreq and authorized and \
       '/users/' in self.path and self.path.endswith('/welcome_final'):
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not is_welcome_screen_complete(self.server.base_dir,
                                          nickname,
                                          self.server.domain):
            msg = \
                html_welcome_final(self.server.base_dir, nickname,
                                   self.server.system_language,
                                   self.server.translate,
                                   self.server.theme_name)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            login_headers(self, 'text/html', msglen, calling_domain)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', 'show welcome final screen',
                                self.server.debug)
            return
        self.path = self.path.replace('/welcome_final', '')

    # if not authorized then show the login screen
    if html_getreq and self.path != '/login' and \
       not is_image_file(self.path) and \
       self.path != '/' and \
       not self.path.startswith('/.well-known/protocol-handler') and \
       self.path != '/users/news/linksmobile' and \
       self.path != '/users/news/newswiremobile':
        if _redirect_to_login_screen(self, calling_domain, self.path,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     getreq_start_time,
                                     authorized, self.server.debug):
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show login screen done',
                        self.server.debug)

    # manifest images used to create a home screen icon
    # when selecting "add to home screen" in browsers
    # which support progressive web apps
    if self.path in ('/logo72.png', '/logo96.png', '/logo128.png',
                     '/logo144.png', '/logo150.png', '/logo192.png',
                     '/logo256.png', '/logo512.png',
                     '/apple-touch-icon.png'):
        media_filename = \
            self.server.base_dir + '/img' + self.path
        if os.path.isfile(media_filename):
            if etag_exists(self, media_filename):
                # The file has not changed
                http_304(self)
                return

            tries = 0
            media_binary = None
            while tries < 5:
                try:
                    with open(media_filename, 'rb') as av_file:
                        media_binary = av_file.read()
                        break
                except OSError as ex:
                    print('EX: manifest logo ' +
                          str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if media_binary:
                mime_type = media_file_mime_type(media_filename)
                set_headers_etag(self, media_filename, mime_type,
                                 media_binary, cookie,
                                 self.server.domain_full,
                                 False, None)
                write2(self, media_binary)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', 'manifest logo shown',
                                    self.server.debug)
                return
        http_404(self, 130)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'manifest logo done',
                        self.server.debug)

    # manifest images used to show example screenshots
    # for use by app stores
    if self.path == '/screenshot1.jpg' or \
       self.path == '/screenshot2.jpg':
        screen_filename = \
            self.server.base_dir + '/img' + self.path
        if os.path.isfile(screen_filename):
            if etag_exists(self, screen_filename):
                # The file has not changed
                http_304(self)
                return

            tries = 0
            media_binary = None
            while tries < 5:
                try:
                    with open(screen_filename, 'rb') as av_file:
                        media_binary = av_file.read()
                        break
                except OSError as ex:
                    print('EX: manifest screenshot ' +
                          str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if media_binary:
                mime_type = media_file_mime_type(screen_filename)
                set_headers_etag(self, screen_filename, mime_type,
                                 media_binary, cookie,
                                 self.server.domain_full,
                                 False, None)
                write2(self, media_binary)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', 'show screenshot',
                                    self.server.debug)
                return
        http_404(self, 131)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show screenshot done',
                        self.server.debug)

    # image on login screen or qrcode
    if (is_image_file(self.path) and
        (self.path.startswith('/login.') or
         self.path.startswith('/qrcode.png'))):
        icon_filename = \
            self.server.base_dir + '/accounts' + self.path
        if os.path.isfile(icon_filename):
            if etag_exists(self, icon_filename):
                # The file has not changed
                http_304(self)
                return

            tries = 0
            media_binary = None
            while tries < 5:
                try:
                    with open(icon_filename, 'rb') as av_file:
                        media_binary = av_file.read()
                        break
                except OSError as ex:
                    print('EX: login screen image ' +
                          str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if media_binary:
                mime_type_str = media_file_mime_type(icon_filename)
                set_headers_etag(self, icon_filename,
                                 mime_type_str,
                                 media_binary, cookie,
                                 self.server.domain_full,
                                 False, None)
                write2(self, media_binary)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', 'login screen logo',
                                    self.server.debug)
                return
        http_404(self, 132)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'login screen logo done',
                        self.server.debug)

    # QR code for account handle
    if users_in_path and \
       self.path.endswith('/qrcode.png'):
        if _show_qrcode(self, calling_domain, self.path,
                        self.server.base_dir,
                        self.server.domain,
                        self.server.onion_domain,
                        self.server.i2p_domain,
                        self.server.port,
                        getreq_start_time):
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'account qrcode done',
                        self.server.debug)

    # search screen banner image
    if users_in_path:
        if self.path.endswith('/search_banner.png'):
            if _search_screen_banner(self, self.path,
                                     self.server.base_dir,
                                     self.server.domain,
                                     getreq_start_time):
                return

        if self.path.endswith('/left_col_image.png'):
            if _column_image(self, 'left', self.path,
                             self.server.base_dir,
                             self.server.domain,
                             getreq_start_time):
                return

        if self.path.endswith('/right_col_image.png'):
            if _column_image(self, 'right', self.path,
                             self.server.base_dir,
                             self.server.domain,
                             getreq_start_time):
                return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'search screen banner done',
                        self.server.debug)

    if self.path.startswith('/defaultprofilebackground'):
        _show_default_profile_background(self, self.server.base_dir,
                                         self.server.theme_name,
                                         getreq_start_time)
        return

    # show a background image on the login or person options page
    if '-background.' in self.path:
        if _show_background_image(self, self.path,
                                  self.server.base_dir,
                                  getreq_start_time):
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'background shown done',
                        self.server.debug)

    # emoji images
    if '/emoji/' in self.path:
        _show_emoji(self, self.path, self.server.base_dir,
                    getreq_start_time)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show emoji done',
                        self.server.debug)

    # show media
    # Note that this comes before the busy flag to avoid conflicts
    # replace mastoson-style media path
    if '/system/media_attachments/files/' in self.path:
        self.path = self.path.replace('/system/media_attachments/files/',
                                      '/media/')
    if '/media/' in self.path:
        _show_media(self, self.path, self.server.base_dir,
                    getreq_start_time)
        return

    if '/ontologies/' in self.path or \
       '/data/' in self.path:
        if not has_users_path(self.path):
            _get_ontology(self, calling_domain,
                          self.path, self.server.base_dir,
                          getreq_start_time)
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show media done',
                        self.server.debug)

    # show shared item images
    # Note that this comes before the busy flag to avoid conflicts
    if '/sharefiles/' in self.path:
        if _show_share_image(self, self.path, self.server.base_dir,
                             getreq_start_time):
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'share image done',
                        self.server.debug)

    # icon images
    # Note that this comes before the busy flag to avoid conflicts
    if self.path.startswith('/icons/'):
        _show_icon(self, self.path, self.server.base_dir,
                   getreq_start_time)
        return

    # show images within https://instancedomain/activitypub
    if self.path.startswith('/activitypub-tutorial-'):
        if self.path.endswith('.png'):
            _show_specification_image(self, self.path,
                                      self.server.base_dir,
                                      getreq_start_time)
            return

    # show images within https://instancedomain/manual
    if self.path.startswith('/manual-'):
        if is_image_file(self.path):
            _show_manual_image(self, self.path,
                               self.server.base_dir,
                               getreq_start_time)
            return

    # help screen images
    # Note that this comes before the busy flag to avoid conflicts
    if self.path.startswith('/helpimages/'):
        _show_help_screen_image(self, self.path,
                                self.server.base_dir,
                                getreq_start_time)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'help screen image done',
                        self.server.debug)

    # cached avatar images
    # Note that this comes before the busy flag to avoid conflicts
    if self.path.startswith('/avatars/'):
        _show_cached_avatar(self, referer_domain, self.path,
                            self.server.base_dir,
                            getreq_start_time)
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'cached avatar done',
                        self.server.debug)

    # show avatar or background image
    # Note that this comes before the busy flag to avoid conflicts
    if _show_avatar_or_banner(self, referer_domain, self.path,
                              self.server.base_dir,
                              self.server.domain,
                              getreq_start_time):
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'avatar or banner shown done',
                        self.server.debug)

    # This busy state helps to avoid flooding
    # Resources which are expected to be called from a web page
    # should be above this
    curr_time_getreq = int(time.time() * 1000)
    if self.server.getreq_busy:
        if curr_time_getreq - self.server.last_getreq < 500:
            if self.server.debug:
                print('DEBUG: GET Busy')
            self.send_response(429)
            self.end_headers()
            return
    self.server.getreq_busy = True
    self.server.last_getreq = curr_time_getreq

    # returns after this point should set getreq_busy to False

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'GET busy time',
                        self.server.debug)

    if not permitted_dir(self.path):
        if self.server.debug:
            print('DEBUG: GET Not permitted')
        http_404(self, 133)
        self.server.getreq_busy = False
        return

    # get webfinger endpoint for a person
    if _webfinger(self, calling_domain, referer_domain, cookie):
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'webfinger called',
                            self.server.debug)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'permitted directory',
                        self.server.debug)

    # show the login screen
    if (self.path.startswith('/login') or
        (self.path == '/' and
         not authorized and
         not self.server.news_instance)):
        # request basic auth
        msg = html_login(self.server.translate,
                         self.server.base_dir,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.system_language,
                         True, ua_str,
                         self.server.theme_name).encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'login shown',
                            self.server.debug)
        self.server.getreq_busy = False
        return

    # show the news front page
    if self.path == '/' and \
       not authorized and \
       self.server.news_instance:
        news_url = get_instance_url(calling_domain,
                                    self.server.http_prefix,
                                    self.server.domain_full,
                                    self.server.onion_domain,
                                    self.server.i2p_domain) + \
                                    '/users/news'
        logout_redirect(self, news_url, calling_domain)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'news front page shown',
                            self.server.debug)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'login shown done',
                        self.server.debug)

    # the newswire screen on mobile
    if html_getreq and self.path.startswith('/users/') and \
       self.path.endswith('/newswiremobile'):
        if (authorized or
            (not authorized and
             self.path.startswith('/users/news/') and
             self.server.news_instance)):
            nickname = get_nickname_from_actor(self.path)
            if not nickname:
                http_404(self, 134)
                self.server.getreq_busy = False
                return
            timeline_path = \
                '/users/' + nickname + '/' + self.server.default_timeline
            show_publish_as_icon = self.server.show_publish_as_icon
            rss_icon_at_top = self.server.rss_icon_at_top
            icons_as_buttons = self.server.icons_as_buttons
            default_timeline = self.server.default_timeline
            access_keys = self.server.access_keys
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]
            msg = \
                html_newswire_mobile(self.server.base_dir,
                                     nickname,
                                     self.server.domain,
                                     self.server.domain_full,
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
                                     access_keys,
                                     ua_str).encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
            self.server.getreq_busy = False
            return

    if html_getreq and self.path.startswith('/users/') and \
       self.path.endswith('/linksmobile'):
        if (authorized or
            (not authorized and
             self.path.startswith('/users/news/') and
             self.server.news_instance)):
            nickname = get_nickname_from_actor(self.path)
            if not nickname:
                http_404(self, 135)
                self.server.getreq_busy = False
                return
            access_keys = self.server.access_keys
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]
            timeline_path = \
                '/users/' + nickname + '/' + self.server.default_timeline
            icons_as_buttons = self.server.icons_as_buttons
            default_timeline = self.server.default_timeline
            shared_items_domains = \
                self.server.shared_items_federated_domains
            msg = \
                html_links_mobile(self.server.base_dir, nickname,
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
                                  shared_items_domains).encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen, cookie, calling_domain,
                        False)
            write2(self, msg)
            self.server.getreq_busy = False
            return

    if '?remotetag=' in self.path and \
       '/users/' in self.path and authorized:
        actor = self.path.split('?remotetag=')[0]
        nickname = get_nickname_from_actor(actor)
        hashtag_url = self.path.split('?remotetag=')[1]
        if ';' in hashtag_url:
            hashtag_url = hashtag_url.split(';')[0]
        hashtag_url = hashtag_url.replace('--', '/')

        page_number = 1
        if ';page=' in self.path:
            page_number_str = self.path.split(';page=')[1]
            if ';' in page_number_str:
                page_number_str = page_number_str.split(';')[0]
            if page_number_str.isdigit():
                page_number = int(page_number_str)

        allow_local_network_access = self.server.allow_local_network_access
        show_published_date_only = self.server.show_published_date_only
        twitter_replacement_domain = self.server.twitter_replacement_domain
        timezone = None
        if self.server.account_timezone.get(nickname):
            timezone = \
                self.server.account_timezone.get(nickname)
        msg = \
            html_hashtag_search_remote(nickname,
                                       self.server.domain,
                                       self.server.port,
                                       self.server.recent_posts_cache,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       self.server.base_dir,
                                       hashtag_url,
                                       page_number, MAX_POSTS_IN_FEED,
                                       self.server.session,
                                       self.server.cached_webfingers,
                                       self.server.person_cache,
                                       self.server.http_prefix,
                                       self.server.project_version,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       self.server.peertube_instances,
                                       allow_local_network_access,
                                       self.server.theme_name,
                                       self.server.system_language,
                                       self.server.max_like_count,
                                       self.server.signing_priv_key_pem,
                                       self.server.cw_lists,
                                       self.server.lists_enabled,
                                       timezone,
                                       self.server.bold_reading,
                                       self.server.dogwhistles,
                                       self.server.min_images_for_accounts,
                                       self.server.debug,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen, cookie, calling_domain,
                        False)
            write2(self, msg)
            self.server.getreq_busy = False
            return
        else:
            hashtag = urllib.parse.unquote(hashtag_url.split('/')[-1])
            tags_filename = \
                self.server.base_dir + '/tags/' + hashtag + '.txt'
            if os.path.isfile(tags_filename):
                # redirect to the local hashtag screen
                self.server.getreq_busy = False
                ht_url = \
                    get_instance_url(calling_domain,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     self.server.onion_domain,
                                     self.server.i2p_domain) + \
                    '/users/' + nickname + '/tags/' + hashtag
                redirect_headers(self, ht_url, cookie, calling_domain)
            else:
                # redirect to the upstream hashtag url
                self.server.getreq_busy = False
                redirect_headers(self, hashtag_url, None, calling_domain)
        return

    # hashtag search
    if self.path.startswith('/tags/') or \
       (authorized and '/tags/' in self.path):
        if self.path.startswith('/tags/rss2/'):
            _hashtag_search_rss2(self, calling_domain,
                                 self.path, cookie,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domain_full,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 getreq_start_time)
            self.server.getreq_busy = False
            return
        if not html_getreq:
            _hashtag_search_json(self, calling_domain, referer_domain,
                                 self.path, cookie,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domain_full,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 getreq_start_time)
            self.server.getreq_busy = False
            return
        _hashtag_search2(self, calling_domain,
                         self.path, cookie,
                         self.server.base_dir,
                         self.server.http_prefix,
                         self.server.domain,
                         self.server.domain_full,
                         self.server.port,
                         self.server.onion_domain,
                         self.server.i2p_domain,
                         getreq_start_time,
                         curr_session)
        self.server.getreq_busy = False
        return

    # hashtag map kml
    if self.path.startswith('/tagmaps/') or \
       (authorized and '/tagmaps/' in self.path):
        map_str = \
            map_format_from_tagmaps_path(self.server.base_dir, self.path,
                                         self.server.map_format,
                                         self.server.domain)
        if map_str:
            msg = map_str.encode('utf-8')
            msglen = len(msg)
            if self.server.map_format == 'gpx':
                header_type = \
                    'application/gpx+xml; charset=utf-8'
            else:
                header_type = \
                    'application/vnd.google-earth.kml+xml; charset=utf-8'
            set_headers(self, header_type, msglen,
                        None, calling_domain, True)
            write2(self, msg)
            self.server.getreq_busy = False
            return
        http_404(self, 136)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'hashtag search done',
                        self.server.debug)

    # show or hide buttons in the web interface
    if html_getreq and users_in_path and \
       self.path.endswith('/minimal') and \
       authorized:
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
            not_min = not is_minimal(self.server.base_dir,
                                     self.server.domain, nickname)
            set_minimal(self.server.base_dir,
                        self.server.domain, nickname, not_min)
            self.path = get_default_path(self.server.media_instance,
                                         self.server.blogs_instance,
                                         nickname)

    # search for a fediverse address, shared item or emoji
    # from the web interface by selecting search icon
    if html_getreq and users_in_path:
        if self.path.endswith('/search') or \
           '/search?' in self.path:
            if '?' in self.path:
                self.path = self.path.split('?')[0]

            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            access_keys = self.server.access_keys
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]

            # show the search screen
            msg = html_search(self.server.translate,
                              self.server.base_dir, self.path,
                              self.server.domain,
                              self.server.default_timeline,
                              self.server.theme_name,
                              self.server.text_mode_banner,
                              access_keys)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen, cookie,
                            calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', 'search screen shown',
                                    self.server.debug)
            self.server.getreq_busy = False
            return

    # show a hashtag category from the search screen
    if html_getreq and '/category/' in self.path:
        msg = html_search_hashtag_category(self.server.translate,
                                           self.server.base_dir, self.path,
                                           self.server.domain,
                                           self.server.theme_name)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen, cookie, calling_domain,
                        False)
            write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', 'hashtag category screen shown',
                            self.server.debug)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'search screen shown done',
                        self.server.debug)

    # Show the html calendar for a user
    if html_getreq and users_in_path:
        if '/calendar' in self.path:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            access_keys = self.server.access_keys
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]

            # show the calendar screen
            msg = html_calendar(self.server.person_cache,
                                self.server.translate,
                                self.server.base_dir, self.path,
                                self.server.http_prefix,
                                self.server.domain_full,
                                self.server.text_mode_banner,
                                access_keys,
                                False, self.server.system_language,
                                self.server.default_timeline,
                                self.server.theme_name)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                if 'ical=true' in self.path:
                    set_headers(self, 'text/calendar',
                                msglen, cookie, calling_domain,
                                      False)
                else:
                    set_headers(self, 'text/html',
                                msglen, cookie, calling_domain,
                                False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', 'calendar shown',
                                    self.server.debug)
            else:
                http_404(self, 137)
            self.server.getreq_busy = False
            return

    # Show the icalendar for a user
    if icalendar_getreq and users_in_path:
        if '/calendar' in self.path:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            access_keys = self.server.access_keys
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]

            # show the calendar screen
            msg = html_calendar(self.server.person_cache,
                                self.server.translate,
                                self.server.base_dir, self.path,
                                self.server.http_prefix,
                                self.server.domain_full,
                                self.server.text_mode_banner,
                                access_keys,
                                True,
                                self.server.system_language,
                                self.server.default_timeline,
                                self.server.theme_name)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/calendar',
                            msglen, cookie, calling_domain,
                                  False)
                write2(self, msg)
            else:
                http_404(self, 138)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', 'icalendar shown',
                                self.server.debug)
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'calendar shown done',
                        self.server.debug)

    # Show confirmation for deleting a calendar event
    if html_getreq and users_in_path:
        if '/eventdelete' in self.path and \
           '?time=' in self.path and \
           '?eventid=' in self.path:
            if _confirm_delete_event(self, calling_domain, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     cookie,
                                     self.server.translate,
                                     self.server.domain_full,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     getreq_start_time):
                self.server.getreq_busy = False
                return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'calendar delete shown done',
                        self.server.debug)

    # search for emoji by name
    if html_getreq and users_in_path:
        if self.path.endswith('/searchemoji'):
            # show the search screen
            msg = \
                html_search_emoji_text_entry(self.server.translate,
                                             self.server.base_dir,
                                             self.path).encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', 'emoji search shown',
                                self.server.debug)
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'emoji search shown done',
                        self.server.debug)

    repeat_private = False
    if html_getreq and '?repeatprivate=' in self.path:
        repeat_private = True
        self.path = self.path.replace('?repeatprivate=', '?repeat=')
    # announce/repeat button was pressed
    if authorized and html_getreq and '?repeat=' in self.path:
        _announce_button(self, calling_domain, self.path,
                         self.server.base_dir,
                         cookie, proxy_type,
                         self.server.http_prefix,
                         self.server.domain,
                         self.server.domain_full,
                         self.server.port,
                         self.server.onion_domain,
                         self.server.i2p_domain,
                         getreq_start_time,
                         repeat_private,
                         self.server.debug,
                         curr_session,
                         self.server.sites_unavailable)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show announce done',
                        self.server.debug)

    if authorized and html_getreq and '?unrepeatprivate=' in self.path:
        self.path = self.path.replace('?unrepeatprivate=', '?unrepeat=')

    # undo an announce/repeat from the web interface
    if authorized and html_getreq and '?unrepeat=' in self.path:
        _announce_button_undo(self, calling_domain, self.path,
                              self.server.base_dir,
                              cookie, proxy_type,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.domain_full,
                              self.server.onion_domain,
                              self.server.i2p_domain,
                              getreq_start_time,
                              self.server.debug,
                              self.server.recent_posts_cache,
                              curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'unannounce done',
                        self.server.debug)

    # send a newswire moderation vote from the web interface
    if authorized and '/newswirevote=' in self.path and \
       self.path.startswith('/users/'):
        _newswire_vote(self, calling_domain, self.path,
                       cookie,
                       self.server.base_dir,
                       self.server.http_prefix,
                       self.server.domain_full,
                       self.server.onion_domain,
                       self.server.i2p_domain,
                       getreq_start_time,
                       self.server.newswire)
        self.server.getreq_busy = False
        return

    # send a newswire moderation unvote from the web interface
    if authorized and '/newswireunvote=' in self.path and \
       self.path.startswith('/users/'):
        _newswire_unvote(self, calling_domain, self.path,
                         cookie,
                         self.server.base_dir,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain,
                         getreq_start_time,
                         self.server.debug,
                         self.server.newswire)
        self.server.getreq_busy = False
        return

    # send a follow request approval from the web interface
    if authorized and '/followapprove=' in self.path and \
       self.path.startswith('/users/'):
        _follow_approve_button(self, calling_domain, self.path,
                               cookie,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.domain_full,
                               self.server.port,
                               self.server.onion_domain,
                               self.server.i2p_domain,
                               getreq_start_time,
                               proxy_type,
                               self.server.debug,
                               curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'follow approve done',
                        self.server.debug)

    # deny a follow request from the web interface
    if authorized and '/followdeny=' in self.path and \
       self.path.startswith('/users/'):
        _follow_deny_button(self, calling_domain, self.path,
                            cookie,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.domain_full,
                            self.server.port,
                            self.server.onion_domain,
                            self.server.i2p_domain,
                            getreq_start_time,
                            self.server.debug)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'follow deny done',
                        self.server.debug)

    # like from the web interface icon
    if authorized and html_getreq and '?like=' in self.path:
        _like_button(self, calling_domain, self.path,
                     self.server.base_dir,
                     self.server.http_prefix,
                     self.server.domain,
                     self.server.domain_full,
                     self.server.onion_domain,
                     self.server.i2p_domain,
                     getreq_start_time,
                     proxy_type,
                     cookie,
                     self.server.debug,
                     curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'like button done',
                        self.server.debug)

    # undo a like from the web interface icon
    if authorized and html_getreq and '?unlike=' in self.path:
        _undo_like_button(self, calling_domain, self.path,
                          self.server.base_dir,
                          self.server.http_prefix,
                          self.server.domain,
                          self.server.domain_full,
                          self.server.onion_domain,
                          self.server.i2p_domain,
                          getreq_start_time,
                          proxy_type,
                          cookie, self.server.debug,
                          curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'unlike button done',
                        self.server.debug)

    # emoji reaction from the web interface icon
    if authorized and html_getreq and \
       '?react=' in self.path and \
       '?actor=' in self.path:
        _reaction_button(self, calling_domain, self.path,
                         self.server.base_dir,
                         self.server.http_prefix,
                         self.server.domain,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain,
                         getreq_start_time,
                         proxy_type,
                         cookie,
                         self.server.debug,
                         curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'emoji reaction button done',
                        self.server.debug)

    # undo an emoji reaction from the web interface icon
    if authorized and html_getreq and \
       '?unreact=' in self.path and \
       '?actor=' in self.path:
        _undo_reaction_button(self, calling_domain, self.path,
                              self.server.base_dir,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.domain_full,
                              self.server.onion_domain,
                              self.server.i2p_domain,
                              getreq_start_time,
                              proxy_type,
                              cookie, self.server.debug,
                              curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'unreaction button done',
                        self.server.debug)

    # bookmark from the web interface icon
    if authorized and html_getreq and '?bookmark=' in self.path:
        _bookmark_button(self, calling_domain, self.path,
                         self.server.base_dir,
                         self.server.http_prefix,
                         self.server.domain,
                         self.server.domain_full,
                         self.server.port,
                         self.server.onion_domain,
                         self.server.i2p_domain,
                         getreq_start_time,
                         proxy_type,
                         cookie, self.server.debug,
                         curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'bookmark shown done',
                        self.server.debug)

    # emoji recation from the web interface bottom icon
    if authorized and html_getreq and '?selreact=' in self.path:
        _reaction_picker2(self, calling_domain, self.path,
                          self.server.base_dir,
                          self.server.http_prefix,
                          self.server.domain,
                          self.server.port,
                          getreq_start_time,
                          cookie, self.server.debug,
                          curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'bookmark shown done',
                        self.server.debug)

    # undo a bookmark from the web interface icon
    if authorized and html_getreq and '?unbookmark=' in self.path:
        _undo_bookmark_button(self, calling_domain, self.path,
                              self.server.base_dir,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.domain_full,
                              self.server.port,
                              self.server.onion_domain,
                              self.server.i2p_domain,
                              getreq_start_time,
                              proxy_type, cookie,
                              self.server.debug,
                              curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'unbookmark shown done',
                        self.server.debug)

    # delete button is pressed on a post
    if authorized and html_getreq and '?delete=' in self.path:
        _delete_button(self, calling_domain, self.path,
                       self.server.base_dir,
                       self.server.http_prefix,
                       self.server.domain_full,
                       self.server.onion_domain,
                       self.server.i2p_domain,
                       getreq_start_time,
                       proxy_type, cookie,
                       self.server.debug,
                       curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'delete shown done',
                        self.server.debug)

    # The mute button is pressed
    if authorized and html_getreq and '?mute=' in self.path:
        _mute_button2(self, calling_domain, self.path,
                      self.server.base_dir,
                      self.server.http_prefix,
                      self.server.domain,
                      self.server.domain_full,
                      self.server.port,
                      self.server.onion_domain,
                      self.server.i2p_domain,
                      getreq_start_time,
                      cookie, self.server.debug,
                      curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'post muted done',
                        self.server.debug)

    # unmute a post from the web interface icon
    if authorized and html_getreq and '?unmute=' in self.path:
        _undo_mute_button(self, calling_domain, self.path,
                          self.server.base_dir,
                          self.server.http_prefix,
                          self.server.domain,
                          self.server.domain_full,
                          self.server.port,
                          self.server.onion_domain,
                          self.server.i2p_domain,
                          getreq_start_time,
                          cookie, self.server.debug,
                          curr_session)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'unmute activated done',
                        self.server.debug)

    # reply from the web interface icon
    in_reply_to_url = None
    reply_to_list = []
    reply_page_number = 1
    reply_category = ''
    share_description = None
    conversation_id = None
    if html_getreq:
        if '?conversationId=' in self.path:
            conversation_id = self.path.split('?conversationId=')[1]
            if '?' in conversation_id:
                conversation_id = conversation_id.split('?')[0]
        # public reply
        if '?replyto=' in self.path:
            in_reply_to_url = self.path.split('?replyto=')[1]
            if '?' in in_reply_to_url:
                mentions_list = in_reply_to_url.split('?')
                for ment in mentions_list:
                    if ment.startswith('mention='):
                        reply_handle = ment.replace('mention=', '')
                        if reply_handle not in reply_to_list:
                            reply_to_list.append(reply_handle)
                    if ment.startswith('page='):
                        reply_page_str = ment.replace('page=', '')
                        if len(reply_page_str) > 5:
                            reply_page_str = "1"
                        if reply_page_str.isdigit():
                            reply_page_number = int(reply_page_str)
                in_reply_to_url = mentions_list[0]
            if not self.server.public_replies_unlisted:
                self.path = self.path.split('?replyto=')[0] + '/newpost'
            else:
                self.path = \
                    self.path.split('?replyto=')[0] + '/newunlisted'
            if self.server.debug:
                print('DEBUG: replyto path ' + self.path)

        # unlisted reply
        if '?replyunlisted=' in self.path:
            in_reply_to_url = self.path.split('?replyunlisted=')[1]
            if '?' in in_reply_to_url:
                mentions_list = in_reply_to_url.split('?')
                for ment in mentions_list:
                    if ment.startswith('mention='):
                        reply_handle = ment.replace('mention=', '')
                        if reply_handle not in reply_to_list:
                            reply_to_list.append(reply_handle)
                    if ment.startswith('page='):
                        reply_page_str = ment.replace('page=', '')
                        if len(reply_page_str) > 5:
                            reply_page_str = "1"
                        if reply_page_str.isdigit():
                            reply_page_number = int(reply_page_str)
                in_reply_to_url = mentions_list[0]
            self.path = \
                self.path.split('?replyunlisted=')[0] + '/newunlisted'
            if self.server.debug:
                print('DEBUG: replyunlisted path ' + self.path)

        # reply to followers
        if '?replyfollowers=' in self.path:
            in_reply_to_url = self.path.split('?replyfollowers=')[1]
            if '?' in in_reply_to_url:
                mentions_list = in_reply_to_url.split('?')
                for ment in mentions_list:
                    if ment.startswith('mention='):
                        reply_handle = ment.replace('mention=', '')
                        ment2 = ment.replace('mention=', '')
                        if ment2 not in reply_to_list:
                            reply_to_list.append(reply_handle)
                    if ment.startswith('page='):
                        reply_page_str = ment.replace('page=', '')
                        if len(reply_page_str) > 5:
                            reply_page_str = "1"
                        if reply_page_str.isdigit():
                            reply_page_number = int(reply_page_str)
                in_reply_to_url = mentions_list[0]
            self.path = self.path.split('?replyfollowers=')[0] + \
                '/newfollowers'
            if self.server.debug:
                print('DEBUG: replyfollowers path ' + self.path)

        # replying as a direct message,
        # for moderation posts or the dm timeline
        reply_is_chat = False
        if '?replydm=' in self.path or '?replychat=' in self.path:
            reply_type = 'replydm'
            if '?replychat=' in self.path:
                reply_type = 'replychat'
                reply_is_chat = True
            in_reply_to_url = self.path.split('?' + reply_type + '=')[1]
            in_reply_to_url = urllib.parse.unquote_plus(in_reply_to_url)
            if '?' in in_reply_to_url:
                # multiple parameters
                mentions_list = in_reply_to_url.split('?')
                for ment in mentions_list:
                    if ment.startswith('mention='):
                        reply_handle = ment.replace('mention=', '')
                        in_reply_to_url = reply_handle
                        if reply_handle not in reply_to_list:
                            reply_to_list.append(reply_handle)
                    elif ment.startswith('page='):
                        reply_page_str = ment.replace('page=', '')
                        if len(reply_page_str) > 5:
                            reply_page_str = "1"
                        if reply_page_str.isdigit():
                            reply_page_number = int(reply_page_str)
                    elif ment.startswith('category='):
                        reply_category = ment.replace('category=', '')
                    elif ment.startswith('sharedesc:'):
                        # get the title for the shared item
                        share_description = \
                            ment.replace('sharedesc:', '').strip()
                        share_description = \
                            share_description.replace('_', ' ')
                in_reply_to_url = mentions_list[0]
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

            self.path = \
                self.path.split('?' + reply_type + '=')[0] + '/newdm'
            if self.server.debug:
                print('DEBUG: ' + reply_type + ' path ' + self.path)

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
            if not nickname:
                http_404(self, 139)
                self.server.getreq_busy = False
                return
            if nickname == actor:
                post_url = \
                    local_actor_url(self.server.http_prefix, nickname,
                                    self.server.domain_full) + \
                    '/statuses/' + message_id
                msg = html_edit_blog(self.server.media_instance,
                                     self.server.translate,
                                     self.server.base_dir,
                                     self.path, reply_page_number,
                                     nickname, self.server.domain,
                                     post_url,
                                     self.server.system_language)
                if msg:
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    set_headers(self, 'text/html', msglen,
                                cookie, calling_domain, False)
                    write2(self, msg)
                    self.server.getreq_busy = False
                    return

        # Edit a post
        edit_post_params = {}
        if authorized and \
           '/users/' in self.path and \
           '?postedit=' in self.path and \
           ';scope=' in self.path and \
           ';actor=' in self.path:
            post_scope = self.path.split(';scope=')[1]
            if ';' in post_scope:
                post_scope = post_scope.split(';')[0]
            edit_post_params['scope'] = post_scope
            message_id = self.path.split('?postedit=')[1]
            if ';' in message_id:
                message_id = message_id.split(';')[0]
            if ';replyTo=' in self.path:
                reply_to = self.path.split(';replyTo=')[1]
                if ';' in reply_to:
                    reply_to = message_id.split(';')[0]
                edit_post_params['replyTo'] = reply_to
            actor = self.path.split(';actor=')[1]
            if ';' in actor:
                actor = actor.split(';')[0]
            edit_post_params['actor'] = actor
            nickname = get_nickname_from_actor(self.path.split('?')[0])
            edit_post_params['nickname'] = nickname
            if not nickname:
                http_404(self, 140)
                self.server.getreq_busy = False
                return
            if nickname != actor:
                http_404(self, 141)
                self.server.getreq_busy = False
                return
            post_url = \
                local_actor_url(self.server.http_prefix, nickname,
                                self.server.domain_full) + \
                '/statuses/' + message_id
            edit_post_params['post_url'] = post_url
            # use the new post functions, but using edit_post_params
            new_post_scope = post_scope
            if post_scope == 'public':
                new_post_scope = 'post'
            self.path = '/users/' + nickname + '/new' + new_post_scope

        # list of known crawlers accessing nodeinfo or masto API
        if _show_known_crawlers(self, calling_domain, self.path,
                                self.server.base_dir,
                                self.server.known_crawlers):
            self.server.getreq_busy = False
            return

        # edit profile in web interface
        if _edit_profile2(self, calling_domain, self.path,
                          self.server.translate,
                          self.server.base_dir,
                          self.server.domain,
                          self.server.port,
                          cookie):
            self.server.getreq_busy = False
            return

        # edit links from the left column of the timeline in web interface
        if _edit_links2(self, calling_domain, self.path,
                        self.server.translate,
                        self.server.base_dir,
                        self.server.domain,
                        cookie,
                        self.server.theme_name):
            self.server.getreq_busy = False
            return

        # edit newswire from the right column of the timeline
        if _edit_newswire2(self, calling_domain, self.path,
                           self.server.translate,
                           self.server.base_dir,
                           self.server.domain, cookie):
            self.server.getreq_busy = False
            return

        # edit news post
        if _edit_news_post2(self, calling_domain, self.path,
                            self.server.translate,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.domain_full,
                            cookie):
            self.server.getreq_busy = False
            return

        if _show_new_post(self, edit_post_params,
                          calling_domain, self.path,
                          self.server.media_instance,
                          self.server.translate,
                          self.server.base_dir,
                          self.server.http_prefix,
                          in_reply_to_url, reply_to_list,
                          reply_is_chat,
                          share_description, reply_page_number,
                          reply_category,
                          self.server.domain,
                          self.server.domain_full,
                          getreq_start_time,
                          cookie, no_drop_down, conversation_id,
                          curr_session):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'new post done',
                        self.server.debug)

    # get an individual post from the path /@nickname/statusnumber
    if _show_individual_at_post(self, ssml_getreq, authorized,
                                calling_domain, referer_domain,
                                self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domain_full,
                                self.server.port,
                                getreq_start_time,
                                proxy_type,
                                cookie, self.server.debug,
                                curr_session):
        self.server.getreq_busy = False
        return

    # show the likers of a post
    if _show_likers_of_post(self, authorized,
                            calling_domain, self.path,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.port,
                            getreq_start_time,
                            cookie, self.server.debug,
                            curr_session):
        self.server.getreq_busy = False
        return

    # show the announcers/repeaters of a post
    if _show_announcers_of_post(self, authorized,
                                calling_domain, self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.port,
                                getreq_start_time,
                                cookie, self.server.debug,
                                curr_session):
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'individual post done',
                        self.server.debug)

    # get replies to a post /users/nickname/statuses/number/replies
    if self.path.endswith('/replies') or '/replies?page=' in self.path:
        if _show_replies_to_post(self, authorized,
                                 calling_domain, referer_domain,
                                 self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domain_full,
                                 self.server.port,
                                 getreq_start_time,
                                 proxy_type, cookie,
                                 self.server.debug,
                                 curr_session):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'post replies done',
                        self.server.debug)

    # roles on profile screen
    if self.path.endswith('/roles') and users_in_path:
        if _show_roles(self, calling_domain, referer_domain,
                       self.path,
                       self.server.base_dir,
                       self.server.http_prefix,
                       self.server.domain,
                       getreq_start_time,
                       proxy_type,
                       cookie, self.server.debug,
                       curr_session):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show roles done',
                        self.server.debug)

    # show skills on the profile page
    if self.path.endswith('/skills') and users_in_path:
        if _show_skills(self, calling_domain, referer_domain,
                        self.path,
                        self.server.base_dir,
                        self.server.http_prefix,
                        self.server.domain,
                        getreq_start_time,
                        proxy_type,
                        cookie, self.server.debug,
                        curr_session):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show skills done',
                        self.server.debug)

    if '?notifypost=' in self.path and users_in_path and authorized:
        if _show_notify_post(self, authorized,
                             calling_domain, referer_domain,
                             self.path,
                             self.server.base_dir,
                             self.server.http_prefix,
                             self.server.domain,
                             self.server.port,
                             getreq_start_time,
                             proxy_type,
                             cookie, self.server.debug,
                             curr_session):
            self.server.getreq_busy = False
            return

    # get an individual post from the path
    # /users/nickname/statuses/number
    if '/statuses/' in self.path and users_in_path:
        if _show_individual_post(self, ssml_getreq, authorized,
                                 calling_domain, referer_domain,
                                 self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domain_full,
                                 self.server.port,
                                 getreq_start_time,
                                 proxy_type,
                                 cookie, self.server.debug,
                                 curr_session):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show status done',
                        self.server.debug)

    # get the inbox timeline for a given person
    if self.path.endswith('/inbox') or '/inbox?page=' in self.path:
        if _show_inbox(self, authorized,
                       calling_domain, referer_domain,
                       self.path,
                       self.server.base_dir,
                       self.server.http_prefix,
                       self.server.domain,
                       self.server.port,
                       getreq_start_time,
                       cookie, self.server.debug,
                       self.server.recent_posts_cache,
                       curr_session,
                       self.server.default_timeline,
                       self.server.max_recent_posts,
                       self.server.translate,
                       self.server.cached_webfingers,
                       self.server.person_cache,
                       self.server.allow_deletion,
                       self.server.project_version,
                       self.server.yt_replace_domain,
                       self.server.twitter_replacement_domain,
                       ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show inbox done',
                        self.server.debug)

    # get the direct messages timeline for a given person
    if self.path.endswith('/dm') or '/dm?page=' in self.path:
        if _show_dms(self, authorized,
                     calling_domain, referer_domain,
                     self.path,
                     self.server.base_dir,
                     self.server.http_prefix,
                     self.server.domain,
                     self.server.port,
                     getreq_start_time,
                     cookie, self.server.debug,
                     curr_session, ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show dms done',
                        self.server.debug)

    # get the replies timeline for a given person
    if self.path.endswith('/tlreplies') or '/tlreplies?page=' in self.path:
        if _show_replies(self, authorized,
                         calling_domain, referer_domain,
                         self.path,
                         self.server.base_dir,
                         self.server.http_prefix,
                         self.server.domain,
                         self.server.port,
                         getreq_start_time,
                         cookie, self.server.debug,
                         curr_session, ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show replies 2 done',
                        self.server.debug)

    # get the media timeline for a given person
    if self.path.endswith('/tlmedia') or '/tlmedia?page=' in self.path:
        if _show_media_timeline(self, authorized,
                                calling_domain, referer_domain,
                                self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.port,
                                getreq_start_time,
                                cookie, self.server.debug,
                                curr_session, ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show media 2 done',
                        self.server.debug)

    # get the blogs for a given person
    if self.path.endswith('/tlblogs') or '/tlblogs?page=' in self.path:
        if _show_blogs_timeline(self, authorized,
                                calling_domain, referer_domain,
                                self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.port,
                                getreq_start_time,
                                cookie, self.server.debug,
                                curr_session, ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show blogs 2 done',
                        self.server.debug)

    # get the news for a given person
    if self.path.endswith('/tlnews') or '/tlnews?page=' in self.path:
        if _show_news_timeline(self, authorized,
                               calling_domain, referer_domain,
                               self.path,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.port,
                               getreq_start_time,
                               cookie, self.server.debug,
                               curr_session, ua_str):
            self.server.getreq_busy = False
            return

    # get features (local blogs) for a given person
    if self.path.endswith('/tlfeatures') or \
       '/tlfeatures?page=' in self.path:
        if _show_features_timeline(self, authorized,
                                   calling_domain, referer_domain,
                                   self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.port,
                                   getreq_start_time,
                                   cookie, self.server.debug,
                                   curr_session, ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show news 2 done',
                        self.server.debug)

    # get the shared items timeline for a given person
    if self.path.endswith('/tlshares') or '/tlshares?page=' in self.path:
        if _show_shares_timeline(self, authorized,
                                 calling_domain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.port,
                                 getreq_start_time,
                                 cookie, self.server.debug,
                                 curr_session, ua_str):
            self.server.getreq_busy = False
            return

    # get the wanted items timeline for a given person
    if self.path.endswith('/tlwanted') or '/tlwanted?page=' in self.path:
        if _show_wanted_timeline(self, authorized,
                                 calling_domain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.port,
                                 getreq_start_time,
                                 cookie, self.server.debug,
                                 curr_session, ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show shares 2 done',
                        self.server.debug)

    # block a domain from html_account_info
    if authorized and users_in_path and \
       '/accountinfo?blockdomain=' in self.path and \
       '?handle=' in self.path:
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not is_moderator(self.server.base_dir, nickname):
            http_400(self)
            self.server.getreq_busy = False
            return
        block_domain = self.path.split('/accountinfo?blockdomain=')[1]
        search_handle = block_domain.split('?handle=')[1]
        search_handle = urllib.parse.unquote_plus(search_handle)
        block_domain = block_domain.split('?handle=')[0]
        block_domain = urllib.parse.unquote_plus(block_domain.strip())
        if '?' in block_domain:
            block_domain = block_domain.split('?')[0]
        add_global_block(self.server.base_dir, '*', block_domain, None)
        self.server.blocked_cache_last_updated = \
            update_blocked_cache(self.server.base_dir,
                                 self.server.blocked_cache,
                                 self.server.blocked_cache_last_updated, 0)
        msg = \
            html_account_info(self.server.translate,
                              self.server.base_dir,
                              self.server.http_prefix,
                              nickname,
                              self.server.domain,
                              search_handle,
                              self.server.debug,
                              self.server.system_language,
                              self.server.signing_priv_key_pem,
                              None,
                              self.server.block_federated)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            login_headers(self, 'text/html',
                          msglen, calling_domain)
            write2(self, msg)
        self.server.getreq_busy = False
        return

    # unblock a domain from html_account_info
    if authorized and users_in_path and \
       '/accountinfo?unblockdomain=' in self.path and \
       '?handle=' in self.path:
        nickname = self.path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not is_moderator(self.server.base_dir, nickname):
            http_400(self)
            self.server.getreq_busy = False
            return
        block_domain = self.path.split('/accountinfo?unblockdomain=')[1]
        search_handle = block_domain.split('?handle=')[1]
        search_handle = urllib.parse.unquote_plus(search_handle)
        block_domain = block_domain.split('?handle=')[0]
        block_domain = urllib.parse.unquote_plus(block_domain.strip())
        remove_global_block(self.server.base_dir, '*', block_domain)
        self.server.blocked_cache_last_updated = \
            update_blocked_cache(self.server.base_dir,
                                 self.server.blocked_cache,
                                 self.server.blocked_cache_last_updated, 0)
        msg = \
            html_account_info(self.server.translate,
                              self.server.base_dir,
                              self.server.http_prefix,
                              nickname,
                              self.server.domain,
                              search_handle,
                              self.server.debug,
                              self.server.system_language,
                              self.server.signing_priv_key_pem,
                              None,
                              self.server.block_federated)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            login_headers(self, 'text/html',
                          msglen, calling_domain)
            write2(self, msg)
        self.server.getreq_busy = False
        return

    # get the bookmarks timeline for a given person
    if self.path.endswith('/tlbookmarks') or \
       '/tlbookmarks?page=' in self.path or \
       self.path.endswith('/bookmarks') or \
       '/bookmarks?page=' in self.path:
        if _show_bookmarks_timeline(self, authorized,
                                    calling_domain, referer_domain,
                                    self.path,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.port,
                                    getreq_start_time,
                                    cookie, self.server.debug,
                                    curr_session, ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show bookmarks 2 done',
                        self.server.debug)

    # outbox timeline
    if self.path.endswith('/outbox') or \
       '/outbox?page=' in self.path:
        if _show_outbox_timeline(self, authorized,
                                 calling_domain, referer_domain,
                                 self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.port,
                                 getreq_start_time,
                                 cookie, self.server.debug,
                                 curr_session, ua_str,
                                 proxy_type):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show outbox done',
                        self.server.debug)

    # get the moderation feed for a moderator
    if self.path.endswith('/moderation') or \
       '/moderation?' in self.path:
        if _show_mod_timeline(self, authorized,
                              calling_domain, referer_domain,
                              self.path,
                              self.server.base_dir,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.port,
                              getreq_start_time,
                              cookie, self.server.debug,
                              curr_session, ua_str):
            self.server.getreq_busy = False
            return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show moderation done',
                        self.server.debug)

    if _show_shares_feed(self, authorized,
                         calling_domain, referer_domain,
                         self.path,
                         self.server.base_dir,
                         self.server.http_prefix,
                         self.server.domain,
                         self.server.port,
                         getreq_start_time,
                         proxy_type,
                         cookie, self.server.debug, 'shares',
                         curr_session):
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show profile 2 done',
                        self.server.debug)

    if _show_following_feed(self, authorized,
                            calling_domain, referer_domain,
                            self.path,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.port,
                            getreq_start_time,
                            proxy_type,
                            cookie, self.server.debug,
                            curr_session):
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show profile 3 done',
                        self.server.debug)

    if _show_moved_feed(self, authorized,
                        calling_domain, referer_domain,
                        self.path,
                        self.server.base_dir,
                        self.server.http_prefix,
                        self.server.domain,
                        self.server.port,
                        getreq_start_time,
                        proxy_type,
                        cookie, self.server.debug,
                        curr_session):
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show moved 4 done',
                        self.server.debug)

    if _show_inactive_feed(self, authorized,
                           calling_domain, referer_domain,
                           self.path,
                           self.server.base_dir,
                           self.server.http_prefix,
                           self.server.domain,
                           self.server.port,
                           getreq_start_time,
                           proxy_type,
                           cookie, self.server.debug,
                           curr_session,
                           self.server.dormant_months,
                           self.server.sites_unavailable):
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show inactive 5 done',
                        self.server.debug)

    if _show_followers_feed(self, authorized,
                            calling_domain, referer_domain,
                            self.path,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.port,
                            getreq_start_time,
                            proxy_type,
                            cookie, self.server.debug,
                            curr_session):
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show profile 5 done',
                        self.server.debug)

    # look up a person
    if _show_person_profile(self, authorized,
                            calling_domain, referer_domain,
                            self.path,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domain,
                            self.server.onion_domain,
                            self.server.i2p_domain,
                            getreq_start_time,
                            proxy_type,
                            cookie, self.server.debug,
                            curr_session):
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'show profile posts done',
                        self.server.debug)

    # check that a json file was requested
    if not self.path.endswith('.json'):
        if self.server.debug:
            print('DEBUG: GET Not json: ' + self.path +
                  ' ' + self.server.base_dir)
        http_404(self, 142)
        self.server.getreq_busy = False
        return

    if not secure_mode(curr_session,
                       proxy_type, False,
                       self.server, self.headers,
                       self.path):
        if self.server.debug:
            print('WARN: Unauthorized GET')
        http_404(self, 143)
        self.server.getreq_busy = False
        return

    fitness_performance(getreq_start_time, self.server.fitness,
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
            try:
                content_json = json.loads(content)
            except json.decoder.JSONDecodeError as ex:
                http_400(self)
                print('EX: json decode error ' + str(ex) +
                      ' from GET content_json ' +
                      str(content))
                self.server.getreq_busy = False
                return

            msg_str = json.dumps(content_json, ensure_ascii=False)
            msg_str = convert_domains(calling_domain,
                                      referer_domain,
                                      msg_str,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.onion_domain,
                                      self.server.i2p_domain)
            msg = msg_str.encode('utf-8')
            msglen = len(msg)
            accept_str = self.headers['Accept']
            protocol_str = \
                get_json_content_from_accept(accept_str)
            set_headers(self, protocol_str, msglen,
                        None, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', 'arbitrary json',
                                self.server.debug)
    else:
        if self.server.debug:
            print('DEBUG: GET Unknown file')
        http_404(self, 144)
    self.server.getreq_busy = False

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', 'end benchmarks',
                        self.server.debug)


def _permitted_crawler_path(self, path: str) -> bool:
    """Is the given path permitted to be crawled by a search engine?
    this should only allow through basic information, such as nodeinfo
    """
    if path == '/' or path == '/about' or path == '/login' or \
       path.startswith('/blog/'):
        return True
    return False


def _get_referer_domain(self, ua_str: str) -> str:
    """Returns the referer domain
    Which domain is the GET request coming from?
    """
    referer_domain = None
    if self.headers.get('referer'):
        referer_domain = \
            user_agent_domain(self.headers['referer'], self.server.debug)
    elif self.headers.get('Referer'):
        referer_domain = \
            user_agent_domain(self.headers['Referer'], self.server.debug)
    elif self.headers.get('Signature'):
        if 'keyId="' in self.headers['Signature']:
            referer_domain = self.headers['Signature'].split('keyId="')[1]
            if '/' in referer_domain:
                referer_domain = referer_domain.split('/')[0]
            elif '#' in referer_domain:
                referer_domain = referer_domain.split('#')[0]
            elif '"' in referer_domain:
                referer_domain = referer_domain.split('"')[0]
    elif ua_str:
        referer_domain = user_agent_domain(ua_str, self.server.debug)
    return referer_domain


def _show_vcard(self, base_dir: str, path: str, calling_domain: str,
                referer_domain: str, domain: str) -> bool:
    """Returns a vcard for the given account
    """
    if not has_accept(self, calling_domain):
        return False
    if path.endswith('.vcf'):
        path = path.split('.vcf')[0]
        accept_str = 'text/vcard'
    else:
        accept_str = self.headers['Accept']
    if 'text/vcard' not in accept_str and \
       'application/vcard+xml' not in accept_str:
        return False
    if path.startswith('/@'):
        if '/@/' not in path:
            path = path.replace('/@', '/users/', 1)
    if not path.startswith('/users/'):
        http_400(self)
        return True
    nickname = path.split('/users/')[1]
    if '/' in nickname:
        nickname = nickname.split('/')[0]
    if '?' in nickname:
        nickname = nickname.split('?')[0]
    if self.server.vcard_is_active:
        print('vcard is busy during request from ' + str(referer_domain))
        http_503(self)
        return True
    self.server.vcard_is_active = True
    actor_json = None
    actor_filename = \
        acct_dir(base_dir, nickname, domain) + '.json'
    if os.path.isfile(actor_filename):
        actor_json = load_json(actor_filename)
    if not actor_json:
        print('WARN: vcard actor not found ' + actor_filename)
        http_404(self, 3)
        self.server.vcard_is_active = False
        return True
    if 'application/vcard+xml' in accept_str:
        vcard_str = actor_to_vcard_xml(actor_json, domain)
        header_type = 'application/vcard+xml; charset=utf-8'
    else:
        vcard_str = actor_to_vcard(actor_json, domain)
        header_type = 'text/vcard; charset=utf-8'
    if vcard_str:
        msg = vcard_str.encode('utf-8')
        msglen = len(msg)
        set_headers(self, header_type, msglen,
                    None, calling_domain, True)
        write2(self, msg)
        print('vcard sent to ' + str(referer_domain))
        self.server.vcard_is_active = False
        return True
    print('WARN: vcard string not returned')
    http_404(self, 4)
    self.server.vcard_is_active = False
    return True


def _nodeinfo(self, ua_str: str, calling_domain: str,
              referer_domain: str,
              http_prefix: str, calling_site_timeout: int,
              debug: bool) -> bool:
    if self.path.startswith('/nodeinfo/1.0'):
        http_400(self)
        return True
    if not self.path.startswith('/nodeinfo/2.'):
        return False
    if not referer_domain:
        if not debug and not self.server.unit_test:
            print('nodeinfo request has no referer domain ' + str(ua_str))
            http_400(self)
            return True
    if referer_domain == self.server.domain_full:
        print('nodeinfo request from self')
        http_400(self)
        return True
    if self.server.nodeinfo_is_active:
        if not referer_domain:
            print('nodeinfo is busy during request without referer domain')
        else:
            print('nodeinfo is busy during request from ' + referer_domain)
        http_503(self)
        return True
    self.server.nodeinfo_is_active = True
    # is this a real website making the call ?
    if not debug and not self.server.unit_test and referer_domain:
        # Does calling_domain look like a domain?
        if ' ' in referer_domain or \
           ';' in referer_domain or \
           '.' not in referer_domain:
            print('nodeinfo referer domain does not look like a domain ' +
                  referer_domain)
            http_400(self)
            self.server.nodeinfo_is_active = False
            return True
        if not self.server.allow_local_network_access:
            if local_network_host(referer_domain):
                print('nodeinfo referer domain is from the ' +
                      'local network ' + referer_domain)
                http_400(self)
                self.server.nodeinfo_is_active = False
                return True

        if not referer_is_active(http_prefix,
                                 referer_domain, ua_str,
                                 calling_site_timeout,
                                 self.server.sites_unavailable):
            print('nodeinfo referer url is not active ' +
                  referer_domain)
            http_400(self)
            self.server.nodeinfo_is_active = False
            return True
    if self.server.debug:
        print('DEBUG: nodeinfo ' + self.path)
    crawl_time = \
        update_known_crawlers(ua_str,
                              self.server.base_dir,
                              self.server.known_crawlers,
                              self.server.last_known_crawler)
    if crawl_time is not None:
        self.server.last_known_crawler = crawl_time

    # If we are in broch mode then don't show potentially
    # sensitive metadata.
    # For example, if this or allied instances are being attacked
    # then numbers of accounts may be changing as people
    # migrate, and that information may be useful to an adversary
    broch_mode = broch_mode_is_active(self.server.base_dir)

    node_info_version = self.server.project_version
    if not self.server.show_node_info_version or broch_mode:
        node_info_version = '0.0.0'

    show_node_info_accounts = self.server.show_node_info_accounts
    if broch_mode:
        show_node_info_accounts = False

    instance_url = get_instance_url(calling_domain,
                                    self.server.http_prefix,
                                    self.server.domain_full,
                                    self.server.onion_domain,
                                    self.server.i2p_domain)
    about_url = instance_url + '/about'
    terms_of_service_url = instance_url + '/terms'
    info = meta_data_node_info(self.server.base_dir,
                               about_url, terms_of_service_url,
                               self.server.registration,
                               node_info_version,
                               show_node_info_accounts)
    if info:
        msg_str = json.dumps(info)
        msg_str = convert_domains(calling_domain, referer_domain,
                                  msg_str, http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        protocol_str = \
            'application/json; profile=' + \
            '"http://nodeinfo.diaspora.software/ns/schema/2.1#"'
        set_headers(self, protocol_str, msglen,
                    None, calling_domain, True)
        write2(self, msg)
        if referer_domain:
            print('nodeinfo sent to ' + referer_domain)
        else:
            print('nodeinfo sent to unknown referer')
        self.server.nodeinfo_is_active = False
        return True
    http_404(self, 5)
    self.server.nodeinfo_is_active = False
    return True


def _security_txt(self, ua_str: str, calling_domain: str,
                  referer_domain: str,
                  http_prefix: str, calling_site_timeout: int,
                  debug: bool) -> bool:
    """See https://www.rfc-editor.org/rfc/rfc9116
    """
    if not self.path.startswith('/security.txt'):
        return False
    if referer_domain == self.server.domain_full:
        print('security.txt request from self')
        http_400(self)
        return True
    if self.server.security_txt_is_active:
        if not referer_domain:
            print('security.txt is busy ' +
                  'during request without referer domain')
        else:
            print('security.txt is busy during request from ' +
                  referer_domain)
        http_503(self)
        return True
    self.server.security_txt_is_active = True
    # is this a real website making the call ?
    if not debug and not self.server.unit_test and referer_domain:
        # Does calling_domain look like a domain?
        if ' ' in referer_domain or \
           ';' in referer_domain or \
           '.' not in referer_domain:
            print('security.txt ' +
                  'referer domain does not look like a domain ' +
                  referer_domain)
            http_400(self)
            self.server.security_txt_is_active = False
            return True
        if not self.server.allow_local_network_access:
            if local_network_host(referer_domain):
                print('security.txt referer domain is from the ' +
                      'local network ' + referer_domain)
                http_400(self)
                self.server.security_txt_is_active = False
                return True

        if not referer_is_active(http_prefix,
                                 referer_domain, ua_str,
                                 calling_site_timeout,
                                 self.server.sites_unavailable):
            print('security.txt referer url is not active ' +
                  referer_domain)
            http_400(self)
            self.server.security_txt_is_active = False
            return True
    if self.server.debug:
        print('DEBUG: security.txt ' + self.path)

    # If we are in broch mode then don't reply
    if not broch_mode_is_active(self.server.base_dir):
        security_txt = \
            'Contact: https://gitlab.com/bashrc2/epicyon/-/issues'

        msg = security_txt.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/plain; charset=utf-8',
                    msglen, None, calling_domain, True)
        write2(self, msg)
        if referer_domain:
            print('security.txt sent to ' + referer_domain)
        else:
            print('security.txt sent to unknown referer')
    self.server.security_txt_is_active = False
    return True


def _show_instance_actor(self, calling_domain: str,
                         referer_domain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str,
                         onion_domain: str, i2p_domain: str,
                         getreq_start_time,
                         cookie: str, debug: str,
                         enable_shared_inbox: bool) -> bool:
    """Shows the instance actor
    """
    if debug:
        print('Instance actor requested by ' + calling_domain)
    if request_http(self.headers, debug):
        http_404(self, 88)
        return False
    actor_json = person_lookup(domain, path, base_dir)
    if not actor_json:
        print('ERROR: no instance actor found')
        http_404(self, 89)
        return False
    accept_str = self.headers['Accept']
    actor_domain_url = get_instance_url(calling_domain,
                                        http_prefix, domain_full,
                                        onion_domain, i2p_domain)
    actor_url = actor_domain_url + '/users/Actor'
    remove_fields = (
        'icon', 'image', 'tts', 'shares',
        'alsoKnownAs', 'hasOccupation', 'featured',
        'featuredTags', 'discoverable', 'published',
        'devices'
    )
    for rfield in remove_fields:
        if rfield in actor_json:
            del actor_json[rfield]
    actor_json['endpoints'] = {}
    if enable_shared_inbox:
        actor_json['endpoints'] = {
            'sharedInbox': actor_domain_url + '/inbox'
        }
    actor_json['name'] = 'ACTOR'
    actor_json['preferredUsername'] = domain_full
    actor_json['id'] = actor_domain_url + '/actor'
    actor_json['type'] = 'Application'
    actor_json['summary'] = 'Instance Actor'
    actor_json['publicKey']['id'] = actor_domain_url + '/actor#main-key'
    actor_json['publicKey']['owner'] = actor_domain_url + '/actor'
    actor_json['url'] = actor_domain_url + '/actor'
    actor_json['inbox'] = actor_url + '/inbox'
    actor_json['followers'] = actor_url + '/followers'
    actor_json['following'] = actor_url + '/following'
    msg_str = json.dumps(actor_json, ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str, http_prefix,
                              domain,
                              self.server.onion_domain,
                              self.server.i2p_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    if 'application/ld+json' in accept_str:
        set_headers(self, 'application/ld+json', msglen,
                    cookie, calling_domain, False)
    elif 'application/jrd+json' in accept_str:
        set_headers(self, 'application/jrd+json', msglen,
                    cookie, calling_domain, False)
    else:
        set_headers(self, 'application/activity+json', msglen,
                    cookie, calling_domain, False)
    write2(self, msg)
    fitness_performance(getreq_start_time,
                        self.server.fitness,
                        '_GET', '_show_instance_actor',
                        debug)
    return True


def _progressive_web_app_manifest(self, base_dir: str,
                                  calling_domain: str,
                                  referer_domain: str,
                                  getreq_start_time) -> None:
    """gets the PWA manifest
    """
    manifest = pwa_manifest(base_dir)
    msg_str = json.dumps(manifest, ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.onion_domain,
                              self.server.i2p_domain)
    msg = msg_str.encode('utf-8')

    msglen = len(msg)
    protocol_str = \
        get_json_content_from_accept(self.headers['Accept'])
    set_headers(self, protocol_str, msglen,
                None, calling_domain, False)
    write2(self, msg)
    if self.server.debug:
        print('Sent manifest: ' + calling_domain)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_progressive_web_app_manifest',
                        self.server.debug)


def _browser_config(self, calling_domain: str, referer_domain: str,
                    getreq_start_time) -> None:
    """Used by MS Windows to put an icon on the desktop if you
    link to a website
    """
    xml_str = \
        '<?xml version="1.0" encoding="utf-8"?>\n' + \
        '<browserconfig>\n' + \
        '  <msapplication>\n' + \
        '    <tile>\n' + \
        '      <square150x150logo src="/logo150.png"/>\n' + \
        '      <TileColor>#eeeeee</TileColor>\n' + \
        '    </tile>\n' + \
        '  </msapplication>\n' + \
        '</browserconfig>'

    msg_str = json.dumps(xml_str, ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.onion_domain,
                              self.server.i2p_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    set_headers(self, 'application/xrd+xml', msglen,
                None, calling_domain, False)
    write2(self, msg)
    if self.server.debug:
        print('Sent browserconfig: ' + calling_domain)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_browser_config',
                        self.server.debug)


def _get_favicon(self, calling_domain: str,
                 base_dir: str, debug: bool,
                 fav_filename: str) -> None:
    """Return the site favicon or default newswire favicon
    """
    fav_type = 'image/x-icon'
    if has_accept(self, calling_domain):
        if 'image/webp' in self.headers['Accept']:
            fav_type = 'image/webp'
            fav_filename = fav_filename.split('.')[0] + '.webp'
        if 'image/avif' in self.headers['Accept']:
            fav_type = 'image/avif'
            fav_filename = fav_filename.split('.')[0] + '.avif'
        if 'image/heic' in self.headers['Accept']:
            fav_type = 'image/heic'
            fav_filename = fav_filename.split('.')[0] + '.heic'
        if 'image/jxl' in self.headers['Accept']:
            fav_type = 'image/jxl'
            fav_filename = fav_filename.split('.')[0] + '.jxl'
    if not self.server.theme_name:
        self.theme_name = get_config_param(base_dir, 'theme')
    if not self.server.theme_name:
        self.server.theme_name = 'default'
    # custom favicon
    favicon_filename = \
        base_dir + '/theme/' + self.server.theme_name + \
        '/icons/' + fav_filename
    if not fav_filename.endswith('.ico'):
        if not os.path.isfile(favicon_filename):
            if fav_filename.endswith('.webp'):
                fav_filename = fav_filename.replace('.webp', '.ico')
            elif fav_filename.endswith('.avif'):
                fav_filename = fav_filename.replace('.avif', '.ico')
            elif fav_filename.endswith('.heic'):
                fav_filename = fav_filename.replace('.heic', '.ico')
            elif fav_filename.endswith('.jxl'):
                fav_filename = fav_filename.replace('.jxl', '.ico')
    if not os.path.isfile(favicon_filename):
        # default favicon
        favicon_filename = \
            base_dir + '/theme/default/icons/' + fav_filename
    if etag_exists(self, favicon_filename):
        # The file has not changed
        if debug:
            print('favicon icon has not changed: ' + calling_domain)
        http_304(self)
        return
    if self.server.iconsCache.get(fav_filename):
        fav_binary = self.server.iconsCache[fav_filename]
        set_headers_etag(self, favicon_filename,
                         fav_type,
                         fav_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, fav_binary)
        if debug:
            print('Sent favicon from cache: ' + calling_domain)
        return
    if os.path.isfile(favicon_filename):
        fav_binary = None
        try:
            with open(favicon_filename, 'rb') as fav_file:
                fav_binary = fav_file.read()
        except OSError:
            print('EX: unable to read favicon ' + favicon_filename)
        if fav_binary:
            set_headers_etag(self, favicon_filename,
                             fav_type,
                             fav_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, fav_binary)
            self.server.iconsCache[fav_filename] = fav_binary
            if self.server.debug:
                print('Sent favicon from file: ' + calling_domain)
            return
    if debug:
        print('favicon not sent: ' + calling_domain)
    http_404(self, 17)


def _show_conversation_thread(self, authorized: bool,
                              calling_domain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, port: int,
                              debug: str, curr_session,
                              cookie: str) -> bool:
    """get conversation thread from the date link on a post
    """
    if not path.startswith('/users/'):
        return False
    if '?convthread=' not in path:
        return False
    post_id = path.split('?convthread=')[1].strip()
    post_id = post_id.replace('--', '/')
    if post_id.startswith('/users/'):
        instance_url = get_instance_url(calling_domain,
                                        self.server.http_prefix,
                                        self.server.domain_full,
                                        self.server.onion_domain,
                                        self.server.i2p_domain)
        post_id = instance_url + post_id
    nickname = path.split('/users/')[1]
    if '?convthread=' in nickname:
        nickname = nickname.split('?convthread=')[0]
    if '/' in nickname:
        nickname = nickname.split('/')[0]
    timezone = None
    if self.server.account_timezone.get(nickname):
        timezone = \
            self.server.account_timezone.get(nickname)
    bold_reading = False
    if self.server.bold_reading.get(nickname):
        bold_reading = True
    conv_str = \
        html_conversation_view(authorized,
                               post_id, self.server.translate,
                               base_dir,
                               http_prefix,
                               nickname,
                               domain,
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
                               self.server.theme_name,
                               self.server.system_language,
                               self.server.max_like_count,
                               self.server.signing_priv_key_pem,
                               self.server.cw_lists,
                               self.server.lists_enabled,
                               timezone, bold_reading,
                               self.server.dogwhistles,
                               self.server.access_keys,
                               self.server.min_images_for_accounts,
                               debug,
                               self.server.buy_sites,
                               self.server.blocked_cache,
                               self.server.block_federated,
                               self.server.auto_cw_cache)
    if conv_str:
        msg = conv_str.encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        self.server.getreq_busy = False
        return True
    # redirect to the original site if there are no results
    if '://' + self.server.domain_full + '/' in post_id:
        redirect_headers(self, post_id, cookie, calling_domain)
    else:
        redirect_headers(self, post_id, None, calling_domain)
    self.server.getreq_busy = False
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
               custom_emoji: [],
               show_node_info_accounts: bool,
               referer_domain: str, debug: bool,
               known_crawlers: {},
               sites_unavailable: []) -> bool:
    if _masto_api_v2(self, path, calling_domain, ua_str, authorized,
                     http_prefix, base_dir, nickname, domain,
                     domain_full, onion_domain, i2p_domain,
                     translate, registration, system_language,
                     project_version,
                     show_node_info_accounts,
                     referer_domain, debug, 5,
                     known_crawlers, sites_unavailable):
        return True
    return _masto_api_v1(self, path, calling_domain, ua_str, authorized,
                         http_prefix, base_dir, nickname, domain,
                         domain_full, onion_domain, i2p_domain,
                         translate, registration, system_language,
                         project_version, custom_emoji,
                         show_node_info_accounts,
                         referer_domain, debug, 5,
                         known_crawlers, sites_unavailable)


def _show_cached_favicon(self, referer_domain: str, path: str,
                         base_dir: str, getreq_start_time) -> None:
    """Shows a favicon image obtained from the cache
    """
    fav_file = path.replace('/favicons/', '')
    fav_filename = base_dir + urllib.parse.unquote_plus(path)
    print('showCachedFavicon: ' + fav_filename)
    if self.server.favicons_cache.get(fav_file):
        media_binary = self.server.favicons_cache[fav_file]
        mime_type = media_file_mime_type(fav_filename)
        set_headers_etag(self, fav_filename,
                         mime_type,
                         media_binary, None,
                         referer_domain,
                         False, None)
        write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_cached_favicon2',
                            self.server.debug)
        return
    if not os.path.isfile(fav_filename):
        http_404(self, 44)
        return
    if etag_exists(self, fav_filename):
        # The file has not changed
        http_304(self)
        return
    media_binary = None
    try:
        with open(fav_filename, 'rb') as av_file:
            media_binary = av_file.read()
    except OSError:
        print('EX: unable to read cached favicon ' + fav_filename)
    if media_binary:
        if binary_is_image(fav_filename, media_binary):
            mime_type = media_file_mime_type(fav_filename)
            set_headers_etag(self, fav_filename,
                             mime_type,
                             media_binary, None,
                             referer_domain,
                             False, None)
            write2(self, media_binary)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_cached_favicon',
                                self.server.debug)
            self.server.favicons_cache[fav_file] = media_binary
            return
        else:
            print('WARN: favicon is not an image ' + fav_filename)
    http_404(self, 45)


def _get_style_sheet(self, base_dir: str, calling_domain: str, path: str,
                     getreq_start_time) -> bool:
    """Returns the content of a css file
    """
    # get the last part of the path
    # eg. /my/path/file.css becomes file.css
    if '/' in path:
        path = path.split('/')[-1]
    path = base_dir + '/' + path
    css = None
    if self.server.css_cache.get(path):
        css = self.server.css_cache[path]
    elif os.path.isfile(path):
        tries = 0
        while tries < 5:
            try:
                css = get_css(self.server.base_dir, path)
                if css:
                    self.server.css_cache[path] = css
                    break
            except BaseException as ex:
                print('EX: _get_style_sheet ' + path + ' ' +
                      str(tries) + ' ' + str(ex))
                time.sleep(1)
                tries += 1
    if css:
        msg = css.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/css', msglen,
                    None, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time,
                            self.server.fitness,
                            '_GET', '_get_style_sheet',
                            self.server.debug)
        return True
    http_404(self, 92)
    return True


def _get_exported_blocks(self, path: str, base_dir: str,
                         domain: str,
                         calling_domain: str) -> None:
    """Returns an exported blocks csv file
    """
    filename = path.split('/exports/', 1)[1]
    filename = base_dir + '/exports/' + filename
    nickname = get_nickname_from_actor(path)
    if nickname:
        blocks_str = export_blocking_file(base_dir, nickname, domain)
        if blocks_str:
            msg = blocks_str.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/csv',
                        msglen, None, calling_domain, False)
            write2(self, msg)
            return
    http_404(self, 20)


def _get_exported_theme(self, path: str, base_dir: str,
                        domain_full: str) -> None:
    """Returns an exported theme zip file
    """
    filename = path.split('/exports/', 1)[1]
    filename = base_dir + '/exports/' + filename
    if os.path.isfile(filename):
        export_binary = None
        try:
            with open(filename, 'rb') as fp_exp:
                export_binary = fp_exp.read()
        except OSError:
            print('EX: unable to read theme export ' + filename)
        if export_binary:
            export_type = 'application/zip'
            set_headers_etag(self, filename, export_type,
                             export_binary, None,
                             domain_full, False, None)
            write2(self, export_binary)
    http_404(self, 19)


def _get_fonts(self, calling_domain: str, path: str,
               base_dir: str, debug: bool,
               getreq_start_time) -> None:
    """Returns a font
    """
    font_str = path.split('/fonts/')[1]
    if font_str.endswith('.otf') or \
       font_str.endswith('.ttf') or \
       font_str.endswith('.woff') or \
       font_str.endswith('.woff2'):
        if font_str.endswith('.otf'):
            font_type = 'font/otf'
        elif font_str.endswith('.ttf'):
            font_type = 'font/ttf'
        elif font_str.endswith('.woff'):
            font_type = 'font/woff'
        else:
            font_type = 'font/woff2'
        font_filename = \
            base_dir + '/fonts/' + font_str
        if etag_exists(self, font_filename):
            # The file has not changed
            http_304(self)
            return
        if self.server.fontsCache.get(font_str):
            font_binary = self.server.fontsCache[font_str]
            set_headers_etag(self, font_filename,
                             font_type,
                             font_binary, None,
                             self.server.domain_full, False, None)
            write2(self, font_binary)
            if debug:
                print('font sent from cache: ' +
                      path + ' ' + calling_domain)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_get_fonts cache',
                                debug)
            return
        if os.path.isfile(font_filename):
            font_binary = None
            try:
                with open(font_filename, 'rb') as fontfile:
                    font_binary = fontfile.read()
            except OSError:
                print('EX: unable to load font ' + font_filename)
            if font_binary:
                set_headers_etag(self, font_filename,
                                 font_type,
                                 font_binary, None,
                                 self.server.domain_full,
                                 False, None)
                write2(self, font_binary)
                self.server.fontsCache[font_str] = font_binary
            if debug:
                print('font sent from file: ' +
                      path + ' ' + calling_domain)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_get_fonts', debug)
            return
    if debug:
        print('font not found: ' + path + ' ' + calling_domain)
    http_404(self, 21)


def _get_hashtag_categories_feed(self, calling_domain: str, path: str,
                                 base_dir: str, proxy_type: str,
                                 getreq_start_time,
                                 debug: bool,
                                 curr_session) -> None:
    """Returns the hashtag categories feed
    """
    curr_session = \
        establish_session("get_hashtag_categories_feed",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 27)
        return

    hashtag_categories = None
    msg = \
        get_hashtag_categories_feed(base_dir, hashtag_categories)
    if msg:
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/xml', msglen,
                    None, calling_domain, True)
        write2(self, msg)
        if debug:
            print('Sent rss2 categories feed: ' +
                  path + ' ' + calling_domain)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_get_hashtag_categories_feed', debug)
        return
    if debug:
        print('Failed to get rss2 categories feed: ' +
              path + ' ' + calling_domain)
    http_404(self, 28)


def _get_newswire_feed(self, calling_domain: str, path: str,
                       proxy_type: str, getreq_start_time,
                       debug: bool, curr_session) -> None:
    """Returns the newswire feed
    """
    curr_session = \
        establish_session("get_newswire_feed",
                          curr_session,
                          proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 25)
        return

    msg = get_rs_sfrom_dict(self.server.newswire,
                            self.server.http_prefix,
                            self.server.domain_full,
                            self.server.translate)
    if msg:
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/xml', msglen,
                    None, calling_domain, True)
        write2(self, msg)
        if debug:
            print('Sent rss2 newswire feed: ' +
                  path + ' ' + calling_domain)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_get_newswire_feed',
                            debug)
        return
    if debug:
        print('Failed to get rss2 newswire feed: ' +
              path + ' ' + calling_domain)
    http_404(self, 26)


def _get_rss2feed(self, calling_domain: str, path: str,
                  base_dir: str, http_prefix: str,
                  domain: str, port: int, proxy_type: str,
                  getreq_start_time, debug: bool,
                  curr_session) -> None:
    """Returns an RSS2 feed for the blog
    """
    nickname = path.split('/blog/')[1]
    if '/' in nickname:
        nickname = nickname.split('/')[0]
    if not nickname.startswith('rss.'):
        account_dir = acct_dir(self.server.base_dir, nickname, domain)
        if os.path.isdir(account_dir):
            curr_session = \
                establish_session("RSS request",
                                  curr_session,
                                  proxy_type,
                                  self.server)
            if not curr_session:
                return

            msg = \
                html_blog_page_rss2(base_dir,
                                    http_prefix,
                                    self.server.translate,
                                    nickname,
                                    domain,
                                    port,
                                    MAX_POSTS_IN_RSS_FEED, 1,
                                    True,
                                    self.server.system_language)
            if msg is not None:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/xml', msglen,
                            None, calling_domain, True)
                write2(self, msg)
                if debug:
                    print('Sent rss2 feed: ' +
                          path + ' ' + calling_domain)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', '_get_rss2feed',
                                    debug)
                return
    if debug:
        print('Failed to get rss2 feed: ' +
              path + ' ' + calling_domain)
    http_404(self, 22)


def _get_rss2site(self, calling_domain: str, path: str,
                  base_dir: str, http_prefix: str,
                  domain_full: str, port: int, proxy_type: str,
                  translate: {},
                  getreq_start_time,
                  debug: bool,
                  curr_session) -> None:
    """Returns an RSS2 feed for all blogs on this instance
    """
    curr_session = \
        establish_session("get_rss2site",
                          curr_session,
                          proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 23)
        return

    msg = ''
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            nickname = acct.split('@')[0]
            domain = acct.split('@')[1]
            msg += \
                html_blog_page_rss2(base_dir,
                                    http_prefix,
                                    self.server.translate,
                                    nickname,
                                    domain,
                                    port,
                                    MAX_POSTS_IN_RSS_FEED, 1,
                                    False,
                                    self.server.system_language)
        break
    if msg:
        msg = rss2header(http_prefix,
                         'news', domain_full,
                         'Site', translate) + msg + rss2footer()

        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/xml', msglen,
                    None, calling_domain, True)
        write2(self, msg)
        if debug:
            print('Sent rss2 feed: ' +
                  path + ' ' + calling_domain)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_get_rss2site',
                            debug)
        return
    if debug:
        print('Failed to get rss2 feed: ' +
              path + ' ' + calling_domain)
    http_404(self, 24)


def _get_rss3feed(self, calling_domain: str, path: str,
                  base_dir: str, http_prefix: str,
                  domain: str, port: int, proxy_type: str,
                  getreq_start_time,
                  debug: bool, system_language: str,
                  curr_session) -> None:
    """Returns an RSS3 feed
    """
    nickname = path.split('/blog/')[1]
    if '/' in nickname:
        nickname = nickname.split('/')[0]
    if not nickname.startswith('rss.'):
        account_dir = acct_dir(base_dir, nickname, domain)
        if os.path.isdir(account_dir):
            curr_session = \
                establish_session("get_rss3feed",
                                  curr_session, proxy_type,
                                  self.server)
            if not curr_session:
                http_404(self, 29)
                return
            msg = \
                html_blog_page_rss3(base_dir, http_prefix,
                                    nickname, domain, port,
                                    MAX_POSTS_IN_RSS_FEED, 1,
                                    system_language)
            if msg is not None:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/plain; charset=utf-8',
                            msglen, None, calling_domain, True)
                write2(self, msg)
                if self.server.debug:
                    print('Sent rss3 feed: ' +
                          path + ' ' + calling_domain)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', '_get_rss3feed', debug)
                return
    if debug:
        print('Failed to get rss3 feed: ' +
              path + ' ' + calling_domain)
    http_404(self, 20)


def _get_following_json(self, base_dir: str, path: str,
                        calling_domain: str, referer_domain: str,
                        http_prefix: str,
                        domain: str, port: int,
                        following_items_per_page: int,
                        debug: bool, list_name: str = 'following') -> None:
    """Returns json collection for following.txt
    """
    following_json = \
        get_following_feed(base_dir, domain, port, path, http_prefix,
                           True, following_items_per_page, list_name)
    if not following_json:
        if debug:
            print(list_name + ' json feed not found for ' + path)
        http_404(self, 109)
        return
    msg_str = json.dumps(following_json,
                         ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str, http_prefix,
                              domain,
                              self.server.onion_domain,
                              self.server.i2p_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    accept_str = self.headers['Accept']
    protocol_str = \
        get_json_content_from_accept(accept_str)
    set_headers(self, protocol_str, msglen,
                None, calling_domain, False)
    write2(self, msg)


def _get_speaker(self, calling_domain: str, referer_domain: str,
                 path: str, base_dir: str, domain: str) -> None:
    """Returns the speaker file used for TTS and
    accessed via c2s
    """
    nickname = path.split('/users/')[1]
    if '/' in nickname:
        nickname = nickname.split('/')[0]
    speaker_filename = \
        acct_dir(base_dir, nickname, domain) + '/speaker.json'
    if not os.path.isfile(speaker_filename):
        http_404(self, 18)
        return

    speaker_json = load_json(speaker_filename)
    msg_str = json.dumps(speaker_json, ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str,
                              self.server.http_prefix,
                              domain,
                              self.server.onion_domain,
                              self.server.i2p_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    protocol_str = \
        get_json_content_from_accept(self.headers['Accept'])
    set_headers(self, protocol_str, msglen,
                None, calling_domain, False)
    write2(self, msg)


def _get_featured_collection(self, calling_domain: str,
                             referer_domain: str,
                             base_dir: str,
                             http_prefix: str,
                             nickname: str, domain: str,
                             domain_full: str,
                             system_language: str) -> None:
    """Returns the featured posts collections in
    actor/collections/featured
    """
    featured_collection = \
        json_pin_post(base_dir, http_prefix,
                      nickname, domain, domain_full, system_language)
    msg_str = json.dumps(featured_collection,
                         ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str, http_prefix,
                              domain,
                              self.server.onion_domain,
                              self.server.i2p_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    accept_str = self.headers['Accept']
    protocol_str = \
        get_json_content_from_accept(accept_str)
    set_headers(self, protocol_str, msglen,
                None, calling_domain, False)
    write2(self, msg)


def _get_featured_tags_collection(self, calling_domain: str,
                                  referer_domain: str,
                                  path: str,
                                  http_prefix: str,
                                  domain_full: str,
                                  domain: str):
    """Returns the featured tags collections in
    actor/collections/featuredTags
    """
    post_context = get_individual_post_context()
    featured_tags_collection = {
        '@context': post_context,
        'id': http_prefix + '://' + domain_full + path,
        'orderedItems': [],
        'totalItems': 0,
        'type': 'OrderedCollection'
    }
    msg_str = json.dumps(featured_tags_collection,
                         ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str, http_prefix,
                              domain,
                              self.server.onion_domain,
                              self.server.i2p_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    accept_str = self.headers['Accept']
    protocol_str = \
        get_json_content_from_accept(accept_str)
    set_headers(self, protocol_str, msglen,
                None, calling_domain, False)
    write2(self, msg)


def _show_blog_page(self, authorized: bool,
                    calling_domain: str, path: str,
                    base_dir: str, http_prefix: str,
                    domain: str, port: int,
                    getreq_start_time,
                    proxy_type: str, cookie: str,
                    translate: {}, debug: str,
                    curr_session) -> bool:
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
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
            if page_number < 1:
                page_number = 1
            elif page_number > 10:
                page_number = 10
    curr_session = \
        establish_session("showBlogPage",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 90)
        self.server.getreq_busy = False
        return True
    msg = html_blog_page(authorized,
                         curr_session,
                         base_dir,
                         http_prefix,
                         translate,
                         nickname,
                         domain, port,
                         MAX_POSTS_IN_BLOGS_FEED, page_number,
                         self.server.peertube_instances,
                         self.server.system_language,
                         self.server.person_cache,
                         debug)
    if msg is not None:
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time,
                            self.server.fitness,
                            '_GET', '_show_blog_page',
                            debug)
        return True
    http_404(self, 91)
    return True


def _redirect_to_login_screen(self, calling_domain: str, path: str,
                              http_prefix: str, domain_full: str,
                              onion_domain: str, i2p_domain: str,
                              getreq_start_time,
                              authorized: bool, debug: bool):
    """Redirects to the login screen if necessary
    """
    divert_to_login_screen = False
    if '/media/' not in path and \
       '/ontologies/' not in path and \
       '/data/' not in path and \
       '/sharefiles/' not in path and \
       '/statuses/' not in path and \
       '/emoji/' not in path and \
       '/tags/' not in path and \
       '/tagmaps/' not in path and \
       '/avatars/' not in path and \
       '/favicons/' not in path and \
       '/headers/' not in path and \
       '/fonts/' not in path and \
       '/icons/' not in path:
        divert_to_login_screen = True
        if path.startswith('/users/'):
            nick_str = path.split('/users/')[1]
            if '/' not in nick_str and '?' not in nick_str:
                divert_to_login_screen = False
            else:
                if path.endswith('/following') or \
                   path.endswith('/followers') or \
                   path.endswith('/skills') or \
                   path.endswith('/roles') or \
                   path.endswith('/wanted') or \
                   path.endswith('/shares'):
                    divert_to_login_screen = False

    if divert_to_login_screen and not authorized:
        divert_path = '/login'
        if self.server.news_instance:
            # for news instances if not logged in then show the
            # front page
            divert_path = '/users/news'
        if debug:
            print('DEBUG: divert_to_login_screen=' +
                  str(divert_to_login_screen))
            print('DEBUG: authorized=' + str(authorized))
            print('DEBUG: path=' + path)
        redirect_url = \
            get_instance_url(calling_domain,
                             http_prefix, domain_full,
                             onion_domain, i2p_domain) + \
            divert_path
        redirect_headers(self, redirect_url, None, calling_domain)
        fitness_performance(getreq_start_time,
                            self.server.fitness,
                            '_GET', '_redirect_to_login_screen',
                            debug)
        return True
    return False


def _show_qrcode(self, calling_domain: str, path: str,
                 base_dir: str, domain: str,
                 onion_domain: str, i2p_domain: str,
                 port: int, getreq_start_time) -> bool:
    """Shows a QR code for an account
    """
    nickname = get_nickname_from_actor(path)
    if not nickname:
        http_404(self, 93)
        return True
    if onion_domain:
        qrcode_domain = onion_domain
        port = 80
    elif i2p_domain:
        qrcode_domain = i2p_domain
        port = 80
    else:
        qrcode_domain = domain
    save_person_qrcode(base_dir, nickname, domain, qrcode_domain, port)
    qr_filename = \
        acct_dir(base_dir, nickname, domain) + '/qrcode.png'
    if os.path.isfile(qr_filename):
        if etag_exists(self, qr_filename):
            # The file has not changed
            http_304(self)
            return

        tries = 0
        media_binary = None
        while tries < 5:
            try:
                with open(qr_filename, 'rb') as av_file:
                    media_binary = av_file.read()
                    break
            except OSError as ex:
                print('EX: _show_qrcode ' + str(tries) + ' ' + str(ex))
                time.sleep(1)
                tries += 1
        if media_binary:
            mime_type = media_file_mime_type(qr_filename)
            set_headers_etag(self, qr_filename, mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            fitness_performance(getreq_start_time,
                                self.server.fitness,
                                '_GET', '_show_qrcode',
                                self.server.debug)
            return True
    http_404(self, 94)
    return True


def _search_screen_banner(self, path: str,
                          base_dir: str, domain: str,
                          getreq_start_time) -> bool:
    """Shows a banner image on the search screen
    """
    nickname = get_nickname_from_actor(path)
    if not nickname:
        http_404(self, 95)
        return True
    banner_filename = \
        acct_dir(base_dir, nickname, domain) + '/search_banner.png'
    if not os.path.isfile(banner_filename):
        if os.path.isfile(base_dir + '/theme/default/search_banner.png'):
            copyfile(base_dir + '/theme/default/search_banner.png',
                     banner_filename)
    if os.path.isfile(banner_filename):
        if etag_exists(self, banner_filename):
            # The file has not changed
            http_304(self)
            return True

        tries = 0
        media_binary = None
        while tries < 5:
            try:
                with open(banner_filename, 'rb') as av_file:
                    media_binary = av_file.read()
                    break
            except OSError as ex:
                print('EX: _search_screen_banner ' +
                      str(tries) + ' ' + str(ex))
                time.sleep(1)
                tries += 1
        if media_binary:
            mime_type = media_file_mime_type(banner_filename)
            set_headers_etag(self, banner_filename, mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            fitness_performance(getreq_start_time,
                                self.server.fitness,
                                '_GET', '_search_screen_banner',
                                self.server.debug)
            return True
    http_404(self, 96)
    return True


def _column_image(self, side: str, path: str, base_dir: str, domain: str,
                  getreq_start_time) -> bool:
    """Shows an image at the top of the left/right column
    """
    nickname = get_nickname_from_actor(path)
    if not nickname:
        http_404(self, 97)
        return True
    banner_filename = \
        acct_dir(base_dir, nickname, domain) + '/' + \
        side + '_col_image.png'
    if os.path.isfile(banner_filename):
        if etag_exists(self, banner_filename):
            # The file has not changed
            http_304(self)
            return True

        tries = 0
        media_binary = None
        while tries < 5:
            try:
                with open(banner_filename, 'rb') as av_file:
                    media_binary = av_file.read()
                    break
            except OSError as ex:
                print('EX: _column_image ' + str(tries) + ' ' + str(ex))
                time.sleep(1)
                tries += 1
        if media_binary:
            mime_type = media_file_mime_type(banner_filename)
            set_headers_etag(self, banner_filename, mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            fitness_performance(getreq_start_time,
                                self.server.fitness,
                                '_GET', '_column_image ' + side,
                                self.server.debug)
            return True
    http_404(self, 98)
    return True


def _show_default_profile_background(self, base_dir: str, theme_name: str,
                                     getreq_start_time) -> bool:
    """If a background image is missing after searching for a handle
    then substitute this image
    """
    image_extensions = get_image_extensions()
    for ext in image_extensions:
        bg_filename = \
            base_dir + '/theme/' + theme_name + '/image.' + ext
        if os.path.isfile(bg_filename):
            if etag_exists(self, bg_filename):
                # The file has not changed
                http_304(self)
                return True

            tries = 0
            bg_binary = None
            while tries < 5:
                try:
                    with open(bg_filename, 'rb') as av_file:
                        bg_binary = av_file.read()
                        break
                except OSError as ex:
                    print('EX: _show_default_profile_background ' +
                          str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if bg_binary:
                if ext == 'jpg':
                    ext = 'jpeg'
                set_headers_etag(self, bg_filename,
                                 'image/' + ext,
                                 bg_binary, None,
                                 self.server.domain_full,
                                 False, None)
                write2(self, bg_binary)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET',
                                    '_show_default_profile_background',
                                    self.server.debug)
                return True
            break

    http_404(self, 100)
    return True


def _show_background_image(self, path: str,
                           base_dir: str, getreq_start_time) -> bool:
    """Show a background image
    """
    image_extensions = get_image_extensions()
    for ext in image_extensions:
        for bg_im in ('follow', 'options', 'login', 'welcome'):
            # follow screen background image
            if path.endswith('/' + bg_im + '-background.' + ext):
                bg_filename = \
                    base_dir + '/accounts/' + \
                    bg_im + '-background.' + ext
                if os.path.isfile(bg_filename):
                    if etag_exists(self, bg_filename):
                        # The file has not changed
                        http_304(self)
                        return True

                    tries = 0
                    bg_binary = None
                    while tries < 5:
                        try:
                            with open(bg_filename, 'rb') as av_file:
                                bg_binary = av_file.read()
                                break
                        except OSError as ex:
                            print('EX: _show_background_image ' +
                                  str(tries) + ' ' + str(ex))
                            time.sleep(1)
                            tries += 1
                    if bg_binary:
                        if ext == 'jpg':
                            ext = 'jpeg'
                        set_headers_etag(self, bg_filename,
                                         'image/' + ext,
                                         bg_binary, None,
                                         self.server.domain_full,
                                         False, None)
                        write2(self, bg_binary)
                        fitness_performance(getreq_start_time,
                                            self.server.fitness,
                                            '_GET',
                                            '_show_background_image',
                                            self.server.debug)
                        return True
    http_404(self, 99)
    return True


def _show_emoji(self, path: str,
                base_dir: str, getreq_start_time) -> None:
    """Returns an emoji image
    """
    if is_image_file(path):
        emoji_str = path.split('/emoji/')[1]
        emoji_filename = base_dir + '/emoji/' + emoji_str
        if not os.path.isfile(emoji_filename):
            emoji_filename = base_dir + '/emojicustom/' + emoji_str
        if os.path.isfile(emoji_filename):
            if etag_exists(self, emoji_filename):
                # The file has not changed
                http_304(self)
                return

            media_image_type = get_image_mime_type(emoji_filename)
            media_binary = None
            try:
                with open(emoji_filename, 'rb') as av_file:
                    media_binary = av_file.read()
            except OSError:
                print('EX: unable to read emoji image ' + emoji_filename)
            if media_binary:
                set_headers_etag(self, emoji_filename,
                                 media_image_type,
                                 media_binary, None,
                                 self.server.domain_full,
                                 False, None)
                write2(self, media_binary)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_emoji', self.server.debug)
            return
    http_404(self, 36)


def _show_media(self, path: str, base_dir: str,
                getreq_start_time) -> None:
    """Returns a media file
    """
    if is_image_file(path) or \
       path_is_video(path) or \
       path_is_transcript(path) or \
       path_is_audio(path):
        media_str = path.split('/media/')[1]
        media_filename = base_dir + '/media/' + media_str
        if os.path.isfile(media_filename):
            if etag_exists(self, media_filename):
                # The file has not changed
                http_304(self)
                return

            media_file_type = media_file_mime_type(media_filename)

            media_tm = os.path.getmtime(media_filename)
            last_modified_time = \
                datetime.datetime.fromtimestamp(media_tm,
                                                datetime.timezone.utc)
            last_modified_time_str = \
                last_modified_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

            if media_filename.endswith('.vtt'):
                media_transcript = None
                try:
                    with open(media_filename, 'r',
                              encoding='utf-8') as fp_vtt:
                        media_transcript = fp_vtt.read()
                        media_file_type = 'text/vtt; charset=utf-8'
                except OSError:
                    print('EX: unable to read media binary ' +
                          media_filename)
                if media_transcript:
                    media_transcript = media_transcript.encode('utf-8')
                    set_headers_etag(self, media_filename, media_file_type,
                                     media_transcript, None,
                                     None, True,
                                     last_modified_time_str)
                    write2(self, media_transcript)
                    fitness_performance(getreq_start_time,
                                        self.server.fitness,
                                        '_GET', '_show_media',
                                        self.server.debug)
                    return
                http_404(self, 32)
                return

            media_binary = None
            try:
                with open(media_filename, 'rb') as av_file:
                    media_binary = av_file.read()
            except OSError:
                print('EX: unable to read media binary ' + media_filename)
            if media_binary:
                set_headers_etag(self, media_filename, media_file_type,
                                 media_binary, None,
                                 None, True,
                                 last_modified_time_str)
                write2(self, media_binary)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_media', self.server.debug)
            return
    http_404(self, 33)


def _get_ontology(self, calling_domain: str,
                  path: str, base_dir: str,
                  getreq_start_time) -> None:
    """Returns an ontology file
    """
    if '.owl' in path or '.rdf' in path or '.json' in path:
        if '/ontologies/' in path:
            ontology_str = path.split('/ontologies/')[1].replace('#', '')
        else:
            ontology_str = path.split('/data/')[1].replace('#', '')
        ontology_filename = None
        ontology_file_type = 'application/rdf+xml'
        if ontology_str.startswith('DFC_'):
            ontology_filename = base_dir + '/ontology/DFC/' + ontology_str
        else:
            ontology_str = ontology_str.replace('/data/', '')
            ontology_filename = base_dir + '/ontology/' + ontology_str
        if ontology_str.endswith('.json'):
            ontology_file_type = 'application/ld+json'
        if os.path.isfile(ontology_filename):
            ontology_file = None
            try:
                with open(ontology_filename, 'r',
                          encoding='utf-8') as fp_ont:
                    ontology_file = fp_ont.read()
            except OSError:
                print('EX: unable to read ontology ' + ontology_filename)
            if ontology_file:
                ontology_file = \
                    ontology_file.replace('static.datafoodconsortium.org',
                                          calling_domain)
                if not calling_domain.endswith('.i2p') and \
                   not calling_domain.endswith('.onion'):
                    ontology_file = \
                        ontology_file.replace('http://' +
                                              calling_domain,
                                              'https://' +
                                              calling_domain)
                msg = ontology_file.encode('utf-8')
                msglen = len(msg)
                set_headers(self, ontology_file_type, msglen,
                            None, calling_domain, False)
                write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_get_ontology', self.server.debug)
            return
    http_404(self, 34)


def _show_share_image(self, path: str,
                      base_dir: str, getreq_start_time) -> bool:
    """Show a shared item image
    """
    if not is_image_file(path):
        http_404(self, 101)
        return True

    media_str = path.split('/sharefiles/')[1]
    media_filename = base_dir + '/sharefiles/' + media_str
    if not os.path.isfile(media_filename):
        http_404(self, 102)
        return True

    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return True

    media_file_type = get_image_mime_type(media_filename)
    media_binary = None
    try:
        with open(media_filename, 'rb') as av_file:
            media_binary = av_file.read()
    except OSError:
        print('EX: unable to read binary ' + media_filename)
    if media_binary:
        set_headers_etag(self, media_filename,
                         media_file_type,
                         media_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, media_binary)
    fitness_performance(getreq_start_time,
                        self.server.fitness,
                        '_GET', '_show_share_image',
                        self.server.debug)
    return True


def _show_icon(self, path: str,
               base_dir: str, getreq_start_time) -> None:
    """Shows an icon
    """
    if not path.endswith('.png'):
        http_404(self, 37)
        return
    media_str = path.split('/icons/')[1]
    if '/' not in media_str:
        if not self.server.theme_name:
            theme = 'default'
        else:
            theme = self.server.theme_name
        icon_filename = media_str
    else:
        theme = media_str.split('/')[0]
        icon_filename = media_str.split('/')[1]
    media_filename = \
        base_dir + '/theme/' + theme + '/icons/' + icon_filename
    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return
    if self.server.iconsCache.get(media_str):
        media_binary = self.server.iconsCache[media_str]
        mime_type_str = media_file_mime_type(media_filename)
        set_headers_etag(self, media_filename,
                         mime_type_str,
                         media_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_icon', self.server.debug)
        return
    if os.path.isfile(media_filename):
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read icon image ' + media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            self.server.iconsCache[media_str] = media_binary
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_icon', self.server.debug)
        return
    http_404(self, 38)


def _show_specification_image(self, path: str,
                              base_dir: str, getreq_start_time) -> None:
    """Shows an image within the ActivityPub specification document
    """
    image_filename = path.split('/', 1)[1]
    if '/' in image_filename:
        http_404(self, 39)
        return
    media_filename = \
        base_dir + '/specification/' + image_filename
    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return
    if self.server.iconsCache.get(media_filename):
        media_binary = self.server.iconsCache[media_filename]
        mime_type_str = media_file_mime_type(media_filename)
        set_headers_etag(self, media_filename,
                         mime_type_str,
                         media_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_specification_image',
                            self.server.debug)
        return
    if os.path.isfile(media_filename):
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read specification image ' +
                  media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            self.server.iconsCache[media_filename] = media_binary
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_specification_image',
                            self.server.debug)
        return
    http_404(self, 40)


def _show_manual_image(self, path: str,
                       base_dir: str, getreq_start_time) -> None:
    """Shows an image within the manual
    """
    image_filename = path.split('/', 1)[1]
    if '/' in image_filename:
        http_404(self, 41)
        return
    media_filename = \
        base_dir + '/manual/' + image_filename
    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return
    if self.server.iconsCache.get(media_filename):
        media_binary = self.server.iconsCache[media_filename]
        mime_type_str = media_file_mime_type(media_filename)
        set_headers_etag(self, media_filename,
                         mime_type_str,
                         media_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_manual_image',
                            self.server.debug)
        return
    if os.path.isfile(media_filename):
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read manual image ' +
                  media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            self.server.iconsCache[media_filename] = media_binary
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_manual_image',
                            self.server.debug)
        return
    http_404(self, 42)


def _show_help_screen_image(self, path: str,
                            base_dir: str, getreq_start_time) -> None:
    """Shows a help screen image
    """
    if not is_image_file(path):
        return
    media_str = path.split('/helpimages/')[1]
    if '/' not in media_str:
        if not self.server.theme_name:
            theme = 'default'
        else:
            theme = self.server.theme_name
        icon_filename = media_str
    else:
        theme = media_str.split('/')[0]
        icon_filename = media_str.split('/')[1]
    media_filename = \
        base_dir + '/theme/' + theme + '/helpimages/' + icon_filename
    # if there is no theme-specific help image then use the default one
    if not os.path.isfile(media_filename):
        media_filename = \
            base_dir + '/theme/default/helpimages/' + icon_filename
    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return
    if os.path.isfile(media_filename):
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read help image ' + media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_help_screen_image',
                            self.server.debug)
        return
    http_404(self, 43)


def _show_cached_avatar(self, referer_domain: str, path: str,
                        base_dir: str, getreq_start_time) -> None:
    """Shows an avatar image obtained from the cache
    """
    media_filename = base_dir + '/cache' + path
    if os.path.isfile(media_filename):
        if etag_exists(self, media_filename):
            # The file has not changed
            http_304(self)
            return
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read cached avatar ' + media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             referer_domain,
                             False, None)
            write2(self, media_binary)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_cached_avatar',
                                self.server.debug)
            return
    http_404(self, 46)


def _show_avatar_or_banner(self, referer_domain: str, path: str,
                           base_dir: str, domain: str,
                           getreq_start_time) -> bool:
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
        avatar_str = path.split('/system/accounts/avatars/')[1]
    elif '/accounts/avatars/' in path:
        avatar_str = path.split('/accounts/avatars/')[1]
    elif '/system/accounts/headers/' in path:
        avatar_str = path.split('/system/accounts/headers/')[1]
    elif '/accounts/headers/' in path:
        avatar_str = path.split('/accounts/headers/')[1]
    else:
        avatar_str = path.split('/users/')[1]
    if not ('/' in avatar_str and '.temp.' not in path):
        return False
    avatar_nickname = avatar_str.split('/')[0]
    avatar_file = avatar_str.split('/')[1]
    avatar_file_ext = avatar_file.split('.')[-1]
    # remove any numbers, eg. avatar123.png becomes avatar.png
    if avatar_file.startswith('avatar'):
        avatar_file = 'avatar.' + avatar_file_ext
    elif avatar_file.startswith('banner'):
        avatar_file = 'banner.' + avatar_file_ext
    elif avatar_file.startswith('search_banner'):
        avatar_file = 'search_banner.' + avatar_file_ext
    elif avatar_file.startswith('image'):
        avatar_file = 'image.' + avatar_file_ext
    elif avatar_file.startswith('left_col_image'):
        avatar_file = 'left_col_image.' + avatar_file_ext
    elif avatar_file.startswith('right_col_image'):
        avatar_file = 'right_col_image.' + avatar_file_ext
    avatar_filename = \
        acct_dir(base_dir, avatar_nickname, domain) + '/' + avatar_file
    if not os.path.isfile(avatar_filename):
        original_ext = avatar_file_ext
        original_avatar_file = avatar_file
        alt_ext = get_image_extensions()
        alt_found = False
        for alt in alt_ext:
            if alt == original_ext:
                continue
            avatar_file = \
                original_avatar_file.replace('.' + original_ext,
                                             '.' + alt)
            avatar_filename = \
                acct_dir(base_dir, avatar_nickname, domain) + \
                '/' + avatar_file
            if os.path.isfile(avatar_filename):
                alt_found = True
                break
        if not alt_found:
            return False
    if etag_exists(self, avatar_filename):
        # The file has not changed
        http_304(self)
        return True

    avatar_tm = os.path.getmtime(avatar_filename)
    last_modified_time = \
        datetime.datetime.fromtimestamp(avatar_tm, datetime.timezone.utc)
    last_modified_time_str = \
        last_modified_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

    media_image_type = get_image_mime_type(avatar_file)
    media_binary = None
    try:
        with open(avatar_filename, 'rb') as av_file:
            media_binary = av_file.read()
    except OSError:
        print('EX: unable to read avatar ' + avatar_filename)
    if media_binary:
        set_headers_etag(self, avatar_filename, media_image_type,
                         media_binary, None,
                         referer_domain, True,
                         last_modified_time_str)
        write2(self, media_binary)
    fitness_performance(getreq_start_time,
                        self.server.fitness,
                        '_GET', '_show_avatar_or_banner',
                        self.server.debug)
    return True


def _webfinger(self, calling_domain: str, referer_domain: str,
               cookie: str) -> bool:
    if not self.path.startswith('/.well-known'):
        return False
    if self.server.debug:
        print('DEBUG: WEBFINGER well-known')

    if self.server.debug:
        print('DEBUG: WEBFINGER host-meta')
    if self.path.startswith('/.well-known/host-meta'):
        if calling_domain.endswith('.onion') and \
           self.server.onion_domain:
            wf_result = \
                webfinger_meta('http', self.server.onion_domain)
        elif (calling_domain.endswith('.i2p') and
              self.server.i2p_domain):
            wf_result = \
                webfinger_meta('http', self.server.i2p_domain)
        else:
            wf_result = \
                webfinger_meta(self.server.http_prefix,
                               self.server.domain_full)
        if wf_result:
            msg = wf_result.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'application/xrd+xml', msglen,
                        None, calling_domain, True)
            write2(self, msg)
            return True
        http_404(self, 6)
        return True
    if self.path.startswith('/api/statusnet') or \
       self.path.startswith('/api/gnusocial') or \
       self.path.startswith('/siteinfo') or \
       self.path.startswith('/poco') or \
       self.path.startswith('/friendi'):
        http_404(self, 7)
        return True
    # protocol handler. See https://fedi-to.github.io/protocol-handler.html
    if self.path.startswith('/.well-known/protocol-handler'):
        if calling_domain.endswith('.onion'):
            protocol_url, _ = \
                wellknown_protocol_handler(self.path, 'http',
                                           self.server.onion_domain)
        elif calling_domain.endswith('.i2p'):
            protocol_url, _ = \
                wellknown_protocol_handler(self.path,
                                           'http', self.server.i2p_domain)
        else:
            protocol_url, _ = \
                wellknown_protocol_handler(self.path,
                                           self.server.http_prefix,
                                           self.server.domain_full)
        if protocol_url:
            redirect_headers(self, protocol_url, cookie,
                             calling_domain, 308)
        else:
            http_404(self, 8)
        return True
    # nodeinfo
    if self.path.startswith('/.well-known/nodeinfo') or \
       self.path.startswith('/.well-known/x-nodeinfo'):
        if calling_domain.endswith('.onion') and \
           self.server.onion_domain:
            wf_result = \
                webfinger_node_info('http', self.server.onion_domain)
        elif (calling_domain.endswith('.i2p') and
              self.server.i2p_domain):
            wf_result = \
                webfinger_node_info('http', self.server.i2p_domain)
        else:
            wf_result = \
                webfinger_node_info(self.server.http_prefix,
                                    self.server.domain_full)
        if wf_result:
            msg_str = json.dumps(wf_result)
            msg_str = convert_domains(calling_domain,
                                      referer_domain,
                                      msg_str,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.onion_domain,
                                      self.server.i2p_domain)
            msg = msg_str.encode('utf-8')
            msglen = len(msg)
            if has_accept(self, calling_domain):
                accept_str = self.headers.get('Accept')
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, True)
            else:
                set_headers(self, 'application/ld+json', msglen,
                            None, calling_domain, True)
            write2(self, msg)
            return True
        http_404(self, 9)
        return True

    if self.server.debug:
        print('DEBUG: WEBFINGER lookup ' + self.path + ' ' +
              str(self.server.base_dir))
    wf_result = \
        webfinger_lookup(self.path, self.server.base_dir,
                         self.server.domain,
                         self.server.onion_domain,
                         self.server.i2p_domain,
                         self.server.port, self.server.debug)
    if wf_result:
        msg_str = json.dumps(wf_result)
        msg_str = convert_domains(calling_domain,
                                  referer_domain,
                                  msg_str,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'application/jrd+json', msglen,
                    None, calling_domain, True)
        write2(self, msg)
    else:
        if self.server.debug:
            print('DEBUG: WEBFINGER lookup 404 ' + self.path)
        http_404(self, 10)
    return True


def _hashtag_search_rss2(self, calling_domain: str,
                         path: str, cookie: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         getreq_start_time) -> None:
    """Return an RSS 2 feed for a hashtag
    """
    hashtag = path.split('/tags/rss2/')[1]
    if is_blocked_hashtag(base_dir, hashtag):
        http_400(self)
        return
    nickname = None
    if '/users/' in path:
        actor = \
            http_prefix + '://' + domain_full + path
        nickname = \
            get_nickname_from_actor(actor)
    hashtag_str = \
        hashtag_search_rss(nickname,
                           domain, port,
                           base_dir, hashtag,
                           http_prefix,
                           self.server.system_language)
    if hashtag_str:
        msg = hashtag_str.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/xml', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
    else:
        origin_path_str = path.split('/tags/rss2/')[0]
        origin_path_str_absolute = \
            http_prefix + '://' + domain_full + origin_path_str
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str_absolute = \
                'http://' + onion_domain + origin_path_str
        elif (calling_domain.endswith('.i2p') and onion_domain):
            origin_path_str_absolute = \
                'http://' + i2p_domain + origin_path_str
        redirect_headers(self, origin_path_str_absolute + '/search',
                         cookie, calling_domain)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_hashtag_search_rss2',
                        self.server.debug)


def _hashtag_search_json(self, calling_domain: str,
                         referer_domain: str,
                         path: str, cookie: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         getreq_start_time) -> None:
    """Return a json collection for a hashtag
    """
    page_number = 1
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if page_number_str.isdigit():
            page_number = int(page_number_str)
        path = path.split('?page=')[0]
    hashtag = path.split('/tags/')[1]
    if is_blocked_hashtag(base_dir, hashtag):
        http_400(self)
        return
    nickname = None
    if '/users/' in path:
        actor = \
            http_prefix + '://' + domain_full + path
        nickname = \
            get_nickname_from_actor(actor)
    hashtag_json = \
        hashtag_search_json(nickname,
                            domain, port,
                            base_dir, hashtag,
                            page_number, MAX_POSTS_IN_FEED,
                            http_prefix)
    if hashtag_json:
        msg_str = json.dumps(hashtag_json)
        msg_str = convert_domains(calling_domain, referer_domain,
                                  msg_str, http_prefix, domain,
                                  onion_domain, i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'application/json', msglen,
                    None, calling_domain, True)
        write2(self, msg)
    else:
        origin_path_str = path.split('/tags/')[0]
        origin_path_str_absolute = \
            http_prefix + '://' + domain_full + origin_path_str
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str_absolute = \
                'http://' + onion_domain + origin_path_str
        elif (calling_domain.endswith('.i2p') and onion_domain):
            origin_path_str_absolute = \
                'http://' + i2p_domain + origin_path_str
        redirect_headers(self, origin_path_str_absolute,
                         cookie, calling_domain)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_hashtag_search_json',
                        self.server.debug)


def _hashtag_search2(self, calling_domain: str,
                     path: str, cookie: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domain_full: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     getreq_start_time,
                     curr_session) -> None:
    """Return the result of a hashtag search
    """
    page_number = 1
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    hashtag = path.split('/tags/')[1]
    if '?page=' in hashtag:
        hashtag = hashtag.split('?page=')[0]
    hashtag = urllib.parse.unquote_plus(hashtag)
    if is_blocked_hashtag(base_dir, hashtag):
        print('BLOCK: blocked hashtag #' + hashtag)
        msg = html_hashtag_blocked(base_dir,
                                   self.server.translate).encode('utf-8')
        msglen = len(msg)
        login_headers(self, 'text/html', msglen, calling_domain)
        write2(self, msg)
        return
    nickname = None
    if '/users/' in path:
        nickname = path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
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
                            base_dir, hashtag, page_number,
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
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
    else:
        origin_path_str = path.split('/tags/')[0]
        origin_path_str_absolute = \
            http_prefix + '://' + domain_full + origin_path_str
        if calling_domain.endswith('.onion') and onion_domain:
            origin_path_str_absolute = \
                'http://' + onion_domain + origin_path_str
        elif (calling_domain.endswith('.i2p') and onion_domain):
            origin_path_str_absolute = \
                'http://' + i2p_domain + origin_path_str
        redirect_headers(self, origin_path_str_absolute + '/search',
                         cookie, calling_domain)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_hashtag_search',
                        self.server.debug)


def _confirm_delete_event(self, calling_domain: str, path: str,
                          base_dir: str, http_prefix: str, cookie: str,
                          translate: {}, domain_full: str,
                          onion_domain: str, i2p_domain: str,
                          getreq_start_time) -> bool:
    """Confirm whether to delete a calendar event
    """
    post_id = path.split('?eventid=')[1]
    if '?' in post_id:
        post_id = post_id.split('?')[0]
    post_time = path.split('?time=')[1]
    if '?' in post_time:
        post_time = post_time.split('?')[0]
    post_year = path.split('?year=')[1]
    if '?' in post_year:
        post_year = post_year.split('?')[0]
    post_month = path.split('?month=')[1]
    if '?' in post_month:
        post_month = post_month.split('?')[0]
    post_day = path.split('?day=')[1]
    if '?' in post_day:
        post_day = post_day.split('?')[0]
    # show the confirmation screen screen
    msg = html_calendar_delete_confirm(translate,
                                       base_dir, path,
                                       http_prefix,
                                       domain_full,
                                       post_id, post_time,
                                       post_year, post_month, post_day,
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
        redirect_headers(self, actor + '/calendar',
                         cookie, calling_domain)
        fitness_performance(getreq_start_time,
                            self.server.fitness,
                            '_GET', '_confirm_delete_event',
                            self.server.debug)
        return True
    msg = msg.encode('utf-8')
    msglen = len(msg)
    set_headers(self, 'text/html', msglen,
                cookie, calling_domain, False)
    write2(self, msg)
    return True


def _announce_button(self, calling_domain: str, path: str,
                     base_dir: str,
                     cookie: str, proxy_type: str,
                     http_prefix: str,
                     domain: str, domain_full: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     getreq_start_time,
                     repeat_private: bool,
                     debug: bool,
                     curr_session, sites_unavailable: []) -> None:
    """The announce/repeat button was pressed on a post
    """
    page_number = 1
    repeat_url = path.split('?repeat=')[1]
    if '?' in repeat_url:
        repeat_url = repeat_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    actor = path.split('?repeat=')[0]
    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number)
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return

    if onion_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_onion
            proxy_type = 'tor'
    if i2p_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_i2p
            proxy_type = 'i2p'

    curr_session = \
        establish_session("announceButton",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 47)
        return
    self.server.actorRepeat = path.split('?actor=')[1]
    announce_to_str = \
        local_actor_url(http_prefix, self.post_to_nickname,
                        domain_full) + \
        '/followers'
    if not repeat_private:
        announce_to_str = 'https://www.w3.org/ns/activitystreams#Public'
    announce_id = None
    announce_json = \
        create_announce(curr_session,
                        base_dir,
                        self.server.federation_list,
                        self.post_to_nickname,
                        domain, port,
                        announce_to_str,
                        None, http_prefix,
                        repeat_url, False, False,
                        self.server.send_threads,
                        self.server.postLog,
                        self.server.person_cache,
                        self.server.cached_webfingers,
                        debug,
                        self.server.project_version,
                        self.server.signing_priv_key_pem,
                        self.server.domain,
                        onion_domain,
                        i2p_domain, sites_unavailable,
                        self.server.system_language)
    announce_filename = None
    if announce_json:
        # save the announce straight to the outbox
        # This is because the subsequent send is within a separate thread
        # but the html still needs to be generated before this call ends
        announce_id = remove_id_ending(announce_json['id'])
        announce_filename = \
            save_post_to_box(base_dir, http_prefix, announce_id,
                             self.post_to_nickname, domain_full,
                             announce_json, 'outbox')

        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('repeat.png'):
            del self.server.iconsCache['repeat.png']

        # send out the announce within a separate thread
        post_to_outbox(self, announce_json,
                       self.server.project_version,
                       self.post_to_nickname,
                       curr_session, proxy_type)

        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_announce_button postToOutboxThread',
                            self.server.debug)

    # generate the html for the announce
    if announce_json and announce_filename:
        if debug:
            print('Generating html post for announce')
        cached_post_filename = \
            get_cached_post_filename(base_dir, self.post_to_nickname,
                                     domain, announce_json)
        if debug:
            print('Announced post json: ' + str(announce_json))
            print('Announced post nickname: ' +
                  self.post_to_nickname + ' ' + domain)
            print('Announced post cache: ' + str(cached_post_filename))
        show_individual_post_icons = True
        manually_approve_followers = \
            follower_approval_active(base_dir,
                                     self.post_to_nickname, domain)
        show_repeats = not is_dm(announce_json)
        timezone = None
        if self.server.account_timezone.get(self.post_to_nickname):
            timezone = \
                self.server.account_timezone.get(self.post_to_nickname)
        mitm = False
        if os.path.isfile(announce_filename.replace('.json', '') +
                          '.mitm'):
            mitm = True
        bold_reading = False
        if self.server.bold_reading.get(self.post_to_nickname):
            bold_reading = True
        minimize_all_images = False
        if self.post_to_nickname in self.server.min_images_for_accounts:
            minimize_all_images = True
        individual_post_as_html(self.server.signing_priv_key_pem, False,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.translate,
                                page_number, base_dir,
                                curr_session,
                                self.server.cached_webfingers,
                                self.server.person_cache,
                                self.post_to_nickname, domain,
                                self.server.port, announce_json,
                                None, True,
                                self.server.allow_deletion,
                                http_prefix, self.server.project_version,
                                timeline_str,
                                self.server.yt_replace_domain,
                                self.server.twitter_replacement_domain,
                                self.server.show_published_date_only,
                                self.server.peertube_instances,
                                self.server.allow_local_network_access,
                                self.server.theme_name,
                                self.server.system_language,
                                self.server.max_like_count,
                                show_repeats,
                                show_individual_post_icons,
                                manually_approve_followers,
                                False, True, False,
                                self.server.cw_lists,
                                self.server.lists_enabled,
                                timezone, mitm, bold_reading,
                                self.server.dogwhistles,
                                minimize_all_images, None,
                                self.server.buy_sites,
                                self.server.auto_cw_cache)

    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        '/users/' + self.post_to_nickname

    actor_path_str = \
        actor_absolute + '/' + timeline_str + '?page=' + \
        str(page_number) + first_post_id + timeline_bookmark
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_announce_button',
                        self.server.debug)
    redirect_headers(self, actor_path_str, cookie, calling_domain)


def _announce_button_undo(self, calling_domain: str, path: str,
                          base_dir: str, cookie: str, proxy_type: str,
                          http_prefix: str, domain: str, domain_full: str,
                          onion_domain: str, i2p_domain: str,
                          getreq_start_time, debug: bool,
                          recent_posts_cache: {}, curr_session) -> None:
    """Undo announce/repeat button was pressed
    """
    page_number = 1

    # the post which was referenced by the announce post
    repeat_url = path.split('?unrepeat=')[1]
    if '?' in repeat_url:
        repeat_url = repeat_url.split('?')[0]

    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')

    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    actor = path.split('?unrepeat=')[0]
    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + '?page=' + \
            str(page_number)
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return

    if onion_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_onion
            proxy_type = 'tor'
    if i2p_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_i2p
            proxy_type = 'i2p'

    curr_session = \
        establish_session("undoAnnounceButton",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 48)
        return
    undo_announce_actor = \
        http_prefix + '://' + domain_full + \
        '/users/' + self.post_to_nickname
    un_repeat_to_str = 'https://www.w3.org/ns/activitystreams#Public'
    new_undo_announce = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': undo_announce_actor,
        'type': 'Undo',
        'cc': [undo_announce_actor + '/followers'],
        'to': [un_repeat_to_str],
        'object': {
            'actor': undo_announce_actor,
            'cc': [undo_announce_actor + '/followers'],
            'object': repeat_url,
            'to': [un_repeat_to_str],
            'type': 'Announce'
        }
    }
    # clear the icon from the cache so that it gets updated
    if self.server.iconsCache.get('repeat_inactive.png'):
        del self.server.iconsCache['repeat_inactive.png']

    # delete the announce post
    if '?unannounce=' in path:
        announce_url = path.split('?unannounce=')[1]
        if '?' in announce_url:
            announce_url = announce_url.split('?')[0]
        post_filename = None
        nickname = get_nickname_from_actor(announce_url)
        if nickname:
            if domain_full + '/users/' + nickname + '/' in announce_url:
                post_filename = \
                    locate_post(base_dir, nickname, domain, announce_url)
        if post_filename:
            delete_post(base_dir, http_prefix,
                        nickname, domain, post_filename,
                        debug, recent_posts_cache, True)

    post_to_outbox(self, new_undo_announce,
                   self.server.project_version,
                   self.post_to_nickname,
                   curr_session, proxy_type)

    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        '/users/' + self.post_to_nickname

    actor_path_str = \
        actor_absolute + '/' + timeline_str + '?page=' + \
        str(page_number) + first_post_id + timeline_bookmark
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_undo_announce_button',
                        self.server.debug)
    redirect_headers(self, actor_path_str, cookie, calling_domain)


def _newswire_vote(self, calling_domain: str, path: str,
                   cookie: str,
                   base_dir: str, http_prefix: str,
                   domain_full: str,
                   onion_domain: str, i2p_domain: str,
                   getreq_start_time,
                   newswire: {}):
    """Vote for a newswire item
    """
    origin_path_str = path.split('/newswirevote=')[0]
    date_str = \
        path.split('/newswirevote=')[1].replace('T', ' ')
    date_str = date_str.replace(' 00:00', '').replace('+00:00', '')
    date_str = urllib.parse.unquote_plus(date_str) + '+00:00'
    nickname = \
        urllib.parse.unquote_plus(origin_path_str.split('/users/')[1])
    if '/' in nickname:
        nickname = nickname.split('/')[0]
    print('Newswire item date: ' + date_str)
    if newswire.get(date_str):
        if is_moderator(base_dir, nickname):
            newswire_item = newswire[date_str]
            print('Voting on newswire item: ' + str(newswire_item))
            votes_index = 2
            filename_index = 3
            if 'vote:' + nickname not in newswire_item[votes_index]:
                newswire_item[votes_index].append('vote:' + nickname)
                filename = newswire_item[filename_index]
                newswire_state_filename = \
                    base_dir + '/accounts/.newswirestate.json'
                try:
                    save_json(newswire, newswire_state_filename)
                except BaseException as ex:
                    print('EX: saving newswire state, ' + str(ex))
                if filename:
                    save_json(newswire_item[votes_index],
                              filename + '.votes')
    else:
        print('No newswire item with date: ' + date_str + ' ' +
              str(newswire))

    origin_path_str_absolute = \
        http_prefix + '://' + domain_full + origin_path_str + '/' + \
        self.server.default_timeline
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str_absolute = \
            'http://' + onion_domain + origin_path_str
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str_absolute = \
            'http://' + i2p_domain + origin_path_str
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_newswire_vote',
                        self.server.debug)
    redirect_headers(self, origin_path_str_absolute,
                     cookie, calling_domain)


def _newswire_unvote(self, calling_domain: str, path: str,
                     cookie: str, base_dir: str, http_prefix: str,
                     domain_full: str,
                     onion_domain: str, i2p_domain: str,
                     getreq_start_time, debug: bool,
                     newswire: {}):
    """Remove vote for a newswire item
    """
    origin_path_str = path.split('/newswireunvote=')[0]
    date_str = \
        path.split('/newswireunvote=')[1].replace('T', ' ')
    date_str = date_str.replace(' 00:00', '').replace('+00:00', '')
    date_str = urllib.parse.unquote_plus(date_str) + '+00:00'
    nickname = \
        urllib.parse.unquote_plus(origin_path_str.split('/users/')[1])
    if '/' in nickname:
        nickname = nickname.split('/')[0]
    if newswire.get(date_str):
        if is_moderator(base_dir, nickname):
            votes_index = 2
            filename_index = 3
            newswire_item = newswire[date_str]
            if 'vote:' + nickname in newswire_item[votes_index]:
                newswire_item[votes_index].remove('vote:' + nickname)
                filename = newswire_item[filename_index]
                newswire_state_filename = \
                    base_dir + '/accounts/.newswirestate.json'
                try:
                    save_json(newswire, newswire_state_filename)
                except BaseException as ex:
                    print('EX: saving newswire state, ' + str(ex))
                if filename:
                    save_json(newswire_item[votes_index],
                              filename + '.votes')
    else:
        print('No newswire item with date: ' + date_str + ' ' +
              str(newswire))

    origin_path_str_absolute = \
        http_prefix + '://' + domain_full + origin_path_str + '/' + \
        self.server.default_timeline
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str_absolute = \
            'http://' + onion_domain + origin_path_str
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str_absolute = \
            'http://' + i2p_domain + origin_path_str
    redirect_headers(self, origin_path_str_absolute,
                     cookie, calling_domain)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_newswire_unvote', debug)


def _follow_approve_button(self, calling_domain: str, path: str,
                           cookie: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domain_full: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           getreq_start_time,
                           proxy_type: str, debug: bool,
                           curr_session) -> None:
    """Follow approve button was pressed
    """
    origin_path_str = path.split('/followapprove=')[0]
    follower_nickname = origin_path_str.replace('/users/', '')
    following_handle = path.split('/followapprove=')[1]
    if '://' in following_handle:
        handle_nickname = get_nickname_from_actor(following_handle)
        handle_domain, handle_port = \
            get_domain_from_actor(following_handle)
        if not handle_nickname or not handle_domain:
            http_404(self, 49)
            return
        following_handle = \
            handle_nickname + '@' + \
            get_full_domain(handle_domain, handle_port)
    if '@' in following_handle:
        if self.server.onion_domain:
            if following_handle.endswith('.onion'):
                curr_session = self.server.session_onion
                proxy_type = 'tor'
                port = 80
        if self.server.i2p_domain:
            if following_handle.endswith('.i2p'):
                curr_session = self.server.session_i2p
                proxy_type = 'i2p'
                port = 80

        curr_session = \
            establish_session("follow_approve_button",
                              curr_session, proxy_type,
                              self.server)
        if not curr_session:
            print('WARN: unable to establish session ' +
                  'when approving follow request')
            http_404(self, 50)
            return
        signing_priv_key_pem = \
            self.server.signing_priv_key_pem
        followers_sync_cache = \
            self.server.followers_sync_cache
        manual_approve_follow_request_thread(self.server.session,
                                             self.server.session_onion,
                                             self.server.session_i2p,
                                             self.server.onion_domain,
                                             self.server.i2p_domain,
                                             base_dir, http_prefix,
                                             follower_nickname,
                                             domain, port,
                                             following_handle,
                                             self.server.federation_list,
                                             self.server.send_threads,
                                             self.server.postLog,
                                             self.server.cached_webfingers,
                                             self.server.person_cache,
                                             debug,
                                             self.server.project_version,
                                             signing_priv_key_pem,
                                             proxy_type,
                                             followers_sync_cache,
                                             self.server.sites_unavailable,
                                             self.server.system_language)
    origin_path_str_absolute = \
        http_prefix + '://' + domain_full + origin_path_str
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str_absolute = \
            'http://' + onion_domain + origin_path_str
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        origin_path_str_absolute = \
            'http://' + i2p_domain + origin_path_str
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_follow_approve_button',
                        self.server.debug)
    redirect_headers(self, origin_path_str_absolute,
                     cookie, calling_domain)


def _follow_deny_button(self, calling_domain: str, path: str,
                        cookie: str, base_dir: str, http_prefix: str,
                        domain: str, domain_full: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        getreq_start_time, debug: bool) -> None:
    """Follow deny button was pressed
    """
    origin_path_str = path.split('/followdeny=')[0]
    follower_nickname = origin_path_str.replace('/users/', '')
    following_handle = path.split('/followdeny=')[1]
    if '://' in following_handle:
        handle_nickname = get_nickname_from_actor(following_handle)
        handle_domain, handle_port = \
            get_domain_from_actor(following_handle)
        if not handle_nickname or not handle_domain:
            http_404(self, 51)
            return
        following_handle = \
            handle_nickname + '@' + \
            get_full_domain(handle_domain, handle_port)
    if '@' in following_handle:
        manual_deny_follow_request_thread(self.server.session,
                                          self.server.session_onion,
                                          self.server.session_i2p,
                                          onion_domain,
                                          i2p_domain,
                                          base_dir, http_prefix,
                                          follower_nickname,
                                          domain, port,
                                          following_handle,
                                          self.server.federation_list,
                                          self.server.send_threads,
                                          self.server.postLog,
                                          self.server.cached_webfingers,
                                          self.server.person_cache,
                                          debug,
                                          self.server.project_version,
                                          self.server.signing_priv_key_pem,
                                          self.server.followers_sync_cache,
                                          self.server.sites_unavailable,
                                          self.server.system_language)
    origin_path_str_absolute = \
        http_prefix + '://' + domain_full + origin_path_str
    if calling_domain.endswith('.onion') and onion_domain:
        origin_path_str_absolute = \
            'http://' + onion_domain + origin_path_str
    elif calling_domain.endswith('.i2p') and i2p_domain:
        origin_path_str_absolute = \
            'http://' + i2p_domain + origin_path_str
    redirect_headers(self, origin_path_str_absolute,
                     cookie, calling_domain)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_follow_deny_button',
                        self.server.debug)


def _like_button(self, calling_domain: str, path: str,
                 base_dir: str, http_prefix: str,
                 domain: str, domain_full: str,
                 onion_domain: str, i2p_domain: str,
                 getreq_start_time,
                 proxy_type: str, cookie: str,
                 debug: str,
                 curr_session) -> None:
    """Press the like button
    """
    page_number = 1
    like_url = path.split('?like=')[1]
    if '?' in like_url:
        like_url = like_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    actor = path.split('?like=')[0]
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]

    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number) + timeline_bookmark
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return

    if onion_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_onion
            proxy_type = 'tor'
    if i2p_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_i2p
            proxy_type = 'i2p'

    curr_session = \
        establish_session("likeButton",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 52)
        return
    like_actor = \
        local_actor_url(http_prefix, self.post_to_nickname, domain_full)
    actor_liked = path.split('?actor=')[1]
    if '?' in actor_liked:
        actor_liked = actor_liked.split('?')[0]

    # if this is an announce then send the like to the original post
    orig_actor, orig_post_url, orig_filename = \
        get_original_post_from_announce_url(like_url, base_dir,
                                            self.post_to_nickname, domain)
    like_url2 = like_url
    liked_post_filename = orig_filename
    if orig_actor and orig_post_url:
        actor_liked = orig_actor
        like_url2 = orig_post_url
        liked_post_filename = None

    like_json = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Like',
        'actor': like_actor,
        'to': [actor_liked],
        'object': like_url2
    }

    # send out the like to followers
    post_to_outbox(self, like_json, self.server.project_version, None,
                   curr_session, proxy_type)

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_like_button postToOutbox',
                        self.server.debug)

    print('Locating liked post ' + like_url)
    # directly like the post file
    if not liked_post_filename:
        liked_post_filename = \
            locate_post(base_dir, self.post_to_nickname, domain, like_url)
    if liked_post_filename:
        recent_posts_cache = self.server.recent_posts_cache
        liked_post_json = load_json(liked_post_filename, 0, 1)
        if orig_filename and orig_post_url:
            update_likes_collection(recent_posts_cache,
                                    base_dir, liked_post_filename,
                                    like_url, like_actor,
                                    self.post_to_nickname,
                                    domain, debug, liked_post_json)
            like_url = orig_post_url
            liked_post_filename = orig_filename
        if debug:
            print('Updating likes for ' + liked_post_filename)
        update_likes_collection(recent_posts_cache,
                                base_dir, liked_post_filename, like_url,
                                like_actor, self.post_to_nickname, domain,
                                debug, None)
        if debug:
            print('Regenerating html post for changed likes collection')
        # clear the icon from the cache so that it gets updated
        if liked_post_json:
            cached_post_filename = \
                get_cached_post_filename(base_dir, self.post_to_nickname,
                                         domain, liked_post_json)
            if debug:
                print('Liked post json: ' + str(liked_post_json))
                print('Liked post nickname: ' +
                      self.post_to_nickname + ' ' + domain)
                print('Liked post cache: ' + str(cached_post_filename))
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir,
                                         self.post_to_nickname, domain)
            show_repeats = not is_dm(liked_post_json)
            timezone = None
            if self.server.account_timezone.get(self.post_to_nickname):
                timezone = \
                    self.server.account_timezone.get(self.post_to_nickname)
            mitm = False
            if os.path.isfile(liked_post_filename.replace('.json', '') +
                              '.mitm'):
                mitm = True
            bold_reading = False
            if self.server.bold_reading.get(self.post_to_nickname):
                bold_reading = True
            minimize_all_images = False
            if self.post_to_nickname in \
               self.server.min_images_for_accounts:
                minimize_all_images = True
            individual_post_as_html(self.server.signing_priv_key_pem,
                                    False,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    self.post_to_nickname, domain,
                                    self.server.port, liked_post_json,
                                    None, True,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    timeline_str,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    show_repeats,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, mitm, bold_reading,
                                    self.server.dogwhistles,
                                    minimize_all_images, None,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
        else:
            print('WARN: Liked post not found: ' + liked_post_filename)
        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('like.png'):
            del self.server.iconsCache['like.png']
    else:
        print('WARN: unable to locate file for liked post ' +
              like_url)

    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        '/users/' + self.post_to_nickname

    actor_path_str = \
        actor_absolute + '/' + timeline_str + \
        '?page=' + str(page_number) + first_post_id + \
        timeline_bookmark
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_like_button',
                        self.server.debug)
    redirect_headers(self, actor_path_str, cookie,
                     calling_domain)


def _undo_like_button(self, calling_domain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domain_full: str,
                      onion_domain: str, i2p_domain: str,
                      getreq_start_time,
                      proxy_type: str, cookie: str,
                      debug: str,
                      curr_session) -> None:
    """A button is pressed to undo
    """
    page_number = 1
    like_url = path.split('?unlike=')[1]
    if '?' in like_url:
        like_url = like_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    actor = path.split('?unlike=')[0]
    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number)
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return

    if onion_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_onion
            proxy_type = 'tor'
    if i2p_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_i2p
            proxy_type = 'i2p'

    curr_session = \
        establish_session("undoLikeButton",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 53)
        return
    undo_actor = \
        local_actor_url(http_prefix, self.post_to_nickname, domain_full)
    actor_liked = path.split('?actor=')[1]
    if '?' in actor_liked:
        actor_liked = actor_liked.split('?')[0]

    # if this is an announce then send the like to the original post
    orig_actor, orig_post_url, orig_filename = \
        get_original_post_from_announce_url(like_url, base_dir,
                                            self.post_to_nickname, domain)
    like_url2 = like_url
    liked_post_filename = orig_filename
    if orig_actor and orig_post_url:
        actor_liked = orig_actor
        like_url2 = orig_post_url
        liked_post_filename = None

    undo_like_json = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': undo_actor,
        'to': [actor_liked],
        'object': {
            'type': 'Like',
            'actor': undo_actor,
            'to': [actor_liked],
            'object': like_url2
        }
    }

    # send out the undo like to followers
    post_to_outbox(self, undo_like_json,
                   self.server.project_version, None,
                   curr_session, proxy_type)

    # directly undo the like within the post file
    if not liked_post_filename:
        liked_post_filename = locate_post(base_dir, self.post_to_nickname,
                                          domain, like_url)
    if liked_post_filename:
        recent_posts_cache = self.server.recent_posts_cache
        liked_post_json = load_json(liked_post_filename, 0, 1)
        if orig_filename and orig_post_url:
            undo_likes_collection_entry(recent_posts_cache,
                                        base_dir, liked_post_filename,
                                        undo_actor,
                                        domain, debug,
                                        liked_post_json)
            like_url = orig_post_url
            liked_post_filename = orig_filename
        if debug:
            print('Removing likes for ' + liked_post_filename)
        undo_likes_collection_entry(recent_posts_cache,
                                    base_dir,
                                    liked_post_filename,
                                    undo_actor, domain, debug, None)
        if debug:
            print('Regenerating html post for changed likes collection')
        if liked_post_json:
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir,
                                         self.post_to_nickname, domain)
            show_repeats = not is_dm(liked_post_json)
            timezone = None
            if self.server.account_timezone.get(self.post_to_nickname):
                timezone = \
                    self.server.account_timezone.get(self.post_to_nickname)
            mitm = False
            if os.path.isfile(liked_post_filename.replace('.json', '') +
                              '.mitm'):
                mitm = True
            bold_reading = False
            if self.server.bold_reading.get(self.post_to_nickname):
                bold_reading = True
            minimize_all_images = False
            if self.post_to_nickname in \
               self.server.min_images_for_accounts:
                minimize_all_images = True
            individual_post_as_html(self.server.signing_priv_key_pem,
                                    False,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    self.post_to_nickname, domain,
                                    self.server.port, liked_post_json,
                                    None, True,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    timeline_str,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    show_repeats,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, mitm, bold_reading,
                                    self.server.dogwhistles,
                                    minimize_all_images, None,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
        else:
            print('WARN: Unliked post not found: ' + liked_post_filename)
        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('like_inactive.png'):
            del self.server.iconsCache['like_inactive.png']
    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        '/users/' + self.post_to_nickname

    actor_path_str = \
        actor_absolute + '/' + timeline_str + \
        '?page=' + str(page_number) + first_post_id + \
        timeline_bookmark
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_undo_like_button',
                        self.server.debug)
    redirect_headers(self, actor_path_str, cookie,
                     calling_domain)


def _reaction_button(self, calling_domain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domain_full: str,
                     onion_domain: str, i2p_domain: str,
                     getreq_start_time,
                     proxy_type: str, cookie: str,
                     debug: str,
                     curr_session) -> None:
    """Press an emoji reaction button
    Note that this is not the emoji reaction selection icon at the
    bottom of the post
    """
    page_number = 1
    reaction_url = path.split('?react=')[1]
    if '?' in reaction_url:
        reaction_url = reaction_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    actor = path.split('?react=')[0]
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    emoji_content_encoded = None
    if '?emojreact=' in path:
        emoji_content_encoded = path.split('?emojreact=')[1]
        if '?' in emoji_content_encoded:
            emoji_content_encoded = emoji_content_encoded.split('?')[0]
    if not emoji_content_encoded:
        print('WARN: no emoji reaction ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number) + timeline_bookmark
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return
    emoji_content = urllib.parse.unquote_plus(emoji_content_encoded)
    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number) + timeline_bookmark
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return

    if onion_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_onion
            proxy_type = 'tor'
    if i2p_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_i2p
            proxy_type = 'i2p'

    curr_session = \
        establish_session("reactionButton",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 54)
        return
    reaction_actor = \
        local_actor_url(http_prefix, self.post_to_nickname, domain_full)
    actor_reaction = path.split('?actor=')[1]
    if '?' in actor_reaction:
        actor_reaction = actor_reaction.split('?')[0]

    # if this is an announce then send the emoji reaction
    # to the original post
    orig_actor, orig_post_url, orig_filename = \
        get_original_post_from_announce_url(reaction_url, base_dir,
                                            self.post_to_nickname, domain)
    reaction_url2 = reaction_url
    reaction_post_filename = orig_filename
    if orig_actor and orig_post_url:
        actor_reaction = orig_actor
        reaction_url2 = orig_post_url
        reaction_post_filename = None

    reaction_json = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'EmojiReact',
        'actor': reaction_actor,
        'to': [actor_reaction],
        'object': reaction_url2,
        'content': emoji_content
    }

    # send out the emoji reaction to followers
    post_to_outbox(self, reaction_json, self.server.project_version, None,
                   curr_session, proxy_type)

    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_reaction_button postToOutbox',
                        self.server.debug)

    print('Locating emoji reaction post ' + reaction_url)
    # directly emoji reaction the post file
    if not reaction_post_filename:
        reaction_post_filename = \
            locate_post(base_dir, self.post_to_nickname, domain,
                        reaction_url)
    if reaction_post_filename:
        recent_posts_cache = self.server.recent_posts_cache
        reaction_post_json = load_json(reaction_post_filename, 0, 1)
        if orig_filename and orig_post_url:
            update_reaction_collection(recent_posts_cache,
                                       base_dir, reaction_post_filename,
                                       reaction_url,
                                       reaction_actor,
                                       self.post_to_nickname,
                                       domain, debug, reaction_post_json,
                                       emoji_content)
            reaction_url = orig_post_url
            reaction_post_filename = orig_filename
        if debug:
            print('Updating emoji reaction for ' + reaction_post_filename)
        update_reaction_collection(recent_posts_cache,
                                   base_dir, reaction_post_filename,
                                   reaction_url,
                                   reaction_actor,
                                   self.post_to_nickname, domain,
                                   debug, None, emoji_content)
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
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir,
                                         self.post_to_nickname, domain)
            show_repeats = not is_dm(reaction_post_json)
            timezone = None
            if self.server.account_timezone.get(self.post_to_nickname):
                timezone = \
                    self.server.account_timezone.get(self.post_to_nickname)
            mitm = False
            if os.path.isfile(reaction_post_filename.replace('.json', '') +
                              '.mitm'):
                mitm = True
            bold_reading = False
            if self.server.bold_reading.get(self.post_to_nickname):
                bold_reading = True
            minimize_all_images = False
            if self.post_to_nickname in \
               self.server.min_images_for_accounts:
                minimize_all_images = True
            individual_post_as_html(self.server.signing_priv_key_pem,
                                    False,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    self.post_to_nickname, domain,
                                    self.server.port, reaction_post_json,
                                    None, True,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    timeline_str,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    show_repeats,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, mitm, bold_reading,
                                    self.server.dogwhistles,
                                    minimize_all_images, None,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
        else:
            print('WARN: Emoji reaction post not found: ' +
                  reaction_post_filename)
    else:
        print('WARN: unable to locate file for emoji reaction post ' +
              reaction_url)

    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        '/users/' + self.post_to_nickname

    actor_path_str = \
        actor_absolute + '/' + timeline_str + \
        '?page=' + str(page_number) + first_post_id + \
        timeline_bookmark
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_reaction_button',
                        self.server.debug)
    redirect_headers(self, actor_path_str, cookie,
                     calling_domain)


def _undo_reaction_button(self, calling_domain: str, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str,
                          onion_domain: str, i2p_domain: str,
                          getreq_start_time,
                          proxy_type: str, cookie: str,
                          debug: str,
                          curr_session) -> None:
    """A button is pressed to undo emoji reaction
    """
    page_number = 1
    reaction_url = path.split('?unreact=')[1]
    if '?' in reaction_url:
        reaction_url = reaction_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    actor = path.split('?unreact=')[0]
    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number)
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return
    emoji_content_encoded = None
    if '?emojreact=' in path:
        emoji_content_encoded = path.split('?emojreact=')[1]
        if '?' in emoji_content_encoded:
            emoji_content_encoded = emoji_content_encoded.split('?')[0]
    if not emoji_content_encoded:
        print('WARN: no emoji reaction ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number) + timeline_bookmark
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return
    emoji_content = urllib.parse.unquote_plus(emoji_content_encoded)

    if onion_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_onion
            proxy_type = 'tor'
    if i2p_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_i2p
            proxy_type = 'i2p'

    curr_session = \
        establish_session("undoReactionButton",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 55)
        return
    undo_actor = \
        local_actor_url(http_prefix, self.post_to_nickname, domain_full)
    actor_reaction = path.split('?actor=')[1]
    if '?' in actor_reaction:
        actor_reaction = actor_reaction.split('?')[0]

    # if this is an announce then send the emoji reaction
    # to the original post
    orig_actor, orig_post_url, orig_filename = \
        get_original_post_from_announce_url(reaction_url, base_dir,
                                            self.post_to_nickname, domain)
    reaction_url2 = reaction_url
    reaction_post_filename = orig_filename
    if orig_actor and orig_post_url:
        actor_reaction = orig_actor
        reaction_url2 = orig_post_url
        reaction_post_filename = None

    undo_reaction_json = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': undo_actor,
        'to': [actor_reaction],
        'object': {
            'type': 'EmojiReact',
            'actor': undo_actor,
            'to': [actor_reaction],
            'object': reaction_url2
        }
    }

    # send out the undo emoji reaction to followers
    post_to_outbox(self, undo_reaction_json,
                   self.server.project_version, None,
                   curr_session, proxy_type)

    # directly undo the emoji reaction within the post file
    if not reaction_post_filename:
        reaction_post_filename = \
            locate_post(base_dir, self.post_to_nickname, domain,
                        reaction_url)
    if reaction_post_filename:
        recent_posts_cache = self.server.recent_posts_cache
        reaction_post_json = load_json(reaction_post_filename, 0, 1)
        if orig_filename and orig_post_url:
            undo_reaction_collection_entry(recent_posts_cache,
                                           base_dir,
                                           reaction_post_filename,
                                           undo_actor, domain, debug,
                                           reaction_post_json,
                                           emoji_content)
            reaction_url = orig_post_url
            reaction_post_filename = orig_filename
        if debug:
            print('Removing emoji reaction for ' + reaction_post_filename)
        undo_reaction_collection_entry(recent_posts_cache,
                                       base_dir, reaction_post_filename,
                                       undo_actor, domain, debug,
                                       reaction_post_json, emoji_content)
        if debug:
            print('Regenerating html post for changed ' +
                  'emoji reaction collection')
        if reaction_post_json:
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir,
                                         self.post_to_nickname, domain)
            show_repeats = not is_dm(reaction_post_json)
            timezone = None
            if self.server.account_timezone.get(self.post_to_nickname):
                timezone = \
                    self.server.account_timezone.get(self.post_to_nickname)
            mitm = False
            if os.path.isfile(reaction_post_filename.replace('.json', '') +
                              '.mitm'):
                mitm = True
            bold_reading = False
            if self.server.bold_reading.get(self.post_to_nickname):
                bold_reading = True
            minimize_all_images = False
            if self.post_to_nickname in \
               self.server.min_images_for_accounts:
                minimize_all_images = True
            individual_post_as_html(self.server.signing_priv_key_pem,
                                    False,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    self.post_to_nickname, domain,
                                    self.server.port, reaction_post_json,
                                    None, True,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    timeline_str,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    show_repeats,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, mitm, bold_reading,
                                    self.server.dogwhistles,
                                    minimize_all_images, None,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
        else:
            print('WARN: Unreaction post not found: ' +
                  reaction_post_filename)

    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        '/users/' + self.post_to_nickname

    actor_path_str = \
        actor_absolute + '/' + timeline_str + \
        '?page=' + str(page_number) + first_post_id + \
        timeline_bookmark
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_undo_reaction_button',
                        self.server.debug)
    redirect_headers(self, actor_path_str, cookie, calling_domain)


def _bookmark_button(self, calling_domain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domain_full: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     getreq_start_time,
                     proxy_type: str, cookie: str,
                     debug: str,
                     curr_session) -> None:
    """Bookmark button was pressed
    """
    page_number = 1
    bookmark_url = path.split('?bookmark=')[1]
    if '?' in bookmark_url:
        bookmark_url = bookmark_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    actor = path.split('?bookmark=')[0]
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]

    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number)
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return

    if onion_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_onion
            proxy_type = 'tor'
    if i2p_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_i2p
            proxy_type = 'i2p'

    curr_session = \
        establish_session("bookmarkButton",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 56)
        return
    bookmark_actor = \
        local_actor_url(http_prefix, self.post_to_nickname, domain_full)
    cc_list = []
    bookmark_post(self.server.recent_posts_cache,
                  base_dir, self.server.federation_list,
                  self.post_to_nickname, domain, port,
                  cc_list, http_prefix, bookmark_url, bookmark_actor,
                  debug)
    # clear the icon from the cache so that it gets updated
    if self.server.iconsCache.get('bookmark.png'):
        del self.server.iconsCache['bookmark.png']
    bookmark_filename = \
        locate_post(base_dir, self.post_to_nickname, domain, bookmark_url)
    if bookmark_filename:
        print('Regenerating html post for changed bookmark')
        bookmark_post_json = load_json(bookmark_filename, 0, 1)
        if bookmark_post_json:
            cached_post_filename = \
                get_cached_post_filename(base_dir, self.post_to_nickname,
                                         domain, bookmark_post_json)
            print('Bookmarked post json: ' + str(bookmark_post_json))
            print('Bookmarked post nickname: ' +
                  self.post_to_nickname + ' ' + domain)
            print('Bookmarked post cache: ' + str(cached_post_filename))
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir,
                                         self.post_to_nickname, domain)
            show_repeats = not is_dm(bookmark_post_json)
            timezone = None
            if self.server.account_timezone.get(self.post_to_nickname):
                timezone = \
                    self.server.account_timezone.get(self.post_to_nickname)
            mitm = False
            if os.path.isfile(bookmark_filename.replace('.json', '') +
                              '.mitm'):
                mitm = True
            bold_reading = False
            if self.server.bold_reading.get(self.post_to_nickname):
                bold_reading = True
            minimize_all_images = False
            if self.post_to_nickname in \
               self.server.min_images_for_accounts:
                minimize_all_images = True
            individual_post_as_html(self.server.signing_priv_key_pem,
                                    False,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    self.post_to_nickname, domain,
                                    self.server.port, bookmark_post_json,
                                    None, True,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    timeline_str,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    show_repeats,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, mitm, bold_reading,
                                    self.server.dogwhistles,
                                    minimize_all_images, None,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
        else:
            print('WARN: Bookmarked post not found: ' + bookmark_filename)
    # _post_to_outbox(self, bookmark_json,
    # self.server.project_version, None,
    # curr_session, proxy_type)
    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        '/users/' + self.post_to_nickname

    actor_path_str = \
        actor_absolute + '/' + timeline_str + \
        '?page=' + str(page_number) + first_post_id + \
        timeline_bookmark
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_bookmark_button',
                        debug)
    redirect_headers(self, actor_path_str, cookie,
                     calling_domain)


def _undo_bookmark_button(self, calling_domain: str, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          getreq_start_time,
                          proxy_type: str, cookie: str,
                          debug: str,
                          curr_session) -> None:
    """Button pressed to undo a bookmark
    """
    page_number = 1
    bookmark_url = path.split('?unbookmark=')[1]
    if '?' in bookmark_url:
        bookmark_url = bookmark_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    actor = path.split('?unbookmark=')[0]
    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number)
        redirect_headers(self, actor_path_str, cookie,
                         calling_domain)
        return

    if onion_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_onion
            proxy_type = 'tor'
    if i2p_domain:
        if '.onion/' in actor:
            curr_session = self.server.session_i2p
            proxy_type = 'i2p'

    curr_session = \
        establish_session("undo_bookmarkButton",
                          curr_session, proxy_type,
                          self.server)
    if not curr_session:
        http_404(self, 57)
        return
    undo_actor = \
        local_actor_url(http_prefix, self.post_to_nickname, domain_full)
    cc_list = []
    undo_bookmark_post(self.server.recent_posts_cache,
                       base_dir, self.server.federation_list,
                       self.post_to_nickname,
                       domain, port, cc_list, http_prefix,
                       bookmark_url, undo_actor, debug)
    # clear the icon from the cache so that it gets updated
    if self.server.iconsCache.get('bookmark_inactive.png'):
        del self.server.iconsCache['bookmark_inactive.png']
    # post_to_outbox(self, undo_bookmark_json,
    #                self.server.project_version, None,
    #                curr_session, proxy_type)
    bookmark_filename = \
        locate_post(base_dir, self.post_to_nickname, domain, bookmark_url)
    if bookmark_filename:
        print('Regenerating html post for changed unbookmark')
        bookmark_post_json = load_json(bookmark_filename, 0, 1)
        if bookmark_post_json:
            cached_post_filename = \
                get_cached_post_filename(base_dir, self.post_to_nickname,
                                         domain, bookmark_post_json)
            print('Unbookmarked post json: ' + str(bookmark_post_json))
            print('Unbookmarked post nickname: ' +
                  self.post_to_nickname + ' ' + domain)
            print('Unbookmarked post cache: ' + str(cached_post_filename))
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir,
                                         self.post_to_nickname, domain)
            show_repeats = not is_dm(bookmark_post_json)
            timezone = None
            if self.server.account_timezone.get(self.post_to_nickname):
                timezone = \
                    self.server.account_timezone.get(self.post_to_nickname)
            mitm = False
            if os.path.isfile(bookmark_filename.replace('.json', '') +
                              '.mitm'):
                mitm = True
            bold_reading = False
            if self.server.bold_reading.get(self.post_to_nickname):
                bold_reading = True
            minimize_all_images = False
            if self.post_to_nickname in \
               self.server.min_images_for_accounts:
                minimize_all_images = True
            individual_post_as_html(self.server.signing_priv_key_pem,
                                    False,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    self.post_to_nickname, domain,
                                    self.server.port, bookmark_post_json,
                                    None, True,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    timeline_str,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    show_repeats,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, mitm, bold_reading,
                                    self.server.dogwhistles,
                                    minimize_all_images, None,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
        else:
            print('WARN: Unbookmarked post not found: ' +
                  bookmark_filename)
    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        '/users/' + self.post_to_nickname

    actor_path_str = \
        actor_absolute + '/' + timeline_str + \
        '?page=' + str(page_number) + first_post_id + \
        timeline_bookmark
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_undo_bookmark_button',
                        self.server.debug)
    redirect_headers(self, actor_path_str, cookie,
                     calling_domain)


def _delete_button(self, calling_domain: str, path: str,
                   base_dir: str, http_prefix: str,
                   domain_full: str,
                   onion_domain: str, i2p_domain: str,
                   getreq_start_time,
                   proxy_type: str, cookie: str,
                   debug: str, curr_session) -> None:
    """Delete button is pressed on a post
    """
    if not cookie:
        print('ERROR: no cookie given when deleting ' + path)
        http_400(self)
        return
    page_number = 1
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
    delete_url = path.split('?delete=')[1]
    if '?' in delete_url:
        delete_url = delete_url.split('?')[0]
    timeline_str = self.server.default_timeline
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    users_path = path.split('?delete=')[0]
    actor = \
        http_prefix + '://' + domain_full + users_path
    if self.server.allow_deletion or \
       delete_url.startswith(actor):
        if self.server.debug:
            print('DEBUG: delete_url=' + delete_url)
            print('DEBUG: actor=' + actor)
        if actor not in delete_url:
            # You can only delete your own posts
            if calling_domain.endswith('.onion') and onion_domain:
                actor = 'http://' + onion_domain + users_path
            elif calling_domain.endswith('.i2p') and i2p_domain:
                actor = 'http://' + i2p_domain + users_path
            redirect_headers(self, actor + '/' + timeline_str,
                             cookie, calling_domain)
            return
        self.post_to_nickname = get_nickname_from_actor(actor)
        if not self.post_to_nickname:
            print('WARN: unable to find nickname in ' + actor)
            if calling_domain.endswith('.onion') and onion_domain:
                actor = 'http://' + onion_domain + users_path
            elif calling_domain.endswith('.i2p') and i2p_domain:
                actor = 'http://' + i2p_domain + users_path
            redirect_headers(self, actor + '/' + timeline_str,
                             cookie, calling_domain)
            return

        if onion_domain:
            if '.onion/' in actor:
                curr_session = self.server.session_onion
                proxy_type = 'tor'
        if i2p_domain:
            if '.onion/' in actor:
                curr_session = self.server.session_i2p
                proxy_type = 'i2p'

        curr_session = \
            establish_session("deleteButton",
                              curr_session, proxy_type,
                              self.server)
        if not curr_session:
            http_404(self, 58)
            return

        delete_str = \
            html_confirm_delete(self.server,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.translate, page_number,
                                curr_session, base_dir,
                                delete_url, http_prefix,
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
                                self.server.lists_enabled,
                                self.server.dogwhistles,
                                self.server.min_images_for_accounts,
                                self.server.buy_sites,
                                self.server.auto_cw_cache)
        if delete_str:
            delete_str_len = len(delete_str)
            set_headers(self, 'text/html', delete_str_len,
                        cookie, calling_domain, False)
            write2(self, delete_str.encode('utf-8'))
            self.server.getreq_busy = False
            return
    if calling_domain.endswith('.onion') and onion_domain:
        actor = 'http://' + onion_domain + users_path
    elif (calling_domain.endswith('.i2p') and i2p_domain):
        actor = 'http://' + i2p_domain + users_path
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_delete_button',
                        debug)
    redirect_headers(self, actor + '/' + timeline_str,
                     cookie, calling_domain)


def _reaction_picker2(self, calling_domain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, port: int,
                      getreq_start_time, cookie: str,
                      debug: str, curr_session) -> None:
    """Press the emoji reaction picker icon at the bottom of the post
    """
    page_number = 1
    reaction_url = path.split('?selreact=')[1]
    if '?' in reaction_url:
        reaction_url = reaction_url.split('?')[0]
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    actor = path.split('?selreact=')[0]
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
    timeline_str = 'inbox'
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    self.post_to_nickname = get_nickname_from_actor(actor)
    if not self.post_to_nickname:
        print('WARN: unable to find nickname in ' + actor)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number) + timeline_bookmark
        redirect_headers(self, actor_path_str, cookie, calling_domain)
        return

    post_json_object = None
    reaction_post_filename = \
        locate_post(base_dir,
                    self.post_to_nickname, domain, reaction_url)
    if reaction_post_filename:
        post_json_object = load_json(reaction_post_filename)
    if not reaction_post_filename or not post_json_object:
        print('WARN: unable to locate reaction post ' + reaction_url)
        actor_absolute = \
            get_instance_url(calling_domain,
                             self.server.http_prefix,
                             self.server.domain_full,
                             self.server.onion_domain,
                             self.server.i2p_domain) + \
            actor
        actor_path_str = \
            actor_absolute + '/' + timeline_str + \
            '?page=' + str(page_number) + timeline_bookmark
        redirect_headers(self, actor_path_str, cookie, calling_domain)
        return

    timezone = None
    if self.server.account_timezone.get(self.post_to_nickname):
        timezone = \
            self.server.account_timezone.get(self.post_to_nickname)

    bold_reading = False
    if self.server.bold_reading.get(self.post_to_nickname):
        bold_reading = True

    msg = \
        html_emoji_reaction_picker(self.server.recent_posts_cache,
                                   self.server.max_recent_posts,
                                   self.server.translate,
                                   base_dir,
                                   curr_session,
                                   self.server.cached_webfingers,
                                   self.server.person_cache,
                                   self.post_to_nickname,
                                   domain, port, post_json_object,
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
                                   timeline_str, page_number,
                                   timezone, bold_reading,
                                   self.server.dogwhistles,
                                   self.server.min_images_for_accounts,
                                   self.server.buy_sites,
                                   self.server.auto_cw_cache)
    msg = msg.encode('utf-8')
    msglen = len(msg)
    set_headers(self, 'text/html', msglen,
                cookie, calling_domain, False)
    write2(self, msg)
    fitness_performance(getreq_start_time,
                        self.server.fitness,
                        '_GET', '_reaction_picker',
                        debug)


def _mute_button2(self, calling_domain: str, path: str,
                  base_dir: str, http_prefix: str,
                  domain: str, domain_full: str, port: int,
                  onion_domain: str, i2p_domain: str,
                  getreq_start_time, cookie: str,
                  debug: str, curr_session):
    """Mute button is pressed
    """
    mute_url = path.split('?mute=')[1]
    if '?' in mute_url:
        mute_url = mute_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    timeline_str = self.server.default_timeline
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    page_number = 1
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    actor = \
        http_prefix + '://' + domain_full + path.split('?mute=')[0]
    nickname = get_nickname_from_actor(actor)
    if not nickname:
        http_404(self, 59)
        return
    mute_post(base_dir, nickname, domain, port,
              http_prefix, mute_url,
              self.server.recent_posts_cache, debug)
    mute_filename = \
        locate_post(base_dir, nickname, domain, mute_url)
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
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir,
                                         nickname, domain)
            show_repeats = not is_dm(mute_post_json)
            show_public_only = False
            store_to_cache = True
            use_cache_only = False
            allow_downloads = False
            show_avatar_options = True
            avatar_url = None
            timezone = None
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
            mitm = False
            if os.path.isfile(mute_filename.replace('.json', '') +
                              '.mitm'):
                mitm = True
            bold_reading = False
            if self.server.bold_reading.get(nickname):
                bold_reading = True
            minimize_all_images = False
            if nickname in self.server.min_images_for_accounts:
                minimize_all_images = True
            individual_post_as_html(self.server.signing_priv_key_pem,
                                    allow_downloads,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    nickname, domain,
                                    self.server.port, mute_post_json,
                                    avatar_url, show_avatar_options,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    timeline_str,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    show_repeats,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    show_public_only, store_to_cache,
                                    use_cache_only,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, mitm, bold_reading,
                                    self.server.dogwhistles,
                                    minimize_all_images, None,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
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
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_mute_button', self.server.debug)

    page_number_str = str(page_number)
    redirect_str = \
        actor + '/' + timeline_str + '?page=' + page_number_str + \
        first_post_id + timeline_bookmark
    redirect_headers(self, redirect_str, cookie, calling_domain)


def _undo_mute_button(self, calling_domain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domain_full: str, port: int,
                      onion_domain: str, i2p_domain: str,
                      getreq_start_time, cookie: str,
                      debug: str, curr_session):
    """Undo mute button is pressed
    """
    mute_url = path.split('?unmute=')[1]
    if '?' in mute_url:
        mute_url = mute_url.split('?')[0]
    first_post_id = ''
    if '?firstpost=' in path:
        first_post_id = path.split('?firstpost=')[1]
        if '?' in first_post_id:
            first_post_id = first_post_id.split('?')[0]
        first_post_id = first_post_id.replace('/', '--')
        first_post_id = ';firstpost=' + first_post_id.replace('#', '--')
    timeline_bookmark = ''
    if '?bm=' in path:
        timeline_bookmark = path.split('?bm=')[1]
        if '?' in timeline_bookmark:
            timeline_bookmark = timeline_bookmark.split('?')[0]
        timeline_bookmark = '#' + timeline_bookmark
    timeline_str = self.server.default_timeline
    if '?tl=' in path:
        timeline_str = path.split('?tl=')[1]
        if '?' in timeline_str:
            timeline_str = timeline_str.split('?')[0]
    page_number = 1
    if '?page=' in path:
        page_number_str = path.split('?page=')[1]
        if ';' in page_number_str:
            page_number_str = page_number_str.split(';')[0]
        if '?' in page_number_str:
            page_number_str = page_number_str.split('?')[0]
        if '#' in page_number_str:
            page_number_str = page_number_str.split('#')[0]
        if len(page_number_str) > 5:
            page_number_str = "1"
        if page_number_str.isdigit():
            page_number = int(page_number_str)
    actor = \
        http_prefix + '://' + domain_full + path.split('?unmute=')[0]
    nickname = get_nickname_from_actor(actor)
    if not nickname:
        http_404(self, 60)
        return
    unmute_post(base_dir, nickname, domain, port,
                http_prefix, mute_url,
                self.server.recent_posts_cache, debug)
    mute_filename = \
        locate_post(base_dir, nickname, domain, mute_url)
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
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir, nickname, domain)
            show_repeats = not is_dm(mute_post_json)
            show_public_only = False
            store_to_cache = True
            use_cache_only = False
            allow_downloads = False
            show_avatar_options = True
            avatar_url = None
            timezone = None
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
            mitm = False
            if os.path.isfile(mute_filename.replace('.json', '') +
                              '.mitm'):
                mitm = True
            bold_reading = False
            if self.server.bold_reading.get(nickname):
                bold_reading = True
            minimize_all_images = False
            if nickname in self.server.min_images_for_accounts:
                minimize_all_images = True
            individual_post_as_html(self.server.signing_priv_key_pem,
                                    allow_downloads,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, base_dir,
                                    curr_session,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    nickname, domain,
                                    self.server.port, mute_post_json,
                                    avatar_url, show_avatar_options,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    timeline_str,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertube_instances,
                                    self.server.allow_local_network_access,
                                    self.server.theme_name,
                                    self.server.system_language,
                                    self.server.max_like_count,
                                    show_repeats,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    show_public_only, store_to_cache,
                                    use_cache_only,
                                    self.server.cw_lists,
                                    self.server.lists_enabled,
                                    timezone, mitm, bold_reading,
                                    self.server.dogwhistles,
                                    minimize_all_images, None,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
        else:
            print('WARN: Unmuted post not found: ' + mute_filename)
    if calling_domain.endswith('.onion') and onion_domain:
        actor = \
            'http://' + onion_domain + path.split('?unmute=')[0]
    elif calling_domain.endswith('.i2p') and i2p_domain:
        actor = \
            'http://' + i2p_domain + path.split('?unmute=')[0]
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_undo_mute_button', self.server.debug)

    page_number_str = str(page_number)
    redirect_str = \
        actor + '/' + timeline_str + '?page=' + page_number_str + \
        first_post_id + timeline_bookmark
    redirect_headers(self, redirect_str, cookie, calling_domain)


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
    crawlers_list = []
    curr_time = int(time.time())
    recent_crawlers = 60 * 60 * 24 * 30
    for ua_str, item in known_crawlers.items():
        if item['lastseen'] - curr_time < recent_crawlers:
            hits_str = str(item['hits']).zfill(8)
            crawlers_list.append(hits_str + ' ' + ua_str)
    crawlers_list.sort(reverse=True)
    msg = ''
    for line_str in crawlers_list:
        msg += line_str + '\n'
    msg = msg.encode('utf-8')
    msglen = len(msg)
    set_headers(self, 'text/plain; charset=utf-8', msglen,
                None, calling_domain, True)
    write2(self, msg)
    return True


def _edit_profile2(self, calling_domain: str, path: str,
                   translate: {}, base_dir: str,
                   domain: str, port: int,
                   cookie: str) -> bool:
    """Show the edit profile screen
    """
    if '/users/' in path and path.endswith('/editprofile'):
        peertube_instances = self.server.peertube_instances
        nickname = get_nickname_from_actor(path)

        access_keys = self.server.access_keys
        if '/users/' in path:
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]

        default_reply_interval_hrs = self.server.default_reply_interval_hrs
        msg = html_edit_profile(self.server, translate,
                                base_dir, path, domain, port,
                                self.server.default_timeline,
                                self.server.theme_name,
                                peertube_instances,
                                self.server.text_mode_banner,
                                self.server.user_agents_blocked,
                                self.server.crawlers_allowed,
                                access_keys,
                                default_reply_interval_hrs,
                                self.server.cw_lists,
                                self.server.lists_enabled,
                                self.server.system_language,
                                self.server.min_images_for_accounts,
                                self.server.max_recent_posts,
                                self.server.reverse_sequence,
                                self.server.buy_sites,
                                self.server.block_military,
                                self.server.block_federated_endpoints)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        else:
            http_404(self, 105)
        return True
    return False


def _edit_links2(self, calling_domain: str, path: str,
                 translate: {}, base_dir: str,
                 domain: str, cookie: str, theme: str) -> bool:
    """Show the links from the left column
    """
    if '/users/' in path and path.endswith('/editlinks'):
        nickname = path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]

        access_keys = self.server.access_keys
        if self.server.key_shortcuts.get(nickname):
            access_keys = self.server.key_shortcuts[nickname]

        msg = html_edit_links(translate,
                              base_dir,
                              path, domain,
                              self.server.default_timeline,
                              theme, access_keys)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        else:
            http_404(self, 106)
        return True
    return False


def _edit_newswire2(self, calling_domain: str, path: str,
                    translate: {}, base_dir: str,
                    domain: str, cookie: str) -> bool:
    """Show the newswire from the right column
    """
    if '/users/' in path and path.endswith('/editnewswire'):
        nickname = path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]

        access_keys = self.server.access_keys
        if self.server.key_shortcuts.get(nickname):
            access_keys = self.server.key_shortcuts[nickname]

        msg = html_edit_newswire(translate,
                                 base_dir,
                                 path, domain,
                                 self.server.default_timeline,
                                 self.server.theme_name,
                                 access_keys,
                                 self.server.dogwhistles)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        else:
            http_404(self, 107)
        return True
    return False


def _edit_news_post2(self, calling_domain: str, path: str,
                     translate: {}, base_dir: str,
                     http_prefix: str, domain: str,
                     domain_full: str, cookie: str) -> bool:
    """Show the edit screen for a news post
    """
    if '/users/' in path and '/editnewspost=' in path:
        post_actor = 'news'
        if '?actor=' in path:
            post_actor = path.split('?actor=')[1]
            if '?' in post_actor:
                post_actor = post_actor.split('?')[0]
        post_id = path.split('/editnewspost=')[1]
        if '?' in post_id:
            post_id = post_id.split('?')[0]
        post_url = \
            local_actor_url(http_prefix, post_actor, domain_full) + \
            '/statuses/' + post_id
        path = path.split('/editnewspost=')[0]
        msg = html_edit_news_post(translate, base_dir,
                                  path, domain,
                                  post_url,
                                  self.server.system_language)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        else:
            http_404(self, 108)
        return True
    return False


def _show_new_post(self, edit_post_params: {},
                   calling_domain: str, path: str,
                   media_instance: bool, translate: {},
                   base_dir: str, http_prefix: str,
                   in_reply_to_url: str, reply_to_list: [],
                   reply_is_chat: bool,
                   share_description: str, reply_page_number: int,
                   reply_category: str,
                   domain: str, domain_full: str,
                   getreq_start_time, cookie,
                   no_drop_down: bool, conversation_id: str,
                   curr_session) -> bool:
    """Shows the new post screen
    """
    is_new_post_endpoint = False
    new_post_month = None
    new_post_year = None
    if '/users/' in path and '/new' in path:
        if '?month=' in path:
            month_str = path.split('?month=')[1]
            if ';' in month_str:
                month_str = month_str.split(';')[0]
            if month_str.isdigit():
                new_post_month = int(month_str)
        if new_post_month and ';year=' in path:
            year_str = path.split(';year=')[1]
            if ';' in year_str:
                year_str = year_str.split(';')[0]
            if year_str.isdigit():
                new_post_year = int(year_str)
            if new_post_year:
                path = path.split('?month=')[0]
        # Various types of new post in the web interface
        new_post_endpoints = get_new_post_endpoints()
        for curr_post_type in new_post_endpoints:
            if path.endswith('/' + curr_post_type):
                is_new_post_endpoint = True
                break
    if is_new_post_endpoint:
        nickname = get_nickname_from_actor(path)
        if not nickname:
            http_404(self, 103)
            return True
        if in_reply_to_url:
            reply_interval_hours = self.server.default_reply_interval_hrs
            if not can_reply_to(base_dir, nickname, domain,
                                in_reply_to_url, reply_interval_hours):
                print('Reply outside of time window ' + in_reply_to_url +
                      ' ' + str(reply_interval_hours) + ' hours')
                http_403(self)
                return True
            if self.server.debug:
                print('Reply is within time interval: ' +
                      str(reply_interval_hours) + ' hours')

        access_keys = self.server.access_keys
        if self.server.key_shortcuts.get(nickname):
            access_keys = self.server.key_shortcuts[nickname]

        custom_submit_text = get_config_param(base_dir, 'customSubmitText')

        default_post_language = self.server.system_language
        if self.server.default_post_language.get(nickname):
            default_post_language = \
                self.server.default_post_language[nickname]

        post_json_object = None
        if in_reply_to_url:
            reply_post_filename = \
                locate_post(base_dir, nickname, domain, in_reply_to_url)
            if reply_post_filename:
                post_json_object = load_json(reply_post_filename)
                if post_json_object:
                    reply_language = \
                        get_reply_language(base_dir, post_json_object)
                    if reply_language:
                        default_post_language = reply_language

        bold_reading = False
        if self.server.bold_reading.get(nickname):
            bold_reading = True

        languages_understood = \
            get_understood_languages(base_dir,
                                     self.server.http_prefix,
                                     nickname,
                                     self.server.domain_full,
                                     self.server.person_cache)
        default_buy_site = ''
        msg = \
            html_new_post(edit_post_params, media_instance,
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
                          custom_submit_text,
                          conversation_id,
                          self.server.recent_posts_cache,
                          self.server.max_recent_posts,
                          curr_session,
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
                          new_post_month, new_post_year,
                          default_post_language,
                          self.server.buy_sites,
                          default_buy_site,
                          self.server.auto_cw_cache)
        if not msg:
            print('Error replying to ' + in_reply_to_url)
            http_404(self, 104)
            return True
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time,
                            self.server.fitness,
                            '_GET', '_show_new_post',
                            self.server.debug)
        return True
    return False


def _show_individual_at_post(self, ssml_getreq: bool, authorized: bool,
                             calling_domain: str, referer_domain: str,
                             path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domain_full: str, port: int,
                             getreq_start_time,
                             proxy_type: str, cookie: str,
                             debug: str,
                             curr_session) -> bool:
    """get an individual post from the path /@nickname/statusnumber
    """
    if '/@' not in path:
        return False

    liked_by = None
    if '?likedBy=' in path:
        liked_by = path.split('?likedBy=')[1].strip()
        if '?' in liked_by:
            liked_by = liked_by.split('?')[0]
        path = path.split('?likedBy=')[0]

    react_by = None
    react_emoji = None
    if '?reactBy=' in path:
        react_by = path.split('?reactBy=')[1].strip()
        if ';' in react_by:
            react_by = react_by.split(';')[0]
        if ';emoj=' in path:
            react_emoji = path.split(';emoj=')[1].strip()
            if ';' in react_emoji:
                react_emoji = react_emoji.split(';')[0]
        path = path.split('?reactBy=')[0]

    named_status = path.split('/@')[1]
    if '/' not in named_status:
        # show actor
        nickname = named_status
        return False

    post_sections = named_status.split('/')
    if len(post_sections) != 2:
        return False
    nickname = post_sections[0]
    status_number = post_sections[1]
    if len(status_number) <= 10 or not status_number.isdigit():
        return False

    if ssml_getreq:
        ssml_filename = \
            acct_dir(base_dir, nickname, domain) + '/outbox/' + \
            http_prefix + ':##' + domain_full + '#users#' + nickname + \
            '#statuses#' + status_number + '.ssml'
        if not os.path.isfile(ssml_filename):
            ssml_filename = \
                acct_dir(base_dir, nickname, domain) + '/postcache/' + \
                http_prefix + ':##' + domain_full + '#users#' + \
                nickname + '#statuses#' + status_number + '.ssml'
        if not os.path.isfile(ssml_filename):
            http_404(self, 67)
            return True
        ssml_str = None
        try:
            with open(ssml_filename, 'r', encoding='utf-8') as fp_ssml:
                ssml_str = fp_ssml.read()
        except OSError:
            pass
        if ssml_str:
            msg = ssml_str.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'application/ssml+xml', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
            return True
        http_404(self, 68)
        return True

    post_filename = \
        acct_dir(base_dir, nickname, domain) + '/outbox/' + \
        http_prefix + ':##' + domain_full + '#users#' + nickname + \
        '#statuses#' + status_number + '.json'

    include_create_wrapper = False
    if post_sections[-1] == 'activity':
        include_create_wrapper = True

    result = _show_post_from_file(self, post_filename, liked_by,
                                  react_by, react_emoji,
                                  authorized, calling_domain,
                                  referer_domain,
                                  base_dir, http_prefix, nickname,
                                  domain, port,
                                  getreq_start_time,
                                  proxy_type, cookie, debug,
                                  include_create_wrapper,
                                  curr_session)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_show_individual_at_post',
                        self.server.debug)
    return result


def _show_likers_of_post(self, authorized: bool,
                         calling_domain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, port: int,
                         getreq_start_time, cookie: str,
                         debug: str, curr_session) -> bool:
    """Show the likers of a post
    """
    if not authorized:
        return False
    if '?likers=' not in path:
        return False
    if '/users/' not in path:
        return False
    nickname = path.split('/users/')[1]
    if '?' in nickname:
        nickname = nickname.split('?')[0]
    post_url = path.split('?likers=')[1]
    if '?' in post_url:
        post_url = post_url.split('?')[0]
    post_url = post_url.replace('--', '/')

    bold_reading = False
    if self.server.bold_reading.get(nickname):
        bold_reading = True

    msg = \
        html_likers_of_post(base_dir, nickname, domain, port,
                            post_url, self.server.translate,
                            http_prefix,
                            self.server.theme_name,
                            self.server.access_keys,
                            self.server.recent_posts_cache,
                            self.server.max_recent_posts,
                            curr_session,
                            self.server.cached_webfingers,
                            self.server.person_cache,
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
                            'inbox', self.server.default_timeline,
                            bold_reading,
                            self.server.dogwhistles,
                            self.server.min_images_for_accounts,
                            self.server.buy_sites,
                            self.server.auto_cw_cache, 'likes')
    if not msg:
        http_404(self, 69)
        return True
    msg = msg.encode('utf-8')
    msglen = len(msg)
    set_headers(self, 'text/html', msglen,
                cookie, calling_domain, False)
    write2(self, msg)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_show_likers_of_post',
                        debug)
    return True


def _show_announcers_of_post(self, authorized: bool,
                             calling_domain: str, path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, port: int,
                             getreq_start_time, cookie: str,
                             debug: str, curr_session) -> bool:
    """Show the announcers of a post
    """
    if not authorized:
        return False
    if '?announcers=' not in path:
        return False
    if '/users/' not in path:
        return False
    nickname = path.split('/users/')[1]
    if '?' in nickname:
        nickname = nickname.split('?')[0]
    post_url = path.split('?announcers=')[1]
    if '?' in post_url:
        post_url = post_url.split('?')[0]
    post_url = post_url.replace('--', '/')

    bold_reading = False
    if self.server.bold_reading.get(nickname):
        bold_reading = True

    # note that the likers function is reused, but with 'shares'
    msg = \
        html_likers_of_post(base_dir, nickname, domain, port,
                            post_url, self.server.translate,
                            http_prefix,
                            self.server.theme_name,
                            self.server.access_keys,
                            self.server.recent_posts_cache,
                            self.server.max_recent_posts,
                            curr_session,
                            self.server.cached_webfingers,
                            self.server.person_cache,
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
                            'inbox', self.server.default_timeline,
                            bold_reading, self.server.dogwhistles,
                            self.server.min_images_for_accounts,
                            self.server.buy_sites,
                            self.server.auto_cw_cache,
                            'shares')
    if not msg:
        http_404(self, 70)
        return True
    msg = msg.encode('utf-8')
    msglen = len(msg)
    set_headers(self, 'text/html', msglen,
                cookie, calling_domain, False)
    write2(self, msg)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_show_announcers_of_post',
                        debug)
    return True


def _show_replies_to_post(self, authorized: bool,
                          calling_domain: str, referer_domain: str,
                          path: str, base_dir: str, http_prefix: str,
                          domain: str, domain_full: str, port: int,
                          getreq_start_time,
                          proxy_type: str, cookie: str,
                          debug: str, curr_session) -> bool:
    """Shows the replies to a post
    """
    if not ('/statuses/' in path and '/users/' in path):
        return False

    named_status = path.split('/users/')[1]
    if '/' not in named_status:
        return False

    post_sections = named_status.split('/')
    if len(post_sections) < 4:
        return False

    if not post_sections[3].startswith('replies'):
        return False
    nickname = post_sections[0]
    status_number = post_sections[2]
    if not (len(status_number) > 10 and status_number.isdigit()):
        return False

    boxname = 'outbox'
    # get the replies file
    post_dir = \
        acct_dir(base_dir, nickname, domain) + '/' + boxname
    orig_post_url = http_prefix + ':##' + domain_full + '#users#' + \
        nickname + '#statuses#' + status_number
    post_replies_filename = \
        post_dir + '/' + orig_post_url + '.replies'
    if not os.path.isfile(post_replies_filename):
        # There are no replies,
        # so show empty collection
        context_str = \
            'https://www.w3.org/ns/activitystreams'

        first_str = \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '/statuses/' + status_number + '/replies?page=true'

        id_str = \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '/statuses/' + status_number + '/replies'

        last_str = \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '/statuses/' + status_number + '/replies?page=true'

        replies_json = {
            '@context': context_str,
            'first': first_str,
            'id': id_str,
            'last': last_str,
            'totalItems': 0,
            'type': 'OrderedCollection'
        }

        if request_http(self.headers, debug):
            curr_session = \
                establish_session("showRepliesToPost",
                                  curr_session, proxy_type,
                                  self.server)
            if not curr_session:
                http_404(self, 61)
                return True
            recent_posts_cache = self.server.recent_posts_cache
            max_recent_posts = self.server.max_recent_posts
            translate = self.server.translate
            cached_webfingers = self.server.cached_webfingers
            person_cache = self.server.person_cache
            project_version = self.server.project_version
            yt_domain = self.server.yt_replace_domain
            twitter_replacement_domain = \
                self.server.twitter_replacement_domain
            peertube_instances = self.server.peertube_instances
            timezone = None
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
            bold_reading = False
            if self.server.bold_reading.get(nickname):
                bold_reading = True
            msg = \
                html_post_replies(recent_posts_cache,
                                  max_recent_posts,
                                  translate,
                                  base_dir,
                                  curr_session,
                                  cached_webfingers,
                                  person_cache,
                                  nickname,
                                  domain,
                                  port,
                                  replies_json,
                                  http_prefix,
                                  project_version,
                                  yt_domain,
                                  twitter_replacement_domain,
                                  self.server.show_published_date_only,
                                  peertube_instances,
                                  self.server.allow_local_network_access,
                                  self.server.theme_name,
                                  self.server.system_language,
                                  self.server.max_like_count,
                                  self.server.signing_priv_key_pem,
                                  self.server.cw_lists,
                                  self.server.lists_enabled,
                                  timezone, bold_reading,
                                  self.server.dogwhistles,
                                  self.server.min_images_for_accounts,
                                  self.server.buy_sites,
                                  self.server.auto_cw_cache)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_replies_to_post',
                                debug)
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                msg_str = json.dumps(replies_json, ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                protocol_str = \
                    get_json_content_from_accept(self.headers['Accept'])
                msglen = len(msg)
                set_headers(self, protocol_str, msglen, None,
                            calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', '_show_replies_to_post json',
                                    debug)
            else:
                http_404(self, 62)
        return True
    else:
        # replies exist. Itterate through the
        # text file containing message ids
        context_str = 'https://www.w3.org/ns/activitystreams'

        id_str = \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '/statuses/' + status_number + '?page=true'

        part_of_str = \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '/statuses/' + status_number

        replies_json = {
            '@context': context_str,
            'id': id_str,
            'orderedItems': [
            ],
            'partOf': part_of_str,
            'type': 'OrderedCollectionPage'
        }

        # if the original post is public then return the replies
        replies_are_public = \
            is_public_post_from_url(base_dir, nickname, domain,
                                    orig_post_url)
        if replies_are_public:
            authorized = True

        # populate the items list with replies
        populate_replies_json(base_dir, nickname, domain,
                              post_replies_filename,
                              authorized, replies_json)

        # send the replies json
        if request_http(self.headers, debug):
            curr_session = \
                establish_session("showRepliesToPost2",
                                  curr_session, proxy_type,
                                  self.server)
            if not curr_session:
                http_404(self, 63)
                return True
            recent_posts_cache = self.server.recent_posts_cache
            max_recent_posts = self.server.max_recent_posts
            translate = self.server.translate
            cached_webfingers = self.server.cached_webfingers
            person_cache = self.server.person_cache
            project_version = self.server.project_version
            yt_domain = self.server.yt_replace_domain
            twitter_replacement_domain = \
                self.server.twitter_replacement_domain
            peertube_instances = self.server.peertube_instances
            timezone = None
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
            bold_reading = False
            if self.server.bold_reading.get(nickname):
                bold_reading = True
            msg = \
                html_post_replies(recent_posts_cache,
                                  max_recent_posts,
                                  translate,
                                  base_dir,
                                  curr_session,
                                  cached_webfingers,
                                  person_cache,
                                  nickname,
                                  domain,
                                  port,
                                  replies_json,
                                  http_prefix,
                                  project_version,
                                  yt_domain,
                                  twitter_replacement_domain,
                                  self.server.show_published_date_only,
                                  peertube_instances,
                                  self.server.allow_local_network_access,
                                  self.server.theme_name,
                                  self.server.system_language,
                                  self.server.max_like_count,
                                  self.server.signing_priv_key_pem,
                                  self.server.cw_lists,
                                  self.server.lists_enabled,
                                  timezone, bold_reading,
                                  self.server.dogwhistles,
                                  self.server.min_images_for_accounts,
                                  self.server.buy_sites,
                                  self.server.auto_cw_cache)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_replies_to_post',
                                debug)
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                msg_str = json.dumps(replies_json, ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                protocol_str = \
                    get_json_content_from_accept(self.headers['Accept'])
                msglen = len(msg)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', '_show_replies_to_post json',
                                    debug)
            else:
                http_404(self, 64)
        return True
    return False


def _show_roles(self, calling_domain: str, referer_domain: str,
                path: str, base_dir: str, http_prefix: str,
                domain: str, getreq_start_time,
                proxy_type: str, cookie: str, debug: str,
                curr_session) -> bool:
    """Show roles within profile screen
    """
    named_status = path.split('/users/')[1]
    if '/' not in named_status:
        return False

    post_sections = named_status.split('/')
    nickname = post_sections[0]
    actor_filename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actor_filename):
        return False

    actor_json = load_json(actor_filename)
    if not actor_json:
        return False

    if actor_json.get('hasOccupation'):
        if request_http(self.headers, debug):
            get_person = \
                person_lookup(domain, path.replace('/roles', ''),
                              base_dir)
            if get_person:
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
                if self.server.key_shortcuts.get(nickname):
                    access_keys = self.server.key_shortcuts[nickname]

                roles_list = get_actor_roles_list(actor_json)
                city = \
                    get_spoofed_city(self.server.city,
                                     base_dir, nickname, domain)
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains

                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                msg = \
                    html_profile(self.server.signing_priv_key_pem,
                                 self.server.rss_icon_at_top,
                                 icons_as_buttons,
                                 default_timeline,
                                 recent_posts_cache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 self.server.project_version,
                                 base_dir, http_prefix, True,
                                 get_person, 'roles',
                                 curr_session,
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
                                 roles_list,
                                 None, None, self.server.cw_lists,
                                 self.server.lists_enabled,
                                 self.server.content_license_url,
                                 timezone, bold_reading,
                                 self.server.buy_sites, None,
                                 self.server.max_shares_on_profile,
                                 self.server.sites_unavailable,
                                 self.server.no_of_books,
                                 self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', '_show_roles', debug)
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                roles_list = get_actor_roles_list(actor_json)
                msg_str = json.dumps(roles_list, ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                protocol_str = \
                    get_json_content_from_accept(self.headers['Accept'])
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', '_show_roles json', debug)
            else:
                http_404(self, 65)
        return True
    return False


def _show_skills(self, calling_domain: str, referer_domain: str,
                 path: str, base_dir: str, http_prefix: str,
                 domain: str, getreq_start_time, proxy_type: str,
                 cookie: str, debug: str, curr_session) -> bool:
    """Show skills on the profile screen
    """
    named_status = path.split('/users/')[1]
    if '/' in named_status:
        post_sections = named_status.split('/')
        nickname = post_sections[0]
        actor_filename = acct_dir(base_dir, nickname, domain) + '.json'
        if os.path.isfile(actor_filename):
            actor_json = load_json(actor_filename)
            if actor_json:
                if no_of_actor_skills(actor_json) > 0:
                    if request_http(self.headers, self.server.debug):
                        get_person = \
                            person_lookup(domain,
                                          path.replace('/skills', ''),
                                          base_dir)
                        if get_person:
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
                            if self.server.key_shortcuts.get(nickname):
                                access_keys = \
                                    self.server.key_shortcuts[nickname]
                            actor_skills_list = \
                                get_occupation_skills(actor_json)
                            skills = \
                                get_skills_from_list(actor_skills_list)
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
                            timezone = None
                            nick = nickname
                            if self.server.account_timezone.get(nick):
                                timezone = \
                                    self.server.account_timezone.get(nick)
                            bold_reading = False
                            if self.server.bold_reading.get(nick):
                                bold_reading = True
                            max_shares_on_profile = \
                                self.server.max_shares_on_profile
                            msg = \
                                html_profile(signing_priv_key_pem,
                                             self.server.rss_icon_at_top,
                                             icons_as_buttons,
                                             default_timeline,
                                             recent_posts_cache,
                                             self.server.max_recent_posts,
                                             self.server.translate,
                                             self.server.project_version,
                                             base_dir, http_prefix, True,
                                             get_person, 'skills',
                                             curr_session,
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
                                             content_license_url,
                                             timezone, bold_reading,
                                             self.server.buy_sites,
                                             None,
                                             max_shares_on_profile,
                                             self.server.sites_unavailable,
                                             self.server.no_of_books,
                                             self.server.auto_cw_cache)
                            msg = msg.encode('utf-8')
                            msglen = len(msg)
                            set_headers(self, 'text/html', msglen,
                                        cookie, calling_domain,
                                              False)
                            write2(self, msg)
                            fitness_performance(getreq_start_time,
                                                self.server.fitness,
                                                '_GET', '_show_skills',
                                                self.server.debug)
                    else:
                        if secure_mode(curr_session,
                                       proxy_type, False,
                                       self.server,
                                       self.headers,
                                       self.path):
                            actor_skills_list = \
                                get_occupation_skills(actor_json)
                            skills = \
                                get_skills_from_list(actor_skills_list)
                            msg_str = json.dumps(skills,
                                                 ensure_ascii=False)
                            onion_domain = self.server.onion_domain
                            i2p_domain = self.server.i2p_domain
                            msg_str = convert_domains(calling_domain,
                                                      referer_domain,
                                                      msg_str,
                                                      http_prefix,
                                                      domain,
                                                      onion_domain,
                                                      i2p_domain)
                            msg = msg_str.encode('utf-8')
                            msglen = len(msg)
                            accept_str = self.headers['Accept']
                            protocol_str = \
                                get_json_content_from_accept(accept_str)
                            set_headers(self, protocol_str, msglen, None,
                                        calling_domain, False)
                            write2(self, msg)
                            fitness_performance(getreq_start_time,
                                                self.server.fitness,
                                                '_GET',
                                                '_show_skills json',
                                                debug)
                        else:
                            http_404(self, 66)
                    return True
    actor = path.replace('/skills', '')
    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        actor
    redirect_headers(self, actor_absolute, cookie, calling_domain)
    return True


def _show_notify_post(self, authorized: bool,
                      calling_domain: str, referer_domain: str,
                      path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, port: int,
                      getreq_start_time,
                      proxy_type: str, cookie: str,
                      debug: str,
                      curr_session) -> bool:
    """Shows an individual post from an account which you are following
    and where you have the notify checkbox set on person options
    """
    liked_by = None
    react_by = None
    react_emoji = None
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

    include_create_wrapper = False
    if path.endswith('/activity'):
        include_create_wrapper = True

    result = _show_post_from_file(self, post_filename, liked_by,
                                  react_by, react_emoji,
                                  authorized, calling_domain,
                                  referer_domain,
                                  base_dir, http_prefix, nickname,
                                  domain, port,
                                  getreq_start_time,
                                  proxy_type, cookie, debug,
                                  include_create_wrapper,
                                  curr_session)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_show_notify_post',
                        self.server.debug)
    return result


def _show_individual_post(self, ssml_getreq: bool, authorized: bool,
                          calling_domain: str, referer_domain: str,
                          path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domain_full: str, port: int,
                          getreq_start_time,
                          proxy_type: str, cookie: str,
                          debug: str,
                          curr_session) -> bool:
    """Shows an individual post
    """
    liked_by = None
    if '?likedBy=' in path:
        liked_by = path.split('?likedBy=')[1].strip()
        if '?' in liked_by:
            liked_by = liked_by.split('?')[0]
        path = path.split('?likedBy=')[0]

    react_by = None
    react_emoji = None
    if '?reactBy=' in path:
        react_by = path.split('?reactBy=')[1].strip()
        if ';' in react_by:
            react_by = react_by.split(';')[0]
        if ';emoj=' in path:
            react_emoji = path.split(';emoj=')[1].strip()
            if ';' in react_emoji:
                react_emoji = react_emoji.split(';')[0]
        path = path.split('?reactBy=')[0]

    named_status = path.split('/users/')[1]
    if '/' not in named_status:
        return False
    post_sections = named_status.split('/')
    if len(post_sections) < 3:
        return False
    nickname = post_sections[0]
    status_number = post_sections[2]
    if len(status_number) <= 10 or (not status_number.isdigit()):
        return False

    if ssml_getreq:
        ssml_filename = \
            acct_dir(base_dir, nickname, domain) + '/outbox/' + \
            http_prefix + ':##' + domain_full + '#users#' + nickname + \
            '#statuses#' + status_number + '.ssml'
        if not os.path.isfile(ssml_filename):
            ssml_filename = \
                acct_dir(base_dir, nickname, domain) + '/postcache/' + \
                http_prefix + ':##' + domain_full + '#users#' + \
                nickname + '#statuses#' + status_number + '.ssml'
        if not os.path.isfile(ssml_filename):
            http_404(self, 74)
            return True
        ssml_str = None
        try:
            with open(ssml_filename, 'r', encoding='utf-8') as fp_ssml:
                ssml_str = fp_ssml.read()
        except OSError:
            pass
        if ssml_str:
            msg = ssml_str.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'application/ssml+xml', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
            return True
        http_404(self, 75)
        return True

    post_filename = \
        acct_dir(base_dir, nickname, domain) + '/outbox/' + \
        http_prefix + ':##' + domain_full + '#users#' + nickname + \
        '#statuses#' + status_number + '.json'

    include_create_wrapper = False
    if post_sections[-1] == 'activity':
        include_create_wrapper = True

    result = _show_post_from_file(self, post_filename, liked_by,
                                  react_by, react_emoji,
                                  authorized, calling_domain,
                                  referer_domain,
                                  base_dir, http_prefix, nickname,
                                  domain, port,
                                  getreq_start_time,
                                  proxy_type, cookie, debug,
                                  include_create_wrapper,
                                  curr_session)
    fitness_performance(getreq_start_time, self.server.fitness,
                        '_GET', '_show_individual_post',
                        self.server.debug)
    return result


def _show_inbox(self, authorized: bool,
                calling_domain: str, referer_domain: str,
                path: str,
                base_dir: str, http_prefix: str,
                domain: str, port: int,
                getreq_start_time,
                cookie: str, debug: str,
                recent_posts_cache: {}, curr_session,
                default_timeline: str,
                max_recent_posts: int,
                translate: {},
                cached_webfingers: {},
                person_cache: {},
                allow_deletion: bool,
                project_version: str,
                yt_replace_domain: str,
                twitter_replacement_domain: str,
                ua_str: str) -> bool:
    """Shows the inbox timeline
    """
    if '/users/' in path:
        if authorized:
            inbox_feed = \
                person_box_json(recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_FEED, 'inbox',
                                authorized,
                                0,
                                self.server.positive_voting,
                                self.server.voting_time_mins)
            if inbox_feed:
                if getreq_start_time:
                    fitness_performance(getreq_start_time,
                                        self.server.fitness,
                                        '_GET', '_show_inbox',
                                        self.server.debug)
                if request_http(self.headers, debug):
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/inbox', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        if ';' in page_number:
                            page_number = page_number.split(';')[0]
                        nickname = nickname.split('?page=')[0]
                        if len(page_number) > 5:
                            page_number = "1"
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inbox_feed = \
                            person_box_json(recent_posts_cache,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            MAX_POSTS_IN_FEED, 'inbox',
                                            authorized,
                                            0,
                                            self.server.positive_voting,
                                            self.server.voting_time_mins)
                        if getreq_start_time:
                            fitness_performance(getreq_start_time,
                                                self.server.fitness,
                                                '_GET', '_show_inbox2',
                                                self.server.debug)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimal_nick = is_minimal(base_dir, domain, nickname)

                    access_keys = self.server.access_keys
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]
                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    timezone = None
                    if self.server.account_timezone.get(nickname):
                        timezone = \
                            self.server.account_timezone.get(nickname)
                    bold_reading = False
                    if self.server.bold_reading.get(nickname):
                        bold_reading = True
                    reverse_sequence = False
                    if nickname in self.server.reverse_sequence:
                        reverse_sequence = True
                    last_post_id = None
                    if ';lastpost=' in path:
                        last_post_id = path.split(';lastpost=')[1]
                        if ';' in last_post_id:
                            last_post_id = last_post_id.split(';')[0]
                    msg = \
                        html_inbox(default_timeline,
                                   recent_posts_cache,
                                   max_recent_posts,
                                   translate,
                                   page_number, MAX_POSTS_IN_FEED,
                                   curr_session,
                                   base_dir,
                                   cached_webfingers,
                                   person_cache,
                                   nickname,
                                   domain,
                                   port,
                                   inbox_feed,
                                   allow_deletion,
                                   http_prefix,
                                   project_version,
                                   minimal_nick,
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
                                   self.server.lists_enabled,
                                   timezone, bold_reading,
                                   self.server.dogwhistles,
                                   ua_str,
                                   self.server.min_images_for_accounts,
                                   reverse_sequence, last_post_id,
                                   self.server.buy_sites,
                                   self.server.auto_cw_cache)
                    if getreq_start_time:
                        fitness_performance(getreq_start_time,
                                            self.server.fitness,
                                            '_GET', '_show_inbox3',
                                            self.server.debug)
                    if msg:
                        msg_str = msg
                        onion_domain = self.server.onion_domain
                        i2p_domain = self.server.i2p_domain
                        msg_str = convert_domains(calling_domain,
                                                  referer_domain,
                                                  msg_str,
                                                  http_prefix,
                                                  domain,
                                                  onion_domain,
                                                  i2p_domain)
                        msg = msg_str.encode('utf-8')
                        msglen = len(msg)
                        set_headers(self, 'text/html', msglen,
                                    cookie, calling_domain, False)
                        write2(self, msg)

                    if getreq_start_time:
                        fitness_performance(getreq_start_time,
                                            self.server.fitness,
                                            '_GET', '_show_inbox4',
                                            self.server.debug)
                else:
                    # don't need authorized fetch here because
                    # there is already the authorization check
                    onion_domain = self.server.onion_domain
                    i2p_domain = self.server.i2p_domain
                    msg_str = json.dumps(inbox_feed, ensure_ascii=False)
                    msg_str = convert_domains(calling_domain,
                                              referer_domain,
                                              msg_str,
                                              http_prefix,
                                              domain,
                                              onion_domain,
                                              i2p_domain)
                    msg = msg_str.encode('utf-8')
                    msglen = len(msg)
                    accept_str = self.headers['Accept']
                    protocol_str = \
                        get_json_content_from_accept(accept_str)
                    set_headers(self, protocol_str, msglen,
                                None, calling_domain, False)
                    write2(self, msg)
                    fitness_performance(getreq_start_time,
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


def _show_dms(self, authorized: bool,
              calling_domain: str, referer_domain: str,
              path: str, base_dir: str, http_prefix: str,
              domain: str, port: int,
              getreq_start_time,
              cookie: str, debug: str,
              curr_session, ua_str: str) -> bool:
    """Shows the DMs timeline
    """
    if '/users/' in path:
        if authorized:
            inbox_dm_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_FEED, 'dm',
                                authorized,
                                0, self.server.positive_voting,
                                self.server.voting_time_mins)
            if inbox_dm_feed:
                if request_http(self.headers, debug):
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/dm', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        if ';' in page_number:
                            page_number = page_number.split(';')[0]
                        nickname = nickname.split('?page=')[0]
                        if len(page_number) > 5:
                            page_number = "1"
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inbox_dm_feed = \
                            person_box_json(self.server.recent_posts_cache,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            MAX_POSTS_IN_FEED, 'dm',
                                            authorized,
                                            0,
                                            self.server.positive_voting,
                                            self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimal_nick = is_minimal(base_dir, domain, nickname)

                    access_keys = self.server.access_keys
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]

                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    timezone = None
                    if self.server.account_timezone.get(nickname):
                        timezone = \
                            self.server.account_timezone.get(nickname)
                    bold_reading = False
                    if self.server.bold_reading.get(nickname):
                        bold_reading = True
                    reverse_sequence = False
                    if nickname in self.server.reverse_sequence:
                        reverse_sequence = True
                    last_post_id = None
                    if ';lastpost=' in path:
                        last_post_id = path.split(';lastpost=')[1]
                        if ';' in last_post_id:
                            last_post_id = last_post_id.split(';')[0]
                    msg = \
                        html_inbox_dms(self.server.default_timeline,
                                       self.server.recent_posts_cache,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       page_number, MAX_POSTS_IN_FEED,
                                       curr_session,
                                       base_dir,
                                       self.server.cached_webfingers,
                                       self.server.person_cache,
                                       nickname,
                                       domain,
                                       port,
                                       inbox_dm_feed,
                                       self.server.allow_deletion,
                                       http_prefix,
                                       self.server.project_version,
                                       minimal_nick,
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
                                       self.server.lists_enabled,
                                       timezone, bold_reading,
                                       self.server.dogwhistles, ua_str,
                                       self.server.min_images_for_accounts,
                                       reverse_sequence, last_post_id,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    set_headers(self, 'text/html', msglen,
                                cookie, calling_domain, False)
                    write2(self, msg)
                    fitness_performance(getreq_start_time,
                                        self.server.fitness,
                                        '_GET', '_show_dms',
                                        self.server.debug)
                else:
                    # don't need authorized fetch here because
                    # there is already the authorization check
                    onion_domain = self.server.onion_domain
                    i2p_domain = self.server.i2p_domain
                    msg_str = \
                        json.dumps(inbox_dm_feed, ensure_ascii=False)
                    msg_str = convert_domains(calling_domain,
                                              referer_domain,
                                              msg_str, http_prefix,
                                              domain,
                                              onion_domain,
                                              i2p_domain)
                    msg = msg_str.encode('utf-8')
                    msglen = len(msg)
                    accept_str = self.headers['Accept']
                    protocol_str = \
                        get_json_content_from_accept(accept_str)
                    set_headers(self, protocol_str, msglen,
                                None, calling_domain, False)
                    write2(self, msg)
                    fitness_performance(getreq_start_time,
                                        self.server.fitness,
                                        '_GET', '_show_dms json',
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
                  calling_domain: str, referer_domain: str,
                  path: str,
                  base_dir: str, http_prefix: str,
                  domain: str, port: int,
                  getreq_start_time,
                  cookie: str, debug: str,
                  curr_session, ua_str: str) -> bool:
    """Shows the replies timeline
    """
    if '/users/' in path:
        if authorized:
            inbox_replies_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_FEED, 'tlreplies',
                                True,
                                0, self.server.positive_voting,
                                self.server.voting_time_mins)
            if not inbox_replies_feed:
                inbox_replies_feed = []
            if request_http(self.headers, debug):
                nickname = path.replace('/users/', '')
                nickname = nickname.replace('/tlreplies', '')
                page_number = 1
                if '?page=' in nickname:
                    page_number = nickname.split('?page=')[1]
                    if ';' in page_number:
                        page_number = page_number.split(';')[0]
                    nickname = nickname.split('?page=')[0]
                    if len(page_number) > 5:
                        page_number = "1"
                    if page_number.isdigit():
                        page_number = int(page_number)
                    else:
                        page_number = 1
                if 'page=' not in path:
                    # if no page was specified then show the first
                    inbox_replies_feed = \
                        person_box_json(self.server.recent_posts_cache,
                                        base_dir,
                                        domain,
                                        port,
                                        path + '?page=1',
                                        http_prefix,
                                        MAX_POSTS_IN_FEED, 'tlreplies',
                                        True,
                                        0, self.server.positive_voting,
                                        self.server.voting_time_mins)
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header
                minimal_nick = is_minimal(base_dir, domain, nickname)

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = \
                        self.server.key_shortcuts[nickname]

                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                allow_local_network_access = \
                    self.server.allow_local_network_access
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                show_published_date_only = \
                    self.server.show_published_date_only
                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                reverse_sequence = False
                if nickname in self.server.reverse_sequence:
                    reverse_sequence = True
                last_post_id = None
                if ';lastpost=' in path:
                    last_post_id = path.split(';lastpost=')[1]
                    if ';' in last_post_id:
                        last_post_id = last_post_id.split(';')[0]
                msg = \
                    html_inbox_replies(self.server.default_timeline,
                                       self.server.recent_posts_cache,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       page_number, MAX_POSTS_IN_FEED,
                                       curr_session,
                                       base_dir,
                                       self.server.cached_webfingers,
                                       self.server.person_cache,
                                       nickname,
                                       domain,
                                       port,
                                       inbox_replies_feed,
                                       self.server.allow_deletion,
                                       http_prefix,
                                       self.server.project_version,
                                       minimal_nick,
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
                                       self.server.lists_enabled,
                                       timezone, bold_reading,
                                       self.server.dogwhistles,
                                       ua_str,
                                       self.server.min_images_for_accounts,
                                       reverse_sequence, last_post_id,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_replies',
                                    self.server.debug)
            else:
                # don't need authorized fetch here because there is
                # already the authorization check
                onion_domain = self.server.onion_domain
                i2p_domain = self.server.i2p_domain
                msg_str = json.dumps(inbox_replies_feed,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          onion_domain, i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_replies json',
                                    self.server.debug)
            return True
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
                         calling_domain: str, referer_domain: str,
                         path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, port: int,
                         getreq_start_time,
                         cookie: str, debug: str,
                         curr_session, ua_str: str) -> bool:
    """Shows the media timeline
    """
    if '/users/' in path:
        if authorized:
            inbox_media_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_MEDIA_FEED, 'tlmedia',
                                True,
                                0, self.server.positive_voting,
                                self.server.voting_time_mins)
            if not inbox_media_feed:
                inbox_media_feed = []
            if request_http(self.headers, debug):
                nickname = path.replace('/users/', '')
                nickname = nickname.replace('/tlmedia', '')
                page_number = 1
                if '?page=' in nickname:
                    page_number = nickname.split('?page=')[1]
                    if ';' in page_number:
                        page_number = page_number.split(';')[0]
                    nickname = nickname.split('?page=')[0]
                    if len(page_number) > 5:
                        page_number = "1"
                    if page_number.isdigit():
                        page_number = int(page_number)
                    else:
                        page_number = 1
                if 'page=' not in path:
                    # if no page was specified then show the first
                    inbox_media_feed = \
                        person_box_json(self.server.recent_posts_cache,
                                        base_dir,
                                        domain,
                                        port,
                                        path + '?page=1',
                                        http_prefix,
                                        MAX_POSTS_IN_MEDIA_FEED, 'tlmedia',
                                        True,
                                        0, self.server.positive_voting,
                                        self.server.voting_time_mins)
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header
                minimal_nick = is_minimal(base_dir, domain, nickname)

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = \
                        self.server.key_shortcuts[nickname]
                fed_domains = \
                    self.server.shared_items_federated_domains
                allow_local_network_access = \
                    self.server.allow_local_network_access
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                reverse_sequence = False
                if nickname in self.server.reverse_sequence:
                    reverse_sequence = True
                last_post_id = None
                if ';lastpost=' in path:
                    last_post_id = path.split(';lastpost=')[1]
                    if ';' in last_post_id:
                        last_post_id = last_post_id.split(';')[0]
                msg = \
                    html_inbox_media(self.server.default_timeline,
                                     self.server.recent_posts_cache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     page_number, MAX_POSTS_IN_MEDIA_FEED,
                                     curr_session,
                                     base_dir,
                                     self.server.cached_webfingers,
                                     self.server.person_cache,
                                     nickname,
                                     domain,
                                     port,
                                     inbox_media_feed,
                                     self.server.allow_deletion,
                                     http_prefix,
                                     self.server.project_version,
                                     minimal_nick,
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
                                     self.server.lists_enabled,
                                     timezone, bold_reading,
                                     self.server.dogwhistles, ua_str,
                                     self.server.min_images_for_accounts,
                                     reverse_sequence, last_post_id,
                                     self.server.buy_sites,
                                     self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_media_timeline',
                                    self.server.debug)
            else:
                # don't need authorized fetch here because there is
                # already the authorization check
                onion_domain = self.server.onion_domain
                i2p_domain = self.server.i2p_domain
                msg_str = json.dumps(inbox_media_feed,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          onion_domain, i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_media_timeline json',
                                    self.server.debug)
            return True
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
                         calling_domain: str, referer_domain: str,
                         path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, port: int,
                         getreq_start_time,
                         cookie: str, debug: str,
                         curr_session, ua_str: str) -> bool:
    """Shows the blogs timeline
    """
    if '/users/' in path:
        if authorized:
            inbox_blogs_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_BLOGS_FEED, 'tlblogs',
                                True,
                                0, self.server.positive_voting,
                                self.server.voting_time_mins)
            if not inbox_blogs_feed:
                inbox_blogs_feed = []
            if request_http(self.headers, debug):
                nickname = path.replace('/users/', '')
                nickname = nickname.replace('/tlblogs', '')
                page_number = 1
                if '?page=' in nickname:
                    page_number = nickname.split('?page=')[1]
                    if ';' in page_number:
                        page_number = page_number.split(';')[0]
                    nickname = nickname.split('?page=')[0]
                    if len(page_number) > 5:
                        page_number = "1"
                    if page_number.isdigit():
                        page_number = int(page_number)
                    else:
                        page_number = 1
                if 'page=' not in path:
                    # if no page was specified then show the first
                    inbox_blogs_feed = \
                        person_box_json(self.server.recent_posts_cache,
                                        base_dir,
                                        domain,
                                        port,
                                        path + '?page=1',
                                        http_prefix,
                                        MAX_POSTS_IN_BLOGS_FEED, 'tlblogs',
                                        True,
                                        0, self.server.positive_voting,
                                        self.server.voting_time_mins)
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header
                minimal_nick = is_minimal(base_dir, domain, nickname)

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = \
                        self.server.key_shortcuts[nickname]
                fed_domains = \
                    self.server.shared_items_federated_domains
                allow_local_network_access = \
                    self.server.allow_local_network_access
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                reverse_sequence = False
                if nickname in self.server.reverse_sequence:
                    reverse_sequence = True
                last_post_id = None
                if ';lastpost=' in path:
                    last_post_id = path.split(';lastpost=')[1]
                    if ';' in last_post_id:
                        last_post_id = last_post_id.split(';')[0]
                msg = \
                    html_inbox_blogs(self.server.default_timeline,
                                     self.server.recent_posts_cache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     page_number, MAX_POSTS_IN_BLOGS_FEED,
                                     curr_session,
                                     base_dir,
                                     self.server.cached_webfingers,
                                     self.server.person_cache,
                                     nickname,
                                     domain,
                                     port,
                                     inbox_blogs_feed,
                                     self.server.allow_deletion,
                                     http_prefix,
                                     self.server.project_version,
                                     minimal_nick,
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
                                     self.server.lists_enabled,
                                     timezone, bold_reading,
                                     self.server.dogwhistles, ua_str,
                                     self.server.min_images_for_accounts,
                                     reverse_sequence, last_post_id,
                                     self.server.buy_sites,
                                     self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_blogs_timeline',
                                    self.server.debug)
            else:
                # don't need authorized fetch here because there is
                # already the authorization check
                onion_domain = self.server.onion_domain
                i2p_domain = self.server.i2p_domain
                msg_str = json.dumps(inbox_blogs_feed,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          onion_domain, i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_blogs_timeline json',
                                    self.server.debug)
            return True
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
                        calling_domain: str, referer_domain: str,
                        path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, port: int,
                        getreq_start_time,
                        cookie: str, debug: str,
                        curr_session, ua_str: str) -> bool:
    """Shows the news timeline
    """
    if '/users/' in path:
        if authorized:
            inbox_news_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_NEWS_FEED, 'tlnews',
                                True,
                                self.server.newswire_votes_threshold,
                                self.server.positive_voting,
                                self.server.voting_time_mins)
            if not inbox_news_feed:
                inbox_news_feed = []
            if request_http(self.headers, debug):
                nickname = path.replace('/users/', '')
                nickname = nickname.replace('/tlnews', '')
                page_number = 1
                if '?page=' in nickname:
                    page_number = nickname.split('?page=')[1]
                    if ';' in page_number:
                        page_number = page_number.split(';')[0]
                    nickname = nickname.split('?page=')[0]
                    if len(page_number) > 5:
                        page_number = "1"
                    if page_number.isdigit():
                        page_number = int(page_number)
                    else:
                        page_number = 1
                if 'page=' not in path:
                    newswire_votes_threshold = \
                        self.server.newswire_votes_threshold
                    # if no page was specified then show the first
                    inbox_news_feed = \
                        person_box_json(self.server.recent_posts_cache,
                                        base_dir,
                                        domain,
                                        port,
                                        path + '?page=1',
                                        http_prefix,
                                        MAX_POSTS_IN_BLOGS_FEED, 'tlnews',
                                        True,
                                        newswire_votes_threshold,
                                        self.server.positive_voting,
                                        self.server.voting_time_mins)
                curr_nickname = path.split('/users/')[1]
                if '/' in curr_nickname:
                    curr_nickname = curr_nickname.split('/')[0]
                moderator = is_moderator(base_dir, curr_nickname)
                editor = is_editor(base_dir, curr_nickname)
                artist = is_artist(base_dir, curr_nickname)
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header
                minimal_nick = is_minimal(base_dir, domain, nickname)

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = \
                        self.server.key_shortcuts[nickname]
                fed_domains = \
                    self.server.shared_items_federated_domains

                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                reverse_sequence = False
                if nickname in self.server.reverse_sequence:
                    reverse_sequence = True
                msg = \
                    html_inbox_news(self.server.default_timeline,
                                    self.server.recent_posts_cache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    page_number, MAX_POSTS_IN_NEWS_FEED,
                                    curr_session,
                                    base_dir,
                                    self.server.cached_webfingers,
                                    self.server.person_cache,
                                    nickname,
                                    domain,
                                    port,
                                    inbox_news_feed,
                                    self.server.allow_deletion,
                                    http_prefix,
                                    self.server.project_version,
                                    minimal_nick,
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
                                    self.server.lists_enabled,
                                    timezone, bold_reading,
                                    self.server.dogwhistles, ua_str,
                                    self.server.min_images_for_accounts,
                                    reverse_sequence,
                                    self.server.buy_sites,
                                    self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_news_timeline',
                                    self.server.debug)
            else:
                # don't need authorized fetch here because there is
                # already the authorization check
                onion_domain = self.server.onion_domain
                i2p_domain = self.server.i2p_domain
                msg_str = json.dumps(inbox_news_feed,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          onion_domain, i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_news_timeline json',
                                    self.server.debug)
            return True
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
                            calling_domain: str, referer_domain: str,
                            path: str, base_dir: str, http_prefix: str,
                            domain: str, port: int,
                            getreq_start_time,
                            cookie: str, debug: str,
                            curr_session, ua_str: str) -> bool:
    """Shows the features timeline (all local blogs)
    """
    if '/users/' in path:
        if authorized:
            inbox_features_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_NEWS_FEED, 'tlfeatures',
                                True,
                                self.server.newswire_votes_threshold,
                                self.server.positive_voting,
                                self.server.voting_time_mins)
            if not inbox_features_feed:
                inbox_features_feed = []
            if request_http(self.headers, debug):
                nickname = path.replace('/users/', '')
                nickname = nickname.replace('/tlfeatures', '')
                page_number = 1
                if '?page=' in nickname:
                    page_number = nickname.split('?page=')[1]
                    if ';' in page_number:
                        page_number = page_number.split(';')[0]
                    nickname = nickname.split('?page=')[0]
                    if len(page_number) > 5:
                        page_number = "1"
                    if page_number.isdigit():
                        page_number = int(page_number)
                    else:
                        page_number = 1
                if 'page=' not in path:
                    newswire_votes_threshold = \
                        self.server.newswire_votes_threshold
                    # if no page was specified then show the first
                    inbox_features_feed = \
                        person_box_json(self.server.recent_posts_cache,
                                        base_dir,
                                        domain,
                                        port,
                                        path + '?page=1',
                                        http_prefix,
                                        MAX_POSTS_IN_BLOGS_FEED,
                                        'tlfeatures',
                                        True,
                                        newswire_votes_threshold,
                                        self.server.positive_voting,
                                        self.server.voting_time_mins)
                curr_nickname = path.split('/users/')[1]
                if '/' in curr_nickname:
                    curr_nickname = curr_nickname.split('/')[0]
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header
                minimal_nick = is_minimal(base_dir, domain, nickname)

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = \
                        self.server.key_shortcuts[nickname]

                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                allow_local_network_access = \
                    self.server.allow_local_network_access
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                show_published_date_only = \
                    self.server.show_published_date_only
                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                min_images_for_accounts = \
                    self.server.min_images_for_accounts
                reverse_sequence = False
                if nickname in self.server.reverse_sequence:
                    reverse_sequence = True
                msg = \
                    html_inbox_features(self.server.default_timeline,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number,
                                        MAX_POSTS_IN_BLOGS_FEED,
                                        curr_session,
                                        base_dir,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        nickname,
                                        domain,
                                        port,
                                        inbox_features_feed,
                                        self.server.allow_deletion,
                                        http_prefix,
                                        self.server.project_version,
                                        minimal_nick,
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
                                        self.server.lists_enabled,
                                        timezone, bold_reading,
                                        self.server.dogwhistles, ua_str,
                                        min_images_for_accounts,
                                        reverse_sequence,
                                        self.server.buy_sites,
                                        self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_features_timeline',
                                    self.server.debug)
            else:
                # don't need authorized fetch here because there is
                # already the authorization check
                onion_domain = self.server.onion_domain
                i2p_domain = self.server.i2p_domain
                msg_str = json.dumps(inbox_features_feed,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str,
                                          http_prefix,
                                          domain,
                                          onion_domain, i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_features_timeline json',
                                    self.server.debug)
            return True
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
                          domain: str, port: int,
                          getreq_start_time,
                          cookie: str, debug: str,
                          curr_session, ua_str: str) -> bool:
    """Shows the shares timeline
    """
    if '/users/' in path:
        if authorized:
            if request_http(self.headers, debug):
                nickname = path.replace('/users/', '')
                nickname = nickname.replace('/tlshares', '')
                page_number = 1
                if '?page=' in nickname:
                    page_number = nickname.split('?page=')[1]
                    if ';' in page_number:
                        page_number = page_number.split(';')[0]
                    nickname = nickname.split('?page=')[0]
                    if len(page_number) > 5:
                        page_number = "1"
                    if page_number.isdigit():
                        page_number = int(page_number)
                    else:
                        page_number = 1

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = \
                        self.server.key_shortcuts[nickname]
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header

                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                reverse_sequence = False
                if nickname in self.server.reverse_sequence:
                    reverse_sequence = True
                msg = \
                    html_shares(self.server.default_timeline,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.translate,
                                page_number, MAX_POSTS_IN_FEED,
                                curr_session,
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
                                self.server.lists_enabled, timezone,
                                bold_reading, self.server.dogwhistles,
                                ua_str,
                                self.server.min_images_for_accounts,
                                reverse_sequence,
                                self.server.buy_sites,
                                self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
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
                          domain: str, port: int,
                          getreq_start_time,
                          cookie: str, debug: str,
                          curr_session, ua_str: str) -> bool:
    """Shows the wanted timeline
    """
    if '/users/' in path:
        if authorized:
            if request_http(self.headers, debug):
                nickname = path.replace('/users/', '')
                nickname = nickname.replace('/tlwanted', '')
                page_number = 1
                if '?page=' in nickname:
                    page_number = nickname.split('?page=')[1]
                    if ';' in page_number:
                        page_number = page_number.split(';')[0]
                    nickname = nickname.split('?page=')[0]
                    if len(page_number) > 5:
                        page_number = "1"
                    if page_number.isdigit():
                        page_number = int(page_number)
                    else:
                        page_number = 1

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = \
                        self.server.key_shortcuts[nickname]
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header
                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                reverse_sequence = False
                if nickname in self.server.reverse_sequence:
                    reverse_sequence = True
                msg = \
                    html_wanted(self.server.default_timeline,
                                self.server.recent_posts_cache,
                                self.server.max_recent_posts,
                                self.server.translate,
                                page_number, MAX_POSTS_IN_FEED,
                                curr_session,
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
                                self.server.lists_enabled,
                                timezone, bold_reading,
                                self.server.dogwhistles, ua_str,
                                self.server.min_images_for_accounts,
                                reverse_sequence,
                                self.server.buy_sites,
                                self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
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
                             calling_domain: str, referer_domain: str,
                             path: str,
                             base_dir: str, http_prefix: str,
                             domain: str, port: int,
                             getreq_start_time,
                             cookie: str, debug: str,
                             curr_session, ua_str: str) -> bool:
    """Shows the bookmarks timeline
    """
    if '/users/' in path:
        if authorized:
            bookmarks_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_FEED, 'tlbookmarks',
                                authorized,
                                0, self.server.positive_voting,
                                self.server.voting_time_mins)
            if bookmarks_feed:
                if request_http(self.headers, debug):
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlbookmarks', '')
                    nickname = nickname.replace('/bookmarks', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        if ';' in page_number:
                            page_number = page_number.split(';')[0]
                        nickname = nickname.split('?page=')[0]
                        if len(page_number) > 5:
                            page_number = "1"
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        bookmarks_feed = \
                            person_box_json(self.server.recent_posts_cache,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            MAX_POSTS_IN_FEED,
                                            'tlbookmarks',
                                            authorized,
                                            0, self.server.positive_voting,
                                            self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimal_nick = is_minimal(base_dir, domain, nickname)

                    access_keys = self.server.access_keys
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]

                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    timezone = None
                    if self.server.account_timezone.get(nickname):
                        timezone = \
                            self.server.account_timezone.get(nickname)
                    bold_reading = False
                    if self.server.bold_reading.get(nickname):
                        bold_reading = True
                    reverse_sequence = False
                    if nickname in self.server.reverse_sequence:
                        reverse_sequence = True
                    msg = \
                        html_bookmarks(self.server.default_timeline,
                                       self.server.recent_posts_cache,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       page_number, MAX_POSTS_IN_FEED,
                                       curr_session,
                                       base_dir,
                                       self.server.cached_webfingers,
                                       self.server.person_cache,
                                       nickname,
                                       domain,
                                       port,
                                       bookmarks_feed,
                                       self.server.allow_deletion,
                                       http_prefix,
                                       self.server.project_version,
                                       minimal_nick,
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
                                       self.server.lists_enabled,
                                       timezone, bold_reading,
                                       self.server.dogwhistles, ua_str,
                                       self.server.min_images_for_accounts,
                                       reverse_sequence,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    set_headers(self, 'text/html', msglen,
                                cookie, calling_domain, False)
                    write2(self, msg)
                    fitness_performance(getreq_start_time,
                                        self.server.fitness,
                                        '_GET', '_show_bookmarks_timeline',
                                        self.server.debug)
                else:
                    # don't need authorized fetch here because
                    # there is already the authorization check
                    onion_domain = self.server.onion_domain
                    i2p_domain = self.server.i2p_domain
                    msg_str = json.dumps(bookmarks_feed,
                                         ensure_ascii=False)
                    msg_str = convert_domains(calling_domain,
                                              referer_domain,
                                              msg_str, http_prefix,
                                              domain,
                                              onion_domain,
                                              i2p_domain)
                    msg = msg_str.encode('utf-8')
                    msglen = len(msg)
                    accept_str = self.headers['Accept']
                    protocol_str = \
                        get_json_content_from_accept(accept_str)
                    set_headers(self, protocol_str, msglen,
                                None, calling_domain, False)
                    write2(self, msg)
                    fitness_performance(getreq_start_time,
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
                          calling_domain: str, referer_domain: str,
                          path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, port: int,
                          getreq_start_time,
                          cookie: str, debug: str,
                          curr_session, ua_str: str,
                          proxy_type: str) -> bool:
    """Shows the outbox timeline
    """
    # get outbox feed for a person
    outbox_feed = \
        person_box_json(self.server.recent_posts_cache,
                        base_dir, domain, port, path,
                        http_prefix, MAX_POSTS_IN_FEED, 'outbox',
                        authorized,
                        self.server.newswire_votes_threshold,
                        self.server.positive_voting,
                        self.server.voting_time_mins)
    if outbox_feed:
        nickname = \
            path.replace('/users/', '').replace('/outbox', '')
        page_number = 0
        if '?page=' in nickname:
            page_number = nickname.split('?page=')[1]
            if ';' in page_number:
                page_number = page_number.split(';')[0]
            nickname = nickname.split('?page=')[0]
            if len(page_number) > 5:
                page_number = "1"
            if page_number.isdigit():
                page_number = int(page_number)
            else:
                page_number = 1
        else:
            if request_http(self.headers, debug):
                page_number = 1
        if authorized and page_number >= 1:
            # if a page wasn't specified then show the first one
            page_str = '?page=' + str(page_number)
            outbox_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir, domain, port,
                                path + page_str,
                                http_prefix,
                                MAX_POSTS_IN_FEED, 'outbox',
                                authorized,
                                self.server.newswire_votes_threshold,
                                self.server.positive_voting,
                                self.server.voting_time_mins)
        else:
            page_number = 1

        if request_http(self.headers, debug):
            full_width_tl_button_header = \
                self.server.full_width_tl_button_header
            minimal_nick = is_minimal(base_dir, domain, nickname)

            access_keys = self.server.access_keys
            if self.server.key_shortcuts.get(nickname):
                access_keys = \
                    self.server.key_shortcuts[nickname]

            timezone = None
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
            bold_reading = False
            if self.server.bold_reading.get(nickname):
                bold_reading = True
            reverse_sequence = False
            if nickname in self.server.reverse_sequence:
                reverse_sequence = True
            msg = \
                html_outbox(self.server.default_timeline,
                            self.server.recent_posts_cache,
                            self.server.max_recent_posts,
                            self.server.translate,
                            page_number, MAX_POSTS_IN_FEED,
                            curr_session,
                            base_dir,
                            self.server.cached_webfingers,
                            self.server.person_cache,
                            nickname, domain, port,
                            outbox_feed,
                            self.server.allow_deletion,
                            http_prefix,
                            self.server.project_version,
                            minimal_nick,
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
                            self.server.lists_enabled,
                            timezone, bold_reading,
                            self.server.dogwhistles, ua_str,
                            self.server.min_images_for_accounts,
                            reverse_sequence,
                            self.server.buy_sites,
                            self.server.auto_cw_cache)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time,
                                self.server.fitness,
                                '_GET', '_show_outbox_timeline',
                                debug)
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                onion_domain = self.server.onion_domain
                i2p_domain = self.server.i2p_domain
                msg_str = json.dumps(outbox_feed,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          onion_domain,
                                          i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_outbox_timeline json',
                                    debug)
            else:
                http_404(self, 76)
        return True
    return False


def _show_mod_timeline(self, authorized: bool,
                       calling_domain: str, referer_domain: str,
                       path: str, base_dir: str, http_prefix: str,
                       domain: str, port: int, getreq_start_time,
                       cookie: str, debug: str,
                       curr_session, ua_str: str) -> bool:
    """Shows the moderation timeline
    """
    if '/users/' in path:
        if authorized:
            moderation_feed = \
                person_box_json(self.server.recent_posts_cache,
                                base_dir,
                                domain,
                                port,
                                path,
                                http_prefix,
                                MAX_POSTS_IN_FEED, 'moderation',
                                True,
                                0, self.server.positive_voting,
                                self.server.voting_time_mins)
            if moderation_feed:
                if request_http(self.headers, debug):
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/moderation', '')
                    page_number = 1
                    if '?page=' in nickname:
                        page_number = nickname.split('?page=')[1]
                        if ';' in page_number:
                            page_number = page_number.split(';')[0]
                        nickname = nickname.split('?page=')[0]
                        if len(page_number) > 5:
                            page_number = "1"
                        if page_number.isdigit():
                            page_number = int(page_number)
                        else:
                            page_number = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        moderation_feed = \
                            person_box_json(self.server.recent_posts_cache,
                                            base_dir,
                                            domain,
                                            port,
                                            path + '?page=1',
                                            http_prefix,
                                            MAX_POSTS_IN_FEED,
                                            'moderation',
                                            True,
                                            0, self.server.positive_voting,
                                            self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    moderation_action_str = ''

                    access_keys = self.server.access_keys
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]

                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    show_published_date_only = \
                        self.server.show_published_date_only
                    timezone = None
                    if self.server.account_timezone.get(nickname):
                        timezone = \
                            self.server.account_timezone.get(nickname)
                    bold_reading = False
                    if self.server.bold_reading.get(nickname):
                        bold_reading = True
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    reverse_sequence = False
                    if nickname in self.server.reverse_sequence:
                        reverse_sequence = True
                    msg = \
                        html_moderation(self.server.default_timeline,
                                        self.server.recent_posts_cache,
                                        self.server.max_recent_posts,
                                        self.server.translate,
                                        page_number, MAX_POSTS_IN_FEED,
                                        curr_session,
                                        base_dir,
                                        self.server.cached_webfingers,
                                        self.server.person_cache,
                                        nickname,
                                        domain,
                                        port,
                                        moderation_feed,
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
                                        authorized, moderation_action_str,
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
                                        self.server.lists_enabled,
                                        timezone, bold_reading,
                                        self.server.dogwhistles,
                                        ua_str,
                                        min_images_for_accounts,
                                        reverse_sequence,
                                        self.server.buy_sites,
                                        self.server.auto_cw_cache)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    set_headers(self, 'text/html', msglen,
                                cookie, calling_domain, False)
                    write2(self, msg)
                    fitness_performance(getreq_start_time,
                                        self.server.fitness,
                                        '_GET', '_show_mod_timeline',
                                        self.server.debug)
                else:
                    # don't need authorized fetch here because
                    # there is already the authorization check
                    onion_domain = self.server.onion_domain
                    i2p_domain = self.server.i2p_domain
                    msg_str = json.dumps(moderation_feed,
                                         ensure_ascii=False)
                    msg_str = convert_domains(calling_domain,
                                              referer_domain,
                                              msg_str, http_prefix,
                                              domain,
                                              onion_domain,
                                              i2p_domain)
                    msg = msg_str.encode('utf-8')
                    msglen = len(msg)
                    accept_str = self.headers['Accept']
                    protocol_str = \
                        get_json_content_from_accept(accept_str)
                    set_headers(self, protocol_str, msglen,
                                None, calling_domain, False)
                    write2(self, msg)
                    fitness_performance(getreq_start_time,
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
                      calling_domain: str, referer_domain: str,
                      path: str, base_dir: str, http_prefix: str,
                      domain: str, port: int, getreq_start_time,
                      proxy_type: str, cookie: str,
                      debug: str, shares_file_type: str,
                      curr_session) -> bool:
    """Shows the shares feed
    """
    shares = \
        get_shares_feed_for_person(base_dir, domain, port, path,
                                   http_prefix, shares_file_type,
                                   SHARES_PER_PAGE)
    if shares:
        if request_http(self.headers, debug):
            page_number = 1
            if '?page=' not in path:
                search_path = path
                # get a page of shares, not the summary
                shares = \
                    get_shares_feed_for_person(base_dir, domain, port,
                                               path + '?page=true',
                                               http_prefix,
                                               shares_file_type,
                                               SHARES_PER_PAGE)
            else:
                page_number_str = path.split('?page=')[1]
                if ';' in page_number_str:
                    page_number_str = page_number_str.split(';')[0]
                if '#' in page_number_str:
                    page_number_str = page_number_str.split('#')[0]
                if len(page_number_str) > 5:
                    page_number_str = "1"
                if page_number_str.isdigit():
                    page_number = int(page_number_str)
                search_path = path.split('?page=')[0]
            search_path2 = search_path.replace('/' + shares_file_type, '')
            get_person = person_lookup(domain, search_path2, base_dir)
            if get_person:
                curr_session = \
                    establish_session("show_shares_feed",
                                      curr_session, proxy_type,
                                      self.server)
                if not curr_session:
                    http_404(self, 77)
                    self.server.getreq_busy = False
                    return True

                access_keys = self.server.access_keys
                if '/users/' in path:
                    nickname = path.split('/users/')[1]
                    if '/' in nickname:
                        nickname = nickname.split('/')[0]
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]

                city = get_spoofed_city(self.server.city,
                                        base_dir, nickname, domain)
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                msg = \
                    html_profile(self.server.signing_priv_key_pem,
                                 self.server.rss_icon_at_top,
                                 self.server.icons_as_buttons,
                                 self.server.default_timeline,
                                 self.server.recent_posts_cache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 self.server.project_version,
                                 base_dir, http_prefix,
                                 authorized,
                                 get_person, shares_file_type,
                                 curr_session,
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
                                 page_number, SHARES_PER_PAGE,
                                 self.server.cw_lists,
                                 self.server.lists_enabled,
                                 self.server.content_license_url,
                                 timezone, bold_reading,
                                 self.server.buy_sites,
                                 None,
                                 self.server.max_shares_on_profile,
                                 self.server.sites_unavailable,
                                 self.server.no_of_books,
                                 self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_shares_feed',
                                    debug)
                self.server.getreq_busy = False
                return True
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                onion_domain = self.server.onion_domain
                i2p_domain = self.server.i2p_domain
                msg_str = json.dumps(shares,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          onion_domain,
                                          i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_shares_feed json',
                                    debug)
            else:
                http_404(self, 78)
            return True
    return False


def _show_following_feed(self, authorized: bool,
                         calling_domain: str, referer_domain: str,
                         path: str, base_dir: str, http_prefix: str,
                         domain: str, port: int, getreq_start_time,
                         proxy_type: str, cookie: str,
                         debug: str, curr_session) -> bool:
    """Shows the following feed
    """
    following = \
        get_following_feed(base_dir, domain, port, path,
                           http_prefix, authorized, FOLLOWS_PER_PAGE,
                           'following')
    if following:
        if request_http(self.headers, debug):
            page_number = 1
            if '?page=' not in path:
                search_path = path
                # get a page of following, not the summary
                following = \
                    get_following_feed(base_dir,
                                       domain,
                                       port,
                                       path + '?page=true',
                                       http_prefix,
                                       authorized, FOLLOWS_PER_PAGE)
            else:
                page_number_str = path.split('?page=')[1]
                if ';' in page_number_str:
                    page_number_str = page_number_str.split(';')[0]
                if '#' in page_number_str:
                    page_number_str = page_number_str.split('#')[0]
                if len(page_number_str) > 5:
                    page_number_str = "1"
                if page_number_str.isdigit():
                    page_number = int(page_number_str)
                search_path = path.split('?page=')[0]
            get_person = \
                person_lookup(domain,
                              search_path.replace('/following', ''),
                              base_dir)
            if get_person:
                curr_session = \
                    establish_session("show_following_feed",
                                      curr_session, proxy_type,
                                      self.server)
                if not curr_session:
                    http_404(self, 79)
                    return True

                access_keys = self.server.access_keys
                city = None
                timezone = None
                if '/users/' in path:
                    nickname = path.split('/users/')[1]
                    if '/' in nickname:
                        nickname = nickname.split('/')[0]
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]

                    city = get_spoofed_city(self.server.city,
                                            base_dir, nickname, domain)
                    if self.server.account_timezone.get(nickname):
                        timezone = \
                            self.server.account_timezone.get(nickname)
                content_license_url = \
                    self.server.content_license_url
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                if not authorized and \
                   self.server.hide_follows.get(nickname):
                    following = {}
                max_shares_on_profile = \
                    self.server.max_shares_on_profile
                sites_unavailable = \
                    self.server.sites_unavailable
                msg = \
                    html_profile(self.server.signing_priv_key_pem,
                                 self.server.rss_icon_at_top,
                                 self.server.icons_as_buttons,
                                 self.server.default_timeline,
                                 self.server.recent_posts_cache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 self.server.project_version,
                                 base_dir, http_prefix,
                                 authorized,
                                 get_person, 'following',
                                 curr_session,
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
                                 FOLLOWS_PER_PAGE,
                                 self.server.cw_lists,
                                 self.server.lists_enabled,
                                 content_license_url,
                                 timezone, bold_reading,
                                 self.server.buy_sites,
                                 None,
                                 max_shares_on_profile,
                                 sites_unavailable,
                                 self.server.no_of_books,
                                 self.server.auto_cw_cache).encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html',
                            msglen, cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_following_feed',
                                    debug)
                return True
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                if '/users/' in path:
                    nickname = path.split('/users/')[1]
                    if '/' in nickname:
                        nickname = nickname.split('/')[0]
                    if nickname and not authorized and \
                       self.server.hide_follows.get(nickname):
                        following = {}

                msg_str = json.dumps(following,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_following_feed json',
                                    debug)
            else:
                http_404(self, 80)
            return True
    return False


def _show_moved_feed(self, authorized: bool,
                     calling_domain: str, referer_domain: str,
                     path: str, base_dir: str, http_prefix: str,
                     domain: str, port: int, getreq_start_time,
                     proxy_type: str, cookie: str,
                     debug: str, curr_session) -> bool:
    """Shows the moved feed
    """
    following = \
        get_moved_feed(base_dir, domain, port, path,
                       http_prefix, authorized, FOLLOWS_PER_PAGE)
    if following:
        if request_http(self.headers, debug):
            page_number = 1
            if '?page=' not in path:
                search_path = path
                # get a page of following, not the summary
                following = \
                    get_moved_feed(base_dir, domain, port, path,
                                   http_prefix, authorized,
                                   FOLLOWS_PER_PAGE)
            else:
                page_number_str = path.split('?page=')[1]
                if ';' in page_number_str:
                    page_number_str = page_number_str.split(';')[0]
                if '#' in page_number_str:
                    page_number_str = page_number_str.split('#')[0]
                if len(page_number_str) > 5:
                    page_number_str = "1"
                if page_number_str.isdigit():
                    page_number = int(page_number_str)
                search_path = path.split('?page=')[0]
            get_person = \
                person_lookup(domain,
                              search_path.replace('/moved', ''),
                              base_dir)
            if get_person:
                curr_session = \
                    establish_session("show_moved_feed",
                                      curr_session, proxy_type,
                                      self.server)
                if not curr_session:
                    http_404(self, 81)
                    return True

                access_keys = self.server.access_keys
                city = None
                timezone = None
                if '/users/' in path:
                    nickname = path.split('/users/')[1]
                    if '/' in nickname:
                        nickname = nickname.split('/')[0]
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]

                    city = get_spoofed_city(self.server.city,
                                            base_dir, nickname, domain)
                    if self.server.account_timezone.get(nickname):
                        timezone = \
                            self.server.account_timezone.get(nickname)
                content_license_url = \
                    self.server.content_license_url
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                max_shares_on_profile = \
                    self.server.max_shares_on_profile
                sites_unavailable = \
                    self.server.sites_unavailable
                msg = \
                    html_profile(self.server.signing_priv_key_pem,
                                 self.server.rss_icon_at_top,
                                 self.server.icons_as_buttons,
                                 self.server.default_timeline,
                                 self.server.recent_posts_cache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 self.server.project_version,
                                 base_dir, http_prefix,
                                 authorized,
                                 get_person, 'moved',
                                 curr_session,
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
                                 FOLLOWS_PER_PAGE,
                                 self.server.cw_lists,
                                 self.server.lists_enabled,
                                 content_license_url,
                                 timezone, bold_reading,
                                 self.server.buy_sites,
                                 None,
                                 max_shares_on_profile,
                                 sites_unavailable,
                                 self.server.no_of_books,
                                 self.server.auto_cw_cache).encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html',
                            msglen, cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_moved_feed',
                                    debug)
                return True
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                msg_str = json.dumps(following,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_moved_feed json',
                                    debug)
            else:
                http_404(self, 81)
            return True
    return False


def _show_inactive_feed(self, authorized: bool,
                        calling_domain: str, referer_domain: str,
                        path: str, base_dir: str, http_prefix: str,
                        domain: str, port: int, getreq_start_time,
                        proxy_type: str, cookie: str,
                        debug: str, curr_session,
                        dormant_months: int,
                        sites_unavailable: []) -> bool:
    """Shows the inactive accounts feed
    """
    following = \
        get_inactive_feed(base_dir, domain, port, path,
                          http_prefix, authorized,
                          dormant_months,
                          FOLLOWS_PER_PAGE, sites_unavailable)
    if following:
        if request_http(self.headers, debug):
            page_number = 1
            if '?page=' not in path:
                search_path = path
                # get a page of following, not the summary
                following = \
                    get_inactive_feed(base_dir, domain, port, path,
                                      http_prefix, authorized,
                                      dormant_months,
                                      FOLLOWS_PER_PAGE,
                                      sites_unavailable)
            else:
                page_number_str = path.split('?page=')[1]
                if ';' in page_number_str:
                    page_number_str = page_number_str.split(';')[0]
                if '#' in page_number_str:
                    page_number_str = page_number_str.split('#')[0]
                if len(page_number_str) > 5:
                    page_number_str = "1"
                if page_number_str.isdigit():
                    page_number = int(page_number_str)
                search_path = path.split('?page=')[0]
            get_person = \
                person_lookup(domain,
                              search_path.replace('/inactive', ''),
                              base_dir)
            if get_person:
                curr_session = \
                    establish_session("show_inactive_feed",
                                      curr_session, proxy_type,
                                      self.server)
                if not curr_session:
                    http_404(self, 82)
                    return True

                access_keys = self.server.access_keys
                city = None
                timezone = None
                if '/users/' in path:
                    nickname = path.split('/users/')[1]
                    if '/' in nickname:
                        nickname = nickname.split('/')[0]
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]

                    city = get_spoofed_city(self.server.city,
                                            base_dir, nickname, domain)
                    if self.server.account_timezone.get(nickname):
                        timezone = \
                            self.server.account_timezone.get(nickname)
                content_license_url = \
                    self.server.content_license_url
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                max_shares_on_profile = \
                    self.server.max_shares_on_profile
                sites_unavailable = \
                    self.server.sites_unavailable
                msg = \
                    html_profile(self.server.signing_priv_key_pem,
                                 self.server.rss_icon_at_top,
                                 self.server.icons_as_buttons,
                                 self.server.default_timeline,
                                 self.server.recent_posts_cache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 self.server.project_version,
                                 base_dir, http_prefix,
                                 authorized,
                                 get_person, 'inactive',
                                 curr_session,
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
                                 FOLLOWS_PER_PAGE,
                                 self.server.cw_lists,
                                 self.server.lists_enabled,
                                 content_license_url,
                                 timezone, bold_reading,
                                 self.server.buy_sites,
                                 None,
                                 max_shares_on_profile,
                                 sites_unavailable,
                                 self.server.no_of_books,
                                 self.server.auto_cw_cache).encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html',
                            msglen, cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_inactive_feed',
                                    debug)
                return True
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                msg_str = json.dumps(following,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_inactive_feed json',
                                    debug)
            else:
                http_404(self, 83)
            return True
    return False


def _show_followers_feed(self, authorized: bool,
                         calling_domain: str, referer_domain: str,
                         path: str, base_dir: str, http_prefix: str,
                         domain: str, port: int, getreq_start_time,
                         proxy_type: str, cookie: str,
                         debug: str, curr_session) -> bool:
    """Shows the followers feed
    """
    followers = \
        get_following_feed(base_dir, domain, port, path, http_prefix,
                           authorized, FOLLOWS_PER_PAGE, 'followers')
    if followers:
        if request_http(self.headers, debug):
            page_number = 1
            if '?page=' not in path:
                search_path = path
                # get a page of followers, not the summary
                followers = \
                    get_following_feed(base_dir,
                                       domain,
                                       port,
                                       path + '?page=1',
                                       http_prefix,
                                       authorized, FOLLOWS_PER_PAGE,
                                       'followers')
            else:
                page_number_str = path.split('?page=')[1]
                if ';' in page_number_str:
                    page_number_str = page_number_str.split(';')[0]
                if '#' in page_number_str:
                    page_number_str = page_number_str.split('#')[0]
                if len(page_number_str) > 5:
                    page_number_str = "1"
                if page_number_str.isdigit():
                    page_number = int(page_number_str)
                search_path = path.split('?page=')[0]
            get_person = \
                person_lookup(domain,
                              search_path.replace('/followers', ''),
                              base_dir)
            if get_person:
                curr_session = \
                    establish_session("show_followers_feed",
                                      curr_session, proxy_type,
                                      self.server)
                if not curr_session:
                    http_404(self, 84)
                    return True

                access_keys = self.server.access_keys
                city = None
                timezone = None
                if '/users/' in path:
                    nickname = path.split('/users/')[1]
                    if '/' in nickname:
                        nickname = nickname.split('/')[0]
                    if self.server.key_shortcuts.get(nickname):
                        access_keys = \
                            self.server.key_shortcuts[nickname]

                    city = get_spoofed_city(self.server.city,
                                            base_dir, nickname, domain)
                    if self.server.account_timezone.get(nickname):
                        timezone = \
                            self.server.account_timezone.get(nickname)
                content_license_url = \
                    self.server.content_license_url
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                if not authorized and \
                   self.server.hide_follows.get(nickname):
                    followers = {}
                max_shares_on_profile = \
                    self.server.max_shares_on_profile
                sites_unavailable = \
                    self.server.sites_unavailable
                msg = \
                    html_profile(self.server.signing_priv_key_pem,
                                 self.server.rss_icon_at_top,
                                 self.server.icons_as_buttons,
                                 self.server.default_timeline,
                                 self.server.recent_posts_cache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 self.server.project_version,
                                 base_dir,
                                 http_prefix,
                                 authorized,
                                 get_person, 'followers',
                                 curr_session,
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
                                 FOLLOWS_PER_PAGE,
                                 self.server.cw_lists,
                                 self.server.lists_enabled,
                                 content_license_url,
                                 timezone, bold_reading,
                                 self.server.buy_sites,
                                 None,
                                 max_shares_on_profile,
                                 sites_unavailable,
                                 self.server.no_of_books,
                                 self.server.auto_cw_cache).encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_followers_feed',
                                    debug)
                return True
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                if '/users/' in path:
                    nickname = path.split('/users/')[1]
                    if '/' in nickname:
                        nickname = nickname.split('/')[0]
                    if nickname and not authorized and \
                       self.server.hide_follows.get(nickname):
                        followers = {}

                msg_str = json.dumps(followers,
                                     ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                accept_str = self.headers['Accept']
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time,
                                    self.server.fitness,
                                    '_GET', '_show_followers_feed json',
                                    debug)
            else:
                http_404(self, 85)
        return True
    return False


def _show_person_profile(self, authorized: bool,
                         calling_domain: str,
                         referer_domain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str,
                         onion_domain: str, i2p_domain: str,
                         getreq_start_time,
                         proxy_type: str, cookie: str,
                         debug: str,
                         curr_session) -> bool:
    """Shows the profile for a person
    """
    # look up a person
    actor_json = person_lookup(domain, path, base_dir)
    if not actor_json:
        return False
    add_alternate_domains(actor_json, domain, onion_domain, i2p_domain)
    if request_http(self.headers, debug):
        curr_session = \
            establish_session("showPersonProfile",
                              curr_session, proxy_type,
                              self.server)
        if not curr_session:
            http_404(self, 86)
            return True

        access_keys = self.server.access_keys
        city = None
        timezone = None
        if '/users/' in path:
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if self.server.key_shortcuts.get(nickname):
                access_keys = \
                    self.server.key_shortcuts[nickname]

            city = get_spoofed_city(self.server.city,
                                    base_dir, nickname, domain)
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
        bold_reading = False
        if self.server.bold_reading.get(nickname):
            bold_reading = True
        max_shares_on_profile = \
            self.server.max_shares_on_profile
        sites_unavailable = \
            self.server.sites_unavailable
        msg = \
            html_profile(self.server.signing_priv_key_pem,
                         self.server.rss_icon_at_top,
                         self.server.icons_as_buttons,
                         self.server.default_timeline,
                         self.server.recent_posts_cache,
                         self.server.max_recent_posts,
                         self.server.translate,
                         self.server.project_version,
                         base_dir, http_prefix, authorized,
                         actor_json, 'posts', curr_session,
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
                         self.server.content_license_url,
                         timezone, bold_reading,
                         self.server.buy_sites,
                         None,
                         max_shares_on_profile,
                         sites_unavailable,
                         self.server.no_of_books,
                         self.server.auto_cw_cache).encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time,
                            self.server.fitness,
                            '_GET', '_show_person_profile',
                            debug)
        if self.server.debug:
            print('DEBUG: html actor sent')
    else:
        if secure_mode(curr_session, proxy_type, False,
                       self.server, self.headers, self.path):
            accept_str = self.headers['Accept']
            msg_str = json.dumps(actor_json, ensure_ascii=False)
            msg_str = convert_domains(calling_domain,
                                      referer_domain,
                                      msg_str, http_prefix,
                                      domain,
                                      self.server.onion_domain,
                                      self.server.i2p_domain)
            msg = msg_str.encode('utf-8')
            msglen = len(msg)
            if 'application/ld+json' in accept_str:
                set_headers(self, 'application/ld+json', msglen,
                            cookie, calling_domain, False)
            elif 'application/jrd+json' in accept_str:
                set_headers(self, 'application/jrd+json', msglen,
                            cookie, calling_domain, False)
            else:
                set_headers(self, 'application/activity+json', msglen,
                            cookie, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time,
                                self.server.fitness,
                                '_GET', '_show_person_profile json',
                                self.server.debug)
            if self.server.debug:
                print('DEBUG: json actor sent')
        else:
            http_404(self, 87)
    return True


def _masto_api_v2(self, path: str, calling_domain: str,
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
                  show_node_info_accounts: bool,
                  referer_domain: str,
                  debug: bool,
                  calling_site_timeout: int,
                  known_crawlers: {},
                  sites_unavailable: []) -> bool:
    """This is a vestigil mastodon v2 API for the purpose
    of returning an empty result to sites like
    https://mastopeek.app-dist.eu
    """
    if not path.startswith('/api/v2/'):
        return False

    if not referer_domain:
        if not (debug and self.server.unit_test):
            print('mastodon api v2 request has no referer domain ' +
                  str(ua_str))
            http_400(self)
            return True
    if referer_domain == domain_full:
        print('mastodon api v2 request from self')
        http_400(self)
        return True
    if self.server.masto_api_is_active:
        print('mastodon api v2 is busy during request from ' +
              referer_domain)
        http_503(self)
        return True
    self.server.masto_api_is_active = True
    # is this a real website making the call ?
    if not debug and not self.server.unit_test and referer_domain:
        # Does calling_domain look like a domain?
        if ' ' in referer_domain or \
           ';' in referer_domain or \
           '.' not in referer_domain:
            print('mastodon api v2 ' +
                  'referer does not look like a domain ' +
                  referer_domain)
            http_400(self)
            self.server.masto_api_is_active = False
            return True
        if not self.server.allow_local_network_access:
            if local_network_host(referer_domain):
                print('mastodon api v2 referer domain is from the ' +
                      'local network ' + referer_domain)
                http_400(self)
                self.server.masto_api_is_active = False
                return True
        if not referer_is_active(http_prefix,
                                 referer_domain, ua_str,
                                 calling_site_timeout,
                                 sites_unavailable):
            print('mastodon api v2 referer url is not active ' +
                  referer_domain)
            http_400(self)
            self.server.masto_api_is_active = False
            return True

    print('mastodon api v2: ' + path)
    print('mastodon api v2: authorized ' + str(authorized))
    print('mastodon api v2: nickname ' + str(nickname))
    print('mastodon api v2: referer ' + str(referer_domain))
    crawl_time = \
        update_known_crawlers(ua_str, base_dir,
                              known_crawlers,
                              self.server.last_known_crawler)
    if crawl_time is not None:
        self.server.last_known_crawler = crawl_time

    broch_mode = broch_mode_is_active(base_dir)
    send_json, send_json_str = \
        masto_api_v2_response(path,
                              calling_domain,
                              ua_str,
                              http_prefix,
                              base_dir,
                              domain,
                              domain_full,
                              onion_domain,
                              i2p_domain,
                              translate,
                              registration,
                              system_language,
                              project_version,
                              show_node_info_accounts,
                              broch_mode)

    if send_json is not None:
        msg_str = json.dumps(send_json)
        msg_str = convert_domains(calling_domain, referer_domain,
                                  msg_str, http_prefix, domain,
                                  onion_domain, i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        if has_accept(self, calling_domain):
            protocol_str = \
                get_json_content_from_accept(self.headers.get('Accept'))
            set_headers(self, protocol_str, msglen,
                        None, calling_domain, True)
        else:
            set_headers(self, 'application/ld+json', msglen,
                        None, calling_domain, True)
        write2(self, msg)
        if send_json_str:
            print(send_json_str)
        self.server.masto_api_is_active = False
        return True

    # no api v2 endpoints were matched
    http_404(self, 2)
    self.server.masto_api_is_active = False
    return True


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
                  custom_emoji: [],
                  show_node_info_accounts: bool,
                  referer_domain: str,
                  debug: bool,
                  calling_site_timeout: int,
                  known_crawlers: {},
                  sites_unavailable: []) -> bool:
    """This is a vestigil mastodon API for the purpose
    of returning an empty result to sites like
    https://mastopeek.app-dist.eu
    """
    if not path.startswith('/api/v1/'):
        return False

    if not referer_domain:
        if not (debug and self.server.unit_test):
            print('mastodon api request has no referer domain ' +
                  str(ua_str))
            http_400(self)
            return True
    if referer_domain == domain_full:
        print('mastodon api request from self')
        http_400(self)
        return True
    if self.server.masto_api_is_active:
        print('mastodon api is busy during request from ' +
              referer_domain)
        http_503(self)
        return True
    self.server.masto_api_is_active = True
    # is this a real website making the call ?
    if not debug and not self.server.unit_test and referer_domain:
        # Does calling_domain look like a domain?
        if ' ' in referer_domain or \
           ';' in referer_domain or \
           '.' not in referer_domain:
            print('mastodon api ' +
                  'referer does not look like a domain ' +
                  referer_domain)
            http_400(self)
            self.server.masto_api_is_active = False
            return True
        if not self.server.allow_local_network_access:
            if local_network_host(referer_domain):
                print('mastodon api referer domain is from the ' +
                      'local network ' + referer_domain)
                http_400(self)
                self.server.masto_api_is_active = False
                return True
        if not referer_is_active(http_prefix,
                                 referer_domain, ua_str,
                                 calling_site_timeout,
                                 sites_unavailable):
            print('mastodon api referer url is not active ' +
                  referer_domain)
            http_400(self)
            self.server.masto_api_is_active = False
            return True

    print('mastodon api v1: ' + path)
    print('mastodon api v1: authorized ' + str(authorized))
    print('mastodon api v1: nickname ' + str(nickname))
    print('mastodon api v1: referer ' + str(referer_domain))
    crawl_time = \
        update_known_crawlers(ua_str, base_dir,
                              known_crawlers,
                              self.server.last_known_crawler)
    if crawl_time is not None:
        self.server.last_known_crawler = crawl_time

    broch_mode = broch_mode_is_active(base_dir)
    send_json, send_json_str = \
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
                              custom_emoji,
                              show_node_info_accounts,
                              broch_mode)

    if send_json is not None:
        msg_str = json.dumps(send_json)
        msg_str = convert_domains(calling_domain, referer_domain,
                                  msg_str, http_prefix, domain,
                                  onion_domain, i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        if has_accept(self, calling_domain):
            protocol_str = \
                get_json_content_from_accept(self.headers.get('Accept'))
            set_headers(self, protocol_str, msglen,
                        None, calling_domain, True)
        else:
            set_headers(self, 'application/ld+json', msglen,
                        None, calling_domain, True)
        write2(self, msg)
        if send_json_str:
            print(send_json_str)
        self.server.masto_api_is_active = False
        return True

    # no api endpoints were matched
    http_404(self, 1)
    self.server.masto_api_is_active = False
    return True


def _show_post_from_file(self, post_filename: str, liked_by: str,
                         react_by: str, react_emoji: str,
                         authorized: bool,
                         calling_domain: str, referer_domain: str,
                         base_dir: str, http_prefix: str, nickname: str,
                         domain: str, port: int,
                         getreq_start_time,
                         proxy_type: str, cookie: str,
                         debug: str, include_create_wrapper: bool,
                         curr_session) -> bool:
    """Shows an individual post from its filename
    """
    if not os.path.isfile(post_filename):
        http_404(self, 71)
        self.server.getreq_busy = False
        return True

    post_json_object = load_json(post_filename)
    if not post_json_object:
        self.send_response(429)
        self.end_headers()
        self.server.getreq_busy = False
        return True

    # Only authorized viewers get to see likes on posts
    # Otherwize marketers could gain more social graph info
    if not authorized:
        pjo = post_json_object
        if not is_public_post(pjo):
            # only public posts may be viewed by unauthorized viewers
            http_401(self, 'only public posts ' +
                     'may be viewed by unauthorized viewers')
            self.server.getreq_busy = False
            return True
        remove_post_interactions(pjo, True)
    if request_http(self.headers, debug):
        timezone = None
        if self.server.account_timezone.get(nickname):
            timezone = \
                self.server.account_timezone.get(nickname)

        mitm = False
        if os.path.isfile(post_filename.replace('.json', '') +
                          '.mitm'):
            mitm = True

        bold_reading = False
        if self.server.bold_reading.get(nickname):
            bold_reading = True

        msg = \
            html_individual_post(self.server.recent_posts_cache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 base_dir,
                                 curr_session,
                                 self.server.cached_webfingers,
                                 self.server.person_cache,
                                 nickname, domain, port,
                                 authorized,
                                 post_json_object,
                                 http_prefix,
                                 self.server.project_version,
                                 liked_by, react_by, react_emoji,
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
                                 timezone, mitm, bold_reading,
                                 self.server.dogwhistles,
                                 self.server.min_images_for_accounts,
                                 self.server.buy_sites,
                                 self.server.auto_cw_cache)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                          cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_post_from_file',
                            debug)
    else:
        if secure_mode(curr_session, proxy_type, False,
                       self.server, self.headers, self.path):
            if not include_create_wrapper and \
               post_json_object['type'] == 'Create' and \
               has_object_dict(post_json_object):
                unwrapped_json = post_json_object['object']
                unwrapped_json['@context'] = \
                    get_individual_post_context()
                msg_str = json.dumps(unwrapped_json,
                                     ensure_ascii=False)
            else:
                msg_str = json.dumps(post_json_object,
                                     ensure_ascii=False)
            msg_str = convert_domains(calling_domain,
                                      referer_domain,
                                      msg_str, http_prefix,
                                      domain,
                                      self.server.onion_domain,
                                      self.server.i2p_domain)
            msg = msg_str.encode('utf-8')
            msglen = len(msg)
            protocol_str = \
                get_json_content_from_accept(self.headers['Accept'])
            set_headers(self, protocol_str, msglen,
                        None, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_post_from_file json',
                                debug)
        else:
            http_404(self, 73)
    self.server.getreq_busy = False
    return True
