__filename__ = "webapp_column_left.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface Columns"

import os
from utils import get_config_param
from utils import get_nickname_from_actor
from utils import is_editor
from utils import is_artist
from utils import remove_domain_port
from utils import local_actor_url
from webapp_utils import shares_timeline_json
from webapp_utils import html_post_separator
from webapp_utils import get_left_image_file
from webapp_utils import header_buttons_front_screen
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_utils import get_banner_file
from webapp_utils import edit_text_field
from shares import share_category_icon


def _links_exist(base_dir: str) -> bool:
    """Returns true if links have been created
    """
    links_filename = base_dir + '/accounts/links.txt'
    return os.path.isfile(links_filename)


def _get_left_column_shares(base_dir: str,
                            http_prefix: str, domain: str, domain_full: str,
                            nickname: str,
                            max_shares_in_left_column: int,
                            translate: {},
                            shared_items_federated_domains: []) -> []:
    """get any shares and turn them into the left column links format
    """
    page_number = 1
    actor = local_actor_url(http_prefix, nickname, domain_full)
    # NOTE: this could potentially be slow if the number of federated
    # shared items is large
    shares_json, last_page = \
        shares_timeline_json(actor, page_number, max_shares_in_left_column,
                             base_dir, domain, nickname,
                             max_shares_in_left_column,
                             shared_items_federated_domains, 'shares')
    if not shares_json:
        return []

    links_list = []
    ctr = 0
    for published, item in shares_json.items():
        sharedesc = item['displayName']
        if '<' in sharedesc or '?' in sharedesc:
            continue
        share_id = item['shareId']
        # selecting this link calls html_show_share
        share_link = actor + '?showshare=' + share_id
        if item.get('category'):
            share_link += '?category=' + item['category']
            shareCategory = share_category_icon(item['category'])

        links_list.append(shareCategory + sharedesc + ' ' + share_link)
        ctr += 1
        if ctr >= max_shares_in_left_column:
            break

    if links_list:
        links_list = ['* ' + translate['Shares']] + links_list
    return links_list


def _get_left_column_wanted(base_dir: str,
                            http_prefix: str, domain: str, domain_full: str,
                            nickname: str,
                            max_shares_in_left_column: int,
                            translate: {},
                            shared_items_federated_domains: []) -> []:
    """get any wanted items and turn them into the left column links format
    """
    page_number = 1
    actor = local_actor_url(http_prefix, nickname, domain_full)
    # NOTE: this could potentially be slow if the number of federated
    # wanted items is large
    shares_json, last_page = \
        shares_timeline_json(actor, page_number, max_shares_in_left_column,
                             base_dir, domain, nickname,
                             max_shares_in_left_column,
                             shared_items_federated_domains, 'wanted')
    if not shares_json:
        return []

    links_list = []
    ctr = 0
    for published, item in shares_json.items():
        sharedesc = item['displayName']
        if '<' in sharedesc or ';' in sharedesc:
            continue
        share_id = item['shareId']
        # selecting this link calls html_show_share
        share_link = actor + '?showwanted=' + share_id
        links_list.append(sharedesc + ' ' + share_link)
        ctr += 1
        if ctr >= max_shares_in_left_column:
            break

    if links_list:
        links_list = ['* ' + translate['Wanted']] + links_list
    return links_list


def get_left_column_content(base_dir: str, nickname: str, domain_full: str,
                            http_prefix: str, translate: {},
                            editor: bool, artist: bool,
                            showBackButton: bool, timelinePath: str,
                            rss_icon_at_top: bool, showHeaderImage: bool,
                            frontPage: bool, theme: str,
                            access_keys: {},
                            shared_items_federated_domains: []) -> str:
    """Returns html content for the left column
    """
    html_str = ''

    separator_str = html_post_separator(base_dir, 'left')
    domain = remove_domain_port(domain_full)

    editImageClass = ''
    if showHeaderImage:
        leftImageFile, leftColumnImageFilename = \
            get_left_image_file(base_dir, nickname, domain, theme)

        # show the image at the top of the column
        editImageClass = 'leftColEdit'
        if os.path.isfile(leftColumnImageFilename):
            editImageClass = 'leftColEditImage'
            html_str += \
                '\n      <center>\n        <img class="leftColImg" ' + \
                'alt="" loading="lazy" src="/users/' + \
                nickname + '/' + leftImageFile + '" />\n' + \
                '      </center>\n'

    if showBackButton:
        html_str += \
            '      <div>      <a href="' + timelinePath + '">' + \
            '<button class="cancelbtn">' + \
            translate['Go Back'] + '</button></a>\n'

    if (editor or rss_icon_at_top) and not showHeaderImage:
        html_str += '<div class="columnIcons">'

    if editImageClass == 'leftColEdit':
        html_str += '\n      <center>\n'

    html_str += '      <div class="leftColIcons">\n'

    if editor:
        # show the edit icon
        html_str += \
            '      <a href="/users/' + nickname + '/editlinks" ' + \
            'accesskey="' + access_keys['menuEdit'] + '">' + \
            '<img class="' + editImageClass + '" loading="lazy" alt="' + \
            translate['Edit Links'] + ' | " title="' + \
            translate['Edit Links'] + '" src="/icons/edit.png" /></a>\n'

    if artist:
        # show the theme designer icon
        html_str += \
            '      <a href="/users/' + nickname + '/themedesigner" ' + \
            'accesskey="' + access_keys['menuThemeDesigner'] + '">' + \
            '<img class="' + editImageClass + '" loading="lazy" alt="' + \
            translate['Theme Designer'] + ' | " title="' + \
            translate['Theme Designer'] + '" src="/icons/theme.png" /></a>\n'

    # RSS icon
    if nickname != 'news':
        # rss feed for this account
        rssUrl = http_prefix + '://' + domain_full + \
            '/blog/' + nickname + '/rss.xml'
    else:
        # rss feed for all accounts on the instance
        rssUrl = http_prefix + '://' + domain_full + '/blog/rss.xml'
    if not frontPage:
        rssTitle = translate['RSS feed for your blog']
    else:
        rssTitle = translate['RSS feed for this site']
    rssIconStr = \
        '      <a href="' + rssUrl + '"><img class="' + editImageClass + \
        '" loading="lazy" alt="' + rssTitle + '" title="' + rssTitle + \
        '" src="/icons/logorss.png" /></a>\n'
    if rss_icon_at_top:
        html_str += rssIconStr
    html_str += '      </div>\n'

    if editImageClass == 'leftColEdit':
        html_str += '      </center>\n'

    if (editor or rss_icon_at_top) and not showHeaderImage:
        html_str += '</div><br>'

    # if showHeaderImage:
    #     html_str += '<br>'

    # flag used not to show the first separator
    first_separator_added = False

    links_filename = base_dir + '/accounts/links.txt'
    linksFileContainsEntries = False
    links_list = None
    if os.path.isfile(links_filename):
        with open(links_filename, 'r') as f:
            links_list = f.readlines()

    if not frontPage:
        # show a number of shares
        max_shares_in_left_column = 3
        sharesList = \
            _get_left_column_shares(base_dir,
                                    http_prefix, domain, domain_full, nickname,
                                    max_shares_in_left_column, translate,
                                    shared_items_federated_domains)
        if links_list and sharesList:
            links_list = sharesList + links_list

        wantedList = \
            _get_left_column_wanted(base_dir,
                                    http_prefix, domain, domain_full, nickname,
                                    max_shares_in_left_column, translate,
                                    shared_items_federated_domains)
        if links_list and wantedList:
            links_list = wantedList + links_list

    newTabStr = ' target="_blank" rel="nofollow noopener noreferrer"'
    if links_list:
        html_str += '<nav>\n'
        for lineStr in links_list:
            if ' ' not in lineStr:
                if '#' not in lineStr:
                    if '*' not in lineStr:
                        if not lineStr.startswith('['):
                            if not lineStr.startswith('=> '):
                                continue
            lineStr = lineStr.strip()
            linkStr = None
            if not lineStr.startswith('['):
                words = lineStr.split(' ')
                # get the link
                for word in words:
                    if word == '#':
                        continue
                    if word == '*':
                        continue
                    if word == '=>':
                        continue
                    if '://' in word:
                        linkStr = word
                        break
            else:
                # markdown link
                if ']' not in lineStr:
                    continue
                if '(' not in lineStr:
                    continue
                if ')' not in lineStr:
                    continue
                linkStr = lineStr.split('(')[1]
                if ')' not in linkStr:
                    continue
                linkStr = linkStr.split(')')[0]
                if '://' not in linkStr:
                    continue
                lineStr = lineStr.split('[')[1]
                if ']' not in lineStr:
                    continue
                lineStr = lineStr.split(']')[0]
            if linkStr:
                lineStr = lineStr.replace(linkStr, '').strip()
                # avoid any dubious scripts being added
                if '<' not in lineStr:
                    # remove trailing comma if present
                    if lineStr.endswith(','):
                        lineStr = lineStr[:len(lineStr)-1]
                    # add link to the returned html
                    if '?showshare=' not in linkStr and \
                       '?showwarning=' not in linkStr:
                        html_str += \
                            '      <p><a href="' + linkStr + \
                            '"' + newTabStr + '>' + \
                            lineStr + '</a></p>\n'
                    else:
                        html_str += \
                            '      <p><a href="' + linkStr + \
                            '">' + lineStr + '</a></p>\n'
                    linksFileContainsEntries = True
                elif lineStr.startswith('=> '):
                    # gemini style link
                    lineStr = lineStr.replace('=> ', '')
                    lineStr = lineStr.replace(linkStr, '')
                    # add link to the returned html
                    if '?showshare=' not in linkStr and \
                       '?showwarning=' not in linkStr:
                        html_str += \
                            '      <p><a href="' + linkStr + \
                            '"' + newTabStr + '>' + \
                            lineStr.strip() + '</a></p>\n'
                    else:
                        html_str += \
                            '      <p><a href="' + linkStr + \
                            '">' + lineStr.strip() + '</a></p>\n'
                    linksFileContainsEntries = True
            else:
                if lineStr.startswith('#') or lineStr.startswith('*'):
                    lineStr = lineStr[1:].strip()
                    if first_separator_added:
                        html_str += separator_str
                    first_separator_added = True
                    html_str += \
                        '      <h3 class="linksHeader">' + \
                        lineStr + '</h3>\n'
                else:
                    html_str += \
                        '      <p>' + lineStr + '</p>\n'
                linksFileContainsEntries = True
        html_str += '</nav>\n'

    if first_separator_added:
        html_str += separator_str
    html_str += \
        '<p class="login-text"><a href="/users/' + nickname + \
        '/catalog.csv">' + translate['Shares Catalog'] + '</a></p>'
    html_str += \
        '<p class="login-text"><a href="/users/' + \
        nickname + '/accesskeys" accesskey="' + \
        access_keys['menuKeys'] + '">' + \
        translate['Key Shortcuts'] + '</a></p>'
    html_str += \
        '<p class="login-text"><a href="/about">' + \
        translate['About this Instance'] + '</a></p>'
    html_str += \
        '<p class="login-text"><a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>'

    if linksFileContainsEntries and not rss_icon_at_top:
        html_str += '<br><div class="columnIcons">' + rssIconStr + '</div>'

    return html_str


def html_links_mobile(css_cache: {}, base_dir: str,
                      nickname: str, domain_full: str,
                      http_prefix: str, translate,
                      timelinePath: str, authorized: bool,
                      rss_icon_at_top: bool,
                      icons_as_buttons: bool,
                      default_timeline: str,
                      theme: str, access_keys: {},
                      shared_items_federated_domains: []) -> str:
    """Show the left column links within mobile view
    """
    html_str = ''

    # the css filename
    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    # is the user a site editor?
    if nickname == 'news':
        editor = False
        artist = False
    else:
        editor = is_editor(base_dir, nickname)
        artist = is_artist(base_dir, nickname)

    domain = remove_domain_port(domain_full)

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    html_str = \
        html_header_with_external_style(css_filename, instance_title, None)
    banner_file, banner_filename = \
        get_banner_file(base_dir, nickname, domain, theme)
    html_str += \
        '<a href="/users/' + nickname + '/' + default_timeline + '" ' + \
        'accesskey="' + access_keys['menuTimeline'] + '">' + \
        '<img loading="lazy" class="timeline-banner" ' + \
        'alt="' + translate['Switch to timeline view'] + '" ' + \
        'src="/users/' + nickname + '/' + banner_file + '" /></a>\n'

    html_str += '<div class="col-left-mobile">\n'
    html_str += '<center>' + \
        header_buttons_front_screen(translate, nickname,
                                    'links', authorized,
                                    icons_as_buttons) + '</center>'
    html_str += \
        get_left_column_content(base_dir, nickname, domain_full,
                                http_prefix, translate,
                                editor, artist,
                                False, timelinePath,
                                rss_icon_at_top, False, False,
                                theme, access_keys,
                                shared_items_federated_domains)
    if editor and not _links_exist(base_dir):
        html_str += '<br><br><br>\n<center>\n  '
        html_str += translate['Select the edit icon to add web links']
        html_str += '\n</center>\n'

    # end of col-left-mobile
    html_str += '</div>\n'

    html_str += '</div>\n' + html_footer()
    return html_str


def html_edit_links(css_cache: {}, translate: {}, base_dir: str, path: str,
                    domain: str, port: int, http_prefix: str,
                    default_timeline: str, theme: str,
                    access_keys: {}) -> str:
    """Shows the edit links screen
    """
    if '/users/' not in path:
        return ''
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '').replace('/wanted', '')

    nickname = get_nickname_from_actor(path)
    if not nickname:
        return ''

    # is the user a moderator?
    if not is_editor(base_dir, nickname):
        return ''

    css_filename = base_dir + '/epicyon-links.css'
    if os.path.isfile(base_dir + '/links.css'):
        css_filename = base_dir + '/links.css'

    # filename of the banner shown at the top
    banner_file, _ = \
        get_banner_file(base_dir, nickname, domain, theme)

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    edit_links_form = \
        html_header_with_external_style(css_filename, instance_title, None)

    # top banner
    edit_links_form += \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + default_timeline + \
        '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + access_keys['menuTimeline'] + '">\n'
    edit_links_form += \
        '<img loading="lazy" class="timeline-banner" ' + \
        'alt = "" src="' + \
        '/users/' + nickname + '/' + banner_file + '" /></a>\n' + \
        '</header>\n'

    edit_links_form += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/linksdata">\n'
    edit_links_form += \
        '  <div class="vertical-center">\n'
    edit_links_form += \
        '    <div class="containerSubmitNewPost">\n'
    edit_links_form += \
        '      <h1>' + translate['Edit Links'] + '</h1>'
    edit_links_form += \
        '      <input type="submit" name="submitLinks" value="' + \
        translate['Submit'] + '" ' + \
        'accesskey="' + access_keys['submitButton'] + '">\n'
    edit_links_form += \
        '    </div>\n'

    links_filename = base_dir + '/accounts/links.txt'
    links_str = ''
    if os.path.isfile(links_filename):
        with open(links_filename, 'r') as fp_links:
            links_str = fp_links.read()

    edit_links_form += \
        '<div class="container">'
    edit_links_form += \
        '  ' + \
        translate['One link per line. Description followed by the link.'] + \
        '<br>'
    new_col_link_str = translate['New link title and URL']
    edit_links_form += \
        edit_text_field(None, 'newColLink', '', new_col_link_str)
    edit_links_form += \
        '  <textarea id="message" name="editedLinks" ' + \
        'style="height:80vh" spellcheck="false">' + links_str + '</textarea>'
    edit_links_form += \
        '</div>'

    # the admin can edit terms of service and about text
    admin_nickname = get_config_param(base_dir, 'admin')
    if admin_nickname:
        if nickname == admin_nickname:
            about_filename = base_dir + '/accounts/about.md'
            about_str = ''
            if os.path.isfile(about_filename):
                with open(about_filename, 'r') as fp_about:
                    about_str = fp_about.read()

            edit_links_form += \
                '<div class="container">'
            edit_links_form += \
                '  ' + \
                translate['About this Instance'] + \
                '<br>'
            edit_links_form += \
                '  <textarea id="message" name="editedAbout" ' + \
                'style="height:100vh" spellcheck="true" autocomplete="on">' + \
                about_str + '</textarea>'
            edit_links_form += \
                '</div>'

            tos_filename = base_dir + '/accounts/tos.md'
            tos_str = ''
            if os.path.isfile(tos_filename):
                with open(tos_filename, 'r') as fp:
                    tos_str = fp.read()

            edit_links_form += \
                '<div class="container">'
            edit_links_form += \
                '  ' + \
                translate['Terms of Service'] + \
                '<br>'
            edit_links_form += \
                '  <textarea id="message" name="editedTOS" ' + \
                'style="height:100vh" spellcheck="true" autocomplete="on">' + \
                tos_str + '</textarea>'
            edit_links_form += \
                '</div>'

    edit_links_form += html_footer()
    return edit_links_form
