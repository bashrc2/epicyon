__filename__ = "acceptreject.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from utils import has_object_string_object
from utils import has_users_path
from utils import get_full_domain
from utils import urlPermitted
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import domainPermitted
from utils import follow_person
from utils import acct_dir
from utils import has_group_type
from utils import local_actor_url
from utils import has_actor
from utils import has_object_stringType


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

    domain = get_full_domain(domain, port)

    new_accept = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': acceptType,
        'actor': local_actor_url(http_prefix, nickname, domain),
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


def _accept_follow(base_dir: str, domain: str, message_json: {},
                   federation_list: [], debug: bool) -> None:
    """Receiving a follow Accept activity
    """
    if not has_object_stringType(message_json, debug):
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
    if not has_object_string_object(message_json, debug):
        return
    if not message_json.get('to'):
        if debug:
            print('DEBUG: No "to" parameter in follow Accept')
        return
    if debug:
        print('DEBUG: follow Accept received')
    this_actor = message_json['object']['actor']
    nickname = getNicknameFromActor(this_actor)
    if not nickname:
        print('WARN: no nickname found in ' + this_actor)
        return
    acceptedDomain, acceptedPort = getDomainFromActor(this_actor)
    if not acceptedDomain:
        if debug:
            print('DEBUG: domain not found in ' + this_actor)
        return
    if not nickname:
        if debug:
            print('DEBUG: nickname not found in ' + this_actor)
        return
    if acceptedPort:
        if '/' + acceptedDomain + ':' + str(acceptedPort) + \
           '/users/' + nickname not in this_actor:
            if debug:
                print('Port: ' + str(acceptedPort))
                print('Expected: /' + acceptedDomain + ':' +
                      str(acceptedPort) + '/users/' + nickname)
                print('Actual:   ' + this_actor)
                print('DEBUG: unrecognized actor ' + this_actor)
            return
    else:
        if not '/' + acceptedDomain + '/users/' + nickname in this_actor:
            if debug:
                print('Expected: /' + acceptedDomain + '/users/' + nickname)
                print('Actual:   ' + this_actor)
                print('DEBUG: unrecognized actor ' + this_actor)
            return
    followed_actor = message_json['object']['object']
    followed_domain, port = getDomainFromActor(followed_actor)
    if not followed_domain:
        print('DEBUG: no domain found within Follow activity object ' +
              followed_actor)
        return
    followed_domain_full = followed_domain
    if port:
        followed_domain_full = followed_domain + ':' + str(port)
    followed_nickname = getNicknameFromActor(followed_actor)
    if not followed_nickname:
        print('DEBUG: no nickname found within Follow activity object ' +
              followed_actor)
        return

    accepted_domain_full = acceptedDomain
    if acceptedPort:
        accepted_domain_full = acceptedDomain + ':' + str(acceptedPort)

    # has this person already been unfollowed?
    unfollowed_filename = \
        acct_dir(base_dir, nickname, accepted_domain_full) + '/unfollowed.txt'
    if os.path.isfile(unfollowed_filename):
        if followed_nickname + '@' + followed_domain_full in \
           open(unfollowed_filename).read():
            if debug:
                print('DEBUG: follow accept arrived for ' +
                      nickname + '@' + accepted_domain_full +
                      ' from ' +
                      followed_nickname + '@' + followed_domain_full +
                      ' but they have been unfollowed')
            return

    # does the url path indicate that this is a group actor
    group_account = has_group_type(base_dir, followed_actor, None, debug)
    if debug:
        print('Accepted follow is a group: ' + str(group_account) +
              ' ' + followed_actor + ' ' + base_dir)

    if follow_person(base_dir,
                     nickname, accepted_domain_full,
                     followed_nickname, followed_domain_full,
                     federation_list, debug, group_account):
        if debug:
            print('DEBUG: ' + nickname + '@' + accepted_domain_full +
                  ' followed ' +
                  followed_nickname + '@' + followed_domain_full)
    else:
        if debug:
            print('DEBUG: Unable to create follow - ' +
                  nickname + '@' + acceptedDomain + ' -> ' +
                  followed_nickname + '@' + followed_domain)


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
    if not has_actor(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + '. Assuming single user instance.')
    domain, _ = getDomainFromActor(message_json['actor'])
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
    _accept_follow(base_dir, domain, message_json, federation_list, debug)
    if debug:
        print('DEBUG: Uh, ' + message_json['type'] + ', I guess')
    return True
