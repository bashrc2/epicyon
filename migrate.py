__filename__ = "migrate.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
from utils import isAccountDir
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import acctDir
from utils import hasGroupType
from webfinger import webfingerHandle
from blocking import isBlocked
from posts import getUserUrl
from follow import unfollowAccount
from person import getActorJson


def _moveFollowingHandlesForAccount(base_dir: str, nickname: str, domain: str,
                                    session,
                                    http_prefix: str, cachedWebfingers: {},
                                    debug: bool,
                                    signingPrivateKeyPem: str) -> int:
    """Goes through all follows for an account and updates any that have moved
    """
    ctr = 0
    followingFilename = acctDir(base_dir, nickname, domain) + '/following.txt'
    if not os.path.isfile(followingFilename):
        return ctr
    with open(followingFilename, 'r') as f:
        followingHandles = f.readlines()
        for followHandle in followingHandles:
            followHandle = followHandle.strip("\n").strip("\r")
            ctr += \
                _updateMovedHandle(base_dir, nickname, domain,
                                   followHandle, session,
                                   http_prefix, cachedWebfingers,
                                   debug, signingPrivateKeyPem)
    return ctr


def _updateMovedHandle(base_dir: str, nickname: str, domain: str,
                       handle: str, session,
                       http_prefix: str, cachedWebfingers: {},
                       debug: bool, signingPrivateKeyPem: str) -> int:
    """Check if an account has moved, and if so then alter following.txt
    for each account.
    Returns 1 if moved, 0 otherwise
    """
    ctr = 0
    if '@' not in handle:
        return ctr
    if len(handle) < 5:
        return ctr
    if handle.startswith('@'):
        handle = handle[1:]
    wfRequest = webfingerHandle(session, handle,
                                http_prefix, cachedWebfingers,
                                domain, __version__, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        print('updateMovedHandle unable to webfinger ' + handle)
        return ctr

    if not isinstance(wfRequest, dict):
        print('updateMovedHandle webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return ctr

    personUrl = None
    if wfRequest.get('errors'):
        print('wfRequest error: ' + str(wfRequest['errors']))
        return ctr

    if not personUrl:
        personUrl = getUserUrl(wfRequest, 0, debug)
        if not personUrl:
            return ctr

    gnunet = False
    if http_prefix == 'gnunet':
        gnunet = True
    personJson = \
        getActorJson(domain, personUrl, http_prefix, gnunet, debug, False,
                     signingPrivateKeyPem, None)
    if not personJson:
        return ctr
    if not personJson.get('movedTo'):
        return ctr
    movedToUrl = personJson['movedTo']
    if '://' not in movedToUrl:
        return ctr
    if '.' not in movedToUrl:
        return ctr
    movedToNickname = getNicknameFromActor(movedToUrl)
    if not movedToNickname:
        return ctr
    movedToDomain, movedToPort = getDomainFromActor(movedToUrl)
    if not movedToDomain:
        return ctr
    movedToDomainFull = movedToDomain
    if movedToPort:
        if movedToPort != 80 and movedToPort != 443:
            movedToDomainFull = movedToDomain + ':' + str(movedToPort)
    groupAccount = hasGroupType(base_dir, movedToUrl, None)
    if isBlocked(base_dir, nickname, domain,
                 movedToNickname, movedToDomain):
        # someone that you follow has moved to a blocked domain
        # so just unfollow them
        unfollowAccount(base_dir, nickname, domain,
                        movedToNickname, movedToDomainFull,
                        debug, groupAccount, 'following.txt')
        return ctr

    followingFilename = acctDir(base_dir, nickname, domain) + '/following.txt'
    if os.path.isfile(followingFilename):
        with open(followingFilename, 'r') as f:
            followingHandles = f.readlines()

            movedToHandle = movedToNickname + '@' + movedToDomainFull
            handleLower = handle.lower()

            refollowFilename = \
                acctDir(base_dir, nickname, domain) + '/refollow.txt'

            # unfollow the old handle
            with open(followingFilename, 'w+') as f:
                for followHandle in followingHandles:
                    if followHandle.strip("\n").strip("\r").lower() != \
                       handleLower:
                        f.write(followHandle)
                    else:
                        handleNickname = handle.split('@')[0]
                        handleDomain = handle.split('@')[1]
                        unfollowAccount(base_dir, nickname, domain,
                                        handleNickname,
                                        handleDomain,
                                        debug, groupAccount, 'following.txt')
                        ctr += 1
                        print('Unfollowed ' + handle + ' who has moved to ' +
                              movedToHandle)

                        # save the new handles to the refollow list
                        if os.path.isfile(refollowFilename):
                            with open(refollowFilename, 'a+') as f:
                                f.write(movedToHandle + '\n')
                        else:
                            with open(refollowFilename, 'w+') as f:
                                f.write(movedToHandle + '\n')

    followersFilename = \
        acctDir(base_dir, nickname, domain) + '/followers.txt'
    if os.path.isfile(followersFilename):
        with open(followersFilename, 'r') as f:
            followerHandles = f.readlines()

            handleLower = handle.lower()

            # remove followers who have moved
            with open(followersFilename, 'w+') as f:
                for followerHandle in followerHandles:
                    if followerHandle.strip("\n").strip("\r").lower() != \
                       handleLower:
                        f.write(followerHandle)
                    else:
                        ctr += 1
                        print('Removed follower who has moved ' + handle)

    return ctr


def migrateAccounts(base_dir: str, session,
                    http_prefix: str, cachedWebfingers: {},
                    debug: bool, signingPrivateKeyPem: str) -> int:
    """If followed accounts change then this modifies the
    following lists for each account accordingly.
    Returns the number of accounts migrated
    """
    # update followers and following lists for each account
    ctr = 0
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if not isAccountDir(handle):
                continue
            nickname = handle.split('@')[0]
            domain = handle.split('@')[1]
            ctr += \
                _moveFollowingHandlesForAccount(base_dir, nickname, domain,
                                                session, http_prefix,
                                                cachedWebfingers, debug,
                                                signingPrivateKeyPem)
        break
    return ctr
