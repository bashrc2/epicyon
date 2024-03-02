__filename__ = "daemon_get_buttons.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import urllib.parse
from blocking import unmute_post
from blocking import mute_post
from bookmarks import bookmark_post
from bookmarks import undo_bookmark_post
from reaction import update_reaction_collection
from manualapprove import manual_deny_follow_request_thread
from manualapprove import manual_approve_follow_request_thread
from follow import follower_approval_active
from fitnessFunctions import fitness_performance
from daemon_utils import post_to_outbox
from posts import get_original_post_from_announce_url
from posts import save_post_to_box
from announce import create_announce
from session import establish_session
from httpheaders import set_headers
from httpheaders import redirect_headers
from httpcodes import write2
from httpcodes import http_400
from httpcodes import http_404
from like import update_likes_collection
from utils import undo_reaction_collection_entry
from utils import undo_likes_collection_entry
from utils import load_json
from utils import get_full_domain
from utils import get_domain_from_actor
from utils import delete_post
from utils import locate_post
from utils import is_dm
from utils import get_cached_post_filename
from utils import remove_id_ending
from utils import local_actor_url
from utils import get_nickname_from_actor
from utils import get_instance_url
from webapp_post import individual_post_as_html
from webapp_confirm import html_confirm_delete


def announce_button(self, calling_domain: str, path: str,
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


def announce_button_undo(self, calling_domain: str, path: str,
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


def follow_approve_button(self, calling_domain: str, path: str,
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


def follow_deny_button(self, calling_domain: str, path: str,
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


def like_button(self, calling_domain: str, path: str,
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


def like_button_undo(self, calling_domain: str, path: str,
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


def reaction_button(self, calling_domain: str, path: str,
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


def reaction_button_undo(self, calling_domain: str, path: str,
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


def bookmark_button(self, calling_domain: str, path: str,
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


def bookmark_button_undo(self, calling_domain: str, path: str,
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


def delete_button(self, calling_domain: str, path: str,
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


def mute_button(self, calling_domain: str, path: str,
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


def mute_button_undo(self, calling_domain: str, path: str,
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
