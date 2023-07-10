__filename__ = "webapp_utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
from collections import OrderedDict
from session import get_json
from utils import local_network_host
from utils import get_media_extensions
from utils import dangerous_markup
from utils import acct_handle_dir
from utils import remove_id_ending
from utils import get_attachment_property_value
from utils import is_account_dir
from utils import remove_html
from utils import get_protocol_prefixes
from utils import load_json
from utils import get_cached_post_filename
from utils import get_config_param
from utils import acct_dir
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import is_float
from utils import get_audio_extensions
from utils import get_video_extensions
from utils import get_image_extensions
from utils import local_actor_url
from utils import text_in_file
from utils import remove_eol
from filters import is_filtered
from cache import store_person_in_cache
from content import add_html_tags
from content import replace_emoji_from_tags
from person import get_person_avatar_url
from posts import is_moderator
from blocking import is_blocked
from blocking import allowed_announce


def minimizing_attached_images(base_dir: str, nickname: str, domain: str,
                               following_nickname: str,
                               following_domain: str) -> bool:
    """Returns true if images from the account being followed should be
    minimized by default
    """
    if following_nickname == nickname and following_domain == domain:
        # reminder post
        return False
    minimize_filename = \
        acct_dir(base_dir, nickname, domain) + '/followingMinimizeImages.txt'
    handle = following_nickname + '@' + following_domain
    if not os.path.isfile(minimize_filename):
        following_filename = \
            acct_dir(base_dir, nickname, domain) + '/following.txt'
        if not os.path.isfile(following_filename):
            return False
        # create a new minimize file from the following file
        try:
            with open(minimize_filename, 'w+',
                      encoding='utf-8') as fp_min:
                fp_min.write('')
        except OSError:
            print('EX: minimizing_attached_images 2 ' + minimize_filename)
    return text_in_file(handle + '\n', minimize_filename, False)


def get_broken_link_substitute() -> str:
    """Returns html used to show a default image if the link to
    an image is broken
    """
    return " onerror=\"this.onerror=null; this.src='" + \
        "/icons/avatar_default.png'\""


def html_following_list(base_dir: str, following_filename: str) -> str:
    """Returns a list of handles being followed
    """
    with open(following_filename, 'r', encoding='utf-8') as following_file:
        msg = following_file.read()
        following_list = msg.split('\n')
        following_list.sort()
        if following_list:
            css_filename = base_dir + '/epicyon-profile.css'
            if os.path.isfile(base_dir + '/epicyon.css'):
                css_filename = base_dir + '/epicyon.css'

            instance_title = \
                get_config_param(base_dir, 'instanceTitle')
            following_list_html = \
                html_header_with_external_style(css_filename,
                                                instance_title, None)
            for following_address in following_list:
                if following_address:
                    following_list_html += \
                        '<h3>@' + following_address + '</h3>'
            following_list_html += html_footer()
            msg = following_list_html
        return msg
    return ''


def csv_following_list(following_filename: str,
                       base_dir: str, nickname: str, domain: str) -> str:
    """Returns a csv of handles being followed
    """
    with open(following_filename, 'r', encoding='utf-8') as following_file:
        msg = following_file.read()
        following_list = msg.split('\n')
        following_list.sort()
        if following_list:
            following_list_csv = ''
            for following_address in following_list:
                if not following_address:
                    continue

                following_nickname = \
                    get_nickname_from_actor(following_address)
                following_domain, _ = \
                    get_domain_from_actor(following_address)

                announce_is_allowed = \
                    allowed_announce(base_dir, nickname, domain,
                                     following_nickname,
                                     following_domain)
                notify_on_new = 'false'
                languages = ''
                person_notes = ''
                person_notes_filename = \
                    acct_dir(base_dir, nickname, domain) + \
                    '/notes/' + following_address + '.txt'
                if os.path.isfile(person_notes_filename):
                    with open(person_notes_filename, 'r',
                              encoding='utf-8') as fp_notes:
                        person_notes = fp_notes.read()
                        person_notes = person_notes.replace(',', ' ')
                        person_notes = person_notes.replace('"', "'")
                        person_notes = person_notes.replace('\n', '<br>')
                        person_notes = person_notes.replace('  ', ' ')
                if not following_list_csv:
                    following_list_csv = \
                        'Account address,Show boosts,' + \
                        'Notify on new posts,Languages,Notes\n'
                following_list_csv += \
                    following_address + ',' + \
                    str(announce_is_allowed).lower() + ',' + \
                    notify_on_new + ',' + \
                    languages + ',' + \
                    person_notes + '\n'
            msg = following_list_csv
        return msg
    return ''


def html_hashtag_blocked(base_dir: str, translate: {}) -> str:
    """Show the screen for a blocked hashtag
    """
    blocked_hashtag_form = ''
    css_filename = base_dir + '/epicyon-suspended.css'
    if os.path.isfile(base_dir + '/suspended.css'):
        css_filename = base_dir + '/suspended.css'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    blocked_hashtag_form = \
        html_header_with_external_style(css_filename, instance_title, None)
    blocked_hashtag_form += '<div><center>\n'
    blocked_hashtag_form += \
        '  <p class="screentitle">' + \
        translate['Hashtag Blocked'] + '</p>\n'
    blocked_hashtag_form += \
        '  <p>See <a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>\n'
    blocked_hashtag_form += '</center></div>\n'
    blocked_hashtag_form += html_footer()
    return blocked_hashtag_form


def header_buttons_front_screen(translate: {},
                                nickname: str, box_name: str,
                                authorized: bool,
                                icons_as_buttons: bool) -> str:
    """Returns the header buttons for the front page of a news instance
    """
    header_str = ''
    if nickname == 'news':
        button_features = 'buttonMobile'
        button_newswire = 'buttonMobile'
        button_links = 'buttonMobile'
        if box_name == 'features':
            button_features = 'buttonselected'
        elif box_name == 'newswire':
            button_newswire = 'buttonselected'
        elif box_name == 'links':
            button_links = 'buttonselected'

        header_str += \
            '        <a href="/">' + \
            '<button class="' + button_features + '">' + \
            '<span>' + translate['Features'] + \
            '</span></button></a>'
        if not authorized:
            header_str += \
                '        <a href="/login">' + \
                '<button class="buttonMobile">' + \
                '<span>' + translate['Login'] + \
                '</span></button></a>'
        if icons_as_buttons:
            header_str += \
                '        <a href="/users/news/newswiremobile">' + \
                '<button class="' + button_newswire + '">' + \
                '<span>' + translate['Newswire'] + \
                '</span></button></a>'
            header_str += \
                '        <a href="/users/news/linksmobile">' + \
                '<button class="' + button_links + '">' + \
                '<span>' + translate['Links'] + \
                '</span></button></a>'
        else:
            header_str += \
                '        <a href="' + \
                '/users/news/newswiremobile">' + \
                '<img loading="lazy" decoding="async" src="/icons' + \
                '/newswire.png" title="' + translate['Newswire'] + \
                '" alt="| ' + translate['Newswire'] + '"/></a>\n'
            header_str += \
                '        <a href="' + \
                '/users/news/linksmobile">' + \
                '<img loading="lazy" decoding="async" src="/icons' + \
                '/links.png" title="' + translate['Links'] + \
                '" alt="| ' + translate['Links'] + '"/></a>\n'
    else:
        if not authorized:
            header_str += \
                '        <a href="/login">' + \
                '<button class="buttonMobile">' + \
                '<span>' + translate['Login'] + \
                '</span></button></a>'

    if header_str:
        header_str = \
            '\n      <div class="frontPageMobileButtons">\n' + \
            header_str + \
            '      </div>\n'
    return header_str


def get_content_warning_button(post_id: str, translate: {},
                               content: str) -> str:
    """Returns the markup for a content warning button
    """
    return '       <details><summary class="cw" tabindex="10">' + \
        translate['SHOW MORE'] + '</summary>' + \
        '<div id="' + post_id + '">' + content + \
        '</div></details>\n'


def _set_actor_property_url(actor_json: {},
                            property_name: str, url: str) -> None:
    """Sets a url for the given actor property
    """
    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    property_name_lower = property_name.lower()

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not name_value.lower().startswith(property_name_lower):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)

    prefixes = get_protocol_prefixes()
    prefix_found = False
    for prefix in prefixes:
        if url.startswith(prefix):
            prefix_found = True
            break
    if not prefix_found:
        return
    if '.' not in url:
        return
    if ' ' in url:
        return
    if ',' in url:
        return

    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not name_value.lower().startswith(property_name_lower):
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        property_value[prop_value_name] = url
        return

    new_address = {
        "name": property_name,
        "type": "PropertyValue",
        "value": url
    }
    actor_json['attachment'].append(new_address)


def set_blog_address(actor_json: {}, blog_address: str) -> None:
    """Sets an blog address for the given actor
    """
    _set_actor_property_url(actor_json, 'Blog', remove_html(blog_address))


def update_avatar_image_cache(signing_priv_key_pem: str,
                              session, base_dir: str, http_prefix: str,
                              actor: str, avatar_url: str,
                              person_cache: {}, allow_downloads: bool,
                              force: bool = False, debug: bool = False) -> str:
    """Updates the cached avatar for the given actor
    """
    if not avatar_url:
        return None
    actor_str = actor.replace('/', '-')
    avatar_image_path = base_dir + '/cache/avatars/' + actor_str

    # try different image types
    image_formats = {
        'png': 'png',
        'jpg': 'jpeg',
        'jxl': 'jxl',
        'jpeg': 'jpeg',
        'gif': 'gif',
        'svg': 'svg+xml',
        'webp': 'webp',
        'avif': 'avif',
        'heic': 'heic'
    }
    avatar_image_filename = None
    for im_format, mime_type in image_formats.items():
        if avatar_url.endswith('.' + im_format) or \
           '.' + im_format + '?' in avatar_url:
            session_headers = {
                'Accept': 'image/' + mime_type
            }
            avatar_image_filename = avatar_image_path + '.' + im_format

    if not avatar_image_filename:
        return None

    if (not os.path.isfile(avatar_image_filename) or force) and \
       allow_downloads:
        try:
            if debug:
                print('avatar image url: ' + avatar_url)
            result = session.get(avatar_url,
                                 headers=session_headers,
                                 params=None,
                                 allow_redirects=False)
            if result.status_code < 200 or \
               result.status_code > 202:
                if debug:
                    print('Avatar image download failed with status ' +
                          str(result.status_code))
                # remove partial download
                if os.path.isfile(avatar_image_filename):
                    try:
                        os.remove(avatar_image_filename)
                    except OSError:
                        print('EX: ' +
                              'update_avatar_image_cache unable to delete ' +
                              avatar_image_filename)
            else:
                with open(avatar_image_filename, 'wb') as fp_av:
                    fp_av.write(result.content)
                    if debug:
                        print('avatar image downloaded for ' + actor)
                    return avatar_image_filename.replace(base_dir + '/cache',
                                                         '')
        except Exception as ex:
            print('EX: Failed to download avatar image: ' +
                  str(avatar_url) + ' ' + str(ex))
        prof = 'https://www.w3.org/ns/activitystreams'
        if '/channel/' not in actor or '/accounts/' not in actor:
            session_headers = {
                'Accept': 'application/activity+json; profile="' + prof + '"'
            }
        else:
            session_headers = {
                'Accept': 'application/ld+json; profile="' + prof + '"'
            }
        person_json = \
            get_json(signing_priv_key_pem, session, actor,
                     session_headers, None,
                     debug, __version__, http_prefix, None)
        if person_json:
            if not person_json.get('id'):
                return None
            if not person_json.get('publicKey'):
                return None
            if not person_json['publicKey'].get('publicKeyPem'):
                return None
            if person_json['id'] != actor:
                return None
            if not person_cache.get(actor):
                return None
            if person_cache[actor]['actor']['publicKey']['publicKeyPem'] != \
               person_json['publicKey']['publicKeyPem']:
                print("ERROR: " +
                      "public keys don't match when downloading actor for " +
                      actor)
                return None
            store_person_in_cache(base_dir, actor, person_json, person_cache,
                                  allow_downloads)
            return get_person_avatar_url(base_dir, actor, person_cache)
        return None
    return avatar_image_filename.replace(base_dir + '/cache', '')


def scheduled_posts_exist(base_dir: str, nickname: str, domain: str) -> bool:
    """Returns true if there are posts scheduled to be delivered
    """
    schedule_index_filename = \
        acct_dir(base_dir, nickname, domain) + '/schedule.index'
    if not os.path.isfile(schedule_index_filename):
        return False
    if text_in_file('#users#', schedule_index_filename):
        return True
    return False


def shares_timeline_json(actor: str, page_number: int, items_per_page: int,
                         base_dir: str, domain: str, nickname: str,
                         max_shares_per_account: int,
                         shared_items_federated_domains: [],
                         shares_file_type: str) -> ({}, bool):
    """Get a page on the shared items timeline as json
    max_shares_per_account helps to avoid one person dominating the timeline
    by sharing a large number of things
    """
    all_shares_json = {}
    for _, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if not is_account_dir(handle):
                continue
            account_dir = acct_handle_dir(base_dir, handle)
            shares_filename = account_dir + '/' + shares_file_type + '.json'
            if not os.path.isfile(shares_filename):
                continue
            shares_json = load_json(shares_filename)
            if not shares_json:
                continue
            account_nickname = handle.split('@')[0]
            # Don't include shared items from blocked accounts
            if account_nickname != nickname:
                if is_blocked(base_dir, nickname, domain,
                              account_nickname, domain, None):
                    continue
            # actor who owns this share
            owner = actor.split('/users/')[0] + '/users/' + account_nickname
            ctr = 0
            for item_id, item in shares_json.items():
                # assign owner to the item
                item['actor'] = owner
                item['shareId'] = item_id
                all_shares_json[str(item['published'])] = item
                ctr += 1
                if ctr >= max_shares_per_account:
                    break
        break
    if shared_items_federated_domains:
        if shares_file_type == 'shares':
            catalogs_dir = base_dir + '/cache/catalogs'
        else:
            catalogs_dir = base_dir + '/cache/wantedItems'
        if os.path.isdir(catalogs_dir):
            for _, dirs, files in os.walk(catalogs_dir):
                for fname in files:
                    if '#' in fname:
                        continue
                    if not fname.endswith('.' + shares_file_type + '.json'):
                        continue
                    federated_domain = fname.split('.')[0]
                    if federated_domain not in shared_items_federated_domains:
                        continue
                    shares_filename = catalogs_dir + '/' + fname
                    shares_json = load_json(shares_filename)
                    if not shares_json:
                        continue
                    ctr = 0
                    for item_id, item in shares_json.items():
                        # assign owner to the item
                        if '--shareditems--' not in item_id:
                            continue
                        share_actor = item_id.split('--shareditems--')[0]
                        share_actor = share_actor.replace('___', '://')
                        share_actor = share_actor.replace('--', '/')
                        share_nickname = get_nickname_from_actor(share_actor)
                        if not share_nickname:
                            continue
                        if is_blocked(base_dir, nickname, domain,
                                      share_nickname, federated_domain, None):
                            continue
                        item['actor'] = share_actor
                        item['shareId'] = item_id
                        all_shares_json[str(item['published'])] = item
                        ctr += 1
                        if ctr >= max_shares_per_account:
                            break
                break
    # sort the shared items in descending order of publication date
    shares_json = OrderedDict(sorted(all_shares_json.items(), reverse=True))
    last_page = False
    start_index = items_per_page * page_number
    max_index = len(shares_json.items())
    if max_index < items_per_page:
        last_page = True
    if start_index >= max_index - items_per_page:
        last_page = True
        start_index = max_index - items_per_page
        start_index = max(start_index, 0)
    ctr = 0
    result_json = {}
    for published, item in shares_json.items():
        if ctr >= start_index + items_per_page:
            break
        if ctr < start_index:
            ctr += 1
            continue
        result_json[published] = item
        ctr += 1
    return result_json, last_page


def get_shares_collection(actor: str, page_number: int, items_per_page: int,
                          base_dir: str, domain: str, nickname: str,
                          max_shares_per_account: int,
                          shared_items_federated_domains: [],
                          shares_file_type: str) -> {}:
    """Returns an ActivityStreams collection of Offer activities
    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-offer
    """
    shares_collection = []
    shares_json, _ = \
        shares_timeline_json(actor, page_number, items_per_page,
                             base_dir, domain, nickname,
                             max_shares_per_account,
                             shared_items_federated_domains, shares_file_type)

    if shares_file_type == 'shares':
        share_type = 'Offer'
    else:
        share_type = 'Want'

    for _, shared_item in shares_json.items():
        if not shared_item.get('shareId'):
            continue
        if not shared_item.get('itemType'):
            continue
        share_id = shared_item['shareId'].replace('___', '://')
        share_id = share_id.replace('--', '/')
        offer_item = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "summary": shared_item['summary'],
            "type": share_type,
            "actor": shared_item['actor'],
            "id": share_id,
            "published": shared_item['published'],
            "object": {
                "id": share_id,
                "type": shared_item['itemType'].title(),
                "name": shared_item['displayName'],
                "published": shared_item['published'],
                "attachment": []
            }
        }
        if shared_item['category']:
            offer_item['object']['attachment'].append({
                "type": "PropertyValue",
                "name": "category",
                "value": shared_item['category']
            })
        if shared_item['location']:
            offer_item['object']['attachment'].append({
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "Place",
                "name": shared_item['location'].title()
            })
        if shared_item['imageUrl']:
            if '://' in shared_item['imageUrl']:
                file_extension = None
                accepted_types = get_media_extensions()
                for mtype in accepted_types:
                    if shared_item['imageUrl'].endswith('.' + mtype):
                        if mtype == 'jpg':
                            mtype = 'jpeg'
                        if mtype == 'mp3':
                            mtype = 'mpeg'
                        file_extension = mtype
                if file_extension:
                    media_type = 'image/' + file_extension
                    offer_item['object']['attachment'].append({
                        'mediaType': media_type,
                        'name': shared_item['displayName'],
                        'type': 'Document',
                        'url': shared_item['imageUrl']
                    })
        if shared_item['itemPrice'] and shared_item['itemCurrency']:
            offer_item['object']['attachment'].append({
                "type": "PropertyValue",
                "name": "price",
                "value": shared_item['itemPrice']
            })
            offer_item['object']['attachment'].append({
                "type": "PropertyValue",
                "name": "currency",
                "value": shared_item['itemCurrency']
            })
        shares_collection.append(offer_item)

    result_json = {
        "@context": [
            "https://www.w3.org/ns/activitystreams"
        ],
        "id": actor + '?page=' + str(page_number),
        "type": "OrderedCollection",
        "name": nickname + "'s Shared Items",
        "orderedItems": shares_collection
    }

    return result_json


def post_contains_public(post_json_object: {}) -> bool:
    """Does the given post contain #Public
    """
    contains_public = False
    if not post_json_object['object'].get('to'):
        return contains_public

    for to_address in post_json_object['object']['to']:
        if to_address.endswith('#Public') or \
           to_address == 'as:Public' or \
           to_address == 'Public':
            contains_public = True
            break
        if not contains_public:
            if post_json_object['object'].get('cc'):
                for to_address2 in post_json_object['object']['cc']:
                    if to_address2.endswith('#Public') or \
                       to_address2 == 'as:Public' or \
                       to_address2 == 'Public':
                        contains_public = True
                        break
    return contains_public


def _get_image_file(base_dir: str, name: str, directory: str,
                    theme: str) -> (str, str):
    """
    returns the filenames for an image with the given name
    """
    banner_extensions = get_image_extensions()
    banner_file = ''
    banner_filename = ''
    im_name = name
    for ext in banner_extensions:
        banner_file_test = im_name + '.' + ext
        banner_filename_test = directory + '/' + banner_file_test
        if os.path.isfile(banner_filename_test):
            banner_file = banner_file_test
            banner_filename = banner_filename_test
            return banner_file, banner_filename
    # if not found then use the default image
    theme = 'default'
    directory = base_dir + '/theme/' + theme
    for ext in banner_extensions:
        banner_file_test = name + '.' + ext
        banner_filename_test = directory + '/' + banner_file_test
        if os.path.isfile(banner_filename_test):
            banner_file = name + '_' + theme + '.' + ext
            banner_filename = banner_filename_test
            break
    return banner_file, banner_filename


def get_banner_file(base_dir: str,
                    nickname: str, domain: str, theme: str) -> (str, str):
    """Gets the image for the timeline banner
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'banner', account_dir, theme)


def get_profile_background_file(base_dir: str,
                                nickname: str, domain: str,
                                theme: str) -> (str, str):
    """Gets the image for the profile background
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'image', account_dir, theme)


def get_search_banner_file(base_dir: str,
                           nickname: str, domain: str,
                           theme: str) -> (str, str):
    """Gets the image for the search banner
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'search_banner', account_dir, theme)


def get_left_image_file(base_dir: str,
                        nickname: str, domain: str, theme: str) -> (str, str):
    """Gets the image for the left column
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'left_col_image', account_dir, theme)


def get_right_image_file(base_dir: str,
                         nickname: str, domain: str, theme: str) -> (str, str):
    """Gets the image for the right column
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'right_col_image', account_dir, theme)


def _get_variable_from_css(css_str: str, variable: str) -> str:
    """Gets a variable value from the css file text
    """
    if '--' + variable + ':' not in css_str:
        return None
    value = css_str.split('--' + variable + ':')[1]
    if ';' in value:
        value = value.split(';')[0].strip()
    value = remove_html(value)
    if ' ' in value:
        value = None
    return value


def get_pwa_theme_colors(css_filename: str) -> (str, str):
    """Gets the theme/statusbar color for progressive web apps
    """
    default_pwa_theme_color = 'apple-mobile-web-app-status-bar-style'
    pwa_theme_color = default_pwa_theme_color

    default_pwa_theme_background_color = 'black-translucent'
    pwa_theme_background_color = default_pwa_theme_background_color

    if not os.path.isfile(css_filename):
        return pwa_theme_color, pwa_theme_background_color

    css_str = ''
    with open(css_filename, 'r', encoding='utf-8') as fp_css:
        css_str = fp_css.read()

    pwa_theme_color = \
        _get_variable_from_css(css_str, 'pwa-theme-color')
    if not pwa_theme_color:
        pwa_theme_color = default_pwa_theme_color

    pwa_theme_background_color = \
        _get_variable_from_css(css_str, 'pwa-theme-background-color')
    if not pwa_theme_background_color:
        pwa_theme_background_color = default_pwa_theme_background_color

    return pwa_theme_color, pwa_theme_background_color


def html_header_with_external_style(css_filename: str, instance_title: str,
                                    metadata: str, lang='en') -> str:
    if metadata is None:
        metadata = ''
    css_file = '/' + css_filename.split('/')[-1]
    pwa_theme_color, pwa_theme_background_color = \
        get_pwa_theme_colors(css_filename)
    html_str = \
        '<!DOCTYPE html>\n' + \
        '<!--\n' + \
        'Thankyou for using Epicyon. If you are reading this message then ' + \
        'consider joining the development at ' + \
        'https://gitlab.com/bashrc2/epicyon\n' + \
        '-->\n' + \
        '<html lang="' + lang + '">\n' + \
        '  <head>\n' + \
        '    <meta charset="utf-8">\n' + \
        '    <link rel="stylesheet" media="all" ' + \
        'href="' + css_file + '">\n' + \
        '    <link rel="manifest" href="/manifest.json">\n' + \
        '    <link href="/favicon.ico" rel="icon" type="image/x-icon">\n' + \
        '    <meta content="/browserconfig.xml" ' + \
        'name="msapplication-config">\n' + \
        '    <meta content="yes" name="apple-mobile-web-app-capable">\n' + \
        '    <link href="/apple-touch-icon.png" rel="apple-touch-icon" ' + \
        'sizes="180x180">\n' + \
        '    <meta name="theme-color" content="' + pwa_theme_color + '">\n' + \
        metadata + \
        '    <meta name="apple-mobile-web-app-status-bar-style" ' + \
        'content="' + pwa_theme_background_color + '">\n' + \
        '    <title>' + instance_title + '</title>\n' + \
        '  </head>\n' + \
        '  <body>\n'
    return html_str


def html_header_with_person_markup(css_filename: str, instance_title: str,
                                   actor_json: {}, city: str,
                                   content_license_url: str,
                                   lang='en') -> str:
    """html header which includes person markup
    https://schema.org/Person
    """
    if not actor_json:
        html_str = \
            html_header_with_external_style(css_filename,
                                            instance_title, None, lang)
        return html_str

    city_markup = ''
    if city:
        city = city.lower().title()
        add_comma = ''
        country_markup = ''
        if ',' in city:
            country = city.split(',', 1)[1].strip().title()
            city = city.split(',', 1)[0]
            country_markup = \
                '          "addressCountry": "' + country + '"\n'
            add_comma = ','
        city_markup = \
            '        "address": {\n' + \
            '          "@type": "PostalAddress",\n' + \
            '          "addressLocality": "' + city + '"' + \
            add_comma + '\n' + country_markup + '        },\n'

    skills_markup = ''
    if actor_json.get('hasOccupation'):
        if isinstance(actor_json['hasOccupation'], list):
            skills_markup = '        "hasOccupation": [\n'
            first_entry = True
            for skill_dict in actor_json['hasOccupation']:
                if skill_dict['@type'] == 'Role':
                    if not first_entry:
                        skills_markup += ',\n'
                    skl = skill_dict['hasOccupation']
                    role_name = skl['name']
                    if not role_name:
                        role_name = 'member'
                    category = \
                        skl['occupationalCategory']['codeValue']
                    category_url = \
                        'https://www.onetonline.org/link/summary/' + category
                    skills_markup += \
                        '        {\n' + \
                        '          "@type": "Role",\n' + \
                        '          "hasOccupation": {\n' + \
                        '            "@type": "Occupation",\n' + \
                        '            "name": "' + role_name + '",\n' + \
                        '            "description": ' + \
                        '"Fediverse instance role",\n' + \
                        '            "occupationLocation": {\n' + \
                        '              "@type": "City",\n' + \
                        '              "name": "' + city + '"\n' + \
                        '            },\n' + \
                        '            "occupationalCategory": {\n' + \
                        '              "@type": "CategoryCode",\n' + \
                        '              "inCodeSet": {\n' + \
                        '                "@type": "CategoryCodeSet",\n' + \
                        '                "name": "O*Net-SOC",\n' + \
                        '                "dateModified": "2019",\n' + \
                        '                ' + \
                        '"url": "https://www.onetonline.org/"\n' + \
                        '              },\n' + \
                        '              "codeValue": "' + category + '",\n' + \
                        '              "url": "' + category_url + '"\n' + \
                        '            }\n' + \
                        '          }\n' + \
                        '        }'
                elif skill_dict['@type'] == 'Occupation':
                    if not first_entry:
                        skills_markup += ',\n'
                    oc_name = skill_dict['name']
                    if not oc_name:
                        oc_name = 'member'
                    skills_list = skill_dict['skills']
                    skills_list_str = '['
                    for skill_str in skills_list:
                        if skills_list_str != '[':
                            skills_list_str += ', '
                        skills_list_str += '"' + skill_str + '"'
                    skills_list_str += ']'
                    skills_markup += \
                        '        {\n' + \
                        '          "@type": "Occupation",\n' + \
                        '          "name": "' + oc_name + '",\n' + \
                        '          "description": ' + \
                        '"Fediverse instance occupation",\n' + \
                        '          "occupationLocation": {\n' + \
                        '            "@type": "City",\n' + \
                        '            "name": "' + city + '"\n' + \
                        '          },\n' + \
                        '          "skills": ' + skills_list_str + '\n' + \
                        '        }'
                first_entry = False
            skills_markup += '\n        ],\n'

    description = remove_html(actor_json['summary'])
    name_str = remove_html(actor_json['name'])
    domain_full = actor_json['id'].split('://')[1].split('/')[0]
    handle = actor_json['preferredUsername'] + '@' + domain_full

    person_markup = \
        '      "about": {\n' + \
        '        "@type" : "Person",\n' + \
        '        "name": "' + name_str + '",\n' + \
        '        "image": "' + actor_json['icon']['url'] + '",\n' + \
        '        "description": "' + description + '",\n' + \
        city_markup + skills_markup + \
        '        "url": "' + actor_json['id'] + '"\n' + \
        '      },\n'

    profile_markup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context":"https://schema.org",\n' + \
        '      "@type": "ProfilePage",\n' + \
        '      "mainEntityOfPage": {\n' + \
        '        "@type": "WebPage",\n' + \
        "        \"@id\": \"" + actor_json['id'] + "\"\n" + \
        '      },\n' + person_markup + \
        '      "accountablePerson": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + name_str + '"\n' + \
        '      },\n' + \
        '      "copyrightHolder": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + name_str + '"\n' + \
        '      },\n' + \
        '      "name": "' + name_str + '",\n' + \
        '      "image": "' + actor_json['icon']['url'] + '",\n' + \
        '      "description": "' + description + '",\n' + \
        '      "license": "' + content_license_url + '"\n' + \
        '    }\n' + \
        '    </script>\n'

    description = remove_html(description)
    og_metadata = \
        "    <meta content=\"profile\" property=\"og:type\" />\n" + \
        "    <meta content=\"" + description + \
        "\" name='description'>\n" + \
        "    <meta content=\"" + actor_json['url'] + \
        "\" property=\"og:url\" />\n" + \
        "    <meta content=\"" + domain_full + \
        "\" property=\"og:site_name\" />\n" + \
        "    <meta content=\"" + name_str + " (@" + handle + \
        ")\" property=\"og:title\" />\n" + \
        "    <meta content=\"" + description + \
        "\" property=\"og:description\" />\n" + \
        "    <meta content=\"" + actor_json['icon']['url'] + \
        "\" property=\"og:image\" />\n" + \
        "    <meta content=\"400\" property=\"og:image:width\" />\n" + \
        "    <meta content=\"400\" property=\"og:image:height\" />\n" + \
        "    <meta content=\"summary\" property=\"twitter:card\" />\n" + \
        "    <meta content=\"" + handle + \
        "\" property=\"profile:username\" />\n"
    if actor_json.get('attachment'):
        og_tags = (
            'email', 'openpgp', 'blog', 'xmpp', 'matrix', 'briar',
            'cwtch', 'languages'
        )
        for attach_json in actor_json['attachment']:
            if not attach_json.get('name'):
                if not attach_json.get('schema:name'):
                    continue
            prop_value_name, _ = get_attachment_property_value(attach_json)
            if not prop_value_name:
                continue
            if attach_json.get('name'):
                name = attach_json['name'].lower()
            else:
                name = attach_json['schema:name'].lower()
            value = attach_json[prop_value_name]
            for og_tag in og_tags:
                if name != og_tag:
                    continue
                og_metadata += \
                    "    <meta content=\"" + value + \
                    "\" property=\"og:" + og_tag + "\" />\n"

    html_str = \
        html_header_with_external_style(css_filename, instance_title,
                                        og_metadata + profile_markup, lang)
    return html_str


def html_header_with_website_markup(css_filename: str, instance_title: str,
                                    http_prefix: str, domain: str,
                                    system_language: str) -> str:
    """html header which includes website markup
    https://schema.org/WebSite
    """
    license_url = 'https://www.gnu.org/licenses/agpl-3.0.rdf'

    # social networking category
    genre_url = 'http://vocab.getty.edu/aat/300312270'

    website_markup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context" : "http://schema.org",\n' + \
        '      "@type" : "WebSite",\n' + \
        '      "name": "' + instance_title + '",\n' + \
        '      "url": "' + http_prefix + '://' + domain + '",\n' + \
        '      "license": "' + license_url + '",\n' + \
        '      "inLanguage": "' + system_language + '",\n' + \
        '      "isAccessibleForFree": true,\n' + \
        '      "genre": "' + genre_url + '",\n' + \
        '      "accessMode": ["textual", "visual"],\n' + \
        '      "accessModeSufficient": ["textual"],\n' + \
        '      "accessibilityAPI" : ["ARIA"],\n' + \
        '      "accessibilityControl" : [\n' + \
        '        "fullKeyboardControl",\n' + \
        '        "fullTouchControl",\n' + \
        '        "fullMouseControl"\n' + \
        '      ],\n' + \
        '      "encodingFormat" : [\n' + \
        '        "text/html", "image/png", "image/webp",\n' + \
        '        "image/jpeg", "image/gif", "text/css"\n' + \
        '      ]\n' + \
        '    }\n' + \
        '    </script>\n'

    og_metadata = \
        '    <meta content="Epicyon hosted on ' + domain + \
        '" property="og:site_name" />\n' + \
        '    <meta content="' + http_prefix + '://' + domain + \
        '/about" property="og:url" />\n' + \
        '    <meta content="website" property="og:type" />\n' + \
        '    <meta content="' + instance_title + \
        '" property="og:title" />\n' + \
        '    <meta content="' + http_prefix + '://' + domain + \
        '/logo.png" property="og:image" />\n' + \
        '    <meta content="' + system_language + \
        '" property="og:locale" />\n' + \
        '    <meta content="summary_large_image" property="twitter:card" />\n'

    html_str = \
        html_header_with_external_style(css_filename, instance_title,
                                        og_metadata + website_markup,
                                        system_language)
    return html_str


def html_header_with_blog_markup(css_filename: str, instance_title: str,
                                 http_prefix: str, domain: str, nickname: str,
                                 system_language: str,
                                 published: str, modified: str,
                                 title: str, snippet: str,
                                 translate: {}, url: str,
                                 content_license_url: str) -> str:
    """html header which includes blog post markup
    https://schema.org/BlogPosting
    """
    author_url = local_actor_url(http_prefix, nickname, domain)
    about_url = http_prefix + '://' + domain + '/about.html'

    # license for content on the site may be different from
    # the software license

    blog_markup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context" : "http://schema.org",\n' + \
        '      "@type" : "BlogPosting",\n' + \
        '      "headline": "' + title + '",\n' + \
        '      "datePublished": "' + published + '",\n' + \
        '      "dateModified": "' + modified + '",\n' + \
        '      "author": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + nickname + '",\n' + \
        '        "sameAs": "' + author_url + '"\n' + \
        '      },\n' + \
        '      "publisher": {\n' + \
        '        "@type": "WebSite",\n' + \
        '        "name": "' + instance_title + '",\n' + \
        '        "sameAs": "' + about_url + '"\n' + \
        '      },\n' + \
        '      "license": "' + content_license_url + '",\n' + \
        '      "description": "' + snippet + '"\n' + \
        '    }\n' + \
        '    </script>\n'

    og_metadata = \
        '    <meta property="og:locale" content="' + \
        system_language + '" />\n' + \
        '    <meta property="og:type" content="article" />\n' + \
        '    <meta property="og:title" content="' + title + '" />\n' + \
        '    <meta property="og:url" content="' + url + '" />\n' + \
        '    <meta content="Epicyon hosted on ' + domain + \
        '" property="og:site_name" />\n' + \
        '    <meta property="article:published_time" content="' + \
        published + '" />\n' + \
        '    <meta property="article:modified_time" content="' + \
        modified + '" />\n'

    html_str = \
        html_header_with_external_style(css_filename, instance_title,
                                        og_metadata + blog_markup,
                                        system_language)
    return html_str


def html_footer() -> str:
    html_str = '  </body>\n'
    html_str += '</html>\n'
    return html_str


def load_individual_post_as_html_from_cache(base_dir: str,
                                            nickname: str, domain: str,
                                            post_json_object: {}) -> str:
    """If a cached html version of the given post exists then load it and
    return the html text
    This is much quicker than generating the html from the json object
    """
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain, post_json_object)

    post_html = ''
    if not cached_post_filename:
        return post_html

    if not os.path.isfile(cached_post_filename):
        return post_html

    tries = 0
    while tries < 3:
        try:
            with open(cached_post_filename, 'r', encoding='utf-8') as file:
                post_html = file.read()
                break
        except OSError as ex:
            print('ERROR: load_individual_post_as_html_from_cache ' +
                  str(tries) + ' ' + str(ex))
            # no sleep
            tries += 1
    if post_html:
        return post_html


def add_emoji_to_display_name(session, base_dir: str, http_prefix: str,
                              nickname: str, domain: str,
                              display_name: str, in_profile_name: bool,
                              translate: {}) -> str:
    """Adds emoji icons to display names or CW on individual posts
    """
    if ':' not in display_name:
        return display_name

    display_name = display_name.replace('<p>', '').replace('</p>', '')
    emoji_tags = {}
#    print('TAG: display_name before tags: ' + display_name)
    display_name = \
        add_html_tags(base_dir, http_prefix,
                      nickname, domain, display_name, [],
                      emoji_tags, translate)
    display_name = display_name.replace('<p>', '').replace('</p>', '')
#    print('TAG: display_name after tags: ' + display_name)
    # convert the emoji dictionary to a list
    emoji_tags_list = []
    for _, tag in emoji_tags.items():
        emoji_tags_list.append(tag)
#    print('TAG: emoji tags list: ' + str(emoji_tags_list))
    if not in_profile_name:
        display_name = \
            replace_emoji_from_tags(session, base_dir,
                                    display_name, emoji_tags_list,
                                    'post header', False, False)
    else:
        display_name = \
            replace_emoji_from_tags(session, base_dir,
                                    display_name, emoji_tags_list, 'profile',
                                    False, False)
#    print('TAG: display_name after tags 2: ' + display_name)

    # remove any stray emoji
    while ':' in display_name:
        if '://' in display_name:
            break
        emoji_str = display_name.split(':')[1]
        prev_display_name = display_name
        display_name = display_name.replace(':' + emoji_str + ':', '').strip()
        if prev_display_name == display_name:
            break
#        print('TAG: display_name after tags 3: ' + display_name)
#    print('TAG: display_name after tag replacements: ' + display_name)

    return display_name


def _is_image_mime_type(mime_type: str) -> bool:
    """Is the given mime type an image?
    """
    if mime_type == 'image/svg+xml':
        return True
    if not mime_type.startswith('image/'):
        return False
    extensions = get_image_extensions()
    ext = mime_type.split('/')[1]
    if ext in extensions:
        return True
    return False


def _is_video_mime_type(mime_type: str) -> bool:
    """Is the given mime type a video?
    """
    if not mime_type.startswith('video/'):
        return False
    extensions = get_video_extensions()
    ext = mime_type.split('/')[1]
    if ext in extensions:
        return True
    return False


def _is_audio_mime_type(mime_type: str) -> bool:
    """Is the given mime type an audio file?
    """
    if mime_type == 'audio/mpeg':
        return True
    if not mime_type.startswith('audio/'):
        return False
    extensions = get_audio_extensions()
    ext = mime_type.split('/')[1]
    if ext in extensions:
        return True
    return False


def _is_attached_image(attachment_filename: str) -> bool:
    """Is the given attachment filename an image?
    """
    if '.' not in attachment_filename:
        return False
    image_ext = (
        'png', 'jpg', 'jpeg', 'webp', 'avif', 'heic', 'svg', 'gif', 'jxl'
    )
    ext = attachment_filename.split('.')[-1]
    if ext in image_ext:
        return True
    return False


def _is_attached_video(attachment_filename: str) -> bool:
    """Is the given attachment filename a video?
    """
    if '.' not in attachment_filename:
        return False
    video_ext = (
        'mp4', 'webm', 'ogv'
    )
    ext = attachment_filename.split('.')[-1]
    if ext in video_ext:
        return True
    return False


def _is_nsfw(content: str) -> bool:
    """Does the given content indicate nsfw?
    """
    content_lower = content.lower()
    nsfw_tags = (
        'nsfw', 'porn', 'pr0n', 'explicit', 'lewd',
        'nude', 'boob', 'erotic', 'sex'
    )
    for tag_name in nsfw_tags:
        if tag_name in content_lower:
            return True
    return False


def get_post_attachments_as_html(base_dir: str,
                                 nickname: str, domain: str,
                                 domain_full: str,
                                 post_json_object: {}, box_name: str,
                                 translate: {},
                                 is_muted: bool, avatar_link: str,
                                 reply_str: str, announce_str: str,
                                 like_str: str,
                                 bookmark_str: str, delete_str: str,
                                 mute_str: str,
                                 content: str,
                                 minimize_all_images: bool,
                                 system_language: str) -> (str, str):
    """Returns a string representing any attachments
    """
    attachment_str = ''
    gallery_str = ''
    if not post_json_object['object'].get('attachment'):
        return attachment_str, gallery_str

    if not isinstance(post_json_object['object']['attachment'], list):
        return attachment_str, gallery_str

    attachment_ctr = 0
    attachment_str = ''
    media_style_added = False
    post_id = None
    if post_json_object['object'].get('id'):
        post_id = post_json_object['object']['id']
        post_id = remove_id_ending(post_id).replace('/', '--')

    # chat links
    # https://codeberg.org/fediverse/fep/src/branch/main/fep/1970/fep-1970.md
    for attach in post_json_object['object']['attachment']:
        if not attach.get('type') or \
           not attach.get('name') or \
           not attach.get('href') or \
           not attach.get('rel'):
            continue
        if not isinstance(attach['type'], str) or \
           not isinstance(attach['name'], str) or \
           not isinstance(attach['href'], str) or \
           not isinstance(attach['rel'], str):
            continue
        if attach['type'] != 'Link' or \
           attach['name'] != 'Chat' or \
           attach['rel'] != 'discussion' or \
           '://' not in attach['href'] or \
           '.' not in attach['href']:
            continue
        # get the domain for the chat link
        chat_domain_str = ''
        chat_domain, _ = get_domain_from_actor(attach['href'])
        if chat_domain:
            if local_network_host(chat_domain):
                print('REJECT: local network chat link ' + attach['href'])
                continue
            chat_domain_str = ' (' + chat_domain + ')'
            # avoid displaying very long domains
            if len(chat_domain_str) > 50:
                chat_domain_str = ''
        attachment_str += \
            '<p><a href="' + attach['href'] + \
            '" target="_blank" rel="nofollow noopener noreferrer">' + \
            '💬 ' + translate['Chat'] + chat_domain_str + '</a></p>'

    # obtain transcripts
    transcripts = {}
    for attach in post_json_object['object']['attachment']:
        if not attach.get('mediaType'):
            continue
        if attach['mediaType'] != 'text/vtt':
            continue
        name = None
        if attach.get('name'):
            name = attach['name']
        if attach.get('nameMap'):
            for name_lang, name_value in attach['nameMap'].items():
                if not isinstance(name_value, str):
                    continue
                if name_lang.startswith(system_language):
                    name = name_value
        if not name and attach.get('hreflang'):
            name = attach['hreflang']
        url = None
        if attach.get('url'):
            url = attach['url']
        elif attach.get('href'):
            url = attach['href']
        if name and url:
            transcripts[name] = url

    for attach in post_json_object['object']['attachment']:
        if not (attach.get('mediaType') and attach.get('url')):
            continue
        media_license = ''
        if attach.get('schema:license'):
            if not dangerous_markup(attach['schema:license'], False, []):
                if not is_filtered(base_dir, nickname, domain,
                                   attach['schema:license'],
                                   system_language):
                    if '://' not in attach['schema:license']:
                        if len(attach['schema:license']) < 60:
                            media_license = attach['schema:license']
                    else:
                        media_license = attach['schema:license']
        elif attach.get('license'):
            if not dangerous_markup(attach['license'], False, []):
                if not is_filtered(base_dir, nickname, domain,
                                   attach['license'],
                                   system_language):
                    if '://' not in attach['license']:
                        if len(attach['license']) < 60:
                            media_license = attach['license']
                    else:
                        media_license = attach['license']
        media_creator = ''
        if attach.get('schema:creator'):
            if len(attach['schema:creator']) < 120:
                if not dangerous_markup(attach['schema:creator'], False, []):
                    if not is_filtered(base_dir, nickname, domain,
                                       attach['schema:creator'],
                                       system_language):
                        media_creator = attach['schema:creator']
        elif attach.get('attribution'):
            if isinstance(attach['attribution'], list):
                if len(attach['attribution']) > 0:
                    attrib_str = attach['attribution'][0]
                    if not dangerous_markup(attrib_str, False, []):
                        if not is_filtered(base_dir, nickname, domain,
                                           attrib_str, system_language):
                            media_creator = attrib_str

        media_type = attach['mediaType']
        image_description = ''
        if attach.get('name'):
            image_description = attach['name'].replace('"', "'")
            image_description = remove_html(image_description)
        if _is_image_mime_type(media_type):
            image_url = attach['url']

            # display svg images if they have first been rendered harmless
            svg_harmless = True
            if 'svg' in media_type:
                svg_harmless = False
                if '://' + domain_full + '/' in image_url:
                    svg_harmless = True
                else:
                    if post_id:
                        if '/' in image_url:
                            im_filename = image_url.split('/')[-1]
                        else:
                            im_filename = image_url
                        cached_svg_filename = \
                            base_dir + '/media/' + post_id + '_' + im_filename
                        if os.path.isfile(cached_svg_filename):
                            svg_harmless = True

            if _is_attached_image(attach['url']) and svg_harmless:
                if not attachment_str:
                    attachment_str += '<div class="media">\n'
                    media_style_added = True

                if attachment_ctr > 0:
                    attachment_str += '<br>'
                if box_name == 'tlmedia':
                    gallery_str += '<div class="gallery">\n'
                    if not is_muted:
                        gallery_str += '  <a href="' + image_url + '">\n'
                        if media_license and media_creator:
                            gallery_str += '  <figure>\n'
                        gallery_str += \
                            '    <img loading="lazy" ' + \
                            'decoding="async" src="' + \
                            image_url + '" alt="" title="">\n'
                        gallery_str += '  </a>\n'
                        license_str = ''
                        if media_license and media_creator:
                            if '://' in media_license:
                                license_str += \
                                    '<a href="' + media_license + \
                                    '" target="_blank" ' + \
                                    'rel="nofollow noopener noreferrer">©</a>'
                            else:
                                license_str += media_license
                            license_str += ' ' + media_creator
                            gallery_str += \
                                '   ' + license_str + \
                                '</figcaption></figure>\n'
                    if post_json_object['object'].get('url'):
                        image_post_url = post_json_object['object']['url']
                    else:
                        image_post_url = post_json_object['object']['id']
                    if image_description and not is_muted:
                        gallery_str += \
                            '  <a href="' + image_post_url + \
                            '" class="gallerytext"><div ' + \
                            'class="gallerytext">' + \
                            image_description + '</div></a>\n'
                    else:
                        gallery_str += \
                            '<label class="transparent">---</label><br>'
                    gallery_str += '  <div class="mediaicons">\n'
                    # don't show the announce icon if there is no image
                    # description
                    if not image_description:
                        announce_str = ''
                    gallery_str += \
                        '    ' + reply_str + announce_str + like_str + \
                        bookmark_str + delete_str + mute_str + '\n'
                    gallery_str += '  </div>\n'
                    gallery_str += '  <div class="mediaavatar">\n'
                    gallery_str += '    ' + avatar_link + '\n'
                    gallery_str += '  </div>\n'
                    gallery_str += '</div>\n'

                # optionally hide the image
                attributed_actor = None
                minimize_images = False
                if minimize_all_images:
                    minimize_images = True
                if post_json_object['object'].get('attributedTo'):
                    if isinstance(post_json_object['object']['attributedTo'],
                                  str):
                        attributed_actor = \
                            post_json_object['object']['attributedTo']
                if attributed_actor:
                    following_nickname = \
                        get_nickname_from_actor(attributed_actor)
                    following_domain, _ = \
                        get_domain_from_actor(attributed_actor)
                    if minimize_all_images:
                        minimize_images = True
                    else:
                        minimize_images = \
                            minimizing_attached_images(base_dir,
                                                       nickname, domain,
                                                       following_nickname,
                                                       following_domain)

                # minimize any NSFW images
                if not minimize_images and content:
                    if _is_nsfw(content):
                        minimize_images = True

                if minimize_images:
                    show_img_str = 'SHOW MEDIA'
                    if translate:
                        show_img_str = translate['SHOW MEDIA']
                    attachment_str += \
                        '<details><summary class="cw" tabindex="10">' + \
                        show_img_str + '</summary>' + \
                        '<div id="' + post_id + '">\n'

                attachment_str += \
                    '<a href="' + image_url + '" tabindex="10">'
                if media_license and media_creator:
                    attachment_str += '<figure>'
                attachment_str += \
                    '<img loading="lazy" decoding="async" ' + \
                    'src="' + image_url + \
                    '" alt="' + image_description + '" title="' + \
                    image_description + '" class="attachment"></a>\n'
                if media_license and media_creator:
                    license_str = ''
                    attachment_str += '<figcaption>'
                    if '://' in media_license:
                        license_str += \
                            '<a href="' + media_license + \
                            '" target="_blank" ' + \
                            'rel="nofollow noopener noreferrer">©</a>'
                    else:
                        license_str += media_license
                    license_str += ' ' + media_creator
                    attachment_str += license_str + '</figcaption></figure>'

                if minimize_images:
                    attachment_str += '</div></details>\n'

                attachment_ctr += 1
        elif _is_video_mime_type(media_type):
            if _is_attached_video(attach['url']):
                extension = attach['url'].split('.')[-1]
                if attachment_ctr > 0:
                    attachment_str += '<br>'
                if box_name == 'tlmedia':
                    gallery_str += '<div class="gallery">\n'
                    if not is_muted:
                        gallery_str += \
                            '  <a href="' + attach['url'] + \
                            '" tabindex="10">\n'
                        gallery_str += \
                            '    <figure id="videoContainer" ' + \
                            'data-fullscreen="false">\n' + \
                            '    <video id="video" controls ' + \
                            'preload="metadata" tabindex="10">\n'
                        gallery_str += \
                            '      <source src="' + attach['url'] + \
                            '" alt="' + image_description + \
                            '" title="' + image_description + \
                            '" class="attachment" type="video/' + \
                            extension + '">\n'
                        if transcripts:
                            for transcript_name, transcript_url in \
                              transcripts.items():
                                gallery_str += \
                                    '<track src=”' + transcript_url + \
                                    '” label=”' + transcript_name + \
                                    '” kind=”captions” >\n'
                        idx = 'Your browser does not support the video tag.'
                        gallery_str += translate[idx] + '\n'
                        gallery_str += '    </video>\n'
                        gallery_str += '    </figure>\n'
                        gallery_str += '  </a>\n'
                    if post_json_object['object'].get('url'):
                        video_post_url = post_json_object['object']['url']
                    else:
                        video_post_url = post_json_object['object']['id']
                    if image_description and not is_muted:
                        gallery_str += \
                            '  <a href="' + video_post_url + \
                            '" class="gallerytext" tabindex="10"><div ' + \
                            'class="gallerytext">' + \
                            image_description + '</div></a>\n'
                    else:
                        gallery_str += \
                            '<label class="transparent">---</label><br>'
                    gallery_str += '  <div class="mediaicons">\n'
                    gallery_str += \
                        '    ' + reply_str + announce_str + like_str + \
                        bookmark_str + delete_str + mute_str + '\n'
                    gallery_str += '  </div>\n'
                    gallery_str += '  <div class="mediaavatar">\n'
                    gallery_str += '    ' + avatar_link + '\n'
                    gallery_str += '  </div>\n'
                    gallery_str += '</div>\n'

                attachment_str += \
                    '<center><figure id="videoContainer" ' + \
                    'data-fullscreen="false">\n' + \
                    '    <video id="video" controls ' + \
                    'preload="metadata" tabindex="10">\n'
                attachment_str += \
                    '      <source src="' + attach['url'] + '" alt="' + \
                    image_description + '" title="' + image_description + \
                    '" class="attachment" type="video/' + \
                    extension + '">\n'
                if transcripts:
                    for transcript_name, transcript_url in \
                      transcripts.items():
                        attachment_str += \
                            '      <track src=”' + transcript_url + \
                            '” label=”' + transcript_name + \
                            '” kind=”captions” >\n'
                attachment_str += \
                    translate['Your browser does not support the video tag.']
                attachment_str += '\n    </video></figure></center>'
                attachment_ctr += 1
        elif _is_audio_mime_type(media_type):
            extension = '.mp3'
            if attach['url'].endswith('.ogg'):
                extension = '.ogg'
            elif attach['url'].endswith('.wav'):
                extension = '.wav'
            elif attach['url'].endswith('.opus'):
                extension = '.opus'
            elif attach['url'].endswith('.spx'):
                extension = '.spx'
            elif attach['url'].endswith('.flac'):
                extension = '.flac'
            if attach['url'].endswith(extension):
                if attachment_ctr > 0:
                    attachment_str += '<br>'
                if box_name == 'tlmedia':
                    gallery_str += '<div class="gallery">\n'
                    if not is_muted:
                        gallery_str += \
                            '  <a href="' + attach['url'] + \
                            '" tabindex="10">\n'
                        gallery_str += '    <audio controls tabindex="10">\n'
                        gallery_str += \
                            '      <source src="' + attach['url'] + \
                            '" alt="' + image_description + \
                            '" title="' + image_description + \
                            '" class="attachment" type="audio/' + \
                            extension.replace('.', '') + '">'
                        idx = 'Your browser does not support the audio tag.'
                        gallery_str += translate[idx]
                        gallery_str += '    </audio>\n'
                        gallery_str += '  </a>\n'
                    if post_json_object['object'].get('url'):
                        audio_post_url = post_json_object['object']['url']
                    else:
                        audio_post_url = post_json_object['object']['id']
                    if image_description and not is_muted:
                        gallery_str += \
                            '  <a href="' + audio_post_url + \
                            '" class="gallerytext"><div ' + \
                            'class="gallerytext">' + \
                            image_description + '</div></a>\n'
                    else:
                        gallery_str += \
                            '<label class="transparent">---</label><br>'
                    gallery_str += '  <div class="mediaicons">\n'
                    gallery_str += \
                        '    ' + reply_str + announce_str + \
                        like_str + bookmark_str + \
                        delete_str + mute_str + '\n'
                    gallery_str += '  </div>\n'
                    gallery_str += '  <div class="mediaavatar">\n'
                    gallery_str += '    ' + avatar_link + '\n'
                    gallery_str += '  </div>\n'
                    gallery_str += '</div>\n'

                attachment_str += '<center>\n<audio controls tabindex="10">\n'
                attachment_str += \
                    '<source src="' + attach['url'] + '" alt="' + \
                    image_description + '" title="' + image_description + \
                    '" class="attachment" type="audio/' + \
                    extension.replace('.', '') + '">'
                attachment_str += \
                    translate['Your browser does not support the audio tag.']
                attachment_str += '</audio>\n</center>\n'
                attachment_ctr += 1
    if media_style_added:
        attachment_str += '</div><br>'
    return attachment_str, gallery_str


def html_post_separator(base_dir: str, column: str) -> str:
    """Returns the html for a timeline post separator image
    """
    theme = get_config_param(base_dir, 'theme')
    filename = 'separator.png'
    separator_class = "postSeparatorImage"
    if column:
        separator_class = "postSeparatorImage" + column.title()
        filename = 'separator_' + column + '.png'
    separator_image_filename = \
        base_dir + '/theme/' + theme + '/icons/' + filename
    separator_str = ''
    if os.path.isfile(separator_image_filename):
        separator_str = \
            '<div class="' + separator_class + '"><center>' + \
            '<img src="/icons/' + filename + '" ' + \
            'alt="" /></center></div>\n'
    return separator_str


def html_highlight_label(label: str, highlight: bool) -> str:
    """If the given text should be highlighted then return
    the appropriate markup.
    This is so that in shell browsers, like lynx, it's possible
    to see if the replies or DM button are highlighted.
    """
    if not highlight:
        return label
    return '*' + str(label) + '*'


def get_avatar_image_url(session, base_dir: str, http_prefix: str,
                         post_actor: str, person_cache: {},
                         avatar_url: str, allow_downloads: bool,
                         signing_priv_key_pem: str) -> str:
    """Returns the avatar image url
    """
    # get the avatar image url for the post actor
    if not avatar_url:
        avatar_url = \
            get_person_avatar_url(base_dir, post_actor, person_cache)
        avatar_url = \
            update_avatar_image_cache(signing_priv_key_pem,
                                      session, base_dir, http_prefix,
                                      post_actor, avatar_url, person_cache,
                                      allow_downloads)
    else:
        update_avatar_image_cache(signing_priv_key_pem,
                                  session, base_dir, http_prefix,
                                  post_actor, avatar_url, person_cache,
                                  allow_downloads)

    if not avatar_url:
        avatar_url = post_actor + '/avatar.png'

    return avatar_url


def html_hide_from_screen_reader(html_str: str) -> str:
    """Returns html which is hidden from screen readers
    """
    return '<span aria-hidden="true">' + html_str + '</span>'


def html_keyboard_navigation(banner: str, links: {}, access_keys: {},
                             sub_heading: str = None,
                             users_path: str = None, translate: {} = None,
                             follow_approvals: bool = False) -> str:
    """Given a set of links return the html for keyboard navigation
    """
    html_str = '<div class="transparent"><ul>\n'

    if banner:
        html_str += '<pre aria-label="">\n' + banner + '\n<br><br></pre>\n'

    if sub_heading:
        html_str += '<strong><label class="transparent">' + \
            sub_heading + '</label></strong><br>\n'

    # show new follower approvals
    if users_path and translate and follow_approvals:
        html_str += '<strong><label class="transparent">' + \
            '<a href="' + users_path + '/followers#timeline" ' + \
            'tabindex="-1">' + \
            translate['Approve follow requests'] + '</a>' + \
            '</label></strong><br><br>\n'

    # show the list of links
    for title, url in links.items():
        access_key_str = ''
        if access_keys.get(title):
            access_key_str = 'accesskey="' + access_keys[title] + '"'

        html_str += '<li><label class="transparent">' + \
            '<a href="' + str(url) + '" ' + access_key_str + \
            ' tabindex="-1">' + \
            str(title) + '</a></label></li>\n'
    html_str += '</ul></div>\n'
    return html_str


def begin_edit_section(label: str) -> str:
    """returns the html for begining a dropdown section on edit profile screen
    """
    return \
        '    <details><summary class="cw">' + label + '</summary>\n' + \
        '<div class="container">'


def end_edit_section() -> str:
    """returns the html for ending a dropdown section on edit profile screen
    """
    return '    </div></details>\n'


def edit_text_field(label: str, name: str, value: str = "",
                    placeholder: str = "", required: bool = False) -> str:
    """Returns html for editing a text field
    """
    if value is None:
        value = ''
    placeholder_str = ''
    if placeholder:
        placeholder_str = ' placeholder="' + placeholder + '"'
    required_str = ''
    if required:
        required_str = ' required'
    text_field_str = ''
    if label:
        text_field_str = \
            '<label class="labels">' + label + '</label><br>\n'
    text_field_str += \
        '      <input type="text" name="' + name + '" value="' + \
        value + '"' + placeholder_str + required_str + '>\n'
    return text_field_str


def edit_number_field(label: str, name: str, value: int,
                      min_value: int, max_value: int,
                      placeholder: int) -> str:
    """Returns html for editing an integer number field
    """
    if value is None:
        value = ''
    placeholder_str = ''
    if placeholder:
        placeholder_str = ' placeholder="' + str(placeholder) + '"'
    return \
        '<label class="labels">' + label + '</label><br>\n' + \
        '      <input type="number" name="' + name + '" value="' + \
        str(value) + '"' + placeholder_str + ' ' + \
        'min="' + str(min_value) + '" max="' + str(max_value) + '" step="1">\n'


def edit_currency_field(label: str, name: str, value: str,
                        placeholder: str, required: bool) -> str:
    """Returns html for editing a currency field
    """
    if value is None:
        value = '0.00'
    placeholder_str = ''
    if placeholder:
        if placeholder.isdigit():
            placeholder_str = ' placeholder="' + str(placeholder) + '"'
    required_str = ''
    if required:
        required_str = ' required'
    return \
        '<label class="labels">' + label + '</label><br>\n' + \
        '      <input type="text" name="' + name + '" value="' + \
        str(value) + '"' + placeholder_str + ' ' + \
        ' pattern="^\\d{1,3}(,\\d{3})*(\\.\\d+)?" data-type="currency"' + \
        required_str + '>\n'


def edit_check_box(label: str, name: str, checked: bool) -> str:
    """Returns html for editing a checkbox field
    """
    checked_str = ''
    if checked:
        checked_str = ' checked'

    return \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="' + name + '"' + checked_str + '> ' + label + '<br>\n'


def edit_text_area(label: str, subtitle: str, name: str, value: str,
                   height: int, placeholder: str, spellcheck: bool) -> str:
    """Returns html for editing a textarea field
    """
    if value is None:
        value = ''
    text = ''
    if label:
        text = '<label class="labels">' + label + '</label><br>\n'
        if subtitle:
            text += subtitle + '<br>\n'
    text += \
        '      <textarea id="message" placeholder=' + \
        '"' + placeholder + '" '
    text += 'name="' + name + '" '
    text += 'style="height:' + str(height) + 'px" '
    text += 'spellcheck="' + str(spellcheck).lower() + '">'
    text += value + '</textarea>\n'
    return text


def html_search_result_share(base_dir: str, shared_item: {}, translate: {},
                             http_prefix: str, domain_full: str,
                             contact_nickname: str, item_id: str,
                             actor: str, shares_file_type: str,
                             category: str) -> str:
    """Returns the html for an individual shared item
    """
    shared_items_form = '<div class="container">\n'
    shared_items_form += \
        '<p class="share-title">' + shared_item['displayName'] + '</p>\n'
    if shared_item.get('imageUrl'):
        shared_items_form += \
            '<a href="' + shared_item['imageUrl'] + '">\n'
        shared_items_form += \
            '<img loading="lazy" decoding="async" ' + \
            'src="' + shared_item['imageUrl'] + \
            '" alt="Item image"></a>\n'
    shared_items_form += '<p>' + shared_item['summary'] + '</p>\n<p>'
    if shared_item.get('itemQty'):
        if shared_item['itemQty'] > 1:
            shared_items_form += \
                '<b>' + translate['Quantity'] + \
                ':</b> ' + str(shared_item['itemQty']) + '<br>'
    shared_items_form += \
        '<b>' + translate['Type'] + ':</b> ' + shared_item['itemType'] + '<br>'
    shared_items_form += \
        '<b>' + translate['Category'] + ':</b> ' + \
        shared_item['category'] + '<br>'
    if shared_item.get('location'):
        shared_items_form += \
            '<b>' + translate['Location'] + ':</b> ' + \
            shared_item['location'] + '<br>'
    contact_title_str = translate['Contact']
    if shared_item.get('itemPrice') and \
       shared_item.get('itemCurrency'):
        if is_float(shared_item['itemPrice']):
            if float(shared_item['itemPrice']) > 0:
                shared_items_form += \
                    ' <b>' + translate['Price'] + \
                    ':</b> ' + shared_item['itemPrice'] + \
                    ' ' + shared_item['itemCurrency']
                contact_title_str = translate['Buy']
    shared_items_form += '</p>\n'
    contact_actor = \
        local_actor_url(http_prefix, contact_nickname, domain_full)
    button_style_str = 'button'
    if category == 'accommodation':
        contact_title_str = translate['Request to stay']
        button_style_str = 'contactbutton'

    shared_items_form += \
        '<p>' + \
        '<a href="' + actor + '?replydm=sharedesc:' + \
        shared_item['displayName'] + '?mention=' + contact_actor + \
        '?category=' + category + \
        '"><button class="' + button_style_str + '">' + contact_title_str + \
        '</button></a>\n' + \
        '<a href="' + contact_actor + '"><button class="button">' + \
        translate['Profile'] + '</button></a>\n'

    # should the remove button be shown?
    show_remove_button = False
    nickname = get_nickname_from_actor(actor)
    if not nickname:
        return ''
    if actor.endswith('/users/' + contact_nickname):
        show_remove_button = True
    elif is_moderator(base_dir, nickname):
        show_remove_button = True
    else:
        admin_nickname = get_config_param(base_dir, 'admin')
        if admin_nickname:
            if actor.endswith('/users/' + admin_nickname):
                show_remove_button = True

    if show_remove_button:
        if shares_file_type == 'shares':
            shared_items_form += \
                ' <a href="' + actor + '?rmshare=' + \
                item_id + '"><button class="button">' + \
                translate['Remove'] + '</button></a>\n'
        else:
            shared_items_form += \
                ' <a href="' + actor + '?rmwanted=' + \
                item_id + '"><button class="button">' + \
                translate['Remove'] + '</button></a>\n'
    shared_items_form += '</p></div>\n'
    return shared_items_form


def html_show_share(base_dir: str, domain: str, nickname: str,
                    http_prefix: str, domain_full: str,
                    item_id: str, translate: {},
                    shared_items_federated_domains: [],
                    default_timeline: str, theme: str,
                    shares_file_type: str, category: str) -> str:
    """Shows an individual shared item after selecting it from the left column
    """
    shares_json = None

    share_url = item_id.replace('___', '://').replace('--', '/')
    contact_nickname = get_nickname_from_actor(share_url)
    if not contact_nickname:
        return None

    if '://' + domain_full + '/' in share_url:
        # shared item on this instance
        shares_filename = \
            acct_dir(base_dir, contact_nickname, domain) + '/' + \
            shares_file_type + '.json'
        if not os.path.isfile(shares_filename):
            return None
        shares_json = load_json(shares_filename)
    else:
        # federated shared item
        if shares_file_type == 'shares':
            catalogs_dir = base_dir + '/cache/catalogs'
        else:
            catalogs_dir = base_dir + '/cache/wantedItems'
        if not os.path.isdir(catalogs_dir):
            return None
        for _, _, files in os.walk(catalogs_dir):
            for fname in files:
                if '#' in fname:
                    continue
                if not fname.endswith('.' + shares_file_type + '.json'):
                    continue
                federated_domain = fname.split('.')[0]
                if federated_domain not in shared_items_federated_domains:
                    continue
                shares_filename = catalogs_dir + '/' + fname
                shares_json = load_json(shares_filename)
                if not shares_json:
                    continue
                if shares_json.get(item_id):
                    break
            break

    if not shares_json:
        return None
    if not shares_json.get(item_id):
        return None
    shared_item = shares_json[item_id]
    actor = local_actor_url(http_prefix, nickname, domain_full)

    # filename of the banner shown at the top
    banner_file, _ = \
        get_banner_file(base_dir, nickname, domain, theme)

    share_str = \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + \
        default_timeline + '" title="" alt="">\n'
    share_str += '<img loading="lazy" decoding="async" ' + \
        'class="timeline-banner" alt="" ' + \
        'src="/users/' + nickname + '/' + banner_file + '" /></a>\n' + \
        '</header><br>\n'
    share_str += \
        html_search_result_share(base_dir, shared_item, translate, http_prefix,
                                 domain_full, contact_nickname, item_id,
                                 actor, shares_file_type, category)

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'
    instance_title = \
        get_config_param(base_dir, 'instanceTitle')

    return html_header_with_external_style(css_filename,
                                           instance_title, None) + \
        share_str + html_footer()


def set_custom_background(base_dir: str, background: str,
                          new_background: str) -> str:
    """Sets a custom background
    Returns the extension, if found
    """
    ext = 'jpg'
    if os.path.isfile(base_dir + '/img/' + background + '.' + ext):
        if not new_background:
            new_background = background
        if not os.path.isfile(base_dir + '/accounts/' +
                              new_background + '.' + ext):
            copyfile(base_dir + '/img/' + background + '.' + ext,
                     base_dir + '/accounts/' + new_background + '.' + ext)
        return ext
    return None


def html_common_emoji(base_dir: str, no_of_emoji: int) -> str:
    """Shows common emoji
    """
    emojis_filename = base_dir + '/emoji/emoji.json'
    if not os.path.isfile(emojis_filename):
        emojis_filename = base_dir + '/emoji/default_emoji.json'
    emojis_json = load_json(emojis_filename)

    common_emoji_filename = base_dir + '/accounts/common_emoji.txt'
    if not os.path.isfile(common_emoji_filename):
        return ''
    common_emoji = None
    try:
        with open(common_emoji_filename, 'r', encoding='utf-8') as fp_emoji:
            common_emoji = fp_emoji.readlines()
    except OSError:
        print('EX: html_common_emoji unable to load file')
        return ''
    if not common_emoji:
        return ''
    line_ctr = 0
    ctr = 0
    html_str = ''
    while ctr < no_of_emoji and line_ctr < len(common_emoji):
        emoji_name1 = common_emoji[line_ctr].split(' ')[1]
        emoji_name = remove_eol(emoji_name1)
        emoji_icon_name = emoji_name
        emoji_filename = base_dir + '/emoji/' + emoji_name + '.png'
        if not os.path.isfile(emoji_filename):
            emoji_filename = base_dir + '/customemoji/' + emoji_name + '.png'
            if not os.path.isfile(emoji_filename):
                # load the emojis index
                if not emojis_json:
                    emojis_json = load_json(emojis_filename)
                # lookup the name within the index to get the hex code
                if emojis_json:
                    for emoji_tag, emoji_code in emojis_json.items():
                        if emoji_tag == emoji_name:
                            # get the filename based on the hex code
                            emoji_filename = \
                                base_dir + '/emoji/' + emoji_code + '.png'
                            emoji_icon_name = emoji_code
                            break
        if os.path.isfile(emoji_filename):
            # NOTE: deliberately no alt text, so that without graphics only
            # the emoji name shows
            html_str += \
                '<label class="hashtagswarm">' + \
                '<img id="commonemojilabel" ' + \
                'loading="lazy" decoding="async" ' + \
                'src="/emoji/' + emoji_icon_name + '.png" ' + \
                'alt="" title="">' + \
                ':' + emoji_name + ':</label>\n'
            ctr += 1
        line_ctr += 1
    return html_str


def text_mode_browser(ua_str: str) -> bool:
    """Does the user agent indicate a text mode browser?
    """
    if ua_str:
        text_mode_agents = ('Lynx/', 'w3m/', 'Links (', 'Emacs/', 'ELinks')
        for agent in text_mode_agents:
            if agent in ua_str:
                return True
    return False


def language_right_to_left(language: str) -> bool:
    """is the given language written from right to left?
    """
    rtl_languages = ('ar', 'fa')
    if language in rtl_languages:
        return True
    return False


def get_default_path(media_instance: bool, blogs_instance: bool,
                     nickname: str) -> str:
    """Returns the default timeline
    """
    if blogs_instance:
        path = '/users/' + nickname + '/tlblogs'
    elif media_instance:
        path = '/users/' + nickname + '/tlmedia'
    else:
        path = '/users/' + nickname + '/inbox'
    return path


def html_following_data_list(base_dir: str, nickname: str,
                             domain: str, domain_full: str,
                             following_type: str,
                             use_petnames: bool) -> str:
    """Returns a datalist of handles being followed
    followingHandles, followersHandles
    """
    list_str = '<datalist id="' + following_type + 'Handles">\n'
    following_filename = \
        acct_dir(base_dir, nickname, domain) + '/' + following_type + '.txt'
    msg = None
    if os.path.isfile(following_filename):
        with open(following_filename, 'r',
                  encoding='utf-8') as following_file:
            msg = following_file.read()
            # add your own handle, so that you can send DMs
            # to yourself as reminders
            msg += nickname + '@' + domain_full + '\n'
    if msg:
        # include petnames
        petnames_filename = \
            acct_dir(base_dir, nickname, domain) + '/petnames.txt'
        if use_petnames and os.path.isfile(petnames_filename):
            following_list = []
            with open(petnames_filename, 'r',
                      encoding='utf-8') as petnames_file:
                pet_str = petnames_file.read()
                # extract each petname and append it
                petnames_list = pet_str.split('\n')
                for pet in petnames_list:
                    following_list.append(pet.split(' ')[0])
            # add the following.txt entries
            following_list += msg.split('\n')
        else:
            # no petnames list exists - just use following.txt
            following_list = msg.split('\n')
        following_list.sort()
        if following_list:
            for following_address in following_list:
                if not following_address:
                    continue
                if '@' not in following_address and \
                   '://' not in following_address:
                    continue
                list_str += '<option>@' + following_address + '</option>\n'
    list_str += '</datalist>\n'
    return list_str


def html_following_dropdown(base_dir: str, nickname: str,
                            domain: str, domain_full: str,
                            following_type: str,
                            use_petnames: bool) -> str:
    """Returns a select list of handles being followed or of followers
    """
    list_str = '<select name="searchtext">\n'
    following_filename = \
        acct_dir(base_dir, nickname, domain) + '/' + following_type + '.txt'
    msg = None
    if os.path.isfile(following_filename):
        with open(following_filename, 'r',
                  encoding='utf-8') as following_file:
            msg = following_file.read()
            # add your own handle, so that you can send DMs
            # to yourself as reminders
            msg += nickname + '@' + domain_full + '\n'
    if msg:
        # include petnames
        petnames_filename = \
            acct_dir(base_dir, nickname, domain) + '/petnames.txt'
        if use_petnames and os.path.isfile(petnames_filename):
            following_list = []
            with open(petnames_filename, 'r',
                      encoding='utf-8') as petnames_file:
                pet_str = petnames_file.read()
                # extract each petname and append it
                petnames_list = pet_str.split('\n')
                for pet in petnames_list:
                    following_list.append(pet.split(' ')[0])
            # add the following.txt entries
            following_list += msg.split('\n')
        else:
            # no petnames list exists - just use following.txt
            following_list = msg.split('\n')
        list_str += '<option value="" selected></option>\n'
        if following_list:
            domain_sorted_list = []
            for following_address in following_list:
                if '@' not in following_address and \
                   '://' not in following_address:
                    continue
                foll_nick = get_nickname_from_actor(following_address)
                foll_domain, _ = get_domain_from_actor(following_address)
                if not foll_domain or not foll_nick:
                    continue
                domain_sorted_list.append(foll_domain + ' ' +
                                          foll_nick + '@' + foll_domain)
            domain_sorted_list.sort()

            prev_foll_domain = ''
            for following_line in domain_sorted_list:
                following_address = following_line.split(' ')[1]
                foll_domain, _ = get_domain_from_actor(following_address)
                if prev_foll_domain and prev_foll_domain != foll_domain:
                    list_str += '<option value="" disabled></option>\n'
                prev_foll_domain = foll_domain
                list_str += '<option value="' + following_address + '">' + \
                    following_address + '</option>\n'
    list_str += '</select>\n'
    return list_str


def get_buy_links(post_json_object: str, translate: {}, buy_sites: {}) -> {}:
    """Returns any links to buy something from an external site
    """
    if not post_json_object['object'].get('attachment'):
        return {}
    if not isinstance(post_json_object['object']['attachment'], list):
        return {}
    links = {}
    buy_strings = []
    for buy_str in ('Buy', 'Purchase', 'Subscribe'):
        if translate.get(buy_str):
            buy_str = translate[buy_str]
        buy_strings += buy_str.lower()
    buy_strings += ('Paypal', 'Stripe', 'Cashapp', 'Venmo')
    for item in post_json_object['object']['attachment']:
        if not isinstance(item, dict):
            continue
        if not item.get('name'):
            continue
        if not isinstance(item['name'], str):
            continue
        if not item.get('type'):
            continue
        if not item.get('href'):
            continue
        if not isinstance(item['type'], str):
            continue
        if not isinstance(item['href'], str):
            continue
        if item['type'] != 'Link':
            continue
        if not item.get('mediaType'):
            continue
        if not isinstance(item['mediaType'], str):
            continue
        if 'html' not in item['mediaType']:
            continue
        item_name = item['name']
        # The name should not be excessively long
        if len(item_name) > 32:
            continue
        # there should be no html in the name
        if remove_html(item_name) != item_name:
            continue
        # there should be no html in the link
        if '<' in item['href'] or \
           '://' not in item['href'] or \
           ' ' in item['href']:
            continue
        if item.get('rel'):
            if isinstance(item['rel'], str):
                if item['rel'] in ('payment', 'pay', 'donate', 'donation',
                                   'buy', 'purchase'):
                    links[item_name] = item['href']
                    continue
        if buy_sites:
            # limited to an allowlist of buying sites
            for site, buy_domain in buy_sites.items():
                if buy_domain in item['href']:
                    links[site.title()] = item['href']
                    continue
        else:
            # The name only needs to indicate that this is a buy link
            for buy_str in buy_strings:
                if buy_str in item_name.lower():
                    links[item_name] = item['href']
                    continue
    return links


def load_buy_sites(base_dir: str) -> {}:
    """Loads domains from which buying is permitted
    """
    buy_sites_filename = base_dir + '/accounts/buy_sites.json'
    if os.path.isfile(buy_sites_filename):
        buy_sites_json = load_json(buy_sites_filename)
        if buy_sites_json:
            return buy_sites_json
    return {}
