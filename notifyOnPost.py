__filename__ = "notifyOnPost.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Calendar"

import os
from utils import remove_domain_port
from utils import acct_dir


def _notify_on_post_arrival(base_dir: str, nickname: str, domain: str,
                            followingNickname: str,
                            followingDomain: str,
                            add: bool) -> None:
    """Adds or removes a handle from the following.txt list into a list
    indicating whether to notify when a new post arrives from that account
    """
    # check that a following file exists
    domain = remove_domain_port(domain)
    followingFilename = acct_dir(base_dir, nickname, domain) + '/following.txt'
    if not os.path.isfile(followingFilename):
        print("WARN: following.txt doesn't exist for " +
              nickname + '@' + domain)
        return
    handle = followingNickname + '@' + followingDomain

    # check that you are following this handle
    if handle + '\n' not in open(followingFilename).read():
        print('WARN: ' + handle + ' is not in ' + followingFilename)
        return

    notifyOnPostFilename = \
        acct_dir(base_dir, nickname, domain) + '/notifyOnPost.txt'

    # get the contents of the notifyOnPost file, which is
    # a set of handles
    followingHandles = ''
    if os.path.isfile(notifyOnPostFilename):
        print('notify file exists')
        with open(notifyOnPostFilename, 'r') as calendarFile:
            followingHandles = calendarFile.read()
    else:
        # create a new notifyOnPost file from the following file
        print('Creating notifyOnPost file ' + notifyOnPostFilename)
        followingHandles = ''
        with open(followingFilename, 'r') as followingFile:
            followingHandles = followingFile.read()
        if add:
            with open(notifyOnPostFilename, 'w+') as fp:
                fp.write(followingHandles + handle + '\n')

    # already in the notifyOnPost file?
    if handle + '\n' in followingHandles:
        print(handle + ' exists in notifyOnPost.txt')
        if add:
            # already added
            return
        # remove from calendar file
        followingHandles = followingHandles.replace(handle + '\n', '')
        with open(notifyOnPostFilename, 'w+') as fp:
            fp.write(followingHandles)
    else:
        print(handle + ' not in notifyOnPost.txt')
        # not already in the notifyOnPost file
        if add:
            # append to the list of handles
            followingHandles += handle + '\n'
            with open(notifyOnPostFilename, 'w+') as fp:
                fp.write(followingHandles)


def add_notify_on_post(base_dir: str, nickname: str, domain: str,
                       followingNickname: str,
                       followingDomain: str) -> None:
    _notify_on_post_arrival(base_dir, nickname, domain,
                            followingNickname, followingDomain, True)


def remove_notify_on_post(base_dir: str, nickname: str, domain: str,
                          followingNickname: str,
                          followingDomain: str) -> None:
    _notify_on_post_arrival(base_dir, nickname, domain,
                            followingNickname, followingDomain, False)


def notify_when_person_posts(base_dir: str, nickname: str, domain: str,
                             followingNickname: str,
                             followingDomain: str) -> bool:
    """Returns true if receiving notifications when the given publishes a post
    """
    if followingNickname == nickname and followingDomain == domain:
        return False
    notifyOnPostFilename = \
        acct_dir(base_dir, nickname, domain) + '/notifyOnPost.txt'
    handle = followingNickname + '@' + followingDomain
    if not os.path.isfile(notifyOnPostFilename):
        # create a new notifyOnPost file
        with open(notifyOnPostFilename, 'w+') as fp:
            fp.write('')
    return handle + '\n' in open(notifyOnPostFilename).read()
