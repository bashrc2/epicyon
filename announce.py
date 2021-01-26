__filename__ = "announce.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

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
from posts import sendSignedJson
from posts import getPersonBox
from session import postJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader


def outboxAnnounce(recentPostsCache: {},
                   baseDir: str, messageJson: {}, debug: bool) -> bool:
    """ Adds or removes announce entries from the shares collection
    within a given post
    """
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('type'):
        return False
    if not messageJson.get('object'):
        return False
    if messageJson['type'] == 'Announce':
        if not isinstance(messageJson['object'], str):
            return False
        nickname = getNicknameFromActor(messageJson['actor'])
        if not nickname:
            print('WARN: no nickname found in '+messageJson['actor'])
            return False
        domain, port = getDomainFromActor(messageJson['actor'])
        postFilename = locatePost(baseDir, nickname, domain,
                                  messageJson['object'])
        if postFilename:
            updateAnnounceCollection(recentPostsCache, baseDir, postFilename,
                                     messageJson['actor'], domain, debug)
            return True
    if messageJson['type'] == 'Undo':
        if not isinstance(messageJson['object'], dict):
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


def announcedByPerson(postJsonObject: {}, nickname: str, domain: str) -> bool:
    """Returns True if the given post is announced by the given person
    """
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    # not to be confused with shared items
    if not postJsonObject['object'].get('shares'):
        return False
    if not isinstance(postJsonObject['object']['shares'], dict):
        return False
    if not postJsonObject['object']['shares'].get('items'):
        return False
    if not isinstance(postJsonObject['object']['shares']['items'], list):
        return False
    actorMatch = domain + '/users/' + nickname
    for item in postJsonObject['object']['shares']['items']:
        if item['actor'].endswith(actorMatch):
            return True
    return False


def createAnnounce(session, baseDir: str, federationList: [],
                   nickname: str, domain: str, port: int,
                   toUrl: str, ccUrl: str, httpPrefix: str,
                   objectUrl: str, saveToFile: bool,
                   clientToServer: bool,
                   sendThreads: [], postLog: [],
                   personCache: {}, cachedWebfingers: {},
                   debug: bool, projectVersion: str) -> {}:
    """Creates an announce message
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and the
    followers url objectUrl is typically the url of the message,
    corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl, federationList):
        return None

    if ':' in domain:
        domain = domain.split(':')[0]
    fullDomain = getFullDomain(domain, port)

    statusNumber, published = getStatusNumber()
    newAnnounceId = httpPrefix + '://' + fullDomain + \
        '/users/' + nickname + '/statuses/' + statusNumber
    atomUriStr = httpPrefix + '://' + fullDomain + '/users/' + nickname + \
        '/statuses/' + statusNumber
    newAnnounce = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
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
    if hasUsersPath(objectUrl):
        announceNickname = getNicknameFromActor(objectUrl)
        announceDomain, announcePort = getDomainFromActor(objectUrl)

    if announceNickname and announceDomain:
        sendSignedJson(newAnnounce, session, baseDir,
                       nickname, domain, port,
                       announceNickname, announceDomain, announcePort, None,
                       httpPrefix, True, clientToServer, federationList,
                       sendThreads, postLog, cachedWebfingers, personCache,
                       debug, projectVersion)

    return newAnnounce


def announcePublic(session, baseDir: str, federationList: [],
                   nickname: str, domain: str, port: int, httpPrefix: str,
                   objectUrl: str, clientToServer: bool,
                   sendThreads: [], postLog: [],
                   personCache: {}, cachedWebfingers: {},
                   debug: bool, projectVersion: str) -> {}:
    """Makes a public announcement
    """
    fromDomain = getFullDomain(domain, port)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://' + fromDomain + '/users/' + nickname + \
        '/followers'
    return createAnnounce(session, baseDir, federationList,
                          nickname, domain, port,
                          toUrl, ccUrl, httpPrefix,
                          objectUrl, True, clientToServer,
                          sendThreads, postLog,
                          personCache, cachedWebfingers,
                          debug, projectVersion)


def sendAnnounceViaServer(baseDir: str, session,
                          fromNickname: str, password: str,
                          fromDomain: str, fromPort: int,
                          httpPrefix: str, repeatObjectUrl: str,
                          cachedWebfingers: {}, personCache: {},
                          debug: bool, projectVersion: str) -> {}:
    """Creates an announce message via c2s
    """
    if not session:
        print('WARN: No session for sendAnnounceViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://' + fromDomainFull + '/users/' + fromNickname + \
        '/followers'

    statusNumber, published = getStatusNumber()
    newAnnounceId = httpPrefix + '://' + fromDomainFull + '/users/' + \
        fromNickname + '/statuses/' + statusNumber
    newAnnounceJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname,
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
    (inboxUrl, pubKeyId, pubKey, fromPersonId,
     sharedInbox, avatarUrl,
     displayName) = getPersonBox(baseDir, session, wfRequest,
                                 personCache,
                                 projectVersion, httpPrefix,
                                 fromNickname, fromDomain,
                                 postToBox, 73528)

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
    postResult = postJson(session, newAnnounceJson, [], inboxUrl, headers)
    if not postResult:
        print('WARN: Announce not posted')

    if debug:
        print('DEBUG: c2s POST announce success')

    return newAnnounceJson
