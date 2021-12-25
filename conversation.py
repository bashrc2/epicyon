__filename__ = "conversation.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from utils import hasObjectDict
from utils import acctDir
from utils import removeIdEnding


def _getConversationFilename(base_dir: str, nickname: str, domain: str,
                             postJsonObject: {}) -> str:
    """Returns the conversation filename
    """
    if not hasObjectDict(postJsonObject):
        return None
    if not postJsonObject['object'].get('conversation'):
        return None
    if not postJsonObject['object'].get('id'):
        return None
    conversationDir = acctDir(base_dir, nickname, domain) + '/conversation'
    if not os.path.isdir(conversationDir):
        os.mkdir(conversationDir)
    conversationId = postJsonObject['object']['conversation']
    conversationId = conversationId.replace('/', '#')
    return conversationDir + '/' + conversationId


def updateConversation(base_dir: str, nickname: str, domain: str,
                       postJsonObject: {}) -> bool:
    """Ads a post to a conversation index in the /conversation subdirectory
    """
    conversationFilename = \
        _getConversationFilename(base_dir, nickname, domain, postJsonObject)
    if not conversationFilename:
        return False
    postId = removeIdEnding(postJsonObject['object']['id'])
    if not os.path.isfile(conversationFilename):
        try:
            with open(conversationFilename, 'w+') as fp:
                fp.write(postId + '\n')
                return True
        except OSError:
            print('EX: updateConversation ' +
                  'unable to write to ' + conversationFilename)
    elif postId + '\n' not in open(conversationFilename).read():
        try:
            with open(conversationFilename, 'a+') as fp:
                fp.write(postId + '\n')
                return True
        except OSError:
            print('EX: updateConversation 2 ' +
                  'unable to write to ' + conversationFilename)
    return False


def muteConversation(base_dir: str, nickname: str, domain: str,
                     conversationId: str) -> None:
    """Mutes the given conversation
    """
    conversationDir = acctDir(base_dir, nickname, domain) + '/conversation'
    conversationFilename = \
        conversationDir + '/' + conversationId.replace('/', '#')
    if not os.path.isfile(conversationFilename):
        return
    if os.path.isfile(conversationFilename + '.muted'):
        return
    try:
        with open(conversationFilename + '.muted', 'w+') as fp:
            fp.write('\n')
    except OSError:
        print('EX: unable to write mute ' + conversationFilename)


def unmuteConversation(base_dir: str, nickname: str, domain: str,
                       conversationId: str) -> None:
    """Unmutes the given conversation
    """
    conversationDir = acctDir(base_dir, nickname, domain) + '/conversation'
    conversationFilename = \
        conversationDir + '/' + conversationId.replace('/', '#')
    if not os.path.isfile(conversationFilename):
        return
    if not os.path.isfile(conversationFilename + '.muted'):
        return
    try:
        os.remove(conversationFilename + '.muted')
    except OSError:
        print('EX: unmuteConversation unable to delete ' +
              conversationFilename + '.muted')
