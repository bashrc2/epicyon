__filename__ = "inbox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import json
import os
import datetime
import time
import random
from linked_data_sig import verifyJsonSignature
from languages import understoodPostLanguage
from like import updateLikesCollection
from utils import fileLastModified
from utils import hasObjectString
from utils import hasObjectStringObject
from utils import getReplyIntervalHours
from utils import canReplyTo
from utils import getUserPaths
from utils import getBaseContentFromPost
from utils import acctDir
from utils import removeDomainPort
from utils import getPortFromDomain
from utils import hasObjectDict
from utils import dmAllowedFromDomain
from utils import isRecentPost
from utils import getConfigParam
from utils import hasUsersPath
from utils import validPostDate
from utils import getFullDomain
from utils import removeIdEnding
from utils import getProtocolPrefixes
from utils import isBlogPost
from utils import removeAvatarFromCache
from utils import isPublicPost
from utils import getCachedPostFilename
from utils import removePostFromCache
from utils import urlPermitted
from utils import createInboxQueueDir
from utils import getStatusNumber
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import locatePost
from utils import deletePost
from utils import removeModerationPostFromIndex
from utils import loadJson
from utils import saveJson
from utils import undoLikesCollectionEntry
from utils import hasGroupType
from utils import localActorUrl
from utils import hasObjectStringType
from categories import getHashtagCategories
from categories import setHashtagCategory
from httpsig import verifyPostHeaders
from session import createSession
from follow import followerApprovalActive
from follow import isFollowingActor
from follow import receiveFollowRequest
from follow import getFollowersOfActor
from follow import unfollowerOfAccount
from pprint import pprint
from cache import storePersonInCache
from cache import getPersonPubKey
from acceptreject import receiveAcceptReject
from bookmarks import updateBookmarksCollection
from bookmarks import undoBookmarksCollectionEntry
from blocking import isBlocked
from blocking import isBlockedDomain
from blocking import brochModeLapses
from filters import isFiltered
from utils import updateAnnounceCollection
from utils import undoAnnounceCollectionEntry
from utils import dangerousMarkup
from utils import isDM
from utils import isReply
from utils import hasActor
from httpsig import messageContentDigest
from posts import editedPostFilename
from posts import savePostToBox
from posts import isCreateInsideAnnounce
from posts import createDirectMessagePost
from posts import validContentWarning
from posts import downloadAnnounce
from posts import isMuted
from posts import isImageMedia
from posts import sendSignedJson
from posts import sendToFollowersThread
from webapp_post import individualPostAsHtml
from question import questionUpdateVotes
from media import replaceYouTube
from media import replaceTwitter
from git import isGitPatch
from git import receiveGitPatch
from followingCalendar import receivingCalendarEvents
from happening import saveEventPost
from delete import removeOldHashtags
from categories import guessHashtagCategory
from context import hasValidContext
from speaker import updateSpeaker
from announce import isSelfAnnounce
from announce import createAnnounce
from notifyOnPost import notifyWhenPersonPosts
from conversation import updateConversation
from content import validHashTag
from webapp_hashtagswarm import htmlHashTagSwarm


def _storeLastPostId(baseDir: str, nickname: str, domain: str,
                     postJsonObject: {}) -> None:
    """Stores the id of the last post made by an actor
    When a new post arrives this allows it to be compared against the last
    to see if it is an edited post.
    It would be great if edited posts contained a back reference id to the
    source but we don't live in that ideal world.
    """
    actor = postId = None
    if hasObjectDict(postJsonObject):
        if postJsonObject['object'].get('attributedTo'):
            if isinstance(postJsonObject['object']['attributedTo'], str):
                actor = postJsonObject['object']['attributedTo']
                postId = removeIdEnding(postJsonObject['object']['id'])
    if not actor:
        actor = postJsonObject['actor']
        postId = removeIdEnding(postJsonObject['id'])
    if not actor:
        return
    lastpostDir = acctDir(baseDir, nickname, domain) + '/lastpost'
    if not os.path.isdir(lastpostDir):
        os.mkdir(lastpostDir)
    actorFilename = lastpostDir + '/' + actor.replace('/', '#')
    try:
        with open(actorFilename, 'w+') as fp:
            fp.write(postId)
    except BaseException:
        print('EX: Unable to write last post id to ' + actorFilename)
        pass


def _updateCachedHashtagSwarm(baseDir: str, nickname: str, domain: str,
                              httpPrefix: str, domainFull: str,
                              translate: {}) -> bool:
    """Updates the hashtag swarm stored as a file
    """
    cachedHashtagSwarmFilename = \
        acctDir(baseDir, nickname, domain) + '/.hashtagSwarm'
    saveSwarm = True
    if os.path.isfile(cachedHashtagSwarmFilename):
        lastModified = fileLastModified(cachedHashtagSwarmFilename)
        modifiedDate = None
        try:
            modifiedDate = \
                datetime.datetime.strptime(lastModified, "%Y-%m-%dT%H:%M:%SZ")
        except BaseException:
            print('EX: unable to parse last modified cache date ' +
                  str(lastModified))
            pass
        if modifiedDate:
            currDate = datetime.datetime.utcnow()
            timeDiff = currDate - modifiedDate
            diffMins = int(timeDiff.total_seconds() / 60)
            if diffMins < 10:
                # was saved recently, so don't save again
                # This avoids too much disk I/O
                saveSwarm = False
            else:
                print('Updating cached hashtag swarm, last changed ' +
                      str(diffMins) + ' minutes ago')
        else:
            print('WARN: no modified date for ' + str(lastModified))
    if saveSwarm:
        actor = localActorUrl(httpPrefix, nickname, domainFull)
        newSwarmStr = htmlHashTagSwarm(baseDir, actor, translate)
        if newSwarmStr:
            try:
                with open(cachedHashtagSwarmFilename, 'w+') as fp:
                    fp.write(newSwarmStr)
                    return True
            except BaseException:
                print('EX: unable to write cached hashtag swarm ' +
                      cachedHashtagSwarmFilename)
                pass
    return False


def storeHashTags(baseDir: str, nickname: str, domain: str,
                  httpPrefix: str, domainFull: str,
                  postJsonObject: {}, translate: {}) -> None:
    """Extracts hashtags from an incoming post and updates the
    relevant tags files.
    """
    if not isPublicPost(postJsonObject):
        return
    if not hasObjectDict(postJsonObject):
        return
    if not postJsonObject['object'].get('tag'):
        return
    if not postJsonObject.get('id'):
        return
    if not isinstance(postJsonObject['object']['tag'], list):
        return
    tagsDir = baseDir + '/tags'

    # add tags directory if it doesn't exist
    if not os.path.isdir(tagsDir):
        print('Creating tags directory')
        os.mkdir(tagsDir)

    hashtagCategories = getHashtagCategories(baseDir)

    hashtagsCtr = 0
    for tag in postJsonObject['object']['tag']:
        if not tag.get('type'):
            continue
        if not isinstance(tag['type'], str):
            continue
        if tag['type'] != 'Hashtag':
            continue
        if not tag.get('name'):
            continue
        tagName = tag['name'].replace('#', '').strip()
        if not validHashTag(tagName):
            continue
        tagsFilename = tagsDir + '/' + tagName + '.txt'
        postUrl = removeIdEnding(postJsonObject['id'])
        postUrl = postUrl.replace('/', '#')
        daysDiff = datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
        daysSinceEpoch = daysDiff.days
        tagline = str(daysSinceEpoch) + '  ' + nickname + '  ' + postUrl + '\n'
        hashtagsCtr += 1
        if not os.path.isfile(tagsFilename):
            with open(tagsFilename, 'w+') as tagsFile:
                tagsFile.write(tagline)
        else:
            if postUrl not in open(tagsFilename).read():
                try:
                    with open(tagsFilename, 'r+') as tagsFile:
                        content = tagsFile.read()
                        if tagline not in content:
                            tagsFile.seek(0, 0)
                            tagsFile.write(tagline + content)
                except Exception as e:
                    print('WARN: Failed to write entry to tags file ' +
                          tagsFilename + ' ' + str(e))
                removeOldHashtags(baseDir, 3)

        # automatically assign a category to the tag if possible
        categoryFilename = tagsDir + '/' + tagName + '.category'
        if not os.path.isfile(categoryFilename):
            categoryStr = \
                guessHashtagCategory(tagName, hashtagCategories)
            if categoryStr:
                setHashtagCategory(baseDir, tagName, categoryStr, False)

    # if some hashtags were found then recalculate the swarm
    # ready for later display
    if hashtagsCtr > 0:
        _updateCachedHashtagSwarm(baseDir, nickname, domain,
                                  httpPrefix, domainFull, translate)


def _inboxStorePostToHtmlCache(recentPostsCache: {}, maxRecentPosts: int,
                               translate: {},
                               baseDir: str, httpPrefix: str,
                               session, cachedWebfingers: {}, personCache: {},
                               nickname: str, domain: str, port: int,
                               postJsonObject: {},
                               allowDeletion: bool, boxname: str,
                               showPublishedDateOnly: bool,
                               peertubeInstances: [],
                               allowLocalNetworkAccess: bool,
                               themeName: str, systemLanguage: str,
                               maxLikeCount: int,
                               signingPrivateKeyPem: str,
                               CWlists: {},
                               listsEnabled: str) -> None:
    """Converts the json post into html and stores it in a cache
    This enables the post to be quickly displayed later
    """
    pageNumber = -999
    avatarUrl = None
    if boxname != 'outbox':
        boxname = 'inbox'

    notDM = not isDM(postJsonObject)
    YTReplacementDomain = getConfigParam(baseDir, 'youtubedomain')
    twitterReplacementDomain = getConfigParam(baseDir, 'twitterdomain')
    individualPostAsHtml(signingPrivateKeyPem,
                         True, recentPostsCache, maxRecentPosts,
                         translate, pageNumber,
                         baseDir, session, cachedWebfingers,
                         personCache,
                         nickname, domain, port, postJsonObject,
                         avatarUrl, True, allowDeletion,
                         httpPrefix, __version__, boxname,
                         YTReplacementDomain, twitterReplacementDomain,
                         showPublishedDateOnly,
                         peertubeInstances, allowLocalNetworkAccess,
                         themeName, systemLanguage, maxLikeCount,
                         notDM, True, True, False, True, False,
                         CWlists, listsEnabled)


def validInbox(baseDir: str, nickname: str, domain: str) -> bool:
    """Checks whether files were correctly saved to the inbox
    """
    domain = removeDomainPort(domain)
    inboxDir = acctDir(baseDir, nickname, domain) + '/inbox'
    if not os.path.isdir(inboxDir):
        return True
    for subdir, dirs, files in os.walk(inboxDir):
        for f in files:
            filename = os.path.join(subdir, f)
            if not os.path.isfile(filename):
                print('filename: ' + filename)
                return False
            if 'postNickname' in open(filename).read():
                print('queue file incorrectly saved to ' + filename)
                return False
        break
    return True


def validInboxFilenames(baseDir: str, nickname: str, domain: str,
                        expectedDomain: str, expectedPort: int) -> bool:
    """Used by unit tests to check that the port number gets appended to
    domain names within saved post filenames
    """
    domain = removeDomainPort(domain)
    inboxDir = acctDir(baseDir, nickname, domain) + '/inbox'
    if not os.path.isdir(inboxDir):
        print('Not an inbox directory: ' + inboxDir)
        return True
    expectedStr = expectedDomain + ':' + str(expectedPort)
    expectedFound = False
    ctr = 0
    for subdir, dirs, files in os.walk(inboxDir):
        for f in files:
            filename = os.path.join(subdir, f)
            ctr += 1
            if not os.path.isfile(filename):
                print('filename: ' + filename)
                return False
            if expectedStr in filename:
                expectedFound = True
        break
    if ctr == 0:
        return True
    if not expectedFound:
        print('Expected file was not found: ' + expectedStr)
        for subdir, dirs, files in os.walk(inboxDir):
            for f in files:
                filename = os.path.join(subdir, f)
                print(filename)
            break
        return False
    return True


def inboxMessageHasParams(messageJson: {}) -> bool:
    """Checks whether an incoming message contains expected parameters
    """
    expectedParams = ['actor', 'type', 'object']
    for param in expectedParams:
        if not messageJson.get(param):
            # print('inboxMessageHasParams: ' +
            #       param + ' ' + str(messageJson))
            return False

    # actor should be a string
    if not isinstance(messageJson['actor'], str):
        print('WARN: actor should be a string, but is actually: ' +
              str(messageJson['actor']))
        pprint(messageJson)
        return False

    # type should be a string
    if not isinstance(messageJson['type'], str):
        print('WARN: type from ' + str(messageJson['actor']) +
              ' should be a string, but is actually: ' +
              str(messageJson['type']))
        return False

    # object should be a dict or a string
    if not hasObjectDict(messageJson):
        if not isinstance(messageJson['object'], str):
            print('WARN: object from ' + str(messageJson['actor']) +
                  ' should be a dict or string, but is actually: ' +
                  str(messageJson['object']))
            return False

    if not messageJson.get('to'):
        allowedWithoutToParam = ['Like', 'Follow', 'Join', 'Request',
                                 'Accept', 'Capability', 'Undo']
        if messageJson['type'] not in allowedWithoutToParam:
            return False
    return True


def inboxPermittedMessage(domain: str, messageJson: {},
                          federationList: []) -> bool:
    """ check that we are receiving from a permitted domain
    """
    if not hasActor(messageJson, False):
        return False

    actor = messageJson['actor']
    # always allow the local domain
    if domain in actor:
        return True

    if not urlPermitted(actor, federationList):
        return False

    alwaysAllowedTypes = ('Follow', 'Join', 'Like', 'Delete', 'Announce')
    if messageJson['type'] not in alwaysAllowedTypes:
        if not hasObjectDict(messageJson):
            return True
        if messageJson['object'].get('inReplyTo'):
            inReplyTo = messageJson['object']['inReplyTo']
            if not isinstance(inReplyTo, str):
                return False
            if not urlPermitted(inReplyTo, federationList):
                return False

    return True


def savePostToInboxQueue(baseDir: str, httpPrefix: str,
                         nickname: str, domain: str,
                         postJsonObject: {},
                         originalPostJsonObject: {},
                         messageBytes: str,
                         httpHeaders: {},
                         postPath: str, debug: bool,
                         blockedCache: [], systemLanguage: str) -> str:
    """Saves the given json to the inbox queue for the person
    keyId specifies the actor sending the post
    """
    if len(messageBytes) > 10240:
        print('WARN: inbox message too long ' +
              str(len(messageBytes)) + ' bytes')
        return None
    originalDomain = domain
    domain = removeDomainPort(domain)

    # block at the ealiest stage possible, which means the data
    # isn't written to file
    postNickname = None
    postDomain = None
    actor = None
    if postJsonObject.get('actor'):
        if not isinstance(postJsonObject['actor'], str):
            return None
        actor = postJsonObject['actor']
        postNickname = getNicknameFromActor(postJsonObject['actor'])
        if not postNickname:
            print('No post Nickname in actor ' + postJsonObject['actor'])
            return None
        postDomain, postPort = getDomainFromActor(postJsonObject['actor'])
        if not postDomain:
            if debug:
                pprint(postJsonObject)
            print('No post Domain in actor')
            return None
        if isBlocked(baseDir, nickname, domain,
                     postNickname, postDomain, blockedCache):
            if debug:
                print('DEBUG: post from ' + postNickname + ' blocked')
            return None
        postDomain = getFullDomain(postDomain, postPort)

    if hasObjectDict(postJsonObject):
        if postJsonObject['object'].get('inReplyTo'):
            if isinstance(postJsonObject['object']['inReplyTo'], str):
                inReplyTo = \
                    postJsonObject['object']['inReplyTo']
                replyDomain, replyPort = \
                    getDomainFromActor(inReplyTo)
                if isBlockedDomain(baseDir, replyDomain, blockedCache):
                    if debug:
                        print('WARN: post contains reply from ' +
                              str(actor) +
                              ' to a blocked domain: ' + replyDomain)
                    return None
                else:
                    replyNickname = \
                        getNicknameFromActor(inReplyTo)
                    if replyNickname and replyDomain:
                        if isBlocked(baseDir, nickname, domain,
                                     replyNickname, replyDomain,
                                     blockedCache):
                            if debug:
                                print('WARN: post contains reply from ' +
                                      str(actor) +
                                      ' to a blocked account: ' +
                                      replyNickname + '@' + replyDomain)
                            return None
        if postJsonObject['object'].get('content'):
            contentStr = getBaseContentFromPost(postJsonObject, systemLanguage)
            if contentStr:
                if isFiltered(baseDir, nickname, domain, contentStr):
                    if debug:
                        print('WARN: post was filtered out due to content')
                    return None
    originalPostId = None
    if postJsonObject.get('id'):
        if not isinstance(postJsonObject['id'], str):
            return None
        originalPostId = removeIdEnding(postJsonObject['id'])

    currTime = datetime.datetime.utcnow()

    postId = None
    if postJsonObject.get('id'):
        postId = removeIdEnding(postJsonObject['id'])
        published = currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not postId:
        statusNumber, published = getStatusNumber()
        if actor:
            postId = actor + '/statuses/' + statusNumber
        else:
            postId = localActorUrl(httpPrefix, nickname, originalDomain) + \
                '/statuses/' + statusNumber

    # NOTE: don't change postJsonObject['id'] before signature check

    inboxQueueDir = createInboxQueueDir(nickname, domain, baseDir)

    handle = nickname + '@' + domain
    destination = baseDir + '/accounts/' + \
        handle + '/inbox/' + postId.replace('/', '#') + '.json'
    filename = inboxQueueDir + '/' + postId.replace('/', '#') + '.json'

    sharedInboxItem = False
    if nickname == 'inbox':
        nickname = originalDomain
        sharedInboxItem = True

    digestStartTime = time.time()
    digest = messageContentDigest(messageBytes)
    timeDiffStr = str(int((time.time() - digestStartTime) * 1000))
    if debug:
        while len(timeDiffStr) < 6:
            timeDiffStr = '0' + timeDiffStr
        print('DIGEST|' + timeDiffStr + '|' + filename)

    newQueueItem = {
        'originalId': originalPostId,
        'id': postId,
        'actor': actor,
        'nickname': nickname,
        'domain': domain,
        'postNickname': postNickname,
        'postDomain': postDomain,
        'sharedInbox': sharedInboxItem,
        'published': published,
        'httpHeaders': httpHeaders,
        'path': postPath,
        'post': postJsonObject,
        'original': originalPostJsonObject,
        'digest': digest,
        'filename': filename,
        'destination': destination
    }

    if debug:
        print('Inbox queue item created')
    saveJson(newQueueItem, filename)
    return filename


def _inboxPostRecipientsAdd(baseDir: str, httpPrefix: str, toList: [],
                            recipientsDict: {},
                            domainMatch: str, domain: str,
                            actor: str, debug: bool) -> bool:
    """Given a list of post recipients (toList) from 'to' or 'cc' parameters
    populate a recipientsDict with the handle for each
    """
    followerRecipients = False
    for recipient in toList:
        if not recipient:
            continue
        # is this a to a local account?
        if domainMatch in recipient:
            # get the handle for the local account
            nickname = recipient.split(domainMatch)[1]
            handle = nickname + '@' + domain
            if os.path.isdir(baseDir + '/accounts/' + handle):
                recipientsDict[handle] = None
            else:
                if debug:
                    print('DEBUG: ' + baseDir + '/accounts/' +
                          handle + ' does not exist')
        else:
            if debug:
                print('DEBUG: ' + recipient + ' is not local to ' +
                      domainMatch)
                print(str(toList))
        if recipient.endswith('followers'):
            if debug:
                print('DEBUG: followers detected as post recipients')
            followerRecipients = True
    return followerRecipients, recipientsDict


def _inboxPostRecipients(baseDir: str, postJsonObject: {},
                         httpPrefix: str, domain: str, port: int,
                         debug: bool) -> ([], []):
    """Returns dictionaries containing the recipients of the given post
    The shared dictionary contains followers
    """
    recipientsDict = {}
    recipientsDictFollowers = {}

    if not postJsonObject.get('actor'):
        if debug:
            pprint(postJsonObject)
            print('WARNING: inbox post has no actor')
        return recipientsDict, recipientsDictFollowers

    domain = removeDomainPort(domain)
    domainBase = domain
    domain = getFullDomain(domain, port)
    domainMatch = '/' + domain + '/users/'

    actor = postJsonObject['actor']
    # first get any specific people which the post is addressed to

    followerRecipients = False
    if hasObjectDict(postJsonObject):
        if postJsonObject['object'].get('to'):
            if isinstance(postJsonObject['object']['to'], list):
                recipientsList = postJsonObject['object']['to']
            else:
                recipientsList = [postJsonObject['object']['to']]
            if debug:
                print('DEBUG: resolving "to"')
            includesFollowers, recipientsDict = \
                _inboxPostRecipientsAdd(baseDir, httpPrefix,
                                        recipientsList,
                                        recipientsDict,
                                        domainMatch, domainBase,
                                        actor, debug)
            if includesFollowers:
                followerRecipients = True
        else:
            if debug:
                print('DEBUG: inbox post has no "to"')

        if postJsonObject['object'].get('cc'):
            if isinstance(postJsonObject['object']['cc'], list):
                recipientsList = postJsonObject['object']['cc']
            else:
                recipientsList = [postJsonObject['object']['cc']]
            includesFollowers, recipientsDict = \
                _inboxPostRecipientsAdd(baseDir, httpPrefix,
                                        recipientsList,
                                        recipientsDict,
                                        domainMatch, domainBase,
                                        actor, debug)
            if includesFollowers:
                followerRecipients = True
        else:
            if debug:
                print('DEBUG: inbox post has no cc')
    else:
        if debug and postJsonObject.get('object'):
            if isinstance(postJsonObject['object'], str):
                if '/statuses/' in postJsonObject['object']:
                    print('DEBUG: inbox item is a link to a post')
                else:
                    if '/users/' in postJsonObject['object']:
                        print('DEBUG: inbox item is a link to an actor')

    if postJsonObject.get('to'):
        if isinstance(postJsonObject['to'], list):
            recipientsList = postJsonObject['to']
        else:
            recipientsList = [postJsonObject['to']]
        includesFollowers, recipientsDict = \
            _inboxPostRecipientsAdd(baseDir, httpPrefix,
                                    recipientsList,
                                    recipientsDict,
                                    domainMatch, domainBase,
                                    actor, debug)
        if includesFollowers:
            followerRecipients = True

    if postJsonObject.get('cc'):
        if isinstance(postJsonObject['cc'], list):
            recipientsList = postJsonObject['cc']
        else:
            recipientsList = [postJsonObject['cc']]
        includesFollowers, recipientsDict = \
            _inboxPostRecipientsAdd(baseDir, httpPrefix,
                                    recipientsList,
                                    recipientsDict,
                                    domainMatch, domainBase,
                                    actor, debug)
        if includesFollowers:
            followerRecipients = True

    if not followerRecipients:
        if debug:
            print('DEBUG: no followers were resolved')
        return recipientsDict, recipientsDictFollowers

    # now resolve the followers
    recipientsDictFollowers = \
        getFollowersOfActor(baseDir, actor, debug)

    return recipientsDict, recipientsDictFollowers


def _receiveUndoFollow(session, baseDir: str, httpPrefix: str,
                       port: int, messageJson: {},
                       federationList: [],
                       debug: bool) -> bool:
    if not messageJson['object'].get('actor'):
        if debug:
            print('DEBUG: follow request has no actor within object')
        return False
    if not hasUsersPath(messageJson['object']['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing ' +
                  'from actor within object')
        return False
    if messageJson['object']['actor'] != messageJson['actor']:
        if debug:
            print('DEBUG: actors do not match')
        return False

    nicknameFollower = \
        getNicknameFromActor(messageJson['object']['actor'])
    if not nicknameFollower:
        print('WARN: unable to find nickname in ' +
              messageJson['object']['actor'])
        return False
    domainFollower, portFollower = \
        getDomainFromActor(messageJson['object']['actor'])
    domainFollowerFull = getFullDomain(domainFollower, portFollower)

    nicknameFollowing = \
        getNicknameFromActor(messageJson['object']['object'])
    if not nicknameFollowing:
        print('WARN: unable to find nickname in ' +
              messageJson['object']['object'])
        return False
    domainFollowing, portFollowing = \
        getDomainFromActor(messageJson['object']['object'])
    domainFollowingFull = getFullDomain(domainFollowing, portFollowing)

    groupAccount = hasGroupType(baseDir, messageJson['object']['actor'], None)
    if unfollowerOfAccount(baseDir,
                           nicknameFollowing, domainFollowingFull,
                           nicknameFollower, domainFollowerFull,
                           debug, groupAccount):
        print(nicknameFollowing + '@' + domainFollowingFull + ': '
              'Follower ' + nicknameFollower + '@' + domainFollowerFull +
              ' was removed')
        return True

    if debug:
        print('DEBUG: Follower ' +
              nicknameFollower + '@' + domainFollowerFull +
              ' was not removed')
    return False


def _receiveUndo(session, baseDir: str, httpPrefix: str,
                 port: int, sendThreads: [], postLog: [],
                 cachedWebfingers: {}, personCache: {},
                 messageJson: {}, federationList: [],
                 debug: bool) -> bool:
    """Receives an undo request within the POST section of HTTPServer
    """
    if not messageJson['type'].startswith('Undo'):
        return False
    if debug:
        print('DEBUG: Undo activity received')
    if not hasActor(messageJson, debug):
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor')
        return False
    if not hasObjectStringType(messageJson, debug):
        return False
    if not hasObjectStringObject(messageJson, debug):
        return False
    if messageJson['object']['type'] == 'Follow' or \
       messageJson['object']['type'] == 'Join':
        return _receiveUndoFollow(session, baseDir, httpPrefix,
                                  port, messageJson,
                                  federationList, debug)
    return False


def _personReceiveUpdate(baseDir: str,
                         domain: str, port: int,
                         updateNickname: str, updateDomain: str,
                         updatePort: int,
                         personJson: {}, personCache: {},
                         debug: bool) -> bool:
    """Changes an actor. eg: avatar or display name change
    """
    if debug:
        print('Receiving actor update for ' + personJson['url'] +
              ' ' + str(personJson))
    domainFull = getFullDomain(domain, port)
    updateDomainFull = getFullDomain(updateDomain, updatePort)
    usersPaths = getUserPaths()
    usersStrFound = False
    for usersStr in usersPaths:
        actor = updateDomainFull + usersStr + updateNickname
        if actor in personJson['id']:
            usersStrFound = True
            break
    if not usersStrFound:
        if debug:
            print('actor: ' + actor)
            print('id: ' + personJson['id'])
            print('DEBUG: Actor does not match id')
        return False
    if updateDomainFull == domainFull:
        if debug:
            print('DEBUG: You can only receive actor updates ' +
                  'for domains other than your own')
        return False
    if not personJson.get('publicKey'):
        if debug:
            print('DEBUG: actor update does not contain a public key')
        return False
    if not personJson['publicKey'].get('publicKeyPem'):
        if debug:
            print('DEBUG: actor update does not contain a public key Pem')
        return False
    actorFilename = baseDir + '/cache/actors/' + \
        personJson['id'].replace('/', '#') + '.json'
    # check that the public keys match.
    # If they don't then this may be a nefarious attempt to hack an account
    idx = personJson['id']
    if personCache.get(idx):
        if personCache[idx]['actor']['publicKey']['publicKeyPem'] != \
           personJson['publicKey']['publicKeyPem']:
            if debug:
                print('WARN: Public key does not match when updating actor')
            return False
    else:
        if os.path.isfile(actorFilename):
            existingPersonJson = loadJson(actorFilename)
            if existingPersonJson:
                if existingPersonJson['publicKey']['publicKeyPem'] != \
                   personJson['publicKey']['publicKeyPem']:
                    if debug:
                        print('WARN: Public key does not match ' +
                              'cached actor when updating')
                    return False
    # save to cache in memory
    storePersonInCache(baseDir, personJson['id'], personJson,
                       personCache, True)
    # save to cache on file
    if saveJson(personJson, actorFilename):
        if debug:
            print('actor updated for ' + personJson['id'])

    # remove avatar if it exists so that it will be refreshed later
    # when a timeline is constructed
    actorStr = personJson['id'].replace('/', '-')
    removeAvatarFromCache(baseDir, actorStr)
    return True


def _receiveUpdateToQuestion(recentPostsCache: {}, messageJson: {},
                             baseDir: str,
                             nickname: str, domain: str) -> None:
    """Updating a question as new votes arrive
    """
    # message url of the question
    if not messageJson.get('id'):
        return
    if not hasActor(messageJson, False):
        return
    messageId = removeIdEnding(messageJson['id'])
    if '#' in messageId:
        messageId = messageId.split('#', 1)[0]
    # find the question post
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        return
    # load the json for the question
    postJsonObject = loadJson(postFilename, 1)
    if not postJsonObject:
        return
    if not postJsonObject.get('actor'):
        return
    # does the actor match?
    if postJsonObject['actor'] != messageJson['actor']:
        return
    saveJson(messageJson, postFilename)
    # ensure that the cached post is removed if it exists, so
    # that it then will be recreated
    cachedPostFilename = \
        getCachedPostFilename(baseDir, nickname, domain, messageJson)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except BaseException:
                print('EX: _receiveUpdateToQuestion unable to delete ' +
                      cachedPostFilename)
                pass
    # remove from memory cache
    removePostFromCache(messageJson, recentPostsCache)


def _receiveUpdate(recentPostsCache: {}, session, baseDir: str,
                   httpPrefix: str, domain: str, port: int,
                   sendThreads: [], postLog: [], cachedWebfingers: {},
                   personCache: {}, messageJson: {}, federationList: [],
                   nickname: str, debug: bool) -> bool:
    """Receives an Update activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Update':
        return False
    if not hasActor(messageJson, debug):
        return False
    if not hasObjectStringType(messageJson, debug):
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  messageJson['type'])
        return False

    if messageJson['object']['type'] == 'Question':
        _receiveUpdateToQuestion(recentPostsCache, messageJson,
                                 baseDir, nickname, domain)
        if debug:
            print('DEBUG: Question update was received')
        return True

    if messageJson['object']['type'] == 'Person' or \
       messageJson['object']['type'] == 'Application' or \
       messageJson['object']['type'] == 'Group' or \
       messageJson['object']['type'] == 'Service':
        if messageJson['object'].get('url') and \
           messageJson['object'].get('id'):
            if debug:
                print('Request to update actor: ' + str(messageJson))
            updateNickname = getNicknameFromActor(messageJson['actor'])
            if updateNickname:
                updateDomain, updatePort = \
                    getDomainFromActor(messageJson['actor'])
                if _personReceiveUpdate(baseDir,
                                        domain, port,
                                        updateNickname, updateDomain,
                                        updatePort,
                                        messageJson['object'],
                                        personCache, debug):
                    print('Person Update: ' + str(messageJson))
                    if debug:
                        print('DEBUG: Profile update was received for ' +
                              messageJson['object']['url'])
                        return True
    return False


def _receiveLike(recentPostsCache: {},
                 session, handle: str, isGroup: bool, baseDir: str,
                 httpPrefix: str, domain: str, port: int,
                 onionDomain: str,
                 sendThreads: [], postLog: [], cachedWebfingers: {},
                 personCache: {}, messageJson: {}, federationList: [],
                 debug: bool,
                 signingPrivateKeyPem: str,
                 maxRecentPosts: int, translate: {},
                 allowDeletion: bool,
                 YTReplacementDomain: str,
                 twitterReplacementDomain: str,
                 peertubeInstances: [],
                 allowLocalNetworkAccess: bool,
                 themeName: str, systemLanguage: str,
                 maxLikeCount: int, CWlists: {},
                 listsEnabled: str) -> bool:
    """Receives a Like activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Like':
        return False
    if not hasActor(messageJson, debug):
        return False
    if not hasObjectString(messageJson, debug):
        return False
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no "to" list')
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  messageJson['type'])
        return False
    if '/statuses/' not in messageJson['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  messageJson['type'])
        return False
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of like - ' + handle)
    # if this post in the outbox of the person?
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    postLikedId = messageJson['object']
    postFilename = locatePost(baseDir, handleName, handleDom, postLikedId)
    if not postFilename:
        if debug:
            print('DEBUG: post not found in inbox or outbox')
            print(postLikedId)
        return True
    if debug:
        print('DEBUG: liked post found in inbox')

    likeActor = messageJson['actor']
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    if not _alreadyLiked(baseDir,
                         handleName, handleDom,
                         postLikedId,
                         likeActor):
        _likeNotify(baseDir, domain, onionDomain, handle,
                    likeActor, postLikedId)
    updateLikesCollection(recentPostsCache, baseDir, postFilename,
                          postLikedId, likeActor,
                          handleName, domain, debug, None)
    # regenerate the html
    likedPostJson = loadJson(postFilename, 0, 1)
    if likedPostJson:
        if likedPostJson.get('type'):
            if likedPostJson['type'] == 'Announce' and \
               likedPostJson.get('object'):
                if isinstance(likedPostJson['object'], str):
                    announceLikeUrl = likedPostJson['object']
                    announceLikedFilename = \
                        locatePost(baseDir, handleName,
                                   domain, announceLikeUrl)
                    if announceLikedFilename:
                        postLikedId = announceLikeUrl
                        postFilename = announceLikedFilename
                        updateLikesCollection(recentPostsCache,
                                              baseDir,
                                              postFilename,
                                              postLikedId,
                                              likeActor,
                                              handleName,
                                              domain, debug, None)
        if likedPostJson:
            if debug:
                cachedPostFilename = \
                    getCachedPostFilename(baseDir, handleName, domain,
                                          likedPostJson)
                print('Liked post json: ' + str(likedPostJson))
                print('Liked post nickname: ' + handleName + ' ' + domain)
                print('Liked post cache: ' + str(cachedPostFilename))
            pageNumber = 1
            showPublishedDateOnly = False
            showIndividualPostIcons = True
            manuallyApproveFollowers = \
                followerApprovalActive(baseDir, handleName, domain)
            notDM = not isDM(likedPostJson)
            individualPostAsHtml(signingPrivateKeyPem, False,
                                 recentPostsCache, maxRecentPosts,
                                 translate, pageNumber, baseDir,
                                 session, cachedWebfingers, personCache,
                                 handleName, domain, port, likedPostJson,
                                 None, True, allowDeletion,
                                 httpPrefix, __version__,
                                 'inbox',
                                 YTReplacementDomain,
                                 twitterReplacementDomain,
                                 showPublishedDateOnly,
                                 peertubeInstances,
                                 allowLocalNetworkAccess,
                                 themeName, systemLanguage,
                                 maxLikeCount, notDM,
                                 showIndividualPostIcons,
                                 manuallyApproveFollowers,
                                 False, True, False, CWlists,
                                 listsEnabled)
    return True


def _receiveUndoLike(recentPostsCache: {},
                     session, handle: str, isGroup: bool, baseDir: str,
                     httpPrefix: str, domain: str, port: int,
                     sendThreads: [], postLog: [], cachedWebfingers: {},
                     personCache: {}, messageJson: {}, federationList: [],
                     debug: bool,
                     signingPrivateKeyPem: str,
                     maxRecentPosts: int, translate: {},
                     allowDeletion: bool,
                     YTReplacementDomain: str,
                     twitterReplacementDomain: str,
                     peertubeInstances: [],
                     allowLocalNetworkAccess: bool,
                     themeName: str, systemLanguage: str,
                     maxLikeCount: int, CWlists: {},
                     listsEnabled: str) -> bool:
    """Receives an undo like activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Undo':
        return False
    if not hasActor(messageJson, debug):
        return False
    if not hasObjectStringType(messageJson, debug):
        return False
    if messageJson['object']['type'] != 'Like':
        return False
    if not hasObjectStringObject(messageJson, debug):
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  messageJson['type'] + ' like')
        return False
    if '/statuses/' not in messageJson['object']['object']:
        if debug:
            print('DEBUG: "statuses" missing from like object in ' +
                  messageJson['type'])
        return False
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of undo like - ' + handle)
    # if this post in the outbox of the person?
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    postFilename = \
        locatePost(baseDir, handleName, handleDom,
                   messageJson['object']['object'])
    if not postFilename:
        if debug:
            print('DEBUG: unliked post not found in inbox or outbox')
            print(messageJson['object']['object'])
        return True
    if debug:
        print('DEBUG: liked post found in inbox. Now undoing.')
    likeActor = messageJson['actor']
    postLikedId = messageJson['object']
    undoLikesCollectionEntry(recentPostsCache, baseDir, postFilename,
                             postLikedId, likeActor, domain, debug, None)
    # regenerate the html
    likedPostJson = loadJson(postFilename, 0, 1)
    if likedPostJson:
        if likedPostJson.get('type'):
            if likedPostJson['type'] == 'Announce' and \
               likedPostJson.get('object'):
                if isinstance(likedPostJson['object'], str):
                    announceLikeUrl = likedPostJson['object']
                    announceLikedFilename = \
                        locatePost(baseDir, handleName,
                                   domain, announceLikeUrl)
                    if announceLikedFilename:
                        postLikedId = announceLikeUrl
                        postFilename = announceLikedFilename
                        undoLikesCollectionEntry(recentPostsCache, baseDir,
                                                 postFilename, postLikedId,
                                                 likeActor, domain, debug,
                                                 None)
        if likedPostJson:
            if debug:
                cachedPostFilename = \
                    getCachedPostFilename(baseDir, handleName, domain,
                                          likedPostJson)
                print('Unliked post json: ' + str(likedPostJson))
                print('Unliked post nickname: ' + handleName + ' ' + domain)
                print('Unliked post cache: ' + str(cachedPostFilename))
            pageNumber = 1
            showPublishedDateOnly = False
            showIndividualPostIcons = True
            manuallyApproveFollowers = \
                followerApprovalActive(baseDir, handleName, domain)
            notDM = not isDM(likedPostJson)
            individualPostAsHtml(signingPrivateKeyPem, False,
                                 recentPostsCache, maxRecentPosts,
                                 translate, pageNumber, baseDir,
                                 session, cachedWebfingers, personCache,
                                 handleName, domain, port, likedPostJson,
                                 None, True, allowDeletion,
                                 httpPrefix, __version__,
                                 'inbox',
                                 YTReplacementDomain,
                                 twitterReplacementDomain,
                                 showPublishedDateOnly,
                                 peertubeInstances,
                                 allowLocalNetworkAccess,
                                 themeName, systemLanguage,
                                 maxLikeCount, notDM,
                                 showIndividualPostIcons,
                                 manuallyApproveFollowers,
                                 False, True, False, CWlists,
                                 listsEnabled)
    return True


def _receiveBookmark(recentPostsCache: {},
                     session, handle: str, isGroup: bool, baseDir: str,
                     httpPrefix: str, domain: str, port: int,
                     sendThreads: [], postLog: [], cachedWebfingers: {},
                     personCache: {}, messageJson: {}, federationList: [],
                     debug: bool, signingPrivateKeyPem: str,
                     maxRecentPosts: int, translate: {},
                     allowDeletion: bool,
                     YTReplacementDomain: str,
                     twitterReplacementDomain: str,
                     peertubeInstances: [],
                     allowLocalNetworkAccess: bool,
                     themeName: str, systemLanguage: str,
                     maxLikeCount: int, CWlists: {},
                     listsEnabled: {}) -> bool:
    """Receives a bookmark activity within the POST section of HTTPServer
    """
    if not messageJson.get('type'):
        return False
    if messageJson['type'] != 'Add':
        return False
    if not hasActor(messageJson, debug):
        return False
    if not messageJson.get('target'):
        if debug:
            print('DEBUG: no target in inbox bookmark Add')
        return False
    if not hasObjectStringType(messageJson, debug):
        return False
    if not isinstance(messageJson['target'], str):
        if debug:
            print('DEBUG: inbox bookmark Add target is not string')
        return False
    domainFull = getFullDomain(domain, port)
    nickname = handle.split('@')[0]
    if not messageJson['actor'].endswith(domainFull + '/users/' + nickname):
        if debug:
            print('DEBUG: inbox bookmark Add unexpected actor')
        return False
    if not messageJson['target'].endswith(messageJson['actor'] +
                                          '/tlbookmarks'):
        if debug:
            print('DEBUG: inbox bookmark Add target invalid ' +
                  messageJson['target'])
        return False
    if messageJson['object']['type'] != 'Document':
        if debug:
            print('DEBUG: inbox bookmark Add type is not Document')
        return False
    if not messageJson['object'].get('url'):
        if debug:
            print('DEBUG: inbox bookmark Add missing url')
        return False
    if '/statuses/' not in messageJson['object']['url']:
        if debug:
            print('DEBUG: inbox bookmark Add missing statuses un url')
        return False
    if debug:
        print('DEBUG: c2s inbox bookmark Add request arrived in outbox')

    messageUrl = removeIdEnding(messageJson['object']['url'])
    domain = removeDomainPort(domain)
    postFilename = locatePost(baseDir, nickname, domain, messageUrl)
    if not postFilename:
        if debug:
            print('DEBUG: c2s inbox like post not found in inbox or outbox')
            print(messageUrl)
        return True

    updateBookmarksCollection(recentPostsCache, baseDir, postFilename,
                              messageJson['object']['url'],
                              messageJson['actor'], domain, debug)
    # regenerate the html
    bookmarkedPostJson = loadJson(postFilename, 0, 1)
    if bookmarkedPostJson:
        if debug:
            cachedPostFilename = \
                getCachedPostFilename(baseDir, nickname, domain,
                                      bookmarkedPostJson)
            print('Bookmarked post json: ' + str(bookmarkedPostJson))
            print('Bookmarked post nickname: ' + nickname + ' ' + domain)
            print('Bookmarked post cache: ' + str(cachedPostFilename))
        pageNumber = 1
        showPublishedDateOnly = False
        showIndividualPostIcons = True
        manuallyApproveFollowers = \
            followerApprovalActive(baseDir, nickname, domain)
        notDM = not isDM(bookmarkedPostJson)
        individualPostAsHtml(signingPrivateKeyPem, False,
                             recentPostsCache, maxRecentPosts,
                             translate, pageNumber, baseDir,
                             session, cachedWebfingers, personCache,
                             nickname, domain, port, bookmarkedPostJson,
                             None, True, allowDeletion,
                             httpPrefix, __version__,
                             'inbox',
                             YTReplacementDomain,
                             twitterReplacementDomain,
                             showPublishedDateOnly,
                             peertubeInstances,
                             allowLocalNetworkAccess,
                             themeName, systemLanguage,
                             maxLikeCount, notDM,
                             showIndividualPostIcons,
                             manuallyApproveFollowers,
                             False, True, False, CWlists,
                             listsEnabled)
    return True


def _receiveUndoBookmark(recentPostsCache: {},
                         session, handle: str, isGroup: bool, baseDir: str,
                         httpPrefix: str, domain: str, port: int,
                         sendThreads: [], postLog: [], cachedWebfingers: {},
                         personCache: {}, messageJson: {}, federationList: [],
                         debug: bool, signingPrivateKeyPem: str,
                         maxRecentPosts: int, translate: {},
                         allowDeletion: bool,
                         YTReplacementDomain: str,
                         twitterReplacementDomain: str,
                         peertubeInstances: [],
                         allowLocalNetworkAccess: bool,
                         themeName: str, systemLanguage: str,
                         maxLikeCount: int, CWlists: {},
                         listsEnabled: str) -> bool:
    """Receives an undo bookmark activity within the POST section of HTTPServer
    """
    if not messageJson.get('type'):
        return False
    if messageJson['type'] != 'Remove':
        return False
    if not hasActor(messageJson, debug):
        return False
    if not messageJson.get('target'):
        if debug:
            print('DEBUG: no target in inbox undo bookmark Remove')
        return False
    if not hasObjectStringType(messageJson, debug):
        return False
    if not isinstance(messageJson['target'], str):
        if debug:
            print('DEBUG: inbox Remove bookmark target is not string')
        return False
    domainFull = getFullDomain(domain, port)
    nickname = handle.split('@')[0]
    if not messageJson['actor'].endswith(domainFull + '/users/' + nickname):
        if debug:
            print('DEBUG: inbox undo bookmark Remove unexpected actor')
        return False
    if not messageJson['target'].endswith(messageJson['actor'] +
                                          '/tlbookmarks'):
        if debug:
            print('DEBUG: inbox undo bookmark Remove target invalid ' +
                  messageJson['target'])
        return False
    if messageJson['object']['type'] != 'Document':
        if debug:
            print('DEBUG: inbox undo bookmark Remove type is not Document')
        return False
    if not messageJson['object'].get('url'):
        if debug:
            print('DEBUG: inbox undo bookmark Remove missing url')
        return False
    if '/statuses/' not in messageJson['object']['url']:
        if debug:
            print('DEBUG: inbox undo bookmark Remove missing statuses un url')
        return False
    if debug:
        print('DEBUG: c2s inbox Remove bookmark ' +
              'request arrived in outbox')

    messageUrl = removeIdEnding(messageJson['object']['url'])
    domain = removeDomainPort(domain)
    postFilename = locatePost(baseDir, nickname, domain, messageUrl)
    if not postFilename:
        if debug:
            print('DEBUG: c2s inbox like post not found in inbox or outbox')
            print(messageUrl)
        return True

    undoBookmarksCollectionEntry(recentPostsCache, baseDir, postFilename,
                                 messageJson['object']['url'],
                                 messageJson['actor'], domain, debug)
    # regenerate the html
    bookmarkedPostJson = loadJson(postFilename, 0, 1)
    if bookmarkedPostJson:
        if debug:
            cachedPostFilename = \
                getCachedPostFilename(baseDir, nickname, domain,
                                      bookmarkedPostJson)
            print('Unbookmarked post json: ' + str(bookmarkedPostJson))
            print('Unbookmarked post nickname: ' + nickname + ' ' + domain)
            print('Unbookmarked post cache: ' + str(cachedPostFilename))
        pageNumber = 1
        showPublishedDateOnly = False
        showIndividualPostIcons = True
        manuallyApproveFollowers = \
            followerApprovalActive(baseDir, nickname, domain)
        notDM = not isDM(bookmarkedPostJson)
        individualPostAsHtml(signingPrivateKeyPem, False,
                             recentPostsCache, maxRecentPosts,
                             translate, pageNumber, baseDir,
                             session, cachedWebfingers, personCache,
                             nickname, domain, port, bookmarkedPostJson,
                             None, True, allowDeletion,
                             httpPrefix, __version__,
                             'inbox',
                             YTReplacementDomain,
                             twitterReplacementDomain,
                             showPublishedDateOnly,
                             peertubeInstances,
                             allowLocalNetworkAccess,
                             themeName, systemLanguage,
                             maxLikeCount, notDM,
                             showIndividualPostIcons,
                             manuallyApproveFollowers,
                             False, True, False, CWlists, listsEnabled)
    return True


def _receiveDelete(session, handle: str, isGroup: bool, baseDir: str,
                   httpPrefix: str, domain: str, port: int,
                   sendThreads: [], postLog: [], cachedWebfingers: {},
                   personCache: {}, messageJson: {}, federationList: [],
                   debug: bool, allowDeletion: bool,
                   recentPostsCache: {}) -> bool:
    """Receives a Delete activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Delete':
        return False
    if not hasActor(messageJson, debug):
        return False
    if debug:
        print('DEBUG: Delete activity arrived')
    if not hasObjectString(messageJson, debug):
        return False
    domainFull = getFullDomain(domain, port)
    deletePrefix = httpPrefix + '://' + domainFull + '/'
    if (not allowDeletion and
        (not messageJson['object'].startswith(deletePrefix) or
         not messageJson['actor'].startswith(deletePrefix))):
        if debug:
            print('DEBUG: delete not permitted from other instances')
        return False
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no "to" list')
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: ' +
                  '"users" or "profile" missing from actor in ' +
                  messageJson['type'])
        return False
    if '/statuses/' not in messageJson['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  messageJson['type'])
        return False
    if messageJson['actor'] not in messageJson['object']:
        if debug:
            print('DEBUG: actor is not the owner of the post to be deleted')
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of like - ' + handle)
    # if this post in the outbox of the person?
    messageId = removeIdEnding(messageJson['object'])
    removeModerationPostFromIndex(baseDir, messageId, debug)
    handleNickname = handle.split('@')[0]
    handleDomain = handle.split('@')[1]
    postFilename = locatePost(baseDir, handleNickname,
                              handleDomain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: delete post not found in inbox or outbox')
            print(messageId)
        return True
    deletePost(baseDir, httpPrefix, handleNickname,
               handleDomain, postFilename, debug,
               recentPostsCache)
    if debug:
        print('DEBUG: post deleted - ' + postFilename)

    # also delete any local blogs saved to the news actor
    if handleNickname != 'news' and handleDomain == domainFull:
        postFilename = locatePost(baseDir, 'news',
                                  handleDomain, messageId)
        if postFilename:
            deletePost(baseDir, httpPrefix, 'news',
                       handleDomain, postFilename, debug,
                       recentPostsCache)
            if debug:
                print('DEBUG: blog post deleted - ' + postFilename)
    return True


def _receiveAnnounce(recentPostsCache: {},
                     session, handle: str, isGroup: bool, baseDir: str,
                     httpPrefix: str,
                     domain: str, onionDomain: str, port: int,
                     sendThreads: [], postLog: [], cachedWebfingers: {},
                     personCache: {}, messageJson: {}, federationList: [],
                     debug: bool, translate: {},
                     YTReplacementDomain: str,
                     twitterReplacementDomain: str,
                     allowLocalNetworkAccess: bool,
                     themeName: str, systemLanguage: str,
                     signingPrivateKeyPem: str,
                     maxRecentPosts: int,
                     allowDeletion: bool,
                     peertubeInstances: [],
                     maxLikeCount: int, CWlists: {},
                     listsEnabled: str) -> bool:
    """Receives an announce activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Announce':
        return False
    if '@' not in handle:
        if debug:
            print('DEBUG: bad handle ' + handle)
        return False
    if not hasActor(messageJson, debug):
        return False
    if debug:
        print('DEBUG: receiving announce on ' + handle)
    if not hasObjectString(messageJson, debug):
        return False
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no "to" list')
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: ' +
                  '"users" or "profile" missing from actor in ' +
                  messageJson['type'])
        return False
    if isSelfAnnounce(messageJson):
        if debug:
            print('DEBUG: self-boost rejected')
        return False
    if not hasUsersPath(messageJson['object']):
        if debug:
            print('DEBUG: ' +
                  '"users", "channel" or "profile" missing in ' +
                  messageJson['type'])
        return False

    blockedCache = {}
    prefixes = getProtocolPrefixes()
    # is the domain of the announce actor blocked?
    objectDomain = messageJson['object']
    for prefix in prefixes:
        objectDomain = objectDomain.replace(prefix, '')
    if '/' in objectDomain:
        objectDomain = objectDomain.split('/')[0]
    if isBlockedDomain(baseDir, objectDomain):
        if debug:
            print('DEBUG: announced domain is blocked')
        return False
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of announce - ' + handle)

    # is the announce actor blocked?
    nickname = handle.split('@')[0]
    actorNickname = getNicknameFromActor(messageJson['actor'])
    actorDomain, actorPort = getDomainFromActor(messageJson['actor'])
    if isBlocked(baseDir, nickname, domain, actorNickname, actorDomain):
        print('Receive announce blocked for actor: ' +
              actorNickname + '@' + actorDomain)
        return False

    # also check the actor for the url being announced
    announcedActorNickname = getNicknameFromActor(messageJson['object'])
    announcedActorDomain, announcedActorPort = \
        getDomainFromActor(messageJson['object'])
    if isBlocked(baseDir, nickname, domain,
                 announcedActorNickname, announcedActorDomain):
        print('Receive announce object blocked for actor: ' +
              announcedActorNickname + '@' + announcedActorDomain)
        return False

    # is this post in the outbox of the person?
    postFilename = locatePost(baseDir, nickname, domain,
                              messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: announce post not found in inbox or outbox')
            print(messageJson['object'])
        return True
    updateAnnounceCollection(recentPostsCache, baseDir, postFilename,
                             messageJson['actor'], nickname, domain, debug)
    if debug:
        print('DEBUG: Downloading announce post ' + messageJson['actor'] +
              ' -> ' + messageJson['object'])
    domainFull = getFullDomain(domain, port)

    # Generate html. This also downloads the announced post.
    pageNumber = 1
    showPublishedDateOnly = False
    showIndividualPostIcons = True
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)
    notDM = True
    if debug:
        print('Generating html for announce ' + messageJson['id'])
    announceHtml = \
        individualPostAsHtml(signingPrivateKeyPem, True,
                             recentPostsCache, maxRecentPosts,
                             translate, pageNumber, baseDir,
                             session, cachedWebfingers, personCache,
                             nickname, domain, port, messageJson,
                             None, True, allowDeletion,
                             httpPrefix, __version__,
                             'inbox',
                             YTReplacementDomain,
                             twitterReplacementDomain,
                             showPublishedDateOnly,
                             peertubeInstances,
                             allowLocalNetworkAccess,
                             themeName, systemLanguage,
                             maxLikeCount, notDM,
                             showIndividualPostIcons,
                             manuallyApproveFollowers,
                             False, True, False, CWlists,
                             listsEnabled)
    if not announceHtml:
        print('WARN: Unable to generate html for announce ' +
              str(messageJson))
    else:
        if debug:
            print('Generated announce html ' + announceHtml.replace('\n', ''))

    postJsonObject = downloadAnnounce(session, baseDir,
                                      httpPrefix,
                                      nickname, domain,
                                      messageJson,
                                      __version__, translate,
                                      YTReplacementDomain,
                                      twitterReplacementDomain,
                                      allowLocalNetworkAccess,
                                      recentPostsCache, debug,
                                      systemLanguage,
                                      domainFull, personCache,
                                      signingPrivateKeyPem,
                                      blockedCache)
    if not postJsonObject:
        print('WARN: unable to download announce: ' + str(messageJson))
        notInOnion = True
        if onionDomain:
            if onionDomain in messageJson['object']:
                notInOnion = False
        if domain not in messageJson['object'] and notInOnion:
            if os.path.isfile(postFilename):
                # if the announce can't be downloaded then remove it
                try:
                    os.remove(postFilename)
                except BaseException:
                    print('EX: _receiveAnnounce unable to delete ' +
                          str(postFilename))
                    pass
    else:
        if debug:
            print('DEBUG: Announce post downloaded for ' +
                  messageJson['actor'] + ' -> ' + messageJson['object'])
        storeHashTags(baseDir, nickname, domain,
                      httpPrefix, domainFull,
                      postJsonObject, translate)
        # Try to obtain the actor for this person
        # so that their avatar can be shown
        lookupActor = None
        if postJsonObject.get('attributedTo'):
            if isinstance(postJsonObject['attributedTo'], str):
                lookupActor = postJsonObject['attributedTo']
        else:
            if hasObjectDict(postJsonObject):
                if postJsonObject['object'].get('attributedTo'):
                    attrib = postJsonObject['object']['attributedTo']
                    if isinstance(attrib, str):
                        lookupActor = attrib
        if lookupActor:
            if hasUsersPath(lookupActor):
                if '/statuses/' in lookupActor:
                    lookupActor = lookupActor.split('/statuses/')[0]

                if isRecentPost(postJsonObject):
                    if not os.path.isfile(postFilename + '.tts'):
                        domainFull = getFullDomain(domain, port)
                        updateSpeaker(baseDir, httpPrefix,
                                      nickname, domain, domainFull,
                                      postJsonObject, personCache,
                                      translate, lookupActor,
                                      themeName)
                        with open(postFilename + '.tts', 'w+') as ttsFile:
                            ttsFile.write('\n')

                if debug:
                    print('DEBUG: Obtaining actor for announce post ' +
                          lookupActor)
                for tries in range(6):
                    pubKey = \
                        getPersonPubKey(baseDir, session, lookupActor,
                                        personCache, debug,
                                        __version__, httpPrefix,
                                        domain, onionDomain,
                                        signingPrivateKeyPem)
                    if pubKey:
                        if debug:
                            print('DEBUG: public key obtained for announce: ' +
                                  lookupActor)
                        break

                    if debug:
                        print('DEBUG: Retry ' + str(tries + 1) +
                              ' obtaining actor for ' + lookupActor)
                    time.sleep(5)
        if debug:
            print('DEBUG: announced/repeated post arrived in inbox')
    return True


def _receiveUndoAnnounce(recentPostsCache: {},
                         session, handle: str, isGroup: bool, baseDir: str,
                         httpPrefix: str, domain: str, port: int,
                         sendThreads: [], postLog: [], cachedWebfingers: {},
                         personCache: {}, messageJson: {}, federationList: [],
                         debug: bool) -> bool:
    """Receives an undo announce activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Undo':
        return False
    if not hasActor(messageJson, debug):
        return False
    if not hasObjectDict(messageJson):
        return False
    if not hasObjectStringObject(messageJson, debug):
        return False
    if messageJson['object']['type'] != 'Announce':
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  messageJson['type'] + ' announce')
        return False
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of undo announce - ' + handle)
    # if this post in the outbox of the person?
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    postFilename = locatePost(baseDir, handleName, handleDom,
                              messageJson['object']['object'])
    if not postFilename:
        if debug:
            print('DEBUG: undo announce post not found in inbox or outbox')
            print(messageJson['object']['object'])
        return True
    if debug:
        print('DEBUG: announced/repeated post to be undone found in inbox')

    postJsonObject = loadJson(postFilename)
    if postJsonObject:
        if not postJsonObject.get('type'):
            if postJsonObject['type'] != 'Announce':
                if debug:
                    print("DEBUG: Attempt to undo something " +
                          "which isn't an announcement")
                return False
    undoAnnounceCollectionEntry(recentPostsCache, baseDir, postFilename,
                                messageJson['actor'], domain, debug)
    if os.path.isfile(postFilename):
        try:
            os.remove(postFilename)
        except BaseException:
            print('EX: _receiveUndoAnnounce unable to delete ' +
                  str(postFilename))
            pass
    return True


def jsonPostAllowsComments(postJsonObject: {}) -> bool:
    """Returns true if the given post allows comments/replies
    """
    if 'commentsEnabled' in postJsonObject:
        return postJsonObject['commentsEnabled']
    if 'rejectReplies' in postJsonObject:
        return not postJsonObject['rejectReplies']
    if postJsonObject.get('object'):
        if not hasObjectDict(postJsonObject):
            return False
        elif 'commentsEnabled' in postJsonObject['object']:
            return postJsonObject['object']['commentsEnabled']
        elif 'rejectReplies' in postJsonObject['object']:
            return not postJsonObject['object']['rejectReplies']
    return True


def _postAllowsComments(postFilename: str) -> bool:
    """Returns true if the given post allows comments/replies
    """
    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return False
    return jsonPostAllowsComments(postJsonObject)


def populateReplies(baseDir: str, httpPrefix: str, domain: str,
                    messageJson: {}, maxReplies: int, debug: bool) -> bool:
    """Updates the list of replies for a post on this domain if
    a reply to it arrives
    """
    if not messageJson.get('id'):
        return False
    if not hasObjectDict(messageJson):
        return False
    if not messageJson['object'].get('inReplyTo'):
        return False
    if not messageJson['object'].get('to'):
        return False
    replyTo = messageJson['object']['inReplyTo']
    if not isinstance(replyTo, str):
        return False
    if debug:
        print('DEBUG: post contains a reply')
    # is this a reply to a post on this domain?
    if not replyTo.startswith(httpPrefix + '://' + domain + '/'):
        if debug:
            print('DEBUG: post is a reply to another not on this domain')
            print(replyTo)
            print('Expected: ' + httpPrefix + '://' + domain + '/')
        return False
    replyToNickname = getNicknameFromActor(replyTo)
    if not replyToNickname:
        print('DEBUG: no nickname found for ' + replyTo)
        return False
    replyToDomain, replyToPort = getDomainFromActor(replyTo)
    if not replyToDomain:
        if debug:
            print('DEBUG: no domain found for ' + replyTo)
        return False

    postFilename = locatePost(baseDir, replyToNickname,
                              replyToDomain, replyTo)
    if not postFilename:
        if debug:
            print('DEBUG: post may have expired - ' + replyTo)
        return False

    if not _postAllowsComments(postFilename):
        if debug:
            print('DEBUG: post does not allow comments - ' + replyTo)
        return False
    # populate a text file containing the ids of replies
    postRepliesFilename = postFilename.replace('.json', '.replies')
    messageId = removeIdEnding(messageJson['id'])
    if os.path.isfile(postRepliesFilename):
        numLines = sum(1 for line in open(postRepliesFilename))
        if numLines > maxReplies:
            return False
        if messageId not in open(postRepliesFilename).read():
            with open(postRepliesFilename, 'a+') as repliesFile:
                repliesFile.write(messageId + '\n')
    else:
        with open(postRepliesFilename, 'w+') as repliesFile:
            repliesFile.write(messageId + '\n')
    return True


def _estimateNumberOfMentions(content: str) -> int:
    """Returns a rough estimate of the number of mentions
    """
    return int(content.count('@') / 2)


def _estimateNumberOfEmoji(content: str) -> int:
    """Returns a rough estimate of the number of emoji
    """
    return int(content.count(':') / 2)


def _validPostContent(baseDir: str, nickname: str, domain: str,
                      messageJson: {}, maxMentions: int, maxEmoji: int,
                      allowLocalNetworkAccess: bool, debug: bool,
                      systemLanguage: str,
                      httpPrefix: str, domainFull: str,
                      personCache: {}) -> bool:
    """Is the content of a received post valid?
    Check for bad html
    Check for hellthreads
    Check number of tags is reasonable
    """
    if not hasObjectDict(messageJson):
        return True
    if not messageJson['object'].get('content'):
        return True

    if not messageJson['object'].get('published'):
        return False
    if 'T' not in messageJson['object']['published']:
        return False
    if 'Z' not in messageJson['object']['published']:
        return False
    if not validPostDate(messageJson['object']['published'], 90, debug):
        return False

    summary = None
    if messageJson['object'].get('summary'):
        summary = messageJson['object']['summary']
        if not isinstance(summary, str):
            print('WARN: content warning is not a string')
            return False
        if summary != validContentWarning(summary):
            print('WARN: invalid content warning ' + summary)
            return False

    # check for patches before dangeousMarkup, which excludes code
    if isGitPatch(baseDir, nickname, domain,
                  messageJson['object']['type'],
                  summary,
                  messageJson['object']['content']):
        return True

    contentStr = getBaseContentFromPost(messageJson, systemLanguage)
    if dangerousMarkup(contentStr, allowLocalNetworkAccess):
        if messageJson['object'].get('id'):
            print('REJECT ARBITRARY HTML: ' + messageJson['object']['id'])
        print('REJECT ARBITRARY HTML: bad string in post - ' +
              contentStr)
        return False

    # check (rough) number of mentions
    mentionsEst = _estimateNumberOfMentions(contentStr)
    if mentionsEst > maxMentions:
        if messageJson['object'].get('id'):
            print('REJECT HELLTHREAD: ' + messageJson['object']['id'])
        print('REJECT HELLTHREAD: Too many mentions in post - ' +
              contentStr)
        return False
    if _estimateNumberOfEmoji(contentStr) > maxEmoji:
        if messageJson['object'].get('id'):
            print('REJECT EMOJI OVERLOAD: ' + messageJson['object']['id'])
        print('REJECT EMOJI OVERLOAD: Too many emoji in post - ' +
              contentStr)
        return False
    # check number of tags
    if messageJson['object'].get('tag'):
        if not isinstance(messageJson['object']['tag'], list):
            messageJson['object']['tag'] = []
        else:
            if len(messageJson['object']['tag']) > int(maxMentions * 2):
                if messageJson['object'].get('id'):
                    print('REJECT: ' + messageJson['object']['id'])
                print('REJECT: Too many tags in post - ' +
                      messageJson['object']['tag'])
                return False
    # check that the post is in a language suitable for this account
    if not understoodPostLanguage(baseDir, nickname, domain,
                                  messageJson, systemLanguage,
                                  httpPrefix, domainFull,
                                  personCache):
        return False
    # check for filtered content
    if isFiltered(baseDir, nickname, domain, contentStr):
        print('REJECT: content filtered')
        return False
    if messageJson['object'].get('inReplyTo'):
        if isinstance(messageJson['object']['inReplyTo'], str):
            originalPostId = messageJson['object']['inReplyTo']
            postPostFilename = locatePost(baseDir, nickname, domain,
                                          originalPostId)
            if postPostFilename:
                if not _postAllowsComments(postPostFilename):
                    print('REJECT: reply to post which does not ' +
                          'allow comments: ' + originalPostId)
                    return False
    if debug:
        print('ACCEPT: post content is valid')
    return True


def _obtainAvatarForReplyPost(session, baseDir: str, httpPrefix: str,
                              domain: str, onionDomain: str, personCache: {},
                              postJsonObject: {}, debug: bool,
                              signingPrivateKeyPem: str) -> None:
    """Tries to obtain the actor for the person being replied to
    so that their avatar can later be shown
    """
    if not hasObjectDict(postJsonObject):
        return

    if not postJsonObject['object'].get('inReplyTo'):
        return

    lookupActor = postJsonObject['object']['inReplyTo']
    if not lookupActor:
        return

    if not isinstance(lookupActor, str):
        return

    if not hasUsersPath(lookupActor):
        return

    if '/statuses/' in lookupActor:
        lookupActor = lookupActor.split('/statuses/')[0]

    if debug:
        print('DEBUG: Obtaining actor for reply post ' + lookupActor)

    for tries in range(6):
        pubKey = \
            getPersonPubKey(baseDir, session, lookupActor,
                            personCache, debug,
                            __version__, httpPrefix,
                            domain, onionDomain, signingPrivateKeyPem)
        if pubKey:
            if debug:
                print('DEBUG: public key obtained for reply: ' + lookupActor)
            break

        if debug:
            print('DEBUG: Retry ' + str(tries + 1) +
                  ' obtaining actor for ' + lookupActor)
        time.sleep(5)


def _dmNotify(baseDir: str, handle: str, url: str) -> None:
    """Creates a notification that a new DM has arrived
    """
    accountDir = baseDir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return
    dmFile = accountDir + '/.newDM'
    if not os.path.isfile(dmFile):
        with open(dmFile, 'w+') as fp:
            fp.write(url)


def _alreadyLiked(baseDir: str, nickname: str, domain: str,
                  postUrl: str, likerActor: str) -> bool:
    """Is the given post already liked by the given handle?
    """
    postFilename = \
        locatePost(baseDir, nickname, domain, postUrl)
    if not postFilename:
        return False
    postJsonObject = loadJson(postFilename, 1)
    if not postJsonObject:
        return False
    if not hasObjectDict(postJsonObject):
        return False
    if not postJsonObject['object'].get('likes'):
        return False
    if not postJsonObject['object']['likes'].get('items'):
        return False
    for like in postJsonObject['object']['likes']['items']:
        if not like.get('type'):
            continue
        if not like.get('actor'):
            continue
        if like['type'] != 'Like':
            continue
        if like['actor'] == likerActor:
            return True
    return False


def _likeNotify(baseDir: str, domain: str, onionDomain: str,
                handle: str, actor: str, url: str) -> None:
    """Creates a notification that a like has arrived
    """
    # This is not you liking your own post
    if actor in url:
        return

    # check that the liked post was by this handle
    nickname = handle.split('@')[0]
    if '/' + domain + '/users/' + nickname not in url:
        if not onionDomain:
            return
        if '/' + onionDomain + '/users/' + nickname not in url:
            return

    accountDir = baseDir + '/accounts/' + handle

    # are like notifications enabled?
    notifyLikesEnabledFilename = accountDir + '/.notifyLikes'
    if not os.path.isfile(notifyLikesEnabledFilename):
        return

    likeFile = accountDir + '/.newLike'
    if os.path.isfile(likeFile):
        if '##sent##' not in open(likeFile).read():
            return

    likerNickname = getNicknameFromActor(actor)
    likerDomain, likerPort = getDomainFromActor(actor)
    if likerNickname and likerDomain:
        likerHandle = likerNickname + '@' + likerDomain
    else:
        print('_likeNotify likerHandle: ' +
              str(likerNickname) + '@' + str(likerDomain))
        likerHandle = actor
    if likerHandle != handle:
        likeStr = likerHandle + ' ' + url + '?likedBy=' + actor
        prevLikeFile = accountDir + '/.prevLike'
        # was there a previous like notification?
        if os.path.isfile(prevLikeFile):
            # is it the same as the current notification ?
            with open(prevLikeFile, 'r') as fp:
                prevLikeStr = fp.read()
                if prevLikeStr == likeStr:
                    return
        try:
            with open(prevLikeFile, 'w+') as fp:
                fp.write(likeStr)
        except BaseException:
            print('EX: ERROR: unable to save previous like notification ' +
                  prevLikeFile)
            pass
        try:
            with open(likeFile, 'w+') as fp:
                fp.write(likeStr)
        except BaseException:
            print('EX: ERROR: unable to write like notification file ' +
                  likeFile)
            pass


def _notifyPostArrival(baseDir: str, handle: str, url: str) -> None:
    """Creates a notification that a new post has arrived.
    This is for followed accounts with the notify checkbox enabled
    on the person options screen
    """
    accountDir = baseDir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return
    notifyFile = accountDir + '/.newNotifiedPost'
    if os.path.isfile(notifyFile):
        # check that the same notification is not repeatedly sent
        with open(notifyFile, 'r') as fp:
            existingNotificationMessage = fp.read()
            if url in existingNotificationMessage:
                return
    with open(notifyFile, 'w+') as fp:
        fp.write(url)


def _replyNotify(baseDir: str, handle: str, url: str) -> None:
    """Creates a notification that a new reply has arrived
    """
    accountDir = baseDir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return
    replyFile = accountDir + '/.newReply'
    if not os.path.isfile(replyFile):
        with open(replyFile, 'w+') as fp:
            fp.write(url)


def _gitPatchNotify(baseDir: str, handle: str,
                    subject: str, content: str,
                    fromNickname: str, fromDomain: str) -> None:
    """Creates a notification that a new git patch has arrived
    """
    accountDir = baseDir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return
    patchFile = accountDir + '/.newPatch'
    subject = subject.replace('[PATCH]', '').strip()
    handle = '@' + fromNickname + '@' + fromDomain
    with open(patchFile, 'w+') as fp:
        fp.write('git ' + handle + ' ' + subject)


def _groupHandle(baseDir: str, handle: str) -> bool:
    """Is the given account handle a group?
    """
    actorFile = baseDir + '/accounts/' + handle + '.json'
    if not os.path.isfile(actorFile):
        return False
    actorJson = loadJson(actorFile)
    if not actorJson:
        return False
    return actorJson['type'] == 'Group'


def _sendToGroupMembers(session, baseDir: str, handle: str, port: int,
                        postJsonObject: {},
                        httpPrefix: str, federationList: [],
                        sendThreads: [], postLog: [], cachedWebfingers: {},
                        personCache: {}, debug: bool,
                        systemLanguage: str,
                        onionDomain: str, i2pDomain: str,
                        signingPrivateKeyPem: str) -> None:
    """When a post arrives for a group send it out to the group members
    """
    if debug:
        print('\n\n=========================================================')
        print(handle + ' sending to group members')

    sharedItemFederationTokens = {}
    sharedItemsFederatedDomains = []
    sharedItemsFederatedDomainsStr = \
        getConfigParam(baseDir, 'sharedItemsFederatedDomains')
    if sharedItemsFederatedDomainsStr:
        siFederatedDomainsList = \
            sharedItemsFederatedDomainsStr.split(',')
        for sharedFederatedDomain in siFederatedDomainsList:
            domainStr = sharedFederatedDomain.strip()
            sharedItemsFederatedDomains.append(domainStr)

    followersFile = baseDir + '/accounts/' + handle + '/followers.txt'
    if not os.path.isfile(followersFile):
        return
    if not postJsonObject.get('to'):
        return
    if not postJsonObject.get('object'):
        return
    if not hasObjectDict(postJsonObject):
        return
    nickname = handle.split('@')[0].replace('!', '')
    domain = handle.split('@')[1]
    domainFull = getFullDomain(domain, port)
    groupActor = localActorUrl(httpPrefix, nickname, domainFull)
    if groupActor not in postJsonObject['to']:
        return
    cc = ''
    nickname = handle.split('@')[0].replace('!', '')

    # save to the group outbox so that replies will be to the group
    # rather than the original sender
    savePostToBox(baseDir, httpPrefix, None,
                  nickname, domain, postJsonObject, 'outbox')

    postId = removeIdEnding(postJsonObject['object']['id'])
    if debug:
        print('Group announce: ' + postId)
    announceJson = \
        createAnnounce(session, baseDir, federationList,
                       nickname, domain, port,
                       groupActor + '/followers', cc,
                       httpPrefix, postId, False, False,
                       sendThreads, postLog,
                       personCache, cachedWebfingers,
                       debug, __version__, signingPrivateKeyPem)

    sendToFollowersThread(session, baseDir, nickname, domain,
                          onionDomain, i2pDomain, port,
                          httpPrefix, federationList,
                          sendThreads, postLog,
                          cachedWebfingers, personCache,
                          announceJson, debug, __version__,
                          sharedItemsFederatedDomains,
                          sharedItemFederationTokens,
                          signingPrivateKeyPem)


def _inboxUpdateCalendar(baseDir: str, handle: str,
                         postJsonObject: {}) -> None:
    """Detects whether the tag list on a post contains calendar events
    and if so saves the post id to a file in the calendar directory
    for the account
    """
    if not postJsonObject.get('actor'):
        return
    if not hasObjectDict(postJsonObject):
        return
    if not postJsonObject['object'].get('tag'):
        return
    if not isinstance(postJsonObject['object']['tag'], list):
        return

    actor = postJsonObject['actor']
    actorNickname = getNicknameFromActor(actor)
    actorDomain, actorPort = getDomainFromActor(actor)
    handleNickname = handle.split('@')[0]
    handleDomain = handle.split('@')[1]
    if not receivingCalendarEvents(baseDir,
                                   handleNickname, handleDomain,
                                   actorNickname, actorDomain):
        return

    postId = removeIdEnding(postJsonObject['id']).replace('/', '#')

    # look for events within the tags list
    for tagDict in postJsonObject['object']['tag']:
        if not tagDict.get('type'):
            continue
        if tagDict['type'] != 'Event':
            continue
        if not tagDict.get('startTime'):
            continue
        saveEventPost(baseDir, handle, postId, tagDict)


def inboxUpdateIndex(boxname: str, baseDir: str, handle: str,
                     destinationFilename: str, debug: bool) -> bool:
    """Updates the index of received posts
    The new entry is added to the top of the file
    """
    indexFilename = baseDir + '/accounts/' + handle + '/' + boxname + '.index'
    if debug:
        print('DEBUG: Updating index ' + indexFilename)

    if '/' + boxname + '/' in destinationFilename:
        destinationFilename = destinationFilename.split('/' + boxname + '/')[1]

    # remove the path
    if '/' in destinationFilename:
        destinationFilename = destinationFilename.split('/')[-1]

    written = False
    if os.path.isfile(indexFilename):
        try:
            with open(indexFilename, 'r+') as indexFile:
                content = indexFile.read()
                if destinationFilename + '\n' not in content:
                    indexFile.seek(0, 0)
                    indexFile.write(destinationFilename + '\n' + content)
                written = True
                return True
        except Exception as e:
            print('WARN: Failed to write entry to index ' + str(e))
    else:
        try:
            with open(indexFilename, 'w+') as indexFile:
                indexFile.write(destinationFilename + '\n')
                written = True
        except Exception as e:
            print('WARN: Failed to write initial entry to index ' + str(e))

    return written


def _updateLastSeen(baseDir: str, handle: str, actor: str) -> None:
    """Updates the time when the given handle last saw the given actor
    This can later be used to indicate if accounts are dormant/abandoned/moved
    """
    if '@' not in handle:
        return
    nickname = handle.split('@')[0]
    domain = handle.split('@')[1]
    domain = removeDomainPort(domain)
    accountPath = acctDir(baseDir, nickname, domain)
    if not os.path.isdir(accountPath):
        return
    if not isFollowingActor(baseDir, nickname, domain, actor):
        return
    lastSeenPath = accountPath + '/lastseen'
    if not os.path.isdir(lastSeenPath):
        os.mkdir(lastSeenPath)
    lastSeenFilename = lastSeenPath + '/' + actor.replace('/', '#') + '.txt'
    currTime = datetime.datetime.utcnow()
    daysSinceEpoch = (currTime - datetime.datetime(1970, 1, 1)).days
    # has the value changed?
    if os.path.isfile(lastSeenFilename):
        with open(lastSeenFilename, 'r') as lastSeenFile:
            daysSinceEpochFile = lastSeenFile.read()
            if int(daysSinceEpochFile) == daysSinceEpoch:
                # value hasn't changed, so we can save writing anything to file
                return
    with open(lastSeenFilename, 'w+') as lastSeenFile:
        lastSeenFile.write(str(daysSinceEpoch))


def _bounceDM(senderPostId: str, session, httpPrefix: str,
              baseDir: str, nickname: str, domain: str, port: int,
              sendingHandle: str, federationList: [],
              sendThreads: [], postLog: [],
              cachedWebfingers: {}, personCache: {},
              translate: {}, debug: bool,
              lastBounceMessage: [], systemLanguage: str,
              signingPrivateKeyPem: str) -> bool:
    """Sends a bounce message back to the sending handle
    if a DM has been rejected
    """
    print(nickname + '@' + domain +
          ' cannot receive DM from ' + sendingHandle +
          ' because they do not follow them')

    # Don't send out bounce messages too frequently.
    # Otherwise an adversary could try to DoS your instance
    # by continuously sending DMs to you
    currTime = int(time.time())
    if currTime - lastBounceMessage[0] < 60:
        return False

    # record the last time that a bounce was generated
    lastBounceMessage[0] = currTime

    senderNickname = sendingHandle.split('@')[0]
    groupAccount = False
    if sendingHandle.startswith('!'):
        sendingHandle = sendingHandle[1:]
        groupAccount = True
    senderDomain = sendingHandle.split('@')[1]
    senderPort = port
    if ':' in senderDomain:
        senderPort = getPortFromDomain(senderDomain)
        senderDomain = removeDomainPort(senderDomain)
    cc = []

    # create the bounce DM
    subject = None
    content = translate['DM bounce']
    followersOnly = False
    saveToFile = False
    clientToServer = False
    commentsEnabled = False
    attachImageFilename = None
    mediaType = None
    imageDescription = ''
    city = 'London, England'
    inReplyTo = removeIdEnding(senderPostId)
    inReplyToAtomUri = None
    schedulePost = False
    eventDate = None
    eventTime = None
    location = None
    conversationId = None
    lowBandwidth = False
    postJsonObject = \
        createDirectMessagePost(baseDir, nickname, domain, port,
                                httpPrefix, content, followersOnly,
                                saveToFile, clientToServer,
                                commentsEnabled,
                                attachImageFilename, mediaType,
                                imageDescription, city,
                                inReplyTo, inReplyToAtomUri,
                                subject, debug, schedulePost,
                                eventDate, eventTime, location,
                                systemLanguage, conversationId, lowBandwidth)
    if not postJsonObject:
        print('WARN: unable to create bounce message to ' + sendingHandle)
        return False
    # bounce DM goes back to the sender
    print('Sending bounce DM to ' + sendingHandle)
    sendSignedJson(postJsonObject, session, baseDir,
                   nickname, domain, port,
                   senderNickname, senderDomain, senderPort, cc,
                   httpPrefix, False, False, federationList,
                   sendThreads, postLog, cachedWebfingers,
                   personCache, debug, __version__, None, groupAccount,
                   signingPrivateKeyPem, 7238634)
    return True


def _isValidDM(baseDir: str, nickname: str, domain: str, port: int,
               postJsonObject: {}, updateIndexList: [],
               session, httpPrefix: str,
               federationList: [],
               sendThreads: [], postLog: [],
               cachedWebfingers: {},
               personCache: {},
               translate: {}, debug: bool,
               lastBounceMessage: [],
               handle: str, systemLanguage: str,
               signingPrivateKeyPem: str) -> bool:
    """Is the given message a valid DM?
    """
    if nickname == 'inbox':
        # going to the shared inbox
        return True

    # check for the flag file which indicates to
    # only receive DMs from people you are following
    followDMsFilename = acctDir(baseDir, nickname, domain) + '/.followDMs'
    if not os.path.isfile(followDMsFilename):
        # dm index will be updated
        updateIndexList.append('dm')
        actUrl = localActorUrl(httpPrefix, nickname, domain)
        _dmNotify(baseDir, handle, actUrl + '/dm')
        return True

    # get the file containing following handles
    followingFilename = acctDir(baseDir, nickname, domain) + '/following.txt'
    # who is sending a DM?
    if not postJsonObject.get('actor'):
        return False
    sendingActor = postJsonObject['actor']
    sendingActorNickname = \
        getNicknameFromActor(sendingActor)
    if not sendingActorNickname:
        return False
    sendingActorDomain, sendingActorPort = \
        getDomainFromActor(sendingActor)
    if not sendingActorDomain:
        return False
    # Is this DM to yourself? eg. a reminder
    sendingToSelf = False
    if sendingActorNickname == nickname and \
       sendingActorDomain == domain:
        sendingToSelf = True

    # check that the following file exists
    if not sendingToSelf:
        if not os.path.isfile(followingFilename):
            print('No following.txt file exists for ' +
                  nickname + '@' + domain +
                  ' so not accepting DM from ' +
                  sendingActorNickname + '@' +
                  sendingActorDomain)
            return False

    # Not sending to yourself
    if not sendingToSelf:
        # get the handle of the DM sender
        sendH = sendingActorNickname + '@' + sendingActorDomain
        # check the follow
        if not isFollowingActor(baseDir, nickname, domain, sendH):
            # DMs may always be allowed from some domains
            if not dmAllowedFromDomain(baseDir,
                                       nickname, domain,
                                       sendingActorDomain):
                # send back a bounce DM
                if postJsonObject.get('id') and \
                   postJsonObject.get('object'):
                    # don't send bounces back to
                    # replies to bounce messages
                    obj = postJsonObject['object']
                    if isinstance(obj, dict):
                        if not obj.get('inReplyTo'):
                            bouncedId = removeIdEnding(postJsonObject['id'])
                            _bounceDM(bouncedId,
                                      session, httpPrefix,
                                      baseDir,
                                      nickname, domain,
                                      port, sendH,
                                      federationList,
                                      sendThreads, postLog,
                                      cachedWebfingers,
                                      personCache,
                                      translate, debug,
                                      lastBounceMessage,
                                      systemLanguage,
                                      signingPrivateKeyPem)
                return False

    # dm index will be updated
    updateIndexList.append('dm')
    actUrl = localActorUrl(httpPrefix, nickname, domain)
    _dmNotify(baseDir, handle, actUrl + '/dm')
    return True


def _inboxAfterInitial(recentPostsCache: {}, maxRecentPosts: int,
                       session, keyId: str, handle: str, messageJson: {},
                       baseDir: str, httpPrefix: str, sendThreads: [],
                       postLog: [], cachedWebfingers: {}, personCache: {},
                       queue: [], domain: str,
                       onionDomain: str, i2pDomain: str,
                       port: int, proxyType: str,
                       federationList: [], debug: bool,
                       queueFilename: str, destinationFilename: str,
                       maxReplies: int, allowDeletion: bool,
                       maxMentions: int, maxEmoji: int, translate: {},
                       unitTest: bool,
                       YTReplacementDomain: str,
                       twitterReplacementDomain: str,
                       showPublishedDateOnly: bool,
                       allowLocalNetworkAccess: bool,
                       peertubeInstances: [],
                       lastBounceMessage: [],
                       themeName: str, systemLanguage: str,
                       maxLikeCount: int,
                       signingPrivateKeyPem: str,
                       defaultReplyIntervalHours: int,
                       CWlists: {}, listsEnabled: str) -> bool:
    """ Anything which needs to be done after initial checks have passed
    """
    actor = keyId
    if '#' in actor:
        actor = keyId.split('#')[0]

    _updateLastSeen(baseDir, handle, actor)

    postIsDM = False
    isGroup = _groupHandle(baseDir, handle)

    if _receiveLike(recentPostsCache,
                    session, handle, isGroup,
                    baseDir, httpPrefix,
                    domain, port,
                    onionDomain,
                    sendThreads, postLog,
                    cachedWebfingers,
                    personCache,
                    messageJson,
                    federationList,
                    debug, signingPrivateKeyPem,
                    maxRecentPosts, translate,
                    allowDeletion,
                    YTReplacementDomain,
                    twitterReplacementDomain,
                    peertubeInstances,
                    allowLocalNetworkAccess,
                    themeName, systemLanguage,
                    maxLikeCount, CWlists, listsEnabled):
        if debug:
            print('DEBUG: Like accepted from ' + actor)
        return False

    if _receiveUndoLike(recentPostsCache,
                        session, handle, isGroup,
                        baseDir, httpPrefix,
                        domain, port,
                        sendThreads, postLog,
                        cachedWebfingers,
                        personCache,
                        messageJson,
                        federationList,
                        debug, signingPrivateKeyPem,
                        maxRecentPosts, translate,
                        allowDeletion,
                        YTReplacementDomain,
                        twitterReplacementDomain,
                        peertubeInstances,
                        allowLocalNetworkAccess,
                        themeName, systemLanguage,
                        maxLikeCount, CWlists, listsEnabled):
        if debug:
            print('DEBUG: Undo like accepted from ' + actor)
        return False

    if _receiveBookmark(recentPostsCache,
                        session, handle, isGroup,
                        baseDir, httpPrefix,
                        domain, port,
                        sendThreads, postLog,
                        cachedWebfingers,
                        personCache,
                        messageJson,
                        federationList,
                        debug, signingPrivateKeyPem,
                        maxRecentPosts, translate,
                        allowDeletion,
                        YTReplacementDomain,
                        twitterReplacementDomain,
                        peertubeInstances,
                        allowLocalNetworkAccess,
                        themeName, systemLanguage,
                        maxLikeCount, CWlists, listsEnabled):
        if debug:
            print('DEBUG: Bookmark accepted from ' + actor)
        return False

    if _receiveUndoBookmark(recentPostsCache,
                            session, handle, isGroup,
                            baseDir, httpPrefix,
                            domain, port,
                            sendThreads, postLog,
                            cachedWebfingers,
                            personCache,
                            messageJson,
                            federationList,
                            debug, signingPrivateKeyPem,
                            maxRecentPosts, translate,
                            allowDeletion,
                            YTReplacementDomain,
                            twitterReplacementDomain,
                            peertubeInstances,
                            allowLocalNetworkAccess,
                            themeName, systemLanguage,
                            maxLikeCount, CWlists, listsEnabled):
        if debug:
            print('DEBUG: Undo bookmark accepted from ' + actor)
        return False

    if isCreateInsideAnnounce(messageJson):
        messageJson = messageJson['object']

    if _receiveAnnounce(recentPostsCache,
                        session, handle, isGroup,
                        baseDir, httpPrefix,
                        domain, onionDomain, port,
                        sendThreads, postLog,
                        cachedWebfingers,
                        personCache,
                        messageJson,
                        federationList,
                        debug, translate,
                        YTReplacementDomain,
                        twitterReplacementDomain,
                        allowLocalNetworkAccess,
                        themeName, systemLanguage,
                        signingPrivateKeyPem,
                        maxRecentPosts,
                        allowDeletion,
                        peertubeInstances,
                        maxLikeCount, CWlists, listsEnabled):
        if debug:
            print('DEBUG: Announce accepted from ' + actor)

    if _receiveUndoAnnounce(recentPostsCache,
                            session, handle, isGroup,
                            baseDir, httpPrefix,
                            domain, port,
                            sendThreads, postLog,
                            cachedWebfingers,
                            personCache,
                            messageJson,
                            federationList,
                            debug):
        if debug:
            print('DEBUG: Undo announce accepted from ' + actor)
        return False

    if _receiveDelete(session, handle, isGroup,
                      baseDir, httpPrefix,
                      domain, port,
                      sendThreads, postLog,
                      cachedWebfingers,
                      personCache,
                      messageJson,
                      federationList,
                      debug, allowDeletion,
                      recentPostsCache):
        if debug:
            print('DEBUG: Delete accepted from ' + actor)
        return False

    if debug:
        print('DEBUG: initial checks passed')
        print('copy queue file from ' + queueFilename +
              ' to ' + destinationFilename)

    if os.path.isfile(destinationFilename):
        return True

    if messageJson.get('postNickname'):
        postJsonObject = messageJson['post']
    else:
        postJsonObject = messageJson

    nickname = handle.split('@')[0]
    jsonObj = None
    domainFull = getFullDomain(domain, port)
    if _validPostContent(baseDir, nickname, domain,
                         postJsonObject, maxMentions, maxEmoji,
                         allowLocalNetworkAccess, debug,
                         systemLanguage, httpPrefix,
                         domainFull, personCache):

        if postJsonObject.get('object'):
            jsonObj = postJsonObject['object']
            if not isinstance(jsonObj, dict):
                jsonObj = None
        else:
            jsonObj = postJsonObject
        # check for incoming git patches
        if jsonObj:
            if jsonObj.get('content') and \
               jsonObj.get('summary') and \
               jsonObj.get('attributedTo'):
                attributedTo = jsonObj['attributedTo']
                if isinstance(attributedTo, str):
                    fromNickname = getNicknameFromActor(attributedTo)
                    fromDomain, fromPort = getDomainFromActor(attributedTo)
                    fromDomain = getFullDomain(fromDomain, fromPort)
                    if receiveGitPatch(baseDir, nickname, domain,
                                       jsonObj['type'],
                                       jsonObj['summary'],
                                       jsonObj['content'],
                                       fromNickname, fromDomain):
                        _gitPatchNotify(baseDir, handle,
                                        jsonObj['summary'],
                                        jsonObj['content'],
                                        fromNickname, fromDomain)
                    elif '[PATCH]' in jsonObj['content']:
                        print('WARN: git patch not accepted - ' +
                              jsonObj['summary'])
                        return False

        # replace YouTube links, so they get less tracking data
        replaceYouTube(postJsonObject, YTReplacementDomain, systemLanguage)
        # replace twitter link domains, so that you can view twitter posts
        # without having an account
        replaceTwitter(postJsonObject, twitterReplacementDomain,
                       systemLanguage)

        # list of indexes to be updated
        updateIndexList = ['inbox']
        populateReplies(baseDir, httpPrefix, domain, postJsonObject,
                        maxReplies, debug)

        # if this is a reply to a question then update the votes
        questionJson = questionUpdateVotes(baseDir, nickname, domain,
                                           postJsonObject)
        if questionJson:
            # Is this a question created by this instance?
            idPrefix = httpPrefix + '://' + domain
            if questionJson['object']['id'].startswith(idPrefix):
                # if the votes on a question have changed then
                # send out an update
                questionJson['type'] = 'Update'
                sharedItemsFederatedDomains = []
                sharedItemFederationTokens = {}

                sharedItemFederationTokens = {}
                sharedItemsFederatedDomains = []
                sharedItemsFederatedDomainsStr = \
                    getConfigParam(baseDir, 'sharedItemsFederatedDomains')
                if sharedItemsFederatedDomainsStr:
                    siFederatedDomainsList = \
                        sharedItemsFederatedDomainsStr.split(',')
                    for sharedFederatedDomain in siFederatedDomainsList:
                        domainStr = sharedFederatedDomain.strip()
                        sharedItemsFederatedDomains.append(domainStr)

                sendToFollowersThread(session, baseDir,
                                      nickname, domain,
                                      onionDomain, i2pDomain, port,
                                      httpPrefix, federationList,
                                      sendThreads, postLog,
                                      cachedWebfingers, personCache,
                                      postJsonObject, debug,
                                      __version__,
                                      sharedItemsFederatedDomains,
                                      sharedItemFederationTokens,
                                      signingPrivateKeyPem)

        isReplyToMutedPost = False

        if not isGroup:
            # create a DM notification file if needed
            postIsDM = isDM(postJsonObject)
            if postIsDM:
                if not _isValidDM(baseDir, nickname, domain, port,
                                  postJsonObject, updateIndexList,
                                  session, httpPrefix,
                                  federationList,
                                  sendThreads, postLog,
                                  cachedWebfingers,
                                  personCache,
                                  translate, debug,
                                  lastBounceMessage,
                                  handle, systemLanguage,
                                  signingPrivateKeyPem):
                    return False

            # get the actor being replied to
            actor = localActorUrl(httpPrefix, nickname, domainFull)

            # create a reply notification file if needed
            if not postIsDM and isReply(postJsonObject, actor):
                if nickname != 'inbox':
                    # replies index will be updated
                    updateIndexList.append('tlreplies')

                    conversationId = None
                    if postJsonObject['object'].get('conversation'):
                        conversationId = \
                            postJsonObject['object']['conversation']

                    if postJsonObject['object'].get('inReplyTo'):
                        inReplyTo = postJsonObject['object']['inReplyTo']
                        if inReplyTo:
                            if isinstance(inReplyTo, str):
                                if not isMuted(baseDir, nickname, domain,
                                               inReplyTo, conversationId):
                                    # check if the reply is within the allowed
                                    # time period after publication
                                    hrs = defaultReplyIntervalHours
                                    replyIntervalHours = \
                                        getReplyIntervalHours(baseDir,
                                                              nickname,
                                                              domain, hrs)
                                    if canReplyTo(baseDir, nickname, domain,
                                                  inReplyTo,
                                                  replyIntervalHours):
                                        actUrl = \
                                            localActorUrl(httpPrefix,
                                                          nickname, domain)
                                        _replyNotify(baseDir, handle,
                                                     actUrl + '/tlreplies')
                                    else:
                                        if debug:
                                            print('Reply to ' + inReplyTo +
                                                  ' is outside of the ' +
                                                  'permitted interval of ' +
                                                  str(replyIntervalHours) +
                                                  ' hours')
                                        return False
                                else:
                                    isReplyToMutedPost = True

            if isImageMedia(session, baseDir, httpPrefix,
                            nickname, domain, postJsonObject,
                            translate,
                            YTReplacementDomain,
                            twitterReplacementDomain,
                            allowLocalNetworkAccess,
                            recentPostsCache, debug, systemLanguage,
                            domainFull, personCache, signingPrivateKeyPem):
                # media index will be updated
                updateIndexList.append('tlmedia')
            if isBlogPost(postJsonObject):
                # blogs index will be updated
                updateIndexList.append('tlblogs')

        # get the avatar for a reply/announce
        _obtainAvatarForReplyPost(session, baseDir,
                                  httpPrefix, domain, onionDomain,
                                  personCache, postJsonObject, debug,
                                  signingPrivateKeyPem)

        # save the post to file
        if saveJson(postJsonObject, destinationFilename):
            # should we notify that a post from this person has arrived?
            # This is for cases where the notify checkbox is enabled
            # on the person options screen
            if not postIsDM and jsonObj:
                if jsonObj.get('attributedTo') and jsonObj.get('id'):
                    attributedTo = jsonObj['attributedTo']
                    if isinstance(attributedTo, str):
                        fromNickname = getNicknameFromActor(attributedTo)
                        fromDomain, fromPort = getDomainFromActor(attributedTo)
                        fromDomainFull = getFullDomain(fromDomain, fromPort)
                        if notifyWhenPersonPosts(baseDir, nickname, domain,
                                                 fromNickname, fromDomainFull):
                            postId = removeIdEnding(jsonObj['id'])
                            domFull = getFullDomain(domain, port)
                            postLink = \
                                localActorUrl(httpPrefix,
                                              nickname, domFull) + \
                                '?notifypost=' + postId.replace('/', '-')
                            _notifyPostArrival(baseDir, handle, postLink)

            # If this is a reply to a muted post then also mute it.
            # This enables you to ignore a threat that's getting boring
            if isReplyToMutedPost:
                print('MUTE REPLY: ' + destinationFilename)
                with open(destinationFilename + '.muted', 'w+') as muteFile:
                    muteFile.write('\n')

            # update the indexes for different timelines
            for boxname in updateIndexList:
                if not inboxUpdateIndex(boxname, baseDir, handle,
                                        destinationFilename, debug):
                    print('ERROR: unable to update ' + boxname + ' index')
                else:
                    if boxname == 'inbox':
                        if isRecentPost(postJsonObject):
                            domainFull = getFullDomain(domain, port)
                            updateSpeaker(baseDir, httpPrefix,
                                          nickname, domain, domainFull,
                                          postJsonObject, personCache,
                                          translate, None, themeName)
                    if not unitTest:
                        if debug:
                            print('Saving inbox post as html to cache')

                        htmlCacheStartTime = time.time()
                        handleName = handle.split('@')[0]
                        _inboxStorePostToHtmlCache(recentPostsCache,
                                                   maxRecentPosts,
                                                   translate, baseDir,
                                                   httpPrefix,
                                                   session, cachedWebfingers,
                                                   personCache,
                                                   handleName,
                                                   domain, port,
                                                   postJsonObject,
                                                   allowDeletion,
                                                   boxname,
                                                   showPublishedDateOnly,
                                                   peertubeInstances,
                                                   allowLocalNetworkAccess,
                                                   themeName, systemLanguage,
                                                   maxLikeCount,
                                                   signingPrivateKeyPem,
                                                   CWlists, listsEnabled)
                        if debug:
                            timeDiff = \
                                str(int((time.time() - htmlCacheStartTime) *
                                        1000))
                            print('Saved ' + boxname +
                                  ' post as html to cache in ' +
                                  timeDiff + ' mS')

            handleName = handle.split('@')[0]

            # is this an edit of a previous post?
            # in Mastodon "delete and redraft"
            # NOTE: this must be done before updateConversation is called
            editedFilename = \
                editedPostFilename(baseDir, handleName, domain,
                                   postJsonObject, debug, 300)

            updateConversation(baseDir, handleName, domain, postJsonObject)

            # If this was an edit then delete the previous version of the post
            if editedFilename:
                deletePost(baseDir, httpPrefix,
                           nickname, domain, editedFilename,
                           debug, recentPostsCache)

            # store the id of the last post made by this actor
            _storeLastPostId(baseDir, nickname, domain, postJsonObject)

            _inboxUpdateCalendar(baseDir, handle, postJsonObject)

            storeHashTags(baseDir, handleName, domain,
                          httpPrefix, domainFull,
                          postJsonObject, translate)

            # send the post out to group members
            if isGroup:
                _sendToGroupMembers(session, baseDir, handle, port,
                                    postJsonObject,
                                    httpPrefix, federationList, sendThreads,
                                    postLog, cachedWebfingers, personCache,
                                    debug, systemLanguage,
                                    onionDomain, i2pDomain,
                                    signingPrivateKeyPem)

    # if the post wasn't saved
    if not os.path.isfile(destinationFilename):
        return False

    return True


def clearQueueItems(baseDir: str, queue: []) -> None:
    """Clears the queue for each account
    """
    ctr = 0
    queue.clear()
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for account in dirs:
            queueDir = baseDir + '/accounts/' + account + '/queue'
            if not os.path.isdir(queueDir):
                continue
            for queuesubdir, queuedirs, queuefiles in os.walk(queueDir):
                for qfile in queuefiles:
                    try:
                        os.remove(os.path.join(queueDir, qfile))
                        ctr += 1
                    except BaseException:
                        print('EX: clearQueueItems unable to delete ' + qfile)
                        pass
                break
        break
    if ctr > 0:
        print('Removed ' + str(ctr) + ' inbox queue items')


def _restoreQueueItems(baseDir: str, queue: []) -> None:
    """Checks the queue for each account and appends filenames
    """
    queue.clear()
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for account in dirs:
            queueDir = baseDir + '/accounts/' + account + '/queue'
            if not os.path.isdir(queueDir):
                continue
            for queuesubdir, queuedirs, queuefiles in os.walk(queueDir):
                for qfile in queuefiles:
                    queue.append(os.path.join(queueDir, qfile))
                break
        break
    if len(queue) > 0:
        print('Restored ' + str(len(queue)) + ' inbox queue items')


def runInboxQueueWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the inbox thread running even if it dies
    """
    print('Starting inbox queue watchdog')
    inboxQueueOriginal = httpd.thrInboxQueue.clone(runInboxQueue)
    httpd.thrInboxQueue.start()
    while True:
        time.sleep(20)
        if not httpd.thrInboxQueue.is_alive() or httpd.restartInboxQueue:
            httpd.restartInboxQueueInProgress = True
            httpd.thrInboxQueue.kill()
            httpd.thrInboxQueue = inboxQueueOriginal.clone(runInboxQueue)
            httpd.inboxQueue.clear()
            httpd.thrInboxQueue.start()
            print('Restarting inbox queue...')
            httpd.restartInboxQueueInProgress = False
            httpd.restartInboxQueue = False


def _inboxQuotaExceeded(queue: {}, queueFilename: str,
                        queueJson: {}, quotasDaily: {}, quotasPerMin: {},
                        domainMaxPostsPerDay: int,
                        accountMaxPostsPerDay: int,
                        debug: bool) -> bool:
    """limit the number of posts which can arrive per domain per day
    """
    postDomain = queueJson['postDomain']
    if not postDomain:
        return False

    if domainMaxPostsPerDay > 0:
        if quotasDaily['domains'].get(postDomain):
            if quotasDaily['domains'][postDomain] > \
               domainMaxPostsPerDay:
                print('Queue: Quota per day - Maximum posts for ' +
                      postDomain + ' reached (' +
                      str(domainMaxPostsPerDay) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queueFilename)
                    except BaseException:
                        print('EX: _inboxQuotaExceeded unable to delete ' +
                              str(queueFilename))
                        pass
                    queue.pop(0)
                return True
            quotasDaily['domains'][postDomain] += 1
        else:
            quotasDaily['domains'][postDomain] = 1

        if quotasPerMin['domains'].get(postDomain):
            domainMaxPostsPerMin = \
                int(domainMaxPostsPerDay / (24 * 60))
            if domainMaxPostsPerMin < 5:
                domainMaxPostsPerMin = 5
            if quotasPerMin['domains'][postDomain] > \
               domainMaxPostsPerMin:
                print('Queue: Quota per min - Maximum posts for ' +
                      postDomain + ' reached (' +
                      str(domainMaxPostsPerMin) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queueFilename)
                    except BaseException:
                        print('EX: _inboxQuotaExceeded unable to delete ' +
                              str(queueFilename))
                        pass
                    queue.pop(0)
                return True
            quotasPerMin['domains'][postDomain] += 1
        else:
            quotasPerMin['domains'][postDomain] = 1

    if accountMaxPostsPerDay > 0:
        postHandle = queueJson['postNickname'] + '@' + postDomain
        if quotasDaily['accounts'].get(postHandle):
            if quotasDaily['accounts'][postHandle] > \
               accountMaxPostsPerDay:
                print('Queue: Quota account posts per day -' +
                      ' Maximum posts for ' +
                      postHandle + ' reached (' +
                      str(accountMaxPostsPerDay) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queueFilename)
                    except BaseException:
                        print('EX: _inboxQuotaExceeded unable to delete ' +
                              str(queueFilename))
                        pass
                    queue.pop(0)
                return True
            quotasDaily['accounts'][postHandle] += 1
        else:
            quotasDaily['accounts'][postHandle] = 1

        if quotasPerMin['accounts'].get(postHandle):
            accountMaxPostsPerMin = \
                int(accountMaxPostsPerDay / (24 * 60))
            if accountMaxPostsPerMin < 5:
                accountMaxPostsPerMin = 5
            if quotasPerMin['accounts'][postHandle] > \
               accountMaxPostsPerMin:
                print('Queue: Quota account posts per min -' +
                      ' Maximum posts for ' +
                      postHandle + ' reached (' +
                      str(accountMaxPostsPerMin) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queueFilename)
                    except BaseException:
                        print('EX: _inboxQuotaExceeded unable to delete ' +
                              str(queueFilename))
                        pass
                    queue.pop(0)
                return True
            quotasPerMin['accounts'][postHandle] += 1
        else:
            quotasPerMin['accounts'][postHandle] = 1

    if debug:
        if accountMaxPostsPerDay > 0 or domainMaxPostsPerDay > 0:
            pprint(quotasDaily)
    return False


def _checkJsonSignature(baseDir: str, queueJson: {}) -> (bool, bool):
    """check if a json signature exists on this post
    """
    hasJsonSignature = False
    jwebsigType = None
    originalJson = queueJson['original']
    if not originalJson.get('@context') or \
       not originalJson.get('signature'):
        return hasJsonSignature, jwebsigType
    if not isinstance(originalJson['signature'], dict):
        return hasJsonSignature, jwebsigType
    # see https://tools.ietf.org/html/rfc7515
    jwebsig = originalJson['signature']
    # signature exists and is of the expected type
    if not jwebsig.get('type') or \
       not jwebsig.get('signatureValue'):
        return hasJsonSignature, jwebsigType
    jwebsigType = jwebsig['type']
    if jwebsigType == 'RsaSignature2017':
        if hasValidContext(originalJson):
            hasJsonSignature = True
        else:
            unknownContextsFile = \
                baseDir + '/accounts/unknownContexts.txt'
            unknownContext = str(originalJson['@context'])

            print('unrecognized @context: ' + unknownContext)

            alreadyUnknown = False
            if os.path.isfile(unknownContextsFile):
                if unknownContext in \
                   open(unknownContextsFile).read():
                    alreadyUnknown = True

            if not alreadyUnknown:
                with open(unknownContextsFile, 'a+') as unknownFile:
                    unknownFile.write(unknownContext + '\n')
    else:
        print('Unrecognized jsonld signature type: ' + jwebsigType)

        unknownSignaturesFile = \
            baseDir + '/accounts/unknownJsonSignatures.txt'

        alreadyUnknown = False
        if os.path.isfile(unknownSignaturesFile):
            if jwebsigType in \
               open(unknownSignaturesFile).read():
                alreadyUnknown = True

        if not alreadyUnknown:
            with open(unknownSignaturesFile, 'a+') as unknownFile:
                unknownFile.write(jwebsigType + '\n')
    return hasJsonSignature, jwebsigType


def runInboxQueue(recentPostsCache: {}, maxRecentPosts: int,
                  projectVersion: str,
                  baseDir: str, httpPrefix: str, sendThreads: [], postLog: [],
                  cachedWebfingers: {}, personCache: {}, queue: [],
                  domain: str,
                  onionDomain: str, i2pDomain: str, port: int, proxyType: str,
                  federationList: [], maxReplies: int,
                  domainMaxPostsPerDay: int, accountMaxPostsPerDay: int,
                  allowDeletion: bool, debug: bool, maxMentions: int,
                  maxEmoji: int, translate: {}, unitTest: bool,
                  YTReplacementDomain: str,
                  twitterReplacementDomain: str,
                  showPublishedDateOnly: bool,
                  maxFollowers: int, allowLocalNetworkAccess: bool,
                  peertubeInstances: [],
                  verifyAllSignatures: bool,
                  themeName: str, systemLanguage: str,
                  maxLikeCount: int, signingPrivateKeyPem: str,
                  defaultReplyIntervalHours: int,
                  CWlists: {}) -> None:
    """Processes received items and moves them to the appropriate
    directories
    """
    currSessionTime = int(time.time())
    sessionLastUpdate = currSessionTime
    print('Starting new session when starting inbox queue')
    session = createSession(proxyType)
    inboxHandle = 'inbox@' + domain
    if debug:
        print('DEBUG: Inbox queue running')

    # if queue processing was interrupted (eg server crash)
    # then this loads any outstanding items back into the queue
    _restoreQueueItems(baseDir, queue)

    # keep track of numbers of incoming posts per day
    quotasLastUpdateDaily = int(time.time())
    quotasDaily = {
        'domains': {},
        'accounts': {}
    }
    quotasLastUpdatePerMin = int(time.time())
    quotasPerMin = {
        'domains': {},
        'accounts': {}
    }

    heartBeatCtr = 0
    queueRestoreCtr = 0

    # time when the last DM bounce message was sent
    # This is in a list so that it can be changed by reference
    # within _bounceDM
    lastBounceMessage = [int(time.time())]

    # how long it takes for broch mode to lapse
    brochLapseDays = random.randrange(7, 14)

    while True:
        time.sleep(1)

        # heartbeat to monitor whether the inbox queue is running
        heartBeatCtr += 1
        if heartBeatCtr >= 10:
            # turn off broch mode after it has timed out
            if brochModeLapses(baseDir, brochLapseDays):
                brochLapseDays = random.randrange(7, 14)
            print('>>> Heartbeat Q:' + str(len(queue)) + ' ' +
                  '{:%F %T}'.format(datetime.datetime.now()))
            heartBeatCtr = 0

        if len(queue) == 0:
            # restore any remaining queue items
            queueRestoreCtr += 1
            if queueRestoreCtr >= 30:
                queueRestoreCtr = 0
                _restoreQueueItems(baseDir, queue)
            continue

        currTime = int(time.time())

        # recreate the session periodically
        if not session or currTime - sessionLastUpdate > 21600:
            print('Regenerating inbox queue session at 6hr interval')
            session = createSession(proxyType)
            if not session:
                continue
            sessionLastUpdate = currTime

        # oldest item first
        queue.sort()
        queueFilename = queue[0]
        if not os.path.isfile(queueFilename):
            print("Queue: queue item rejected because it has no file: " +
                  queueFilename)
            if len(queue) > 0:
                queue.pop(0)
            continue

        if debug:
            print('Loading queue item ' + queueFilename)

        # Load the queue json
        queueJson = loadJson(queueFilename, 1)
        if not queueJson:
            print('Queue: runInboxQueue failed to load inbox queue item ' +
                  queueFilename)
            # Assume that the file is probably corrupt/unreadable
            if len(queue) > 0:
                queue.pop(0)
            # delete the queue file
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except BaseException:
                    print('EX: runInboxQueue 1 unable to delete ' +
                          str(queueFilename))
                    pass
            continue

        # clear the daily quotas for maximum numbers of received posts
        if currTime - quotasLastUpdateDaily > 60 * 60 * 24:
            quotasDaily = {
                'domains': {},
                'accounts': {}
            }
            quotasLastUpdateDaily = currTime

        if currTime - quotasLastUpdatePerMin > 60:
            # clear the per minute quotas for maximum numbers of received posts
            quotasPerMin = {
                'domains': {},
                'accounts': {}
            }
            # also check if the json signature enforcement has changed
            verifyAllSigs = getConfigParam(baseDir, "verifyAllSignatures")
            if verifyAllSigs is not None:
                verifyAllSignatures = verifyAllSigs
            # change the last time that this was done
            quotasLastUpdatePerMin = currTime

        if _inboxQuotaExceeded(queue, queueFilename,
                               queueJson, quotasDaily, quotasPerMin,
                               domainMaxPostsPerDay,
                               accountMaxPostsPerDay, debug):
            continue

        if debug and queueJson.get('actor'):
            print('Obtaining public key for actor ' + queueJson['actor'])

        # Try a few times to obtain the public key
        pubKey = None
        keyId = None
        for tries in range(8):
            keyId = None
            signatureParams = \
                queueJson['httpHeaders']['signature'].split(',')
            for signatureItem in signatureParams:
                if signatureItem.startswith('keyId='):
                    if '"' in signatureItem:
                        keyId = signatureItem.split('"')[1]
                        break
            if not keyId:
                print('Queue: No keyId in signature: ' +
                      queueJson['httpHeaders']['signature'])
                pubKey = None
                break

            pubKey = \
                getPersonPubKey(baseDir, session, keyId,
                                personCache, debug,
                                projectVersion, httpPrefix,
                                domain, onionDomain, signingPrivateKeyPem)
            if pubKey:
                if debug:
                    print('DEBUG: public key: ' + str(pubKey))
                break

            if debug:
                print('DEBUG: Retry ' + str(tries+1) +
                      ' obtaining public key for ' + keyId)
            time.sleep(1)

        if not pubKey:
            if debug:
                print('Queue: public key could not be obtained from ' + keyId)
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except BaseException:
                    print('EX: runInboxQueue 2 unable to delete ' +
                          str(queueFilename))
                    pass
            if len(queue) > 0:
                queue.pop(0)
            continue

        # check the http header signature
        if debug:
            print('DEBUG: checking http header signature')
            pprint(queueJson['httpHeaders'])
        postStr = json.dumps(queueJson['post'])
        httpSignatureFailed = False
        if not verifyPostHeaders(httpPrefix,
                                 pubKey,
                                 queueJson['httpHeaders'],
                                 queueJson['path'], False,
                                 queueJson['digest'],
                                 postStr,
                                 debug):
            httpSignatureFailed = True
            print('Queue: Header signature check failed')
            pprint(queueJson['httpHeaders'])
        else:
            if debug:
                print('DEBUG: http header signature check success')

        # check if a json signature exists on this post
        hasJsonSignature, jwebsigType = _checkJsonSignature(baseDir, queueJson)

        # strict enforcement of json signatures
        if not hasJsonSignature:
            if httpSignatureFailed:
                if jwebsigType:
                    print('Queue: Header signature check failed and does ' +
                          'not have a recognised jsonld signature type ' +
                          jwebsigType)
                else:
                    print('Queue: Header signature check failed and ' +
                          'does not have jsonld signature')
                if debug:
                    pprint(queueJson['httpHeaders'])

            if verifyAllSignatures:
                originalJson = queueJson['original']
                print('Queue: inbox post does not have a jsonld signature ' +
                      keyId + ' ' + str(originalJson))

            if httpSignatureFailed or verifyAllSignatures:
                if os.path.isfile(queueFilename):
                    try:
                        os.remove(queueFilename)
                    except BaseException:
                        print('EX: runInboxQueue 3 unable to delete ' +
                              str(queueFilename))
                        pass
                if len(queue) > 0:
                    queue.pop(0)
                continue
        else:
            if httpSignatureFailed or verifyAllSignatures:
                # use the original json message received, not one which
                # may have been modified along the way
                originalJson = queueJson['original']
                if not verifyJsonSignature(originalJson, pubKey):
                    if debug:
                        print('WARN: jsonld inbox signature check failed ' +
                              keyId + ' ' + pubKey + ' ' + str(originalJson))
                    else:
                        print('WARN: jsonld inbox signature check failed ' +
                              keyId)
                    if os.path.isfile(queueFilename):
                        try:
                            os.remove(queueFilename)
                        except BaseException:
                            print('EX: runInboxQueue 4 unable to delete ' +
                                  str(queueFilename))
                            pass
                    if len(queue) > 0:
                        queue.pop(0)
                    continue
                else:
                    if httpSignatureFailed:
                        print('jsonld inbox signature check success ' +
                              'via relay ' + keyId)
                    else:
                        print('jsonld inbox signature check success ' + keyId)

        # set the id to the same as the post filename
        # This makes the filename and the id consistent
        # if queueJson['post'].get('id'):
        #     queueJson['post']['id'] = queueJson['id']

        if _receiveUndo(session,
                        baseDir, httpPrefix, port,
                        sendThreads, postLog,
                        cachedWebfingers,
                        personCache,
                        queueJson['post'],
                        federationList,
                        debug):
            print('Queue: Undo accepted from ' + keyId)
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except BaseException:
                    print('EX: runInboxQueue 5 unable to delete ' +
                          str(queueFilename))
                    pass
            if len(queue) > 0:
                queue.pop(0)
            continue

        if debug:
            print('DEBUG: checking for follow requests')
        if receiveFollowRequest(session,
                                baseDir, httpPrefix, port,
                                sendThreads, postLog,
                                cachedWebfingers,
                                personCache,
                                queueJson['post'],
                                federationList,
                                debug, projectVersion,
                                maxFollowers, onionDomain,
                                signingPrivateKeyPem):
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except BaseException:
                    print('EX: runInboxQueue 6 unable to delete ' +
                          str(queueFilename))
                    pass
            if len(queue) > 0:
                queue.pop(0)
            print('Queue: Follow activity for ' + keyId +
                  ' removed from queue')
            continue
        else:
            if debug:
                print('DEBUG: No follow requests')

        if receiveAcceptReject(session,
                               baseDir, httpPrefix, domain, port,
                               sendThreads, postLog,
                               cachedWebfingers, personCache,
                               queueJson['post'],
                               federationList, debug):
            print('Queue: Accept/Reject received from ' + keyId)
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except BaseException:
                    print('EX: runInboxQueue 7 unable to delete ' +
                          str(queueFilename))
                    pass
            if len(queue) > 0:
                queue.pop(0)
            continue

        if _receiveUpdate(recentPostsCache, session,
                          baseDir, httpPrefix,
                          domain, port,
                          sendThreads, postLog,
                          cachedWebfingers,
                          personCache,
                          queueJson['post'],
                          federationList,
                          queueJson['postNickname'],
                          debug):
            if debug:
                print('Queue: Update accepted from ' + keyId)
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except BaseException:
                    print('EX: runInboxQueue 8 unable to delete ' +
                          str(queueFilename))
                    pass
            if len(queue) > 0:
                queue.pop(0)
            continue

        # get recipients list
        recipientsDict, recipientsDictFollowers = \
            _inboxPostRecipients(baseDir, queueJson['post'],
                                 httpPrefix, domain, port, debug)
        if len(recipientsDict.items()) == 0 and \
           len(recipientsDictFollowers.items()) == 0:
            if debug:
                print('Queue: no recipients were resolved ' +
                      'for post arriving in inbox')
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except BaseException:
                    print('EX: runInboxQueue 9 unable to delete ' +
                          str(queueFilename))
                    pass
            if len(queue) > 0:
                queue.pop(0)
            continue

        # if there are only a small number of followers then
        # process them as if they were specifically
        # addresses to particular accounts
        noOfFollowItems = len(recipientsDictFollowers.items())
        if noOfFollowItems > 0:
            # always deliver to individual inboxes
            if noOfFollowItems < 999999:
                if debug:
                    print('DEBUG: moving ' + str(noOfFollowItems) +
                          ' inbox posts addressed to followers')
                for handle, postItem in recipientsDictFollowers.items():
                    recipientsDict[handle] = postItem
                recipientsDictFollowers = {}
#            recipientsList = [recipientsDict, recipientsDictFollowers]

        if debug:
            print('*************************************')
            print('Resolved recipients list:')
            pprint(recipientsDict)
            print('Resolved followers list:')
            pprint(recipientsDictFollowers)
            print('*************************************')

        # Copy any posts addressed to followers into the shared inbox
        # this avoid copying file multiple times to potentially many
        # individual inboxes
        if len(recipientsDictFollowers) > 0:
            sharedInboxPostFilename = \
                queueJson['destination'].replace(inboxHandle, inboxHandle)
            if not os.path.isfile(sharedInboxPostFilename):
                saveJson(queueJson['post'], sharedInboxPostFilename)

        listsEnabled = getConfigParam(baseDir, "listsEnabled")

        # for posts addressed to specific accounts
        for handle, capsId in recipientsDict.items():
            destination = \
                queueJson['destination'].replace(inboxHandle, handle)
            _inboxAfterInitial(recentPostsCache,
                               maxRecentPosts,
                               session, keyId, handle,
                               queueJson['post'],
                               baseDir, httpPrefix,
                               sendThreads, postLog,
                               cachedWebfingers,
                               personCache, queue,
                               domain,
                               onionDomain, i2pDomain,
                               port, proxyType,
                               federationList,
                               debug,
                               queueFilename, destination,
                               maxReplies, allowDeletion,
                               maxMentions, maxEmoji,
                               translate, unitTest,
                               YTReplacementDomain,
                               twitterReplacementDomain,
                               showPublishedDateOnly,
                               allowLocalNetworkAccess,
                               peertubeInstances,
                               lastBounceMessage,
                               themeName, systemLanguage,
                               maxLikeCount,
                               signingPrivateKeyPem,
                               defaultReplyIntervalHours,
                               CWlists, listsEnabled)
            if debug:
                pprint(queueJson['post'])
                print('Queue: Queue post accepted')
        if os.path.isfile(queueFilename):
            try:
                os.remove(queueFilename)
            except BaseException:
                print('EX: runInboxQueue 10 unable to delete ' +
                      str(queueFilename))
                pass
        if len(queue) > 0:
            queue.pop(0)
