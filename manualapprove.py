__filename__ = "manualapprove.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from follow import followedAccountAccepts
from follow import followedAccountRejects
from follow import removeFromFollowRequests
from utils import loadJson


def manualDenyFollowRequest(session, baseDir: str,
                            httpPrefix: str,
                            nickname: str, domain: str, port: int,
                            denyHandle: str,
                            federationList: [],
                            sendThreads: [], postLog: [],
                            cachedWebfingers: {}, personCache: {},
                            debug: bool,
                            projectVersion: str) -> None:
    """Manually deny a follow request
    """
    handle = nickname + '@' + domain
    accountsDir = baseDir + '/accounts/' + handle

    # has this handle already been rejected?
    rejectedFollowsFilename = accountsDir + '/followrejects.txt'
    if os.path.isfile(rejectedFollowsFilename):
        if denyHandle in open(rejectedFollowsFilename).read():
            removeFromFollowRequests(baseDir, nickname, domain,
                                     denyHandle, debug)
            print(denyHandle + ' has already been rejected as a follower of ' +
                  nickname)
            return

    removeFromFollowRequests(baseDir, nickname, domain, denyHandle, debug)

    # Store rejected follows
    rejectsFile = open(rejectedFollowsFilename, "a+")
    rejectsFile.write(denyHandle + '\n')
    rejectsFile.close()

    denyNickname = denyHandle.split('@')[0]
    denyDomain = \
        denyHandle.split('@')[1].replace('\n', '').replace('\r', '')
    denyPort = port
    if ':' in denyDomain:
        denyPort = denyDomain.split(':')[1]
        denyDomain = denyDomain.split(':')[0]
    followedAccountRejects(session, baseDir, httpPrefix,
                           nickname, domain, port,
                           denyNickname, denyDomain, denyPort,
                           federationList,
                           sendThreads, postLog,
                           cachedWebfingers, personCache,
                           debug, projectVersion)

    print('Follow request from ' + denyHandle + ' was denied.')


def _approveFollowerHandle(accountDir: str, approveHandle: str) -> None:
    """ Record manually approved handles so that if they unfollow and then
     re-follow later then they don't need to be manually approved again
    """
    approvedFilename = accountDir + '/approved.txt'
    if os.path.isfile(approvedFilename):
        if approveHandle not in open(approvedFilename).read():
            approvedFile = open(approvedFilename, "a+")
            approvedFile.write(approveHandle + '\n')
            approvedFile.close()
    else:
        approvedFile = open(approvedFilename, "w+")
        approvedFile.write(approveHandle + '\n')
        approvedFile.close()


def manualApproveFollowRequest(session, baseDir: str,
                               httpPrefix: str,
                               nickname: str, domain: str, port: int,
                               approveHandle: str,
                               federationList: [],
                               sendThreads: [], postLog: [],
                               cachedWebfingers: {}, personCache: {},
                               debug: bool,
                               projectVersion: str) -> None:
    """Manually approve a follow request
    """
    handle = nickname + '@' + domain
    print('Manual follow accept: ' + handle +
          ' approving follow request from ' + approveHandle)
    accountDir = baseDir + '/accounts/' + handle
    approveFollowsFilename = accountDir + '/followrequests.txt'
    if not os.path.isfile(approveFollowsFilename):
        print('Manual follow accept: follow requests file ' +
              approveFollowsFilename + ' not found')
        return

    # is the handle in the requests file?
    approveFollowsStr = ''
    with open(approveFollowsFilename, 'r') as fpFollowers:
        approveFollowsStr = fpFollowers.read()
    exists = False
    approveHandleFull = approveHandle
    if approveHandle in approveFollowsStr:
        exists = True
    elif '@' in approveHandle:
        reqNick = approveHandle.split('@')[0]
        reqDomain = approveHandle.split('@')[1].strip()
        reqPrefix = httpPrefix + '://' + reqDomain
        if reqPrefix + '/profile/' + reqNick in approveFollowsStr:
            exists = True
            approveHandleFull = reqPrefix + '/profile/' + reqNick
        elif reqPrefix + '/channel/' + reqNick in approveFollowsStr:
            exists = True
            approveHandleFull = reqPrefix + '/channel/' + reqNick
        elif reqPrefix + '/accounts/' + reqNick in approveFollowsStr:
            exists = True
            approveHandleFull = reqPrefix + '/accounts/' + reqNick
    if not exists:
        print('Manual follow accept: ' + approveHandleFull +
              ' not in requests file "' +
              approveFollowsStr.replace('\n', ' ') +
              '" ' + approveFollowsFilename)
        return

    approvefilenew = open(approveFollowsFilename + '.new', 'w+')
    updateApprovedFollowers = False
    followActivityfilename = None
    with open(approveFollowsFilename, 'r') as approvefile:
        for handleOfFollowRequester in approvefile:
            # is this the approved follow?
            if handleOfFollowRequester.startswith(approveHandleFull):
                handleOfFollowRequester = \
                    handleOfFollowRequester.replace('\n', '').replace('\r', '')
                port2 = port
                if ':' in handleOfFollowRequester:
                    port2Str = handleOfFollowRequester.split(':')[1]
                    if port2Str.isdigit():
                        port2 = int(port2Str)
                requestsDir = accountDir + '/requests'
                followActivityfilename = \
                    requestsDir + '/' + handleOfFollowRequester + '.follow'
                if os.path.isfile(followActivityfilename):
                    followJson = loadJson(followActivityfilename)
                    if followJson:
                        approveNickname = approveHandle.split('@')[0]
                        approveDomain = approveHandle.split('@')[1]
                        approveDomain = \
                            approveDomain.replace('\n', '').replace('\r', '')
                        approvePort = port2
                        if ':' in approveDomain:
                            approvePort = approveDomain.split(':')[1]
                            approveDomain = approveDomain.split(':')[0]
                        print('Manual follow accept: Sending Accept for ' +
                              handle + ' follow request from ' +
                              approveNickname + '@' + approveDomain)
                        followedAccountAccepts(session, baseDir, httpPrefix,
                                               nickname, domain, port,
                                               approveNickname, approveDomain,
                                               approvePort,
                                               followJson['actor'],
                                               federationList,
                                               followJson,
                                               sendThreads, postLog,
                                               cachedWebfingers, personCache,
                                               debug, projectVersion, False)
                updateApprovedFollowers = True
            else:
                # this isn't the approved follow so it will remain
                # in the requests file
                approvefilenew.write(handleOfFollowRequester)
    approvefilenew.close()

    followersFilename = accountDir + '/followers.txt'
    if updateApprovedFollowers:
        # update the followers
        print('Manual follow accept: updating ' + followersFilename)
        if os.path.isfile(followersFilename):
            if approveHandleFull not in open(followersFilename).read():
                try:
                    with open(followersFilename, 'r+') as followersFile:
                        content = followersFile.read()
                        if approveHandleFull + '\n' not in content:
                            followersFile.seek(0, 0)
                            followersFile.write(approveHandleFull + '\n' +
                                                content)
                except Exception as e:
                    print('WARN: Manual follow accept. ' +
                          'Failed to write entry to followers file ' + str(e))
            else:
                print('WARN: Manual follow accept: ' + approveHandleFull +
                      ' already exists in ' + followersFilename)
        else:
            print('Manual follow accept: first follower accepted for ' +
                  handle + ' is ' + approveHandleFull)
            followersFile = open(followersFilename, "w+")
            followersFile.write(approveHandleFull + '\n')
            followersFile.close()

    # only update the follow requests file if the follow is confirmed to be
    # in followers.txt
    if approveHandleFull in open(followersFilename).read():
        # mark this handle as approved for following
        _approveFollowerHandle(accountDir, approveHandle)
        # update the follow requests with the handles not yet approved
        os.rename(approveFollowsFilename + '.new', approveFollowsFilename)
        # remove the .follow file
        if followActivityfilename:
            if os.path.isfile(followActivityfilename):
                os.remove(followActivityfilename)
    else:
        os.remove(approveFollowsFilename + '.new')
