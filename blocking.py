__filename__ = "blocking.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import hasUsersPath
from utils import getFullDomain
from utils import removeIdEnding
from utils import isEvil
from utils import locatePost
from utils import evilIncarnate
from utils import getDomainFromActor
from utils import getNicknameFromActor


def addGlobalBlock(baseDir: str,
                   blockNickname: str, blockDomain: str) -> bool:
    """Global block which applies to all accounts
    """
    blockingFilename = baseDir + '/accounts/blocking.txt'
    if not blockNickname.startswith('#'):
        # is the handle already blocked?
        blockHandle = blockNickname + '@' + blockDomain
        if os.path.isfile(blockingFilename):
            if blockHandle in open(blockingFilename).read():
                return False
        # block an account handle or domain
        blockFile = open(blockingFilename, "a+")
        if blockFile:
            blockFile.write(blockHandle + '\n')
            blockFile.close()
    else:
        blockHashtag = blockNickname
        # is the hashtag already blocked?
        if os.path.isfile(blockingFilename):
            if blockHashtag + '\n' in open(blockingFilename).read():
                return False
        # block a hashtag
        blockFile = open(blockingFilename, "a+")
        if blockFile:
            blockFile.write(blockHashtag + '\n')
            blockFile.close()
    return True


def addBlock(baseDir: str, nickname: str, domain: str,
             blockNickname: str, blockDomain: str) -> bool:
    """Block the given account
    """
    if ':' in domain:
        domain = domain.split(':')[0]
    blockingFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/blocking.txt'
    blockHandle = blockNickname + '@' + blockDomain
    if os.path.isfile(blockingFilename):
        if blockHandle in open(blockingFilename).read():
            return False
    blockFile = open(blockingFilename, "a+")
    blockFile.write(blockHandle + '\n')
    blockFile.close()
    return True


def removeGlobalBlock(baseDir: str,
                      unblockNickname: str,
                      unblockDomain: str) -> bool:
    """Unblock the given global block
    """
    unblockingFilename = baseDir + '/accounts/blocking.txt'
    if not unblockNickname.startswith('#'):
        unblockHandle = unblockNickname + '@' + unblockDomain
        if os.path.isfile(unblockingFilename):
            if unblockHandle in open(unblockingFilename).read():
                with open(unblockingFilename, 'r') as fp:
                    with open(unblockingFilename + '.new', 'w+') as fpnew:
                        for line in fp:
                            handle = line.replace('\n', '').replace('\r', '')
                            if unblockHandle not in line:
                                fpnew.write(handle + '\n')
                if os.path.isfile(unblockingFilename + '.new'):
                    os.rename(unblockingFilename + '.new', unblockingFilename)
                    return True
    else:
        unblockHashtag = unblockNickname
        if os.path.isfile(unblockingFilename):
            if unblockHashtag + '\n' in open(unblockingFilename).read():
                with open(unblockingFilename, 'r') as fp:
                    with open(unblockingFilename + '.new', 'w+') as fpnew:
                        for line in fp:
                            blockLine = \
                                line.replace('\n', '').replace('\r', '')
                            if unblockHashtag not in line:
                                fpnew.write(blockLine + '\n')
                if os.path.isfile(unblockingFilename + '.new'):
                    os.rename(unblockingFilename + '.new', unblockingFilename)
                    return True
    return False


def removeBlock(baseDir: str, nickname: str, domain: str,
                unblockNickname: str, unblockDomain: str) -> bool:
    """Unblock the given account
    """
    if ':' in domain:
        domain = domain.split(':')[0]
    unblockingFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/blocking.txt'
    unblockHandle = unblockNickname + '@' + unblockDomain
    if os.path.isfile(unblockingFilename):
        if unblockHandle in open(unblockingFilename).read():
            with open(unblockingFilename, 'r') as fp:
                with open(unblockingFilename + '.new', 'w+') as fpnew:
                    for line in fp:
                        handle = line.replace('\n', '').replace('\r', '')
                        if unblockHandle not in line:
                            fpnew.write(handle + '\n')
            if os.path.isfile(unblockingFilename + '.new'):
                os.rename(unblockingFilename + '.new', unblockingFilename)
                return True
    return False


def isBlockedHashtag(baseDir: str, hashtag: str) -> bool:
    """Is the given hashtag blocked?
    """
    # avoid very long hashtags
    if len(hashtag) > 32:
        return True
    globalBlockingFilename = baseDir + '/accounts/blocking.txt'
    if os.path.isfile(globalBlockingFilename):
        hashtag = hashtag.strip('\n').strip('\r')
        if not hashtag.startswith('#'):
            hashtag = '#' + hashtag
        if hashtag + '\n' in open(globalBlockingFilename).read():
            return True
    return False


def getDomainBlocklist(baseDir: str) -> str:
    """Returns all globally blocked domains as a string
    This can be used for fast matching to mitigate flooding
    """
    blockedStr = ''

    evilDomains = evilIncarnate()
    for evil in evilDomains:
        blockedStr += evil + '\n'

    globalBlockingFilename = baseDir + '/accounts/blocking.txt'
    if not os.path.isfile(globalBlockingFilename):
        return blockedStr
    with open(globalBlockingFilename, 'r') as fpBlocked:
        blockedStr += fpBlocked.read()
    return blockedStr


def isBlockedDomain(baseDir: str, domain: str) -> bool:
    """Is the given domain blocked?
    """
    if '.' not in domain:
        return False

    if isEvil(domain):
        return True

    # by checking a shorter version we can thwart adversaries
    # who constantly change their subdomain
    sections = domain.split('.')
    noOfSections = len(sections)
    shortDomain = None
    if noOfSections > 2:
        shortDomain = domain[noOfSections-2] + '.' + domain[noOfSections-1]

    globalBlockingFilename = baseDir + '/accounts/blocking.txt'
    if os.path.isfile(globalBlockingFilename):
        with open(globalBlockingFilename, 'r') as fpBlocked:
            blockedStr = fpBlocked.read()
            if '*@' + domain in blockedStr:
                return True
            if shortDomain:
                if '*@' + shortDomain in blockedStr:
                    return True
    return False


def isBlocked(baseDir: str, nickname: str, domain: str,
              blockNickname: str, blockDomain: str) -> bool:
    """Is the given nickname blocked?
    """
    if isEvil(blockDomain):
        return True
    globalBlockingFilename = baseDir + '/accounts/blocking.txt'
    if os.path.isfile(globalBlockingFilename):
        if '*@' + blockDomain in open(globalBlockingFilename).read():
            return True
        if blockNickname:
            blockHandle = blockNickname + '@' + blockDomain
            if blockHandle in open(globalBlockingFilename).read():
                return True
    allowFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/allowedinstances.txt'
    if os.path.isfile(allowFilename):
        if blockDomain not in open(allowFilename).read():
            return True
    blockingFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/blocking.txt'
    if os.path.isfile(blockingFilename):
        if '*@' + blockDomain in open(blockingFilename).read():
            return True
        if blockNickname:
            blockHandle = blockNickname + '@' + blockDomain
            if blockHandle in open(blockingFilename).read():
                return True
    return False


def outboxBlock(baseDir: str, httpPrefix: str,
                nickname: str, domain: str, port: int,
                messageJson: {}, debug: bool) -> None:
    """ When a block request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: block - no type')
        return
    if not messageJson['type'] == 'Block':
        if debug:
            print('DEBUG: not a block')
        return
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in block')
        return
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: block object is not string')
        return
    if debug:
        print('DEBUG: c2s block request arrived in outbox')

    messageId = removeIdEnding(messageJson['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s block object is not a status')
        return
    if not hasUsersPath(messageId):
        if debug:
            print('DEBUG: c2s block object has no nickname')
        return
    if ':' in domain:
        domain = domain.split(':')[0]
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s block post not found in inbox or outbox')
            print(messageId)
        return
    nicknameBlocked = getNicknameFromActor(messageJson['object'])
    if not nicknameBlocked:
        print('WARN: unable to find nickname in ' + messageJson['object'])
        return
    domainBlocked, portBlocked = getDomainFromActor(messageJson['object'])
    domainBlockedFull = getFullDomain(domainBlocked, portBlocked)

    addBlock(baseDir, nickname, domain,
             nicknameBlocked, domainBlockedFull)

    if debug:
        print('DEBUG: post blocked via c2s - ' + postFilename)


def outboxUndoBlock(baseDir: str, httpPrefix: str,
                    nickname: str, domain: str, port: int,
                    messageJson: {}, debug: bool) -> None:
    """ When an undo block request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: undo block - no type')
        return
    if not messageJson['type'] == 'Undo':
        if debug:
            print('DEBUG: not an undo block')
        return
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in undo block')
        return
    if not isinstance(messageJson['object'], dict):
        if debug:
            print('DEBUG: undo block object is not string')
        return

    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: undo block - no type')
        return
    if not messageJson['object']['type'] == 'Block':
        if debug:
            print('DEBUG: not an undo block')
        return
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: no object in undo block')
        return
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: undo block object is not string')
        return
    if debug:
        print('DEBUG: c2s undo block request arrived in outbox')

    messageId = removeIdEnding(messageJson['object']['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s undo block object is not a status')
        return
    if not hasUsersPath(messageId):
        if debug:
            print('DEBUG: c2s undo block object has no nickname')
        return
    if ':' in domain:
        domain = domain.split(':')[0]
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo block post not found in inbox or outbox')
            print(messageId)
        return
    nicknameBlocked = getNicknameFromActor(messageJson['object']['object'])
    if not nicknameBlocked:
        print('WARN: unable to find nickname in ' +
              messageJson['object']['object'])
        return
    domainObject = messageJson['object']['object']
    domainBlocked, portBlocked = getDomainFromActor(domainObject)
    domainBlockedFull = getFullDomain(domainBlocked, portBlocked)

    removeBlock(baseDir, nickname, domain,
                nicknameBlocked, domainBlockedFull)
    if debug:
        print('DEBUG: post undo blocked via c2s - ' + postFilename)
