__filename__ = "conversation.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"


import os
from conversation import download_conversation_posts
from utils import get_config_param
from webapp_utils import html_header_with_external_style
from webapp_utils import html_post_separator
from webapp_utils import html_footer
from webapp_post import individual_post_as_html


def html_conversation_view(post_id: str,
                           translate: {}, base_dir: str,
                           http_prefix: str,
                           nickname: str, domain: str,
                           project_version: str,
                           recent_posts_cache: {},
                           max_recent_posts: int,
                           session,
                           cached_webfingers,
                           person_cache: {},
                           port: int,
                           yt_replace_domain: str,
                           twitter_replacement_domain: str,
                           show_published_date_only: bool,
                           peertube_instances: [],
                           allow_local_network_access: bool,
                           theme_name: str,
                           system_language: str,
                           max_like_count: int,
                           signing_priv_key_pem: str,
                           cw_lists: {},
                           lists_enabled: str,
                           timezone: str, bold_reading: bool,
                           dogwhistles: {}, access_keys: {},
                           min_images_for_accounts: [],
                           debug: bool, buy_sites: {}) -> str:
    """Show a page containing a conversation thread
    """
    conv_posts = \
        download_conversation_posts(session, http_prefix, base_dir,
                                    nickname, domain,
                                    post_id, debug)

    if not conv_posts:
        return None

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    conv_str = \
        html_header_with_external_style(css_filename, instance_title, None)

    separator_str = html_post_separator(base_dir, None)
    text_mode_separator = '<div class="transparent"><hr></div>\n'

    minimize_all_images = False
    if nickname in min_images_for_accounts:
        minimize_all_images = True
    for post_json_object in conv_posts:
        show_individual_post_icons = True
        allow_deletion = False
        post_str = \
            individual_post_as_html(signing_priv_key_pem,
                                    True, recent_posts_cache,
                                    max_recent_posts,
                                    translate, None,
                                    base_dir, session, cached_webfingers,
                                    person_cache,
                                    nickname, domain, port,
                                    post_json_object,
                                    None, True, allow_deletion,
                                    http_prefix, project_version,
                                    'search',
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    show_published_date_only,
                                    peertube_instances,
                                    allow_local_network_access,
                                    theme_name, system_language,
                                    max_like_count,
                                    show_individual_post_icons,
                                    show_individual_post_icons,
                                    False, False, False, False,
                                    cw_lists, lists_enabled,
                                    timezone, False, bold_reading,
                                    dogwhistles,
                                    minimize_all_images, None,
                                    buy_sites)
        if post_str:
            conv_str += text_mode_separator + separator_str + post_str

    conv_str += text_mode_separator + html_footer()
    return conv_str
