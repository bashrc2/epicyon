__filename__ = "webapp_frontscreen.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from utils import is_system_account
from utils import get_domain_from_actor
from utils import get_config_param
from person import person_box_json
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_utils import get_banner_file
from webapp_utils import html_post_separator
from webapp_utils import header_buttons_front_screen
from webapp_column_left import get_left_column_content
from webapp_column_right import get_right_column_content
from webapp_post import individual_post_as_html


def _html_front_screen_posts(recent_posts_cache: {}, max_recent_posts: int,
                             translate: {},
                             base_dir: str, http_prefix: str,
                             nickname: str, domain: str, port: int,
                             session, cached_webfingers: {}, person_cache: {},
                             project_version: str,
                             yt_replace_domain: str,
                             twitter_replacement_domain: str,
                             show_published_date_only: bool,
                             peertube_instances: [],
                             allow_local_network_access: bool,
                             theme_name: str, system_language: str,
                             max_like_count: int,
                             signing_priv_key_pem: str, cw_lists: {},
                             lists_enabled: str) -> str:
    """Shows posts on the front screen of a news instance
    These should only be public blog posts from the features timeline
    which is the blog timeline of the news actor
    """
    separatorStr = html_post_separator(base_dir, None)
    profileStr = ''
    maxItems = 4
    ctr = 0
    currPage = 1
    boxName = 'tlfeatures'
    authorized = True
    while ctr < maxItems and currPage < 4:
        outboxFeedPathStr = \
            '/users/' + nickname + '/' + boxName + \
            '?page=' + str(currPage)
        outboxFeed = \
            person_box_json({}, session, base_dir, domain, port,
                            outboxFeedPathStr,
                            http_prefix, 10, boxName,
                            authorized, 0, False, 0)
        if not outboxFeed:
            break
        if len(outboxFeed['orderedItems']) == 0:
            break
        for item in outboxFeed['orderedItems']:
            if item['type'] == 'Create':
                postStr = \
                    individual_post_as_html(signing_priv_key_pem,
                                            True, recent_posts_cache,
                                            max_recent_posts,
                                            translate, None,
                                            base_dir, session,
                                            cached_webfingers,
                                            person_cache,
                                            nickname, domain, port, item,
                                            None, True, False,
                                            http_prefix,
                                            project_version, 'inbox',
                                            yt_replace_domain,
                                            twitter_replacement_domain,
                                            show_published_date_only,
                                            peertube_instances,
                                            allow_local_network_access,
                                            theme_name, system_language,
                                            max_like_count,
                                            False, False, False,
                                            True, False, False,
                                            cw_lists, lists_enabled)
                if postStr:
                    profileStr += postStr + separatorStr
                    ctr += 1
                    if ctr >= maxItems:
                        break
        currPage += 1
    return profileStr


def html_front_screen(signing_priv_key_pem: str,
                      rss_icon_at_top: bool,
                      css_cache: {}, icons_as_buttons: bool,
                      defaultTimeline: str,
                      recent_posts_cache: {}, max_recent_posts: int,
                      translate: {}, project_version: str,
                      base_dir: str, http_prefix: str, authorized: bool,
                      profile_json: {}, selected: str,
                      session, cached_webfingers: {}, person_cache: {},
                      yt_replace_domain: str,
                      twitter_replacement_domain: str,
                      show_published_date_only: bool,
                      newswire: {}, theme: str,
                      peertube_instances: [],
                      allow_local_network_access: bool,
                      access_keys: {},
                      system_language: str, max_like_count: int,
                      shared_items_federated_domains: [],
                      extraJson: {},
                      pageNumber: int,
                      maxItemsPerPage: int,
                      cw_lists: {}, lists_enabled: str) -> str:
    """Show the news instance front screen
    """
    nickname = profile_json['preferredUsername']
    if not nickname:
        return ""
    if not is_system_account(nickname):
        return ""
    domain, port = get_domain_from_actor(profile_json['id'])
    if not domain:
        return ""
    domain_full = domain
    if port:
        domain_full = domain + ':' + str(port)

    loginButton = header_buttons_front_screen(translate, nickname,
                                              'features', authorized,
                                              icons_as_buttons)

    # If this is the news account then show a different banner
    banner_file, banner_filename = \
        get_banner_file(base_dir, nickname, domain, theme)
    profileHeaderStr = \
        '<img loading="lazy" class="timeline-banner" ' + \
        'src="/users/' + nickname + '/' + banner_file + '" />\n'
    if loginButton:
        profileHeaderStr += '<center>' + loginButton + '</center>\n'

    profileHeaderStr += \
        '<table class="timeline">\n' + \
        '  <colgroup>\n' + \
        '    <col span="1" class="column-left">\n' + \
        '    <col span="1" class="column-center">\n' + \
        '    <col span="1" class="column-right">\n' + \
        '  </colgroup>\n' + \
        '  <tbody>\n' + \
        '    <tr>\n' + \
        '      <td valign="top" class="col-left">\n'
    profileHeaderStr += \
        get_left_column_content(base_dir, 'news', domain_full,
                                http_prefix, translate,
                                False, False,
                                False, None, rss_icon_at_top, True,
                                True, theme, access_keys,
                                shared_items_federated_domains)
    profileHeaderStr += \
        '      </td>\n' + \
        '      <td valign="top" class="col-center">\n'

    profileStr = profileHeaderStr

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    licenseStr = ''
    banner_file, banner_filename = \
        get_banner_file(base_dir, nickname, domain, theme)
    profileStr += \
        _html_front_screen_posts(recent_posts_cache, max_recent_posts,
                                 translate,
                                 base_dir, http_prefix,
                                 nickname, domain, port,
                                 session, cached_webfingers, person_cache,
                                 project_version,
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 peertube_instances,
                                 allow_local_network_access,
                                 theme, system_language,
                                 max_like_count,
                                 signing_priv_key_pem,
                                 cw_lists, lists_enabled) + licenseStr

    # Footer which is only used for system accounts
    profileFooterStr = '      </td>\n'
    profileFooterStr += '      <td valign="top" class="col-right">\n'
    profileFooterStr += \
        get_right_column_content(base_dir, 'news', domain_full,
                                 http_prefix, translate,
                                 False, False, newswire, False,
                                 False, None, False, False,
                                 False, True, authorized, True, theme,
                                 defaultTimeline, access_keys)
    profileFooterStr += \
        '      </td>\n' + \
        '  </tr>\n' + \
        '  </tbody>\n' + \
        '</table>\n'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    profileStr = \
        html_header_with_external_style(css_filename, instanceTitle, None) + \
        profileStr + profileFooterStr + html_footer()
    return profileStr
