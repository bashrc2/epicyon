__filename__ = "notifyOnPost.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Calendar"

import os
from utils import remove_domain_port
from utils import acct_dir
from utils import text_in_file


def _notify_on_post_arrival(base_dir: str, nickname: str, domain: str,
                            following_nickname: str,
                            following_domain: str,
                            add: bool) -> None:
    """Adds or removes a handle from the following.txt list into a list
    indicating whether to notify when a new post arrives from that account
    """
    # check that a following file exists
    domain = remove_domain_port(domain)
    following_filename = \
        acct_dir(base_dir, nickname, domain) + '/following.txt'
    if not os.path.isfile(following_filename):
        print("WARN: following.txt doesn't exist for " +
              nickname + '@' + domain)
        return
    handle = following_nickname + '@' + following_domain

    # check that you are following this handle
    if not text_in_file(handle + '\n', following_filename, False):
        print('WARN: ' + handle + ' is not in ' + following_filename)
        return

    notify_on_post_filename = \
        acct_dir(base_dir, nickname, domain) + '/notifyOnPost.txt'

    # get the contents of the notifyOnPost file, which is
    # a set of handles
    following_handles = ''
    if os.path.isfile(notify_on_post_filename):
        print('notify file exists')
        with open(notify_on_post_filename, 'r',
                  encoding='utf-8') as calendar_file:
            following_handles = calendar_file.read()
    else:
        # create a new notifyOnPost file from the following file
        print('Creating notifyOnPost file ' + notify_on_post_filename)
        following_handles = ''
        with open(following_filename, 'r',
                  encoding='utf-8') as following_file:
            following_handles = following_file.read()
        if add:
            with open(notify_on_post_filename, 'w+',
                      encoding='utf-8') as fp_notify:
                fp_notify.write(following_handles + handle + '\n')

    # already in the notifyOnPost file?
    if handle + '\n' in following_handles or \
       handle + '\n' in following_handles.lower():
        print(handle + ' exists in notifyOnPost.txt')
        if add:
            # already added
            return
        # remove from calendar file
        new_following_handles = ''
        following_handles_list = following_handles.split('\n')
        handle_lower = handle.lower()
        for followed in following_handles_list:
            if followed.lower() != handle_lower:
                new_following_handles += followed + '\n'
        following_handles = new_following_handles

        with open(notify_on_post_filename, 'w+',
                  encoding='utf-8') as fp_notify:
            fp_notify.write(following_handles)
    else:
        print(handle + ' not in notifyOnPost.txt')
        # not already in the notifyOnPost file
        if add:
            # append to the list of handles
            following_handles += handle + '\n'
            with open(notify_on_post_filename, 'w+',
                      encoding='utf-8') as fp_notify:
                fp_notify.write(following_handles)


def add_notify_on_post(base_dir: str, nickname: str, domain: str,
                       following_nickname: str,
                       following_domain: str) -> None:
    """Add a notification
    """
    _notify_on_post_arrival(base_dir, nickname, domain,
                            following_nickname, following_domain, True)


def remove_notify_on_post(base_dir: str, nickname: str, domain: str,
                          following_nickname: str,
                          following_domain: str) -> None:
    """Remove a notification
    """
    _notify_on_post_arrival(base_dir, nickname, domain,
                            following_nickname, following_domain, False)


def notify_when_person_posts(base_dir: str, nickname: str, domain: str,
                             following_nickname: str,
                             following_domain: str) -> bool:
    """Returns true if receiving notifications when the given publishes a post
    """
    if following_nickname == nickname and following_domain == domain:
        return False
    notify_on_post_filename = \
        acct_dir(base_dir, nickname, domain) + '/notifyOnPost.txt'
    handle = following_nickname + '@' + following_domain
    if not os.path.isfile(notify_on_post_filename):
        # create a new notifyOnPost file
        with open(notify_on_post_filename, 'w+',
                  encoding='utf-8') as fp_notify:
            fp_notify.write('')
    return text_in_file(handle + '\n', notify_on_post_filename, False)
