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
from reaction import updateReactionCollection
from reaction import validEmojiContent
from utils import domainPermitted
from utils import isGroupAccount
from utils import isSystemAccount
from utils import invalidCiphertext
from utils import removeHtml
from utils import fileLastModified
from utils import hasObjectString
from utils import has_object_string_object
from utils import getReplyIntervalHours
from utils import canReplyTo
from utils import get_user_paths
from utils import get_base_content_from_post
from utils import acct_dir
from utils import removeDomainPort
from utils import getPortFromDomain
from utils import has_object_dict
from utils import dmAllowedFromDomain
from utils import isRecentPost
from utils import get_config_param
from utils import has_users_path
from utils import valid_post_date
from utils import get_full_domain
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
from utils import load_json
from utils import save_json
from utils import undoLikesCollectionEntry
from utils import undoReactionCollectionEntry
from utils import hasGroupType
from utils import local_actor_url
from utils import hasObjectStringType
from categories import getHashtagCategories
from categories import setHashtagCategory
from httpsig import getDigestAlgorithmFromHeaders
from httpsig import verifyPostHeaders
from session import createSession
from follow import followerApprovalActive
from follow import isFollowingActor
from follow import getFollowersOfActor
from follow import unfollowerOfAccount
from follow import isFollowerOfPerson
from follow import followedAccountAccepts
from follow import storeFollowRequest
from follow import noOfFollowRequests
from follow import getNoOfFollowers
from follow import followApprovalRequired
from pprint import pprint
from cache import storePersonInCache
from cache import getPersonPubKey
from acceptreject import receiveAcceptReject
from bookmarks import updateBookmarksCollection
from bookmarks import undoBookmarksCollectionEntry
from blocking import isBlocked
from blocking import isBlockedDomain
from blocking import broch_modeLapses
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
from person import validSendingActor


def _storeLastPostId(base_dir: str, nickname: str, domain: str,
                     post_json_object: {}) -> None:
    """Stores the id of the last post made by an actor
    When a new post arrives this allows it to be compared against the last
    to see if it is an edited post.
    It would be great if edited posts contained a back reference id to the
    source but we don't live in that ideal world.
    """
    actor = postId = None
    if has_object_dict(post_json_object):
        if post_json_object['object'].get('attributedTo'):
            if isinstance(post_json_object['object']['attributedTo'], str):
                actor = post_json_object['object']['attributedTo']
                postId = removeIdEnding(post_json_object['object']['id'])
    if not actor:
        actor = post_json_object['actor']
        postId = removeIdEnding(post_json_object['id'])
    if not actor:
        return
    lastpostDir = acct_dir(base_dir, nickname, domain) + '/lastpost'
    if not os.path.isdir(lastpostDir):
        os.mkdir(lastpostDir)
    actorFilename = lastpostDir + '/' + actor.replace('/', '#')
    try:
        with open(actorFilename, 'w+') as fp:
            fp.write(postId)
    except OSError:
        print('EX: Unable to write last post id to ' + actorFilename)


def _updateCachedHashtagSwarm(base_dir: str, nickname: str, domain: str,
                              http_prefix: str, domain_full: str,
                              translate: {}) -> bool:
    """Updates the hashtag swarm stored as a file
    """
    cachedHashtagSwarmFilename = \
        acct_dir(base_dir, nickname, domain) + '/.hashtagSwarm'
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
        actor = local_actor_url(http_prefix, nickname, domain_full)
        newSwarmStr = htmlHashTagSwarm(base_dir, actor, translate)
        if newSwarmStr:
            try:
                with open(cachedHashtagSwarmFilename, 'w+') as fp:
                    fp.write(newSwarmStr)
                    return True
            except OSError:
                print('EX: unable to write cached hashtag swarm ' +
                      cachedHashtagSwarmFilename)
    return False


def storeHashTags(base_dir: str, nickname: str, domain: str,
                  http_prefix: str, domain_full: str,
                  post_json_object: {}, translate: {}) -> None:
    """Extracts hashtags from an incoming post and updates the
    relevant tags files.
    """
    if not isPublicPost(post_json_object):
        return
    if not has_object_dict(post_json_object):
        return
    if not post_json_object['object'].get('tag'):
        return
    if not post_json_object.get('id'):
        return
    if not isinstance(post_json_object['object']['tag'], list):
        return
    tagsDir = base_dir + '/tags'

    # add tags directory if it doesn't exist
    if not os.path.isdir(tagsDir):
        print('Creating tags directory')
        os.mkdir(tagsDir)

    hashtagCategories = getHashtagCategories(base_dir)

    hashtagsCtr = 0
    for tag in post_json_object['object']['tag']:
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
        postUrl = removeIdEnding(post_json_object['id'])
        postUrl = postUrl.replace('/', '#')
        daysDiff = datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
        daysSinceEpoch = daysDiff.days
        tagline = str(daysSinceEpoch) + '  ' + nickname + '  ' + postUrl + '\n'
        hashtagsCtr += 1
        if not os.path.isfile(tagsFilename):
            try:
                with open(tagsFilename, 'w+') as tagsFile:
                    tagsFile.write(tagline)
            except OSError:
                print('EX: unable to write ' + tagsFilename)
        else:
            if postUrl not in open(tagsFilename).read():
                try:
                    with open(tagsFilename, 'r+') as tagsFile:
                        content = tagsFile.read()
                        if tagline not in content:
                            tagsFile.seek(0, 0)
                            tagsFile.write(tagline + content)
                except OSError as ex:
                    print('EX: Failed to write entry to tags file ' +
                          tagsFilename + ' ' + str(ex))
                removeOldHashtags(base_dir, 3)

        # automatically assign a category to the tag if possible
        categoryFilename = tagsDir + '/' + tagName + '.category'
        if not os.path.isfile(categoryFilename):
            categoryStr = \
                guessHashtagCategory(tagName, hashtagCategories)
            if categoryStr:
                setHashtagCategory(base_dir, tagName, categoryStr, False)

    # if some hashtags were found then recalculate the swarm
    # ready for later display
    if hashtagsCtr > 0:
        _updateCachedHashtagSwarm(base_dir, nickname, domain,
                                  http_prefix, domain_full, translate)


def _inboxStorePostToHtmlCache(recentPostsCache: {}, max_recent_posts: int,
                               translate: {},
                               base_dir: str, http_prefix: str,
                               session, cached_webfingers: {},
                               person_cache: {},
                               nickname: str, domain: str, port: int,
                               post_json_object: {},
                               allow_deletion: bool, boxname: str,
                               show_published_date_only: bool,
                               peertube_instances: [],
                               allow_local_network_access: bool,
                               theme_name: str, system_language: str,
                               max_like_count: int,
                               signing_priv_key_pem: str,
                               cw_lists: {},
                               lists_enabled: str) -> None:
    """Converts the json post into html and stores it in a cache
    This enables the post to be quickly displayed later
    """
    pageNumber = -999
    avatarUrl = None
    if boxname != 'outbox':
        boxname = 'inbox'

    notDM = not isDM(post_json_object)
    yt_replace_domain = get_config_param(base_dir, 'youtubedomain')
    twitter_replacement_domain = get_config_param(base_dir, 'twitterdomain')
    individualPostAsHtml(signing_priv_key_pem,
                         True, recentPostsCache, max_recent_posts,
                         translate, pageNumber,
                         base_dir, session, cached_webfingers,
                         person_cache,
                         nickname, domain, port, post_json_object,
                         avatarUrl, True, allow_deletion,
                         http_prefix, __version__, boxname,
                         yt_replace_domain, twitter_replacement_domain,
                         show_published_date_only,
                         peertube_instances, allow_local_network_access,
                         theme_name, system_language, max_like_count,
                         notDM, True, True, False, True, False,
                         cw_lists, lists_enabled)


def validInbox(base_dir: str, nickname: str, domain: str) -> bool:
    """Checks whether files were correctly saved to the inbox
    """
    domain = removeDomainPort(domain)
    inboxDir = acct_dir(base_dir, nickname, domain) + '/inbox'
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


def validInboxFilenames(base_dir: str, nickname: str, domain: str,
                        expectedDomain: str, expectedPort: int) -> bool:
    """Used by unit tests to check that the port number gets appended to
    domain names within saved post filenames
    """
    domain = removeDomainPort(domain)
    inboxDir = acct_dir(base_dir, nickname, domain) + '/inbox'
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


def inboxMessageHasParams(message_json: {}) -> bool:
    """Checks whether an incoming message contains expected parameters
    """
    expectedParams = ['actor', 'type', 'object']
    for param in expectedParams:
        if not message_json.get(param):
            # print('inboxMessageHasParams: ' +
            #       param + ' ' + str(message_json))
            return False

    # actor should be a string
    if not isinstance(message_json['actor'], str):
        print('WARN: actor should be a string, but is actually: ' +
              str(message_json['actor']))
        pprint(message_json)
        return False

    # type should be a string
    if not isinstance(message_json['type'], str):
        print('WARN: type from ' + str(message_json['actor']) +
              ' should be a string, but is actually: ' +
              str(message_json['type']))
        return False

    # object should be a dict or a string
    if not has_object_dict(message_json):
        if not isinstance(message_json['object'], str):
            print('WARN: object from ' + str(message_json['actor']) +
                  ' should be a dict or string, but is actually: ' +
                  str(message_json['object']))
            return False

    if not message_json.get('to'):
        allowedWithoutToParam = ['Like', 'EmojiReact',
                                 'Follow', 'Join', 'Request',
                                 'Accept', 'Capability', 'Undo']
        if message_json['type'] not in allowedWithoutToParam:
            return False
    return True


def inboxPermittedMessage(domain: str, message_json: {},
                          federation_list: []) -> bool:
    """ check that we are receiving from a permitted domain
    """
    if not hasActor(message_json, False):
        return False

    actor = message_json['actor']
    # always allow the local domain
    if domain in actor:
        return True

    if not urlPermitted(actor, federation_list):
        return False

    alwaysAllowedTypes = (
        'Follow', 'Join', 'Like', 'EmojiReact', 'Delete', 'Announce'
    )
    if message_json['type'] not in alwaysAllowedTypes:
        if not has_object_dict(message_json):
            return True
        if message_json['object'].get('inReplyTo'):
            inReplyTo = message_json['object']['inReplyTo']
            if not isinstance(inReplyTo, str):
                return False
            if not urlPermitted(inReplyTo, federation_list):
                return False

    return True


def savePostToInboxQueue(base_dir: str, http_prefix: str,
                         nickname: str, domain: str,
                         post_json_object: {},
                         originalPostJsonObject: {},
                         messageBytes: str,
                         httpHeaders: {},
                         postPath: str, debug: bool,
                         blockedCache: [], system_language: str) -> str:
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
    if post_json_object.get('actor'):
        if not isinstance(post_json_object['actor'], str):
            return None
        actor = post_json_object['actor']
        postNickname = getNicknameFromActor(post_json_object['actor'])
        if not postNickname:
            print('No post Nickname in actor ' + post_json_object['actor'])
            return None
        postDomain, postPort = getDomainFromActor(post_json_object['actor'])
        if not postDomain:
            if debug:
                pprint(post_json_object)
            print('No post Domain in actor')
            return None
        if isBlocked(base_dir, nickname, domain,
                     postNickname, postDomain, blockedCache):
            if debug:
                print('DEBUG: post from ' + postNickname + ' blocked')
            return None
        postDomain = get_full_domain(postDomain, postPort)

    if has_object_dict(post_json_object):
        if post_json_object['object'].get('inReplyTo'):
            if isinstance(post_json_object['object']['inReplyTo'], str):
                inReplyTo = \
                    post_json_object['object']['inReplyTo']
                replyDomain, replyPort = \
                    getDomainFromActor(inReplyTo)
                if isBlockedDomain(base_dir, replyDomain, blockedCache):
                    if debug:
                        print('WARN: post contains reply from ' +
                              str(actor) +
                              ' to a blocked domain: ' + replyDomain)
                    return None
                else:
                    replyNickname = \
                        getNicknameFromActor(inReplyTo)
                    if replyNickname and replyDomain:
                        if isBlocked(base_dir, nickname, domain,
                                     replyNickname, replyDomain,
                                     blockedCache):
                            if debug:
                                print('WARN: post contains reply from ' +
                                      str(actor) +
                                      ' to a blocked account: ' +
                                      replyNickname + '@' + replyDomain)
                            return None
        if post_json_object['object'].get('content'):
            contentStr = \
                get_base_content_from_post(post_json_object, system_language)
            if contentStr:
                if isFiltered(base_dir, nickname, domain, contentStr):
                    if debug:
                        print('WARN: post was filtered out due to content')
                    return None
    originalPostId = None
    if post_json_object.get('id'):
        if not isinstance(post_json_object['id'], str):
            return None
        originalPostId = removeIdEnding(post_json_object['id'])

    curr_time = datetime.datetime.utcnow()

    postId = None
    if post_json_object.get('id'):
        postId = removeIdEnding(post_json_object['id'])
        published = curr_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not postId:
        statusNumber, published = getStatusNumber()
        if actor:
            postId = actor + '/statuses/' + statusNumber
        else:
            postId = local_actor_url(http_prefix, nickname, originalDomain) + \
                '/statuses/' + statusNumber

    # NOTE: don't change post_json_object['id'] before signature check

    inbox_queueDir = createInboxQueueDir(nickname, domain, base_dir)

    handle = nickname + '@' + domain
    destination = base_dir + '/accounts/' + \
        handle + '/inbox/' + postId.replace('/', '#') + '.json'
    filename = inbox_queueDir + '/' + postId.replace('/', '#') + '.json'

    sharedInboxItem = False
    if nickname == 'inbox':
        nickname = originalDomain
        sharedInboxItem = True

    digestStartTime = time.time()
    digestAlgorithm = getDigestAlgorithmFromHeaders(httpHeaders)
    digest = messageContentDigest(messageBytes, digestAlgorithm)
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
        'post': post_json_object,
        'original': originalPostJsonObject,
        'digest': digest,
        'filename': filename,
        'destination': destination
    }

    if debug:
        print('Inbox queue item created')
    save_json(newQueueItem, filename)
    return filename


def _inboxPostRecipientsAdd(base_dir: str, http_prefix: str, toList: [],
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
            if os.path.isdir(base_dir + '/accounts/' + handle):
                recipientsDict[handle] = None
            else:
                if debug:
                    print('DEBUG: ' + base_dir + '/accounts/' +
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


def _inboxPostRecipients(base_dir: str, post_json_object: {},
                         http_prefix: str, domain: str, port: int,
                         debug: bool) -> ([], []):
    """Returns dictionaries containing the recipients of the given post
    The shared dictionary contains followers
    """
    recipientsDict = {}
    recipientsDictFollowers = {}

    if not post_json_object.get('actor'):
        if debug:
            pprint(post_json_object)
            print('WARNING: inbox post has no actor')
        return recipientsDict, recipientsDictFollowers

    domain = removeDomainPort(domain)
    domainBase = domain
    domain = get_full_domain(domain, port)
    domainMatch = '/' + domain + '/users/'

    actor = post_json_object['actor']
    # first get any specific people which the post is addressed to

    followerRecipients = False
    if has_object_dict(post_json_object):
        if post_json_object['object'].get('to'):
            if isinstance(post_json_object['object']['to'], list):
                recipientsList = post_json_object['object']['to']
            else:
                recipientsList = [post_json_object['object']['to']]
            if debug:
                print('DEBUG: resolving "to"')
            includesFollowers, recipientsDict = \
                _inboxPostRecipientsAdd(base_dir, http_prefix,
                                        recipientsList,
                                        recipientsDict,
                                        domainMatch, domainBase,
                                        actor, debug)
            if includesFollowers:
                followerRecipients = True
        else:
            if debug:
                print('DEBUG: inbox post has no "to"')

        if post_json_object['object'].get('cc'):
            if isinstance(post_json_object['object']['cc'], list):
                recipientsList = post_json_object['object']['cc']
            else:
                recipientsList = [post_json_object['object']['cc']]
            includesFollowers, recipientsDict = \
                _inboxPostRecipientsAdd(base_dir, http_prefix,
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
        if debug and post_json_object.get('object'):
            if isinstance(post_json_object['object'], str):
                if '/statuses/' in post_json_object['object']:
                    print('DEBUG: inbox item is a link to a post')
                else:
                    if '/users/' in post_json_object['object']:
                        print('DEBUG: inbox item is a link to an actor')

    if post_json_object.get('to'):
        if isinstance(post_json_object['to'], list):
            recipientsList = post_json_object['to']
        else:
            recipientsList = [post_json_object['to']]
        includesFollowers, recipientsDict = \
            _inboxPostRecipientsAdd(base_dir, http_prefix,
                                    recipientsList,
                                    recipientsDict,
                                    domainMatch, domainBase,
                                    actor, debug)
        if includesFollowers:
            followerRecipients = True

    if post_json_object.get('cc'):
        if isinstance(post_json_object['cc'], list):
            recipientsList = post_json_object['cc']
        else:
            recipientsList = [post_json_object['cc']]
        includesFollowers, recipientsDict = \
            _inboxPostRecipientsAdd(base_dir, http_prefix,
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
        getFollowersOfActor(base_dir, actor, debug)

    return recipientsDict, recipientsDictFollowers


def _receiveUndoFollow(session, base_dir: str, http_prefix: str,
                       port: int, message_json: {},
                       federation_list: [],
                       debug: bool) -> bool:
    if not message_json['object'].get('actor'):
        if debug:
            print('DEBUG: follow request has no actor within object')
        return False
    if not has_users_path(message_json['object']['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing ' +
                  'from actor within object')
        return False
    if message_json['object']['actor'] != message_json['actor']:
        if debug:
            print('DEBUG: actors do not match')
        return False

    nicknameFollower = \
        getNicknameFromActor(message_json['object']['actor'])
    if not nicknameFollower:
        print('WARN: unable to find nickname in ' +
              message_json['object']['actor'])
        return False
    domainFollower, portFollower = \
        getDomainFromActor(message_json['object']['actor'])
    domainFollowerFull = get_full_domain(domainFollower, portFollower)

    nicknameFollowing = \
        getNicknameFromActor(message_json['object']['object'])
    if not nicknameFollowing:
        print('WARN: unable to find nickname in ' +
              message_json['object']['object'])
        return False
    domainFollowing, portFollowing = \
        getDomainFromActor(message_json['object']['object'])
    domainFollowingFull = get_full_domain(domainFollowing, portFollowing)

    group_account = \
        hasGroupType(base_dir, message_json['object']['actor'], None)
    if unfollowerOfAccount(base_dir,
                           nicknameFollowing, domainFollowingFull,
                           nicknameFollower, domainFollowerFull,
                           debug, group_account):
        print(nicknameFollowing + '@' + domainFollowingFull + ': '
              'Follower ' + nicknameFollower + '@' + domainFollowerFull +
              ' was removed')
        return True

    if debug:
        print('DEBUG: Follower ' +
              nicknameFollower + '@' + domainFollowerFull +
              ' was not removed')
    return False


def _receiveUndo(session, base_dir: str, http_prefix: str,
                 port: int, send_threads: [], postLog: [],
                 cached_webfingers: {}, person_cache: {},
                 message_json: {}, federation_list: [],
                 debug: bool) -> bool:
    """Receives an undo request within the POST section of HTTPServer
    """
    if not message_json['type'].startswith('Undo'):
        return False
    if debug:
        print('DEBUG: Undo activity received')
    if not hasActor(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor')
        return False
    if not hasObjectStringType(message_json, debug):
        return False
    if not has_object_string_object(message_json, debug):
        return False
    if message_json['object']['type'] == 'Follow' or \
       message_json['object']['type'] == 'Join':
        return _receiveUndoFollow(session, base_dir, http_prefix,
                                  port, message_json,
                                  federation_list, debug)
    return False


def _personReceiveUpdate(base_dir: str,
                         domain: str, port: int,
                         updateNickname: str, updateDomain: str,
                         updatePort: int,
                         personJson: {}, person_cache: {},
                         debug: bool) -> bool:
    """Changes an actor. eg: avatar or display name change
    """
    if debug:
        print('Receiving actor update for ' + personJson['url'] +
              ' ' + str(personJson))
    domain_full = get_full_domain(domain, port)
    updateDomainFull = get_full_domain(updateDomain, updatePort)
    usersPaths = get_user_paths()
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
    if updateDomainFull == domain_full:
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
    actorFilename = base_dir + '/cache/actors/' + \
        personJson['id'].replace('/', '#') + '.json'
    # check that the public keys match.
    # If they don't then this may be a nefarious attempt to hack an account
    idx = personJson['id']
    if person_cache.get(idx):
        if person_cache[idx]['actor']['publicKey']['publicKeyPem'] != \
           personJson['publicKey']['publicKeyPem']:
            if debug:
                print('WARN: Public key does not match when updating actor')
            return False
    else:
        if os.path.isfile(actorFilename):
            existingPersonJson = load_json(actorFilename)
            if existingPersonJson:
                if existingPersonJson['publicKey']['publicKeyPem'] != \
                   personJson['publicKey']['publicKeyPem']:
                    if debug:
                        print('WARN: Public key does not match ' +
                              'cached actor when updating')
                    return False
    # save to cache in memory
    storePersonInCache(base_dir, personJson['id'], personJson,
                       person_cache, True)
    # save to cache on file
    if save_json(personJson, actorFilename):
        if debug:
            print('actor updated for ' + personJson['id'])

    # remove avatar if it exists so that it will be refreshed later
    # when a timeline is constructed
    actorStr = personJson['id'].replace('/', '-')
    removeAvatarFromCache(base_dir, actorStr)
    return True


def _receiveUpdateToQuestion(recentPostsCache: {}, message_json: {},
                             base_dir: str,
                             nickname: str, domain: str) -> None:
    """Updating a question as new votes arrive
    """
    # message url of the question
    if not message_json.get('id'):
        return
    if not hasActor(message_json, False):
        return
    messageId = removeIdEnding(message_json['id'])
    if '#' in messageId:
        messageId = messageId.split('#', 1)[0]
    # find the question post
    postFilename = locatePost(base_dir, nickname, domain, messageId)
    if not postFilename:
        return
    # load the json for the question
    post_json_object = load_json(postFilename, 1)
    if not post_json_object:
        return
    if not post_json_object.get('actor'):
        return
    # does the actor match?
    if post_json_object['actor'] != message_json['actor']:
        return
    save_json(message_json, postFilename)
    # ensure that the cached post is removed if it exists, so
    # that it then will be recreated
    cachedPostFilename = \
        getCachedPostFilename(base_dir, nickname, domain, message_json)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                print('EX: _receiveUpdateToQuestion unable to delete ' +
                      cachedPostFilename)
    # remove from memory cache
    removePostFromCache(message_json, recentPostsCache)


def _receiveUpdate(recentPostsCache: {}, session, base_dir: str,
                   http_prefix: str, domain: str, port: int,
                   send_threads: [], postLog: [], cached_webfingers: {},
                   person_cache: {}, message_json: {}, federation_list: [],
                   nickname: str, debug: bool) -> bool:
    """Receives an Update activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Update':
        return False
    if not hasActor(message_json, debug):
        return False
    if not hasObjectStringType(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False

    if message_json['object']['type'] == 'Question':
        _receiveUpdateToQuestion(recentPostsCache, message_json,
                                 base_dir, nickname, domain)
        if debug:
            print('DEBUG: Question update was received')
        return True

    if message_json['object']['type'] == 'Person' or \
       message_json['object']['type'] == 'Application' or \
       message_json['object']['type'] == 'Group' or \
       message_json['object']['type'] == 'Service':
        if message_json['object'].get('url') and \
           message_json['object'].get('id'):
            if debug:
                print('Request to update actor: ' + str(message_json))
            updateNickname = getNicknameFromActor(message_json['actor'])
            if updateNickname:
                updateDomain, updatePort = \
                    getDomainFromActor(message_json['actor'])
                if _personReceiveUpdate(base_dir,
                                        domain, port,
                                        updateNickname, updateDomain,
                                        updatePort,
                                        message_json['object'],
                                        person_cache, debug):
                    print('Person Update: ' + str(message_json))
                    if debug:
                        print('DEBUG: Profile update was received for ' +
                              message_json['object']['url'])
                        return True
    return False


def _receiveLike(recentPostsCache: {},
                 session, handle: str, isGroup: bool, base_dir: str,
                 http_prefix: str, domain: str, port: int,
                 onion_domain: str,
                 send_threads: [], postLog: [], cached_webfingers: {},
                 person_cache: {}, message_json: {}, federation_list: [],
                 debug: bool,
                 signing_priv_key_pem: str,
                 max_recent_posts: int, translate: {},
                 allow_deletion: bool,
                 yt_replace_domain: str,
                 twitter_replacement_domain: str,
                 peertube_instances: [],
                 allow_local_network_access: bool,
                 theme_name: str, system_language: str,
                 max_like_count: int, cw_lists: {},
                 lists_enabled: str) -> bool:
    """Receives a Like activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Like':
        return False
    if not hasActor(message_json, debug):
        return False
    if not hasObjectString(message_json, debug):
        return False
    if not message_json.get('to'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "to" list')
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False
    if '/statuses/' not in message_json['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  message_json['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of like - ' + handle)
    # if this post in the outbox of the person?
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    postLikedId = message_json['object']
    postFilename = locatePost(base_dir, handleName, handleDom, postLikedId)
    if not postFilename:
        if debug:
            print('DEBUG: post not found in inbox or outbox')
            print(postLikedId)
        return True
    if debug:
        print('DEBUG: liked post found in inbox')

    likeActor = message_json['actor']
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    if not _alreadyLiked(base_dir,
                         handleName, handleDom,
                         postLikedId,
                         likeActor):
        _likeNotify(base_dir, domain, onion_domain, handle,
                    likeActor, postLikedId)
    updateLikesCollection(recentPostsCache, base_dir, postFilename,
                          postLikedId, likeActor,
                          handleName, domain, debug, None)
    # regenerate the html
    likedPostJson = load_json(postFilename, 0, 1)
    if likedPostJson:
        if likedPostJson.get('type'):
            if likedPostJson['type'] == 'Announce' and \
               likedPostJson.get('object'):
                if isinstance(likedPostJson['object'], str):
                    announceLikeUrl = likedPostJson['object']
                    announceLikedFilename = \
                        locatePost(base_dir, handleName,
                                   domain, announceLikeUrl)
                    if announceLikedFilename:
                        postLikedId = announceLikeUrl
                        postFilename = announceLikedFilename
                        updateLikesCollection(recentPostsCache,
                                              base_dir,
                                              postFilename,
                                              postLikedId,
                                              likeActor,
                                              handleName,
                                              domain, debug, None)
        if likedPostJson:
            if debug:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, handleName, domain,
                                          likedPostJson)
                print('Liked post json: ' + str(likedPostJson))
                print('Liked post nickname: ' + handleName + ' ' + domain)
                print('Liked post cache: ' + str(cachedPostFilename))
            pageNumber = 1
            show_published_date_only = False
            showIndividualPostIcons = True
            manuallyApproveFollowers = \
                followerApprovalActive(base_dir, handleName, domain)
            notDM = not isDM(likedPostJson)
            individualPostAsHtml(signing_priv_key_pem, False,
                                 recentPostsCache, max_recent_posts,
                                 translate, pageNumber, base_dir,
                                 session, cached_webfingers, person_cache,
                                 handleName, domain, port, likedPostJson,
                                 None, True, allow_deletion,
                                 http_prefix, __version__,
                                 'inbox',
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 peertube_instances,
                                 allow_local_network_access,
                                 theme_name, system_language,
                                 max_like_count, notDM,
                                 showIndividualPostIcons,
                                 manuallyApproveFollowers,
                                 False, True, False, cw_lists,
                                 lists_enabled)
    return True


def _receiveUndoLike(recentPostsCache: {},
                     session, handle: str, isGroup: bool, base_dir: str,
                     http_prefix: str, domain: str, port: int,
                     send_threads: [], postLog: [], cached_webfingers: {},
                     person_cache: {}, message_json: {}, federation_list: [],
                     debug: bool,
                     signing_priv_key_pem: str,
                     max_recent_posts: int, translate: {},
                     allow_deletion: bool,
                     yt_replace_domain: str,
                     twitter_replacement_domain: str,
                     peertube_instances: [],
                     allow_local_network_access: bool,
                     theme_name: str, system_language: str,
                     max_like_count: int, cw_lists: {},
                     lists_enabled: str) -> bool:
    """Receives an undo like activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Undo':
        return False
    if not hasActor(message_json, debug):
        return False
    if not hasObjectStringType(message_json, debug):
        return False
    if message_json['object']['type'] != 'Like':
        return False
    if not has_object_string_object(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + ' like')
        return False
    if '/statuses/' not in message_json['object']['object']:
        if debug:
            print('DEBUG: "statuses" missing from like object in ' +
                  message_json['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of undo like - ' + handle)
    # if this post in the outbox of the person?
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    postFilename = \
        locatePost(base_dir, handleName, handleDom,
                   message_json['object']['object'])
    if not postFilename:
        if debug:
            print('DEBUG: unliked post not found in inbox or outbox')
            print(message_json['object']['object'])
        return True
    if debug:
        print('DEBUG: liked post found in inbox. Now undoing.')
    likeActor = message_json['actor']
    postLikedId = message_json['object']
    undoLikesCollectionEntry(recentPostsCache, base_dir, postFilename,
                             postLikedId, likeActor, domain, debug, None)
    # regenerate the html
    likedPostJson = load_json(postFilename, 0, 1)
    if likedPostJson:
        if likedPostJson.get('type'):
            if likedPostJson['type'] == 'Announce' and \
               likedPostJson.get('object'):
                if isinstance(likedPostJson['object'], str):
                    announceLikeUrl = likedPostJson['object']
                    announceLikedFilename = \
                        locatePost(base_dir, handleName,
                                   domain, announceLikeUrl)
                    if announceLikedFilename:
                        postLikedId = announceLikeUrl
                        postFilename = announceLikedFilename
                        undoLikesCollectionEntry(recentPostsCache, base_dir,
                                                 postFilename, postLikedId,
                                                 likeActor, domain, debug,
                                                 None)
        if likedPostJson:
            if debug:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, handleName, domain,
                                          likedPostJson)
                print('Unliked post json: ' + str(likedPostJson))
                print('Unliked post nickname: ' + handleName + ' ' + domain)
                print('Unliked post cache: ' + str(cachedPostFilename))
            pageNumber = 1
            show_published_date_only = False
            showIndividualPostIcons = True
            manuallyApproveFollowers = \
                followerApprovalActive(base_dir, handleName, domain)
            notDM = not isDM(likedPostJson)
            individualPostAsHtml(signing_priv_key_pem, False,
                                 recentPostsCache, max_recent_posts,
                                 translate, pageNumber, base_dir,
                                 session, cached_webfingers, person_cache,
                                 handleName, domain, port, likedPostJson,
                                 None, True, allow_deletion,
                                 http_prefix, __version__,
                                 'inbox',
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 peertube_instances,
                                 allow_local_network_access,
                                 theme_name, system_language,
                                 max_like_count, notDM,
                                 showIndividualPostIcons,
                                 manuallyApproveFollowers,
                                 False, True, False, cw_lists,
                                 lists_enabled)
    return True


def _receiveReaction(recentPostsCache: {},
                     session, handle: str, isGroup: bool, base_dir: str,
                     http_prefix: str, domain: str, port: int,
                     onion_domain: str,
                     send_threads: [], postLog: [], cached_webfingers: {},
                     person_cache: {}, message_json: {}, federation_list: [],
                     debug: bool,
                     signing_priv_key_pem: str,
                     max_recent_posts: int, translate: {},
                     allow_deletion: bool,
                     yt_replace_domain: str,
                     twitter_replacement_domain: str,
                     peertube_instances: [],
                     allow_local_network_access: bool,
                     theme_name: str, system_language: str,
                     max_like_count: int, cw_lists: {},
                     lists_enabled: str) -> bool:
    """Receives an emoji reaction within the POST section of HTTPServer
    """
    if message_json['type'] != 'EmojiReact':
        return False
    if not hasActor(message_json, debug):
        return False
    if not hasObjectString(message_json, debug):
        return False
    if not message_json.get('to'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "to" list')
        return False
    if not message_json.get('content'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "content"')
        return False
    if not isinstance(message_json['content'], str):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' content is not string')
        return False
    if not validEmojiContent(message_json['content']):
        print('_receiveReaction: Invalid emoji reaction: "' +
              message_json['content'] + '" from ' + message_json['actor'])
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False
    if '/statuses/' not in message_json['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  message_json['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of emoji reaction - ' + handle)
    if os.path.isfile(base_dir + '/accounts/' + handle +
                      '/.hideReactionButton'):
        print('Emoji reaction rejected by ' + handle +
              ' due to their settings')
        return True
    # if this post in the outbox of the person?
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]

    postReactionId = message_json['object']
    emojiContent = removeHtml(message_json['content'])
    if not emojiContent:
        if debug:
            print('DEBUG: emoji reaction has no content')
        return True
    postFilename = locatePost(base_dir, handleName, handleDom, postReactionId)
    if not postFilename:
        if debug:
            print('DEBUG: emoji reaction post not found in inbox or outbox')
            print(postReactionId)
        return True
    if debug:
        print('DEBUG: emoji reaction post found in inbox')

    reactionActor = message_json['actor']
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    if not _alreadyReacted(base_dir,
                           handleName, handleDom,
                           postReactionId,
                           reactionActor,
                           emojiContent):
        _reactionNotify(base_dir, domain, onion_domain, handle,
                        reactionActor, postReactionId, emojiContent)
    updateReactionCollection(recentPostsCache, base_dir, postFilename,
                             postReactionId, reactionActor,
                             handleName, domain, debug, None, emojiContent)
    # regenerate the html
    reactionPostJson = load_json(postFilename, 0, 1)
    if reactionPostJson:
        if reactionPostJson.get('type'):
            if reactionPostJson['type'] == 'Announce' and \
               reactionPostJson.get('object'):
                if isinstance(reactionPostJson['object'], str):
                    announceReactionUrl = reactionPostJson['object']
                    announceReactionFilename = \
                        locatePost(base_dir, handleName,
                                   domain, announceReactionUrl)
                    if announceReactionFilename:
                        postReactionId = announceReactionUrl
                        postFilename = announceReactionFilename
                        updateReactionCollection(recentPostsCache,
                                                 base_dir,
                                                 postFilename,
                                                 postReactionId,
                                                 reactionActor,
                                                 handleName,
                                                 domain, debug, None,
                                                 emojiContent)
        if reactionPostJson:
            if debug:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, handleName, domain,
                                          reactionPostJson)
                print('Reaction post json: ' + str(reactionPostJson))
                print('Reaction post nickname: ' + handleName + ' ' + domain)
                print('Reaction post cache: ' + str(cachedPostFilename))
            pageNumber = 1
            show_published_date_only = False
            showIndividualPostIcons = True
            manuallyApproveFollowers = \
                followerApprovalActive(base_dir, handleName, domain)
            notDM = not isDM(reactionPostJson)
            individualPostAsHtml(signing_priv_key_pem, False,
                                 recentPostsCache, max_recent_posts,
                                 translate, pageNumber, base_dir,
                                 session, cached_webfingers, person_cache,
                                 handleName, domain, port, reactionPostJson,
                                 None, True, allow_deletion,
                                 http_prefix, __version__,
                                 'inbox',
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 peertube_instances,
                                 allow_local_network_access,
                                 theme_name, system_language,
                                 max_like_count, notDM,
                                 showIndividualPostIcons,
                                 manuallyApproveFollowers,
                                 False, True, False, cw_lists,
                                 lists_enabled)
    return True


def _receiveUndoReaction(recentPostsCache: {},
                         session, handle: str, isGroup: bool, base_dir: str,
                         http_prefix: str, domain: str, port: int,
                         send_threads: [], postLog: [],
                         cached_webfingers: {},
                         person_cache: {}, message_json: {},
                         federation_list: [],
                         debug: bool,
                         signing_priv_key_pem: str,
                         max_recent_posts: int, translate: {},
                         allow_deletion: bool,
                         yt_replace_domain: str,
                         twitter_replacement_domain: str,
                         peertube_instances: [],
                         allow_local_network_access: bool,
                         theme_name: str, system_language: str,
                         max_like_count: int, cw_lists: {},
                         lists_enabled: str) -> bool:
    """Receives an undo emoji reaction within the POST section of HTTPServer
    """
    if message_json['type'] != 'Undo':
        return False
    if not hasActor(message_json, debug):
        return False
    if not hasObjectStringType(message_json, debug):
        return False
    if message_json['object']['type'] != 'EmojiReact':
        return False
    if not has_object_string_object(message_json, debug):
        return False
    if not message_json['object'].get('content'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "content"')
        return False
    if not isinstance(message_json['object']['content'], str):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' content is not string')
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + ' reaction')
        return False
    if '/statuses/' not in message_json['object']['object']:
        if debug:
            print('DEBUG: "statuses" missing from reaction object in ' +
                  message_json['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of undo reaction - ' + handle)
    # if this post in the outbox of the person?
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    postFilename = \
        locatePost(base_dir, handleName, handleDom,
                   message_json['object']['object'])
    if not postFilename:
        if debug:
            print('DEBUG: unreaction post not found in inbox or outbox')
            print(message_json['object']['object'])
        return True
    if debug:
        print('DEBUG: reaction post found in inbox. Now undoing.')
    reactionActor = message_json['actor']
    postReactionId = message_json['object']
    emojiContent = removeHtml(message_json['object']['content'])
    if not emojiContent:
        if debug:
            print('DEBUG: unreaction has no content')
        return True
    undoReactionCollectionEntry(recentPostsCache, base_dir, postFilename,
                                postReactionId, reactionActor, domain,
                                debug, None, emojiContent)
    # regenerate the html
    reactionPostJson = load_json(postFilename, 0, 1)
    if reactionPostJson:
        if reactionPostJson.get('type'):
            if reactionPostJson['type'] == 'Announce' and \
               reactionPostJson.get('object'):
                if isinstance(reactionPostJson['object'], str):
                    announceReactionUrl = reactionPostJson['object']
                    announceReactionFilename = \
                        locatePost(base_dir, handleName,
                                   domain, announceReactionUrl)
                    if announceReactionFilename:
                        postReactionId = announceReactionUrl
                        postFilename = announceReactionFilename
                        undoReactionCollectionEntry(recentPostsCache, base_dir,
                                                    postFilename,
                                                    postReactionId,
                                                    reactionActor, domain,
                                                    debug, None,
                                                    emojiContent)
        if reactionPostJson:
            if debug:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, handleName, domain,
                                          reactionPostJson)
                print('Unreaction post json: ' + str(reactionPostJson))
                print('Unreaction post nickname: ' + handleName + ' ' + domain)
                print('Unreaction post cache: ' + str(cachedPostFilename))
            pageNumber = 1
            show_published_date_only = False
            showIndividualPostIcons = True
            manuallyApproveFollowers = \
                followerApprovalActive(base_dir, handleName, domain)
            notDM = not isDM(reactionPostJson)
            individualPostAsHtml(signing_priv_key_pem, False,
                                 recentPostsCache, max_recent_posts,
                                 translate, pageNumber, base_dir,
                                 session, cached_webfingers, person_cache,
                                 handleName, domain, port, reactionPostJson,
                                 None, True, allow_deletion,
                                 http_prefix, __version__,
                                 'inbox',
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 peertube_instances,
                                 allow_local_network_access,
                                 theme_name, system_language,
                                 max_like_count, notDM,
                                 showIndividualPostIcons,
                                 manuallyApproveFollowers,
                                 False, True, False, cw_lists,
                                 lists_enabled)
    return True


def _receiveBookmark(recentPostsCache: {},
                     session, handle: str, isGroup: bool, base_dir: str,
                     http_prefix: str, domain: str, port: int,
                     send_threads: [], postLog: [], cached_webfingers: {},
                     person_cache: {}, message_json: {}, federation_list: [],
                     debug: bool, signing_priv_key_pem: str,
                     max_recent_posts: int, translate: {},
                     allow_deletion: bool,
                     yt_replace_domain: str,
                     twitter_replacement_domain: str,
                     peertube_instances: [],
                     allow_local_network_access: bool,
                     theme_name: str, system_language: str,
                     max_like_count: int, cw_lists: {},
                     lists_enabled: {}) -> bool:
    """Receives a bookmark activity within the POST section of HTTPServer
    """
    if not message_json.get('type'):
        return False
    if message_json['type'] != 'Add':
        return False
    if not hasActor(message_json, debug):
        return False
    if not message_json.get('target'):
        if debug:
            print('DEBUG: no target in inbox bookmark Add')
        return False
    if not hasObjectStringType(message_json, debug):
        return False
    if not isinstance(message_json['target'], str):
        if debug:
            print('DEBUG: inbox bookmark Add target is not string')
        return False
    domain_full = get_full_domain(domain, port)
    nickname = handle.split('@')[0]
    if not message_json['actor'].endswith(domain_full + '/users/' + nickname):
        if debug:
            print('DEBUG: inbox bookmark Add unexpected actor')
        return False
    if not message_json['target'].endswith(message_json['actor'] +
                                           '/tlbookmarks'):
        if debug:
            print('DEBUG: inbox bookmark Add target invalid ' +
                  message_json['target'])
        return False
    if message_json['object']['type'] != 'Document':
        if debug:
            print('DEBUG: inbox bookmark Add type is not Document')
        return False
    if not message_json['object'].get('url'):
        if debug:
            print('DEBUG: inbox bookmark Add missing url')
        return False
    if '/statuses/' not in message_json['object']['url']:
        if debug:
            print('DEBUG: inbox bookmark Add missing statuses un url')
        return False
    if debug:
        print('DEBUG: c2s inbox bookmark Add request arrived in outbox')

    messageUrl = removeIdEnding(message_json['object']['url'])
    domain = removeDomainPort(domain)
    postFilename = locatePost(base_dir, nickname, domain, messageUrl)
    if not postFilename:
        if debug:
            print('DEBUG: c2s inbox like post not found in inbox or outbox')
            print(messageUrl)
        return True

    updateBookmarksCollection(recentPostsCache, base_dir, postFilename,
                              message_json['object']['url'],
                              message_json['actor'], domain, debug)
    # regenerate the html
    bookmarkedPostJson = load_json(postFilename, 0, 1)
    if bookmarkedPostJson:
        if debug:
            cachedPostFilename = \
                getCachedPostFilename(base_dir, nickname, domain,
                                      bookmarkedPostJson)
            print('Bookmarked post json: ' + str(bookmarkedPostJson))
            print('Bookmarked post nickname: ' + nickname + ' ' + domain)
            print('Bookmarked post cache: ' + str(cachedPostFilename))
        pageNumber = 1
        show_published_date_only = False
        showIndividualPostIcons = True
        manuallyApproveFollowers = \
            followerApprovalActive(base_dir, nickname, domain)
        notDM = not isDM(bookmarkedPostJson)
        individualPostAsHtml(signing_priv_key_pem, False,
                             recentPostsCache, max_recent_posts,
                             translate, pageNumber, base_dir,
                             session, cached_webfingers, person_cache,
                             nickname, domain, port, bookmarkedPostJson,
                             None, True, allow_deletion,
                             http_prefix, __version__,
                             'inbox',
                             yt_replace_domain,
                             twitter_replacement_domain,
                             show_published_date_only,
                             peertube_instances,
                             allow_local_network_access,
                             theme_name, system_language,
                             max_like_count, notDM,
                             showIndividualPostIcons,
                             manuallyApproveFollowers,
                             False, True, False, cw_lists,
                             lists_enabled)
    return True


def _receiveUndoBookmark(recentPostsCache: {},
                         session, handle: str, isGroup: bool, base_dir: str,
                         http_prefix: str, domain: str, port: int,
                         send_threads: [], postLog: [],
                         cached_webfingers: {},
                         person_cache: {}, message_json: {},
                         federation_list: [],
                         debug: bool, signing_priv_key_pem: str,
                         max_recent_posts: int, translate: {},
                         allow_deletion: bool,
                         yt_replace_domain: str,
                         twitter_replacement_domain: str,
                         peertube_instances: [],
                         allow_local_network_access: bool,
                         theme_name: str, system_language: str,
                         max_like_count: int, cw_lists: {},
                         lists_enabled: str) -> bool:
    """Receives an undo bookmark activity within the POST section of HTTPServer
    """
    if not message_json.get('type'):
        return False
    if message_json['type'] != 'Remove':
        return False
    if not hasActor(message_json, debug):
        return False
    if not message_json.get('target'):
        if debug:
            print('DEBUG: no target in inbox undo bookmark Remove')
        return False
    if not hasObjectStringType(message_json, debug):
        return False
    if not isinstance(message_json['target'], str):
        if debug:
            print('DEBUG: inbox Remove bookmark target is not string')
        return False
    domain_full = get_full_domain(domain, port)
    nickname = handle.split('@')[0]
    if not message_json['actor'].endswith(domain_full + '/users/' + nickname):
        if debug:
            print('DEBUG: inbox undo bookmark Remove unexpected actor')
        return False
    if not message_json['target'].endswith(message_json['actor'] +
                                           '/tlbookmarks'):
        if debug:
            print('DEBUG: inbox undo bookmark Remove target invalid ' +
                  message_json['target'])
        return False
    if message_json['object']['type'] != 'Document':
        if debug:
            print('DEBUG: inbox undo bookmark Remove type is not Document')
        return False
    if not message_json['object'].get('url'):
        if debug:
            print('DEBUG: inbox undo bookmark Remove missing url')
        return False
    if '/statuses/' not in message_json['object']['url']:
        if debug:
            print('DEBUG: inbox undo bookmark Remove missing statuses un url')
        return False
    if debug:
        print('DEBUG: c2s inbox Remove bookmark ' +
              'request arrived in outbox')

    messageUrl = removeIdEnding(message_json['object']['url'])
    domain = removeDomainPort(domain)
    postFilename = locatePost(base_dir, nickname, domain, messageUrl)
    if not postFilename:
        if debug:
            print('DEBUG: c2s inbox like post not found in inbox or outbox')
            print(messageUrl)
        return True

    undoBookmarksCollectionEntry(recentPostsCache, base_dir, postFilename,
                                 message_json['object']['url'],
                                 message_json['actor'], domain, debug)
    # regenerate the html
    bookmarkedPostJson = load_json(postFilename, 0, 1)
    if bookmarkedPostJson:
        if debug:
            cachedPostFilename = \
                getCachedPostFilename(base_dir, nickname, domain,
                                      bookmarkedPostJson)
            print('Unbookmarked post json: ' + str(bookmarkedPostJson))
            print('Unbookmarked post nickname: ' + nickname + ' ' + domain)
            print('Unbookmarked post cache: ' + str(cachedPostFilename))
        pageNumber = 1
        show_published_date_only = False
        showIndividualPostIcons = True
        manuallyApproveFollowers = \
            followerApprovalActive(base_dir, nickname, domain)
        notDM = not isDM(bookmarkedPostJson)
        individualPostAsHtml(signing_priv_key_pem, False,
                             recentPostsCache, max_recent_posts,
                             translate, pageNumber, base_dir,
                             session, cached_webfingers, person_cache,
                             nickname, domain, port, bookmarkedPostJson,
                             None, True, allow_deletion,
                             http_prefix, __version__,
                             'inbox',
                             yt_replace_domain,
                             twitter_replacement_domain,
                             show_published_date_only,
                             peertube_instances,
                             allow_local_network_access,
                             theme_name, system_language,
                             max_like_count, notDM,
                             showIndividualPostIcons,
                             manuallyApproveFollowers,
                             False, True, False, cw_lists, lists_enabled)
    return True


def _receiveDelete(session, handle: str, isGroup: bool, base_dir: str,
                   http_prefix: str, domain: str, port: int,
                   send_threads: [], postLog: [], cached_webfingers: {},
                   person_cache: {}, message_json: {}, federation_list: [],
                   debug: bool, allow_deletion: bool,
                   recentPostsCache: {}) -> bool:
    """Receives a Delete activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Delete':
        return False
    if not hasActor(message_json, debug):
        return False
    if debug:
        print('DEBUG: Delete activity arrived')
    if not hasObjectString(message_json, debug):
        return False
    domain_full = get_full_domain(domain, port)
    deletePrefix = http_prefix + '://' + domain_full + '/'
    if (not allow_deletion and
        (not message_json['object'].startswith(deletePrefix) or
         not message_json['actor'].startswith(deletePrefix))):
        if debug:
            print('DEBUG: delete not permitted from other instances')
        return False
    if not message_json.get('to'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "to" list')
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: ' +
                  '"users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False
    if '/statuses/' not in message_json['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  message_json['type'])
        return False
    if message_json['actor'] not in message_json['object']:
        if debug:
            print('DEBUG: actor is not the owner of the post to be deleted')
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of like - ' + handle)
    # if this post in the outbox of the person?
    messageId = removeIdEnding(message_json['object'])
    removeModerationPostFromIndex(base_dir, messageId, debug)
    handleNickname = handle.split('@')[0]
    handleDomain = handle.split('@')[1]
    postFilename = locatePost(base_dir, handleNickname,
                              handleDomain, messageId)
    if not postFilename:
        if debug:
            print('DEBUG: delete post not found in inbox or outbox')
            print(messageId)
        return True
    deletePost(base_dir, http_prefix, handleNickname,
               handleDomain, postFilename, debug,
               recentPostsCache)
    if debug:
        print('DEBUG: post deleted - ' + postFilename)

    # also delete any local blogs saved to the news actor
    if handleNickname != 'news' and handleDomain == domain_full:
        postFilename = locatePost(base_dir, 'news',
                                  handleDomain, messageId)
        if postFilename:
            deletePost(base_dir, http_prefix, 'news',
                       handleDomain, postFilename, debug,
                       recentPostsCache)
            if debug:
                print('DEBUG: blog post deleted - ' + postFilename)
    return True


def _receiveAnnounce(recentPostsCache: {},
                     session, handle: str, isGroup: bool, base_dir: str,
                     http_prefix: str,
                     domain: str, onion_domain: str, port: int,
                     send_threads: [], postLog: [], cached_webfingers: {},
                     person_cache: {}, message_json: {}, federation_list: [],
                     debug: bool, translate: {},
                     yt_replace_domain: str,
                     twitter_replacement_domain: str,
                     allow_local_network_access: bool,
                     theme_name: str, system_language: str,
                     signing_priv_key_pem: str,
                     max_recent_posts: int,
                     allow_deletion: bool,
                     peertube_instances: [],
                     max_like_count: int, cw_lists: {},
                     lists_enabled: str) -> bool:
    """Receives an announce activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Announce':
        return False
    if '@' not in handle:
        if debug:
            print('DEBUG: bad handle ' + handle)
        return False
    if not hasActor(message_json, debug):
        return False
    if debug:
        print('DEBUG: receiving announce on ' + handle)
    if not hasObjectString(message_json, debug):
        return False
    if not message_json.get('to'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "to" list')
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: ' +
                  '"users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False
    if isSelfAnnounce(message_json):
        if debug:
            print('DEBUG: self-boost rejected')
        return False
    if not has_users_path(message_json['object']):
        if debug:
            print('DEBUG: ' +
                  '"users", "channel" or "profile" missing in ' +
                  message_json['type'])
        return False

    blockedCache = {}
    prefixes = getProtocolPrefixes()
    # is the domain of the announce actor blocked?
    objectDomain = message_json['object']
    for prefix in prefixes:
        objectDomain = objectDomain.replace(prefix, '')
    if '/' in objectDomain:
        objectDomain = objectDomain.split('/')[0]
    if isBlockedDomain(base_dir, objectDomain):
        if debug:
            print('DEBUG: announced domain is blocked')
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of announce - ' + handle)

    # is the announce actor blocked?
    nickname = handle.split('@')[0]
    actorNickname = getNicknameFromActor(message_json['actor'])
    actorDomain, actorPort = getDomainFromActor(message_json['actor'])
    if isBlocked(base_dir, nickname, domain, actorNickname, actorDomain):
        print('Receive announce blocked for actor: ' +
              actorNickname + '@' + actorDomain)
        return False

    # also check the actor for the url being announced
    announcedActorNickname = getNicknameFromActor(message_json['object'])
    announcedActorDomain, announcedActorPort = \
        getDomainFromActor(message_json['object'])
    if isBlocked(base_dir, nickname, domain,
                 announcedActorNickname, announcedActorDomain):
        print('Receive announce object blocked for actor: ' +
              announcedActorNickname + '@' + announcedActorDomain)
        return False

    # is this post in the outbox of the person?
    postFilename = locatePost(base_dir, nickname, domain,
                              message_json['object'])
    if not postFilename:
        if debug:
            print('DEBUG: announce post not found in inbox or outbox')
            print(message_json['object'])
        return True
    updateAnnounceCollection(recentPostsCache, base_dir, postFilename,
                             message_json['actor'], nickname, domain, debug)
    if debug:
        print('DEBUG: Downloading announce post ' + message_json['actor'] +
              ' -> ' + message_json['object'])
    domain_full = get_full_domain(domain, port)

    # Generate html. This also downloads the announced post.
    pageNumber = 1
    show_published_date_only = False
    showIndividualPostIcons = True
    manuallyApproveFollowers = \
        followerApprovalActive(base_dir, nickname, domain)
    notDM = True
    if debug:
        print('Generating html for announce ' + message_json['id'])
    announceHtml = \
        individualPostAsHtml(signing_priv_key_pem, True,
                             recentPostsCache, max_recent_posts,
                             translate, pageNumber, base_dir,
                             session, cached_webfingers, person_cache,
                             nickname, domain, port, message_json,
                             None, True, allow_deletion,
                             http_prefix, __version__,
                             'inbox',
                             yt_replace_domain,
                             twitter_replacement_domain,
                             show_published_date_only,
                             peertube_instances,
                             allow_local_network_access,
                             theme_name, system_language,
                             max_like_count, notDM,
                             showIndividualPostIcons,
                             manuallyApproveFollowers,
                             False, True, False, cw_lists,
                             lists_enabled)
    if not announceHtml:
        print('WARN: Unable to generate html for announce ' +
              str(message_json))
    else:
        if debug:
            print('Generated announce html ' + announceHtml.replace('\n', ''))

    post_json_object = downloadAnnounce(session, base_dir,
                                        http_prefix,
                                        nickname, domain,
                                        message_json,
                                        __version__, translate,
                                        yt_replace_domain,
                                        twitter_replacement_domain,
                                        allow_local_network_access,
                                        recentPostsCache, debug,
                                        system_language,
                                        domain_full, person_cache,
                                        signing_priv_key_pem,
                                        blockedCache)
    if not post_json_object:
        print('WARN: unable to download announce: ' + str(message_json))
        notInOnion = True
        if onion_domain:
            if onion_domain in message_json['object']:
                notInOnion = False
        if domain not in message_json['object'] and notInOnion:
            if os.path.isfile(postFilename):
                # if the announce can't be downloaded then remove it
                try:
                    os.remove(postFilename)
                except OSError:
                    print('EX: _receiveAnnounce unable to delete ' +
                          str(postFilename))
    else:
        if debug:
            print('DEBUG: Announce post downloaded for ' +
                  message_json['actor'] + ' -> ' + message_json['object'])
        storeHashTags(base_dir, nickname, domain,
                      http_prefix, domain_full,
                      post_json_object, translate)
        # Try to obtain the actor for this person
        # so that their avatar can be shown
        lookupActor = None
        if post_json_object.get('attributedTo'):
            if isinstance(post_json_object['attributedTo'], str):
                lookupActor = post_json_object['attributedTo']
        else:
            if has_object_dict(post_json_object):
                if post_json_object['object'].get('attributedTo'):
                    attrib = post_json_object['object']['attributedTo']
                    if isinstance(attrib, str):
                        lookupActor = attrib
        if lookupActor:
            if has_users_path(lookupActor):
                if '/statuses/' in lookupActor:
                    lookupActor = lookupActor.split('/statuses/')[0]

                if isRecentPost(post_json_object, 3):
                    if not os.path.isfile(postFilename + '.tts'):
                        domain_full = get_full_domain(domain, port)
                        updateSpeaker(base_dir, http_prefix,
                                      nickname, domain, domain_full,
                                      post_json_object, person_cache,
                                      translate, lookupActor,
                                      theme_name)
                        try:
                            with open(postFilename + '.tts', 'w+') as ttsFile:
                                ttsFile.write('\n')
                        except OSError:
                            print('EX: unable to write recent post ' +
                                  postFilename)

                if debug:
                    print('DEBUG: Obtaining actor for announce post ' +
                          lookupActor)
                for tries in range(6):
                    pubKey = \
                        getPersonPubKey(base_dir, session, lookupActor,
                                        person_cache, debug,
                                        __version__, http_prefix,
                                        domain, onion_domain,
                                        signing_priv_key_pem)
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
                         session, handle: str, isGroup: bool, base_dir: str,
                         http_prefix: str, domain: str, port: int,
                         send_threads: [], postLog: [],
                         cached_webfingers: {},
                         person_cache: {}, message_json: {},
                         federation_list: [],
                         debug: bool) -> bool:
    """Receives an undo announce activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Undo':
        return False
    if not hasActor(message_json, debug):
        return False
    if not has_object_dict(message_json):
        return False
    if not has_object_string_object(message_json, debug):
        return False
    if message_json['object']['type'] != 'Announce':
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + ' announce')
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of undo announce - ' + handle)
    # if this post in the outbox of the person?
    handleName = handle.split('@')[0]
    handleDom = handle.split('@')[1]
    postFilename = locatePost(base_dir, handleName, handleDom,
                              message_json['object']['object'])
    if not postFilename:
        if debug:
            print('DEBUG: undo announce post not found in inbox or outbox')
            print(message_json['object']['object'])
        return True
    if debug:
        print('DEBUG: announced/repeated post to be undone found in inbox')

    post_json_object = load_json(postFilename)
    if post_json_object:
        if not post_json_object.get('type'):
            if post_json_object['type'] != 'Announce':
                if debug:
                    print("DEBUG: Attempt to undo something " +
                          "which isn't an announcement")
                return False
    undoAnnounceCollectionEntry(recentPostsCache, base_dir, postFilename,
                                message_json['actor'], domain, debug)
    if os.path.isfile(postFilename):
        try:
            os.remove(postFilename)
        except OSError:
            print('EX: _receiveUndoAnnounce unable to delete ' +
                  str(postFilename))
    return True


def jsonPostAllowsComments(post_json_object: {}) -> bool:
    """Returns true if the given post allows comments/replies
    """
    if 'commentsEnabled' in post_json_object:
        return post_json_object['commentsEnabled']
    if 'rejectReplies' in post_json_object:
        return not post_json_object['rejectReplies']
    if post_json_object.get('object'):
        if not has_object_dict(post_json_object):
            return False
        elif 'commentsEnabled' in post_json_object['object']:
            return post_json_object['object']['commentsEnabled']
        elif 'rejectReplies' in post_json_object['object']:
            return not post_json_object['object']['rejectReplies']
    return True


def _postAllowsComments(postFilename: str) -> bool:
    """Returns true if the given post allows comments/replies
    """
    post_json_object = load_json(postFilename)
    if not post_json_object:
        return False
    return jsonPostAllowsComments(post_json_object)


def populateReplies(base_dir: str, http_prefix: str, domain: str,
                    message_json: {}, max_replies: int, debug: bool) -> bool:
    """Updates the list of replies for a post on this domain if
    a reply to it arrives
    """
    if not message_json.get('id'):
        return False
    if not has_object_dict(message_json):
        return False
    if not message_json['object'].get('inReplyTo'):
        return False
    if not message_json['object'].get('to'):
        return False
    replyTo = message_json['object']['inReplyTo']
    if not isinstance(replyTo, str):
        return False
    if debug:
        print('DEBUG: post contains a reply')
    # is this a reply to a post on this domain?
    if not replyTo.startswith(http_prefix + '://' + domain + '/'):
        if debug:
            print('DEBUG: post is a reply to another not on this domain')
            print(replyTo)
            print('Expected: ' + http_prefix + '://' + domain + '/')
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

    postFilename = locatePost(base_dir, replyToNickname,
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
    messageId = removeIdEnding(message_json['id'])
    if os.path.isfile(postRepliesFilename):
        numLines = sum(1 for line in open(postRepliesFilename))
        if numLines > max_replies:
            return False
        if messageId not in open(postRepliesFilename).read():
            try:
                with open(postRepliesFilename, 'a+') as repliesFile:
                    repliesFile.write(messageId + '\n')
            except OSError:
                print('EX: unable to append ' + postRepliesFilename)
    else:
        try:
            with open(postRepliesFilename, 'w+') as repliesFile:
                repliesFile.write(messageId + '\n')
        except OSError:
            print('EX: unable to write ' + postRepliesFilename)
    return True


def _estimateNumberOfMentions(content: str) -> int:
    """Returns a rough estimate of the number of mentions
    """
    return int(content.count('@') / 2)


def _estimateNumberOfEmoji(content: str) -> int:
    """Returns a rough estimate of the number of emoji
    """
    return int(content.count(':') / 2)


def _validPostContent(base_dir: str, nickname: str, domain: str,
                      message_json: {}, max_mentions: int, max_emoji: int,
                      allow_local_network_access: bool, debug: bool,
                      system_language: str,
                      http_prefix: str, domain_full: str,
                      person_cache: {}) -> bool:
    """Is the content of a received post valid?
    Check for bad html
    Check for hellthreads
    Check that the language is understood
    Check if it's a git patch
    Check number of tags and mentions is reasonable
    """
    if not has_object_dict(message_json):
        return True
    if not message_json['object'].get('content'):
        return True

    if not message_json['object'].get('published'):
        return False
    if 'T' not in message_json['object']['published']:
        return False
    if 'Z' not in message_json['object']['published']:
        return False
    if not valid_post_date(message_json['object']['published'], 90, debug):
        return False

    summary = None
    if message_json['object'].get('summary'):
        summary = message_json['object']['summary']
        if not isinstance(summary, str):
            print('WARN: content warning is not a string')
            return False
        if summary != validContentWarning(summary):
            print('WARN: invalid content warning ' + summary)
            return False

    # check for patches before dangeousMarkup, which excludes code
    if isGitPatch(base_dir, nickname, domain,
                  message_json['object']['type'],
                  summary,
                  message_json['object']['content']):
        return True

    contentStr = get_base_content_from_post(message_json, system_language)
    if dangerousMarkup(contentStr, allow_local_network_access):
        if message_json['object'].get('id'):
            print('REJECT ARBITRARY HTML: ' + message_json['object']['id'])
        print('REJECT ARBITRARY HTML: bad string in post - ' +
              contentStr)
        return False

    # check (rough) number of mentions
    mentionsEst = _estimateNumberOfMentions(contentStr)
    if mentionsEst > max_mentions:
        if message_json['object'].get('id'):
            print('REJECT HELLTHREAD: ' + message_json['object']['id'])
        print('REJECT HELLTHREAD: Too many mentions in post - ' +
              contentStr)
        return False
    if _estimateNumberOfEmoji(contentStr) > max_emoji:
        if message_json['object'].get('id'):
            print('REJECT EMOJI OVERLOAD: ' + message_json['object']['id'])
        print('REJECT EMOJI OVERLOAD: Too many emoji in post - ' +
              contentStr)
        return False
    # check number of tags
    if message_json['object'].get('tag'):
        if not isinstance(message_json['object']['tag'], list):
            message_json['object']['tag'] = []
        else:
            if len(message_json['object']['tag']) > int(max_mentions * 2):
                if message_json['object'].get('id'):
                    print('REJECT: ' + message_json['object']['id'])
                print('REJECT: Too many tags in post - ' +
                      message_json['object']['tag'])
                return False
    # check that the post is in a language suitable for this account
    if not understoodPostLanguage(base_dir, nickname, domain,
                                  message_json, system_language,
                                  http_prefix, domain_full,
                                  person_cache):
        return False
    # check for filtered content
    if isFiltered(base_dir, nickname, domain, contentStr):
        print('REJECT: content filtered')
        return False
    if message_json['object'].get('inReplyTo'):
        if isinstance(message_json['object']['inReplyTo'], str):
            originalPostId = message_json['object']['inReplyTo']
            postPostFilename = locatePost(base_dir, nickname, domain,
                                          originalPostId)
            if postPostFilename:
                if not _postAllowsComments(postPostFilename):
                    print('REJECT: reply to post which does not ' +
                          'allow comments: ' + originalPostId)
                    return False
    if invalidCiphertext(message_json['object']['content']):
        print('REJECT: malformed ciphertext in content')
        return False
    if debug:
        print('ACCEPT: post content is valid')
    return True


def _obtainAvatarForReplyPost(session, base_dir: str, http_prefix: str,
                              domain: str, onion_domain: str, person_cache: {},
                              post_json_object: {}, debug: bool,
                              signing_priv_key_pem: str) -> None:
    """Tries to obtain the actor for the person being replied to
    so that their avatar can later be shown
    """
    if not has_object_dict(post_json_object):
        return

    if not post_json_object['object'].get('inReplyTo'):
        return

    lookupActor = post_json_object['object']['inReplyTo']
    if not lookupActor:
        return

    if not isinstance(lookupActor, str):
        return

    if not has_users_path(lookupActor):
        return

    if '/statuses/' in lookupActor:
        lookupActor = lookupActor.split('/statuses/')[0]

    if debug:
        print('DEBUG: Obtaining actor for reply post ' + lookupActor)

    for tries in range(6):
        pubKey = \
            getPersonPubKey(base_dir, session, lookupActor,
                            person_cache, debug,
                            __version__, http_prefix,
                            domain, onion_domain, signing_priv_key_pem)
        if pubKey:
            if debug:
                print('DEBUG: public key obtained for reply: ' + lookupActor)
            break

        if debug:
            print('DEBUG: Retry ' + str(tries + 1) +
                  ' obtaining actor for ' + lookupActor)
        time.sleep(5)


def _dmNotify(base_dir: str, handle: str, url: str) -> None:
    """Creates a notification that a new DM has arrived
    """
    accountDir = base_dir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return
    dmFile = accountDir + '/.newDM'
    if not os.path.isfile(dmFile):
        try:
            with open(dmFile, 'w+') as fp:
                fp.write(url)
        except OSError:
            print('EX: unable to write ' + dmFile)


def _alreadyLiked(base_dir: str, nickname: str, domain: str,
                  postUrl: str, likerActor: str) -> bool:
    """Is the given post already liked by the given handle?
    """
    postFilename = \
        locatePost(base_dir, nickname, domain, postUrl)
    if not postFilename:
        return False
    post_json_object = load_json(postFilename, 1)
    if not post_json_object:
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('likes'):
        return False
    if not post_json_object['object']['likes'].get('items'):
        return False
    for like in post_json_object['object']['likes']['items']:
        if not like.get('type'):
            continue
        if not like.get('actor'):
            continue
        if like['type'] != 'Like':
            continue
        if like['actor'] == likerActor:
            return True
    return False


def _alreadyReacted(base_dir: str, nickname: str, domain: str,
                    postUrl: str, reactionActor: str,
                    emojiContent: str) -> bool:
    """Is the given post already emoji reacted by the given handle?
    """
    postFilename = \
        locatePost(base_dir, nickname, domain, postUrl)
    if not postFilename:
        return False
    post_json_object = load_json(postFilename, 1)
    if not post_json_object:
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('reactions'):
        return False
    if not post_json_object['object']['reactions'].get('items'):
        return False
    for react in post_json_object['object']['reactions']['items']:
        if not react.get('type'):
            continue
        if not react.get('content'):
            continue
        if not react.get('actor'):
            continue
        if react['type'] != 'EmojiReact':
            continue
        if react['content'] != emojiContent:
            continue
        if react['actor'] == reactionActor:
            return True
    return False


def _likeNotify(base_dir: str, domain: str, onion_domain: str,
                handle: str, actor: str, url: str) -> None:
    """Creates a notification that a like has arrived
    """
    # This is not you liking your own post
    if actor in url:
        return

    # check that the liked post was by this handle
    nickname = handle.split('@')[0]
    if '/' + domain + '/users/' + nickname not in url:
        if not onion_domain:
            return
        if '/' + onion_domain + '/users/' + nickname not in url:
            return

    accountDir = base_dir + '/accounts/' + handle

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
        except OSError:
            print('EX: ERROR: unable to save previous like notification ' +
                  prevLikeFile)

        try:
            with open(likeFile, 'w+') as fp:
                fp.write(likeStr)
        except OSError:
            print('EX: ERROR: unable to write like notification file ' +
                  likeFile)


def _reactionNotify(base_dir: str, domain: str, onion_domain: str,
                    handle: str, actor: str,
                    url: str, emojiContent: str) -> None:
    """Creates a notification that an emoji reaction has arrived
    """
    # This is not you reacting to your own post
    if actor in url:
        return

    # check that the reaction post was by this handle
    nickname = handle.split('@')[0]
    if '/' + domain + '/users/' + nickname not in url:
        if not onion_domain:
            return
        if '/' + onion_domain + '/users/' + nickname not in url:
            return

    accountDir = base_dir + '/accounts/' + handle

    # are reaction notifications enabled?
    notifyReactionEnabledFilename = accountDir + '/.notifyReactions'
    if not os.path.isfile(notifyReactionEnabledFilename):
        return

    reactionFile = accountDir + '/.newReaction'
    if os.path.isfile(reactionFile):
        if '##sent##' not in open(reactionFile).read():
            return

    reactionNickname = getNicknameFromActor(actor)
    reactionDomain, reactionPort = getDomainFromActor(actor)
    if reactionNickname and reactionDomain:
        reactionHandle = reactionNickname + '@' + reactionDomain
    else:
        print('_reactionNotify reactionHandle: ' +
              str(reactionNickname) + '@' + str(reactionDomain))
        reactionHandle = actor
    if reactionHandle != handle:
        reactionStr = \
            reactionHandle + ' ' + url + '?reactBy=' + actor + \
            ';emoj=' + emojiContent
        prevReactionFile = accountDir + '/.prevReaction'
        # was there a previous reaction notification?
        if os.path.isfile(prevReactionFile):
            # is it the same as the current notification ?
            with open(prevReactionFile, 'r') as fp:
                prevReactionStr = fp.read()
                if prevReactionStr == reactionStr:
                    return
        try:
            with open(prevReactionFile, 'w+') as fp:
                fp.write(reactionStr)
        except OSError:
            print('EX: ERROR: unable to save previous reaction notification ' +
                  prevReactionFile)

        try:
            with open(reactionFile, 'w+') as fp:
                fp.write(reactionStr)
        except OSError:
            print('EX: ERROR: unable to write reaction notification file ' +
                  reactionFile)


def _notifyPostArrival(base_dir: str, handle: str, url: str) -> None:
    """Creates a notification that a new post has arrived.
    This is for followed accounts with the notify checkbox enabled
    on the person options screen
    """
    accountDir = base_dir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return
    notifyFile = accountDir + '/.newNotifiedPost'
    if os.path.isfile(notifyFile):
        # check that the same notification is not repeatedly sent
        with open(notifyFile, 'r') as fp:
            existingNotificationMessage = fp.read()
            if url in existingNotificationMessage:
                return
    try:
        with open(notifyFile, 'w+') as fp:
            fp.write(url)
    except OSError:
        print('EX: unable to write ' + notifyFile)


def _replyNotify(base_dir: str, handle: str, url: str) -> None:
    """Creates a notification that a new reply has arrived
    """
    accountDir = base_dir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return
    replyFile = accountDir + '/.newReply'
    if not os.path.isfile(replyFile):
        try:
            with open(replyFile, 'w+') as fp:
                fp.write(url)
        except OSError:
            print('EX: unable to write ' + replyFile)


def _gitPatchNotify(base_dir: str, handle: str,
                    subject: str, content: str,
                    fromNickname: str, fromDomain: str) -> None:
    """Creates a notification that a new git patch has arrived
    """
    accountDir = base_dir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return
    patchFile = accountDir + '/.newPatch'
    subject = subject.replace('[PATCH]', '').strip()
    handle = '@' + fromNickname + '@' + fromDomain
    try:
        with open(patchFile, 'w+') as fp:
            fp.write('git ' + handle + ' ' + subject)
    except OSError:
        print('EX: unable to write ' + patchFile)


def _groupHandle(base_dir: str, handle: str) -> bool:
    """Is the given account handle a group?
    """
    actorFile = base_dir + '/accounts/' + handle + '.json'
    if not os.path.isfile(actorFile):
        return False
    actor_json = load_json(actorFile)
    if not actor_json:
        return False
    return actor_json['type'] == 'Group'


def _sendToGroupMembers(session, base_dir: str, handle: str, port: int,
                        post_json_object: {},
                        http_prefix: str, federation_list: [],
                        send_threads: [], postLog: [], cached_webfingers: {},
                        person_cache: {}, debug: bool,
                        system_language: str,
                        onion_domain: str, i2p_domain: str,
                        signing_priv_key_pem: str) -> None:
    """When a post arrives for a group send it out to the group members
    """
    if debug:
        print('\n\n=========================================================')
        print(handle + ' sending to group members')

    sharedItemFederationTokens = {}
    shared_items_federated_domains = []
    shared_items_federated_domainsStr = \
        get_config_param(base_dir, 'shared_items_federated_domains')
    if shared_items_federated_domainsStr:
        siFederatedDomainsList = \
            shared_items_federated_domainsStr.split(',')
        for sharedFederatedDomain in siFederatedDomainsList:
            domainStr = sharedFederatedDomain.strip()
            shared_items_federated_domains.append(domainStr)

    followersFile = base_dir + '/accounts/' + handle + '/followers.txt'
    if not os.path.isfile(followersFile):
        return
    if not post_json_object.get('to'):
        return
    if not post_json_object.get('object'):
        return
    if not has_object_dict(post_json_object):
        return
    nickname = handle.split('@')[0].replace('!', '')
    domain = handle.split('@')[1]
    domain_full = get_full_domain(domain, port)
    groupActor = local_actor_url(http_prefix, nickname, domain_full)
    if groupActor not in post_json_object['to']:
        return
    cc = ''
    nickname = handle.split('@')[0].replace('!', '')

    # save to the group outbox so that replies will be to the group
    # rather than the original sender
    savePostToBox(base_dir, http_prefix, None,
                  nickname, domain, post_json_object, 'outbox')

    postId = removeIdEnding(post_json_object['object']['id'])
    if debug:
        print('Group announce: ' + postId)
    announceJson = \
        createAnnounce(session, base_dir, federation_list,
                       nickname, domain, port,
                       groupActor + '/followers', cc,
                       http_prefix, postId, False, False,
                       send_threads, postLog,
                       person_cache, cached_webfingers,
                       debug, __version__, signing_priv_key_pem)

    sendToFollowersThread(session, base_dir, nickname, domain,
                          onion_domain, i2p_domain, port,
                          http_prefix, federation_list,
                          send_threads, postLog,
                          cached_webfingers, person_cache,
                          announceJson, debug, __version__,
                          shared_items_federated_domains,
                          sharedItemFederationTokens,
                          signing_priv_key_pem)


def _inboxUpdateCalendar(base_dir: str, handle: str,
                         post_json_object: {}) -> None:
    """Detects whether the tag list on a post contains calendar events
    and if so saves the post id to a file in the calendar directory
    for the account
    """
    if not post_json_object.get('actor'):
        return
    if not has_object_dict(post_json_object):
        return
    if not post_json_object['object'].get('tag'):
        return
    if not isinstance(post_json_object['object']['tag'], list):
        return

    actor = post_json_object['actor']
    actorNickname = getNicknameFromActor(actor)
    actorDomain, actorPort = getDomainFromActor(actor)
    handleNickname = handle.split('@')[0]
    handleDomain = handle.split('@')[1]
    if not receivingCalendarEvents(base_dir,
                                   handleNickname, handleDomain,
                                   actorNickname, actorDomain):
        return

    postId = removeIdEnding(post_json_object['id']).replace('/', '#')

    # look for events within the tags list
    for tagDict in post_json_object['object']['tag']:
        if not tagDict.get('type'):
            continue
        if tagDict['type'] != 'Event':
            continue
        if not tagDict.get('startTime'):
            continue
        saveEventPost(base_dir, handle, postId, tagDict)


def inboxUpdateIndex(boxname: str, base_dir: str, handle: str,
                     destinationFilename: str, debug: bool) -> bool:
    """Updates the index of received posts
    The new entry is added to the top of the file
    """
    indexFilename = base_dir + '/accounts/' + handle + '/' + boxname + '.index'
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
        except OSError as ex:
            print('EX: Failed to write entry to index ' + str(ex))
    else:
        try:
            with open(indexFilename, 'w+') as indexFile:
                indexFile.write(destinationFilename + '\n')
                written = True
        except OSError as ex:
            print('EX: Failed to write initial entry to index ' + str(ex))

    return written


def _updateLastSeen(base_dir: str, handle: str, actor: str) -> None:
    """Updates the time when the given handle last saw the given actor
    This can later be used to indicate if accounts are dormant/abandoned/moved
    """
    if '@' not in handle:
        return
    nickname = handle.split('@')[0]
    domain = handle.split('@')[1]
    domain = removeDomainPort(domain)
    accountPath = acct_dir(base_dir, nickname, domain)
    if not os.path.isdir(accountPath):
        return
    if not isFollowingActor(base_dir, nickname, domain, actor):
        return
    lastSeenPath = accountPath + '/lastseen'
    if not os.path.isdir(lastSeenPath):
        os.mkdir(lastSeenPath)
    lastSeenFilename = lastSeenPath + '/' + actor.replace('/', '#') + '.txt'
    curr_time = datetime.datetime.utcnow()
    daysSinceEpoch = (curr_time - datetime.datetime(1970, 1, 1)).days
    # has the value changed?
    if os.path.isfile(lastSeenFilename):
        with open(lastSeenFilename, 'r') as lastSeenFile:
            daysSinceEpochFile = lastSeenFile.read()
            if int(daysSinceEpochFile) == daysSinceEpoch:
                # value hasn't changed, so we can save writing anything to file
                return
    try:
        with open(lastSeenFilename, 'w+') as lastSeenFile:
            lastSeenFile.write(str(daysSinceEpoch))
    except OSError:
        print('EX: unable to write ' + lastSeenFilename)


def _bounceDM(senderPostId: str, session, http_prefix: str,
              base_dir: str, nickname: str, domain: str, port: int,
              sendingHandle: str, federation_list: [],
              send_threads: [], postLog: [],
              cached_webfingers: {}, person_cache: {},
              translate: {}, debug: bool,
              lastBounceMessage: [], system_language: str,
              signing_priv_key_pem: str,
              content_license_url: str) -> bool:
    """Sends a bounce message back to the sending handle
    if a DM has been rejected
    """
    print(nickname + '@' + domain +
          ' cannot receive DM from ' + sendingHandle +
          ' because they do not follow them')

    # Don't send out bounce messages too frequently.
    # Otherwise an adversary could try to DoS your instance
    # by continuously sending DMs to you
    curr_time = int(time.time())
    if curr_time - lastBounceMessage[0] < 60:
        return False

    # record the last time that a bounce was generated
    lastBounceMessage[0] = curr_time

    senderNickname = sendingHandle.split('@')[0]
    group_account = False
    if sendingHandle.startswith('!'):
        sendingHandle = sendingHandle[1:]
        group_account = True
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
    client_to_server = False
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
    low_bandwidth = False
    post_json_object = \
        createDirectMessagePost(base_dir, nickname, domain, port,
                                http_prefix, content, followersOnly,
                                saveToFile, client_to_server,
                                commentsEnabled,
                                attachImageFilename, mediaType,
                                imageDescription, city,
                                inReplyTo, inReplyToAtomUri,
                                subject, debug, schedulePost,
                                eventDate, eventTime, location,
                                system_language, conversationId, low_bandwidth,
                                content_license_url)
    if not post_json_object:
        print('WARN: unable to create bounce message to ' + sendingHandle)
        return False
    # bounce DM goes back to the sender
    print('Sending bounce DM to ' + sendingHandle)
    sendSignedJson(post_json_object, session, base_dir,
                   nickname, domain, port,
                   senderNickname, senderDomain, senderPort, cc,
                   http_prefix, False, False, federation_list,
                   send_threads, postLog, cached_webfingers,
                   person_cache, debug, __version__, None, group_account,
                   signing_priv_key_pem, 7238634)
    return True


def _isValidDM(base_dir: str, nickname: str, domain: str, port: int,
               post_json_object: {}, updateIndexList: [],
               session, http_prefix: str,
               federation_list: [],
               send_threads: [], postLog: [],
               cached_webfingers: {},
               person_cache: {},
               translate: {}, debug: bool,
               lastBounceMessage: [],
               handle: str, system_language: str,
               signing_priv_key_pem: str,
               content_license_url: str) -> bool:
    """Is the given message a valid DM?
    """
    if nickname == 'inbox':
        # going to the shared inbox
        return True

    # check for the flag file which indicates to
    # only receive DMs from people you are following
    followDMsFilename = acct_dir(base_dir, nickname, domain) + '/.followDMs'
    if not os.path.isfile(followDMsFilename):
        # dm index will be updated
        updateIndexList.append('dm')
        actUrl = local_actor_url(http_prefix, nickname, domain)
        _dmNotify(base_dir, handle, actUrl + '/dm')
        return True

    # get the file containing following handles
    followingFilename = acct_dir(base_dir, nickname, domain) + '/following.txt'
    # who is sending a DM?
    if not post_json_object.get('actor'):
        return False
    sendingActor = post_json_object['actor']
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
        if not isFollowingActor(base_dir, nickname, domain, sendH):
            # DMs may always be allowed from some domains
            if not dmAllowedFromDomain(base_dir,
                                       nickname, domain,
                                       sendingActorDomain):
                # send back a bounce DM
                if post_json_object.get('id') and \
                   post_json_object.get('object'):
                    # don't send bounces back to
                    # replies to bounce messages
                    obj = post_json_object['object']
                    if isinstance(obj, dict):
                        if not obj.get('inReplyTo'):
                            bouncedId = removeIdEnding(post_json_object['id'])
                            _bounceDM(bouncedId,
                                      session, http_prefix,
                                      base_dir,
                                      nickname, domain,
                                      port, sendH,
                                      federation_list,
                                      send_threads, postLog,
                                      cached_webfingers,
                                      person_cache,
                                      translate, debug,
                                      lastBounceMessage,
                                      system_language,
                                      signing_priv_key_pem,
                                      content_license_url)
                return False

    # dm index will be updated
    updateIndexList.append('dm')
    actUrl = local_actor_url(http_prefix, nickname, domain)
    _dmNotify(base_dir, handle, actUrl + '/dm')
    return True


def _receiveQuestionVote(base_dir: str, nickname: str, domain: str,
                         http_prefix: str, handle: str, debug: bool,
                         post_json_object: {}, recentPostsCache: {},
                         session, onion_domain: str,
                         i2p_domain: str, port: int,
                         federation_list: [], send_threads: [], postLog: [],
                         cached_webfingers: {}, person_cache: {},
                         signing_priv_key_pem: str,
                         max_recent_posts: int, translate: {},
                         allow_deletion: bool,
                         yt_replace_domain: str,
                         twitter_replacement_domain: str,
                         peertube_instances: [],
                         allow_local_network_access: bool,
                         theme_name: str, system_language: str,
                         max_like_count: int,
                         cw_lists: {}, lists_enabled: bool) -> None:
    """Updates the votes on a Question/poll
    """
    # if this is a reply to a question then update the votes
    questionJson, questionPostFilename = \
        questionUpdateVotes(base_dir, nickname, domain, post_json_object)
    if not questionJson:
        return
    if not questionPostFilename:
        return

    removePostFromCache(questionJson, recentPostsCache)
    # ensure that the cached post is removed if it exists, so
    # that it then will be recreated
    cachedPostFilename = \
        getCachedPostFilename(base_dir, nickname, domain, questionJson)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                print('EX: replytoQuestion unable to delete ' +
                      cachedPostFilename)

    pageNumber = 1
    show_published_date_only = False
    showIndividualPostIcons = True
    manuallyApproveFollowers = \
        followerApprovalActive(base_dir, nickname, domain)
    notDM = not isDM(questionJson)
    individualPostAsHtml(signing_priv_key_pem, False,
                         recentPostsCache, max_recent_posts,
                         translate, pageNumber, base_dir,
                         session, cached_webfingers, person_cache,
                         nickname, domain, port, questionJson,
                         None, True, allow_deletion,
                         http_prefix, __version__,
                         'inbox',
                         yt_replace_domain,
                         twitter_replacement_domain,
                         show_published_date_only,
                         peertube_instances,
                         allow_local_network_access,
                         theme_name, system_language,
                         max_like_count, notDM,
                         showIndividualPostIcons,
                         manuallyApproveFollowers,
                         False, True, False, cw_lists,
                         lists_enabled)

    # add id to inbox index
    inboxUpdateIndex('inbox', base_dir, handle,
                     questionPostFilename, debug)

    # Is this a question created by this instance?
    idPrefix = http_prefix + '://' + domain
    if not questionJson['object']['id'].startswith(idPrefix):
        return
    # if the votes on a question have changed then
    # send out an update
    questionJson['type'] = 'Update'
    shared_items_federated_domains = []
    sharedItemFederationTokens = {}
    sendToFollowersThread(session, base_dir, nickname, domain,
                          onion_domain, i2p_domain, port,
                          http_prefix, federation_list,
                          send_threads, postLog,
                          cached_webfingers, person_cache,
                          post_json_object, debug, __version__,
                          shared_items_federated_domains,
                          sharedItemFederationTokens,
                          signing_priv_key_pem)


def _createReplyNotificationFile(base_dir: str, nickname: str, domain: str,
                                 handle: str, debug: bool, postIsDM: bool,
                                 post_json_object: {}, actor: str,
                                 updateIndexList: [], http_prefix: str,
                                 default_reply_interval_hrs: int) -> bool:
    """Generates a file indicating that a new reply has arrived
    The file can then be used by other systems to create a notification
    xmpp, matrix, email, etc
    """
    isReplyToMutedPost = False
    if postIsDM:
        return isReplyToMutedPost
    if not isReply(post_json_object, actor):
        return isReplyToMutedPost
    if nickname == 'inbox':
        return isReplyToMutedPost
    # replies index will be updated
    updateIndexList.append('tlreplies')

    conversationId = None
    if post_json_object['object'].get('conversation'):
        conversationId = post_json_object['object']['conversation']

    if not post_json_object['object'].get('inReplyTo'):
        return isReplyToMutedPost
    inReplyTo = post_json_object['object']['inReplyTo']
    if not inReplyTo:
        return isReplyToMutedPost
    if not isinstance(inReplyTo, str):
        return isReplyToMutedPost
    if not isMuted(base_dir, nickname, domain, inReplyTo, conversationId):
        # check if the reply is within the allowed time period
        # after publication
        replyIntervalHours = \
            getReplyIntervalHours(base_dir, nickname, domain,
                                  default_reply_interval_hrs)
        if canReplyTo(base_dir, nickname, domain, inReplyTo,
                      replyIntervalHours):
            actUrl = local_actor_url(http_prefix, nickname, domain)
            _replyNotify(base_dir, handle, actUrl + '/tlreplies')
        else:
            if debug:
                print('Reply to ' + inReplyTo + ' is outside of the ' +
                      'permitted interval of ' + str(replyIntervalHours) +
                      ' hours')
            return False
    else:
        isReplyToMutedPost = True
    return isReplyToMutedPost


def _lowFrequencyPostNotification(base_dir: str, http_prefix: str,
                                  nickname: str, domain: str,
                                  port: int, handle: str,
                                  postIsDM: bool, jsonObj: {}) -> None:
    """Should we notify that a post from this person has arrived?
    This is for cases where the notify checkbox is enabled on the
    person options screen
    """
    if postIsDM:
        return
    if not jsonObj:
        return
    if not jsonObj.get('attributedTo'):
        return
    if not jsonObj.get('id'):
        return
    attributedTo = jsonObj['attributedTo']
    if not isinstance(attributedTo, str):
        return
    fromNickname = getNicknameFromActor(attributedTo)
    fromDomain, fromPort = getDomainFromActor(attributedTo)
    fromDomainFull = get_full_domain(fromDomain, fromPort)
    if notifyWhenPersonPosts(base_dir, nickname, domain,
                             fromNickname, fromDomainFull):
        postId = removeIdEnding(jsonObj['id'])
        domFull = get_full_domain(domain, port)
        postLink = \
            local_actor_url(http_prefix, nickname, domFull) + \
            '?notifypost=' + postId.replace('/', '-')
        _notifyPostArrival(base_dir, handle, postLink)


def _checkForGitPatches(base_dir: str, nickname: str, domain: str,
                        handle: str, jsonObj: {}) -> int:
    """check for incoming git patches
    """
    if not jsonObj:
        return 0
    if not jsonObj.get('content'):
        return 0
    if not jsonObj.get('summary'):
        return 0
    if not jsonObj.get('attributedTo'):
        return 0
    attributedTo = jsonObj['attributedTo']
    if not isinstance(attributedTo, str):
        return 0
    fromNickname = getNicknameFromActor(attributedTo)
    fromDomain, fromPort = getDomainFromActor(attributedTo)
    fromDomainFull = get_full_domain(fromDomain, fromPort)
    if receiveGitPatch(base_dir, nickname, domain,
                       jsonObj['type'], jsonObj['summary'],
                       jsonObj['content'],
                       fromNickname, fromDomainFull):
        _gitPatchNotify(base_dir, handle,
                        jsonObj['summary'], jsonObj['content'],
                        fromNickname, fromDomainFull)
        return 1
    elif '[PATCH]' in jsonObj['content']:
        print('WARN: git patch not accepted - ' + jsonObj['summary'])
        return 2
    return 0


def _inboxAfterInitial(recentPostsCache: {}, max_recent_posts: int,
                       session, keyId: str, handle: str, message_json: {},
                       base_dir: str, http_prefix: str, send_threads: [],
                       postLog: [], cached_webfingers: {}, person_cache: {},
                       queue: [], domain: str,
                       onion_domain: str, i2p_domain: str,
                       port: int, proxy_type: str,
                       federation_list: [], debug: bool,
                       queueFilename: str, destinationFilename: str,
                       max_replies: int, allow_deletion: bool,
                       max_mentions: int, max_emoji: int, translate: {},
                       unit_test: bool,
                       yt_replace_domain: str,
                       twitter_replacement_domain: str,
                       show_published_date_only: bool,
                       allow_local_network_access: bool,
                       peertube_instances: [],
                       lastBounceMessage: [],
                       theme_name: str, system_language: str,
                       max_like_count: int,
                       signing_priv_key_pem: str,
                       default_reply_interval_hrs: int,
                       cw_lists: {}, lists_enabled: str,
                       content_license_url: str) -> bool:
    """ Anything which needs to be done after initial checks have passed
    """
    actor = keyId
    if '#' in actor:
        actor = keyId.split('#')[0]

    _updateLastSeen(base_dir, handle, actor)

    postIsDM = False
    isGroup = _groupHandle(base_dir, handle)

    if _receiveLike(recentPostsCache,
                    session, handle, isGroup,
                    base_dir, http_prefix,
                    domain, port,
                    onion_domain,
                    send_threads, postLog,
                    cached_webfingers,
                    person_cache,
                    message_json,
                    federation_list,
                    debug, signing_priv_key_pem,
                    max_recent_posts, translate,
                    allow_deletion,
                    yt_replace_domain,
                    twitter_replacement_domain,
                    peertube_instances,
                    allow_local_network_access,
                    theme_name, system_language,
                    max_like_count, cw_lists, lists_enabled):
        if debug:
            print('DEBUG: Like accepted from ' + actor)
        return False

    if _receiveUndoLike(recentPostsCache,
                        session, handle, isGroup,
                        base_dir, http_prefix,
                        domain, port,
                        send_threads, postLog,
                        cached_webfingers,
                        person_cache,
                        message_json,
                        federation_list,
                        debug, signing_priv_key_pem,
                        max_recent_posts, translate,
                        allow_deletion,
                        yt_replace_domain,
                        twitter_replacement_domain,
                        peertube_instances,
                        allow_local_network_access,
                        theme_name, system_language,
                        max_like_count, cw_lists, lists_enabled):
        if debug:
            print('DEBUG: Undo like accepted from ' + actor)
        return False

    if _receiveReaction(recentPostsCache,
                        session, handle, isGroup,
                        base_dir, http_prefix,
                        domain, port,
                        onion_domain,
                        send_threads, postLog,
                        cached_webfingers,
                        person_cache,
                        message_json,
                        federation_list,
                        debug, signing_priv_key_pem,
                        max_recent_posts, translate,
                        allow_deletion,
                        yt_replace_domain,
                        twitter_replacement_domain,
                        peertube_instances,
                        allow_local_network_access,
                        theme_name, system_language,
                        max_like_count, cw_lists, lists_enabled):
        if debug:
            print('DEBUG: Reaction accepted from ' + actor)
        return False

    if _receiveUndoReaction(recentPostsCache,
                            session, handle, isGroup,
                            base_dir, http_prefix,
                            domain, port,
                            send_threads, postLog,
                            cached_webfingers,
                            person_cache,
                            message_json,
                            federation_list,
                            debug, signing_priv_key_pem,
                            max_recent_posts, translate,
                            allow_deletion,
                            yt_replace_domain,
                            twitter_replacement_domain,
                            peertube_instances,
                            allow_local_network_access,
                            theme_name, system_language,
                            max_like_count, cw_lists, lists_enabled):
        if debug:
            print('DEBUG: Undo reaction accepted from ' + actor)
        return False

    if _receiveBookmark(recentPostsCache,
                        session, handle, isGroup,
                        base_dir, http_prefix,
                        domain, port,
                        send_threads, postLog,
                        cached_webfingers,
                        person_cache,
                        message_json,
                        federation_list,
                        debug, signing_priv_key_pem,
                        max_recent_posts, translate,
                        allow_deletion,
                        yt_replace_domain,
                        twitter_replacement_domain,
                        peertube_instances,
                        allow_local_network_access,
                        theme_name, system_language,
                        max_like_count, cw_lists, lists_enabled):
        if debug:
            print('DEBUG: Bookmark accepted from ' + actor)
        return False

    if _receiveUndoBookmark(recentPostsCache,
                            session, handle, isGroup,
                            base_dir, http_prefix,
                            domain, port,
                            send_threads, postLog,
                            cached_webfingers,
                            person_cache,
                            message_json,
                            federation_list,
                            debug, signing_priv_key_pem,
                            max_recent_posts, translate,
                            allow_deletion,
                            yt_replace_domain,
                            twitter_replacement_domain,
                            peertube_instances,
                            allow_local_network_access,
                            theme_name, system_language,
                            max_like_count, cw_lists, lists_enabled):
        if debug:
            print('DEBUG: Undo bookmark accepted from ' + actor)
        return False

    if isCreateInsideAnnounce(message_json):
        message_json = message_json['object']

    if _receiveAnnounce(recentPostsCache,
                        session, handle, isGroup,
                        base_dir, http_prefix,
                        domain, onion_domain, port,
                        send_threads, postLog,
                        cached_webfingers,
                        person_cache,
                        message_json,
                        federation_list,
                        debug, translate,
                        yt_replace_domain,
                        twitter_replacement_domain,
                        allow_local_network_access,
                        theme_name, system_language,
                        signing_priv_key_pem,
                        max_recent_posts,
                        allow_deletion,
                        peertube_instances,
                        max_like_count, cw_lists, lists_enabled):
        if debug:
            print('DEBUG: Announce accepted from ' + actor)

    if _receiveUndoAnnounce(recentPostsCache,
                            session, handle, isGroup,
                            base_dir, http_prefix,
                            domain, port,
                            send_threads, postLog,
                            cached_webfingers,
                            person_cache,
                            message_json,
                            federation_list,
                            debug):
        if debug:
            print('DEBUG: Undo announce accepted from ' + actor)
        return False

    if _receiveDelete(session, handle, isGroup,
                      base_dir, http_prefix,
                      domain, port,
                      send_threads, postLog,
                      cached_webfingers,
                      person_cache,
                      message_json,
                      federation_list,
                      debug, allow_deletion,
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

    if message_json.get('postNickname'):
        post_json_object = message_json['post']
    else:
        post_json_object = message_json

    nickname = handle.split('@')[0]
    jsonObj = None
    domain_full = get_full_domain(domain, port)
    if _validPostContent(base_dir, nickname, domain,
                         post_json_object, max_mentions, max_emoji,
                         allow_local_network_access, debug,
                         system_language, http_prefix,
                         domain_full, person_cache):
        # is the sending actor valid?
        if not validSendingActor(session, base_dir, nickname, domain,
                                 person_cache, post_json_object,
                                 signing_priv_key_pem, debug, unit_test):
            return False

        if post_json_object.get('object'):
            jsonObj = post_json_object['object']
            if not isinstance(jsonObj, dict):
                jsonObj = None
        else:
            jsonObj = post_json_object

        if _checkForGitPatches(base_dir, nickname, domain,
                               handle, jsonObj) == 2:
            return False

        # replace YouTube links, so they get less tracking data
        replaceYouTube(post_json_object, yt_replace_domain, system_language)
        # replace twitter link domains, so that you can view twitter posts
        # without having an account
        replaceTwitter(post_json_object, twitter_replacement_domain,
                       system_language)

        # list of indexes to be updated
        updateIndexList = ['inbox']
        populateReplies(base_dir, http_prefix, domain, post_json_object,
                        max_replies, debug)

        _receiveQuestionVote(base_dir, nickname, domain,
                             http_prefix, handle, debug,
                             post_json_object, recentPostsCache,
                             session, onion_domain, i2p_domain, port,
                             federation_list, send_threads, postLog,
                             cached_webfingers, person_cache,
                             signing_priv_key_pem,
                             max_recent_posts, translate,
                             allow_deletion,
                             yt_replace_domain,
                             twitter_replacement_domain,
                             peertube_instances,
                             allow_local_network_access,
                             theme_name, system_language,
                             max_like_count,
                             cw_lists, lists_enabled)

        isReplyToMutedPost = False

        if not isGroup:
            # create a DM notification file if needed
            postIsDM = isDM(post_json_object)
            if postIsDM:
                if not _isValidDM(base_dir, nickname, domain, port,
                                  post_json_object, updateIndexList,
                                  session, http_prefix,
                                  federation_list,
                                  send_threads, postLog,
                                  cached_webfingers,
                                  person_cache,
                                  translate, debug,
                                  lastBounceMessage,
                                  handle, system_language,
                                  signing_priv_key_pem,
                                  content_license_url):
                    return False

            # get the actor being replied to
            actor = local_actor_url(http_prefix, nickname, domain_full)

            # create a reply notification file if needed
            isReplyToMutedPost = \
                _createReplyNotificationFile(base_dir, nickname, domain,
                                             handle, debug, postIsDM,
                                             post_json_object, actor,
                                             updateIndexList, http_prefix,
                                             default_reply_interval_hrs)

            if isImageMedia(session, base_dir, http_prefix,
                            nickname, domain, post_json_object,
                            translate,
                            yt_replace_domain,
                            twitter_replacement_domain,
                            allow_local_network_access,
                            recentPostsCache, debug, system_language,
                            domain_full, person_cache, signing_priv_key_pem):
                # media index will be updated
                updateIndexList.append('tlmedia')
            if isBlogPost(post_json_object):
                # blogs index will be updated
                updateIndexList.append('tlblogs')

        # get the avatar for a reply/announce
        _obtainAvatarForReplyPost(session, base_dir,
                                  http_prefix, domain, onion_domain,
                                  person_cache, post_json_object, debug,
                                  signing_priv_key_pem)

        # save the post to file
        if save_json(post_json_object, destinationFilename):
            _lowFrequencyPostNotification(base_dir, http_prefix,
                                          nickname, domain, port,
                                          handle, postIsDM, jsonObj)

            # If this is a reply to a muted post then also mute it.
            # This enables you to ignore a threat that's getting boring
            if isReplyToMutedPost:
                print('MUTE REPLY: ' + destinationFilename)
                destinationFilenameMuted = destinationFilename + '.muted'
                try:
                    with open(destinationFilenameMuted, 'w+') as muteFile:
                        muteFile.write('\n')
                except OSError:
                    print('EX: unable to write ' + destinationFilenameMuted)

            # update the indexes for different timelines
            for boxname in updateIndexList:
                if not inboxUpdateIndex(boxname, base_dir, handle,
                                        destinationFilename, debug):
                    print('ERROR: unable to update ' + boxname + ' index')
                else:
                    if boxname == 'inbox':
                        if isRecentPost(post_json_object, 3):
                            domain_full = get_full_domain(domain, port)
                            updateSpeaker(base_dir, http_prefix,
                                          nickname, domain, domain_full,
                                          post_json_object, person_cache,
                                          translate, None, theme_name)
                    if not unit_test:
                        if debug:
                            print('Saving inbox post as html to cache')

                        htmlCacheStartTime = time.time()
                        handleName = handle.split('@')[0]
                        _inboxStorePostToHtmlCache(recentPostsCache,
                                                   max_recent_posts,
                                                   translate, base_dir,
                                                   http_prefix,
                                                   session, cached_webfingers,
                                                   person_cache,
                                                   handleName,
                                                   domain, port,
                                                   post_json_object,
                                                   allow_deletion,
                                                   boxname,
                                                   show_published_date_only,
                                                   peertube_instances,
                                                   allow_local_network_access,
                                                   theme_name, system_language,
                                                   max_like_count,
                                                   signing_priv_key_pem,
                                                   cw_lists, lists_enabled)
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
                editedPostFilename(base_dir, handleName, domain,
                                   post_json_object, debug, 300)

            updateConversation(base_dir, handleName, domain, post_json_object)

            # If this was an edit then delete the previous version of the post
            if editedFilename:
                deletePost(base_dir, http_prefix,
                           nickname, domain, editedFilename,
                           debug, recentPostsCache)

            # store the id of the last post made by this actor
            _storeLastPostId(base_dir, nickname, domain, post_json_object)

            _inboxUpdateCalendar(base_dir, handle, post_json_object)

            storeHashTags(base_dir, handleName, domain,
                          http_prefix, domain_full,
                          post_json_object, translate)

            # send the post out to group members
            if isGroup:
                _sendToGroupMembers(session, base_dir, handle, port,
                                    post_json_object,
                                    http_prefix, federation_list, send_threads,
                                    postLog, cached_webfingers, person_cache,
                                    debug, system_language,
                                    onion_domain, i2p_domain,
                                    signing_priv_key_pem)

    # if the post wasn't saved
    if not os.path.isfile(destinationFilename):
        return False

    return True


def clearQueueItems(base_dir: str, queue: []) -> None:
    """Clears the queue for each account
    """
    ctr = 0
    queue.clear()
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for account in dirs:
            queueDir = base_dir + '/accounts/' + account + '/queue'
            if not os.path.isdir(queueDir):
                continue
            for queuesubdir, queuedirs, queuefiles in os.walk(queueDir):
                for qfile in queuefiles:
                    try:
                        os.remove(os.path.join(queueDir, qfile))
                        ctr += 1
                    except OSError:
                        print('EX: clearQueueItems unable to delete ' + qfile)
                break
        break
    if ctr > 0:
        print('Removed ' + str(ctr) + ' inbox queue items')


def _restoreQueueItems(base_dir: str, queue: []) -> None:
    """Checks the queue for each account and appends filenames
    """
    queue.clear()
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for account in dirs:
            queueDir = base_dir + '/accounts/' + account + '/queue'
            if not os.path.isdir(queueDir):
                continue
            for queuesubdir, queuedirs, queuefiles in os.walk(queueDir):
                for qfile in queuefiles:
                    queue.append(os.path.join(queueDir, qfile))
                break
        break
    if len(queue) > 0:
        print('Restored ' + str(len(queue)) + ' inbox queue items')


def runInboxQueueWatchdog(project_version: str, httpd) -> None:
    """This tries to keep the inbox thread running even if it dies
    """
    print('Starting inbox queue watchdog')
    inbox_queueOriginal = httpd.thrInboxQueue.clone(runInboxQueue)
    httpd.thrInboxQueue.start()
    while True:
        time.sleep(20)
        if not httpd.thrInboxQueue.is_alive() or httpd.restartInboxQueue:
            httpd.restartInboxQueueInProgress = True
            httpd.thrInboxQueue.kill()
            httpd.thrInboxQueue = inbox_queueOriginal.clone(runInboxQueue)
            httpd.inbox_queue.clear()
            httpd.thrInboxQueue.start()
            print('Restarting inbox queue...')
            httpd.restartInboxQueueInProgress = False
            httpd.restartInboxQueue = False


def _inboxQuotaExceeded(queue: {}, queueFilename: str,
                        queueJson: {}, quotasDaily: {}, quotasPerMin: {},
                        domain_max_posts_per_day: int,
                        account_max_posts_per_day: int,
                        debug: bool) -> bool:
    """limit the number of posts which can arrive per domain per day
    """
    postDomain = queueJson['postDomain']
    if not postDomain:
        return False

    if domain_max_posts_per_day > 0:
        if quotasDaily['domains'].get(postDomain):
            if quotasDaily['domains'][postDomain] > \
               domain_max_posts_per_day:
                print('Queue: Quota per day - Maximum posts for ' +
                      postDomain + ' reached (' +
                      str(domain_max_posts_per_day) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queueFilename)
                    except OSError:
                        print('EX: _inboxQuotaExceeded unable to delete ' +
                              str(queueFilename))
                    queue.pop(0)
                return True
            quotasDaily['domains'][postDomain] += 1
        else:
            quotasDaily['domains'][postDomain] = 1

        if quotasPerMin['domains'].get(postDomain):
            domainMaxPostsPerMin = \
                int(domain_max_posts_per_day / (24 * 60))
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
                    except OSError:
                        print('EX: _inboxQuotaExceeded unable to delete ' +
                              str(queueFilename))
                    queue.pop(0)
                return True
            quotasPerMin['domains'][postDomain] += 1
        else:
            quotasPerMin['domains'][postDomain] = 1

    if account_max_posts_per_day > 0:
        postHandle = queueJson['postNickname'] + '@' + postDomain
        if quotasDaily['accounts'].get(postHandle):
            if quotasDaily['accounts'][postHandle] > \
               account_max_posts_per_day:
                print('Queue: Quota account posts per day -' +
                      ' Maximum posts for ' +
                      postHandle + ' reached (' +
                      str(account_max_posts_per_day) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queueFilename)
                    except OSError:
                        print('EX: _inboxQuotaExceeded unable to delete ' +
                              str(queueFilename))
                    queue.pop(0)
                return True
            quotasDaily['accounts'][postHandle] += 1
        else:
            quotasDaily['accounts'][postHandle] = 1

        if quotasPerMin['accounts'].get(postHandle):
            accountMaxPostsPerMin = \
                int(account_max_posts_per_day / (24 * 60))
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
                    except OSError:
                        print('EX: _inboxQuotaExceeded unable to delete ' +
                              str(queueFilename))
                    queue.pop(0)
                return True
            quotasPerMin['accounts'][postHandle] += 1
        else:
            quotasPerMin['accounts'][postHandle] = 1

    if debug:
        if account_max_posts_per_day > 0 or domain_max_posts_per_day > 0:
            pprint(quotasDaily)
    return False


def _checkJsonSignature(base_dir: str, queueJson: {}) -> (bool, bool):
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
                base_dir + '/accounts/unknownContexts.txt'
            unknownContext = str(originalJson['@context'])

            print('unrecognized @context: ' + unknownContext)

            alreadyUnknown = False
            if os.path.isfile(unknownContextsFile):
                if unknownContext in \
                   open(unknownContextsFile).read():
                    alreadyUnknown = True

            if not alreadyUnknown:
                try:
                    with open(unknownContextsFile, 'a+') as unknownFile:
                        unknownFile.write(unknownContext + '\n')
                except OSError:
                    print('EX: unable to append ' + unknownContextsFile)
    else:
        print('Unrecognized jsonld signature type: ' + jwebsigType)

        unknownSignaturesFile = \
            base_dir + '/accounts/unknownJsonSignatures.txt'

        alreadyUnknown = False
        if os.path.isfile(unknownSignaturesFile):
            if jwebsigType in \
               open(unknownSignaturesFile).read():
                alreadyUnknown = True

        if not alreadyUnknown:
            try:
                with open(unknownSignaturesFile, 'a+') as unknownFile:
                    unknownFile.write(jwebsigType + '\n')
            except OSError:
                print('EX: unable to append ' + unknownSignaturesFile)
    return hasJsonSignature, jwebsigType


def _receiveFollowRequest(session, base_dir: str, http_prefix: str,
                          port: int, send_threads: [], postLog: [],
                          cached_webfingers: {}, person_cache: {},
                          message_json: {}, federation_list: [],
                          debug: bool, project_version: str,
                          max_followers: int, onion_domain: str,
                          signing_priv_key_pem: str, unit_test: bool) -> bool:
    """Receives a follow request within the POST section of HTTPServer
    """
    if not message_json['type'].startswith('Follow'):
        if not message_json['type'].startswith('Join'):
            return False
    print('Receiving follow request')
    if not hasActor(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: users/profile/accounts/channel missing from actor')
        return False
    domain, tempPort = getDomainFromActor(message_json['actor'])
    fromPort = port
    domain_full = get_full_domain(domain, tempPort)
    if tempPort:
        fromPort = tempPort
    if not domainPermitted(domain, federation_list):
        if debug:
            print('DEBUG: follower from domain not permitted - ' + domain)
        return False
    nickname = getNicknameFromActor(message_json['actor'])
    if not nickname:
        # single user instance
        nickname = 'dev'
        if debug:
            print('DEBUG: follow request does not contain a ' +
                  'nickname. Assuming single user instance.')
    if not message_json.get('to'):
        message_json['to'] = message_json['object']
    if not has_users_path(message_json['object']):
        if debug:
            print('DEBUG: users/profile/channel/accounts ' +
                  'not found within object')
        return False
    domainToFollow, tempPort = getDomainFromActor(message_json['object'])
    if not domainPermitted(domainToFollow, federation_list):
        if debug:
            print('DEBUG: follow domain not permitted ' + domainToFollow)
        return True
    domainToFollowFull = get_full_domain(domainToFollow, tempPort)
    nicknameToFollow = getNicknameFromActor(message_json['object'])
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
    if max_followers > 0:
        if getNoOfFollowers(base_dir,
                            nicknameToFollow, domainToFollow,
                            True) > max_followers:
            print('WARN: ' + nicknameToFollow +
                  ' has reached their maximum number of followers')
            return True
    handleToFollow = nicknameToFollow + '@' + domainToFollow
    if domainToFollow == domain:
        if not os.path.isdir(base_dir + '/accounts/' + handleToFollow):
            if debug:
                print('DEBUG: followed account not found - ' +
                      base_dir + '/accounts/' + handleToFollow)
            return True

    if isFollowerOfPerson(base_dir,
                          nicknameToFollow, domainToFollowFull,
                          nickname, domain_full):
        if debug:
            print('DEBUG: ' + nickname + '@' + domain +
                  ' is already a follower of ' +
                  nicknameToFollow + '@' + domainToFollow)
        return True

    approveHandle = nickname + '@' + domain_full

    # is the actor sending the request valid?
    if not validSendingActor(session, base_dir,
                             nicknameToFollow, domainToFollow,
                             person_cache, message_json,
                             signing_priv_key_pem, debug, unit_test):
        print('REJECT spam follow request ' + approveHandle)
        return False

    # what is the followers policy?
    if followApprovalRequired(base_dir, nicknameToFollow,
                              domainToFollow, debug, approveHandle):
        print('Follow approval is required')
        if domain.endswith('.onion'):
            if noOfFollowRequests(base_dir,
                                  nicknameToFollow, domainToFollow,
                                  nickname, domain, fromPort,
                                  'onion') > 5:
                print('Too many follow requests from onion addresses')
                return False
        elif domain.endswith('.i2p'):
            if noOfFollowRequests(base_dir,
                                  nicknameToFollow, domainToFollow,
                                  nickname, domain, fromPort,
                                  'i2p') > 5:
                print('Too many follow requests from i2p addresses')
                return False
        else:
            if noOfFollowRequests(base_dir,
                                  nicknameToFollow, domainToFollow,
                                  nickname, domain, fromPort,
                                  '') > 10:
                print('Too many follow requests')
                return False

        # Get the actor for the follower and add it to the cache.
        # Getting their public key has the same result
        if debug:
            print('Obtaining the following actor: ' + message_json['actor'])
        if not getPersonPubKey(base_dir, session, message_json['actor'],
                               person_cache, debug, project_version,
                               http_prefix, domainToFollow, onion_domain,
                               signing_priv_key_pem):
            if debug:
                print('Unable to obtain following actor: ' +
                      message_json['actor'])

        group_account = \
            hasGroupType(base_dir, message_json['actor'], person_cache)
        if group_account and isGroupAccount(base_dir, nickname, domain):
            print('Group cannot follow a group')
            return False

        print('Storing follow request for approval')
        return storeFollowRequest(base_dir,
                                  nicknameToFollow, domainToFollow, port,
                                  nickname, domain, fromPort,
                                  message_json, debug, message_json['actor'],
                                  group_account)
    else:
        print('Follow request does not require approval ' + approveHandle)
        # update the followers
        accountToBeFollowed = \
            acct_dir(base_dir, nicknameToFollow, domainToFollow)
        if os.path.isdir(accountToBeFollowed):
            followersFilename = accountToBeFollowed + '/followers.txt'

            # for actors which don't follow the mastodon
            # /users/ path convention store the full actor
            if '/users/' not in message_json['actor']:
                approveHandle = message_json['actor']

            # Get the actor for the follower and add it to the cache.
            # Getting their public key has the same result
            if debug:
                print('Obtaining the following actor: ' +
                      message_json['actor'])
            if not getPersonPubKey(base_dir, session, message_json['actor'],
                                   person_cache, debug, project_version,
                                   http_prefix, domainToFollow, onion_domain,
                                   signing_priv_key_pem):
                if debug:
                    print('Unable to obtain following actor: ' +
                          message_json['actor'])

            print('Updating followers file: ' +
                  followersFilename + ' adding ' + approveHandle)
            if os.path.isfile(followersFilename):
                if approveHandle not in open(followersFilename).read():
                    group_account = \
                        hasGroupType(base_dir,
                                     message_json['actor'], person_cache)
                    if debug:
                        print(approveHandle + ' / ' + message_json['actor'] +
                              ' is Group: ' + str(group_account))
                    if group_account and \
                       isGroupAccount(base_dir, nickname, domain):
                        print('Group cannot follow a group')
                        return False
                    try:
                        with open(followersFilename, 'r+') as followersFile:
                            content = followersFile.read()
                            if approveHandle + '\n' not in content:
                                followersFile.seek(0, 0)
                                if not group_account:
                                    followersFile.write(approveHandle +
                                                        '\n' + content)
                                else:
                                    followersFile.write('!' + approveHandle +
                                                        '\n' + content)
                    except Exception as ex:
                        print('WARN: ' +
                              'Failed to write entry to followers file ' +
                              str(ex))
            else:
                try:
                    with open(followersFilename, 'w+') as followersFile:
                        followersFile.write(approveHandle + '\n')
                except OSError:
                    print('EX: unable to write ' + followersFilename)

    print('Beginning follow accept')
    return followedAccountAccepts(session, base_dir, http_prefix,
                                  nicknameToFollow, domainToFollow, port,
                                  nickname, domain, fromPort,
                                  message_json['actor'], federation_list,
                                  message_json, send_threads, postLog,
                                  cached_webfingers, person_cache,
                                  debug, project_version, True,
                                  signing_priv_key_pem)


def runInboxQueue(recentPostsCache: {}, max_recent_posts: int,
                  project_version: str,
                  base_dir: str, http_prefix: str,
                  send_threads: [], postLog: [],
                  cached_webfingers: {}, person_cache: {}, queue: [],
                  domain: str,
                  onion_domain: str, i2p_domain: str,
                  port: int, proxy_type: str,
                  federation_list: [], max_replies: int,
                  domain_max_posts_per_day: int,
                  account_max_posts_per_day: int,
                  allow_deletion: bool, debug: bool, max_mentions: int,
                  max_emoji: int, translate: {}, unit_test: bool,
                  yt_replace_domain: str,
                  twitter_replacement_domain: str,
                  show_published_date_only: bool,
                  max_followers: int,
                  allow_local_network_access: bool,
                  peertube_instances: [],
                  verify_all_signatures: bool,
                  theme_name: str, system_language: str,
                  max_like_count: int, signing_priv_key_pem: str,
                  default_reply_interval_hrs: int,
                  cw_lists: {}) -> None:
    """Processes received items and moves them to the appropriate
    directories
    """
    currSessionTime = int(time.time())
    session_last_update = currSessionTime
    print('Starting new session when starting inbox queue')
    session = createSession(proxy_type)
    inboxHandle = 'inbox@' + domain
    if debug:
        print('DEBUG: Inbox queue running')

    # if queue processing was interrupted (eg server crash)
    # then this loads any outstanding items back into the queue
    _restoreQueueItems(base_dir, queue)

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
            if broch_modeLapses(base_dir, brochLapseDays):
                brochLapseDays = random.randrange(7, 14)
            print('>>> Heartbeat Q:' + str(len(queue)) + ' ' +
                  '{:%F %T}'.format(datetime.datetime.now()))
            heartBeatCtr = 0

        if len(queue) == 0:
            # restore any remaining queue items
            queueRestoreCtr += 1
            if queueRestoreCtr >= 30:
                queueRestoreCtr = 0
                _restoreQueueItems(base_dir, queue)
            continue

        curr_time = int(time.time())

        # recreate the session periodically
        if not session or curr_time - session_last_update > 21600:
            print('Regenerating inbox queue session at 6hr interval')
            session = createSession(proxy_type)
            if not session:
                continue
            session_last_update = curr_time

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
        queueJson = load_json(queueFilename, 1)
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
                except OSError:
                    print('EX: runInboxQueue 1 unable to delete ' +
                          str(queueFilename))
            continue

        # clear the daily quotas for maximum numbers of received posts
        if curr_time - quotasLastUpdateDaily > 60 * 60 * 24:
            quotasDaily = {
                'domains': {},
                'accounts': {}
            }
            quotasLastUpdateDaily = curr_time

        if curr_time - quotasLastUpdatePerMin > 60:
            # clear the per minute quotas for maximum numbers of received posts
            quotasPerMin = {
                'domains': {},
                'accounts': {}
            }
            # also check if the json signature enforcement has changed
            verifyAllSigs = get_config_param(base_dir, "verify_all_signatures")
            if verifyAllSigs is not None:
                verify_all_signatures = verifyAllSigs
            # change the last time that this was done
            quotasLastUpdatePerMin = curr_time

        if _inboxQuotaExceeded(queue, queueFilename,
                               queueJson, quotasDaily, quotasPerMin,
                               domain_max_posts_per_day,
                               account_max_posts_per_day, debug):
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
                getPersonPubKey(base_dir, session, keyId,
                                person_cache, debug,
                                project_version, http_prefix,
                                domain, onion_domain, signing_priv_key_pem)
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
                except OSError:
                    print('EX: runInboxQueue 2 unable to delete ' +
                          str(queueFilename))
            if len(queue) > 0:
                queue.pop(0)
            continue

        # check the http header signature
        if debug:
            print('DEBUG: checking http header signature')
            pprint(queueJson['httpHeaders'])
        postStr = json.dumps(queueJson['post'])
        httpSignatureFailed = False
        if not verifyPostHeaders(http_prefix,
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
        hasJsonSignature, jwebsigType = \
            _checkJsonSignature(base_dir, queueJson)

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

            if verify_all_signatures:
                originalJson = queueJson['original']
                print('Queue: inbox post does not have a jsonld signature ' +
                      keyId + ' ' + str(originalJson))

            if httpSignatureFailed or verify_all_signatures:
                if os.path.isfile(queueFilename):
                    try:
                        os.remove(queueFilename)
                    except OSError:
                        print('EX: runInboxQueue 3 unable to delete ' +
                              str(queueFilename))
                if len(queue) > 0:
                    queue.pop(0)
                continue
        else:
            if httpSignatureFailed or verify_all_signatures:
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
                        except OSError:
                            print('EX: runInboxQueue 4 unable to delete ' +
                                  str(queueFilename))
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
                        base_dir, http_prefix, port,
                        send_threads, postLog,
                        cached_webfingers,
                        person_cache,
                        queueJson['post'],
                        federation_list,
                        debug):
            print('Queue: Undo accepted from ' + keyId)
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except OSError:
                    print('EX: runInboxQueue 5 unable to delete ' +
                          str(queueFilename))
            if len(queue) > 0:
                queue.pop(0)
            continue

        if debug:
            print('DEBUG: checking for follow requests')
        if _receiveFollowRequest(session,
                                 base_dir, http_prefix, port,
                                 send_threads, postLog,
                                 cached_webfingers,
                                 person_cache,
                                 queueJson['post'],
                                 federation_list,
                                 debug, project_version,
                                 max_followers, onion_domain,
                                 signing_priv_key_pem, unit_test):
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except OSError:
                    print('EX: runInboxQueue 6 unable to delete ' +
                          str(queueFilename))
            if len(queue) > 0:
                queue.pop(0)
            print('Queue: Follow activity for ' + keyId +
                  ' removed from queue')
            continue
        else:
            if debug:
                print('DEBUG: No follow requests')

        if receiveAcceptReject(session,
                               base_dir, http_prefix, domain, port,
                               send_threads, postLog,
                               cached_webfingers, person_cache,
                               queueJson['post'],
                               federation_list, debug):
            print('Queue: Accept/Reject received from ' + keyId)
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except OSError:
                    print('EX: runInboxQueue 7 unable to delete ' +
                          str(queueFilename))
            if len(queue) > 0:
                queue.pop(0)
            continue

        if _receiveUpdate(recentPostsCache, session,
                          base_dir, http_prefix,
                          domain, port,
                          send_threads, postLog,
                          cached_webfingers,
                          person_cache,
                          queueJson['post'],
                          federation_list,
                          queueJson['postNickname'],
                          debug):
            if debug:
                print('Queue: Update accepted from ' + keyId)
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except OSError:
                    print('EX: runInboxQueue 8 unable to delete ' +
                          str(queueFilename))
            if len(queue) > 0:
                queue.pop(0)
            continue

        # get recipients list
        recipientsDict, recipientsDictFollowers = \
            _inboxPostRecipients(base_dir, queueJson['post'],
                                 http_prefix, domain, port, debug)
        if len(recipientsDict.items()) == 0 and \
           len(recipientsDictFollowers.items()) == 0:
            if debug:
                print('Queue: no recipients were resolved ' +
                      'for post arriving in inbox')
            if os.path.isfile(queueFilename):
                try:
                    os.remove(queueFilename)
                except OSError:
                    print('EX: runInboxQueue 9 unable to delete ' +
                          str(queueFilename))
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
                save_json(queueJson['post'], sharedInboxPostFilename)

        lists_enabled = get_config_param(base_dir, "lists_enabled")
        content_license_url = get_config_param(base_dir, "content_license_url")

        # for posts addressed to specific accounts
        for handle, capsId in recipientsDict.items():
            destination = \
                queueJson['destination'].replace(inboxHandle, handle)
            _inboxAfterInitial(recentPostsCache,
                               max_recent_posts,
                               session, keyId, handle,
                               queueJson['post'],
                               base_dir, http_prefix,
                               send_threads, postLog,
                               cached_webfingers,
                               person_cache, queue,
                               domain,
                               onion_domain, i2p_domain,
                               port, proxy_type,
                               federation_list,
                               debug,
                               queueFilename, destination,
                               max_replies, allow_deletion,
                               max_mentions, max_emoji,
                               translate, unit_test,
                               yt_replace_domain,
                               twitter_replacement_domain,
                               show_published_date_only,
                               allow_local_network_access,
                               peertube_instances,
                               lastBounceMessage,
                               theme_name, system_language,
                               max_like_count,
                               signing_priv_key_pem,
                               default_reply_interval_hrs,
                               cw_lists, lists_enabled,
                               content_license_url)
            if debug:
                pprint(queueJson['post'])
                print('Queue: Queue post accepted')
        if os.path.isfile(queueFilename):
            try:
                os.remove(queueFilename)
            except OSError:
                print('EX: runInboxQueue 10 unable to delete ' +
                      str(queueFilename))
        if len(queue) > 0:
            queue.pop(0)
