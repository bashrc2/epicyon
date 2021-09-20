__filename__ = "announce.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

from utils import hasGroupType
from utils import removeDomainPort
from utils import hasObjectDict
from utils import removeIdEnding
from utils import hasUsersPath
from utils import getFullDomain
from utils import getStatusNumber
from utils import createOutboxDir
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import saveJson
from utils import undoAnnounceCollectionEntry
from utils import updateAnnounceCollection
from utils import localActorUrl
from utils import replaceUsersWithAt
from posts import sendSignedJson
from posts import getPersonBox
from session import postJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader


def isSelfAnnounce(postJsonObject: {}) -> bool:
    """Is the given post a self announce?
    """
    if not postJsonObject.get('actor'):
        return False
    if not postJsonObject.get('type'):
        return False
    if postJsonObject['type'] != 'Announce':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['actor'], str):
        return False
    if not isinstance(postJsonObject['object'], str):
        return False
    return postJsonObject['actor'] in postJsonObject['object']


def outboxAnnounce(recentPostsCache: {},
                   baseDir: str, messageJson: {}, debug: bool) -> bool:
    """ Adds or removes announce entries from the shares collection
    within a given post
    """
    if not messageJson.get('actor'):
        return False
    if not isinstance(messageJson['actor'], str):
        return False
    if not messageJson.get('type'):
        return False
    if not messageJson.get('object'):
        return False
    if messageJson['type'] == 'Announce':
        if not isinstance(messageJson['object'], str):
            return False
        if isSelfAnnounce(messageJson):
            return False
        nickname = getNicknameFromActor(messageJson['actor'])
        if not nickname:
            print('WARN: no nickname found in ' + messageJson['actor'])
            return False
        domain, port = getDomainFromActor(messageJson['actor'])
        postFilename = locatePost(baseDir, nickname, domain,
                                  messageJson['object'])
        if postFilename:
            updateAnnounceCollection(recentPostsCache, baseDir, postFilename,
                                     messageJson['actor'],
                                     nickname, domain, debug)
            return True
    elif messageJson['type'] == 'Undo':
        if not hasObjectDict(messageJson):
            return False
        if not messageJson['object'].get('type'):
            return False
        if messageJson['object']['type'] == 'Announce':
            if not isinstance(messageJson['object']['object'], str):
                return False
            nickname = getNicknameFromActor(messageJson['actor'])
            if not nickname:
                print('WARN: no nickname found in ' + messageJson['actor'])
                return False
            domain, port = getDomainFromActor(messageJson['actor'])
            postFilename = locatePost(baseDir, nickname, domain,
                                      messageJson['object']['object'])
            if postFilename:
                undoAnnounceCollectionEntry(recentPostsCache,
                                            baseDir, postFilename,
                                            messageJson['actor'],
                                            domain, debug)
                return True
    return False


def announcedByPerson(isAnnounced: bool, postActor: str,
                      nickname: str, domainFull: str) -> bool:
    """Returns True if the given post is announced by the given person
    """
    if not postActor:
        return False
    if isAnnounced and \
       postActor.endswith(domainFull + '/users/' + nickname):
        return True
    return False


def createAnnounce(session, baseDir: str, federationList: [],
                   nickname: str, domain: str, port: int,
                   toUrl: str, ccUrl: str, httpPrefix: str,
                   objectUrl: str, saveToFile: bool,
                   clientToServer: bool,
                   sendThreads: [], postLog: [],
                   personCache: {}, cachedWebfingers: {},
                   debug: bool, projectVersion: str,
                   signingPrivateKeyPem: str) -> {}:
    """Creates an announce message
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and the
    followers url objectUrl is typically the url of the message,
    corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl, federationList):
        return None

    domain = removeDomainPort(domain)
    fullDomain = getFullDomain(domain, port)

    statusNumber, published = getStatusNumber()
    newAnnounceId = httpPrefix + '://' + fullDomain + \
        '/users/' + nickname + '/statuses/' + statusNumber
    atomUriStr = localActorUrl(httpPrefix, nickname, fullDomain) + \
        '/statuses/' + statusNumber
    newAnnounce = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': localActorUrl(httpPrefix, nickname, fullDomain),
        'atomUri': atomUriStr,
        'cc': [],
        'id': newAnnounceId + '/activity',
        'object': objectUrl,
        'published': published,
        'to': [toUrl],
        'type': 'Announce'
    }
    if ccUrl:
        if len(ccUrl) > 0:
            newAnnounce['cc'] = [ccUrl]
    if saveToFile:
        outboxDir = createOutboxDir(nickname, domain, baseDir)
        filename = outboxDir + '/' + newAnnounceId.replace('/', '#') + '.json'
        saveJson(newAnnounce, filename)

    announceNickname = None
    announceDomain = None
    announcePort = None
    groupAccount = False
    if hasUsersPath(objectUrl):
        announceNickname = getNicknameFromActor(objectUrl)
        announceDomain, announcePort = getDomainFromActor(objectUrl)
        if '/' + str(announceNickname) + '/' in objectUrl:
            announceActor = \
                objectUrl.split('/' + announceNickname + '/')[0] + \
                '/' + announceNickname
            if hasGroupType(baseDir, announceActor, personCache):
                groupAccount = True

    if announceNickname and announceDomain:
        sendSignedJson(newAnnounce, session, baseDir,
                       nickname, domain, port,
                       announceNickname, announceDomain, announcePort, None,
                       httpPrefix, True, clientToServer, federationList,
                       sendThreads, postLog, cachedWebfingers, personCache,
                       debug, projectVersion, None, groupAccount,
                       signingPrivateKeyPem, 639633)

    return newAnnounce


def announcePublic(session, baseDir: str, federationList: [],
                   nickname: str, domain: str, port: int, httpPrefix: str,
                   objectUrl: str, clientToServer: bool,
                   sendThreads: [], postLog: [],
                   personCache: {}, cachedWebfingers: {},
                   debug: bool, projectVersion: str,
                   signingPrivateKeyPem: str) -> {}:
    """Makes a public announcement
    """
    fromDomain = getFullDomain(domain, port)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = localActorUrl(httpPrefix, nickname, fromDomain) + '/followers'
    return createAnnounce(session, baseDir, federationList,
                          nickname, domain, port,
                          toUrl, ccUrl, httpPrefix,
                          objectUrl, True, clientToServer,
                          sendThreads, postLog,
                          personCache, cachedWebfingers,
                          debug, projectVersion,
                          signingPrivateKeyPem)


def sendAnnounceViaServer(baseDir: str, session,
                          fromNickname: str, password: str,
                          fromDomain: str, fromPort: int,
                          httpPrefix: str, repeatObjectUrl: str,
                          cachedWebfingers: {}, personCache: {},
                          debug: bool, projectVersion: str,
                          signingPrivateKeyPem: str) -> {}:
    """Creates an announce message via c2s
    """
    if not session:
        print('WARN: No session for sendAnnounceViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    actorStr = localActorUrl(httpPrefix, fromNickname, fromDomainFull)
    ccUrl = actorStr + '/followers'

    statusNumber, published = getStatusNumber()
    newAnnounceId = actorStr + '/statuses/' + statusNumber
    newAnnounceJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': actorStr,
        'atomUri': newAnnounceId,
        'cc': [ccUrl],
        'id': newAnnounceId + '/activity',
        'object': repeatObjectUrl,
        'published': published,
        'to': [toUrl],
        'type': 'Announce'
    }

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, httpPrefix,
                                cachedWebfingers,
                                fromDomain, projectVersion, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: announce webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId,
     sharedInbox, avatarUrl,
     displayName) = getPersonBox(signingPrivateKeyPem,
                                 originDomain,
                                 baseDir, session, wfRequest,
                                 personCache,
                                 projectVersion, httpPrefix,
                                 fromNickname, fromDomain,
                                 postToBox, 73528)

    if not inboxUrl:
        if debug:
            print('DEBUG: announce no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: announce no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(httpPrefix, fromDomainFull,
                          session, newAnnounceJson, [], inboxUrl,
                          headers, 3, True)
    if not postResult:
        print('WARN: announce not posted')

    if debug:
        print('DEBUG: c2s POST announce success')

    return newAnnounceJson


def sendUndoAnnounceViaServer(baseDir: str, session,
                              undoPostJsonObject: {},
                              nickname: str, password: str,
                              domain: str, port: int,
                              httpPrefix: str, repeatObjectUrl: str,
                              cachedWebfingers: {}, personCache: {},
                              debug: bool, projectVersion: str,
                              signingPrivateKeyPem: str) -> {}:
    """Undo an announce message via c2s
    """
    if not session:
        print('WARN: No session for sendUndoAnnounceViaServer')
        return 6

    domainFull = getFullDomain(domain, port)

    actor = localActorUrl(httpPrefix, nickname, domainFull)
    handle = replaceUsersWithAt(actor)

    statusNumber, published = getStatusNumber()
    unAnnounceJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': actor + '/statuses/' + str(statusNumber) + '/undo',
        'type': 'Undo',
        'actor': actor,
        'object': undoPostJsonObject['object']
    }

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, httpPrefix,
                                cachedWebfingers,
                                domain, projectVersion, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: undo announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: undo announce webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = domain
    (inboxUrl, pubKeyId, pubKey, fromPersonId,
     sharedInbox, avatarUrl,
     displayName) = getPersonBox(signingPrivateKeyPem,
                                 originDomain,
                                 baseDir, session, wfRequest,
                                 personCache,
                                 projectVersion, httpPrefix,
                                 nickname, domain,
                                 postToBox, 73528)

    if not inboxUrl:
        if debug:
            print('DEBUG: undo announce no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: undo announce no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(httpPrefix, domainFull,
                          session, unAnnounceJson, [], inboxUrl,
                          headers, 3, True)
    if not postResult:
        print('WARN: undo announce not posted')

    if debug:
        print('DEBUG: c2s POST undo announce success')

    return unAnnounceJson


def outboxUndoAnnounce(recentPostsCache: {},
                       baseDir: str, httpPrefix: str,
                       nickname: str, domain: str, port: int,
                       messageJson: {}, debug: bool) -> None:
    """ When an undo announce is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        return
    if not messageJson['type'] == 'Undo':
        return
    if not hasObjectDict(messageJson):
        if debug:
            print('DEBUG: undo like object is not dict')
        return
    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: undo like - no type')
        return
    if not messageJson['object']['type'] == 'Announce':
        if debug:
            print('DEBUG: not a undo announce')
        return
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: no object in undo announce')
        return
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: undo announce object is not string')
        return
    if debug:
        print('DEBUG: c2s undo announce request arrived in outbox')

    messageId = removeIdEnding(messageJson['object']['object'])
    domain = removeDomainPort(domain)
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo announce post not found in inbox or outbox')
            print(messageId)
        return True
    undoAnnounceCollectionEntry(recentPostsCache, baseDir, postFilename,
                                messageJson['actor'], domain, debug)
    if debug:
        print('DEBUG: post undo announce via c2s - ' + postFilename)
