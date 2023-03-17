__filename__ = "followerSync.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from hashlib import sha256
from utils import acct_dir
from utils import get_user_paths


def _get_followers_for_domain(base_dir: str,
                              nickname: str, domain: str,
                              search_domain: str) -> []:
    """Returns the followers for a given domain
    this is used for followers synchronization
    """
    followers_filename = \
        acct_dir(base_dir, nickname, domain) + '/followers.txt'
    if not os.path.isfile(followers_filename):
        return []
    lines = []
    foll_text = ''
    try:
        with open(followers_filename, 'r', encoding='utf-8') as fp_foll:
            foll_text = fp_foll.read()
    except OSError:
        print('EX: get_followers_for_domain unable to read followers ' +
              followers_filename)
    if search_domain not in foll_text:
        return []
    lines = foll_text.splitlines()
    result = []
    for line_str in lines:
        if search_domain not in line_str:
            continue
        if line_str.endswith('@' + search_domain):
            nick = line_str.split('@')[0]
            paths_list = get_user_paths()
            found = False
            for prefix in ('https', 'http'):
                if found:
                    break
                for possible_path in paths_list:
                    url = prefix + '://' + search_domain + \
                        possible_path + nick
                    filename = base_dir + '/cache/actors/' + \
                        url.replace('/', '#') + '.json'
                    if not os.path.isfile(filename):
                        continue
                    if url not in result:
                        result.append(url)
                    found = True
                    break
        elif '://' + search_domain in line_str:
            result.append(line_str)
    result.sort()
    return result


def _get_followers_sync_json(base_dir: str,
                             nickname: str, domain: str,
                             http_prefix: str, domain_full: str,
                             search_domain: str) -> {}:
    """Returns a response for followers synchronization
    See https://github.com/mastodon/mastodon/pull/14510
    https://codeberg.org/fediverse/fep/src/branch/main/feps/fep-8fcf.md
    """
    sync_list = \
        _get_followers_for_domain(base_dir,
                                  nickname, domain,
                                  search_domain)
    id_str = http_prefix + '://' + domain_full + \
        '/users/' + nickname + '/followers?domain=' + search_domain
    sync_json = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': id_str,
        'orderedItems': sync_list,
        'type': 'OrderedCollection'
    }
    return sync_json


def _get_followers_sync_hash(sync_json: {}) -> str:
    """Returns a hash used within the Collection-Synchronization http header
    See https://github.com/mastodon/mastodon/pull/14510
    https://codeberg.org/fediverse/fep/src/branch/main/feps/fep-8fcf.md
    """
    if not sync_json:
        return None
    sync_hash = None
    for actor in sync_json['orderedItems']:
        actor_hash = sha256(actor.encode('utf-8'))
        if sync_hash:
            sync_hash = sync_hash ^ actor_hash
        else:
            sync_hash = actor_hash
    if sync_hash:
        sync_hash = sync_hash.hexdigest()
    return sync_hash


def update_followers_sync_cache(base_dir: str,
                                nickname: str, domain: str,
                                http_prefix: str, domain_full: str,
                                calling_domain: str,
                                sync_cache: {}) -> ({}, str):
    """Updates the followers synchronization cache
    See https://github.com/mastodon/mastodon/pull/14510
    https://codeberg.org/fediverse/fep/src/branch/main/feps/fep-8fcf.md
    """
    foll_sync_key = nickname + ':' + calling_domain
    if sync_cache.get(foll_sync_key):
        sync_hash = sync_cache[foll_sync_key]['hash']
        sync_json = sync_cache[foll_sync_key]['response']
    else:
        sync_json = \
            _get_followers_sync_json(base_dir,
                                     nickname, domain,
                                     http_prefix,
                                     domain_full,
                                     calling_domain)
        sync_hash = _get_followers_sync_hash(sync_json)
        if sync_hash:
            sync_cache[foll_sync_key] = {
                "hash": sync_hash,
                "response": sync_json
            }
    return sync_json, sync_hash
