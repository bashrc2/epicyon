__filename__ = "posts.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import json
import html
import datetime
import os
import shutil
import sys
import time
import random
from socket import error as SocketError
from time import gmtime, strftime
from collections import OrderedDict
from threads import threadWithTrace
from cache import storePersonInCache
from cache import getPersonFromCache
from cache import expirePersonCache
from pprint import pprint
from session import createSession
from session import getJson
from session import postJson
from session import postJsonString
from session import postImage
from webfinger import webfingerHandle
from httpsig import createSignedHeader
from siteactive import siteIsActive
from languages import understoodPostLanguage
from utils import getUserPaths
from utils import invalidCiphertext
from utils import hasObjectStringType
from utils import removeIdEnding
from utils import replaceUsersWithAt
from utils import hasGroupType
from utils import getBaseContentFromPost
from utils import removeDomainPort
from utils import getPortFromDomain
from utils import hasObjectDict
from utils import rejectPostId
from utils import removeInvalidChars
from utils import fileLastModified
from utils import isPublicPost
from utils import hasUsersPath
from utils import validPostDate
from utils import getFullDomain
from utils import getFollowersList
from utils import isEvil
from utils import getStatusNumber
from utils import createPersonDir
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import deletePost
from utils import validNickname
from utils import locatePost
from utils import loadJson
from utils import saveJson
from utils import getConfigParam
from utils import locateNewsVotes
from utils import locateNewsArrival
from utils import votesOnNewswireItem
from utils import removeHtml
from utils import dangerousMarkup
from utils import acctDir
from utils import localActorUrl
from media import attachMedia
from media import replaceYouTube
from media import replaceTwitter
from content import wordsSimilarity
from content import limitRepeatedWords
from content import tagExists
from content import removeLongWords
from content import addHtmlTags
from content import replaceEmojiFromTags
from content import removeTextFormatting
from auth import createBasicAuthHeader
from blocking import isBlocked
from blocking import isBlockedDomain
from filters import isFiltered
from git import convertPostToPatch
from linked_data_sig import generateJsonSignature
from petnames import resolvePetnames
from video import convertVideoToNote
from context import getIndividualPostContext


def isModerator(base_dir: str, nickname: str) -> bool:
    """Returns true if the given nickname is a moderator
    """
    moderatorsFile = base_dir + '/accounts/moderators.txt'

    if not os.path.isfile(moderatorsFile):
        adminName = getConfigParam(base_dir, 'admin')
        if not adminName:
            return False
        if adminName == nickname:
            return True
        return False

    with open(moderatorsFile, 'r') as f:
        lines = f.readlines()
        if len(lines) == 0:
            adminName = getConfigParam(base_dir, 'admin')
            if not adminName:
                return False
            if adminName == nickname:
                return True
        for moderator in lines:
            moderator = moderator.strip('\n').strip('\r')
            if moderator == nickname:
                return True
    return False


def noOfFollowersOnDomain(base_dir: str, handle: str,
                          domain: str, followFile='followers.txt') -> int:
    """Returns the number of followers of the given handle from the given domain
    """
    filename = base_dir + '/accounts/' + handle + '/' + followFile
    if not os.path.isfile(filename):
        return 0

    ctr = 0
    with open(filename, 'r') as followersFilename:
        for followerHandle in followersFilename:
            if '@' in followerHandle:
                followerDomain = followerHandle.split('@')[1]
                followerDomain = followerDomain.replace('\n', '')
                followerDomain = followerDomain.replace('\r', '')
                if domain == followerDomain:
                    ctr += 1
    return ctr


def _getLocalPrivateKey(base_dir: str, nickname: str, domain: str) -> str:
    """Returns the private key for a local account
    """
    if not domain or not nickname:
        return None
    handle = nickname + '@' + domain
    keyFilename = base_dir + '/keys/private/' + handle.lower() + '.key'
    if not os.path.isfile(keyFilename):
        return None
    with open(keyFilename, 'r') as pemFile:
        return pemFile.read()
    return None


def getInstanceActorKey(base_dir: str, domain: str) -> str:
    """Returns the private key for the instance actor used for
    signing GET posts
    """
    return _getLocalPrivateKey(base_dir, 'inbox', domain)


def _getLocalPublicKey(base_dir: str, nickname: str, domain: str) -> str:
    """Returns the public key for a local account
    """
    if not domain or not nickname:
        return None
    handle = nickname + '@' + domain
    keyFilename = base_dir + '/keys/public/' + handle.lower() + '.key'
    if not os.path.isfile(keyFilename):
        return None
    with open(keyFilename, 'r') as pemFile:
        return pemFile.read()
    return None


def _getPersonKey(nickname: str, domain: str, base_dir: str,
                  keyType: str = 'public', debug: bool = False):
    """Returns the public or private key of a person
    """
    if keyType == 'private':
        keyPem = _getLocalPrivateKey(base_dir, nickname, domain)
    else:
        keyPem = _getLocalPublicKey(base_dir, nickname, domain)
    if not keyPem:
        if debug:
            print('DEBUG: ' + keyType + ' key file not found')
        return ''
    if len(keyPem) < 20:
        if debug:
            print('DEBUG: private key was too short: ' + keyPem)
        return ''
    return keyPem


def _cleanHtml(rawHtml: str) -> str:
    # text=BeautifulSoup(rawHtml, 'html.parser').get_text()
    text = rawHtml
    return html.unescape(text)


def getUserUrl(wfRequest: {}, sourceId: int, debug: bool) -> str:
    """Gets the actor url from a webfinger request
    """
    if not wfRequest.get('links'):
        if sourceId == 72367:
            print('getUserUrl ' + str(sourceId) +
                  ' failed to get display name for webfinger ' +
                  str(wfRequest))
        else:
            print('getUserUrl webfinger activity+json contains no links ' +
                  str(sourceId) + ' ' + str(wfRequest))
        return None
    for link in wfRequest['links']:
        if not (link.get('type') and link.get('href')):
            continue
        if link['type'] != 'application/activity+json':
            continue
        if '/@' not in link['href']:
            if debug and not hasUsersPath(link['href']):
                print('getUserUrl webfinger activity+json ' +
                      'contains single user instance actor ' +
                      str(sourceId) + ' ' + str(link))
        else:
            return link['href'].replace('/@', '/users/')
        return link['href']
    return None


def parseUserFeed(signingPrivateKeyPem: str,
                  session, feedUrl: str, asHeader: {},
                  project_version: str, http_prefix: str,
                  originDomain: str, debug: bool, depth: int = 0) -> []:
    if depth > 10:
        if debug:
            print('Maximum search depth reached')
        return None

    if debug:
        print('Getting user feed for ' + feedUrl)
        print('User feed header ' + str(asHeader))
        print('http_prefix ' + str(http_prefix))
        print('originDomain ' + str(originDomain))

    feedJson = getJson(signingPrivateKeyPem, session, feedUrl, asHeader, None,
                       debug, project_version, http_prefix, originDomain)
    if not feedJson:
        profileStr = 'https://www.w3.org/ns/activitystreams'
        acceptStr = 'application/ld+json; profile="' + profileStr + '"'
        if asHeader['Accept'] != acceptStr:
            asHeader = {
                'Accept': acceptStr
            }
            feedJson = getJson(signingPrivateKeyPem, session, feedUrl,
                               asHeader, None, debug, project_version,
                               http_prefix, originDomain)
    if not feedJson:
        if debug:
            print('No user feed was returned')
        return None

    if debug:
        print('User feed:')
        pprint(feedJson)

    if 'orderedItems' in feedJson:
        return feedJson['orderedItems']
    elif 'items' in feedJson:
        return feedJson['items']

    nextUrl = None
    if 'first' in feedJson:
        nextUrl = feedJson['first']
    elif 'next' in feedJson:
        nextUrl = feedJson['next']

    if debug:
        print('User feed next url: ' + str(nextUrl))

    if nextUrl:
        if isinstance(nextUrl, str):
            if '?max_id=0' not in nextUrl:
                userFeed = \
                    parseUserFeed(signingPrivateKeyPem,
                                  session, nextUrl, asHeader,
                                  project_version, http_prefix,
                                  originDomain, debug, depth + 1)
                if userFeed:
                    return userFeed
        elif isinstance(nextUrl, dict):
            userFeed = nextUrl
            if userFeed.get('orderedItems'):
                return userFeed['orderedItems']
            elif userFeed.get('items'):
                return userFeed['items']
    return None


def _getPersonBoxActor(session, base_dir: str, actor: str,
                       profileStr: str, asHeader: {},
                       debug: bool, project_version: str,
                       http_prefix: str, originDomain: str,
                       personCache: {},
                       signingPrivateKeyPem: str,
                       sourceId: int) -> {}:
    """Returns the actor json for the given actor url
    """
    personJson = \
        getPersonFromCache(base_dir, actor, personCache, True)
    if personJson:
        return personJson

    if '/channel/' in actor or '/accounts/' in actor:
        asHeader = {
            'Accept': 'application/ld+json; profile="' + profileStr + '"'
        }
    personJson = getJson(signingPrivateKeyPem, session, actor, asHeader, None,
                         debug, project_version, http_prefix, originDomain)
    if personJson:
        return personJson
    asHeader = {
        'Accept': 'application/ld+json; profile="' + profileStr + '"'
    }
    personJson = getJson(signingPrivateKeyPem, session, actor, asHeader, None,
                         debug, project_version, http_prefix, originDomain)
    if personJson:
        return personJson
    print('Unable to get actor for ' + actor + ' ' + str(sourceId))
    if not signingPrivateKeyPem:
        print('No signing key provided when getting actor')
    return None


def getPersonBox(signingPrivateKeyPem: str, originDomain: str,
                 base_dir: str, session, wfRequest: {}, personCache: {},
                 project_version: str, http_prefix: str,
                 nickname: str, domain: str,
                 boxName: str = 'inbox',
                 sourceId=0) -> (str, str, str, str, str, str, str, bool):
    debug = False
    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/activity+json; profile="' + profileStr + '"'
    }
    if not wfRequest:
        print('No webfinger given')
        return None, None, None, None, None, None, None, None

    # get the actor / personUrl
    if not wfRequest.get('errors'):
        # get the actor url from webfinger links
        personUrl = getUserUrl(wfRequest, sourceId, debug)
    else:
        if nickname == 'dev':
            # try single user instance
            print('getPersonBox: Trying single user instance with ld+json')
            personUrl = http_prefix + '://' + domain
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
        else:
            # the final fallback is a mastodon style url
            personUrl = localActorUrl(http_prefix, nickname, domain)
    if not personUrl:
        return None, None, None, None, None, None, None, None

    # get the actor json from the url
    personJson = \
        _getPersonBoxActor(session, base_dir, personUrl,
                           profileStr, asHeader,
                           debug, project_version,
                           http_prefix, originDomain,
                           personCache, signingPrivateKeyPem,
                           sourceId)
    if not personJson:
        return None, None, None, None, None, None, None, None

    isGroup = False
    if personJson.get('type'):
        if personJson['type'] == 'Group':
            isGroup = True

    # get the url for the box/collection
    boxJson = None
    if not personJson.get(boxName):
        if personJson.get('endpoints'):
            if personJson['endpoints'].get(boxName):
                boxJson = personJson['endpoints'][boxName]
    else:
        boxJson = personJson[boxName]
    if not boxJson:
        return None, None, None, None, None, None, None, None

    personId = None
    if personJson.get('id'):
        personId = personJson['id']
    pubKeyId = None
    pubKey = None
    if personJson.get('publicKey'):
        if personJson['publicKey'].get('id'):
            pubKeyId = personJson['publicKey']['id']
        if personJson['publicKey'].get('publicKeyPem'):
            pubKey = personJson['publicKey']['publicKeyPem']
    sharedInbox = None
    if personJson.get('sharedInbox'):
        sharedInbox = personJson['sharedInbox']
    else:
        if personJson.get('endpoints'):
            if personJson['endpoints'].get('sharedInbox'):
                sharedInbox = personJson['endpoints']['sharedInbox']
    avatarUrl = None
    if personJson.get('icon'):
        if personJson['icon'].get('url'):
            avatarUrl = personJson['icon']['url']
    displayName = None
    if personJson.get('name'):
        displayName = personJson['name']
        if dangerousMarkup(personJson['name'], False):
            displayName = '*ADVERSARY*'
        elif isFiltered(base_dir,
                        nickname, domain,
                        displayName):
            displayName = '*FILTERED*'
        # have they moved?
        if personJson.get('movedTo'):
            displayName += ' ⌂'

    storePersonInCache(base_dir, personUrl, personJson, personCache, True)

    return boxJson, pubKeyId, pubKey, personId, sharedInbox, \
        avatarUrl, displayName, isGroup


def _isPublicFeedPost(item: {}, personPosts: {}, debug: bool) -> bool:
    """Is the given post a public feed post?
    """
    if not isinstance(item, dict):
        if debug:
            print('item object is not a dict')
            pprint(item)
        return False
    if not item.get('id'):
        if debug:
            print('No id')
        return False
    if not item.get('type'):
        if debug:
            print('No type')
        return False
    if item['type'] != 'Create' and \
       item['type'] != 'Announce' and \
       item['type'] != 'Page' and \
       item['type'] != 'Note':
        if debug:
            print('Not a Create/Note/Announce type')
        return False
    if item.get('object'):
        if isinstance(item['object'], dict):
            if not item['object'].get('published'):
                if debug:
                    print('No published attribute')
                return False
        elif isinstance(item['object'], str):
            if not item.get('published'):
                if debug:
                    print('No published attribute')
                return False
        else:
            if debug:
                print('object is not a dict or string')
            return False
    elif item['type'] == 'Note' or item['type'] == 'Page':
        if not item.get('published'):
            if debug:
                print('No published attribute')
            return False
    if not personPosts.get(item['id']):
        thisItem = item
        if item.get('object'):
            thisItem = item['object']
        # check that this is a public post
        # #Public should appear in the "to" list
        itemIsNote = False
        if item['type'] == 'Note' or item['type'] == 'Page':
            itemIsNote = True

        if isinstance(thisItem, dict):
            if thisItem.get('to'):
                isPublic = False
                for recipient in thisItem['to']:
                    if recipient.endswith('#Public'):
                        isPublic = True
                        break
                if not isPublic:
                    return False
        elif isinstance(thisItem, str) or itemIsNote:
            if item.get('to'):
                isPublic = False
                for recipient in item['to']:
                    if recipient.endswith('#Public'):
                        isPublic = True
                        break
                if not isPublic:
                    return False
    return True


def isCreateInsideAnnounce(item: {}) -> bool:
    """ is this a Create inside of an Announce?
    eg. lemmy feed item
    """
    if not isinstance(item, dict):
        return False
    if item['type'] != 'Announce':
        return False
    if not item.get('object'):
        return False
    if not isinstance(item['object'], dict):
        return False
    if not item['object'].get('type'):
        return False
    if item['object']['type'] != 'Create':
        return False
    return True


def _getPosts(session, outboxUrl: str, maxPosts: int,
              max_mentions: int,
              max_emoji: int, maxAttachments: int,
              federationList: [],
              personCache: {}, raw: bool,
              simple: bool, debug: bool,
              project_version: str, http_prefix: str,
              originDomain: str, systemLanguage: str,
              signingPrivateKeyPem: str) -> {}:
    """Gets public posts from an outbox
    """
    if debug:
        print('Getting outbox posts for ' + outboxUrl)
    personPosts = {}
    if not outboxUrl:
        return personPosts
    profileStr = 'https://www.w3.org/ns/activitystreams'
    acceptStr = \
        'application/activity+json; ' + \
        'profile="' + profileStr + '"'
    asHeader = {
        'Accept': acceptStr
    }
    if '/outbox/' in outboxUrl:
        acceptStr = \
            'application/ld+json; ' + \
            'profile="' + profileStr + '"'
        asHeader = {
            'Accept': acceptStr
        }
    if raw:
        if debug:
            print('Returning the raw feed')
        result = []
        i = 0
        userFeed = parseUserFeed(signingPrivateKeyPem,
                                 session, outboxUrl, asHeader,
                                 project_version, http_prefix,
                                 originDomain, debug)
        for item in userFeed:
            result.append(item)
            i += 1
            if i == maxPosts:
                break
        pprint(result)
        return None

    if debug:
        print('Returning a human readable version of the feed')
    userFeed = parseUserFeed(signingPrivateKeyPem,
                             session, outboxUrl, asHeader,
                             project_version, http_prefix,
                             originDomain, debug)
    if not userFeed:
        return personPosts

    i = 0
    for item in userFeed:
        if isCreateInsideAnnounce(item):
            item = item['object']

        if not _isPublicFeedPost(item, personPosts, debug):
            continue

        thisItem = item
        if item['type'] != 'Note' and item['type'] != 'Page':
            thisItem = item['object']

        content = getBaseContentFromPost(item, systemLanguage)
        content = content.replace('&apos;', "'")

        mentions = []
        emoji = {}
        summary = ''
        inReplyTo = ''
        attachment = []
        sensitive = False
        if isinstance(thisItem, dict):
            if thisItem.get('tag'):
                for tagItem in thisItem['tag']:
                    if not tagItem.get('type'):
                        continue
                    tagType = tagItem['type'].lower()
                    if tagType == 'emoji':
                        if tagItem.get('name') and tagItem.get('icon'):
                            if tagItem['icon'].get('url'):
                                # No emoji from non-permitted domains
                                if urlPermitted(tagItem['icon']['url'],
                                                federationList):
                                    emojiName = tagItem['name']
                                    emojiIcon = tagItem['icon']['url']
                                    emoji[emojiName] = emojiIcon
                                else:
                                    if debug:
                                        print('url not permitted ' +
                                              tagItem['icon']['url'])
                    if tagType == 'mention':
                        if tagItem.get('name'):
                            if tagItem['name'] not in mentions:
                                mentions.append(tagItem['name'])
            if len(mentions) > max_mentions:
                if debug:
                    print('max mentions reached')
                continue
            if len(emoji) > max_emoji:
                if debug:
                    print('max emojis reached')
                continue

            if thisItem.get('summary'):
                if thisItem['summary']:
                    summary = thisItem['summary']

            if thisItem.get('inReplyTo'):
                if thisItem['inReplyTo']:
                    if isinstance(thisItem['inReplyTo'], str):
                        # No replies to non-permitted domains
                        if not urlPermitted(thisItem['inReplyTo'],
                                            federationList):
                            if debug:
                                print('url not permitted ' +
                                      thisItem['inReplyTo'])
                            continue
                        inReplyTo = thisItem['inReplyTo']

            if thisItem.get('attachment'):
                if thisItem['attachment']:
                    for attach in thisItem['attachment']:
                        if attach.get('name') and attach.get('url'):
                            # no attachments from non-permitted domains
                            if urlPermitted(attach['url'],
                                            federationList):
                                attachment.append([attach['name'],
                                                   attach['url']])
                            else:
                                if debug:
                                    print('url not permitted ' +
                                          attach['url'])

            sensitive = False
            if thisItem.get('sensitive'):
                sensitive = thisItem['sensitive']

        if content:
            if simple:
                print(_cleanHtml(content) + '\n')
            else:
                pprint(item)
                personPosts[item['id']] = {
                    "sensitive": sensitive,
                    "inreplyto": inReplyTo,
                    "summary": summary,
                    "html": content,
                    "plaintext": _cleanHtml(content),
                    "attachment": attachment,
                    "mentions": mentions,
                    "emoji": emoji
                }
            i += 1

            if i == maxPosts:
                break
    return personPosts


def _getCommonWords() -> str:
    """Returns a list of common words
    """
    return (
        'that', 'some', 'about', 'then', 'they', 'were',
        'also', 'from', 'with', 'this', 'have', 'more',
        'need', 'here', 'would', 'these', 'into', 'very',
        'well', 'when', 'what', 'your', 'there', 'which',
        'even', 'there', 'such', 'just', 'those', 'only',
        'will', 'much', 'than', 'them', 'each', 'goes',
        'been', 'over', 'their', 'where', 'could', 'though',
        'like', 'think', 'same', 'maybe', 'really', 'thing',
        'something', 'possible', 'actual', 'actually',
        'because', 'around', 'having', 'especially', 'other',
        'making', 'made', 'make', 'makes', 'including',
        'includes', 'know', 'knowing', 'knows', 'things',
        'say', 'says', 'saying', 'many', 'somewhat',
        'problem', 'problems', 'idea', 'ideas',
        'using', 'uses', 'https', 'still', 'want', 'wants'
    )


def _updateWordFrequency(content: str, wordFrequency: {}) -> None:
    """Creates a dictionary containing words and the number of times
    that they appear
    """
    plainText = removeHtml(content)
    removeChars = ('.', ';', '?', '\n', ':')
    for ch in removeChars:
        plainText = plainText.replace(ch, ' ')
    wordsList = plainText.split(' ')
    commonWords = _getCommonWords()
    for word in wordsList:
        wordLen = len(word)
        if wordLen < 3:
            continue
        if wordLen < 4:
            if word.upper() != word:
                continue
        if '&' in word or \
           '"' in word or \
           '@' in word or \
           "'" in word or \
           "--" in word or \
           '//' in word:
            continue
        if word.lower() in commonWords:
            continue
        if wordFrequency.get(word):
            wordFrequency[word] += 1
        else:
            wordFrequency[word] = 1


def getPostDomains(session, outboxUrl: str, maxPosts: int,
                   max_mentions: int,
                   max_emoji: int, maxAttachments: int,
                   federationList: [],
                   personCache: {},
                   debug: bool,
                   project_version: str, http_prefix: str,
                   domain: str,
                   wordFrequency: {},
                   domainList: [], systemLanguage: str,
                   signingPrivateKeyPem: str) -> []:
    """Returns a list of domains referenced within public posts
    """
    if not outboxUrl:
        return []
    profileStr = 'https://www.w3.org/ns/activitystreams'
    acceptStr = \
        'application/activity+json; ' + \
        'profile="' + profileStr + '"'
    asHeader = {
        'Accept': acceptStr
    }
    if '/outbox/' in outboxUrl:
        acceptStr = \
            'application/ld+json; ' + \
            'profile="' + profileStr + '"'
        asHeader = {
            'Accept': acceptStr
        }

    postDomains = domainList

    i = 0
    userFeed = parseUserFeed(signingPrivateKeyPem,
                             session, outboxUrl, asHeader,
                             project_version, http_prefix, domain, debug)
    for item in userFeed:
        i += 1
        if i > maxPosts:
            break
        if not hasObjectDict(item):
            continue
        contentStr = getBaseContentFromPost(item, systemLanguage)
        if contentStr:
            _updateWordFrequency(contentStr, wordFrequency)
        if item['object'].get('inReplyTo'):
            if isinstance(item['object']['inReplyTo'], str):
                postDomain, postPort = \
                    getDomainFromActor(item['object']['inReplyTo'])
                if postDomain not in postDomains:
                    postDomains.append(postDomain)

        if item['object'].get('tag'):
            for tagItem in item['object']['tag']:
                if not tagItem.get('type'):
                    continue
                tagType = tagItem['type'].lower()
                if tagType == 'mention':
                    if tagItem.get('href'):
                        postDomain, postPort = \
                            getDomainFromActor(tagItem['href'])
                        if postDomain not in postDomains:
                            postDomains.append(postDomain)
    return postDomains


def _getPostsForBlockedDomains(base_dir: str,
                               session, outboxUrl: str, maxPosts: int,
                               max_mentions: int,
                               max_emoji: int, maxAttachments: int,
                               federationList: [],
                               personCache: {},
                               debug: bool,
                               project_version: str, http_prefix: str,
                               domain: str,
                               signingPrivateKeyPem: str) -> {}:
    """Returns a dictionary of posts for blocked domains
    """
    if not outboxUrl:
        return {}
    profileStr = 'https://www.w3.org/ns/activitystreams'
    acceptStr = \
        'application/activity+json; ' + \
        'profile="' + profileStr + '"'
    asHeader = {
        'Accept': acceptStr
    }
    if '/outbox/' in outboxUrl:
        acceptStr = \
            'application/ld+json; ' + \
            'profile="' + profileStr + '"'
        asHeader = {
            'Accept': acceptStr
        }

    blockedPosts = {}

    i = 0
    userFeed = parseUserFeed(signingPrivateKeyPem,
                             session, outboxUrl, asHeader,
                             project_version, http_prefix, domain, debug)
    for item in userFeed:
        i += 1
        if i > maxPosts:
            break
        if not hasObjectDict(item):
            continue
        if item['object'].get('inReplyTo'):
            if isinstance(item['object']['inReplyTo'], str):
                postDomain, postPort = \
                    getDomainFromActor(item['object']['inReplyTo'])
                if isBlockedDomain(base_dir, postDomain):
                    if item['object'].get('url'):
                        url = item['object']['url']
                    else:
                        url = item['object']['id']
                    if not blockedPosts.get(postDomain):
                        blockedPosts[postDomain] = [url]
                    else:
                        if url not in blockedPosts[postDomain]:
                            blockedPosts[postDomain].append(url)

        if item['object'].get('tag'):
            for tagItem in item['object']['tag']:
                if not tagItem.get('type'):
                    continue
                tagType = tagItem['type'].lower()
                if tagType == 'mention' and tagItem.get('href'):
                    postDomain, postPort = \
                        getDomainFromActor(tagItem['href'])
                    if isBlockedDomain(base_dir, postDomain):
                        if item['object'].get('url'):
                            url = item['object']['url']
                        else:
                            url = item['object']['id']
                        if not blockedPosts.get(postDomain):
                            blockedPosts[postDomain] = [url]
                        else:
                            if url not in blockedPosts[postDomain]:
                                blockedPosts[postDomain].append(url)
    return blockedPosts


def deleteAllPosts(base_dir: str,
                   nickname: str, domain: str, boxname: str) -> None:
    """Deletes all posts for a person from inbox or outbox
    """
    if boxname != 'inbox' and boxname != 'outbox' and \
       boxname != 'tlblogs' and boxname != 'tlnews':
        return
    boxDir = createPersonDir(nickname, domain, base_dir, boxname)
    for deleteFilename in os.scandir(boxDir):
        deleteFilename = deleteFilename.name
        filePath = os.path.join(boxDir, deleteFilename)
        try:
            if os.path.isfile(filePath):
                os.unlink(filePath)
            elif os.path.isdir(filePath):
                shutil.rmtree(filePath, ignore_errors=False, onerror=None)
        except Exception as ex:
            print('ERROR: deleteAllPosts ' + str(ex))


def savePostToBox(base_dir: str, http_prefix: str, postId: str,
                  nickname: str, domain: str, postJsonObject: {},
                  boxname: str) -> str:
    """Saves the give json to the give box
    Returns the filename
    """
    if boxname != 'inbox' and boxname != 'outbox' and \
       boxname != 'tlblogs' and boxname != 'tlnews' and \
       boxname != 'scheduled':
        return None
    originalDomain = domain
    domain = removeDomainPort(domain)

    if not postId:
        statusNumber, published = getStatusNumber()
        postId = \
            localActorUrl(http_prefix, nickname, originalDomain) + \
            '/statuses/' + statusNumber
        postJsonObject['id'] = postId + '/activity'
    if hasObjectDict(postJsonObject):
        postJsonObject['object']['id'] = postId
        postJsonObject['object']['atomUri'] = postId

    boxDir = createPersonDir(nickname, domain, base_dir, boxname)
    filename = boxDir + '/' + postId.replace('/', '#') + '.json'

    saveJson(postJsonObject, filename)
    return filename


def _updateHashtagsIndex(base_dir: str, tag: {}, newPostId: str) -> None:
    """Writes the post url for hashtags to a file
    This allows posts for a hashtag to be quickly looked up
    """
    if tag['type'] != 'Hashtag':
        return

    # create hashtags directory
    tagsDir = base_dir + '/tags'
    if not os.path.isdir(tagsDir):
        os.mkdir(tagsDir)
    tagName = tag['name']
    tagsFilename = tagsDir + '/' + tagName[1:] + '.txt'
    tagline = newPostId + '\n'

    if not os.path.isfile(tagsFilename):
        # create a new tags index file
        with open(tagsFilename, 'w+') as tagsFile:
            tagsFile.write(tagline)
    else:
        # prepend to tags index file
        if tagline not in open(tagsFilename).read():
            try:
                with open(tagsFilename, 'r+') as tagsFile:
                    content = tagsFile.read()
                    if tagline not in content:
                        tagsFile.seek(0, 0)
                        tagsFile.write(tagline + content)
            except Exception as ex:
                print('WARN: Failed to write entry to tags file ' +
                      tagsFilename + ' ' + str(ex))


def _addSchedulePost(base_dir: str, nickname: str, domain: str,
                     eventDateStr: str, postId: str) -> None:
    """Adds a scheduled post to the index
    """
    handle = nickname + '@' + domain
    scheduleIndexFilename = \
        base_dir + '/accounts/' + handle + '/schedule.index'

    indexStr = eventDateStr + ' ' + postId.replace('/', '#')
    if os.path.isfile(scheduleIndexFilename):
        if indexStr not in open(scheduleIndexFilename).read():
            try:
                with open(scheduleIndexFilename, 'r+') as scheduleFile:
                    content = scheduleFile.read()
                    if indexStr + '\n' not in content:
                        scheduleFile.seek(0, 0)
                        scheduleFile.write(indexStr + '\n' + content)
                        print('DEBUG: scheduled post added to index')
            except Exception as ex:
                print('WARN: Failed to write entry to scheduled posts index ' +
                      scheduleIndexFilename + ' ' + str(ex))
    else:
        with open(scheduleIndexFilename, 'w+') as scheduleFile:
            scheduleFile.write(indexStr + '\n')


def validContentWarning(cw: str) -> str:
    """Returns a validated content warning
    """
    cw = removeHtml(cw)
    # hashtags within content warnings apparently cause a lot of trouble
    # so remove them
    if '#' in cw:
        cw = cw.replace('#', '').replace('  ', ' ')
    return removeInvalidChars(cw)


def _loadAutoCW(base_dir: str, nickname: str, domain: str) -> []:
    """Loads automatic CWs file and returns a list containing
    the lines of the file
    """
    filename = acctDir(base_dir, nickname, domain) + '/autocw.txt'
    if not os.path.isfile(filename):
        return []
    with open(filename, 'r') as f:
        return f.readlines()
    return []


def _addAutoCW(base_dir: str, nickname: str, domain: str,
               subject: str, content: str) -> str:
    """Appends any automatic CW to the subject line
    and returns the new subject line
    """
    newSubject = subject
    autoCWList = _loadAutoCW(base_dir, nickname, domain)
    for cwRule in autoCWList:
        if '->' not in cwRule:
            continue
        rulematch = cwRule.split('->')[0].strip()
        if rulematch not in content:
            continue
        cwStr = cwRule.split('->')[1].strip()
        if newSubject:
            if cwStr not in newSubject:
                newSubject += ', ' + cwStr
        else:
            newSubject = cwStr
    return newSubject


def _createPostCWFromReply(base_dir: str, nickname: str, domain: str,
                           inReplyTo: str,
                           sensitive: bool, summary: str) -> (bool, str):
    """If this is a reply and the original post has a CW
    then use the same CW
    """
    if inReplyTo and not sensitive:
        # locate the post which this is a reply to and check if
        # it has a content warning. If it does then reproduce
        # the same warning
        replyPostFilename = \
            locatePost(base_dir, nickname, domain, inReplyTo)
        if replyPostFilename:
            replyToJson = loadJson(replyPostFilename)
            if replyToJson:
                if replyToJson.get('object'):
                    if replyToJson['object'].get('sensitive'):
                        if replyToJson['object']['sensitive']:
                            sensitive = True
                            if replyToJson['object'].get('summary'):
                                summary = replyToJson['object']['summary']
    return sensitive, summary


def _createPostS2S(base_dir: str, nickname: str, domain: str, port: int,
                   http_prefix: str, content: str, statusNumber: str,
                   published: str, newPostId: str, postContext: {},
                   toRecipients: [], toCC: [], inReplyTo: str,
                   sensitive: bool, commentsEnabled: bool,
                   tags: [], attachImageFilename: str,
                   mediaType: str, imageDescription: str, city: str,
                   postObjectType: str, summary: str,
                   inReplyToAtomUri: str, systemLanguage: str,
                   conversationId: str, low_bandwidth: bool,
                   content_license_url: str) -> {}:
    """Creates a new server-to-server post
    """
    actorUrl = localActorUrl(http_prefix, nickname, domain)
    idStr = \
        localActorUrl(http_prefix, nickname, domain) + \
        '/statuses/' + statusNumber + '/replies'
    newPostUrl = \
        http_prefix + '://' + domain + '/@' + nickname + '/' + statusNumber
    newPostAttributedTo = \
        localActorUrl(http_prefix, nickname, domain)
    if not conversationId:
        conversationId = newPostId
    newPost = {
        '@context': postContext,
        'id': newPostId + '/activity',
        'type': 'Create',
        'actor': actorUrl,
        'published': published,
        'to': toRecipients,
        'cc': toCC,
        'object': {
            'id': newPostId,
            'conversation': conversationId,
            'type': postObjectType,
            'summary': summary,
            'inReplyTo': inReplyTo,
            'published': published,
            'url': newPostUrl,
            'attributedTo': newPostAttributedTo,
            'to': toRecipients,
            'cc': toCC,
            'sensitive': sensitive,
            'atomUri': newPostId,
            'inReplyToAtomUri': inReplyToAtomUri,
            'commentsEnabled': commentsEnabled,
            'rejectReplies': not commentsEnabled,
            'mediaType': 'text/html',
            'content': content,
            'contentMap': {
                systemLanguage: content
            },
            'attachment': [],
            'tag': tags,
            'replies': {
                'id': idStr,
                'type': 'Collection',
                'first': {
                    'type': 'CollectionPage',
                    'next': idStr + '?only_other_accounts=true&page=true',
                    'partOf': idStr,
                    'items': []
                }
            }
        }
    }
    if attachImageFilename:
        newPost['object'] = \
            attachMedia(base_dir, http_prefix, nickname, domain, port,
                        newPost['object'], attachImageFilename,
                        mediaType, imageDescription, city, low_bandwidth,
                        content_license_url)
    return newPost


def _createPostC2S(base_dir: str, nickname: str, domain: str, port: int,
                   http_prefix: str, content: str, statusNumber: str,
                   published: str, newPostId: str, postContext: {},
                   toRecipients: [], toCC: [], inReplyTo: str,
                   sensitive: bool, commentsEnabled: bool,
                   tags: [], attachImageFilename: str,
                   mediaType: str, imageDescription: str, city: str,
                   postObjectType: str, summary: str,
                   inReplyToAtomUri: str, systemLanguage: str,
                   conversationId: str, low_bandwidth: str,
                   content_license_url: str) -> {}:
    """Creates a new client-to-server post
    """
    domainFull = getFullDomain(domain, port)
    idStr = \
        localActorUrl(http_prefix, nickname, domainFull) + \
        '/statuses/' + statusNumber + '/replies'
    newPostUrl = \
        http_prefix + '://' + domain + '/@' + nickname + '/' + statusNumber
    if not conversationId:
        conversationId = newPostId
    newPost = {
        "@context": postContext,
        'id': newPostId,
        'conversation': conversationId,
        'type': postObjectType,
        'summary': summary,
        'inReplyTo': inReplyTo,
        'published': published,
        'url': newPostUrl,
        'attributedTo': localActorUrl(http_prefix, nickname, domainFull),
        'to': toRecipients,
        'cc': toCC,
        'sensitive': sensitive,
        'atomUri': newPostId,
        'inReplyToAtomUri': inReplyToAtomUri,
        'commentsEnabled': commentsEnabled,
        'rejectReplies': not commentsEnabled,
        'mediaType': 'text/html',
        'content': content,
        'contentMap': {
            systemLanguage: content
        },
        'attachment': [],
        'tag': tags,
        'replies': {
            'id': idStr,
            'type': 'Collection',
            'first': {
                'type': 'CollectionPage',
                'next': idStr + '?only_other_accounts=true&page=true',
                'partOf': idStr,
                'items': []
            }
        }
    }
    if attachImageFilename:
        newPost = \
            attachMedia(base_dir, http_prefix, nickname, domain, port,
                        newPost, attachImageFilename,
                        mediaType, imageDescription, city, low_bandwidth,
                        content_license_url)
    return newPost


def _createPostPlaceAndTime(eventDate: str, endDate: str,
                            eventTime: str, endTime: str,
                            summary: str, content: str,
                            schedulePost: bool,
                            eventUUID: str,
                            location: str,
                            tags: []) -> str:
    """Adds a place and time to the tags on a new post
    """
    endDateStr = None
    if endDate:
        eventName = summary
        if not eventName:
            eventName = content
        endDateStr = endDate
        if endTime:
            if endTime.endswith('Z'):
                endDateStr = endDate + 'T' + endTime
            else:
                endDateStr = endDate + 'T' + endTime + \
                    ':00' + strftime("%z", gmtime())
        else:
            endDateStr = endDate + 'T12:00:00Z'

    # get the starting date and time
    eventDateStr = None
    if eventDate:
        eventName = summary
        if not eventName:
            eventName = content
        eventDateStr = eventDate
        if eventTime:
            if eventTime.endswith('Z'):
                eventDateStr = eventDate + 'T' + eventTime
            else:
                eventDateStr = eventDate + 'T' + eventTime + \
                    ':00' + strftime("%z", gmtime())
        else:
            eventDateStr = eventDate + 'T12:00:00Z'
        if not endDateStr:
            endDateStr = eventDateStr
        if not schedulePost and not eventUUID:
            tags.append({
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "Event",
                "name": eventName,
                "startTime": eventDateStr,
                "endTime": endDateStr
            })
    if location and not eventUUID:
        tags.append({
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Place",
            "name": location
        })
    return eventDateStr


def _consolidateActorsList(actorsList: []) -> None:
    """ consolidate duplicated actors
    https://domain/@nick gets merged with https://domain/users/nick
    """
    possibleDuplicateActors = []
    for ccActor in actorsList:
        if '/@' in ccActor:
            if ccActor not in possibleDuplicateActors:
                possibleDuplicateActors.append(ccActor)
    if possibleDuplicateActors:
        uPaths = getUserPaths()
        removeActors = []
        for ccActor in possibleDuplicateActors:
            for usrPath in uPaths:
                ccActorFull = ccActor.replace('/@', usrPath)
                if ccActorFull in actorsList:
                    if ccActor not in removeActors:
                        removeActors.append(ccActor)
                    break
        for ccActor in removeActors:
            actorsList.remove(ccActor)


def _createPostMentions(ccUrl: str, newPost: {},
                        toRecipients: [], tags: []) -> None:
    """Updates mentions for a new post
    """
    if not ccUrl:
        return
    if len(ccUrl) == 0:
        return

    if newPost.get('object'):
        if ccUrl not in newPost['object']['cc']:
            newPost['object']['cc'] = [ccUrl] + newPost['object']['cc']

        # if this is a public post then include any mentions in cc
        toCC = newPost['object']['cc']
        if len(toRecipients) != 1:
            return
        if toRecipients[0].endswith('#Public') and \
           ccUrl.endswith('/followers'):
            for tag in tags:
                if tag['type'] != 'Mention':
                    continue
                if tag['href'] not in toCC:
                    newPost['object']['cc'].append(tag['href'])

        _consolidateActorsList(newPost['object']['cc'])
        newPost['cc'] = newPost['object']['cc']
    else:
        if ccUrl not in newPost['cc']:
            newPost['cc'] = [ccUrl] + newPost['cc']
        _consolidateActorsList(['cc'])


def _createPostModReport(base_dir: str,
                         isModerationReport: bool, newPost: {},
                         newPostId: str) -> None:
    """ if this is a moderation report then add a status
    """
    if not isModerationReport:
        return
    # add status
    if newPost.get('object'):
        newPost['object']['moderationStatus'] = 'pending'
    else:
        newPost['moderationStatus'] = 'pending'
    # save to index file
    moderationIndexFile = base_dir + '/accounts/moderation.txt'
    with open(moderationIndexFile, 'a+') as modFile:
        modFile.write(newPostId + '\n')


def getActorFromInReplyTo(inReplyTo: str) -> str:
    """Tries to get the replied to actor from the inReplyTo post id
    Note: this will not always be successful for some instance types
    """
    replyNickname = getNicknameFromActor(inReplyTo)
    if not replyNickname:
        return None
    replyActor = None
    if '/' + replyNickname + '/' in inReplyTo:
        replyActor = \
            inReplyTo.split('/' + replyNickname + '/')[0] + \
            '/' + replyNickname
    elif '#' + replyNickname + '#' in inReplyTo:
        replyActor = \
            inReplyTo.split('#' + replyNickname + '#')[0] + \
            '#' + replyNickname
        replyActor = replyActor.replace('#', '/')
    if not replyActor:
        return None
    if '://' not in replyActor:
        return None
    return replyActor


def _createPostBase(base_dir: str,
                    nickname: str, domain: str, port: int,
                    toUrl: str, ccUrl: str, http_prefix: str, content: str,
                    followersOnly: bool, saveToFile: bool,
                    client_to_server: bool, commentsEnabled: bool,
                    attachImageFilename: str,
                    mediaType: str, imageDescription: str, city: str,
                    isModerationReport: bool,
                    isArticle: bool,
                    inReplyTo: str,
                    inReplyToAtomUri: str,
                    subject: str, schedulePost: bool,
                    eventDate: str, eventTime: str,
                    location: str,
                    eventUUID: str, category: str,
                    joinMode: str,
                    endDate: str, endTime: str,
                    maximumAttendeeCapacity: int,
                    repliesModerationOption: str,
                    anonymousParticipationEnabled: bool,
                    eventStatus: str, ticketUrl: str,
                    systemLanguage: str,
                    conversationId: str, low_bandwidth: bool,
                    content_license_url: str) -> {}:
    """Creates a message
    """
    content = removeInvalidChars(content)

    subject = _addAutoCW(base_dir, nickname, domain, subject, content)

    if nickname != 'news':
        mentionedRecipients = \
            getMentionedPeople(base_dir, http_prefix, content, domain, False)
    else:
        mentionedRecipients = ''

    tags = []
    hashtagsDict = {}

    domain = getFullDomain(domain, port)

    # add tags
    if nickname != 'news':
        content = \
            addHtmlTags(base_dir, http_prefix,
                        nickname, domain, content,
                        mentionedRecipients,
                        hashtagsDict, True)

    # replace emoji with unicode
    tags = []
    for tagName, tag in hashtagsDict.items():
        tags.append(tag)

    # get list of tags
    if nickname != 'news':
        content = \
            replaceEmojiFromTags(None, base_dir, content, tags, 'content',
                                 False)
    # remove replaced emoji
    hashtagsDictCopy = hashtagsDict.copy()
    for tagName, tag in hashtagsDictCopy.items():
        if tag.get('name'):
            if tag['name'].startswith(':'):
                if tag['name'] not in content:
                    del hashtagsDict[tagName]

    statusNumber, published = getStatusNumber()
    newPostId = \
        localActorUrl(http_prefix, nickname, domain) + \
        '/statuses/' + statusNumber

    sensitive = False
    summary = None
    if subject:
        summary = removeInvalidChars(validContentWarning(subject))
        sensitive = True

    toRecipients = []
    toCC = []
    if toUrl:
        if not isinstance(toUrl, str):
            print('ERROR: toUrl is not a string')
            return None
        toRecipients = [toUrl]

    # who to send to
    if mentionedRecipients:
        for mention in mentionedRecipients:
            if mention not in toCC:
                toCC.append(mention)

    isPublic = False
    for recipient in toRecipients:
        if recipient.endswith('#Public'):
            isPublic = True
            break

    # create a list of hashtags
    # Only posts which are #Public are searchable by hashtag
    if hashtagsDict:
        for tagName, tag in hashtagsDict.items():
            if not tagExists(tag['type'], tag['name'], tags):
                tags.append(tag)
            if isPublic:
                _updateHashtagsIndex(base_dir, tag, newPostId)
        # print('Content tags: ' + str(tags))

    sensitive, summary = \
        _createPostCWFromReply(base_dir, nickname, domain,
                               inReplyTo, sensitive, summary)

    eventDateStr = \
        _createPostPlaceAndTime(eventDate, endDate,
                                eventTime, endTime,
                                summary, content, schedulePost,
                                eventUUID, location, tags)

    postContext = getIndividualPostContext()

    if not isPublic:
        # make sure that CC doesn't also contain a To address
        # eg. To: [ "https://mydomain/users/foo/followers" ]
        #     CC: [ "X", "Y", "https://mydomain/users/foo", "Z" ]
        removeFromCC = []
        for ccRecipient in toCC:
            for sendToActor in toRecipients:
                if ccRecipient in sendToActor and \
                   ccRecipient not in removeFromCC:
                    removeFromCC.append(ccRecipient)
                    break
        for ccRemoval in removeFromCC:
            toCC.remove(ccRemoval)
    else:
        if inReplyTo:
            # If this is a public post then get the actor being
            # replied to end ensure that it is within the CC list
            replyActor = getActorFromInReplyTo(inReplyTo)
            if replyActor:
                if replyActor not in toCC:
                    toCC.append(replyActor)

    # the type of post to be made
    postObjectType = 'Note'
    if isArticle:
        postObjectType = 'Article'

    if not client_to_server:
        newPost = \
            _createPostS2S(base_dir, nickname, domain, port,
                           http_prefix, content, statusNumber,
                           published, newPostId, postContext,
                           toRecipients, toCC, inReplyTo,
                           sensitive, commentsEnabled,
                           tags, attachImageFilename,
                           mediaType, imageDescription, city,
                           postObjectType, summary,
                           inReplyToAtomUri, systemLanguage,
                           conversationId, low_bandwidth,
                           content_license_url)
    else:
        newPost = \
            _createPostC2S(base_dir, nickname, domain, port,
                           http_prefix, content, statusNumber,
                           published, newPostId, postContext,
                           toRecipients, toCC, inReplyTo,
                           sensitive, commentsEnabled,
                           tags, attachImageFilename,
                           mediaType, imageDescription, city,
                           postObjectType, summary,
                           inReplyToAtomUri, systemLanguage,
                           conversationId, low_bandwidth,
                           content_license_url)

    _createPostMentions(ccUrl, newPost, toRecipients, tags)

    _createPostModReport(base_dir, isModerationReport, newPost, newPostId)

    # If a patch has been posted - i.e. the output from
    # git format-patch - then convert the activitypub type
    convertPostToPatch(base_dir, nickname, domain, newPost)

    if schedulePost:
        if eventDate and eventTime:
            # add an item to the scheduled post index file
            _addSchedulePost(base_dir, nickname, domain,
                             eventDateStr, newPostId)
            savePostToBox(base_dir, http_prefix, newPostId,
                          nickname, domain, newPost, 'scheduled')
        else:
            print('Unable to create scheduled post without ' +
                  'date and time values')
            return newPost
    elif saveToFile:
        if isArticle:
            savePostToBox(base_dir, http_prefix, newPostId,
                          nickname, domain, newPost, 'tlblogs')
        else:
            savePostToBox(base_dir, http_prefix, newPostId,
                          nickname, domain, newPost, 'outbox')
    return newPost


def outboxMessageCreateWrap(http_prefix: str,
                            nickname: str, domain: str, port: int,
                            messageJson: {}) -> {}:
    """Wraps a received message in a Create
    https://www.w3.org/TR/activitypub/#object-without-create
    """

    domain = getFullDomain(domain, port)
    statusNumber, published = getStatusNumber()
    if messageJson.get('published'):
        published = messageJson['published']
    newPostId = \
        localActorUrl(http_prefix, nickname, domain) + \
        '/statuses/' + statusNumber
    cc = []
    if messageJson.get('cc'):
        cc = messageJson['cc']
    newPost = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'id': newPostId + '/activity',
        'type': 'Create',
        'actor': localActorUrl(http_prefix, nickname, domain),
        'published': published,
        'to': messageJson['to'],
        'cc': cc,
        'object': messageJson
    }
    newPost['object']['id'] = newPost['id']
    newPost['object']['url'] = \
        http_prefix + '://' + domain + '/@' + nickname + '/' + statusNumber
    newPost['object']['atomUri'] = \
        localActorUrl(http_prefix, nickname, domain) + \
        '/statuses/' + statusNumber
    return newPost


def _postIsAddressedToFollowers(base_dir: str,
                                nickname: str, domain: str, port: int,
                                http_prefix: str,
                                postJsonObject: {}) -> bool:
    """Returns true if the given post is addressed to followers of the nickname
    """
    domainFull = getFullDomain(domain, port)

    if not postJsonObject.get('object'):
        return False
    toList = []
    ccList = []
    if postJsonObject['type'] != 'Update' and \
       hasObjectDict(postJsonObject):
        if postJsonObject['object'].get('to'):
            toList = postJsonObject['object']['to']
        if postJsonObject['object'].get('cc'):
            ccList = postJsonObject['object']['cc']
    else:
        if postJsonObject.get('to'):
            toList = postJsonObject['to']
        if postJsonObject.get('cc'):
            ccList = postJsonObject['cc']

    followersUrl = \
        localActorUrl(http_prefix, nickname, domainFull) + '/followers'

    # does the followers url exist in 'to' or 'cc' lists?
    addressedToFollowers = False
    if followersUrl in toList:
        addressedToFollowers = True
    elif followersUrl in ccList:
        addressedToFollowers = True
    return addressedToFollowers


def pinPost(base_dir: str, nickname: str, domain: str,
            pinnedContent: str, followersOnly: bool) -> None:
    """Pins the given post Id to the profile of then given account
    """
    accountDir = acctDir(base_dir, nickname, domain)
    pinnedFilename = accountDir + '/pinToProfile.txt'
    try:
        with open(pinnedFilename, 'w+') as pinFile:
            pinFile.write(pinnedContent)
    except OSError:
        print('EX: unable to write ' + pinnedFilename)


def undoPinnedPost(base_dir: str, nickname: str, domain: str) -> None:
    """Removes pinned content for then given account
    """
    accountDir = acctDir(base_dir, nickname, domain)
    pinnedFilename = accountDir + '/pinToProfile.txt'
    if os.path.isfile(pinnedFilename):
        try:
            os.remove(pinnedFilename)
        except OSError:
            print('EX: undoPinnedPost unable to delete ' + pinnedFilename)


def getPinnedPostAsJson(base_dir: str, http_prefix: str,
                        nickname: str, domain: str,
                        domainFull: str, systemLanguage: str) -> {}:
    """Returns the pinned profile post as json
    """
    accountDir = acctDir(base_dir, nickname, domain)
    pinnedFilename = accountDir + '/pinToProfile.txt'
    pinnedPostJson = {}
    actor = localActorUrl(http_prefix, nickname, domainFull)
    if os.path.isfile(pinnedFilename):
        pinnedContent = None
        with open(pinnedFilename, 'r') as pinFile:
            pinnedContent = pinFile.read()
        if pinnedContent:
            pinnedPostJson = {
                'atomUri': actor + '/pinned',
                'attachment': [],
                'attributedTo': actor,
                'cc': [
                    actor + '/followers'
                ],
                'content': pinnedContent,
                'contentMap': {
                    systemLanguage: pinnedContent
                },
                'id': actor + '/pinned',
                'inReplyTo': None,
                'inReplyToAtomUri': None,
                'published': fileLastModified(pinnedFilename),
                'replies': {},
                'sensitive': False,
                'summary': None,
                'tag': [],
                'to': ['https://www.w3.org/ns/activitystreams#Public'],
                'type': 'Note',
                'url': replaceUsersWithAt(actor) + '/pinned'
            }
    return pinnedPostJson


def jsonPinPost(base_dir: str, http_prefix: str,
                nickname: str, domain: str,
                domainFull: str, systemLanguage: str) -> {}:
    """Returns a pinned post as json
    """
    pinnedPostJson = \
        getPinnedPostAsJson(base_dir, http_prefix,
                            nickname, domain,
                            domainFull, systemLanguage)
    itemsList = []
    if pinnedPostJson:
        itemsList = [pinnedPostJson]

    actor = localActorUrl(http_prefix, nickname, domainFull)
    postContext = getIndividualPostContext()
    return {
        '@context': postContext,
        'id': actor + '/collections/featured',
        'orderedItems': itemsList,
        'totalItems': len(itemsList),
        'type': 'OrderedCollection'
    }


def regenerateIndexForBox(base_dir: str,
                          nickname: str, domain: str, boxName: str) -> None:
    """Generates an index for the given box if it doesn't exist
    Used by unit tests to artificially create an index
    """
    boxDir = acctDir(base_dir, nickname, domain) + '/' + boxName
    boxIndexFilename = boxDir + '.index'

    if not os.path.isdir(boxDir):
        return
    if os.path.isfile(boxIndexFilename):
        return

    indexLines = []
    for subdir, dirs, files in os.walk(boxDir):
        for f in files:
            if ':##' not in f:
                continue
            indexLines.append(f)
        break

    indexLines.sort(reverse=True)

    result = ''
    with open(boxIndexFilename, 'w+') as fp:
        for line in indexLines:
            result += line + '\n'
            fp.write(line + '\n')
    print('Index generated for ' + boxName + '\n' + result)


def createPublicPost(base_dir: str,
                     nickname: str, domain: str, port: int, http_prefix: str,
                     content: str, followersOnly: bool, saveToFile: bool,
                     client_to_server: bool, commentsEnabled: bool,
                     attachImageFilename: str, mediaType: str,
                     imageDescription: str, city: str,
                     inReplyTo: str,
                     inReplyToAtomUri: str, subject: str,
                     schedulePost: bool,
                     eventDate: str, eventTime: str,
                     location: str,
                     isArticle: bool,
                     systemLanguage: str,
                     conversationId: str, low_bandwidth: bool,
                     content_license_url: str) -> {}:
    """Public post
    """
    domainFull = getFullDomain(domain, port)
    isModerationReport = False
    eventUUID = None
    category = None
    joinMode = None
    endDate = None
    endTime = None
    maximumAttendeeCapacity = None
    repliesModerationOption = None
    anonymousParticipationEnabled = None
    eventStatus = None
    ticketUrl = None
    localActor = localActorUrl(http_prefix, nickname, domainFull)
    return _createPostBase(base_dir, nickname, domain, port,
                           'https://www.w3.org/ns/activitystreams#Public',
                           localActor + '/followers',
                           http_prefix, content, followersOnly, saveToFile,
                           client_to_server, commentsEnabled,
                           attachImageFilename, mediaType,
                           imageDescription, city,
                           isModerationReport, isArticle,
                           inReplyTo, inReplyToAtomUri, subject,
                           schedulePost, eventDate, eventTime, location,
                           eventUUID, category, joinMode, endDate, endTime,
                           maximumAttendeeCapacity,
                           repliesModerationOption,
                           anonymousParticipationEnabled,
                           eventStatus, ticketUrl, systemLanguage,
                           conversationId, low_bandwidth,
                           content_license_url)


def _appendCitationsToBlogPost(base_dir: str,
                               nickname: str, domain: str,
                               blogJson: {}) -> None:
    """Appends any citations to a new blog post
    """
    # append citations tags, stored in a file
    citationsFilename = \
        acctDir(base_dir, nickname, domain) + '/.citations.txt'
    if not os.path.isfile(citationsFilename):
        return
    citationsSeparator = '#####'
    with open(citationsFilename, 'r') as f:
        citations = f.readlines()
        for line in citations:
            if citationsSeparator not in line:
                continue
            sections = line.strip().split(citationsSeparator)
            if len(sections) != 3:
                continue
            # dateStr = sections[0]
            title = sections[1]
            link = sections[2]
            tagJson = {
                "type": "Article",
                "name": title,
                "url": link
            }
            blogJson['object']['tag'].append(tagJson)


def createBlogPost(base_dir: str,
                   nickname: str, domain: str, port: int, http_prefix: str,
                   content: str, followersOnly: bool, saveToFile: bool,
                   client_to_server: bool, commentsEnabled: bool,
                   attachImageFilename: str, mediaType: str,
                   imageDescription: str, city: str,
                   inReplyTo: str, inReplyToAtomUri: str,
                   subject: str, schedulePost: bool,
                   eventDate: str, eventTime: str,
                   location: str, systemLanguage: str,
                   conversationId: str, low_bandwidth: bool,
                   content_license_url: str) -> {}:
    blogJson = \
        createPublicPost(base_dir,
                         nickname, domain, port, http_prefix,
                         content, followersOnly, saveToFile,
                         client_to_server, commentsEnabled,
                         attachImageFilename, mediaType,
                         imageDescription, city,
                         inReplyTo, inReplyToAtomUri, subject,
                         schedulePost,
                         eventDate, eventTime, location,
                         True, systemLanguage, conversationId,
                         low_bandwidth, content_license_url)
    blogJson['object']['url'] = \
        blogJson['object']['url'].replace('/@', '/users/')
    _appendCitationsToBlogPost(base_dir, nickname, domain, blogJson)

    return blogJson


def createNewsPost(base_dir: str,
                   domain: str, port: int, http_prefix: str,
                   content: str, followersOnly: bool, saveToFile: bool,
                   attachImageFilename: str, mediaType: str,
                   imageDescription: str, city: str,
                   subject: str, systemLanguage: str,
                   conversationId: str, low_bandwidth: bool,
                   content_license_url: str) -> {}:
    client_to_server = False
    inReplyTo = None
    inReplyToAtomUri = None
    schedulePost = False
    eventDate = None
    eventTime = None
    location = None
    blog = \
        createPublicPost(base_dir,
                         'news', domain, port, http_prefix,
                         content, followersOnly, saveToFile,
                         client_to_server, False,
                         attachImageFilename, mediaType,
                         imageDescription, city,
                         inReplyTo, inReplyToAtomUri, subject,
                         schedulePost,
                         eventDate, eventTime, location,
                         True, systemLanguage, conversationId,
                         low_bandwidth, content_license_url)
    blog['object']['type'] = 'Article'
    return blog


def createQuestionPost(base_dir: str,
                       nickname: str, domain: str, port: int, http_prefix: str,
                       content: str, qOptions: [],
                       followersOnly: bool, saveToFile: bool,
                       client_to_server: bool, commentsEnabled: bool,
                       attachImageFilename: str, mediaType: str,
                       imageDescription: str, city: str,
                       subject: str, durationDays: int,
                       systemLanguage: str, low_bandwidth: bool,
                       content_license_url: str) -> {}:
    """Question post with multiple choice options
    """
    domainFull = getFullDomain(domain, port)
    localActor = localActorUrl(http_prefix, nickname, domainFull)
    messageJson = \
        _createPostBase(base_dir, nickname, domain, port,
                        'https://www.w3.org/ns/activitystreams#Public',
                        localActor + '/followers',
                        http_prefix, content, followersOnly, saveToFile,
                        client_to_server, commentsEnabled,
                        attachImageFilename, mediaType,
                        imageDescription, city,
                        False, False, None, None, subject,
                        False, None, None, None, None, None,
                        None, None, None,
                        None, None, None, None, None, systemLanguage,
                        None, low_bandwidth, content_license_url)
    messageJson['object']['type'] = 'Question'
    messageJson['object']['oneOf'] = []
    messageJson['object']['votersCount'] = 0
    currTime = datetime.datetime.utcnow()
    daysSinceEpoch = \
        int((currTime - datetime.datetime(1970, 1, 1)).days + durationDays)
    endTime = datetime.datetime(1970, 1, 1) + \
        datetime.timedelta(daysSinceEpoch)
    messageJson['object']['endTime'] = endTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    for questionOption in qOptions:
        messageJson['object']['oneOf'].append({
            "type": "Note",
            "name": questionOption,
            "replies": {
                "type": "Collection",
                "totalItems": 0
            }
        })
    return messageJson


def createUnlistedPost(base_dir: str,
                       nickname: str, domain: str, port: int, http_prefix: str,
                       content: str, followersOnly: bool, saveToFile: bool,
                       client_to_server: bool, commentsEnabled: bool,
                       attachImageFilename: str, mediaType: str,
                       imageDescription: str, city: str,
                       inReplyTo: str, inReplyToAtomUri: str,
                       subject: str, schedulePost: bool,
                       eventDate: str, eventTime: str,
                       location: str, systemLanguage: str,
                       conversationId: str, low_bandwidth: bool,
                       content_license_url: str) -> {}:
    """Unlisted post. This has the #Public and followers links inverted.
    """
    domainFull = getFullDomain(domain, port)
    localActor = localActorUrl(http_prefix, nickname, domainFull)
    return _createPostBase(base_dir, nickname, domain, port,
                           localActor + '/followers',
                           'https://www.w3.org/ns/activitystreams#Public',
                           http_prefix, content, followersOnly, saveToFile,
                           client_to_server, commentsEnabled,
                           attachImageFilename, mediaType,
                           imageDescription, city,
                           False, False,
                           inReplyTo, inReplyToAtomUri, subject,
                           schedulePost, eventDate, eventTime, location,
                           None, None, None, None, None,
                           None, None, None, None, None, systemLanguage,
                           conversationId, low_bandwidth,
                           content_license_url)


def createFollowersOnlyPost(base_dir: str,
                            nickname: str, domain: str, port: int,
                            http_prefix: str,
                            content: str, followersOnly: bool,
                            saveToFile: bool,
                            client_to_server: bool, commentsEnabled: bool,
                            attachImageFilename: str, mediaType: str,
                            imageDescription: str, city: str,
                            inReplyTo: str,
                            inReplyToAtomUri: str,
                            subject: str, schedulePost: bool,
                            eventDate: str, eventTime: str,
                            location: str, systemLanguage: str,
                            conversationId: str, low_bandwidth: bool,
                            content_license_url: str) -> {}:
    """Followers only post
    """
    domainFull = getFullDomain(domain, port)
    localActor = localActorUrl(http_prefix, nickname, domainFull)
    return _createPostBase(base_dir, nickname, domain, port,
                           localActor + '/followers',
                           None,
                           http_prefix, content, followersOnly, saveToFile,
                           client_to_server, commentsEnabled,
                           attachImageFilename, mediaType,
                           imageDescription, city,
                           False, False,
                           inReplyTo, inReplyToAtomUri, subject,
                           schedulePost, eventDate, eventTime, location,
                           None, None, None, None, None,
                           None, None, None, None, None, systemLanguage,
                           conversationId, low_bandwidth,
                           content_license_url)


def getMentionedPeople(base_dir: str, http_prefix: str,
                       content: str, domain: str, debug: bool) -> []:
    """Extracts a list of mentioned actors from the given message content
    """
    if '@' not in content:
        return None
    mentions = []
    words = content.split(' ')
    for wrd in words:
        if not wrd.startswith('@'):
            continue
        handle = wrd[1:]
        if debug:
            print('DEBUG: mentioned handle ' + handle)
        if '@' not in handle:
            handle = handle + '@' + domain
            if not os.path.isdir(base_dir + '/accounts/' + handle):
                continue
        else:
            externalDomain = handle.split('@')[1]
            if not ('.' in externalDomain or
                    externalDomain == 'localhost'):
                continue
        mentionedNickname = handle.split('@')[0]
        mentionedDomain = handle.split('@')[1].strip('\n').strip('\r')
        if ':' in mentionedDomain:
            mentionedDomain = removeDomainPort(mentionedDomain)
        if not validNickname(mentionedDomain, mentionedNickname):
            continue
        actor = \
            localActorUrl(http_prefix, mentionedNickname, handle.split('@')[1])
        mentions.append(actor)
    return mentions


def createDirectMessagePost(base_dir: str,
                            nickname: str, domain: str, port: int,
                            http_prefix: str,
                            content: str, followersOnly: bool,
                            saveToFile: bool, client_to_server: bool,
                            commentsEnabled: bool,
                            attachImageFilename: str, mediaType: str,
                            imageDescription: str, city: str,
                            inReplyTo: str,
                            inReplyToAtomUri: str,
                            subject: str, debug: bool,
                            schedulePost: bool,
                            eventDate: str, eventTime: str,
                            location: str, systemLanguage: str,
                            conversationId: str, low_bandwidth: bool,
                            content_license_url: str) -> {}:
    """Direct Message post
    """
    content = resolvePetnames(base_dir, nickname, domain, content)
    mentionedPeople = \
        getMentionedPeople(base_dir, http_prefix, content, domain, debug)
    if debug:
        print('mentionedPeople: ' + str(mentionedPeople))
    if not mentionedPeople:
        return None
    postTo = None
    postCc = None
    messageJson = \
        _createPostBase(base_dir, nickname, domain, port,
                        postTo, postCc,
                        http_prefix, content, followersOnly, saveToFile,
                        client_to_server, commentsEnabled,
                        attachImageFilename, mediaType,
                        imageDescription, city,
                        False, False,
                        inReplyTo, inReplyToAtomUri, subject,
                        schedulePost, eventDate, eventTime, location,
                        None, None, None, None, None,
                        None, None, None, None, None, systemLanguage,
                        conversationId, low_bandwidth,
                        content_license_url)
    # mentioned recipients go into To rather than Cc
    messageJson['to'] = messageJson['object']['cc']
    messageJson['object']['to'] = messageJson['to']
    messageJson['cc'] = []
    messageJson['object']['cc'] = []
    if schedulePost:
        postId = removeIdEnding(messageJson['object']['id'])
        savePostToBox(base_dir, http_prefix, postId,
                      nickname, domain, messageJson, 'scheduled')
    return messageJson


def createReportPost(base_dir: str,
                     nickname: str, domain: str, port: int, http_prefix: str,
                     content: str, followersOnly: bool, saveToFile: bool,
                     client_to_server: bool, commentsEnabled: bool,
                     attachImageFilename: str, mediaType: str,
                     imageDescription: str, city: str,
                     debug: bool, subject: str, systemLanguage: str,
                     low_bandwidth: bool,
                     content_license_url: str) -> {}:
    """Send a report to moderators
    """
    domainFull = getFullDomain(domain, port)

    # add a title to distinguish moderation reports from other posts
    reportTitle = 'Moderation Report'
    if not subject:
        subject = reportTitle
    else:
        if not subject.startswith(reportTitle):
            subject = reportTitle + ': ' + subject

    # create the list of moderators from the moderators file
    moderatorsList = []
    moderatorsFile = base_dir + '/accounts/moderators.txt'
    if os.path.isfile(moderatorsFile):
        with open(moderatorsFile, 'r') as fileHandler:
            for line in fileHandler:
                line = line.strip('\n').strip('\r')
                if line.startswith('#'):
                    continue
                if line.startswith('/users/'):
                    line = line.replace('users', '')
                if line.startswith('@'):
                    line = line[1:]
                if '@' in line:
                    nick = line.split('@')[0]
                    moderatorActor = \
                        localActorUrl(http_prefix, nick, domainFull)
                    if moderatorActor not in moderatorsList:
                        moderatorsList.append(moderatorActor)
                    continue
                if line.startswith('http') or line.startswith('hyper'):
                    # must be a local address - no remote moderators
                    if '://' + domainFull + '/' in line:
                        if line not in moderatorsList:
                            moderatorsList.append(line)
                else:
                    if '/' not in line:
                        moderatorActor = \
                            localActorUrl(http_prefix, line, domainFull)
                        if moderatorActor not in moderatorsList:
                            moderatorsList.append(moderatorActor)
    if len(moderatorsList) == 0:
        # if there are no moderators then the admin becomes the moderator
        adminNickname = getConfigParam(base_dir, 'admin')
        if adminNickname:
            localActor = localActorUrl(http_prefix, adminNickname, domainFull)
            moderatorsList.append(localActor)
    if not moderatorsList:
        return None
    if debug:
        print('DEBUG: Sending report to moderators')
        print(str(moderatorsList))
    postTo = moderatorsList
    postCc = None
    postJsonObject = None
    for toUrl in postTo:
        # who is this report going to?
        toNickname = toUrl.split('/users/')[1]
        handle = toNickname + '@' + domain

        postJsonObject = \
            _createPostBase(base_dir, nickname, domain, port,
                            toUrl, postCc,
                            http_prefix, content, followersOnly, saveToFile,
                            client_to_server, commentsEnabled,
                            attachImageFilename, mediaType,
                            imageDescription, city,
                            True, False, None, None, subject,
                            False, None, None, None, None, None,
                            None, None, None,
                            None, None, None, None, None, systemLanguage,
                            None, low_bandwidth, content_license_url)
        if not postJsonObject:
            continue

        # save a notification file so that the moderator
        # knows something new has appeared
        newReportFile = base_dir + '/accounts/' + handle + '/.newReport'
        if os.path.isfile(newReportFile):
            continue
        try:
            with open(newReportFile, 'w+') as fp:
                fp.write(toUrl + '/moderation')
        except OSError:
            print('EX: createReportPost unable to write ' + newReportFile)

    return postJsonObject


def threadSendPost(session, postJsonStr: str, federationList: [],
                   inboxUrl: str, base_dir: str,
                   signatureHeaderJson: {}, postLog: [],
                   debug: bool) -> None:
    """Sends a with retries
    """
    tries = 0
    sendIntervalSec = 30
    for attempt in range(20):
        postResult = None
        unauthorized = False
        if debug:
            print('Getting postJsonString for ' + inboxUrl)
        try:
            postResult, unauthorized, returnCode = \
                postJsonString(session, postJsonStr, federationList,
                               inboxUrl, signatureHeaderJson,
                               debug)
            if returnCode >= 500 and returnCode < 600:
                # if an instance is returning a code which indicates that
                # it might have a runtime error, like 503, then don't
                # continue to post to it
                break
            if debug:
                print('Obtained postJsonString for ' + inboxUrl +
                      ' unauthorized: ' + str(unauthorized))
        except Exception as ex:
            print('ERROR: postJsonString failed ' + str(ex))
        if unauthorized:
            print('WARN: threadSendPost: Post is unauthorized ' +
                  inboxUrl + ' ' + postJsonStr)
            break
        if postResult:
            logStr = 'Success on try ' + str(tries) + ': ' + postJsonStr
        else:
            logStr = 'Retry ' + str(tries) + ': ' + postJsonStr
        postLog.append(logStr)
        # keep the length of the log finite
        # Don't accumulate massive files on systems with limited resources
        while len(postLog) > 16:
            postLog.pop(0)
        if debug:
            # save the log file
            postLogFilename = base_dir + '/post.log'
            if os.path.isfile(postLogFilename):
                with open(postLogFilename, 'a+') as logFile:
                    logFile.write(logStr + '\n')
            else:
                with open(postLogFilename, 'w+') as logFile:
                    logFile.write(logStr + '\n')

        if postResult:
            if debug:
                print('DEBUG: successful json post to ' + inboxUrl)
            # our work here is done
            break
        if debug:
            print(postJsonStr)
            print('DEBUG: json post to ' + inboxUrl +
                  ' failed. Waiting for ' +
                  str(sendIntervalSec) + ' seconds.')
        time.sleep(sendIntervalSec)
        tries += 1


def sendPost(signingPrivateKeyPem: str, project_version: str,
             session, base_dir: str, nickname: str, domain: str, port: int,
             toNickname: str, toDomain: str, toPort: int, cc: str,
             http_prefix: str, content: str, followersOnly: bool,
             saveToFile: bool, client_to_server: bool,
             commentsEnabled: bool,
             attachImageFilename: str, mediaType: str,
             imageDescription: str, city: str,
             federationList: [], sendThreads: [], postLog: [],
             cachedWebfingers: {}, personCache: {},
             isArticle: bool, systemLanguage: str,
             shared_items_federated_domains: [],
             sharedItemFederationTokens: {},
             low_bandwidth: bool, content_license_url: str,
             debug: bool = False, inReplyTo: str = None,
             inReplyToAtomUri: str = None, subject: str = None) -> int:
    """Post to another inbox. Used by unit tests.
    """
    withDigest = True
    conversationId = None

    if toNickname == 'inbox':
        # shared inbox actor on @domain@domain
        toNickname = toDomain

    toDomain = getFullDomain(toDomain, toPort)

    handle = http_prefix + '://' + toDomain + '/@' + toNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cachedWebfingers,
                                domain, project_version, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    if not client_to_server:
        postToBox = 'inbox'
    else:
        postToBox = 'outbox'
        if isArticle:
            postToBox = 'tlblogs'

    # get the actor inbox for the To handle
    originDomain = domain
    (inboxUrl, pubKeyId, pubKey, toPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix,
                                    nickname, domain, postToBox,
                                    72533)

    if not inboxUrl:
        return 3
    if not pubKey:
        return 4
    if not toPersonId:
        return 5
    # sharedInbox is optional

    postJsonObject = \
        _createPostBase(base_dir, nickname, domain, port,
                        toPersonId, cc, http_prefix, content,
                        followersOnly, saveToFile, client_to_server,
                        commentsEnabled,
                        attachImageFilename, mediaType,
                        imageDescription, city,
                        False, isArticle, inReplyTo,
                        inReplyToAtomUri, subject,
                        False, None, None, None, None, None,
                        None, None, None,
                        None, None, None, None, None, systemLanguage,
                        conversationId, low_bandwidth,
                        content_license_url)

    # get the senders private key
    privateKeyPem = _getPersonKey(nickname, domain, base_dir, 'private')
    if len(privateKeyPem) == 0:
        return 6

    if toDomain not in inboxUrl:
        return 7
    postPath = inboxUrl.split(toDomain, 1)[1]

    if not postJsonObject.get('signature'):
        try:
            signedPostJsonObject = postJsonObject.copy()
            generateJsonSignature(signedPostJsonObject, privateKeyPem)
            postJsonObject = signedPostJsonObject
        except Exception as ex:
            print('WARN: failed to JSON-LD sign post, ' + str(ex))
            pass

    # convert json to string so that there are no
    # subsequent conversions after creating message body digest
    postJsonStr = json.dumps(postJsonObject)

    # construct the http header, including the message body digest
    signatureHeaderJson = \
        createSignedHeader(None, privateKeyPem, nickname, domain, port,
                           toDomain, toPort,
                           postPath, http_prefix, withDigest, postJsonStr,
                           None)

    # if the "to" domain is within the shared items
    # federation list then send the token for this domain
    # so that it can request a catalog
    if toDomain in shared_items_federated_domains:
        domainFull = getFullDomain(domain, port)
        if sharedItemFederationTokens.get(domainFull):
            signatureHeaderJson['Origin'] = domainFull
            signatureHeaderJson['SharesCatalog'] = \
                sharedItemFederationTokens[domainFull]
            if debug:
                print('SharesCatalog added to header')
        elif debug:
            print(domainFull + ' not in sharedItemFederationTokens')
    elif debug:
        print(toDomain + ' not in shared_items_federated_domains ' +
              str(shared_items_federated_domains))

    if debug:
        print('signatureHeaderJson: ' + str(signatureHeaderJson))

    # Keep the number of threads being used small
    while len(sendThreads) > 1000:
        print('WARN: Maximum threads reached - killing send thread')
        sendThreads[0].kill()
        sendThreads.pop(0)
        print('WARN: thread killed')
    thr = \
        threadWithTrace(target=threadSendPost,
                        args=(session,
                              postJsonStr,
                              federationList,
                              inboxUrl, base_dir,
                              signatureHeaderJson.copy(),
                              postLog,
                              debug), daemon=True)
    sendThreads.append(thr)
    thr.start()
    return 0


def sendPostViaServer(signingPrivateKeyPem: str, project_version: str,
                      base_dir: str, session, fromNickname: str, password: str,
                      fromDomain: str, fromPort: int,
                      toNickname: str, toDomain: str, toPort: int, cc: str,
                      http_prefix: str, content: str, followersOnly: bool,
                      commentsEnabled: bool,
                      attachImageFilename: str, mediaType: str,
                      imageDescription: str, city: str,
                      cachedWebfingers: {}, personCache: {},
                      isArticle: bool, systemLanguage: str,
                      low_bandwidth: bool,
                      content_license_url: str,
                      debug: bool = False,
                      inReplyTo: str = None,
                      inReplyToAtomUri: str = None,
                      conversationId: str = None,
                      subject: str = None) -> int:
    """Send a post via a proxy (c2s)
    """
    if not session:
        print('WARN: No session for sendPostViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cachedWebfingers,
                        fromDomainFull, project_version, debug, False,
                        signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: post webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: post webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'
    if isArticle:
        postToBox = 'tlblogs'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix,
                                    fromNickname,
                                    fromDomainFull, postToBox,
                                    82796)
    if not inboxUrl:
        if debug:
            print('DEBUG: post no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: post no actor was found for ' + handle)
        return 4

    # Get the json for the c2s post, not saving anything to file
    # Note that base_dir is set to None
    saveToFile = False
    client_to_server = True
    if toDomain.lower().endswith('public'):
        toPersonId = 'https://www.w3.org/ns/activitystreams#Public'
        cc = localActorUrl(http_prefix, fromNickname, fromDomainFull) + \
            '/followers'
    else:
        if toDomain.lower().endswith('followers') or \
           toDomain.lower().endswith('followersonly'):
            toPersonId = \
                localActorUrl(http_prefix, fromNickname, fromDomainFull) + \
                '/followers'
        else:
            toDomainFull = getFullDomain(toDomain, toPort)
            toPersonId = localActorUrl(http_prefix, toNickname, toDomainFull)

    postJsonObject = \
        _createPostBase(base_dir,
                        fromNickname, fromDomain, fromPort,
                        toPersonId, cc, http_prefix, content,
                        followersOnly, saveToFile, client_to_server,
                        commentsEnabled,
                        attachImageFilename, mediaType,
                        imageDescription, city,
                        False, isArticle, inReplyTo,
                        inReplyToAtomUri, subject,
                        False, None, None, None, None, None,
                        None, None, None,
                        None, None, None, None, None, systemLanguage,
                        conversationId, low_bandwidth,
                        content_license_url)

    authHeader = createBasicAuthHeader(fromNickname, password)

    if attachImageFilename:
        headers = {
            'host': fromDomainFull,
            'Authorization': authHeader
        }
        postResult = \
            postImage(session, attachImageFilename, [],
                      inboxUrl, headers)
        if not postResult:
            if debug:
                print('DEBUG: post failed to upload image')
#            return 9

    headers = {
        'host': fromDomainFull,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postDumps = json.dumps(postJsonObject)
    postResult, unauthorized, returnCode = \
        postJsonString(session, postDumps, [],
                       inboxUrl, headers, debug, 5, True)
    if not postResult:
        if debug:
            if unauthorized:
                print('DEBUG: POST failed for c2s to ' +
                      inboxUrl + ' unathorized')
            else:
                print('DEBUG: POST failed for c2s to '
                      + inboxUrl + ' return code ' + str(returnCode))
        return 5

    if debug:
        print('DEBUG: c2s POST success')
    return 0


def groupFollowersByDomain(base_dir: str, nickname: str, domain: str) -> {}:
    """Returns a dictionary with followers grouped by domain
    """
    handle = nickname + '@' + domain
    followersFilename = base_dir + '/accounts/' + handle + '/followers.txt'
    if not os.path.isfile(followersFilename):
        return None
    grouped = {}
    with open(followersFilename, 'r') as f:
        for followerHandle in f:
            if '@' not in followerHandle:
                continue
            fHandle = \
                followerHandle.strip().replace('\n', '').replace('\r', '')
            followerDomain = fHandle.split('@')[1]
            if not grouped.get(followerDomain):
                grouped[followerDomain] = [fHandle]
            else:
                grouped[followerDomain].append(fHandle)
    return grouped


def _addFollowersToPublicPost(postJsonObject: {}) -> None:
    """Adds followers entry to cc if it doesn't exist
    """
    if not postJsonObject.get('actor'):
        return

    if isinstance(postJsonObject['object'], str):
        if not postJsonObject.get('to'):
            return
        if len(postJsonObject['to']) > 1:
            return
        if len(postJsonObject['to']) == 0:
            return
        if not postJsonObject['to'][0].endswith('#Public'):
            return
        if postJsonObject.get('cc'):
            return
        postJsonObject['cc'] = postJsonObject['actor'] + '/followers'
    elif hasObjectDict(postJsonObject):
        if not postJsonObject['object'].get('to'):
            return
        if len(postJsonObject['object']['to']) > 1:
            return
        elif len(postJsonObject['object']['to']) == 0:
            return
        elif not postJsonObject['object']['to'][0].endswith('#Public'):
            return
        if postJsonObject['object'].get('cc'):
            return
        postJsonObject['object']['cc'] = postJsonObject['actor'] + '/followers'


def sendSignedJson(postJsonObject: {}, session, base_dir: str,
                   nickname: str, domain: str, port: int,
                   toNickname: str, toDomain: str, toPort: int, cc: str,
                   http_prefix: str, saveToFile: bool, client_to_server: bool,
                   federationList: [],
                   sendThreads: [], postLog: [], cachedWebfingers: {},
                   personCache: {}, debug: bool, project_version: str,
                   sharedItemsToken: str, groupAccount: bool,
                   signingPrivateKeyPem: str,
                   sourceId: int) -> int:
    """Sends a signed json object to an inbox/outbox
    """
    if debug:
        print('DEBUG: sendSignedJson start')
    if not session:
        print('WARN: No session specified for sendSignedJson')
        return 8
    withDigest = True

    if toDomain.endswith('.onion') or toDomain.endswith('.i2p'):
        http_prefix = 'http'

    if toNickname == 'inbox':
        # shared inbox actor on @domain@domain
        toNickname = toDomain

    toDomain = getFullDomain(toDomain, toPort)

    toDomainUrl = http_prefix + '://' + toDomain
    if not siteIsActive(toDomainUrl, 10):
        print('Domain is inactive: ' + toDomainUrl)
        return 9
    print('Domain is active: ' + toDomainUrl)
    handleBase = toDomainUrl + '/@'
    if toNickname:
        handle = handleBase + toNickname
    else:
        singleUserInstanceNickname = 'dev'
        handle = handleBase + singleUserInstanceNickname

    if debug:
        print('DEBUG: handle - ' + handle + ' toPort ' + str(toPort))

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix, cachedWebfingers,
                                domain, project_version, debug, groupAccount,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: webfinger for ' + handle + ' failed')
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    if wfRequest.get('errors'):
        if debug:
            print('DEBUG: webfinger for ' + handle +
                  ' failed with errors ' + str(wfRequest['errors']))

    if not client_to_server:
        postToBox = 'inbox'
    else:
        postToBox = 'outbox'

    # get the actor inbox/outbox for the To handle
    originDomain = domain
    (inboxUrl, pubKeyId, pubKey, toPersonId, sharedInboxUrl, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix,
                                    nickname, domain, postToBox,
                                    sourceId)

    print("inboxUrl: " + str(inboxUrl))
    print("toPersonId: " + str(toPersonId))
    print("sharedInboxUrl: " + str(sharedInboxUrl))
    if inboxUrl:
        if inboxUrl.endswith('/actor/inbox'):
            inboxUrl = sharedInboxUrl

    if not inboxUrl:
        if debug:
            print('DEBUG: missing inboxUrl')
        return 3

    if debug:
        print('DEBUG: Sending to endpoint ' + inboxUrl)

    if not pubKey:
        if debug:
            print('DEBUG: missing pubkey')
        return 4
    if not toPersonId:
        if debug:
            print('DEBUG: missing personId')
        return 5
    # sharedInbox is optional

    # get the senders private key
    privateKeyPem = _getPersonKey(nickname, domain, base_dir, 'private', debug)
    if len(privateKeyPem) == 0:
        if debug:
            print('DEBUG: Private key not found for ' +
                  nickname + '@' + domain +
                  ' in ' + base_dir + '/keys/private')
        return 6

    if toDomain not in inboxUrl:
        if debug:
            print('DEBUG: ' + toDomain + ' is not in ' + inboxUrl)
        return 7
    postPath = inboxUrl.split(toDomain, 1)[1]

    _addFollowersToPublicPost(postJsonObject)

    if not postJsonObject.get('signature'):
        try:
            signedPostJsonObject = postJsonObject.copy()
            generateJsonSignature(signedPostJsonObject, privateKeyPem)
            postJsonObject = signedPostJsonObject
        except Exception as ex:
            print('WARN: failed to JSON-LD sign post, ' + str(ex))
            pass

    # convert json to string so that there are no
    # subsequent conversions after creating message body digest
    postJsonStr = json.dumps(postJsonObject)

    # construct the http header, including the message body digest
    signatureHeaderJson = \
        createSignedHeader(None, privateKeyPem, nickname, domain, port,
                           toDomain, toPort,
                           postPath, http_prefix, withDigest, postJsonStr,
                           None)
    # optionally add a token so that the receiving instance may access
    # your shared items catalog
    if sharedItemsToken:
        signatureHeaderJson['Origin'] = getFullDomain(domain, port)
        signatureHeaderJson['SharesCatalog'] = sharedItemsToken
    elif debug:
        print('Not sending shared items federation token')

    # Keep the number of threads being used small
    while len(sendThreads) > 1000:
        print('WARN: Maximum threads reached - killing send thread')
        sendThreads[0].kill()
        sendThreads.pop(0)
        print('WARN: thread killed')

    if debug:
        print('DEBUG: starting thread to send post')
        pprint(postJsonObject)
    thr = \
        threadWithTrace(target=threadSendPost,
                        args=(session,
                              postJsonStr,
                              federationList,
                              inboxUrl, base_dir,
                              signatureHeaderJson.copy(),
                              postLog,
                              debug), daemon=True)
    sendThreads.append(thr)
    # thr.start()
    return 0


def addToField(activityType: str, postJsonObject: {},
               debug: bool) -> ({}, bool):
    """The Follow/Add/Remove activity doesn't have a 'to' field and so one
    needs to be added so that activity distribution happens in a consistent way
    Returns true if a 'to' field exists or was added
    """
    if postJsonObject.get('to'):
        return postJsonObject, True

    if debug:
        pprint(postJsonObject)
        print('DEBUG: no "to" field when sending to named addresses 2')

    isSameType = False
    toFieldAdded = False
    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], str):
            if postJsonObject.get('type'):
                if postJsonObject['type'] == activityType:
                    isSameType = True
                    if debug:
                        print('DEBUG: "to" field assigned to ' + activityType)
                    toAddress = postJsonObject['object']
                    if '/statuses/' in toAddress:
                        toAddress = toAddress.split('/statuses/')[0]
                    postJsonObject['to'] = [toAddress]
                    toFieldAdded = True
        elif hasObjectDict(postJsonObject):
            # add a to field to bookmark add or remove
            if postJsonObject.get('type') and \
               postJsonObject.get('actor') and \
               postJsonObject['object'].get('type'):
                if postJsonObject['type'] == 'Add' or \
                   postJsonObject['type'] == 'Remove':
                    if postJsonObject['object']['type'] == 'Document':
                        postJsonObject['to'] = \
                            [postJsonObject['actor']]
                        postJsonObject['object']['to'] = \
                            [postJsonObject['actor']]
                        toFieldAdded = True

            if not toFieldAdded and \
               postJsonObject['object'].get('type'):
                if postJsonObject['object']['type'] == activityType:
                    isSameType = True
                    if isinstance(postJsonObject['object']['object'], str):
                        if debug:
                            print('DEBUG: "to" field assigned to ' +
                                  activityType)
                        toAddress = postJsonObject['object']['object']
                        if '/statuses/' in toAddress:
                            toAddress = toAddress.split('/statuses/')[0]
                        postJsonObject['object']['to'] = [toAddress]
                        postJsonObject['to'] = \
                            [postJsonObject['object']['object']]
                        toFieldAdded = True

    if not isSameType:
        return postJsonObject, True
    if toFieldAdded:
        return postJsonObject, True
    return postJsonObject, False


def _isProfileUpdate(postJsonObject: {}) -> bool:
    """Is the given post a profile update?
    for actor updates there is no 'to' within the object
    """
    if postJsonObject.get('type'):
        if hasObjectStringType(postJsonObject, False):
            if (postJsonObject['type'] == 'Update' and
                (postJsonObject['object']['type'] == 'Person' or
                 postJsonObject['object']['type'] == 'Application' or
                 postJsonObject['object']['type'] == 'Group' or
                 postJsonObject['object']['type'] == 'Service')):
                return True
    return False


def _sendToNamedAddresses(session, base_dir: str,
                          nickname: str, domain: str,
                          onion_domain: str, i2p_domain: str, port: int,
                          http_prefix: str, federationList: [],
                          sendThreads: [], postLog: [],
                          cachedWebfingers: {}, personCache: {},
                          postJsonObject: {}, debug: bool,
                          project_version: str,
                          shared_items_federated_domains: [],
                          sharedItemFederationTokens: {},
                          signingPrivateKeyPem: str) -> None:
    """sends a post to the specific named addresses in to/cc
    """
    if not session:
        print('WARN: No session for sendToNamedAddresses')
        return
    if not postJsonObject.get('object'):
        return
    isProfileUpdate = False
    if hasObjectDict(postJsonObject):
        if _isProfileUpdate(postJsonObject):
            # use the original object, which has a 'to'
            recipientsObject = postJsonObject
            isProfileUpdate = True

        if not isProfileUpdate:
            if not postJsonObject['object'].get('to'):
                if debug:
                    pprint(postJsonObject)
                    print('DEBUG: ' +
                          'no "to" field when sending to named addresses')
                if hasObjectStringType(postJsonObject, debug):
                    if postJsonObject['object']['type'] == 'Follow' or \
                       postJsonObject['object']['type'] == 'Join':
                        if isinstance(postJsonObject['object']['object'], str):
                            if debug:
                                print('DEBUG: "to" field assigned to Follow')
                            postJsonObject['object']['to'] = \
                                [postJsonObject['object']['object']]
                if not postJsonObject['object'].get('to'):
                    return
            recipientsObject = postJsonObject['object']
    else:
        postJsonObject, fieldAdded = \
            addToField('Follow', postJsonObject, debug)
        if not fieldAdded:
            return
        postJsonObject, fieldAdded = addToField('Like', postJsonObject, debug)
        if not fieldAdded:
            return
        recipientsObject = postJsonObject

    recipients = []
    recipientType = ('to', 'cc')
    for rType in recipientType:
        if not recipientsObject.get(rType):
            continue
        if isinstance(recipientsObject[rType], list):
            if debug:
                pprint(recipientsObject)
                print('recipientsObject: ' + str(recipientsObject[rType]))
            for address in recipientsObject[rType]:
                if not address:
                    continue
                if '/' not in address:
                    continue
                if address.endswith('#Public'):
                    continue
                if address.endswith('/followers'):
                    continue
                recipients.append(address)
        elif isinstance(recipientsObject[rType], str):
            address = recipientsObject[rType]
            if address:
                if '/' in address:
                    if address.endswith('#Public'):
                        continue
                    if address.endswith('/followers'):
                        continue
                    recipients.append(address)
    if not recipients:
        if debug:
            print('DEBUG: no individual recipients')
        return
    if debug:
        print('DEBUG: Sending individually addressed posts: ' +
              str(recipients))
    # this is after the message has arrived at the server
    client_to_server = False
    for address in recipients:
        toNickname = getNicknameFromActor(address)
        if not toNickname:
            continue
        toDomain, toPort = getDomainFromActor(address)
        if not toDomain:
            continue
        # Don't send profile/actor updates to yourself
        if isProfileUpdate:
            domainFull = getFullDomain(domain, port)
            toDomainFull = getFullDomain(toDomain, toPort)
            if nickname == toNickname and \
               domainFull == toDomainFull:
                if debug:
                    print('Not sending profile update to self. ' +
                          nickname + '@' + domainFull)
                continue
        if debug:
            domainFull = getFullDomain(domain, port)
            toDomainFull = getFullDomain(toDomain, toPort)
            print('DEBUG: Post sending s2s: ' + nickname + '@' + domainFull +
                  ' to ' + toNickname + '@' + toDomainFull)

        # if we have an alt onion domain and we are sending to
        # another onion domain then switch the clearnet
        # domain for the onion one
        fromDomain = domain
        fromDomainFull = getFullDomain(domain, port)
        fromHttpPrefix = http_prefix
        if onion_domain:
            if toDomain.endswith('.onion'):
                fromDomain = onion_domain
                fromDomainFull = onion_domain
                fromHttpPrefix = 'http'
        elif i2p_domain:
            if toDomain.endswith('.i2p'):
                fromDomain = i2p_domain
                fromDomainFull = i2p_domain
                fromHttpPrefix = 'http'
        cc = []

        # if the "to" domain is within the shared items
        # federation list then send the token for this domain
        # so that it can request a catalog
        sharedItemsToken = None
        if toDomain in shared_items_federated_domains:
            if sharedItemFederationTokens.get(fromDomainFull):
                sharedItemsToken = sharedItemFederationTokens[fromDomainFull]

        groupAccount = hasGroupType(base_dir, address, personCache)

        sendSignedJson(postJsonObject, session, base_dir,
                       nickname, fromDomain, port,
                       toNickname, toDomain, toPort,
                       cc, fromHttpPrefix, True, client_to_server,
                       federationList,
                       sendThreads, postLog, cachedWebfingers,
                       personCache, debug, project_version,
                       sharedItemsToken, groupAccount,
                       signingPrivateKeyPem, 34436782)


def sendToNamedAddressesThread(session, base_dir: str,
                               nickname: str, domain: str,
                               onion_domain: str, i2p_domain: str, port: int,
                               http_prefix: str, federationList: [],
                               sendThreads: [], postLog: [],
                               cachedWebfingers: {}, personCache: {},
                               postJsonObject: {}, debug: bool,
                               project_version: str,
                               shared_items_federated_domains: [],
                               sharedItemFederationTokens: {},
                               signingPrivateKeyPem: str):
    """Returns a thread used to send a post to named addresses
    """
    sendThread = \
        threadWithTrace(target=_sendToNamedAddresses,
                        args=(session, base_dir,
                              nickname, domain,
                              onion_domain, i2p_domain, port,
                              http_prefix, federationList,
                              sendThreads, postLog,
                              cachedWebfingers, personCache,
                              postJsonObject, debug,
                              project_version,
                              shared_items_federated_domains,
                              sharedItemFederationTokens,
                              signingPrivateKeyPem), daemon=True)
    try:
        sendThread.start()
    except SocketError as ex:
        print('WARN: socket error while starting ' +
              'thread to send to named addresses. ' + str(ex))
        return None
    except ValueError as ex:
        print('WARN: error while starting ' +
              'thread to send to named addresses. ' + str(ex))
        return None
    return sendThread


def _hasSharedInbox(session, http_prefix: str, domain: str,
                    debug: bool, signingPrivateKeyPem: str) -> bool:
    """Returns true if the given domain has a shared inbox
    This tries the new and the old way of webfingering the shared inbox
    """
    tryHandles = []
    if ':' not in domain:
        tryHandles.append(domain + '@' + domain)
    tryHandles.append('inbox@' + domain)
    for handle in tryHandles:
        wfRequest = webfingerHandle(session, handle, http_prefix, {},
                                    domain, __version__, debug, False,
                                    signingPrivateKeyPem)
        if wfRequest:
            if isinstance(wfRequest, dict):
                if not wfRequest.get('errors'):
                    return True
    return False


def _sendingProfileUpdate(postJsonObject: {}) -> bool:
    """Returns true if the given json is a profile update
    """
    if postJsonObject['type'] != 'Update':
        return False
    if not hasObjectStringType(postJsonObject, False):
        return False
    activityType = postJsonObject['object']['type']
    if activityType == 'Person' or \
       activityType == 'Application' or \
       activityType == 'Group' or \
       activityType == 'Service':
        return True
    return False


def sendToFollowers(session, base_dir: str,
                    nickname: str,
                    domain: str,
                    onion_domain: str, i2p_domain: str, port: int,
                    http_prefix: str, federationList: [],
                    sendThreads: [], postLog: [],
                    cachedWebfingers: {}, personCache: {},
                    postJsonObject: {}, debug: bool,
                    project_version: str,
                    shared_items_federated_domains: [],
                    sharedItemFederationTokens: {},
                    signingPrivateKeyPem: str) -> None:
    """sends a post to the followers of the given nickname
    """
    print('sendToFollowers')
    if not session:
        print('WARN: No session for sendToFollowers')
        return
    if not _postIsAddressedToFollowers(base_dir, nickname, domain,
                                       port, http_prefix,
                                       postJsonObject):
        if debug:
            print('Post is not addressed to followers')
        return
    print('Post is addressed to followers')

    grouped = groupFollowersByDomain(base_dir, nickname, domain)
    if not grouped:
        if debug:
            print('Post to followers did not resolve any domains')
        return
    print('Post to followers resolved domains')
    # print(str(grouped))

    # this is after the message has arrived at the server
    client_to_server = False

    # for each instance
    sendingStartTime = datetime.datetime.utcnow()
    print('Sending post to followers begins ' +
          sendingStartTime.strftime("%Y-%m-%dT%H:%M:%SZ"))
    sendingCtr = 0
    for followerDomain, followerHandles in grouped.items():
        print('Sending post to followers progress ' +
              str(int(sendingCtr * 100 / len(grouped.items()))) + '% ' +
              followerDomain)
        sendingCtr += 1

        if debug:
            pprint(followerHandles)

        # if the followers domain is within the shared items
        # federation list then send the token for this domain
        # so that it can request a catalog
        sharedItemsToken = None
        if followerDomain in shared_items_federated_domains:
            domainFull = getFullDomain(domain, port)
            if sharedItemFederationTokens.get(domainFull):
                sharedItemsToken = sharedItemFederationTokens[domainFull]

        # check that the follower's domain is active
        followerDomainUrl = http_prefix + '://' + followerDomain
        if not siteIsActive(followerDomainUrl, 10):
            print('Sending post to followers domain is inactive: ' +
                  followerDomainUrl)
            continue
        print('Sending post to followers domain is active: ' +
              followerDomainUrl)

        withSharedInbox = \
            _hasSharedInbox(session, http_prefix, followerDomain, debug,
                            signingPrivateKeyPem)
        if debug:
            if withSharedInbox:
                print(followerDomain + ' has shared inbox')
        if not withSharedInbox:
            print('Sending post to followers, ' + followerDomain +
                  ' does not have a shared inbox')

        toPort = port
        index = 0
        toDomain = followerHandles[index].split('@')[1]
        if ':' in toDomain:
            toPort = getPortFromDomain(toDomain)
            toDomain = removeDomainPort(toDomain)

        cc = ''

        # if we are sending to an onion domain and we
        # have an alt onion domain then use the alt
        fromDomain = domain
        fromHttpPrefix = http_prefix
        if onion_domain:
            if toDomain.endswith('.onion'):
                fromDomain = onion_domain
                fromHttpPrefix = 'http'
        elif i2p_domain:
            if toDomain.endswith('.i2p'):
                fromDomain = i2p_domain
                fromHttpPrefix = 'http'

        if withSharedInbox:
            toNickname = followerHandles[index].split('@')[0]

            groupAccount = False
            if toNickname.startswith('!'):
                groupAccount = True
                toNickname = toNickname[1:]

            # if there are more than one followers on the domain
            # then send the post to the shared inbox
            if len(followerHandles) > 1:
                toNickname = 'inbox'

            if toNickname != 'inbox' and postJsonObject.get('type'):
                if _sendingProfileUpdate(postJsonObject):
                    print('Sending post to followers ' +
                          'shared inbox of ' + toDomain)
                    toNickname = 'inbox'

            print('Sending post to followers from ' +
                  nickname + '@' + domain +
                  ' to ' + toNickname + '@' + toDomain)

            sendSignedJson(postJsonObject, session, base_dir,
                           nickname, fromDomain, port,
                           toNickname, toDomain, toPort,
                           cc, fromHttpPrefix, True, client_to_server,
                           federationList,
                           sendThreads, postLog, cachedWebfingers,
                           personCache, debug, project_version,
                           sharedItemsToken, groupAccount,
                           signingPrivateKeyPem, 639342)
        else:
            # send to individual followers without using a shared inbox
            for handle in followerHandles:
                print('Sending post to followers ' + handle)
                toNickname = handle.split('@')[0]

                groupAccount = False
                if toNickname.startswith('!'):
                    groupAccount = True
                    toNickname = toNickname[1:]

                if postJsonObject['type'] != 'Update':
                    print('Sending post to followers from ' +
                          nickname + '@' + domain + ' to ' +
                          toNickname + '@' + toDomain)
                else:
                    print('Sending post to followers profile update from ' +
                          nickname + '@' + domain + ' to ' +
                          toNickname + '@' + toDomain)

                sendSignedJson(postJsonObject, session, base_dir,
                               nickname, fromDomain, port,
                               toNickname, toDomain, toPort,
                               cc, fromHttpPrefix, True, client_to_server,
                               federationList,
                               sendThreads, postLog, cachedWebfingers,
                               personCache, debug, project_version,
                               sharedItemsToken, groupAccount,
                               signingPrivateKeyPem, 634219)

        time.sleep(4)

    if debug:
        print('DEBUG: End of sendToFollowers')

    sendingEndTime = datetime.datetime.utcnow()
    sendingMins = int((sendingEndTime - sendingStartTime).total_seconds() / 60)
    print('Sending post to followers ends ' + str(sendingMins) + ' mins')


def sendToFollowersThread(session, base_dir: str,
                          nickname: str,
                          domain: str,
                          onion_domain: str, i2p_domain: str, port: int,
                          http_prefix: str, federationList: [],
                          sendThreads: [], postLog: [],
                          cachedWebfingers: {}, personCache: {},
                          postJsonObject: {}, debug: bool,
                          project_version: str,
                          shared_items_federated_domains: [],
                          sharedItemFederationTokens: {},
                          signingPrivateKeyPem: str):
    """Returns a thread used to send a post to followers
    """
    sendThread = \
        threadWithTrace(target=sendToFollowers,
                        args=(session, base_dir,
                              nickname, domain,
                              onion_domain, i2p_domain, port,
                              http_prefix, federationList,
                              sendThreads, postLog,
                              cachedWebfingers, personCache,
                              postJsonObject.copy(), debug,
                              project_version,
                              shared_items_federated_domains,
                              sharedItemFederationTokens,
                              signingPrivateKeyPem), daemon=True)
    try:
        sendThread.start()
    except SocketError as ex:
        print('WARN: socket error while starting ' +
              'thread to send to followers. ' + str(ex))
        return None
    except ValueError as ex:
        print('WARN: error while starting ' +
              'thread to send to followers. ' + str(ex))
        return None
    return sendThread


def createInbox(recentPostsCache: {},
                session, base_dir: str, nickname: str, domain: str, port: int,
                http_prefix: str, itemsPerPage: int, headerOnly: bool,
                pageNumber: int) -> {}:
    return _createBoxIndexed(recentPostsCache,
                             session, base_dir, 'inbox',
                             nickname, domain, port, http_prefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createBookmarksTimeline(session, base_dir: str, nickname: str, domain: str,
                            port: int, http_prefix: str, itemsPerPage: int,
                            headerOnly: bool, pageNumber: int) -> {}:
    return _createBoxIndexed({}, session, base_dir, 'tlbookmarks',
                             nickname, domain,
                             port, http_prefix, itemsPerPage, headerOnly,
                             True, 0, False, 0, pageNumber)


def createDMTimeline(recentPostsCache: {},
                     session, base_dir: str, nickname: str, domain: str,
                     port: int, http_prefix: str, itemsPerPage: int,
                     headerOnly: bool, pageNumber: int) -> {}:
    return _createBoxIndexed(recentPostsCache,
                             session, base_dir, 'dm', nickname,
                             domain, port, http_prefix, itemsPerPage,
                             headerOnly, True, 0, False, 0, pageNumber)


def createRepliesTimeline(recentPostsCache: {},
                          session, base_dir: str, nickname: str, domain: str,
                          port: int, http_prefix: str, itemsPerPage: int,
                          headerOnly: bool, pageNumber: int) -> {}:
    return _createBoxIndexed(recentPostsCache, session, base_dir, 'tlreplies',
                             nickname, domain, port, http_prefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createBlogsTimeline(session, base_dir: str, nickname: str, domain: str,
                        port: int, http_prefix: str, itemsPerPage: int,
                        headerOnly: bool, pageNumber: int) -> {}:
    return _createBoxIndexed({}, session, base_dir, 'tlblogs', nickname,
                             domain, port, http_prefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createFeaturesTimeline(session, base_dir: str, nickname: str, domain: str,
                           port: int, http_prefix: str, itemsPerPage: int,
                           headerOnly: bool, pageNumber: int) -> {}:
    return _createBoxIndexed({}, session, base_dir, 'tlfeatures', nickname,
                             domain, port, http_prefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createMediaTimeline(session, base_dir: str, nickname: str, domain: str,
                        port: int, http_prefix: str, itemsPerPage: int,
                        headerOnly: bool, pageNumber: int) -> {}:
    return _createBoxIndexed({}, session, base_dir, 'tlmedia', nickname,
                             domain, port, http_prefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createNewsTimeline(session, base_dir: str, nickname: str, domain: str,
                       port: int, http_prefix: str, itemsPerPage: int,
                       headerOnly: bool, newswire_votes_threshold: int,
                       positive_voting: bool, voting_time_mins: int,
                       pageNumber: int) -> {}:
    return _createBoxIndexed({}, session, base_dir, 'outbox', 'news',
                             domain, port, http_prefix,
                             itemsPerPage, headerOnly, True,
                             newswire_votes_threshold, positive_voting,
                             voting_time_mins, pageNumber)


def createOutbox(session, base_dir: str, nickname: str, domain: str,
                 port: int, http_prefix: str,
                 itemsPerPage: int, headerOnly: bool, authorized: bool,
                 pageNumber: int) -> {}:
    return _createBoxIndexed({}, session, base_dir, 'outbox',
                             nickname, domain, port, http_prefix,
                             itemsPerPage, headerOnly, authorized,
                             0, False, 0, pageNumber)


def createModeration(base_dir: str, nickname: str, domain: str, port: int,
                     http_prefix: str, itemsPerPage: int, headerOnly: bool,
                     pageNumber: int) -> {}:
    boxDir = createPersonDir(nickname, domain, base_dir, 'inbox')
    boxname = 'moderation'

    domain = getFullDomain(domain, port)

    if not pageNumber:
        pageNumber = 1

    pageStr = '?page=' + str(pageNumber)
    boxUrl = localActorUrl(http_prefix, nickname, domain) + '/' + boxname
    boxHeader = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'first': boxUrl + '?page=true',
        'id': boxUrl,
        'last': boxUrl + '?page=true',
        'totalItems': 0,
        'type': 'OrderedCollection'
    }
    boxItems = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': boxUrl + pageStr,
        'orderedItems': [
        ],
        'partOf': boxUrl,
        'type': 'OrderedCollectionPage'
    }

    if isModerator(base_dir, nickname):
        moderationIndexFile = base_dir + '/accounts/moderation.txt'
        if os.path.isfile(moderationIndexFile):
            with open(moderationIndexFile, 'r') as f:
                lines = f.readlines()
            boxHeader['totalItems'] = len(lines)
            if headerOnly:
                return boxHeader

            pageLines = []
            if len(lines) > 0:
                endLineNumber = len(lines) - 1 - int(itemsPerPage * pageNumber)
                if endLineNumber < 0:
                    endLineNumber = 0
                startLineNumber = \
                    len(lines) - 1 - int(itemsPerPage * (pageNumber - 1))
                if startLineNumber < 0:
                    startLineNumber = 0
                lineNumber = startLineNumber
                while lineNumber >= endLineNumber:
                    pageLines.append(lines[lineNumber].strip('\n').strip('\r'))
                    lineNumber -= 1

            for postUrl in pageLines:
                postFilename = \
                    boxDir + '/' + postUrl.replace('/', '#') + '.json'
                if os.path.isfile(postFilename):
                    postJsonObject = loadJson(postFilename)
                    if postJsonObject:
                        boxItems['orderedItems'].append(postJsonObject)

    if headerOnly:
        return boxHeader
    return boxItems


def isImageMedia(session, base_dir: str, http_prefix: str,
                 nickname: str, domain: str,
                 postJsonObject: {}, translate: {},
                 yt_replace_domain: str,
                 twitter_replacement_domain: str,
                 allow_local_network_access: bool,
                 recentPostsCache: {}, debug: bool,
                 systemLanguage: str,
                 domainFull: str, personCache: {},
                 signingPrivateKeyPem: str) -> bool:
    """Returns true if the given post has attached image media
    """
    if postJsonObject['type'] == 'Announce':
        blockedCache = {}
        postJsonAnnounce = \
            downloadAnnounce(session, base_dir, http_prefix,
                             nickname, domain, postJsonObject,
                             __version__, translate,
                             yt_replace_domain,
                             twitter_replacement_domain,
                             allow_local_network_access,
                             recentPostsCache, debug,
                             systemLanguage,
                             domainFull, personCache,
                             signingPrivateKeyPem,
                             blockedCache)
        if postJsonAnnounce:
            postJsonObject = postJsonAnnounce
    if postJsonObject['type'] != 'Create':
        return False
    if not hasObjectDict(postJsonObject):
        return False
    if postJsonObject['object'].get('moderationStatus'):
        return False
    if postJsonObject['object']['type'] != 'Note' and \
       postJsonObject['object']['type'] != 'Page' and \
       postJsonObject['object']['type'] != 'Event' and \
       postJsonObject['object']['type'] != 'Article':
        return False
    if not postJsonObject['object'].get('attachment'):
        return False
    if not isinstance(postJsonObject['object']['attachment'], list):
        return False
    for attach in postJsonObject['object']['attachment']:
        if attach.get('mediaType') and attach.get('url'):
            if attach['mediaType'].startswith('image/') or \
               attach['mediaType'].startswith('audio/') or \
               attach['mediaType'].startswith('video/'):
                return True
    return False


def _addPostStringToTimeline(postStr: str, boxname: str,
                             postsInBox: [], boxActor: str) -> bool:
    """ is this a valid timeline post?
    """
    # must be a recognized ActivityPub type
    if ('"Note"' in postStr or
        '"EncryptedMessage"' in postStr or
        '"Event"' in postStr or
        '"Article"' in postStr or
        '"Patch"' in postStr or
        '"Announce"' in postStr or
        ('"Question"' in postStr and
         ('"Create"' in postStr or '"Update"' in postStr))):

        if boxname == 'dm':
            if '#Public' in postStr or '/followers' in postStr:
                return False
        elif boxname == 'tlreplies':
            if boxActor not in postStr:
                return False
        elif (boxname == 'tlblogs' or
              boxname == 'tlnews' or
              boxname == 'tlfeatures'):
            if '"Create"' not in postStr:
                return False
            if '"Article"' not in postStr:
                return False
        elif boxname == 'tlmedia':
            if '"Create"' in postStr:
                if ('mediaType' not in postStr or
                    ('image/' not in postStr and
                     'video/' not in postStr and
                     'audio/' not in postStr)):
                    return False
        # add the post to the dictionary
        postsInBox.append(postStr)
        return True
    return False


def _addPostToTimeline(filePath: str, boxname: str,
                       postsInBox: [], boxActor: str) -> bool:
    """ Reads a post from file and decides whether it is valid
    """
    with open(filePath, 'r') as postFile:
        postStr = postFile.read()

        if filePath.endswith('.json'):
            repliesFilename = filePath.replace('.json', '.replies')
            if os.path.isfile(repliesFilename):
                # append a replies identifier, which will later be removed
                postStr += '<hasReplies>'

        return _addPostStringToTimeline(postStr, boxname, postsInBox, boxActor)
    return False


def removePostInteractions(postJsonObject: {}, force: bool) -> bool:
    """ Don't show likes, replies, bookmarks, DMs or shares (announces) to
    unauthorized viewers. This makes the timeline less useful to
    marketers and other surveillance-oriented organizations.
    Returns False if this is a private post
    """
    hasObject = False
    if hasObjectDict(postJsonObject):
        hasObject = True
    if hasObject:
        postObj = postJsonObject['object']
        if not force:
            # If not authorized and it's a private post
            # then just don't show it within timelines
            if not isPublicPost(postJsonObject):
                return False
    else:
        postObj = postJsonObject

    # clear the likes
    if postObj.get('likes'):
        postObj['likes'] = {
            'items': []
        }
    # clear the reactions
    if postObj.get('reactions'):
        postObj['reactions'] = {
            'items': []
        }
    # remove other collections
    removeCollections = (
        'replies', 'shares', 'bookmarks', 'ignores'
    )
    for removeName in removeCollections:
        if postObj.get(removeName):
            postObj[removeName] = {}
    return True


def _passedNewswireVoting(newswire_votes_threshold: int,
                          base_dir: str, domain: str,
                          postFilename: str,
                          positive_voting: bool,
                          voting_time_mins: int) -> bool:
    """Returns true if the post has passed through newswire voting
    """
    # apply votes within this timeline
    if newswire_votes_threshold <= 0:
        return True
    # note that the presence of an arrival file also indicates
    # that this post is moderated
    arrivalDate = \
        locateNewsArrival(base_dir, domain, postFilename)
    if not arrivalDate:
        return True
    # how long has elapsed since this post arrived?
    currDate = datetime.datetime.utcnow()
    timeDiffMins = \
        int((currDate - arrivalDate).total_seconds() / 60)
    # has the voting time elapsed?
    if timeDiffMins < voting_time_mins:
        # voting is still happening, so don't add this
        # post to the timeline
        return False
    # if there a votes file for this post?
    votesFilename = \
        locateNewsVotes(base_dir, domain, postFilename)
    if not votesFilename:
        return True
    # load the votes file and count the votes
    votesJson = loadJson(votesFilename, 0, 2)
    if not votesJson:
        return True
    if not positive_voting:
        if votesOnNewswireItem(votesJson) >= \
           newswire_votes_threshold:
            # Too many veto votes.
            # Continue without incrementing
            # the posts counter
            return False
    else:
        if votesOnNewswireItem < \
           newswire_votes_threshold:
            # Not enough votes.
            # Continue without incrementing
            # the posts counter
            return False
    return True


def _createBoxIndexed(recentPostsCache: {},
                      session, base_dir: str, boxname: str,
                      nickname: str, domain: str, port: int, http_prefix: str,
                      itemsPerPage: int, headerOnly: bool, authorized: bool,
                      newswire_votes_threshold: int, positive_voting: bool,
                      voting_time_mins: int, pageNumber: int) -> {}:
    """Constructs the box feed for a person with the given nickname
    """
    if not authorized or not pageNumber:
        pageNumber = 1

    if boxname != 'inbox' and boxname != 'dm' and \
       boxname != 'tlreplies' and boxname != 'tlmedia' and \
       boxname != 'tlblogs' and boxname != 'tlnews' and \
       boxname != 'tlfeatures' and \
       boxname != 'outbox' and boxname != 'tlbookmarks' and \
       boxname != 'bookmarks':
        print('ERROR: invalid boxname ' + boxname)
        return None

    # bookmarks and events timelines are like the inbox
    # but have their own separate index
    indexBoxName = boxname
    timelineNickname = nickname
    if boxname == "tlbookmarks":
        boxname = "bookmarks"
        indexBoxName = boxname
    elif boxname == "tlfeatures":
        boxname = "tlblogs"
        indexBoxName = boxname
        timelineNickname = 'news'

    originalDomain = domain
    domain = getFullDomain(domain, port)

    boxActor = localActorUrl(http_prefix, nickname, domain)

    pageStr = '?page=true'
    if pageNumber:
        if pageNumber < 1:
            pageNumber = 1
        try:
            pageStr = '?page=' + str(pageNumber)
        except BaseException:
            print('EX: _createBoxIndexed ' +
                  'unable to convert page number to string')
            pass
    boxUrl = localActorUrl(http_prefix, nickname, domain) + '/' + boxname
    boxHeader = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'first': boxUrl + '?page=true',
        'id': boxUrl,
        'last': boxUrl + '?page=true',
        'totalItems': 0,
        'type': 'OrderedCollection'
    }
    boxItems = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': boxUrl + pageStr,
        'orderedItems': [
        ],
        'partOf': boxUrl,
        'type': 'OrderedCollectionPage'
    }

    postsInBox = []
    postUrlsInBox = []

    indexFilename = \
        acctDir(base_dir, timelineNickname, originalDomain) + \
        '/' + indexBoxName + '.index'
    totalPostsCount = 0
    postsAddedToTimeline = 0
    if os.path.isfile(indexFilename):
        with open(indexFilename, 'r') as indexFile:
            postsAddedToTimeline = 0
            while postsAddedToTimeline < itemsPerPage:
                postFilename = indexFile.readline()

                if not postFilename:
                    break

                # Has this post passed through the newswire voting stage?
                if not _passedNewswireVoting(newswire_votes_threshold,
                                             base_dir, domain,
                                             postFilename,
                                             positive_voting,
                                             voting_time_mins):
                    continue

                # Skip through any posts previous to the current page
                if totalPostsCount < int((pageNumber - 1) * itemsPerPage):
                    totalPostsCount += 1
                    continue

                # if this is a full path then remove the directories
                if '/' in postFilename:
                    postFilename = postFilename.split('/')[-1]

                # filename of the post without any extension or path
                # This should also correspond to any index entry in
                # the posts cache
                postUrl = \
                    postFilename.replace('\n', '').replace('\r', '')
                postUrl = postUrl.replace('.json', '').strip()

                if postUrl in postUrlsInBox:
                    continue

                # is the post cached in memory?
                if recentPostsCache.get('index'):
                    if postUrl in recentPostsCache['index']:
                        if recentPostsCache['json'].get(postUrl):
                            url = recentPostsCache['json'][postUrl]
                            if _addPostStringToTimeline(url,
                                                        boxname, postsInBox,
                                                        boxActor):
                                totalPostsCount += 1
                                postsAddedToTimeline += 1
                                postUrlsInBox.append(postUrl)
                                continue
                            else:
                                print('Post not added to timeline')

                # read the post from file
                fullPostFilename = \
                    locatePost(base_dir, nickname,
                               originalDomain, postUrl, False)
                if fullPostFilename:
                    # has the post been rejected?
                    if os.path.isfile(fullPostFilename + '.reject'):
                        continue

                    if _addPostToTimeline(fullPostFilename, boxname,
                                          postsInBox, boxActor):
                        postsAddedToTimeline += 1
                        totalPostsCount += 1
                        postUrlsInBox.append(postUrl)
                    else:
                        print('WARN: Unable to add post ' + postUrl +
                              ' nickname ' + nickname +
                              ' timeline ' + boxname)
                else:
                    if timelineNickname != nickname:
                        # if this is the features timeline
                        fullPostFilename = \
                            locatePost(base_dir, timelineNickname,
                                       originalDomain, postUrl, False)
                        if fullPostFilename:
                            if _addPostToTimeline(fullPostFilename, boxname,
                                                  postsInBox, boxActor):
                                postsAddedToTimeline += 1
                                totalPostsCount += 1
                                postUrlsInBox.append(postUrl)
                            else:
                                print('WARN: Unable to add features post ' +
                                      postUrl + ' nickname ' + nickname +
                                      ' timeline ' + boxname)
                        else:
                            print('WARN: features timeline. ' +
                                  'Unable to locate post ' + postUrl)
                    else:
                        print('WARN: Unable to locate post ' + postUrl +
                              ' nickname ' + nickname)

    if totalPostsCount < 3:
        print('Posts added to json timeline ' + boxname + ': ' +
              str(postsAddedToTimeline))

    # Generate first and last entries within header
    if totalPostsCount > 0:
        lastPage = int(totalPostsCount / itemsPerPage)
        if lastPage < 1:
            lastPage = 1
        boxHeader['last'] = \
            localActorUrl(http_prefix, nickname, domain) + \
            '/' + boxname + '?page=' + str(lastPage)

    if headerOnly:
        boxHeader['totalItems'] = len(postsInBox)
        prevPageStr = 'true'
        if pageNumber > 1:
            prevPageStr = str(pageNumber - 1)
        boxHeader['prev'] = \
            localActorUrl(http_prefix, nickname, domain) + \
            '/' + boxname + '?page=' + prevPageStr

        nextPageStr = str(pageNumber + 1)
        boxHeader['next'] = \
            localActorUrl(http_prefix, nickname, domain) + \
            '/' + boxname + '?page=' + nextPageStr
        return boxHeader

    for postStr in postsInBox:
        # Check if the post has replies
        hasReplies = False
        if postStr.endswith('<hasReplies>'):
            hasReplies = True
            # remove the replies identifier
            postStr = postStr.replace('<hasReplies>', '')

        p = None
        try:
            p = json.loads(postStr)
        except BaseException:
            print('EX: _createBoxIndexed unable to load json ' + postStr)
            continue

        # Does this post have replies?
        # This will be used to indicate that replies exist within the html
        # created by individualPostAsHtml
        p['hasReplies'] = hasReplies

        if not authorized:
            if not removePostInteractions(p, False):
                continue

        boxItems['orderedItems'].append(p)

    return boxItems


def expireCache(base_dir: str, personCache: {},
                http_prefix: str, archiveDir: str,
                recentPostsCache: {},
                maxPostsInBox=32000):
    """Thread used to expire actors from the cache and archive old posts
    """
    while True:
        # once per day
        time.sleep(60 * 60 * 24)
        expirePersonCache(personCache)
        archivePosts(base_dir, http_prefix, archiveDir, recentPostsCache,
                     maxPostsInBox)


def archivePosts(base_dir: str, http_prefix: str, archiveDir: str,
                 recentPostsCache: {},
                 maxPostsInBox=32000) -> None:
    """Archives posts for all accounts
    """
    if maxPostsInBox == 0:
        return

    if archiveDir:
        if not os.path.isdir(archiveDir):
            os.mkdir(archiveDir)

    if archiveDir:
        if not os.path.isdir(archiveDir + '/accounts'):
            os.mkdir(archiveDir + '/accounts')

    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if '@' in handle:
                nickname = handle.split('@')[0]
                domain = handle.split('@')[1]
                archiveSubdir = None
                if archiveDir:
                    if not os.path.isdir(archiveDir + '/accounts/' + handle):
                        os.mkdir(archiveDir + '/accounts/' + handle)
                    if not os.path.isdir(archiveDir + '/accounts/' +
                                         handle + '/inbox'):
                        os.mkdir(archiveDir + '/accounts/' +
                                 handle + '/inbox')
                    if not os.path.isdir(archiveDir + '/accounts/' +
                                         handle + '/outbox'):
                        os.mkdir(archiveDir + '/accounts/' +
                                 handle + '/outbox')
                    archiveSubdir = archiveDir + '/accounts/' + \
                        handle + '/inbox'
                archivePostsForPerson(http_prefix, nickname, domain, base_dir,
                                      'inbox', archiveSubdir,
                                      recentPostsCache, maxPostsInBox)
                if archiveDir:
                    archiveSubdir = archiveDir + '/accounts/' + \
                        handle + '/outbox'
                archivePostsForPerson(http_prefix, nickname, domain, base_dir,
                                      'outbox', archiveSubdir,
                                      recentPostsCache, maxPostsInBox)
        break


def archivePostsForPerson(http_prefix: str, nickname: str, domain: str,
                          base_dir: str,
                          boxname: str, archiveDir: str,
                          recentPostsCache: {},
                          maxPostsInBox=32000) -> None:
    """Retain a maximum number of posts within the given box
    Move any others to an archive directory
    """
    if boxname != 'inbox' and boxname != 'outbox':
        return
    if archiveDir:
        if not os.path.isdir(archiveDir):
            os.mkdir(archiveDir)
    boxDir = createPersonDir(nickname, domain, base_dir, boxname)
    postsInBox = os.scandir(boxDir)
    noOfPosts = 0
    for f in postsInBox:
        noOfPosts += 1
    if noOfPosts <= maxPostsInBox:
        print('Checked ' + str(noOfPosts) + ' ' + boxname +
              ' posts for ' + nickname + '@' + domain)
        return

    # remove entries from the index
    handle = nickname + '@' + domain
    indexFilename = base_dir + '/accounts/' + handle + '/' + boxname + '.index'
    if os.path.isfile(indexFilename):
        indexCtr = 0
        # get the existing index entries as a string
        newIndex = ''
        with open(indexFilename, 'r') as indexFile:
            for postId in indexFile:
                newIndex += postId
                indexCtr += 1
                if indexCtr >= maxPostsInBox:
                    break
        # save the new index file
        if len(newIndex) > 0:
            with open(indexFilename, 'w+') as indexFile:
                indexFile.write(newIndex)

    postsInBoxDict = {}
    postsCtr = 0
    postsInBox = os.scandir(boxDir)
    for postFilename in postsInBox:
        postFilename = postFilename.name
        if not postFilename.endswith('.json'):
            continue
        # Time of file creation
        fullFilename = os.path.join(boxDir, postFilename)
        if os.path.isfile(fullFilename):
            content = open(fullFilename).read()
            if '"published":' in content:
                publishedStr = content.split('"published":')[1]
                if '"' in publishedStr:
                    publishedStr = publishedStr.split('"')[1]
                    if publishedStr.endswith('Z'):
                        postsInBoxDict[publishedStr] = postFilename
                        postsCtr += 1

    noOfPosts = postsCtr
    if noOfPosts <= maxPostsInBox:
        print('Checked ' + str(noOfPosts) + ' ' + boxname +
              ' posts for ' + nickname + '@' + domain)
        return

    # sort the list in ascending order of date
    postsInBoxSorted = \
        OrderedDict(sorted(postsInBoxDict.items(), reverse=False))

    # directory containing cached html posts
    postCacheDir = boxDir.replace('/' + boxname, '/postcache')

    removeCtr = 0
    for publishedStr, postFilename in postsInBoxSorted.items():
        filePath = os.path.join(boxDir, postFilename)
        if not os.path.isfile(filePath):
            continue
        if archiveDir:
            archivePath = os.path.join(archiveDir, postFilename)
            os.rename(filePath, archivePath)

            extensions = ('replies', 'votes', 'arrived', 'muted')
            for ext in extensions:
                extPath = filePath.replace('.json', '.' + ext)
                if os.path.isfile(extPath):
                    os.rename(extPath,
                              archivePath.replace('.json', '.' + ext))
                else:
                    extPath = filePath.replace('.json',
                                               '.json.' + ext)
                    if os.path.isfile(extPath):
                        os.rename(extPath,
                                  archivePath.replace('.json', '.json.' + ext))
        else:
            deletePost(base_dir, http_prefix, nickname, domain,
                       filePath, False, recentPostsCache)

        # remove cached html posts
        postCacheFilename = \
            os.path.join(postCacheDir, postFilename).replace('.json', '.html')
        if os.path.isfile(postCacheFilename):
            try:
                os.remove(postCacheFilename)
            except OSError:
                print('EX: archivePostsForPerson unable to delete ' +
                      postCacheFilename)

        noOfPosts -= 1
        removeCtr += 1
        if noOfPosts <= maxPostsInBox:
            break
    if archiveDir:
        print('Archived ' + str(removeCtr) + ' ' + boxname +
              ' posts for ' + nickname + '@' + domain)
    else:
        print('Removed ' + str(removeCtr) + ' ' + boxname +
              ' posts for ' + nickname + '@' + domain)
    print(nickname + '@' + domain + ' has ' + str(noOfPosts) +
          ' in ' + boxname)


def getPublicPostsOfPerson(base_dir: str, nickname: str, domain: str,
                           raw: bool, simple: bool, proxyType: str,
                           port: int, http_prefix: str,
                           debug: bool, project_version: str,
                           systemLanguage: str,
                           signingPrivateKeyPem: str,
                           originDomain: str) -> None:
    """ This is really just for test purposes
    """
    if debug:
        if signingPrivateKeyPem:
            print('Signing key available')
        else:
            print('Signing key missing')

    print('Starting new session for getting public posts')
    session = createSession(proxyType)
    if not session:
        if debug:
            print('Session was not created')
        return
    personCache = {}
    cachedWebfingers = {}
    federationList = []
    groupAccount = False
    if nickname.startswith('!'):
        nickname = nickname[1:]
        groupAccount = True
    domainFull = getFullDomain(domain, port)
    handle = http_prefix + "://" + domainFull + "/@" + nickname

    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cachedWebfingers,
                        originDomain, project_version, debug, groupAccount,
                        signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('No webfinger result was returned for ' + handle)
        sys.exit()
    if not isinstance(wfRequest, dict):
        print('Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        sys.exit()

    if debug:
        print('Getting the outbox for ' + handle)
    (personUrl, pubKeyId, pubKey, personId, shaedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix,
                                    nickname, domain, 'outbox',
                                    62524)
    if debug:
        print('Actor url: ' + str(personId))
    if not personId:
        return

    max_mentions = 10
    max_emoji = 10
    maxAttachments = 5
    _getPosts(session, personUrl, 30, max_mentions, max_emoji,
              maxAttachments, federationList,
              personCache, raw, simple, debug,
              project_version, http_prefix, originDomain, systemLanguage,
              signingPrivateKeyPem)


def getPublicPostDomains(session, base_dir: str, nickname: str, domain: str,
                         originDomain: str,
                         proxyType: str, port: int, http_prefix: str,
                         debug: bool, project_version: str,
                         wordFrequency: {}, domainList: [],
                         systemLanguage: str,
                         signingPrivateKeyPem: str) -> []:
    """ Returns a list of domains referenced within public posts
    """
    if not session:
        session = createSession(proxyType)
    if not session:
        return domainList
    personCache = {}
    cachedWebfingers = {}
    federationList = []

    domainFull = getFullDomain(domain, port)
    handle = http_prefix + "://" + domainFull + "/@" + nickname
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cachedWebfingers,
                        domain, project_version, debug, False,
                        signingPrivateKeyPem)
    if not wfRequest:
        return domainList
    if not isinstance(wfRequest, dict):
        print('Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return domainList

    (personUrl, pubKeyId, pubKey, personId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix,
                                    nickname, domain, 'outbox',
                                    92522)
    max_mentions = 99
    max_emoji = 99
    maxAttachments = 5
    postDomains = \
        getPostDomains(session, personUrl, 64, max_mentions, max_emoji,
                       maxAttachments, federationList,
                       personCache, debug,
                       project_version, http_prefix, domain,
                       wordFrequency, domainList, systemLanguage,
                       signingPrivateKeyPem)
    postDomains.sort()
    return postDomains


def downloadFollowCollection(signingPrivateKeyPem: str,
                             followType: str,
                             session, http_prefix: str,
                             actor: str, pageNumber: int,
                             noOfPages: int, debug: bool) -> []:
    """Returns a list of following/followers for the given actor
    by downloading the json for their following/followers collection
    """
    prof = 'https://www.w3.org/ns/activitystreams'
    if '/channel/' not in actor or '/accounts/' not in actor:
        acceptStr = \
            'application/activity+json; ' + \
            'profile="' + prof + '"'
        sessionHeaders = {
            'Accept': acceptStr
        }
    else:
        acceptStr = \
            'application/ld+json; ' + \
            'profile="' + prof + '"'
        sessionHeaders = {
            'Accept': acceptStr
        }
    result = []
    for pageCtr in range(noOfPages):
        url = actor + '/' + followType + '?page=' + str(pageNumber + pageCtr)
        followersJson = \
            getJson(signingPrivateKeyPem, session, url, sessionHeaders, None,
                    debug, __version__, http_prefix, None)
        if followersJson:
            if followersJson.get('orderedItems'):
                for followerActor in followersJson['orderedItems']:
                    if followerActor not in result:
                        result.append(followerActor)
            elif followersJson.get('items'):
                for followerActor in followersJson['items']:
                    if followerActor not in result:
                        result.append(followerActor)
            else:
                break
        else:
            break
    return result


def getPublicPostInfo(session, base_dir: str, nickname: str, domain: str,
                      originDomain: str,
                      proxyType: str, port: int, http_prefix: str,
                      debug: bool, project_version: str,
                      wordFrequency: {}, systemLanguage: str,
                      signingPrivateKeyPem: str) -> []:
    """ Returns a dict of domains referenced within public posts
    """
    if not session:
        session = createSession(proxyType)
    if not session:
        return {}
    personCache = {}
    cachedWebfingers = {}
    federationList = []

    domainFull = getFullDomain(domain, port)
    handle = http_prefix + "://" + domainFull + "/@" + nickname
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cachedWebfingers,
                        domain, project_version, debug, False,
                        signingPrivateKeyPem)
    if not wfRequest:
        return {}
    if not isinstance(wfRequest, dict):
        print('Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return {}

    (personUrl, pubKeyId, pubKey, personId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix,
                                    nickname, domain, 'outbox',
                                    13863)
    max_mentions = 99
    max_emoji = 99
    maxAttachments = 5
    maxPosts = 64
    postDomains = \
        getPostDomains(session, personUrl, maxPosts, max_mentions, max_emoji,
                       maxAttachments, federationList,
                       personCache, debug,
                       project_version, http_prefix, domain,
                       wordFrequency, [], systemLanguage, signingPrivateKeyPem)
    postDomains.sort()
    domainsInfo = {}
    for d in postDomains:
        if not domainsInfo.get(d):
            domainsInfo[d] = []

    blockedPosts = \
        _getPostsForBlockedDomains(base_dir, session, personUrl, maxPosts,
                                   max_mentions,
                                   max_emoji, maxAttachments,
                                   federationList,
                                   personCache,
                                   debug,
                                   project_version, http_prefix,
                                   domain, signingPrivateKeyPem)
    for blockedDomain, postUrlList in blockedPosts.items():
        domainsInfo[blockedDomain] += postUrlList

    return domainsInfo


def getPublicPostDomainsBlocked(session, base_dir: str,
                                nickname: str, domain: str,
                                proxyType: str, port: int, http_prefix: str,
                                debug: bool, project_version: str,
                                wordFrequency: {}, domainList: [],
                                systemLanguage: str,
                                signingPrivateKeyPem: str) -> []:
    """ Returns a list of domains referenced within public posts which
    are globally blocked on this instance
    """
    originDomain = domain
    postDomains = \
        getPublicPostDomains(session, base_dir, nickname, domain,
                             originDomain,
                             proxyType, port, http_prefix,
                             debug, project_version,
                             wordFrequency, domainList, systemLanguage,
                             signingPrivateKeyPem)
    if not postDomains:
        return []

    blockingFilename = base_dir + '/accounts/blocking.txt'
    if not os.path.isfile(blockingFilename):
        return []

    # read the blocked domains as a single string
    blockedStr = ''
    with open(blockingFilename, 'r') as fp:
        blockedStr = fp.read()

    blockedDomains = []
    for domainName in postDomains:
        if '@' not in domainName:
            continue
        # get the domain after the @
        domainName = domainName.split('@')[1].strip()
        if isEvil(domainName):
            blockedDomains.append(domainName)
            continue
        if domainName in blockedStr:
            blockedDomains.append(domainName)

    return blockedDomains


def _getNonMutualsOfPerson(base_dir: str,
                           nickname: str, domain: str) -> []:
    """Returns the followers who are not mutuals of a person
    i.e. accounts which follow you but you don't follow them
    """
    followers = \
        getFollowersList(base_dir, nickname, domain, 'followers.txt')
    following = \
        getFollowersList(base_dir, nickname, domain, 'following.txt')
    nonMutuals = []
    for handle in followers:
        if handle not in following:
            nonMutuals.append(handle)
    return nonMutuals


def checkDomains(session, base_dir: str,
                 nickname: str, domain: str,
                 proxyType: str, port: int, http_prefix: str,
                 debug: bool, project_version: str,
                 maxBlockedDomains: int, singleCheck: bool,
                 systemLanguage: str,
                 signingPrivateKeyPem: str) -> None:
    """Checks follower accounts for references to globally blocked domains
    """
    wordFrequency = {}
    nonMutuals = _getNonMutualsOfPerson(base_dir, nickname, domain)
    if not nonMutuals:
        print('No non-mutual followers were found')
        return
    followerWarningFilename = base_dir + '/accounts/followerWarnings.txt'
    updateFollowerWarnings = False
    followerWarningStr = ''
    if os.path.isfile(followerWarningFilename):
        with open(followerWarningFilename, 'r') as fp:
            followerWarningStr = fp.read()

    if singleCheck:
        # checks a single random non-mutual
        index = random.randrange(0, len(nonMutuals))
        handle = nonMutuals[index]
        if '@' in handle:
            nonMutualNickname = handle.split('@')[0]
            nonMutualDomain = handle.split('@')[1].strip()
            blockedDomains = \
                getPublicPostDomainsBlocked(session, base_dir,
                                            nonMutualNickname,
                                            nonMutualDomain,
                                            proxyType, port, http_prefix,
                                            debug, project_version,
                                            wordFrequency, [],
                                            systemLanguage,
                                            signingPrivateKeyPem)
            if blockedDomains:
                if len(blockedDomains) > maxBlockedDomains:
                    followerWarningStr += handle + '\n'
                    updateFollowerWarnings = True
    else:
        # checks all non-mutuals
        for handle in nonMutuals:
            if '@' not in handle:
                continue
            if handle in followerWarningStr:
                continue
            nonMutualNickname = handle.split('@')[0]
            nonMutualDomain = handle.split('@')[1].strip()
            blockedDomains = \
                getPublicPostDomainsBlocked(session, base_dir,
                                            nonMutualNickname,
                                            nonMutualDomain,
                                            proxyType, port, http_prefix,
                                            debug, project_version,
                                            wordFrequency, [],
                                            systemLanguage,
                                            signingPrivateKeyPem)
            if blockedDomains:
                print(handle)
                for d in blockedDomains:
                    print('  ' + d)
                if len(blockedDomains) > maxBlockedDomains:
                    followerWarningStr += handle + '\n'
                    updateFollowerWarnings = True

    if updateFollowerWarnings and followerWarningStr:
        with open(followerWarningFilename, 'w+') as fp:
            fp.write(followerWarningStr)
        if not singleCheck:
            print(followerWarningStr)


def populateRepliesJson(base_dir: str, nickname: str, domain: str,
                        postRepliesFilename: str, authorized: bool,
                        repliesJson: {}) -> None:
    pubStr = 'https://www.w3.org/ns/activitystreams#Public'
    # populate the items list with replies
    repliesBoxes = ('outbox', 'inbox')
    with open(postRepliesFilename, 'r') as repliesFile:
        for messageId in repliesFile:
            replyFound = False
            # examine inbox and outbox
            for boxname in repliesBoxes:
                messageId2 = messageId.replace('\n', '').replace('\r', '')
                searchFilename = \
                    acctDir(base_dir, nickname, domain) + '/' + \
                    boxname + '/' + \
                    messageId2.replace('/', '#') + '.json'
                if os.path.isfile(searchFilename):
                    if authorized or \
                       pubStr in open(searchFilename).read():
                        postJsonObject = loadJson(searchFilename)
                        if postJsonObject:
                            if postJsonObject['object'].get('cc'):
                                pjo = postJsonObject
                                if (authorized or
                                    (pubStr in pjo['object']['to'] or
                                     pubStr in pjo['object']['cc'])):
                                    repliesJson['orderedItems'].append(pjo)
                                    replyFound = True
                            else:
                                if authorized or \
                                   pubStr in postJsonObject['object']['to']:
                                    pjo = postJsonObject
                                    repliesJson['orderedItems'].append(pjo)
                                    replyFound = True
                    break
            # if not in either inbox or outbox then examine the shared inbox
            if not replyFound:
                messageId2 = messageId.replace('\n', '').replace('\r', '')
                searchFilename = \
                    base_dir + \
                    '/accounts/inbox@' + \
                    domain + '/inbox/' + \
                    messageId2.replace('/', '#') + '.json'
                if os.path.isfile(searchFilename):
                    if authorized or \
                       pubStr in open(searchFilename).read():
                        # get the json of the reply and append it to
                        # the collection
                        postJsonObject = loadJson(searchFilename)
                        if postJsonObject:
                            if postJsonObject['object'].get('cc'):
                                pjo = postJsonObject
                                if (authorized or
                                    (pubStr in pjo['object']['to'] or
                                     pubStr in pjo['object']['cc'])):
                                    pjo = postJsonObject
                                    repliesJson['orderedItems'].append(pjo)
                            else:
                                if authorized or \
                                   pubStr in postJsonObject['object']['to']:
                                    pjo = postJsonObject
                                    repliesJson['orderedItems'].append(pjo)


def _rejectAnnounce(announceFilename: str,
                    base_dir: str, nickname: str, domain: str,
                    announcePostId: str, recentPostsCache: {}):
    """Marks an announce as rejected
    """
    rejectPostId(base_dir, nickname, domain, announcePostId, recentPostsCache)

    # reject the post referenced by the announce activity object
    if not os.path.isfile(announceFilename + '.reject'):
        with open(announceFilename + '.reject', 'w+') as rejectAnnounceFile:
            rejectAnnounceFile.write('\n')


def downloadAnnounce(session, base_dir: str, http_prefix: str,
                     nickname: str, domain: str,
                     postJsonObject: {}, project_version: str,
                     translate: {},
                     yt_replace_domain: str,
                     twitter_replacement_domain: str,
                     allow_local_network_access: bool,
                     recentPostsCache: {}, debug: bool,
                     systemLanguage: str,
                     domainFull: str, personCache: {},
                     signingPrivateKeyPem: str,
                     blockedCache: {}) -> {}:
    """Download the post referenced by an announce
    """
    if not postJsonObject.get('object'):
        return None
    if not isinstance(postJsonObject['object'], str):
        return None
    # ignore self-boosts
    if postJsonObject['actor'] in postJsonObject['object']:
        return None

    # get the announced post
    announceCacheDir = base_dir + '/cache/announce/' + nickname
    if not os.path.isdir(announceCacheDir):
        os.mkdir(announceCacheDir)

    postId = None
    if postJsonObject.get('id'):
        postId = removeIdEnding(postJsonObject['id'])
    announceFilename = \
        announceCacheDir + '/' + \
        postJsonObject['object'].replace('/', '#') + '.json'

    if os.path.isfile(announceFilename + '.reject'):
        return None

    if os.path.isfile(announceFilename):
        if debug:
            print('Reading cached Announce content for ' +
                  postJsonObject['object'])
        postJsonObject = loadJson(announceFilename)
        if postJsonObject:
            return postJsonObject
    else:
        profileStr = 'https://www.w3.org/ns/activitystreams'
        acceptStr = \
            'application/activity+json; ' + \
            'profile="' + profileStr + '"'
        asHeader = {
            'Accept': acceptStr
        }
        if '/channel/' in postJsonObject['actor'] or \
           '/accounts/' in postJsonObject['actor']:
            acceptStr = \
                'application/ld+json; ' + \
                'profile="' + profileStr + '"'
            asHeader = {
                'Accept': acceptStr
            }
        actorNickname = getNicknameFromActor(postJsonObject['actor'])
        actorDomain, actorPort = getDomainFromActor(postJsonObject['actor'])
        if not actorDomain:
            print('Announce actor does not contain a ' +
                  'valid domain or port number: ' +
                  str(postJsonObject['actor']))
            return None
        if isBlocked(base_dir, nickname, domain, actorNickname, actorDomain):
            print('Announce download blocked actor: ' +
                  actorNickname + '@' + actorDomain)
            return None
        objectNickname = getNicknameFromActor(postJsonObject['object'])
        objectDomain, objectPort = getDomainFromActor(postJsonObject['object'])
        if not objectDomain:
            print('Announce object does not contain a ' +
                  'valid domain or port number: ' +
                  str(postJsonObject['object']))
            return None
        if isBlocked(base_dir, nickname, domain, objectNickname, objectDomain):
            if objectNickname and objectDomain:
                print('Announce download blocked object: ' +
                      objectNickname + '@' + objectDomain)
            else:
                print('Announce download blocked object: ' +
                      str(postJsonObject['object']))
            return None
        if debug:
            print('Downloading Announce content for ' +
                  postJsonObject['object'])
        announcedJson = \
            getJson(signingPrivateKeyPem, session,
                    postJsonObject['object'],
                    asHeader, None, debug, project_version,
                    http_prefix, domain)

        if not announcedJson:
            return None

        if not isinstance(announcedJson, dict):
            print('WARN: announce json is not a dict - ' +
                  postJsonObject['object'])
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if not announcedJson.get('id'):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if not announcedJson.get('type'):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if announcedJson['type'] == 'Video':
            convertedJson = \
                convertVideoToNote(base_dir, nickname, domain,
                                   systemLanguage,
                                   announcedJson, blockedCache)
            if convertedJson:
                announcedJson = convertedJson
        if '/statuses/' not in announcedJson['id']:
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if not hasUsersPath(announcedJson['id']):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if announcedJson['type'] != 'Note' and \
           announcedJson['type'] != 'Page' and \
           announcedJson['type'] != 'Article':
            # You can only announce Note or Article types
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if not announcedJson.get('content'):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if not announcedJson.get('published'):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if not validPostDate(announcedJson['published'], 90, debug):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None
        if not understoodPostLanguage(base_dir, nickname, domain,
                                      announcedJson, systemLanguage,
                                      http_prefix, domainFull,
                                      personCache):
            return None
        # Check the content of the announce
        contentStr = announcedJson['content']
        if dangerousMarkup(contentStr, allow_local_network_access):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None

        if isFiltered(base_dir, nickname, domain, contentStr):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None

        if invalidCiphertext(contentStr):
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            print('WARN: Invalid ciphertext within announce ' +
                  str(announcedJson))
            return None

        # remove any long words
        contentStr = removeLongWords(contentStr, 40, [])

        # Prevent the same word from being repeated many times
        contentStr = limitRepeatedWords(contentStr, 6)

        # remove text formatting, such as bold/italics
        contentStr = removeTextFormatting(contentStr)

        # set the content after santitization
        announcedJson['content'] = contentStr

        # wrap in create to be consistent with other posts
        announcedJson = \
            outboxMessageCreateWrap(http_prefix,
                                    actorNickname, actorDomain, actorPort,
                                    announcedJson)
        if announcedJson['type'] != 'Create':
            # Create wrap failed
            _rejectAnnounce(announceFilename,
                            base_dir, nickname, domain, postId,
                            recentPostsCache)
            return None

        # labelAccusatoryPost(postJsonObject, translate)
        # set the id to the original status
        announcedJson['id'] = postJsonObject['object']
        announcedJson['object']['id'] = postJsonObject['object']
        # check that the repeat isn't for a blocked account
        attributedNickname = \
            getNicknameFromActor(announcedJson['object']['id'])
        attributedDomain, attributedPort = \
            getDomainFromActor(announcedJson['object']['id'])
        if attributedNickname and attributedDomain:
            attributedDomain = getFullDomain(attributedDomain, attributedPort)
            if isBlocked(base_dir, nickname, domain,
                         attributedNickname, attributedDomain):
                _rejectAnnounce(announceFilename,
                                base_dir, nickname, domain, postId,
                                recentPostsCache)
                return None
        postJsonObject = announcedJson
        replaceYouTube(postJsonObject, yt_replace_domain, systemLanguage)
        replaceTwitter(postJsonObject, twitter_replacement_domain,
                       systemLanguage)
        if saveJson(postJsonObject, announceFilename):
            return postJsonObject
    return None


def isMuted(base_dir: str, nickname: str, domain: str, postId: str,
            conversationId: str) -> bool:
    """Returns true if the given post is muted
    """
    if conversationId:
        convMutedFilename = \
            acctDir(base_dir, nickname, domain) + '/conversation/' + \
            conversationId.replace('/', '#') + '.muted'
        if os.path.isfile(convMutedFilename):
            return True
    postFilename = locatePost(base_dir, nickname, domain, postId)
    if not postFilename:
        return False
    if os.path.isfile(postFilename + '.muted'):
        return True
    return False


def sendBlockViaServer(base_dir: str, session,
                       fromNickname: str, password: str,
                       fromDomain: str, fromPort: int,
                       http_prefix: str, blockedUrl: str,
                       cachedWebfingers: {}, personCache: {},
                       debug: bool, project_version: str,
                       signingPrivateKeyPem: str) -> {}:
    """Creates a block via c2s
    """
    if not session:
        print('WARN: No session for sendBlockViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    blockActor = localActorUrl(http_prefix, fromNickname, fromDomainFull)
    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = blockActor + '/followers'

    newBlockJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Block',
        'actor': blockActor,
        'object': blockedUrl,
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cachedWebfingers,
                                fromDomain, project_version, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: block webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: block Webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix, fromNickname,
                                    fromDomain, postToBox, 72652)

    if not inboxUrl:
        if debug:
            print('DEBUG: block no ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: block no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(http_prefix, fromDomainFull,
                          session, newBlockJson, [], inboxUrl,
                          headers, 30, True)
    if not postResult:
        print('WARN: block unable to post')

    if debug:
        print('DEBUG: c2s POST block success')

    return newBlockJson


def sendMuteViaServer(base_dir: str, session,
                      fromNickname: str, password: str,
                      fromDomain: str, fromPort: int,
                      http_prefix: str, mutedUrl: str,
                      cachedWebfingers: {}, personCache: {},
                      debug: bool, project_version: str,
                      signingPrivateKeyPem: str) -> {}:
    """Creates a mute via c2s
    """
    if not session:
        print('WARN: No session for sendMuteViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    actor = localActorUrl(http_prefix, fromNickname, fromDomainFull)
    handle = replaceUsersWithAt(actor)

    newMuteJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Ignore',
        'actor': actor,
        'to': [actor],
        'object': mutedUrl
    }

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cachedWebfingers,
                                fromDomain, project_version, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: mute webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: mute Webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix, fromNickname,
                                    fromDomain, postToBox, 72652)

    if not inboxUrl:
        if debug:
            print('DEBUG: mute no ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: mute no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(http_prefix, fromDomainFull,
                          session, newMuteJson, [], inboxUrl,
                          headers, 3, True)
    if postResult is None:
        print('WARN: mute unable to post')

    if debug:
        print('DEBUG: c2s POST mute success')

    return newMuteJson


def sendUndoMuteViaServer(base_dir: str, session,
                          fromNickname: str, password: str,
                          fromDomain: str, fromPort: int,
                          http_prefix: str, mutedUrl: str,
                          cachedWebfingers: {}, personCache: {},
                          debug: bool, project_version: str,
                          signingPrivateKeyPem: str) -> {}:
    """Undoes a mute via c2s
    """
    if not session:
        print('WARN: No session for sendUndoMuteViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    actor = localActorUrl(http_prefix, fromNickname, fromDomainFull)
    handle = replaceUsersWithAt(actor)

    undoMuteJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': actor,
        'to': [actor],
        'object': {
            'type': 'Ignore',
            'actor': actor,
            'to': [actor],
            'object': mutedUrl
        }
    }

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cachedWebfingers,
                                fromDomain, project_version, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: undo mute webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: undo mute Webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    personCache,
                                    project_version, http_prefix, fromNickname,
                                    fromDomain, postToBox, 72652)

    if not inboxUrl:
        if debug:
            print('DEBUG: undo mute no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: undo mute no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(http_prefix, fromDomainFull,
                          session, undoMuteJson, [], inboxUrl,
                          headers, 3, True)
    if postResult is None:
        print('WARN: undo mute unable to post')

    if debug:
        print('DEBUG: c2s POST undo mute success')

    return undoMuteJson


def sendUndoBlockViaServer(base_dir: str, session,
                           fromNickname: str, password: str,
                           fromDomain: str, fromPort: int,
                           http_prefix: str, blockedUrl: str,
                           cachedWebfingers: {}, personCache: {},
                           debug: bool, project_version: str,
                           signingPrivateKeyPem: str) -> {}:
    """Creates a block via c2s
    """
    if not session:
        print('WARN: No session for sendBlockViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    blockActor = localActorUrl(http_prefix, fromNickname, fromDomainFull)
    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = blockActor + '/followers'

    newBlockJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': blockActor,
        'object': {
            'type': 'Block',
            'actor': blockActor,
            'object': blockedUrl,
            'to': [toUrl],
            'cc': [ccUrl]
        }
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cachedWebfingers,
                                fromDomain, project_version, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: unblock webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: unblock webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    base_dir, session, wfRequest, personCache,
                                    project_version, http_prefix, fromNickname,
                                    fromDomain, postToBox, 53892)

    if not inboxUrl:
        if debug:
            print('DEBUG: unblock no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: unblock no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(http_prefix, fromDomainFull,
                          session, newBlockJson, [], inboxUrl,
                          headers, 30, True)
    if not postResult:
        print('WARN: unblock unable to post')

    if debug:
        print('DEBUG: c2s POST unblock success')

    return newBlockJson


def postIsMuted(base_dir: str, nickname: str, domain: str,
                postJsonObject: {}, messageId: str) -> bool:
    """ Returns true if the given post is muted
    """
    isMuted = None
    if 'muted' in postJsonObject:
        isMuted = postJsonObject['muted']
    if isMuted is True or isMuted is False:
        return isMuted

    isMuted = False
    postDir = acctDir(base_dir, nickname, domain)
    muteFilename = \
        postDir + '/inbox/' + messageId.replace('/', '#') + '.json.muted'
    if os.path.isfile(muteFilename):
        isMuted = True
    else:
        muteFilename = \
            postDir + '/outbox/' + messageId.replace('/', '#') + '.json.muted'
        if os.path.isfile(muteFilename):
            isMuted = True
        else:
            muteFilename = \
                base_dir + '/accounts/cache/announce/' + nickname + \
                '/' + messageId.replace('/', '#') + '.json.muted'
            if os.path.isfile(muteFilename):
                isMuted = True
    return isMuted


def c2sBoxJson(base_dir: str, session,
               nickname: str, password: str,
               domain: str, port: int,
               http_prefix: str,
               boxName: str, pageNumber: int,
               debug: bool, signingPrivateKeyPem: str) -> {}:
    """C2S Authenticated GET of posts for a timeline
    """
    if not session:
        print('WARN: No session for c2sBoxJson')
        return None

    domainFull = getFullDomain(domain, port)
    actor = localActorUrl(http_prefix, nickname, domainFull)

    authHeader = createBasicAuthHeader(nickname, password)

    profileStr = 'https://www.w3.org/ns/activitystreams'
    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader,
        'Accept': 'application/ld+json; profile="' + profileStr + '"'
    }

    # GET json
    url = actor + '/' + boxName + '?page=' + str(pageNumber)
    boxJson = getJson(signingPrivateKeyPem, session, url, headers, None,
                      debug, __version__, http_prefix, None)

    if boxJson is not None and debug:
        print('DEBUG: GET c2sBoxJson success')

    return boxJson


def secondsBetweenPublished(published1: str, published2: str) -> int:
    """Returns the number of seconds between two published dates
    """
    try:
        published1Time = \
            datetime.datetime.strptime(published1, '%Y-%m-%dT%H:%M:%SZ')
    except BaseException:
        print('EX: secondsBetweenPublished unable to parse date 1 ' +
              str(published1))
        return -1
    try:
        published2Time = \
            datetime.datetime.strptime(published2, '%Y-%m-%dT%H:%M:%SZ')
    except BaseException:
        print('EX: secondsBetweenPublished unable to parse date 2 ' +
              str(published2))
        return -1
    return (published2Time - published1Time).seconds


def editedPostFilename(base_dir: str, nickname: str, domain: str,
                       postJsonObject: {}, debug: bool,
                       maxTimeDiffSeconds: int) -> str:
    """Returns the filename of the edited post
    """
    if not hasObjectDict(postJsonObject):
        return ''
    if not postJsonObject.get('type'):
        return ''
    if not postJsonObject['object'].get('type'):
        return ''
    if not postJsonObject['object'].get('published'):
        return ''
    if not postJsonObject['object'].get('id'):
        return ''
    if not postJsonObject['object'].get('content'):
        return ''
    if not postJsonObject['object'].get('attributedTo'):
        return ''
    if not isinstance(postJsonObject['object']['attributedTo'], str):
        return ''
    actor = postJsonObject['object']['attributedTo']
    actorFilename = \
        acctDir(base_dir, nickname, domain) + '/lastpost/' + \
        actor.replace('/', '#')
    if not os.path.isfile(actorFilename):
        return ''
    postId = removeIdEnding(postJsonObject['object']['id'])
    lastpostId = None
    try:
        with open(actorFilename, 'r') as fp:
            lastpostId = fp.read()
    except OSError:
        print('EX: editedPostFilename unable to read ' + actorFilename)
        return ''
    if not lastpostId:
        return ''
    if lastpostId == postId:
        return ''
    lastpostFilename = \
        locatePost(base_dir, nickname, domain, lastpostId, False)
    if not lastpostFilename:
        return ''
    lastpostJson = loadJson(lastpostFilename, 0)
    if not lastpostJson:
        return ''
    if not lastpostJson.get('type'):
        return ''
    if lastpostJson['type'] != postJsonObject['type']:
        return ''
    if not lastpostJson['object'].get('type'):
        return ''
    if lastpostJson['object']['type'] != postJsonObject['object']['type']:
        return
    if not lastpostJson['object'].get('published'):
        return ''
    if not lastpostJson['object'].get('id'):
        return ''
    if not lastpostJson['object'].get('content'):
        return ''
    if not lastpostJson['object'].get('attributedTo'):
        return ''
    if not isinstance(lastpostJson['object']['attributedTo'], str):
        return ''
    timeDiffSeconds = \
        secondsBetweenPublished(lastpostJson['object']['published'],
                                postJsonObject['object']['published'])
    if timeDiffSeconds > maxTimeDiffSeconds:
        return ''
    if debug:
        print(postId + ' might be an edit of ' + lastpostId)
    if wordsSimilarity(lastpostJson['object']['content'],
                       postJsonObject['object']['content'], 10) < 70:
        return ''
    print(postId + ' is an edit of ' + lastpostId)
    return lastpostFilename


def getOriginalPostFromAnnounceUrl(announceUrl: str, base_dir: str,
                                   nickname: str,
                                   domain: str) -> (str, str, str):
    """From the url of an announce this returns the actor, url and
    filename (if available) of the original post being announced
    """
    postFilename = locatePost(base_dir, nickname, domain, announceUrl)
    if not postFilename:
        return None, None, None
    announcePostJson = loadJson(postFilename, 0, 1)
    if not announcePostJson:
        return None, None, postFilename
    if not announcePostJson.get('type'):
        return None, None, postFilename
    if announcePostJson['type'] != 'Announce':
        return None, None, postFilename
    if not announcePostJson.get('object'):
        return None, None, postFilename
    if not isinstance(announcePostJson['object'], str):
        return None, None, postFilename
    actor = url = None
    # do we have the original post?
    origPostId = announcePostJson['object']
    origFilename = locatePost(base_dir, nickname, domain, origPostId)
    if origFilename:
        # we have the original post
        origPostJson = loadJson(origFilename, 0, 1)
        if origPostJson:
            if hasObjectDict(origPostJson):
                if origPostJson['object'].get('attributedTo'):
                    if isinstance(origPostJson['object']['attributedTo'], str):
                        actor = origPostJson['object']['attributedTo']
                        url = origPostId
                elif origPostJson['object'].get('actor'):
                    actor = origPostJson['actor']
                    url = origPostId
    else:
        # we don't have the original post
        if hasUsersPath(origPostId):
            # get the actor from the original post url
            origNick = getNicknameFromActor(origPostId)
            origDomain, origPort = getDomainFromActor(origPostId)
            if origNick and origDomain:
                actor = \
                    origPostId.split('/' + origNick + '/')[0] + \
                    '/' + origNick
                url = origPostId

    return actor, url, origFilename
