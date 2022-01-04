__filename__ = "conversation.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from utils import has_object_dict
from utils import acct_dir
from utils import remove_id_ending


def _get_conversation_filename(base_dir: str, nickname: str, domain: str,
                               post_json_object: {}) -> str:
    """Returns the conversation filename
    """
    if not has_object_dict(post_json_object):
        return None
    if not post_json_object['object'].get('conversation'):
        return None
    if not post_json_object['object'].get('id'):
        return None
    conversation_dir = acct_dir(base_dir, nickname, domain) + '/conversation'
    if not os.path.isdir(conversation_dir):
        os.mkdir(conversation_dir)
    conversation_id = post_json_object['object']['conversation']
    conversation_id = conversation_id.replace('/', '#')
    return conversation_dir + '/' + conversation_id


def update_conversation(base_dir: str, nickname: str, domain: str,
                        post_json_object: {}) -> bool:
    """Ads a post to a conversation index in the /conversation subdirectory
    """
    conversation_filename = \
        _get_conversation_filename(base_dir, nickname, domain,
                                   post_json_object)
    if not conversation_filename:
        return False
    post_id = remove_id_ending(post_json_object['object']['id'])
    if not os.path.isfile(conversation_filename):
        try:
            with open(conversation_filename, 'w+') as conv_file:
                conv_file.write(post_id + '\n')
                return True
        except OSError:
            print('EX: update_conversation ' +
                  'unable to write to ' + conversation_filename)
    elif post_id + '\n' not in open(conversation_filename).read():
        try:
            with open(conversation_filename, 'a+') as conv_file:
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
        with open(conversation_filename + '.muted', 'w+') as conv_file:
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
