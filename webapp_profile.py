__filename__ = "webapp_profile.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from pprint import pprint
from webfinger import webfinger_handle
from utils import get_display_name
from utils import is_group_account
from utils import has_object_dict
from utils import get_occupation_name
from utils import get_locked_account
from utils import get_full_domain
from utils import is_artist
from utils import is_dormant
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import is_system_account
from utils import remove_html
from utils import load_json
from utils import get_config_param
from utils import get_image_formats
from utils import acct_dir
from utils import get_supported_languages
from utils import local_actor_url
from utils import get_reply_interval_hours
from utils import get_account_timezone
from languages import get_actor_languages
from skills import get_skills
from theme import get_themes_list
from person import person_box_json
from person import get_actor_json
from person import get_person_avatar_url
from posts import get_person_box
from posts import is_moderator
from posts import parse_user_feed
from posts import is_create_inside_announce
from donate import get_donation_url
from donate import get_website
from xmpp import get_xmpp_address
from matrix import get_matrix_address
from ssb import get_ssb_address
from pgp import get_email_address
from pgp import get_pgp_fingerprint
from pgp import get_pgp_pub_key
from enigma import get_enigma_pub_key
from tox import get_tox_address
from briar import get_briar_address
from cwtch import get_cwtch_address
from filters import is_filtered
from follow import is_follower_of_person
from follow import get_follower_domains
from webapp_frontscreen import html_front_screen
from webapp_utils import html_keyboard_navigation
from webapp_utils import html_hide_from_screen_reader
from webapp_utils import scheduled_posts_exist
from webapp_utils import html_header_with_external_style
from webapp_utils import html_header_with_person_markup
from webapp_utils import html_footer
from webapp_utils import add_emoji_to_display_name
from webapp_utils import get_banner_file
from webapp_utils import html_post_separator
from webapp_utils import edit_check_box
from webapp_utils import edit_text_field
from webapp_utils import edit_text_area
from webapp_utils import begin_edit_section
from webapp_utils import end_edit_section
from blog import get_blog_address
from webapp_post import individual_post_as_html
from webapp_timeline import html_individual_share
from blocking import get_cw_list_variable
from blocking import is_blocked
from content import bold_reading_string

THEME_FORMATS = '.zip, .gz'


def _valid_profile_preview_post(post_json_object: {},
                                person_url: str) -> (bool, {}):
    """Returns true if the given post should appear on a person/group profile
    after searching for a handle
    """
    is_announced_feed_item = False
    if is_create_inside_announce(post_json_object):
        is_announced_feed_item = True
        post_json_object = post_json_object['object']
    if not post_json_object.get('type'):
        return False, None
    if post_json_object['type'] == 'Create':
        if not has_object_dict(post_json_object):
            return False, None
    if post_json_object['type'] != 'Create' and \
       post_json_object['type'] != 'Announce':
        if post_json_object['type'] != 'Note' and \
           post_json_object['type'] != 'Page':
            return False, None
        if not post_json_object.get('to'):
            return False, None
        if not post_json_object.get('id'):
            return False, None
        # wrap in create
        cc_list = []
        if post_json_object.get('cc'):
            cc_list = post_json_object['cc']
        new_post_json_object = {
            'object': post_json_object,
            'to': post_json_object['to'],
            'cc': cc_list,
            'id': post_json_object['id'],
            'actor': person_url,
            'type': 'Create'
        }
        post_json_object = new_post_json_object
    if not post_json_object.get('actor'):
        return False, None
    if not is_announced_feed_item:
        if has_object_dict(post_json_object):
            if post_json_object['actor'] != person_url and \
               post_json_object['object']['type'] != 'Page':
                return False, None
    return True, post_json_object


def html_profile_after_search(css_cache: {},
                              recent_posts_cache: {}, max_recent_posts: int,
                              translate: {},
                              base_dir: str, path: str, http_prefix: str,
                              nickname: str, domain: str, port: int,
                              profile_handle: str,
                              session, cached_webfingers: {}, person_cache: {},
                              debug: bool, project_version: str,
                              yt_replace_domain: str,
                              twitter_replacement_domain: str,
                              show_published_date_only: bool,
                              default_timeline: str,
                              peertube_instances: [],
                              allow_local_network_access: bool,
                              theme_name: str,
                              access_keys: {},
                              system_language: str,
                              max_like_count: int,
                              signing_priv_key_pem: str,
                              cw_lists: {}, lists_enabled: str,
                              timezone: str,
                              onion_domain: str, i2p_domain: str,
                              bold_reading: bool) -> str:
    """Show a profile page after a search for a fediverse address
    """
    http = False
    gnunet = False
    ipfs = False
    ipns = False
    if http_prefix == 'http':
        http = True
    elif http_prefix == 'gnunet':
        gnunet = True
    elif http_prefix == 'ipfs':
        ipfs = True
    elif http_prefix == 'ipns':
        ipns = True
    from_domain = domain
    if onion_domain:
        if '.onion/' in profile_handle or profile_handle.endswith('.onion'):
            from_domain = onion_domain
            http = True
    if i2p_domain:
        if '.i2p/' in profile_handle or profile_handle.endswith('.i2p'):
            from_domain = i2p_domain
            http = True
    profile_json, as_header = \
        get_actor_json(from_domain, profile_handle, http,
                       gnunet, ipfs, ipns, debug, False,
                       signing_priv_key_pem, session)
    if not profile_json:
        return None

    person_url = profile_json['id']
    search_domain, search_port = get_domain_from_actor(person_url)
    if not search_domain:
        return None
    search_nickname = get_nickname_from_actor(person_url)
    if not search_nickname:
        return None
    search_domain_full = get_full_domain(search_domain, search_port)

    profile_str = ''
    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    is_group = False
    if profile_json.get('type'):
        if profile_json['type'] == 'Group':
            is_group = True

    avatar_url = ''
    if profile_json.get('icon'):
        if profile_json['icon'].get('url'):
            avatar_url = profile_json['icon']['url']
    if not avatar_url:
        avatar_url = get_person_avatar_url(base_dir, person_url,
                                           person_cache, True)
    display_name = search_nickname
    if profile_json.get('name'):
        display_name = profile_json['name']

    locked_account = get_locked_account(profile_json)
    if locked_account:
        display_name += '🔒'
    moved_to = ''
    if profile_json.get('movedTo'):
        moved_to = profile_json['movedTo']
        if '"' in moved_to:
            moved_to = moved_to.split('"')[1]
        display_name += ' ⌂'

    follows_you = \
        is_follower_of_person(base_dir,
                              nickname, domain,
                              search_nickname,
                              search_domain_full)

    profile_description = ''
    if profile_json.get('summary'):
        profile_description = profile_json['summary']
    outbox_url = None
    if not profile_json.get('outbox'):
        if debug:
            pprint(profile_json)
            print('DEBUG: No outbox found')
        return None
    outbox_url = profile_json['outbox']

    # profileBackgroundImage = ''
    # if profile_json.get('image'):
    #     if profile_json['image'].get('url'):
    #         profileBackgroundImage = profile_json['image']['url']

    # url to return to
    back_url = path
    if not back_url.endswith('/inbox'):
        back_url += '/inbox'

    profile_description_short = profile_description
    if '\n' in profile_description:
        if len(profile_description.split('\n')) > 2:
            profile_description_short = ''
    else:
        if '<br>' in profile_description:
            if len(profile_description.split('<br>')) > 2:
                profile_description_short = ''
    # keep the profile description short
    if len(profile_description_short) > 2048:
        profile_description_short = ''
    # remove formatting from profile description used on title
    avatar_description = ''
    if profile_json.get('summary'):
        if isinstance(profile_json['summary'], str):
            avatar_description = \
                profile_json['summary'].replace('<br>', '\n')
            avatar_description = avatar_description.replace('<p>', '')
            avatar_description = avatar_description.replace('</p>', '')
            if '<' in avatar_description:
                avatar_description = remove_html(avatar_description)

    image_url = ''
    if profile_json.get('image'):
        if profile_json['image'].get('url'):
            image_url = profile_json['image']['url']

    also_known_as = None
    if profile_json.get('alsoKnownAs'):
        also_known_as = profile_json['alsoKnownAs']

    joined_date = None
    if profile_json.get('published'):
        if 'T' in profile_json['published']:
            joined_date = profile_json['published']

    profile_str = \
        _get_profile_header_after_search(base_dir,
                                         nickname, default_timeline,
                                         search_nickname,
                                         search_domain_full,
                                         translate,
                                         display_name, follows_you,
                                         profile_description_short,
                                         avatar_url, image_url,
                                         moved_to, profile_json['id'],
                                         also_known_as, access_keys,
                                         joined_date)

    domain_full = get_full_domain(domain, port)

    follow_is_permitted = True
    if not profile_json.get('followers'):
        # no followers collection specified within actor
        follow_is_permitted = False
    elif search_nickname == 'news' and search_domain_full == domain_full:
        # currently the news actor is not something you can follow
        follow_is_permitted = False
    elif search_nickname == nickname and search_domain_full == domain_full:
        # don't follow yourself!
        follow_is_permitted = False

    blocked = \
        is_blocked(base_dir, nickname, domain, search_nickname, search_domain)

    if follow_is_permitted:
        follow_str = 'Follow'
        if is_group:
            follow_str = 'Join'

        profile_str += \
            '<div class="container">\n' + \
            '  <form method="POST" action="' + \
            back_url + '/followconfirm">\n' + \
            '    <center>\n'
        profile_str += \
            '      <input type="hidden" name="actor" value="' + \
            person_url + '">\n' + \
            '      <button type="submit" class="button" name="submitYes" ' + \
            'accesskey="' + access_keys['followButton'] + '">' + \
            translate[follow_str] + '</button>\n'
        profile_str += \
            '      <button type="submit" class="button" name="submitView" ' + \
            'accesskey="' + access_keys['viewButton'] + '">' + \
            translate['View'] + '</button>\n'
        if blocked:
            profile_str += \
                '      <button type="submit" ' + \
                'class="button" name="submitUnblock" ' + \
                'accesskey="' + access_keys['unblockButton'] + '">' + \
                translate['Unblock'] + '</button>\n'
        profile_str += \
            '    </center>\n' + \
            '  </form>\n' + \
            '</div>\n'
    else:
        profile_str += \
            '<div class="container">\n' + \
            '  <form method="POST" action="' + \
            back_url + '/followconfirm">\n' + \
            '    <center>\n' + \
            '      <input type="hidden" name="actor" value="' + \
            person_url + '">\n' + \
            '      <button type="submit" class="button" name="submitView" ' + \
            'accesskey="' + access_keys['viewButton'] + '">' + \
            translate['View'] + '</button>\n' + \
            '    </center>\n' + \
            '  </form>\n' + \
            '</div>\n'

    user_feed = \
        parse_user_feed(signing_priv_key_pem,
                        session, outbox_url, as_header, project_version,
                        http_prefix, from_domain, debug)
    if user_feed:
        i = 0
        for item in user_feed:
            show_item, post_json_object = \
                _valid_profile_preview_post(item, person_url)
            if not show_item:
                continue

            profile_str += \
                individual_post_as_html(signing_priv_key_pem,
                                        True, recent_posts_cache,
                                        max_recent_posts,
                                        translate, None, base_dir,
                                        session, cached_webfingers,
                                        person_cache,
                                        nickname, domain, port,
                                        post_json_object, avatar_url,
                                        False, False,
                                        http_prefix, project_version, 'inbox',
                                        yt_replace_domain,
                                        twitter_replacement_domain,
                                        show_published_date_only,
                                        peertube_instances,
                                        allow_local_network_access,
                                        theme_name, system_language,
                                        max_like_count,
                                        False, False, False,
                                        False, False, False,
                                        cw_lists, lists_enabled,
                                        timezone, False,
                                        bold_reading)
            i += 1
            if i >= 8:
                break

    instance_title = get_config_param(base_dir, 'instanceTitle')
    return html_header_with_external_style(css_filename,
                                           instance_title, None) + \
        profile_str + html_footer()


def _get_profile_header(base_dir: str, http_prefix: str,
                        nickname: str, domain: str,
                        domain_full: str, translate: {},
                        default_timeline: str,
                        display_name: str,
                        avatar_description: str,
                        profile_description_short: str,
                        login_button: str, avatar_url: str,
                        theme: str, moved_to: str,
                        also_known_as: [],
                        pinned_content: str,
                        access_keys: {},
                        joined_date: str,
                        occupation_name: str) -> str:
    """The header of the profile screen, containing background
    image and avatar
    """
    html_str = \
        '\n\n    <figure class="profileHeader">\n' + \
        '      <a href="/users/' + \
        nickname + '/' + default_timeline + '" title="' + \
        translate['Switch to timeline view'] + '" tabindex="1" ' + \
        'accesskey="' + access_keys['menuTimeline'] + '">\n' + \
        '        <img class="profileBackground" ' + \
        'alt="" ' + \
        'src="/users/' + nickname + '/image_' + theme + '.png" /></a>\n' + \
        '      <figcaption>\n' + \
        '        <a href="/users/' + \
        nickname + '/' + default_timeline + '" title="' + \
        translate['Switch to timeline view'] + '">\n' + \
        '          <img loading="lazy" decoding="async" ' + \
        'src="' + avatar_url + '" alt=""  class="title"></a>\n'

    occupation_str = ''
    if occupation_name:
        occupation_str += \
            '        <b>' + occupation_name + '</b><br>\n'

    html_str += '        <h1>' + display_name + '</h1>\n' + occupation_str

    html_str += \
        '    <p><b>@' + nickname + '@' + domain_full + '</b><br>\n'
    if joined_date:
        html_str += \
            '    <p>' + translate['Joined'] + ' ' + \
            joined_date.split('T')[0] + '<br>\n'
    if moved_to:
        new_nickname = get_nickname_from_actor(moved_to)
        new_domain, new_port = get_domain_from_actor(moved_to)
        new_domain_full = get_full_domain(new_domain, new_port)
        if new_nickname and new_domain:
            html_str += \
                '    <p>' + translate['New account'] + ': ' + \
                '<a href="' + moved_to + '">@' + \
                new_nickname + '@' + new_domain_full + '</a><br>\n'
    elif also_known_as:
        other_accounts_html = \
            '    <p>' + translate['Other accounts'] + ': '

        actor = local_actor_url(http_prefix, nickname, domain_full)
        ctr = 0
        if isinstance(also_known_as, list):
            for alt_actor in also_known_as:
                if alt_actor == actor:
                    continue
                if ctr > 0:
                    other_accounts_html += ' '
                ctr += 1
                alt_domain, _ = get_domain_from_actor(alt_actor)
                other_accounts_html += \
                    '<a href="' + alt_actor + \
                    '" tabindex="1">' + alt_domain + '</a>'
        elif isinstance(also_known_as, str):
            if also_known_as != actor:
                ctr += 1
                alt_domain, _ = get_domain_from_actor(also_known_as)
                other_accounts_html += \
                    '<a href="' + also_known_as + '">' + alt_domain + '</a>'
        other_accounts_html += '</p>\n'
        if ctr > 0:
            html_str += other_accounts_html
    html_str += \
        '    <a href="/users/' + nickname + \
        '/qrcode.png" alt="' + translate['QR Code'] + '" title="' + \
        translate['QR Code'] + '" tabindex="1">' + \
        '<img class="qrcode" alt="' + translate['QR Code'] + \
        '" src="/icons/qrcode.png" /></a></p>\n' + \
        '        <p>' + profile_description_short + '</p>\n' + login_button
    if pinned_content:
        html_str += pinned_content.replace('<p>', '<p>📎', 1)

    # show vcard download link
    html_str += \
        '    <a href="/users/' + nickname + '.vcf" ' + \
        'download="contact_' + nickname + '@' + domain_full + \
        '.vcf" tabindex="1" class="imageAnchor">' + \
        '<img class="vcard" src="/icons/vcard.png" ' + \
        'title="vCard" alt="vCard" /></a>\n'

    html_str += \
        '      </figcaption>\n' + \
        '    </figure>\n\n'
    return html_str


def _get_profile_header_after_search(base_dir: str,
                                     nickname: str, default_timeline: str,
                                     search_nickname: str,
                                     search_domain_full: str,
                                     translate: {},
                                     display_name: str,
                                     follows_you: bool,
                                     profile_description_short: str,
                                     avatar_url: str, image_url: str,
                                     moved_to: str, actor: str,
                                     also_known_as: [],
                                     access_keys: {},
                                     joined_date: str) -> str:
    """The header of a searched for handle, containing background
    image and avatar
    """
    if not image_url:
        image_url = '/defaultprofilebackground'
    html_str = \
        '\n\n    <figure class="profileHeader">\n' + \
        '      <a href="/users/' + \
        nickname + '/' + default_timeline + '" title="' + \
        translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + access_keys['menuTimeline'] + '" tabindex="1">\n' + \
        '        <img class="profileBackground" ' + \
        'alt="" ' + \
        'src="' + image_url + '" /></a>\n' + \
        '      <figcaption>\n'
    if avatar_url:
        html_str += \
            '      <a href="/users/' + \
            nickname + '/' + default_timeline + '" title="' + \
            translate['Switch to timeline view'] + '">\n' + \
            '          <img loading="lazy" decoding="async" src="' + \
            avatar_url + '" ' + 'alt="" class="title"></a>\n'
    if not display_name:
        display_name = search_nickname
    html_str += \
        '        <h1>' + display_name + '</h1>\n' + \
        '    <p><b>@' + search_nickname + '@' + search_domain_full + \
        '</b><br>\n'
    if joined_date:
        html_str += '        <p>' + translate['Joined'] + ' ' + \
            joined_date.split('T')[0] + '</p>\n'
    if follows_you:
        html_str += '        <p><b>' + translate['Follows you'] + '</b></p>\n'
    if moved_to:
        new_nickname = get_nickname_from_actor(moved_to)
        new_domain, new_port = get_domain_from_actor(moved_to)
        new_domain_full = get_full_domain(new_domain, new_port)
        if new_nickname and new_domain:
            new_handle = new_nickname + '@' + new_domain_full
            html_str += '        <p>' + translate['New account'] + \
                ': <a href="' + moved_to + '">@' + new_handle + '</a></p>\n'
    elif also_known_as:
        other_accounts_html = \
            '        <p>' + translate['Other accounts'] + ': '

        ctr = 0
        if isinstance(also_known_as, list):
            for alt_actor in also_known_as:
                if alt_actor == actor:
                    continue
                if ctr > 0:
                    other_accounts_html += ' '
                ctr += 1
                alt_domain, _ = get_domain_from_actor(alt_actor)
                other_accounts_html += \
                    '<a href="' + alt_actor + \
                    '" tabindex="1">' + alt_domain + '</a>'
        elif isinstance(also_known_as, str):
            if also_known_as != actor:
                ctr += 1
                alt_domain, _ = get_domain_from_actor(also_known_as)
                other_accounts_html += \
                    '<a href="' + also_known_as + '">' + alt_domain + '</a>'

        other_accounts_html += '</p>\n'
        if ctr > 0:
            html_str += other_accounts_html

    html_str += \
        '        <p>' + profile_description_short + '</p>\n' + \
        '      </figcaption>\n' + \
        '    </figure>\n\n'
    return html_str


def html_profile(signing_priv_key_pem: str,
                 rss_icon_at_top: bool,
                 css_cache: {}, icons_as_buttons: bool,
                 default_timeline: str,
                 recent_posts_cache: {}, max_recent_posts: int,
                 translate: {}, project_version: str,
                 base_dir: str, http_prefix: str, authorized: bool,
                 profile_json: {}, selected: str,
                 session, cached_webfingers: {}, person_cache: {},
                 yt_replace_domain: str,
                 twitter_replacement_domain: str,
                 show_published_date_only: bool,
                 newswire: {}, theme: str, dormant_months: int,
                 peertube_instances: [],
                 allow_local_network_access: bool,
                 text_mode_banner: str,
                 debug: bool, access_keys: {}, city: str,
                 system_language: str, max_like_count: int,
                 shared_items_federated_domains: [],
                 extra_json: {}, page_number: int,
                 max_items_per_page: int,
                 cw_lists: {}, lists_enabled: str,
                 content_license_url: str,
                 timezone: str, bold_reading: bool) -> str:
    """Show the profile page as html
    """
    nickname = profile_json['preferredUsername']
    if not nickname:
        return ""
    if is_system_account(nickname):
        return html_front_screen(signing_priv_key_pem,
                                 rss_icon_at_top,
                                 css_cache, icons_as_buttons,
                                 default_timeline,
                                 recent_posts_cache, max_recent_posts,
                                 translate, project_version,
                                 base_dir, http_prefix, authorized,
                                 profile_json, selected,
                                 session, cached_webfingers, person_cache,
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 newswire, theme, extra_json,
                                 allow_local_network_access, access_keys,
                                 system_language, max_like_count,
                                 shared_items_federated_domains, None,
                                 page_number, max_items_per_page, cw_lists,
                                 lists_enabled)

    domain, port = get_domain_from_actor(profile_json['id'])
    if not domain:
        return ""
    display_name = \
        add_emoji_to_display_name(session, base_dir, http_prefix,
                                  nickname, domain,
                                  profile_json['name'], True)
    domain_full = get_full_domain(domain, port)
    profile_description = \
        add_emoji_to_display_name(session, base_dir, http_prefix,
                                  nickname, domain,
                                  profile_json['summary'], False)
    posts_button = 'button'
    following_button = 'button'
    followers_button = 'button'
    roles_button = 'button'
    skills_button = 'button'
#    shares_button = 'button'
#    wanted_button = 'button'
    if selected == 'posts':
        posts_button = 'buttonselected'
    elif selected == 'following':
        following_button = 'buttonselected'
    elif selected == 'followers':
        followers_button = 'buttonselected'
    elif selected == 'roles':
        roles_button = 'buttonselected'
    elif selected == 'skills':
        skills_button = 'buttonselected'
#    elif selected == 'shares':
#        shares_button = 'buttonselected'
#    elif selected == 'wanted':
#        wanted_button = 'buttonselected'
    login_button = ''

    follow_approvals_section = ''
    follow_approvals = False
    edit_profile_str = ''
    logout_str = ''
    actor = profile_json['id']
    users_path = '/users/' + actor.split('/users/')[1]

    donate_section = ''
    donate_url = get_donation_url(profile_json)
    website_url = get_website(profile_json, translate)
    blog_address = get_blog_address(profile_json)
    enigma_pub_key = get_enigma_pub_key(profile_json)
    pgp_pub_key = get_pgp_pub_key(profile_json)
    pgp_fingerprint = get_pgp_fingerprint(profile_json)
    email_address = get_email_address(profile_json)
    xmpp_address = get_xmpp_address(profile_json)
    matrix_address = get_matrix_address(profile_json)
    ssb_address = get_ssb_address(profile_json)
    tox_address = get_tox_address(profile_json)
    briar_address = get_briar_address(profile_json)
    cwtch_address = get_cwtch_address(profile_json)
    if donate_url or website_url or xmpp_address or matrix_address or \
       ssb_address or tox_address or briar_address or \
       cwtch_address or pgp_pub_key or enigma_pub_key or \
       pgp_fingerprint or email_address:
        donate_section = '<div class="container">\n'
        donate_section += '  <center>\n'
        if donate_url and not is_system_account(nickname):
            donate_section += \
                '    <p><a href="' + donate_url + '" tabindex="1">' + \
                '<button class="donateButton">' + translate['Donate'] + \
                '</button></a></p>\n'
        if website_url:
            donate_section += \
                '<p>' + translate['Website'] + ': <a href="' + \
                website_url + '" tabindex="1">' + website_url + '</a></p>\n'
        if email_address:
            donate_section += \
                '<p>' + translate['Email'] + ': <a href="mailto:' + \
                email_address + '" tabindex="1">' + \
                email_address + '</a></p>\n'
        if blog_address:
            donate_section += \
                '<p>Blog: <a href="' + \
                blog_address + '" tabindex="1">' + blog_address + '</a></p>\n'
        if xmpp_address:
            donate_section += \
                '<p>' + translate['XMPP'] + ': <a href="xmpp:' + \
                xmpp_address + '" tabindex="1">' + xmpp_address + '</a></p>\n'
        if matrix_address:
            donate_section += \
                '<p>' + translate['Matrix'] + ': ' + matrix_address + '</p>\n'
        if ssb_address:
            donate_section += \
                '<p>SSB: <label class="ssbaddr">' + \
                ssb_address + '</label></p>\n'
        if tox_address:
            donate_section += \
                '<p>Tox: <label class="toxaddr">' + \
                tox_address + '</label></p>\n'
        if briar_address:
            if briar_address.startswith('briar://'):
                donate_section += \
                    '<p><label class="toxaddr">' + \
                    briar_address + '</label></p>\n'
            else:
                donate_section += \
                    '<p>briar://<label class="toxaddr">' + \
                    briar_address + '</label></p>\n'
        if cwtch_address:
            donate_section += \
                '<p>Cwtch: <label class="toxaddr">' + \
                cwtch_address + '</label></p>\n'
        if enigma_pub_key:
            donate_section += \
                '<p>Enigma: <label class="toxaddr">' + \
                enigma_pub_key + '</label></p>\n'
        if pgp_fingerprint:
            donate_section += \
                '<p class="pgp">PGP: ' + \
                pgp_fingerprint.replace('\n', '<br>') + '</p>\n'
        if pgp_pub_key:
            donate_section += \
                '<p class="pgp">' + \
                pgp_pub_key.replace('\n', '<br>') + '</p>\n'
        donate_section += '  </center>\n'
        donate_section += '</div>\n'

    if authorized:
        edit_profile_str = \
            '<a class="imageAnchor" href="' + users_path + \
            '/editprofile" tabindex="1">' + \
            '<img loading="lazy" decoding="async" src="/icons' + \
            '/edit.png" title="' + translate['Edit'] + \
            '" alt="| ' + translate['Edit'] + '" class="timelineicon"/></a>\n'

        logout_str = \
            '<a class="imageAnchor" href="/logout" tabindex="1">' + \
            '<img loading="lazy" decoding="async" src="/icons' + \
            '/logout.png" title="' + translate['Logout'] + \
            '" alt="| ' + translate['Logout'] + \
            '" class="timelineicon"/></a>\n'

        # are there any follow requests?
        follow_requests_filename = \
            acct_dir(base_dir, nickname, domain) + '/followrequests.txt'
        if os.path.isfile(follow_requests_filename):
            with open(follow_requests_filename, 'r') as foll_file:
                for line in foll_file:
                    if len(line) > 0:
                        follow_approvals = True
                        followers_button = 'buttonhighlighted'
                        if selected == 'followers':
                            followers_button = 'buttonselectedhighlighted'
                        break
        if selected == 'followers':
            if follow_approvals:
                curr_follower_domains = \
                    get_follower_domains(base_dir, nickname, domain)
                with open(follow_requests_filename, 'r') as req_file:
                    for follower_handle in req_file:
                        if len(follower_handle) > 0:
                            follower_handle = follower_handle.replace('\n', '')
                            if '://' in follower_handle:
                                follower_actor = follower_handle
                            else:
                                nick = follower_handle.split('@')[0]
                                dom = follower_handle.split('@')[1]
                                follower_actor = \
                                    local_actor_url(http_prefix, nick, dom)

                            # is this a new domain?
                            # if so then append a new instance indicator
                            follower_domain, _ = \
                                get_domain_from_actor(follower_actor)
                            new_follower_domain = ''
                            if follower_domain not in curr_follower_domains:
                                new_follower_domain = ' ✨'

                            base_path = '/users/' + nickname
                            follow_approvals_section += \
                                '<div class="container">'
                            follow_approvals_section += \
                                '<a href="' + follower_actor + \
                                '" tabindex="2">'
                            follow_approvals_section += \
                                '<span class="followRequestHandle">' + \
                                follower_handle + \
                                new_follower_domain + '</span></a>'

                            # show Approve and Deny buttons
                            follow_approvals_section += \
                                '<a href="' + base_path + \
                                '/followapprove=' + follower_handle + \
                                '" tabindex="2">'
                            follow_approvals_section += \
                                '<button class="followApprove">' + \
                                translate['Approve'] + '</button></a><br><br>'
                            follow_approvals_section += \
                                '<a href="' + base_path + \
                                '/followdeny=' + follower_handle + \
                                '" tabindex="3">'
                            follow_approvals_section += \
                                '<button class="followDeny">' + \
                                translate['Deny'] + '</button></a>'
                            follow_approvals_section += '</div>'

    profile_description_short = profile_description
    if '\n' in profile_description:
        if len(profile_description.split('\n')) > 2:
            profile_description_short = ''
    else:
        if '<br>' in profile_description:
            if len(profile_description.split('<br>')) > 2:
                profile_description_short = ''
                profile_description = profile_description.replace('<br>', '\n')
    # keep the profile description short
    if len(profile_description_short) > 2048:
        profile_description_short = ''
    # remove formatting from profile description used on title
    avatar_description = ''
    if profile_json.get('summary'):
        avatar_description = profile_json['summary'].replace('<br>', '\n')
        avatar_description = avatar_description.replace('<p>', '')
        avatar_description = avatar_description.replace('</p>', '')

    moved_to = ''
    if profile_json.get('movedTo'):
        moved_to = profile_json['movedTo']
        if '"' in moved_to:
            moved_to = moved_to.split('"')[1]

    also_known_as = None
    if profile_json.get('alsoKnownAs'):
        also_known_as = profile_json['alsoKnownAs']

    joined_date = None
    if profile_json.get('published'):
        if 'T' in profile_json['published']:
            joined_date = profile_json['published']
    occupation_name = None
    if profile_json.get('hasOccupation'):
        occupation_name = get_occupation_name(profile_json)

    avatar_url = profile_json['icon']['url']
    # use alternate path for local avatars to avoid any caching issues
    if '://' + domain_full + '/system/accounts/avatars/' in avatar_url:
        avatar_url = \
            avatar_url.replace('://' + domain_full +
                               '/system/accounts/avatars/',
                               '://' + domain_full + '/users/')

    # get pinned post content
    account_dir = acct_dir(base_dir, nickname, domain)
    pinned_filename = account_dir + '/pinToProfile.txt'
    pinned_content = None
    if os.path.isfile(pinned_filename):
        with open(pinned_filename, 'r') as pin_file:
            pinned_content = pin_file.read()

    profile_header_str = \
        _get_profile_header(base_dir, http_prefix,
                            nickname, domain,
                            domain_full, translate,
                            default_timeline, display_name,
                            avatar_description,
                            profile_description_short,
                            login_button, avatar_url, theme,
                            moved_to, also_known_as,
                            pinned_content, access_keys,
                            joined_date, occupation_name)

    # keyboard navigation
    user_path_str = '/users/' + nickname
    deft = default_timeline
    is_group = False
    followers_str = translate['Followers']
    if is_group_account(base_dir, nickname, domain):
        is_group = True
        followers_str = translate['Members']
    menu_timeline = \
        html_hide_from_screen_reader('🏠') + ' ' + \
        translate['Switch to timeline view']
    menu_edit = \
        html_hide_from_screen_reader('✍') + ' ' + translate['Edit']
    menu_followers = \
        html_hide_from_screen_reader('👪') + ' ' + followers_str
    menu_logout = \
        html_hide_from_screen_reader('❎') + ' ' + translate['Logout']
    nav_links = {
        menu_timeline: user_path_str + '/' + deft,
        menu_edit: user_path_str + '/editprofile',
        menu_followers: user_path_str + '/followers#timeline',
        menu_logout: '/logout'
    }
    if not is_group:
        menu_following = \
            html_hide_from_screen_reader('👥') + ' ' + translate['Following']
        nav_links[menu_following] = user_path_str + '/following#timeline'
        menu_roles = \
            html_hide_from_screen_reader('🤚') + ' ' + translate['Roles']
        nav_links[menu_roles] = user_path_str + '/roles#timeline'
        menu_skills = \
            html_hide_from_screen_reader('🛠') + ' ' + translate['Skills']
        nav_links[menu_skills] = user_path_str + '/skills#timeline'
    if is_artist(base_dir, nickname):
        menu_theme_designer = \
            html_hide_from_screen_reader('🎨') + ' ' + \
            translate['Theme Designer']
        nav_links[menu_theme_designer] = user_path_str + '/themedesigner'
    nav_access_keys = {}
    for variable_name, key in access_keys.items():
        if not locals().get(variable_name):
            continue
        nav_access_keys[locals()[variable_name]] = key

    profile_str = html_keyboard_navigation(text_mode_banner,
                                           nav_links, nav_access_keys)

    profile_str += profile_header_str + donate_section
    profile_str += '<div class="container" id="buttonheader">\n'
    profile_str += '  <center>'
    profile_str += \
        '    <a href="' + users_path + '#buttonheader" tabindex="2">' + \
        '<button class="' + \
        posts_button + '"><span>' + translate['Posts'] + \
        ' </span></button></a>'
    if not is_group:
        profile_str += \
            '    <a href="' + users_path + \
            '/following#buttonheader" tabindex="2">' + \
            '<button class="' + following_button + '"><span>' + \
            translate['Following'] + ' </span></button></a>'
    profile_str += \
        '    <a href="' + users_path + \
        '/followers#buttonheader" tabindex="2">' + \
        '<button class="' + followers_button + \
        '"><span>' + followers_str + ' </span></button></a>'
    if not is_group:
        profile_str += \
            '    <a href="' + users_path + \
            '/roles#buttonheader" tabindex="2">' + \
            '<button class="' + roles_button + '"><span>' + \
            translate['Roles'] + \
            ' </span></button></a>'
        profile_str += \
            '    <a href="' + users_path + \
            '/skills#buttonheader" tabindex="2">' + \
            '<button class="' + skills_button + '"><span>' + \
            translate['Skills'] + ' </span></button></a>'
#    profile_str += \
#        '    <a href="' + users_path + \
#             '/shares#buttonheader" tabindex="2">' + \
#        '<button class="' + shares_button + '"><span>' + \
#        translate['Shares'] + ' </span></button></a>'
#    profile_str += \
#        '    <a href="' + users_path + \
#        '/wanted#buttonheader" tabindex="2">' + \
#        '<button class="' + wanted_button + '"><span>' + \
#        translate['Wanted'] + ' </span></button></a>'
    profile_str += logout_str + edit_profile_str
    profile_str += '  </center>'
    profile_str += '</div>'

    # start of #timeline
    profile_str += '<div id="timeline">\n'

    profile_str += follow_approvals_section

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    license_str = \
        '<a href="https://gitlab.com/bashrc2/epicyon" tabindex="2">' + \
        '<img loading="lazy" decoding="async" class="license" alt="' + \
        translate['Get the source code'] + '" title="' + \
        translate['Get the source code'] + '" src="/icons/agpl.png" /></a>'

    if selected == 'posts':
        profile_str += \
            _html_profile_posts(recent_posts_cache, max_recent_posts,
                                translate,
                                base_dir, http_prefix, authorized,
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
                                cw_lists, lists_enabled,
                                timezone, bold_reading) + license_str
    if not is_group:
        if selected == 'following':
            profile_str += \
                _html_profile_following(translate, base_dir, http_prefix,
                                        authorized, nickname,
                                        domain, port, session,
                                        cached_webfingers,
                                        person_cache, extra_json,
                                        project_version, ["unfollow"],
                                        selected,
                                        users_path, page_number,
                                        max_items_per_page,
                                        dormant_months, debug,
                                        signing_priv_key_pem)
    if selected == 'followers':
        profile_str += \
            _html_profile_following(translate, base_dir, http_prefix,
                                    authorized, nickname,
                                    domain, port, session,
                                    cached_webfingers,
                                    person_cache, extra_json,
                                    project_version, ["block"],
                                    selected, users_path, page_number,
                                    max_items_per_page, dormant_months, debug,
                                    signing_priv_key_pem)
    if not is_group:
        if selected == 'roles':
            profile_str += \
                _html_profile_roles(translate, nickname, domain_full,
                                    extra_json)
        elif selected == 'skills':
            profile_str += \
                _html_profile_skills(translate, nickname, domain_full,
                                     extra_json)
#       elif selected == 'shares':
#           profile_str += \
#                _html_profile_shares(actor, translate,
#                                   nickname, domain_full,
#                                   extra_json, 'shares') + license_str
#        elif selected == 'wanted':
#            profile_str += \
#                _html_profile_shares(actor, translate,
#                                   nickname, domain_full,
#                                   extra_json, 'wanted') + license_str
    # end of #timeline
    profile_str += '</div>'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    profile_str = \
        html_header_with_person_markup(css_filename, instance_title,
                                       profile_json, city,
                                       content_license_url) + \
        profile_str + html_footer()
    return profile_str


def _html_profile_posts(recent_posts_cache: {}, max_recent_posts: int,
                        translate: {},
                        base_dir: str, http_prefix: str,
                        authorized: bool,
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
                        signing_priv_key_pem: str,
                        cw_lists: {}, lists_enabled: str,
                        timezone: str, bold_reading: bool) -> str:
    """Shows posts on the profile screen
    These should only be public posts
    """
    separator_str = html_post_separator(base_dir, None)
    profile_str = ''
    max_items = 4
    ctr = 0
    curr_page = 1
    box_name = 'outbox'
    while ctr < max_items and curr_page < 4:
        outbox_feed_path_str = \
            '/users/' + nickname + '/' + box_name + '?page=' + \
            str(curr_page)
        outbox_feed = \
            person_box_json({}, session, base_dir, domain,
                            port,
                            outbox_feed_path_str,
                            http_prefix,
                            10, box_name,
                            authorized, 0, False, 0)
        if not outbox_feed:
            break
        if len(outbox_feed['orderedItems']) == 0:
            break
        for item in outbox_feed['orderedItems']:
            if item['type'] == 'Create':
                post_str = \
                    individual_post_as_html(signing_priv_key_pem,
                                            True, recent_posts_cache,
                                            max_recent_posts,
                                            translate, None,
                                            base_dir, session,
                                            cached_webfingers,
                                            person_cache,
                                            nickname, domain, port, item,
                                            None, True, False,
                                            http_prefix, project_version,
                                            'inbox',
                                            yt_replace_domain,
                                            twitter_replacement_domain,
                                            show_published_date_only,
                                            peertube_instances,
                                            allow_local_network_access,
                                            theme_name, system_language,
                                            max_like_count,
                                            False, False, False,
                                            True, False, False,
                                            cw_lists, lists_enabled,
                                            timezone, False,
                                            bold_reading)
                if post_str:
                    profile_str += post_str + separator_str
                    ctr += 1
                    if ctr >= max_items:
                        break
        curr_page += 1
    return profile_str


def _html_profile_following(translate: {}, base_dir: str, http_prefix: str,
                            authorized: bool,
                            nickname: str, domain: str, port: int,
                            session, cached_webfingers: {}, person_cache: {},
                            following_json: {}, project_version: str,
                            buttons: [],
                            feedName: str, actor: str,
                            page_number: int,
                            max_items_per_page: int,
                            dormant_months: int, debug: bool,
                            signing_priv_key_pem: str) -> str:
    """Shows following on the profile screen
    """
    profile_str = ''

    if authorized and page_number:
        if authorized and page_number > 1:
            # page up arrow
            profile_str += \
                '  <center>\n' + \
                '    <a href="' + actor + '/' + feedName + \
                '?page=' + str(page_number - 1) + '#buttonheader' + \
                '"><img loading="lazy" decoding="async" ' + \
                'class="pageicon" src="/' + \
                'icons/pageup.png" title="' + \
                translate['Page up'] + '" alt="' + \
                translate['Page up'] + '"></a>\n' + \
                '  </center>\n'

    for following_actor in following_json['orderedItems']:
        # is this a dormant followed account?
        dormant = False
        if authorized and feedName == 'following':
            dormant = \
                is_dormant(base_dir, nickname, domain, following_actor,
                           dormant_months)

        profile_str += \
            _individual_follow_as_html(signing_priv_key_pem,
                                       translate, base_dir, session,
                                       cached_webfingers, person_cache,
                                       domain, following_actor,
                                       authorized, nickname,
                                       http_prefix, project_version, dormant,
                                       debug, buttons)

    if authorized and max_items_per_page and page_number:
        if len(following_json['orderedItems']) >= max_items_per_page:
            # page down arrow
            profile_str += \
                '  <center>\n' + \
                '    <a href="' + actor + '/' + feedName + \
                '?page=' + str(page_number + 1) + '#buttonheader' + \
                '"><img loading="lazy" decoding="async" ' + \
                'class="pageicon" src="/' + \
                'icons/pagedown.png" title="' + \
                translate['Page down'] + '" alt="' + \
                translate['Page down'] + '"></a>\n' + \
                '  </center>\n'

    return profile_str


def _html_profile_roles(translate: {}, nickname: str, domain: str,
                        roles_list: []) -> str:
    """Shows roles on the profile screen
    """
    profile_str = ''
    profile_str += \
        '<div class="roles">\n<div class="roles-inner">\n'
    for role in roles_list:
        if translate.get(role):
            profile_str += '<h3>' + translate[role] + '</h3>\n'
        else:
            profile_str += '<h3>' + role + '</h3>\n'
    profile_str += '</div></div>\n'
    if len(profile_str) == 0:
        profile_str += \
            '<p>@' + nickname + '@' + domain + ' has no roles assigned</p>\n'
    else:
        profile_str = '<div>' + profile_str + '</div>\n'
    return profile_str


def _html_profile_skills(translate: {}, nickname: str, domain: str,
                         skillsJson: {}) -> str:
    """Shows skills on the profile screen
    """
    profile_str = ''
    for skill, level in skillsJson.items():
        profile_str += \
            '<div>' + skill + \
            '<br><div id="myProgress"><div id="myBar" style="width:' + \
            str(level) + '%"></div></div></div>\n<br>\n'
    if len(profile_str) > 0:
        profile_str = '<center><div class="skill-title">' + \
            profile_str + '</div></center>\n'
    return profile_str


def _html_profile_shares(actor: str, translate: {},
                         nickname: str, domain: str, shares_json: {},
                         shares_file_type: str) -> str:
    """Shows shares on the profile screen
    """
    profile_str = ''
    for item in shares_json['orderedItems']:
        profile_str += html_individual_share(domain, item['shareId'],
                                             actor, item, translate,
                                             False, False,
                                             shares_file_type)
    if len(profile_str) > 0:
        profile_str = '<div class="share-title">' + profile_str + '</div>\n'
    return profile_str


def _grayscale_enabled(base_dir: str) -> bool:
    """Is grayscale UI enabled?
    """
    return os.path.isfile(base_dir + '/accounts/.grayscale')


def _html_themes_dropdown(base_dir: str, translate: {}) -> str:
    """Returns the html for theme selection dropdown
    """
    # Themes section
    themes = get_themes_list(base_dir)
    themes_dropdown = '  <label class="labels">' + \
        translate['Theme'] + '</label><br>\n'
    grayscale = _grayscale_enabled(base_dir)
    themes_dropdown += \
        edit_check_box(translate['Grayscale'], 'grayscale', grayscale)
    dyslexic_font = get_config_param(base_dir, 'dyslexicFont')
    themes_dropdown += \
        edit_check_box(translate['Dyslexic font'], 'dyslexicFont',
                       dyslexic_font)
    themes_dropdown += '  <select id="themeDropdown" ' + \
        'name="themeDropdown" class="theme">'
    for theme_name in themes:
        translated_theme_name = theme_name
        if translate.get(theme_name):
            translated_theme_name = translate[theme_name]
        themes_dropdown += '    <option value="' + \
            theme_name.lower() + '">' + \
            translated_theme_name + '</option>'
    themes_dropdown += '  </select><br>'
    if os.path.isfile(base_dir + '/fonts/custom.woff') or \
       os.path.isfile(base_dir + '/fonts/custom.woff2') or \
       os.path.isfile(base_dir + '/fonts/custom.otf') or \
       os.path.isfile(base_dir + '/fonts/custom.ttf'):
        themes_dropdown += \
            edit_check_box(translate['Remove the custom font'],
                           'removeCustomFont', False)
    theme_name = get_config_param(base_dir, 'theme')
    themes_dropdown = \
        themes_dropdown.replace('<option value="' + theme_name + '">',
                                '<option value="' + theme_name +
                                '" selected>')
    return themes_dropdown


def _html_edit_profile_graphic_design(base_dir: str, translate: {}) -> str:
    """Graphic design section on Edit Profile screen
    """
    graphics_str = begin_edit_section(translate['Graphic Design'])

    low_bandwidth = get_config_param(base_dir, 'lowBandwidth')
    if not low_bandwidth:
        low_bandwidth = False
    graphics_str += _html_themes_dropdown(base_dir, translate)
    graphics_str += \
        '      <label class="labels">' + \
        translate['Import Theme'] + '</label>\n'
    graphics_str += '      <input type="file" id="import_theme" '
    graphics_str += 'name="submitImportTheme" '
    graphics_str += 'accept="' + THEME_FORMATS + '">\n'
    graphics_str += \
        '      <label class="labels">' + \
        translate['Export Theme'] + '</label><br>\n'
    graphics_str += \
        '      <button type="submit" class="button" ' + \
        'name="submitExportTheme">➤</button><br>\n'
    graphics_str += \
        edit_check_box(translate['Low Bandwidth'], 'lowBandwidth',
                       bool(low_bandwidth))

    graphics_str += end_edit_section()
    return graphics_str


def _html_edit_profile_twitter(base_dir: str, translate: {},
                               remove_twitter: str) -> str:
    """Edit twitter settings within profile
    """
    # Twitter section
    twitter_str = begin_edit_section(translate['Twitter'])
    twitter_str += \
        edit_check_box(translate['Remove Twitter posts'],
                       'removeTwitter', remove_twitter)
    twitter_replacement_domain = get_config_param(base_dir, "twitterdomain")
    if not twitter_replacement_domain:
        twitter_replacement_domain = ''
    twitter_str += \
        edit_text_field(translate['Twitter Replacement Domain'],
                        'twitterdomain', twitter_replacement_domain)
    twitter_str += end_edit_section()
    return twitter_str


def _html_edit_profile_instance(base_dir: str, translate: {},
                                peertube_instances: [],
                                media_instance_str: str,
                                blogs_instance_str: str,
                                news_instance_str: str) -> (str, str,
                                                            str, str):
    """Edit profile instance settings
    """
    image_formats = get_image_formats()

    # Instance details section
    instance_description = \
        get_config_param(base_dir, 'instanceDescription')
    custom_submit_text = \
        get_config_param(base_dir, 'customSubmitText')
    instance_description_short = \
        get_config_param(base_dir, 'instanceDescriptionShort')
    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    content_license_url = \
        get_config_param(base_dir, 'contentLicenseUrl')
    if not content_license_url:
        content_license_url = 'https://creativecommons.org/licenses/by/4.0'

    instance_str = begin_edit_section(translate['Instance Settings'])

    instance_str += \
        edit_text_field(translate['Instance Title'],
                        'instanceTitle', instance_title)
    instance_str += '<br>\n'
    instance_str += \
        edit_text_field(translate['Instance Short Description'],
                        'instanceDescriptionShort', instance_description_short)
    instance_str += '<br>\n'
    instance_str += \
        edit_text_area(translate['Instance Description'],
                       'instanceDescription', instance_description, 200,
                       '', True)
    instance_str += \
        edit_text_field(translate['Content License'],
                        'contentLicenseUrl', content_license_url)
    instance_str += '<br>\n'
    instance_str += \
        edit_text_field(translate['Custom post submit button text'],
                        'customSubmitText', custom_submit_text)
    instance_str += '<br>\n'
    instance_str += \
        '  <label class="labels">' + \
        translate['Instance Logo'] + '</label>' + \
        '  <input type="file" id="instanceLogo" name="instanceLogo"' + \
        '      accept="' + image_formats + '"><br>\n' + \
        '  <br><label class="labels">' + \
        translate['Security'] + '</label><br>\n'

    node_info_str = \
        translate['Show numbers of accounts within instance metadata']
    if get_config_param(base_dir, "showNodeInfoAccounts"):
        instance_str += \
            edit_check_box(node_info_str, 'showNodeInfoAccounts', True)
    else:
        instance_str += \
            edit_check_box(node_info_str, 'showNodeInfoAccounts', False)

    node_info_str = \
        translate['Show version number within instance metadata']
    if get_config_param(base_dir, "showNodeInfoVersion"):
        instance_str += \
            edit_check_box(node_info_str, 'showNodeInfoVersion', True)
    else:
        instance_str += \
            edit_check_box(node_info_str, 'showNodeInfoVersion', False)

    if get_config_param(base_dir, "verifyAllSignatures"):
        instance_str += \
            edit_check_box(translate['Verify all signatures'],
                           'verifyallsignatures', True)
    else:
        instance_str += \
            edit_check_box(translate['Verify all signatures'],
                           'verifyallsignatures', False)

    instance_str += translate['Enabling broch mode'] + '<br>\n'
    if get_config_param(base_dir, "brochMode"):
        instance_str += \
            edit_check_box(translate['Broch mode'], 'brochMode', True)
    else:
        instance_str += \
            edit_check_box(translate['Broch mode'], 'brochMode', False)
    # Instance type
    instance_str += \
        '  <br><label class="labels">' + \
        translate['Type of instance'] + '</label><br>\n'
    instance_str += \
        edit_check_box(translate['This is a media instance'],
                       'mediaInstance', media_instance_str)
    instance_str += \
        edit_check_box(translate['This is a blogging instance'],
                       'blogsInstance', blogs_instance_str)
    instance_str += \
        edit_check_box(translate['This is a news instance'],
                       'newsInstance', news_instance_str)

    instance_str += end_edit_section()

    # Role assignments section
    moderators = ''
    moderators_file = base_dir + '/accounts/moderators.txt'
    if os.path.isfile(moderators_file):
        with open(moderators_file, 'r') as mod_file:
            moderators = mod_file.read()
    # site moderators
    role_assign_str = \
        begin_edit_section(translate['Role Assignment']) + \
        '  <b><label class="labels">' + \
        translate['Moderators'] + '</label></b><br>\n' + \
        '  ' + \
        translate['A list of moderator nicknames. One per line.'] + \
        '  <textarea id="message" name="moderators" placeholder="' + \
        translate['List of moderator nicknames'] + \
        '..." style="height:200px" spellcheck="false">' + \
        moderators + '</textarea>'

    # site editors
    editors = ''
    editors_file = base_dir + '/accounts/editors.txt'
    if os.path.isfile(editors_file):
        with open(editors_file, 'r') as edit_file:
            editors = edit_file.read()
    role_assign_str += \
        '  <b><label class="labels">' + \
        translate['Site Editors'] + '</label></b><br>\n' + \
        '  ' + \
        translate['A list of editor nicknames. One per line.'] + \
        '  <textarea id="message" name="editors" placeholder="" ' + \
        'style="height:200px" spellcheck="false">' + \
        editors + '</textarea>'

    # counselors
    counselors = ''
    counselors_file = base_dir + '/accounts/counselors.txt'
    if os.path.isfile(counselors_file):
        with open(counselors_file, 'r') as co_file:
            counselors = co_file.read()
    role_assign_str += \
        edit_text_area(translate['Counselors'], 'counselors', counselors,
                       200, '', False)

    # artists
    artists = ''
    artists_file = base_dir + '/accounts/artists.txt'
    if os.path.isfile(artists_file):
        with open(artists_file, 'r') as art_file:
            artists = art_file.read()
    role_assign_str += \
        edit_text_area(translate['Artists'], 'artists', artists,
                       200, '', False)
    role_assign_str += end_edit_section()

    # Video section
    peertube_str = begin_edit_section(translate['Video Settings'])
    peertube_instances_str = ''
    for url in peertube_instances:
        peertube_instances_str += url + '\n'
    peertube_str += \
        edit_text_area(translate['Peertube Instances'], 'ptInstances',
                       peertube_instances_str, 200, '', False)
    peertube_str += \
        '      <br>\n'
    yt_replace_domain = get_config_param(base_dir, "youtubedomain")
    if not yt_replace_domain:
        yt_replace_domain = ''
    peertube_str += \
        edit_text_field(translate['YouTube Replacement Domain'],
                        'ytdomain', yt_replace_domain)
    peertube_str += end_edit_section()

    libretranslate_url = get_config_param(base_dir, 'libretranslateUrl')
    libretranslate_api_key = get_config_param(base_dir, 'libretranslateApiKey')
    libretranslate_str = \
        _html_edit_profile_libre_translate(translate,
                                           libretranslate_url,
                                           libretranslate_api_key)

    return instance_str, role_assign_str, peertube_str, libretranslate_str


def _html_edit_profile_danger_zone(translate: {}) -> str:
    """danger zone section of Edit Profile screen
    """
    edit_profile_form = begin_edit_section(translate['Danger Zone'])

    edit_profile_form += \
        '      <b><label class="labels">' + \
        translate['Danger Zone'] + '</label></b><br>\n'

    edit_profile_form += \
        edit_check_box(translate['Deactivate this account'],
                       'deactivateThisAccount', False)

    edit_profile_form += end_edit_section()
    return edit_profile_form


def _html_system_monitor(nickname: str, translate: {}) -> str:
    """Links to performance graphs
    """
    system_monitor_str = begin_edit_section(translate['System Monitor'])
    system_monitor_str += '<p><a href="/users/' + nickname + \
        '/performance?graph=get">📊 GET</a></p>'
    system_monitor_str += '<p><a href="/users/' + nickname + \
        '/performance?graph=inbox">📊 INBOX</a></p>'
    system_monitor_str += '<p><a href="/users/' + nickname + \
        '/performance?graph=post">📊 POST</a></p>'
    system_monitor_str += end_edit_section()
    return system_monitor_str


def _html_edit_profile_skills(base_dir: str, nickname: str, domain: str,
                              translate: {}) -> str:
    """skills section of Edit Profile screen
    """
    skills = get_skills(base_dir, nickname, domain)
    skills_str = ''
    skill_ctr = 1
    if skills:
        for skill_desc, skill_value in skills.items():
            if is_filtered(base_dir, nickname, domain, skill_desc):
                continue
            skills_str += \
                '<p><input type="text" placeholder="' + translate['Skill'] + \
                ' ' + str(skill_ctr) + '" name="skillName' + str(skill_ctr) + \
                '" value="' + skill_desc + '" style="width:40%">' + \
                '<input type="range" min="1" max="100" ' + \
                'class="slider" name="skillValue' + \
                str(skill_ctr) + '" value="' + str(skill_value) + '"></p>'
            skill_ctr += 1

    skills_str += \
        '<p><input type="text" placeholder="Skill ' + str(skill_ctr) + \
        '" name="skillName' + str(skill_ctr) + \
        '" value="" style="width:40%">' + \
        '<input type="range" min="1" max="100" ' + \
        'class="slider" name="skillValue' + \
        str(skill_ctr) + '" value="50"></p>' + end_edit_section()

    idx = 'If you want to participate within organizations then you ' + \
        'can indicate some skills that you have and approximate ' + \
        'proficiency levels. This helps organizers to construct ' + \
        'teams with an appropriate combination of skills.'
    edit_profile_form = \
        begin_edit_section(translate['Skills']) + \
        '      <b><label class="labels">' + \
        translate['Skills'] + '</label></b><br>\n' + \
        '      <label class="labels">' + \
        translate[idx] + '</label>\n' + skills_str
    return edit_profile_form


def _html_edit_profile_git_projects(base_dir: str, nickname: str, domain: str,
                                    translate: {}) -> str:
    """git projects section of edit profile screen
    """
    git_projects_str = ''
    git_projects_filename = \
        acct_dir(base_dir, nickname, domain) + '/gitprojects.txt'
    if os.path.isfile(git_projects_filename):
        with open(git_projects_filename, 'r') as git_file:
            git_projects_str = git_file.read()

    edit_profile_form = begin_edit_section(translate['Git Projects'])
    idx = 'List of project names that you wish to receive git patches for'
    edit_profile_form += \
        edit_text_area(translate[idx], 'gitProjects', git_projects_str,
                       100, '', False)
    edit_profile_form += end_edit_section()
    return edit_profile_form


def _html_edit_profile_shared_items(base_dir: str, nickname: str, domain: str,
                                    translate: {}) -> str:
    """shared items section of edit profile screen
    """
    shared_items_str = ''
    shared_items_federated_domains_str = \
        get_config_param(base_dir, 'sharedItemsFederatedDomains')
    if shared_items_federated_domains_str:
        shared_items_federated_domains_list = \
            shared_items_federated_domains_str.split(',')
        for shared_federated_domain in shared_items_federated_domains_list:
            shared_items_str += shared_federated_domain.strip() + '\n'

    edit_profile_form = begin_edit_section(translate['Shares'])
    idx = 'List of domains which can access the shared items catalog'
    edit_profile_form += \
        edit_text_area(translate[idx], 'shareDomainList',
                       shared_items_str, 200, '', False)
    edit_profile_form += end_edit_section()
    return edit_profile_form


def _html_edit_profile_filtering(base_dir: str, nickname: str, domain: str,
                                 user_agents_blocked: str,
                                 crawlers_allowed: str,
                                 translate: {}, reply_interval_hours: int,
                                 cw_lists: {}, lists_enabled: str) -> str:
    """Filtering and blocking section of edit profile screen
    """
    filter_str = ''
    filter_filename = \
        acct_dir(base_dir, nickname, domain) + '/filters.txt'
    if os.path.isfile(filter_filename):
        with open(filter_filename, 'r') as filterfile:
            filter_str = filterfile.read()

    filter_bio_str = ''
    filter_bio_filename = \
        acct_dir(base_dir, nickname, domain) + '/filters_bio.txt'
    if os.path.isfile(filter_bio_filename):
        with open(filter_bio_filename, 'r') as filterfile:
            filter_bio_str = filterfile.read()

    switch_str = ''
    switch_filename = \
        acct_dir(base_dir, nickname, domain) + '/replacewords.txt'
    if os.path.isfile(switch_filename):
        with open(switch_filename, 'r') as switchfile:
            switch_str = switchfile.read()

    auto_tags = ''
    auto_tags_filename = \
        acct_dir(base_dir, nickname, domain) + '/autotags.txt'
    if os.path.isfile(auto_tags_filename):
        with open(auto_tags_filename, 'r') as auto_file:
            auto_tags = auto_file.read()

    auto_cw = ''
    auto_cw_filename = \
        acct_dir(base_dir, nickname, domain) + '/autocw.txt'
    if os.path.isfile(auto_cw_filename):
        with open(auto_cw_filename, 'r') as cw_file:
            auto_cw = cw_file.read()

    blocked_str = ''
    blocked_filename = \
        acct_dir(base_dir, nickname, domain) + '/blocking.txt'
    if os.path.isfile(blocked_filename):
        with open(blocked_filename, 'r') as blockedfile:
            blocked_str = blockedfile.read()

    dm_allowed_instances_str = ''
    dm_allowed_instances_filename = \
        acct_dir(base_dir, nickname, domain) + '/dmAllowedInstances.txt'
    if os.path.isfile(dm_allowed_instances_filename):
        with open(dm_allowed_instances_filename, 'r') as dm_file:
            dm_allowed_instances_str = dm_file.read()

    allowed_instances_str = ''
    allowed_instances_filename = \
        acct_dir(base_dir, nickname, domain) + '/allowedinstances.txt'
    if os.path.isfile(allowed_instances_filename):
        with open(allowed_instances_filename, 'r') as allow_file:
            allowed_instances_str = allow_file.read()

    edit_profile_form = begin_edit_section(translate['Filtering and Blocking'])

    idx = 'Hours after posting during which replies are allowed'
    edit_profile_form += \
        '  <label class="labels">' + \
        translate[idx] + \
        ':</label> <input type="number" name="replyhours" ' + \
        'min="0" max="999999999999" step="1" ' + \
        'value="' + str(reply_interval_hours) + '"><br>\n'

    edit_profile_form += \
        '<label class="labels">' + \
        translate['City for spoofed GPS image metadata'] + \
        '</label><br>\n'

    city = ''
    city_filename = acct_dir(base_dir, nickname, domain) + '/city.txt'
    if os.path.isfile(city_filename):
        with open(city_filename, 'r') as city_file:
            city = city_file.read().replace('\n', '')
    locations_filename = base_dir + '/custom_locations.txt'
    if not os.path.isfile(locations_filename):
        locations_filename = base_dir + '/locations.txt'
    cities = []
    with open(locations_filename, 'r') as loc_file:
        cities = loc_file.readlines()
        cities.sort()
    edit_profile_form += '  <select id="cityDropdown" ' + \
        'name="cityDropdown" class="theme">\n'
    city = city.lower()
    for city_name in cities:
        if ':' not in city_name:
            continue
        city_selected = ''
        city_name = city_name.split(':')[0]
        city_name = city_name.lower()
        if city:
            if city in city_name:
                city_selected = ' selected'
        edit_profile_form += \
            '    <option value="' + city_name + \
            '"' + city_selected.title() + '>' + \
            city_name + '</option>\n'
    edit_profile_form += '  </select><br>\n'

    edit_profile_form += \
        '      <b><label class="labels">' + \
        translate['Filtered words'] + '</label></b>\n' + \
        '      <br><label class="labels">' + \
        translate['One per line'] + '</label>\n' + \
        '      <textarea id="message" ' + \
        'name="filteredWords" style="height:200px" spellcheck="false">' + \
        filter_str + '</textarea>\n' + \
        '      <br><b><label class="labels">' + \
        translate['Filtered words within bio'] + '</label></b>\n' + \
        '      <br><label class="labels">' + \
        translate['One per line'] + '</label>\n' + \
        '      <textarea id="message" ' + \
        'name="filteredWordsBio" style="height:200px" spellcheck="false">' + \
        filter_bio_str + '</textarea>\n' + \
        '      <br><b><label class="labels">' + \
        translate['Word Replacements'] + '</label></b>\n' + \
        '      <br><label class="labels">A -> B</label>\n' + \
        '      <textarea id="message" name="switchwords" ' + \
        'style="height:200px" spellcheck="false">' + \
        switch_str + '</textarea>\n' + \
        '      <br><b><label class="labels">' + \
        translate['Autogenerated Hashtags'] + '</label></b>\n' + \
        '      <br><label class="labels">A -> #B</label>\n' + \
        '      <textarea id="message" name="autoTags" ' + \
        'style="height:200px" spellcheck="false">' + \
        auto_tags + '</textarea>\n' + \
        '      <br><b><label class="labels">' + \
        translate['Autogenerated Content Warnings'] + '</label></b>\n' + \
        '      <br><label class="labels">A -> B</label>\n' + \
        '      <textarea id="message" name="autoCW" ' + \
        'style="height:200px" spellcheck="true">' + auto_cw + '</textarea>\n'

    idx = 'Blocked accounts, one per line, in the form ' + \
        'nickname@domain or *@blockeddomain'
    edit_profile_form += \
        edit_text_area(translate['Blocked accounts'], 'blocked', blocked_str,
                       200, '', False)

    idx = 'Direct messages are always allowed from these instances.'
    edit_profile_form += \
        edit_text_area(translate['Direct Message permitted instances'],
                       'dmAllowedInstances', dm_allowed_instances_str,
                       200, '', False)

    idx = 'Federate only with a defined set of instances. ' + \
        'One domain name per line.'
    edit_profile_form += \
        '      <br><b><label class="labels">' + \
        translate['Federation list'] + '</label></b>\n' + \
        '      <br><label class="labels">' + \
        translate[idx] + '</label>\n' + \
        '      <textarea id="message" name="allowedInstances" ' + \
        'style="height:200px" spellcheck="false">' + \
        allowed_instances_str + '</textarea>\n'

    if is_moderator(base_dir, nickname):
        edit_profile_form += \
            '<a href="/users/' + nickname + '/crawlers">' + \
            translate['Known Web Crawlers'] + '</a><br>\n'

        user_agents_blocked_str = ''
        for uagent in user_agents_blocked:
            if user_agents_blocked_str:
                user_agents_blocked_str += '\n'
            user_agents_blocked_str += uagent
        edit_profile_form += \
            edit_text_area(translate['Blocked User Agents'],
                           'userAgentsBlockedStr', user_agents_blocked_str,
                           200, '', False)

        edit_profile_form += \
            '<a href="/users/' + nickname + '/bots.txt">' + \
            translate['Known Search Bots'] + '</a><br>\n'

        crawlers_allowed_str = ''
        for uagent in crawlers_allowed:
            if crawlers_allowed_str:
                crawlers_allowed_str += '\n'
            crawlers_allowed_str += uagent
        edit_profile_form += \
            edit_text_area(translate['Web Bots Allowed'],
                           'crawlersAllowedStr', crawlers_allowed_str,
                           200, '', False)

        cw_lists_str = ''
        for name, _ in cw_lists.items():
            variablename = get_cw_list_variable(name)
            list_is_enabled = False
            if lists_enabled:
                if name in lists_enabled:
                    list_is_enabled = True
            if translate.get(name):
                name = translate[name]
            cw_lists_str += \
                edit_check_box(name, variablename, list_is_enabled)
        if cw_lists_str:
            idx = 'Add content warnings for the following sites'
            edit_profile_form += \
                '<label class="labels">' + translate[idx] + ':</label>\n' + \
                '<br>' + cw_lists_str

    edit_profile_form += end_edit_section()
    return edit_profile_form


def _html_edit_profile_change_password(translate: {}) -> str:
    """Change password section of edit profile screen
    """
    edit_profile_form = \
        begin_edit_section(translate['Change Password']) + \
        '<label class="labels">' + translate['Change Password'] + \
        '</label><br>\n' + \
        '      <input type="password" name="password" ' + \
        'value=""><br>\n' + \
        '<label class="labels">' + translate['Confirm Password'] + \
        '</label><br>\n' + \
        '      <input type="password" name="passwordconfirm" value="">\n' + \
        end_edit_section()
    return edit_profile_form


def _html_edit_profile_libre_translate(translate: {},
                                       libretranslate_url: str,
                                       libretranslate_api_key: str) -> str:
    """Change automatic translation settings
    """
    edit_profile_form = begin_edit_section('LibreTranslate')

    edit_profile_form += \
        edit_text_field('URL', 'libretranslateUrl', libretranslate_url,
                        'http://0.0.0.0:5000')
    edit_profile_form += \
        edit_text_field('API Key', 'libretranslateApiKey',
                        libretranslate_api_key)

    edit_profile_form += end_edit_section()
    return edit_profile_form


def _html_edit_profile_background(news_instance: bool, translate: {}) -> str:
    """Background images section of edit profile screen
    """
    idx = 'The files attached below should be no larger than ' + \
        '10MB in total uploaded at once.'
    edit_profile_form = \
        begin_edit_section(translate['Background Images']) + \
        '      <label class="labels">' + translate[idx] + '</label><br><br>\n'

    if not news_instance:
        image_formats = get_image_formats()
        edit_profile_form += \
            '      <label class="labels">' + \
            translate['Background image'] + '</label>\n' + \
            '      <input type="file" id="image" name="image"' + \
            '            accept="' + image_formats + '">\n' + \
            '      <br><label class="labels">' + \
            translate['Timeline banner image'] + '</label>\n' + \
            '      <input type="file" id="banner" name="banner"' + \
            '            accept="' + image_formats + '">\n' + \
            '      <br><label class="labels">' + \
            translate['Search banner image'] + '</label>\n' + \
            '      <input type="file" id="search_banner" ' + \
            'name="search_banner"' + \
            '            accept="' + image_formats + '">\n' + \
            '      <br><label class="labels">' + \
            translate['Left column image'] + '</label>\n' + \
            '      <input type="file" id="left_col_image" ' + \
            'name="left_col_image"' + \
            '            accept="' + image_formats + '">\n' + \
            '      <br><label class="labels">' + \
            translate['Right column image'] + '</label>\n' + \
            '      <input type="file" id="right_col_image" ' + \
            'name="right_col_image"' + \
            '            accept="' + image_formats + '">\n'

    edit_profile_form += end_edit_section()
    return edit_profile_form


def _html_edit_profile_contact_info(nickname: str,
                                    email_address: str,
                                    xmpp_address: str,
                                    matrix_address: str,
                                    ssb_address: str,
                                    tox_address: str,
                                    briar_address: str,
                                    cwtch_address: str,
                                    translate: {}) -> str:
    """Contact Information section of edit profile screen
    """
    edit_profile_form = begin_edit_section(translate['Contact Details'])

    edit_profile_form += edit_text_field(translate['Email'],
                                         'email', email_address)
    edit_profile_form += edit_text_field(translate['XMPP'],
                                         'xmppAddress', xmpp_address)
    edit_profile_form += edit_text_field(translate['Matrix'],
                                         'matrixAddress', matrix_address)
    edit_profile_form += edit_text_field('SSB', 'ssbAddress', ssb_address)
    edit_profile_form += edit_text_field('Tox', 'toxAddress', tox_address)
    edit_profile_form += edit_text_field('Briar', 'briarAddress',
                                         briar_address)
    edit_profile_form += edit_text_field('Cwtch', 'cwtchAddress',
                                         cwtch_address)
    edit_profile_form += \
        '<a href="/users/' + nickname + \
        '/followingaccounts"><label class="labels">' + \
        translate['Following'] + '</label></a><br>\n'

    edit_profile_form += end_edit_section()
    return edit_profile_form


def _html_edit_profile_encryption_keys(pgp_fingerprint: str,
                                       pgp_pub_key: str,
                                       enigma_pub_key: str,
                                       translate: {}) -> str:
    """Contact Information section of edit profile screen
    """
    edit_profile_form = begin_edit_section(translate['Encryption Keys'])

    enigma_url = 'https://github.com/enigma-reloaded/enigma-reloaded'
    edit_profile_form += \
        edit_text_field('<a href="' + enigma_url + '">Enigma</a>',
                        'enigmapubkey', enigma_pub_key)
    edit_profile_form += edit_text_field(translate['PGP Fingerprint'],
                                         'openpgp', pgp_fingerprint)
    edit_profile_form += \
        edit_text_area(translate['PGP'], 'pgp', pgp_pub_key, 600,
                       '-----BEGIN PGP PUBLIC KEY BLOCK-----', False)

    edit_profile_form += end_edit_section()
    return edit_profile_form


def _html_edit_profile_options(is_admin: bool,
                               manually_approves_followers: str,
                               is_bot: str, is_group: str,
                               follow_dms: str, remove_twitter: str,
                               notify_likes: str, notify_reactions: str,
                               hide_like_button: str,
                               hide_reaction_button: str,
                               translate: {}, bold_reading: bool) -> str:
    """option checkboxes section of edit profile screen
    """
    edit_profile_form = '    <div class="container">\n'
    edit_profile_form += \
        edit_check_box(translate['Approve follower requests'],
                       'approveFollowers', manually_approves_followers)
    edit_profile_form += \
        edit_check_box(translate['This is a bot account'],
                       'isBot', is_bot)
    if is_admin:
        edit_profile_form += \
            edit_check_box(translate['This is a group account'],
                           'isGroup', is_group)
    edit_profile_form += \
        edit_check_box(translate['Only people I follow can send me DMs'],
                       'followDMs', follow_dms)
    edit_profile_form += \
        edit_check_box(translate['Remove Twitter posts'],
                       'removeTwitter', remove_twitter)
    edit_profile_form += \
        edit_check_box(translate['Notify when posts are liked'],
                       'notifyLikes', notify_likes)
    edit_profile_form += \
        edit_check_box(translate['Notify on emoji reactions'],
                       'notifyReactions', notify_reactions)
    edit_profile_form += \
        edit_check_box(translate["Don't show the Like button"],
                       'hideLikeButton', hide_like_button)
    edit_profile_form += \
        edit_check_box(translate["Don't show the Reaction button"],
                       'hideReactionButton', hide_reaction_button)
    bold_str = bold_reading_string(translate['Bold reading'])
    edit_profile_form += \
        edit_check_box(bold_str, 'boldReading', bold_reading)
    edit_profile_form += '    </div>\n'
    return edit_profile_form


def _get_supported_languagesSorted(base_dir: str) -> str:
    """Returns a list of supported languages
    """
    lang_list = get_supported_languages(base_dir)
    if not lang_list:
        return ''
    lang_list.sort()
    languages_str = ''
    for lang in lang_list:
        if languages_str:
            languages_str += ' / ' + lang
        else:
            languages_str = lang
    return languages_str


def _html_edit_profile_main(base_dir: str, display_nickname: str, bio_str: str,
                            moved_to: str, donate_url: str, website_url: str,
                            blog_address: str, actor_json: {},
                            translate: {},
                            nickname: str, domain: str) -> str:
    """main info on edit profile screen
    """
    image_formats = get_image_formats()

    edit_profile_form = '    <div class="container">\n'

    edit_profile_form += \
        edit_text_field(translate['Nickname'], 'displayNickname',
                        display_nickname)

    edit_profile_form += \
        edit_text_area(translate['Your bio'], 'bio', bio_str, 200, '', True)

    edit_profile_form += \
        '      <label class="labels">' + translate['Avatar image'] + \
        '</label>\n' + \
        '      <input type="file" id="avatar" name="avatar"' + \
        '            accept="' + image_formats + '">\n'

    occupation_name = ''
    if actor_json.get('hasOccupation'):
        occupation_name = get_occupation_name(actor_json)

    edit_profile_form += \
        edit_text_field(translate['Occupation'], 'occupationName',
                        occupation_name)

    also_known_as_str = ''
    if actor_json.get('alsoKnownAs'):
        also_known_as = actor_json['alsoKnownAs']
        ctr = 0
        for alt_actor in also_known_as:
            if ctr > 0:
                also_known_as_str += ', '
            ctr += 1
            also_known_as_str += alt_actor

    edit_profile_form += \
        edit_text_field(translate['Other accounts'], 'alsoKnownAs',
                        also_known_as_str, 'https://...')

    edit_profile_form += \
        edit_text_field(translate['Moved to new account address'], 'movedTo',
                        moved_to, 'https://...')

    edit_profile_form += \
        edit_text_field(translate['Donations link'], 'donateUrl',
                        donate_url, 'https://...')

    edit_profile_form += \
        edit_text_field(translate['Website'], 'websiteUrl',
                        website_url, 'https://...')

    edit_profile_form += \
        edit_text_field('Blog', 'blogAddress', blog_address, 'https://...')

    languages_list_str = _get_supported_languagesSorted(base_dir)
    show_languages = get_actor_languages(actor_json)
    edit_profile_form += \
        edit_text_field(translate['Languages'], 'showLanguages',
                        show_languages, languages_list_str)

    timezone = get_account_timezone(base_dir, nickname, domain)
    edit_profile_form += \
        edit_text_field(translate['Time Zone'], 'timeZone',
                        timezone, 'Europe/London')

    edit_profile_form += '    </div>\n'
    return edit_profile_form


def _html_edit_profile_top_banner(base_dir: str,
                                  nickname: str, domain: str, domain_full: str,
                                  default_timeline: str, banner_file: str,
                                  path: str, access_keys: {},
                                  translate: {}) -> str:
    """top banner on edit profile screen
    """
    edit_profile_form = \
        '<a href="/users/' + nickname + '/' + default_timeline + '">' + \
        '<img loading="lazy" decoding="async" ' + \
        'class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + banner_file + '" alt="" /></a>\n'

    edit_profile_form += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/profiledata">\n'
    edit_profile_form += '  <div class="vertical-center">\n'
    edit_profile_form += \
        '    <h1>' + translate['Profile for'] + \
        ' ' + nickname + '@' + domain_full + '</h1>'
    edit_profile_form += '    <div class="container">\n'
    edit_profile_form += \
        '      <center>\n' + \
        '        <input type="submit" name="submitProfile" ' + \
        'accesskey="' + access_keys['submitButton'] + '" ' + \
        'value="' + translate['Publish'] + '">\n' + \
        '      </center>\n'
    edit_profile_form += '    </div>\n'

    if scheduled_posts_exist(base_dir, nickname, domain):
        edit_profile_form += '    <div class="container">\n'
        edit_profile_form += \
            edit_check_box(translate['Remove scheduled posts'],
                           'removeScheduledPosts', False)
        edit_profile_form += '    </div>\n'
    return edit_profile_form


def html_edit_profile(server, css_cache: {}, translate: {},
                      base_dir: str, path: str,
                      domain: str, port: int, http_prefix: str,
                      default_timeline: str, theme: str,
                      peertube_instances: [],
                      text_mode_banner: str, city: str,
                      user_agents_blocked: [],
                      crawlers_allowed: [],
                      access_keys: {},
                      default_reply_interval_hrs: int,
                      cw_lists: {}, lists_enabled: str) -> str:
    """Shows the edit profile screen
    """
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '').replace('/wanted', '')
    nickname = get_nickname_from_actor(path)
    if not nickname:
        return ''
    domain_full = get_full_domain(domain, port)

    bold_reading = False
    if server.bold_reading.get(nickname):
        bold_reading = True

    actor_filename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actor_filename):
        return ''

    # filename of the banner shown at the top
    banner_file, _ = \
        get_banner_file(base_dir, nickname, domain, theme)

    display_nickname = nickname
    is_bot = is_group = follow_dms = remove_twitter = ''
    notify_likes = notify_reactions = ''
    hide_like_button = hide_reaction_button = media_instance_str = ''
    blogs_instance_str = news_instance_str = moved_to = twitter_str = ''
    bio_str = donate_url = website_url = email_address = ''
    pgp_pub_key = enigma_pub_key = ''
    pgp_fingerprint = xmpp_address = matrix_address = ''
    ssb_address = blog_address = tox_address = ''
    cwtch_address = briar_address = manually_approves_followers = ''

    actor_json = load_json(actor_filename)
    if actor_json:
        if actor_json.get('movedTo'):
            moved_to = actor_json['movedTo']
        donate_url = get_donation_url(actor_json)
        website_url = get_website(actor_json, translate)
        xmpp_address = get_xmpp_address(actor_json)
        matrix_address = get_matrix_address(actor_json)
        ssb_address = get_ssb_address(actor_json)
        blog_address = get_blog_address(actor_json)
        tox_address = get_tox_address(actor_json)
        briar_address = get_briar_address(actor_json)
        cwtch_address = get_cwtch_address(actor_json)
        email_address = get_email_address(actor_json)
        enigma_pub_key = get_enigma_pub_key(actor_json)
        pgp_pub_key = get_pgp_pub_key(actor_json)
        pgp_fingerprint = get_pgp_fingerprint(actor_json)
        if actor_json.get('name'):
            if not is_filtered(base_dir, nickname, domain, actor_json['name']):
                display_nickname = actor_json['name']
        if actor_json.get('summary'):
            bio_str = \
                actor_json['summary'].replace('<p>', '').replace('</p>', '')
            if is_filtered(base_dir, nickname, domain, bio_str):
                bio_str = ''
            bio_str = remove_html(bio_str)
        if actor_json.get('manuallyApprovesFollowers'):
            if actor_json['manuallyApprovesFollowers']:
                manually_approves_followers = 'checked'
            else:
                manually_approves_followers = ''
        if actor_json.get('type'):
            if actor_json['type'] == 'Service':
                is_bot = 'checked'
                is_group = ''
            elif actor_json['type'] == 'Group':
                is_group = 'checked'
                is_bot = ''
    account_dir = acct_dir(base_dir, nickname, domain)
    if os.path.isfile(account_dir + '/.followDMs'):
        follow_dms = 'checked'
    if os.path.isfile(account_dir + '/.removeTwitter'):
        remove_twitter = 'checked'
    if os.path.isfile(account_dir + '/.notifyLikes'):
        notify_likes = 'checked'
    if os.path.isfile(account_dir + '/.notifyReactions'):
        notify_reactions = 'checked'
    if os.path.isfile(account_dir + '/.hideLikeButton'):
        hide_like_button = 'checked'
    if os.path.isfile(account_dir + '/.hideReactionButton'):
        hide_reaction_button = 'checked'

    media_instance = get_config_param(base_dir, "mediaInstance")
    if media_instance:
        if media_instance is True:
            media_instance_str = 'checked'
            blogs_instance_str = news_instance_str = ''

    news_instance = get_config_param(base_dir, "newsInstance")
    if news_instance:
        if news_instance is True:
            news_instance_str = 'checked'
            blogs_instance_str = media_instance_str = ''

    blogs_instance = get_config_param(base_dir, "blogsInstance")
    if blogs_instance:
        if blogs_instance is True:
            blogs_instance_str = 'checked'
            media_instance_str = news_instance_str = ''

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instance_str = ''
    role_assign_str = ''
    peertube_str = ''
    libretranslate_str = ''
    system_monitor_str = ''
    graphics_str = ''
    shares_federation_str = ''

    admin_nickname = get_config_param(base_dir, 'admin')

    if is_artist(base_dir, nickname) or \
       path.startswith('/users/' + str(admin_nickname) + '/'):
        graphics_str = _html_edit_profile_graphic_design(base_dir, translate)

    is_admin = False
    if admin_nickname:
        if path.startswith('/users/' + admin_nickname + '/'):
            is_admin = True
            twitter_str = \
                _html_edit_profile_twitter(base_dir, translate, remove_twitter)
            # shared items section
            shares_federation_str = \
                _html_edit_profile_shared_items(base_dir, nickname,
                                                domain, translate)
            instance_str, role_assign_str, peertube_str, libretranslate_str = \
                _html_edit_profile_instance(base_dir, translate,
                                            peertube_instances,
                                            media_instance_str,
                                            blogs_instance_str,
                                            news_instance_str)
            system_monitor_str = _html_system_monitor(nickname, translate)

    instance_title = get_config_param(base_dir, 'instanceTitle')
    edit_profile_form = \
        html_header_with_external_style(css_filename, instance_title, None)

    # keyboard navigation
    user_path_str = '/users/' + nickname
    user_timeline_str = '/users/' + nickname + '/' + default_timeline
    menu_timeline = \
        html_hide_from_screen_reader('🏠') + ' ' + \
        translate['Switch to timeline view']
    menu_profile = \
        html_hide_from_screen_reader('👤') + ' ' + \
        translate['Switch to profile view']
    nav_links = {
        menu_profile: user_path_str,
        menu_timeline: user_timeline_str
    }
    nav_access_keys = {
        menu_profile: 'p',
        menu_timeline: 't'
    }
    edit_profile_form += \
        html_keyboard_navigation(text_mode_banner, nav_links, nav_access_keys)

    # top banner
    edit_profile_form += \
        _html_edit_profile_top_banner(base_dir, nickname, domain, domain_full,
                                      default_timeline, banner_file,
                                      path, access_keys, translate)

    # main info
    edit_profile_form += \
        _html_edit_profile_main(base_dir, display_nickname, bio_str,
                                moved_to, donate_url, website_url,
                                blog_address, actor_json, translate,
                                nickname, domain)

    # Option checkboxes
    edit_profile_form += \
        _html_edit_profile_options(is_admin, manually_approves_followers,
                                   is_bot, is_group, follow_dms,
                                   remove_twitter,
                                   notify_likes, notify_reactions,
                                   hide_like_button, hide_reaction_button,
                                   translate, bold_reading)

    # Contact information
    edit_profile_form += \
        _html_edit_profile_contact_info(nickname, email_address,
                                        xmpp_address, matrix_address,
                                        ssb_address, tox_address,
                                        briar_address,
                                        cwtch_address, translate)

    # Encryption Keys
    edit_profile_form += \
        _html_edit_profile_encryption_keys(pgp_fingerprint,
                                           pgp_pub_key, enigma_pub_key,
                                           translate)

    # Customize images and banners
    edit_profile_form += \
        _html_edit_profile_background(news_instance, translate)

    # Change password
    edit_profile_form += _html_edit_profile_change_password(translate)

    # automatic translations
    edit_profile_form += libretranslate_str

    # system monitor
    edit_profile_form += system_monitor_str

    # Filtering and blocking section
    reply_interval_hours = \
        get_reply_interval_hours(base_dir, nickname, domain,
                                 default_reply_interval_hrs)
    edit_profile_form += \
        _html_edit_profile_filtering(base_dir, nickname, domain,
                                     user_agents_blocked, crawlers_allowed,
                                     translate, reply_interval_hours,
                                     cw_lists, lists_enabled)

    # git projects section
    edit_profile_form += \
        _html_edit_profile_git_projects(base_dir, nickname, domain, translate)

    # Skills section
    edit_profile_form += \
        _html_edit_profile_skills(base_dir, nickname, domain, translate)

    edit_profile_form += role_assign_str + peertube_str + graphics_str
    edit_profile_form += shares_federation_str + twitter_str + instance_str

    # danger zone section
    edit_profile_form += _html_edit_profile_danger_zone(translate)

    edit_profile_form += '    <div class="container">\n'
    edit_profile_form += \
        '      <center>\n' + \
        '        <input type="submit" name="submitProfile" value="' + \
        translate['Publish'] + '">\n' + \
        '      </center>\n'
    edit_profile_form += '    </div>\n'

    edit_profile_form += '  </div>\n'
    edit_profile_form += '</form>\n'
    edit_profile_form += html_footer()
    return edit_profile_form


def _individual_follow_as_html(signing_priv_key_pem: str,
                               translate: {},
                               base_dir: str, session,
                               cached_webfingers: {},
                               person_cache: {}, domain: str,
                               follow_url: str,
                               authorized: bool,
                               actor_nickname: str,
                               http_prefix: str,
                               project_version: str,
                               dormant: bool,
                               debug: bool,
                               buttons=[]) -> str:
    """An individual follow entry on the profile screen
    """
    follow_url_nickname = get_nickname_from_actor(follow_url)
    if not follow_url_nickname:
        return ''
    follow_url_domain, follow_url_port = get_domain_from_actor(follow_url)
    follow_url_domain_full = \
        get_full_domain(follow_url_domain, follow_url_port)
    title_str = '@' + follow_url_nickname + '@' + follow_url_domain_full
    avatar_url = \
        get_person_avatar_url(base_dir, follow_url, person_cache, True)
    if not avatar_url:
        avatar_url = follow_url + '/avatar.png'

    display_name = get_display_name(base_dir, follow_url, person_cache)
    is_group = False
    if not display_name:
        # lookup the correct webfinger for the follow_url
        follow_url_handle = follow_url_nickname + '@' + follow_url_domain_full
        follow_url_wf = \
            webfinger_handle(session, follow_url_handle, http_prefix,
                             cached_webfingers,
                             domain, __version__, debug, False,
                             signing_priv_key_pem)

        origin_domain = domain
        (_, _, _, _, _, avatar_url2,
         display_name, is_group) = get_person_box(signing_priv_key_pem,
                                                  origin_domain,
                                                  base_dir, session,
                                                  follow_url_wf,
                                                  person_cache,
                                                  project_version,
                                                  http_prefix,
                                                  follow_url_nickname,
                                                  domain, 'outbox', 43036)
        if avatar_url2:
            avatar_url = avatar_url2

    if display_name:
        display_name = \
            add_emoji_to_display_name(None, base_dir, http_prefix,
                                      actor_nickname, domain,
                                      display_name, False)
        title_str = display_name

    if dormant:
        title_str += ' 💤'

    buttons_str = ''
    if authorized:
        for btn in buttons:
            if btn == 'block':
                buttons_str += \
                    '<a href="/users/' + actor_nickname + \
                    '?options=' + follow_url + \
                    ';1;' + avatar_url + \
                    '"><button class="buttonunfollow">' + \
                    translate['Block'] + '</button></a>\n'
            elif btn == 'unfollow':
                unfollow_str = 'Unfollow'
                if is_group or \
                   is_group_account(base_dir,
                                    follow_url_nickname, follow_url_domain):
                    unfollow_str = 'Leave'
                buttons_str += \
                    '<a href="/users/' + actor_nickname + \
                    '?options=' + follow_url + \
                    ';1;' + avatar_url + \
                    '"><button class="buttonunfollow">' + \
                    translate[unfollow_str] + '</button></a>\n'

    result_str = '<div class="container">\n'
    result_str += \
        '<a href="/users/' + actor_nickname + '?options=' + \
        follow_url + ';1;' + avatar_url + '">\n'
    result_str += '<p><img loading="lazy" decoding="async" ' + \
        'src="' + avatar_url + '" alt=" ">'
    result_str += title_str + '</a>' + buttons_str + '</p>\n'
    result_str += '</div>\n'
    return result_str
