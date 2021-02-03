__filename__ = "webapp_utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from collections import OrderedDict
from session import getJson
from utils import removeHtml
from utils import getImageExtensions
from utils import getProtocolPrefixes
from utils import loadJson
from utils import getCachedPostFilename
from utils import getConfigParam
from cache import getPersonFromCache
from cache import storePersonInCache
from content import addHtmlTags
from content import replaceEmojiFromTags


def getBrokenLinkSubstitute() -> str:
    """Returns html used to show a default image if the link to
    an image is broken
    """
    return " onerror=\"this.onerror=null; this.src='" + \
        "/icons/avatar_default.png'\""


def htmlFollowingList(cssCache: {}, baseDir: str,
                      followingFilename: str) -> str:
    """Returns a list of handles being followed
    """
    with open(followingFilename, 'r') as followingFile:
        msg = followingFile.read()
        followingList = msg.split('\n')
        followingList.sort()
        if followingList:
            cssFilename = baseDir + '/epicyon-profile.css'
            if os.path.isfile(baseDir + '/epicyon.css'):
                cssFilename = baseDir + '/epicyon.css'

            instanceTitle = \
                getConfigParam(baseDir, 'instanceTitle')
            followingListHtml = htmlHeaderWithExternalStyle(cssFilename,
                                                            instanceTitle)
            for followingAddress in followingList:
                if followingAddress:
                    followingListHtml += \
                        '<h3>@' + followingAddress + '</h3>'
            followingListHtml += htmlFooter()
            msg = followingListHtml
        return msg
    return ''


def htmlHashtagBlocked(cssCache: {}, baseDir: str, translate: {}) -> str:
    """Show the screen for a blocked hashtag
    """
    blockedHashtagForm = ''
    cssFilename = baseDir + '/epicyon-suspended.css'
    if os.path.isfile(baseDir + '/suspended.css'):
        cssFilename = baseDir + '/suspended.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    blockedHashtagForm = htmlHeaderWithExternalStyle(cssFilename,
                                                     instanceTitle)
    blockedHashtagForm += '<div><center>\n'
    blockedHashtagForm += \
        '  <p class="screentitle">' + \
        translate['Hashtag Blocked'] + '</p>\n'
    blockedHashtagForm += \
        '  <p>See <a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>\n'
    blockedHashtagForm += '</center></div>\n'
    blockedHashtagForm += htmlFooter()
    return blockedHashtagForm


def headerButtonsFrontScreen(translate: {},
                             nickname: str, boxName: str,
                             authorized: bool,
                             iconsAsButtons: bool) -> str:
    """Returns the header buttons for the front page of a news instance
    """
    headerStr = ''
    if nickname == 'news':
        buttonFeatures = 'buttonMobile'
        buttonNewswire = 'buttonMobile'
        buttonLinks = 'buttonMobile'
        if boxName == 'features':
            buttonFeatures = 'buttonselected'
        elif boxName == 'newswire':
            buttonNewswire = 'buttonselected'
        elif boxName == 'links':
            buttonLinks = 'buttonselected'

        headerStr += \
            '        <a href="/">' + \
            '<button class="' + buttonFeatures + '">' + \
            '<span>' + translate['Features'] + \
            '</span></button></a>'
        if not authorized:
            headerStr += \
                '        <a href="/login">' + \
                '<button class="buttonMobile">' + \
                '<span>' + translate['Login'] + \
                '</span></button></a>'
        if iconsAsButtons:
            headerStr += \
                '        <a href="/users/news/newswiremobile">' + \
                '<button class="' + buttonNewswire + '">' + \
                '<span>' + translate['Newswire'] + \
                '</span></button></a>'
            headerStr += \
                '        <a href="/users/news/linksmobile">' + \
                '<button class="' + buttonLinks + '">' + \
                '<span>' + translate['Links'] + \
                '</span></button></a>'
        else:
            headerStr += \
                '        <a href="' + \
                '/users/news/newswiremobile">' + \
                '<img loading="lazy" src="/icons' + \
                '/newswire.png" title="' + translate['Newswire'] + \
                '" alt="| ' + translate['Newswire'] + '"/></a>\n'
            headerStr += \
                '        <a href="' + \
                '/users/news/linksmobile">' + \
                '<img loading="lazy" src="/icons' + \
                '/links.png" title="' + translate['Links'] + \
                '" alt="| ' + translate['Links'] + '"/></a>\n'
    else:
        if not authorized:
            headerStr += \
                '        <a href="/login">' + \
                '<button class="buttonMobile">' + \
                '<span>' + translate['Login'] + \
                '</span></button></a>'

    if headerStr:
        headerStr = \
            '\n      <div class="frontPageMobileButtons">\n' + \
            headerStr + \
            '      </div>\n'
    return headerStr


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
    return '       <details><summary class="cw">' + \
        translate['SHOW MORE'] + '</summary>' + \
        '<div id="' + postID + '">' + content + \
        '</div></details>\n'


def _getActorPropertyUrl(actorJson: {}, propertyName: str) -> str:
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
    return _getActorPropertyUrl(actorJson, 'Blog')


def _setActorPropertyUrl(actorJson: {}, propertyName: str, url: str) -> None:
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
    _setActorPropertyUrl(actorJson, 'Blog', removeHtml(blogAddress))


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

    # try different image types
    imageFormats = {
        'png': 'png',
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'gif': 'gif',
        'svg': 'svg+xml',
        'webp': 'webp',
        'avif': 'avif'
    }
    avatarImageFilename = None
    for imFormat, mimeType in imageFormats.items():
        if avatarUrl.endswith('.' + imFormat) or \
           '.' + imFormat + '?' in avatarUrl:
            sessionHeaders = {
                'Accept': 'image/' + mimeType
            }
            avatarImageFilename = avatarImagePath + '.' + imFormat

    if not avatarImageFilename:
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
            if '@' not in handle:
                continue
            accountDir = baseDir + '/accounts/' + handle
            sharesFilename = accountDir + '/shares.json'
            if not os.path.isfile(sharesFilename):
                continue
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


def _getImageFile(baseDir: str, name: str, directory: str,
                  nickname: str, domain: str, theme: str) -> (str, str):
    """
    returns the filenames for an image with the given name
    """
    bannerExtensions = getImageExtensions()
    bannerFile = ''
    bannerFilename = ''
    for ext in bannerExtensions:
        bannerFileTest = name + '.' + ext
        bannerFilenameTest = directory + '/' + bannerFileTest
        if os.path.isfile(bannerFilenameTest):
            bannerFile = name + '_' + theme + '.' + ext
            bannerFilename = bannerFilenameTest
            break
    return bannerFile, bannerFilename


def getBannerFile(baseDir: str,
                  nickname: str, domain: str, theme: str) -> (str, str):
    return _getImageFile(baseDir, 'banner',
                         baseDir + '/accounts/' + nickname + '@' + domain,
                         nickname, domain, theme)


def getSearchBannerFile(baseDir: str,
                        nickname: str, domain: str, theme: str) -> (str, str):
    return _getImageFile(baseDir, 'search_banner',
                         baseDir + '/accounts/' + nickname + '@' + domain,
                         nickname, domain, theme)


def getLeftImageFile(baseDir: str,
                     nickname: str, domain: str, theme: str) -> (str, str):
    return _getImageFile(baseDir, 'left_col_image',
                         baseDir + '/accounts/' + nickname + '@' + domain,
                         nickname, domain, theme)


def getRightImageFile(baseDir: str,
                      nickname: str, domain: str, theme: str) -> (str, str):
    return _getImageFile(baseDir, 'right_col_image',
                         baseDir + '/accounts/' + nickname + '@' + domain,
                         nickname, domain, theme)


def htmlHeaderWithExternalStyle(cssFilename: str, instanceTitle: str,
                                lang='en') -> str:
    htmlStr = '<!DOCTYPE html>\n'
    htmlStr += '<html lang="' + lang + '">\n'
    htmlStr += '  <head>\n'
    htmlStr += '    <meta charset="utf-8">\n'
    cssFile = '/' + cssFilename.split('/')[-1]
    htmlStr += '    <link rel="stylesheet" href="' + cssFile + '">\n'
    htmlStr += '    <link rel="manifest" href="/manifest.json">\n'
    htmlStr += '    <meta name="theme-color" content="grey">\n'
    htmlStr += '    <title>' + instanceTitle + '</title>\n'
    htmlStr += '  </head>\n'
    htmlStr += '  <body>\n'
    return htmlStr


def htmlFooter() -> str:
    htmlStr = '  </body>\n'
    htmlStr += '</html>\n'
    return htmlStr


def loadIndividualPostAsHtmlFromCache(baseDir: str,
                                      nickname: str, domain: str,
                                      postJsonObject: {}) -> str:
    """If a cached html version of the given post exists then load it and
    return the html text
    This is much quicker than generating the html from the json object
    """
    cachedPostFilename = \
        getCachedPostFilename(baseDir, nickname, domain, postJsonObject)

    postHtml = ''
    if not cachedPostFilename:
        return postHtml

    if not os.path.isfile(cachedPostFilename):
        return postHtml

    tries = 0
    while tries < 3:
        try:
            with open(cachedPostFilename, 'r') as file:
                postHtml = file.read()
                break
        except Exception as e:
            print(e)
            # no sleep
            tries += 1
    if postHtml:
        return postHtml


def addEmojiToDisplayName(baseDir: str, httpPrefix: str,
                          nickname: str, domain: str,
                          displayName: str, inProfileName: bool) -> str:
    """Adds emoji icons to display names or CW on individual posts
    """
    if ':' not in displayName:
        return displayName

    displayName = displayName.replace('<p>', '').replace('</p>', '')
    emojiTags = {}
#    print('TAG: displayName before tags: ' + displayName)
    displayName = \
        addHtmlTags(baseDir, httpPrefix,
                    nickname, domain, displayName, [], emojiTags)
    displayName = displayName.replace('<p>', '').replace('</p>', '')
#    print('TAG: displayName after tags: ' + displayName)
    # convert the emoji dictionary to a list
    emojiTagsList = []
    for tagName, tag in emojiTags.items():
        emojiTagsList.append(tag)
#    print('TAG: emoji tags list: ' + str(emojiTagsList))
    if not inProfileName:
        displayName = \
            replaceEmojiFromTags(displayName, emojiTagsList, 'post header')
    else:
        displayName = \
            replaceEmojiFromTags(displayName, emojiTagsList, 'profile')
#    print('TAG: displayName after tags 2: ' + displayName)

    # remove any stray emoji
    while ':' in displayName:
        if '://' in displayName:
            break
        emojiStr = displayName.split(':')[1]
        prevDisplayName = displayName
        displayName = displayName.replace(':' + emojiStr + ':', '').strip()
        if prevDisplayName == displayName:
            break
#        print('TAG: displayName after tags 3: ' + displayName)
#    print('TAG: displayName after tag replacements: ' + displayName)

    return displayName


def getPostAttachmentsAsHtml(postJsonObject: {}, boxName: str, translate: {},
                             isMuted: bool, avatarLink: str,
                             replyStr: str, announceStr: str, likeStr: str,
                             bookmarkStr: str, deleteStr: str,
                             muteStr: str) -> (str, str):
    """Returns a string representing any attachments
    """
    attachmentStr = ''
    galleryStr = ''
    if not postJsonObject['object'].get('attachment'):
        return attachmentStr, galleryStr

    if not isinstance(postJsonObject['object']['attachment'], list):
        return attachmentStr, galleryStr

    attachmentCtr = 0
    attachmentStr += '<div class="media">\n'
    for attach in postJsonObject['object']['attachment']:
        if not (attach.get('mediaType') and attach.get('url')):
            continue

        mediaType = attach['mediaType']
        imageDescription = ''
        if attach.get('name'):
            imageDescription = attach['name'].replace('"', "'")
        if mediaType == 'image/png' or \
           mediaType == 'image/jpeg' or \
           mediaType == 'image/webp' or \
           mediaType == 'image/avif' or \
           mediaType == 'image/svg+xml' or \
           mediaType == 'image/gif':
            if attach['url'].endswith('.png') or \
               attach['url'].endswith('.jpg') or \
               attach['url'].endswith('.jpeg') or \
               attach['url'].endswith('.webp') or \
               attach['url'].endswith('.avif') or \
               attach['url'].endswith('.svg') or \
               attach['url'].endswith('.gif'):
                if attachmentCtr > 0:
                    attachmentStr += '<br>'
                if boxName == 'tlmedia':
                    galleryStr += '<div class="gallery">\n'
                    if not isMuted:
                        galleryStr += '  <a href="' + attach['url'] + '">\n'
                        galleryStr += \
                            '    <img loading="lazy" src="' + \
                            attach['url'] + '" alt="" title="">\n'
                        galleryStr += '  </a>\n'
                    if postJsonObject['object'].get('url'):
                        imagePostUrl = postJsonObject['object']['url']
                    else:
                        imagePostUrl = postJsonObject['object']['id']
                    if imageDescription and not isMuted:
                        galleryStr += \
                            '  <a href="' + imagePostUrl + \
                            '" class="gallerytext"><div ' + \
                            'class="gallerytext">' + \
                            imageDescription + '</div></a>\n'
                    else:
                        galleryStr += \
                            '<label class="transparent">---</label><br>'
                    galleryStr += '  <div class="mediaicons">\n'
                    galleryStr += \
                        '    ' + replyStr+announceStr + likeStr + \
                        bookmarkStr + deleteStr + muteStr + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '  <div class="mediaavatar">\n'
                    galleryStr += '    ' + avatarLink + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '</div>\n'

                attachmentStr += '<a href="' + attach['url'] + '">'
                attachmentStr += \
                    '<img loading="lazy" src="' + attach['url'] + \
                    '" alt="' + imageDescription + '" title="' + \
                    imageDescription + '" class="attachment"></a>\n'
                attachmentCtr += 1
        elif (mediaType == 'video/mp4' or
              mediaType == 'video/webm' or
              mediaType == 'video/ogv'):
            extension = '.mp4'
            if attach['url'].endswith('.webm'):
                extension = '.webm'
            elif attach['url'].endswith('.ogv'):
                extension = '.ogv'
            if attach['url'].endswith(extension):
                if attachmentCtr > 0:
                    attachmentStr += '<br>'
                if boxName == 'tlmedia':
                    galleryStr += '<div class="gallery">\n'
                    if not isMuted:
                        galleryStr += '  <a href="' + attach['url'] + '">\n'
                        galleryStr += \
                            '    <video width="600" height="400" controls>\n'
                        galleryStr += \
                            '      <source src="' + attach['url'] + \
                            '" alt="' + imageDescription + \
                            '" title="' + imageDescription + \
                            '" class="attachment" type="video/' + \
                            extension.replace('.', '') + '">'
                        idx = 'Your browser does not support the video tag.'
                        galleryStr += translate[idx]
                        galleryStr += '    </video>\n'
                        galleryStr += '  </a>\n'
                    if postJsonObject['object'].get('url'):
                        videoPostUrl = postJsonObject['object']['url']
                    else:
                        videoPostUrl = postJsonObject['object']['id']
                    if imageDescription and not isMuted:
                        galleryStr += \
                            '  <a href="' + videoPostUrl + \
                            '" class="gallerytext"><div ' + \
                            'class="gallerytext">' + \
                            imageDescription + '</div></a>\n'
                    else:
                        galleryStr += \
                            '<label class="transparent">---</label><br>'
                    galleryStr += '  <div class="mediaicons">\n'
                    galleryStr += \
                        '    ' + replyStr + announceStr + likeStr + \
                        bookmarkStr + deleteStr + muteStr + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '  <div class="mediaavatar">\n'
                    galleryStr += '    ' + avatarLink + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '</div>\n'

                attachmentStr += \
                    '<center><video width="400" height="300" controls>'
                attachmentStr += \
                    '<source src="' + attach['url'] + '" alt="' + \
                    imageDescription + '" title="' + imageDescription + \
                    '" class="attachment" type="video/' + \
                    extension.replace('.', '') + '">'
                attachmentStr += \
                    translate['Your browser does not support the video tag.']
                attachmentStr += '</video></center>'
                attachmentCtr += 1
        elif (mediaType == 'audio/mpeg' or
              mediaType == 'audio/ogg'):
            extension = '.mp3'
            if attach['url'].endswith('.ogg'):
                extension = '.ogg'
            if attach['url'].endswith(extension):
                if attachmentCtr > 0:
                    attachmentStr += '<br>'
                if boxName == 'tlmedia':
                    galleryStr += '<div class="gallery">\n'
                    if not isMuted:
                        galleryStr += '  <a href="' + attach['url'] + '">\n'
                        galleryStr += '    <audio controls>\n'
                        galleryStr += \
                            '      <source src="' + attach['url'] + \
                            '" alt="' + imageDescription + \
                            '" title="' + imageDescription + \
                            '" class="attachment" type="audio/' + \
                            extension.replace('.', '') + '">'
                        idx = 'Your browser does not support the audio tag.'
                        galleryStr += translate[idx]
                        galleryStr += '    </audio>\n'
                        galleryStr += '  </a>\n'
                    if postJsonObject['object'].get('url'):
                        audioPostUrl = postJsonObject['object']['url']
                    else:
                        audioPostUrl = postJsonObject['object']['id']
                    if imageDescription and not isMuted:
                        galleryStr += \
                            '  <a href="' + audioPostUrl + \
                            '" class="gallerytext"><div ' + \
                            'class="gallerytext">' + \
                            imageDescription + '</div></a>\n'
                    else:
                        galleryStr += \
                            '<label class="transparent">---</label><br>'
                    galleryStr += '  <div class="mediaicons">\n'
                    galleryStr += \
                        '    ' + replyStr + announceStr + \
                        likeStr + bookmarkStr + \
                        deleteStr + muteStr+'\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '  <div class="mediaavatar">\n'
                    galleryStr += '    ' + avatarLink + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '</div>\n'

                attachmentStr += '<center>\n<audio controls>\n'
                attachmentStr += \
                    '<source src="' + attach['url'] + '" alt="' + \
                    imageDescription + '" title="' + imageDescription + \
                    '" class="attachment" type="audio/' + \
                    extension.replace('.', '') + '">'
                attachmentStr += \
                    translate['Your browser does not support the audio tag.']
                attachmentStr += '</audio>\n</center>\n'
                attachmentCtr += 1
    attachmentStr += '</div>'
    return attachmentStr, galleryStr


def htmlPostSeparator(baseDir: str, column: str) -> str:
    """Returns the html for a timeline post separator image
    """
    theme = getConfigParam(baseDir, 'theme')
    filename = 'separator.png'
    separatorClass = "postSeparatorImage"
    if column:
        separatorClass = "postSeparatorImage" + column.title()
        filename = 'separator_' + column + '.png'
    separatorImageFilename = baseDir + '/theme/' + theme + '/icons/' + filename
    separatorStr = ''
    if os.path.isfile(separatorImageFilename):
        separatorStr = \
            '<div class="' + separatorClass + '"><center>' + \
            '<img src="/icons/' + filename + '" ' + \
            'alt="" /></center></div>\n'
    return separatorStr


def htmlHighlightLabel(label: str, highlight: bool) -> str:
    """If the given text should be highlighted then return
    the appropriate markup.
    This is so that in shell browsers, like lynx, it's possible
    to see if the replies or DM button are highlighted.
    """
    if not highlight:
        return label
    return '*' + str(label) + '*'


def getAvatarImageUrl(session,
                      baseDir: str, httpPrefix: str,
                      postActor: str, personCache: {},
                      avatarUrl: str, allowDownloads: bool) -> str:
    """Returns the avatar image url
    """
    # get the avatar image url for the post actor
    if not avatarUrl:
        avatarUrl = \
            getPersonAvatarUrl(baseDir, postActor, personCache,
                               allowDownloads)
        avatarUrl = \
            updateAvatarImageCache(session, baseDir, httpPrefix,
                                   postActor, avatarUrl, personCache,
                                   allowDownloads)
    else:
        updateAvatarImageCache(session, baseDir, httpPrefix,
                               postActor, avatarUrl, personCache,
                               allowDownloads)

    if not avatarUrl:
        avatarUrl = postActor + '/avatar.png'

    return avatarUrl
