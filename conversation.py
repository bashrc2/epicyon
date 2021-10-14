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


def _getConversationFilename(baseDir: str, nickname: str, domain: str,
                             postJsonObject: {}) -> str:
    """Returns the conversation filename
    """
    if not hasObjectDict(postJsonObject):
        return None
    if not postJsonObject['object'].get('conversation'):
        return None
    if not postJsonObject['object'].get('id'):
        return None
    conversationDir = acctDir(baseDir, nickname, domain) + '/conversation'
    if not os.path.isdir(conversationDir):
        os.mkdir(conversationDir)
    conversationId = postJsonObject['object']['conversation']
    conversationId = conversationId.replace('/', '#')
    return conversationDir + '/' + conversationId


def previousConversationPostId(baseDir: str, nickname: str, domain: str,
                               postJsonObject: {}) -> str:
    """Returns the previous conversation post id
    """
    conversationFilename = \
        _getConversationFilename(baseDir, nickname, domain, postJsonObject)
    if not conversationFilename:
        return False
    if not os.path.isfile(conversationFilename):
        return False
    with open(conversationFilename, 'r') as fp:
        lines = fp.readlines()
        if lines:
            return lines[-1].replace('\n', '')
    return False


def updateConversation(baseDir: str, nickname: str, domain: str,
                       postJsonObject: {}) -> bool:
    """Ads a post to a conversation index in the /conversation subdirectory
    """
    conversationFilename = \
        _getConversationFilename(baseDir, nickname, domain, postJsonObject)
    if not conversationFilename:
        return False
    postId = removeIdEnding(postJsonObject['object']['id'])
    if not os.path.isfile(conversationFilename):
        try:
            with open(conversationFilename, 'w+') as fp:
                fp.write(postId + '\n')
                return True
        except BaseException:
            pass
    elif postId + '\n' not in open(conversationFilename).read():
        try:
            with open(conversationFilename, 'a+') as fp:
                fp.write(postId + '\n')
                return True
        except BaseException:
            pass
    return False


def muteConversation(baseDir: str, nickname: str, domain: str,
                     conversationId: str) -> None:
    """Mutes the given conversation
    """
    conversationDir = acctDir(baseDir, nickname, domain) + '/conversation'
    conversationFilename = \
        conversationDir + '/' + conversationId.replace('/', '#')
    if not os.path.isfile(conversationFilename):
        return
    if os.path.isfile(conversationFilename + '.muted'):
        return
    with open(conversationFilename + '.muted', 'w+') as fp:
        fp.write('\n')


def unmuteConversation(baseDir: str, nickname: str, domain: str,
                       conversationId: str) -> None:
    """Unmutes the given conversation
    """
    conversationDir = acctDir(baseDir, nickname, domain) + '/conversation'
    conversationFilename = \
        conversationDir + '/' + conversationId.replace('/', '#')
    if not os.path.isfile(conversationFilename):
        return
    if not os.path.isfile(conversationFilename + '.muted'):
        return
    try:
        os.remove(conversationFilename + '.muted')
    except BaseException:
        pass
