__filename__ = "inbox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import os
import datetime
import time
from linked_data_sig import verifyJsonSignature
from utils import getConfigParam
from utils import hasUsersPath
from utils import validPostDate
from utils import getFullDomain
from utils import isEventPost
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
from utils import updateLikesCollection
from utils import undoLikesCollectionEntry
from categories import getHashtagCategories
from categories import setHashtagCategory
from httpsig import verifyPostHeaders
from session import createSession
from session import getJson
from follow import receiveFollowRequest
from follow import getFollowersOfActor
from follow import unfollowerOfAccount
from pprint import pprint
from cache import getPersonFromCache
from cache import storePersonInCache
from acceptreject import receiveAcceptReject
from bookmarks import updateBookmarksCollection
from bookmarks import undoBookmarksCollectionEntry
from blocking import isBlocked
from blocking import isBlockedDomain
from filters import isFiltered
from utils import updateAnnounceCollection
from utils import undoAnnounceCollectionEntry
from utils import dangerousMarkup
from httpsig import messageContentDigest
from posts import validContentWarning
from posts import downloadAnnounce
from posts import isDM
from posts import isReply
from posts import isMuted
from posts import isImageMedia
from posts import sendSignedJson
from posts import sendToFollowersThread
from webapp_post import individualPostAsHtml
from question import questionUpdateVotes
from media import replaceYouTube
from git import isGitPatch
from git import receiveGitPatch
from followingCalendar import receivingCalendarEvents
from happening import saveEventPost
from delete import removeOldHashtags
from follow import isFollowingActor
from categories import guessHashtagCategory
from context import hasValidContext


def storeHashTags(baseDir: str, nickname: str, postJsonObject: {}) -> None:
    """Extracts hashtags from an incoming post and updates the
    relevant tags files.
    """
    if not isPublicPost(postJsonObject):
        return
    if not postJsonObject.get('object'):
        return
    if not isinstance(postJsonObject['object'], dict):
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

    for tag in postJsonObject['object']['tag']:
        if not tag.get('type'):
            continue
        if tag['type'] != 'Hashtag':
            continue
        if not tag.get('name'):
            continue
        tagName = tag['name'].replace('#', '').strip()
        tagsFilename = tagsDir + '/' + tagName + '.txt'
        postUrl = removeIdEnding(postJsonObject['id'])
        postUrl = postUrl.replace('/', '#')
        daysDiff = datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
        daysSinceEpoch = daysDiff.days
        tagline = str(daysSinceEpoch) + '  ' + nickname + '  ' + postUrl + '\n'
        if not os.path.isfile(tagsFilename):
            tagsFile = open(tagsFilename, "w+")
            if tagsFile:
                tagsFile.write(tagline)
                tagsFile.close()
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
                setHashtagCategory(baseDir, tagName, categoryStr)


def _inboxStorePostToHtmlCache(recentPostsCache: {}, maxRecentPosts: int,
                               translate: {},
                               baseDir: str, httpPrefix: str,
                               session, cachedWebfingers: {}, personCache: {},
                               nickname: str, domain: str, port: int,
                               postJsonObject: {},
                               allowDeletion: bool, boxname: str,
                               showPublishedDateOnly: bool,
                               peertubeInstances: [],
                               allowLocalNetworkAccess: bool) -> None:
    """Converts the json post into html and stores it in a cache
    This enables the post to be quickly displayed later
    """
    pageNumber = -999
    avatarUrl = None
    if boxname != 'tlevents' and boxname != 'outbox':
        boxname = 'inbox'

    individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                         translate, pageNumber,
                         baseDir, session, cachedWebfingers,
                         personCache,
                         nickname, domain, port, postJsonObject,
                         avatarUrl, True, allowDeletion,
                         httpPrefix, __version__, boxname, None,
                         showPublishedDateOnly,
                         peertubeInstances, allowLocalNetworkAccess,
                         not isDM(postJsonObject),
                         True, True, False, True)


def validInbox(baseDir: str, nickname: str, domain: str) -> bool:
    """Checks whether files were correctly saved to the inbox
    """
    if ':' in domain:
        domain = domain.split(':')[0]
    inboxDir = baseDir+'/accounts/' + nickname + '@' + domain + '/inbox'
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
    if ':' in domain:
        domain = domain.split(':')[0]
    inboxDir = baseDir + '/accounts/' + nickname + '@' + domain + '/inbox'
    if not os.path.isdir(inboxDir):
        return True
    expectedStr = expectedDomain + ':' + str(expectedPort)
    for subdir, dirs, files in os.walk(inboxDir):
        for f in files:
            filename = os.path.join(subdir, f)
            if not os.path.isfile(filename):
                print('filename: ' + filename)
                return False
            if expectedStr not in filename:
                print('Expected: ' + expectedStr)
                print('Invalid filename: ' + filename)
                return False
        break
    return True


def getPersonPubKey(baseDir: str, session, personUrl: str,
                    personCache: {}, debug: bool,
                    projectVersion: str, httpPrefix: str,
                    domain: str, onionDomain: str) -> str:
    if not personUrl:
        return None
    personUrl = personUrl.replace('#main-key', '')
    if personUrl.endswith('/users/inbox'):
        if debug:
            print('DEBUG: Obtaining public key for shared inbox')
        personUrl = personUrl.replace('/users/inbox', '/inbox')
    personJson = \
        getPersonFromCache(baseDir, personUrl, personCache, True)
    if not personJson:
        if debug:
            print('DEBUG: Obtaining public key for ' + personUrl)
        personDomain = domain
        if onionDomain:
            if '.onion/' in personUrl:
                personDomain = onionDomain
        profileStr = 'https://www.w3.org/ns/activitystreams'
        asHeader = {
            'Accept': 'application/activity+json; profile="' + profileStr + '"'
        }
        personJson = \
            getJson(session, personUrl, asHeader, None, projectVersion,
                    httpPrefix, personDomain)
        if not personJson:
            return None
    pubKey = None
    if personJson.get('publicKey'):
        if personJson['publicKey'].get('publicKeyPem'):
            pubKey = personJson['publicKey']['publicKeyPem']
    else:
        if personJson.get('publicKeyPem'):
            pubKey = personJson['publicKeyPem']

    if not pubKey:
        if debug:
            print('DEBUG: Public key not found for ' + personUrl)

    storePersonInCache(baseDir, personUrl, personJson, personCache, True)
    return pubKey


def inboxMessageHasParams(messageJson: {}) -> bool:
    """Checks whether an incoming message contains expected parameters
    """
    expectedParams = ['actor', 'type', 'object']
    for param in expectedParams:
        if not messageJson.get(param):
            # print('inboxMessageHasParams: ' +
            #       param + ' ' + str(messageJson))
            return False
    if not messageJson.get('to'):
        allowedWithoutToParam = ['Like', 'Follow', 'Request',
                                 'Accept', 'Capability', 'Undo']
        if messageJson['type'] not in allowedWithoutToParam:
            return False
    return True


def inboxPermittedMessage(domain: str, messageJson: {},
                          federationList: []) -> bool:
    """ check that we are receiving from a permitted domain
    """
    if not messageJson.get('actor'):
        return False

    actor = messageJson['actor']
    # always allow the local domain
    if domain in actor:
        return True

    if not urlPermitted(actor, federationList):
        return False

    alwaysAllowedTypes = ('Follow', 'Like', 'Delete', 'Announce')
    if messageJson['type'] not in alwaysAllowedTypes:
        if not messageJson.get('object'):
            return True
        if not isinstance(messageJson['object'], dict):
            return False
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
                         postPath: str, debug: bool) -> str:
    """Saves the give json to the inbox queue for the person
    keyId specifies the actor sending the post
    """
    if len(messageBytes) > 10240:
        print('WARN: inbox message too long ' +
              str(len(messageBytes)) + ' bytes')
        return None
    originalDomain = domain
    if ':' in domain:
        domain = domain.split(':')[0]

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
        if isBlocked(baseDir, nickname, domain, postNickname, postDomain):
            if debug:
                print('DEBUG: post from ' + postNickname + ' blocked')
            return None
        postDomain = getFullDomain(postDomain, postPort)

    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], dict):
            if postJsonObject['object'].get('inReplyTo'):
                if isinstance(postJsonObject['object']['inReplyTo'], str):
                    inReplyTo = \
                        postJsonObject['object']['inReplyTo']
                    replyDomain, replyPort = \
                        getDomainFromActor(inReplyTo)
                    if isBlockedDomain(baseDir, replyDomain):
                        print('WARN: post contains reply from ' +
                              str(actor) +
                              ' to a blocked domain: ' + replyDomain)
                        return None
                    else:
                        replyNickname = \
                            getNicknameFromActor(inReplyTo)
                        if replyNickname and replyDomain:
                            if isBlocked(baseDir, nickname, domain,
                                         replyNickname, replyDomain):
                                print('WARN: post contains reply from ' +
                                      str(actor) +
                                      ' to a blocked account: ' +
                                      replyNickname + '@' + replyDomain)
                                return None
            if postJsonObject['object'].get('content'):
                if isinstance(postJsonObject['object']['content'], str):
                    if isFiltered(baseDir, nickname, domain,
                                  postJsonObject['object']['content']):
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
            postId = httpPrefix + '://' + originalDomain + \
                '/users/' + nickname + '/statuses/' + statusNumber

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
            handle = nickname+'@'+domain
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

    if ':' in domain:
        domain = domain.split(':')[0]
    domainBase = domain
    domain = getFullDomain(domain, port)
    domainMatch = '/' + domain + '/users/'

    actor = postJsonObject['actor']
    # first get any specific people which the post is addressed to

    followerRecipients = False
    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], dict):
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
            if debug:
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

    if unfollowerOfAccount(baseDir,
                           nicknameFollowing, domainFollowingFull,
                           nicknameFollower, domainFollowerFull,
                           debug):
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
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: follow request has no actor')
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no object')
        return False
    if not isinstance(messageJson['object'], dict):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' object is not a dict')
        return False
    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no object type')
        return False
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] +
                  ' has no object within object')
        return False
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: ' + messageJson['type'] +
                  ' object within object is not a string')
        return False
    if messageJson['object']['type'] == 'Follow':
        return _receiveUndoFollow(session, baseDir, httpPrefix,
                                  port, messageJson,
                                  federationList, debug)
    return False


def _receiveEventPost(recentPostsCache: {}, session, baseDir: str,
                      httpPrefix: str, domain: str, port: int,
                      sendThreads: [], postLog: [], cachedWebfingers: {},
                      personCache: {}, messageJson: {}, federationList: [],
                      nickname: str, debug: bool) -> bool:
    """Receive a mobilizon-type event activity
    See https://framagit.org/framasoft/mobilizon/-/blob/
    master/lib/federation/activity_stream/converter/event.ex
    """
    if not isEventPost(messageJson):
        return
    print('Receiving event: ' + str(messageJson['object']))
    handle = getFullDomain(nickname + '@' + domain, port)

    postId = removeIdEnding(messageJson['id']).replace('/', '#')

    saveEventPost(baseDir, handle, postId, messageJson['object'])


def _personReceiveUpdate(baseDir: str,
                         domain: str, port: int,
                         updateNickname: str, updateDomain: str,
                         updatePort: int,
                         personJson: {}, personCache: {},
                         debug: bool) -> bool:
    """Changes an actor. eg: avatar or display name change
    """
    print('Receiving actor update for ' + personJson['url'] +
          ' ' + str(personJson))
    domainFull = getFullDomain(domain, port)
    updateDomainFull = getFullDomain(updateDomain, updatePort)
    usersPaths = ('users', 'profile', 'channel', 'accounts')
    usersStrFound = False
    for usersStr in usersPaths:
        actor = updateDomainFull + '/' + usersStr + '/' + updateNickname
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
    if not messageJson.get('actor'):
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
            os.remove(cachedPostFilename)
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
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no actor')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no object')
        return False
    if not isinstance(messageJson['object'], dict):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' object is not a dict')
        return False
    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' object has no type')
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

    if messageJson['type'] == 'Person':
        if messageJson.get('url') and messageJson.get('id'):
            print('Request to update actor unwrapped: ' + str(messageJson))
            updateNickname = getNicknameFromActor(messageJson['id'])
            if updateNickname:
                updateDomain, updatePort = \
                    getDomainFromActor(messageJson['id'])
                if _personReceiveUpdate(baseDir, domain, port,
                                        updateNickname, updateDomain,
                                        updatePort, messageJson,
                                        personCache, debug):
                    if debug:
                        print('DEBUG: ' +
                              'Unwrapped profile update was received for ' +
                              messageJson['url'])
                        return True

    if messageJson['object']['type'] == 'Person' or \
       messageJson['object']['type'] == 'Application' or \
       messageJson['object']['type'] == 'Group' or \
       messageJson['object']['type'] == 'Service':
        if messageJson['object'].get('url') and \
           messageJson['object'].get('id'):
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
                 debug: bool) -> bool:
    """Receives a Like activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Like':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no actor')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no object')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' object is not a string')
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
    postFilename = locatePost(baseDir, handleName, handleDom,
                              messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: post not found in inbox or outbox')
            print(messageJson['object'])
        return True
    if debug:
        print('DEBUG: liked post found in inbox')

    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    updateLikesCollection(recentPostsCache, baseDir, postFilename,
                          messageJson['object'],
                          messageJson['actor'], domain, debug)
    if not _alreadyLiked(baseDir,
                         handleName, handleDom,
                         messageJson['object'],
                         messageJson['actor']):
        _likeNotify(baseDir, domain, onionDomain, handle,
                    messageJson['actor'], messageJson['object'])
    return True


def _receiveUndoLike(recentPostsCache: {},
                     session, handle: str, isGroup: bool, baseDir: str,
                     httpPrefix: str, domain: str, port: int,
                     sendThreads: [], postLog: [], cachedWebfingers: {},
                     personCache: {}, messageJson: {}, federationList: [],
                     debug: bool) -> bool:
    """Receives an undo like activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Undo':
        return False
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
        return False
    if not messageJson['object'].get('type'):
        return False
    if messageJson['object']['type'] != 'Like':
        return False
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' like has no object')
        return False
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: ' + messageJson['type'] +
                  ' like object is not a string')
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
    undoLikesCollectionEntry(recentPostsCache, baseDir, postFilename,
                             messageJson['object'],
                             messageJson['actor'], domain, debug)
    return True


def _receiveBookmark(recentPostsCache: {},
                     session, handle: str, isGroup: bool, baseDir: str,
                     httpPrefix: str, domain: str, port: int,
                     sendThreads: [], postLog: [], cachedWebfingers: {},
                     personCache: {}, messageJson: {}, federationList: [],
                     debug: bool) -> bool:
    """Receives a bookmark activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Bookmark':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no actor')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no object')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' object is not a string')
        return False
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no "to" list')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in ' +
                  messageJson['type'])
        return False
    if '/statuses/' not in messageJson['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  messageJson['type'])
        return False
    if domain not in handle.split('@')[1]:
        if debug:
            print('DEBUG: unrecognized domain ' + handle)
        return False
    domainFull = getFullDomain(domain, port)
    nickname = handle.split('@')[0]
    if not messageJson['actor'].endswith(domainFull + '/users/' + nickname):
        if debug:
            print('DEBUG: ' +
                  'bookmark actor should be the same as the handle sent to ' +
                  handle + ' != ' + messageJson['actor'])
        return False
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of bookmark - ' + handle)
    # if this post in the outbox of the person?
    postFilename = locatePost(baseDir, nickname, domain, messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: post not found in inbox or outbox')
            print(messageJson['object'])
        return True
    if debug:
        print('DEBUG: bookmarked post was found')

    updateBookmarksCollection(recentPostsCache, baseDir, postFilename,
                              messageJson['object'],
                              messageJson['actor'], domain, debug)
    return True


def _receiveUndoBookmark(recentPostsCache: {},
                         session, handle: str, isGroup: bool, baseDir: str,
                         httpPrefix: str, domain: str, port: int,
                         sendThreads: [], postLog: [], cachedWebfingers: {},
                         personCache: {}, messageJson: {}, federationList: [],
                         debug: bool) -> bool:
    """Receives an undo bookmark activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Undo':
        return False
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
        return False
    if not messageJson['object'].get('type'):
        return False
    if messageJson['object']['type'] != 'Bookmark':
        return False
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' like has no object')
        return False
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: ' + messageJson['type'] +
                  ' like object is not a string')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in ' +
                  messageJson['type'] + ' like')
        return False
    if '/statuses/' not in messageJson['object']['object']:
        if debug:
            print('DEBUG: "statuses" missing from like object in ' +
                  messageJson['type'])
        return False
    domainFull = getFullDomain(domain, port)
    nickname = handle.split('@')[0]
    if domain not in handle.split('@')[1]:
        if debug:
            print('DEBUG: unrecognized bookmark domain ' + handle)
        return False
    if not messageJson['actor'].endswith(domainFull + '/users/' + nickname):
        if debug:
            print('DEBUG: ' +
                  'bookmark actor should be the same as the handle sent to ' +
                  handle + ' != ' + messageJson['actor'])
        return False
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of bookmark undo - ' + handle)
    # if this post in the outbox of the person?
    postFilename = locatePost(baseDir, nickname, domain,
                              messageJson['object']['object'])
    if not postFilename:
        if debug:
            print('DEBUG: unbookmarked post not found in inbox or outbox')
            print(messageJson['object']['object'])
        return True
    if debug:
        print('DEBUG: bookmarked post found. Now undoing.')
    undoBookmarksCollectionEntry(recentPostsCache, baseDir, postFilename,
                                 messageJson['object'],
                                 messageJson['actor'], domain, debug)
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
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no actor')
        return False
    if debug:
        print('DEBUG: Delete activity arrived')
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no object')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' object is not a string')
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
                     allowLocalNetworkAccess: bool) -> bool:
    """Receives an announce activity within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Announce':
        return False
    if '@' not in handle:
        if debug:
            print('DEBUG: bad handle ' + handle)
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no actor')
        return False
    if debug:
        print('DEBUG: receiving announce on ' + handle)
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no object')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' object is not a string')
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
    if not hasUsersPath(messageJson['object']):
        if debug:
            print('DEBUG: ' +
                  '"users", "channel" or "profile" missing in ' +
                  messageJson['type'])
        return False

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

    # is this post in the outbox of the person?
    postFilename = locatePost(baseDir, nickname, domain,
                              messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: announce post not found in inbox or outbox')
            print(messageJson['object'])
        return True
    updateAnnounceCollection(recentPostsCache, baseDir, postFilename,
                             messageJson['actor'], domain, debug)
    if debug:
        print('DEBUG: Downloading announce post ' + messageJson['actor'] +
              ' -> ' + messageJson['object'])
    postJsonObject = downloadAnnounce(session, baseDir, httpPrefix,
                                      nickname, domain, messageJson,
                                      __version__, translate,
                                      YTReplacementDomain,
                                      allowLocalNetworkAccess)
    if not postJsonObject:
        if domain not in messageJson['object'] and \
           onionDomain not in messageJson['object']:
            if os.path.isfile(postFilename):
                # if the announce can't be downloaded then remove it
                os.remove(postFilename)
    else:
        if debug:
            print('DEBUG: Announce post downloaded for ' +
                  messageJson['actor'] + ' -> ' + messageJson['object'])
        storeHashTags(baseDir, nickname, postJsonObject)
        # Try to obtain the actor for this person
        # so that their avatar can be shown
        lookupActor = None
        if postJsonObject.get('attributedTo'):
            if isinstance(postJsonObject['attributedTo'], str):
                lookupActor = postJsonObject['attributedTo']
        else:
            if postJsonObject.get('object'):
                if isinstance(postJsonObject['object'], dict):
                    if postJsonObject['object'].get('attributedTo'):
                        attrib = postJsonObject['object']['attributedTo']
                        if isinstance(attrib, str):
                            lookupActor = attrib
        if lookupActor:
            if hasUsersPath(lookupActor):
                if '/statuses/' in lookupActor:
                    lookupActor = lookupActor.split('/statuses/')[0]

                if debug:
                    print('DEBUG: Obtaining actor for announce post ' +
                          lookupActor)
                for tries in range(6):
                    pubKey = \
                        getPersonPubKey(baseDir, session, lookupActor,
                                        personCache, debug,
                                        __version__, httpPrefix,
                                        domain, onionDomain)
                    if pubKey:
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
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
        return False
    if not messageJson['object'].get('object'):
        return False
    if not isinstance(messageJson['object']['object'], str):
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
        os.remove(postFilename)
    return True


def jsonPostAllowsComments(postJsonObject: {}) -> bool:
    """Returns true if the given post allows comments/replies
    """
    if 'commentsEnabled' in postJsonObject:
        return postJsonObject['commentsEnabled']
    if postJsonObject.get('object'):
        if not isinstance(postJsonObject['object'], dict):
            return False
        if 'commentsEnabled' in postJsonObject['object']:
            return postJsonObject['object']['commentsEnabled']
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
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
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
            repliesFile = open(postRepliesFilename, 'a+')
            repliesFile.write(messageId + '\n')
            repliesFile.close()
    else:
        repliesFile = open(postRepliesFilename, 'w+')
        repliesFile.write(messageId + '\n')
        repliesFile.close()
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
                      allowLocalNetworkAccess: bool) -> bool:
    """Is the content of a received post valid?
    Check for bad html
    Check for hellthreads
    Check number of tags is reasonable
    """
    if not messageJson.get('object'):
        return True
    if not isinstance(messageJson['object'], dict):
        return True
    if not messageJson['object'].get('content'):
        return True

    if not messageJson['object'].get('published'):
        return False
    if 'T' not in messageJson['object']['published']:
        return False
    if 'Z' not in messageJson['object']['published']:
        return False
    if not validPostDate(messageJson['object']['published']):
        return False

    if messageJson['object'].get('summary'):
        summary = messageJson['object']['summary']
        if not isinstance(summary, str):
            print('WARN: content warning is not a string')
            return False
        if summary != validContentWarning(summary):
            print('WARN: invalid content warning ' + summary)
            return False

    if isGitPatch(baseDir, nickname, domain,
                  messageJson['object']['type'],
                  messageJson['object']['summary'],
                  messageJson['object']['content']):
        return True

    if dangerousMarkup(messageJson['object']['content'],
                       allowLocalNetworkAccess):
        if messageJson['object'].get('id'):
            print('REJECT ARBITRARY HTML: ' + messageJson['object']['id'])
        print('REJECT ARBITRARY HTML: bad string in post - ' +
              messageJson['object']['content'])
        return False

    # check (rough) number of mentions
    mentionsEst = _estimateNumberOfMentions(messageJson['object']['content'])
    if mentionsEst > maxMentions:
        if messageJson['object'].get('id'):
            print('REJECT HELLTHREAD: ' + messageJson['object']['id'])
        print('REJECT HELLTHREAD: Too many mentions in post - ' +
              messageJson['object']['content'])
        return False
    if _estimateNumberOfEmoji(messageJson['object']['content']) > maxEmoji:
        if messageJson['object'].get('id'):
            print('REJECT EMOJI OVERLOAD: ' + messageJson['object']['id'])
        print('REJECT EMOJI OVERLOAD: Too many emoji in post - ' +
              messageJson['object']['content'])
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
    # check for filtered content
    if isFiltered(baseDir, nickname, domain,
                  messageJson['object']['content']):
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
    print('ACCEPT: post content is valid')
    return True


def _obtainAvatarForReplyPost(session, baseDir: str, httpPrefix: str,
                              domain: str, onionDomain: str, personCache: {},
                              postJsonObject: {}, debug: bool) -> None:
    """Tries to obtain the actor for the person being replied to
    so that their avatar can later be shown
    """
    if not postJsonObject.get('object'):
        return

    if not isinstance(postJsonObject['object'], dict):
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
                            domain, onionDomain)
        if pubKey:
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
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
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
            print('ERROR: unable to save previous like notification ' +
                  prevLikeFile)
            pass
        try:
            with open(likeFile, 'w+') as fp:
                fp.write(likeStr)
        except BaseException:
            print('ERROR: unable to write like notification file ' +
                  likeFile)
            pass


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


def _getGroupName(baseDir: str, handle: str) -> str:
    """Returns the preferred name of a group
    """
    actorFile = baseDir + '/accounts/' + handle + '.json'
    if not os.path.isfile(actorFile):
        return False
    actorJson = loadJson(actorFile)
    if not actorJson:
        return 'Group'
    return actorJson['name']


def _sendToGroupMembers(session, baseDir: str, handle: str, port: int,
                        postJsonObject: {},
                        httpPrefix: str, federationList: [],
                        sendThreads: [], postLog: [], cachedWebfingers: {},
                        personCache: {}, debug: bool) -> None:
    """When a post arrives for a group send it out to the group members
    """
    followersFile = baseDir + '/accounts/' + handle + '/followers.txt'
    if not os.path.isfile(followersFile):
        return
    if not postJsonObject.get('object'):
        return
    nickname = handle.split('@')[0]
#    groupname = _getGroupName(baseDir, handle)
    domain = handle.split('@')[1]
    domainFull = getFullDomain(domain, port)
    # set sender
    cc = ''
    sendingActor = postJsonObject['actor']
    sendingActorNickname = getNicknameFromActor(sendingActor)
    sendingActorDomain, sendingActorPort = \
        getDomainFromActor(sendingActor)
    sendingActorDomainFull = \
        getFullDomain(sendingActorDomain, sendingActorPort)
    senderStr = '@' + sendingActorNickname + '@' + sendingActorDomainFull
    if not postJsonObject['object']['content'].startswith(senderStr):
        postJsonObject['object']['content'] = \
            senderStr + ' ' + postJsonObject['object']['content']
        # add mention to tag list
        if not postJsonObject['object']['tag']:
            postJsonObject['object']['tag'] = []
        # check if the mention already exists
        mentionExists = False
        for mention in postJsonObject['object']['tag']:
            if mention['type'] == 'Mention':
                if mention.get('href'):
                    if mention['href'] == sendingActor:
                        mentionExists = True
        if not mentionExists:
            # add the mention of the original sender
            postJsonObject['object']['tag'].append({
                'href': sendingActor,
                'name': senderStr,
                'type': 'Mention'
            })

    postJsonObject['actor'] = \
        httpPrefix + '://' + domainFull + '/users/' + nickname
    postJsonObject['to'] = \
        [postJsonObject['actor'] + '/followers']
    postJsonObject['cc'] = [cc]
    postJsonObject['object']['to'] = postJsonObject['to']
    postJsonObject['object']['cc'] = [cc]
    # set subject
    if not postJsonObject['object'].get('summary'):
        postJsonObject['object']['summary'] = 'General Discussion'
    if ':' in domain:
        domain = domain.split(':')[0]
    with open(followersFile, 'r') as groupMembers:
        for memberHandle in groupMembers:
            if memberHandle != handle:
                memberNickname = memberHandle.split('@')[0]
                memberDomain = memberHandle.split('@')[1]
                memberPort = port
                if ':' in memberDomain:
                    memberPortStr = memberDomain.split(':')[1]
                    if memberPortStr.isdigit():
                        memberPort = int(memberPortStr)
                    memberDomain = memberDomain.split(':')[0]
                sendSignedJson(postJsonObject, session, baseDir,
                               nickname, domain, port,
                               memberNickname, memberDomain, memberPort, cc,
                               httpPrefix, False, False, federationList,
                               sendThreads, postLog, cachedWebfingers,
                               personCache, debug, __version__)


def _inboxUpdateCalendar(baseDir: str, handle: str,
                         postJsonObject: {}) -> None:
    """Detects whether the tag list on a post contains calendar events
    and if so saves the post id to a file in the calendar directory
    for the account
    """
    if not postJsonObject.get('actor'):
        return
    if not postJsonObject.get('object'):
        return
    if not isinstance(postJsonObject['object'], dict):
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

    if os.path.isfile(indexFilename):
        try:
            with open(indexFilename, 'r+') as indexFile:
                content = indexFile.read()
                if destinationFilename + '\n' not in content:
                    indexFile.seek(0, 0)
                    indexFile.write(destinationFilename + '\n' + content)
                return True
        except Exception as e:
            print('WARN: Failed to write entry to index ' + str(e))
    else:
        try:
            indexFile = open(indexFilename, 'w+')
            if indexFile:
                indexFile.write(destinationFilename + '\n')
                indexFile.close()
        except Exception as e:
            print('WARN: Failed to write initial entry to index ' + str(e))

    return False


def _updateLastSeen(baseDir: str, handle: str, actor: str) -> None:
    """Updates the time when the given handle last saw the given actor
    This can later be used to indicate if accounts are dormant/abandoned/moved
    """
    if '@' not in handle:
        return
    nickname = handle.split('@')[0]
    domain = handle.split('@')[1]
    if ':' in domain:
        domain = domain.split(':')[0]
    accountPath = baseDir + '/accounts/' + nickname + '@' + domain
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
                       unitTest: bool, YTReplacementDomain: str,
                       showPublishedDateOnly: bool,
                       allowLocalNetworkAccess: bool,
                       peertubeInstances: []) -> bool:
    """ Anything which needs to be done after initial checks have passed
    """
    actor = keyId
    if '#' in actor:
        actor = keyId.split('#')[0]

    _updateLastSeen(baseDir, handle, actor)

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
                    debug):
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
                        debug):
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
                        debug):
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
                            debug):
        if debug:
            print('DEBUG: Undo bookmark accepted from ' + actor)
        return False

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
                        allowLocalNetworkAccess):
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
    if _validPostContent(baseDir, nickname, domain,
                         postJsonObject, maxMentions, maxEmoji,
                         allowLocalNetworkAccess):

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
        replaceYouTube(postJsonObject, YTReplacementDomain)

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
                sendToFollowersThread(session, baseDir,
                                      nickname, domain,
                                      onionDomain, i2pDomain, port,
                                      httpPrefix, federationList,
                                      sendThreads, postLog,
                                      cachedWebfingers, personCache,
                                      postJsonObject, debug,
                                      __version__)

        isReplyToMutedPost = False

        if not isGroup:
            # create a DM notification file if needed
            postIsDM = isDM(postJsonObject)
            if postIsDM:
                if nickname != 'inbox':
                    followDMsFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + '/.followDMs'
                    if os.path.isfile(followDMsFilename):
                        followingFilename = \
                            baseDir + '/accounts/' + \
                            nickname + '@' + domain + '/following.txt'
                        if not postJsonObject.get('actor'):
                            return False
                        sendingActor = postJsonObject['actor']
                        sendingActorNickname = \
                            getNicknameFromActor(sendingActor)
                        sendingActorDomain, sendingActorPort = \
                            getDomainFromActor(sendingActor)
                        if sendingActorNickname and sendingActorDomain:
                            if not os.path.isfile(followingFilename):
                                print('No following.txt file exists for ' +
                                      nickname + '@' + domain +
                                      ' so not accepting DM from ' +
                                      sendingActorNickname + '@' +
                                      sendingActorDomain)
                                return False
                            sendH = \
                                sendingActorNickname + '@' + sendingActorDomain
                            if sendH != nickname + '@' + domain:
                                if sendH not in \
                                   open(followingFilename).read():
                                    print(nickname + '@' + domain +
                                          ' cannot receive DM from ' +
                                          sendH +
                                          ' because they do not ' +
                                          'follow them')
                                    return False
                        else:
                            return False
                    # dm index will be updated
                    updateIndexList.append('dm')
                    _dmNotify(baseDir, handle,
                              httpPrefix + '://' + domain + '/users/' +
                              nickname + '/dm')

            # get the actor being replied to
            domainFull = getFullDomain(domain, port)
            actor = httpPrefix + '://' + domainFull + \
                '/users/' + handle.split('@')[0]

            # create a reply notification file if needed
            if not postIsDM and isReply(postJsonObject, actor):
                if nickname != 'inbox':
                    # replies index will be updated
                    updateIndexList.append('tlreplies')
                    if postJsonObject['object'].get('inReplyTo'):
                        inReplyTo = postJsonObject['object']['inReplyTo']
                        if inReplyTo:
                            if isinstance(inReplyTo, str):
                                if not isMuted(baseDir, nickname, domain,
                                               inReplyTo):
                                    _replyNotify(baseDir, handle,
                                                 httpPrefix + '://' + domain +
                                                 '/users/' + nickname +
                                                 '/tlreplies')
                                else:
                                    isReplyToMutedPost = True

            if isImageMedia(session, baseDir, httpPrefix,
                            nickname, domain, postJsonObject,
                            translate, YTReplacementDomain,
                            allowLocalNetworkAccess):
                # media index will be updated
                updateIndexList.append('tlmedia')
            if isBlogPost(postJsonObject):
                # blogs index will be updated
                updateIndexList.append('tlblogs')
            elif isEventPost(postJsonObject):
                # events index will be updated
                updateIndexList.append('tlevents')

        # get the avatar for a reply/announce
        _obtainAvatarForReplyPost(session, baseDir,
                                  httpPrefix, domain, onionDomain,
                                  personCache, postJsonObject, debug)

        # save the post to file
        if saveJson(postJsonObject, destinationFilename):
            # If this is a reply to a muted post then also mute it.
            # This enables you to ignore a threat that's getting boring
            if isReplyToMutedPost:
                print('MUTE REPLY: ' + destinationFilename)
                muteFile = open(destinationFilename + '.muted', 'w+')
                if muteFile:
                    muteFile.write('\n')
                    muteFile.close()

            # update the indexes for different timelines
            for boxname in updateIndexList:
                if not inboxUpdateIndex(boxname, baseDir, handle,
                                        destinationFilename, debug):
                    print('ERROR: unable to update ' + boxname + ' index')
                else:
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
                                                   allowLocalNetworkAccess)
                        if debug:
                            timeDiff = \
                                str(int((time.time() - htmlCacheStartTime) *
                                        1000))
                            print('Saved ' + boxname +
                                  ' post as html to cache in ' +
                                  timeDiff + ' mS')

            _inboxUpdateCalendar(baseDir, handle, postJsonObject)

            handleName = handle.split('@')[0]
            storeHashTags(baseDir, handleName, postJsonObject)

            # send the post out to group members
            if isGroup:
                _sendToGroupMembers(session, baseDir, handle, port,
                                    postJsonObject,
                                    httpPrefix, federationList, sendThreads,
                                    postLog, cachedWebfingers, personCache,
                                    debug)

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
                        pass
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
                  showPublishedDateOnly: bool,
                  maxFollowers: int, allowLocalNetworkAccess: bool,
                  peertubeInstances: [],
                  verifyAllSignatures: bool) -> None:
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

    while True:
        time.sleep(1)

        # heartbeat to monitor whether the inbox queue is running
        heartBeatCtr += 5
        if heartBeatCtr >= 10:
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

        # limit the number of posts which can arrive per domain per day
        postDomain = queueJson['postDomain']
        if postDomain:
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
                                pass
                            queue.pop(0)
                        continue
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
                                pass
                            queue.pop(0)
                        continue
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
                                pass
                            queue.pop(0)
                        continue
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
                                pass
                            queue.pop(0)
                        continue
                    quotasPerMin['accounts'][postHandle] += 1
                else:
                    quotasPerMin['accounts'][postHandle] = 1

            if debug:
                if accountMaxPostsPerDay > 0 or domainMaxPostsPerDay > 0:
                    pprint(quotasDaily)

        if queueJson.get('actor'):
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
                                domain, onionDomain)
            if pubKey:
                if debug:
                    print('DEBUG: public key: ' + str(pubKey))
                break

            if debug:
                print('DEBUG: Retry ' + str(tries+1) +
                      ' obtaining public key for ' + keyId)
            time.sleep(1)

        if not pubKey:
            print('Queue: public key could not be obtained from ' + keyId)
            if os.path.isfile(queueFilename):
                os.remove(queueFilename)
            if len(queue) > 0:
                queue.pop(0)
            continue

        # check the http header signature
        if debug:
            print('DEBUG: checking http header signature')
            pprint(queueJson['httpHeaders'])
        postStr = json.dumps(queueJson['post'])
        if not verifyPostHeaders(httpPrefix,
                                 pubKey,
                                 queueJson['httpHeaders'],
                                 queueJson['path'], False,
                                 queueJson['digest'],
                                 postStr,
                                 debug):
            print('Queue: Header signature check failed')
            pprint(queueJson['httpHeaders'])
            if os.path.isfile(queueFilename):
                os.remove(queueFilename)
            if len(queue) > 0:
                queue.pop(0)
            continue

        if debug:
            print('DEBUG: http header signature check success')

        # check if a json signature exists on this post
        checkJsonSignature = False
        originalJson = queueJson['original']
        if originalJson.get('@context') and \
           originalJson.get('signature'):
            if isinstance(originalJson['signature'], dict):
                # see https://tools.ietf.org/html/rfc7515
                jwebsig = originalJson['signature']
                # signature exists and is of the expected type
                if jwebsig.get('type') and jwebsig.get('signatureValue'):
                    if jwebsig['type'] == 'RsaSignature2017':
                        if hasValidContext(originalJson):
                            checkJsonSignature = True
                        else:
                            print('unrecognised @context: ' +
                                  str(originalJson['@context']))

        # strict enforcement of json signatures
        if verifyAllSignatures and \
           not checkJsonSignature:
            print('inbox post does not have a jsonld signature ' +
                  keyId + ' ' + str(originalJson))
            if os.path.isfile(queueFilename):
                os.remove(queueFilename)
            if len(queue) > 0:
                queue.pop(0)
            continue

        if checkJsonSignature and verifyAllSignatures:
            # use the original json message received, not one which may have
            # been modified along the way
            if not verifyJsonSignature(originalJson, pubKey):
                if debug:
                    print('WARN: jsonld inbox signature check failed ' +
                          keyId + ' ' + pubKey + ' ' + str(originalJson))
                else:
                    print('WARN: jsonld inbox signature check failed ' +
                          keyId)
                if os.path.isfile(queueFilename):
                    os.remove(queueFilename)
                if len(queue) > 0:
                    queue.pop(0)
                continue
            else:
                print('jsonld inbox signature check success ' + keyId)

        # set the id to the same as the post filename
        # This makes the filename and the id consistent
        # if queueJson['post'].get('id'):
        #     queueJson['post']['id']=queueJson['id']

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
                os.remove(queueFilename)
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
                                maxFollowers):
            if os.path.isfile(queueFilename):
                os.remove(queueFilename)
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
                os.remove(queueFilename)
            if len(queue) > 0:
                queue.pop(0)
            continue

        if _receiveEventPost(recentPostsCache, session,
                             baseDir, httpPrefix,
                             domain, port,
                             sendThreads, postLog,
                             cachedWebfingers,
                             personCache,
                             queueJson['post'],
                             federationList,
                             queueJson['postNickname'],
                             debug):
            print('Queue: Event activity accepted from ' + keyId)
            if os.path.isfile(queueFilename):
                os.remove(queueFilename)
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
            print('Queue: Update accepted from ' + keyId)
            if os.path.isfile(queueFilename):
                os.remove(queueFilename)
            if len(queue) > 0:
                queue.pop(0)
            continue

        # get recipients list
        recipientsDict, recipientsDictFollowers = \
            _inboxPostRecipients(baseDir, queueJson['post'],
                                 httpPrefix, domain, port, debug)
        if len(recipientsDict.items()) == 0 and \
           len(recipientsDictFollowers.items()) == 0:
            print('Queue: no recipients were resolved ' +
                  'for post arriving in inbox')
            if os.path.isfile(queueFilename):
                os.remove(queueFilename)
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
                               showPublishedDateOnly,
                               allowLocalNetworkAccess,
                               peertubeInstances)
            if debug:
                pprint(queueJson['post'])

            print('Queue: Queue post accepted')
        if os.path.isfile(queueFilename):
            os.remove(queueFilename)
        if len(queue) > 0:
            queue.pop(0)
