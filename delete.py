__filename__ = "delete.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from datetime import datetime
from utils import has_object_string
from utils import remove_domain_port
from utils import has_users_path
from utils import get_full_domain
from utils import remove_id_ending
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import locate_post
from utils import delete_post
from utils import remove_moderation_post_from_index
from utils import local_actor_url
from session import postJson
from webfinger import webfingerHandle
from auth import create_basic_auth_header
from posts import getPersonBox


def sendDeleteViaServer(base_dir: str, session,
                        fromNickname: str, password: str,
                        fromDomain: str, fromPort: int,
                        http_prefix: str, deleteObjectUrl: str,
                        cached_webfingers: {}, person_cache: {},
                        debug: bool, project_version: str,
                        signing_priv_key_pem: str) -> {}:
    """Creates a delete request message via c2s
    """
    if not session:
        print('WARN: No session for sendDeleteViaServer')
        return 6

    fromDomainFull = get_full_domain(fromDomain, fromPort)

    actor = local_actor_url(http_prefix, fromNickname, fromDomainFull)
    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = actor + '/followers'

    newDeleteJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': actor,
        'cc': [ccUrl],
        'object': deleteObjectUrl,
        'to': [toUrl],
        'type': 'Delete'
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cached_webfingers,
                        fromDomain, project_version, debug, False,
                        signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: delete webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: delete webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem, originDomain,
                                    base_dir, session, wfRequest, person_cache,
                                    project_version, http_prefix, fromNickname,
                                    fromDomain, postToBox, 53036)

    if not inboxUrl:
        if debug:
            print('DEBUG: delete no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: delete no actor was found for ' + handle)
        return 4

    authHeader = create_basic_auth_header(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(http_prefix, fromDomainFull,
                 session, newDeleteJson, [], inboxUrl, headers, 3, True)
    if not postResult:
        if debug:
            print('DEBUG: POST delete failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST delete request success')

    return newDeleteJson


def outboxDelete(base_dir: str, http_prefix: str,
                 nickname: str, domain: str,
                 message_json: {}, debug: bool,
                 allow_deletion: bool,
                 recent_posts_cache: {}) -> None:
    """ When a delete request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        if debug:
            print('DEBUG: delete - no type')
        return
    if not message_json['type'] == 'Delete':
        if debug:
            print('DEBUG: not a delete')
        return
    if not has_object_string(message_json, debug):
        return
    if debug:
        print('DEBUG: c2s delete request arrived in outbox')
    deletePrefix = http_prefix + '://' + domain
    if (not allow_deletion and
        (not message_json['object'].startswith(deletePrefix) or
         not message_json['actor'].startswith(deletePrefix))):
        if debug:
            print('DEBUG: delete not permitted from other instances')
        return
    messageId = remove_id_ending(message_json['object'])
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s delete object is not a status')
        return
    if not has_users_path(messageId):
        if debug:
            print('DEBUG: c2s delete object has no nickname')
        return
    deleteNickname = get_nickname_from_actor(messageId)
    if deleteNickname != nickname:
        if debug:
            print("DEBUG: you can't delete a post which " +
                  "wasn't created by you (nickname does not match)")
        return
    deleteDomain, deletePort = get_domain_from_actor(messageId)
    domain = remove_domain_port(domain)
    if deleteDomain != domain:
        if debug:
            print("DEBUG: you can't delete a post which " +
                  "wasn't created by you (domain does not match)")
        return
    remove_moderation_post_from_index(base_dir, messageId, debug)
    post_filename = locate_post(base_dir, deleteNickname, deleteDomain,
                                messageId)
    if not post_filename:
        if debug:
            print('DEBUG: c2s delete post not found in inbox or outbox')
            print(messageId)
        return True
    delete_post(base_dir, http_prefix, deleteNickname, deleteDomain,
                post_filename, debug, recent_posts_cache)
    if debug:
        print('DEBUG: post deleted via c2s - ' + post_filename)


def removeOldHashtags(base_dir: str, maxMonths: int) -> str:
    """Remove old hashtags
    """
    if maxMonths > 11:
        maxMonths = 11
    maxDaysSinceEpoch = \
        (datetime.utcnow() - datetime(1970, 1 + maxMonths, 1)).days
    removeHashtags = []

    for subdir, dirs, files in os.walk(base_dir + '/tags'):
        for f in files:
            tagsFilename = os.path.join(base_dir + '/tags', f)
            if not os.path.isfile(tagsFilename):
                continue
            # get last modified datetime
            modTimesinceEpoc = os.path.getmtime(tagsFilename)
            lastModifiedDate = datetime.fromtimestamp(modTimesinceEpoc)
            fileDaysSinceEpoch = (lastModifiedDate - datetime(1970, 1, 1)).days

            # check of the file is too old
            if fileDaysSinceEpoch < maxDaysSinceEpoch:
                removeHashtags.append(tagsFilename)
        break

    for removeFilename in removeHashtags:
        try:
            os.remove(removeFilename)
        except OSError:
            print('EX: removeOldHashtags unable to delete ' + removeFilename)
