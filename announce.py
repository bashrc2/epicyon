__filename__ = "announce.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

from utils import has_object_string_object
from utils import has_group_type
from utils import remove_domain_port
from utils import removeIdEnding
from utils import has_users_path
from utils import get_full_domain
from utils import getStatusNumber
from utils import createOutboxDir
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import save_json
from utils import undoAnnounceCollectionEntry
from utils import updateAnnounceCollection
from utils import local_actor_url
from utils import replace_users_with_at
from utils import has_actor
from utils import has_object_stringType
from posts import sendSignedJson
from posts import getPersonBox
from session import postJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader


def isSelfAnnounce(post_json_object: {}) -> bool:
    """Is the given post a self announce?
    """
    if not post_json_object.get('actor'):
        return False
    if not post_json_object.get('type'):
        return False
    if post_json_object['type'] != 'Announce':
        return False
    if not post_json_object.get('object'):
        return False
    if not isinstance(post_json_object['actor'], str):
        return False
    if not isinstance(post_json_object['object'], str):
        return False
    return post_json_object['actor'] in post_json_object['object']


def outboxAnnounce(recentPostsCache: {},
                   base_dir: str, message_json: {}, debug: bool) -> bool:
    """ Adds or removes announce entries from the shares collection
    within a given post
    """
    if not has_actor(message_json, debug):
        return False
    if not isinstance(message_json['actor'], str):
        return False
    if not message_json.get('type'):
        return False
    if not message_json.get('object'):
        return False
    if message_json['type'] == 'Announce':
        if not isinstance(message_json['object'], str):
            return False
        if isSelfAnnounce(message_json):
            return False
        nickname = getNicknameFromActor(message_json['actor'])
        if not nickname:
            print('WARN: no nickname found in ' + message_json['actor'])
            return False
        domain, port = getDomainFromActor(message_json['actor'])
        postFilename = locatePost(base_dir, nickname, domain,
                                  message_json['object'])
        if postFilename:
            updateAnnounceCollection(recentPostsCache, base_dir, postFilename,
                                     message_json['actor'],
                                     nickname, domain, debug)
            return True
    elif message_json['type'] == 'Undo':
        if not has_object_stringType(message_json, debug):
            return False
        if message_json['object']['type'] == 'Announce':
            if not isinstance(message_json['object']['object'], str):
                return False
            nickname = getNicknameFromActor(message_json['actor'])
            if not nickname:
                print('WARN: no nickname found in ' + message_json['actor'])
                return False
            domain, port = getDomainFromActor(message_json['actor'])
            postFilename = locatePost(base_dir, nickname, domain,
                                      message_json['object']['object'])
            if postFilename:
                undoAnnounceCollectionEntry(recentPostsCache,
                                            base_dir, postFilename,
                                            message_json['actor'],
                                            domain, debug)
                return True
    return False


def announcedByPerson(isAnnounced: bool, postActor: str,
                      nickname: str, domain_full: str) -> bool:
    """Returns True if the given post is announced by the given person
    """
    if not postActor:
        return False
    if isAnnounced and \
       postActor.endswith(domain_full + '/users/' + nickname):
        return True
    return False


def createAnnounce(session, base_dir: str, federation_list: [],
                   nickname: str, domain: str, port: int,
                   toUrl: str, ccUrl: str, http_prefix: str,
                   objectUrl: str, saveToFile: bool,
                   client_to_server: bool,
                   send_threads: [], postLog: [],
                   person_cache: {}, cached_webfingers: {},
                   debug: bool, project_version: str,
                   signing_priv_key_pem: str) -> {}:
    """Creates an announce message
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and the
    followers url objectUrl is typically the url of the message,
    corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl, federation_list):
        return None

    domain = remove_domain_port(domain)
    fullDomain = get_full_domain(domain, port)

    statusNumber, published = getStatusNumber()
    newAnnounceId = http_prefix + '://' + fullDomain + \
        '/users/' + nickname + '/statuses/' + statusNumber
    atomUriStr = local_actor_url(http_prefix, nickname, fullDomain) + \
        '/statuses/' + statusNumber
    newAnnounce = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': local_actor_url(http_prefix, nickname, fullDomain),
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
        outboxDir = createOutboxDir(nickname, domain, base_dir)
        filename = outboxDir + '/' + newAnnounceId.replace('/', '#') + '.json'
        save_json(newAnnounce, filename)

    announceNickname = None
    announceDomain = None
    announcePort = None
    group_account = False
    if has_users_path(objectUrl):
        announceNickname = getNicknameFromActor(objectUrl)
        announceDomain, announcePort = getDomainFromActor(objectUrl)
        if '/' + str(announceNickname) + '/' in objectUrl:
            announceActor = \
                objectUrl.split('/' + announceNickname + '/')[0] + \
                '/' + announceNickname
            if has_group_type(base_dir, announceActor, person_cache):
                group_account = True

    if announceNickname and announceDomain:
        sendSignedJson(newAnnounce, session, base_dir,
                       nickname, domain, port,
                       announceNickname, announceDomain, announcePort, None,
                       http_prefix, True, client_to_server, federation_list,
                       send_threads, postLog, cached_webfingers, person_cache,
                       debug, project_version, None, group_account,
                       signing_priv_key_pem, 639633)

    return newAnnounce


def announcePublic(session, base_dir: str, federation_list: [],
                   nickname: str, domain: str, port: int, http_prefix: str,
                   objectUrl: str, client_to_server: bool,
                   send_threads: [], postLog: [],
                   person_cache: {}, cached_webfingers: {},
                   debug: bool, project_version: str,
                   signing_priv_key_pem: str) -> {}:
    """Makes a public announcement
    """
    fromDomain = get_full_domain(domain, port)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = local_actor_url(http_prefix, nickname, fromDomain) + '/followers'
    return createAnnounce(session, base_dir, federation_list,
                          nickname, domain, port,
                          toUrl, ccUrl, http_prefix,
                          objectUrl, True, client_to_server,
                          send_threads, postLog,
                          person_cache, cached_webfingers,
                          debug, project_version,
                          signing_priv_key_pem)


def sendAnnounceViaServer(base_dir: str, session,
                          fromNickname: str, password: str,
                          fromDomain: str, fromPort: int,
                          http_prefix: str, repeatObjectUrl: str,
                          cached_webfingers: {}, person_cache: {},
                          debug: bool, project_version: str,
                          signing_priv_key_pem: str) -> {}:
    """Creates an announce message via c2s
    """
    if not session:
        print('WARN: No session for sendAnnounceViaServer')
        return 6

    fromDomainFull = get_full_domain(fromDomain, fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    actorStr = local_actor_url(http_prefix, fromNickname, fromDomainFull)
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

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cached_webfingers,
                                fromDomain, project_version, debug, False,
                                signing_priv_key_pem)
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
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache,
                                    project_version, http_prefix,
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
    postResult = postJson(http_prefix, fromDomainFull,
                          session, newAnnounceJson, [], inboxUrl,
                          headers, 3, True)
    if not postResult:
        print('WARN: announce not posted')

    if debug:
        print('DEBUG: c2s POST announce success')

    return newAnnounceJson


def sendUndoAnnounceViaServer(base_dir: str, session,
                              undoPostJsonObject: {},
                              nickname: str, password: str,
                              domain: str, port: int,
                              http_prefix: str, repeatObjectUrl: str,
                              cached_webfingers: {}, person_cache: {},
                              debug: bool, project_version: str,
                              signing_priv_key_pem: str) -> {}:
    """Undo an announce message via c2s
    """
    if not session:
        print('WARN: No session for sendUndoAnnounceViaServer')
        return 6

    domain_full = get_full_domain(domain, port)

    actor = local_actor_url(http_prefix, nickname, domain_full)
    handle = replace_users_with_at(actor)

    statusNumber, published = getStatusNumber()
    unAnnounceJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': actor + '/statuses/' + str(statusNumber) + '/undo',
        'type': 'Undo',
        'actor': actor,
        'object': undoPostJsonObject['object']
    }

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cached_webfingers,
                                domain, project_version, debug, False,
                                signing_priv_key_pem)
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
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache,
                                    project_version, http_prefix,
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
    postResult = postJson(http_prefix, domain_full,
                          session, unAnnounceJson, [], inboxUrl,
                          headers, 3, True)
    if not postResult:
        print('WARN: undo announce not posted')

    if debug:
        print('DEBUG: c2s POST undo announce success')

    return unAnnounceJson


def outboxUndoAnnounce(recentPostsCache: {},
                       base_dir: str, http_prefix: str,
                       nickname: str, domain: str, port: int,
                       message_json: {}, debug: bool) -> None:
    """ When an undo announce is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if not message_json['type'] == 'Undo':
        return
    if not has_object_stringType(message_json, debug):
        return
    if not message_json['object']['type'] == 'Announce':
        if debug:
            print('DEBUG: not a undo announce')
        return
    if not has_object_string_object(message_json, debug):
        return
    if debug:
        print('DEBUG: c2s undo announce request arrived in outbox')

    messageId = removeIdEnding(message_json['object']['object'])
    domain = remove_domain_port(domain)
    postFilename = locatePost(base_dir, nickname, domain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo announce post not found in inbox or outbox')
            print(messageId)
        return True
    undoAnnounceCollectionEntry(recentPostsCache, base_dir, postFilename,
                                message_json['actor'], domain, debug)
    if debug:
        print('DEBUG: post undo announce via c2s - ' + postFilename)
