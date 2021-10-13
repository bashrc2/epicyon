__filename__ = "blocking.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import json
import time
from datetime import datetime
from utils import removeDomainPort
from utils import hasObjectDict
from utils import isAccountDir
from utils import getCachedPostFilename
from utils import loadJson
from utils import saveJson
from utils import fileLastModified
from utils import setConfigParam
from utils import hasUsersPath
from utils import getFullDomain
from utils import removeIdEnding
from utils import isEvil
from utils import locatePost
from utils import evilIncarnate
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import acctDir
from utils import localActorUrl
from utils import hasActor
from conversation import muteConversation
from conversation import unmuteConversation


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
        with open(blockingFilename, 'a+') as blockFile:
            blockFile.write(blockHandle + '\n')
    else:
        blockHashtag = blockNickname
        # is the hashtag already blocked?
        if os.path.isfile(blockingFilename):
            if blockHashtag + '\n' in open(blockingFilename).read():
                return False
        # block a hashtag
        with open(blockingFilename, 'a+') as blockFile:
            blockFile.write(blockHashtag + '\n')
    return True


def addBlock(baseDir: str, nickname: str, domain: str,
             blockNickname: str, blockDomain: str) -> bool:
    """Block the given account
    """
    if blockDomain.startswith(domain) and nickname == blockNickname:
        # don't block self
        return False

    domain = removeDomainPort(domain)
    blockingFilename = acctDir(baseDir, nickname, domain) + '/blocking.txt'
    blockHandle = blockNickname + '@' + blockDomain
    if os.path.isfile(blockingFilename):
        if blockHandle + '\n' in open(blockingFilename).read():
            return False

    # if we are following then unfollow
    followingFilename = acctDir(baseDir, nickname, domain) + '/following.txt'
    if os.path.isfile(followingFilename):
        if blockHandle + '\n' in open(followingFilename).read():
            followingStr = ''
            with open(followingFilename, 'r') as followingFile:
                followingStr = followingFile.read()
                followingStr = followingStr.replace(blockHandle + '\n', '')
            with open(followingFilename, 'w+') as followingFile:
                followingFile.write(followingStr)

    # if they are a follower then remove them
    followersFilename = acctDir(baseDir, nickname, domain) + '/followers.txt'
    if os.path.isfile(followersFilename):
        if blockHandle + '\n' in open(followersFilename).read():
            followersStr = ''
            with open(followersFilename, 'r') as followersFile:
                followersStr = followersFile.read()
                followersStr = followersStr.replace(blockHandle + '\n', '')
            with open(followersFilename, 'w+') as followersFile:
                followersFile.write(followersStr)

    with open(blockingFilename, 'a+') as blockFile:
        blockFile.write(blockHandle + '\n')
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
    domain = removeDomainPort(domain)
    unblockingFilename = acctDir(baseDir, nickname, domain) + '/blocking.txt'
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


def updateBlockedCache(baseDir: str,
                       blockedCache: [],
                       blockedCacheLastUpdated: int,
                       blockedCacheUpdateSecs: int) -> int:
    """Updates the cache of globally blocked domains held in memory
    """
    currTime = int(time.time())
    if blockedCacheLastUpdated > currTime:
        print('WARN: Cache updated in the future')
        blockedCacheLastUpdated = 0
    secondsSinceLastUpdate = currTime - blockedCacheLastUpdated
    if secondsSinceLastUpdate < blockedCacheUpdateSecs:
        return blockedCacheLastUpdated
    globalBlockingFilename = baseDir + '/accounts/blocking.txt'
    if not os.path.isfile(globalBlockingFilename):
        return blockedCacheLastUpdated
    with open(globalBlockingFilename, 'r') as fpBlocked:
        blockedLines = fpBlocked.readlines()
        # remove newlines
        for index in range(len(blockedLines)):
            blockedLines[index] = blockedLines[index].replace('\n', '')
        # update the cache
        blockedCache.clear()
        blockedCache += blockedLines
    return currTime


def _getShortDomain(domain: str) -> str:
    """ by checking a shorter version we can thwart adversaries
    who constantly change their subdomain
    e.g. subdomain123.mydomain.com becomes mydomain.com
    """
    sections = domain.split('.')
    noOfSections = len(sections)
    if noOfSections > 2:
        return sections[noOfSections-2] + '.' + sections[-1]
    return None


def isBlockedDomain(baseDir: str, domain: str,
                    blockedCache: [] = None) -> bool:
    """Is the given domain blocked?
    """
    if '.' not in domain:
        return False

    if isEvil(domain):
        return True

    shortDomain = _getShortDomain(domain)

    if not brochModeIsActive(baseDir):
        if blockedCache:
            for blockedStr in blockedCache:
                if '*@' + domain in blockedStr:
                    return True
                if shortDomain:
                    if '*@' + shortDomain in blockedStr:
                        return True
        else:
            # instance block list
            globalBlockingFilename = baseDir + '/accounts/blocking.txt'
            if os.path.isfile(globalBlockingFilename):
                with open(globalBlockingFilename, 'r') as fpBlocked:
                    blockedStr = fpBlocked.read()
                    if '*@' + domain in blockedStr:
                        return True
                    if shortDomain:
                        if '*@' + shortDomain in blockedStr:
                            return True
    else:
        allowFilename = baseDir + '/accounts/allowedinstances.txt'
        # instance allow list
        if not shortDomain:
            if domain not in open(allowFilename).read():
                return True
        else:
            if shortDomain not in open(allowFilename).read():
                return True

    return False


def isBlocked(baseDir: str, nickname: str, domain: str,
              blockNickname: str, blockDomain: str,
              blockedCache: [] = None) -> bool:
    """Is the given nickname blocked?
    """
    if isEvil(blockDomain):
        return True

    blockHandle = None
    if blockNickname and blockDomain:
        blockHandle = blockNickname + '@' + blockDomain

    if not brochModeIsActive(baseDir):
        # instance level block list
        if blockedCache:
            for blockedStr in blockedCache:
                if '*@' + domain in blockedStr:
                    return True
                if blockHandle:
                    if blockHandle in blockedStr:
                        return True
        else:
            globalBlockingFilename = baseDir + '/accounts/blocking.txt'
            if os.path.isfile(globalBlockingFilename):
                if '*@' + blockDomain in open(globalBlockingFilename).read():
                    return True
                if blockHandle:
                    if blockHandle in open(globalBlockingFilename).read():
                        return True
    else:
        # instance allow list
        allowFilename = baseDir + '/accounts/allowedinstances.txt'
        shortDomain = _getShortDomain(blockDomain)
        if not shortDomain:
            if blockDomain not in open(allowFilename).read():
                return True
        else:
            if shortDomain not in open(allowFilename).read():
                return True

    # account level allow list
    accountDir = acctDir(baseDir, nickname, domain)
    allowFilename = accountDir + '/allowedinstances.txt'
    if os.path.isfile(allowFilename):
        if blockDomain not in open(allowFilename).read():
            return True

    # account level block list
    blockingFilename = accountDir + '/blocking.txt'
    if os.path.isfile(blockingFilename):
        if '*@' + blockDomain in open(blockingFilename).read():
            return True
        if blockHandle:
            if blockHandle in open(blockingFilename).read():
                return True
    return False


def outboxBlock(baseDir: str, httpPrefix: str,
                nickname: str, domain: str, port: int,
                messageJson: {}, debug: bool) -> bool:
    """ When a block request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: block - no type')
        return False
    if not messageJson['type'] == 'Block':
        if debug:
            print('DEBUG: not a block')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in block')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: block object is not string')
        return False
    if debug:
        print('DEBUG: c2s block request arrived in outbox')

    messageId = removeIdEnding(messageJson['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s block object is not a status')
        return False
    if not hasUsersPath(messageId):
        if debug:
            print('DEBUG: c2s block object has no nickname')
        return False
    domain = removeDomainPort(domain)
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s block post not found in inbox or outbox')
            print(messageId)
        return False
    nicknameBlocked = getNicknameFromActor(messageJson['object'])
    if not nicknameBlocked:
        print('WARN: unable to find nickname in ' + messageJson['object'])
        return False
    domainBlocked, portBlocked = getDomainFromActor(messageJson['object'])
    domainBlockedFull = getFullDomain(domainBlocked, portBlocked)

    addBlock(baseDir, nickname, domain,
             nicknameBlocked, domainBlockedFull)

    if debug:
        print('DEBUG: post blocked via c2s - ' + postFilename)
    return True


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
    if not hasObjectDict(messageJson):
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
    domain = removeDomainPort(domain)
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


def mutePost(baseDir: str, nickname: str, domain: str, port: int,
             httpPrefix: str, postId: str, recentPostsCache: {},
             debug: bool) -> None:
    """ Mutes the given post
    """
    print('mutePost: postId ' + postId)
    postFilename = locatePost(baseDir, nickname, domain, postId)
    if not postFilename:
        print('mutePost: file not found ' + postId)
        return
    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        print('mutePost: object not loaded ' + postId)
        return
    print('mutePost: ' + str(postJsonObject))

    postJsonObj = postJsonObject
    alsoUpdatePostId = None
    if hasObjectDict(postJsonObject):
        postJsonObj = postJsonObject['object']
    else:
        if postJsonObject.get('object'):
            if isinstance(postJsonObject['object'], str):
                alsoUpdatePostId = removeIdEnding(postJsonObject['object'])

    domainFull = getFullDomain(domain, port)
    actor = localActorUrl(httpPrefix, nickname, domainFull)

    if postJsonObj.get('conversation'):
        muteConversation(baseDir, nickname, domain,
                         postJsonObj['conversation'])

    # does this post have ignores on it from differenent actors?
    if not postJsonObj.get('ignores'):
        if debug:
            print('DEBUG: Adding initial mute to ' + postId)
        ignoresJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'id': postId,
            'type': 'Collection',
            "totalItems": 1,
            'items': [{
                'type': 'Ignore',
                'actor': actor
            }]
        }
        postJsonObj['ignores'] = ignoresJson
    else:
        if not postJsonObj['ignores'].get('items'):
            postJsonObj['ignores']['items'] = []
        itemsList = postJsonObj['ignores']['items']
        for ignoresItem in itemsList:
            if ignoresItem.get('actor'):
                if ignoresItem['actor'] == actor:
                    return
        newIgnore = {
            'type': 'Ignore',
            'actor': actor
        }
        igIt = len(itemsList)
        itemsList.append(newIgnore)
        postJsonObj['ignores']['totalItems'] = igIt
    postJsonObj['muted'] = True
    if saveJson(postJsonObject, postFilename):
        print('mutePost: saved ' + postFilename)

    # remove cached post so that the muted version gets recreated
    # without its content text and/or image
    cachedPostFilename = \
        getCachedPostFilename(baseDir, nickname, domain, postJsonObject)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
                print('MUTE: cached post removed ' + cachedPostFilename)
            except BaseException:
                pass
        else:
            print('MUTE: cached post not found ' + cachedPostFilename)

    with open(postFilename + '.muted', 'w+') as muteFile:
        muteFile.write('\n')
        print('MUTE: ' + postFilename + '.muted file added')

    # if the post is in the recent posts cache then mark it as muted
    if recentPostsCache.get('index'):
        postId = \
            removeIdEnding(postJsonObject['id']).replace('/', '#')
        if postId in recentPostsCache['index']:
            print('MUTE: ' + postId + ' is in recent posts cache')
        if recentPostsCache.get('json'):
            recentPostsCache['json'][postId] = json.dumps(postJsonObject)
            print('MUTE: ' + postId +
                  ' marked as muted in recent posts memory cache')
        if recentPostsCache.get('html'):
            if recentPostsCache['html'].get(postId):
                del recentPostsCache['html'][postId]
                print('MUTE: ' + postId + ' removed cached html')

    if alsoUpdatePostId:
        postFilename = locatePost(baseDir, nickname, domain, alsoUpdatePostId)
        if os.path.isfile(postFilename):
            postJsonObj = loadJson(postFilename)
            cachedPostFilename = \
                getCachedPostFilename(baseDir, nickname, domain,
                                      postJsonObj)
            if cachedPostFilename:
                if os.path.isfile(cachedPostFilename):
                    try:
                        os.remove(cachedPostFilename)
                        print('MUTE: cached referenced post removed ' +
                              cachedPostFilename)
                    except BaseException:
                        pass

        if recentPostsCache.get('json'):
            if recentPostsCache['json'].get(alsoUpdatePostId):
                del recentPostsCache['json'][alsoUpdatePostId]
                print('MUTE: ' + alsoUpdatePostId + ' removed referenced json')
        if recentPostsCache.get('html'):
            if recentPostsCache['html'].get(alsoUpdatePostId):
                del recentPostsCache['html'][alsoUpdatePostId]
                print('MUTE: ' + alsoUpdatePostId + ' removed referenced html')


def unmutePost(baseDir: str, nickname: str, domain: str, port: int,
               httpPrefix: str, postId: str, recentPostsCache: {},
               debug: bool) -> None:
    """ Unmutes the given post
    """
    postFilename = locatePost(baseDir, nickname, domain, postId)
    if not postFilename:
        return
    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return

    muteFilename = postFilename + '.muted'
    if os.path.isfile(muteFilename):
        try:
            os.remove(muteFilename)
        except BaseException:
            pass
        print('UNMUTE: ' + muteFilename + ' file removed')

    postJsonObj = postJsonObject
    alsoUpdatePostId = None
    if hasObjectDict(postJsonObject):
        postJsonObj = postJsonObject['object']
    else:
        if postJsonObject.get('object'):
            if isinstance(postJsonObject['object'], str):
                alsoUpdatePostId = removeIdEnding(postJsonObject['object'])

    if postJsonObj.get('conversation'):
        unmuteConversation(baseDir, nickname, domain,
                           postJsonObj['conversation'])

    if postJsonObj.get('ignores'):
        domainFull = getFullDomain(domain, port)
        actor = localActorUrl(httpPrefix, nickname, domainFull)
        totalItems = 0
        if postJsonObj['ignores'].get('totalItems'):
            totalItems = postJsonObj['ignores']['totalItems']
        itemsList = postJsonObj['ignores']['items']
        for ignoresItem in itemsList:
            if ignoresItem.get('actor'):
                if ignoresItem['actor'] == actor:
                    if debug:
                        print('DEBUG: mute was removed for ' + actor)
                    itemsList.remove(ignoresItem)
                    break
        if totalItems == 1:
            if debug:
                print('DEBUG: mute was removed from post')
            del postJsonObj['ignores']
        else:
            igItLen = len(postJsonObj['ignores']['items'])
            postJsonObj['ignores']['totalItems'] = igItLen
    postJsonObj['muted'] = False
    saveJson(postJsonObject, postFilename)

    # remove cached post so that the muted version gets recreated
    # with its content text and/or image
    cachedPostFilename = \
        getCachedPostFilename(baseDir, nickname, domain, postJsonObject)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except BaseException:
                pass

    # if the post is in the recent posts cache then mark it as unmuted
    if recentPostsCache.get('index'):
        postId = \
            removeIdEnding(postJsonObject['id']).replace('/', '#')
        if postId in recentPostsCache['index']:
            print('UNMUTE: ' + postId + ' is in recent posts cache')
        if recentPostsCache.get('json'):
            recentPostsCache['json'][postId] = json.dumps(postJsonObject)
            print('UNMUTE: ' + postId +
                  ' marked as unmuted in recent posts cache')
        if recentPostsCache.get('html'):
            if recentPostsCache['html'].get(postId):
                del recentPostsCache['html'][postId]
                print('UNMUTE: ' + postId + ' removed cached html')
    if alsoUpdatePostId:
        postFilename = locatePost(baseDir, nickname, domain, alsoUpdatePostId)
        if os.path.isfile(postFilename):
            postJsonObj = loadJson(postFilename)
            cachedPostFilename = \
                getCachedPostFilename(baseDir, nickname, domain,
                                      postJsonObj)
            if cachedPostFilename:
                if os.path.isfile(cachedPostFilename):
                    try:
                        os.remove(cachedPostFilename)
                        print('MUTE: cached referenced post removed ' +
                              cachedPostFilename)
                    except BaseException:
                        pass

        if recentPostsCache.get('json'):
            if recentPostsCache['json'].get(alsoUpdatePostId):
                del recentPostsCache['json'][alsoUpdatePostId]
                print('UNMUTE: ' +
                      alsoUpdatePostId + ' removed referenced json')
        if recentPostsCache.get('html'):
            if recentPostsCache['html'].get(alsoUpdatePostId):
                del recentPostsCache['html'][alsoUpdatePostId]
                print('UNMUTE: ' +
                      alsoUpdatePostId + ' removed referenced html')


def outboxMute(baseDir: str, httpPrefix: str,
               nickname: str, domain: str, port: int,
               messageJson: {}, debug: bool,
               recentPostsCache: {}) -> None:
    """When a mute is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        return
    if not hasActor(messageJson, debug):
        return
    domainFull = getFullDomain(domain, port)
    if not messageJson['actor'].endswith(domainFull + '/users/' + nickname):
        return
    if not messageJson['type'] == 'Ignore':
        return
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in mute')
        return
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: mute object is not string')
        return
    if debug:
        print('DEBUG: c2s mute request arrived in outbox')

    messageId = removeIdEnding(messageJson['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s mute object is not a status')
        return
    if not hasUsersPath(messageId):
        if debug:
            print('DEBUG: c2s mute object has no nickname')
        return
    domain = removeDomainPort(domain)
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s mute post not found in inbox or outbox')
            print(messageId)
        return
    nicknameMuted = getNicknameFromActor(messageJson['object'])
    if not nicknameMuted:
        print('WARN: unable to find nickname in ' + messageJson['object'])
        return

    mutePost(baseDir, nickname, domain, port,
             httpPrefix, messageJson['object'], recentPostsCache,
             debug)

    if debug:
        print('DEBUG: post muted via c2s - ' + postFilename)


def outboxUndoMute(baseDir: str, httpPrefix: str,
                   nickname: str, domain: str, port: int,
                   messageJson: {}, debug: bool,
                   recentPostsCache: {}) -> None:
    """When an undo mute is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        return
    if not hasActor(messageJson, debug):
        return
    domainFull = getFullDomain(domain, port)
    if not messageJson['actor'].endswith(domainFull + '/users/' + nickname):
        return
    if not messageJson['type'] == 'Undo':
        return
    if not hasObjectDict(messageJson):
        return
    if not messageJson['object'].get('type'):
        return
    if messageJson['object']['type'] != 'Ignore':
        return
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: undo mute object is not a string')
        return
    if debug:
        print('DEBUG: c2s undo mute request arrived in outbox')

    messageId = removeIdEnding(messageJson['object']['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s undo mute object is not a status')
        return
    if not hasUsersPath(messageId):
        if debug:
            print('DEBUG: c2s undo mute object has no nickname')
        return
    domain = removeDomainPort(domain)
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo mute post not found in inbox or outbox')
            print(messageId)
        return
    nicknameMuted = getNicknameFromActor(messageJson['object']['object'])
    if not nicknameMuted:
        print('WARN: unable to find nickname in ' +
              messageJson['object']['object'])
        return

    unmutePost(baseDir, nickname, domain, port,
               httpPrefix, messageJson['object']['object'],
               recentPostsCache, debug)

    if debug:
        print('DEBUG: post undo mute via c2s - ' + postFilename)


def brochModeIsActive(baseDir: str) -> bool:
    """Returns true if broch mode is active
    """
    allowFilename = baseDir + '/accounts/allowedinstances.txt'
    return os.path.isfile(allowFilename)


def setBrochMode(baseDir: str, domainFull: str, enabled: bool) -> None:
    """Broch mode can be used to lock down the instance during
    a period of time when it is temporarily under attack.
    For example, where an adversary is constantly spinning up new
    instances.
    It surveys the following lists of all accounts and uses that
    to construct an instance level allow list. Anything arriving
    which is then not from one of the allowed domains will be dropped
    """
    allowFilename = baseDir + '/accounts/allowedinstances.txt'

    if not enabled:
        # remove instance allow list
        if os.path.isfile(allowFilename):
            try:
                os.remove(allowFilename)
            except BaseException:
                pass
            print('Broch mode turned off')
    else:
        if os.path.isfile(allowFilename):
            lastModified = fileLastModified(allowFilename)
            print('Broch mode already activated ' + lastModified)
            return
        # generate instance allow list
        allowedDomains = [domainFull]
        followFiles = ('following.txt', 'followers.txt')
        for subdir, dirs, files in os.walk(baseDir + '/accounts'):
            for acct in dirs:
                if not isAccountDir(acct):
                    continue
                accountDir = os.path.join(baseDir + '/accounts', acct)
                for followFileType in followFiles:
                    followingFilename = accountDir + '/' + followFileType
                    if not os.path.isfile(followingFilename):
                        continue
                    with open(followingFilename, 'r') as f:
                        followList = f.readlines()
                        for handle in followList:
                            if '@' not in handle:
                                continue
                            handle = handle.replace('\n', '')
                            handleDomain = handle.split('@')[1]
                            if handleDomain not in allowedDomains:
                                allowedDomains.append(handleDomain)
            break

        # write the allow file
        with open(allowFilename, 'w+') as allowFile:
            allowFile.write(domainFull + '\n')
            for d in allowedDomains:
                allowFile.write(d + '\n')
            print('Broch mode enabled')

    setConfigParam(baseDir, "brochMode", enabled)


def brochModeLapses(baseDir: str, lapseDays: int = 7) -> bool:
    """After broch mode is enabled it automatically
    elapses after a period of time
    """
    allowFilename = baseDir + '/accounts/allowedinstances.txt'
    if not os.path.isfile(allowFilename):
        return False
    lastModified = fileLastModified(allowFilename)
    modifiedDate = None
    try:
        modifiedDate = \
            datetime.strptime(lastModified, "%Y-%m-%dT%H:%M:%SZ")
    except BaseException:
        return False
    if not modifiedDate:
        return False
    currTime = datetime.datetime.utcnow()
    daysSinceBroch = (currTime - modifiedDate).days
    if daysSinceBroch >= lapseDays:
        removed = False
        try:
            os.remove(allowFilename)
            removed = True
        except BaseException:
            pass
        if removed:
            setConfigParam(baseDir, "brochMode", False)
            print('Broch mode has elapsed')
            return True
    return False
