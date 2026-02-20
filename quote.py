__filename__ = "quote.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
from utils import acct_dir
from utils import resembles_url
from utils import remove_html
from utils import text_in_file
from utils import has_object_dict


def get_quote_toot_url(post_json_object: str) -> str:
    """ Returns the url for a quote toot
    This suffers from a general lack of protocol consensus
    """
    # adhoc quote toot implementations
    object_quote_url_fields = (
        'quoteUri', 'quoteUrl', 'quoteReply', 'toot:quoteReply',
        '_misskey_quote', 'quote'
    )
    post_obj = post_json_object
    if has_object_dict(post_json_object):
        post_obj = post_json_object['object']

    for fieldname in object_quote_url_fields:
        if not post_obj.get(fieldname):
            continue
        quote_url = post_obj[fieldname]
        if isinstance(quote_url, str):
            if resembles_url(quote_url):
                return remove_html(quote_url)

    # as defined by FEP-dd4b
    # https://codeberg.org/fediverse/fep/src/branch/main/fep/dd4b/fep-dd4b.md
    if has_object_dict(post_json_object):
        if ((post_json_object.get('content') or
             post_json_object.get('contentMap')) and
            (not post_json_object['object'].get('content') and
             not post_json_object['object'].get('contentMap')) and
           post_json_object['object'].get('id')):
            quote_url = post_json_object['object']['id']
            if isinstance(quote_url, str):
                if resembles_url(quote_url):
                    return remove_html(quote_url)

    # Other ActivityPub implementation - adding a Link tag
    if not post_obj.get('tag'):
        return ''

    if not isinstance(post_obj['tag'], list):
        return ''

    for item in post_obj['tag']:
        if not isinstance(item, dict):
            continue
        if item.get('rel'):
            mk_quote = False
            if isinstance(item['rel'], list):
                for rel_str in item['rel']:
                    if not isinstance(rel_str, str):
                        continue
                    if '_misskey_quote' in rel_str:
                        mk_quote = True
            elif isinstance(item['rel'], str):
                if '_misskey_quote' in item['rel']:
                    mk_quote = True
            if mk_quote and item.get('href'):
                if isinstance(item['href'], str):
                    if resembles_url(item['href']):
                        return remove_html(item['href'])
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
        if item.get('href'):
            if isinstance(item['href'], str):
                if resembles_url(item['href']):
                    return remove_html(item['href'])
    return ''


def quote_toots_allowed(base_dir: str, nickname: str, domain: str,
                        sender_nickname: str, sender_domain: str) -> bool:
    """ Returns true if quote toots are allowed by the given account
    for the given sender
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    quotes_enabled_filename = account_dir + '/.allowQuotes'
    if os.path.isfile(quotes_enabled_filename):
        # check blocks on individual sending accounts
        quotes_blocked_filename = account_dir + '/quotesblocked.txt'
        if sender_nickname is None:
            return True
        if os.path.isfile(quotes_blocked_filename):
            sender_handle = sender_nickname + '@' + sender_domain
            if text_in_file(sender_handle, quotes_blocked_filename, False):
                # quote toots not permitted from this sender
                return False
        return True
    return False
