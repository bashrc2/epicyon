__filename__ = "daemon_get_hashtag.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import json
import urllib.parse
from httpcodes import http_400
from httpcodes import write2
from httpheaders import login_headers
from httpheaders import redirect_headers
from httpheaders import set_headers
from blocking import is_blocked_hashtag
from utils import convert_domains
from utils import get_nickname_from_actor
from webapp_utils import html_hashtag_blocked
from webapp_search import html_hashtag_search
from webapp_search import hashtag_search_rss
from webapp_search import hashtag_search_json
from fitnessFunctions import fitness_performance


def hashtag_search_rss2(self, calling_domain: str,
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


def hashtag_search_json2(self, calling_domain: str,
                         referer_domain: str,
                         path: str, cookie: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domain_full: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         getreq_start_time,
                         max_posts_in_feed: int) -> None:
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
                            page_number, max_posts_in_feed,
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


def hashtag_search2(self, calling_domain: str,
                    path: str, cookie: str,
                    base_dir: str, http_prefix: str,
                    domain: str, domain_full: str, port: int,
                    onion_domain: str, i2p_domain: str,
                    getreq_start_time,
                    curr_session,
                    max_posts_in_hashtag_feed: int) -> None:
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
