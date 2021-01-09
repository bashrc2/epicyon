__filename__ = "migrate.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import getNicknameFromActor
from utils import getDomainFromActor
from webfinger import webfingerHandle
from blocking import isBlocked
from session import getJson
from posts import getUserUrl
from follow import unfollowAccount


def _moveFollowingHandlesForAccount(baseDir: str, nickname: str, domain: str,
                                    session,
                                    httpPrefix: str, cachedWebfingers: {},
                                    followFile: str, debug: bool) -> int:
    """Goes through all follows for an account and updates any that have moved
    """
    ctr = 0
    followingFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/' + followFile
    if not os.path.isfile(followingFilename):
        return ctr
    with open(followingFilename, "r") as f:
        followingHandles = f.readlines()
        for followHandle in followingHandles:
            followHandle = followHandle.strip("\n").strip("\r")
            ctr += \
                _updateMovedHandle(baseDir, nickname, domain,
                                   followHandle, session,
                                   httpPrefix, cachedWebfingers,
                                   followFile, debug)
    return ctr


def _updateMovedHandle(baseDir: str, nickname: str, domain: str,
                       handle: str, session,
                       httpPrefix: str, cachedWebfingers: {},
                       followFile: str, debug: bool) -> int:
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
                                httpPrefix, cachedWebfingers,
                                None, __version__)
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

    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/activity+json; profile="' + profileStr + '"'
    }
    if not personUrl:
        personUrl = getUserUrl(wfRequest)
        if not personUrl:
            return ctr

    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/ld+json; profile="' + profileStr + '"'
    }
    personJson = \
        getJson(session, personUrl, asHeader, None, __version__,
                httpPrefix, None)
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
    if isBlocked(baseDir, nickname, domain,
                 movedToNickname, movedToDomain):
        # someone that you follow has moved to a blocked domain
        # so just unfollow them
        unfollowAccount(baseDir, nickname, domain,
                        movedToNickname, movedToDomainFull,
                        followFile, debug)
        return ctr
    followingFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/' + followFile
    if not os.path.isfile(followingFilename):
        return ctr
    with open(followingFilename, "r") as f:
        followingHandles = f.readlines()
        movedToHandle = movedToNickname + '@' + movedToDomainFull
        movedToHandleLower = movedToHandle.lower()
        handleLower = handle.lower()
        # does the new handle already exist in the following list?
        alreadyFollowingHandle = False
        for followHandle in followingHandles:
            if followHandle.strip("\n").strip("\r").lower() == \
               movedToHandleLower:
                alreadyFollowingHandle = True
        if not alreadyFollowingHandle:
            # replace the old handle with the new one
            with open(followingFilename, 'w+') as f:
                for followHandle in followingHandles:
                    if followHandle.strip("\n").strip("\r").lower() != \
                       handleLower:
                        f.write(followHandle)
                    else:
                        f.write(movedToHandleLower + '\n')
                        ctr += 1
                        print('Follow moved from ' + handleLower +
                              ' to ' + movedToHandleLower)
        else:
            # remove the old handle
            with open(followingFilename, 'w+') as f:
                for followHandle in followingHandles:
                    if followHandle.strip("\n").strip("\r").lower() != \
                       handleLower:
                        f.write(followHandle)
                    else:
                        ctr += 1
    return ctr


def migrateAccounts(baseDir: str, session,
                    httpPrefix: str, cachedWebfingers: {},
                    debug: bool) -> int:
    """If followed accounts change then this modifies the
    following lists for each account accordingly.
    Returns the number of accounts migrated
    """
    # update followers and following lists for each account
    ctr = 0
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if '@' not in handle:
                continue
            if handle.startswith('inbox@'):
                continue
            if handle.startswith('news@'):
                continue
            nickname = handle.split('@')[0]
            domain = handle.split('@')[1]
            ctr += \
                _moveFollowingHandlesForAccount(baseDir, nickname, domain,
                                                session, httpPrefix,
                                                cachedWebfingers,
                                                'following.txt', debug)
        break
    return ctr
