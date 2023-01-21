__filename__ = "conversation.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from utils import has_object_dict
from utils import acct_dir
from utils import remove_id_ending
from utils import text_in_file
from utils import locate_post
from utils import load_json
from utils import harmless_markup
from keys import get_instance_actor_key
from session import get_json


def _get_conversation_filename(base_dir: str, nickname: str, domain: str,
                               post_json_object: {}) -> str:
    """Returns the conversation filename
    """
    if not has_object_dict(post_json_object):
        return None
    if not post_json_object['object'].get('conversation') and \
       not post_json_object['object'].get('context'):
        return None
    if not post_json_object['object'].get('id'):
        return None
    conversation_dir = acct_dir(base_dir, nickname, domain) + '/conversation'
    if not os.path.isdir(conversation_dir):
        os.mkdir(conversation_dir)
    if post_json_object['object'].get('conversation'):
        conversation_id = post_json_object['object']['conversation']
    else:
        conversation_id = post_json_object['object']['context']
    conversation_id = conversation_id.replace('/', '#')
    return conversation_dir + '/' + conversation_id


def update_conversation(base_dir: str, nickname: str, domain: str,
                        post_json_object: {}) -> bool:
    """Adds a post to a conversation index in the /conversation subdirectory
    """
    conversation_filename = \
        _get_conversation_filename(base_dir, nickname, domain,
                                   post_json_object)
    if not conversation_filename:
        return False
    post_id = remove_id_ending(post_json_object['object']['id'])
    if not os.path.isfile(conversation_filename):
        try:
            with open(conversation_filename, 'w+',
                      encoding='utf-8') as conv_file:
                conv_file.write(post_id + '\n')
                return True
        except OSError:
            print('EX: update_conversation ' +
                  'unable to write to ' + conversation_filename)
    elif not text_in_file(post_id + '\n', conversation_filename):
        try:
            with open(conversation_filename, 'a+',
                      encoding='utf-8') as conv_file:
                conv_file.write(post_id + '\n')
                return True
        except OSError:
            print('EX: update_conversation 2 ' +
                  'unable to write to ' + conversation_filename)
    return False


def mute_conversation(base_dir: str, nickname: str, domain: str,
                      conversation_id: str) -> None:
    """Mutes the given conversation
    """
    conversation_dir = acct_dir(base_dir, nickname, domain) + '/conversation'
    conversation_filename = \
        conversation_dir + '/' + conversation_id.replace('/', '#')
    if not os.path.isfile(conversation_filename):
        return
    if os.path.isfile(conversation_filename + '.muted'):
        return
    try:
        with open(conversation_filename + '.muted', 'w+',
                  encoding='utf-8') as conv_file:
            conv_file.write('\n')
    except OSError:
        print('EX: unable to write mute ' + conversation_filename)


def unmute_conversation(base_dir: str, nickname: str, domain: str,
                        conversation_id: str) -> None:
    """Unmutes the given conversation
    """
    conversation_dir = acct_dir(base_dir, nickname, domain) + '/conversation'
    conversation_filename = \
        conversation_dir + '/' + conversation_id.replace('/', '#')
    if not os.path.isfile(conversation_filename):
        return
    if not os.path.isfile(conversation_filename + '.muted'):
        return
    try:
        os.remove(conversation_filename + '.muted')
    except OSError:
        print('EX: unmute_conversation unable to delete ' +
              conversation_filename + '.muted')


def download_conversation_posts(session, http_prefix: str, base_dir: str,
                                nickname: str, domain: str,
                                post_id: str, debug: bool) -> []:
    """Downloads all posts for a conversation and returns a list of the
    json objects
    """
    if '://' not in post_id:
        return []
    profile_str = 'https://www.w3.org/ns/activitystreams'
    as_header = {
        'Accept': 'application/ld+json; profile="' + profile_str + '"'
    }
    conversation_view = []
    signing_priv_key_pem = get_instance_actor_key(base_dir, domain)
    post_id = remove_id_ending(post_id)
    post_filename = \
        locate_post(base_dir, nickname, domain, post_id)
    if post_filename:
        post_json_object = load_json(post_filename)
    else:
        post_json_object = \
            get_json(signing_priv_key_pem, session, post_id,
                     as_header, None, debug, __version__,
                     http_prefix, domain)
    if debug:
        if not post_json_object:
            print(post_id + ' returned no json')
    while post_json_object:
        if not isinstance(post_json_object, dict):
            break
        if not has_object_dict(post_json_object):
            if not post_json_object.get('attributedTo'):
                print(str(post_json_object))
                if debug:
                    print(post_id + ' has no attributedTo')
                break
            if not isinstance(post_json_object['attributedTo'], str):
                break
            if not post_json_object.get('published'):
                if debug:
                    print(post_id + ' has no published date')
                break
            if not post_json_object.get('to'):
                if debug:
                    print(post_id + ' has no "to" list')
                break
            if not isinstance(post_json_object['to'], list):
                break
            if 'cc' not in post_json_object:
                if debug:
                    print(post_id + ' has no "cc" list')
                break
            if not isinstance(post_json_object['cc'], list):
                break
            wrapped_post = {
                "@context": "https://www.w3.org/ns/activitystreams",
                'id': post_id + '/activity',
                'type': 'Create',
                'actor': post_json_object['attributedTo'],
                'published': post_json_object['published'],
                'to': post_json_object['to'],
                'cc': post_json_object['cc'],
                'object': post_json_object
            }
            post_json_object = wrapped_post
        if not post_json_object['object'].get('published'):
            break

        # render harmless any dangerous markup
        harmless_markup(post_json_object)

        conversation_view = [post_json_object] + conversation_view
        if not post_json_object['object'].get('inReplyTo'):
            if debug:
                print(post_id + ' is not a reply')
            break
        post_id = post_json_object['object']['inReplyTo']
        post_id = remove_id_ending(post_id)
        post_filename = \
            locate_post(base_dir, nickname, domain, post_id)
        if post_filename:
            post_json_object = load_json(post_filename)
        else:
            post_json_object = \
                get_json(signing_priv_key_pem, session, post_id,
                         as_header, None, debug, __version__,
                         http_prefix, domain)
        if debug:
            if not post_json_object:
                print(post_id + ' returned no json')
    return conversation_view
