__filename__ = "daemon_get_reactions.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

from httpcodes import write2
from httpheaders import redirect_headers
from httpheaders import set_headers
from utils import load_json
from utils import locate_post
from utils import get_nickname_from_actor
from utils import get_instance_url
from webapp_post import html_emoji_reaction_picker
from fitnessFunctions import fitness_performance


def reaction_picker2(self, calling_domain: str, path: str,
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
                        '_GET', 'reaction_picker2',
                        debug)
