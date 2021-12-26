__filename__ = "availability.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import os
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox
from session import postJson
from utils import hasObjectString
from utils import get_full_domain
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import loadJson
from utils import saveJson
from utils import acct_dir
from utils import local_actor_url
from utils import hasActor


def setAvailability(base_dir: str, nickname: str, domain: str,
                    status: str) -> bool:
    """Set an availability status
    """
    # avoid giant strings
    if len(status) > 128:
        return False
    actorFilename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        return False
    actor_json = loadJson(actorFilename)
    if actor_json:
        actor_json['availability'] = status
        saveJson(actor_json, actorFilename)
    return True


def getAvailability(base_dir: str, nickname: str, domain: str) -> str:
    """Returns the availability for a given person
    """
    actorFilename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        return False
    actor_json = loadJson(actorFilename)
    if actor_json:
        if not actor_json.get('availability'):
            return None
        return actor_json['availability']
    return None


def outboxAvailability(base_dir: str, nickname: str, message_json: {},
                       debug: bool) -> bool:
    """Handles receiving an availability update
    """
    if not message_json.get('type'):
        return False
    if not message_json['type'] == 'Availability':
        return False
    if not hasActor(message_json, debug):
        return False
    if not hasObjectString(message_json, debug):
        return False

    actorNickname = getNicknameFromActor(message_json['actor'])
    if actorNickname != nickname:
        return False
    domain, port = getDomainFromActor(message_json['actor'])
    status = message_json['object'].replace('"', '')

    return setAvailability(base_dir, nickname, domain, status)


def sendAvailabilityViaServer(base_dir: str, session,
                              nickname: str, password: str,
                              domain: str, port: int,
                              http_prefix: str,
                              status: str,
                              cached_webfingers: {}, person_cache: {},
                              debug: bool, project_version: str,
                              signing_priv_key_pem: str) -> {}:
    """Sets the availability for a person via c2s
    """
    if not session:
        print('WARN: No session for sendAvailabilityViaServer')
        return 6

    domain_full = get_full_domain(domain, port)

    toUrl = local_actor_url(http_prefix, nickname, domain_full)
    ccUrl = toUrl + '/followers'

    newAvailabilityJson = {
        'type': 'Availability',
        'actor': toUrl,
        'object': '"' + status + '"',
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = http_prefix + '://' + domain_full + '/@' + nickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cached_webfingers,
                                domain, project_version, debug, False,
                                signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: availability webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: availability webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = domain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache, project_version,
                                    http_prefix, nickname,
                                    domain, postToBox, 57262)

    if not inboxUrl:
        if debug:
            print('DEBUG: availability no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: availability no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(http_prefix, domain_full,
                          session, newAvailabilityJson, [],
                          inboxUrl, headers, 30, True)
    if not postResult:
        print('WARN: availability failed to post')

    if debug:
        print('DEBUG: c2s POST availability success')

    return newAvailabilityJson
