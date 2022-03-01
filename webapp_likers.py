__filename__ = "webapp_likers.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from utils import locate_post
from utils import get_config_param
from utils import get_account_timezone
from utils import get_display_name
from utils import get_nickname_from_actor
from utils import has_object_dict
from utils import load_json
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_utils import get_banner_file
from webapp_post import individual_post_as_html


def html_likers_of_post(base_dir: str, nickname: str,
                        domain: str, port: int,
                        post_url: str, translate: {},
                        http_prefix: str,
                        theme: str, access_keys: {},
                        recent_posts_cache: {}, max_recent_posts: int,
                        session, cached_webfingers: {},
                        person_cache: {},
                        project_version: str,
                        yt_replace_domain: str,
                        twitter_replacement_domain: str,
                        show_published_date_only: bool,
                        peertube_instances: [],
                        allow_local_network_access: bool,
                        system_language: str,
                        max_like_count: int, signing_priv_key_pem: str,
                        cw_lists: {}, lists_enabled: str,
                        boxName: str, default_timeline: str) -> str:
    """Returns html for a screen showing who liked a post
    """
    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instance_title = get_config_param(base_dir, 'instanceTitle')
    html_str = \
        html_header_with_external_style(css_filename, instance_title, None)

    # get the post which was liked
    filename = locate_post(base_dir, nickname, domain, post_url)
    if not filename:
        return None
    post_json_object = load_json(filename)
    if not post_json_object:
        return None
    if not post_json_object.get('actor') or not post_json_object.get('object'):
        return None

    # show the top banner
    banner_file, _ = \
        get_banner_file(base_dir, nickname, domain, theme)
    html_str += \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + default_timeline + \
        '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + access_keys['menuTimeline'] + '">\n'
    html_str += '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + banner_file + '" alt="" /></a>\n' + \
        '</header>\n'

    # show the post which was liked
    timezone = get_account_timezone(base_dir, nickname, domain)
    html_str += \
        individual_post_as_html(signing_priv_key_pem,
                                True, recent_posts_cache,
                                max_recent_posts,
                                translate, None,
                                base_dir, session,
                                cached_webfingers,
                                person_cache,
                                nickname, domain, port,
                                post_json_object,
                                None, True, False,
                                http_prefix,
                                project_version,
                                boxName,
                                yt_replace_domain,
                                twitter_replacement_domain,
                                show_published_date_only,
                                peertube_instances,
                                allow_local_network_access,
                                theme, system_language,
                                max_like_count,
                                False, False, False,
                                False, False, False,
                                cw_lists, lists_enabled,
                                timezone)

    # show likers beneath the post
    obj = post_json_object
    if has_object_dict(post_json_object):
        obj = post_json_object['object']
    if not obj.get('likes'):
        return None
    if not isinstance(obj['likes'], dict):
        return None
    if not obj['likes'].get('items'):
        return None

    html_str += '<center><h2>' + translate['Liked by'] + '</h2></center>\n'

    likers_list = ''
    for like_item in obj['likes']['items']:
        if not like_item.get('actor'):
            continue
        liker_actor = like_item['actor']
        liker_display_name = \
            get_display_name(base_dir, liker_actor, person_cache)
        if liker_display_name:
            liker_name = liker_display_name
        else:
            liker_name = get_nickname_from_actor(liker_actor)
        if likers_list:
            likers_list += ' '        
        likers_list += \
            '<label class="labels">' + \
            '<a href="' + liker_actor + '">' + liker_name + '</a>' + \
            '</label>'
    html_str += '<center>\n' + likers_list + '\n</center>\n'

    return html_str + html_footer()
