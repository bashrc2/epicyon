__filename__ = "posts.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import html
import datetime
import os
import shutil
import sys
import time
import uuid
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
from utils import fileLastModified
from utils import isPublicPost
from utils import hasUsersPath
from utils import validPostDate
from utils import getFullDomain
from utils import getFollowersList
from utils import isEvil
from utils import removeIdEnding
from utils import siteIsActive
from utils import getCachedPostFilename
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
from media import attachMedia
from media import replaceYouTube
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


def isModerator(baseDir: str, nickname: str) -> bool:
    """Returns true if the given nickname is a moderator
    """
    moderatorsFile = baseDir + '/accounts/moderators.txt'

    if not os.path.isfile(moderatorsFile):
        adminName = getConfigParam(baseDir, 'admin')
        if not adminName:
            return False
        if adminName == nickname:
            return True
        return False

    with open(moderatorsFile, "r") as f:
        lines = f.readlines()
        if len(lines) == 0:
            adminName = getConfigParam(baseDir, 'admin')
            if not adminName:
                return False
            if adminName == nickname:
                return True
        for moderator in lines:
            moderator = moderator.strip('\n').strip('\r')
            if moderator == nickname:
                return True
    return False


def noOfFollowersOnDomain(baseDir: str, handle: str,
                          domain: str, followFile='followers.txt') -> int:
    """Returns the number of followers of the given handle from the given domain
    """
    filename = baseDir + '/accounts/' + handle + '/' + followFile
    if not os.path.isfile(filename):
        return 0

    ctr = 0
    with open(filename, "r") as followersFilename:
        for followerHandle in followersFilename:
            if '@' in followerHandle:
                followerDomain = followerHandle.split('@')[1]
                followerDomain = followerDomain.replace('\n', '')
                followerDomain = followerDomain.replace('\r', '')
                if domain == followerDomain:
                    ctr += 1
    return ctr


def _getPersonKey(nickname: str, domain: str, baseDir: str, keyType='public',
                  debug=False):
    """Returns the public or private key of a person
    """
    handle = nickname + '@' + domain
    keyFilename = baseDir + '/keys/' + keyType + '/' + handle.lower() + '.key'
    if not os.path.isfile(keyFilename):
        if debug:
            print('DEBUG: private key file not found: ' + keyFilename)
        return ''
    keyPem = ''
    with open(keyFilename, "r") as pemFile:
        keyPem = pemFile.read()
    if len(keyPem) < 20:
        if debug:
            print('DEBUG: private key was too short: ' + keyPem)
        return ''
    return keyPem


def _cleanHtml(rawHtml: str) -> str:
    # text=BeautifulSoup(rawHtml, 'html.parser').get_text()
    text = rawHtml
    return html.unescape(text)


def getUserUrl(wfRequest: {}, sourceId=0) -> str:
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
            if not hasUsersPath(link['href']):
                print('getUserUrl webfinger activity+json ' +
                      'contains single user instance actor ' +
                      str(sourceId) + ' ' + str(link))
        else:
            return link['href'].replace('/@', '/users/')
        return link['href']
    return None


def parseUserFeed(session, feedUrl: str, asHeader: {},
                  projectVersion: str, httpPrefix: str,
                  domain: str, depth=0) -> {}:
    if depth > 10:
        return None

    feedJson = getJson(session, feedUrl, asHeader, None,
                       projectVersion, httpPrefix, domain)
    if not feedJson:
        return None

    if 'orderedItems' in feedJson:
        for item in feedJson['orderedItems']:
            yield item

    nextUrl = None
    if 'first' in feedJson:
        nextUrl = feedJson['first']
    elif 'next' in feedJson:
        nextUrl = feedJson['next']

    if nextUrl:
        if isinstance(nextUrl, str):
            if '?max_id=0' not in nextUrl:
                userFeed = \
                    parseUserFeed(session, nextUrl, asHeader,
                                  projectVersion, httpPrefix,
                                  domain, depth + 1)
                if userFeed:
                    for item in userFeed:
                        yield item
        elif isinstance(nextUrl, dict):
            userFeed = nextUrl
            if userFeed.get('orderedItems'):
                for item in userFeed['orderedItems']:
                    yield item


def getPersonBox(baseDir: str, session, wfRequest: {},
                 personCache: {},
                 projectVersion: str, httpPrefix: str,
                 nickname: str, domain: str,
                 boxName='inbox',
                 sourceId=0) -> (str, str, str, str, str, str, str, str):
    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/activity+json; profile="' + profileStr + '"'
    }
    if not wfRequest:
        print('No webfinger given')
        return None, None, None, None, None, None, None

    if not wfRequest.get('errors'):
        personUrl = getUserUrl(wfRequest, sourceId)
    else:
        if nickname == 'dev':
            # try single user instance
            print('getPersonBox: Trying single user instance with ld+json')
            personUrl = httpPrefix + '://' + domain
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
        else:
            personUrl = httpPrefix + '://' + domain + '/users/' + nickname
    if not personUrl:
        return None, None, None, None, None, None, None
    personJson = \
        getPersonFromCache(baseDir, personUrl, personCache, True)
    if not personJson:
        if '/channel/' in personUrl or '/accounts/' in personUrl:
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
        personJson = getJson(session, personUrl, asHeader, None,
                             projectVersion, httpPrefix, domain)
        if not personJson:
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
            personJson = getJson(session, personUrl, asHeader, None,
                                 projectVersion, httpPrefix, domain)
            if not personJson:
                print('Unable to get actor')
                return None, None, None, None, None, None, None
    boxJson = None
    if not personJson.get(boxName):
        if personJson.get('endpoints'):
            if personJson['endpoints'].get(boxName):
                boxJson = personJson['endpoints'][boxName]
    else:
        boxJson = personJson[boxName]

    if not boxJson:
        return None, None, None, None, None, None, None

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
        elif isFiltered(baseDir,
                        nickname, domain,
                        displayName):
            displayName = '*FILTERED*'
        # have they moved?
        if personJson.get('movedTo'):
            displayName += ' ⌂'

    storePersonInCache(baseDir, personUrl, personJson, personCache, True)

    return boxJson, pubKeyId, pubKey, personId, sharedInbox, \
        avatarUrl, displayName


def _getPosts(session, outboxUrl: str, maxPosts: int,
              maxMentions: int,
              maxEmoji: int, maxAttachments: int,
              federationList: [],
              personCache: {}, raw: bool,
              simple: bool, debug: bool,
              projectVersion: str, httpPrefix: str,
              domain: str) -> {}:
    """Gets public posts from an outbox
    """
    personPosts = {}
    if not outboxUrl:
        return personPosts
    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/activity+json; profile="' + profileStr + '"'
    }
    if '/outbox/' in outboxUrl:
        asHeader = {
            'Accept': 'application/ld+json; profile="' + profileStr + '"'
        }
    if raw:
        result = []
        i = 0
        userFeed = parseUserFeed(session, outboxUrl, asHeader,
                                 projectVersion, httpPrefix, domain)
        for item in userFeed:
            result.append(item)
            i += 1
            if i == maxPosts:
                break
        pprint(result)
        return None

    i = 0
    userFeed = parseUserFeed(session, outboxUrl, asHeader,
                             projectVersion, httpPrefix, domain)
    for item in userFeed:
        if not item.get('id'):
            if debug:
                print('No id')
            continue
        if not item.get('type'):
            if debug:
                print('No type')
            continue
        if item['type'] != 'Create':
            if debug:
                print('Not Create type')
            continue
        if not item.get('object'):
            if debug:
                print('No object')
            continue
        if not isinstance(item['object'], dict):
            if debug:
                print('item object is not a dict')
            continue
        if not item['object'].get('published'):
            if debug:
                print('No published attribute')
            continue
        if not personPosts.get(item['id']):
            # check that this is a public post
            # #Public should appear in the "to" list
            if item['object'].get('to'):
                isPublic = False
                for recipient in item['object']['to']:
                    if recipient.endswith('#Public'):
                        isPublic = True
                        break
                if not isPublic:
                    continue

            content = \
                item['object']['content'].replace('&apos;', "'")

            mentions = []
            emoji = {}
            if item['object'].get('tag'):
                for tagItem in item['object']['tag']:
                    tagType = tagItem['type'].lower()
                    if tagType == 'emoji':
                        if tagItem.get('name') and tagItem.get('icon'):
                            if tagItem['icon'].get('url'):
                                # No emoji from non-permitted domains
                                if urlPermitted(tagItem['icon']['url'],
                                                federationList,
                                                "objects:read"):
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
            if len(mentions) > maxMentions:
                if debug:
                    print('max mentions reached')
                continue
            if len(emoji) > maxEmoji:
                if debug:
                    print('max emojis reached')
                continue

            summary = ''
            if item['object'].get('summary'):
                if item['object']['summary']:
                    summary = item['object']['summary']

            inReplyTo = ''
            if item['object'].get('inReplyTo'):
                if item['object']['inReplyTo']:
                    if isinstance(item['object']['inReplyTo'], str):
                        # No replies to non-permitted domains
                        if not urlPermitted(item['object']['inReplyTo'],
                                            federationList,
                                            "objects:read"):
                            if debug:
                                print('url not permitted ' +
                                      item['object']['inReplyTo'])
                            continue
                        inReplyTo = item['object']['inReplyTo']

            conversation = ''
            if item['object'].get('conversation'):
                if item['object']['conversation']:
                    # no conversations originated in non-permitted domains
                    if urlPermitted(item['object']['conversation'],
                                    federationList, "objects:read"):
                        conversation = item['object']['conversation']

            attachment = []
            if item['object'].get('attachment'):
                if item['object']['attachment']:
                    for attach in item['object']['attachment']:
                        if attach.get('name') and attach.get('url'):
                            # no attachments from non-permitted domains
                            if urlPermitted(attach['url'],
                                            federationList,
                                            "objects:read"):
                                attachment.append([attach['name'],
                                                   attach['url']])
                            else:
                                if debug:
                                    print('url not permitted ' +
                                          attach['url'])

            sensitive = False
            if item['object'].get('sensitive'):
                sensitive = item['object']['sensitive']

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
                    "emoji": emoji,
                    "conversation": conversation
                }
        i += 1

        if i == maxPosts:
            break
    return personPosts


def _updateWordFrequency(content: str, wordFrequency: {}) -> None:
    """Creates a dictionary containing words and the number of times
    that they appear
    """
    plainText = removeHtml(content)
    plainText = plainText.replace('.', ' ')
    plainText = plainText.replace(';', ' ')
    plainText = plainText.replace('?', ' ')
    wordsList = plainText.split(' ')
    commonWords = (
        'that', 'some', 'about', 'then', 'they', 'were',
        'also', 'from', 'with', 'this', 'have', 'more',
        'need', 'here', 'would', 'these', 'into', 'very',
        'well', 'when', 'what', 'your', 'there', 'which',
        'even', 'there', 'such', 'just', 'those', 'only',
        'will', 'much', 'than', 'them', 'each', 'goes',
        'been', 'over', 'their', 'where', 'could', 'though'
    )
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
           '://' in word:
            continue
        if word.endswith(':'):
            word = word.replace(':', '')
        if word.lower() in commonWords:
            continue
        if wordFrequency.get(word):
            wordFrequency[word] += 1
        else:
            wordFrequency[word] = 1


def getPostDomains(session, outboxUrl: str, maxPosts: int,
                   maxMentions: int,
                   maxEmoji: int, maxAttachments: int,
                   federationList: [],
                   personCache: {},
                   debug: bool,
                   projectVersion: str, httpPrefix: str,
                   domain: str,
                   wordFrequency: {},
                   domainList=[]) -> []:
    """Returns a list of domains referenced within public posts
    """
    if not outboxUrl:
        return []
    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/activity+json; profile="' + profileStr + '"'
    }
    if '/outbox/' in outboxUrl:
        asHeader = {
            'Accept': 'application/ld+json; profile="' + profileStr + '"'
        }

    postDomains = domainList

    i = 0
    userFeed = parseUserFeed(session, outboxUrl, asHeader,
                             projectVersion, httpPrefix, domain)
    for item in userFeed:
        i += 1
        if i > maxPosts:
            break
        if not item.get('object'):
            continue
        if not isinstance(item['object'], dict):
            continue
        if item['object'].get('content'):
            _updateWordFrequency(item['object']['content'],
                                 wordFrequency)
        if item['object'].get('inReplyTo'):
            if isinstance(item['object']['inReplyTo'], str):
                postDomain, postPort = \
                    getDomainFromActor(item['object']['inReplyTo'])
                if postDomain not in postDomains:
                    postDomains.append(postDomain)

        if item['object'].get('tag'):
            for tagItem in item['object']['tag']:
                tagType = tagItem['type'].lower()
                if tagType == 'mention':
                    if tagItem.get('href'):
                        postDomain, postPort = \
                            getDomainFromActor(tagItem['href'])
                        if postDomain not in postDomains:
                            postDomains.append(postDomain)
    return postDomains


def _getPostsForBlockedDomains(baseDir: str,
                               session, outboxUrl: str, maxPosts: int,
                               maxMentions: int,
                               maxEmoji: int, maxAttachments: int,
                               federationList: [],
                               personCache: {},
                               debug: bool,
                               projectVersion: str, httpPrefix: str,
                               domain: str) -> {}:
    """Returns a dictionary of posts for blocked domains
    """
    if not outboxUrl:
        return {}
    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/activity+json; profile="' + profileStr + '"'
    }
    if '/outbox/' in outboxUrl:
        asHeader = {
            'Accept': 'application/ld+json; profile="' + profileStr + '"'
        }

    blockedPosts = {}

    i = 0
    userFeed = parseUserFeed(session, outboxUrl, asHeader,
                             projectVersion, httpPrefix, domain)
    for item in userFeed:
        i += 1
        if i > maxPosts:
            break
        if not item.get('object'):
            continue
        if not isinstance(item['object'], dict):
            continue
        if item['object'].get('inReplyTo'):
            if isinstance(item['object']['inReplyTo'], str):
                postDomain, postPort = \
                    getDomainFromActor(item['object']['inReplyTo'])
                if isBlockedDomain(baseDir, postDomain):
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
                tagType = tagItem['type'].lower()
                if tagType == 'mention':
                    if tagItem.get('href'):
                        postDomain, postPort = \
                            getDomainFromActor(tagItem['href'])
                        if isBlockedDomain(baseDir, postDomain):
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


def deleteAllPosts(baseDir: str,
                   nickname: str, domain: str, boxname: str) -> None:
    """Deletes all posts for a person from inbox or outbox
    """
    if boxname != 'inbox' and boxname != 'outbox' and \
       boxname != 'tlblogs' and boxname != 'tlnews' and \
       boxname != 'tlevents':
        return
    boxDir = createPersonDir(nickname, domain, baseDir, boxname)
    for deleteFilename in os.scandir(boxDir):
        deleteFilename = deleteFilename.name
        filePath = os.path.join(boxDir, deleteFilename)
        try:
            if os.path.isfile(filePath):
                os.unlink(filePath)
            elif os.path.isdir(filePath):
                shutil.rmtree(filePath)
        except Exception as e:
            print(e)


def savePostToBox(baseDir: str, httpPrefix: str, postId: str,
                  nickname: str, domain: str, postJsonObject: {},
                  boxname: str) -> str:
    """Saves the give json to the give box
    Returns the filename
    """
    if boxname != 'inbox' and boxname != 'outbox' and \
       boxname != 'tlblogs' and boxname != 'tlnews' and \
       boxname != 'tlevents' and \
       boxname != 'scheduled':
        return None
    originalDomain = domain
    if ':' in domain:
        domain = domain.split(':')[0]

    if not postId:
        statusNumber, published = getStatusNumber()
        postId = \
            httpPrefix + '://' + originalDomain + '/users/' + nickname + \
            '/statuses/' + statusNumber
        postJsonObject['id'] = postId + '/activity'
    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], dict):
            postJsonObject['object']['id'] = postId
            postJsonObject['object']['atomUri'] = postId

    boxDir = createPersonDir(nickname, domain, baseDir, boxname)
    filename = boxDir + '/' + postId.replace('/', '#') + '.json'

    saveJson(postJsonObject, filename)
    return filename


def _updateHashtagsIndex(baseDir: str, tag: {}, newPostId: str) -> None:
    """Writes the post url for hashtags to a file
    This allows posts for a hashtag to be quickly looked up
    """
    if tag['type'] != 'Hashtag':
        return

    # create hashtags directory
    tagsDir = baseDir + '/tags'
    if not os.path.isdir(tagsDir):
        os.mkdir(tagsDir)
    tagName = tag['name']
    tagsFilename = tagsDir + '/' + tagName[1:] + '.txt'
    tagline = newPostId + '\n'

    if not os.path.isfile(tagsFilename):
        # create a new tags index file
        tagsFile = open(tagsFilename, "w+")
        if tagsFile:
            tagsFile.write(tagline)
            tagsFile.close()
    else:
        # prepend to tags index file
        if tagline not in open(tagsFilename).read():
            try:
                with open(tagsFilename, 'r+') as tagsFile:
                    content = tagsFile.read()
                    if tagline not in content:
                        tagsFile.seek(0, 0)
                        tagsFile.write(tagline + content)
            except Exception as e:
                print('WARN: Failed to write entry to tags file ' +
                      tagsFilename + ' ' + str(e))


def _addSchedulePost(baseDir: str, nickname: str, domain: str,
                     eventDateStr: str, postId: str) -> None:
    """Adds a scheduled post to the index
    """
    handle = nickname + '@' + domain
    scheduleIndexFilename = baseDir + '/accounts/' + handle + '/schedule.index'

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
            except Exception as e:
                print('WARN: Failed to write entry to scheduled posts index ' +
                      scheduleIndexFilename + ' ' + str(e))
    else:
        scheduleFile = open(scheduleIndexFilename, 'w+')
        if scheduleFile:
            scheduleFile.write(indexStr + '\n')
            scheduleFile.close()


def _appendEventFields(newPost: {},
                       eventUUID: str, eventStatus: str,
                       anonymousParticipationEnabled: bool,
                       repliesModerationOption: str,
                       category: str,
                       joinMode: str,
                       eventDateStr: str,
                       endDateStr: str,
                       location: str,
                       maximumAttendeeCapacity: int,
                       ticketUrl: str,
                       subject: str) -> None:
    """Appends Mobilizon-type event fields to a post
    """
    if not eventUUID:
        return

    # add attributes for Mobilizon-type events
    newPost['uuid'] = eventUUID
    if eventStatus:
        newPost['ical:status'] = eventStatus
    if anonymousParticipationEnabled:
        newPost['anonymousParticipationEnabled'] = \
            anonymousParticipationEnabled
    if repliesModerationOption:
        newPost['repliesModerationOption'] = repliesModerationOption
    if category:
        newPost['category'] = category
    if joinMode:
        newPost['joinMode'] = joinMode
    newPost['startTime'] = eventDateStr
    newPost['endTime'] = endDateStr
    if location:
        newPost['location'] = location
    if maximumAttendeeCapacity:
        newPost['maximumAttendeeCapacity'] = maximumAttendeeCapacity
    if ticketUrl:
        newPost['ticketUrl'] = ticketUrl
    if subject:
        newPost['name'] = subject
        newPost['summary'] = None
        newPost['sensitive'] = False


def validContentWarning(cw: str) -> str:
    """Returns a validated content warning
    """
    cw = removeHtml(cw)
    # hashtags within content warnings apparently cause a lot of trouble
    # so remove them
    if '#' in cw:
        cw = cw.replace('#', '').replace('  ', ' ')
    return cw


def _loadAutoCW(baseDir: str, nickname: str, domain: str) -> []:
    """Loads automatic CWs file and returns a list containing
    the lines of the file
    """
    filename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/autocw.txt'
    if not os.path.isfile(filename):
        return []
    with open(filename, "r") as f:
        return f.readlines()
    return []


def _addAutoCW(baseDir: str, nickname: str, domain: str,
               subject: str, content: str) -> str:
    """Appends any automatic CW to the subject line
    and returns the new subject line
    """
    newSubject = subject
    autoCWList = _loadAutoCW(baseDir, nickname, domain)
    for cwRule in autoCWList:
        if '->' not in cwRule:
            continue
        match = cwRule.split('->')[0].strip()
        if match not in content:
            continue
        cwStr = cwRule.split('->')[1].strip()
        if newSubject:
            if cwStr not in newSubject:
                newSubject += ', ' + cwStr
        else:
            newSubject = cwStr
    return newSubject


def _createPostBase(baseDir: str, nickname: str, domain: str, port: int,
                    toUrl: str, ccUrl: str, httpPrefix: str, content: str,
                    followersOnly: bool, saveToFile: bool,
                    clientToServer: bool, commentsEnabled: bool,
                    attachImageFilename: str,
                    mediaType: str, imageDescription: str,
                    isModerationReport: bool,
                    isArticle: bool,
                    inReplyTo=None,
                    inReplyToAtomUri=None, subject=None, schedulePost=False,
                    eventDate=None, eventTime=None, location=None,
                    eventUUID=None, category=None, joinMode=None,
                    endDate=None, endTime=None,
                    maximumAttendeeCapacity=None,
                    repliesModerationOption=None,
                    anonymousParticipationEnabled=None,
                    eventStatus=None, ticketUrl=None) -> {}:
    """Creates a message
    """
    subject = _addAutoCW(baseDir, nickname, domain, subject, content)

    if nickname != 'news':
        mentionedRecipients = \
            getMentionedPeople(baseDir, httpPrefix, content, domain, False)
    else:
        mentionedRecipients = ''

    tags = []
    hashtagsDict = {}

    domain = getFullDomain(domain, port)

    # add tags
    if nickname != 'news':
        content = \
            addHtmlTags(baseDir, httpPrefix,
                        nickname, domain, content,
                        mentionedRecipients,
                        hashtagsDict, True)

    # replace emoji with unicode
    tags = []
    for tagName, tag in hashtagsDict.items():
        tags.append(tag)
    # get list of tags
    if nickname != 'news':
        content = replaceEmojiFromTags(content, tags, 'content')
    # remove replaced emoji
    hashtagsDictCopy = hashtagsDict.copy()
    for tagName, tag in hashtagsDictCopy.items():
        if tag.get('name'):
            if tag['name'].startswith(':'):
                if tag['name'] not in content:
                    del hashtagsDict[tagName]

    statusNumber, published = getStatusNumber()
    newPostId = \
        httpPrefix + '://' + domain + '/users/' + \
        nickname + '/statuses/' + statusNumber

    sensitive = False
    summary = None
    if subject:
        summary = validContentWarning(subject)
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

    # create a list of hashtags
    # Only posts which are #Public are searchable by hashtag
    if hashtagsDict:
        isPublic = False
        for recipient in toRecipients:
            if recipient.endswith('#Public'):
                isPublic = True
                break
        for tagName, tag in hashtagsDict.items():
            if not tagExists(tag['type'], tag['name'], tags):
                tags.append(tag)
            if isPublic:
                _updateHashtagsIndex(baseDir, tag, newPostId)
        print('Content tags: ' + str(tags))

    if inReplyTo and not sensitive:
        # locate the post which this is a reply to and check if
        # it has a content warning. If it does then reproduce
        # the same warning
        replyPostFilename = \
            locatePost(baseDir, nickname, domain, inReplyTo)
        if replyPostFilename:
            replyToJson = loadJson(replyPostFilename)
            if replyToJson:
                if replyToJson.get('object'):
                    if replyToJson['object'].get('sensitive'):
                        if replyToJson['object']['sensitive']:
                            sensitive = True
                            if replyToJson['object'].get('summary'):
                                summary = replyToJson['object']['summary']

    # get the ending date and time
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

    postContext = [
        'https://www.w3.org/ns/activitystreams',
        {
            'Hashtag': 'as:Hashtag',
            'sensitive': 'as:sensitive',
            'toot': 'http://joinmastodon.org/ns#',
            'votersCount': 'toot:votersCount'
        }
    ]

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

    # the type of post to be made
    postObjectType = 'Note'
    if eventUUID:
        postObjectType = 'Event'

    if not clientToServer:
        actorUrl = httpPrefix + '://' + domain + '/users/' + nickname

        idStr = \
            httpPrefix + '://' + domain + '/users/' + nickname + \
            '/statuses/' + statusNumber + '/replies'
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
                'type': postObjectType,
                'summary': summary,
                'inReplyTo': inReplyTo,
                'published': published,
                'url': httpPrefix+'://'+domain+'/@'+nickname+'/'+statusNumber,
                'attributedTo': httpPrefix+'://'+domain+'/users/'+nickname,
                'to': toRecipients,
                'cc': toCC,
                'sensitive': sensitive,
                'atomUri': newPostId,
                'inReplyToAtomUri': inReplyToAtomUri,
                'commentsEnabled': commentsEnabled,
                'mediaType': 'text/html',
                'content': content,
                'contentMap': {
                    'en': content
                },
                'attachment': [],
                'tag': tags,
                'replies': {
                    'id': idStr,
                    'type': 'Collection',
                    'first': {
                        'type': 'CollectionPage',
                        'partOf': idStr,
                        'items': []
                    }
                }
            }
        }
        if attachImageFilename:
            newPost['object'] = \
                attachMedia(baseDir, httpPrefix, domain, port,
                            newPost['object'], attachImageFilename,
                            mediaType, imageDescription)
        _appendEventFields(newPost['object'], eventUUID, eventStatus,
                           anonymousParticipationEnabled,
                           repliesModerationOption,
                           category, joinMode,
                           eventDateStr, endDateStr,
                           location, maximumAttendeeCapacity,
                           ticketUrl, subject)
    else:
        idStr = \
            httpPrefix + '://' + domain + '/users/' + nickname + \
            '/statuses/' + statusNumber + '/replies'
        newPost = {
            "@context": postContext,
            'id': newPostId,
            'type': postObjectType,
            'summary': summary,
            'inReplyTo': inReplyTo,
            'published': published,
            'url': httpPrefix+'://'+domain+'/@'+nickname+'/'+statusNumber,
            'attributedTo': httpPrefix+'://'+domain+'/users/'+nickname,
            'to': toRecipients,
            'cc': toCC,
            'sensitive': sensitive,
            'atomUri': newPostId,
            'inReplyToAtomUri': inReplyToAtomUri,
            'commentsEnabled': commentsEnabled,
            'mediaType': 'text/html',
            'content': content,
            'contentMap': {
                'en': content
            },
            'attachment': [],
            'tag': tags,
            'replies': {
                'id': idStr,
                'type': 'Collection',
                'first': {
                    'type': 'CollectionPage',
                    'partOf': idStr,
                    'items': []
                }
            }
        }
        if attachImageFilename:
            newPost = \
                attachMedia(baseDir, httpPrefix, domain, port,
                            newPost, attachImageFilename,
                            mediaType, imageDescription)
        _appendEventFields(newPost, eventUUID, eventStatus,
                           anonymousParticipationEnabled,
                           repliesModerationOption,
                           category, joinMode,
                           eventDateStr, endDateStr,
                           location, maximumAttendeeCapacity,
                           ticketUrl, subject)
    if ccUrl:
        if len(ccUrl) > 0:
            newPost['cc'] = [ccUrl]
            if newPost.get('object'):
                newPost['object']['cc'] = [ccUrl]

                # if this is a public post then include any mentions in cc
                toCC = newPost['object']['cc']
                if len(toRecipients) == 1:
                    if toRecipients[0].endswith('#Public') and \
                       ccUrl.endswith('/followers'):
                        for tag in tags:
                            if tag['type'] == 'Mention':
                                if tag['href'] not in toCC:
                                    toCC.append(tag['href'])

    # if this is a moderation report then add a status
    if isModerationReport:
        # add status
        if newPost.get('object'):
            newPost['object']['moderationStatus'] = 'pending'
        else:
            newPost['moderationStatus'] = 'pending'
        # save to index file
        moderationIndexFile = baseDir + '/accounts/moderation.txt'
        modFile = open(moderationIndexFile, "a+")
        if modFile:
            modFile.write(newPostId + '\n')
            modFile.close()

    # If a patch has been posted - i.e. the output from
    # git format-patch - then convert the activitypub type
    convertPostToPatch(baseDir, nickname, domain, newPost)

    if schedulePost:
        if eventDate and eventTime:
            # add an item to the scheduled post index file
            _addSchedulePost(baseDir, nickname, domain,
                             eventDateStr, newPostId)
            savePostToBox(baseDir, httpPrefix, newPostId,
                          nickname, domain, newPost, 'scheduled')
        else:
            print('Unable to create scheduled post without ' +
                  'date and time values')
            return newPost
    elif saveToFile:
        if isArticle:
            savePostToBox(baseDir, httpPrefix, newPostId,
                          nickname, domain, newPost, 'tlblogs')
        elif eventUUID:
            savePostToBox(baseDir, httpPrefix, newPostId,
                          nickname, domain, newPost, 'tlevents')
        else:
            savePostToBox(baseDir, httpPrefix, newPostId,
                          nickname, domain, newPost, 'outbox')
    return newPost


def outboxMessageCreateWrap(httpPrefix: str,
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
        httpPrefix + '://' + domain + '/users/' + nickname + \
        '/statuses/' + statusNumber
    cc = []
    if messageJson.get('cc'):
        cc = messageJson['cc']
    newPost = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'id': newPostId + '/activity',
        'type': 'Create',
        'actor': httpPrefix + '://' + domain + '/users/' + nickname,
        'published': published,
        'to': messageJson['to'],
        'cc': cc,
        'object': messageJson
    }
    newPost['object']['id'] = newPost['id']
    newPost['object']['url'] = \
        httpPrefix + '://' + domain + '/@' + nickname + '/' + statusNumber
    newPost['object']['atomUri'] = \
        httpPrefix + '://' + domain + '/users/' + nickname + \
        '/statuses/' + statusNumber
    return newPost


def _postIsAddressedToFollowers(baseDir: str,
                                nickname: str, domain: str, port: int,
                                httpPrefix: str,
                                postJsonObject: {}) -> bool:
    """Returns true if the given post is addressed to followers of the nickname
    """
    domainFull = getFullDomain(domain, port)

    if not postJsonObject.get('object'):
        return False
    toList = []
    ccList = []
    if postJsonObject['type'] != 'Update' and \
       isinstance(postJsonObject['object'], dict):
        if postJsonObject['object'].get('to'):
            toList = postJsonObject['object']['to']
        if postJsonObject['object'].get('cc'):
            ccList = postJsonObject['object']['cc']
    else:
        if postJsonObject.get('to'):
            toList = postJsonObject['to']
        if postJsonObject.get('cc'):
            ccList = postJsonObject['cc']

    followersUrl = httpPrefix + '://' + domainFull + '/users/' + \
        nickname + '/followers'

    # does the followers url exist in 'to' or 'cc' lists?
    addressedToFollowers = False
    if followersUrl in toList:
        addressedToFollowers = True
    elif followersUrl in ccList:
        addressedToFollowers = True
    return addressedToFollowers


def pinPost(baseDir: str, nickname: str, domain: str,
            pinnedContent: str) -> None:
    """Pins the given post Id to the profile of then given account
    """
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain
    pinnedFilename = accountDir + '/pinToProfile.txt'
    pinFile = open(pinnedFilename, "w+")
    if pinFile:
        pinFile.write(pinnedContent)
        pinFile.close()


def undoPinnedPost(baseDir: str, nickname: str, domain: str) -> None:
    """Removes pinned content for then given account
    """
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain
    pinnedFilename = accountDir + '/pinToProfile.txt'
    if os.path.isfile(pinnedFilename):
        os.remove(pinnedFilename)


def getPinnedPostAsJson(baseDir: str, httpPrefix: str,
                        nickname: str, domain: str,
                        domainFull: str) -> {}:
    """Returns the pinned profile post as json
    """
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain
    pinnedFilename = accountDir + '/pinToProfile.txt'
    pinnedPostJson = {}
    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    if os.path.isfile(pinnedFilename):
        pinFile = open(pinnedFilename, "r")
        pinnedContent = None
        if pinFile:
            pinnedContent = pinFile.read()
            pinFile.close()
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
                    'en': pinnedContent
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
                'url': actor.replace('/users/', '/@') + '/pinned'
            }
    return pinnedPostJson


def jsonPinPost(baseDir: str, httpPrefix: str,
                nickname: str, domain: str,
                domainFull: str) -> {}:
    """Returns a pinned post as json
    """
    pinnedPostJson = \
        getPinnedPostAsJson(baseDir, httpPrefix,
                            nickname, domain,
                            domainFull)
    itemsList = []
    if pinnedPostJson:
        itemsList = [pinnedPostJson]

    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    return {
        '@context': [
            'https://www.w3.org/ns/activitystreams',
            {
                'atomUri': 'ostatus:atomUri',
                'conversation': 'ostatus:conversation',
                'inReplyToAtomUri': 'ostatus:inReplyToAtomUri',
                'ostatus': 'http://ostatus.org#',
                'sensitive': 'as:sensitive',
                'toot': 'http://joinmastodon.org/ns#',
                'votersCount': 'toot:votersCount'
            }
        ],
        'id': actor + '/collections/featured',
        'orderedItems': itemsList,
        'totalItems': len(itemsList),
        'type': 'OrderedCollection'
    }


def createPublicPost(baseDir: str,
                     nickname: str, domain: str, port: int, httpPrefix: str,
                     content: str, followersOnly: bool, saveToFile: bool,
                     clientToServer: bool, commentsEnabled: bool,
                     attachImageFilename: str, mediaType: str,
                     imageDescription: str,
                     inReplyTo=None, inReplyToAtomUri=None, subject=None,
                     schedulePost=False,
                     eventDate=None, eventTime=None, location=None) -> {}:
    """Public post
    """
    domainFull = getFullDomain(domain, port)
    return _createPostBase(baseDir, nickname, domain, port,
                           'https://www.w3.org/ns/activitystreams#Public',
                           httpPrefix + '://' + domainFull + '/users/' +
                           nickname + '/followers',
                           httpPrefix, content, followersOnly, saveToFile,
                           clientToServer, commentsEnabled,
                           attachImageFilename, mediaType,
                           imageDescription,
                           False, False, inReplyTo, inReplyToAtomUri, subject,
                           schedulePost, eventDate, eventTime, location,
                           None, None, None, None, None,
                           None, None, None, None, None)


def createBlogPost(baseDir: str,
                   nickname: str, domain: str, port: int, httpPrefix: str,
                   content: str, followersOnly: bool, saveToFile: bool,
                   clientToServer: bool, commentsEnabled: bool,
                   attachImageFilename: str, mediaType: str,
                   imageDescription: str,
                   inReplyTo=None, inReplyToAtomUri=None, subject=None,
                   schedulePost=False,
                   eventDate=None, eventTime=None, location=None) -> {}:
    blog = \
        createPublicPost(baseDir,
                         nickname, domain, port, httpPrefix,
                         content, followersOnly, saveToFile,
                         clientToServer, commentsEnabled,
                         attachImageFilename, mediaType,
                         imageDescription,
                         inReplyTo, inReplyToAtomUri, subject,
                         schedulePost,
                         eventDate, eventTime, location)
    blog['object']['type'] = 'Article'

    # append citations tags, stored in a file
    citationsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/.citations.txt'
    if os.path.isfile(citationsFilename):
        citationsSeparator = '#####'
        with open(citationsFilename, "r") as f:
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
                blog['object']['tag'].append(tagJson)

    return blog


def createNewsPost(baseDir: str,
                   domain: str, port: int, httpPrefix: str,
                   content: str, followersOnly: bool, saveToFile: bool,
                   attachImageFilename: str, mediaType: str,
                   imageDescription: str,
                   subject: str) -> {}:
    clientToServer = False
    inReplyTo = None
    inReplyToAtomUri = None
    schedulePost = False
    eventDate = None
    eventTime = None
    location = None
    blog = \
        createPublicPost(baseDir,
                         'news', domain, port, httpPrefix,
                         content, followersOnly, saveToFile,
                         clientToServer, False,
                         attachImageFilename, mediaType,
                         imageDescription,
                         inReplyTo, inReplyToAtomUri, subject,
                         schedulePost,
                         eventDate, eventTime, location)
    blog['object']['type'] = 'Article'
    return blog


def createQuestionPost(baseDir: str,
                       nickname: str, domain: str, port: int, httpPrefix: str,
                       content: str, qOptions: [],
                       followersOnly: bool, saveToFile: bool,
                       clientToServer: bool, commentsEnabled: bool,
                       attachImageFilename: str, mediaType: str,
                       imageDescription: str,
                       subject: str, durationDays: int) -> {}:
    """Question post with multiple choice options
    """
    domainFull = getFullDomain(domain, port)
    messageJson = \
        _createPostBase(baseDir, nickname, domain, port,
                        'https://www.w3.org/ns/activitystreams#Public',
                        httpPrefix + '://' + domainFull + '/users/' +
                        nickname + '/followers',
                        httpPrefix, content, followersOnly, saveToFile,
                        clientToServer, commentsEnabled,
                        attachImageFilename, mediaType,
                        imageDescription,
                        False, False, None, None, subject,
                        False, None, None, None, None, None,
                        None, None, None,
                        None, None, None, None, None)
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


def createUnlistedPost(baseDir: str,
                       nickname: str, domain: str, port: int, httpPrefix: str,
                       content: str, followersOnly: bool, saveToFile: bool,
                       clientToServer: bool, commentsEnabled: bool,
                       attachImageFilename: str, mediaType: str,
                       imageDescription: str,
                       inReplyTo=None, inReplyToAtomUri=None, subject=None,
                       schedulePost=False,
                       eventDate=None, eventTime=None, location=None) -> {}:
    """Unlisted post. This has the #Public and followers links inverted.
    """
    domainFull = getFullDomain(domain, port)
    return _createPostBase(baseDir, nickname, domain, port,
                           httpPrefix + '://' + domainFull + '/users/' +
                           nickname + '/followers',
                           'https://www.w3.org/ns/activitystreams#Public',
                           httpPrefix, content, followersOnly, saveToFile,
                           clientToServer, commentsEnabled,
                           attachImageFilename, mediaType,
                           imageDescription,
                           False, False, inReplyTo, inReplyToAtomUri, subject,
                           schedulePost, eventDate, eventTime, location,
                           None, None, None, None, None,
                           None, None, None, None, None)


def createFollowersOnlyPost(baseDir: str,
                            nickname: str, domain: str, port: int,
                            httpPrefix: str,
                            content: str, followersOnly: bool,
                            saveToFile: bool,
                            clientToServer: bool, commentsEnabled: bool,
                            attachImageFilename: str, mediaType: str,
                            imageDescription: str,
                            inReplyTo=None, inReplyToAtomUri=None,
                            subject=None, schedulePost=False,
                            eventDate=None, eventTime=None,
                            location=None) -> {}:
    """Followers only post
    """
    domainFull = getFullDomain(domain, port)
    return _createPostBase(baseDir, nickname, domain, port,
                           httpPrefix + '://' + domainFull + '/users/' +
                           nickname + '/followers',
                           None,
                           httpPrefix, content, followersOnly, saveToFile,
                           clientToServer, commentsEnabled,
                           attachImageFilename, mediaType,
                           imageDescription,
                           False, False, inReplyTo, inReplyToAtomUri, subject,
                           schedulePost, eventDate, eventTime, location,
                           None, None, None, None, None,
                           None, None, None, None, None)


def createEventPost(baseDir: str,
                    nickname: str, domain: str, port: int,
                    httpPrefix: str,
                    content: str, followersOnly: bool,
                    saveToFile: bool,
                    clientToServer: bool, commentsEnabled: bool,
                    attachImageFilename: str, mediaType: str,
                    imageDescription: str,
                    subject=None, schedulePost=False,
                    eventDate=None, eventTime=None,
                    location=None, category=None, joinMode=None,
                    endDate=None, endTime=None,
                    maximumAttendeeCapacity=None,
                    repliesModerationOption=None,
                    anonymousParticipationEnabled=None,
                    eventStatus=None, ticketUrl=None) -> {}:
    """Mobilizon-type Event post
    """
    if not attachImageFilename:
        print('Event has no attached image')
        return None
    if not category:
        print('Event has no category')
        return None
    domainFull = getFullDomain(domain, port)

    # create event uuid
    eventUUID = str(uuid.uuid1())

    toStr1 = 'https://www.w3.org/ns/activitystreams#Public'
    toStr2 = httpPrefix + '://' + domainFull + '/users/' + \
        nickname + '/followers',
    if followersOnly:
        toStr1 = toStr2
        toStr2 = None
    return _createPostBase(baseDir, nickname, domain, port,
                           toStr1, toStr2,
                           httpPrefix, content, followersOnly, saveToFile,
                           clientToServer, commentsEnabled,
                           attachImageFilename, mediaType,
                           imageDescription,
                           False, False, None, None, subject,
                           schedulePost, eventDate, eventTime, location,
                           eventUUID, category, joinMode,
                           endDate, endTime, maximumAttendeeCapacity,
                           repliesModerationOption,
                           anonymousParticipationEnabled,
                           eventStatus, ticketUrl)


def getMentionedPeople(baseDir: str, httpPrefix: str,
                       content: str, domain: str, debug: bool) -> []:
    """Extracts a list of mentioned actors from the given message content
    """
    if '@' not in content:
        return None
    mentions = []
    words = content.split(' ')
    for wrd in words:
        if wrd.startswith('@'):
            handle = wrd[1:]
            if debug:
                print('DEBUG: mentioned handle ' + handle)
            if '@' not in handle:
                handle = handle + '@' + domain
                if not os.path.isdir(baseDir + '/accounts/' + handle):
                    continue
            else:
                externalDomain = handle.split('@')[1]
                if not ('.' in externalDomain or
                        externalDomain == 'localhost'):
                    continue
            mentionedNickname = handle.split('@')[0]
            mentionedDomain = handle.split('@')[1].strip('\n').strip('\r')
            if ':' in mentionedDomain:
                mentionedDomain = mentionedDomain.split(':')[0]
            if not validNickname(mentionedDomain, mentionedNickname):
                continue
            actor = \
                httpPrefix + '://' + handle.split('@')[1] + \
                '/users/' + mentionedNickname
            mentions.append(actor)
    return mentions


def createDirectMessagePost(baseDir: str,
                            nickname: str, domain: str, port: int,
                            httpPrefix: str,
                            content: str, followersOnly: bool,
                            saveToFile: bool, clientToServer: bool,
                            commentsEnabled: bool,
                            attachImageFilename: str, mediaType: str,
                            imageDescription: str,
                            inReplyTo=None, inReplyToAtomUri=None,
                            subject=None, debug=False,
                            schedulePost=False,
                            eventDate=None, eventTime=None,
                            location=None) -> {}:
    """Direct Message post
    """
    content = resolvePetnames(baseDir, nickname, domain, content)
    mentionedPeople = \
        getMentionedPeople(baseDir, httpPrefix, content, domain, debug)
    if debug:
        print('mentionedPeople: ' + str(mentionedPeople))
    if not mentionedPeople:
        return None
    postTo = None
    postCc = None
    messageJson = \
        _createPostBase(baseDir, nickname, domain, port,
                        postTo, postCc,
                        httpPrefix, content, followersOnly, saveToFile,
                        clientToServer, commentsEnabled,
                        attachImageFilename, mediaType,
                        imageDescription,
                        False, False, inReplyTo, inReplyToAtomUri, subject,
                        schedulePost, eventDate, eventTime, location,
                        None, None, None, None, None,
                        None, None, None, None, None)
    # mentioned recipients go into To rather than Cc
    messageJson['to'] = messageJson['object']['cc']
    messageJson['object']['to'] = messageJson['to']
    messageJson['cc'] = []
    messageJson['object']['cc'] = []
    if schedulePost:
        savePostToBox(baseDir, httpPrefix, messageJson['object']['id'],
                      nickname, domain, messageJson, 'scheduled')
    return messageJson


def createReportPost(baseDir: str,
                     nickname: str, domain: str, port: int, httpPrefix: str,
                     content: str, followersOnly: bool, saveToFile: bool,
                     clientToServer: bool, commentsEnabled: bool,
                     attachImageFilename: str, mediaType: str,
                     imageDescription: str,
                     debug: bool, subject=None) -> {}:
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
    moderatorsFile = baseDir + '/accounts/moderators.txt'
    if os.path.isfile(moderatorsFile):
        with open(moderatorsFile, "r") as fileHandler:
            for line in fileHandler:
                line = line.strip('\n').strip('\r')
                if line.startswith('#'):
                    continue
                if line.startswith('/users/'):
                    line = line.replace('users', '')
                if line.startswith('@'):
                    line = line[1:]
                if '@' in line:
                    moderatorActor = httpPrefix + '://' + domainFull + \
                        '/users/' + line.split('@')[0]
                    if moderatorActor not in moderatorsList:
                        moderatorsList.append(moderatorActor)
                    continue
                if line.startswith('http') or line.startswith('dat'):
                    # must be a local address - no remote moderators
                    if '://' + domainFull + '/' in line:
                        if line not in moderatorsList:
                            moderatorsList.append(line)
                else:
                    if '/' not in line:
                        moderatorActor = httpPrefix + '://' + domainFull + \
                            '/users/' + line
                        if moderatorActor not in moderatorsList:
                            moderatorsList.append(moderatorActor)
    if len(moderatorsList) == 0:
        # if there are no moderators then the admin becomes the moderator
        adminNickname = getConfigParam(baseDir, 'admin')
        if adminNickname:
            moderatorsList.append(httpPrefix + '://' + domainFull +
                                  '/users/' + adminNickname)
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
            _createPostBase(baseDir, nickname, domain, port,
                            toUrl, postCc,
                            httpPrefix, content, followersOnly, saveToFile,
                            clientToServer, commentsEnabled,
                            attachImageFilename, mediaType,
                            imageDescription,
                            True, False, None, None, subject,
                            False, None, None, None, None, None,
                            None, None, None,
                            None, None, None, None, None)
        if not postJsonObject:
            continue

        # update the inbox index with the report filename
        # indexFilename = baseDir+'/accounts/'+handle+'/inbox.index'
        # indexEntry = \
        #     removeIdEnding(postJsonObject['id']).replace('/','#') + '.json'
        # if indexEntry not in open(indexFilename).read():
        #     try:
        #         with open(indexFilename, 'a+') as fp:
        #             fp.write(indexEntry)
        #     except:
        #         pass

        # save a notification file so that the moderator
        # knows something new has appeared
        newReportFile = baseDir + '/accounts/' + handle + '/.newReport'
        if os.path.isfile(newReportFile):
            continue
        try:
            with open(newReportFile, 'w+') as fp:
                fp.write(toUrl + '/moderation')
        except BaseException:
            pass

    return postJsonObject


def threadSendPost(session, postJsonStr: str, federationList: [],
                   inboxUrl: str, baseDir: str,
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
            postResult, unauthorized = \
                postJsonString(session, postJsonStr, federationList,
                               inboxUrl, signatureHeaderJson,
                               debug)
            if debug:
                print('Obtained postJsonString for ' + inboxUrl +
                      ' unauthorized: ' + str(unauthorized))
        except Exception as e:
            print('ERROR: postJsonString failed ' + str(e))
        if unauthorized:
            print(postJsonStr)
            print('threadSendPost: Post is unauthorized')
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
            postLogFilename = baseDir + '/post.log'
            with open(postLogFilename, "a+") as logFile:
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


def sendPost(projectVersion: str,
             session, baseDir: str, nickname: str, domain: str, port: int,
             toNickname: str, toDomain: str, toPort: int, cc: str,
             httpPrefix: str, content: str, followersOnly: bool,
             saveToFile: bool, clientToServer: bool,
             commentsEnabled: bool,
             attachImageFilename: str, mediaType: str,
             imageDescription: str,
             federationList: [], sendThreads: [], postLog: [],
             cachedWebfingers: {}, personCache: {},
             isArticle: bool,
             debug=False, inReplyTo=None,
             inReplyToAtomUri=None, subject=None) -> int:
    """Post to another inbox
    """
    withDigest = True

    if toNickname == 'inbox':
        # shared inbox actor on @domain@domain
        toNickname = toDomain

    toDomain = getFullDomain(toDomain, toPort)

    handle = httpPrefix + '://' + toDomain + '/@' + toNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, httpPrefix,
                                cachedWebfingers,
                                domain, projectVersion)
    if not wfRequest:
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    if not clientToServer:
        postToBox = 'inbox'
    else:
        postToBox = 'outbox'
        if isArticle:
            postToBox = 'tlblogs'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey,
     toPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache,
                                            projectVersion, httpPrefix,
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
        _createPostBase(baseDir, nickname, domain, port,
                        toPersonId, cc, httpPrefix, content,
                        followersOnly, saveToFile, clientToServer,
                        commentsEnabled,
                        attachImageFilename, mediaType,
                        imageDescription,
                        False, isArticle, inReplyTo,
                        inReplyToAtomUri, subject,
                        False, None, None, None, None, None,
                        None, None, None,
                        None, None, None, None, None)

    # get the senders private key
    privateKeyPem = _getPersonKey(nickname, domain, baseDir, 'private')
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
        except Exception as e:
            print('WARN: failed to JSON-LD sign post, ' + str(e))
            pass

    # convert json to string so that there are no
    # subsequent conversions after creating message body digest
    postJsonStr = json.dumps(postJsonObject)

    # construct the http header, including the message body digest
    signatureHeaderJson = \
        createSignedHeader(privateKeyPem, nickname, domain, port,
                           toDomain, toPort,
                           postPath, httpPrefix, withDigest, postJsonStr)

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
                              inboxUrl, baseDir,
                              signatureHeaderJson.copy(),
                              postLog,
                              debug), daemon=True)
    sendThreads.append(thr)
    thr.start()
    return 0


def sendPostViaServer(projectVersion: str,
                      baseDir: str, session, fromNickname: str, password: str,
                      fromDomain: str, fromPort: int,
                      toNickname: str, toDomain: str, toPort: int, cc: str,
                      httpPrefix: str, content: str, followersOnly: bool,
                      commentsEnabled: bool,
                      attachImageFilename: str, mediaType: str,
                      imageDescription: str,
                      cachedWebfingers: {}, personCache: {},
                      isArticle: bool, debug=False, inReplyTo=None,
                      inReplyToAtomUri=None, subject=None) -> int:
    """Send a post via a proxy (c2s)
    """
    if not session:
        print('WARN: No session for sendPostViaServer')
        return 6

    fromDomain = getFullDomain(fromDomain, fromPort)

    handle = httpPrefix + '://' + fromDomain + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix, cachedWebfingers,
                        fromDomain, projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'
    if isArticle:
        postToBox = 'tlblogs'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache,
                                            projectVersion, httpPrefix,
                                            fromNickname,
                                            fromDomain, postToBox,
                                            82796)
    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    # Get the json for the c2s post, not saving anything to file
    # Note that baseDir is set to None
    saveToFile = False
    clientToServer = True
    if toDomain.lower().endswith('public'):
        toPersonId = 'https://www.w3.org/ns/activitystreams#Public'
        fromDomainFull = getFullDomain(fromDomain, fromPort)
        cc = httpPrefix + '://' + fromDomainFull + '/users/' + \
            fromNickname + '/followers'
    else:
        if toDomain.lower().endswith('followers') or \
           toDomain.lower().endswith('followersonly'):
            toPersonId = \
                httpPrefix + '://' + \
                fromDomainFull + '/users/' + fromNickname + '/followers'
        else:
            toDomainFull = getFullDomain(toDomain, toPort)
            toPersonId = httpPrefix + '://' + toDomainFull + \
                '/users/' + toNickname

    postJsonObject = \
        _createPostBase(baseDir,
                        fromNickname, fromDomain, fromPort,
                        toPersonId, cc, httpPrefix, content,
                        followersOnly, saveToFile, clientToServer,
                        commentsEnabled,
                        attachImageFilename, mediaType,
                        imageDescription,
                        False, isArticle, inReplyTo,
                        inReplyToAtomUri, subject,
                        False, None, None, None, None, None,
                        None, None, None,
                        None, None, None, None, None)

    authHeader = createBasicAuthHeader(fromNickname, password)

    if attachImageFilename:
        headers = {
            'host': fromDomain,
            'Authorization': authHeader
        }
        postResult = \
            postImage(session, attachImageFilename, [],
                      inboxUrl, headers)
        if not postResult:
            if debug:
                print('DEBUG: Failed to upload image')
#            return 9

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postDumps = json.dumps(postJsonObject)
    postResult = \
        postJsonString(session, postDumps, [],
                       inboxUrl, headers, debug)
    if not postResult:
        if debug:
            print('DEBUG: POST failed for c2s to '+inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST success')
    return 0


def groupFollowersByDomain(baseDir: str, nickname: str, domain: str) -> {}:
    """Returns a dictionary with followers grouped by domain
    """
    handle = nickname + '@' + domain
    followersFilename = baseDir + '/accounts/' + handle + '/followers.txt'
    if not os.path.isfile(followersFilename):
        return None
    grouped = {}
    with open(followersFilename, "r") as f:
        for followerHandle in f:
            if '@' in followerHandle:
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
    elif isinstance(postJsonObject['object'], dict):
        if not postJsonObject['object'].get('to'):
            return
        if len(postJsonObject['object']['to']) > 1:
            return
        if len(postJsonObject['object']['to']) == 0:
            return
        if not postJsonObject['object']['to'][0].endswith('#Public'):
            return
        if postJsonObject['object'].get('cc'):
            return
        postJsonObject['object']['cc'] = postJsonObject['actor'] + '/followers'


def sendSignedJson(postJsonObject: {}, session, baseDir: str,
                   nickname: str, domain: str, port: int,
                   toNickname: str, toDomain: str, toPort: int, cc: str,
                   httpPrefix: str, saveToFile: bool, clientToServer: bool,
                   federationList: [],
                   sendThreads: [], postLog: [], cachedWebfingers: {},
                   personCache: {}, debug: bool, projectVersion: str) -> int:
    """Sends a signed json object to an inbox/outbox
    """
    if debug:
        print('DEBUG: sendSignedJson start')
    if not session:
        print('WARN: No session specified for sendSignedJson')
        return 8
    withDigest = True

    if toDomain.endswith('.onion') or toDomain.endswith('.i2p'):
        httpPrefix = 'http'

#    sharedInbox = False
    if toNickname == 'inbox':
        # shared inbox actor on @domain@domain
        toNickname = toDomain
#        sharedInbox = True

    toDomain = getFullDomain(toDomain, toPort)

    toDomainUrl = httpPrefix + '://' + toDomain
    if not siteIsActive(toDomainUrl):
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
    wfRequest = webfingerHandle(session, handle, httpPrefix, cachedWebfingers,
                                domain, projectVersion)
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

    if not clientToServer:
        postToBox = 'inbox'
    else:
        postToBox = 'outbox'

    # get the actor inbox/outbox for the To handle
    (inboxUrl, pubKeyId, pubKey, toPersonId, sharedInboxUrl, avatarUrl,
     displayName) = getPersonBox(baseDir, session, wfRequest,
                                 personCache,
                                 projectVersion, httpPrefix,
                                 nickname, domain, postToBox,
                                 30873)

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
    privateKeyPem = _getPersonKey(nickname, domain, baseDir, 'private', debug)
    if len(privateKeyPem) == 0:
        if debug:
            print('DEBUG: Private key not found for ' +
                  nickname + '@' + domain + ' in ' + baseDir + '/keys/private')
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
        except Exception as e:
            print('WARN: failed to JSON-LD sign post, ' + str(e))
            pass

    # convert json to string so that there are no
    # subsequent conversions after creating message body digest
    postJsonStr = json.dumps(postJsonObject)

    # construct the http header, including the message body digest
    signatureHeaderJson = \
        createSignedHeader(privateKeyPem, nickname, domain, port,
                           toDomain, toPort,
                           postPath, httpPrefix, withDigest, postJsonStr)

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
                              inboxUrl, baseDir,
                              signatureHeaderJson.copy(),
                              postLog,
                              debug), daemon=True)
    sendThreads.append(thr)
    # thr.start()
    return 0


def addToField(activityType: str, postJsonObject: {},
               debug: bool) -> ({}, bool):
    """The Follow activity doesn't have a 'to' field and so one
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
                        print('DEBUG: "to" field assigned to Follow')
                    toAddress = postJsonObject['object']
                    if '/statuses/' in toAddress:
                        toAddress = toAddress.split('/statuses/')[0]
                    postJsonObject['to'] = [toAddress]
                    toFieldAdded = True
        elif isinstance(postJsonObject['object'], dict):
            if postJsonObject['object'].get('type'):
                if postJsonObject['object']['type'] == activityType:
                    isSameType = True
                    if isinstance(postJsonObject['object']['object'], str):
                        if debug:
                            print('DEBUG: "to" field assigned to Follow')
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


def sendToNamedAddresses(session, baseDir: str,
                         nickname: str, domain: str,
                         onionDomain: str, i2pDomain: str, port: int,
                         httpPrefix: str, federationList: [],
                         sendThreads: [], postLog: [],
                         cachedWebfingers: {}, personCache: {},
                         postJsonObject: {}, debug: bool,
                         projectVersion: str) -> None:
    """sends a post to the specific named addresses in to/cc
    """
    if not session:
        print('WARN: No session for sendToNamedAddresses')
        return
    if not postJsonObject.get('object'):
        return
    if isinstance(postJsonObject['object'], dict):
        isProfileUpdate = False
        # for actor updates there is no 'to' within the object
        if postJsonObject['object'].get('type') and postJsonObject.get('type'):
            if (postJsonObject['type'] == 'Update' and
                (postJsonObject['object']['type'] == 'Person' or
                 postJsonObject['object']['type'] == 'Application' or
                 postJsonObject['object']['type'] == 'Group' or
                 postJsonObject['object']['type'] == 'Service')):
                # use the original object, which has a 'to'
                recipientsObject = postJsonObject
                isProfileUpdate = True

        if not isProfileUpdate:
            if not postJsonObject['object'].get('to'):
                if debug:
                    pprint(postJsonObject)
                    print('DEBUG: ' +
                          'no "to" field when sending to named addresses')
                if postJsonObject['object'].get('type'):
                    if postJsonObject['object']['type'] == 'Follow':
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
    clientToServer = False
    for address in recipients:
        toNickname = getNicknameFromActor(address)
        if not toNickname:
            continue
        toDomain, toPort = getDomainFromActor(address)
        if not toDomain:
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
        fromHttpPrefix = httpPrefix
        if onionDomain:
            if toDomain.endswith('.onion'):
                fromDomain = onionDomain
                fromHttpPrefix = 'http'
        elif i2pDomain:
            if toDomain.endswith('.i2p'):
                fromDomain = i2pDomain
                fromHttpPrefix = 'http'
        cc = []
        sendSignedJson(postJsonObject, session, baseDir,
                       nickname, fromDomain, port,
                       toNickname, toDomain, toPort,
                       cc, fromHttpPrefix, True, clientToServer,
                       federationList,
                       sendThreads, postLog, cachedWebfingers,
                       personCache, debug, projectVersion)


def _hasSharedInbox(session, httpPrefix: str, domain: str) -> bool:
    """Returns true if the given domain has a shared inbox
    This tries the new and the old way of webfingering the shared inbox
    """
    tryHandles = [
        domain + '@' + domain,
        'inbox@' + domain
    ]
    for handle in tryHandles:
        wfRequest = webfingerHandle(session, handle,
                                    httpPrefix, {},
                                    None, __version__)
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
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if not postJsonObject['object'].get('type'):
        return False
    activityType = postJsonObject['object']['type']
    if activityType == 'Person' or \
       activityType == 'Application' or \
       activityType == 'Group' or \
       activityType == 'Service':
        return True
    return False


def sendToFollowers(session, baseDir: str,
                    nickname: str,
                    domain: str,
                    onionDomain: str, i2pDomain: str, port: int,
                    httpPrefix: str, federationList: [],
                    sendThreads: [], postLog: [],
                    cachedWebfingers: {}, personCache: {},
                    postJsonObject: {}, debug: bool,
                    projectVersion: str) -> None:
    """sends a post to the followers of the given nickname
    """
    print('sendToFollowers')
    if not session:
        print('WARN: No session for sendToFollowers')
        return
    if not _postIsAddressedToFollowers(baseDir, nickname, domain,
                                       port, httpPrefix,
                                       postJsonObject):
        if debug:
            print('Post is not addressed to followers')
        return
    print('Post is addressed to followers')

    grouped = groupFollowersByDomain(baseDir, nickname, domain)
    if not grouped:
        if debug:
            print('Post to followers did not resolve any domains')
        return
    print('Post to followers resolved domains')
    print(str(grouped))

    # this is after the message has arrived at the server
    clientToServer = False

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

        # check that the follower's domain is active
        followerDomainUrl = httpPrefix + '://' + followerDomain
        if not siteIsActive(followerDomainUrl):
            print('Sending post to followers domain is inactive: ' +
                  followerDomainUrl)
            continue
        print('Sending post to followers domain is active: ' +
              followerDomainUrl)

        withSharedInbox = _hasSharedInbox(session, httpPrefix, followerDomain)
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
            toPort = toDomain.split(':')[1]
            toDomain = toDomain.split(':')[0]

        cc = ''

        # if we are sending to an onion domain and we
        # have an alt onion domain then use the alt
        fromDomain = domain
        fromHttpPrefix = httpPrefix
        if onionDomain:
            if toDomain.endswith('.onion'):
                fromDomain = onionDomain
                fromHttpPrefix = 'http'
        elif i2pDomain:
            if toDomain.endswith('.i2p'):
                fromDomain = i2pDomain
                fromHttpPrefix = 'http'

        if withSharedInbox:
            toNickname = followerHandles[index].split('@')[0]

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

            sendSignedJson(postJsonObject, session, baseDir,
                           nickname, fromDomain, port,
                           toNickname, toDomain, toPort,
                           cc, fromHttpPrefix, True, clientToServer,
                           federationList,
                           sendThreads, postLog, cachedWebfingers,
                           personCache, debug, projectVersion)
        else:
            # send to individual followers without using a shared inbox
            for handle in followerHandles:
                print('Sending post to followers ' + handle)
                toNickname = handle.split('@')[0]

                if postJsonObject['type'] != 'Update':
                    print('Sending post to followers from ' +
                          nickname + '@' + domain + ' to ' +
                          toNickname + '@' + toDomain)
                else:
                    print('Sending post to followers profile update from ' +
                          nickname + '@' + domain + ' to ' +
                          toNickname + '@' + toDomain)

                sendSignedJson(postJsonObject, session, baseDir,
                               nickname, fromDomain, port,
                               toNickname, toDomain, toPort,
                               cc, fromHttpPrefix, True, clientToServer,
                               federationList,
                               sendThreads, postLog, cachedWebfingers,
                               personCache, debug, projectVersion)

        time.sleep(4)

    if debug:
        print('DEBUG: End of sendToFollowers')

    sendingEndTime = datetime.datetime.utcnow()
    sendingMins = int((sendingEndTime - sendingStartTime).total_seconds() / 60)
    print('Sending post to followers ends ' + str(sendingMins) + ' mins')


def sendToFollowersThread(session, baseDir: str,
                          nickname: str,
                          domain: str,
                          onionDomain: str, i2pDomain: str, port: int,
                          httpPrefix: str, federationList: [],
                          sendThreads: [], postLog: [],
                          cachedWebfingers: {}, personCache: {},
                          postJsonObject: {}, debug: bool,
                          projectVersion: str):
    """Returns a thread used to send a post to followers
    """
    sendThread = \
        threadWithTrace(target=sendToFollowers,
                        args=(session, baseDir,
                              nickname, domain,
                              onionDomain, i2pDomain, port,
                              httpPrefix, federationList,
                              sendThreads, postLog,
                              cachedWebfingers, personCache,
                              postJsonObject.copy(), debug,
                              projectVersion), daemon=True)
    try:
        sendThread.start()
    except SocketError as e:
        print('WARN: socket error while starting ' +
              'thread to send to followers. ' + str(e))
        return None
    except ValueError as e:
        print('WARN: error while starting ' +
              'thread to send to followers. ' + str(e))
        return None
    return sendThread


def createInbox(recentPostsCache: {},
                session, baseDir: str, nickname: str, domain: str, port: int,
                httpPrefix: str, itemsPerPage: int, headerOnly: bool,
                pageNumber=None) -> {}:
    return _createBoxIndexed(recentPostsCache,
                             session, baseDir, 'inbox',
                             nickname, domain, port, httpPrefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createBookmarksTimeline(session, baseDir: str, nickname: str, domain: str,
                            port: int, httpPrefix: str, itemsPerPage: int,
                            headerOnly: bool, pageNumber=None) -> {}:
    return _createBoxIndexed({}, session, baseDir, 'tlbookmarks',
                             nickname, domain,
                             port, httpPrefix, itemsPerPage, headerOnly,
                             True, 0, False, 0, pageNumber)


def createEventsTimeline(recentPostsCache: {},
                         session, baseDir: str, nickname: str, domain: str,
                         port: int, httpPrefix: str, itemsPerPage: int,
                         headerOnly: bool, pageNumber=None) -> {}:
    return _createBoxIndexed(recentPostsCache, session, baseDir, 'tlevents',
                             nickname, domain,
                             port, httpPrefix, itemsPerPage, headerOnly,
                             True, 0, False, 0, pageNumber)


def createDMTimeline(recentPostsCache: {},
                     session, baseDir: str, nickname: str, domain: str,
                     port: int, httpPrefix: str, itemsPerPage: int,
                     headerOnly: bool, pageNumber=None) -> {}:
    return _createBoxIndexed(recentPostsCache,
                             session, baseDir, 'dm', nickname,
                             domain, port, httpPrefix, itemsPerPage,
                             headerOnly, True, 0, False, 0, pageNumber)


def createRepliesTimeline(recentPostsCache: {},
                          session, baseDir: str, nickname: str, domain: str,
                          port: int, httpPrefix: str, itemsPerPage: int,
                          headerOnly: bool, pageNumber=None) -> {}:
    return _createBoxIndexed(recentPostsCache, session, baseDir, 'tlreplies',
                             nickname, domain, port, httpPrefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createBlogsTimeline(session, baseDir: str, nickname: str, domain: str,
                        port: int, httpPrefix: str, itemsPerPage: int,
                        headerOnly: bool, pageNumber=None) -> {}:
    return _createBoxIndexed({}, session, baseDir, 'tlblogs', nickname,
                             domain, port, httpPrefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createFeaturesTimeline(session, baseDir: str, nickname: str, domain: str,
                           port: int, httpPrefix: str, itemsPerPage: int,
                           headerOnly: bool, pageNumber=None) -> {}:
    return _createBoxIndexed({}, session, baseDir, 'tlfeatures', nickname,
                             domain, port, httpPrefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createMediaTimeline(session, baseDir: str, nickname: str, domain: str,
                        port: int, httpPrefix: str, itemsPerPage: int,
                        headerOnly: bool, pageNumber=None) -> {}:
    return _createBoxIndexed({}, session, baseDir, 'tlmedia', nickname,
                             domain, port, httpPrefix,
                             itemsPerPage, headerOnly, True,
                             0, False, 0, pageNumber)


def createNewsTimeline(session, baseDir: str, nickname: str, domain: str,
                       port: int, httpPrefix: str, itemsPerPage: int,
                       headerOnly: bool, newswireVotesThreshold: int,
                       positiveVoting: bool, votingTimeMins: int,
                       pageNumber=None) -> {}:
    return _createBoxIndexed({}, session, baseDir, 'outbox', 'news',
                             domain, port, httpPrefix,
                             itemsPerPage, headerOnly, True,
                             newswireVotesThreshold, positiveVoting,
                             votingTimeMins, pageNumber)


def createOutbox(session, baseDir: str, nickname: str, domain: str,
                 port: int, httpPrefix: str,
                 itemsPerPage: int, headerOnly: bool, authorized: bool,
                 pageNumber=None) -> {}:
    return _createBoxIndexed({}, session, baseDir, 'outbox',
                             nickname, domain, port, httpPrefix,
                             itemsPerPage, headerOnly, authorized,
                             0, False, 0, pageNumber)


def createModeration(baseDir: str, nickname: str, domain: str, port: int,
                     httpPrefix: str, itemsPerPage: int, headerOnly: bool,
                     pageNumber=None) -> {}:
    boxDir = createPersonDir(nickname, domain, baseDir, 'inbox')
    boxname = 'moderation'

    domain = getFullDomain(domain, port)

    if not pageNumber:
        pageNumber = 1

    pageStr = '?page=' + str(pageNumber)
    boxUrl = httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname
    boxHeader = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'first': boxUrl+'?page=true',
        'id': boxUrl,
        'last': boxUrl+'?page=true',
        'totalItems': 0,
        'type': 'OrderedCollection'
    }
    boxItems = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': boxUrl+pageStr,
        'orderedItems': [
        ],
        'partOf': boxUrl,
        'type': 'OrderedCollectionPage'
    }

    if isModerator(baseDir, nickname):
        moderationIndexFile = baseDir + '/accounts/moderation.txt'
        if os.path.isfile(moderationIndexFile):
            with open(moderationIndexFile, "r") as f:
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


def isDM(postJsonObject: {}) -> bool:
    """Returns true if the given post is a DM
    """
    if postJsonObject['type'] != 'Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if postJsonObject['object']['type'] != 'Note' and \
       postJsonObject['object']['type'] != 'Patch' and \
       postJsonObject['object']['type'] != 'EncryptedMessage' and \
       postJsonObject['object']['type'] != 'Article':
        return False
    if postJsonObject['object'].get('moderationStatus'):
        return False
    fields = ('to', 'cc')
    for f in fields:
        if not postJsonObject['object'].get(f):
            continue
        for toAddress in postJsonObject['object'][f]:
            if toAddress.endswith('#Public'):
                return False
            if toAddress.endswith('followers'):
                return False
    return True


def isImageMedia(session, baseDir: str, httpPrefix: str,
                 nickname: str, domain: str,
                 postJsonObject: {}, translate: {},
                 YTReplacementDomain: str,
                 allowLocalNetworkAccess: bool) -> bool:
    """Returns true if the given post has attached image media
    """
    if postJsonObject['type'] == 'Announce':
        postJsonAnnounce = \
            downloadAnnounce(session, baseDir, httpPrefix,
                             nickname, domain, postJsonObject,
                             __version__, translate,
                             YTReplacementDomain,
                             allowLocalNetworkAccess)
        if postJsonAnnounce:
            postJsonObject = postJsonAnnounce
    if postJsonObject['type'] != 'Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if postJsonObject['object'].get('moderationStatus'):
        return False
    if postJsonObject['object']['type'] != 'Note' and \
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


def isReply(postJsonObject: {}, actor: str) -> bool:
    """Returns true if the given post is a reply to the given actor
    """
    if postJsonObject['type'] != 'Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if postJsonObject['object'].get('moderationStatus'):
        return False
    if postJsonObject['object']['type'] != 'Note' and \
       postJsonObject['object']['type'] != 'EncryptedMessage' and \
       postJsonObject['object']['type'] != 'Article':
        return False
    if postJsonObject['object'].get('inReplyTo'):
        if isinstance(postJsonObject['object']['inReplyTo'], str):
            if postJsonObject['object']['inReplyTo'].startswith(actor):
                return True
    if not postJsonObject['object'].get('tag'):
        return False
    if not isinstance(postJsonObject['object']['tag'], list):
        return False
    for tag in postJsonObject['object']['tag']:
        if not tag.get('type'):
            continue
        if tag['type'] == 'Mention':
            if not tag.get('href'):
                continue
            if actor in tag['href']:
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
                if 'mediaType' not in postStr or 'image/' not in postStr:
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


def _createBoxIndexed(recentPostsCache: {},
                      session, baseDir: str, boxname: str,
                      nickname: str, domain: str, port: int, httpPrefix: str,
                      itemsPerPage: int, headerOnly: bool, authorized: bool,
                      newswireVotesThreshold: int, positiveVoting: bool,
                      votingTimeMins: int, pageNumber=None) -> {}:
    """Constructs the box feed for a person with the given nickname
    """
    if not authorized or not pageNumber:
        pageNumber = 1

    if boxname != 'inbox' and boxname != 'dm' and \
       boxname != 'tlreplies' and boxname != 'tlmedia' and \
       boxname != 'tlblogs' and boxname != 'tlnews' and \
       boxname != 'tlfeatures' and \
       boxname != 'outbox' and boxname != 'tlbookmarks' and \
       boxname != 'bookmarks' and \
       boxname != 'tlevents':
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

    domain = getFullDomain(domain, port)

    boxActor = httpPrefix + '://' + domain + '/users/' + nickname

    pageStr = '?page=true'
    if pageNumber:
        if pageNumber < 1:
            pageNumber = 1
        try:
            pageStr = '?page=' + str(pageNumber)
        except BaseException:
            pass
    boxUrl = httpPrefix + '://' + domain + '/users/' + nickname + '/' + boxname
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

    indexFilename = \
        baseDir + '/accounts/' + timelineNickname + '@' + domain + \
        '/' + indexBoxName + '.index'
    postsCtr = 0
    if os.path.isfile(indexFilename):
        maxPostCtr = itemsPerPage * pageNumber
        with open(indexFilename, 'r') as indexFile:
            while postsCtr < maxPostCtr:
                postFilename = indexFile.readline()

                if not postFilename:
                    break

                # apply votes within this timeline
                if newswireVotesThreshold > 0:
                    # note that the presence of an arrival file also indicates
                    # that this post is moderated
                    arrivalDate = \
                        locateNewsArrival(baseDir, domain, postFilename)
                    if arrivalDate:
                        # how long has elapsed since this post arrived?
                        currDate = datetime.datetime.utcnow()
                        timeDiffMins = \
                            int((currDate - arrivalDate).total_seconds() / 60)
                        # has the voting time elapsed?
                        if timeDiffMins < votingTimeMins:
                            # voting is still happening, so don't add this
                            # post to the timeline
                            continue
                        # if there a votes file for this post?
                        votesFilename = \
                            locateNewsVotes(baseDir, domain, postFilename)
                        if votesFilename:
                            # load the votes file and count the votes
                            votesJson = loadJson(votesFilename, 0, 2)
                            if votesJson:
                                if not positiveVoting:
                                    if votesOnNewswireItem(votesJson) >= \
                                       newswireVotesThreshold:
                                        # Too many veto votes.
                                        # Continue without incrementing
                                        # the posts counter
                                        continue
                                else:
                                    if votesOnNewswireItem < \
                                       newswireVotesThreshold:
                                        # Not enough votes.
                                        # Continue without incrementing
                                        # the posts counter
                                        continue

                # Skip through any posts previous to the current page
                if postsCtr < int((pageNumber - 1) * itemsPerPage):
                    postsCtr += 1
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

                # is the post cached in memory?
                if recentPostsCache.get('index'):
                    if postUrl in recentPostsCache['index']:
                        if recentPostsCache['json'].get(postUrl):
                            url = recentPostsCache['json'][postUrl]
                            _addPostStringToTimeline(url,
                                                     boxname, postsInBox,
                                                     boxActor)
                            postsCtr += 1
                            continue

                # read the post from file
                fullPostFilename = \
                    locatePost(baseDir, nickname,
                               domain, postUrl, False)
                if fullPostFilename:
                    _addPostToTimeline(fullPostFilename, boxname,
                                       postsInBox, boxActor)
                else:
                    # if this is the features timeline
                    if timelineNickname != nickname:
                        fullPostFilename = \
                            locatePost(baseDir, timelineNickname,
                                       domain, postUrl, False)
                        if fullPostFilename:
                            _addPostToTimeline(fullPostFilename, boxname,
                                               postsInBox, boxActor)
                        else:
                            print('WARN: unable to locate post ' + postUrl)
                    else:
                        print('WARN: unable to locate post ' + postUrl)

                postsCtr += 1

    # Generate first and last entries within header
    if postsCtr > 0:
        lastPage = int(postsCtr / itemsPerPage)
        if lastPage < 1:
            lastPage = 1
        boxHeader['last'] = \
            httpPrefix + '://' + domain + '/users/' + \
            nickname + '/' + boxname + '?page=' + str(lastPage)

    if headerOnly:
        boxHeader['totalItems'] = len(postsInBox)
        prevPageStr = 'true'
        if pageNumber > 1:
            prevPageStr = str(pageNumber - 1)
        boxHeader['prev'] = \
            httpPrefix + '://' + domain + '/users/' + \
            nickname + '/' + boxname + '?page=' + prevPageStr

        nextPageStr = str(pageNumber + 1)
        boxHeader['next'] = \
            httpPrefix + '://' + domain + '/users/' + \
            nickname + '/' + boxname + '?page=' + nextPageStr
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
            continue

        # Does this post have replies?
        # This will be used to indicate that replies exist within the html
        # created by individualPostAsHtml
        p['hasReplies'] = hasReplies

        # Don't show likes, replies, DMs or shares (announces) to
        # unauthorized viewers
        if not authorized:
            if p.get('object'):
                if isinstance(p['object'], dict):
                    if not isPublicPost(p):
                        continue
                    if p['object'].get('likes'):
                        p['likes'] = {'items': []}
                    if p['object'].get('replies'):
                        p['replies'] = {}
                    if p['object'].get('shares'):
                        p['shares'] = {}
                    if p['object'].get('bookmarks'):
                        p['bookmarks'] = {}

        boxItems['orderedItems'].append(p)

    return boxItems


def expireCache(baseDir: str, personCache: {},
                httpPrefix: str, archiveDir: str,
                recentPostsCache: {},
                maxPostsInBox=32000):
    """Thread used to expire actors from the cache and archive old posts
    """
    while True:
        # once per day
        time.sleep(60 * 60 * 24)
        expirePersonCache(baseDir, personCache)
        archivePosts(baseDir, httpPrefix, archiveDir, recentPostsCache,
                     maxPostsInBox)


def archivePosts(baseDir: str, httpPrefix: str, archiveDir: str,
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

    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
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
                archivePostsForPerson(httpPrefix, nickname, domain, baseDir,
                                      'inbox', archiveSubdir,
                                      recentPostsCache, maxPostsInBox)
                if archiveDir:
                    archiveSubdir = archiveDir + '/accounts/' + \
                        handle + '/outbox'
                archivePostsForPerson(httpPrefix, nickname, domain, baseDir,
                                      'outbox', archiveSubdir,
                                      recentPostsCache, maxPostsInBox)
        break


def archivePostsForPerson(httpPrefix: str, nickname: str, domain: str,
                          baseDir: str,
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
    boxDir = createPersonDir(nickname, domain, baseDir, boxname)
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
    indexFilename = baseDir + '/accounts/' + handle + '/' + boxname + '.index'
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
            indexFile = open(indexFilename, 'w+')
            if indexFile:
                indexFile.write(newIndex)
                indexFile.close()

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
            deletePost(baseDir, httpPrefix, nickname, domain,
                       filePath, False, recentPostsCache)

        # remove cached html posts
        postCacheFilename = \
            os.path.join(postCacheDir, postFilename).replace('.json', '.html')
        if os.path.isfile(postCacheFilename):
            os.remove(postCacheFilename)

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


def getPublicPostsOfPerson(baseDir: str, nickname: str, domain: str,
                           raw: bool, simple: bool, proxyType: str,
                           port: int, httpPrefix: str,
                           debug: bool, projectVersion: str) -> None:
    """ This is really just for test purposes
    """
    print('Starting new session for getting public posts')
    session = createSession(proxyType)
    if not session:
        return
    personCache = {}
    cachedWebfingers = {}
    federationList = []

    domainFull = getFullDomain(domain, port)
    handle = httpPrefix + "://" + domainFull + "/@" + nickname
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix, cachedWebfingers,
                        domain, projectVersion)
    if not wfRequest:
        sys.exit()
    if not isinstance(wfRequest, dict):
        print('Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        sys.exit()

    (personUrl, pubKeyId, pubKey,
     personId, shaedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache,
                                            projectVersion, httpPrefix,
                                            nickname, domain, 'outbox',
                                            62524)
    maxMentions = 10
    maxEmoji = 10
    maxAttachments = 5
    _getPosts(session, personUrl, 30, maxMentions, maxEmoji,
              maxAttachments, federationList,
              personCache, raw, simple, debug,
              projectVersion, httpPrefix, domain)


def getPublicPostDomains(session, baseDir: str, nickname: str, domain: str,
                         proxyType: str, port: int, httpPrefix: str,
                         debug: bool, projectVersion: str,
                         wordFrequency: {}, domainList=[]) -> []:
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
    handle = httpPrefix + "://" + domainFull + "/@" + nickname
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix, cachedWebfingers,
                        domain, projectVersion)
    if not wfRequest:
        return domainList
    if not isinstance(wfRequest, dict):
        print('Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return domainList

    (personUrl, pubKeyId, pubKey,
     personId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache,
                                            projectVersion, httpPrefix,
                                            nickname, domain, 'outbox',
                                            92522)
    maxMentions = 99
    maxEmoji = 99
    maxAttachments = 5
    postDomains = \
        getPostDomains(session, personUrl, 64, maxMentions, maxEmoji,
                       maxAttachments, federationList,
                       personCache, debug,
                       projectVersion, httpPrefix, domain,
                       wordFrequency, domainList)
    postDomains.sort()
    return postDomains


def downloadFollowCollection(followType: str,
                             session, httpPrefix,
                             actor: str, pageNumber=1,
                             noOfPages=1) -> []:
    """Returns a list of following/followers for the given actor
    by downloading the json for their following/followers collection
    """
    prof = 'https://www.w3.org/ns/activitystreams'
    if '/channel/' not in actor or '/accounts/' not in actor:
        sessionHeaders = {
            'Accept': 'application/activity+json; profile="' + prof + '"'
        }
    else:
        sessionHeaders = {
            'Accept': 'application/ld+json; profile="' + prof + '"'
        }
    result = []
    for pageCtr in range(noOfPages):
        url = actor + '/' + followType + '?page=' + str(pageNumber + pageCtr)
        followersJson = \
            getJson(session, url, sessionHeaders, None, __version__,
                    httpPrefix, None)
        if followersJson:
            if followersJson.get('orderedItems'):
                for followerActor in followersJson['orderedItems']:
                    if followerActor not in result:
                        result.append(followerActor)
            else:
                break
        else:
            break
    return result


def getPublicPostInfo(session, baseDir: str, nickname: str, domain: str,
                      proxyType: str, port: int, httpPrefix: str,
                      debug: bool, projectVersion: str,
                      wordFrequency: {}) -> []:
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
    handle = httpPrefix + "://" + domainFull + "/@" + nickname
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix, cachedWebfingers,
                        domain, projectVersion)
    if not wfRequest:
        return {}
    if not isinstance(wfRequest, dict):
        print('Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return {}

    (personUrl, pubKeyId, pubKey,
     personId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache,
                                            projectVersion, httpPrefix,
                                            nickname, domain, 'outbox',
                                            13863)
    maxMentions = 99
    maxEmoji = 99
    maxAttachments = 5
    maxPosts = 64
    postDomains = \
        getPostDomains(session, personUrl, maxPosts, maxMentions, maxEmoji,
                       maxAttachments, federationList,
                       personCache, debug,
                       projectVersion, httpPrefix, domain,
                       wordFrequency, [])
    postDomains.sort()
    domainsInfo = {}
    for d in postDomains:
        if not domainsInfo.get(d):
            domainsInfo[d] = []

    blockedPosts = \
        _getPostsForBlockedDomains(baseDir, session, personUrl, maxPosts,
                                   maxMentions,
                                   maxEmoji, maxAttachments,
                                   federationList,
                                   personCache,
                                   debug,
                                   projectVersion, httpPrefix,
                                   domain)
    for blockedDomain, postUrlList in blockedPosts.items():
        domainsInfo[blockedDomain] += postUrlList

    return domainsInfo


def getPublicPostDomainsBlocked(session, baseDir: str,
                                nickname: str, domain: str,
                                proxyType: str, port: int, httpPrefix: str,
                                debug: bool, projectVersion: str,
                                wordFrequency: {}, domainList=[]) -> []:
    """ Returns a list of domains referenced within public posts which
    are globally blocked on this instance
    """
    postDomains = \
        getPublicPostDomains(session, baseDir, nickname, domain,
                             proxyType, port, httpPrefix,
                             debug, projectVersion,
                             wordFrequency, domainList)
    if not postDomains:
        return []

    blockingFilename = baseDir + '/accounts/blocking.txt'
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


def _getNonMutualsOfPerson(baseDir: str,
                           nickname: str, domain: str) -> []:
    """Returns the followers who are not mutuals of a person
    i.e. accounts which follow you but you don't follow them
    """
    followers = \
        getFollowersList(baseDir, nickname, domain, 'followers.txt')
    following = \
        getFollowersList(baseDir, nickname, domain, 'following.txt')
    nonMutuals = []
    for handle in followers:
        if handle not in following:
            nonMutuals.append(handle)
    return nonMutuals


def checkDomains(session, baseDir: str,
                 nickname: str, domain: str,
                 proxyType: str, port: int, httpPrefix: str,
                 debug: bool, projectVersion: str,
                 maxBlockedDomains: int, singleCheck: bool) -> None:
    """Checks follower accounts for references to globally blocked domains
    """
    wordFrequency = {}
    nonMutuals = _getNonMutualsOfPerson(baseDir, nickname, domain)
    if not nonMutuals:
        print('No non-mutual followers were found')
        return
    followerWarningFilename = baseDir + '/accounts/followerWarnings.txt'
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
                getPublicPostDomainsBlocked(session, baseDir,
                                            nonMutualNickname,
                                            nonMutualDomain,
                                            proxyType, port, httpPrefix,
                                            debug, projectVersion,
                                            wordFrequency, [])
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
                getPublicPostDomainsBlocked(session, baseDir,
                                            nonMutualNickname,
                                            nonMutualDomain,
                                            proxyType, port, httpPrefix,
                                            debug, projectVersion,
                                            wordFrequency, [])
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


def populateRepliesJson(baseDir: str, nickname: str, domain: str,
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
                    baseDir + \
                    '/accounts/' + nickname + '@' + \
                    domain+'/' + \
                    boxname+'/' + \
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
                    baseDir + \
                    '/accounts/inbox@' + \
                    domain+'/inbox/' + \
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


def _rejectAnnounce(announceFilename: str):
    """Marks an announce as rejected
    """
    if not os.path.isfile(announceFilename + '.reject'):
        rejectAnnounceFile = open(announceFilename + '.reject', "w+")
        if rejectAnnounceFile:
            rejectAnnounceFile.write('\n')
            rejectAnnounceFile.close()


def downloadAnnounce(session, baseDir: str, httpPrefix: str,
                     nickname: str, domain: str,
                     postJsonObject: {}, projectVersion: str,
                     translate: {}, YTReplacementDomain: str,
                     allowLocalNetworkAccess: bool) -> {}:
    """Download the post referenced by an announce
    """
    if not postJsonObject.get('object'):
        return None
    if not isinstance(postJsonObject['object'], str):
        return None

    # get the announced post
    announceCacheDir = baseDir + '/cache/announce/' + nickname
    if not os.path.isdir(announceCacheDir):
        os.mkdir(announceCacheDir)
    announceFilename = \
        announceCacheDir + '/' + \
        postJsonObject['object'].replace('/', '#') + '.json'

    if os.path.isfile(announceFilename + '.reject'):
        return None

    if os.path.isfile(announceFilename):
        print('Reading cached Announce content for ' +
              postJsonObject['object'])
        postJsonObject = loadJson(announceFilename)
        if postJsonObject:
            return postJsonObject
    else:
        profileStr = 'https://www.w3.org/ns/activitystreams'
        asHeader = {
            'Accept': 'application/activity+json; profile="' + profileStr + '"'
        }
        if '/channel/' in postJsonObject['actor'] or \
           '/accounts/' in postJsonObject['actor']:
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
        actorNickname = getNicknameFromActor(postJsonObject['actor'])
        actorDomain, actorPort = getDomainFromActor(postJsonObject['actor'])
        if not actorDomain:
            print('Announce actor does not contain a ' +
                  'valid domain or port number: ' +
                  str(postJsonObject['actor']))
            return None
        if isBlocked(baseDir, nickname, domain, actorNickname, actorDomain):
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
        if isBlocked(baseDir, nickname, domain, objectNickname, objectDomain):
            if objectNickname and objectDomain:
                print('Announce download blocked object: ' +
                      objectNickname + '@' + objectDomain)
            else:
                print('Announce download blocked object: ' +
                      str(postJsonObject['object']))
            return None
        print('Downloading Announce content for ' + postJsonObject['object'])
        announcedJson = \
            getJson(session, postJsonObject['object'], asHeader,
                    None, projectVersion, httpPrefix, domain)

        if not announcedJson:
            return None

        if not isinstance(announcedJson, dict):
            print('WARN: announce json is not a dict - ' +
                  postJsonObject['object'])
            _rejectAnnounce(announceFilename)
            return None
        if not announcedJson.get('id'):
            _rejectAnnounce(announceFilename)
            return None
        if '/statuses/' not in announcedJson['id']:
            _rejectAnnounce(announceFilename)
            return None
        if not hasUsersPath(announcedJson['id']):
            _rejectAnnounce(announceFilename)
            return None
        if not announcedJson.get('type'):
            _rejectAnnounce(announceFilename)
            return None
        if announcedJson['type'] != 'Note' and \
           announcedJson['type'] != 'Article':
            # You can only announce Note or Article types
            _rejectAnnounce(announceFilename)
            return None
        if not announcedJson.get('content'):
            _rejectAnnounce(announceFilename)
            return None
        if not announcedJson.get('published'):
            _rejectAnnounce(announceFilename)
            return None
        if not validPostDate(announcedJson['published']):
            _rejectAnnounce(announceFilename)
            return None

        # Check the content of the announce
        contentStr = announcedJson['content']
        if dangerousMarkup(contentStr, allowLocalNetworkAccess):
            _rejectAnnounce(announceFilename)
            return None

        if isFiltered(baseDir, nickname, domain, contentStr):
            _rejectAnnounce(announceFilename)
            return None

        # remove any long words
        contentStr = removeLongWords(contentStr, 40, [])

        # remove text formatting, such as bold/italics
        contentStr = removeTextFormatting(contentStr)

        # set the content after santitization
        announcedJson['content'] = contentStr

        # wrap in create to be consistent with other posts
        announcedJson = \
            outboxMessageCreateWrap(httpPrefix,
                                    actorNickname, actorDomain, actorPort,
                                    announcedJson)
        if announcedJson['type'] != 'Create':
            # Create wrap failed
            _rejectAnnounce(announceFilename)
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
            if isBlocked(baseDir, nickname, domain,
                         attributedNickname, attributedDomain):
                _rejectAnnounce(announceFilename)
                return None
        postJsonObject = announcedJson
        replaceYouTube(postJsonObject, YTReplacementDomain)
        if saveJson(postJsonObject, announceFilename):
            return postJsonObject
    return None


def isMuted(baseDir: str, nickname: str, domain: str, postId: str) -> bool:
    """Returns true if the given post is muted
    """
    postFilename = locatePost(baseDir, nickname, domain, postId)
    if not postFilename:
        return False
    if os.path.isfile(postFilename + '.muted'):
        return True
    return False


def mutePost(baseDir: str, nickname: str, domain: str, postId: str,
             recentPostsCache: {}) -> None:
    """ Mutes the given post
    """
    postFilename = locatePost(baseDir, nickname, domain, postId)
    if not postFilename:
        return
    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return

    # remove cached post so that the muted version gets recreated
    # without its content text and/or image
    cachedPostFilename = \
        getCachedPostFilename(baseDir, nickname, domain, postJsonObject)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            os.remove(cachedPostFilename)

    muteFile = open(postFilename + '.muted', 'w+')
    if muteFile:
        muteFile.write('\n')
        muteFile.close()
        print('MUTE: ' + postFilename + '.muted file added')

    # if the post is in the recent posts cache then mark it as muted
    if recentPostsCache.get('index'):
        postId = \
            removeIdEnding(postJsonObject['id']).replace('/', '#')
        if postId in recentPostsCache['index']:
            print('MUTE: ' + postId + ' is in recent posts cache')
            if recentPostsCache['json'].get(postId):
                postJsonObject['muted'] = True
                recentPostsCache['json'][postId] = json.dumps(postJsonObject)
                if recentPostsCache.get('html'):
                    if recentPostsCache['html'].get(postId):
                        del recentPostsCache['html'][postId]
                print('MUTE: ' + postId +
                      ' marked as muted in recent posts memory cache')


def unmutePost(baseDir: str, nickname: str, domain: str, postId: str,
               recentPostsCache: {}) -> None:
    """ Unmutes the given post
    """
    postFilename = locatePost(baseDir, nickname, domain, postId)
    if not postFilename:
        return
    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return

    muteFilename = postFilename + '.muted'
    if os.path.isfile(muteFilename):
        os.remove(muteFilename)
        print('UNMUTE: ' + muteFilename + ' file removed')

    # remove cached post so that the muted version gets recreated
    # with its content text and/or image
    cachedPostFilename = \
        getCachedPostFilename(baseDir, nickname, domain, postJsonObject)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            os.remove(cachedPostFilename)

    # if the post is in the recent posts cache then mark it as unmuted
    if recentPostsCache.get('index'):
        postId = \
            removeIdEnding(postJsonObject['id']).replace('/', '#')
        if postId in recentPostsCache['index']:
            print('UNMUTE: ' + postId + ' is in recent posts cache')
            if recentPostsCache['json'].get(postId):
                postJsonObject['muted'] = False
                recentPostsCache['json'][postId] = json.dumps(postJsonObject)
                if recentPostsCache.get('html'):
                    if recentPostsCache['html'].get(postId):
                        del recentPostsCache['html'][postId]
                print('UNMUTE: ' + postId +
                      ' marked as unmuted in recent posts cache')


def sendBlockViaServer(baseDir: str, session,
                       fromNickname: str, password: str,
                       fromDomain: str, fromPort: int,
                       httpPrefix: str, blockedUrl: str,
                       cachedWebfingers: {}, personCache: {},
                       debug: bool, projectVersion: str) -> {}:
    """Creates a block via c2s
    """
    if not session:
        print('WARN: No session for sendBlockViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://' + fromDomainFull + '/users/' + \
        fromNickname + '/followers'

    blockActor = httpPrefix + '://' + fromDomainFull + '/users/' + fromNickname
    newBlockJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Block',
        'actor': blockActor,
        'object': blockedUrl,
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, httpPrefix,
                                cachedWebfingers,
                                fromDomain, projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox, avatarUrl,
     displayName) = getPersonBox(baseDir, session, wfRequest,
                                 personCache,
                                 projectVersion, httpPrefix, fromNickname,
                                 fromDomain, postToBox, 72652)

    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(session, newBlockJson, [], inboxUrl, headers)
    if not postResult:
        print('WARN: Unable to post block')

    if debug:
        print('DEBUG: c2s POST block success')

    return newBlockJson


def sendUndoBlockViaServer(baseDir: str, session,
                           fromNickname: str, password: str,
                           fromDomain: str, fromPort: int,
                           httpPrefix: str, blockedUrl: str,
                           cachedWebfingers: {}, personCache: {},
                           debug: bool, projectVersion: str) -> {}:
    """Creates a block via c2s
    """
    if not session:
        print('WARN: No session for sendBlockViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://' + fromDomainFull + '/users/' + \
        fromNickname + '/followers'

    blockActor = httpPrefix + '://' + fromDomainFull + '/users/' + fromNickname
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

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, httpPrefix,
                                cachedWebfingers,
                                fromDomain, projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox, avatarUrl,
     displayName) = getPersonBox(baseDir, session, wfRequest, personCache,
                                 projectVersion, httpPrefix, fromNickname,
                                 fromDomain, postToBox, 53892)

    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(session, newBlockJson, [], inboxUrl, headers)
    if not postResult:
        print('WARN: Unable to post block')

    if debug:
        print('DEBUG: c2s POST block success')

    return newBlockJson


def postIsMuted(baseDir: str, nickname: str, domain: str,
                postJsonObject: {}, messageId: str) -> bool:
    """ Returns true if the given post is muted
    """
    isMuted = postJsonObject.get('muted')
    if isMuted is True or isMuted is False:
        return isMuted
    postDir = baseDir + '/accounts/' + nickname + '@' + domain
    muteFilename = \
        postDir + '/inbox/' + messageId.replace('/', '#') + '.json.muted'
    if os.path.isfile(muteFilename):
        return True
    muteFilename = \
        postDir + '/outbox/' + messageId.replace('/', '#') + '.json.muted'
    if os.path.isfile(muteFilename):
        return True
    muteFilename = \
        baseDir + '/accounts/cache/announce/' + nickname + \
        '/' + messageId.replace('/', '#') + '.json.muted'
    if os.path.isfile(muteFilename):
        return True
    return False
