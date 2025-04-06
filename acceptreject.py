""" ActivityPub Accept or Reject json """

__filename__ = "acceptreject.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from flags import has_group_type
from flags import url_permitted
from utils import get_attributed_to
from utils import get_user_paths
from utils import text_in_file
from utils import has_object_string_object
from utils import has_users_path
from utils import get_full_domain
from utils import get_domain_from_actor
from utils import get_nickname_from_actor
from utils import domain_permitted
from utils import follow_person
from utils import acct_dir
from utils import local_actor_url
from utils import has_actor
from utils import has_object_string_type
from utils import get_actor_from_post


def _create_accept_reject(federation_list: [],
                          nickname: str, domain: str, port: int,
                          to_url: str, cc_url: str, http_prefix: str,
                          object_json: {}, accept_type: str) -> {}:
    """Accepts or rejects something (eg. a follow request or offer)
    Typically to_url will be https://www.w3.org/ns/activitystreams#Public
    and cc_url might be a specific person favorited or repeated and
    the followers url objectUrl is typically the url of the message,
    corresponding to url or atomUri in createPostBase
    """
    if not object_json.get('actor'):
        return None

    actor_url = get_actor_from_post(object_json)
    if not url_permitted(actor_url, federation_list):
        return None

    domain = get_full_domain(domain, port)

    new_accept = {
        "@context": [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1'
        ],
        'type': accept_type,
        'actor': local_actor_url(http_prefix, nickname, domain),
        'to': [to_url],
        'cc': [],
        'object': object_json
    }
    if cc_url:
        if len(cc_url) > 0:
            new_accept['cc'] = [cc_url]
    return new_accept


def create_accept(federation_list: [],
                  nickname: str, domain: str, port: int,
                  to_url: str, cc_url: str, http_prefix: str,
                  object_json: {}) -> {}:
    """ Create json for ActivityPub Accept """
    return _create_accept_reject(federation_list,
                                 nickname, domain, port,
                                 to_url, cc_url, http_prefix,
                                 object_json, 'Accept')


def create_reject(federation_list: [],
                  nickname: str, domain: str, port: int,
                  to_url: str, cc_url: str, http_prefix: str,
                  object_json: {}) -> {}:
    """ Create json for ActivityPub Reject """
    return _create_accept_reject(federation_list,
                                 nickname, domain, port,
                                 to_url, cc_url,
                                 http_prefix, object_json, 'Reject')


def _reject_quote_request(message_json: {}) -> None:
    """ Rejects a QuoteRequest
    """
    actor = None
    if message_json.get('actor'):
        actor = message_json['actor']
    elif message_json.get('instrument'):
        if isinstance(message_json['instrument'], dict):
            if message_json['instrument'].get('attributedTo'):
                instrument_dict = message_json['instrument']
                actor = get_attributed_to(instrument_dict['attributedTo'])
    if not actor:
        return
    # TODO send back a Reject
    print('REJECT: QuoteRequest from ' + actor)


def _accept_follow(base_dir: str, message_json: {},
                   federation_list: [], debug: bool,
                   curr_domain: str,
                   onion_domain: str, i2p_domain: str) -> None:
    """ Receiving an ActivityPub follow Accept activity
    Your follow was accepted
    """
    if not has_object_string_type(message_json, debug):
        return
    if message_json['object']['type'] not in ('Follow', 'Join'):
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
        print('DEBUG: follow Accept received ' + str(message_json))
    this_actor = get_actor_from_post(message_json['object'])
    nickname = get_nickname_from_actor(this_actor)
    if not nickname:
        print('WARN: no nickname found in ' + this_actor)
        return
    accepted_domain, accepted_port = get_domain_from_actor(this_actor)
    if not accepted_domain:
        if debug:
            print('DEBUG: domain not found in ' + this_actor)
        return
    if not nickname:
        if debug:
            print('DEBUG: nickname not found in ' + this_actor)
        return
    if accepted_port:
        if '/' + accepted_domain + ':' + str(accepted_port) + \
           '/users/' + nickname not in this_actor:
            if debug:
                print('Port: ' + str(accepted_port))
                print('Expected: /' + accepted_domain + ':' +
                      str(accepted_port) + '/users/' + nickname)
                print('Actual:   ' + this_actor)
                print('DEBUG: unrecognized actor ' + this_actor)
            return
    else:
        actor_found = False
        users_list = get_user_paths()
        for users_str in users_list:
            if '/' + accepted_domain + users_str + nickname in this_actor:
                actor_found = True
                break

        if not actor_found:
            if debug:
                print('Expected: /' + accepted_domain + '/users/' + nickname)
                print('Actual:   ' + this_actor)
                print('DEBUG: unrecognized actor ' + this_actor)
            return
    followed_actor = message_json['object']['object']
    followed_domain, port = get_domain_from_actor(followed_actor)
    if not followed_domain:
        print('DEBUG: no domain found within Follow activity object ' +
              followed_actor)
        return
    followed_domain_full = followed_domain
    if port:
        followed_domain_full = followed_domain + ':' + str(port)
    followed_nickname = get_nickname_from_actor(followed_actor)
    if not followed_nickname:
        print('DEBUG: no nickname found within Follow activity object ' +
              followed_actor)
        return

    # convert from onion/i2p to clearnet accepted domain
    if onion_domain:
        if accepted_domain.endswith('.onion') and \
           not curr_domain.endswith('.onion'):
            accepted_domain = curr_domain
    if i2p_domain:
        if accepted_domain.endswith('.i2p') and \
           not curr_domain.endswith('.i2p'):
            accepted_domain = curr_domain

    accepted_domain_full = accepted_domain
    if accepted_port:
        accepted_domain_full = accepted_domain + ':' + str(accepted_port)

    # has this person already been unfollowed?
    unfollowed_filename = \
        acct_dir(base_dir, nickname, accepted_domain_full) + '/unfollowed.txt'
    if os.path.isfile(unfollowed_filename):
        if text_in_file(followed_nickname + '@' + followed_domain_full,
                        unfollowed_filename):
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
                     federation_list, debug, group_account,
                     'following.txt'):
        if debug:
            print('DEBUG: ' + nickname + '@' + accepted_domain_full +
                  ' followed ' +
                  followed_nickname + '@' + followed_domain_full)
    else:
        if debug:
            print('DEBUG: Unable to create follow - ' +
                  nickname + '@' + accepted_domain + ' -> ' +
                  followed_nickname + '@' + followed_domain)


def receive_accept_reject(base_dir: str, domain: str, message_json: {},
                          federation_list: [], debug: bool, curr_domain: str,
                          onion_domain: str, i2p_domain: str) -> bool:
    """Receives an Accept or Reject within the POST section of HTTPServer
    """
    if message_json['type'] not in ('Accept', 'Reject'):
        return False
    if not has_actor(message_json, debug):
        return False
    actor_url = get_actor_from_post(message_json)
    if not has_users_path(actor_url):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + '. Assuming single user instance.')
    domain, _ = get_domain_from_actor(actor_url)
    if not domain_permitted(domain, federation_list):
        if debug:
            print('DEBUG: ' + message_json['type'] +
                  ' from domain not permitted - ' + domain)
        return False
    nickname = get_nickname_from_actor(actor_url)
    if not nickname:
        # single user instance
        nickname = 'dev'
        if debug:
            print('DEBUG: ' + message_json['type'] +
                  ' does not contain a nickname. ' +
                  'Assuming single user instance.')
    # receive follow accept
    _accept_follow(base_dir, message_json, federation_list, debug,
                   curr_domain, onion_domain, i2p_domain)
    if debug:
        print('DEBUG: Uh, ' + message_json['type'] + ', I guess')
    return True


def receive_quote_request(message_json: {}) -> bool:
    """Receives a QuoteRequest within the POST section of HTTPServer
    """
    if message_json['type'] != 'QuoteRequest':
        return False
    _reject_quote_request(message_json)
    return True
