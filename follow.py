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
from utils import removeDomainPort
from utils import hasObjectDict
from utils import hasUsersPath
from utils import getFullDomain
from utils import isSystemAccount
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
from utils import isGroupAccount
from utils import localActorUrl
from acceptreject import createAccept
from acceptreject import createReject
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from session import getJson
from session import postJson
from cache import getPersonPubKey


def createInitialLastSeen(baseDir: str, httpPrefix: str) -> None:
    """Creates initial lastseen files for all follows.
    The lastseen files are used to generate the Zzz icons on
    follows/following lists on the profile screen.
    """
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for acct in dirs:
            if not isAccountDir(acct):
                continue
            accountDir = os.path.join(baseDir + '/accounts', acct)
            followingFilename = accountDir + '/following.txt'
            if not os.path.isfile(followingFilename):
                continue
            lastSeenDir = accountDir + '/lastseen'
            if not os.path.isdir(lastSeenDir):
                os.mkdir(lastSeenDir)
            with open(followingFilename, 'r') as fp:
                followingHandles = fp.readlines()
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
                    actor = localActorUrl(httpPrefix, nickname, domain)
                    lastSeenFilename = \
                        lastSeenDir + '/' + actor.replace('/', '#') + '.txt'
                    if not os.path.isfile(lastSeenFilename):
                        with open(lastSeenFilename, 'w+') as fp:
                            fp.write(str(100))
        break


def _preApprovedFollower(baseDir: str,
                         nickname: str, domain: str,
                         approveHandle: str) -> bool:
    """Is the given handle an already manually approved follower?
    """
    handle = nickname + '@' + domain
    accountDir = baseDir + '/accounts/' + handle
    approvedFilename = accountDir + '/approved.txt'
    if os.path.isfile(approvedFilename):
        if approveHandle in open(approvedFilename).read():
            return True
    return False


def _removeFromFollowBase(baseDir: str,
                          nickname: str, domain: str,
                          acceptOrDenyHandle: str, followFile: str,
                          debug: bool) -> None:
    """Removes a handle/actor from follow requests or rejects file
    """
    handle = nickname + '@' + domain
    accountsDir = baseDir + '/accounts/' + handle
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

    os.rename(approveFollowsFilename + '.new', approveFollowsFilename)


def removeFromFollowRequests(baseDir: str,
                             nickname: str, domain: str,
                             denyHandle: str, debug: bool) -> None:
    """Removes a handle from follow requests
    """
    _removeFromFollowBase(baseDir, nickname, domain,
                          denyHandle, 'followrequests', debug)


def _removeFromFollowRejects(baseDir: str,
                             nickname: str, domain: str,
                             acceptHandle: str, debug: bool) -> None:
    """Removes a handle from follow rejects
    """
    _removeFromFollowBase(baseDir, nickname, domain,
                          acceptHandle, 'followrejects', debug)


def isFollowingActor(baseDir: str,
                     nickname: str, domain: str, actor: str) -> bool:
    """Is the given nickname following the given actor?
    The actor can also be a handle: nickname@domain
    """
    domain = removeDomainPort(domain)
    handle = nickname + '@' + domain
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        return False
    followingFile = baseDir + '/accounts/' + handle + '/following.txt'
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


def getMutualsOfPerson(baseDir: str,
                       nickname: str, domain: str) -> []:
    """Returns the mutuals of a person
    i.e. accounts which they follow and which also follow back
    """
    followers = \
        getFollowersList(baseDir, nickname, domain, 'followers.txt')
    following = \
        getFollowersList(baseDir, nickname, domain, 'following.txt')
    mutuals = []
    for handle in following:
        if handle in followers:
            mutuals.append(handle)
    return mutuals


def followerOfPerson(baseDir: str, nickname: str, domain: str,
                     followerNickname: str, followerDomain: str,
                     federationList: [], debug: bool,
                     groupAccount: bool) -> bool:
    """Adds a follower of the given person
    """
    return followPerson(baseDir, nickname, domain,
                        followerNickname, followerDomain,
                        federationList, debug, groupAccount, 'followers.txt')


def isFollowerOfPerson(baseDir: str, nickname: str, domain: str,
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
    followersFile = acctDir(baseDir, nickname, domain) + '/followers.txt'
    if not os.path.isfile(followersFile):
        return False
    handle = followerNickname + '@' + followerDomain

    alreadyFollowing = False

    followersStr = ''
    with open(followersFile, 'r') as fpFollowers:
        followersStr = fpFollowers.read()

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


def unfollowAccount(baseDir: str, nickname: str, domain: str,
                    followNickname: str, followDomain: str,
                    debug: bool, groupAccount: bool,
                    followFile: str = 'following.txt') -> bool:
    """Removes a person to the follow list
    """
    domain = removeDomainPort(domain)
    handle = nickname + '@' + domain
    handleToUnfollow = followNickname + '@' + followDomain
    if groupAccount:
        handleToUnfollow = '!' + handleToUnfollow
    if not os.path.isdir(baseDir + '/accounts'):
        os.mkdir(baseDir + '/accounts')
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        os.mkdir(baseDir + '/accounts/' + handle)

    filename = baseDir + '/accounts/' + handle + '/' + followFile
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
    with open(filename, 'r') as f:
        lines = f.readlines()
        with open(filename, 'w+') as f:
            for line in lines:
                checkHandle = line.strip("\n").strip("\r").lower()
                if checkHandle != handleToUnfollowLower and \
                   checkHandle != '!' + handleToUnfollowLower:
                    f.write(line)

    # write to an unfollowed file so that if a follow accept
    # later arrives then it can be ignored
    unfollowedFilename = baseDir + '/accounts/' + handle + '/unfollowed.txt'
    if os.path.isfile(unfollowedFilename):
        if handleToUnfollowLower not in \
           open(unfollowedFilename).read().lower():
            with open(unfollowedFilename, 'a+') as f:
                f.write(handleToUnfollow + '\n')
    else:
        with open(unfollowedFilename, 'w+') as f:
            f.write(handleToUnfollow + '\n')

    return True


def unfollowerOfAccount(baseDir: str, nickname: str, domain: str,
                        followerNickname: str, followerDomain: str,
                        debug: bool, groupAccount: bool) -> bool:
    """Remove a follower of a person
    """
    return unfollowAccount(baseDir, nickname, domain,
                           followerNickname, followerDomain,
                           debug, groupAccount, 'followers.txt')


def clearFollows(baseDir: str, nickname: str, domain: str,
                 followFile: str = 'following.txt') -> None:
    """Removes all follows
    """
    handle = nickname + '@' + domain
    if not os.path.isdir(baseDir + '/accounts'):
        os.mkdir(baseDir + '/accounts')
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        os.mkdir(baseDir + '/accounts/' + handle)
    filename = baseDir + '/accounts/' + handle + '/' + followFile
    if os.path.isfile(filename):
        try:
            os.remove(filename)
        except BaseException:
            pass


def clearFollowers(baseDir: str, nickname: str, domain: str) -> None:
    """Removes all followers
    """
    clearFollows(baseDir, nickname, domain, 'followers.txt')


def _getNoOfFollows(baseDir: str, nickname: str, domain: str,
                    authenticated: bool,
                    followFile='following.txt') -> int:
    """Returns the number of follows or followers
    """
    # only show number of followers to authenticated
    # account holders
    # if not authenticated:
    #     return 9999
    handle = nickname + '@' + domain
    filename = baseDir + '/accounts/' + handle + '/' + followFile
    if not os.path.isfile(filename):
        return 0
    ctr = 0
    with open(filename, 'r') as f:
        lines = f.readlines()
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


def _getNoOfFollowers(baseDir: str,
                      nickname: str, domain: str, authenticated: bool) -> int:
    """Returns the number of followers of the given person
    """
    return _getNoOfFollows(baseDir, nickname, domain,
                           authenticated, 'followers.txt')


def getFollowingFeed(baseDir: str, domain: str, port: int, path: str,
                     httpPrefix: str, authorized: bool,
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
            localActorUrl(httpPrefix, nickname, domain) + \
            '/' + followFile + '?page=1'
        idStr = \
            localActorUrl(httpPrefix, nickname, domain) + '/' + followFile
        totalStr = \
            _getNoOfFollows(baseDir, nickname, domain, authorized)
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
        localActorUrl(httpPrefix, nickname, domain) + \
        '/' + followFile + '?page=' + str(pageNumber)
    partOfStr = \
        localActorUrl(httpPrefix, nickname, domain) + '/' + followFile
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
    filename = baseDir + '/accounts/' + handle + '/' + followFile + '.txt'
    if not os.path.isfile(filename):
        return following
    currPage = 1
    pageCtr = 0
    totalCtr = 0
    with open(filename, 'r') as f:
        lines = f.readlines()
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
                            url = localActorUrl(httpPrefix, nick, dom)
                        else:
                            # group actor
                            url = httpPrefix + '://' + dom + '/c/' + nick
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
            localActorUrl(httpPrefix, nickname, domain) + \
            '/' + followFile + '?page=' + str(lastPage)
    return following


def _followApprovalRequired(baseDir: str, nicknameToFollow: str,
                            domainToFollow: str, debug: bool,
                            followRequestHandle: str) -> bool:
    """ Returns the policy for follower approvals
    """
    # has this handle already been manually approved?
    if _preApprovedFollower(baseDir, nicknameToFollow, domainToFollow,
                            followRequestHandle):
        return False

    manuallyApproveFollows = False
    domainToFollow = removeDomainPort(domainToFollow)
    actorFilename = baseDir + '/accounts/' + \
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


def _noOfFollowRequests(baseDir: str,
                        nicknameToFollow: str, domainToFollow: str,
                        nickname: str, domain: str, fromPort: int,
                        followType: str) -> int:
    """Returns the current number of follow requests
    """
    accountsDir = baseDir + '/accounts/' + \
        nicknameToFollow + '@' + domainToFollow
    approveFollowsFilename = accountsDir + '/followrequests.txt'
    if not os.path.isfile(approveFollowsFilename):
        return 0
    ctr = 0
    with open(approveFollowsFilename, 'r') as f:
        lines = f.readlines()
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


def _storeFollowRequest(baseDir: str,
                        nicknameToFollow: str, domainToFollow: str, port: int,
                        nickname: str, domain: str, fromPort: int,
                        followJson: {},
                        debug: bool, personUrl: str,
                        groupAccount: bool) -> bool:
    """Stores the follow request for later use
    """
    accountsDir = baseDir + '/accounts/' + \
        nicknameToFollow + '@' + domainToFollow
    if not os.path.isdir(accountsDir):
        return False

    domainFull = getFullDomain(domain, fromPort)
    approveHandle = getFullDomain(nickname + '@' + domain, fromPort)

    if groupAccount:
        approveHandle = '!' + approveHandle

    followersFilename = accountsDir + '/followers.txt'
    if os.path.isfile(followersFilename):
        alreadyFollowing = False

        followersStr = ''
        with open(followersFilename, 'r') as fpFollowers:
            followersStr = fpFollowers.read()

        if approveHandle in followersStr:
            alreadyFollowing = True
        else:
            usersPaths = getUserPaths()
            for possibleUsersPath in usersPaths:
                url = '://' + domainFull + possibleUsersPath + nickname
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
            removeFromFollowRequests(baseDir, nicknameToFollow,
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
        if groupAccount:
            approveHandle = '!' + approveHandle

    if os.path.isfile(approveFollowsFilename):
        if approveHandle not in open(approveFollowsFilename).read():
            with open(approveFollowsFilename, 'a+') as fp:
                fp.write(approveHandleStored + '\n')
        else:
            if debug:
                print('DEBUG: ' + approveHandleStored +
                      ' is already awaiting approval')
    else:
        with open(approveFollowsFilename, 'w+') as fp:
            fp.write(approveHandleStored + '\n')

    # store the follow request in its own directory
    # We don't rely upon the inbox because items in there could expire
    requestsDir = accountsDir + '/requests'
    if not os.path.isdir(requestsDir):
        os.mkdir(requestsDir)
    followActivityfilename = requestsDir + '/' + approveHandle + '.follow'
    return saveJson(followJson, followActivityfilename)


def receiveFollowRequest(session, baseDir: str, httpPrefix: str,
                         port: int, sendThreads: [], postLog: [],
                         cachedWebfingers: {}, personCache: {},
                         messageJson: {}, federationList: [],
                         debug: bool, projectVersion: str,
                         maxFollowers: int, onionDomain: str,
                         signingPrivateKeyPem: str) -> bool:
    """Receives a follow request within the POST section of HTTPServer
    """
    if not messageJson['type'].startswith('Follow'):
        if not messageJson['type'].startswith('Join'):
            return False
    print('Receiving follow request')
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: follow request has no actor')
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: users/profile/accounts/channel missing from actor')
        return False
    domain, tempPort = getDomainFromActor(messageJson['actor'])
    fromPort = port
    domainFull = getFullDomain(domain, tempPort)
    if tempPort:
        fromPort = tempPort
    if not domainPermitted(domain, federationList):
        if debug:
            print('DEBUG: follower from domain not permitted - ' + domain)
        return False
    nickname = getNicknameFromActor(messageJson['actor'])
    if not nickname:
        # single user instance
        nickname = 'dev'
        if debug:
            print('DEBUG: follow request does not contain a ' +
                  'nickname. Assuming single user instance.')
    if not messageJson.get('to'):
        messageJson['to'] = messageJson['object']
    if not hasUsersPath(messageJson['object']):
        if debug:
            print('DEBUG: users/profile/channel/accounts ' +
                  'not found within object')
        return False
    domainToFollow, tempPort = getDomainFromActor(messageJson['object'])
    if not domainPermitted(domainToFollow, federationList):
        if debug:
            print('DEBUG: follow domain not permitted ' + domainToFollow)
        return True
    domainToFollowFull = getFullDomain(domainToFollow, tempPort)
    nicknameToFollow = getNicknameFromActor(messageJson['object'])
    if not nicknameToFollow:
        if debug:
            print('DEBUG: follow request does not contain a ' +
                  'nickname for the account followed')
        return True
    if isSystemAccount(nicknameToFollow):
        if debug:
            print('DEBUG: Cannot follow system account - ' +
                  nicknameToFollow)
        return True
    if maxFollowers > 0:
        if _getNoOfFollowers(baseDir,
                             nicknameToFollow, domainToFollow,
                             True) > maxFollowers:
            print('WARN: ' + nicknameToFollow +
                  ' has reached their maximum number of followers')
            return True
    handleToFollow = nicknameToFollow + '@' + domainToFollow
    if domainToFollow == domain:
        if not os.path.isdir(baseDir + '/accounts/' + handleToFollow):
            if debug:
                print('DEBUG: followed account not found - ' +
                      baseDir + '/accounts/' + handleToFollow)
            return True

    if isFollowerOfPerson(baseDir,
                          nicknameToFollow, domainToFollowFull,
                          nickname, domainFull):
        if debug:
            print('DEBUG: ' + nickname + '@' + domain +
                  ' is already a follower of ' +
                  nicknameToFollow + '@' + domainToFollow)
        return True

    # what is the followers policy?
    approveHandle = nickname + '@' + domainFull
    if _followApprovalRequired(baseDir, nicknameToFollow,
                               domainToFollow, debug, approveHandle):
        print('Follow approval is required')
        if domain.endswith('.onion'):
            if _noOfFollowRequests(baseDir,
                                   nicknameToFollow, domainToFollow,
                                   nickname, domain, fromPort,
                                   'onion') > 5:
                print('Too many follow requests from onion addresses')
                return False
        elif domain.endswith('.i2p'):
            if _noOfFollowRequests(baseDir,
                                   nicknameToFollow, domainToFollow,
                                   nickname, domain, fromPort,
                                   'i2p') > 5:
                print('Too many follow requests from i2p addresses')
                return False
        else:
            if _noOfFollowRequests(baseDir,
                                   nicknameToFollow, domainToFollow,
                                   nickname, domain, fromPort,
                                   '') > 10:
                print('Too many follow requests')
                return False

        # Get the actor for the follower and add it to the cache.
        # Getting their public key has the same result
        if debug:
            print('Obtaining the following actor: ' + messageJson['actor'])
        if not getPersonPubKey(baseDir, session, messageJson['actor'],
                               personCache, debug, projectVersion,
                               httpPrefix, domainToFollow, onionDomain,
                               signingPrivateKeyPem):
            if debug:
                print('Unable to obtain following actor: ' +
                      messageJson['actor'])

        groupAccount = \
            hasGroupType(baseDir, messageJson['actor'], personCache)
        if groupAccount and isGroupAccount(baseDir, nickname, domain):
            print('Group cannot follow a group')
            return False

        print('Storing follow request for approval')
        return _storeFollowRequest(baseDir,
                                   nicknameToFollow, domainToFollow, port,
                                   nickname, domain, fromPort,
                                   messageJson, debug, messageJson['actor'],
                                   groupAccount)
    else:
        print('Follow request does not require approval ' + approveHandle)
        # update the followers
        accountToBeFollowed = \
            acctDir(baseDir, nicknameToFollow, domainToFollow)
        if os.path.isdir(accountToBeFollowed):
            followersFilename = accountToBeFollowed + '/followers.txt'

            # for actors which don't follow the mastodon
            # /users/ path convention store the full actor
            if '/users/' not in messageJson['actor']:
                approveHandle = messageJson['actor']

            # Get the actor for the follower and add it to the cache.
            # Getting their public key has the same result
            if debug:
                print('Obtaining the following actor: ' + messageJson['actor'])
            if not getPersonPubKey(baseDir, session, messageJson['actor'],
                                   personCache, debug, projectVersion,
                                   httpPrefix, domainToFollow, onionDomain,
                                   signingPrivateKeyPem):
                if debug:
                    print('Unable to obtain following actor: ' +
                          messageJson['actor'])

            print('Updating followers file: ' +
                  followersFilename + ' adding ' + approveHandle)
            if os.path.isfile(followersFilename):
                if approveHandle not in open(followersFilename).read():
                    groupAccount = \
                        hasGroupType(baseDir,
                                     messageJson['actor'], personCache)
                    if debug:
                        print(approveHandle + ' / ' + messageJson['actor'] +
                              ' is Group: ' + str(groupAccount))
                    if groupAccount and \
                       isGroupAccount(baseDir, nickname, domain):
                        print('Group cannot follow a group')
                        return False
                    try:
                        with open(followersFilename, 'r+') as followersFile:
                            content = followersFile.read()
                            if approveHandle + '\n' not in content:
                                followersFile.seek(0, 0)
                                if not groupAccount:
                                    followersFile.write(approveHandle +
                                                        '\n' + content)
                                else:
                                    followersFile.write('!' + approveHandle +
                                                        '\n' + content)
                    except Exception as e:
                        print('WARN: ' +
                              'Failed to write entry to followers file ' +
                              str(e))
            else:
                with open(followersFilename, 'w+') as followersFile:
                    followersFile.write(approveHandle + '\n')

    print('Beginning follow accept')
    return followedAccountAccepts(session, baseDir, httpPrefix,
                                  nicknameToFollow, domainToFollow, port,
                                  nickname, domain, fromPort,
                                  messageJson['actor'], federationList,
                                  messageJson, sendThreads, postLog,
                                  cachedWebfingers, personCache,
                                  debug, projectVersion, True,
                                  signingPrivateKeyPem)


def followedAccountAccepts(session, baseDir: str, httpPrefix: str,
                           nicknameToFollow: str, domainToFollow: str,
                           port: int,
                           nickname: str, domain: str, fromPort: int,
                           personUrl: str, federationList: [],
                           followJson: {}, sendThreads: [], postLog: [],
                           cachedWebfingers: {}, personCache: {},
                           debug: bool, projectVersion: str,
                           removeFollowActivity: bool,
                           signingPrivateKeyPem: str):
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
    acceptJson = createAccept(baseDir, federationList,
                              nicknameToFollow, domainToFollow, port,
                              personUrl, '', httpPrefix,
                              followJson)
    if debug:
        pprint(acceptJson)
        print('DEBUG: sending follow Accept from ' +
              nicknameToFollow + '@' + domainToFollow +
              ' port ' + str(port) + ' to ' +
              acceptHandle + ' port ' + str(fromPort))
    clientToServer = False

    if removeFollowActivity:
        # remove the follow request json
        followActivityfilename = \
            acctDir(baseDir, nicknameToFollow, domainToFollow) + \
            '/requests/' + \
            nickname + '@' + domain + '.follow'
        if os.path.isfile(followActivityfilename):
            try:
                os.remove(followActivityfilename)
            except BaseException:
                pass

    groupAccount = False
    if followJson:
        if followJson.get('actor'):
            if hasGroupType(baseDir, followJson['actor'], personCache):
                groupAccount = True

    return sendSignedJson(acceptJson, session, baseDir,
                          nicknameToFollow, domainToFollow, port,
                          nickname, domain, fromPort, '',
                          httpPrefix, True, clientToServer,
                          federationList,
                          sendThreads, postLog, cachedWebfingers,
                          personCache, debug, projectVersion, None,
                          groupAccount, signingPrivateKeyPem,
                          7856837)


def followedAccountRejects(session, baseDir: str, httpPrefix: str,
                           nicknameToFollow: str, domainToFollow: str,
                           port: int,
                           nickname: str, domain: str, fromPort: int,
                           federationList: [],
                           sendThreads: [], postLog: [],
                           cachedWebfingers: {}, personCache: {},
                           debug: bool, projectVersion: str,
                           signingPrivateKeyPem: str):
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
        acctDir(baseDir, nicknameToFollow, domainToFollow) + '/requests/' + \
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
        createReject(baseDir, federationList,
                     nicknameToFollow, domainToFollow, port,
                     personUrl, '', httpPrefix, followJson)
    if debug:
        pprint(rejectJson)
        print('DEBUG: sending follow Reject from ' +
              nicknameToFollow + '@' + domainToFollow +
              ' port ' + str(port) + ' to ' +
              nickname + '@' + domain + ' port ' + str(fromPort))
    clientToServer = False
    denyHandle = getFullDomain(nickname + '@' + domain, fromPort)
    groupAccount = False
    if hasGroupType(baseDir, personUrl, personCache):
        groupAccount = True
    # remove from the follow requests file
    removeFromFollowRequests(baseDir, nicknameToFollow, domainToFollow,
                             denyHandle, debug)
    # remove the follow request json
    try:
        os.remove(followActivityfilename)
    except BaseException:
        pass
    # send the reject activity
    return sendSignedJson(rejectJson, session, baseDir,
                          nicknameToFollow, domainToFollow, port,
                          nickname, domain, fromPort, '',
                          httpPrefix, True, clientToServer,
                          federationList,
                          sendThreads, postLog, cachedWebfingers,
                          personCache, debug, projectVersion, None,
                          groupAccount, signingPrivateKeyPem,
                          6393063)


def sendFollowRequest(session, baseDir: str,
                      nickname: str, domain: str, port: int, httpPrefix: str,
                      followNickname: str, followDomain: str,
                      followedActor: str,
                      followPort: int, followHttpPrefix: str,
                      clientToServer: bool, federationList: [],
                      sendThreads: [], postLog: [], cachedWebfingers: {},
                      personCache: {}, debug: bool,
                      projectVersion: str, signingPrivateKeyPem: str) -> {}:
    """Gets the json object for sending a follow request
    """
    if not signingPrivateKeyPem:
        print('WARN: follow request without signing key')

    if not domainPermitted(followDomain, federationList):
        print('You are not permitted to follow the domain ' + followDomain)
        return None

    fullDomain = getFullDomain(domain, port)
    followActor = localActorUrl(httpPrefix, nickname, fullDomain)

    requestDomain = getFullDomain(followDomain, followPort)

    statusNumber, published = getStatusNumber()

    groupAccount = False
    if followNickname:
        followedId = followedActor
        followHandle = followNickname + '@' + requestDomain
        groupAccount = hasGroupType(baseDir, followedActor, personCache)
        if groupAccount:
            followHandle = '!' + followHandle
            print('Follow request being sent to group account')
    else:
        if debug:
            print('DEBUG: sendFollowRequest - assuming single user instance')
        followedId = followHttpPrefix + '://' + requestDomain
        singleUserNickname = 'dev'
        followHandle = singleUserNickname + '@' + requestDomain

    newFollowJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': followActor + '/statuses/' + str(statusNumber),
        'type': 'Follow',
        'actor': followActor,
        'object': followedId
    }
    if groupAccount:
        newFollowJson['to'] = followedId
        print('Follow request: ' + str(newFollowJson))

    if _followApprovalRequired(baseDir, nickname, domain, debug,
                               followHandle):
        # Remove any follow requests rejected for the account being followed.
        # It's assumed that if you are following someone then you are
        # ok with them following back. If this isn't the case then a rejected
        # follow request will block them again.
        _removeFromFollowRejects(baseDir,
                                 nickname, domain,
                                 followHandle, debug)

    sendSignedJson(newFollowJson, session, baseDir, nickname, domain, port,
                   followNickname, followDomain, followPort,
                   'https://www.w3.org/ns/activitystreams#Public',
                   httpPrefix, True, clientToServer,
                   federationList,
                   sendThreads, postLog, cachedWebfingers, personCache,
                   debug, projectVersion, None, groupAccount,
                   signingPrivateKeyPem, 8234389)

    return newFollowJson


def sendFollowRequestViaServer(baseDir: str, session,
                               fromNickname: str, password: str,
                               fromDomain: str, fromPort: int,
                               followNickname: str, followDomain: str,
                               followPort: int,
                               httpPrefix: str,
                               cachedWebfingers: {}, personCache: {},
                               debug: bool, projectVersion: str,
                               signingPrivateKeyPem: str) -> {}:
    """Creates a follow request via c2s
    """
    if not session:
        print('WARN: No session for sendFollowRequestViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    followDomainFull = getFullDomain(followDomain, followPort)

    followActor = localActorUrl(httpPrefix, fromNickname, fromDomainFull)
    followedId = \
        httpPrefix + '://' + followDomainFull + '/@' + followNickname

    statusNumber, published = getStatusNumber()
    newFollowJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': followActor + '/statuses/' + str(statusNumber),
        'type': 'Follow',
        'actor': followActor,
        'object': followedId
    }

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix, cachedWebfingers,
                        fromDomain, projectVersion, debug, False,
                        signingPrivateKeyPem)
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
     displayName) = getPersonBox(signingPrivateKeyPem, originDomain,
                                 baseDir, session, wfRequest, personCache,
                                 projectVersion, httpPrefix, fromNickname,
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
        postJson(httpPrefix, fromDomainFull,
                 session, newFollowJson, [], inboxUrl, headers, 3, True)
    if not postResult:
        if debug:
            print('DEBUG: POST follow request failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST follow request success')

    return newFollowJson


def sendUnfollowRequestViaServer(baseDir: str, session,
                                 fromNickname: str, password: str,
                                 fromDomain: str, fromPort: int,
                                 followNickname: str, followDomain: str,
                                 followPort: int,
                                 httpPrefix: str,
                                 cachedWebfingers: {}, personCache: {},
                                 debug: bool, projectVersion: str,
                                 signingPrivateKeyPem: str) -> {}:
    """Creates a unfollow request via c2s
    """
    if not session:
        print('WARN: No session for sendUnfollowRequestViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)
    followDomainFull = getFullDomain(followDomain, followPort)

    followActor = localActorUrl(httpPrefix, fromNickname, fromDomainFull)
    followedId = \
        httpPrefix + '://' + followDomainFull + '/@' + followNickname
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

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix, cachedWebfingers,
                        fromDomain, projectVersion, debug, False,
                        signingPrivateKeyPem)
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
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(signingPrivateKeyPem,
                                            originDomain,
                                            baseDir, session,
                                            wfRequest, personCache,
                                            projectVersion, httpPrefix,
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
        postJson(httpPrefix, fromDomainFull,
                 session, unfollowJson, [], inboxUrl, headers, 3, True)
    if not postResult:
        if debug:
            print('DEBUG: POST unfollow failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST unfollow success')

    return unfollowJson


def getFollowingViaServer(baseDir: str, session,
                          nickname: str, password: str,
                          domain: str, port: int,
                          httpPrefix: str, pageNumber: int,
                          cachedWebfingers: {}, personCache: {},
                          debug: bool, projectVersion: str,
                          signingPrivateKeyPem: str) -> {}:
    """Gets a page from the following collection as json
    """
    if not session:
        print('WARN: No session for getFollowingViaServer')
        return 6

    domainFull = getFullDomain(domain, port)
    followActor = localActorUrl(httpPrefix, nickname, domainFull)

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
        getJson(signingPrivateKeyPem, session, url, headers, {}, debug,
                __version__, httpPrefix, domain, 10, True)
    if not followingJson:
        if debug:
            print('DEBUG: GET following list failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET following list request success')

    return followingJson


def getFollowersViaServer(baseDir: str, session,
                          nickname: str, password: str,
                          domain: str, port: int,
                          httpPrefix: str, pageNumber: int,
                          cachedWebfingers: {}, personCache: {},
                          debug: bool, projectVersion: str,
                          signingPrivateKeyPem: str) -> {}:
    """Gets a page from the followers collection as json
    """
    if not session:
        print('WARN: No session for getFollowersViaServer')
        return 6

    domainFull = getFullDomain(domain, port)
    followActor = localActorUrl(httpPrefix, nickname, domainFull)

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
        getJson(signingPrivateKeyPem, session, url, headers, {}, debug,
                __version__, httpPrefix, domain, 10, True)
    if not followersJson:
        if debug:
            print('DEBUG: GET followers list failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET followers list request success')

    return followersJson


def getFollowRequestsViaServer(baseDir: str, session,
                               nickname: str, password: str,
                               domain: str, port: int,
                               httpPrefix: str, pageNumber: int,
                               cachedWebfingers: {}, personCache: {},
                               debug: bool, projectVersion: str,
                               signingPrivateKeyPem: str) -> {}:
    """Gets a page from the follow requests collection as json
    """
    if not session:
        print('WARN: No session for getFollowRequestsViaServer')
        return 6

    domainFull = getFullDomain(domain, port)

    followActor = localActorUrl(httpPrefix, nickname, domainFull)
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
        getJson(signingPrivateKeyPem, session, url, headers, {}, debug,
                __version__, httpPrefix, domain, 10, True)
    if not followersJson:
        if debug:
            print('DEBUG: GET follow requests list failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET follow requests list request success')

    return followersJson


def approveFollowRequestViaServer(baseDir: str, session,
                                  nickname: str, password: str,
                                  domain: str, port: int,
                                  httpPrefix: str, approveHandle: int,
                                  cachedWebfingers: {}, personCache: {},
                                  debug: bool, projectVersion: str,
                                  signingPrivateKeyPem: str) -> str:
    """Approves a follow request
    This is not exactly via c2s though. It simulates pressing the Approve
    button on the web interface
    """
    if not session:
        print('WARN: No session for approveFollowRequestViaServer')
        return 6

    domainFull = getFullDomain(domain, port)
    actor = localActorUrl(httpPrefix, nickname, domainFull)

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'text/html; charset=utf-8',
        'Authorization': authHeader
    }

    url = actor + '/followapprove=' + approveHandle
    approveHtml = \
        getJson(signingPrivateKeyPem, session, url, headers, {}, debug,
                __version__, httpPrefix, domain, 10, True)
    if not approveHtml:
        if debug:
            print('DEBUG: GET approve follow request failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET approve follow request request success')

    return approveHtml


def denyFollowRequestViaServer(baseDir: str, session,
                               nickname: str, password: str,
                               domain: str, port: int,
                               httpPrefix: str, denyHandle: int,
                               cachedWebfingers: {}, personCache: {},
                               debug: bool, projectVersion: str,
                               signingPrivateKeyPem: str) -> str:
    """Denies a follow request
    This is not exactly via c2s though. It simulates pressing the Deny
    button on the web interface
    """
    if not session:
        print('WARN: No session for denyFollowRequestViaServer')
        return 6

    domainFull = getFullDomain(domain, port)
    actor = localActorUrl(httpPrefix, nickname, domainFull)

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'text/html; charset=utf-8',
        'Authorization': authHeader
    }

    url = actor + '/followdeny=' + denyHandle
    denyHtml = \
        getJson(signingPrivateKeyPem, session, url, headers, {}, debug,
                __version__, httpPrefix, domain, 10, True)
    if not denyHtml:
        if debug:
            print('DEBUG: GET deny follow request failed for c2s to ' + url)
        return 5

    if debug:
        print('DEBUG: c2s GET deny follow request request success')

    return denyHtml


def getFollowersOfActor(baseDir: str, actor: str, debug: bool) -> {}:
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
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
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


def outboxUndoFollow(baseDir: str, messageJson: {}, debug: bool) -> None:
    """When an unfollow request is received by the outbox from c2s
    This removes the followed handle from the following.txt file
    of the relevant account
    """
    if not messageJson.get('type'):
        return
    if not messageJson['type'] == 'Undo':
        return
    if not hasObjectDict(messageJson):
        return
    if not messageJson['object'].get('type'):
        return
    if not messageJson['object']['type'] == 'Follow':
        if not messageJson['object']['type'] == 'Join':
            return
    if not messageJson['object'].get('object'):
        return
    if not messageJson['object'].get('actor'):
        return
    if not isinstance(messageJson['object']['object'], str):
        return
    if debug:
        print('DEBUG: undo follow arrived in outbox')

    nicknameFollower = getNicknameFromActor(messageJson['object']['actor'])
    if not nicknameFollower:
        print('WARN: unable to find nickname in ' +
              messageJson['object']['actor'])
        return
    domainFollower, portFollower = \
        getDomainFromActor(messageJson['object']['actor'])
    domainFollowerFull = getFullDomain(domainFollower, portFollower)

    nicknameFollowing = getNicknameFromActor(messageJson['object']['object'])
    if not nicknameFollowing:
        print('WARN: unable to find nickname in ' +
              messageJson['object']['object'])
        return
    domainFollowing, portFollowing = \
        getDomainFromActor(messageJson['object']['object'])
    domainFollowingFull = getFullDomain(domainFollowing, portFollowing)

    groupAccount = hasGroupType(baseDir, messageJson['object']['object'], None)
    if unfollowAccount(baseDir, nicknameFollower, domainFollowerFull,
                       nicknameFollowing, domainFollowingFull,
                       debug, groupAccount):
        if debug:
            print('DEBUG: ' + nicknameFollower + ' unfollowed ' +
                  nicknameFollowing + '@' + domainFollowingFull)
    else:
        if debug:
            print('WARN: ' + nicknameFollower + ' could not unfollow ' +
                  nicknameFollowing + '@' + domainFollowingFull)


def followerApprovalActive(baseDir: str, nickname: str, domain: str) -> bool:
    """Returns true if the given account requires follower approval
    """
    manuallyApprovesFollowers = False
    actorFilename = acctDir(baseDir, nickname, domain) + '.json'
    if os.path.isfile(actorFilename):
        actorJson = loadJson(actorFilename)
        if actorJson:
            if actorJson.get('manuallyApprovesFollowers'):
                manuallyApprovesFollowers = \
                    actorJson['manuallyApprovesFollowers']
    return manuallyApprovesFollowers
