__filename__ = "daemon_get_timeline.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core GET"

import json
from securemode import secure_mode
from posts import is_moderator
from utils import is_artist
from utils import is_editor
from utils import convert_domains
from utils import get_json_content_from_accept
from httpheaders import set_headers
from httpcodes import http_404
from httpcodes import write2
from httprequests import request_http
from person import person_box_json
from webapp_minimalbutton import is_minimal
from webapp_timeline import html_outbox
from webapp_timeline import html_bookmarks
from webapp_timeline import html_wanted
from webapp_timeline import html_shares
from webapp_timeline import html_inbox_dms
from webapp_timeline import html_inbox_features
from webapp_timeline import html_inbox_news
from webapp_timeline import html_inbox_blogs
from webapp_timeline import html_inbox_media
from webapp_timeline import html_inbox_replies
from webapp_timeline import html_inbox
from webapp_moderation import html_moderation
from fitnessFunctions import fitness_performance


def show_media_timeline(self, authorized: bool,
                        calling_domain: str, referer_domain: str,
                        path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, port: int,
                        getreq_start_time,
                        cookie: str, debug: str,
                        curr_session, ua_str: str,
                        max_posts_in_media_feed: int) -> bool:
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
                                max_posts_in_media_feed, 'tlmedia',
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
                                        max_posts_in_media_feed, 'tlmedia',
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
                                     page_number, max_posts_in_media_feed,
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


def show_blogs_timeline(self, authorized: bool,
                        calling_domain: str, referer_domain: str,
                        path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, port: int,
                        getreq_start_time,
                        cookie: str, debug: str,
                        curr_session, ua_str: str,
                        max_posts_in_blogs_feed: int) -> bool:
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
                                max_posts_in_blogs_feed, 'tlblogs',
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
                                        max_posts_in_blogs_feed, 'tlblogs',
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
                                     page_number, max_posts_in_blogs_feed,
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


def show_news_timeline(self, authorized: bool,
                       calling_domain: str, referer_domain: str,
                       path: str,
                       base_dir: str, http_prefix: str,
                       domain: str, port: int,
                       getreq_start_time,
                       cookie: str, debug: str,
                       curr_session, ua_str: str,
                       max_posts_in_news_feed: int) -> bool:
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
                                max_posts_in_news_feed, 'tlnews',
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
                                        max_posts_in_news_feed, 'tlnews',
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
                                    page_number, max_posts_in_news_feed,
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


def show_features_timeline(self, authorized: bool,
                           calling_domain: str, referer_domain: str,
                           path: str, base_dir: str, http_prefix: str,
                           domain: str, port: int,
                           getreq_start_time,
                           cookie: str, debug: str,
                           curr_session, ua_str: str,
                           max_posts_in_news_feed: int) -> bool:
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
                                max_posts_in_news_feed, 'tlfeatures',
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
                                        max_posts_in_news_feed,
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
                                        max_posts_in_news_feed,
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


def show_shares_timeline(self, authorized: bool,
                         calling_domain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, port: int,
                         getreq_start_time,
                         cookie: str, debug: str,
                         curr_session, ua_str: str,
                         max_posts_in_feed: int) -> bool:
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
                                page_number, max_posts_in_feed,
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


def show_wanted_timeline(self, authorized: bool,
                         calling_domain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, port: int,
                         getreq_start_time,
                         cookie: str, debug: str,
                         curr_session, ua_str: str,
                         max_posts_in_feed: int) -> bool:
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
                                page_number, max_posts_in_feed,
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


def show_bookmarks_timeline(self, authorized: bool,
                            calling_domain: str, referer_domain: str,
                            path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, port: int,
                            getreq_start_time,
                            cookie: str, debug: str,
                            curr_session, ua_str: str,
                            max_posts_in_feed: int) -> bool:
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
                                max_posts_in_feed, 'tlbookmarks',
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
                                            max_posts_in_feed,
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
                                       page_number, max_posts_in_feed,
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


def show_outbox_timeline(self, authorized: bool,
                         calling_domain: str, referer_domain: str,
                         path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, port: int,
                         getreq_start_time,
                         cookie: str, debug: str,
                         curr_session, ua_str: str,
                         proxy_type: str,
                         max_posts_in_feed: int) -> bool:
    """Shows the outbox timeline
    """
    # get outbox feed for a person
    outbox_feed = \
        person_box_json(self.server.recent_posts_cache,
                        base_dir, domain, port, path,
                        http_prefix, max_posts_in_feed, 'outbox',
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
                                max_posts_in_feed, 'outbox',
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
                            page_number, max_posts_in_feed,
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


def show_mod_timeline(self, authorized: bool,
                      calling_domain: str, referer_domain: str,
                      path: str, base_dir: str, http_prefix: str,
                      domain: str, port: int, getreq_start_time,
                      cookie: str, debug: str,
                      curr_session, ua_str: str,
                      max_posts_in_feed: int) -> bool:
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
                                max_posts_in_feed, 'moderation',
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
                                            max_posts_in_feed,
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
                                        page_number, max_posts_in_feed,
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


def show_dms(self, authorized: bool,
             calling_domain: str, referer_domain: str,
             path: str, base_dir: str, http_prefix: str,
             domain: str, port: int,
             getreq_start_time,
             cookie: str, debug: str,
             curr_session, ua_str: str,
             max_posts_in_feed: int) -> bool:
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
                                max_posts_in_feed, 'dm',
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
                                            max_posts_in_feed, 'dm',
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
                                       page_number, max_posts_in_feed,
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


def show_replies(self, authorized: bool,
                 calling_domain: str, referer_domain: str,
                 path: str,
                 base_dir: str, http_prefix: str,
                 domain: str, port: int,
                 getreq_start_time,
                 cookie: str, debug: str,
                 curr_session, ua_str: str,
                 max_posts_in_feed: int) -> bool:
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
                                max_posts_in_feed, 'tlreplies',
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
                                        max_posts_in_feed, 'tlreplies',
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
                                       page_number, max_posts_in_feed,
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


def show_inbox(self, authorized: bool,
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
               ua_str: str,
               max_posts_in_feed: int) -> bool:
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
                                max_posts_in_feed, 'inbox',
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
                                            max_posts_in_feed, 'inbox',
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
                                   page_number, max_posts_in_feed,
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
