__filename__ = "daemon_get_collections.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Daemon GET"

import json
from src.context import get_individual_post_context
from src.httpcodes import write2
from src.httpcodes import http_404
from src.httpheaders import set_headers
from src.posts import json_pin_post
from src.utils import convert_domains
from src.utils import get_json_content_from_accept
from src.utils import acct_dir
from src.utils import load_json
from src.follow import get_following_feed
from src.data import is_a_file


def get_feature_authorization(self, calling_domain: str,
                              referer_domain: str,
                              base_dir: str,
                              http_prefix: str,
                              nickname: str, domain: str,
                              domain_full: str,
                              onion_domain: str,
                              i2p_domain: str,
                              yggdrasil_domain: str) -> None:
    """Returns the verification stamp for feature authorization
    https://codeberg.org/fediverse/fep/src/branch/main/fep/7aa9/fep-7aa9.md
    """
    if '/stamps/' not in self.path:
        return
    stamp_number = self.path.split('/stamps/')[1]
    if '/' in stamp_number:
        stamp_number = stamp_number.split('/')[0]
    if not stamp_number:
        return
    if not stamp_number.isdigit():
        return
    # does the stamp exist?
    account_dir = acct_dir(base_dir, nickname, domain)
    stamp_filename = account_dir + '/stamps/' + stamp_number
    if not is_a_file(stamp_filename):
        return
    # load the stamp from file
    stamp_json = load_json(stamp_filename)
    if not stamp_json:
        return
    if not stamp_json.get('id') or not stamp_json.get('object'):
        return
    # create the verification
    stamp_url = \
        http_prefix + '://' + domain_full + '/users/' + nickname + \
        '/stamps/' + stamp_number
    verification_json = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://gotosocial.org/ns",
            "https://w3id.org/fep/7aa9"
        ],
        "id": stamp_url,
        "type": "FeatureAuthorization",
        "interactingObject": stamp_json['id'],
        "interactionTarget": stamp_json['object']
    }
    # send the verification
    msg_str = json.dumps(verification_json, ensure_ascii=False)
    msg_str = convert_domains(calling_domain, referer_domain,
                              msg_str, http_prefix,
                              domain, onion_domain, i2p_domain,
                              yggdrasil_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    accept_str = self.headers['Accept']
    protocol_str = get_json_content_from_accept(accept_str)
    set_headers(self, protocol_str, msglen, None, calling_domain, False)
    write2(self, msg)


def get_featured_collection(self, calling_domain: str,
                            referer_domain: str,
                            base_dir: str,
                            http_prefix: str,
                            nickname: str, domain: str,
                            domain_full: str,
                            system_language: str,
                            onion_domain: str,
                            i2p_domain: str,
                            yggdrasil_domain: str) -> None:
    """Returns the featured posts collections in
    actor/collections/featured
    """
    featured_collection = \
        json_pin_post(base_dir, http_prefix,
                      nickname, domain, domain_full, system_language)
    msg_str = json.dumps(featured_collection,
                         ensure_ascii=False)
    msg_str = convert_domains(calling_domain, referer_domain,
                              msg_str, http_prefix,
                              domain, onion_domain, i2p_domain,
                              yggdrasil_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    accept_str = self.headers['Accept']
    protocol_str = \
        get_json_content_from_accept(accept_str)
    set_headers(self, protocol_str, msglen,
                None, calling_domain, False)
    write2(self, msg)


def get_featured_tags_collection(self, calling_domain: str,
                                 referer_domain: str,
                                 path: str, http_prefix: str,
                                 domain_full: str, domain: str,
                                 onion_domain: str, i2p_domain: str,
                                 yggdrasil_domain: str) -> None:
    """Returns the featured tags collections in
    actor/collections/featuredTags
    """
    post_context = get_individual_post_context()
    featured_tags_collection = {
        '@context': post_context,
        'id': http_prefix + '://' + domain_full + path,
        'orderedItems': [],
        'totalItems': 0,
        'type': 'OrderedCollection'
    }
    msg_str = json.dumps(featured_tags_collection,
                         ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str, http_prefix,
                              domain,
                              onion_domain,
                              i2p_domain,
                              yggdrasil_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    accept_str = self.headers['Accept']
    protocol_str = \
        get_json_content_from_accept(accept_str)
    set_headers(self, protocol_str, msglen,
                None, calling_domain, False)
    write2(self, msg)


def get_following_json(self, base_dir: str, path: str,
                       calling_domain: str, referer_domain: str,
                       http_prefix: str,
                       domain: str, port: int,
                       following_items_per_page: int,
                       debug: bool, list_name: str,
                       onion_domain: str, i2p_domain: str,
                       yggdrasil_domain: str) -> None:
    """Returns json collection for following.txt
    """
    following_json = \
        get_following_feed(base_dir, domain, port, path, http_prefix,
                           True, following_items_per_page, list_name)
    if not following_json:
        if debug:
            print(list_name + ' json feed not found for ' + path)
        http_404(self, 109)
        return
    msg_str = json.dumps(following_json,
                         ensure_ascii=False)
    msg_str = convert_domains(calling_domain,
                              referer_domain,
                              msg_str, http_prefix,
                              domain,
                              onion_domain,
                              i2p_domain,
                              yggdrasil_domain)
    msg = msg_str.encode('utf-8')
    msglen = len(msg)
    accept_str = self.headers['Accept']
    protocol_str = \
        get_json_content_from_accept(accept_str)
    set_headers(self, protocol_str, msglen,
                None, calling_domain, False)
    write2(self, msg)
