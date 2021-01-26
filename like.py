__filename__ = "like.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from utils import hasUsersPath
from utils import getFullDomain
from utils import removeIdEnding
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import updateLikesCollection
from utils import undoLikesCollectionEntry
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
    for item in postJsonObject['object']['likes']['items']:
        if item['actor'].endswith(actorMatch):
            return True
    return False


def noOfLikes(postJsonObject: {}) -> int:
    """Returns the number of likes ona  given post
    """
    if not postJsonObject.get('object'):
        return 0
    if not isinstance(postJsonObject['object'], dict):
        return 0
    if not postJsonObject['object'].get('likes'):
        return 0
    if not isinstance(postJsonObject['object']['likes'], dict):
        return 0
    if not postJsonObject['object']['likes'].get('items'):
        postJsonObject['object']['likes']['items'] = []
        postJsonObject['object']['likes']['totalItems'] = 0
    return len(postJsonObject['object']['likes']['items'])


def _like(recentPostsCache: {},
          session, baseDir: str, federationList: [],
          nickname: str, domain: str, port: int,
          ccList: [], httpPrefix: str,
          objectUrl: str, actorLiked: str,
          clientToServer: bool,
          sendThreads: [], postLog: [],
          personCache: {}, cachedWebfingers: {},
          debug: bool, projectVersion: str) -> {}:
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
        'actor': httpPrefix + '://' + fullDomain + '/users/' + nickname,
        'object': objectUrl
    }
    if ccList:
        if len(ccList) > 0:
            newLikeJson['cc'] = ccList

    # Extract the domain and nickname from a statuses link
    likedPostNickname = None
    likedPostDomain = None
    likedPostPort = None
    if actorLiked:
        likedPostNickname = getNicknameFromActor(actorLiked)
        likedPostDomain, likedPostPort = getDomainFromActor(actorLiked)
    else:
        if hasUsersPath(objectUrl):
            likedPostNickname = getNicknameFromActor(objectUrl)
            likedPostDomain, likedPostPort = getDomainFromActor(objectUrl)

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
                              newLikeJson['actor'], domain, debug)

        sendSignedJson(newLikeJson, session, baseDir,
                       nickname, domain, port,
                       likedPostNickname, likedPostDomain, likedPostPort,
                       'https://www.w3.org/ns/activitystreams#Public',
                       httpPrefix, True, clientToServer, federationList,
                       sendThreads, postLog, cachedWebfingers, personCache,
                       debug, projectVersion)

    return newLikeJson


def likePost(recentPostsCache: {},
             session, baseDir: str, federationList: [],
             nickname: str, domain: str, port: int, httpPrefix: str,
             likeNickname: str, likeDomain: str, likePort: int,
             ccList: [],
             likeStatusNumber: int, clientToServer: bool,
             sendThreads: [], postLog: [],
             personCache: {}, cachedWebfingers: {},
             debug: bool, projectVersion: str) -> {}:
    """Likes a given status post. This is only used by unit tests
    """
    likeDomain = getFullDomain(likeDomain, likePort)

    actorLiked = httpPrefix + '://' + likeDomain + '/users/' + likeNickname
    objectUrl = actorLiked + '/statuses/' + str(likeStatusNumber)

    return _like(recentPostsCache,
                 session, baseDir, federationList, nickname, domain, port,
                 ccList, httpPrefix, objectUrl, actorLiked, clientToServer,
                 sendThreads, postLog, personCache, cachedWebfingers,
                 debug, projectVersion)


def sendLikeViaServer(baseDir: str, session,
                      fromNickname: str, password: str,
                      fromDomain: str, fromPort: int,
                      httpPrefix: str, likeUrl: str,
                      cachedWebfingers: {}, personCache: {},
                      debug: bool, projectVersion: str) -> {}:
    """Creates a like via c2s
    """
    if not session:
        print('WARN: No session for sendLikeViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    actor = httpPrefix + '://' + fromDomainFull + '/users/' + fromNickname

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
                                fromDomain, projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache,
                                            projectVersion, httpPrefix,
                                            fromNickname, fromDomain,
                                            postToBox, 72873)

    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(session, newLikeJson, [], inboxUrl, headers)
    if not postResult:
        print('WARN: POST announce failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST like success')

    return newLikeJson


def sendUndoLikeViaServer(baseDir: str, session,
                          fromNickname: str, password: str,
                          fromDomain: str, fromPort: int,
                          httpPrefix: str, likeUrl: str,
                          cachedWebfingers: {}, personCache: {},
                          debug: bool, projectVersion: str) -> {}:
    """Undo a like via c2s
    """
    if not session:
        print('WARN: No session for sendUndoLikeViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    actor = httpPrefix + '://' + fromDomainFull + '/users/' + fromNickname

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
                                fromDomain, projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache, projectVersion,
                                            httpPrefix, fromNickname,
                                            fromDomain, postToBox,
                                            72625)

    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(session, newUndoLikeJson, [], inboxUrl, headers)
    if not postResult:
        print('WARN: POST announce failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST undo like success')

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
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in like')
        return
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: like object is not string')
        return
    if debug:
        print('DEBUG: c2s like request arrived in outbox')

    messageId = removeIdEnding(messageJson['object'])
    if ':' in domain:
        domain = domain.split(':')[0]
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s like post not found in inbox or outbox')
            print(messageId)
        return True
    updateLikesCollection(recentPostsCache,
                          baseDir, postFilename, messageId,
                          messageJson['actor'], domain, debug)
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
    if not messageJson.get('object'):
        return
    if not isinstance(messageJson['object'], dict):
        if debug:
            print('DEBUG: undo like object is not dict')
        return
    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: undo like - no type')
        return
    if not messageJson['object']['type'] == 'Like':
        if debug:
            print('DEBUG: not a undo like')
        return
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: no object in undo like')
        return
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: undo like object is not string')
        return
    if debug:
        print('DEBUG: c2s undo like request arrived in outbox')

    messageId = removeIdEnding(messageJson['object']['object'])
    if ':' in domain:
        domain = domain.split(':')[0]
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo like post not found in inbox or outbox')
            print(messageId)
        return True
    undoLikesCollectionEntry(recentPostsCache, baseDir, postFilename,
                             messageId, messageJson['actor'],
                             domain, debug)
    if debug:
        print('DEBUG: post undo liked via c2s - ' + postFilename)
