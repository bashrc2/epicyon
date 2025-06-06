__filename__ = "utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"
__accounts_data_path__ = None
__accounts_data_path_tests__ = False

import os
import re
import time
import shutil
import datetime
import json
import locale
import idna
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from followingCalendar import add_person_to_calendar
from unicodetext import standardize_text
from formats import get_image_extensions

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


def is_account_dir(dir_name: str) -> bool:
    """Is the given directory an account within /accounts ?
    """
    if '@' not in dir_name:
        return False
    if 'inbox@' in dir_name or 'news@' in dir_name or 'Actor@' in dir_name:
        return False
    return True


def remove_zero_length_strings(text: str) -> str:
    """removes zero length strings from text
    """
    return text.replace('​', '')


def get_url_from_post(url_field) -> str:
    """Returns a url from a post object
    """
    if isinstance(url_field, str):
        return url_field
    if isinstance(url_field, list):
        for url_dict in url_field:
            if not isinstance(url_dict, dict):
                continue
            if 'href' not in url_dict:
                continue
            if 'mediaType' not in url_dict:
                continue
            if not isinstance(url_dict['href'], str):
                continue
            if not isinstance(url_dict['mediaType'], str):
                continue
            if url_dict['mediaType'] != 'text/html':
                continue
            if '://' not in url_dict['href']:
                continue
            return url_dict['href']
    return ''


def get_person_icon(person_json: {}) -> str:
    """Returns an icon url for an actor
    """
    if not person_json.get('icon'):
        return ''
    person_icon = person_json['icon']
    if isinstance(person_icon, list):
        # choose the first icon available
        person_icon = person_json['icon'][0]
    if isinstance(person_icon, dict):
        if person_icon.get('url'):
            url_str = get_url_from_post(person_icon['url'])
            if '.svg' not in url_str.lower():
                return remove_html(url_str)
    else:
        print('DEBUG: get_person_icon icon is not a dict ' +
              str(person_icon))
    return ''


def get_attributed_to(field) -> str:
    """Returns the actor
    """
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        for attrib in field:
            if not isinstance(attrib, dict):
                continue
            if not (attrib.get('type') and attrib.get('id')):
                continue
            if not (isinstance(attrib['type'], str) and
                    isinstance(attrib['id'], str)):
                continue
            if attrib['type'] == 'Person' and \
               resembles_url(attrib['id']):
                return attrib['id']
        if isinstance(field[0], str):
            return field[0]
    return None


def remove_eol(line: str) -> str:
    """Removes line ending characters
    """
    return line.rstrip()


def text_in_file(text: str, filename: str,
                 case_sensitive: bool = True) -> bool:
    """is the given text in the given file?
    """
    if not case_sensitive:
        text = text.lower()

    content = None
    try:
        with open(filename, 'r', encoding='utf-8') as fp_file:
            content = fp_file.read()
    except OSError:
        print('EX: unable to find text in missing file ' + filename)

    if content:
        if not case_sensitive:
            content = content.lower()
        if text in content:
            return True
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
            lang_list_temp: list[str] = []
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
            lang_list: list[str] = []
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
    if '<' + tag not in html and \
       '</' + tag not in html:
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


def remove_header_tags(html: str) -> str:
    """Removes any header tags from the given html text
    """
    header_tags = ('h1', 'h2', 'h3', 'h4', 'h5')
    for tag_str in header_tags:
        html = remove_markup_tag(html, tag_str)
    return html


def get_content_from_post(post_json_object: {}, system_language: str,
                          languages_understood: [],
                          content_type: str) -> str:
    """Returns the content from the post in the given language
    including searching for a matching entry within contentMap
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        # handle quote posts FEP-dd4b, where there is no content within object
        if (content_type != 'content' or
            ('content' in this_post_json['object'] or
             'contentMap' in this_post_json['object'])):
            this_post_json = post_json_object['object']
    map_dict = content_type + 'Map'
    has_contentmap_dict = False
    if this_post_json.get(map_dict):
        if isinstance(this_post_json[map_dict], dict):
            has_contentmap_dict = True
    if not this_post_json.get(content_type) and \
       not has_contentmap_dict:
        return ''
    content = ''
    replacements = {
        '&amp;': '&',
        '<u>': '',
        '</u>': ''
    }
    if has_contentmap_dict:
        if this_post_json[map_dict].get(system_language):
            sys_lang = this_post_json[map_dict][system_language]
            if isinstance(sys_lang, str):
                content = sys_lang
                content = remove_markup_tag(content, 'pre')
                content = replace_strings(content, replacements)
                return standardize_text(content)
        else:
            # is there a contentMap/summaryMap entry for one of
            # the understood languages?
            for lang in languages_understood:
                if not this_post_json[map_dict].get(lang):
                    continue
                map_lang = this_post_json[map_dict][lang]
                if not isinstance(map_lang, str):
                    continue
                content = map_lang
                content = remove_markup_tag(content, 'pre')
                content = replace_strings(content, replacements)
                return standardize_text(content)
    else:
        if isinstance(this_post_json[content_type], str):
            content = this_post_json[content_type]
            content = replace_strings(content, replacements)
            content = remove_markup_tag(content, 'pre')
    return standardize_text(content)


def get_language_from_post(post_json_object: {}, system_language: str,
                           languages_understood: [],
                           content_type: str) -> str:
    """Returns the content language from the post
    including searching for a matching entry within contentMap
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    if not this_post_json.get(content_type):
        return system_language
    map_dict = content_type + 'Map'
    if not this_post_json.get(map_dict):
        return system_language
    if not isinstance(this_post_json[map_dict], dict):
        return system_language
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
    post_attachments = get_post_attachments(post_json_object)
    if not post_attachments:
        return ''
    descriptions = ''
    for attach in post_attachments:
        if not isinstance(attach, dict):
            print('WARN: attachment is not a dict ' + str(attach))
            continue
        if not attach.get('name'):
            continue
        descriptions += attach['name'] + ' '
        if attach.get('url'):
            descriptions += get_url_from_post(attach['url']) + ' '
    return descriptions.strip()


def _valid_summary(possible_summary: str) -> bool:
    """Returns true if the given summary field is valid
    """
    if not isinstance(possible_summary, str):
        return False
    if len(possible_summary) < 2:
        return False
    return True


def get_summary_from_post(post_json_object: {}, system_language: str,
                          languages_understood: []) -> str:
    """Returns the summary from the post in the given language
    including searching for a matching entry within summaryMap.
    """
    summary_str = \
        get_content_from_post(post_json_object, system_language,
                              languages_understood, 'summary')
    if not summary_str:
        # Also try the "name" field if summary is not available.
        # See https://codeberg.org/
        # fediverse/fep/src/branch/main/fep/b2b8/fep-b2b8.md
        obj = post_json_object
        if has_object_dict(post_json_object):
            obj = post_json_object['object']
        if obj.get('type'):
            if isinstance(obj['type'], str):
                if obj['type'] == 'Article':
                    summary_str = \
                        get_content_from_post(post_json_object,
                                              system_language,
                                              languages_understood, 'name')
    if summary_str:
        summary_str = summary_str.strip()
        if not _valid_summary(summary_str):
            summary_str = ''
    return summary_str


def get_base_content_from_post(post_json_object: {},
                               system_language: str) -> str:
    """Returns the content from the post in the given language
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        # handle quote posts FEP-dd4b, where there is no content within object
        if 'content' in this_post_json['object'] or \
           'contentMap' in this_post_json['object']:
            this_post_json = post_json_object['object']
    if 'contentMap' in this_post_json:
        if isinstance(this_post_json['contentMap'], dict):
            if this_post_json['contentMap'].get(system_language):
                return this_post_json['contentMap'][system_language]
    if 'content' not in this_post_json:
        return ''
    return this_post_json['content']


def data_dir_testing(base_dir: str) -> None:
    """During unit tests __accounts_data_path__ should not be retained
    """
    global __accounts_data_path__
    global __accounts_data_path_tests__
    __accounts_data_path_tests__ = True
    __accounts_data_path__ = base_dir + '/accounts'
    print('Data directory is in testing mode')


def set_accounts_data_dir(base_dir: str, accounts_data_path: str) -> None:
    """Sets the directory used to store instance accounts data
    """
    if not accounts_data_path:
        return

    accounts_data_path_filename = base_dir + '/data_path.txt'
    if os.path.isfile(accounts_data_path_filename):
        # read the existing path
        path = None
        try:
            with open(accounts_data_path_filename, 'r',
                      encoding='utf-8') as fp_accounts:
                path = fp_accounts.read()
        except OSError:
            print('EX: unable to read ' + accounts_data_path_filename)
        if path.strip() == accounts_data_path:
            # path is already set, so avoid writing it again
            return

    try:
        with open(accounts_data_path_filename, 'w+',
                  encoding='utf-8') as fp_accounts:
            fp_accounts.write(accounts_data_path)
    except OSError:
        print('EX: unable to write ' + accounts_data_path_filename)


def data_dir(base_dir: str) -> str:
    """Returns the directory where account data is stored
    """
    global __accounts_data_path__
    global __accounts_data_path_tests__
    if __accounts_data_path_tests__:
        __accounts_data_path__ = base_dir + '/accounts'
        return __accounts_data_path__

    if not __accounts_data_path__:
        # the default path for accounts data
        __accounts_data_path__ = base_dir + '/accounts'

        # is an alternative path set?
        accounts_data_path_filename = base_dir + '/data_path.txt'
        if os.path.isfile(accounts_data_path_filename):
            path = None
            try:
                with open(accounts_data_path_filename, 'r',
                          encoding='utf-8') as fp_accounts:
                    path = fp_accounts.read()
            except OSError:
                print('EX: unable to read ' + accounts_data_path_filename)
            if path:
                __accounts_data_path__ = path.strip()
                print('Accounts data path set to ' + __accounts_data_path__)

    return __accounts_data_path__


def acct_dir(base_dir: str, nickname: str, domain: str) -> str:
    """Returns the directory for an account on this instance
    """
    return data_dir(base_dir) + '/' + nickname + '@' + domain


def acct_handle_dir(base_dir: str, handle: str) -> str:
    """Returns the directory for an account on this instance
    """
    return data_dir(base_dir) + '/' + handle


def refresh_newswire(base_dir: str) -> None:
    """Causes the newswire to be updates after a change to user accounts
    """
    refresh_newswire_filename = data_dir(base_dir) + '/.refresh_newswire'
    if os.path.isfile(refresh_newswire_filename):
        return
    try:
        with open(refresh_newswire_filename, 'w+',
                  encoding='utf-8') as fp_refresh:
            fp_refresh.write('\n')
    except OSError:
        print('EX: refresh_newswire unable to write ' +
              refresh_newswire_filename)


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
    if not path_str:
        return False

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


def remove_html(content: str) -> str:
    """Removes html links from the given content.
    Used to ensure that profile descriptions don't contain dubious content
    """
    if '<' not in content:
        return content
    removing = False
    replacements = {
        '<a href': ' <a href',
        '<q>': '"',
        '</q>': '"',
        '</p>': '\n\n',
        '<br>': '\n'
    }
    content = replace_strings(content, replacements)
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


def get_memorials(base_dir: str) -> str:
    """Returns the nicknames for memorial accounts
    """
    memorial_file = data_dir(base_dir) + '/memorial'
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
    memorial_file = data_dir(base_dir) + '/memorial'
    try:
        with open(memorial_file, 'w+', encoding='utf-8') as fp_memorial:
            fp_memorial.write(memorial_str)
    except OSError:
        print('EX: unable to write ' + memorial_file)


def _create_config(base_dir: str) -> None:
    """Creates a configuration file
    """
    config_filename = base_dir + '/config.json'
    if os.path.isfile(config_filename):
        return
    config_json = {}
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


def get_config_param(base_dir: str, variable_name: str) -> str:
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


def get_followers_list(base_dir: str,
                       nickname: str, domain: str,
                       follow_file: str = 'following.txt') -> []:
    """Returns a list of followers for the given account
    """
    filename = acct_dir(base_dir, nickname, domain) + '/' + follow_file

    if not os.path.isfile(filename):
        return []

    lines: list[str] = []
    try:
        with open(filename, 'r', encoding='utf-8') as fp_foll:
            lines = fp_foll.readlines()
    except OSError:
        print('EX: get_followers_list unable to read ' + filename)

    if lines:
        for i, _ in enumerate(lines):
            lines[i] = lines[i].strip()
        return lines
    return []


def get_followers_of_person(base_dir: str,
                            nickname: str, domain: str,
                            follow_file: str = 'following.txt') -> []:
    """Returns a list containing the followers of the given person
    Used by the shared inbox to know who to send incoming mail to
    """
    followers: list[str] = []
    domain = remove_domain_port(domain)
    handle = nickname + '@' + domain
    handle_dir = acct_handle_dir(base_dir, handle)
    if not os.path.isdir(handle_dir):
        return followers
    dir_str = data_dir(base_dir)
    for subdir, dirs, _ in os.walk(dir_str):
        for account in dirs:
            filename = os.path.join(subdir, account) + '/' + follow_file
            if account == handle or \
               account.startswith('inbox@') or \
               account.startswith('Actor@') or \
               account.startswith('news@'):
                continue
            if not os.path.isfile(filename):
                continue
            try:
                with open(filename, 'r', encoding='utf-8') as fp_following:
                    for following_handle in fp_following:
                        following_handle2 = remove_eol(following_handle)
                        if following_handle2 != handle:
                            continue
                        if account not in followers:
                            followers.append(account)
                        break
            except OSError as exc:
                print('EX: get_followers_of_person unable to read ' +
                      filename + ' ' + str(exc))
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


def save_json(json_object: {}, filename: str) -> bool:
    """Saves json to a file
    """
    if not isinstance(json_object, dict):
        if not isinstance(json_object, list):
            print('EX: save_json object is not json ' + str(json_object))
            return False

    tries = 1
    while tries <= 5:
        try:
            with open(filename, 'w+', encoding='utf-8') as fp_json:
                fp_json.write(json.dumps(json_object))
                return True
        except OSError as exc:
            print('EX: save_json ' + str(tries) + ' ' + str(filename) +
                  ' ' + str(exc))
            if exc.errno == 36:
                # filename too long
                break
            time.sleep(1)
            tries += 1
    return False


def load_json(filename: str) -> {}:
    """Makes a few attempts to load a json formatted file
    """
    if '/Actor@' in filename:
        filename = filename.replace('/Actor@', '/inbox@')

    json_object = None
    data = None

    # load from file
    try:
        with open(filename, 'r', encoding='utf-8') as fp_json:
            data = fp_json.read()
    except OSError as exc:
        print('EX: load_json exception ' + str(filename) + ' ' + str(exc))
        return json_object

    # check that something was loaded
    if not data:
        print('EX: load_json no data ' + str(filename))
        return json_object

    # convert to json
    try:
        json_object = json.loads(data)
    except BaseException as exc:
        print('EX: load_json exception ' + str(filename) + ' ' + str(exc))
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
            with open(filename, 'r', encoding='utf-8') as fp_json:
                data = fp_json.read()
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


def evil_incarnate() -> []:
    """Hardcoded blocked domains
    """
    return ('fedilist.com', 'gab.com', 'gabfed.com', 'spinster.xyz')


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
    if not federation_list:
        return True
    domain = remove_domain_port(domain)
    if domain in federation_list:
        return True
    return False


def get_local_network_addresses() -> []:
    """Returns patterns for local network address detection
    """
    return ('localhost', '127.0.', '192.168', '10.0.')


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
    return ('/statuses/', '/objects/', '/honk/', '/p/', '/h/', '/api/posts/',
            '/note/', '/notes/', '/comment/', '/post/', '/item/', '/videos/',
            '/button/', '/x/', '/o/', '/posts/', '/items/', '/object/', '/r/',
            '/content/', '/federation/', '/elsewhere/', '/article/',
            '/activity/', '/blog/', '/app.bsky.feed.post/')


def contains_statuses(url: str) -> bool:
    """Whether the given url contains /statuses/
    """
    statuses_list = _get_statuses_list()
    for status_str in statuses_list:
        if status_str in url:
            return True

    # wordpress-style blog post
    today = datetime.date.today()
    if '/' + str(today.year) + '/' in url or \
       '/' + str(today.year - 1) + '/' in url:
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
            actor_json = load_json(cached_actor_filename)
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
            actor_json = load_json(cached_actor_filename)
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

    # handle brid.gy urls
    actor = actor.replace('at://did:', 'did:')

    users_paths = get_user_paths()
    for possible_path in users_paths:
        if possible_path not in actor:
            continue
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
    return ('/users/', '/profile/', '/accounts/', '/channel/',
            '/u/', '/c/', '/m/', '/a/', '/video-channels/',
            '/nieuws/author/', '/author/', '/federation/user/',
            '/activitypub/', '/actors/', '/snac/', '/@/', '/~/',
            '/fediverse/blog/', '/user/', '/@', '/api/collections/',
            '/feed/', '/actor/', '/ap/')


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
        if possible_path not in actor:
            continue
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
        try:
            with open(petnames_filename, 'w+',
                      encoding='utf-8') as fp_petnames:
                fp_petnames.write(petname_lookup_entry)
        except OSError:
            print('EX: _set_default_pet_name unable to write ' +
                  petnames_filename)
        return

    try:
        with open(petnames_filename, 'r', encoding='utf-8') as fp_petnames:
            petnames_str = fp_petnames.read()
            if petnames_str:
                petnames_list = petnames_str.split('\n')
                for pet in petnames_list:
                    if pet.startswith(follow_nickname + ' '):
                        # petname already exists
                        return
    except OSError:
        print('EX: _set_default_pet_name unable to read 1 ' +
              petnames_filename)
    # petname doesn't already exist
    try:
        with open(petnames_filename, 'a+', encoding='utf-8') as fp_petnames:
            fp_petnames.write(petname_lookup_entry)
    except OSError:
        print('EX: _set_default_pet_name unable to read 2 ' +
              petnames_filename)


def follow_person(base_dir: str, nickname: str, domain: str,
                  follow_nickname: str, follow_domain: str,
                  federation_list: [], debug: bool,
                  group_account: bool,
                  follow_file: str) -> bool:
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
            try:
                with open(unfollowed_filename, 'r',
                          encoding='utf-8') as fp_unfoll:
                    lines = fp_unfoll.readlines()
                    for line in lines:
                        if handle_to_follow not in line:
                            new_lines += line
            except OSError:
                print('EX: follow_person unable to read ' +
                      unfollowed_filename)
            try:
                with open(unfollowed_filename, 'w+',
                          encoding='utf-8') as fp_unfoll:
                    fp_unfoll.write(new_lines)
            except OSError:
                print('EX: follow_person unable to write ' +
                      unfollowed_filename)

    dir_str = data_dir(base_dir)
    if not os.path.isdir(dir_str):
        os.mkdir(dir_str)
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
            with open(filename, 'r+', encoding='utf-8') as fp_foll:
                content = fp_foll.read()
                if handle_to_follow + '\n' not in content:
                    fp_foll.seek(0, 0)
                    fp_foll.write(handle_to_follow + '\n' + content)
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
        try:
            with open(filename, 'w+', encoding='utf-8') as fp_foll:
                fp_foll.write(handle_to_follow + '\n')
        except OSError:
            print('EX: follow_person unable to write ' + filename)

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

    account_dir = data_dir(base_dir) + '/news@' + domain + '/'
    post_filename = account_dir + 'outbox/' + post_url
    if os.path.isfile(post_filename):
        return post_filename

    return None


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
    account_dir = data_dir(base_dir) + '/news' + '@' + domain + '/'
    post_filename = account_dir + 'outbox/' + post_url
    if os.path.isfile(post_filename):
        return post_filename

    # is it in the announce cache?
    post_filename = base_dir + '/cache/announce/' + nickname + '/' + post_url
    if os.path.isfile(post_filename):
        return post_filename

    # print('WARN: unable to locate ' + nickname + ' ' + post_url)
    return None


def get_reply_interval_hours(base_dir: str, nickname: str, domain: str,
                             default_reply_interval_hrs: int) -> int:
    """Returns the reply interval for the given account.
    The reply interval is the number of hours after a post being made
    during which replies are allowed
    """
    reply_interval_filename = \
        acct_dir(base_dir, nickname, domain) + '/.reply_interval_hours'
    if os.path.isfile(reply_interval_filename):
        try:
            with open(reply_interval_filename, 'r',
                      encoding='utf-8') as fp_interval:
                hours_str = fp_interval.read()
                if hours_str.isdigit():
                    return int(hours_str)
        except OSError:
            print('EX: get_reply_interval_hours unable to read ' +
                  reply_interval_filename)
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
                  encoding='utf-8') as fp_interval:
            fp_interval.write(str(reply_interval_hours))
            return True
    except OSError:
        print('EX: set_reply_interval_hours unable to save reply interval ' +
              str(reply_interval_filename) + ' ' +
              str(reply_interval_hours))
    return False


def _remove_attachment(base_dir: str, http_prefix: str,
                       nickname: str, domain: str, post_json: {}) -> None:
    """Removes media files for an attachment
    """
    post_attachments = get_post_attachments(post_json)
    if not post_attachments:
        return
    if not post_attachments[0].get('url'):
        return
    attachment_url = get_url_from_post(post_attachments[0]['url'])
    if not attachment_url:
        return
    attachment_url = remove_html(attachment_url)

    # remove the media
    media_filename = base_dir + '/' + \
        attachment_url.replace(http_prefix + '://' + domain + '/', '')
    if os.path.isfile(media_filename):
        try:
            os.remove(media_filename)
        except OSError:
            print('EX: _remove_attachment unable to delete media file ' +
                  str(media_filename))

    # remove from the log file
    account_dir = acct_dir(base_dir, nickname, domain)
    account_media_log_filename = account_dir + '/media_log.txt'
    if os.path.isfile(account_media_log_filename):
        search_filename = media_filename.replace(base_dir, '')
        media_log_text = ''
        try:
            with open(account_media_log_filename, 'r',
                      encoding='utf-8') as fp_log:
                media_log_text = fp_log.read()
        except OSError:
            print('EX: _remove unable to read media log for ' + nickname)
        if search_filename + '\n' in media_log_text:
            media_log_text = media_log_text.replace(search_filename + '\n', '')
            try:
                with open(account_media_log_filename, 'w+',
                          encoding='utf-8') as fp_log:
                    fp_log.write(media_log_text)
            except OSError:
                print('EX: unable to write media log after removal for ' +
                      nickname)

    # remove the transcript
    if os.path.isfile(media_filename + '.vtt'):
        try:
            os.remove(media_filename + '.vtt')
        except OSError:
            print('EX: _remove_attachment unable to delete media transcript ' +
                  str(media_filename) + '.vtt')

    # remove the etag
    etag_filename = media_filename + '.etag'
    if os.path.isfile(etag_filename):
        try:
            os.remove(etag_filename)
        except OSError:
            print('EX: _remove_attachment unable to delete etag file ' +
                  str(etag_filename))
    post_json['attachment']: list[dict] = []


def remove_post_from_index(post_url: str, debug: bool,
                           index_file: str) -> None:
    """Removes a url from a box index
    """
    if not os.path.isfile(index_file):
        return
    post_id = remove_id_ending(post_url)
    if not text_in_file(post_id, index_file):
        return
    lines: list[str] = []
    try:
        with open(index_file, 'r', encoding='utf-8') as fp_mod1:
            lines = fp_mod1.readlines()
    except OSError as exc:
        print('EX: remove_post_from_index unable to read ' +
              index_file + ' ' + str(exc))

    if not lines:
        return
    try:
        with open(index_file, 'w+',
                  encoding='utf-8') as fp_mod2:
            for line in lines:
                if line.strip("\n").strip("\r") != post_id:
                    fp_mod2.write(line)
                    continue
                if debug:
                    print('DEBUG: removed ' + post_id +
                          ' from index ' + index_file)
    except OSError as exc:
        print('EX: ' +
              'remove_post_from_index unable to write ' +
              index_file + ' ' + str(exc))


def remove_moderation_post_from_index(base_dir: str, post_url: str,
                                      debug: bool) -> None:
    """Removes a url from the moderation index
    """
    moderation_index_file = data_dir(base_dir) + '/moderation.txt'
    remove_post_from_index(post_url, debug, moderation_index_file)


def _is_reply_to_blog_post(base_dir: str, nickname: str, domain: str,
                           post_json_object: str) -> bool:
    """Is the given post a reply to a blog post?
    """
    if not has_object_dict(post_json_object):
        return False
    reply_id = get_reply_to(post_json_object['object'])
    if not reply_id:
        return False
    if not isinstance(reply_id, str):
        return False
    blogs_index_filename = \
        acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogs_index_filename):
        return False
    post_id = remove_id_ending(reply_id)
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
    try:
        with open(replies_filename, 'r', encoding='utf-8') as fp_replies:
            for reply_id in fp_replies:
                reply_file = locate_post(base_dir, nickname, domain, reply_id)
                if not reply_file:
                    continue
                if not os.path.isfile(reply_file):
                    continue
                delete_post(base_dir, http_prefix,
                            nickname, domain, reply_file, debug,
                            recent_posts_cache, manual)
    except OSError:
        print('EX: _delete_post_remove_replies unable to read ' +
              replies_filename)
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
                       post_json_object: {}) -> None:
    """Removes cached html file for the given post
    """
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain, post_json_object)
    if not cached_post_filename:
        return
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
    try:
        with open(tag_index_filename, 'r', encoding='utf-8') as fp_index:
            lines = fp_index.readlines()
    except OSError:
        print('EX: _remove_post_id_from_tag_index unable to read ' +
              tag_index_filename)
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
        try:
            with open(tag_index_filename, 'w+',
                      encoding='utf-8') as fp_index:
                fp_index.write(newlines)
        except OSError:
            print('EX: _remove_post_id_from_tag_index unable to write ' +
                  tag_index_filename)


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
    # Due to lack of AP specification maintenance, a conversation can also be
    # referred to as a thread or (confusingly) "context"
    if not post_json_object['object'].get('conversation') and \
       not post_json_object['object'].get('thread') and \
       not post_json_object['object'].get('context'):
        return False
    if not post_json_object['object'].get('id'):
        return False
    conversation_dir = \
        acct_dir(base_dir, nickname, domain) + '/conversation'
    if post_json_object['object'].get('conversation'):
        conversation_id = post_json_object['object']['conversation']
    elif post_json_object['object'].get('context'):
        conversation_id = post_json_object['object']['context']
    else:
        conversation_id = post_json_object['object']['thread']
    if not isinstance(conversation_id, str):
        return False
    conversation_id = conversation_id.replace('/', '#')
    post_id = post_json_object['object']['id']
    conversation_filename = conversation_dir + '/' + conversation_id
    if not os.path.isfile(conversation_filename):
        return False
    conversation_str = ''
    try:
        with open(conversation_filename, 'r', encoding='utf-8') as fp_conv:
            conversation_str = fp_conv.read()
    except OSError:
        print('EX: _delete_conversation_post unable to read ' +
              conversation_filename)
    if post_id + '\n' not in conversation_str:
        return False
    conversation_str = conversation_str.replace(post_id + '\n', '')
    if conversation_str:
        try:
            with open(conversation_filename, 'w+',
                      encoding='utf-8') as fp_conv:
                fp_conv.write(conversation_str)
        except OSError:
            print('EX: _delete_conversation_post unable to write ' +
                  conversation_filename)
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
        if post_json_object['object']['type'] not in ('Note', 'Event',
                                                      'Page', 'Patch',
                                                      'EncryptedMessage',
                                                      'Article'):
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


def _is_remote_dm(domain_full: str, post_json_object: {}) -> bool:
    """Is the given post a DM from a different domain?
    """
    if not is_dm(post_json_object):
        return False
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    if this_post_json.get('attributedTo'):
        attrib = get_attributed_to(this_post_json['attributedTo'])
        if attrib:
            if '://' + domain_full not in attrib:
                return True
    return False


def delete_post(base_dir: str, http_prefix: str,
                nickname: str, domain: str, post_filename: str,
                debug: bool, recent_posts_cache: {},
                manual: bool) -> None:
    """Recursively deletes a post and its replies and attachments
    """
    post_json_object = load_json(post_filename)
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
    _remove_attachment(base_dir, http_prefix, nickname, domain,
                       post_json_object)

    extensions = (
        'votes', 'arrived', 'muted', 'tts', 'reject', 'mitm', 'edits', 'seen'
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
    """Returns a list of reserved words which should not be
    used for nicknames in order to avoid confusion
    """
    return ('inbox', 'dm', 'outbox', 'following',
            'public', 'followers', 'category',
            'channel', 'calendar', 'video-channels',
            'videos', 'tlreplies', 'tlmedia', 'tlblogs',
            'tlblogs', 'tlfeatures',
            'moderation', 'moderationaction',
            'activity', 'undo', 'pinned',
            'actor', 'Actor', 'instance.actor',
            'reply', 'replies', 'question', 'like',
            'likes', 'user', 'users', 'statuses',
            'tags', 'author', 'accounts', 'headers', 'snac',
            'channels', 'profile', 'u', 'c',
            'updates', 'repeat', 'announce',
            'shares', 'fonts', 'icons', 'avatars',
            'welcome', 'helpimages',
            'bookmark', 'bookmarks', 'tlbookmarks',
            'ignores', 'linksmobile', 'newswiremobile',
            'minimal', 'search', 'eventdelete',
            'searchemoji', 'catalog', 'conversationId', 'thread',
            'mention', 'http', 'https', 'ipfs', 'ipns',
            'ontologies', 'data', 'postedit', 'moved',
            'inactive', 'activitypub', 'actors',
            'note', 'notes', 'offers', 'wanted', 'honk',
            'button', 'post', 'item', 'comment',
            'content', 'federation', 'elsewhere',
            'article', 'activity')


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
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
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
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
        for account in dirs:
            if not is_account_dir(account):
                continue
            last_used_filename = \
                dir_str + '/' + account + '/.lastUsed'
            if not os.path.isfile(last_used_filename):
                continue
            try:
                with open(last_used_filename, 'r',
                          encoding='utf-8') as fp_last_used:
                    last_used = fp_last_used.read()
                    if last_used.isdigit():
                        time_diff = curr_time - int(last_used)
                        if time_diff < month_seconds:
                            account_ctr += 1
            except OSError:
                print('EX: no_of_active_accounts_monthly unable to read ' +
                      last_used_filename)
        break
    return account_ctr


def copytree(src: str, dst: str, symlinks: str, ignore: bool) -> None:
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


def file_last_modified(filename: str) -> str:
    """Returns the date when a file was last modified
    """
    time_val = os.path.getmtime(filename)
    modified_time = \
        datetime.datetime.fromtimestamp(time_val, datetime.timezone.utc)
    return modified_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_css(base_dir: str, css_filename: str) -> str:
    """Retrieves the css for a given file, or from a cache
    """
    # does the css file exist?
    if not os.path.isfile(css_filename):
        return None

    try:
        with open(css_filename, 'r', encoding='utf-8') as fp_css:
            css = fp_css.read()
            return css
    except OSError:
        print('EX: get_css unable to read ' + css_filename)

    return None


def get_file_case_insensitive(path: str) -> str:
    """Returns a case specific filename given a case insensitive version of it
    """
    if os.path.isfile(path):
        return path
    if path != path.lower():
        if os.path.isfile(path.lower()):
            return path.lower()
    return None


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
                   post_id: str, recent_posts_cache: {},
                   debug: bool) -> None:
    """ Marks the given post as rejected,
    for example an announce which is too old
    """
    post_filename = locate_post(base_dir, nickname, domain, post_id)
    if not post_filename:
        return

    post_url = None
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

    try:
        with open(post_filename + '.reject', 'w+',
                  encoding='utf-8') as fp_reject:
            fp_reject.write('\n')
    except OSError:
        print('EX: reject_post_id unable to write ' +
              post_filename + '.reject')

    # if the post is in the inbox index then remove it
    index_file = \
        acct_dir(base_dir, nickname, domain) + '/inbox.index'
    if not post_url:
        index_filename = post_filename
        if '/' in post_filename:
            index_filename = post_filename.split('/')[-1]
        post_url = remove_eol(index_filename)
        post_url = post_url.replace('.json', '').strip()
    post_url2 = post_url.replace('/', '#') + '.json'
    remove_post_from_index(post_url2, debug, index_file)


def load_translations_from_file(base_dir: str, language: str) -> ({}, str):
    """Returns the translations dictionary
    """
    if not os.path.isdir(base_dir + '/translations'):
        print('ERROR: translations directory not found')
        return None, None
    if not language:
        system_language = locale.getlocale()[0]
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
        name_value_lower = name_value.lower()
        if not name_value_lower.startswith(property_name) and \
           not name_value_lower.endswith(property_name):
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
        prop_value = remove_html(property_value[prop_value_name])
        for prefix in prefixes:
            if prop_value.startswith(prefix):
                prefix_found = True
                break
        if not prefix_found:
            continue
        if '.' not in prop_value:
            continue
        if ' ' in prop_value:
            continue
        if ',' in prop_value:
            continue
        return prop_value
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


def valid_password(password: str, debug: bool) -> bool:
    """Returns true if the given password contains valid characters and
    is within a range of lengths
    """
    if len(password) < 8 or len(password) > 1024:
        if debug:
            print('WARN: password length out of range (8-255): ' +
                  str(len(password)))
        return False
    # check for trailing end of line or carriage returns
    if remove_eol(password) != password:
        return False
    return True


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
    languages_str: list[str] = []
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
    categories: list[str] = []
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


def get_actor_from_post(post_json_object: {}) -> str:
    """Gets the actor url from the given post
    """
    if not post_json_object.get('actor'):
        return ''

    actor_id = None
    if isinstance(post_json_object['actor'], str):
        # conventionally the actor is just a string url
        actor_id = post_json_object['actor']
    elif isinstance(post_json_object['actor'], dict):
        # in pixelfed/friendica the actor is sometimes a dict
        # with a lot of properties
        if post_json_object['actor'].get('id'):
            if isinstance(post_json_object['actor']['id'], str):
                actor_id = post_json_object['actor']['id']

    if actor_id:
        # looks vaguely like a url
        if resembles_url(actor_id):
            return actor_id
    return ''


def has_actor(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have an actor?
    """
    if post_json_object.get('actor'):
        actor_url = get_actor_from_post(post_json_object)
        if '#' in actor_url or not actor_url:
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
        'editblogpost', 'newreadingstatus'
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


def load_bold_reading(base_dir: str) -> {}:
    """Returns a dictionary containing the bold reading status for each account
    """
    bold_reading = {}
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
        for acct in dirs:
            if '@' not in acct:
                continue
            if acct.startswith('inbox@') or acct.startswith('Actor@'):
                continue
            bold_reading_filename = dir_str + '/' + acct + '/.boldReading'
            if os.path.isfile(bold_reading_filename):
                nickname = acct.split('@')[0]
                bold_reading[nickname] = True
        break
    return bold_reading


def load_hide_follows(base_dir: str) -> {}:
    """Returns a dictionary containing the hide follows status for each account
    """
    hide_follows = {}
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
        for acct in dirs:
            if '@' not in acct:
                continue
            if acct.startswith('inbox@') or acct.startswith('Actor@'):
                continue
            hide_follows_filename = dir_str + '/' + acct + '/.hideFollows'
            if os.path.isfile(hide_follows_filename):
                nickname = acct.split('@')[0]
                hide_follows[nickname] = True
        break
    return hide_follows


def load_hide_recent_posts(base_dir: str) -> {}:
    """Returns a dictionary containing the hide recent posts status
    for each account
    """
    hide_recent_posts = {}
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
        for acct in dirs:
            if '@' not in acct:
                continue
            if acct.startswith('inbox@') or acct.startswith('Actor@'):
                continue
            hide_recent_posts_filename = \
                dir_str + '/' + acct + '/.hideRecentPosts'
            if os.path.isfile(hide_recent_posts_filename):
                nickname = acct.split('@')[0]
                hide_recent_posts[nickname] = True
        break
    return hide_recent_posts


def _is_onion_request(calling_domain: str, referer_domain: str,
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


def _is_i2p_request(calling_domain: str, referer_domain: str,
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


def disallow_reply(content: str) -> bool:
    """Are replies not allowed for the given post?
    """
    disallow_strings = (
        ':reply_no:',
        ':noreply:',
        ':noreplies:',
        ':no_reply:',
        ':no_replies:',
        ':no_responses:',
        ':replies_no:',
        'dont_at_me',
        'do not reply',
        "don't reply",
        "don't @ me",
        'dont@me',
        'dontatme',
        'noresponses'
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
    min_images_for_accounts: list[str] = []
    dir_str = data_dir(base_dir)
    for subdir, dirs, _ in os.walk(dir_str):
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
    reverse_sequence: list[str] = []
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
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


def save_reverse_timeline(base_dir: str, reverse_sequence: []) -> None:
    """Saves flags for each user indicating whether they prefer to
    see reversed timelines
    """
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
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


def license_link_from_name(license_name: str) -> str:
    """Returns the license link from its name
    """
    if '://' in license_name:
        return license_name
    value_upper = license_name.upper()
    cc_strings1 = ('CC-BY-SA-NC', 'CC-BY-NC-SA', 'CC BY SA NC', 'CC BY NC SA')
    cc_strings2 = ('CC-BY-SA', 'CC-SA-BY', 'CC BY SA', 'CC SA BY')
    if string_contains(value_upper, cc_strings1):
        value = 'https://creativecommons.org/licenses/by-nc-sa/4.0'
    elif string_contains(value_upper, cc_strings2):
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


def valid_content_warning(summary: str) -> str:
    """Returns a validated content warning
    """
    cw_str = remove_html(summary)
    # hashtags within content warnings apparently cause a lot of trouble
    # so remove them
    if '#' in cw_str:
        cw_str = cw_str.replace('#', '').replace('  ', ' ')
    return remove_invalid_chars(cw_str)


def harmless_markup(post_json_object: {}) -> None:
    """render harmless any dangerous markup
    """
    if not isinstance(post_json_object['object'], dict):
        return

    remove_trash = [' id="wordads-inline-marker"']

    for field_name in ('content', 'summary'):
        if post_json_object['object'].get(field_name):
            # tidy up content warnings
            if field_name == 'summary':
                summary = post_json_object['object'][field_name]
                post_json_object['object'][field_name] = \
                    valid_content_warning(summary)

            text = post_json_object['object'][field_name]

            # take out the trash
            for trash in remove_trash:
                if trash in text:
                    post_json_object['object'][field_name] = \
                        text.replace(trash, '')

            # remove things which would cause display issues
            if dangerous_markup(text, False, ['pre']):
                post_json_object['object'][field_name] = remove_html(text)
            post_json_object['object'][field_name] = \
                remove_markup_tag(text, 'pre')

        map_name = field_name + 'Map'
        if post_json_object['object'].get(map_name):
            if isinstance(post_json_object['object'][map_name], dict):
                map_dict = post_json_object['object'][map_name].items()
                for lang, content in map_dict:
                    if not isinstance(content, str):
                        continue

                    # tidy up language mapped content warnings
                    if field_name == 'summary':
                        post_json_object['object'][map_name][lang] = \
                            valid_content_warning(content)
                        content = post_json_object['object'][map_name][lang]

                    # take out the trash
                    for trash in remove_trash:
                        if trash in content:
                            post_json_object['object'][map_name][lang] = \
                                content.replace(trash, '')

                    # remove things which would cause display issues
                    if dangerous_markup(content, False, ['pre']):
                        content = remove_html(content)
                        post_json_object['object'][map_name][lang] = \
                            content
                    content = post_json_object['object'][map_name][lang]
                    post_json_object['object'][map_name][lang] = \
                        remove_markup_tag(content, 'pre')
            else:
                print('WARN: harmless_markup unknown Map ' + map_name + ' ' +
                      str(post_json_object['object'][map_name]))


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


def get_status_count(base_dir: str) -> int:
    """Get the total number of posts
    """
    status_ctr = 0
    accounts_dir = data_dir(base_dir)
    for _, dirs, _ in os.walk(accounts_dir):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            account_dir = os.path.join(accounts_dir, acct + '/outbox')
            for _, _, files2 in os.walk(account_dir):
                status_ctr += len(files2)
                break
        break
    return status_ctr


def lines_in_file(filename: str) -> int:
    """Returns the number of lines in a file
    """
    if os.path.isfile(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as fp_lines:
                return len(fp_lines.read().split('\n'))
        except OSError:
            print('EX: lines_in_file error reading ' + filename)
    return 0


def get_media_url_from_video(post_json_object: {}) -> (str, str, str, str):
    """Within a Video post (eg peertube) return the media details
    """
    media_type = None
    media_url = None
    media_torrent = None
    media_magnet = None
    if not post_json_object.get('url'):
        return media_type, media_url, media_torrent, media_magnet
    if not isinstance(post_json_object['url'], list):
        return media_type, media_url, media_torrent, media_magnet
    for media_link in post_json_object['url']:
        if not isinstance(media_link, dict):
            continue
        if not media_link.get('mediaType'):
            continue
        if not media_link.get('href'):
            continue
        if media_link.get('tag'):
            media_tags = media_link['tag']
            if isinstance(media_tags, list):
                for tag_link in media_tags:
                    if not isinstance(tag_link, dict):
                        continue
                    if not tag_link.get('mediaType'):
                        continue
                    if not tag_link.get('href'):
                        continue
                    if tag_link['mediaType'] == 'video/mp4' or \
                       tag_link['mediaType'] == 'video/ogv':
                        media_type = tag_link['mediaType']
                        media_url = remove_html(tag_link['href'])
                        break
                if media_type and media_url:
                    continue
        if media_link['mediaType'] == 'application/x-bittorrent':
            media_torrent = remove_html(media_link['href'])
        if media_link['href'].startswith('magnet:'):
            media_magnet = remove_html(media_link['href'])
        if media_link['mediaType'] != 'video/mp4' and \
           media_link['mediaType'] != 'video/ogv':
            continue
        if not media_url:
            media_type = media_link['mediaType']
            media_url = remove_html(media_link['href'])
    return media_type, media_url, media_torrent, media_magnet


def get_reply_to(post_json_object: {}) -> str:
    """Returns the reply to link from a post
    """
    if post_json_object.get('inReplyTo'):
        if not isinstance(post_json_object['inReplyTo'], str):
            if isinstance(post_json_object['inReplyTo'], dict):
                if post_json_object['inReplyTo'].get('id'):
                    reply_id = post_json_object['inReplyTo']['id']
                    if isinstance(reply_id, str):
                        return reply_id
            print('WARN: inReplyTo is not a string ' +
                  str(post_json_object['inReplyTo']))
            return ''
        return post_json_object['inReplyTo']
    if post_json_object.get('inReplyToBook'):
        if not isinstance(post_json_object['inReplyToBook'], str):
            if isinstance(post_json_object['inReplyToBook'], dict):
                if post_json_object['inReplyToBook'].get('id'):
                    reply_id = post_json_object['inReplyToBook']['id']
                    if isinstance(reply_id, str):
                        return reply_id
            print('WARN: inReplyToBook is not a string ' +
                  str(post_json_object['inReplyToBook']))
            return ''
        return post_json_object['inReplyToBook']
    return ''


def resembles_url(text: str) -> bool:
    """Does the given text look like a url?
    """
    if '://' in text and '.' in text and \
       ' ' not in text and '<' not in text:
        return True
    return False


def post_summary_contains_links(message_json: {}) -> bool:
    """check if the json post summary contains links
    """
    if not (message_json['object'].get('type') and
            message_json['object'].get('summary')):
        return False

    if message_json['object']['type'] not in ('Person',
                                              'Application', 'Group'):
        if len(message_json['object']['summary']) > 1024:
            actor_url = get_actor_from_post(message_json)
            print('INBOX: summary is too long ' +
                  actor_url + ' ' +
                  message_json['object']['summary'])
            return True
        if '://' in message_json['object']['summary']:
            actor_url = get_actor_from_post(message_json)
            print('INBOX: summary should not contain links ' +
                  actor_url + ' ' +
                  message_json['object']['summary'])
            return True
    else:
        if len(message_json['object']['summary']) > 4096:
            actor_url = get_actor_from_post(message_json)
            print('INBOX: person summary is too long ' +
                  actor_url + ' ' +
                  message_json['object']['summary'])
            return True
    return False


def convert_domains(calling_domain: str, referer_domain: str,
                    msg_str: str, http_prefix: str,
                    domain: str,
                    onion_domain: str,
                    i2p_domain: str) -> str:
    """Convert domains to onion or i2p, depending upon who is asking
    """
    curr_http_prefix = http_prefix + '://'
    if _is_onion_request(calling_domain, referer_domain,
                         domain,
                         onion_domain):
        msg_str = msg_str.replace(curr_http_prefix +
                                  domain,
                                  'http://' +
                                  onion_domain)
    elif _is_i2p_request(calling_domain, referer_domain,
                         domain,
                         i2p_domain):
        msg_str = msg_str.replace(curr_http_prefix +
                                  domain,
                                  'http://' +
                                  i2p_domain)
    return msg_str


def get_instance_url(calling_domain: str,
                     http_prefix: str,
                     domain_full: str,
                     onion_domain: str,
                     i2p_domain: str) -> str:
    """Returns the URL for this instance
    """
    if calling_domain.endswith('.onion') and \
       onion_domain:
        instance_url = 'http://' + onion_domain
    elif (calling_domain.endswith('.i2p') and
          i2p_domain):
        instance_url = 'http://' + i2p_domain
    else:
        instance_url = \
            http_prefix + '://' + domain_full
    return instance_url


def check_bad_path(path: str):
    """for http GET or POST check that the path looks valid
    """
    path_lower = path.lower()
    bad_strings = ('..', '/.', '%2e%2e', '%252e%252e')

    # allow /.well-known/...
    if '/.' in path_lower:
        if path_lower.startswith('/.well-known/') or \
           path_lower.startswith('/users/.well-known/'):
            bad_strings = ('..', '%2e%2e', '%252e%252e')

    if string_contains(path_lower, bad_strings):
        print('WARN: bad path ' + path)
        return True
    return False


def set_premium_account(base_dir: str, nickname: str, domain: str,
                        flag_state: bool) -> bool:
    """ Set or clear the premium account flag
    """
    premium_filename = acct_dir(base_dir, nickname, domain) + '/.premium'
    if os.path.isfile(premium_filename):
        if not flag_state:
            try:
                os.remove(premium_filename)
            except OSError:
                print('EX: unable to remove premium flag ' + premium_filename)
                return False
    else:
        if flag_state:
            try:
                with open(premium_filename, 'w+',
                          encoding='utf-8') as fp_premium:
                    fp_premium.write('\n')
            except OSError:
                print('EX: unable to set premium flag ' + premium_filename)
                return False
    return True


def get_post_attachments(post_json_object: {}) -> []:
    """ Returns the list of attachments for a post
    """
    post_obj = post_json_object
    if has_object_dict(post_json_object):
        post_obj = post_json_object['object']
    if not post_obj.get('attachment'):
        return []
    if isinstance(post_obj['attachment'], list):
        return post_obj['attachment']
    if isinstance(post_obj['attachment'], dict):
        return [post_obj['attachment']]
    return []


def string_ends_with(text: str, possible_endings: []) -> bool:
    """ Does the given text end with at least one of the endings
    """
    for ending in possible_endings:
        if text.endswith(ending):
            return True
    return False


def string_contains(text: str, possible_substrings: []) -> bool:
    """ Does the given text contain at least one of the possible substrings
    """
    for substring in possible_substrings:
        if substring in text:
            return True
    return False


def remove_link_tracking(url: str) -> str:
    """ Removes any web link tracking, such as utm_medium, utm_campaign
    or utm_source
    """
    if '?utm_' not in url:
        return url
    return url.split('?utm_')[0]


def get_image_file(base_dir: str, name: str, directory: str,
                   theme: str) -> (str, str):
    """returns the filenames for an image with the given name
    """
    banner_extensions = get_image_extensions()
    banner_file = ''
    banner_filename = ''
    im_name = name
    for ext in banner_extensions:
        banner_file_test = im_name + '.' + ext
        banner_filename_test = directory + '/' + banner_file_test
        if not os.path.isfile(banner_filename_test):
            continue
        banner_file = banner_file_test
        banner_filename = banner_filename_test
        return banner_file, banner_filename
    # if not found then use the default image
    curr_theme = 'default'
    if theme:
        curr_theme = theme
    directory = base_dir + '/theme/' + curr_theme
    for ext in banner_extensions:
        banner_file_test = name + '.' + ext
        banner_filename_test = directory + '/' + banner_file_test
        if not os.path.isfile(banner_filename_test):
            continue
        banner_file = name + '_' + curr_theme + '.' + ext
        banner_filename = banner_filename_test
        break
    return banner_file, banner_filename


def get_watermark_file(base_dir: str,
                       nickname: str, domain: str) -> (str, str):
    """Gets the filename for watermarking when an image is attached to a post
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    watermark_file, watermark_filename = \
        get_image_file(base_dir, 'watermark_image', account_dir, '')
    return watermark_file, watermark_filename


def replace_strings(text: str, replacements: {}) -> str:
    """Does a series of string replacements
    """
    for orig_str, new_str in replacements.items():
        text = text.replace(orig_str, new_str)
    return text


def account_is_indexable(actor_json: {}) -> bool:
    """Returns true if the given actor is indexable
    """
    if 'indexable' not in actor_json:
        return False
    if isinstance(actor_json['indexable'], bool):
        return actor_json['indexable']
    if isinstance(actor_json['indexable'], list):
        if '#Public' in str(actor_json['indexable']):
            return True
    elif isinstance(actor_json['indexable'], str):
        if '#Public' in actor_json['indexable']:
            return True
    return False


def browser_supports_download_filename(ua_str: str) -> bool:
    """Does the browser indicated by the user agent string support specifying
    a default download filename?
    https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#download
    https://www.w3schools.com/howto/howto_html_download_link.asp
    """
    if 'mozilla' in ua_str or 'firefox' in ua_str:
        return True
    return False


def load_instance_software(base_dir: str) -> []:
    """For each domain encountered this stores the instance type
    such as mastodon, epicyon, pixelfed, etc
    """
    instance_software_filename = data_dir(base_dir) + '/instance_software.json'
    if os.path.isfile(instance_software_filename):
        instance_software_json = load_json(instance_software_filename)
        if instance_software_json:
            return instance_software_json
    return {}


def get_event_categories() -> []:
    """Returns event categories
    https://codeberg.org/fediverse/fep/src/branch/main/fep/8a8e/fep-8a8e.md
    """
    return (
        'ARTS',
        'AUTO_BOAT_AIR',
        'BOOK_CLUBS',
        'BUSINESS',
        'CAUSES',
        'CLIMATE_ENVIRONMENT',
        'COMMUNITY',
        'COMEDY',
        'CRAFTS',
        'CREATIVE_JAM',
        'DIY_MAKER_SPACES',
        'FAMILY_EDUCATION',
        'FASHION_BEAUTY',
        'FESTIVALS',
        'FILM_MEDIA',
        'FOOD_DRINK',
        'GAMES',
        'INCLUSIVE_SPACES',
        'LANGUAGE_CULTURE',
        'LEARNING',
        'LGBTQ',
        'MEETING',
        'MEDITATION_WELLBEING',
        'MOVEMENTS_POLITICS',
        'MUSIC',
        'NETWORKING',
        'OUTDOORS_ADVENTURE',
        'PARTY',
        'PERFORMING_VISUAL_ARTS',
        'PETS',
        'PHOTOGRAPHY',
        'SCIENCE_TECH',
        'SPIRITUALITY_RELIGION_BELIEFS',
        'SPORTS',
        'THEATRE',
        'WORKSHOPS_SKILL_SHARING'
    )
