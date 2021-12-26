__filename__ = "follow.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

from pprint import pprint
import os
from utils import hasObjectStringObject
from utils import hasObjectStringType
from utils import removeDomainPort
from utils import hasUsersPath
from utils import getFullDomain
from utils import getFollowersList
from utils import validNickname
from utils import domainPermitted
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import getStatusNumber
from utils import followPerson
from posts import sendSignedJson
from posts import getPersonBox
from utils import loadJson
from utils import saveJson
from utils import isAccountDir
from utils import getUserPaths
from utils import acctDir
from utils import hasGroupType
from utils import local_actor_url
from acceptreject import createAccept
from acceptreject import createReject
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from session import getJson
from session import postJson


def createInitialLastSeen(base_dir: str, http_prefix: str) -> None:
    """Creates initial lastseen files for all follows.
    The lastseen files are used to generate the Zzz icons on
    follows/following lists on the profile screen.
    """
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not isAccountDir(acct):
                continue
            accountDir = os.path.join(base_dir + '/accounts', acct)
            followingFilename = accountDir + '/following.txt'
            if not os.path.isfile(followingFilename):
                continue
            lastSeenDir = accountDir + '/lastseen'
            if not os.path.isdir(lastSeenDir):
                os.mkdir(lastSeenDir)
            followingHandles = []
            try:
                with open(followingFilename, 'r') as fp:
                    followingHandles = fp.readlines()
            except OSError:
                print('EX: createInitialLastSeen ' + followingFilename)
            for handle in followingHandles:
                if '#' in handle:
                    continue
                if '@' not in handle:
                    continue
                handle = handle.replace('\n', '')
                nickname = handle.split('@')[0]
                domain = handle.split('@')[1]
                if nickname.startswith('!'):
                    nickname = nickname[1:]
                actor = local_actor_url(http_prefix, nickname, domain)
                lastSeenFilename = \
                    lastSeenDir + '/' + actor.replace('/', '#') + '.txt'
                if not os.path.isfile(lastSeenFilename):
                    try:
                        with open(lastSeenFilename, 'w+') as fp:
                            fp.write(str(100))
                    except OSError:
                        print('EX: createInitialLastSeen 2 ' +
                              lastSeenFilename)
        break


def _preApprovedFollower(base_dir: str,
                         nickname: str, domain: str,
                         approveHandle: str) -> bool:
    """Is the given handle an already manually approved follower?
    """
    handle = nickname + '@' + domain
    accountDir = base_dir + '/accounts/' + handle
    approvedFilename = accountDir + '/approved.txt'
    if os.path.isfile(approvedFilename):
        if approveHandle in open(approvedFilename).read():
            return True
    return False


def _removeFromFollowBase(base_dir: str,
                          nickname: str, domain: str,
                          acceptOrDenyHandle: str, followFile: str,
                          debug: bool) -> None:
    """Removes a handle/actor from follow requests or rejects file
    """
    handle = nickname + '@' + domain
    accountsDir = base_dir + '/accounts/' + handle
    approveFollowsFilename = accountsDir + '/' + followFile + '.txt'
    if not os.path.isfile(approveFollowsFilename):
        if debug:
            print('WARN: Approve follow requests file ' +
                  approveFollowsFilename + ' not found')
        return
    acceptDenyActor = None
    if acceptOrDenyHandle not in open(approveFollowsFilename).read():
        # is this stored in the file as an actor rather than a handle?
        acceptDenyNickname = acceptOrDenyHandle.split('@')[0]
        acceptDenyDomain = acceptOrDenyHandle.split('@')[1]
        # for each possible users path construct an actor and
        # check if it exists in teh file
        usersPaths = getUserPaths()
        actorFound = False
        for usersName in usersPaths:
            acceptDenyActor = \
                '://' + acceptDenyDomain + usersName + acceptDenyNickname
            if acceptDenyActor in open(approveFollowsFilename).read():
                actorFound = True
                break
        if not actorFound:
            return
    try:
        with open(approveFollowsFilename + '.new', 'w+') as approvefilenew:
            with open(approveFollowsFilename, 'r') as approvefile:
                if not acceptDenyActor:
                    for approveHandle in approvefile:
                        if not approveHandle.startswith(acceptOrDenyHandle):
                            approvefilenew.write(approveHandle)
                else:
                    for approveHandle in approvefile:
                        if acceptDenyActor not in approveHandle:
                            approvefilenew.write(approveHandle)
    except OSError as ex:
        print('EX: _removeFromFollowBase ' +
              approveFollowsFilename + ' ' + str(ex))

    os.rename(approveFollowsFilename + '.new', approveFollowsFilename)


def removeFromFollowRequests(base_dir: str,
                             nickname: str, domain: str,
                             denyHandle: str, debug: bool) -> None:
    """Removes a handle from follow requests
    """
    _removeFromFollowBase(base_dir, nickname, domain,
                          denyHandle, 'followrequests', debug)


def _removeFromFollowRejects(base_dir: str,
                             nickname: str, domain: str,
                             acceptHandle: str, debug: bool) -> None:
    """Removes a handle from follow rejects
    """
    _removeFromFollowBase(base_dir, nickname, domain,
                          acceptHandle, 'followrejects', debug)


def isFollowingActor(base_dir: str,
                     nickname: str, domain: str, actor: str) -> bool:
    """Is the given nickname following the given actor?
    The actor can also be a handle: nickname@domain
    """
    domain = removeDomainPort(domain)
    handle = nickname + '@' + domain
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        return False
    followingFile = base_dir + '/accounts/' + handle + '/following.txt'
    if not os.path.isfile(followingFile):
        return False
    if actor.lower() in open(followingFile).read().lower():
        return True
    followingNickname = getNicknameFromActor(actor)
    if not followingNickname:
        print('WARN: unable to find nickname in ' + actor)
        return False
    followingDomain, followingPort = getDomainFromActor(actor)
    followingHandle = \
        getFullDomain(followingNickname + '@' + followingDomain, followingPort)
    if followingHandle.lower() in open(followingFile).read().lower():
        return True
    return False


def getMutualsOfPerson(base_dir: str,
                       nickname: str, domain: str) -> []:
    """Returns the mutuals of a person
    i.e. accounts which they follow and which also follow back
    """
    followers = \
        getFollowersList(base_dir, nickname, domain, 'followers.txt')
    following = \
        getFollowersList(base_dir, nickname, domain, 'following.txt')
    mutuals = []
    for handle in following:
        if handle in followers:
            mutuals.append(handle)
    return mutuals


def followerOfPerson(base_dir: str, nickname: str, domain: str,
                     followerNickname: str, followerDomain: str,
                     federation_list: [], debug: bool,
                     group_account: bool) -> bool:
    """Adds a follower of the given person
    """
    return followPerson(base_dir, nickname, domain,
                        followerNickname, followerDomain,
                        federation_list, debug, group_account, 'followers.txt')


def getFollowerDomains(base_dir: str, nickname: str, domain: str) -> []:
    """Returns a list of domains for followers
    """
    domain = removeDomainPort(domain)
    followersFile = acctDir(base_dir, nickname, domain) + '/followers.txt'
    if not os.path.isfile(followersFile):
        return []

    lines = []
    try:
        with open(followersFile, 'r') as fpFollowers:
            lines = fpFollowers.readlines()
    except OSError:
        print('EX: getFollowerDomains ' + followersFile)

    domainsList = []
    for handle in lines:
        handle = handle.replace('\n', '')
        followerDomain, _ = getDomainFromActor(handle)
        if not followerDomain:
            continue
        if followerDomain not in domainsList:
            domainsList.append(followerDomain)
    return domainsList


def isFollowerOfPerson(base_dir: str, nickname: str, domain: str,
                       followerNickname: str, followerDomain: str) -> bool:
    """is the given nickname a follower of followerNickname?
    """
    if not followerDomain:
        print('No followerDomain')
        return False
    if not followerNickname:
        print('No followerNickname for ' + followerDomain)
        return False
    domain = removeDomainPort(domain)
    followersFile = acctDir(base_dir, nickname, domain) + '/followers.txt'
    if not os.path.isfile(followersFile):
        return False
    handle = followerNickname + '@' + followerDomain

    alreadyFollowing = False

    followersStr = ''
    try:
        with open(followersFile, 'r') as fpFollowers:
            followersStr = fpFollowers.read()
    except OSError:
        print('EX: isFollowerOfPerson ' + followersFile)

    if handle in followersStr:
        alreadyFollowing = True
    else:
        paths = getUserPaths()
        for userPath in paths:
            url = '://' + followerDomain + userPath + followerNickname
            if url in followersStr:
                alreadyFollowing = True
                break

    return alreadyFollowing


def unfollowAccount(base_dir: str, nickname: str, domain: str,
                    followNickname: str, followDomain: str,
                    debug: bool, group_account: bool,
                    followFile: str = 'following.txt') -> bool:
    """Removes a person to the follow list
    """
    domain = removeDomainPort(domain)
    handle = nickname + '@' + domain
    handleToUnfollow = followNickname + '@' + followDomain
    if group_account:
        handleToUnfollow = '!' + handleToUnfollow
    if not os.path.isdir(base_dir + '/accounts'):
        os.mkdir(base_dir + '/accounts')
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        os.mkdir(base_dir + '/accounts/' + handle)

    filename = base_dir + '/accounts/' + handle + '/' + followFile
    if not os.path.isfile(filename):
        if debug:
            print('DEBUG: follow file ' + filename + ' was not found')
        return False
    handleToUnfollowLower = handleToUnfollow.lower()
    if handleToUnfollowLower not in open(filename).read().lower():
        if debug:
            print('DEBUG: handle to unfollow ' + handleToUnfollow +
                  ' is not in ' + filename)
        return
    lines = []
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
    except OSError:
        print('EX: unfollowAccount ' + filename)
    if lines:
        try:
            with open(filename, 'w+') as f:
                for line in lines:
                    checkHandle = line.strip("\n").strip("\r").lower()
                    if checkHandle != handleToUnfollowLower and \
                       checkHandle != '!' + handleToUnfollowLower:
                        f.write(line)
        except OSError as ex:
            print('EX: unable to write ' + filename + ' ' + str(ex))

    # write to an unfollowed file so that if a follow accept
    # later arrives then it can be ignored
    unfollowedFilename = base_dir + '/accounts/' + handle + '/unfollowed.txt'
    if os.path.isfile(unfollowedFilename):
        if handleToUnfollowLower not in \
           open(unfollowedFilename).read().lower():
            try:
                with open(unfollowedFilename, 'a+') as f:
                    f.write(handleToUnfollow + '\n')
            except OSError:
                print('EX: unable to append ' + unfollowedFilename)
    else:
        try:
            with open(unfollowedFilename, 'w+') as f:
                f.write(handleToUnfollow + '\n')
        except OSError:
            print('EX: unable to write ' + unfollowedFilename)

    return True


def unfollowerOfAccount(base_dir: str, nickname: str, domain: str,
                        followerNickname: str, followerDomain: str,
                        debug: bool, group_account: bool) -> bool:
    """Remove a follower of a person
    """
    return unfollowAccount(base_dir, nickname, domain,
                           followerNickname, followerDomain,
                           debug, group_account, 'followers.txt')


def clearFollows(base_dir: str, nickname: str, domain: str,
                 followFile: str = 'following.txt') -> None:
    """Removes all follows
    """
    handle = nickname + '@' + domain
    if not os.path.isdir(base_dir + '/accounts'):
        os.mkdir(base_dir + '/accounts')
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        os.mkdir(base_dir + '/accounts/' + handle)
    filename = base_dir + '/accounts/' + handle + '/' + followFile
    if os.path.isfile(filename):
        try:
            os.remove(filename)
        except OSError:
            print('EX: clearFollows unable to delete ' + filename)


def clearFollowers(base_dir: str, nickname: str, domain: str) -> None:
    """Removes all followers
    """
    clearFollows(base_dir, nickname, domain, 'followers.txt')


def _getNoOfFollows(base_dir: str, nickname: str, domain: str,
                    authenticated: bool,
                    followFile='following.txt') -> int:
    """Returns the number of follows or followers
    """
    # only show number of followers to authenticated
    # account holders
    # if not authenticated:
    #     return 9999
    handle = nickname + '@' + domain
    filename = base_dir + '/accounts/' + handle + '/' + followFile
    if not os.path.isfile(filename):
        return 0
    ctr = 0
    lines = []
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
    except OSError:
        print('EX: _getNoOfFollows ' + filename)
    if lines:
        for line in lines:
            if '#' in line:
                continue
            if '@' in line and \
               '.' in line and \
               not line.startswith('http'):
                ctr += 1
            elif ((line.startswith('http') or
                   line.startswith('hyper')) and
                  hasUsersPath(line)):
                ctr += 1
    return ctr


def getNoOfFollowers(base_dir: str,
                     nickname: str, domain: str, authenticated: bool) -> int:
    """Returns the number of followers of the given person
    """
    return _getNoOfFollows(base_dir, nickname, domain,
                           authenticated, 'followers.txt')


def getFollowingFeed(base_dir: str, domain: str, port: int, path: str,
                     http_prefix: str, authorized: bool,
                     followsPerPage=12,
                     followFile='following') -> {}:
    """Returns the following and followers feeds from GET requests.
    This accesses the following.txt or followers.txt and builds a collection.
    """
    # Show a small number of follows to non-authorized viewers
    if not authorized:
        followsPerPage = 6

    if '/' + followFile not in path:
        return None
    # handle page numbers
    headerOnly = True
    pageNumber = None
    if '?page=' in path:
        pageNumber = path.split('?page=')[1]
        if pageNumber == 'true' or not authorized:
            pageNumber = 1
        else:
            try:
                pageNumber = int(pageNumber)
            except BaseException:
                print('EX: getFollowingFeed unable to convert to int ' +
                      str(pageNumber))
                pass
        path = path.split('?page=')[0]
        headerOnly = False

    if not path.endswith('/' + followFile):
        return None
    nickname = None
    if path.startswith('/users/'):
        nickname = path.replace('/users/', '', 1).replace('/' + followFile, '')
    if path.startswith('/@'):
        nickname = path.replace('/@', '', 1).replace('/' + followFile, '')
    if not nickname:
        return None
    if not validNickname(domain, nickname):
        return None

    domain = getFullDomain(domain, port)

    if headerOnly:
        firstStr = \
            local_actor_url(http_prefix, nickname, domain) + \
            '/' + followFile + '?page=1'
        idStr = \
            local_actor_url(http_prefix, nickname, domain) + '/' + followFile
        totalStr = \
            _getNoOfFollows(base_dir, nickname, domain, authorized)
        following = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': firstStr,
            'id': idStr,
            'totalItems': totalStr,
            'type': 'OrderedCollection'
        }
        return following

    if not pageNumber:
        pageNumber = 1

    nextPageNumber = int(pageNumber + 1)
    idStr = \
        local_actor_url(http_prefix, nickname, domain) + \
        '/' + followFile + '?page=' + str(pageNumber)
    partOfStr = \
        local_actor_url(http_prefix, nickname, domain) + '/' + followFile
    following = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': idStr,
        'orderedItems': [],
        'partOf': partOfStr,
        'totalItems': 0,
        'type': 'OrderedCollectionPage'
    }

    handleDomain = domain
    handleDomain = removeDomainPort(handleDomain)
    handle = nickname + '@' + handleDomain
    filename = base_dir + '/accounts/' + handle + '/' + followFile + '.txt'
    if not os.path.isfile(filename):
        return following
    currPage = 1
    pageCtr = 0
    totalCtr = 0
    lines = []
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
    except OSError:
        print('EX: getFollowingFeed ' + filename)
    for line in lines:
        if '#' not in line:
            if '@' in line and not line.startswith('http'):
                # nickname@domain
                pageCtr += 1
                totalCtr += 1
                if currPage == pageNumber:
                    line2 = \
                        line.lower().replace('\n', '').replace('\r', '')
                    nick = line2.split('@')[0]
                    dom = line2.split('@')[1]
                    if not nick.startswith('!'):
                        # person actor
                        url = local_actor_url(http_prefix, nick, dom)
                    else:
                        # group actor
                        url = http_prefix + '://' + dom + '/c/' + nick
                    following['orderedItems'].append(url)
            elif ((line.startswith('http') or
                   line.startswith('hyper')) and
                  hasUsersPath(line)):
                # https://domain/users/nickname
                pageCtr += 1
                totalCtr += 1
                if currPage == pageNumber:
                    appendStr = \
                        line.lower().replace('\n', '').replace('\r', '')
                    following['orderedItems'].append(appendStr)
        if pageCtr >= followsPerPage:
            pageCtr = 0
            currPage += 1
    following['totalItems'] = totalCtr
    lastPage = int(totalCtr / followsPerPage)
    if lastPage < 1:
        lastPage = 1
    if nextPageNumber > lastPage:
        following['next'] = \
            local_actor_url(http_prefix, nickname, domain) + \
            '/' + followFile + '?page=' + str(lastPage)
    return following


def followApprovalRequired(base_dir: str, nicknameToFollow: str,
                           domainToFollow: str, debug: bool,
                           followRequestHandle: str) -> bool:
    """ Returns the policy for follower approvals
    """
    # has this handle already been manually approved?
    if _preApprovedFollower(base_dir, nicknameToFollow, domainToFollow,
                            followRequestHandle):
        return False

    manuallyApproveFollows = False
    domainToFollow = removeDomainPort(domainToFollow)
    actorFilename = base_dir + '/accounts/' + \
        nicknameToFollow + '@' + domainToFollow + '.json'
    if os.path.isfile(actorFilename):
        actor = loadJson(actorFilename)
        if actor:
            if actor.get('manuallyApprovesFollowers'):
                manuallyApproveFollows = actor['manuallyApprovesFollowers']
            else:
                if debug:
                    print(nicknameToFollow + '@' + domainToFollow +
                          ' automatically approves followers')
    else:
        if debug:
            print('DEBUG: Actor file not found: ' + actorFilename)
    return manuallyApproveFollows


def noOfFollowRequests(base_dir: str,
                       nicknameToFollow: str, domainToFollow: str,
                       nickname: str, domain: str, fromPort: int,
                       followType: str) -> int:
    """Returns the current number of follow requests
    """
    accountsDir = base_dir + '/accounts/' + \
        nicknameToFollow + '@' + domainToFollow
    approveFollowsFilename = accountsDir + '/followrequests.txt'
    if not os.path.isfile(approveFollowsFilename):
        return 0
    ctr = 0
    lines = []
    try:
        with open(approveFollowsFilename, 'r') as f:
            lines = f.readlines()
    except OSError:
        print('EX: noOfFollowRequests ' + approveFollowsFilename)
    if lines:
        if followType == "onion":
            for fileLine in lines:
                if '.onion' in fileLine:
                    ctr += 1
        elif followType == "i2p":
            for fileLine in lines:
                if '.i2p' in fileLine:
                    ctr += 1
        else:
            return len(lines)
    return ctr


def storeFollowRequest(base_dir: str,
                       nicknameToFollow: str, domainToFollow: str, port: int,
                       nickname: str, domain: str, fromPort: int,
                       followJson: {},
                       debug: bool, personUrl: str,
                       group_account: bool) -> bool:
    """Stores the follow request for later use
    """
    accountsDir = base_dir + '/accounts/' + \
        nicknameToFollow + '@' + domainToFollow
    if not os.path.isdir(accountsDir):
        return False

    domain_full = getFullDomain(domain, fromPort)
    approveHandle = getFullDomain(nickname + '@' + domain, fromPort)

    if group_account:
        approveHandle = '!' + approveHandle

    followersFilename = accountsDir + '/followers.txt'
    if os.path.isfile(followersFilename):
        alreadyFollowing = False

        followersStr = ''
        try:
            with open(followersFilename, 'r') as fpFollowers:
                followersStr = fpFollowers.read()
        except OSError:
            print('EX: storeFollowRequest ' + followersFilename)

        if approveHandle in followersStr:
            alreadyFollowing = True
        else:
            usersPaths = getUserPaths()
            for possibleUsersPath in usersPaths:
                url = '://' + domain_full + possibleUsersPath + nickname
                if url in followersStr:
                    alreadyFollowing = True
                    break

        if alreadyFollowing:
            if debug:
                print('DEBUG: ' +
                      nicknameToFollow + '@' + domainToFollow +
                      ' already following ' + approveHandle)
            return True

    # should this follow be denied?
    denyFollowsFilename = accountsDir + '/followrejects.txt'
    if os.path.isfile(denyFollowsFilename):
        if approveHandle in open(denyFollowsFilename).read():
            removeFromFollowRequests(base_dir, nicknameToFollow,
                                     domainToFollow, approveHandle, debug)
            print(approveHandle + ' was already denied as a follower of ' +
                  nicknameToFollow)
            return True

    # add to a file which contains a list of requests
    approveFollowsFilename = accountsDir + '/followrequests.txt'

    # store either nick@domain or the full person/actor url
    approveHandleStored = approveHandle
    if '/users/' not in personUrl:
        approveHandleStored = personUrl
        if group_account:
            approveHandle = '!' + approveHandle

    if os.path.isfile(approveFollowsFilename):
        if approveHandle not in open(approveFollowsFilename).read():
            try:
                with open(approveFollowsFilename, 'a+') as fp:
                    fp.write(approveHandleStored + '\n')
            except OSError:
                print('EX: storeFollowRequest 2 ' + approveFollowsFilename)
        else:
            if debug:
                print('DEBUG: ' + approveHandleStored +
                      ' is already awaiting approval')
    else:
        try:
            with open(approveFollowsFilename, 'w+') as fp:
                fp.write(approveHandleStored + '\n')
        except OSError:
            print('EX: storeFollowRequest 3 ' + approveFollowsFilename)

    # store the follow request in its own directory
    # We don't rely upon the inbox because items in there could expire
    requestsDir = accountsDir + '/requests'
    if not os.path.isdir(requestsDir):
        os.mkdir(requestsDir)
    followActivityfilename = requestsDir + '/' + approveHandle + '.follow'
    return saveJson(followJson, followActivityfilename)


def followedAccountAccepts(session, base_dir: str, http_prefix: str,
                           nicknameToFollow: str, domainToFollow: str,
                           port: int,
                           nickname: str, domain: str, fromPort: int,
                           personUrl: str, federation_list: [],
                           followJson: {}, send_threads: [], postLog: [],
                           cached_webfingers: {}, person_cache: {},
                           debug: bool, project_version: str,
                           removeFollowActivity: bool,
                           signing_priv_key_pem: str):
    """The person receiving a follow request accepts the new follower
    and sends back an Accept activity
    """
    acceptHandle = nickname + '@' + domain

    # send accept back
    if debug:
        print('DEBUG: sending Accept activity for ' +
              'follow request which arrived at ' +
              nicknameToFollow + '@' + domainToFollow +
              ' back to ' + acceptHandle)
    acceptJson = createAccept(base_dir, federation_list,
                              nicknameToFollow, domainToFollow, port,
                              personUrl, '', http_prefix,
                              followJson)
    if debug:
        pprint(acceptJson)
        print('DEBUG: sending follow Accept from ' +
              nicknameToFollow + '@' + domainToFollow +
              ' port ' + str(port) + ' to ' +
              acceptHandle + ' port ' + str(fromPort))
    client_to_server = False

    if removeFollowActivity:
        # remove the follow request json
        followActivityfilename = \
            acctDir(base_dir, nicknameToFollow, domainToFollow) + \
            '/requests/' + \
            nickname + '@' + domain + '.follow'
        if os.path.isfile(followActivityfilename):
            try:
                os.remove(followActivityfilename)
            except OSError:
                print('EX: followedAccountAccepts unable to delete ' +
                      followActivityfilename)

    group_account = False
    if followJson:
        if followJson.get('actor'):
            if hasGroupType(base_dir, followJson['actor'], person_cache):
                group_account = True

    return sendSignedJson(acceptJson, session, base_dir,
                          nicknameToFollow, domainToFollow, port,
                          nickname, domain, fromPort, '',
                          http_prefix, True, client_to_server,
                          federation_list,
                          send_threads, postLog, cached_webfingers,
                          person_cache, debug, project_version, None,
                          group_account, signing_priv_key_pem,
                          7856837)


def followedAccountRejects(session, base_dir: str, http_prefix: str,
                           nicknameToFollow: str, domainToFollow: str,
                           port: int,
                           nickname: str, domain: str, fromPort: int,
                           federation_list: [],
                           send_threads: [], postLog: [],
                           cached_webfingers: {}, person_cache: {},
                           debug: bool, project_version: str,
                           signing_priv_key_pem: str):
    """The person receiving a follow request rejects the new follower
    and sends back a Reject activity
    """
    # send reject back
    if debug:
        print('DEBUG: sending Reject activity for ' +
              'follow request which arrived at ' +
              nicknameToFollow + '@' + domainToFollow +
              ' back to ' + nickname + '@' + domain)

    # get the json for the original follow request
    followActivityfilename = \
        acctDir(base_dir, nicknameToFollow, domainToFollow) + '/requests/' + \
        nickname + '@' + domain + '.follow'
    followJson = loadJson(followActivityfilename)
    if not followJson:
        print('No follow request json was found for ' +
              followActivityfilename)
        return None
    # actor who made the follow request
    personUrl = followJson['actor']

    # create the reject activity
    rejectJson = \
        createReject(base_dir, federation_list,
                     nicknameToFollow, domainToFollow, port,
                     personUrl, '', http_prefix, followJson)
    if debug:
        pprint(rejectJson)
        print('DEBUG: sending follow Reject from ' +
              nicknameToFollow + '@' + domainToFollow +
              ' port ' + str(port) + ' to ' +
              nickname + '@' + domain + ' port ' + str(fromPort))
    client_to_server = False
    denyHandle = getFullDomain(nickname + '@' + domain, fromPort)
    group_account = False
    if hasGroupType(base_dir, personUrl, person_cache):
        group_account = True
    # remove from the follow requests file
    removeFromFollowRequests(base_dir, nicknameToFollow, domainToFollow,
                             denyHandle, debug)
    # remove the follow request json
    try:
        os.remove(followActivityfilename)
    except OSError:
        print('EX: followedAccountRejects unable to delete ' +
              followActivityfilename)
    # send the reject activity
    return sendSignedJson(rejectJson, session, base_dir,
                          nicknameToFollow, domainToFollow, port,
                          nickname, domain, fromPort, '',
                          http_prefix, True, client_to_server,
                          federation_list,
                          send_threads, postLog, cached_webfingers,
                          person_cache, debug, project_version, None,
                          group_account, signing_priv_key_pem,
                          6393063)


def sendFollowRequest(session, base_dir: str,
                      nickname: str, domain: str, port: int, http_prefix: str,
                      followNickname: str, followDomain: str,
                      followedActor: str,
                      followPort: int, followHttpPrefix: str,
                      client_to_server: bool, federation_list: [],
                      send_threads: [], postLog: [], cached_webfingers: {},
                      person_cache: {}, debug: bool,
                      project_version: str, signing_priv_key_pem: str) -> {}:
    """Gets the json object for sending a follow request
    """
    if not signing_priv_key_pem:
        print('WARN: follow request without signing key')

    if not domainPermitted(followDomain, federation_list):
        print('You are not permitted to follow the domain ' + followDomain)
        return None

    fullDomain = getFullDomain(domain, port)
    followActor = local_actor_url(http_prefix, nickname, fullDomain)

    requestDomain = getFullDomain(followDomain, followPort)

    statusNumber, published = getStatusNumber()

    group_account = False
    if followNickname:
        followedId = followedActor
        followHandle = followNickname + '@' + requestDomain
        group_account = hasGroupType(base_dir, followedActor, person_cache)
        if group_account:
            followHandle = '!' + followHandle
            print('Follow request being sent to group account')
    else:
        if debug:
            print('DEBUG: sendFollowRequest - assuming single user instance')
        followedId = followHttpPrefix + '://' + requestDomain
        singleUserNickname = 'dev'
        followHandle = singleUserNickname + '@' + requestDomain

    # remove follow handle from unfollowed.txt
    unfollowedFilename = \
        acctDir(base_dir, nickname, domain) + '/unfollowed.txt'
    if os.path.isfile(unfollowedFilename):
        if followHandle in open(unfollowedFilename).read():
            unfollowedFile = None
            try:
                with open(unfollowedFilename, 'r') as fp:
                    unfollowedFile = fp.read()
            except OSError:
                print('EX: sendFollowRequest ' + unfollowedFilename)
            if unfollowedFile:
                unfollowedFile = \
                    unfollowedFile.replace(followHandle + '\n', '')
                try:
                    with open(unfollowedFilename, 'w+') as fp:
                        fp.write(unfollowedFile)
                except OSError:
                    print('EX: unable to write ' + unfollowedFilename)

    newFollowJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': followActor + '/statuses/' + str(statusNumber),
        'type': 'Follow',
        'actor': followActor,
        'object': followedId
    }
    if group_account:
        newFollowJson['to'] = followedId
        print('Follow request: ' + str(newFollowJson))

    if followApprovalRequired(base_dir, nickname, domain, debug,
                              followHandle):
        # Remove any follow requests rejected for the account being followed.
        # It's assumed that if you are following someone then you are
        # ok with them following back. If this isn't the case then a rejected
        # follow request will block them again.
        _removeFromFollowRejects(base_dir,
                                 nickname, domain,
                                 followHandle, debug)

    sendSignedJson(newFollowJson, session, base_dir, nickname, domain, port,
                   followNickname, followDomain, followPort,
                   'https://www.w3.org/ns/activitystreams#Public',
                   http_prefix, True, client_to_server,
                   federation_list,
                   send_threads, postLog, cached_webfingers, person_cache,
                   debug, project_version, None, group_account,
                   signing_priv_key_pem, 8234389)

    return newFollowJson


def sendFollowRequestViaServer(base_dir: str, session,
                               fromNickname: str, password: str,
                               fromDomain: str, fromPort: int,
                               followNickname: str, followDomain: str,
                               followPort: int,
                               http_prefix: str,
                               cached_webfingers: {}, person_cache: {},
                               debug: bool, project_version: str,
                               signing_priv_key_pem: str) -> {}:
    """Creates a follow request via c2s
    """
    if not session:
        print('WARN: No session for sendFollowRequestViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    followDomainFull = getFullDomain(followDomain, followPort)

    followActor = local_actor_url(http_prefix, fromNickname, fromDomainFull)
    followedId = \
        http_prefix + '://' + followDomainFull + '/@' + followNickname

    statusNumber, published = getStatusNumber()
    newFollowJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': followActor + '/statuses/' + str(statusNumber),
        'type': 'Follow',
        'actor': followActor,
        'object': followedId
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cached_webfingers,
                        fromDomain, project_version, debug, False,
                        signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: follow request webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: follow request Webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem, originDomain,
                                    base_dir, session, wfRequest, person_cache,
                                    project_version, http_prefix, fromNickname,
                                    fromDomain, postToBox, 52025)

    if not inboxUrl:
        if debug:
            print('DEBUG: follow request no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: follow request no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(http_prefix, fromDomainFull,
                 session, newFollowJson, [], inboxUrl, headers, 3, True)
    if not postResult:
        if debug:
            print('DEBUG: POST follow request failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST follow request success')

    return newFollowJson


def sendUnfollowRequestViaServer(base_dir: str, session,
                                 fromNickname: str, password: str,
                                 fromDomain: str, fromPort: int,
                                 followNickname: str, followDomain: str,
                                 followPort: int,
                                 http_prefix: str,
                                 cached_webfingers: {}, person_cache: {},
                                 debug: bool, project_version: str,
                                 signing_priv_key_pem: str) -> {}:
    """Creates a unfollow request via c2s
    """
    if not session:
        print('WARN: No session for sendUnfollowRequestViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)
    followDomainFull = getFullDomain(followDomain, followPort)

    followActor = local_actor_url(http_prefix, fromNickname, fromDomainFull)
    followedId = \
        http_prefix + '://' + followDomainFull + '/@' + followNickname
    statusNumber, published = getStatusNumber()

    unfollowJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': followActor + '/statuses/' + str(statusNumber) + '/undo',
        'type': 'Undo',
        'actor': followActor,
        'object': {
            'id': followActor + '/statuses/' + str(statusNumber),
            'type': 'Follow',
            'actor': followActor,
            'object': followedId
        }
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cached_webfingers,
                        fromDomain, project_version, debug, False,
                        signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: unfollow webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: unfollow webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session,
                                    wfRequest, person_cache,
                                    project_version, http_prefix,
                                    fromNickname,
                                    fromDomain, postToBox,
                                    76536)

    if not inboxUrl:
        if debug:
            print('DEBUG: unfollow no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: unfollow no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(http_prefix, fromDomainFull,
                 session, unfollowJson, [], inboxUrl, headers, 3, True)
    if not postResult:
        if debug:
            print('DEBUG: POST unfollow failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST unfollow success')

    return unfollowJson


def getFollowingViaServer(base_dir: str, session,
                          nickname: str, password: str,
                          domain: str, port: int,
                          http_prefix: str, pageNumber: int,
                          cached_webfingers: {}, person_cache: {},
                          debug: bool, project_version: str,
                          signing_priv_key_pem: str) -> {}:
    """Gets a page from the following collection as json
    """
    if not session:
        print('WARN: No session for getFollowingViaServer')
        return 6

    domain_full = getFullDomain(domain, port)
    followActor = local_actor_url(http_prefix, nickname, domain_full)

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }

    if pageNumber < 1:
        pageNumber = 1
    url = followActor + '/following?page=' + str(pageNumber)
    followingJson = \
        getJson(signing_priv_key_pem, session, url, headers, {}, debug,
                __version__, http_prefix, domain, 10, True)
    if not followingJson:
        if debug:
            print('DEBUG: GET following list failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET following list request success')

    return followingJson


def getFollowersViaServer(base_dir: str, session,
                          nickname: str, password: str,
                          domain: str, port: int,
                          http_prefix: str, pageNumber: int,
                          cached_webfingers: {}, person_cache: {},
                          debug: bool, project_version: str,
                          signing_priv_key_pem: str) -> {}:
    """Gets a page from the followers collection as json
    """
    if not session:
        print('WARN: No session for getFollowersViaServer')
        return 6

    domain_full = getFullDomain(domain, port)
    followActor = local_actor_url(http_prefix, nickname, domain_full)

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }

    if pageNumber < 1:
        pageNumber = 1
    url = followActor + '/followers?page=' + str(pageNumber)
    followersJson = \
        getJson(signing_priv_key_pem, session, url, headers, {}, debug,
                __version__, http_prefix, domain, 10, True)
    if not followersJson:
        if debug:
            print('DEBUG: GET followers list failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET followers list request success')

    return followersJson


def getFollowRequestsViaServer(base_dir: str, session,
                               nickname: str, password: str,
                               domain: str, port: int,
                               http_prefix: str, pageNumber: int,
                               cached_webfingers: {}, person_cache: {},
                               debug: bool, project_version: str,
                               signing_priv_key_pem: str) -> {}:
    """Gets a page from the follow requests collection as json
    """
    if not session:
        print('WARN: No session for getFollowRequestsViaServer')
        return 6

    domain_full = getFullDomain(domain, port)

    followActor = local_actor_url(http_prefix, nickname, domain_full)
    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }

    if pageNumber < 1:
        pageNumber = 1
    url = followActor + '/followrequests?page=' + str(pageNumber)
    followersJson = \
        getJson(signing_priv_key_pem, session, url, headers, {}, debug,
                __version__, http_prefix, domain, 10, True)
    if not followersJson:
        if debug:
            print('DEBUG: GET follow requests list failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET follow requests list request success')

    return followersJson


def approveFollowRequestViaServer(base_dir: str, session,
                                  nickname: str, password: str,
                                  domain: str, port: int,
                                  http_prefix: str, approveHandle: int,
                                  cached_webfingers: {}, person_cache: {},
                                  debug: bool, project_version: str,
                                  signing_priv_key_pem: str) -> str:
    """Approves a follow request
    This is not exactly via c2s though. It simulates pressing the Approve
    button on the web interface
    """
    if not session:
        print('WARN: No session for approveFollowRequestViaServer')
        return 6

    domain_full = getFullDomain(domain, port)
    actor = local_actor_url(http_prefix, nickname, domain_full)

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'text/html; charset=utf-8',
        'Authorization': authHeader
    }

    url = actor + '/followapprove=' + approveHandle
    approveHtml = \
        getJson(signing_priv_key_pem, session, url, headers, {}, debug,
                __version__, http_prefix, domain, 10, True)
    if not approveHtml:
        if debug:
            print('DEBUG: GET approve follow request failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET approve follow request request success')

    return approveHtml


def denyFollowRequestViaServer(base_dir: str, session,
                               nickname: str, password: str,
                               domain: str, port: int,
                               http_prefix: str, denyHandle: int,
                               cached_webfingers: {}, person_cache: {},
                               debug: bool, project_version: str,
                               signing_priv_key_pem: str) -> str:
    """Denies a follow request
    This is not exactly via c2s though. It simulates pressing the Deny
    button on the web interface
    """
    if not session:
        print('WARN: No session for denyFollowRequestViaServer')
        return 6

    domain_full = getFullDomain(domain, port)
    actor = local_actor_url(http_prefix, nickname, domain_full)

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'text/html; charset=utf-8',
        'Authorization': authHeader
    }

    url = actor + '/followdeny=' + denyHandle
    denyHtml = \
        getJson(signing_priv_key_pem, session, url, headers, {}, debug,
                __version__, http_prefix, domain, 10, True)
    if not denyHtml:
        if debug:
            print('DEBUG: GET deny follow request failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET deny follow request request success')

    return denyHtml


def getFollowersOfActor(base_dir: str, actor: str, debug: bool) -> {}:
    """In a shared inbox if we receive a post we know who it's from
    and if it's addressed to followers then we need to get a list of those.
    This returns a list of account handles which follow the given actor
    """
    if debug:
        print('DEBUG: getting followers of ' + actor)
    recipientsDict = {}
    if ':' not in actor:
        return recipientsDict
    nickname = getNicknameFromActor(actor)
    if not nickname:
        if debug:
            print('DEBUG: no nickname found in ' + actor)
        return recipientsDict
    domain, port = getDomainFromActor(actor)
    if not domain:
        if debug:
            print('DEBUG: no domain found in ' + actor)
        return recipientsDict
    actorHandle = nickname + '@' + domain
    if debug:
        print('DEBUG: searching for handle ' + actorHandle)
    # for each of the accounts
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for account in dirs:
            if '@' in account and not account.startswith('inbox@'):
                followingFilename = \
                    os.path.join(subdir, account) + '/following.txt'
                if debug:
                    print('DEBUG: examining follows of ' + account)
                    print(followingFilename)
                if os.path.isfile(followingFilename):
                    # does this account follow the given actor?
                    if debug:
                        print('DEBUG: checking if ' + actorHandle +
                              ' in ' + followingFilename)
                    if actorHandle in open(followingFilename).read():
                        if debug:
                            print('DEBUG: ' + account +
                                  ' follows ' + actorHandle)
                        recipientsDict[account] = None
        break
    return recipientsDict


def outboxUndoFollow(base_dir: str, message_json: {}, debug: bool) -> None:
    """When an unfollow request is received by the outbox from c2s
    This removes the followed handle from the following.txt file
    of the relevant account
    """
    if not message_json.get('type'):
        return
    if not message_json['type'] == 'Undo':
        return
    if not hasObjectStringType(message_json, debug):
        return
    if not message_json['object']['type'] == 'Follow':
        if not message_json['object']['type'] == 'Join':
            return
    if not hasObjectStringObject(message_json, debug):
        return
    if not message_json['object'].get('actor'):
        return
    if debug:
        print('DEBUG: undo follow arrived in outbox')

    nicknameFollower = getNicknameFromActor(message_json['object']['actor'])
    if not nicknameFollower:
        print('WARN: unable to find nickname in ' +
              message_json['object']['actor'])
        return
    domainFollower, portFollower = \
        getDomainFromActor(message_json['object']['actor'])
    domainFollowerFull = getFullDomain(domainFollower, portFollower)

    nicknameFollowing = getNicknameFromActor(message_json['object']['object'])
    if not nicknameFollowing:
        print('WARN: unable to find nickname in ' +
              message_json['object']['object'])
        return
    domainFollowing, portFollowing = \
        getDomainFromActor(message_json['object']['object'])
    domainFollowingFull = getFullDomain(domainFollowing, portFollowing)

    group_account = \
        hasGroupType(base_dir, message_json['object']['object'], None)
    if unfollowAccount(base_dir, nicknameFollower, domainFollowerFull,
                       nicknameFollowing, domainFollowingFull,
                       debug, group_account):
        if debug:
            print('DEBUG: ' + nicknameFollower + ' unfollowed ' +
                  nicknameFollowing + '@' + domainFollowingFull)
    else:
        if debug:
            print('WARN: ' + nicknameFollower + ' could not unfollow ' +
                  nicknameFollowing + '@' + domainFollowingFull)


def followerApprovalActive(base_dir: str, nickname: str, domain: str) -> bool:
    """Returns true if the given account requires follower approval
    """
    manuallyApprovesFollowers = False
    actorFilename = acctDir(base_dir, nickname, domain) + '.json'
    if os.path.isfile(actorFilename):
        actor_json = loadJson(actorFilename)
        if actor_json:
            if actor_json.get('manuallyApprovesFollowers'):
                manuallyApprovesFollowers = \
                    actor_json['manuallyApprovesFollowers']
    return manuallyApprovesFollowers
