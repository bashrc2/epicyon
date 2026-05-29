__filename__ = "cwlists.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
from utils import load_json
from utils import get_content_from_post
from utils import content_is_single_url
from utils import is_yggdrasil_address
from utils import get_attributed_to
from utils import has_object_dict
from data import is_a_dir


def load_cw_lists(base_dir: str, verbose: bool) -> {}:
    """Load lists used for content warnings
    """
    if not is_a_dir(base_dir + '/cwlists'):
        return {}
    result = {}
    # NOTE: here we do want to allow recursive walk through
    # possible subdirectories
    for _, _, files in os.walk(base_dir + '/cwlists'):
        for fname in files:
            if not fname.endswith('.json'):
                continue
            list_filename = os.path.join(base_dir + '/cwlists', fname)
            print('list_filename: ' + list_filename)
            list_json = load_json(list_filename)
            if not list_json:
                continue
            if not list_json.get('name'):
                continue
            if not list_json.get('words') and \
               not list_json.get('hashtags') and \
               not list_json.get('domains'):
                continue
            name = list_json['name']
            if verbose:
                print('List: ' + name)
            result[name] = list_json
    return result


def _add_cw_match_tags(item: {}, post_tags: {}, cw_text: str,
                       warning: str) -> (bool, str):
    """Updates content warning text using hashtags from within
    the post content
    """
    matched: bool = False
    for tag in item['hashtags']:
        tag = tag.strip()
        if not tag:
            continue
        if not tag.startswith('#'):
            tag = '#' + tag
        tag = tag.lower()
        for tag_dict in post_tags:
            if not isinstance(tag_dict, dict):
                continue
            if not tag_dict.get('Hashtag'):
                continue
            if not tag_dict.get('name'):
                continue
            if tag_dict['name'].lower() == tag:
                if cw_text:
                    cw_text = warning + ' / ' + cw_text
                else:
                    cw_text = warning
                matched = True
                break
        if matched:
            break
    return matched, cw_text


def _add_cw_match_domains(item: {}, content: str, cw_text: str,
                          warning: str) -> (bool, str):
    """Updates content warning text using domains from within
    the post content
    """
    matched: bool = False

    for domain in item['domains']:
        if '.' in domain or is_yggdrasil_address(domain):
            first_section = domain.split('.')[0]
            len_first_section = len(first_section)
            if len_first_section in range(1, 4):
                if '.' + domain in content or \
                   '/' + domain in content:
                    if cw_text:
                        cw_text = warning + ' / ' + cw_text
                    else:
                        cw_text = warning
                    matched = True
                    break
                continue

        if domain in content:
            if cw_text:
                cw_text = warning + ' / ' + cw_text
            else:
                cw_text = warning
            matched = True
            break
    return matched, cw_text


def add_cw_from_lists(post_json_object: {}, cw_lists: {}, translate: {},
                      lists_enabled: str, system_language: str,
                      languages_understood: []) -> None:
    """Adds content warnings by matching the post content
    against domains or keywords
    """
    if not lists_enabled:
        return
    if 'content' not in post_json_object['object']:
        if 'contentMap' not in post_json_object['object']:
            return

    cw_text: str = ''
    if post_json_object['object'].get('summary'):
        cw_text = post_json_object['object']['summary']

    content = get_content_from_post(post_json_object, system_language,
                                    languages_understood, "content")
    if not content:
        return

    # warn about possible dangerous web links, which could be phishing scams
    if content_is_single_url(content):
        single_link_warning = translate['Warning: Possible dangerous link']
        if cw_text:
            if single_link_warning not in cw_text:
                cw_text = single_link_warning + ' / ' + cw_text
        else:
            cw_text = single_link_warning

    post_tags: list[dict] = []
    if post_json_object['object'].get('tag'):
        if isinstance(post_json_object['object']['tag'], list):
            post_tags = post_json_object['object']['tag']

    for name, item in cw_lists.items():
        if name not in lists_enabled:
            continue
        if not item.get('warning'):
            continue
        warning = item['warning']

        # is there a translated version of the warning?
        if translate.get(warning):
            warning = translate[warning]

        # is the warning already in the CW?
        if warning in cw_text:
            continue

        matched: bool = False

        # match hashtags within the post
        if post_tags and item.get('hashtags'):
            matched, cw_text = \
                _add_cw_match_tags(item, post_tags, cw_text, warning)

        if matched:
            continue

        # match domains within the content and the original post author
        if item.get('domains'):
            # when checking domains also check the domain of the post author.
            # A typical scenario might be someone you follow boosting a post
            # from a disinformation instance
            attrib_str: str = ''
            this_post_json: dict = post_json_object
            if has_object_dict(post_json_object):
                this_post_json = post_json_object['object']
            if this_post_json.get('attributedTo'):
                attrib: str = get_attributed_to(this_post_json['attributedTo'])
                if attrib:
                    attrib_str = ' ' + attrib

            matched, cw_text = \
                _add_cw_match_domains(item, content + attrib_str, cw_text,
                                      warning)

        if matched:
            continue

        # match words within the content
        if item.get('words'):
            for word_str in item['words']:
                if word_str in content or word_str.title() in content:
                    if cw_text:
                        cw_text = warning + ' / ' + cw_text
                    else:
                        cw_text = warning
                    break
    if cw_text:
        post_json_object['object']['summary'] = cw_text
        post_json_object['object']['sensitive'] = True


def get_cw_list_variable(list_name: str) -> str:
    """Returns the variable associated with a CW list
    """
    return 'list' + list_name.replace(' ', '').replace("'", '')
