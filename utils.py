__filename__ = "utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import re
import time
import shutil
import datetime
import json
import idna
import locale
from dateutil.tz import tz
from pprint import pprint
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from followingCalendar import add_person_to_calendar

VALID_HASHTAG_CHARS = \
    set('_0123456789' +
        'abcdefghijklmnopqrstuvwxyz' +
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
        '¡¿ÄäÀàÁáÂâÃãÅåǍǎĄąĂăÆæĀā' +
        'ÇçĆćĈĉČčĎđĐďðÈèÉéÊêËëĚěĘęĖėĒē' +
        'ĜĝĢģĞğĤĥÌìÍíÎîÏïıĪīĮįĴĵĶķ' +
        'ĹĺĻļŁłĽľĿŀÑñŃńŇňŅņÖöÒòÓóÔôÕõŐőØøŒœ' +
        'ŔŕŘřẞßŚśŜŝŞşŠšȘșŤťŢţÞþȚțÜüÙùÚúÛûŰűŨũŲųŮůŪū' +
        'ŴŵÝýŸÿŶŷŹźŽžŻż')

# posts containing these strings will always get screened out,
# both incoming and outgoing.
# Could include dubious clacks or admin dogwhistles
INVALID_CHARACTERS = (
    '卐', '卍', '࿕', '࿖', '࿗', '࿘', 'ϟϟ', '🏳️‍🌈🚫', '⚡⚡', '​'
)

INVALID_ACTOR_URL_CHARACTERS = (
    ' ', '​', '<', '>', '%', '{', '}', '|', '\\', '^', '`',
    '?', '#', '[', ']', '!', '$', '&', "'", '(', ')', '*',
    '+', ',', ';', '='
)


def _standardize_text_range(text: str,
                            range_start: int, range_end: int,
                            offset: str) -> str:
    """Convert any fancy characters within the given range into ordinary ones
    """
    offset = ord(offset)
    ctr = 0
    text = list(text)
    while ctr < len(text):
        val = ord(text[ctr])
        if val in range(range_start, range_end):
            text[ctr] = chr(val - range_start + offset)
        ctr += 1
    return "".join(text)


def standardize_text(text: str) -> str:
    """Converts fancy unicode text to ordinary letters
    """
    if not text:
        return text

    char_ranges = (
        [65345, 'a'],
        [119886, 'a'],
        [119990, 'a'],
        [120042, 'a'],
        [120094, 'a'],
        [120146, 'a'],
        [120198, 'a'],
        [120302, 'a'],
        [120354, 'a'],
        [120406, 'a'],
        [65313, 'A'],
        [119912, 'A'],
        [119964, 'A'],
        [120016, 'A'],
        [120068, 'A'],
        [120120, 'A'],
        [120172, 'A'],
        [120224, 'A'],
        [120328, 'A'],
        [120380, 'A'],
        [120432, 'A'],
        [127344, 'A'],
        [127312, 'A'],
        [127280, 'A'],
        [127248, 'A']
    )
    for char_range in char_ranges:
        range_start = char_range[0]
        range_end = range_start + 26
        offset = char_range[1]
        text = _standardize_text_range(text, range_start, range_end, offset)

    return text


def remove_eol(line: str):
    """Removes line ending characters
    """
    return line.replace('\n', '').replace('\r', '')


def text_in_file(text: str, filename: str,
                 case_sensitive: bool = True) -> bool:
    """is the given text in the given file?
    """
    if not case_sensitive:
        text = text.lower()
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            if content:
                if not case_sensitive:
                    content = content.lower()
                if text in content:
                    return True
    except OSError:
        print('EX: unable to find text in missing file ' + filename)
    return False


def local_actor_url(http_prefix: str, nickname: str, domain_full: str) -> str:
    """Returns the url for an actor on this instance
    """
    return http_prefix + '://' + domain_full + '/users/' + nickname


def get_actor_languages_list(actor_json: {}) -> []:
    """Returns a list containing languages used by the given actor
    """
    if not actor_json.get('attachment'):
        return []
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not name_value.lower().startswith('languages'):
            continue
        if not property_value.get('type'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        if isinstance(property_value[prop_value_name], list):
            lang_list = property_value[prop_value_name]
            lang_list.sort()
            return lang_list
        if isinstance(property_value[prop_value_name], str):
            lang_str = property_value[prop_value_name]
            lang_list_temp = []
            if ',' in lang_str:
                lang_list_temp = lang_str.split(',')
            elif ';' in lang_str:
                lang_list_temp = lang_str.split(';')
            elif '/' in lang_str:
                lang_list_temp = lang_str.split('/')
            elif '+' in lang_str:
                lang_list_temp = lang_str.split('+')
            elif ' ' in lang_str:
                lang_list_temp = lang_str.split(' ')
            else:
                return [lang_str]
            lang_list = []
            for lang in lang_list_temp:
                lang = lang.strip()
                if lang not in lang_list:
                    lang_list.append(lang)
            lang_list.sort()
            return lang_list
    return []


def has_object_dict(post_json_object: {}) -> bool:
    """Returns true if the given post has an object dict
    """
    if post_json_object.get('object'):
        if isinstance(post_json_object['object'], dict):
            return True
    return False


def remove_markup_tag(html: str, tag: str) -> str:
    """Remove the given tag from the given html markup
    """
    if '<' + tag not in html:
        return html

    section = html.split('<' + tag)
    result = ''
    for text in section:
        if not result:
            if html.startswith('<' + tag) and '>' in text:
                result = text.split('>', 1)[1]
            else:
                result = text
            continue
        result += text.split('>', 1)[1]

    html = result
    section = html.split('</' + tag)
    result = ''
    for text in section:
        if not result:
            if html.startswith('</' + tag) and '>' in text:
                result = text.split('>', 1)[1]
            else:
                result = text
            continue
        result += text.split('>', 1)[1]

    return result


def get_content_from_post(post_json_object: {}, system_language: str,
                          languages_understood: [],
                          content_type: str = "content") -> str:
    """Returns the content from the post in the given language
    including searching for a matching entry within contentMap
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    map_dict = content_type + 'Map'
    if not this_post_json.get(content_type) and \
       not this_post_json.get(map_dict):
        return ''
    content = ''
    map_dict = content_type + 'Map'
    if this_post_json.get(map_dict):
        if isinstance(this_post_json[map_dict], dict):
            if this_post_json[map_dict].get(system_language):
                sys_lang = this_post_json[map_dict][system_language]
                if isinstance(sys_lang, str):
                    content = sys_lang
                    content = remove_markup_tag(content, 'pre')
                    content = content.replace('&amp;', '&')
                    return standardize_text(content)
            else:
                # is there a contentMap/summaryMap entry for one of
                # the understood languages?
                for lang in languages_understood:
                    if this_post_json[map_dict].get(lang):
                        map_lang = this_post_json[map_dict][lang]
                        if isinstance(map_lang, str):
                            content = map_lang
                            content = remove_markup_tag(content, 'pre')
                            content = content.replace('&amp;', '&')
                            return standardize_text(content)
    else:
        if isinstance(this_post_json[content_type], str):
            content = this_post_json[content_type]
            content = content.replace('&amp;', '&')
            content = remove_markup_tag(content, 'pre')
    return standardize_text(content)


def get_language_from_post(post_json_object: {}, system_language: str,
                           languages_understood: [],
                           content_type: str = "content") -> str:
    """Returns the content language from the post
    including searching for a matching entry within contentMap
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    if not this_post_json.get(content_type):
        return system_language
    map_dict = content_type + 'Map'
    if this_post_json.get(map_dict):
        if isinstance(this_post_json[map_dict], dict):
            if this_post_json[map_dict].get(system_language):
                sys_lang = this_post_json[map_dict][system_language]
                if isinstance(sys_lang, str):
                    return system_language
            else:
                # is there a contentMap/summaryMap entry for one of
                # the understood languages?
                for lang in languages_understood:
                    if this_post_json[map_dict].get(lang):
                        return lang
    return system_language


def get_media_descriptions_from_post(post_json_object: {}) -> str:
    """Returns all attached media descriptions as a single text.
    This is used for filtering
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    if not this_post_json.get('attachment'):
        return ''
    descriptions = ''
    for attach in this_post_json['attachment']:
        if not attach.get('name'):
            continue
        descriptions += attach['name'] + ' '
        if attach.get('url'):
            descriptions += attach['url'] + ' '
    return descriptions.strip()


def get_summary_from_post(post_json_object: {}, system_language: str,
                          languages_understood: []) -> str:
    """Returns the summary from the post in the given language
    including searching for a matching entry within summaryMap
    """
    return get_content_from_post(post_json_object, system_language,
                                 languages_understood, "summary")


def get_base_content_from_post(post_json_object: {},
                               system_language: str) -> str:
    """Returns the content from the post in the given language
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    if 'content' not in this_post_json:
        return ''
    return this_post_json['content']


def acct_dir(base_dir: str, nickname: str, domain: str) -> str:
    return base_dir + '/accounts/' + nickname + '@' + domain


def acct_handle_dir(base_dir: str, handle: str) -> str:
    return base_dir + '/accounts/' + handle


def is_featured_writer(base_dir: str, nickname: str, domain: str) -> bool:
    """Is the given account a featured writer, appearing in the features
    timeline on news instances?
    """
    features_blocked_filename = \
        acct_dir(base_dir, nickname, domain) + '/.nofeatures'
    return not os.path.isfile(features_blocked_filename)


def refresh_newswire(base_dir: str):
    """Causes the newswire to be updates after a change to user accounts
    """
    refresh_newswire_filename = base_dir + '/accounts/.refresh_newswire'
    if os.path.isfile(refresh_newswire_filename):
        return
    with open(refresh_newswire_filename, 'w+',
              encoding='utf-8') as refresh_file:
        refresh_file.write('\n')


def get_sha_256(msg: str):
    """Returns a SHA256 hash of the given string
    """
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(msg)
    return digest.finalize()


def get_sha_512(msg: str):
    """Returns a SHA512 hash of the given string
    """
    digest = hashes.Hash(hashes.SHA512(), backend=default_backend())
    digest.update(msg)
    return digest.finalize()


def local_network_host(host: str) -> bool:
    """Returns true if the given host is on the local network
    """
    if host.startswith('localhost') or \
       host.startswith('192.') or \
       host.startswith('127.') or \
       host.startswith('10.'):
        return True
    return False


def decoded_host(host: str) -> str:
    """Convert hostname to internationalized domain
    https://en.wikipedia.org/wiki/Internationalized_domain_name
    """
    if ':' not in host:
        # eg. mydomain:8000
        if not local_network_host(host):
            if not host.endswith('.onion'):
                if not host.endswith('.i2p'):
                    return idna.decode(host)
    return host


def get_locked_account(actor_json: {}) -> bool:
    """Returns whether the given account requires follower approval
    """
    if not actor_json.get('manuallyApprovesFollowers'):
        return False
    if actor_json['manuallyApprovesFollowers'] is True:
        return True
    return False


def has_users_path(path_str: str) -> bool:
    """Whether there is a /users/ path (or equivalent) in the given string
    """
    users_list = get_user_paths()
    for users_str in users_list:
        if users_str in path_str:
            return True
    if '://' in path_str:
        domain = path_str.split('://')[1]
        if '/' in domain:
            domain = domain.split('/')[0]
        if '://' + domain + '/' not in path_str:
            return False
        nickname = path_str.split('://' + domain + '/')[1]
        if '/' in nickname or '.' in nickname:
            return False
        return True
    return False


def valid_post_date(published: str, max_age_days: int, debug: bool) -> bool:
    """Returns true if the published date is recent and is not in the future
    """
    baseline_time = datetime.datetime(1970, 1, 1)

    days_diff = datetime.datetime.utcnow() - baseline_time
    now_days_since_epoch = days_diff.days

    try:
        post_time_object = \
            datetime.datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
    except BaseException:
        if debug:
            print('EX: valid_post_date invalid published date ' +
                  str(published))
        return False

    days_diff = post_time_object - baseline_time
    post_days_since_epoch = days_diff.days

    if post_days_since_epoch > now_days_since_epoch:
        if debug:
            print("Inbox post has a published date in the future!")
        return False

    if now_days_since_epoch - post_days_since_epoch >= max_age_days:
        if debug:
            print("Inbox post is not recent enough")
        return False
    return True


def get_full_domain(domain: str, port: int) -> str:
    """Returns the full domain name, including port number
    """
    if not port:
        return domain
    if ':' in domain:
        return domain
    if port in (80, 443):
        return domain
    return domain + ':' + str(port)


def is_dormant(base_dir: str, nickname: str, domain: str, actor: str,
               dormant_months: int) -> bool:
    """Is the given followed actor dormant, from the standpoint
    of the given account
    """
    last_seen_filename = acct_dir(base_dir, nickname, domain) + \
        '/lastseen/' + actor.replace('/', '#') + '.txt'

    if not os.path.isfile(last_seen_filename):
        return False

    days_since_epoch_str = None
    try:
        with open(last_seen_filename, 'r',
                  encoding='utf-8') as last_seen_file:
            days_since_epoch_str = last_seen_file.read()
    except OSError:
        print('EX: failed to read last seen ' + last_seen_filename)
        return False

    if days_since_epoch_str:
        days_since_epoch = int(days_since_epoch_str)
        curr_time = datetime.datetime.utcnow()
        curr_days_since_epoch = \
            (curr_time - datetime.datetime(1970, 1, 1)).days
        time_diff_months = \
            int((curr_days_since_epoch - days_since_epoch) / 30)
        if time_diff_months >= dormant_months:
            return True
    return False


def is_editor(base_dir: str, nickname: str) -> bool:
    """Returns true if the given nickname is an editor
    """
    editors_file = base_dir + '/accounts/editors.txt'

    if not os.path.isfile(editors_file):
        admin_name = get_config_param(base_dir, 'admin')
        if admin_name:
            if admin_name == nickname:
                return True
        return False

    with open(editors_file, 'r', encoding='utf-8') as editors:
        lines = editors.readlines()
        if len(lines) == 0:
            admin_name = get_config_param(base_dir, 'admin')
            if admin_name:
                if admin_name == nickname:
                    return True
        for editor in lines:
            editor = editor.strip('\n').strip('\r')
            if editor == nickname:
                return True
    return False


def is_artist(base_dir: str, nickname: str) -> bool:
    """Returns true if the given nickname is an artist
    """
    artists_file = base_dir + '/accounts/artists.txt'

    if not os.path.isfile(artists_file):
        admin_name = get_config_param(base_dir, 'admin')
        if admin_name:
            if admin_name == nickname:
                return True
        return False

    with open(artists_file, 'r', encoding='utf-8') as artists:
        lines = artists.readlines()
        if len(lines) == 0:
            admin_name = get_config_param(base_dir, 'admin')
            if admin_name:
                if admin_name == nickname:
                    return True
        for artist in lines:
            artist = artist.strip('\n').strip('\r')
            if artist == nickname:
                return True
    return False


def get_video_extensions() -> []:
    """Returns a list of the possible video file extensions
    """
    return ('mp4', 'webm', 'ogv')


def get_audio_extensions() -> []:
    """Returns a list of the possible audio file extensions
    """
    return ('mp3', 'ogg', 'flac', 'opus', 'spx', 'wav')


def get_image_extensions() -> []:
    """Returns a list of the possible image file extensions
    """
    return ('jpg', 'jpeg', 'gif', 'webp', 'avif', 'heic',
            'svg', 'ico', 'jxl', 'png')


def get_image_mime_type(image_filename: str) -> str:
    """Returns the mime type for the given image
    """
    extensions_to_mime = {
        'png': 'png',
        'jpg': 'jpeg',
        'jxl': 'jxl',
        'gif': 'gif',
        'avif': 'avif',
        'heic': 'heic',
        'svg': 'svg+xml',
        'webp': 'webp',
        'ico': 'x-icon'
    }
    for ext, mime_ext in extensions_to_mime.items():
        if image_filename.endswith('.' + ext):
            return 'image/' + mime_ext
    return 'image/png'


def get_image_extension_from_mime_type(content_type: str) -> str:
    """Returns the image extension from a mime type, such as image/jpeg
    """
    image_media = {
        'png': 'png',
        'jpeg': 'jpg',
        'jxl': 'jxl',
        'gif': 'gif',
        'svg+xml': 'svg',
        'webp': 'webp',
        'avif': 'avif',
        'heic': 'heic',
        'x-icon': 'ico'
    }
    for mime_ext, ext in image_media.items():
        if content_type.endswith(mime_ext):
            return ext
    return 'png'


def get_media_extensions() -> []:
    """Returns a list of the possible media file extensions
    """
    return get_image_extensions() + \
        get_video_extensions() + get_audio_extensions()


def get_image_formats() -> str:
    """Returns a string of permissable image formats
    used when selecting an image for a new post
    """
    image_ext = get_image_extensions()

    image_formats = ''
    for ext in image_ext:
        if image_formats:
            image_formats += ', '
        image_formats += '.' + ext
    return image_formats


def is_image_file(filename: str) -> bool:
    """Is the given filename an image?
    """
    for ext in get_image_extensions():
        if filename.endswith('.' + ext):
            return True
    return False


def get_media_formats() -> str:
    """Returns a string of permissable media formats
    used when selecting an attachment for a new post
    """
    media_ext = get_media_extensions()

    media_formats = ''
    for ext in media_ext:
        if media_formats:
            media_formats += ', '
        media_formats += '.' + ext
    return media_formats


def remove_html(content: str) -> str:
    """Removes html links from the given content.
    Used to ensure that profile descriptions don't contain dubious content
    """
    if '<' not in content:
        return content
    removing = False
    content = content.replace('<a href', ' <a href')
    content = content.replace('<q>', '"').replace('</q>', '"')
    content = content.replace('</p>', '\n\n').replace('<br>', '\n')
    result = ''
    for char in content:
        if char == '<':
            removing = True
        elif char == '>':
            removing = False
        elif not removing:
            result += char

    plain_text = result.replace('  ', ' ')

    # insert spaces after full stops
    str_len = len(plain_text)
    result = ''
    for i in range(str_len):
        result += plain_text[i]
        if plain_text[i] == '.' and i < str_len - 1:
            if plain_text[i + 1] >= 'A' and plain_text[i + 1] <= 'Z':
                result += ' '

    result = result.replace('  ', ' ').strip()
    return result


def remove_style_within_html(content: str) -> str:
    """Removes style="something" within html post content.
    Used to ensure that styles
    """
    if '<' not in content:
        return content
    if ' style="' not in content:
        return content
    sections = content.split(' style="')
    result = ''
    ctr = 0
    for section_text in sections:
        if ctr > 0:
            result += section_text.split('"', 1)[1]
        else:
            result = section_text
        ctr = 1
    return result


def first_paragraph_from_string(content: str) -> str:
    """Get the first paragraph from a blog post
    to be used as a summary in the newswire feed
    """
    if '<p>' not in content or '</p>' not in content:
        return remove_html(content)
    paragraph = content.split('<p>')[1]
    if '</p>' in paragraph:
        paragraph = paragraph.split('</p>')[0]
    return remove_html(paragraph)


def is_system_account(nickname: str) -> bool:
    """Returns true if the given nickname is a system account
    """
    if nickname in ('news', 'inbox'):
        return True
    return False


def get_memorials(base_dir: str) -> str:
    """Returns the nicknames for memorial accounts
    """
    memorial_file = base_dir + '/accounts/memorial'
    if not os.path.isfile(memorial_file):
        return ''

    memorial_str = ''
    try:
        with open(memorial_file, 'r', encoding='utf-8') as fp_memorial:
            memorial_str = fp_memorial.read()
    except OSError:
        print('EX: unable to read ' + memorial_file)
    return memorial_str


def set_memorials(base_dir: str, domain: str, memorial_str) -> None:
    """Sets the nicknames for memorial accounts
    """
    # check that the accounts exist
    memorial_list = memorial_str.split('\n')
    new_memorial_str = ''
    for memorial_item in memorial_list:
        memorial_nick = memorial_item.strip()
        check_dir = acct_dir(base_dir, memorial_nick, domain)
        if os.path.isdir(check_dir):
            new_memorial_str += memorial_nick + '\n'
    memorial_str = new_memorial_str

    # save the accounts
    memorial_file = base_dir + '/accounts/memorial'
    try:
        with open(memorial_file, 'w+', encoding='utf-8') as fp_memorial:
            fp_memorial.write(memorial_str)
    except OSError:
        print('EX: unable to write ' + memorial_file)


def is_memorial_account(base_dir: str, nickname: str) -> bool:
    """Returns true if the given nickname is a memorial account
    """
    memorial_file = base_dir + '/accounts/memorial'
    if not os.path.isfile(memorial_file):
        return False
    memorial_list = []
    try:
        with open(memorial_file, 'r', encoding='utf-8') as fp_memorial:
            memorial_list = fp_memorial.read().split('\n')
    except OSError:
        print('EX: unable to read ' + memorial_file)
    if nickname in memorial_list:
        return True
    return False


def _create_config(base_dir: str) -> None:
    """Creates a configuration file
    """
    config_filename = base_dir + '/config.json'
    if os.path.isfile(config_filename):
        return
    config_json = {
    }
    save_json(config_json, config_filename)


def set_config_param(base_dir: str, variable_name: str,
                     variable_value) -> None:
    """Sets a configuration value
    """
    _create_config(base_dir)
    config_filename = base_dir + '/config.json'
    config_json = {}
    if os.path.isfile(config_filename):
        config_json = load_json(config_filename)
    variable_name = _convert_to_camel_case(variable_name)
    config_json[variable_name] = variable_value
    save_json(config_json, config_filename)


def get_config_param(base_dir: str, variable_name: str):
    """Gets a configuration value
    """
    _create_config(base_dir)
    config_filename = base_dir + '/config.json'
    config_json = load_json(config_filename)
    if config_json:
        variable_name = _convert_to_camel_case(variable_name)
        if variable_name in config_json:
            return config_json[variable_name]
    return None


def is_suspended(base_dir: str, nickname: str) -> bool:
    """Returns true if the given nickname is suspended
    """
    admin_nickname = get_config_param(base_dir, 'admin')
    if not admin_nickname:
        return False
    if nickname == admin_nickname:
        return False

    suspended_filename = base_dir + '/accounts/suspended.txt'
    if os.path.isfile(suspended_filename):
        with open(suspended_filename, 'r', encoding='utf-8') as susp_file:
            lines = susp_file.readlines()
        for suspended in lines:
            if suspended.strip('\n').strip('\r') == nickname:
                return True
    return False


def get_followers_list(base_dir: str,
                       nickname: str, domain: str,
                       follow_file='following.txt') -> []:
    """Returns a list of followers for the given account
    """
    filename = acct_dir(base_dir, nickname, domain) + '/' + follow_file

    if not os.path.isfile(filename):
        return []

    with open(filename, 'r', encoding='utf-8') as foll_file:
        lines = foll_file.readlines()
        for i, _ in enumerate(lines):
            lines[i] = lines[i].strip()
        return lines
    return []


def get_followers_of_person(base_dir: str,
                            nickname: str, domain: str,
                            follow_file='following.txt') -> []:
    """Returns a list containing the followers of the given person
    Used by the shared inbox to know who to send incoming mail to
    """
    followers = []
    domain = remove_domain_port(domain)
    handle = nickname + '@' + domain
    handle_dir = acct_handle_dir(base_dir, handle)
    if not os.path.isdir(handle_dir):
        return followers
    for subdir, dirs, _ in os.walk(base_dir + '/accounts'):
        for account in dirs:
            filename = os.path.join(subdir, account) + '/' + follow_file
            if account == handle or \
               account.startswith('inbox@') or \
               account.startswith('Actor@') or \
               account.startswith('news@'):
                continue
            if not os.path.isfile(filename):
                continue
            with open(filename, 'r', encoding='utf-8') as followingfile:
                for following_handle in followingfile:
                    following_handle2 = remove_eol(following_handle)
                    if following_handle2 == handle:
                        if account not in followers:
                            followers.append(account)
                        break
        break
    return followers


def remove_id_ending(id_str: str) -> str:
    """Removes endings such as /activity and /undo
    """
    if id_str.endswith('/activity'):
        id_str = id_str[:-len('/activity')]
    elif id_str.endswith('/undo'):
        id_str = id_str[:-len('/undo')]
    elif id_str.endswith('/event'):
        id_str = id_str[:-len('/event')]
    elif id_str.endswith('/replies'):
        id_str = id_str[:-len('/replies')]
    elif id_str.endswith('/delete'):
        id_str = id_str[:-len('/delete')]
    elif id_str.endswith('/update'):
        id_str = id_str[:-len('/update')]
    if id_str.endswith('#Create'):
        id_str = id_str.split('#Create')[0]
    elif id_str.endswith('#delete'):
        id_str = id_str.split('#delete')[0]
    elif '#update' in id_str:
        id_str = id_str.split('#update')[0]
    elif '#moved' in id_str:
        id_str = id_str.split('#moved')[0]
    elif '#primary' in id_str:
        id_str = id_str.split('#primary')[0]
    elif '#reciprocal' in id_str:
        id_str = id_str.split('#reciprocal')[0]
    return id_str


def remove_hash_from_post_id(post_id: str) -> str:
    """Removes any has from a post id
    """
    if '#' not in post_id:
        return post_id
    return post_id.split('#')[0]


def get_protocol_prefixes() -> []:
    """Returns a list of valid prefixes
    """
    return ('https://', 'http://', 'ftp://',
            'dat://', 'i2p://', 'gnunet://',
            'ipfs://', 'ipns://',
            'hyper://', 'gemini://', 'gopher://')


def get_link_prefixes() -> []:
    """Returns a list of valid web link prefixes
    """
    return ('https://', 'http://', 'ftp://',
            'dat://', 'i2p://', 'gnunet://', 'payto://',
            'hyper://', 'gemini://', 'gopher://', 'briar:')


def remove_avatar_from_cache(base_dir: str, actor_str: str) -> None:
    """Removes any existing avatar entries from the cache
    This avoids duplicate entries with differing extensions
    """
    avatar_filename_extensions = get_image_extensions()
    for extension in avatar_filename_extensions:
        avatar_filename = \
            base_dir + '/cache/avatars/' + actor_str + '.' + extension
        if os.path.isfile(avatar_filename):
            try:
                os.remove(avatar_filename)
            except OSError:
                print('EX: remove_avatar_from_cache ' +
                      'unable to delete cached avatar ' +
                      str(avatar_filename))


def save_json(json_object: {}, filename: str) -> bool:
    """Saves json to a file
    """
    tries = 1
    while tries <= 5:
        try:
            with open(filename, 'w+', encoding='utf-8') as json_file:
                json_file.write(json.dumps(json_object))
                return True
        except OSError:
            print('EX: save_json ' + str(tries) + ' ' + str(filename))
            time.sleep(1)
            tries += 1
    return False


def load_json(filename: str, delay_sec: int = 2, max_tries: int = 5) -> {}:
    """Makes a few attempts to load a json formatted file
    """
    if '/Actor@' in filename:
        filename = filename.replace('/Actor@', '/inbox@')
    json_object = None
    tries = 1
    while tries <= max_tries:
        try:
            with open(filename, 'r', encoding='utf-8') as json_file:
                data = json_file.read()
                json_object = json.loads(data)
                break
        except BaseException:
            print('EX: load_json exception ' +
                  str(tries) + ' ' + str(filename))
            if delay_sec > 0:
                time.sleep(delay_sec)
            tries += 1
    return json_object


def load_json_onionify(filename: str, domain: str, onion_domain: str,
                       delay_sec: int = 2) -> {}:
    """Makes a few attempts to load a json formatted file
    This also converts the domain name to the onion domain
    """
    if '/Actor@' in filename:
        filename = filename.replace('/Actor@', '/inbox@')
    json_object = None
    tries = 0
    while tries < 5:
        try:
            with open(filename, 'r', encoding='utf-8') as json_file:
                data = json_file.read()
                if data:
                    data = data.replace(domain, onion_domain)
                    data = data.replace('https:', 'http:')
                json_object = json.loads(data)
                break
        except BaseException:
            print('EX: load_json_onionify exception ' + str(filename))
            if delay_sec > 0:
                time.sleep(delay_sec)
            tries += 1
    return json_object


def get_status_number(published_str: str = None) -> (str, str):
    """Returns the status number and published date
    """
    if not published_str:
        curr_time = datetime.datetime.utcnow()
    else:
        curr_time = \
            datetime.datetime.strptime(published_str, '%Y-%m-%dT%H:%M:%SZ')
    days_since_epoch = (curr_time - datetime.datetime(1970, 1, 1)).days
    # status is the number of seconds since epoch
    status_number = \
        str(((days_since_epoch * 24 * 60 * 60) +
             (curr_time.hour * 60 * 60) +
             (curr_time.minute * 60) +
             curr_time.second) * 1000 +
            int(curr_time.microsecond / 1000))
    # See https://github.com/tootsuite/mastodon/blob/
    # 995f8b389a66ab76ec92d9a240de376f1fc13a38/lib/mastodon/snowflake.rb
    # use the leftover microseconds as the sequence number
    sequence_id = curr_time.microsecond % 1000
    # shift by 16bits "sequence data"
    status_number = str((int(status_number) << 16) + sequence_id)
    published = curr_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return status_number, published


def evil_incarnate() -> []:
    """Hardcoded blocked domains
    """
    return ('fedilist.com', 'gab.com', 'gabfed.com', 'spinster.xyz',
            'kiwifarms.cc', 'djitter.com')


def is_evil(domain: str) -> bool:
    """ https://www.youtube.com/watch?v=5qw1hcevmdU
    """
    if not isinstance(domain, str):
        print('WARN: Malformed domain ' + str(domain))
        return True
    # if a domain contains any of these strings then it is
    # declaring itself to be hostile
    evil_emporium = (
        'nazi', 'extremis', 'extreemis', 'gendercritic',
        'kiwifarm', 'illegal', 'raplst', 'rapist',
        'rapl.st', 'rapi.st', 'antivax', 'plandemic', 'terror'
    )
    for hostile_str in evil_emporium:
        if hostile_str in domain:
            return True
    evil_domains = evil_incarnate()
    for concentrated_evil in evil_domains:
        if domain.endswith(concentrated_evil):
            return True
    return False


def contains_invalid_chars(json_str: str) -> bool:
    """Does the given json string contain invalid characters?
    """
    for is_invalid in INVALID_CHARACTERS:
        if is_invalid in json_str:
            return True
    return False


def contains_invalid_actor_url_chars(url: str) -> bool:
    """Does the given actor url contain invalid characters?
    """
    for is_invalid in INVALID_ACTOR_URL_CHARACTERS:
        if is_invalid in url:
            return True

    return contains_invalid_chars(url)


def remove_invalid_chars(text: str) -> str:
    """Removes any invalid characters from a string
    """
    for is_invalid in INVALID_CHARACTERS:
        if is_invalid not in text:
            continue
        text = text.replace(is_invalid, '')
    return text


def create_person_dir(nickname: str, domain: str, base_dir: str,
                      dir_name: str) -> str:
    """Create a directory for a person
    """
    handle = nickname + '@' + domain
    handle_dir = acct_handle_dir(base_dir, handle)
    if not os.path.isdir(handle_dir):
        os.mkdir(handle_dir)
    box_dir = acct_handle_dir(base_dir, handle) + '/' + dir_name
    if not os.path.isdir(box_dir):
        os.mkdir(box_dir)
    return box_dir


def create_outbox_dir(nickname: str, domain: str, base_dir: str) -> str:
    """Create an outbox for a person
    """
    return create_person_dir(nickname, domain, base_dir, 'outbox')


def create_inbox_queue_dir(nickname: str, domain: str, base_dir: str) -> str:
    """Create an inbox queue and returns the feed filename and directory
    """
    return create_person_dir(nickname, domain, base_dir, 'queue')


def domain_permitted(domain: str, federation_list: []) -> bool:
    """Is the given domain permitted according to the federation list?
    """
    if len(federation_list) == 0:
        return True
    domain = remove_domain_port(domain)
    if domain in federation_list:
        return True
    return False


def url_permitted(url: str, federation_list: []):
    if is_evil(url):
        return False
    if not federation_list:
        return True
    for domain in federation_list:
        if domain in url:
            return True
    return False


def get_local_network_addresses() -> []:
    """Returns patterns for local network address detection
    """
    return ('localhost', '127.0.', '192.168', '10.0.')


def is_local_network_address(ip_address: str) -> bool:
    """Is the given ip address local?
    """
    local_ips = get_local_network_addresses()
    for ip_addr in local_ips:
        if ip_address.startswith(ip_addr):
            return True
    return False


def _is_dangerous_string_tag(content: str, allow_local_network_access: bool,
                             separators: [], invalid_strings: []) -> bool:
    """Returns true if the given string is dangerous
    """
    for separator_style in separators:
        start_char = separator_style[0]
        end_char = separator_style[1]
        if start_char not in content:
            continue
        if end_char not in content:
            continue
        content_sections = content.split(start_char)
        invalid_partials = ()
        if not allow_local_network_access:
            invalid_partials = get_local_network_addresses()
        for markup in content_sections:
            if end_char not in markup:
                continue
            markup = markup.split(end_char)[0].strip()
            for partial_match in invalid_partials:
                if partial_match in markup:
                    return True
            if ' ' not in markup:
                for bad_str in invalid_strings:
                    if not bad_str.endswith('-'):
                        if bad_str in markup:
                            return True
                    else:
                        if markup.startswith(bad_str):
                            return True
            else:
                for bad_str in invalid_strings:
                    if not bad_str.endswith('-'):
                        if bad_str + ' ' in markup:
                            return True
                    else:
                        if markup.startswith(bad_str):
                            return True
    return False


def _is_dangerous_string_simple(content: str, allow_local_network_access: bool,
                                separators: [], invalid_strings: []) -> bool:
    """Returns true if the given string is dangerous
    """
    for separator_style in separators:
        start_char = separator_style[0]
        end_char = separator_style[1]
        if start_char not in content:
            continue
        if end_char not in content:
            continue
        content_sections = content.split(start_char)
        invalid_partials = ()
        if not allow_local_network_access:
            invalid_partials = get_local_network_addresses()
        for markup in content_sections:
            if end_char not in markup:
                continue
            markup = markup.split(end_char)[0].strip()
            for partial_match in invalid_partials:
                if partial_match in markup:
                    return True
            for bad_str in invalid_strings:
                if bad_str in markup:
                    return True
    return False


def html_tag_has_closing(tag_name: str, content: str) -> bool:
    """Does the given tag have opening and closing labels?
    """
    content_lower = content.lower()
    if '<' + tag_name not in content_lower:
        return True
    sections = content_lower.split('<' + tag_name)
    ctr = 0
    end_tag = '</' + tag_name + '>'
    for section in sections:
        if ctr == 0:
            ctr += 1
            continue
        # check that an ending tag exists
        if end_tag not in section:
            return False
        if tag_name in ('code', 'pre'):
            # check that lines are not too long
            section = section.split(end_tag)[0]
            section = section.replace('<br>', '\n')
            code_lines = section.split('\n')
            for line in code_lines:
                if len(line) >= 60:
                    print('<code> or <pre> line too long')
                    return False
        ctr += 1
    return True


def dangerous_markup(content: str, allow_local_network_access: bool,
                     allow_tags: []) -> bool:
    """Returns true if the given content contains dangerous html markup
    """
    if '.svg' in content.lower():
        return True
    separators = [['<', '>'], ['&lt;', '&gt;']]
    invalid_strings = [
        'ampproject', 'googleapis', '_exec(', ' id=', ' name='
    ]
    if _is_dangerous_string_simple(content, allow_local_network_access,
                                   separators, invalid_strings):
        return True
    for closing_tag in ('code', 'pre'):
        if not html_tag_has_closing(closing_tag, content):
            return True
    invalid_strings = [
        'script', 'noscript', 'canvas', 'style', 'abbr', 'input',
        'frame', 'iframe', 'html', 'body', 'hr', 'allow-popups',
        'allow-scripts', 'amp-', '?php', 'pre'
    ]
    for allowed in allow_tags:
        if allowed in invalid_strings:
            invalid_strings.remove(allowed)
    return _is_dangerous_string_tag(content, allow_local_network_access,
                                    separators, invalid_strings)


def dangerous_svg(content: str, allow_local_network_access: bool) -> bool:
    """Returns true if the given svg file content contains dangerous scripts
    """
    separators = [['<', '>'], ['&lt;', '&gt;']]
    invalid_strings = [
        'script'
    ]
    return _is_dangerous_string_tag(content, allow_local_network_access,
                                    separators, invalid_strings)


def _get_statuses_list() -> []:
    """Returns a list of statuses path strings
    """
    return ('/statuses/', '/objects/', '/honk/', '/p/', '/h/')


def contains_statuses(url: str) -> bool:
    """Whether the given url contains /statuses/
    """
    statuses_list = _get_statuses_list()
    for status_str in statuses_list:
        if status_str in url:
            return True
    return False


def get_actor_from_post_id(post_id: str) -> str:
    """Returns an actor url from a post id containing /statuses/ or equivalent
    eg. https://somedomain/users/nick/statuses/123 becomes
    https://somedomain/users/nick
    """
    actor = post_id
    statuses_list = _get_statuses_list()
    pixelfed_style_statuses = ['/p/']
    for status_str in statuses_list:
        if status_str not in actor:
            continue
        if status_str in pixelfed_style_statuses:
            # pixelfed style post id
            nick = actor.split(status_str)[1]
            if '/' in nick:
                nick = nick.split('/')[0]
            actor = actor.split(status_str)[0] + '/users/' + nick
            break
        if has_users_path(actor):
            actor = actor.split(status_str)[0]
            break
    return actor


def get_display_name(base_dir: str, actor: str, person_cache: {}) -> str:
    """Returns the display name for the given actor
    """
    actor = get_actor_from_post_id(actor)
    if not person_cache.get(actor):
        return None
    name_found = None
    if person_cache[actor].get('actor'):
        if person_cache[actor]['actor'].get('name'):
            name_found = person_cache[actor]['actor']['name']
    else:
        # Try to obtain from the cached actors
        cached_actor_filename = \
            base_dir + '/cache/actors/' + (actor.replace('/', '#')) + '.json'
        if os.path.isfile(cached_actor_filename):
            actor_json = load_json(cached_actor_filename, 1)
            if actor_json:
                if actor_json.get('name'):
                    name_found = actor_json['name']
    if name_found:
        if dangerous_markup(name_found, False, []):
            name_found = "*ADVERSARY*"
    return standardize_text(name_found)


def display_name_is_emoji(display_name: str) -> bool:
    """Returns true if the given display name is an emoji
    """
    if ' ' in display_name:
        words = display_name.split(' ')
        for wrd in words:
            if not wrd.startswith(':'):
                return False
            if not wrd.endswith(':'):
                return False
        return True
    if len(display_name) < 2:
        return False
    if not display_name.startswith(':'):
        return False
    if not display_name.endswith(':'):
        return False
    return True


def _gender_from_string(translate: {}, text: str) -> str:
    """Given some text, does it contain a gender description?
    """
    gender = None
    if not text:
        return None
    text_orig = text
    text = text.lower()
    if translate['He/Him'].lower() in text or \
       translate['boy'].lower() in text:
        gender = 'He/Him'
    elif (translate['She/Her'].lower() in text or
          translate['girl'].lower() in text):
        gender = 'She/Her'
    elif 'him' in text or 'male' in text:
        gender = 'He/Him'
    elif 'her' in text or 'she' in text or \
         'fem' in text or 'woman' in text:
        gender = 'She/Her'
    elif 'man' in text or 'He' in text_orig:
        gender = 'He/Him'
    return gender


def get_gender_from_bio(base_dir: str, actor: str, person_cache: {},
                        translate: {}) -> str:
    """Tries to ascertain gender from bio description
    This is for use by text-to-speech for pitch setting
    """
    default_gender = 'They/Them'
    actor = get_actor_from_post_id(actor)
    if not person_cache.get(actor):
        return default_gender
    bio_found = None
    if translate:
        pronoun_str = translate['pronoun'].lower()
    else:
        pronoun_str = 'pronoun'
    actor_json = None
    if person_cache[actor].get('actor'):
        actor_json = person_cache[actor]['actor']
    else:
        # Try to obtain from the cached actors
        cached_actor_filename = \
            base_dir + '/cache/actors/' + (actor.replace('/', '#')) + '.json'
        if os.path.isfile(cached_actor_filename):
            actor_json = load_json(cached_actor_filename, 1)
    if not actor_json:
        return default_gender
    # is gender defined as a profile tag?
    if actor_json.get('attachment'):
        tags_list = actor_json['attachment']
        if isinstance(tags_list, list):
            # look for a gender field name
            for tag in tags_list:
                if not isinstance(tag, dict):
                    continue
                name_value = None
                if tag.get('name'):
                    name_value = tag['name']
                if tag.get('schema:name'):
                    name_value = tag['schema:name']
                if not name_value:
                    continue
                prop_value_name, _ = get_attachment_property_value(tag)
                if not prop_value_name:
                    continue
                if name_value.lower() == \
                   translate['gender'].lower():
                    bio_found = tag[prop_value_name]
                    break
                if name_value.lower().startswith(pronoun_str):
                    bio_found = tag[prop_value_name]
                    break
            # the field name could be anything,
            # just look at the value
            if not bio_found:
                for tag in tags_list:
                    if not isinstance(tag, dict):
                        continue
                    if not tag.get('name') and not tag.get('schema:name'):
                        continue
                    prop_value_name, _ = get_attachment_property_value(tag)
                    if not prop_value_name:
                        continue
                    gender = \
                        _gender_from_string(translate, tag[prop_value_name])
                    if gender:
                        return gender
    # if not then use the bio
    if not bio_found and actor_json.get('summary'):
        bio_found = actor_json['summary']
    if not bio_found:
        return default_gender
    gender = _gender_from_string(translate, bio_found)
    if not gender:
        gender = default_gender
    return gender


def get_nickname_from_actor(actor: str) -> str:
    """Returns the nickname from an actor url
    """
    if actor.startswith('@'):
        actor = actor[1:]
    users_paths = get_user_paths()
    for possible_path in users_paths:
        if possible_path in actor:
            nick_str = actor.split(possible_path)[1].replace('@', '')
            if '/' not in nick_str:
                return nick_str
            return nick_str.split('/')[0]
    if '/@/' not in actor:
        if '/@' in actor:
            # https://domain/@nick
            nick_str = actor.split('/@')[1]
            if '/' in nick_str:
                nick_str = nick_str.split('/')[0]
            return nick_str
        if '@' in actor:
            nick_str = actor.split('@')[0]
            return nick_str
    if '://' in actor:
        domain = actor.split('://')[1]
        if '/' in domain:
            domain = domain.split('/')[0]
        if '://' + domain + '/' not in actor:
            return None
        nick_str = actor.split('://' + domain + '/')[1]
        if '/' in nick_str or '.' in nick_str:
            return None
        return nick_str
    return None


def get_user_paths() -> []:
    """Returns possible user paths
    e.g. /users/nickname, /channel/nickname
    """
    return ('/users/', '/profile/', '/accounts/', '/channel/', '/u/',
            '/c/', '/m/', '/video-channels/', '/author/',
            '/activitypub/', '/actors/', '/snac/', '/@/', '/~/',
            '/fediverse/blog/', '/user/')


def get_group_paths() -> []:
    """Returns possible group paths
    e.g. https://lemmy/c/groupname
    """
    return ['/c/', '/video-channels/', '/m/']


def get_domain_from_actor(actor: str) -> (str, int):
    """Returns the domain name from an actor url
    """
    if actor.startswith('@'):
        actor = actor[1:]
    port = None
    prefixes = get_protocol_prefixes()
    users_paths = get_user_paths()
    for possible_path in users_paths:
        if possible_path in actor:
            domain = actor.split(possible_path)[0]
            for prefix in prefixes:
                domain = domain.replace(prefix, '')
            break
    if '/@' in actor and '/@/' not in actor:
        domain = actor.split('/@')[0]
        for prefix in prefixes:
            domain = domain.replace(prefix, '')
    elif '@' in actor and '/@/' not in actor:
        domain = actor.split('@')[1].strip()
    else:
        domain = actor
        for prefix in prefixes:
            domain = domain.replace(prefix, '')
        if '/' in actor:
            domain = domain.split('/')[0]
    if ':' in domain:
        port = get_port_from_domain(domain)
        domain = remove_domain_port(domain)
    return domain, port


def _set_default_pet_name(base_dir: str, nickname: str, domain: str,
                          follow_nickname: str, follow_domain: str) -> None:
    """Sets a default petname
    This helps especially when using onion or i2p address
    """
    domain = remove_domain_port(domain)
    user_path = acct_dir(base_dir, nickname, domain)
    petnames_filename = user_path + '/petnames.txt'

    petname_lookup_entry = follow_nickname + ' ' + \
        follow_nickname + '@' + follow_domain + '\n'
    if not os.path.isfile(petnames_filename):
        # if there is no existing petnames lookup file
        with open(petnames_filename, 'w+', encoding='utf-8') as petnames_file:
            petnames_file.write(petname_lookup_entry)
        return

    with open(petnames_filename, 'r', encoding='utf-8') as petnames_file:
        petnames_str = petnames_file.read()
        if petnames_str:
            petnames_list = petnames_str.split('\n')
            for pet in petnames_list:
                if pet.startswith(follow_nickname + ' '):
                    # petname already exists
                    return
    # petname doesn't already exist
    with open(petnames_filename, 'a+', encoding='utf-8') as petnames_file:
        petnames_file.write(petname_lookup_entry)


def follow_person(base_dir: str, nickname: str, domain: str,
                  follow_nickname: str, follow_domain: str,
                  federation_list: [], debug: bool,
                  group_account: bool,
                  follow_file: str = 'following.txt') -> bool:
    """Adds a person to the follow list
    """
    follow_domain_str_lower1 = follow_domain.lower()
    follow_domain_str_lower = remove_eol(follow_domain_str_lower1)
    if not domain_permitted(follow_domain_str_lower,
                            federation_list):
        if debug:
            print('DEBUG: follow of domain ' +
                  follow_domain + ' not permitted')
        return False
    if debug:
        print('DEBUG: follow of domain ' + follow_domain)

    if ':' in domain:
        domain_only = remove_domain_port(domain)
        handle = nickname + '@' + domain_only
    else:
        handle = nickname + '@' + domain

    handle_dir = acct_handle_dir(base_dir, handle)
    if not os.path.isdir(handle_dir):
        print('WARN: account for ' + handle + ' does not exist')
        return False

    if ':' in follow_domain:
        follow_domain_only = remove_domain_port(follow_domain)
        handle_to_follow = follow_nickname + '@' + follow_domain_only
    else:
        handle_to_follow = follow_nickname + '@' + follow_domain

    if group_account:
        handle_to_follow = '!' + handle_to_follow

    # was this person previously unfollowed?
    unfollowed_filename = acct_handle_dir(base_dir, handle) + '/unfollowed.txt'
    if os.path.isfile(unfollowed_filename):
        if text_in_file(handle_to_follow, unfollowed_filename):
            # remove them from the unfollowed file
            new_lines = ''
            with open(unfollowed_filename, 'r',
                      encoding='utf-8') as unfoll_file:
                lines = unfoll_file.readlines()
                for line in lines:
                    if handle_to_follow not in line:
                        new_lines += line
            with open(unfollowed_filename, 'w+',
                      encoding='utf-8') as unfoll_file:
                unfoll_file.write(new_lines)

    if not os.path.isdir(base_dir + '/accounts'):
        os.mkdir(base_dir + '/accounts')
    handle_to_follow = follow_nickname + '@' + follow_domain
    if group_account:
        handle_to_follow = '!' + handle_to_follow
    filename = acct_handle_dir(base_dir, handle) + '/' + follow_file
    if os.path.isfile(filename):
        if text_in_file(handle_to_follow, filename):
            if debug:
                print('DEBUG: follow already exists')
            return True
        # prepend to follow file
        try:
            with open(filename, 'r+', encoding='utf-8') as foll_file:
                content = foll_file.read()
                if handle_to_follow + '\n' not in content:
                    foll_file.seek(0, 0)
                    foll_file.write(handle_to_follow + '\n' + content)
                    print('DEBUG: follow added')
        except OSError as ex:
            print('WARN: Failed to write entry to follow file ' +
                  filename + ' ' + str(ex))
    else:
        # first follow
        if debug:
            print('DEBUG: ' + handle +
                  ' creating new following file to follow ' +
                  handle_to_follow +
                  ', filename is ' + filename)
        with open(filename, 'w+', encoding='utf-8') as foll_file:
            foll_file.write(handle_to_follow + '\n')

    if follow_file.endswith('following.txt'):
        # Default to adding new follows to the calendar.
        # Possibly this could be made optional
        # if following a person add them to the list of
        # calendar follows
        print('DEBUG: adding ' +
              follow_nickname + '@' + follow_domain + ' to calendar of ' +
              nickname + '@' + domain)
        add_person_to_calendar(base_dir, nickname, domain,
                               follow_nickname, follow_domain)
        # add a default petname
        _set_default_pet_name(base_dir, nickname, domain,
                              follow_nickname, follow_domain)
    return True


def votes_on_newswire_item(status: []) -> int:
    """Returns the number of votes on a newswire item
    """
    total_votes = 0
    for line in status:
        if 'vote:' in line:
            total_votes += 1
    return total_votes


def locate_news_votes(base_dir: str, domain: str,
                      post_url: str) -> str:
    """Returns the votes filename for a news post
    within the news user account
    """
    post_url1 = post_url.strip()
    post_url = remove_eol(post_url1)

    # if this post in the shared inbox?
    post_url = remove_id_ending(post_url.strip()).replace('/', '#')

    if post_url.endswith('.json'):
        post_url = post_url + '.votes'
    else:
        post_url = post_url + '.json.votes'

    account_dir = base_dir + '/accounts/news@' + domain + '/'
    post_filename = account_dir + 'outbox/' + post_url
    if os.path.isfile(post_filename):
        return post_filename

    return None


def locate_news_arrival(base_dir: str, domain: str,
                        post_url: str) -> str:
    """Returns the arrival time for a news post
    within the news user account
    """
    post_url1 = post_url.strip()
    post_url = remove_eol(post_url1)

    # if this post in the shared inbox?
    post_url = remove_id_ending(post_url.strip()).replace('/', '#')

    if post_url.endswith('.json'):
        post_url = post_url + '.arrived'
    else:
        post_url = post_url + '.json.arrived'

    account_dir = base_dir + '/accounts/news@' + domain + '/'
    post_filename = account_dir + 'outbox/' + post_url
    if os.path.isfile(post_filename):
        with open(post_filename, 'r', encoding='utf-8') as arrival_file:
            arrival = arrival_file.read()
            if arrival:
                arrival_date = \
                    datetime.datetime.strptime(arrival,
                                               "%Y-%m-%dT%H:%M:%SZ")
                return arrival_date

    return None


def clear_from_post_caches(base_dir: str, recent_posts_cache: {},
                           post_id: str) -> None:
    """Clears cached html for the given post, so that edits
    to news will appear
    """
    filename = '/postcache/' + post_id + '.html'
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if acct.startswith('inbox@') or acct.startswith('Actor@'):
                continue
            cache_dir = os.path.join(base_dir + '/accounts', acct)
            post_filename = cache_dir + filename
            if os.path.isfile(post_filename):
                try:
                    os.remove(post_filename)
                except OSError:
                    print('EX: clear_from_post_caches file not removed ' +
                          str(post_filename))
            # if the post is in the recent posts cache then remove it
            if recent_posts_cache.get('index'):
                if post_id in recent_posts_cache['index']:
                    recent_posts_cache['index'].remove(post_id)
            if recent_posts_cache.get('json'):
                if recent_posts_cache['json'].get(post_id):
                    del recent_posts_cache['json'][post_id]
            if recent_posts_cache.get('html'):
                if recent_posts_cache['html'].get(post_id):
                    del recent_posts_cache['html'][post_id]
        break


def locate_post(base_dir: str, nickname: str, domain: str,
                post_url: str, replies: bool = False) -> str:
    """Returns the filename for the given status post url
    """
    if not replies:
        extension = 'json'
    else:
        extension = 'replies'

    # if this post in the shared inbox?
    post_url = remove_id_ending(post_url.strip()).replace('/', '#')

    # add the extension
    post_url = post_url + '.' + extension

    # search boxes
    boxes = ('inbox', 'outbox', 'tlblogs')
    account_dir = acct_dir(base_dir, nickname, domain) + '/'
    for box_name in boxes:
        post_filename = account_dir + box_name + '/' + post_url
        if os.path.isfile(post_filename):
            return post_filename

    # check news posts
    account_dir = base_dir + '/accounts/news' + '@' + domain + '/'
    post_filename = account_dir + 'outbox/' + post_url
    if os.path.isfile(post_filename):
        return post_filename

    # is it in the announce cache?
    post_filename = base_dir + '/cache/announce/' + nickname + '/' + post_url
    if os.path.isfile(post_filename):
        return post_filename

    # print('WARN: unable to locate ' + nickname + ' ' + post_url)
    return None


def _get_published_date(post_json_object: {}) -> str:
    """Returns the published date on the given post
    """
    published = None
    if post_json_object.get('published'):
        published = post_json_object['published']
    elif has_object_dict(post_json_object):
        if post_json_object['object'].get('published'):
            published = post_json_object['object']['published']
    if not published:
        return None
    if not isinstance(published, str):
        return None
    return published


def get_reply_interval_hours(base_dir: str, nickname: str, domain: str,
                             default_reply_interval_hrs: int) -> int:
    """Returns the reply interval for the given account.
    The reply interval is the number of hours after a post being made
    during which replies are allowed
    """
    reply_interval_filename = \
        acct_dir(base_dir, nickname, domain) + '/.reply_interval_hours'
    if os.path.isfile(reply_interval_filename):
        with open(reply_interval_filename, 'r',
                  encoding='utf-8') as interval_file:
            hours_str = interval_file.read()
            if hours_str.isdigit():
                return int(hours_str)
    return default_reply_interval_hrs


def set_reply_interval_hours(base_dir: str, nickname: str, domain: str,
                             reply_interval_hours: int) -> bool:
    """Sets the reply interval for the given account.
    The reply interval is the number of hours after a post being made
    during which replies are allowed
    """
    reply_interval_filename = \
        acct_dir(base_dir, nickname, domain) + '/.reply_interval_hours'
    try:
        with open(reply_interval_filename, 'w+',
                  encoding='utf-8') as interval_file:
            interval_file.write(str(reply_interval_hours))
            return True
    except OSError:
        print('EX: set_reply_interval_hours unable to save reply interval ' +
              str(reply_interval_filename) + ' ' +
              str(reply_interval_hours))
    return False


def can_reply_to(base_dir: str, nickname: str, domain: str,
                 post_url: str, reply_interval_hours: int,
                 curr_date_str: str = None,
                 post_json_object: {} = None) -> bool:
    """Is replying to the given local post permitted?
    This is a spam mitigation feature, so that spammers can't
    add a lot of replies to old post which you don't notice.
    """
    if '/statuses/' not in post_url:
        return True
    if not post_json_object:
        post_filename = locate_post(base_dir, nickname, domain, post_url)
        if not post_filename:
            # the post is not stored locally
            return True
        post_json_object = load_json(post_filename)
    if not post_json_object:
        return False
    published = _get_published_date(post_json_object)
    if not published:
        return False
    try:
        pub_date = datetime.datetime.strptime(published, '%Y-%m-%dT%H:%M:%SZ')
    except BaseException:
        print('EX: can_reply_to unrecognized published date ' + str(published))
        return False
    if not curr_date_str:
        curr_date = datetime.datetime.utcnow()
    else:
        try:
            curr_date = \
                datetime.datetime.strptime(curr_date_str, '%Y-%m-%dT%H:%M:%SZ')
        except BaseException:
            print('EX: can_reply_to unrecognized current date ' +
                  str(curr_date_str))
            return False
    hours_since_publication = \
        int((curr_date - pub_date).total_seconds() / 3600)
    if hours_since_publication < 0 or \
       hours_since_publication >= reply_interval_hours:
        return False
    return True


def _remove_attachment(base_dir: str, http_prefix: str, domain: str,
                       post_json: {}):
    """Removes media files for an attachment
    """
    if not post_json.get('attachment'):
        return
    if not post_json['attachment'][0].get('url'):
        return
    attachment_url = post_json['attachment'][0]['url']
    if not attachment_url:
        return
    attachment_url = remove_html(attachment_url)
    media_filename = base_dir + '/' + \
        attachment_url.replace(http_prefix + '://' + domain + '/', '')
    if os.path.isfile(media_filename):
        try:
            os.remove(media_filename)
        except OSError:
            print('EX: _remove_attachment unable to delete media file ' +
                  str(media_filename))
    if os.path.isfile(media_filename + '.vtt'):
        try:
            os.remove(media_filename + '.vtt')
        except OSError:
            print('EX: _remove_attachment unable to delete media transcript ' +
                  str(media_filename) + '.vtt')
    etag_filename = media_filename + '.etag'
    if os.path.isfile(etag_filename):
        try:
            os.remove(etag_filename)
        except OSError:
            print('EX: _remove_attachment unable to delete etag file ' +
                  str(etag_filename))
    post_json['attachment'] = []


def remove_moderation_post_from_index(base_dir: str, post_url: str,
                                      debug: bool) -> None:
    """Removes a url from the moderation index
    """
    moderation_index_file = base_dir + '/accounts/moderation.txt'
    if not os.path.isfile(moderation_index_file):
        return
    post_id = remove_id_ending(post_url)
    if text_in_file(post_id, moderation_index_file):
        with open(moderation_index_file, 'r',
                  encoding='utf-8') as file1:
            lines = file1.readlines()
            with open(moderation_index_file, 'w+',
                      encoding='utf-8') as file2:
                for line in lines:
                    if line.strip("\n").strip("\r") != post_id:
                        file2.write(line)
                        continue
                    if debug:
                        print('DEBUG: removed ' + post_id +
                              ' from moderation index')


def _is_reply_to_blog_post(base_dir: str, nickname: str, domain: str,
                           post_json_object: str):
    """Is the given post a reply to a blog post?
    """
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('inReplyTo'):
        return False
    if not isinstance(post_json_object['object']['inReplyTo'], str):
        return False
    blogs_index_filename = \
        acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogs_index_filename):
        return False
    post_id = remove_id_ending(post_json_object['object']['inReplyTo'])
    post_id = post_id.replace('/', '#')
    if text_in_file(post_id, blogs_index_filename):
        return True
    return False


def _delete_post_remove_replies(base_dir: str, nickname: str, domain: str,
                                http_prefix: str, post_filename: str,
                                recent_posts_cache: {}, debug: bool,
                                manual: bool) -> None:
    """Removes replies when deleting a post
    """
    replies_filename = post_filename.replace('.json', '.replies')
    if not os.path.isfile(replies_filename):
        return
    if debug:
        print('DEBUG: removing replies to ' + post_filename)
    with open(replies_filename, 'r', encoding='utf-8') as replies_file:
        for reply_id in replies_file:
            reply_file = locate_post(base_dir, nickname, domain, reply_id)
            if not reply_file:
                continue
            if os.path.isfile(reply_file):
                delete_post(base_dir, http_prefix,
                            nickname, domain, reply_file, debug,
                            recent_posts_cache, manual)
    # remove the replies file
    try:
        os.remove(replies_filename)
    except OSError:
        print('EX: _delete_post_remove_replies ' +
              'unable to delete replies file ' + str(replies_filename))


def _is_bookmarked(base_dir: str, nickname: str, domain: str,
                   post_filename: str) -> bool:
    """Returns True if the given post is bookmarked
    """
    bookmarks_index_filename = \
        acct_dir(base_dir, nickname, domain) + '/bookmarks.index'
    if os.path.isfile(bookmarks_index_filename):
        bookmark_index = post_filename.split('/')[-1] + '\n'
        if text_in_file(bookmark_index, bookmarks_index_filename):
            return True
    return False


def remove_post_from_cache(post_json_object: {},
                           recent_posts_cache: {}) -> None:
    """ if the post exists in the recent posts cache then remove it
    """
    if not recent_posts_cache:
        return

    if not post_json_object.get('id'):
        return

    if not recent_posts_cache.get('index'):
        return

    post_id = post_json_object['id']
    if '#' in post_id:
        post_id = post_id.split('#', 1)[0]
    post_id = remove_id_ending(post_id).replace('/', '#')
    if post_id not in recent_posts_cache['index']:
        return

    if recent_posts_cache.get('index'):
        if post_id in recent_posts_cache['index']:
            recent_posts_cache['index'].remove(post_id)

    if recent_posts_cache.get('json'):
        if recent_posts_cache['json'].get(post_id):
            del recent_posts_cache['json'][post_id]

    if recent_posts_cache.get('html'):
        if recent_posts_cache['html'].get(post_id):
            del recent_posts_cache['html'][post_id]


def delete_cached_html(base_dir: str, nickname: str, domain: str,
                       post_json_object: {}):
    """Removes cached html file for the given post
    """
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain, post_json_object)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                print('EX: delete_cached_html ' +
                      'unable to delete cached post file ' +
                      str(cached_post_filename))

        cached_post_filename = cached_post_filename.replace('.html', '.ssml')
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                print('EX: delete_cached_html ' +
                      'unable to delete cached ssml post file ' +
                      str(cached_post_filename))

        cached_post_filename = \
            cached_post_filename.replace('/postcache/', '/outbox/')
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                print('EX: delete_cached_html ' +
                      'unable to delete cached outbox ssml post file ' +
                      str(cached_post_filename))


def _remove_post_id_from_tag_index(tag_index_filename: str,
                                   post_id: str) -> None:
    """Remove post_id from the tag index file
    """
    lines = None
    with open(tag_index_filename, 'r', encoding='utf-8') as index_file:
        lines = index_file.readlines()
    if not lines:
        return
    newlines = ''
    for file_line in lines:
        if post_id in file_line:
            # skip over the deleted post
            continue
        newlines += file_line
    if not newlines.strip():
        # if there are no lines then remove the hashtag file
        try:
            os.remove(tag_index_filename)
        except OSError:
            print('EX: _delete_hashtags_on_post ' +
                  'unable to delete tag index ' + str(tag_index_filename))
    else:
        # write the new hashtag index without the given post in it
        with open(tag_index_filename, 'w+',
                  encoding='utf-8') as index_file:
            index_file.write(newlines)


def _delete_hashtags_on_post(base_dir: str, post_json_object: {}) -> None:
    """Removes hashtags when a post is deleted
    """
    remove_hashtag_index = False
    if has_object_dict(post_json_object):
        if post_json_object['object'].get('content'):
            if '#' in post_json_object['object']['content']:
                remove_hashtag_index = True

    if not remove_hashtag_index:
        return

    if not post_json_object['object'].get('id') or \
       not post_json_object['object'].get('tag'):
        return

    # get the id of the post
    post_id = remove_id_ending(post_json_object['object']['id'])
    for tag in post_json_object['object']['tag']:
        if not tag.get('type'):
            continue
        if tag['type'] != 'Hashtag':
            continue
        if not tag.get('name'):
            continue
        # find the index file for this tag
        tag_map_filename = base_dir + '/tagmaps/' + tag['name'][1:] + '.txt'
        if os.path.isfile(tag_map_filename):
            _remove_post_id_from_tag_index(tag_map_filename, post_id)
        # find the index file for this tag
        tag_index_filename = base_dir + '/tags/' + tag['name'][1:] + '.txt'
        if os.path.isfile(tag_index_filename):
            _remove_post_id_from_tag_index(tag_index_filename, post_id)


def _delete_conversation_post(base_dir: str, nickname: str, domain: str,
                              post_json_object: {}) -> None:
    """Deletes a post from a conversation
    """
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('conversation') and \
       not post_json_object['object'].get('context'):
        return False
    if not post_json_object['object'].get('id'):
        return False
    conversation_dir = \
        acct_dir(base_dir, nickname, domain) + '/conversation'
    if post_json_object['object'].get('conversation'):
        conversation_id = post_json_object['object']['conversation']
    else:
        conversation_id = post_json_object['object']['context']
    conversation_id = conversation_id.replace('/', '#')
    post_id = post_json_object['object']['id']
    conversation_filename = conversation_dir + '/' + conversation_id
    if not os.path.isfile(conversation_filename):
        return False
    conversation_str = ''
    with open(conversation_filename, 'r', encoding='utf-8') as conv_file:
        conversation_str = conv_file.read()
    if post_id + '\n' not in conversation_str:
        return False
    conversation_str = conversation_str.replace(post_id + '\n', '')
    if conversation_str:
        with open(conversation_filename, 'w+', encoding='utf-8') as conv_file:
            conv_file.write(conversation_str)
    else:
        if os.path.isfile(conversation_filename + '.muted'):
            try:
                os.remove(conversation_filename + '.muted')
            except OSError:
                print('EX: _delete_conversation_post ' +
                      'unable to remove conversation ' +
                      str(conversation_filename) + '.muted')
        try:
            os.remove(conversation_filename)
        except OSError:
            print('EX: _delete_conversation_post ' +
                  'unable to remove conversation ' +
                  str(conversation_filename))


def is_dm(post_json_object: {}) -> bool:
    """Returns true if the given post is a DM
    """
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if post_json_object['object']['type'] != 'ChatMessage':
        if post_json_object['object']['type'] != 'Note' and \
           post_json_object['object']['type'] != 'Page' and \
           post_json_object['object']['type'] != 'Patch' and \
           post_json_object['object']['type'] != 'EncryptedMessage' and \
           post_json_object['object']['type'] != 'Article':
            return False
    if post_json_object['object'].get('moderationStatus'):
        return False
    fields = ('to', 'cc')
    for field_name in fields:
        if not post_json_object['object'].get(field_name):
            continue
        if isinstance(post_json_object['object'][field_name], list):
            for to_address in post_json_object['object'][field_name]:
                if to_address.endswith('#Public') or \
                   to_address == 'as:Public' or \
                   to_address == 'Public':
                    return False
                if to_address.endswith('followers'):
                    return False
        elif isinstance(post_json_object['object'][field_name], str):
            if post_json_object['object'][field_name].endswith('#Public'):
                return False
    return True


def is_reminder(post_json_object: {}) -> bool:
    """Returns true if the given post is a reminder
    """
    if not is_dm(post_json_object):
        return False
    if not post_json_object['object'].get('to'):
        return False
    if not post_json_object['object'].get('attributedTo'):
        return False
    if not post_json_object['object'].get('tag'):
        return False
    if len(post_json_object['object']['to']) != 1:
        return False
    if post_json_object['object']['to'][0] != \
       post_json_object['object']['attributedTo']:
        return False
    for tag in post_json_object['object']['tag']:
        if tag['type'] == 'Event':
            return True
    return False


def _is_remote_dm(domain_full: str, post_json_object: {}) -> bool:
    """Is the given post a DM from a different domain?
    """
    if not is_dm(post_json_object):
        return False
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    if this_post_json.get('attributedTo'):
        if isinstance(this_post_json['attributedTo'], str):
            if '://' + domain_full not in this_post_json['attributedTo']:
                return True
    return False


def delete_post(base_dir: str, http_prefix: str,
                nickname: str, domain: str, post_filename: str,
                debug: bool, recent_posts_cache: {},
                manual: bool) -> None:
    """Recursively deletes a post and its replies and attachments
    """
    post_json_object = load_json(post_filename, 1)
    if not post_json_object:
        # remove any replies
        _delete_post_remove_replies(base_dir, nickname, domain,
                                    http_prefix, post_filename,
                                    recent_posts_cache, debug, manual)
        # finally, remove the post itself
        try:
            os.remove(post_filename)
        except OSError:
            if debug:
                print('EX: delete_post unable to delete post ' +
                      str(post_filename))
        return

    # don't allow DMs to be deleted if they came from a different instance
    # otherwise this breaks expectations about how DMs should operate
    # i.e. DMs should only be removed if they are manually deleted
    if not manual:
        if _is_remote_dm(domain, post_json_object):
            return

    # don't allow deletion of bookmarked posts
    if _is_bookmarked(base_dir, nickname, domain, post_filename):
        return

    # don't remove replies to blog posts
    if _is_reply_to_blog_post(base_dir, nickname, domain,
                              post_json_object):
        return

    # remove from recent posts cache in memory
    remove_post_from_cache(post_json_object, recent_posts_cache)

    # remove from conversation index
    _delete_conversation_post(base_dir, nickname, domain, post_json_object)

    # remove any attachment
    _remove_attachment(base_dir, http_prefix, domain, post_json_object)

    extensions = (
        'votes', 'arrived', 'muted', 'tts', 'reject', 'mitm', 'edits'
    )
    for ext in extensions:
        ext_filename = post_filename + '.' + ext
        if os.path.isfile(ext_filename):
            try:
                os.remove(ext_filename)
            except OSError:
                print('EX: delete_post unable to remove ext ' +
                      str(ext_filename))
        elif post_filename.endswith('.json'):
            ext_filename = post_filename.replace('.json', '') + '.' + ext
            if os.path.isfile(ext_filename):
                try:
                    os.remove(ext_filename)
                except OSError:
                    print('EX: delete_post unable to remove ext ' +
                          str(ext_filename))

    # remove cached html version of the post
    delete_cached_html(base_dir, nickname, domain, post_json_object)

    has_object = False
    if post_json_object.get('object'):
        has_object = True

    # remove from moderation index file
    if has_object:
        if has_object_dict(post_json_object):
            if post_json_object['object'].get('moderationStatus'):
                if post_json_object.get('id'):
                    post_id = remove_id_ending(post_json_object['id'])
                    remove_moderation_post_from_index(base_dir, post_id, debug)

    # remove any hashtags index entries
    if has_object:
        _delete_hashtags_on_post(base_dir, post_json_object)

    # remove any replies
    _delete_post_remove_replies(base_dir, nickname, domain,
                                http_prefix, post_filename,
                                recent_posts_cache, debug, manual)
    # finally, remove the post itself
    try:
        os.remove(post_filename)
    except OSError:
        if debug:
            print('EX: delete_post unable to delete post ' +
                  str(post_filename))


def _is_valid_language(text: str) -> bool:
    """Returns true if the given text contains a valid
    natural language string
    """
    natural_languages = {
        "Latin": [65, 866],
        "Greek": [880, 1280],
        "isArmenian": [1328, 1424],
        "isHebrew": [1424, 1536],
        "Arabic": [1536, 1792],
        "Syriac": [1792, 1872],
        "Thaan": [1920, 1984],
        "Devanagari": [2304, 2432],
        "Bengali": [2432, 2560],
        "Gurmukhi": [2560, 2688],
        "Gujarati": [2688, 2816],
        "Oriya": [2816, 2944],
        "Tamil": [2944, 3072],
        "Telugu": [3072, 3200],
        "Kannada": [3200, 3328],
        "Malayalam": [3328, 3456],
        "Sinhala": [3456, 3584],
        "Thai": [3584, 3712],
        "Lao": [3712, 3840],
        "Tibetan": [3840, 4096],
        "Myanmar": [4096, 4256],
        "Georgian": [4256, 4352],
        "HangulJamo": [4352, 4608],
        "Cherokee": [5024, 5120],
        "UCAS": [5120, 5760],
        "Ogham": [5760, 5792],
        "Runic": [5792, 5888],
        "Khmer": [6016, 6144],
        "Hangul Syllables": [44032, 55203],
        "Hangul Jamo": [4352, 4607],
        "Hangul Compatibility Jamo": [12592, 12687],
        "Hangul Jamo Extended-A": [43360, 43391],
        "Hangul Jamo Extended-B": [55216, 55295],
        "Mongolian": [6144, 6320],
        "Cyrillic": [1024, 1279],
        "Cyrillic Supplement": [1280, 1327],
        "Cyrillic Extended A": [11744, 11775],
        "Cyrillic Extended B": [42560, 42655],
        "Cyrillic Extended C": [7296, 7311],
        "Phonetic Extensions": [7467, 7544],
        "Combining Half Marks": [65070, 65071]
    }
    for _, lang_range in natural_languages.items():
        ok_lang = True
        for char in text:
            if char.isdigit() or char == '_':
                continue
            if ord(char) not in range(lang_range[0], lang_range[1]):
                ok_lang = False
                break
        if ok_lang:
            return True
    return False


def _get_reserved_words() -> str:
    return ('inbox', 'dm', 'outbox', 'following',
            'public', 'followers', 'category',
            'channel', 'calendar', 'video-channels',
            'tlreplies', 'tlmedia', 'tlblogs',
            'tlblogs', 'tlfeatures',
            'moderation', 'moderationaction',
            'activity', 'undo', 'pinned',
            'actor', 'Actor', 'instance.actor',
            'reply', 'replies', 'question', 'like',
            'likes', 'users', 'statuses', 'tags', 'author',
            'accounts', 'headers', 'snac',
            'channels', 'profile', 'u', 'c',
            'updates', 'repeat', 'announce',
            'shares', 'fonts', 'icons', 'avatars',
            'welcome', 'helpimages',
            'bookmark', 'bookmarks', 'tlbookmarks',
            'ignores', 'linksmobile', 'newswiremobile',
            'minimal', 'search', 'eventdelete',
            'searchemoji', 'catalog', 'conversationId',
            'mention', 'http', 'https', 'ipfs', 'ipns',
            'ontologies', 'data', 'postedit', 'moved',
            'inactive', 'activitypub', 'actors',
            'notes', 'offers', 'wanted', 'honk')


def get_nickname_validation_pattern() -> str:
    """Returns a html text input validation pattern for nickname
    """
    reserved_names = _get_reserved_words()
    pattern = ''
    for word in reserved_names:
        if pattern:
            pattern += '(?!.*\\b' + word + '\\b)'
        else:
            pattern = '^(?!.*\\b' + word + '\\b)'
    return pattern + '.*${1,30}'


def _is_reserved_name(nickname: str) -> bool:
    """Is the given nickname reserved for some special function?
    """
    reserved_names = _get_reserved_words()
    if nickname in reserved_names:
        return True
    return False


def valid_nickname(domain: str, nickname: str) -> bool:
    """Is the given nickname valid?
    """
    if len(nickname) == 0:
        return False
    if len(nickname) > 30:
        return False
    if not _is_valid_language(nickname):
        return False
    forbidden_chars = ('.', ' ', '/', '?', ':', ';', '@', '#', '!')
    for char in forbidden_chars:
        if char in nickname:
            return False
    # this should only apply for the shared inbox
    if nickname == domain:
        return False
    if _is_reserved_name(nickname):
        return False
    return True


def no_of_accounts(base_dir: str) -> bool:
    """Returns the number of accounts on the system
    """
    account_ctr = 0
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for account in dirs:
            if is_account_dir(account):
                account_ctr += 1
        break
    return account_ctr


def no_of_active_accounts_monthly(base_dir: str, months: int) -> bool:
    """Returns the number of accounts on the system this month
    """
    account_ctr = 0
    curr_time = int(time.time())
    month_seconds = int(60*60*24*30*months)
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for account in dirs:
            if not is_account_dir(account):
                continue
            last_used_filename = \
                base_dir + '/accounts/' + account + '/.lastUsed'
            if not os.path.isfile(last_used_filename):
                continue
            with open(last_used_filename, 'r',
                      encoding='utf-8') as last_used_file:
                last_used = last_used_file.read()
                if last_used.isdigit():
                    time_diff = (curr_time - int(last_used))
                    if time_diff < month_seconds:
                        account_ctr += 1
        break
    return account_ctr


def is_public_post_from_url(base_dir: str, nickname: str, domain: str,
                            post_url: str) -> bool:
    """Returns whether the given url is a public post
    """
    post_filename = locate_post(base_dir, nickname, domain, post_url)
    if not post_filename:
        return False
    post_json_object = load_json(post_filename, 1)
    if not post_json_object:
        return False
    return is_public_post(post_json_object)


def is_public_post(post_json_object: {}) -> bool:
    """Returns true if the given post is public
    """
    if not post_json_object.get('type'):
        return False
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('to'):
        return False
    if isinstance(post_json_object['object']['to'], list):
        for recipient in post_json_object['object']['to']:
            if recipient.endswith('#Public') or \
               recipient == 'as:Public' or \
               recipient == 'Public':
                return True
    elif isinstance(post_json_object['object']['to'], str):
        if post_json_object['object']['to'].endswith('#Public'):
            return True
    return False


def is_followers_post(post_json_object: {}) -> bool:
    """Returns true if the given post is to followers
    """
    if not post_json_object.get('type'):
        return False
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('to'):
        return False
    for recipient in post_json_object['object']['to']:
        if recipient.endswith('/followers'):
            return True
    return False


def is_unlisted_post(post_json_object: {}) -> bool:
    """Returns true if the given post is unlisted
    """
    if not post_json_object.get('type'):
        return False
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('to'):
        return False
    if not post_json_object['object'].get('cc'):
        return False
    has_followers = False
    for recipient in post_json_object['object']['to']:
        if recipient.endswith('/followers'):
            has_followers = True
            break
    if not has_followers:
        return False
    for recipient in post_json_object['object']['cc']:
        if recipient.endswith('#Public') or \
           recipient == 'as:Public' or \
           recipient == 'Public':
            return True
    return False


def copytree(src: str, dst: str, symlinks: str = False, ignore: bool = None):
    """Copy a directory
    """
    for item in os.listdir(src):
        s_dir = os.path.join(src, item)
        d_dir = os.path.join(dst, item)
        if os.path.isdir(s_dir):
            shutil.copytree(s_dir, d_dir, symlinks, ignore)
        else:
            shutil.copy2(s_dir, d_dir)


def get_cached_post_directory(base_dir: str,
                              nickname: str, domain: str) -> str:
    """Returns the directory where the html post cache exists
    """
    html_post_cache_dir = acct_dir(base_dir, nickname, domain) + '/postcache'
    return html_post_cache_dir


def get_cached_post_filename(base_dir: str, nickname: str, domain: str,
                             post_json_object: {}) -> str:
    """Returns the html cache filename for the given post
    """
    cached_post_dir = get_cached_post_directory(base_dir, nickname, domain)
    if not os.path.isdir(cached_post_dir):
        # print('ERROR: invalid html cache directory ' + cached_post_dir)
        return None
    if '@' not in cached_post_dir:
        # print('ERROR: invalid html cache directory ' + cached_post_dir)
        return None
    cached_post_id = remove_id_ending(post_json_object['id'])
    cached_post_filename = \
        cached_post_dir + '/' + cached_post_id.replace('/', '#')
    return cached_post_filename + '.html'


def update_recent_posts_cache(recent_posts_cache: {}, max_recent_posts: int,
                              post_json_object: {}, html_str: str) -> None:
    """Store recent posts in memory so that they can be quickly recalled
    """
    if not post_json_object.get('id'):
        return
    post_id = post_json_object['id']
    if '#' in post_id:
        post_id = post_id.split('#', 1)[0]
    post_id = remove_id_ending(post_id).replace('/', '#')
    if recent_posts_cache.get('index'):
        if post_id in recent_posts_cache['index']:
            return
        recent_posts_cache['index'].append(post_id)
        post_json_object['muted'] = False
        recent_posts_cache['json'][post_id] = json.dumps(post_json_object)
        recent_posts_cache['html'][post_id] = html_str

        while len(recent_posts_cache['html'].items()) > max_recent_posts:
            post_id = recent_posts_cache['index'][0]
            recent_posts_cache['index'].pop(0)
            if recent_posts_cache['json'].get(post_id):
                del recent_posts_cache['json'][post_id]
            if recent_posts_cache['html'].get(post_id):
                del recent_posts_cache['html'][post_id]
    else:
        recent_posts_cache['index'] = [post_id]
        recent_posts_cache['json'] = {}
        recent_posts_cache['html'] = {}
        recent_posts_cache['json'][post_id] = json.dumps(post_json_object)
        recent_posts_cache['html'][post_id] = html_str


def file_last_modified(filename: str) -> str:
    """Returns the date when a file was last modified
    """
    time_val = os.path.getmtime(filename)
    modified_time = datetime.datetime.fromtimestamp(time_val)
    return modified_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_css(base_dir: str, css_filename: str) -> str:
    """Retrieves the css for a given file, or from a cache
    """
    # does the css file exist?
    if not os.path.isfile(css_filename):
        return None

    with open(css_filename, 'r', encoding='utf-8') as fp_css:
        css = fp_css.read()
        return css

    return None


def is_blog_post(post_json_object: {}) -> bool:
    """Is the given post a blog post?
    """
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if not has_object_string_type(post_json_object, False):
        return False
    if 'content' not in post_json_object['object']:
        return False
    if post_json_object['object']['type'] != 'Article':
        return False
    return True


def is_news_post(post_json_object: {}) -> bool:
    """Is the given post a blog post?
    """
    return post_json_object.get('news')


def _search_virtual_box_posts(base_dir: str, nickname: str, domain: str,
                              search_str: str, max_results: int,
                              box_name: str) -> []:
    """Searches through a virtual box, which is typically an index on the inbox
    """
    index_filename = \
        acct_dir(base_dir, nickname, domain) + '/' + box_name + '.index'
    if box_name == 'bookmarks':
        box_name = 'inbox'
    path = acct_dir(base_dir, nickname, domain) + '/' + box_name
    if not os.path.isdir(path):
        return []

    search_str = search_str.lower().strip()

    if '+' in search_str:
        search_words = search_str.split('+')
        for index, _ in enumerate(search_words):
            search_words[index] = search_words[index].strip()
        print('SEARCH: ' + str(search_words))
    else:
        search_words = [search_str]

    res = []
    with open(index_filename, 'r', encoding='utf-8') as index_file:
        post_filename = 'start'
        while post_filename:
            post_filename = index_file.readline()
            if not post_filename:
                break
            if '.json' not in post_filename:
                break
            post_filename = path + '/' + post_filename.strip()
            if not os.path.isfile(post_filename):
                continue
            with open(post_filename, 'r', encoding='utf-8') as post_file:
                data = post_file.read().lower()

                not_found = False
                for keyword in search_words:
                    if keyword not in data:
                        not_found = True
                        break
                if not_found:
                    continue

                res.append(post_filename)
                if len(res) >= max_results:
                    return res
    return res


def search_box_posts(base_dir: str, nickname: str, domain: str,
                     search_str: str, max_results: int,
                     box_name='outbox') -> []:
    """Search your posts and return a list of the filenames
    containing matching strings
    """
    path = acct_dir(base_dir, nickname, domain) + '/' + box_name
    # is this a virtual box, such as direct messages?
    if not os.path.isdir(path):
        if os.path.isfile(path + '.index'):
            return _search_virtual_box_posts(base_dir, nickname, domain,
                                             search_str, max_results, box_name)
        return []
    search_str = search_str.lower().strip()

    if '+' in search_str:
        search_words = search_str.split('+')
        for index, _ in enumerate(search_words):
            search_words[index] = search_words[index].strip()
        print('SEARCH: ' + str(search_words))
    else:
        search_words = [search_str]

    res = []
    for root, _, fnames in os.walk(path):
        for fname in fnames:
            file_path = os.path.join(root, fname)
            with open(file_path, 'r', encoding='utf-8') as post_file:
                data = post_file.read().lower()

                not_found = False
                for keyword in search_words:
                    if keyword not in data:
                        not_found = True
                        break
                if not_found:
                    continue

                res.append(file_path)
                if len(res) >= max_results:
                    return res
        break
    return res


def get_file_case_insensitive(path: str) -> str:
    """Returns a case specific filename given a case insensitive version of it
    """
    if os.path.isfile(path):
        return path
    if path != path.lower():
        if os.path.isfile(path.lower()):
            return path.lower()
    return None


def undo_likes_collection_entry(recent_posts_cache: {},
                                base_dir: str, post_filename: str,
                                object_url: str,
                                actor: str, domain: str, debug: bool,
                                post_json_object: {}) -> None:
    """Undoes a like for a particular actor
    """
    if not post_json_object:
        post_json_object = load_json(post_filename)
    if not post_json_object:
        return
    # remove any cached version of this post so that the
    # like icon is changed
    nickname = get_nickname_from_actor(actor)
    if not nickname:
        return
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname,
                                 domain, post_json_object)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                print('EX: undo_likes_collection_entry ' +
                      'unable to delete cached post ' +
                      str(cached_post_filename))
    remove_post_from_cache(post_json_object, recent_posts_cache)

    if not post_json_object.get('type'):
        return
    if post_json_object['type'] != 'Create':
        return
    obj = post_json_object
    if has_object_dict(post_json_object):
        obj = post_json_object['object']
    if not obj.get('likes'):
        return
    if not isinstance(obj['likes'], dict):
        return
    if not obj['likes'].get('items'):
        return
    total_items = 0
    if obj['likes'].get('totalItems'):
        total_items = obj['likes']['totalItems']
    item_found = False
    for like_item in obj['likes']['items']:
        if like_item.get('actor'):
            if like_item['actor'] == actor:
                if debug:
                    print('DEBUG: like was removed for ' + actor)
                obj['likes']['items'].remove(like_item)
                item_found = True
                break
    if not item_found:
        return
    if total_items == 1:
        if debug:
            print('DEBUG: likes was removed from post')
        del obj['likes']
    else:
        itlen = len(obj['likes']['items'])
        obj['likes']['totalItems'] = itlen

    save_json(post_json_object, post_filename)


def undo_reaction_collection_entry(recent_posts_cache: {},
                                   base_dir: str, post_filename: str,
                                   object_url: str,
                                   actor: str, domain: str, debug: bool,
                                   post_json_object: {},
                                   emoji_content: str) -> None:
    """Undoes an emoji reaction for a particular actor
    """
    if not post_json_object:
        post_json_object = load_json(post_filename)
    if not post_json_object:
        return
    # remove any cached version of this post so that the
    # like icon is changed
    nickname = get_nickname_from_actor(actor)
    if not nickname:
        return
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname,
                                 domain, post_json_object)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                print('EX: undo_reaction_collection_entry ' +
                      'unable to delete cached post ' +
                      str(cached_post_filename))
    remove_post_from_cache(post_json_object, recent_posts_cache)

    if not post_json_object.get('type'):
        return
    if post_json_object['type'] != 'Create':
        return
    obj = post_json_object
    if has_object_dict(post_json_object):
        obj = post_json_object['object']
    if not obj.get('reactions'):
        return
    if not isinstance(obj['reactions'], dict):
        return
    if not obj['reactions'].get('items'):
        return
    total_items = 0
    if obj['reactions'].get('totalItems'):
        total_items = obj['reactions']['totalItems']
    item_found = False
    for like_item in obj['reactions']['items']:
        if like_item.get('actor'):
            if like_item['actor'] == actor and \
               like_item['content'] == emoji_content:
                if debug:
                    print('DEBUG: emoji reaction was removed for ' + actor)
                obj['reactions']['items'].remove(like_item)
                item_found = True
                break
    if not item_found:
        return
    if total_items == 1:
        if debug:
            print('DEBUG: emoji reaction was removed from post')
        del obj['reactions']
    else:
        itlen = len(obj['reactions']['items'])
        obj['reactions']['totalItems'] = itlen

    save_json(post_json_object, post_filename)


def undo_announce_collection_entry(recent_posts_cache: {},
                                   base_dir: str, post_filename: str,
                                   actor: str, domain: str,
                                   debug: bool) -> None:
    """Undoes an announce for a particular actor by removing it from
    the "shares" collection within a post. Note that the "shares"
    collection has no relation to shared items in shares.py. It's
    shares of posts, not shares of physical objects.
    """
    post_json_object = load_json(post_filename)
    if not post_json_object:
        return
    # remove any cached version of this announce so that the announce
    # icon is changed
    nickname = get_nickname_from_actor(actor)
    if not nickname:
        return
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain,
                                 post_json_object)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                if debug:
                    print('EX: undo_announce_collection_entry ' +
                          'unable to delete cached post ' +
                          str(cached_post_filename))
    remove_post_from_cache(post_json_object, recent_posts_cache)

    if not post_json_object.get('type'):
        return
    if post_json_object['type'] != 'Create':
        return
    if not has_object_dict(post_json_object):
        if debug:
            pprint(post_json_object)
            print('DEBUG: post has no object')
        return
    if not post_json_object['object'].get('shares'):
        return
    if not post_json_object['object']['shares'].get('items'):
        return
    total_items = 0
    if post_json_object['object']['shares'].get('totalItems'):
        total_items = post_json_object['object']['shares']['totalItems']
    item_found = False
    for announce_item in post_json_object['object']['shares']['items']:
        if announce_item.get('actor'):
            if announce_item['actor'] == actor:
                if debug:
                    print('DEBUG: Announce was removed for ' + actor)
                an_it = announce_item
                post_json_object['object']['shares']['items'].remove(an_it)
                item_found = True
                break
    if not item_found:
        return
    if total_items == 1:
        if debug:
            print('DEBUG: shares (announcements) ' +
                  'was removed from post')
        del post_json_object['object']['shares']
    else:
        itlen = len(post_json_object['object']['shares']['items'])
        post_json_object['object']['shares']['totalItems'] = itlen

    save_json(post_json_object, post_filename)


def update_announce_collection(recent_posts_cache: {},
                               base_dir: str, post_filename: str,
                               actor: str, nickname: str, domain: str,
                               debug: bool) -> None:
    """Updates the announcements collection within a post
    Confusingly this is known as "shares", but isn't the
    same as shared items within shares.py
    It's shares of posts, not shares of physical objects.
    """
    post_json_object = load_json(post_filename)
    if not post_json_object:
        return
    # remove any cached version of this announce so that the announce
    # icon is changed
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain,
                                 post_json_object)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                if debug:
                    print('EX: update_announce_collection ' +
                          'unable to delete cached post ' +
                          str(cached_post_filename))
    remove_post_from_cache(post_json_object, recent_posts_cache)

    if not has_object_dict(post_json_object):
        if debug:
            pprint(post_json_object)
            print('DEBUG: post ' + post_filename + ' has no object')
        return
    post_url = remove_id_ending(post_json_object['id']) + '/shares'
    if not post_json_object['object'].get('shares'):
        if debug:
            print('DEBUG: Adding initial shares (announcements) to ' +
                  post_url)
        announcements_json = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'id': post_url,
            'type': 'Collection',
            "totalItems": 1,
            'items': [{
                'type': 'Announce',
                'actor': actor
            }]
        }
        post_json_object['object']['shares'] = announcements_json
    else:
        if post_json_object['object']['shares'].get('items'):
            shares_items = post_json_object['object']['shares']['items']
            for announce_item in shares_items:
                if announce_item.get('actor'):
                    if announce_item['actor'] == actor:
                        return
            new_announce = {
                'type': 'Announce',
                'actor': actor
            }
            post_json_object['object']['shares']['items'].append(new_announce)
            itlen = len(post_json_object['object']['shares']['items'])
            post_json_object['object']['shares']['totalItems'] = itlen
        else:
            if debug:
                print('DEBUG: shares (announcements) section of post ' +
                      'has no items list')

    if debug:
        print('DEBUG: saving post with shares (announcements) added')
        pprint(post_json_object)
    save_json(post_json_object, post_filename)


def week_day_of_month_start(month_number: int, year: int) -> int:
    """Gets the day number of the first day of the month
    1=sun, 7=sat
    """
    first_day_of_month = datetime.datetime(year, month_number, 1, 0, 0)
    return int(first_day_of_month.strftime("%w")) + 1


def media_file_mime_type(filename: str) -> str:
    """Given a media filename return its mime type
    """
    if '.' not in filename:
        return 'image/png'
    extensions = {
        'json': 'application/json',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jxl': 'image/jxl',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        'avif': 'image/avif',
        'heic': 'image/heic',
        'ico': 'image/x-icon',
        'mp3': 'audio/mpeg',
        'ogg': 'audio/ogg',
        'audio/wav': 'wav',
        'audio/x-wav': 'wav',
        'audio/x-pn-wave': 'wav',
        'wav': 'audio/vnd.wave',
        'opus': 'audio/opus',
        'spx': 'audio/speex',
        'flac': 'audio/flac',
        'mp4': 'video/mp4',
        'ogv': 'video/ogv'
    }
    file_ext = filename.split('.')[-1]
    if not extensions.get(file_ext):
        return 'image/png'
    return extensions[file_ext]


def is_recent_post(post_json_object: {}, max_days: int) -> bool:
    """ Is the given post recent?
    """
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('published'):
        return False
    if not isinstance(post_json_object['object']['published'], str):
        return False
    curr_time = datetime.datetime.utcnow()
    days_since_epoch = (curr_time - datetime.datetime(1970, 1, 1)).days
    recently = days_since_epoch - max_days

    published_date_str = post_json_object['object']['published']
    if '.' in published_date_str:
        published_date_str = published_date_str.split('.')[0] + 'Z'
    try:
        published_date = \
            datetime.datetime.strptime(published_date_str,
                                       "%Y-%m-%dT%H:%M:%SZ")
    except BaseException:
        print('EX: is_recent_post unrecognized published date ' +
              str(published_date_str))
        return False

    published_days_since_epoch = \
        (published_date - datetime.datetime(1970, 1, 1)).days
    if published_days_since_epoch < recently:
        return False
    return True


def camel_case_split(text: str) -> str:
    """ Splits CamelCase into "Camel Case"
    """
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|' +
                          '(?<=[A-Z])(?=[A-Z][a-z])|$)', text)
    if not matches:
        return text
    result_str = ''
    for word in matches:
        result_str += word.group(0) + ' '
    return result_str.strip()


def convert_to_snake_case(text: str) -> str:
    """Convert camel case to snake case
    """
    return camel_case_split(text).lower().replace(' ', '_')


def _convert_to_camel_case(text: str) -> str:
    """Convers a snake case string to camel case
    """
    if '_' not in text:
        return text
    words = text.split('_')
    result = ''
    ctr = 0
    for wrd in words:
        if ctr > 0:
            result += wrd.title()
        else:
            result = wrd.lower()
        ctr += 1
    return result


def reject_post_id(base_dir: str, nickname: str, domain: str,
                   post_id: str, recent_posts_cache: {}) -> None:
    """ Marks the given post as rejected,
    for example an announce which is too old
    """
    post_filename = locate_post(base_dir, nickname, domain, post_id)
    if not post_filename:
        return

    if recent_posts_cache.get('index'):
        # if this is a full path then remove the directories
        index_filename = post_filename
        if '/' in post_filename:
            index_filename = post_filename.split('/')[-1]

        # filename of the post without any extension or path
        # This should also correspond to any index entry in
        # the posts cache
        post_url = remove_eol(index_filename)
        post_url = post_url.replace('.json', '').strip()

        if post_url in recent_posts_cache['index']:
            if recent_posts_cache['json'].get(post_url):
                del recent_posts_cache['json'][post_url]
            if recent_posts_cache['html'].get(post_url):
                del recent_posts_cache['html'][post_url]

    with open(post_filename + '.reject', 'w+',
              encoding='utf-8') as reject_file:
        reject_file.write('\n')


def is_chat_message(post_json_object: {}) -> bool:
    """Returns true if the given post is a chat message
    Note that is_dm should be checked before calling this
    """
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if post_json_object['object']['type'] != 'ChatMessage':
        return False
    return True


def is_reply(post_json_object: {}, actor: str) -> bool:
    """Returns true if the given post is a reply to the given actor
    """
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if post_json_object['object'].get('moderationStatus'):
        return False
    if post_json_object['object']['type'] != 'Note' and \
       post_json_object['object']['type'] != 'Page' and \
       post_json_object['object']['type'] != 'EncryptedMessage' and \
       post_json_object['object']['type'] != 'ChatMessage' and \
       post_json_object['object']['type'] != 'Article':
        return False
    if post_json_object['object'].get('inReplyTo'):
        if isinstance(post_json_object['object']['inReplyTo'], str):
            if post_json_object['object']['inReplyTo'].startswith(actor):
                return True
    if not post_json_object['object'].get('tag'):
        return False
    if not isinstance(post_json_object['object']['tag'], list):
        return False
    for tag in post_json_object['object']['tag']:
        if not tag.get('type'):
            continue
        if tag['type'] == 'Mention':
            if not tag.get('href'):
                continue
            if actor in tag['href']:
                return True
    return False


def contains_pgp_public_key(content: str) -> bool:
    """Returns true if the given content contains a PGP public key
    """
    if '--BEGIN PGP PUBLIC KEY BLOCK--' in content:
        if '--END PGP PUBLIC KEY BLOCK--' in content:
            return True
    return False


def is_pgp_encrypted(content: str) -> bool:
    """Returns true if the given content is PGP encrypted
    """
    if '--BEGIN PGP MESSAGE--' in content:
        if '--END PGP MESSAGE--' in content:
            return True
    return False


def invalid_ciphertext(content: str) -> bool:
    """Returns true if the given content contains an invalid key
    """
    if '----BEGIN ' in content or '----END ' in content:
        if not contains_pgp_public_key(content) and \
           not is_pgp_encrypted(content):
            return True
    return False


def load_translations_from_file(base_dir: str, language: str) -> ({}, str):
    """Returns the translations dictionary
    """
    if not os.path.isdir(base_dir + '/translations'):
        print('ERROR: translations directory not found')
        return None, None
    if not language:
        system_language = locale.getdefaultlocale()[0]
    else:
        system_language = language
    if not system_language:
        system_language = 'en'
    if '_' in system_language:
        system_language = system_language.split('_')[0]
    while '/' in system_language:
        system_language = system_language.split('/')[1]
    if '.' in system_language:
        system_language = system_language.split('.')[0]
    translations_file = base_dir + '/translations/' + \
        system_language + '.json'
    if not os.path.isfile(translations_file):
        system_language = 'en'
        translations_file = base_dir + '/translations/' + \
            system_language + '.json'
    return load_json(translations_file), system_language


def dm_allowed_from_domain(base_dir: str,
                           nickname: str, domain: str,
                           sending_actor_domain: str) -> bool:
    """When a DM is received and the .followDMs flag file exists
    Then optionally some domains can be specified as allowed,
    regardless of individual follows.
    i.e. Mostly you only want DMs from followers, but there are
    a few particular instances that you trust
    """
    dm_allowed_instances_file = \
        acct_dir(base_dir, nickname, domain) + '/dmAllowedInstances.txt'
    if not os.path.isfile(dm_allowed_instances_file):
        return False
    if text_in_file(sending_actor_domain + '\n', dm_allowed_instances_file):
        return True
    return False


def get_occupation_skills(actor_json: {}) -> []:
    """Returns the list of skills for an actor
    """
    if 'hasOccupation' not in actor_json:
        return []
    if not isinstance(actor_json['hasOccupation'], list):
        return []
    for occupation_item in actor_json['hasOccupation']:
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if not occupation_item['@type'] == 'Occupation':
            continue
        if not occupation_item.get('skills'):
            continue
        if isinstance(occupation_item['skills'], list):
            return occupation_item['skills']
        if isinstance(occupation_item['skills'], str):
            return [occupation_item['skills']]
        break
    return []


def get_occupation_name(actor_json: {}) -> str:
    """Returns the occupation name an actor
    """
    if not actor_json.get('hasOccupation'):
        return ""
    if not isinstance(actor_json['hasOccupation'], list):
        return ""
    for occupation_item in actor_json['hasOccupation']:
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] != 'Occupation':
            continue
        if not occupation_item.get('name'):
            continue
        if isinstance(occupation_item['name'], str):
            return occupation_item['name']
        break
    return ""


def set_occupation_name(actor_json: {}, name: str) -> bool:
    """Sets the occupation name of an actor
    """
    if not actor_json.get('hasOccupation'):
        return False
    if not isinstance(actor_json['hasOccupation'], list):
        return False
    for index, _ in enumerate(actor_json['hasOccupation']):
        occupation_item = actor_json['hasOccupation'][index]
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] != 'Occupation':
            continue
        occupation_item['name'] = name
        return True
    return False


def set_occupation_skills_list(actor_json: {}, skills_list: []) -> bool:
    """Sets the occupation skills for an actor
    """
    if 'hasOccupation' not in actor_json:
        return False
    if not isinstance(actor_json['hasOccupation'], list):
        return False
    for index, _ in enumerate(actor_json['hasOccupation']):
        occupation_item = actor_json['hasOccupation'][index]
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] != 'Occupation':
            continue
        occupation_item['skills'] = skills_list
        return True
    return False


def is_account_dir(dir_name: str) -> bool:
    """Is the given directory an account within /accounts ?
    """
    if '@' not in dir_name:
        return False
    if 'inbox@' in dir_name or 'news@' in dir_name or 'Actor@' in dir_name:
        return False
    return True


def permitted_dir(path: str) -> bool:
    """These are special paths which should not be accessible
       directly via GET or POST
    """
    if path.startswith('/wfendpoints') or \
       path.startswith('/keys') or \
       path.startswith('/accounts'):
        return False
    return True


def user_agent_domain(user_agent: str, debug: bool) -> str:
    """If the User-Agent string contains a domain
    then return it
    """
    if 'https://' not in user_agent and 'http://' not in user_agent:
        return None
    agent_domain = ''
    if 'https://' in user_agent:
        agent_domain = user_agent.split('https://')[1].strip()
    else:
        agent_domain = user_agent.split('http://')[1].strip()
    if '/' in agent_domain:
        agent_domain = agent_domain.split('/')[0]
    if ')' in agent_domain:
        agent_domain = agent_domain.split(')')[0].strip()
    if ' ' in agent_domain:
        agent_domain = agent_domain.replace(' ', '')
    if ';' in agent_domain:
        agent_domain = agent_domain.replace(';', '')
    if '.' not in agent_domain:
        return None
    if debug:
        print('User-Agent Domain: ' + agent_domain)
    return agent_domain


def get_alt_path(actor: str, domain_full: str, calling_domain: str) -> str:
    """Returns alternate path from the actor
    eg. https://clearnetdomain/path becomes http://oniondomain/path
    """
    post_actor = actor
    if calling_domain not in actor and domain_full in actor:
        if calling_domain.endswith('.onion') or \
           calling_domain.endswith('.i2p'):
            post_actor = \
                'http://' + calling_domain + actor.split(domain_full)[1]
            print('Changed POST domain from ' + actor + ' to ' + post_actor)
    return post_actor


def get_actor_property_url(actor_json: {}, property_name: str) -> str:
    """Returns a url property from an actor
    """
    if not actor_json.get('attachment'):
        return ''
    property_name = property_name.lower()
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not name_value.lower().startswith(property_name):
            continue
        if not property_value.get('type'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        property_value['value'] = property_value[prop_value_name].strip()
        prefixes = get_protocol_prefixes()
        prefix_found = False
        for prefix in prefixes:
            if property_value[prop_value_name].startswith(prefix):
                prefix_found = True
                break
        if not prefix_found:
            continue
        if '.' not in property_value[prop_value_name]:
            continue
        if ' ' in property_value[prop_value_name]:
            continue
        if ',' in property_value[prop_value_name]:
            continue
        return property_value[prop_value_name]
    return ''


def remove_domain_port(domain: str) -> str:
    """If the domain has a port appended then remove it
    eg. mydomain.com:80 becomes mydomain.com
    """
    if ':' in domain:
        if domain.startswith('did:'):
            return domain
        domain = domain.split(':')[0]
    return domain


def get_port_from_domain(domain: str) -> int:
    """If the domain has a port number appended then return it
    eg. mydomain.com:80 returns 80
    """
    if ':' in domain:
        if domain.startswith('did:'):
            return None
        port_str = domain.split(':')[1]
        if port_str.isdigit():
            return int(port_str)
    return None


def valid_url_prefix(url: str) -> bool:
    """Does the given url have a valid prefix?
    """
    if '/' not in url:
        return False
    prefixes = ('https:', 'http:', 'hyper:', 'i2p:', 'gnunet:')
    for pre in prefixes:
        if url.startswith(pre):
            return True
    return False


def valid_password(password: str) -> bool:
    """Returns true if the given password is valid
    """
    if len(password) < 8:
        return False
    return True


def is_float(value) -> bool:
    """Is the given value a float?
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


def date_string_to_seconds(date_str: str) -> int:
    """Converts a date string (eg "published") into seconds since epoch
    """
    try:
        expiry_time = \
            datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
    except BaseException:
        print('EX: date_string_to_seconds unable to parse date ' +
              str(date_str))
        return None
    return int(datetime.datetime.timestamp(expiry_time))


def date_seconds_to_string(date_sec: int) -> str:
    """Converts a date in seconds since epoch to a string
    """
    this_date = datetime.datetime.fromtimestamp(date_sec)
    return this_date.strftime("%Y-%m-%dT%H:%M:%SZ")


def has_group_type(base_dir: str, actor: str, person_cache: {},
                   debug: bool = False) -> bool:
    """Does the given actor url have a group type?
    """
    # does the actor path clearly indicate that this is a group?
    # eg. https://lemmy/c/groupname
    group_paths = get_group_paths()
    for grp_path in group_paths:
        if grp_path in actor:
            if debug:
                print('grpPath ' + grp_path + ' in ' + actor)
            return True
    # is there a cached actor which can be examined for Group type?
    return is_group_actor(base_dir, actor, person_cache, debug)


def is_group_actor(base_dir: str, actor: str, person_cache: {},
                   debug: bool = False) -> bool:
    """Is the given actor a group?
    """
    if person_cache:
        if person_cache.get(actor):
            if person_cache[actor].get('actor'):
                if person_cache[actor]['actor'].get('type'):
                    if person_cache[actor]['actor']['type'] == 'Group':
                        if debug:
                            print('Cached actor ' + actor + ' has Group type')
                        return True
                return False
    if debug:
        print('Actor ' + actor + ' not in cache')
    cached_actor_filename = \
        base_dir + '/cache/actors/' + (actor.replace('/', '#')) + '.json'
    if not os.path.isfile(cached_actor_filename):
        if debug:
            print('Cached actor file not found ' + cached_actor_filename)
        return False
    if text_in_file('"type": "Group"', cached_actor_filename):
        if debug:
            print('Group type found in ' + cached_actor_filename)
        return True
    return False


def is_group_account(base_dir: str, nickname: str, domain: str) -> bool:
    """Returns true if the given account is a group
    """
    account_filename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(account_filename):
        return False
    if text_in_file('"type": "Group"', account_filename):
        return True
    return False


def get_currencies() -> {}:
    """Returns a dictionary of currencies
    """
    return {
        "CA$": "CAD",
        "J$": "JMD",
        "£": "GBP",
        "€": "EUR",
        "؋": "AFN",
        "ƒ": "AWG",
        "₼": "AZN",
        "Br": "BYN",
        "BZ$": "BZD",
        "$b": "BOB",
        "KM": "BAM",
        "P": "BWP",
        "лв": "BGN",
        "R$": "BRL",
        "៛": "KHR",
        "$U": "UYU",
        "RD$": "DOP",
        "$": "USD",
        "₡": "CRC",
        "kn": "HRK",
        "₱": "CUP",
        "Kč": "CZK",
        "kr": "NOK",
        "¢": "GHS",
        "Q": "GTQ",
        "L": "HNL",
        "Ft": "HUF",
        "Rp": "IDR",
        "₹": "INR",
        "﷼": "IRR",
        "₪": "ILS",
        "¥": "JPY",
        "₩": "KRW",
        "₭": "LAK",
        "ден": "MKD",
        "RM": "MYR",
        "₨": "MUR",
        "₮": "MNT",
        "MT": "MZN",
        "C$": "NIO",
        "₦": "NGN",
        "Gs": "PYG",
        "zł": "PLN",
        "lei": "RON",
        "₽": "RUB",
        "Дин": "RSD",
        "S": "SOS",
        "R": "ZAR",
        "CHF": "CHF",
        "NT$": "TWD",
        "฿": "THB",
        "TT$": "TTD",
        "₴": "UAH",
        "Bs": "VEB",
        "₫": "VND",
        "Z$": "ZQD"
    }


def get_supported_languages(base_dir: str) -> []:
    """Returns a list of supported languages
    """
    translations_dir = base_dir + '/translations'
    languages_str = []
    for _, _, files in os.walk(translations_dir):
        for fname in files:
            if not fname.endswith('.json'):
                continue
            lang = fname.split('.')[0]
            if len(lang) == 2:
                languages_str.append(lang)
        break
    return languages_str


def get_category_types(base_dir: str) -> []:
    """Returns the list of ontologies
    """
    ontology_dir = base_dir + '/ontology'
    categories = []
    for _, _, files in os.walk(ontology_dir):
        for fname in files:
            if not fname.endswith('.json'):
                continue
            if '#' in fname or '~' in fname:
                continue
            if fname.startswith('custom'):
                continue
            ontology_filename = fname.split('.')[0]
            if 'Types' in ontology_filename:
                categories.append(ontology_filename.replace('Types', ''))
        break
    return categories


def get_shares_files_list() -> []:
    """Returns the possible shares files
    """
    return ('shares', 'wanted')


def replace_users_with_at(actor: str) -> str:
    """ https://domain/users/nick becomes https://domain/@nick
    """
    u_paths = get_user_paths()
    for path in u_paths:
        if path in actor:
            if '/@/' not in actor:
                actor = actor.replace(path, '/@')
            break
    return actor


def has_actor(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have an actor?
    """
    if post_json_object.get('actor'):
        if '#' in post_json_object['actor']:
            return False
        return True
    if debug:
        if post_json_object.get('type'):
            msg = post_json_object['type'] + ' has missing actor'
            if post_json_object.get('id'):
                msg += ' ' + post_json_object['id']
            print(msg)
    return False


def has_object_string_type(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have a type field within an object dict?
    """
    if not has_object_dict(post_json_object):
        if debug:
            print('has_object_string_type no object found')
        return False
    if post_json_object['object'].get('type'):
        if isinstance(post_json_object['object']['type'], str):
            return True
        if post_json_object.get('type'):
            print('DEBUG: ' + post_json_object['type'] +
                  ' type within object is not a string ' +
                  str(post_json_object))
    if debug:
        print('No type field within object ' + post_json_object['id'])
    return False


def has_object_string_object(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have an object string field within an object dict?
    """
    if not has_object_dict(post_json_object):
        if debug:
            print('has_object_string_type no object found')
        return False
    if post_json_object['object'].get('object'):
        if isinstance(post_json_object['object']['object'], str):
            return True
        if debug:
            if post_json_object.get('type'):
                print('DEBUG: ' + post_json_object['type'] +
                      ' object within dict is not a string')
    if debug:
        print('No object field within dict ' + post_json_object['id'])
    return False


def has_object_string(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have an object string field?
    """
    if post_json_object.get('object'):
        if isinstance(post_json_object['object'], str):
            return True
        if debug:
            if post_json_object.get('type'):
                print('DEBUG: ' + post_json_object['type'] +
                      ' object is not a string')
    if debug:
        print('No object field within post ' + post_json_object['id'])
    return False


def get_new_post_endpoints() -> []:
    """Returns a list of endpoints for new posts
    """
    return (
        'newpost', 'newblog', 'newunlisted', 'newfollowers', 'newdm',
        'newreminder', 'newreport', 'newquestion', 'newshare', 'newwanted',
        'editblogpost'
    )


def get_fav_filename_from_url(base_dir: str, favicon_url: str) -> str:
    """Returns the cached filename for a favicon based upon its url
    """
    if '://' in favicon_url:
        favicon_url = favicon_url.split('://')[1]
    if '/favicon.' in favicon_url:
        favicon_url = favicon_url.replace('/favicon.', '.')
    return base_dir + '/favicons/' + favicon_url.replace('/', '-')


def valid_hash_tag(hashtag: str) -> bool:
    """Returns true if the give hashtag contains valid characters
    """
    # long hashtags are not valid
    if len(hashtag) >= 32:
        return False
    # numbers are not permitted to be hashtags
    if hashtag.isdigit():
        return False
    if set(hashtag).issubset(VALID_HASHTAG_CHARS):
        return True
    if _is_valid_language(hashtag):
        return True
    return False


def convert_published_to_local_timezone(published, timezone: str) -> str:
    """Converts a post published time into local time
    """
    from_zone = tz.gettz('UTC')
    if timezone:
        try:
            to_zone = tz.gettz(timezone)
        except BaseException:
            pass
    if not timezone:
        return published

    utc = published.replace(tzinfo=from_zone)
    local_time = utc.astimezone(to_zone)
    return local_time


def load_account_timezones(base_dir: str) -> {}:
    """Returns a dictionary containing the preferred timezone for each account
    """
    account_timezone = {}
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if acct.startswith('inbox@') or acct.startswith('Actor@'):
                continue
            acct_directory = os.path.join(base_dir + '/accounts', acct)
            tz_filename = acct_directory + '/timezone.txt'
            if not os.path.isfile(tz_filename):
                continue
            timezone = None
            with open(tz_filename, 'r', encoding='utf-8') as fp_timezone:
                timezone = fp_timezone.read().strip()
            if timezone:
                nickname = acct.split('@')[0]
                account_timezone[nickname] = timezone
        break
    return account_timezone


def load_bold_reading(base_dir: str) -> {}:
    """Returns a dictionary containing the bold reading status for each account
    """
    bold_reading = {}
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if acct.startswith('inbox@') or acct.startswith('Actor@'):
                continue
            bold_reading_filename = \
                base_dir + '/accounts/' + acct + '/.boldReading'
            if os.path.isfile(bold_reading_filename):
                nickname = acct.split('@')[0]
                bold_reading[nickname] = True
        break
    return bold_reading


def get_account_timezone(base_dir: str, nickname: str, domain: str) -> str:
    """Returns the timezone for the given account
    """
    tz_filename = \
        acct_dir(base_dir, nickname, domain) + '/timezone.txt'
    if not os.path.isfile(tz_filename):
        return None
    timezone = None
    with open(tz_filename, 'r', encoding='utf-8') as fp_timezone:
        timezone = fp_timezone.read().strip()
    return timezone


def set_account_timezone(base_dir: str, nickname: str, domain: str,
                         timezone: str) -> None:
    """Sets the timezone for the given account
    """
    tz_filename = \
        acct_dir(base_dir, nickname, domain) + '/timezone.txt'
    timezone = timezone.strip()
    with open(tz_filename, 'w+', encoding='utf-8') as fp_timezone:
        fp_timezone.write(timezone)


def is_onion_request(calling_domain: str, referer_domain: str,
                     domain: str, onion_domain: str) -> bool:
    """Do the given domains indicate that this is a request
    from an onion instance
    """
    if not onion_domain:
        return False
    if domain == onion_domain:
        return True
    if calling_domain.endswith('.onion'):
        return True
    if not referer_domain:
        return False
    if referer_domain.endswith('.onion'):
        return True
    return False


def is_i2p_request(calling_domain: str, referer_domain: str,
                   domain: str, i2p_domain: str) -> bool:
    """Do the given domains indicate that this is a request
    from an i2p instance
    """
    if not i2p_domain:
        return False
    if domain == i2p_domain:
        return True
    if calling_domain.endswith('.i2p'):
        return True
    if not referer_domain:
        return False
    if referer_domain.endswith('.i2p'):
        return True
    return False


def disallow_announce(content: str, attachment: [], capabilities: {}) -> bool:
    """Are announces/boosts not allowed for the given post?
    """
    # pixelfed style capabilities
    if capabilities.get('announce'):
        if isinstance(capabilities['announce'], str):
            if not capabilities['announce'].endswith('#Public'):
                # TODO handle non-public announce permissions
                print('CAPABILITIES: announce ' + capabilities['announce'])
                return True

    # emojis
    disallow_strings = (
        ':boost_no:',
        ':noboost:',
        ':noboosts:',
        ':no_boost:',
        ':no_boosts:',
        ':boosts_no:',
        'dont_repeat',
        'dont_announce',
        'dont_boost',
        'do not boost',
        "don't boost",
        'boost_denied',
        'boosts_denied',
        'boostdenied',
        'boostsdenied'
    )
    content_lower = content.lower()
    for diss in disallow_strings:
        if diss in content_lower:
            return True

    # check for attached images without descriptions
    if isinstance(attachment, list):
        for item in attachment:
            if not isinstance(item, dict):
                continue
            if not item.get('mediaType'):
                continue
            if not item.get('url'):
                continue
            if not item['mediaType'].startswith('image/'):
                continue
            if not item.get('name'):
                # no image description
                return True
    return False


def disallow_reply(content: str) -> bool:
    """Are replies not allowed for the given post?
    """
    disallow_strings = (
        ':reply_no:',
        ':noreply:',
        ':noreplies:',
        ':no_reply:',
        ':no_replies:',
        ':replies_no:',
        'dont_at_me',
        'do not reply',
        "don't reply",
        "don't @ me",
        'dont@me',
        'dontatme'
    )
    content_lower = content.lower()
    for diss in disallow_strings:
        if diss in content_lower:
            return True
    return False


def get_attachment_property_value(property_value: {}) -> (str, str):
    """Returns the fieldname and value for an attachment property
    """
    prop_value = None
    prop_value_name = None
    if property_value.get('value'):
        prop_value = property_value['value']
        prop_value_name = 'value'
    elif property_value.get('http://schema.org#value'):
        prop_value_name = 'http://schema.org#value'
        prop_value = property_value[prop_value_name]
    elif property_value.get('https://schema.org#value'):
        prop_value_name = 'https://schema.org#value'
        prop_value = property_value[prop_value_name]
    elif property_value.get('href'):
        prop_value_name = 'href'
        prop_value = property_value[prop_value_name]
    return prop_value_name, prop_value


def safe_system_string(text: str) -> str:
    """Returns a safe version of a string which can be used within a
    system command
    """
    text = text.replace('$(', '(').replace('`', '')
    return text


def get_json_content_from_accept(accept: str) -> str:
    """returns the json content type for the given accept
    """
    protocol_str = 'application/json'
    if accept:
        if 'application/ld+json' in accept:
            protocol_str = 'application/ld+json'
    return protocol_str


def remove_inverted_text(text: str, system_language: str) -> str:
    """Removes any inverted text from the given string
    """
    if system_language != 'en':
        return text

    inverted_lower = [*"_ʎ_ʍʌ_ʇ_ɹ____ɯʃʞɾıɥƃɟǝ_ɔ_ɐ"]
    inverted_upper = [*"_⅄__ᴧ∩⊥_ᴚΌԀ_ᴎ_⅂⋊ſ__⅁ℲƎ◖Ↄ𐐒∀"]

    start_separator = ''
    separator = '\n'
    if '</p>' in text:
        text = text.replace('<p>', '')
        start_separator = '<p>'
        separator = '</p>'
    paragraphs = text.split(separator)
    new_text = ''
    inverted_list = (inverted_lower, inverted_upper)
    z_value = (ord('z'), ord('Z'))
    for para in paragraphs:
        replaced_chars = 0

        for idx in range(2):
            index = 0
            for test_ch in inverted_list[idx]:
                if test_ch == '_':
                    index += 1
                    continue
                if test_ch in para:
                    para = para.replace(test_ch, chr(z_value[idx] - index))
                    replaced_chars += 1
                index += 1

        if replaced_chars > 2:
            para = para[::-1]
        if para:
            new_text += start_separator + para
            if separator in text:
                new_text += separator

    return new_text


def remove_square_capitals(text: str, system_language: str) -> str:
    """Removes any square capital text from the given string
    """
    if system_language != 'en':
        return text
    offset = ord('A')
    start_value = ord('🅰')
    end_value = start_value + 26
    result = ''
    for text_ch in text:
        text_value = ord(text_ch)
        if text_value < start_value or text_value > end_value:
            result += text_ch
        else:
            result += chr(offset + text_value - start_value)
    return result


def dont_speak_hashtags(content: str) -> str:
    """Ensure that hashtags aren't announced by screen readers
    """
    if not content:
        return content
    return content.replace('>#<span',
                           '><span aria-hidden="true">#</span><span')


def load_min_images_for_accounts(base_dir: str) -> []:
    """Loads a list of nicknames for accounts where all images should
    be minimized by default
    """
    min_images_for_accounts = []
    for subdir, dirs, _ in os.walk(base_dir + '/accounts'):
        for account in dirs:
            if not is_account_dir(account):
                continue
            filename = os.path.join(subdir, account) + '/.minimize_all_images'
            if os.path.isfile(filename):
                min_images_for_accounts.append(account.split('@')[0])
        break
    return min_images_for_accounts


def set_minimize_all_images(base_dir: str,
                            nickname: str, domain: str,
                            minimize: bool,
                            min_images_for_accounts: []) -> None:
    """Add of remove a file indicating that all images for an account
    should be minimized by default
    """
    filename = acct_dir(base_dir, nickname, domain) + '/.minimize_all_images'
    if minimize:
        if nickname not in min_images_for_accounts:
            min_images_for_accounts.append(nickname)
        if not os.path.isfile(filename):
            try:
                with open(filename, 'w+', encoding='utf-8') as fp_min:
                    fp_min.write('\n')
            except OSError:
                print('EX: unable to write ' + filename)
        return

    if nickname in min_images_for_accounts:
        min_images_for_accounts.remove(nickname)
    if os.path.isfile(filename):
        try:
            os.remove(filename)
        except OSError:
            print('EX: unable to delete ' + filename)


def load_reverse_timeline(base_dir: str) -> []:
    """Loads flags for each user indicating whether they prefer to
    see reversed timelines
    """
    reverse_sequence = []
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            nickname = acct.split('@')[0]
            domain = acct.split('@')[1]
            reverse_filename = \
                acct_dir(base_dir, nickname, domain) + '/.reverse_timeline'
            if os.path.isfile(reverse_filename):
                if nickname not in reverse_sequence:
                    reverse_sequence.append(nickname)
        break
    return reverse_sequence


def save_reverse_timeline(base_dir: str, reverse_sequence: []) -> []:
    """Saves flags for each user indicating whether they prefer to
    see reversed timelines
    """
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            nickname = acct.split('@')[0]
            domain = acct.split('@')[1]
            reverse_filename = \
                acct_dir(base_dir, nickname, domain) + '/.reverse_timeline'
            if nickname in reverse_sequence:
                if not os.path.isfile(reverse_filename):
                    try:
                        with open(reverse_filename, 'w+',
                                  encoding='utf-8') as fp_reverse:
                            fp_reverse.write('\n')
                    except OSError:
                        print('EX: failed to save reverse ' + reverse_filename)
            else:
                if os.path.isfile(reverse_filename):
                    try:
                        os.remove(reverse_filename)
                    except OSError:
                        print('EX: failed to delete reverse ' +
                              reverse_filename)
        break


def is_quote_toot(post_json_object: str, content: str) -> bool:
    """Returns true if the given post is a quote toot / quote tweet
    """
    # Pleroma/Misskey implementations
    if post_json_object['object'].get('quoteUri') or \
       post_json_object['object'].get('quoteUrl') or \
       post_json_object['object'].get('quoteReply') or \
       post_json_object['object'].get('toot:quoteReply') or \
       post_json_object['object'].get('_misskey_quote'):
        return True
    # More correct ActivityPub implementation - adding a Link tag
    if post_json_object['object'].get('tag'):
        if isinstance(post_json_object['object']['tag'], list):
            for item in post_json_object['object']['tag']:
                if not isinstance(item, dict):
                    continue
                if item.get('rel'):
                    if isinstance(item['rel'], list):
                        for rel_str in item['rel']:
                            if not isinstance(rel_str, str):
                                continue
                            if '_misskey_quote' in rel_str:
                                return True
                    elif isinstance(item['rel'], str):
                        if '_misskey_quote' in item['rel']:
                            return True
                if not item.get('type'):
                    continue
                if not item.get('mediaType'):
                    continue
                if not isinstance(item['type'], str):
                    continue
                if item['type'] != 'Link':
                    continue
                if not isinstance(item['mediaType'], str):
                    continue
                if 'json' not in item['mediaType']:
                    continue
                return True
    # Twitter-style indicator
    if content:
        if 'QT: ' in content:
            return True
    return False


def license_link_from_name(license: str) -> str:
    """Returns the license link from its name
    """
    if '://' in license:
        return license
    value_upper = license.upper()
    if 'CC-BY-SA-NC' in value_upper or \
       'CC-BY-NC-SA' in value_upper or \
       'CC BY SA NC' in value_upper or \
       'CC BY NC SA' in value_upper:
        value = 'https://creativecommons.org/licenses/by-nc-sa/4.0'
    elif 'CC-BY-SA' in value_upper or 'CC-SA-BY' in value_upper or \
         'CC BY SA' in value_upper or 'CC SA BY' in value_upper:
        value = 'https://creativecommons.org/licenses/by-sa/4.0'
    elif 'CC-BY-NC' in value_upper or 'CC BY NC' in value_upper:
        value = 'https://creativecommons.org/licenses/by-nc/4.0'
    elif 'CC-BY-ND' in value_upper or 'CC BY ND' in value_upper:
        value = 'https://creativecommons.org/licenses/by-nc-nd/4.0'
    elif 'CC-BY' in value_upper or 'CC BY' in value_upper:
        value = 'https://creativecommons.org/licenses/by/4.0'
    elif 'GFDL' in value_upper or 'GNU FREE DOC' in value_upper:
        value = 'https://www.gnu.org/licenses/fdl-1.3.html'
    elif 'OPL' in value_upper or 'OPEN PUBLICATION LIC' in value_upper:
        value = 'https://opencontent.org/openpub'
    elif 'PDDL' in value_upper or 'OPEN DATA COMMONS PUBLIC' in value_upper:
        value = 'https://opendatacommons.org/licenses/pddl'
    elif 'ODBL' in value_upper or 'OPEN DATA COMMONS OPEN' in value_upper:
        value = 'https://opendatacommons.org/licenses/odbl'
    elif 'ODC' in value_upper or 'OPEN DATA COMMONS ATTR' in value_upper:
        value = 'https://opendatacommons.org/licenses/by'
    elif 'OGL' in value_upper or 'OPEN GOVERNMENT LIC' in value_upper:
        value = \
            'https://www.nationalarchives.gov.uk/doc/open-government-licence'
    elif 'PDL' in value_upper or \
         'PUBLIC DOCUMENTATION LIC' in value_upper:
        value = 'http://www.openoffice.org/licenses/PDL.html'
    elif 'FREEBSD' in value_upper:
        value = 'https://www.freebsd.org/copyright/freebsd-doc-license'
    elif 'WTF' in value_upper:
        value = 'http://www.wtfpl.net/txt/copying'
    elif 'UNLICENSE' in value_upper:
        value = 'https://unlicense.org'
    else:
        value = 'https://creativecommons.org/publicdomain/zero/1.0'
    return value


def _get_escaped_chars() -> {}:
    """Returns escaped characters
    """
    return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&apos;"
    }


def escape_text(txt: str) -> str:
    """Escape text for inclusion in xml/rss
    """
    for orig, replacement in _get_escaped_chars().items():
        txt = txt.replace(orig, replacement)
    return txt


def unescaped_text(txt: str) -> str:
    """Escape text for inclusion in xml/rss
    """
    for orig, replacement in _get_escaped_chars().items():
        txt = txt.replace(replacement, orig)
    return txt


def harmless_markup(post_json_object: {}) -> None:
    """render harmless any dangerous markup
    """
    for field_name in ('content', 'summary'):
        if post_json_object['object'].get(field_name):
            if dangerous_markup(post_json_object['object'][field_name],
                                False, ['pre']):
                post_json_object['object'][field_name] = \
                    remove_html(post_json_object['object'][field_name])
            post_json_object['object'][field_name] = \
                remove_markup_tag(post_json_object['object'][field_name],
                                  'pre')
        map_name = field_name + 'Map'
        if post_json_object['object'].get(map_name):
            map_dict = post_json_object['object'][map_name].items()
            for lang, content in map_dict:
                if not isinstance(content, str):
                    continue
                if dangerous_markup(content, False, ['pre']):
                    content = remove_html(content)
                    post_json_object['object'][map_name][lang] = \
                        content
                content = post_json_object['object'][map_name][lang]
                post_json_object['object'][map_name][lang] = \
                    remove_markup_tag(content, 'pre')


def ap_proxy_type(json_object: {}) -> str:
    """Returns a string indicating the proxy for an activitypub post
    or None if not proxied
    See https://codeberg.org/fediverse/fep/src/branch/main/feps/fep-fffd.md
    """
    if not json_object.get('proxyOf'):
        return None
    if not isinstance(json_object['proxyOf'], list):
        return None
    for proxy_dict in json_object['proxyOf']:
        if proxy_dict.get('protocol'):
            if isinstance(proxy_dict['protocol'], str):
                return proxy_dict['protocol']
    return None


def language_right_to_left(language: str) -> bool:
    """is the given language written from right to left?
    """
    rtl_languages = ('ar', 'fa', 'he', 'yi')
    if language in rtl_languages:
        return True
    return False


def is_right_to_left_text(text: str) -> bool:
    """Is the given text right to left?
    Persian \u0600-\u06FF
    Arabic \u0627-\u064a
    Hebrew/Yiddish \u0590-\u05FF\uFB2A-\uFB4E
    """
    unicode_str = '[\u0627-\u064a]|[\u0600-\u06FF]|' + \
        '[\u0590-\u05FF\uFB2A-\uFB4E]'
    pattern = re.compile(unicode_str)

    return len(re.findall(pattern, text)) > (len(text)/2)


def binary_is_image(filename: str, media_binary) -> bool:
    """Returns true if the given file binary data contains an image
    """
    if len(media_binary) < 13:
        return False
    filename_lower = filename.lower()
    bin_is_image = False
    if filename_lower.endswith('.jpeg') or filename_lower.endswith('jpg'):
        if media_binary[6:10] in (b'JFIF', b'Exif'):
            bin_is_image = True
    elif filename_lower.endswith('.ico'):
        if media_binary.startswith(b'\x00\x00\x01\x00'):
            bin_is_image = True
    elif filename_lower.endswith('.png'):
        if media_binary.startswith(b'\211PNG\r\n\032\n'):
            bin_is_image = True
    elif filename_lower.endswith('.webp'):
        if media_binary.startswith(b'RIFF') and media_binary[8:12] == b'WEBP':
            bin_is_image = True
    elif filename_lower.endswith('.gif'):
        if media_binary[:6] in (b'GIF87a', b'GIF89a'):
            bin_is_image = True
    elif filename_lower.endswith('.avif'):
        if media_binary[4:12] == b'ftypavif':
            bin_is_image = True
    elif filename_lower.endswith('.heic'):
        if media_binary[4:12] == b'ftypmif1':
            bin_is_image = True
    elif filename_lower.endswith('.jxl'):
        if media_binary.startswith(b'\xff\n'):
            bin_is_image = True
    elif filename_lower.endswith('.svg'):
        if '<svg' in str(media_binary):
            bin_is_image = True
    return bin_is_image
