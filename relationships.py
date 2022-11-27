__filename__ = "relationships.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
from utils import acct_dir
from utils import valid_nickname
from utils import get_full_domain
from utils import local_actor_url
from utils import remove_domain_port
from utils import remove_eol


def get_moved_accounts(base_dir: str, nickname: str, domain: str,
                       filename: str = 'following.txt') -> {}:
    """returns a dict of moved accounts
    """
    refollow_filename = base_dir + '/accounts/actors_moved.txt'
    if not os.path.isfile(refollow_filename):
        return {}
    refollow_str = ''
    try:
        with open(refollow_filename, 'r',
                  encoding='utf-8') as fp_refollow:
            refollow_str = fp_refollow.read()
    except OSError:
        print('EX: get_moved_accounts unable to read ' +
              refollow_filename)
    refollow_list = refollow_str.split('\n')
    refollow_dict = {}
    for line in refollow_list:
        prev_handle = line.split(' ')[0]
        new_handle = line.split(' ')[1]
        refollow_dict[prev_handle] = new_handle

    follow_filename = \
        acct_dir(base_dir, nickname, domain) + '/' + filename
    follow_str = ''
    try:
        with open(follow_filename, 'r',
                  encoding='utf-8') as fp_follow:
            follow_str = fp_follow.read()
    except OSError:
        print('EX: get_moved_accounts unable to read ' +
              follow_filename)
    follow_list = follow_str.split('\n')

    result = {}
    for handle in follow_list:
        if refollow_dict.get(handle):
            result[handle] = refollow_dict[handle]
    return result


def get_moved_feed(base_dir: str, domain: str, port: int, path: str,
                   http_prefix: str, authorized: bool,
                   follows_per_page=12) -> {}:
    """Returns the moved accounts feed from GET requests.
    """
    # Show a small number of follows to non-authorized viewers
    if not authorized:
        follows_per_page = 6

    if '/moved' not in path:
        return None
    # handle page numbers
    header_only = True
    page_number = None
    if '?page=' in path:
        page_number = path.split('?page=')[1]
        if len(page_number) > 5:
            page_number = "1"
        if page_number == 'true' or not authorized:
            page_number = 1
        else:
            try:
                page_number = int(page_number)
            except BaseException:
                print('EX: get_moved_feed unable to convert to int ' +
                      str(page_number))
        path = path.split('?page=')[0]
        header_only = False

    if not path.endswith('/moved'):
        return None
    nickname = None
    if path.startswith('/users/'):
        nickname = \
            path.replace('/users/', '', 1).replace('/moved', '')
    if path.startswith('/@'):
        nickname = path.replace('/@', '', 1).replace('/moved', '')
    if not nickname:
        return None
    if not valid_nickname(domain, nickname):
        return None

    domain = get_full_domain(domain, port)

    lines = get_moved_accounts(base_dir, nickname, domain,
                               'following.txt')

    if header_only:
        first_str = \
            local_actor_url(http_prefix, nickname, domain) + \
            '/moved?page=1'
        id_str = \
            local_actor_url(http_prefix, nickname, domain) + '/moved'
        total_str = str(len(lines.items()))
        following = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': first_str,
            'id': id_str,
            'totalItems': total_str,
            'type': 'OrderedCollection',
            'orderedItems': []
        }
        return following

    if not page_number:
        page_number = 1

    next_page_number = int(page_number + 1)
    id_str = \
        local_actor_url(http_prefix, nickname, domain) + \
        '/moved?page=' + str(page_number)
    part_of_str = \
        local_actor_url(http_prefix, nickname, domain) + '/moved'
    following = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': id_str,
        'orderedItems': [],
        'partOf': part_of_str,
        'totalItems': 0,
        'type': 'OrderedCollectionPage'
    }

    handle_domain = domain
    handle_domain = remove_domain_port(handle_domain)
    accounts_dir = acct_dir(base_dir, nickname, handle_domain)
    filename = accounts_dir + '/moved.txt'
    if not os.path.isfile(filename):
        return following
    curr_page = 1
    page_ctr = 0
    total_ctr = 0
    for handle, new_handle in lines.items():
        # nickname@domain
        page_ctr += 1
        total_ctr += 1
        if curr_page == page_number:
            line2_lower = handle.lower()
            line2 = remove_eol(line2_lower)
            nick = line2.split('@')[0]
            dom = line2.split('@')[1]
            if not nick.startswith('!'):
                # person actor
                url = local_actor_url(http_prefix, nick, dom)
            else:
                # group actor
                url = http_prefix + '://' + dom + '/c/' + nick
                following['orderedItems'].append(url)
        if page_ctr >= follows_per_page:
            page_ctr = 0
            curr_page += 1
    following['totalItems'] = total_ctr
    last_page = int(total_ctr / follows_per_page)
    last_page = max(last_page, 1)
    if next_page_number > last_page:
        following['next'] = \
            local_actor_url(http_prefix, nickname, domain) + \
            '/moved?page=' + str(last_page)
    return following
