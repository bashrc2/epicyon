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
            new_handle = refollow_dict[handle]
            result[handle] = new_handle
    return result
