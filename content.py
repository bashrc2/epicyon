__filename__ = "content.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import email.parser
import urllib.parse
from shutil import copyfile
from utils import valid_hash_tag
from utils import dangerous_svg
from utils import remove_domain_port
from utils import get_image_extensions
from utils import load_json
from utils import save_json
from utils import file_last_modified
from utils import get_link_prefixes
from utils import dangerous_markup
from utils import is_pgp_encrypted
from utils import contains_pgp_public_key
from utils import acct_dir
from utils import is_float
from utils import get_currencies
from utils import remove_html
from petnames import get_pet_name
from session import download_image

MUSIC_SITES = ('soundcloud.com', 'bandcamp.com')

MAX_LINK_LENGTH = 40

REMOVE_MARKUP = (
    'b', 'i', 'ul', 'ol', 'li', 'em', 'strong',
    'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5'
)

INVALID_CONTENT_STRINGS = (
    'mute', 'unmute', 'editeventpost', 'notifypost',
    'delete', 'options', 'page', 'repeat',
    'bm', 'tl', 'actor', 'unrepeat', 'eventid',
    'unannounce', 'like', 'unlike', 'bookmark',
    'unbookmark', 'likedBy', 'time',
    'year', 'month', 'day', 'editnewpost',
    'graph', 'showshare', 'category', 'showwanted',
    'rmshare', 'rmwanted', 'repeatprivate',
    'unrepeatprivate', 'replyto',
    'replyfollowers', 'replydm', 'editblogpost',
    'handle', 'blockdomain'
)


def remove_html_tag(html_str: str, tag: str) -> str:
    """Removes a given tag from a html string
    """
    tag_found = True
    while tag_found:
        match_str = ' ' + tag + '="'
        if match_str not in html_str:
            tag_found = False
            break
        sections = html_str.split(match_str, 1)
        if '"' not in sections[1]:
            tag_found = False
            break
        html_str = sections[0] + sections[1].split('"', 1)[1]
    return html_str


def _remove_quotes_within_quotes(content: str) -> str:
    """Removes any blockquote inside blockquote
    """
    if '<blockquote>' not in content:
        return content
    if '</blockquote>' not in content:
        return content
    ctr = 1
    found = True
    while found:
        prefix = content.split('<blockquote>', ctr)[0] + '<blockquote>'
        quoted_str = content.split('<blockquote>', ctr)[1]
        if '</blockquote>' not in quoted_str:
            found = False
        else:
            end_str = quoted_str.split('</blockquote>')[1]
            quoted_str = quoted_str.split('</blockquote>')[0]
            if '<blockquote>' not in end_str:
                found = False
            if '<blockquote>' in quoted_str:
                quoted_str = quoted_str.replace('<blockquote>', '')
                content = prefix + quoted_str + '</blockquote>' + end_str
        ctr += 1
    return content


def html_replace_email_quote(content: str) -> str:
    """Replaces an email style quote "> Some quote" with html blockquote
    """
    if is_pgp_encrypted(content) or contains_pgp_public_key(content):
        return content
    # replace quote paragraph
    if '<p>&quot;' in content:
        if '&quot;</p>' in content:
            if content.count('<p>&quot;') == content.count('&quot;</p>'):
                content = content.replace('<p>&quot;', '<p><blockquote>')
                content = content.replace('&quot;</p>', '</blockquote></p>')
    if '>\u201c' in content:
        if '\u201d<' in content:
            if content.count('>\u201c') == content.count('\u201d<'):
                content = content.replace('>\u201c', '><blockquote>')
                content = content.replace('\u201d<', '</blockquote><')
    # replace email style quote
    if '>&gt; ' not in content:
        return content
    content_str = content.replace('<p>', '')
    content_lines = content_str.split('</p>')
    new_content = ''
    for line_str in content_lines:
        if not line_str:
            continue
        if '>&gt; ' not in line_str:
            if line_str.startswith('&gt; '):
                line_str = line_str.replace('&gt; ', '<blockquote>')
                line_str = line_str.replace('&gt;', '<br>')
                new_content += '<p>' + line_str + '</blockquote></p>'
            else:
                new_content += '<p>' + line_str + '</p>'
        else:
            line_str = line_str.replace('>&gt; ', '><blockquote>')
            if line_str.startswith('&gt;'):
                line_str = line_str.replace('&gt;', '<blockquote>', 1)
            else:
                line_str = line_str.replace('&gt;', '<br>')
            new_content += '<p>' + line_str + '</blockquote></p>'
    return _remove_quotes_within_quotes(new_content)


def html_replace_quote_marks(content: str) -> str:
    """Replaces quotes with html formatting
    "hello" becomes <q>hello</q>
    """
    if is_pgp_encrypted(content) or contains_pgp_public_key(content):
        return content
    if '"' not in content:
        if '&quot;' not in content:
            return content

    # only if there are a few quote marks
    if content.count('"') > 4:
        return content
    if content.count('&quot;') > 4:
        return content

    new_content = content
    if '"' in content:
        sections = content.split('"')
        if len(sections) > 1:
            new_content = ''
            open_quote = True
            markup = False
            for char in content:
                curr_char = char
                if char == '<':
                    markup = True
                elif char == '>':
                    markup = False
                elif char == '"' and not markup:
                    if open_quote:
                        curr_char = '“'
                    else:
                        curr_char = '”'
                    open_quote = not open_quote
                new_content += curr_char

    if '&quot;' in new_content:
        open_quote = True
        content = new_content
        new_content = ''
        ctr = 0
        sections = content.split('&quot;')
        no_of_sections = len(sections)
        for sec in sections:
            new_content += sec
            if ctr < no_of_sections - 1:
                if open_quote:
                    new_content += '“'
                else:
                    new_content += '”'
                open_quote = not open_quote
            ctr += 1
    return new_content


def dangerous_css(filename: str, allow_local_network_access: bool) -> bool:
    """Returns true is the css file contains code which
    can create security problems
    """
    if not os.path.isfile(filename):
        return False

    content = None
    try:
        with open(filename, 'r') as css_file:
            content = css_file.read().lower()
    except OSError:
        print('EX: unable to read css file ' + filename)

    if not content:
        return False

    css_matches = (
        'behavior:', ':expression', '?php', '.php',
        'google', 'regexp', 'localhost',
        '127.0.', '192.168', '10.0.', '@import'
    )
    for cssmatch in css_matches:
        if cssmatch in content:
            return True

    # search for non-local web links
    if 'url(' in content:
        url_list = content.split('url(')
        ctr = 0
        for url_str in url_list:
            if ctr > 0:
                if ')' in url_str:
                    url_str = url_str.split(')')[0]
                    if 'http' in url_str:
                        print('ERROR: non-local web link in CSS ' +
                              filename)
                        return True
            ctr += 1

    # an attacker can include html inside of the css
    # file as a comment and this may then be run from the html
    if dangerous_markup(content, allow_local_network_access):
        return True
    return False


def switch_words(base_dir: str, nickname: str, domain: str, content: str,
                 rules: [] = []) -> str:
    """Performs word replacements. eg. Trump -> The Orange Menace
    """
    if is_pgp_encrypted(content) or contains_pgp_public_key(content):
        return content

    if not rules:
        switch_words_filename = \
            acct_dir(base_dir, nickname, domain) + '/replacewords.txt'
        if not os.path.isfile(switch_words_filename):
            return content
        try:
            with open(switch_words_filename, 'r') as words_file:
                rules = words_file.readlines()
        except OSError:
            print('EX: unable to read switches ' + switch_words_filename)

    for line in rules:
        replace_str = line.replace('\n', '').replace('\r', '')
        splitters = ('->', ':', ',', ';', '-')
        word_transform = None
        for split_str in splitters:
            if split_str in replace_str:
                word_transform = replace_str.split(split_str)
                break
        if not word_transform:
            continue
        if len(word_transform) == 2:
            replace_str1 = word_transform[0].strip().replace('"', '')
            replace_str2 = word_transform[1].strip().replace('"', '')
            content = content.replace(replace_str1, replace_str2)
    return content


def _save_custom_emoji(session, base_dir: str, emojiName: str, url: str,
                       debug: bool) -> None:
    """Saves custom emoji to file
    """
    if not session:
        if debug:
            print('EX: _save_custom_emoji no session')
        return
    if '.' not in url:
        return
    ext = url.split('.')[-1]
    if ext != 'png':
        if debug:
            print('EX: Custom emoji is wrong format ' + url)
        return
    emojiName = emojiName.replace(':', '').strip().lower()
    custom_emoji_dir = base_dir + '/emojicustom'
    if not os.path.isdir(custom_emoji_dir):
        os.mkdir(custom_emoji_dir)
    emoji_image_filename = custom_emoji_dir + '/' + emojiName + '.' + ext
    if not download_image(session, base_dir, url,
                          emoji_image_filename, debug, False):
        if debug:
            print('EX: custom emoji not downloaded ' + url)
        return
    emoji_json_filename = custom_emoji_dir + '/emoji.json'
    emoji_json = {}
    if os.path.isfile(emoji_json_filename):
        emoji_json = load_json(emoji_json_filename, 0, 1)
        if not emoji_json:
            emoji_json = {}
    if not emoji_json.get(emojiName):
        emoji_json[emojiName] = emojiName
        save_json(emoji_json, emoji_json_filename)
        if debug:
            print('EX: Saved custom emoji ' + emoji_json_filename)
    elif debug:
        print('EX: cusom emoji already saved')


def replace_emoji_from_tags(session, base_dir: str,
                            content: str, tag: [], message_type: str,
                            debug: bool) -> str:
    """Uses the tags to replace :emoji: with html image markup
    """
    for tag_item in tag:
        if not tag_item.get('type'):
            continue
        if tag_item['type'] != 'Emoji':
            continue
        if not tag_item.get('name'):
            continue
        if not tag_item.get('icon'):
            continue
        if not tag_item['icon'].get('url'):
            continue
        if '/' not in tag_item['icon']['url']:
            continue
        if tag_item['name'] not in content:
            continue
        icon_name = tag_item['icon']['url'].split('/')[-1]
        if icon_name:
            if len(icon_name) > 1:
                if icon_name[0].isdigit():
                    if '.' in icon_name:
                        icon_name = icon_name.split('.')[0]
                        # see https://unicode.org/
                        # emoji/charts/full-emoji-list.html
                        if '-' not in icon_name:
                            # a single code
                            replaced = False
                            try:
                                replace_char = chr(int("0x" + icon_name, 16))
                                content = content.replace(tag_item['name'],
                                                          replace_char)
                                replaced = True
                            except BaseException:
                                print('EX: replace_emoji_from_tags 1 ' +
                                      'no conversion of ' +
                                      str(icon_name) + ' to chr ' +
                                      tag_item['name'] + ' ' +
                                      tag_item['icon']['url'])
                            if not replaced:
                                _save_custom_emoji(session, base_dir,
                                                   tag_item['name'],
                                                   tag_item['icon']['url'],
                                                   debug)
                        else:
                            # sequence of codes
                            icon_codes = icon_name.split('-')
                            icon_code_sequence = ''
                            for icode in icon_codes:
                                replaced = False
                                try:
                                    icon_code_sequence += chr(int("0x" +
                                                                  icode, 16))
                                    replaced = True
                                except BaseException:
                                    icon_code_sequence = ''
                                    print('EX: replace_emoji_from_tags 2 ' +
                                          'no conversion of ' +
                                          str(icode) + ' to chr ' +
                                          tag_item['name'] + ' ' +
                                          tag_item['icon']['url'])
                                if not replaced:
                                    _save_custom_emoji(session, base_dir,
                                                       tag_item['name'],
                                                       tag_item['icon']['url'],
                                                       debug)
                            if icon_code_sequence:
                                content = content.replace(tag_item['name'],
                                                          icon_code_sequence)

        html_class = 'emoji'
        if message_type == 'post header':
            html_class = 'emojiheader'
        if message_type == 'profile':
            html_class = 'emojiprofile'
        emoji_html = "<img src=\"" + tag_item['icon']['url'] + "\" alt=\"" + \
            tag_item['name'].replace(':', '') + \
            "\" align=\"middle\" class=\"" + html_class + "\"/>"
        content = content.replace(tag_item['name'], emoji_html)
    return content


def _add_music_tag(content: str, tag: str) -> str:
    """If a music link is found then ensure that the post is
    tagged appropriately
    """
    if '#podcast' in content or '#documentary' in content:
        return content
    if '#' not in tag:
        tag = '#' + tag
    if tag in content:
        return content
    music_site_found = False
    for site in MUSIC_SITES:
        if site + '/' in content:
            music_site_found = True
            break
    if not music_site_found:
        return content
    return ':music: ' + content + ' ' + tag + ' '


def add_web_links(content: str) -> str:
    """Adds markup for web links
    """
    if ':' not in content:
        return content

    prefixes = get_link_prefixes()

    # do any of these prefixes exist within the content?
    prefix_found = False
    for prefix in prefixes:
        if prefix in content:
            prefix_found = True
            break

    # if there are no prefixes then just keep the content we have
    if not prefix_found:
        return content

    content = content.replace('\r', '')
    words = content.replace('\n', ' --linebreak-- ').split(' ')
    replace_dict = {}
    for wrd in words:
        if ':' not in wrd:
            continue
        # does the word begin with a prefix?
        prefix_found = False
        for prefix in prefixes:
            if wrd.startswith(prefix):
                prefix_found = True
                break
        if not prefix_found:
            continue
        # the word contains a prefix
        if wrd.endswith('.') or wrd.endswith(';'):
            wrd = wrd[:-1]
        markup = '<a href="' + wrd + \
            '" rel="nofollow noopener noreferrer" target="_blank">'
        for prefix in prefixes:
            if wrd.startswith(prefix):
                markup += '<span class="invisible">' + prefix + '</span>'
                break
        link_text = wrd
        for prefix in prefixes:
            link_text = link_text.replace(prefix, '')
        # prevent links from becoming too long
        if len(link_text) > MAX_LINK_LENGTH:
            markup += '<span class="ellipsis">' + \
                link_text[:MAX_LINK_LENGTH] + '</span>'
            markup += '<span class="invisible">' + \
                link_text[MAX_LINK_LENGTH:] + '</span></a>'
        else:
            markup += '<span class="ellipsis">' + link_text + '</span></a>'
        replace_dict[wrd] = markup

    # do the replacements
    for url, markup in replace_dict.items():
        content = content.replace(url, markup)

    # replace any line breaks
    content = content.replace(' --linebreak-- ', '<br>')

    return content


def _add_hash_tags(word_str: str, http_prefix: str, domain: str,
                   replace_hashtags: {}, post_hashtags: {}) -> bool:
    """Detects hashtags and adds them to the replacements dict
    Also updates the hashtags list to be added to the post
    """
    if replace_hashtags.get(word_str):
        return True
    hashtag = word_str[1:]
    if not valid_hash_tag(hashtag):
        return False
    hashtag_url = http_prefix + "://" + domain + "/tags/" + hashtag
    post_hashtags[hashtag] = {
        'href': hashtag_url,
        'name': '#' + hashtag,
        'type': 'Hashtag'
    }
    replace_hashtags[word_str] = "<a href=\"" + hashtag_url + \
        "\" class=\"mention hashtag\" rel=\"tag\">#<span>" + \
        hashtag + "</span></a>"
    return True


def _add_emoji(base_dir: str, word_str: str,
               http_prefix: str, domain: str,
               replace_emoji: {}, post_tags: {},
               emoji_dict: {}) -> bool:
    """Detects Emoji and adds them to the replacements dict
    Also updates the tags list to be added to the post
    """
    if not word_str.startswith(':'):
        return False
    if not word_str.endswith(':'):
        return False
    if len(word_str) < 3:
        return False
    if replace_emoji.get(word_str):
        return True
    # remove leading and trailing : characters
    emoji = word_str[1:]
    emoji = emoji[:-1]
    # is the text of the emoji valid?
    if not valid_hash_tag(emoji):
        return False
    if not emoji_dict.get(emoji):
        return False
    emoji_filename = base_dir + '/emoji/' + emoji_dict[emoji] + '.png'
    if not os.path.isfile(emoji_filename):
        return False
    emoji_url = http_prefix + "://" + domain + \
        "/emoji/" + emoji_dict[emoji] + '.png'
    post_tags[emoji] = {
        'icon': {
            'mediaType': 'image/png',
            'type': 'Image',
            'url': emoji_url
        },
        'name': ':' + emoji + ':',
        "updated": file_last_modified(emoji_filename),
        "id": emoji_url.replace('.png', ''),
        'type': 'Emoji'
    }
    return True


def post_tag_exists(tagType: str, tagName: str, tags: {}) -> bool:
    """Returns true if a tag exists in the given dict
    """
    for tag in tags:
        if tag['name'] == tagName and tag['type'] == tagType:
            return True
    return False


def _add_mention(word_str: str, http_prefix: str, following: str,
                 petnames: str, replace_mentions: {},
                 recipients: [], tags: {}) -> bool:
    """Detects mentions and adds them to the replacements dict and
    recipients list
    """
    possible_handle = word_str[1:]
    # @nick
    if following and '@' not in possible_handle:
        # fall back to a best effort match against the following list
        # if no domain was specified. eg. @nick
        possible_nickname = possible_handle
        for follow in following:
            if '@' not in follow:
                continue
            follow_nick = follow.split('@')[0]
            if possible_nickname == follow_nick:
                follow_str = follow.replace('\n', '').replace('\r', '')
                replace_domain = follow_str.split('@')[1]
                recipient_actor = http_prefix + "://" + \
                    replace_domain + "/@" + possible_nickname
                if recipient_actor not in recipients:
                    recipients.append(recipient_actor)
                tags[word_str] = {
                    'href': recipient_actor,
                    'name': word_str,
                    'type': 'Mention'
                }
                replace_mentions[word_str] = \
                    "<span class=\"h-card\"><a href=\"" + http_prefix + \
                    "://" + replace_domain + "/@" + possible_nickname + \
                    "\" class=\"u-url mention\">@<span>" + \
                    possible_nickname + "</span></a></span>"
                return True
        # try replacing petnames with mentions
        follow_ctr = 0
        for follow in following:
            if '@' not in follow:
                follow_ctr += 1
                continue
            pet = petnames[follow_ctr].replace('\n', '')
            if pet:
                if possible_nickname == pet:
                    follow_str = follow.replace('\n', '').replace('\r', '')
                    replace_nickname = follow_str.split('@')[0]
                    replace_domain = follow_str.split('@')[1]
                    recipient_actor = http_prefix + "://" + \
                        replace_domain + "/@" + replace_nickname
                    if recipient_actor not in recipients:
                        recipients.append(recipient_actor)
                    tags[word_str] = {
                        'href': recipient_actor,
                        'name': word_str,
                        'type': 'Mention'
                    }
                    replace_mentions[word_str] = \
                        "<span class=\"h-card\"><a href=\"" + http_prefix + \
                        "://" + replace_domain + "/@" + replace_nickname + \
                        "\" class=\"u-url mention\">@<span>" + \
                        replace_nickname + "</span></a></span>"
                    return True
            follow_ctr += 1
        return False
    possible_nickname = None
    possible_domain = None
    if '@' not in possible_handle:
        return False
    possible_nickname = possible_handle.split('@')[0]
    if not possible_nickname:
        return False
    possible_domain = \
        possible_handle.split('@')[1].strip('\n').strip('\r')
    if not possible_domain:
        return False
    if following:
        for follow in following:
            if follow.replace('\n', '').replace('\r', '') != possible_handle:
                continue
            recipient_actor = http_prefix + "://" + \
                possible_domain + "/@" + possible_nickname
            if recipient_actor not in recipients:
                recipients.append(recipient_actor)
            tags[word_str] = {
                'href': recipient_actor,
                'name': word_str,
                'type': 'Mention'
            }
            replace_mentions[word_str] = \
                "<span class=\"h-card\"><a href=\"" + http_prefix + \
                "://" + possible_domain + "/@" + possible_nickname + \
                "\" class=\"u-url mention\">@<span>" + possible_nickname + \
                "</span></a></span>"
            return True
    # @nick@domain
    if not (possible_domain == 'localhost' or '.' in possible_domain):
        return False
    recipient_actor = http_prefix + "://" + \
        possible_domain + "/@" + possible_nickname
    if recipient_actor not in recipients:
        recipients.append(recipient_actor)
    tags[word_str] = {
        'href': recipient_actor,
        'name': word_str,
        'type': 'Mention'
    }
    replace_mentions[word_str] = \
        "<span class=\"h-card\"><a href=\"" + http_prefix + \
        "://" + possible_domain + "/@" + possible_nickname + \
        "\" class=\"u-url mention\">@<span>" + possible_nickname + \
        "</span></a></span>"
    return True


def replace_content_duplicates(content: str) -> str:
    """Replaces invalid duplicates within content
    """
    if is_pgp_encrypted(content) or contains_pgp_public_key(content):
        return content
    while '<<' in content:
        content = content.replace('<<', '<')
    while '>>' in content:
        content = content.replace('>>', '>')
    content = content.replace('<\\p>', '')
    return content


def remove_text_formatting(content: str) -> str:
    """Removes markup for bold, italics, etc
    """
    if is_pgp_encrypted(content) or contains_pgp_public_key(content):
        return content
    if '<' not in content:
        return content
    for markup in REMOVE_MARKUP:
        content = content.replace('<' + markup + '>', '')
        content = content.replace('</' + markup + '>', '')
        content = content.replace('<' + markup.upper() + '>', '')
        content = content.replace('</' + markup.upper() + '>', '')
    return content


def remove_long_words(content: str, max_word_length: int,
                      long_words_list: []) -> str:
    """Breaks up long words so that on mobile screens this doesn't
    disrupt the layout
    """
    if is_pgp_encrypted(content) or contains_pgp_public_key(content):
        return content
    content = replace_content_duplicates(content)
    if ' ' not in content:
        # handle a single very long string with no spaces
        content_str = content.replace('<p>', '').replace(r'<\p>', '')
        if '://' not in content_str:
            if len(content_str) > max_word_length:
                if '<p>' in content:
                    content = '<p>' + content_str[:max_word_length] + r'<\p>'
                else:
                    content = content[:max_word_length]
                return content
    words = content.split(' ')
    if not long_words_list:
        long_words_list = []
        for word_str in words:
            if len(word_str) > max_word_length:
                if word_str not in long_words_list:
                    long_words_list.append(word_str)
    for word_str in long_words_list:
        if word_str.startswith('<p>'):
            word_str = word_str.replace('<p>', '')
        if word_str.startswith('<'):
            continue
        if len(word_str) == 76:
            if word_str.upper() == word_str:
                # tox address
                continue
        if '=\"' in word_str:
            continue
        if '@' in word_str:
            if '@@' not in word_str:
                continue
        if '=.ed25519' in word_str:
            continue
        if '.onion' in word_str:
            continue
        if '.i2p' in word_str:
            continue
        if 'https:' in word_str:
            continue
        elif 'http:' in word_str:
            continue
        elif 'i2p:' in word_str:
            continue
        elif 'gnunet:' in word_str:
            continue
        elif 'dat:' in word_str:
            continue
        elif 'rad:' in word_str:
            continue
        elif 'hyper:' in word_str:
            continue
        elif 'briar:' in word_str:
            continue
        if '<' in word_str:
            replace_word = word_str.split('<', 1)[0]
            # if len(replace_word) > max_word_length:
            #     replace_word = replace_word[:max_word_length]
            content = content.replace(word_str, replace_word)
            word_str = replace_word
        if '/' in word_str:
            continue
        if len(word_str[max_word_length:]) < max_word_length:
            content = content.replace(word_str,
                                      word_str[:max_word_length] + '\n' +
                                      word_str[max_word_length:])
        else:
            content = content.replace(word_str,
                                      word_str[:max_word_length])
    if content.startswith('<p>'):
        if not content.endswith('</p>'):
            content = content.strip() + '</p>'
    return content


def _load_auto_tags(base_dir: str, nickname: str, domain: str) -> []:
    """Loads automatic tags file and returns a list containing
    the lines of the file
    """
    filename = acct_dir(base_dir, nickname, domain) + '/autotags.txt'
    if not os.path.isfile(filename):
        return []
    try:
        with open(filename, 'r') as tags_file:
            return tags_file.readlines()
    except OSError:
        print('EX: unable to read auto tags ' + filename)
    return []


def _auto_tag(base_dir: str, nickname: str, domain: str,
              word_str: str, auto_tag_list: [],
              append_tags: []):
    """Generates a list of tags to be automatically appended to the content
    """
    for tag_rule in auto_tag_list:
        if word_str not in tag_rule:
            continue
        if '->' not in tag_rule:
            continue
        rulematch = tag_rule.split('->')[0].strip()
        if rulematch != word_str:
            continue
        tag_name = tag_rule.split('->')[1].strip()
        if tag_name.startswith('#'):
            if tag_name not in append_tags:
                append_tags.append(tag_name)
        else:
            if '#' + tag_name not in append_tags:
                append_tags.append('#' + tag_name)


def add_html_tags(base_dir: str, http_prefix: str,
                  nickname: str, domain: str, content: str,
                  recipients: [], hashtags: {},
                  is_json_content: bool = False) -> str:
    """ Replaces plaintext mentions such as @nick@domain into html
    by matching against known following accounts
    """
    if content.startswith('<p>'):
        content = html_replace_email_quote(content)
        return html_replace_quote_marks(content)
    max_word_length = 40
    content = content.replace('\r', '')
    content = content.replace('\n', ' --linebreak-- ')
    content = _add_music_tag(content, 'nowplaying')
    content_simplified = \
        content.replace(',', ' ').replace(';', ' ').replace('- ', ' ')
    content_simplified = content_simplified.replace('. ', ' ').strip()
    if content_simplified.endswith('.'):
        content_simplified = content_simplified[:len(content_simplified)-1]
    words = content_simplified.split(' ')

    # remove . for words which are not mentions
    new_words = []
    for word_index in range(0, len(words)):
        word_str = words[word_index]
        if word_str.endswith('.'):
            if not word_str.startswith('@'):
                word_str = word_str[:-1]
        if word_str.startswith('.'):
            word_str = word_str[1:]
        new_words.append(word_str)
    words = new_words

    replace_mentions = {}
    replace_hashtags = {}
    replace_emoji = {}
    emoji_dict = {}
    original_domain = domain
    domain = remove_domain_port(domain)
    following_filename = \
        acct_dir(base_dir, nickname, domain) + '/following.txt'

    # read the following list so that we can detect just @nick
    # in addition to @nick@domain
    following = None
    petnames = None
    if '@' in words:
        if os.path.isfile(following_filename):
            following = []
            try:
                with open(following_filename, 'r') as foll_file:
                    following = foll_file.readlines()
            except OSError:
                print('EX: unable to read ' + following_filename)
            for handle in following:
                pet = get_pet_name(base_dir, nickname, domain, handle)
                if pet:
                    petnames.append(pet + '\n')

    # extract mentions and tags from words
    long_words_list = []
    prev_word_str = ''
    auto_tags_list = _load_auto_tags(base_dir, nickname, domain)
    append_tags = []
    for word_str in words:
        word_len = len(word_str)
        if word_len > 2:
            if word_len > max_word_length:
                long_words_list.append(word_str)
            first_char = word_str[0]
            if first_char == '@':
                if _add_mention(word_str, http_prefix, following, petnames,
                                replace_mentions, recipients, hashtags):
                    prev_word_str = ''
                    continue
            elif first_char == '#':
                # remove any endings from the hashtag
                hash_tag_endings = ('.', ':', ';', '-', '\n')
                for ending in hash_tag_endings:
                    if word_str.endswith(ending):
                        word_str = word_str[:len(word_str) - 1]
                        break

                if _add_hash_tags(word_str, http_prefix, original_domain,
                                  replace_hashtags, hashtags):
                    prev_word_str = ''
                    continue
            elif ':' in word_str:
                word_str2 = word_str.split(':')[1]
#                print('TAG: emoji located - ' + word_str)
                if not emoji_dict:
                    # emoji.json is generated so that it can be customized and
                    # the changes will be retained even if default_emoji.json
                    # is subsequently updated
                    if not os.path.isfile(base_dir + '/emoji/emoji.json'):
                        copyfile(base_dir + '/emoji/default_emoji.json',
                                 base_dir + '/emoji/emoji.json')
                emoji_dict = load_json(base_dir + '/emoji/emoji.json')

                # append custom emoji to the dict
                if os.path.isfile(base_dir + '/emojicustom/emoji.json'):
                    custom_emoji_dict = \
                        load_json(base_dir + '/emojicustom/emoji.json')
                    if custom_emoji_dict:
                        emoji_dict = dict(emoji_dict, **custom_emoji_dict)

#                print('TAG: looking up emoji for :' + word_str2 + ':')
                _add_emoji(base_dir, ':' + word_str2 + ':', http_prefix,
                           original_domain, replace_emoji, hashtags,
                           emoji_dict)
            else:
                if _auto_tag(base_dir, nickname, domain, word_str,
                             auto_tags_list, append_tags):
                    prev_word_str = ''
                    continue
                if prev_word_str:
                    if _auto_tag(base_dir, nickname, domain,
                                 prev_word_str + ' ' + word_str,
                                 auto_tags_list, append_tags):
                        prev_word_str = ''
                        continue
            prev_word_str = word_str

    # add any auto generated tags
    for appended in append_tags:
        content = content + ' ' + appended
        _add_hash_tags(appended, http_prefix, original_domain,
                       replace_hashtags, hashtags)

    # replace words with their html versions
    for word_str, replace_str in replace_mentions.items():
        content = content.replace(word_str, replace_str)
    for word_str, replace_str in replace_hashtags.items():
        content = content.replace(word_str, replace_str)
    if not is_json_content:
        for word_str, replace_str in replace_emoji.items():
            content = content.replace(word_str, replace_str)

    content = add_web_links(content)
    if long_words_list:
        content = remove_long_words(content, max_word_length, long_words_list)
    content = limit_repeated_words(content, 6)
    content = content.replace(' --linebreak-- ', '</p><p>')
    content = html_replace_email_quote(content)
    return '<p>' + html_replace_quote_marks(content) + '</p>'


def get_mentions_from_html(html_text: str, match_str: str) -> []:
    """Extracts mentioned actors from the given html content string
    """
    mentions = []
    if match_str not in html_text:
        return mentions
    mentions_list = html_text.split(match_str)
    for mention_str in mentions_list:
        if '"' not in mention_str:
            continue
        actor_str = mention_str.split('"')[0]
        if actor_str.startswith('http') or \
           actor_str.startswith('gnunet') or \
           actor_str.startswith('i2p') or \
           actor_str.startswith('hyper') or \
           actor_str.startswith('dat:'):
            if actor_str not in mentions:
                mentions.append(actor_str)
    return mentions


def extract_media_in_form_post(post_bytes, boundary, name: str):
    """Extracts the binary encoding for image/video/audio within a http
    form POST
    Returns the media bytes and the remaining bytes
    """
    image_start_boundary = b'Content-Disposition: form-data; name="' + \
        name.encode('utf8', 'ignore') + b'";'
    image_start_location = post_bytes.find(image_start_boundary)
    if image_start_location == -1:
        return None, post_bytes

    # bytes after the start boundary appears
    media_bytes = post_bytes[image_start_location:]

    # look for the next boundary
    image_end_boundary = boundary.encode('utf8', 'ignore')
    image_end_location = media_bytes.find(image_end_boundary)
    if image_end_location == -1:
        # no ending boundary
        return media_bytes, post_bytes[:image_start_location]

    # remaining bytes after the end of the image
    remainder = media_bytes[image_end_location:]

    # remove bytes after the end boundary
    media_bytes = media_bytes[:image_end_location]

    # return the media and the before+after bytes
    return media_bytes, post_bytes[:image_start_location] + remainder


def save_media_in_form_post(media_bytes, debug: bool,
                            filename_base: str = None) -> (str, str):
    """Saves the given media bytes extracted from http form POST
    Returns the filename and attachment type
    """
    if not media_bytes:
        if filename_base:
            # remove any existing files
            extension_types = get_image_extensions()
            for ex in extension_types:
                possible_other_format = filename_base + '.' + ex
                if os.path.isfile(possible_other_format):
                    try:
                        os.remove(possible_other_format)
                    except OSError:
                        if debug:
                            print('EX: save_media_in_form_post ' +
                                  'unable to delete other ' +
                                  str(possible_other_format))
            if os.path.isfile(filename_base):
                try:
                    os.remove(filename_base)
                except OSError:
                    if debug:
                        print('EX: save_media_in_form_post ' +
                              'unable to delete ' +
                              str(filename_base))

        if debug:
            print('DEBUG: No media found within POST')
        return None, None

    media_location = -1
    search_str = ''
    filename = None

    # directly search the binary array for the beginning
    # of an image
    extension_list = {
        'png': 'image/png',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        'avif': 'image/avif',
        'mp4': 'video/mp4',
        'ogv': 'video/ogv',
        'mp3': 'audio/mpeg',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'zip': 'application/zip'
    }
    detected_extension = None
    for extension, content_type in extension_list.items():
        search_str = b'Content-Type: ' + content_type.encode('utf8', 'ignore')
        media_location = media_bytes.find(search_str)
        if media_location > -1:
            # image/video/audio binaries
            if extension == 'jpeg':
                extension = 'jpg'
            elif extension == 'mpeg':
                extension = 'mp3'
            if filename_base:
                filename = filename_base + '.' + extension
            attachment_media_type = \
                search_str.decode().split('/')[0].replace('Content-Type: ', '')
            detected_extension = extension
            break

    if not filename:
        return None, None

    # locate the beginning of the image, after any
    # carriage returns
    start_pos = media_location + len(search_str)
    for offset in range(1, 8):
        if media_bytes[start_pos+offset] != 10:
            if media_bytes[start_pos+offset] != 13:
                start_pos += offset
                break

    # remove any existing image files with a different format
    if detected_extension != 'zip':
        extension_types = get_image_extensions()
        for ex in extension_types:
            if ex == detected_extension:
                continue
            possible_other_format = \
                filename.replace('.temp', '').replace('.' +
                                                      detected_extension, '.' +
                                                      ex)
            if os.path.isfile(possible_other_format):
                try:
                    os.remove(possible_other_format)
                except OSError:
                    if debug:
                        print('EX: save_media_in_form_post ' +
                              'unable to delete other 2 ' +
                              str(possible_other_format))

    # don't allow scripts within svg files
    if detected_extension == 'svg':
        svg_str = media_bytes[start_pos:]
        svg_str = svg_str.decode()
        if dangerous_svg(svg_str, False):
            return None, None

    try:
        with open(filename, 'wb') as fp_media:
            fp_media.write(media_bytes[start_pos:])
    except OSError:
        print('EX: unable to write media')

    if not os.path.isfile(filename):
        print('WARN: Media file could not be written to file: ' + filename)
        return None, None
    print('Uploaded media file written: ' + filename)

    return filename, attachment_media_type


def extract_text_fields_in_post(post_bytes, boundary: str, debug: bool,
                                unit_testData: str = None) -> {}:
    """Returns a dictionary containing the text fields of a http form POST
    The boundary argument comes from the http header
    """
    if not unit_testData:
        msg_bytes = email.parser.BytesParser().parsebytes(post_bytes)
        message_fields = msg_bytes.get_payload(decode=True).decode('utf-8')
    else:
        message_fields = unit_testData

    if debug:
        print('DEBUG: POST arriving ' + message_fields)

    message_fields = message_fields.split(boundary)
    fields = {}
    fields_with_semicolon_allowed = (
        'message', 'bio', 'autoCW', 'password', 'passwordconfirm',
        'instanceDescription', 'instanceDescriptionShort',
        'subject', 'location', 'imageDescription'
    )
    # examine each section of the POST, separated by the boundary
    for fld in message_fields:
        if fld == '--':
            continue
        if ' name="' not in fld:
            continue
        post_str = fld.split(' name="', 1)[1]
        if '"' not in post_str:
            continue
        post_key = post_str.split('"', 1)[0]
        post_value_str = post_str.split('"', 1)[1]
        if ';' in post_value_str:
            if post_key not in fields_with_semicolon_allowed and \
               not post_key.startswith('edited'):
                continue
        if '\r\n' not in post_value_str:
            continue
        post_lines = post_value_str.split('\r\n')
        post_value = ''
        if len(post_lines) > 2:
            for line in range(2, len(post_lines)-1):
                if line > 2:
                    post_value += '\n'
                post_value += post_lines[line]
        fields[post_key] = urllib.parse.unquote(post_value)
    return fields


def limit_repeated_words(text: str, max_repeats: int) -> str:
    """Removes words which are repeated many times
    """
    words = text.replace('\n', ' ').split(' ')
    repeat_ctr = 0
    repeated_text = ''
    replacements = {}
    prev_word = ''
    for word in words:
        if word == prev_word:
            repeat_ctr += 1
            if repeated_text:
                repeated_text += ' ' + word
            else:
                repeated_text = word + ' ' + word
        else:
            if repeat_ctr > max_repeats:
                new_text = ((prev_word + ' ') * max_repeats).strip()
                replacements[prev_word] = [repeated_text, new_text]
            repeat_ctr = 0
            repeated_text = ''
        prev_word = word

    if repeat_ctr > max_repeats:
        new_text = ((prev_word + ' ') * max_repeats).strip()
        replacements[prev_word] = [repeated_text, new_text]

    for word, item in replacements.items():
        text = text.replace(item[0], item[1])
    return text


def get_price_from_string(priceStr: str) -> (str, str):
    """Returns the item price and currency
    """
    currencies = get_currencies()
    for symbol, name in currencies.items():
        if symbol in priceStr:
            price = priceStr.replace(symbol, '')
            if is_float(price):
                return price, name
        elif name in priceStr:
            price = priceStr.replace(name, '')
            if is_float(price):
                return price, name
    if is_float(priceStr):
        return priceStr, "EUR"
    return "0.00", "EUR"


def _words_similarity_histogram(words: []) -> {}:
    """Returns a histogram for word combinations
    """
    histogram = {}
    for index in range(1, len(words)):
        combined_words = words[index - 1] + words[index]
        if histogram.get(combined_words):
            histogram[combined_words] += 1
        else:
            histogram[combined_words] = 1
    return histogram


def _words_similarity_words_list(content: str) -> []:
    """Returns a list of words for the given content
    """
    remove_punctuation = ('.', ',', ';', '-', ':', '"')
    content = remove_html(content).lower()
    for punc in remove_punctuation:
        content = content.replace(punc, ' ')
        content = content.replace('  ', ' ')
    return content.split(' ')


def words_similarity(content1: str, content2: str, min_words: int) -> int:
    """Returns percentage similarity
    """
    if content1 == content2:
        return 100

    words1 = _words_similarity_words_list(content1)
    if len(words1) < min_words:
        return 0

    words2 = _words_similarity_words_list(content2)
    if len(words2) < min_words:
        return 0

    histogram1 = _words_similarity_histogram(words1)
    histogram2 = _words_similarity_histogram(words2)

    diff = 0
    for combined_words, _ in histogram1.items():
        if not histogram2.get(combined_words):
            diff += 1
        else:
            diff += \
                abs(histogram2[combined_words] - histogram1[combined_words])
    return 100 - int(diff * 100 / len(histogram1.items()))


def contains_invalid_local_links(content: str) -> bool:
    """Returns true if the given content has invalid links
    """
    for inv_str in INVALID_CONTENT_STRINGS:
        if '?' + inv_str + '=' in content:
            return True
    return False
