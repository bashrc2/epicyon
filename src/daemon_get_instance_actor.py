__filename__ = "daemon_get_instance_actor.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Daemon GET"

import json
from src.httprequests import request_http
from src.httpcodes import write2
from src.httpcodes import http_404
from src.person import person_lookup
from src.utils import get_instance_url
from src.utils import convert_domains
from src.httpheaders import set_headers
from src.fitnessFunctions import fitness_performance


def show_instance_actor(self, calling_domain: str,
                        referer_domain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domain_full: str,
                        onion_domain: str, i2p_domain: str,
                        yggdrasil_domain: str,
                        getreq_start_time,
                        cookie: str, debug: bool,
                        enable_shared_inbox: bool,
                        fitness: {}) -> bool:
    """Shows the instance actor
    """
    if debug:
        print('Instance actor requested by ' + calling_domain)
    if request_http(self.headers, debug):
        http_404(self, 88)
        return False
    actor_json = person_lookup(domain, path, base_dir)
    if not actor_json:
        print('ERROR: no instance actor found')
        http_404(self, 89)
        return False
    accept_str = self.headers['Accept']
    actor_domain_url = get_instance_url(calling_domain,
                                        http_prefix, domain_full,
                                        onion_domain, i2p_domain,
                                        yggdrasil_domain)
    actor_url = actor_domain_url + '/users/Actor'
    remove_fields = (
        'icon', 'image', 'tts', 'shares',
        'alsoKnownAs', 'hasOccupation', 'featured',
        'featuredTags', 'discoverable', 'published',
        'devices'
    )
    for rfield in remove_fields:
        if rfield in actor_json:
            del actor_json[rfield]
    actor_json['endpoints'] = {}
    if enable_shared_inbox:
        actor_json['endpoints'] = {
            'sharedInbox': actor_domain_url + '/inbox'
        }
    actor_json['name'] = 'ACTOR'
    # FEPs
    actor_json['implements'] = [
        {
            'href': 'https://w3id.org/fep/7aa9',
            'name': 'FEP-7aa9: Featuring recommendations using a dedicated '
            'collection'
        },
        {
            'href': 'https://w3id.org/fep/ee3a',
            'name': 'FEP-ee3a: Exif metadata support'
        },
        {
            'href': 'https://w3id.org/fep/82f6',
            'name': 'FEP-82f6: Actor statuses'
        },
        {
            'href': 'https://w3id.org/fep/5711',
            'name': 'FEP-5711: Inverse Properties for Collections'
        },
        {
            'href': 'https://w3id.org/fep/dd4b',
            'name': 'FEP-dd4b: Quote Posts'
        },
        {
            'href': 'https://w3id.org/fep/b2b8',
            'name': 'FEP-b2b8: Long-form Text'
        },
        {
            'href': 'https://w3id.org/fep/268d',
            'name': 'FEP-268d: Search consent signals for objects'
        },
        {
            'href': 'https://w3id.org/fep/c16b',
            'name': 'FEP-c16b: Formatting MFM functions'
        },
        {
            'href': 'https://w3id.org/fep/5e53',
            'name': 'FEP-5e53: Opt-out Preference Signals'
        },
        {
            'href': 'https://w3id.org/fep/2677',
            'name': 'FEP-2677: Identifying the Application Actor'
        },
        {
            'href': 'https://w3id.org/fep/0837',
            'name': 'FEP-0837: Federated Marketplace'
        },
        {
            'href': 'https://w3id.org/fep/1970',
            'name': 'FEP-1970: Chat Links'
        },
        {
            'href': 'https://w3id.org/fep/fffd',
            'name': 'FEP-fffd: Proxy Objects'
        },
        {
            'href': 'https://w3id.org/fep/c118',
            'name': 'FEP-c118: Content licensing support'
        },
        {
            'href': 'https://w3id.org/fep/4ccd',
            'name': 'FEP-4ccd: Pending Followers Collection and Pending '
            'Following Collection'
        },
        {
            'href': 'https://w3id.org/fep/521a',
            'name': "FEP-521a: Representing actor's public keys"
        },
        {
            'href': 'https://w3id.org/fep/c648',
            'name': 'FEP-c648: Blocked Collection'
        },
        {
            'href': 'https://w3id.org/fep/f1d5',
            'name': 'FEP-f1d5: NodeInfo in Fediverse Software'
        },
        {
            'href': 'https://w3id.org/fep/8fcf',
            'name': 'FEP-8fcf: Followers collection synchronization '
            'across servers'
        },
        {
            'href': 'https://w3id.org/fep/9967',
            'name': 'FEP-9967: Polls'
        },
        {
            'href': 'https://w3id.org/fep/044f',
            'name': 'FEP-044f: Consent-Respecting Quote Posts'
        },
        {
            'href': 'https://w3id.org/fep/7628',
            'name': 'FEP-7628: Move actor (incoming)'
        }
    ]
    actor_json['preferredUsername'] = domain_full
    actor_json['id'] = actor_domain_url + '/actor'
    actor_json['type'] = 'Application'
    actor_json['summary'] = 'Instance Actor'
    actor_json['publicKey']['id'] = actor_domain_url + '/actor#main-key'
    actor_json['publicKey']['owner'] = actor_domain_url + '/actor'
    actor_json['url'] = actor_domain_url + '/actor'
    actor_json['inbox'] = actor_url + '/inbox'
    actor_json['followers'] = actor_url + '/followers'
    actor_json['following'] = actor_url + '/following'
    msg_str = json.dumps(actor_json, ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str, http_prefix,
                              domain,
                              onion_domain,
                              i2p_domain,
                              yggdrasil_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    if 'application/ld+json' in accept_str:
        set_headers(self, 'application/ld+json', msglen,
                    cookie, calling_domain, False)
    elif 'application/jrd+json' in accept_str:
        set_headers(self, 'application/jrd+json', msglen,
                    cookie, calling_domain, False)
    else:
        set_headers(self, 'application/activity+json', msglen,
                    cookie, calling_domain, False)
    write2(self, msg)
    fitness_performance(getreq_start_time, fitness,
                        '_GET', 'show_instance_actor',
                        debug)
    return True
