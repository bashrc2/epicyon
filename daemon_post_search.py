__filename__ = "daemon_post_search.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core POST"

import errno
import urllib.parse
from socket import error as SocketError
from utils import get_instance_url
from httpcodes import write2
from httpheaders import login_headers
from httpheaders import redirect_headers
from utils import string_ends_with
from utils import has_users_path
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import get_full_domain
from utils import local_actor_url
from utils import remove_eol
from webapp_utils import get_avatar_image_url
from webapp_search import html_hashtag_search
from webapp_search import html_skills_search
from webapp_search import html_history_search
from webapp_search import html_search_emoji
from webapp_search import html_search_shared_items
from webapp_profile import html_profile_after_search
from follow import is_follower_of_person
from follow import is_following_actor
from session import establish_session
from daemon_utils import show_person_options


def receive_search_query(self, calling_domain: str, cookie: str,
                         authorized: bool, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str,
                         port: int, search_for_emoji: bool,
                         onion_domain: str, i2p_domain: str,
                         getreq_start_time, debug: bool,
                         curr_session, proxy_type: str,
                         max_posts_in_hashtag_feed: int,
                         max_posts_in_feed: int) -> None:
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

        my_posts_endings = (
            ' history', ' in sent', ' in outbox', ' in outgoing',
            ' in sent items', ' in sent posts', ' in outgoing posts',
            ' in my history', ' in my outbox', ' in my posts')
        bookmark_endings = (
            ' in my saved items', ' in my saved posts',
            ' in my bookmarks', ' in my saved', ' in my saves',
            ' in saved posts', ' in saved items', ' in bookmarks',
            ' in saved', ' in saves', ' bookmark')

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
                                    max_posts_in_hashtag_feed,
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
              string_ends_with(search_str, my_posts_endings)):
            # your post history search
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
                                    max_posts_in_feed,
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
              string_ends_with(search_str, bookmark_endings)):
            # bookmark search
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
                                    max_posts_in_feed,
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
                                              debug,
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
                                              onion_domain,
                                              i2p_domain,
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
                                         max_posts_in_feed,
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
                                         max_posts_in_feed,
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
