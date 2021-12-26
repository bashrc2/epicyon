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
from utils import hasObjectString
from utils import hasObjectStringObject
from utils import hasObjectStringType
from utils import removeDomainPort
from utils import has_object_dict
from utils import isAccountDir
from utils import getCachedPostFilename
from utils import loadJson
from utils import saveJson
from utils import fileLastModified
from utils import setConfigParam
from utils import has_users_path
from utils import get_full_domain
from utils import removeIdEnding
from utils import isEvil
from utils import locatePost
from utils import evilIncarnate
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import acct_dir
from utils import local_actor_url
from utils import hasActor
from conversation import muteConversation
from conversation import unmuteConversation


def addGlobalBlock(base_dir: str,
                   blockNickname: str, blockDomain: str) -> bool:
    """Global block which applies to all accounts
    """
    blockingFilename = base_dir + '/accounts/blocking.txt'
    if not blockNickname.startswith('#'):
        # is the handle already blocked?
        blockHandle = blockNickname + '@' + blockDomain
        if os.path.isfile(blockingFilename):
            if blockHandle in open(blockingFilename).read():
                return False
        # block an account handle or domain
        try:
            with open(blockingFilename, 'a+') as blockFile:
                blockFile.write(blockHandle + '\n')
        except OSError:
            print('EX: unable to save blocked handle ' + blockHandle)
            return False
    else:
        blockHashtag = blockNickname
        # is the hashtag already blocked?
        if os.path.isfile(blockingFilename):
            if blockHashtag + '\n' in open(blockingFilename).read():
                return False
        # block a hashtag
        try:
            with open(blockingFilename, 'a+') as blockFile:
                blockFile.write(blockHashtag + '\n')
        except OSError:
            print('EX: unable to save blocked hashtag ' + blockHashtag)
            return False
    return True


def addBlock(base_dir: str, nickname: str, domain: str,
             blockNickname: str, blockDomain: str) -> bool:
    """Block the given account
    """
    if blockDomain.startswith(domain) and nickname == blockNickname:
        # don't block self
        return False

    domain = removeDomainPort(domain)
    blockingFilename = acct_dir(base_dir, nickname, domain) + '/blocking.txt'
    blockHandle = blockNickname + '@' + blockDomain
    if os.path.isfile(blockingFilename):
        if blockHandle + '\n' in open(blockingFilename).read():
            return False

    # if we are following then unfollow
    followingFilename = acct_dir(base_dir, nickname, domain) + '/following.txt'
    if os.path.isfile(followingFilename):
        if blockHandle + '\n' in open(followingFilename).read():
            followingStr = ''
            try:
                with open(followingFilename, 'r') as followingFile:
                    followingStr = followingFile.read()
            except OSError:
                print('EX: Unable to read following ' + followingFilename)
                return False

            if followingStr:
                followingStr = followingStr.replace(blockHandle + '\n', '')

            try:
                with open(followingFilename, 'w+') as followingFile:
                    followingFile.write(followingStr)
            except OSError:
                print('EX: Unable to write following ' + followingStr)
                return False

    # if they are a follower then remove them
    followersFilename = acct_dir(base_dir, nickname, domain) + '/followers.txt'
    if os.path.isfile(followersFilename):
        if blockHandle + '\n' in open(followersFilename).read():
            followersStr = ''
            try:
                with open(followersFilename, 'r') as followersFile:
                    followersStr = followersFile.read()
            except OSError:
                print('EX: Unable to read followers ' + followersFilename)
                return False

            if followersStr:
                followersStr = followersStr.replace(blockHandle + '\n', '')

            try:
                with open(followersFilename, 'w+') as followersFile:
                    followersFile.write(followersStr)
            except OSError:
                print('EX: Unable to write followers ' + followersStr)
                return False

    try:
        with open(blockingFilename, 'a+') as blockFile:
            blockFile.write(blockHandle + '\n')
    except OSError:
        print('EX: unable to append block handle ' + blockHandle)
        return False
    return True


def removeGlobalBlock(base_dir: str,
                      unblockNickname: str,
                      unblockDomain: str) -> bool:
    """Unblock the given global block
    """
    unblockingFilename = base_dir + '/accounts/blocking.txt'
    if not unblockNickname.startswith('#'):
        unblockHandle = unblockNickname + '@' + unblockDomain
        if os.path.isfile(unblockingFilename):
            if unblockHandle in open(unblockingFilename).read():
                try:
                    with open(unblockingFilename, 'r') as fp:
                        with open(unblockingFilename + '.new', 'w+') as fpnew:
                            for line in fp:
                                handle = \
                                    line.replace('\n', '').replace('\r', '')
                                if unblockHandle not in line:
                                    fpnew.write(handle + '\n')
                except OSError as ex:
                    print('EX: failed to remove global block ' +
                          unblockingFilename + ' ' + str(ex))
                    return False

                if os.path.isfile(unblockingFilename + '.new'):
                    try:
                        os.rename(unblockingFilename + '.new',
                                  unblockingFilename)
                    except OSError:
                        print('EX: unable to rename ' + unblockingFilename)
                        return False
                    return True
    else:
        unblockHashtag = unblockNickname
        if os.path.isfile(unblockingFilename):
            if unblockHashtag + '\n' in open(unblockingFilename).read():
                try:
                    with open(unblockingFilename, 'r') as fp:
                        with open(unblockingFilename + '.new', 'w+') as fpnew:
                            for line in fp:
                                blockLine = \
                                    line.replace('\n', '').replace('\r', '')
                                if unblockHashtag not in line:
                                    fpnew.write(blockLine + '\n')
                except OSError as ex:
                    print('EX: failed to remove global hashtag block ' +
                          unblockingFilename + ' ' + str(ex))
                    return False

                if os.path.isfile(unblockingFilename + '.new'):
                    try:
                        os.rename(unblockingFilename + '.new',
                                  unblockingFilename)
                    except OSError:
                        print('EX: unable to rename 2 ' + unblockingFilename)
                        return False
                    return True
    return False


def removeBlock(base_dir: str, nickname: str, domain: str,
                unblockNickname: str, unblockDomain: str) -> bool:
    """Unblock the given account
    """
    domain = removeDomainPort(domain)
    unblockingFilename = acct_dir(base_dir, nickname, domain) + '/blocking.txt'
    unblockHandle = unblockNickname + '@' + unblockDomain
    if os.path.isfile(unblockingFilename):
        if unblockHandle in open(unblockingFilename).read():
            try:
                with open(unblockingFilename, 'r') as fp:
                    with open(unblockingFilename + '.new', 'w+') as fpnew:
                        for line in fp:
                            handle = line.replace('\n', '').replace('\r', '')
                            if unblockHandle not in line:
                                fpnew.write(handle + '\n')
            except OSError as ex:
                print('EX: failed to remove block ' +
                      unblockingFilename + ' ' + str(ex))
                return False

            if os.path.isfile(unblockingFilename + '.new'):
                try:
                    os.rename(unblockingFilename + '.new', unblockingFilename)
                except OSError:
                    print('EX: unable to rename 3 ' + unblockingFilename)
                    return False
                return True
    return False


def isBlockedHashtag(base_dir: str, hashtag: str) -> bool:
    """Is the given hashtag blocked?
    """
    # avoid very long hashtags
    if len(hashtag) > 32:
        return True
    globalBlockingFilename = base_dir + '/accounts/blocking.txt'
    if os.path.isfile(globalBlockingFilename):
        hashtag = hashtag.strip('\n').strip('\r')
        if not hashtag.startswith('#'):
            hashtag = '#' + hashtag
        if hashtag + '\n' in open(globalBlockingFilename).read():
            return True
    return False


def getDomainBlocklist(base_dir: str) -> str:
    """Returns all globally blocked domains as a string
    This can be used for fast matching to mitigate flooding
    """
    blockedStr = ''

    evilDomains = evilIncarnate()
    for evil in evilDomains:
        blockedStr += evil + '\n'

    globalBlockingFilename = base_dir + '/accounts/blocking.txt'
    if not os.path.isfile(globalBlockingFilename):
        return blockedStr
    try:
        with open(globalBlockingFilename, 'r') as fpBlocked:
            blockedStr += fpBlocked.read()
    except OSError:
        print('EX: unable to read ' + globalBlockingFilename)
    return blockedStr


def updateBlockedCache(base_dir: str,
                       blockedCache: [],
                       blockedCacheLastUpdated: int,
                       blockedCacheUpdateSecs: int) -> int:
    """Updates the cache of globally blocked domains held in memory
    """
    curr_time = int(time.time())
    if blockedCacheLastUpdated > curr_time:
        print('WARN: Cache updated in the future')
        blockedCacheLastUpdated = 0
    secondsSinceLastUpdate = curr_time - blockedCacheLastUpdated
    if secondsSinceLastUpdate < blockedCacheUpdateSecs:
        return blockedCacheLastUpdated
    globalBlockingFilename = base_dir + '/accounts/blocking.txt'
    if not os.path.isfile(globalBlockingFilename):
        return blockedCacheLastUpdated
    try:
        with open(globalBlockingFilename, 'r') as fpBlocked:
            blockedLines = fpBlocked.readlines()
            # remove newlines
            for index in range(len(blockedLines)):
                blockedLines[index] = blockedLines[index].replace('\n', '')
            # update the cache
            blockedCache.clear()
            blockedCache += blockedLines
    except OSError as ex:
        print('EX: unable to read ' + globalBlockingFilename + ' ' + str(ex))
    return curr_time


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


def isBlockedDomain(base_dir: str, domain: str,
                    blockedCache: [] = None) -> bool:
    """Is the given domain blocked?
    """
    if '.' not in domain:
        return False

    if isEvil(domain):
        return True

    shortDomain = _getShortDomain(domain)

    if not broch_modeIsActive(base_dir):
        if blockedCache:
            for blockedStr in blockedCache:
                if '*@' + domain in blockedStr:
                    return True
                if shortDomain:
                    if '*@' + shortDomain in blockedStr:
                        return True
        else:
            # instance block list
            globalBlockingFilename = base_dir + '/accounts/blocking.txt'
            if os.path.isfile(globalBlockingFilename):
                try:
                    with open(globalBlockingFilename, 'r') as fpBlocked:
                        blockedStr = fpBlocked.read()
                        if '*@' + domain in blockedStr:
                            return True
                        if shortDomain:
                            if '*@' + shortDomain in blockedStr:
                                return True
                except OSError as ex:
                    print('EX: unable to read ' + globalBlockingFilename +
                          ' ' + str(ex))
    else:
        allowFilename = base_dir + '/accounts/allowedinstances.txt'
        # instance allow list
        if not shortDomain:
            if domain not in open(allowFilename).read():
                return True
        else:
            if shortDomain not in open(allowFilename).read():
                return True

    return False


def isBlocked(base_dir: str, nickname: str, domain: str,
              blockNickname: str, blockDomain: str,
              blockedCache: [] = None) -> bool:
    """Is the given nickname blocked?
    """
    if isEvil(blockDomain):
        return True

    blockHandle = None
    if blockNickname and blockDomain:
        blockHandle = blockNickname + '@' + blockDomain

    if not broch_modeIsActive(base_dir):
        # instance level block list
        if blockedCache:
            for blockedStr in blockedCache:
                if '*@' + domain in blockedStr:
                    return True
                if blockHandle:
                    if blockHandle in blockedStr:
                        return True
        else:
            globalBlockingFilename = base_dir + '/accounts/blocking.txt'
            if os.path.isfile(globalBlockingFilename):
                if '*@' + blockDomain in open(globalBlockingFilename).read():
                    return True
                if blockHandle:
                    if blockHandle in open(globalBlockingFilename).read():
                        return True
    else:
        # instance allow list
        allowFilename = base_dir + '/accounts/allowedinstances.txt'
        shortDomain = _getShortDomain(blockDomain)
        if not shortDomain:
            if blockDomain not in open(allowFilename).read():
                return True
        else:
            if shortDomain not in open(allowFilename).read():
                return True

    # account level allow list
    accountDir = acct_dir(base_dir, nickname, domain)
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


def outboxBlock(base_dir: str, http_prefix: str,
                nickname: str, domain: str, port: int,
                message_json: {}, debug: bool) -> bool:
    """ When a block request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        if debug:
            print('DEBUG: block - no type')
        return False
    if not message_json['type'] == 'Block':
        if debug:
            print('DEBUG: not a block')
        return False
    if not hasObjectString(message_json, debug):
        return False
    if debug:
        print('DEBUG: c2s block request arrived in outbox')

    messageId = removeIdEnding(message_json['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s block object is not a status')
        return False
    if not has_users_path(messageId):
        if debug:
            print('DEBUG: c2s block object has no nickname')
        return False
    domain = removeDomainPort(domain)
    postFilename = locatePost(base_dir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s block post not found in inbox or outbox')
            print(messageId)
        return False
    nicknameBlocked = getNicknameFromActor(message_json['object'])
    if not nicknameBlocked:
        print('WARN: unable to find nickname in ' + message_json['object'])
        return False
    domainBlocked, portBlocked = getDomainFromActor(message_json['object'])
    domainBlockedFull = get_full_domain(domainBlocked, portBlocked)

    addBlock(base_dir, nickname, domain,
             nicknameBlocked, domainBlockedFull)

    if debug:
        print('DEBUG: post blocked via c2s - ' + postFilename)
    return True


def outboxUndoBlock(base_dir: str, http_prefix: str,
                    nickname: str, domain: str, port: int,
                    message_json: {}, debug: bool) -> None:
    """ When an undo block request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        if debug:
            print('DEBUG: undo block - no type')
        return
    if not message_json['type'] == 'Undo':
        if debug:
            print('DEBUG: not an undo block')
        return

    if not hasObjectStringType(message_json, debug):
        return
    if not message_json['object']['type'] == 'Block':
        if debug:
            print('DEBUG: not an undo block')
        return
    if not hasObjectStringObject(message_json, debug):
        return
    if debug:
        print('DEBUG: c2s undo block request arrived in outbox')

    messageId = removeIdEnding(message_json['object']['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s undo block object is not a status')
        return
    if not has_users_path(messageId):
        if debug:
            print('DEBUG: c2s undo block object has no nickname')
        return
    domain = removeDomainPort(domain)
    postFilename = locatePost(base_dir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo block post not found in inbox or outbox')
            print(messageId)
        return
    nicknameBlocked = getNicknameFromActor(message_json['object']['object'])
    if not nicknameBlocked:
        print('WARN: unable to find nickname in ' +
              message_json['object']['object'])
        return
    domainObject = message_json['object']['object']
    domainBlocked, portBlocked = getDomainFromActor(domainObject)
    domainBlockedFull = get_full_domain(domainBlocked, portBlocked)

    removeBlock(base_dir, nickname, domain,
                nicknameBlocked, domainBlockedFull)
    if debug:
        print('DEBUG: post undo blocked via c2s - ' + postFilename)


def mutePost(base_dir: str, nickname: str, domain: str, port: int,
             http_prefix: str, postId: str, recentPostsCache: {},
             debug: bool) -> None:
    """ Mutes the given post
    """
    print('mutePost: postId ' + postId)
    postFilename = locatePost(base_dir, nickname, domain, postId)
    if not postFilename:
        print('mutePost: file not found ' + postId)
        return
    post_json_object = loadJson(postFilename)
    if not post_json_object:
        print('mutePost: object not loaded ' + postId)
        return
    print('mutePost: ' + str(post_json_object))

    postJsonObj = post_json_object
    alsoUpdatePostId = None
    if has_object_dict(post_json_object):
        postJsonObj = post_json_object['object']
    else:
        if hasObjectString(post_json_object, debug):
            alsoUpdatePostId = removeIdEnding(post_json_object['object'])

    domain_full = get_full_domain(domain, port)
    actor = local_actor_url(http_prefix, nickname, domain_full)

    if postJsonObj.get('conversation'):
        muteConversation(base_dir, nickname, domain,
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
    if saveJson(post_json_object, postFilename):
        print('mutePost: saved ' + postFilename)

    # remove cached post so that the muted version gets recreated
    # without its content text and/or image
    cachedPostFilename = \
        getCachedPostFilename(base_dir, nickname, domain, post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
                print('MUTE: cached post removed ' + cachedPostFilename)
            except OSError:
                print('EX: MUTE cached post not removed ' +
                      cachedPostFilename)
                pass
        else:
            print('MUTE: cached post not found ' + cachedPostFilename)

    try:
        with open(postFilename + '.muted', 'w+') as muteFile:
            muteFile.write('\n')
    except OSError:
        print('EX: Failed to save mute file ' + postFilename + '.muted')
        return
    print('MUTE: ' + postFilename + '.muted file added')

    # if the post is in the recent posts cache then mark it as muted
    if recentPostsCache.get('index'):
        postId = \
            removeIdEnding(post_json_object['id']).replace('/', '#')
        if postId in recentPostsCache['index']:
            print('MUTE: ' + postId + ' is in recent posts cache')
        if recentPostsCache.get('json'):
            recentPostsCache['json'][postId] = json.dumps(post_json_object)
            print('MUTE: ' + postId +
                  ' marked as muted in recent posts memory cache')
        if recentPostsCache.get('html'):
            if recentPostsCache['html'].get(postId):
                del recentPostsCache['html'][postId]
                print('MUTE: ' + postId + ' removed cached html')

    if alsoUpdatePostId:
        postFilename = locatePost(base_dir, nickname, domain, alsoUpdatePostId)
        if os.path.isfile(postFilename):
            postJsonObj = loadJson(postFilename)
            cachedPostFilename = \
                getCachedPostFilename(base_dir, nickname, domain,
                                      postJsonObj)
            if cachedPostFilename:
                if os.path.isfile(cachedPostFilename):
                    try:
                        os.remove(cachedPostFilename)
                        print('MUTE: cached referenced post removed ' +
                              cachedPostFilename)
                    except OSError:
                        print('EX: ' +
                              'MUTE cached referenced post not removed ' +
                              cachedPostFilename)
                        pass

        if recentPostsCache.get('json'):
            if recentPostsCache['json'].get(alsoUpdatePostId):
                del recentPostsCache['json'][alsoUpdatePostId]
                print('MUTE: ' + alsoUpdatePostId + ' removed referenced json')
        if recentPostsCache.get('html'):
            if recentPostsCache['html'].get(alsoUpdatePostId):
                del recentPostsCache['html'][alsoUpdatePostId]
                print('MUTE: ' + alsoUpdatePostId + ' removed referenced html')


def unmutePost(base_dir: str, nickname: str, domain: str, port: int,
               http_prefix: str, postId: str, recentPostsCache: {},
               debug: bool) -> None:
    """ Unmutes the given post
    """
    postFilename = locatePost(base_dir, nickname, domain, postId)
    if not postFilename:
        return
    post_json_object = loadJson(postFilename)
    if not post_json_object:
        return

    muteFilename = postFilename + '.muted'
    if os.path.isfile(muteFilename):
        try:
            os.remove(muteFilename)
        except OSError:
            if debug:
                print('EX: unmutePost mute filename not deleted ' +
                      str(muteFilename))
        print('UNMUTE: ' + muteFilename + ' file removed')

    postJsonObj = post_json_object
    alsoUpdatePostId = None
    if has_object_dict(post_json_object):
        postJsonObj = post_json_object['object']
    else:
        if hasObjectString(post_json_object, debug):
            alsoUpdatePostId = removeIdEnding(post_json_object['object'])

    if postJsonObj.get('conversation'):
        unmuteConversation(base_dir, nickname, domain,
                           postJsonObj['conversation'])

    if postJsonObj.get('ignores'):
        domain_full = get_full_domain(domain, port)
        actor = local_actor_url(http_prefix, nickname, domain_full)
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
    saveJson(post_json_object, postFilename)

    # remove cached post so that the muted version gets recreated
    # with its content text and/or image
    cachedPostFilename = \
        getCachedPostFilename(base_dir, nickname, domain, post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                if debug:
                    print('EX: unmutePost cached post not deleted ' +
                          str(cachedPostFilename))

    # if the post is in the recent posts cache then mark it as unmuted
    if recentPostsCache.get('index'):
        postId = \
            removeIdEnding(post_json_object['id']).replace('/', '#')
        if postId in recentPostsCache['index']:
            print('UNMUTE: ' + postId + ' is in recent posts cache')
        if recentPostsCache.get('json'):
            recentPostsCache['json'][postId] = json.dumps(post_json_object)
            print('UNMUTE: ' + postId +
                  ' marked as unmuted in recent posts cache')
        if recentPostsCache.get('html'):
            if recentPostsCache['html'].get(postId):
                del recentPostsCache['html'][postId]
                print('UNMUTE: ' + postId + ' removed cached html')
    if alsoUpdatePostId:
        postFilename = locatePost(base_dir, nickname, domain, alsoUpdatePostId)
        if os.path.isfile(postFilename):
            postJsonObj = loadJson(postFilename)
            cachedPostFilename = \
                getCachedPostFilename(base_dir, nickname, domain,
                                      postJsonObj)
            if cachedPostFilename:
                if os.path.isfile(cachedPostFilename):
                    try:
                        os.remove(cachedPostFilename)
                        print('MUTE: cached referenced post removed ' +
                              cachedPostFilename)
                    except OSError:
                        if debug:
                            print('EX: ' +
                                  'unmutePost cached ref post not removed ' +
                                  str(cachedPostFilename))

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


def outboxMute(base_dir: str, http_prefix: str,
               nickname: str, domain: str, port: int,
               message_json: {}, debug: bool,
               recentPostsCache: {}) -> None:
    """When a mute is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if not hasActor(message_json, debug):
        return
    domain_full = get_full_domain(domain, port)
    if not message_json['actor'].endswith(domain_full + '/users/' + nickname):
        return
    if not message_json['type'] == 'Ignore':
        return
    if not hasObjectString(message_json, debug):
        return
    if debug:
        print('DEBUG: c2s mute request arrived in outbox')

    messageId = removeIdEnding(message_json['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s mute object is not a status')
        return
    if not has_users_path(messageId):
        if debug:
            print('DEBUG: c2s mute object has no nickname')
        return
    domain = removeDomainPort(domain)
    postFilename = locatePost(base_dir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s mute post not found in inbox or outbox')
            print(messageId)
        return
    nicknameMuted = getNicknameFromActor(message_json['object'])
    if not nicknameMuted:
        print('WARN: unable to find nickname in ' + message_json['object'])
        return

    mutePost(base_dir, nickname, domain, port,
             http_prefix, message_json['object'], recentPostsCache,
             debug)

    if debug:
        print('DEBUG: post muted via c2s - ' + postFilename)


def outboxUndoMute(base_dir: str, http_prefix: str,
                   nickname: str, domain: str, port: int,
                   message_json: {}, debug: bool,
                   recentPostsCache: {}) -> None:
    """When an undo mute is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if not hasActor(message_json, debug):
        return
    domain_full = get_full_domain(domain, port)
    if not message_json['actor'].endswith(domain_full + '/users/' + nickname):
        return
    if not message_json['type'] == 'Undo':
        return
    if not hasObjectStringType(message_json, debug):
        return
    if message_json['object']['type'] != 'Ignore':
        return
    if not isinstance(message_json['object']['object'], str):
        if debug:
            print('DEBUG: undo mute object is not a string')
        return
    if debug:
        print('DEBUG: c2s undo mute request arrived in outbox')

    messageId = removeIdEnding(message_json['object']['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s undo mute object is not a status')
        return
    if not has_users_path(messageId):
        if debug:
            print('DEBUG: c2s undo mute object has no nickname')
        return
    domain = removeDomainPort(domain)
    postFilename = locatePost(base_dir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo mute post not found in inbox or outbox')
            print(messageId)
        return
    nicknameMuted = getNicknameFromActor(message_json['object']['object'])
    if not nicknameMuted:
        print('WARN: unable to find nickname in ' +
              message_json['object']['object'])
        return

    unmutePost(base_dir, nickname, domain, port,
               http_prefix, message_json['object']['object'],
               recentPostsCache, debug)

    if debug:
        print('DEBUG: post undo mute via c2s - ' + postFilename)


def broch_modeIsActive(base_dir: str) -> bool:
    """Returns true if broch mode is active
    """
    allowFilename = base_dir + '/accounts/allowedinstances.txt'
    return os.path.isfile(allowFilename)


def setBrochMode(base_dir: str, domain_full: str, enabled: bool) -> None:
    """Broch mode can be used to lock down the instance during
    a period of time when it is temporarily under attack.
    For example, where an adversary is constantly spinning up new
    instances.
    It surveys the following lists of all accounts and uses that
    to construct an instance level allow list. Anything arriving
    which is then not from one of the allowed domains will be dropped
    """
    allowFilename = base_dir + '/accounts/allowedinstances.txt'

    if not enabled:
        # remove instance allow list
        if os.path.isfile(allowFilename):
            try:
                os.remove(allowFilename)
            except OSError:
                print('EX: setBrochMode allow file not deleted ' +
                      str(allowFilename))
            print('Broch mode turned off')
    else:
        if os.path.isfile(allowFilename):
            lastModified = fileLastModified(allowFilename)
            print('Broch mode already activated ' + lastModified)
            return
        # generate instance allow list
        allowedDomains = [domain_full]
        follow_files = ('following.txt', 'followers.txt')
        for subdir, dirs, files in os.walk(base_dir + '/accounts'):
            for acct in dirs:
                if not isAccountDir(acct):
                    continue
                accountDir = os.path.join(base_dir + '/accounts', acct)
                for followFileType in follow_files:
                    followingFilename = accountDir + '/' + followFileType
                    if not os.path.isfile(followingFilename):
                        continue
                    try:
                        with open(followingFilename, 'r') as f:
                            followList = f.readlines()
                            for handle in followList:
                                if '@' not in handle:
                                    continue
                                handle = handle.replace('\n', '')
                                handleDomain = handle.split('@')[1]
                                if handleDomain not in allowedDomains:
                                    allowedDomains.append(handleDomain)
                    except OSError as ex:
                        print('EX: failed to read ' + followingFilename +
                              ' ' + str(ex))
            break

        # write the allow file
        try:
            with open(allowFilename, 'w+') as allowFile:
                allowFile.write(domain_full + '\n')
                for d in allowedDomains:
                    allowFile.write(d + '\n')
                print('Broch mode enabled')
        except OSError as ex:
            print('EX: Broch mode not enabled due to file write ' + str(ex))
            return

    setConfigParam(base_dir, "broch_mode", enabled)


def broch_modeLapses(base_dir: str, lapseDays: int) -> bool:
    """After broch mode is enabled it automatically
    elapses after a period of time
    """
    allowFilename = base_dir + '/accounts/allowedinstances.txt'
    if not os.path.isfile(allowFilename):
        return False
    lastModified = fileLastModified(allowFilename)
    modifiedDate = None
    try:
        modifiedDate = \
            datetime.strptime(lastModified, "%Y-%m-%dT%H:%M:%SZ")
    except BaseException:
        print('EX: broch_modeLapses date not parsed ' + str(lastModified))
        return False
    if not modifiedDate:
        return False
    curr_time = datetime.datetime.utcnow()
    daysSinceBroch = (curr_time - modifiedDate).days
    if daysSinceBroch >= lapseDays:
        removed = False
        try:
            os.remove(allowFilename)
            removed = True
        except OSError:
            print('EX: broch_modeLapses allow file not deleted ' +
                  str(allowFilename))
        if removed:
            setConfigParam(base_dir, "broch_mode", False)
            print('Broch mode has elapsed')
            return True
    return False


def loadCWLists(base_dir: str, verbose: bool) -> {}:
    """Load lists used for content warnings
    """
    if not os.path.isdir(base_dir + '/cwlists'):
        return {}
    result = {}
    for subdir, dirs, files in os.walk(base_dir + '/cwlists'):
        for f in files:
            if not f.endswith('.json'):
                continue
            listFilename = os.path.join(base_dir + '/cwlists', f)
            print('listFilename: ' + listFilename)
            listJson = loadJson(listFilename, 0, 1)
            if not listJson:
                continue
            if not listJson.get('name'):
                continue
            if not listJson.get('words') and not listJson.get('domains'):
                continue
            name = listJson['name']
            if verbose:
                print('List: ' + name)
            result[name] = listJson
    return result


def addCWfromLists(post_json_object: {}, cw_lists: {}, translate: {},
                   lists_enabled: str) -> None:
    """Adds content warnings by matching the post content
    against domains or keywords
    """
    if not lists_enabled:
        return
    if not post_json_object['object'].get('content'):
        return
    cw = ''
    if post_json_object['object'].get('summary'):
        cw = post_json_object['object']['summary']

    content = post_json_object['object']['content']
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
        if warning in cw:
            continue

        matched = False

        # match domains within the content
        if item.get('domains'):
            for domain in item['domains']:
                if domain in content:
                    if cw:
                        cw = warning + ' / ' + cw
                    else:
                        cw = warning
                    matched = True
                    break

        if matched:
            continue

        # match words within the content
        if item.get('words'):
            for wordStr in item['words']:
                if wordStr in content:
                    if cw:
                        cw = warning + ' / ' + cw
                    else:
                        cw = warning
                    break
    if cw:
        post_json_object['object']['summary'] = cw
        post_json_object['object']['sensitive'] = True


def getCWlistVariable(listName: str) -> str:
    """Returns the variable associated with a CW list
    """
    return 'list' + listName.replace(' ', '').replace("'", '')
