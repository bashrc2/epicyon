__filename__ = "webapp_utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from collections import OrderedDict
from utils import getProtocolPrefixes
from utils import loadJson
from utils import getJson
from utils import getConfigParam
from cache import getPersonFromCache
from cache import storePersonInCache


def getAltPath(actor: str, domainFull: str, callingDomain: str) -> str:
    """Returns alternate path from the actor
    eg. https://clearnetdomain/path becomes http://oniondomain/path
    """
    postActor = actor
    if callingDomain not in actor and domainFull in actor:
        if callingDomain.endswith('.onion') or \
           callingDomain.endswith('.i2p'):
            postActor = \
                'http://' + callingDomain + actor.split(domainFull)[1]
            print('Changed POST domain from ' + actor + ' to ' + postActor)
    return postActor


def getContentWarningButton(postID: str, translate: {},
                            content: str) -> str:
    """Returns the markup for a content warning button
    """
    return '       <details><summary><b>' + \
        translate['SHOW MORE'] + '</b></summary>' + \
        '<div id="' + postID + '">' + content + \
        '</div></details>\n'


def getActorPropertyUrl(actorJson: {}, propertyName: str) -> str:
    """Returns a url property from an actor
    """
    if not actorJson.get('attachment'):
        return ''
    propertyName = propertyName.lower()
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith(propertyName):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = propertyValue['value'].strip()
        prefixes = getProtocolPrefixes()
        prefixFound = False
        for prefix in prefixes:
            if propertyValue['value'].startswith(prefix):
                prefixFound = True
                break
        if not prefixFound:
            continue
        if '.' not in propertyValue['value']:
            continue
        if ' ' in propertyValue['value']:
            continue
        if ',' in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''


def getBlogAddress(actorJson: {}) -> str:
    """Returns blog address for the given actor
    """
    return getActorPropertyUrl(actorJson, 'Blog')


def setActorPropertyUrl(actorJson: {}, propertyName: str, url: str) -> None:
    """Sets a url for the given actor property
    """
    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    propertyNameLower = propertyName.lower()

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith(propertyNameLower):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)

    prefixes = getProtocolPrefixes()
    prefixFound = False
    for prefix in prefixes:
        if url.startswith(prefix):
            prefixFound = True
            break
    if not prefixFound:
        return
    if '.' not in url:
        return
    if ' ' in url:
        return
    if ',' in url:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith(propertyNameLower):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = url
        return

    newAddress = {
        "name": propertyName,
        "type": "PropertyValue",
        "value": url
    }
    actorJson['attachment'].append(newAddress)


def setBlogAddress(actorJson: {}, blogAddress: str) -> None:
    """Sets an blog address for the given actor
    """
    setActorPropertyUrl(actorJson, 'Blog', blogAddress)


def updateAvatarImageCache(session, baseDir: str, httpPrefix: str,
                           actor: str, avatarUrl: str,
                           personCache: {}, allowDownloads: bool,
                           force=False) -> str:
    """Updates the cached avatar for the given actor
    """
    if not avatarUrl:
        return None
    actorStr = actor.replace('/', '-')
    avatarImagePath = baseDir + '/cache/avatars/' + actorStr
    if avatarUrl.endswith('.png') or \
       '.png?' in avatarUrl:
        sessionHeaders = {
            'Accept': 'image/png'
        }
        avatarImageFilename = avatarImagePath + '.png'
    elif (avatarUrl.endswith('.jpg') or
          avatarUrl.endswith('.jpeg') or
          '.jpg?' in avatarUrl or
          '.jpeg?' in avatarUrl):
        sessionHeaders = {
            'Accept': 'image/jpeg'
        }
        avatarImageFilename = avatarImagePath + '.jpg'
    elif avatarUrl.endswith('.gif') or '.gif?' in avatarUrl:
        sessionHeaders = {
            'Accept': 'image/gif'
        }
        avatarImageFilename = avatarImagePath + '.gif'
    elif avatarUrl.endswith('.webp') or '.webp?' in avatarUrl:
        sessionHeaders = {
            'Accept': 'image/webp'
        }
        avatarImageFilename = avatarImagePath + '.webp'
    elif avatarUrl.endswith('.avif') or '.avif?' in avatarUrl:
        sessionHeaders = {
            'Accept': 'image/avif'
        }
        avatarImageFilename = avatarImagePath + '.avif'
    else:
        return None

    if (not os.path.isfile(avatarImageFilename) or force) and allowDownloads:
        try:
            print('avatar image url: ' + avatarUrl)
            result = session.get(avatarUrl,
                                 headers=sessionHeaders,
                                 params=None)
            if result.status_code < 200 or \
               result.status_code > 202:
                print('Avatar image download failed with status ' +
                      str(result.status_code))
                # remove partial download
                if os.path.isfile(avatarImageFilename):
                    os.remove(avatarImageFilename)
            else:
                with open(avatarImageFilename, 'wb') as f:
                    f.write(result.content)
                    print('avatar image downloaded for ' + actor)
                    return avatarImageFilename.replace(baseDir + '/cache', '')
        except Exception as e:
            print('Failed to download avatar image: ' + str(avatarUrl))
            print(e)
        prof = 'https://www.w3.org/ns/activitystreams'
        if '/channel/' not in actor or '/accounts/' not in actor:
            sessionHeaders = {
                'Accept': 'application/activity+json; profile="' + prof + '"'
            }
        else:
            sessionHeaders = {
                'Accept': 'application/ld+json; profile="' + prof + '"'
            }
        personJson = \
            getJson(session, actor, sessionHeaders, None, __version__,
                    httpPrefix, None)
        if personJson:
            if not personJson.get('id'):
                return None
            if not personJson.get('publicKey'):
                return None
            if not personJson['publicKey'].get('publicKeyPem'):
                return None
            if personJson['id'] != actor:
                return None
            if not personCache.get(actor):
                return None
            if personCache[actor]['actor']['publicKey']['publicKeyPem'] != \
               personJson['publicKey']['publicKeyPem']:
                print("ERROR: " +
                      "public keys don't match when downloading actor for " +
                      actor)
                return None
            storePersonInCache(baseDir, actor, personJson, personCache,
                               allowDownloads)
            return getPersonAvatarUrl(baseDir, actor, personCache,
                                      allowDownloads)
        return None
    return avatarImageFilename.replace(baseDir + '/cache', '')


def getImageExtensions() -> []:
    """Returns a list of the possible image file extensions
    """
    return ('png', 'jpg', 'jpeg', 'gif', 'webp', 'avif')


def getPersonAvatarUrl(baseDir: str, personUrl: str, personCache: {},
                       allowDownloads: bool) -> str:
    """Returns the avatar url for the person
    """
    personJson = \
        getPersonFromCache(baseDir, personUrl, personCache, allowDownloads)
    if not personJson:
        return None

    # get from locally stored image
    actorStr = personJson['id'].replace('/', '-')
    avatarImagePath = baseDir + '/cache/avatars/' + actorStr

    imageExtension = getImageExtensions()
    for ext in imageExtension:
        if os.path.isfile(avatarImagePath + '.' + ext):
            return '/avatars/' + actorStr + '.' + ext
        elif os.path.isfile(avatarImagePath.lower() + '.' + ext):
            return '/avatars/' + actorStr.lower() + '.' + ext

    if personJson.get('icon'):
        if personJson['icon'].get('url'):
            return personJson['icon']['url']
    return None


def getIconsDir(baseDir: str) -> str:
    """Returns the directory where icons exist
    """
    iconsDir = 'icons'
    theme = getConfigParam(baseDir, 'theme')
    if theme:
        if os.path.isdir(baseDir + '/img/icons/' + theme):
            iconsDir = 'icons/' + theme
    return iconsDir


def scheduledPostsExist(baseDir: str, nickname: str, domain: str) -> bool:
    """Returns true if there are posts scheduled to be delivered
    """
    scheduleIndexFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/schedule.index'
    if not os.path.isfile(scheduleIndexFilename):
        return False
    if '#users#' in open(scheduleIndexFilename).read():
        return True
    return False


def sharesTimelineJson(actor: str, pageNumber: int, itemsPerPage: int,
                       baseDir: str, maxSharesPerAccount: int) -> ({}, bool):
    """Get a page on the shared items timeline as json
    maxSharesPerAccount helps to avoid one person dominating the timeline
    by sharing a large number of things
    """
    allSharesJson = {}
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if '@' in handle:
                accountDir = baseDir + '/accounts/' + handle
                sharesFilename = accountDir + '/shares.json'
                if os.path.isfile(sharesFilename):
                    sharesJson = loadJson(sharesFilename)
                    if not sharesJson:
                        continue
                    nickname = handle.split('@')[0]
                    # actor who owns this share
                    owner = actor.split('/users/')[0] + '/users/' + nickname
                    ctr = 0
                    for itemID, item in sharesJson.items():
                        # assign owner to the item
                        item['actor'] = owner
                        allSharesJson[str(item['published'])] = item
                        ctr += 1
                        if ctr >= maxSharesPerAccount:
                            break
    # sort the shared items in descending order of publication date
    sharesJson = OrderedDict(sorted(allSharesJson.items(), reverse=True))
    lastPage = False
    startIndex = itemsPerPage * pageNumber
    maxIndex = len(sharesJson.items())
    if maxIndex < itemsPerPage:
        lastPage = True
    if startIndex >= maxIndex - itemsPerPage:
        lastPage = True
        startIndex = maxIndex - itemsPerPage
        if startIndex < 0:
            startIndex = 0
    ctr = 0
    resultJson = {}
    for published, item in sharesJson.items():
        if ctr >= startIndex + itemsPerPage:
            break
        if ctr < startIndex:
            ctr += 1
            continue
        resultJson[published] = item
        ctr += 1
    return resultJson, lastPage


def postContainsPublic(postJsonObject: {}) -> bool:
    """Does the given post contain #Public
    """
    containsPublic = False
    if not postJsonObject['object'].get('to'):
        return containsPublic

    for toAddress in postJsonObject['object']['to']:
        if toAddress.endswith('#Public'):
            containsPublic = True
            break
        if not containsPublic:
            if postJsonObject['object'].get('cc'):
                for toAddress in postJsonObject['object']['cc']:
                    if toAddress.endswith('#Public'):
                        containsPublic = True
                        break
    return containsPublic


def isQuestion(postObjectJson: {}) -> bool:
    """ is the given post a question?
    """
    if postObjectJson['type'] != 'Create' and \
       postObjectJson['type'] != 'Update':
        return False
    if not isinstance(postObjectJson['object'], dict):
        return False
    if not postObjectJson['object'].get('type'):
        return False
    if postObjectJson['object']['type'] != 'Question':
        return False
    if not postObjectJson['object'].get('oneOf'):
        return False
    if not isinstance(postObjectJson['object']['oneOf'], list):
        return False
    return True
