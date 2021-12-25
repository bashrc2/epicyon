__filename__ = "acceptreject.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from utils import hasObjectStringObject
from utils import hasUsersPath
from utils import getFullDomain
from utils import urlPermitted
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import domainPermitted
from utils import followPerson
from utils import acctDir
from utils import hasGroupType
from utils import localActorUrl
from utils import hasActor
from utils import hasObjectStringType


def _create_accept_reject(base_dir: str, federation_list: [],
                          nickname: str, domain: str, port: int,
                          toUrl: str, ccUrl: str, http_prefix: str,
                          objectJson: {}, acceptType: str) -> {}:
    """Accepts or rejects something (eg. a follow request or offer)
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and
    the followers url objectUrl is typically the url of the message,
    corresponding to url or atomUri in createPostBase
    """
    if not objectJson.get('actor'):
        return None

    if not urlPermitted(objectJson['actor'], federation_list):
        return None

    domain = getFullDomain(domain, port)

    new_accept = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': acceptType,
        'actor': localActorUrl(http_prefix, nickname, domain),
        'to': [toUrl],
        'cc': [],
        'object': objectJson
    }
    if ccUrl:
        if len(ccUrl) > 0:
            new_accept['cc'] = [ccUrl]
    return new_accept


def createAccept(base_dir: str, federation_list: [],
                 nickname: str, domain: str, port: int,
                 toUrl: str, ccUrl: str, http_prefix: str,
                 objectJson: {}) -> {}:
    return _create_accept_reject(base_dir, federation_list,
                                 nickname, domain, port,
                                 toUrl, ccUrl, http_prefix,
                                 objectJson, 'Accept')


def createReject(base_dir: str, federation_list: [],
                 nickname: str, domain: str, port: int,
                 toUrl: str, ccUrl: str, http_prefix: str,
                 objectJson: {}) -> {}:
    return _create_accept_reject(base_dir, federation_list,
                                 nickname, domain, port,
                                 toUrl, ccUrl,
                                 http_prefix, objectJson, 'Reject')


def _acceptFollow(base_dir: str, domain: str, message_json: {},
                  federation_list: [], debug: bool) -> None:
    """Receiving a follow Accept activity
    """
    if not hasObjectStringType(message_json, debug):
        return
    if not message_json['object']['type'] == 'Follow':
        if not message_json['object']['type'] == 'Join':
            return
    if debug:
        print('DEBUG: receiving Follow activity')
    if not message_json['object'].get('actor'):
        print('DEBUG: no actor in Follow activity')
        return
    # no, this isn't a mistake
    if not hasObjectStringObject(message_json, debug):
        return
    if not message_json.get('to'):
        if debug:
            print('DEBUG: No "to" parameter in follow Accept')
        return
    if debug:
        print('DEBUG: follow Accept received')
    thisActor = message_json['object']['actor']
    nickname = getNicknameFromActor(thisActor)
    if not nickname:
        print('WARN: no nickname found in ' + thisActor)
        return
    acceptedDomain, acceptedPort = getDomainFromActor(thisActor)
    if not acceptedDomain:
        if debug:
            print('DEBUG: domain not found in ' + thisActor)
        return
    if not nickname:
        if debug:
            print('DEBUG: nickname not found in ' + thisActor)
        return
    if acceptedPort:
        if '/' + acceptedDomain + ':' + str(acceptedPort) + \
           '/users/' + nickname not in thisActor:
            if debug:
                print('Port: ' + str(acceptedPort))
                print('Expected: /' + acceptedDomain + ':' +
                      str(acceptedPort) + '/users/' + nickname)
                print('Actual:   ' + thisActor)
                print('DEBUG: unrecognized actor ' + thisActor)
            return
    else:
        if not '/' + acceptedDomain + '/users/' + nickname in thisActor:
            if debug:
                print('Expected: /' + acceptedDomain + '/users/' + nickname)
                print('Actual:   ' + thisActor)
                print('DEBUG: unrecognized actor ' + thisActor)
            return
    followedActor = message_json['object']['object']
    followedDomain, port = getDomainFromActor(followedActor)
    if not followedDomain:
        print('DEBUG: no domain found within Follow activity object ' +
              followedActor)
        return
    followedDomainFull = followedDomain
    if port:
        followedDomainFull = followedDomain + ':' + str(port)
    followedNickname = getNicknameFromActor(followedActor)
    if not followedNickname:
        print('DEBUG: no nickname found within Follow activity object ' +
              followedActor)
        return

    acceptedDomainFull = acceptedDomain
    if acceptedPort:
        acceptedDomainFull = acceptedDomain + ':' + str(acceptedPort)

    # has this person already been unfollowed?
    unfollowedFilename = \
        acctDir(base_dir, nickname, acceptedDomainFull) + '/unfollowed.txt'
    if os.path.isfile(unfollowedFilename):
        if followedNickname + '@' + followedDomainFull in \
           open(unfollowedFilename).read():
            if debug:
                print('DEBUG: follow accept arrived for ' +
                      nickname + '@' + acceptedDomainFull +
                      ' from ' + followedNickname + '@' + followedDomainFull +
                      ' but they have been unfollowed')
            return

    # does the url path indicate that this is a group actor
    groupAccount = hasGroupType(base_dir, followedActor, None, debug)
    if debug:
        print('Accepted follow is a group: ' + str(groupAccount) +
              ' ' + followedActor + ' ' + base_dir)

    if followPerson(base_dir,
                    nickname, acceptedDomainFull,
                    followedNickname, followedDomainFull,
                    federation_list, debug, groupAccount):
        if debug:
            print('DEBUG: ' + nickname + '@' + acceptedDomainFull +
                  ' followed ' + followedNickname + '@' + followedDomainFull)
    else:
        if debug:
            print('DEBUG: Unable to create follow - ' +
                  nickname + '@' + acceptedDomain + ' -> ' +
                  followedNickname + '@' + followedDomain)


def receiveAcceptReject(session, base_dir: str,
                        http_prefix: str, domain: str, port: int,
                        send_threads: [], postLog: [],
                        cached_webfingers: {},
                        person_cache: {}, message_json: {},
                        federation_list: [],
                        debug: bool) -> bool:
    """Receives an Accept or Reject within the POST section of HTTPServer
    """
    if message_json['type'] != 'Accept' and message_json['type'] != 'Reject':
        return False
    if not hasActor(message_json, debug):
        return False
    if not hasUsersPath(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + '. Assuming single user instance.')
    domain, tempPort = getDomainFromActor(message_json['actor'])
    if not domainPermitted(domain, federation_list):
        if debug:
            print('DEBUG: ' + message_json['type'] +
                  ' from domain not permitted - ' + domain)
        return False
    nickname = getNicknameFromActor(message_json['actor'])
    if not nickname:
        # single user instance
        nickname = 'dev'
        if debug:
            print('DEBUG: ' + message_json['type'] +
                  ' does not contain a nickname. ' +
                  'Assuming single user instance.')
    # receive follow accept
    _acceptFollow(base_dir, domain, message_json, federation_list, debug)
    if debug:
        print('DEBUG: Uh, ' + message_json['type'] + ', I guess')
    return True
