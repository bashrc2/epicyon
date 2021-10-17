__filename__ = "like.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from pprint import pprint
from utils import hasObjectString
from utils import hasObjectStringObject
from utils import hasObjectStringType
from utils import removeDomainPort
from utils import hasObjectDict
from utils import hasUsersPath
from utils import getFullDomain
from utils import removeIdEnding
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import undoLikesCollectionEntry
from utils import hasGroupType
from utils import localActorUrl
from utils import loadJson
from utils import saveJson
from utils import removePostFromCache
from utils import getCachedPostFilename
from posts import sendSignedJson
from session import postJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox


def likedByPerson(postJsonObject: {}, nickname: str, domain: str) -> bool:
    """Returns True if the given post is liked by the given person
    """
    if noOfLikes(postJsonObject) == 0:
        return False
    actorMatch = domain + '/users/' + nickname

    obj = postJsonObject
    if hasObjectDict(postJsonObject):
        obj = postJsonObject['object']

    for item in obj['likes']['items']:
        if item['actor'].endswith(actorMatch):
            return True
    return False


def noOfLikes(postJsonObject: {}) -> int:
    """Returns the number of likes ona  given post
    """
    obj = postJsonObject
    if hasObjectDict(postJsonObject):
        obj = postJsonObject['object']
    if not obj.get('likes'):
        return 0
    if not isinstance(obj['likes'], dict):
        return 0
    if not obj['likes'].get('items'):
        obj['likes']['items'] = []
        obj['likes']['totalItems'] = 0
    return len(obj['likes']['items'])


def _like(recentPostsCache: {},
          session, baseDir: str, federationList: [],
          nickname: str, domain: str, port: int,
          ccList: [], httpPrefix: str,
          objectUrl: str, actorLiked: str,
          clientToServer: bool,
          sendThreads: [], postLog: [],
          personCache: {}, cachedWebfingers: {},
          debug: bool, projectVersion: str,
          signingPrivateKeyPem: str) -> {}:
    """Creates a like
    actor is the person doing the liking
    'to' might be a specific person (actor) whose post was liked
    object is typically the url of the message which was liked
    """
    if not urlPermitted(objectUrl, federationList):
        return None

    fullDomain = getFullDomain(domain, port)

    newLikeJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Like',
        'actor': localActorUrl(httpPrefix, nickname, fullDomain),
        'object': objectUrl
    }
    if ccList:
        if len(ccList) > 0:
            newLikeJson['cc'] = ccList

    # Extract the domain and nickname from a statuses link
    likedPostNickname = None
    likedPostDomain = None
    likedPostPort = None
    groupAccount = False
    if actorLiked:
        likedPostNickname = getNicknameFromActor(actorLiked)
        likedPostDomain, likedPostPort = getDomainFromActor(actorLiked)
        groupAccount = hasGroupType(baseDir, actorLiked, personCache)
    else:
        if hasUsersPath(objectUrl):
            likedPostNickname = getNicknameFromActor(objectUrl)
            likedPostDomain, likedPostPort = getDomainFromActor(objectUrl)
            if '/' + str(likedPostNickname) + '/' in objectUrl:
                actorLiked = \
                    objectUrl.split('/' + likedPostNickname + '/')[0] + \
                    '/' + likedPostNickname
                groupAccount = hasGroupType(baseDir, actorLiked, personCache)

    if likedPostNickname:
        postFilename = locatePost(baseDir, nickname, domain, objectUrl)
        if not postFilename:
            print('DEBUG: like baseDir: ' + baseDir)
            print('DEBUG: like nickname: ' + nickname)
            print('DEBUG: like domain: ' + domain)
            print('DEBUG: like objectUrl: ' + objectUrl)
            return None

        updateLikesCollection(recentPostsCache,
                              baseDir, postFilename, objectUrl,
                              newLikeJson['actor'],
                              nickname, domain, debug, None)

        sendSignedJson(newLikeJson, session, baseDir,
                       nickname, domain, port,
                       likedPostNickname, likedPostDomain, likedPostPort,
                       'https://www.w3.org/ns/activitystreams#Public',
                       httpPrefix, True, clientToServer, federationList,
                       sendThreads, postLog, cachedWebfingers, personCache,
                       debug, projectVersion, None, groupAccount,
                       signingPrivateKeyPem, 7367374)

    return newLikeJson


def likePost(recentPostsCache: {},
             session, baseDir: str, federationList: [],
             nickname: str, domain: str, port: int, httpPrefix: str,
             likeNickname: str, likeDomain: str, likePort: int,
             ccList: [],
             likeStatusNumber: int, clientToServer: bool,
             sendThreads: [], postLog: [],
             personCache: {}, cachedWebfingers: {},
             debug: bool, projectVersion: str,
             signingPrivateKeyPem: str) -> {}:
    """Likes a given status post. This is only used by unit tests
    """
    likeDomain = getFullDomain(likeDomain, likePort)

    actorLiked = localActorUrl(httpPrefix, likeNickname, likeDomain)
    objectUrl = actorLiked + '/statuses/' + str(likeStatusNumber)

    return _like(recentPostsCache,
                 session, baseDir, federationList, nickname, domain, port,
                 ccList, httpPrefix, objectUrl, actorLiked, clientToServer,
                 sendThreads, postLog, personCache, cachedWebfingers,
                 debug, projectVersion, signingPrivateKeyPem)


def sendLikeViaServer(baseDir: str, session,
                      fromNickname: str, password: str,
                      fromDomain: str, fromPort: int,
                      httpPrefix: str, likeUrl: str,
                      cachedWebfingers: {}, personCache: {},
                      debug: bool, projectVersion: str,
                      signingPrivateKeyPem: str) -> {}:
    """Creates a like via c2s
    """
    if not session:
        print('WARN: No session for sendLikeViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    actor = localActorUrl(httpPrefix, fromNickname, fromDomainFull)

    newLikeJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Like',
        'actor': actor,
        'object': likeUrl
    }

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, httpPrefix,
                                cachedWebfingers,
                                fromDomain, projectVersion, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: like webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: like webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    baseDir, session, wfRequest,
                                    personCache,
                                    projectVersion, httpPrefix,
                                    fromNickname, fromDomain,
                                    postToBox, 72873)

    if not inboxUrl:
        if debug:
            print('DEBUG: like no ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: like no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(httpPrefix, fromDomainFull,
                          session, newLikeJson, [], inboxUrl,
                          headers, 3, True)
    if not postResult:
        if debug:
            print('WARN: POST like failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST like success')

    return newLikeJson


def sendUndoLikeViaServer(baseDir: str, session,
                          fromNickname: str, password: str,
                          fromDomain: str, fromPort: int,
                          httpPrefix: str, likeUrl: str,
                          cachedWebfingers: {}, personCache: {},
                          debug: bool, projectVersion: str,
                          signingPrivateKeyPem: str) -> {}:
    """Undo a like via c2s
    """
    if not session:
        print('WARN: No session for sendUndoLikeViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    actor = localActorUrl(httpPrefix, fromNickname, fromDomainFull)

    newUndoLikeJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': actor,
        'object': {
            'type': 'Like',
            'actor': actor,
            'object': likeUrl
        }
    }

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, httpPrefix,
                                cachedWebfingers,
                                fromDomain, projectVersion, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: unlike webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        if debug:
            print('WARN: unlike webfinger for ' + handle +
                  ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    baseDir, session, wfRequest,
                                    personCache, projectVersion,
                                    httpPrefix, fromNickname,
                                    fromDomain, postToBox,
                                    72625)

    if not inboxUrl:
        if debug:
            print('DEBUG: unlike no ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: unlike no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(httpPrefix, fromDomainFull,
                          session, newUndoLikeJson, [], inboxUrl,
                          headers, 3, True)
    if not postResult:
        if debug:
            print('WARN: POST unlike failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST unlike success')

    return newUndoLikeJson


def outboxLike(recentPostsCache: {},
               baseDir: str, httpPrefix: str,
               nickname: str, domain: str, port: int,
               messageJson: {}, debug: bool) -> None:
    """ When a like request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: like - no type')
        return
    if not messageJson['type'] == 'Like':
        if debug:
            print('DEBUG: not a like')
        return
    if not hasObjectString(messageJson, debug):
        return
    if debug:
        print('DEBUG: c2s like request arrived in outbox')

    messageId = removeIdEnding(messageJson['object'])
    domain = removeDomainPort(domain)
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s like post not found in inbox or outbox')
            print(messageId)
        return True
    updateLikesCollection(recentPostsCache,
                          baseDir, postFilename, messageId,
                          messageJson['actor'],
                          nickname, domain, debug, None)
    if debug:
        print('DEBUG: post liked via c2s - ' + postFilename)


def outboxUndoLike(recentPostsCache: {},
                   baseDir: str, httpPrefix: str,
                   nickname: str, domain: str, port: int,
                   messageJson: {}, debug: bool) -> None:
    """ When an undo like request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        return
    if not messageJson['type'] == 'Undo':
        return
    if not hasObjectStringType(messageJson, debug):
        return
    if not messageJson['object']['type'] == 'Like':
        if debug:
            print('DEBUG: not a undo like')
        return
    if not hasObjectStringObject(messageJson, debug):
        return
    if debug:
        print('DEBUG: c2s undo like request arrived in outbox')

    messageId = removeIdEnding(messageJson['object']['object'])
    domain = removeDomainPort(domain)
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo like post not found in inbox or outbox')
            print(messageId)
        return True
    undoLikesCollectionEntry(recentPostsCache, baseDir, postFilename,
                             messageId, messageJson['actor'],
                             domain, debug, None)
    if debug:
        print('DEBUG: post undo liked via c2s - ' + postFilename)


def updateLikesCollection(recentPostsCache: {},
                          baseDir: str, postFilename: str,
                          objectUrl: str, actor: str,
                          nickname: str, domain: str, debug: bool,
                          postJsonObject: {}) -> None:
    """Updates the likes collection within a post
    """
    if not postJsonObject:
        postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return

    # remove any cached version of this post so that the
    # like icon is changed
    removePostFromCache(postJsonObject, recentPostsCache)
    cachedPostFilename = getCachedPostFilename(baseDir, nickname,
                                               domain, postJsonObject)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except BaseException:
                pass

    obj = postJsonObject
    if hasObjectDict(postJsonObject):
        obj = postJsonObject['object']

    if not objectUrl.endswith('/likes'):
        objectUrl = objectUrl + '/likes'
    if not obj.get('likes'):
        if debug:
            print('DEBUG: Adding initial like to ' + objectUrl)
        likesJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'id': objectUrl,
            'type': 'Collection',
            "totalItems": 1,
            'items': [{
                'type': 'Like',
                'actor': actor
            }]
        }
        obj['likes'] = likesJson
    else:
        if not obj['likes'].get('items'):
            obj['likes']['items'] = []
        for likeItem in obj['likes']['items']:
            if likeItem.get('actor'):
                if likeItem['actor'] == actor:
                    # already liked
                    return
        newLike = {
            'type': 'Like',
            'actor': actor
        }
        obj['likes']['items'].append(newLike)
        itlen = len(obj['likes']['items'])
        obj['likes']['totalItems'] = itlen

    if debug:
        print('DEBUG: saving post with likes added')
        pprint(postJsonObject)
    saveJson(postJsonObject, postFilename)
