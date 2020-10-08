__filename__ = "webinterface.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import time
import os
import urllib.parse
from collections import OrderedDict
from datetime import datetime
from datetime import date
from dateutil.parser import parse
from shutil import copyfile
from pprint import pprint
from person import personBoxJson
from person import isPersonSnoozed
from pgp import getEmailAddress
from pgp import getPGPpubKey
from pgp import getPGPfingerprint
from xmpp import getXmppAddress
from ssb import getSSBAddress
from tox import getToxAddress
from matrix import getMatrixAddress
from donate import getDonationUrl
from utils import removeIdEnding
from utils import getProtocolPrefixes
from utils import searchBoxPosts
from utils import isEventPost
from utils import isBlogPost
from utils import isNewsPost
from utils import updateRecentPostsCache
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import noOfAccounts
from utils import isPublicPost
from utils import isPublicPostFromUrl
from utils import getDisplayName
from utils import getCachedPostDirectory
from utils import getCachedPostFilename
from utils import loadJson
from utils import getConfigParam
from follow import isFollowingActor
from webfinger import webfingerHandle
from posts import isDM
from posts import getPersonBox
from posts import getUserUrl
from posts import parseUserFeed
from posts import populateRepliesJson
from posts import isModerator
from posts import downloadAnnounce
from session import getJson
from auth import createPassword
from like import likedByPerson
from like import noOfLikes
from bookmarks import bookmarkedByPerson
from announce import announcedByPerson
from blocking import isBlocked
from blocking import isBlockedHashtag
from content import htmlReplaceEmailQuote
from content import htmlReplaceQuoteMarks
from content import removeTextFormatting
from content import switchWords
from content import getMentionsFromHtml
from content import addHtmlTags
from content import replaceEmojiFromTags
from content import removeLongWords
from content import removeHtml
from skills import getSkills
from cache import getPersonFromCache
from cache import storePersonInCache
from shares import getValidSharedItemID
from happening import todaysEventsCheck
from happening import thisWeeksEventsCheck
from happening import getCalendarEvents
from happening import getTodaysEvents
from git import isGitPatch
from theme import getThemesList
from petnames import getPetName
from followingCalendar import receivingCalendarEvents
from devices import E2EEdecryptMessageFromDevice


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


def getBlogAddress(actorJson: {}) -> str:
    """Returns blog address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('blog'):
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


def setBlogAddress(actorJson: {}, blogAddress: str) -> None:
    """Sets an blog address for the given actor
    """
    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('blog'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)

    prefixes = getProtocolPrefixes()
    prefixFound = False
    for prefix in prefixes:
        if blogAddress.startswith(prefix):
            prefixFound = True
            break
    if not prefixFound:
        return
    if '.' not in blogAddress:
        return
    if ' ' in blogAddress:
        return
    if ',' in blogAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('blog'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = blogAddress
        return

    newBlogAddress = {
        "name": "Blog",
        "type": "PropertyValue",
        "value": blogAddress
    }
    actorJson['attachment'].append(newBlogAddress)


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

    imageExtension = ('png', 'jpg', 'jpeg', 'gif', 'webp', 'avif')
    for ext in imageExtension:
        if os.path.isfile(avatarImagePath + '.' + ext):
            return '/avatars/' + actorStr + '.' + ext
        elif os.path.isfile(avatarImagePath.lower() + '.' + ext):
            return '/avatars/' + actorStr.lower() + '.' + ext

    if personJson.get('icon'):
        if personJson['icon'].get('url'):
            return personJson['icon']['url']
    return None


def htmlFollowingList(baseDir: str, followingFilename: str) -> str:
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
            with open(cssFilename, 'r') as cssFile:
                profileCSS = cssFile.read()
                followingListHtml = htmlHeader(cssFilename, profileCSS)
                for followingAddress in followingList:
                    if followingAddress:
                        followingListHtml += \
                            '<h3>@' + followingAddress + '</h3>'
                followingListHtml += htmlFooter()
                msg = followingListHtml
        return msg
    return ''


def htmlFollowingDataList(baseDir: str, nickname: str,
                          domain: str, domainFull: str) -> str:
    """Returns a datalist of handles being followed
    """
    listStr = '<datalist id="followingHandles">\n'
    followingFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/following.txt'
    if os.path.isfile(followingFilename):
        with open(followingFilename, 'r') as followingFile:
            msg = followingFile.read()
            # add your own handle, so that you can send DMs
            # to yourself as reminders
            msg += nickname + '@' + domainFull + '\n'
            # include petnames
            petnamesFilename = \
                baseDir + '/accounts/' + \
                nickname + '@' + domain + '/petnames.txt'
            if os.path.isfile(petnamesFilename):
                followingList = []
                with open(petnamesFilename, 'r') as petnamesFile:
                    petStr = petnamesFile.read()
                    # extract each petname and append it
                    petnamesList = petStr.split('\n')
                    for pet in petnamesList:
                        followingList.append(pet.split(' ')[0])
                # add the following.txt entries
                followingList += msg.split('\n')
            else:
                # no petnames list exists - just use following.txt
                followingList = msg.split('\n')
            followingList.sort()
            if followingList:
                for followingAddress in followingList:
                    if followingAddress:
                        listStr += \
                            '<option>@' + followingAddress + '</option>\n'
    listStr += '</datalist>\n'
    return listStr


def htmlSearchEmoji(translate: {}, baseDir: str, httpPrefix: str,
                    searchStr: str) -> str:
    """Search results for emoji
    """
    # emoji.json is generated so that it can be customized and the changes
    # will be retained even if default_emoji.json is subsequently updated
    if not os.path.isfile(baseDir + '/emoji/emoji.json'):
        copyfile(baseDir + '/emoji/default_emoji.json',
                 baseDir + '/emoji/emoji.json')

    searchStr = searchStr.lower().replace(':', '').strip('\n').strip('\r')
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        emojiCSS = cssFile.read()
        if httpPrefix != 'https':
            emojiCSS = emojiCSS.replace('https://',
                                        httpPrefix + '://')
        emojiLookupFilename = baseDir + '/emoji/emoji.json'

        # create header
        emojiForm = htmlHeader(cssFilename, emojiCSS)
        emojiForm += '<center><h1>' + \
            translate['Emoji Search'] + \
            '</h1></center>'

        # does the lookup file exist?
        if not os.path.isfile(emojiLookupFilename):
            emojiForm += '<center><h5>' + \
                translate['No results'] + '</h5></center>'
            emojiForm += htmlFooter()
            return emojiForm

        emojiJson = loadJson(emojiLookupFilename)
        if emojiJson:
            results = {}
            for emojiName, filename in emojiJson.items():
                if searchStr in emojiName:
                    results[emojiName] = filename + '.png'
            for emojiName, filename in emojiJson.items():
                if emojiName in searchStr:
                    results[emojiName] = filename + '.png'
            headingShown = False
            emojiForm += '<center>'
            msgStr1 = translate['Copy the text then paste it into your post']
            msgStr2 = ':<img loading="lazy" class="searchEmoji" src="/emoji/'
            for emojiName, filename in results.items():
                if os.path.isfile(baseDir + '/emoji/' + filename):
                    if not headingShown:
                        emojiForm += \
                            '<center><h5>' + msgStr1 + \
                            '</h5></center>'
                        headingShown = True
                    emojiForm += \
                        '<h3>:' + emojiName + msgStr2 + \
                        filename + '"/></h3>'
            emojiForm += '</center>'

        emojiForm += htmlFooter()
    return emojiForm


def getIconsDir(baseDir: str) -> str:
    """Returns the directory where icons exist
    """
    iconsDir = 'icons'
    theme = getConfigParam(baseDir, 'theme')
    if theme:
        if os.path.isdir(baseDir + '/img/icons/' + theme):
            iconsDir = 'icons/' + theme
    return iconsDir


def htmlSearchSharedItems(translate: {},
                          baseDir: str, searchStr: str,
                          pageNumber: int,
                          resultsPerPage: int,
                          httpPrefix: str,
                          domainFull: str, actor: str,
                          callingDomain: str) -> str:
    """Search results for shared items
    """
    iconsDir = getIconsDir(baseDir)
    currPage = 1
    ctr = 0
    sharedItemsForm = ''
    searchStrLower = urllib.parse.unquote(searchStr)
    searchStrLower = searchStrLower.lower().strip('\n').strip('\r')
    searchStrLowerList = searchStrLower.split('+')
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    with open(cssFilename, 'r') as cssFile:
        sharedItemsCSS = cssFile.read()
        if httpPrefix != 'https':
            sharedItemsCSS = \
                sharedItemsCSS.replace('https://',
                                       httpPrefix + '://')
        sharedItemsForm = htmlHeader(cssFilename, sharedItemsCSS)
        sharedItemsForm += \
            '<center><h1>' + translate['Shared Items Search'] + \
            '</h1></center>'
        resultsExist = False
        for subdir, dirs, files in os.walk(baseDir + '/accounts'):
            for handle in dirs:
                if '@' not in handle:
                    continue
                contactNickname = handle.split('@')[0]
                sharesFilename = baseDir + '/accounts/' + handle + \
                    '/shares.json'
                if not os.path.isfile(sharesFilename):
                    continue

                sharesJson = loadJson(sharesFilename)
                if not sharesJson:
                    continue

                for name, sharedItem in sharesJson.items():
                    matched = True
                    for searchSubstr in searchStrLowerList:
                        subStrMatched = False
                        searchSubstr = searchSubstr.strip()
                        if searchSubstr in sharedItem['location'].lower():
                            subStrMatched = True
                        elif searchSubstr in sharedItem['summary'].lower():
                            subStrMatched = True
                        elif searchSubstr in sharedItem['displayName'].lower():
                            subStrMatched = True
                        elif searchSubstr in sharedItem['category'].lower():
                            subStrMatched = True
                        if not subStrMatched:
                            matched = False
                            break
                    if matched:
                        if currPage == pageNumber:
                            sharedItemsForm += '<div class="container">\n'
                            sharedItemsForm += \
                                '<p class="share-title">' + \
                                sharedItem['displayName'] + '</p>\n'
                            if sharedItem.get('imageUrl'):
                                sharedItemsForm += \
                                    '<a href="' + \
                                    sharedItem['imageUrl'] + '">\n'
                                sharedItemsForm += \
                                    '<img loading="lazy" src="' + \
                                    sharedItem['imageUrl'] + \
                                    '" alt="Item image"></a>\n'
                            sharedItemsForm += \
                                '<p>' + sharedItem['summary'] + '</p>\n'
                            sharedItemsForm += \
                                '<p><b>' + translate['Type'] + \
                                ':</b> ' + sharedItem['itemType'] + ' '
                            sharedItemsForm += \
                                '<b>' + translate['Category'] + \
                                ':</b> ' + sharedItem['category'] + ' '
                            sharedItemsForm += \
                                '<b>' + translate['Location'] + \
                                ':</b> ' + sharedItem['location'] + '</p>\n'
                            contactActor = \
                                httpPrefix + '://' + domainFull + \
                                '/users/' + contactNickname
                            sharedItemsForm += \
                                '<p><a href="' + actor + \
                                '?replydm=sharedesc:' + \
                                sharedItem['displayName'] + \
                                '?mention=' + contactActor + \
                                '"><button class="button">' + \
                                translate['Contact'] + '</button></a>\n'
                            if actor.endswith('/users/' + contactNickname):
                                sharedItemsForm += \
                                    ' <a href="' + actor + '?rmshare=' + \
                                    name + '"><button class="button">' + \
                                    translate['Remove'] + '</button></a>\n'
                            sharedItemsForm += '</p></div>\n'
                            if not resultsExist and currPage > 1:
                                postActor = \
                                    getAltPath(actor, domainFull,
                                               callingDomain)
                                # previous page link, needs to be a POST
                                sharedItemsForm += \
                                    '<form method="POST" action="' + \
                                    postActor + \
                                    '/searchhandle?page=' + \
                                    str(pageNumber - 1) + '">\n'
                                sharedItemsForm += \
                                    '  <input type="hidden" ' + \
                                    'name="actor" value="' + actor + '">\n'
                                sharedItemsForm += \
                                    '  <input type="hidden" ' + \
                                    'name="searchtext" value="' + \
                                    searchStrLower + '"><br>\n'
                                sharedItemsForm += \
                                    '  <center>\n' + \
                                    '    <a href="' + actor + \
                                    '" type="submit" name="submitSearch">\n'
                                sharedItemsForm += \
                                    '    <img loading="lazy" ' + \
                                    'class="pageicon" src="/' + iconsDir + \
                                    '/pageup.png" title="' + \
                                    translate['Page up'] + \
                                    '" alt="' + translate['Page up'] + \
                                    '"/></a>\n'
                                sharedItemsForm += '  </center>\n'
                                sharedItemsForm += '</form>\n'
                                resultsExist = True
                        ctr += 1
                        if ctr >= resultsPerPage:
                            currPage += 1
                            if currPage > pageNumber:
                                postActor = \
                                    getAltPath(actor, domainFull,
                                               callingDomain)
                                # next page link, needs to be a POST
                                sharedItemsForm += \
                                    '<form method="POST" action="' + \
                                    postActor + \
                                    '/searchhandle?page=' + \
                                    str(pageNumber + 1) + '">\n'
                                sharedItemsForm += \
                                    '  <input type="hidden" ' + \
                                    'name="actor" value="' + actor + '">\n'
                                sharedItemsForm += \
                                    '  <input type="hidden" ' + \
                                    'name="searchtext" value="' + \
                                    searchStrLower + '"><br>\n'
                                sharedItemsForm += \
                                    '  <center>\n' + \
                                    '    <a href="' + actor + \
                                    '" type="submit" name="submitSearch">\n'
                                sharedItemsForm += \
                                    '    <img loading="lazy" ' + \
                                    'class="pageicon" src="/' + iconsDir + \
                                    '/pagedown.png" title="' + \
                                    translate['Page down'] + \
                                    '" alt="' + translate['Page down'] + \
                                    '"/></a>\n'
                                sharedItemsForm += '  </center>\n'
                                sharedItemsForm += '</form>\n'
                                break
                            ctr = 0
        if not resultsExist:
            sharedItemsForm += \
                '<center><h5>' + translate['No results'] + '</h5></center>\n'
        sharedItemsForm += htmlFooter()
    return sharedItemsForm


def htmlModerationInfo(translate: {}, baseDir: str, httpPrefix: str) -> str:
    msgStr1 = \
        'These are globally blocked for all accounts on this instance'
    msgStr2 = \
        'Any blocks or suspensions made by moderators will be shown here.'
    infoForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        infoCSS = cssFile.read()
        if httpPrefix != 'https':
            infoCSS = infoCSS.replace('https://',
                                      httpPrefix + '://')
        infoForm = htmlHeader(cssFilename, infoCSS)

        infoForm += \
            '<center><h1>' + \
            translate['Moderation Information'] + \
            '</h1></center>'

        infoShown = False
        suspendedFilename = baseDir + '/accounts/suspended.txt'
        if os.path.isfile(suspendedFilename):
            with open(suspendedFilename, "r") as f:
                suspendedStr = f.read()
                infoForm += '<div class="container">'
                infoForm += '  <br><b>' + \
                    translate['Suspended accounts'] + '</b>'
                infoForm += '  <br>' + \
                    translate['These are currently suspended']
                infoForm += \
                    '  <textarea id="message" ' + \
                    'name="suspended" style="height:200px">' + \
                    suspendedStr + '</textarea>'
                infoForm += '</div>'
                infoShown = True

        blockingFilename = baseDir + '/accounts/blocking.txt'
        if os.path.isfile(blockingFilename):
            with open(blockingFilename, "r") as f:
                blockedStr = f.read()
                infoForm += '<div class="container">'
                infoForm += \
                    '  <br><b>' + \
                    translate['Blocked accounts and hashtags'] + '</b>'
                infoForm += \
                    '  <br>' + \
                    translate[msgStr1]
                infoForm += \
                    '  <textarea id="message" ' + \
                    'name="blocked" style="height:700px">' + \
                    blockedStr + '</textarea>'
                infoForm += '</div>'
                infoShown = True
        if not infoShown:
            infoForm += \
                '<center><p>' + \
                translate[msgStr2] + \
                '</p></center>'
        infoForm += htmlFooter()
    return infoForm


def htmlHashtagSearch(nickname: str, domain: str, port: int,
                      recentPostsCache: {}, maxRecentPosts: int,
                      translate: {},
                      baseDir: str, hashtag: str, pageNumber: int,
                      postsPerPage: int,
                      session, wfRequest: {}, personCache: {},
                      httpPrefix: str, projectVersion: str,
                      YTReplacementDomain: str) -> str:
    """Show a page containing search results for a hashtag
    """
    if hashtag.startswith('#'):
        hashtag = hashtag[1:]
    hashtag = urllib.parse.unquote(hashtag)
    hashtagIndexFile = baseDir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtagIndexFile):
        if hashtag != hashtag.lower():
            hashtag = hashtag.lower()
            hashtagIndexFile = baseDir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtagIndexFile):
        print('WARN: hashtag file not found ' + hashtagIndexFile)
        return None

    iconsDir = getIconsDir(baseDir)

    # check that the directory for the nickname exists
    if nickname:
        if not os.path.isdir(baseDir + '/accounts/' +
                             nickname + '@' + domain):
            nickname = None

    # read the index
    with open(hashtagIndexFile, "r") as f:
        lines = f.readlines()

    # read the css
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        hashtagSearchCSS = cssFile.read()
        if httpPrefix != 'https':
            hashtagSearchCSS = \
                hashtagSearchCSS.replace('https://',
                                         httpPrefix + '://')

    # ensure that the page number is in bounds
    if not pageNumber:
        pageNumber = 1
    elif pageNumber < 1:
        pageNumber = 1

    # get the start end end within the index file
    startIndex = int((pageNumber - 1) * postsPerPage)
    endIndex = startIndex + postsPerPage
    noOfLines = len(lines)
    if endIndex >= noOfLines and noOfLines > 0:
        endIndex = noOfLines - 1

    # add the page title
    hashtagSearchForm = htmlHeader(cssFilename, hashtagSearchCSS)
    if nickname:
        hashtagSearchForm += '<center>\n' + \
            '<h1><a href="/users/' + nickname + '/search">#' + \
            hashtag + '</a></h1>\n' + '</center>\n'
    else:
        hashtagSearchForm += '<center>\n' + \
            '<h1>#' + hashtag + '</h1>\n' + '</center>\n'

    # RSS link for hashtag feed
    hashtagSearchForm += '<center><a href="/tags/rss2/' + hashtag + '">'
    hashtagSearchForm += \
        '<img style="width:3%;min-width:50px" ' + \
        'loading="lazy" alt="RSS 2.0" ' + \
        'title="RSS 2.0" src="/' + \
        iconsDir + '/rss.png" /></a></center>'

    if startIndex > 0:
        # previous page link
        hashtagSearchForm += \
            '  <center>\n' + \
            '    <a href="/tags/' + hashtag + '?page=' + \
            str(pageNumber - 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pageup.png" title="' + \
            translate['Page up'] + \
            '" alt="' + translate['Page up'] + \
            '"></a>\n  </center>\n'
    index = startIndex
    while index <= endIndex:
        postId = lines[index].strip('\n').strip('\r')
        if '  ' not in postId:
            nickname = getNicknameFromActor(postId)
            if not nickname:
                index += 1
                continue
        else:
            postFields = postId.split('  ')
            if len(postFields) != 3:
                index += 1
                continue
            nickname = postFields[1]
            postId = postFields[2]
        postFilename = locatePost(baseDir, nickname, domain, postId)
        if not postFilename:
            index += 1
            continue
        postJsonObject = loadJson(postFilename)
        if postJsonObject:
            if not isPublicPost(postJsonObject):
                index += 1
                continue
            showIndividualPostIcons = False
            if nickname:
                showIndividualPostIcons = True
            allowDeletion = False
            hashtagSearchForm += \
                individualPostAsHtml(True, recentPostsCache,
                                     maxRecentPosts,
                                     iconsDir, translate, None,
                                     baseDir, session, wfRequest,
                                     personCache,
                                     nickname, domain, port,
                                     postJsonObject,
                                     None, True, allowDeletion,
                                     httpPrefix, projectVersion,
                                     'search',
                                     YTReplacementDomain,
                                     showIndividualPostIcons,
                                     showIndividualPostIcons,
                                     False, False, False)
        index += 1

    if endIndex < noOfLines - 1:
        # next page link
        hashtagSearchForm += \
            '  <center>\n' + \
            '    <a href="/tags/' + hashtag + \
            '?page=' + str(pageNumber + 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + iconsDir + \
            '/pagedown.png" title="' + translate['Page down'] + \
            '" alt="' + translate['Page down'] + '"></a>' + \
            '  </center>'
    hashtagSearchForm += htmlFooter()
    return hashtagSearchForm


def rss2TagHeader(hashtag: str, httpPrefix: str, domainFull: str) -> str:
    rssStr = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
    rssStr += "<rss version=\"2.0\">"
    rssStr += '<channel>'
    rssStr += '    <title>#' + hashtag + '</title>'
    rssStr += '    <link>' + httpPrefix + '://' + domainFull + \
        '/tags/rss2/' + hashtag + '</link>'
    return rssStr


def rss2TagFooter() -> str:
    rssStr = '</channel>'
    rssStr += '</rss>'
    return rssStr


def rssHashtagSearch(nickname: str, domain: str, port: int,
                     recentPostsCache: {}, maxRecentPosts: int,
                     translate: {},
                     baseDir: str, hashtag: str,
                     postsPerPage: int,
                     session, wfRequest: {}, personCache: {},
                     httpPrefix: str, projectVersion: str,
                     YTReplacementDomain: str) -> str:
    """Show an rss feed for a hashtag
    """
    if hashtag.startswith('#'):
        hashtag = hashtag[1:]
    hashtag = urllib.parse.unquote(hashtag)
    hashtagIndexFile = baseDir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtagIndexFile):
        if hashtag != hashtag.lower():
            hashtag = hashtag.lower()
            hashtagIndexFile = baseDir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtagIndexFile):
        print('WARN: hashtag file not found ' + hashtagIndexFile)
        return None

    # check that the directory for the nickname exists
    if nickname:
        if not os.path.isdir(baseDir + '/accounts/' +
                             nickname + '@' + domain):
            nickname = None

    # read the index
    lines = []
    with open(hashtagIndexFile, "r") as f:
        lines = f.readlines()
    if not lines:
        return None

    domainFull = domain
    if port:
        if port != 80 and port != 443:
            domainFull = domain + ':' + str(port)

    maxFeedLength = 10
    hashtagFeed = \
        rss2TagHeader(hashtag, httpPrefix, domainFull)
    for index in range(len(lines)):
        postId = lines[index].strip('\n').strip('\r')
        if '  ' not in postId:
            nickname = getNicknameFromActor(postId)
            if not nickname:
                index += 1
                if index >= maxFeedLength:
                    break
                continue
        else:
            postFields = postId.split('  ')
            if len(postFields) != 3:
                index += 1
                if index >= maxFeedLength:
                    break
                continue
            nickname = postFields[1]
            postId = postFields[2]
        postFilename = locatePost(baseDir, nickname, domain, postId)
        if not postFilename:
            index += 1
            if index >= maxFeedLength:
                break
            continue
        postJsonObject = loadJson(postFilename)
        if postJsonObject:
            if not isPublicPost(postJsonObject):
                index += 1
                if index >= maxFeedLength:
                    break
                continue
            # add to feed
            if postJsonObject['object'].get('content') and \
               postJsonObject['object'].get('attributedTo') and \
               postJsonObject['object'].get('published'):
                published = postJsonObject['object']['published']
                pubDate = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                rssDateStr = pubDate.strftime("%a, %d %b %Y %H:%M:%S UT")
                hashtagFeed += '     <item>'
                hashtagFeed += \
                    '         <author>' + \
                    postJsonObject['object']['attributedTo'] + \
                    '</author>'
                if postJsonObject['object'].get('summary'):
                    hashtagFeed += \
                        '         <title>' + \
                        postJsonObject['object']['summary'] + \
                        '</title>'
                hashtagFeed += \
                    '         <description><![CDATA[' + \
                    postJsonObject['object']['content'] + \
                    ']]></description>'
                hashtagFeed += \
                    '         <pubDate>' + rssDateStr + '</pubDate>'
                if postJsonObject['object'].get('attachment'):
                    for attach in postJsonObject['object']['attachment']:
                        if not attach.get('url'):
                            continue
                        hashtagFeed += \
                            '         <link>' + attach['url'] + '</link>'
                hashtagFeed += '     </item>'
        index += 1
        if index >= maxFeedLength:
            break

    return hashtagFeed + rss2TagFooter()


def htmlSkillsSearch(translate: {}, baseDir: str,
                     httpPrefix: str,
                     skillsearch: str, instanceOnly: bool,
                     postsPerPage: int) -> str:
    """Show a page containing search results for a skill
    """
    if skillsearch.startswith('*'):
        skillsearch = skillsearch[1:].strip()

    skillsearch = skillsearch.lower().strip('\n').strip('\r')

    results = []
    # search instance accounts
    for subdir, dirs, files in os.walk(baseDir + '/accounts/'):
        for f in files:
            if not f.endswith('.json'):
                continue
            if '@' not in f:
                continue
            if f.startswith('inbox@'):
                continue
            actorFilename = os.path.join(subdir, f)
            actorJson = loadJson(actorFilename)
            if actorJson:
                if actorJson.get('id') and \
                   actorJson.get('skills') and \
                   actorJson.get('name') and \
                   actorJson.get('icon'):
                    actor = actorJson['id']
                    for skillName, skillLevel in actorJson['skills'].items():
                        skillName = skillName.lower()
                        if not (skillName in skillsearch or
                                skillsearch in skillName):
                            continue
                        skillLevelStr = str(skillLevel)
                        if skillLevel < 100:
                            skillLevelStr = '0' + skillLevelStr
                        if skillLevel < 10:
                            skillLevelStr = '0' + skillLevelStr
                        indexStr = \
                            skillLevelStr + ';' + actor + ';' + \
                            actorJson['name'] + \
                            ';' + actorJson['icon']['url']
                        if indexStr not in results:
                            results.append(indexStr)
    if not instanceOnly:
        # search actor cache
        for subdir, dirs, files in os.walk(baseDir + '/cache/actors/'):
            for f in files:
                if not f.endswith('.json'):
                    continue
                if '@' not in f:
                    continue
                if f.startswith('inbox@'):
                    continue
                actorFilename = os.path.join(subdir, f)
                cachedActorJson = loadJson(actorFilename)
                if cachedActorJson:
                    if cachedActorJson.get('actor'):
                        actorJson = cachedActorJson['actor']
                        if actorJson.get('id') and \
                           actorJson.get('skills') and \
                           actorJson.get('name') and \
                           actorJson.get('icon'):
                            actor = actorJson['id']
                            for skillName, skillLevel in \
                                    actorJson['skills'].items():
                                skillName = skillName.lower()
                                if not (skillName in skillsearch or
                                        skillsearch in skillName):
                                    continue
                                skillLevelStr = str(skillLevel)
                                if skillLevel < 100:
                                    skillLevelStr = '0' + skillLevelStr
                                if skillLevel < 10:
                                    skillLevelStr = '0' + skillLevelStr
                                indexStr = \
                                    skillLevelStr + ';' + actor + ';' + \
                                    actorJson['name'] + \
                                    ';' + actorJson['icon']['url']
                                if indexStr not in results:
                                    results.append(indexStr)

    results.sort(reverse=True)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        skillSearchCSS = cssFile.read()
        if httpPrefix != 'https':
            skillSearchCSS = \
                skillSearchCSS.replace('https://',
                                       httpPrefix + '://')
    skillSearchForm = htmlHeader(cssFilename, skillSearchCSS)
    skillSearchForm += \
        '<center><h1>' + translate['Skills search'] + ': ' + \
        skillsearch + '</h1></center>'

    if len(results) == 0:
        skillSearchForm += \
            '<center><h5>' + translate['No results'] + \
            '</h5></center>'
    else:
        skillSearchForm += '<center>'
        ctr = 0
        for skillMatch in results:
            skillMatchFields = skillMatch.split(';')
            if len(skillMatchFields) != 4:
                continue
            actor = skillMatchFields[1]
            actorName = skillMatchFields[2]
            avatarUrl = skillMatchFields[3]
            skillSearchForm += \
                '<div class="search-result""><a href="' + \
                actor + '/skills">'
            skillSearchForm += \
                '<img loading="lazy" src="' + avatarUrl + \
                '"/><span class="search-result-text">' + actorName + \
                '</span></a></div>'
            ctr += 1
            if ctr >= postsPerPage:
                break
        skillSearchForm += '</center>'
    skillSearchForm += htmlFooter()
    return skillSearchForm


def htmlHistorySearch(translate: {}, baseDir: str,
                      httpPrefix: str,
                      nickname: str, domain: str,
                      historysearch: str,
                      postsPerPage: int, pageNumber: int,
                      projectVersion: str,
                      recentPostsCache: {},
                      maxRecentPosts: int,
                      session,
                      wfRequest,
                      personCache: {},
                      port: int,
                      YTReplacementDomain: str) -> str:
    """Show a page containing search results for your post history
    """
    if historysearch.startswith('!'):
        historysearch = historysearch[1:].strip()

    historysearch = historysearch.lower().strip('\n').strip('\r')

    boxFilenames = \
        searchBoxPosts(baseDir, nickname, domain,
                       historysearch, postsPerPage)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        historySearchCSS = cssFile.read()
        if httpPrefix != 'https':
            historySearchCSS = \
                historySearchCSS.replace('https://',
                                         httpPrefix + '://')
    historySearchForm = htmlHeader(cssFilename, historySearchCSS)

    # add the page title
    historySearchForm += \
        '<center><h1>' + translate['Your Posts'] + '</h1></center>'

    if len(boxFilenames) == 0:
        historySearchForm += \
            '<center><h5>' + translate['No results'] + \
            '</h5></center>'
        return historySearchForm

    iconsDir = getIconsDir(baseDir)

    # ensure that the page number is in bounds
    if not pageNumber:
        pageNumber = 1
    elif pageNumber < 1:
        pageNumber = 1

    # get the start end end within the index file
    startIndex = int((pageNumber - 1) * postsPerPage)
    endIndex = startIndex + postsPerPage
    noOfBoxFilenames = len(boxFilenames)
    if endIndex >= noOfBoxFilenames and noOfBoxFilenames > 0:
        endIndex = noOfBoxFilenames - 1

    index = startIndex
    while index <= endIndex:
        postFilename = boxFilenames[index]
        if not postFilename:
            index += 1
            continue
        postJsonObject = loadJson(postFilename)
        if not postJsonObject:
            index += 1
            continue
        showIndividualPostIcons = True
        allowDeletion = False
        historySearchForm += \
            individualPostAsHtml(True, recentPostsCache,
                                 maxRecentPosts,
                                 iconsDir, translate, None,
                                 baseDir, session, wfRequest,
                                 personCache,
                                 nickname, domain, port,
                                 postJsonObject,
                                 None, True, allowDeletion,
                                 httpPrefix, projectVersion,
                                 'search',
                                 YTReplacementDomain,
                                 showIndividualPostIcons,
                                 showIndividualPostIcons,
                                 False, False, False)
        index += 1

    historySearchForm += htmlFooter()
    return historySearchForm


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


def htmlEditLinks(translate: {}, baseDir: str, path: str,
                  domain: str, port: int, httpPrefix: str) -> str:
    """Shows the edit links screen
    """
    if '/users/' not in path:
        return ''
    pathOriginal = path
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '')

    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''

    # is the user a moderator?
    if not isModerator(baseDir, nickname):
        return ''

    cssFilename = baseDir + '/epicyon-links.css'
    if os.path.isfile(baseDir + '/links.css'):
        cssFilename = baseDir + '/links.css'
    with open(cssFilename, 'r') as cssFile:
        editCSS = cssFile.read()
        if httpPrefix != 'https':
            editCSS = \
                editCSS.replace('https://', httpPrefix + '://')

    editLinksForm = htmlHeader(cssFilename, editCSS)
    editLinksForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/linksdata">\n'
    editLinksForm += \
        '  <div class="vertical-center">\n'
    editLinksForm += \
        '    <p class="new-post-text">' + translate['Edit Links'] + '</p>'
    editLinksForm += \
        '    <div class="container">\n'
    editLinksForm += \
        '      <a href="' + pathOriginal + '"><button class="cancelbtn">' + \
        translate['Go Back'] + '</button></a>\n'
    editLinksForm += \
        '      <input type="submit" name="submitLinks" value="' + \
        translate['Submit'] + '">\n'
    editLinksForm += \
        '    </div>\n'

    linksFilename = baseDir + '/accounts/links.txt'
    linksStr = ''
    if os.path.isfile(linksFilename):
        with open(linksFilename, 'r') as fp:
            linksStr = fp.read()

    editLinksForm += \
        '<div class="container">'
    editLinksForm += \
        '  ' + \
        translate['One link per line. Description followed by the link.'] + \
        '<br>'
    editLinksForm += \
        '  <textarea id="message" name="editedLinks" style="height:500px">' + \
        linksStr + '</textarea>'
    editLinksForm += \
        '</div>'

    editLinksForm += htmlFooter()
    return editLinksForm


def htmlEditNewswire(translate: {}, baseDir: str, path: str,
                     domain: str, port: int, httpPrefix: str) -> str:
    """Shows the edit newswire screen
    """
    if '/users/' not in path:
        return ''
    pathOriginal = path
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '')

    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''

    # is the user a moderator?
    if not isModerator(baseDir, nickname):
        return ''

    cssFilename = baseDir + '/epicyon-links.css'
    if os.path.isfile(baseDir + '/links.css'):
        cssFilename = baseDir + '/links.css'
    with open(cssFilename, 'r') as cssFile:
        editCSS = cssFile.read()
        if httpPrefix != 'https':
            editCSS = \
                editCSS.replace('https://', httpPrefix + '://')

    editNewswireForm = htmlHeader(cssFilename, editCSS)
    editNewswireForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/newswiredata">\n'
    editNewswireForm += \
        '  <div class="vertical-center">\n'
    editNewswireForm += \
        '    <p class="new-post-text">' + translate['Edit newswire'] + '</p>'
    editNewswireForm += \
        '    <div class="container">\n'
    editNewswireForm += \
        '      <a href="' + pathOriginal + '"><button class="cancelbtn">' + \
        translate['Go Back'] + '</button></a>\n'
    editNewswireForm += \
        '      <input type="submit" name="submitNewswire" value="' + \
        translate['Submit'] + '">\n'
    editNewswireForm += \
        '    </div>\n'

    newswireFilename = baseDir + '/accounts/newswire.txt'
    newswireStr = ''
    if os.path.isfile(newswireFilename):
        with open(newswireFilename, 'r') as fp:
            newswireStr = fp.read()

    editNewswireForm += \
        '<div class="container">'

    editNewswireForm += \
        '  ' + \
        translate['Add RSS feed links below.'] + \
        '<br>'
    editNewswireForm += \
        '  <textarea id="message" name="editedNewswire" ' + \
        'style="height:500px">' + newswireStr + '</textarea>'

    editNewswireForm += \
        '</div>'

    editNewswireForm += htmlFooter()
    return editNewswireForm


def htmlEditProfile(translate: {}, baseDir: str, path: str,
                    domain: str, port: int, httpPrefix: str) -> str:
    """Shows the edit profile screen
    """
    imageFormats = '.png, .jpg, .jpeg, .gif, .webp, .avif'
    pathOriginal = path
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '')
    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''
    domainFull = domain
    if port:
        if port != 80 and port != 443:
            if ':' not in domain:
                domainFull = domain + ':' + str(port)

    actorFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    if not os.path.isfile(actorFilename):
        return ''

    isBot = ''
    isGroup = ''
    followDMs = ''
    removeTwitter = ''
    notifyLikes = ''
    hideLikeButton = ''
    mediaInstanceStr = ''
    blogsInstanceStr = ''
    newsInstanceStr = ''
    displayNickname = nickname
    bioStr = ''
    donateUrl = ''
    emailAddress = ''
    PGPpubKey = ''
    PGPfingerprint = ''
    xmppAddress = ''
    matrixAddress = ''
    ssbAddress = ''
    blogAddress = ''
    toxAddress = ''
    manuallyApprovesFollowers = ''
    actorJson = loadJson(actorFilename)
    if actorJson:
        donateUrl = getDonationUrl(actorJson)
        xmppAddress = getXmppAddress(actorJson)
        matrixAddress = getMatrixAddress(actorJson)
        ssbAddress = getSSBAddress(actorJson)
        blogAddress = getBlogAddress(actorJson)
        toxAddress = getToxAddress(actorJson)
        emailAddress = getEmailAddress(actorJson)
        PGPpubKey = getPGPpubKey(actorJson)
        PGPfingerprint = getPGPfingerprint(actorJson)
        if actorJson.get('name'):
            displayNickname = actorJson['name']
        if actorJson.get('summary'):
            bioStr = \
                actorJson['summary'].replace('<p>', '').replace('</p>', '')
        if actorJson.get('manuallyApprovesFollowers'):
            if actorJson['manuallyApprovesFollowers']:
                manuallyApprovesFollowers = 'checked'
            else:
                manuallyApprovesFollowers = ''
        if actorJson.get('type'):
            if actorJson['type'] == 'Service':
                isBot = 'checked'
                isGroup = ''
            elif actorJson['type'] == 'Group':
                isGroup = 'checked'
                isBot = ''
    if os.path.isfile(baseDir + '/accounts/' +
                      nickname + '@' + domain + '/.followDMs'):
        followDMs = 'checked'
    if os.path.isfile(baseDir + '/accounts/' +
                      nickname + '@' + domain + '/.removeTwitter'):
        removeTwitter = 'checked'
    if os.path.isfile(baseDir + '/accounts/' +
                      nickname + '@' + domain + '/.notifyLikes'):
        notifyLikes = 'checked'
    if os.path.isfile(baseDir + '/accounts/' +
                      nickname + '@' + domain + '/.hideLikeButton'):
        hideLikeButton = 'checked'

    mediaInstance = getConfigParam(baseDir, "mediaInstance")
    if mediaInstance:
        if mediaInstance is True:
            mediaInstanceStr = 'checked'
            blogsInstanceStr = ''
            newsInstanceStr = ''

    newsInstance = getConfigParam(baseDir, "newsInstance")
    if newsInstance:
        if newsInstance is True:
            newsInstanceStr = 'checked'
            blogsInstanceStr = ''
            mediaInstanceStr = ''

    blogsInstance = getConfigParam(baseDir, "blogsInstance")
    if blogsInstance:
        if blogsInstance is True:
            blogsInstanceStr = 'checked'
            mediaInstanceStr = ''
            newsInstanceStr = ''

    filterStr = ''
    filterFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/filters.txt'
    if os.path.isfile(filterFilename):
        with open(filterFilename, 'r') as filterfile:
            filterStr = filterfile.read()

    switchStr = ''
    switchFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/replacewords.txt'
    if os.path.isfile(switchFilename):
        with open(switchFilename, 'r') as switchfile:
            switchStr = switchfile.read()

    autoTags = ''
    autoTagsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/autotags.txt'
    if os.path.isfile(autoTagsFilename):
        with open(autoTagsFilename, 'r') as autoTagsFile:
            autoTags = autoTagsFile.read()

    autoCW = ''
    autoCWFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/autocw.txt'
    if os.path.isfile(autoCWFilename):
        with open(autoCWFilename, 'r') as autoCWFile:
            autoCW = autoCWFile.read()

    blockedStr = ''
    blockedFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/blocking.txt'
    if os.path.isfile(blockedFilename):
        with open(blockedFilename, 'r') as blockedfile:
            blockedStr = blockedfile.read()

    allowedInstancesStr = ''
    allowedInstancesFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/allowedinstances.txt'
    if os.path.isfile(allowedInstancesFilename):
        with open(allowedInstancesFilename, 'r') as allowedInstancesFile:
            allowedInstancesStr = allowedInstancesFile.read()

    gitProjectsStr = ''
    gitProjectsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/gitprojects.txt'
    if os.path.isfile(gitProjectsFilename):
        with open(gitProjectsFilename, 'r') as gitProjectsFile:
            gitProjectsStr = gitProjectsFile.read()

    skills = getSkills(baseDir, nickname, domain)
    skillsStr = ''
    skillCtr = 1
    if skills:
        for skillDesc, skillValue in skills.items():
            skillsStr += \
                '<p><input type="text" placeholder="' + translate['Skill'] + \
                ' ' + str(skillCtr) + '" name="skillName' + str(skillCtr) + \
                '" value="' + skillDesc + '" style="width:40%">'
            skillsStr += \
                '<input type="range" min="1" max="100" ' + \
                'class="slider" name="skillValue' + \
                str(skillCtr) + '" value="' + str(skillValue) + '"></p>'
            skillCtr += 1

    skillsStr += \
        '<p><input type="text" placeholder="Skill ' + str(skillCtr) + \
        '" name="skillName' + str(skillCtr) + \
        '" value="" style="width:40%">'
    skillsStr += \
        '<input type="range" min="1" max="100" ' + \
        'class="slider" name="skillValue' + \
        str(skillCtr) + '" value="50"></p>'

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        editProfileCSS = cssFile.read()
        if httpPrefix != 'https':
            editProfileCSS = \
                editProfileCSS.replace('https://', httpPrefix + '://')

    instanceStr = ''
    moderatorsStr = ''
    themesDropdown = ''
    adminNickname = getConfigParam(baseDir, 'admin')
    if path.startswith('/users/' + adminNickname + '/'):
        instanceDescription = \
            getConfigParam(baseDir, 'instanceDescription')
        instanceDescriptionShort = \
            getConfigParam(baseDir, 'instanceDescriptionShort')
        instanceTitle = \
            getConfigParam(baseDir, 'instanceTitle')
        instanceStr = '<div class="container">'
        instanceStr += \
            '  <label class="labels">' + \
            translate['Instance Title'] + '</label>'
        if instanceTitle:
            instanceStr += \
                '  <input type="text" name="instanceTitle" value="' + \
                instanceTitle + '"><br>'
        else:
            instanceStr += \
                '  <input type="text" name="instanceTitle" value=""><br>'
        instanceStr += \
            '  <label class="labels">' + \
            translate['Instance Short Description'] + '</label>'
        if instanceDescriptionShort:
            instanceStr += \
                '  <input type="text" ' + \
                'name="instanceDescriptionShort" value="' + \
                instanceDescriptionShort + '"><br>'
        else:
            instanceStr += \
                '  <input type="text" ' + \
                'name="instanceDescriptionShort" value=""><br>'
        instanceStr += \
            '  <label class="labels">' + \
            translate['Instance Description'] + '</label>'
        if instanceDescription:
            instanceStr += \
                '  <textarea id="message" name="instanceDescription" ' + \
                'style="height:200px">' + \
                instanceDescription + '</textarea>'
        else:
            instanceStr += \
                '  <textarea id="message" name="instanceDescription" ' + \
                'style="height:200px"></textarea>'
        instanceStr += \
            '  <label class="labels">' + \
            translate['Instance Logo'] + '</label>'
        instanceStr += \
            '  <input type="file" id="instanceLogo" name="instanceLogo"'
        instanceStr += '      accept="' + imageFormats + '">'
        instanceStr += '</div>'

        moderators = ''
        moderatorsFile = baseDir + '/accounts/moderators.txt'
        if os.path.isfile(moderatorsFile):
            with open(moderatorsFile, "r") as f:
                moderators = f.read()
        moderatorsStr = '<div class="container">'
        moderatorsStr += '  <b>' + translate['Moderators'] + '</b><br>'
        moderatorsStr += '  ' + \
            translate['A list of moderator nicknames. One per line.']
        moderatorsStr += \
            '  <textarea id="message" name="moderators" placeholder="' + \
            translate['List of moderator nicknames'] + \
            '..." style="height:200px">' + moderators + '</textarea>'
        moderatorsStr += '</div>'

        themes = getThemesList()
        themesDropdown = '<div class="container">'
        themesDropdown += '  <b>' + translate['Theme'] + '</b><br>'
        grayscaleFilename = \
            baseDir + '/accounts/.grayscale'
        grayscale = ''
        if os.path.isfile(grayscaleFilename):
            grayscale = 'checked'
        themesDropdown += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="grayscale" ' + grayscale + \
            '> ' + translate['Grayscale'] + '<br>'
        themesDropdown += '  <select id="themeDropdown" ' + \
            'name="themeDropdown" class="theme">'
        for themeName in themes:
            themesDropdown += '    <option value="' + \
                themeName.lower() + '">' + \
                translate[themeName] + '</option>'
        themesDropdown += '  </select><br>'
        if os.path.isfile(baseDir + '/fonts/custom.woff') or \
           os.path.isfile(baseDir + '/fonts/custom.woff2') or \
           os.path.isfile(baseDir + '/fonts/custom.otf') or \
           os.path.isfile(baseDir + '/fonts/custom.ttf'):
            themesDropdown += \
                '      <input type="checkbox" class="profilecheckbox" ' + \
                'name="removeCustomFont"> ' + \
                translate['Remove the custom font'] + '<br>'
        themesDropdown += '</div>'
        themeName = getConfigParam(baseDir, 'theme')
        themesDropdown = \
            themesDropdown.replace('<option value="' + themeName + '">',
                                   '<option value="' + themeName +
                                   '" selected>')

    editProfileForm = htmlHeader(cssFilename, editProfileCSS)
    editProfileForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/profiledata">\n'
    editProfileForm += '  <div class="vertical-center">\n'
    editProfileForm += \
        '    <p class="new-post-text">' + translate['Profile for'] + \
        ' ' + nickname + '@' + domainFull + '</p>'
    editProfileForm += '    <div class="container">\n'
    editProfileForm += \
        '      <a href="' + pathOriginal + '"><button class="cancelbtn">' + \
        translate['Go Back'] + '</button></a>\n'
    editProfileForm += \
        '      <input type="submit" name="submitProfile" value="' + \
        translate['Submit'] + '">\n'
    editProfileForm += '    </div>\n'

    if scheduledPostsExist(baseDir, nickname, domain):
        editProfileForm += '    <div class="container">\n'
        editProfileForm += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="removeScheduledPosts"> ' + \
            translate['Remove scheduled posts'] + '<br>\n'
        editProfileForm += '    </div>\n'

    editProfileForm += '    <div class="container">\n'
    editProfileForm += '      <label class="labels">' + \
        translate['Nickname'] + '</label>\n'
    editProfileForm += \
        '      <input type="text" name="displayNickname" value="' + \
        displayNickname + '"><br>\n'
    editProfileForm += \
        '      <label class="labels">' + translate['Your bio'] + '</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="bio" style="height:200px">' + \
        bioStr + '</textarea>\n'
    editProfileForm += '<label class="labels">' + \
        translate['Donations link'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" placeholder="https://..." ' + \
        'name="donateUrl" value="' + donateUrl + '">\n'
    editProfileForm += \
        '<label class="labels">' + translate['XMPP'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="xmppAddress" value="' + \
        xmppAddress + '">\n'
    editProfileForm += '<label class="labels">' + \
        translate['Matrix'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="matrixAddress" value="' + \
        matrixAddress+'">\n'

    editProfileForm += '<label class="labels">SSB</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="ssbAddress" value="' + \
        ssbAddress + '">\n'

    editProfileForm += '<label class="labels">Blog</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="blogAddress" value="' + \
        blogAddress + '">\n'

    editProfileForm += '<label class="labels">Tox</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="toxAddress" value="' + \
        toxAddress + '">\n'
    editProfileForm += '<label class="labels">' + \
        translate['Email'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="email" value="' + emailAddress + '">\n'
    editProfileForm += \
        '<label class="labels">' + \
        translate['PGP Fingerprint'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="openpgp" value="' + \
        PGPfingerprint + '">\n'
    editProfileForm += \
        '<label class="labels">' + translate['PGP'] + '</label><br>\n'
    editProfileForm += \
        '      <textarea id="message" placeholder=' + \
        '"-----BEGIN PGP PUBLIC KEY BLOCK-----" name="pgp" ' + \
        'style="height:100px">' + PGPpubKey + '</textarea>\n'
    editProfileForm += '<a href="/users/' + nickname + \
        '/followingaccounts"><label class="labels">' + \
        translate['Following'] + '</label></a><br>\n'
    editProfileForm += '    </div>\n'
    editProfileForm += '    <div class="container">\n'
    idx = 'The files attached below should be no larger than ' + \
        '10MB in total uploaded at once.'
    editProfileForm += \
        '      <label class="labels">' + translate[idx] + '</label><br><br>\n'
    editProfileForm += \
        '      <label class="labels">' + translate['Avatar image'] + \
        '</label>\n'
    editProfileForm += \
        '      <input type="file" id="avatar" name="avatar"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += \
        '      <br><label class="labels">' + \
        translate['Background image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="image" name="image"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '      <br><label class="labels">' + \
        translate['Timeline banner image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="banner" name="banner"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '      <br><label class="labels">' + \
        translate['Search banner image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="search_banner" '
    editProfileForm += 'name="search_banner"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '      <br><label class="labels">' + \
        translate['Left column image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="left_col_image" '
    editProfileForm += 'name="left_col_image"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '      <br><label class="labels">' + \
        translate['Right column image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="right_col_image" '
    editProfileForm += 'name="right_col_image"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '    </div>\n'
    editProfileForm += '    <div class="container">\n'
    editProfileForm += \
        '<label class="labels">' + translate['Change Password'] + \
        '</label><br>\n'
    editProfileForm += '      <input type="text" name="password" ' + \
        'value=""><br>\n'
    editProfileForm += \
        '<label class="labels">' + translate['Confirm Password'] + \
        '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="passwordconfirm" value="">\n'
    editProfileForm += '    </div>\n'

    if path.startswith('/users/' + adminNickname + '/'):
        editProfileForm += '    <div class="container">\n'
        editProfileForm += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="mediaInstance" ' + mediaInstanceStr + '> ' + \
            translate['This is a media instance'] + '<br>\n'
        editProfileForm += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="blogsInstance" ' + blogsInstanceStr + '> ' + \
            translate['This is a blogging instance'] + '<br>\n'
        editProfileForm += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="newsInstance" ' + newsInstanceStr + '> ' + \
            translate['This is a news instance'] + '<br>\n'
        editProfileForm += '    </div>\n'

    editProfileForm += '    <div class="container">\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="approveFollowers" ' + manuallyApprovesFollowers + \
        '> ' + translate['Approve follower requests'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" ' + \
        'class="profilecheckbox" name="isBot" ' + \
        isBot + '> ' + translate['This is a bot account'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" ' + \
        'class="profilecheckbox" name="isGroup" ' + isGroup + '> ' + \
        translate['This is a group account'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="followDMs" ' + followDMs + '> ' + \
        translate['Only people I follow can send me DMs'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="removeTwitter" ' + removeTwitter + '> ' + \
        translate['Remove Twitter posts'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="notifyLikes" ' + notifyLikes + '> ' + \
        translate['Notify when posts are liked'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="hideLikeButton" ' + hideLikeButton + '> ' + \
        translate["Don't show the Like button"] + '<br>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Filtered words'] + '</label></b>\n'
    editProfileForm += '      <br><label class="labels">' + \
        translate['One per line'] + '</label>\n'
    editProfileForm += '      <textarea id="message" ' + \
        'name="filteredWords" style="height:200px">' + \
        filterStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Word Replacements'] + '</label></b>\n'
    editProfileForm += '      <br><label class="labels">A -> B</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="switchWords" ' + \
        'style="height:200px">' + switchStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Autogenerated Hashtags'] + '</label></b>\n'
    editProfileForm += '      <br><label class="labels">A -> #B</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="autoTags" ' + \
        'style="height:200px">' + autoTags + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Autogenerated Content Warnings'] + '</label></b>\n'
    editProfileForm += '      <br><label class="labels">A -> B</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="autoCW" ' + \
        'style="height:200px">' + autoCW + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Blocked accounts'] + '</label></b>\n'
    idx = 'Blocked accounts, one per line, in the form ' + \
        'nickname@domain or *@blockeddomain'
    editProfileForm += \
        '      <br><label class="labels">' + translate[idx] + '</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="blocked" style="height:200px">' + \
        blockedStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Federation list'] + '</label></b>\n'
    idx = 'Federate only with a defined set of instances. ' + \
        'One domain name per line.'
    editProfileForm += \
        '      <br><label class="labels">' + \
        translate[idx] + '</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="allowedInstances" ' + \
        'style="height:200px">' + allowedInstancesStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Git Projects'] + '</label></b>\n'
    idx = 'List of project names that you wish to receive git patches for'
    editProfileForm += \
        '      <br><label class="labels">' + \
        translate[idx] + '</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="gitProjects" ' + \
        'style="height:100px">' + gitProjectsStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['YouTube Replacement Domain'] + '</label></b>\n'
    YTReplacementDomain = getConfigParam(baseDir, "youtubedomain")
    if not YTReplacementDomain:
        YTReplacementDomain = ''
    editProfileForm += \
        '      <input type="text" name="ytdomain" value="' + \
        YTReplacementDomain + '">\n'

    editProfileForm += '    </div>\n'
    editProfileForm += '    <div class="container">\n'
    editProfileForm += \
        '      <b><label class="labels">' + \
        translate['Skills'] + '</label></b><br>\n'
    idx = 'If you want to participate within organizations then you ' + \
        'can indicate some skills that you have and approximate ' + \
        'proficiency levels. This helps organizers to construct ' + \
        'teams with an appropriate combination of skills.'
    editProfileForm += '      <label class="labels">' + \
        translate[idx] + '</label>\n'
    editProfileForm += skillsStr + themesDropdown + moderatorsStr
    editProfileForm += '    </div>\n' + instanceStr
    editProfileForm += '    <div class="container">\n'
    editProfileForm += '      <b><label class="labels">' + \
        translate['Danger Zone'] + '</label></b><br>\n'
    editProfileForm += \
        '      <input type="checkbox" class=dangercheckbox" ' + \
        'name="deactivateThisAccount"> ' + \
        translate['Deactivate this account'] + '<br>\n'
    editProfileForm += '    </div>\n'
    editProfileForm += '  </div>\n'
    editProfileForm += '</form>\n'
    editProfileForm += htmlFooter()
    return editProfileForm


def htmlGetLoginCredentials(loginParams: str,
                            lastLoginTime: int) -> (str, str, bool):
    """Receives login credentials via HTTPServer POST
    """
    if not loginParams.startswith('username='):
        return None, None, None
    # minimum time between login attempts
    currTime = int(time.time())
    if currTime < lastLoginTime+10:
        return None, None, None
    if '&' not in loginParams:
        return None, None, None
    loginArgs = loginParams.split('&')
    nickname = None
    password = None
    register = False
    for arg in loginArgs:
        if '=' in arg:
            if arg.split('=', 1)[0] == 'username':
                nickname = arg.split('=', 1)[1]
            elif arg.split('=', 1)[0] == 'password':
                password = arg.split('=', 1)[1]
            elif arg.split('=', 1)[0] == 'register':
                register = True
    return nickname, password, register


def htmlLogin(translate: {}, baseDir: str, autocomplete=True) -> str:
    """Shows the login screen
    """
    accounts = noOfAccounts(baseDir)

    loginImage = 'login.png'
    loginImageFilename = None
    if os.path.isfile(baseDir + '/accounts/' + loginImage):
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.jpg'):
        loginImage = 'login.jpg'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.jpeg'):
        loginImage = 'login.jpeg'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.gif'):
        loginImage = 'login.gif'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.webp'):
        loginImage = 'login.webp'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.avif'):
        loginImage = 'login.avif'
        loginImageFilename = baseDir + '/accounts/' + loginImage

    if not loginImageFilename:
        loginImageFilename = baseDir + '/accounts/' + loginImage
        copyfile(baseDir + '/img/login.png', loginImageFilename)

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    if accounts > 0:
        loginText = \
            '<p class="login-text">' + \
            translate['Welcome. Please enter your login details below.'] + \
            '</p>'
    else:
        loginText = \
            '<p class="login-text">' + \
            translate['Please enter some credentials'] + '</p>'
        loginText += \
            '<p class="login-text">' + \
            translate['You will become the admin of this site.'] + \
            '</p>'
    if os.path.isfile(baseDir + '/accounts/login.txt'):
        # custom login message
        with open(baseDir + '/accounts/login.txt', 'r') as file:
            loginText = '<p class="login-text">' + file.read() + '</p>'

    cssFilename = baseDir + '/epicyon-login.css'
    if os.path.isfile(baseDir + '/login.css'):
        cssFilename = baseDir + '/login.css'
    with open(cssFilename, 'r') as cssFile:
        loginCSS = cssFile.read()

    # show the register button
    registerButtonStr = ''
    if getConfigParam(baseDir, 'registration') == 'open':
        if int(getConfigParam(baseDir, 'registrationsRemaining')) > 0:
            if accounts > 0:
                idx = 'Welcome. Please login or register a new account.'
                loginText = \
                    '<p class="login-text">' + \
                    translate[idx] + \
                    '</p>'
            registerButtonStr = \
                '<button type="submit" name="register">Register</button>'

    TOSstr = \
        '<p class="login-text"><a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>'
    TOSstr += \
        '<p class="login-text"><a href="/about">' + \
        translate['About this Instance'] + '</a></p>'

    loginButtonStr = ''
    if accounts > 0:
        loginButtonStr = \
            '<button type="submit" name="submit">' + \
            translate['Login'] + '</button>'

    autocompleteStr = ''
    if not autocomplete:
        autocompleteStr = 'autocomplete="off" value=""'

    loginForm = htmlHeader(cssFilename, loginCSS)
    loginForm += '<br>\n'
    loginForm += '<form method="POST" action="/login">\n'
    loginForm += '  <div class="imgcontainer">\n'
    loginForm += \
        '    <img loading="lazy" src="' + loginImage + \
        '" alt="login image" class="loginimage">\n'
    loginForm += loginText + TOSstr + '\n'
    loginForm += '  </div>\n'
    loginForm += '\n'
    loginForm += '  <div class="container">\n'
    loginForm += '    <label for="nickname"><b>' + \
        translate['Nickname'] + '</b></label>\n'
    loginForm += \
        '    <input type="text" ' + autocompleteStr + ' placeholder="' + \
        translate['Enter Nickname'] + '" name="username" required autofocus>\n'
    loginForm += '\n'
    loginForm += '    <label for="password"><b>' + \
        translate['Password'] + '</b></label>\n'
    loginForm += \
        '    <input type="password" ' + autocompleteStr + \
        ' placeholder="' + translate['Enter Password'] + \
        '" name="password" required>\n'
    loginForm += loginButtonStr + registerButtonStr + '\n'
    loginForm += '  </div>\n'
    loginForm += '</form>\n'
    loginForm += \
        '<a href="https://gitlab.com/bashrc2/epicyon">' + \
        '<img loading="lazy" class="license" title="' + \
        translate['Get the source code'] + '" alt="' + \
        translate['Get the source code'] + '" src="/icons/agpl.png" /></a>\n'
    loginForm += htmlFooter()
    return loginForm


def htmlTermsOfService(baseDir: str, httpPrefix: str, domainFull: str) -> str:
    """Show the terms of service screen
    """
    adminNickname = getConfigParam(baseDir, 'admin')
    if not os.path.isfile(baseDir + '/accounts/tos.txt'):
        copyfile(baseDir + '/default_tos.txt',
                 baseDir + '/accounts/tos.txt')

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    TOSText = 'Terms of Service go here.'
    if os.path.isfile(baseDir + '/accounts/tos.txt'):
        with open(baseDir + '/accounts/tos.txt', 'r') as file:
            TOSText = file.read()

    TOSForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        termsCSS = cssFile.read()
        if httpPrefix != 'https':
            termsCSS = termsCSS.replace('https://', httpPrefix+'://')

        TOSForm = htmlHeader(cssFilename, termsCSS)
        TOSForm += '<div class="container">' + TOSText + '</div>\n'
        if adminNickname:
            adminActor = httpPrefix + '://' + domainFull + \
                '/users/' + adminNickname
            TOSForm += \
                '<div class="container"><center>\n' + \
                '<p class="administeredby">Administered by <a href="' + \
                adminActor + '">' + adminNickname + '</a></p>\n' + \
                '</center></div>\n'
        TOSForm += htmlFooter()
    return TOSForm


def htmlAbout(baseDir: str, httpPrefix: str,
              domainFull: str, onionDomain: str) -> str:
    """Show the about screen
    """
    adminNickname = getConfigParam(baseDir, 'admin')
    if not os.path.isfile(baseDir + '/accounts/about.txt'):
        copyfile(baseDir + '/default_about.txt',
                 baseDir + '/accounts/about.txt')

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    aboutText = 'Information about this instance goes here.'
    if os.path.isfile(baseDir + '/accounts/about.txt'):
        with open(baseDir + '/accounts/about.txt', 'r') as aboutFile:
            aboutText = aboutFile.read()

    aboutForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        aboutCSS = cssFile.read()
        if httpPrefix != 'http':
            aboutCSS = aboutCSS.replace('https://',
                                        httpPrefix + '://')

        aboutForm = htmlHeader(cssFilename, aboutCSS)
        aboutForm += '<div class="container">' + aboutText + '</div>'
        if onionDomain:
            aboutForm += \
                '<div class="container"><center>\n' + \
                '<p class="administeredby">' + \
                'http://' + onionDomain + '</p>\n</center></div>\n'
        if adminNickname:
            adminActor = '/users/' + adminNickname
            aboutForm += \
                '<div class="container"><center>\n' + \
                '<p class="administeredby">Administered by <a href="' + \
                adminActor + '">' + adminNickname + '</a></p>\n' + \
                '</center></div>\n'
        aboutForm += htmlFooter()
    return aboutForm


def htmlHashtagBlocked(baseDir: str, translate: {}) -> str:
    """Show the screen for a blocked hashtag
    """
    blockedHashtagForm = ''
    cssFilename = baseDir + '/epicyon-suspended.css'
    if os.path.isfile(baseDir + '/suspended.css'):
        cssFilename = baseDir + '/suspended.css'
    with open(cssFilename, 'r') as cssFile:
        blockedHashtagCSS = cssFile.read()
        blockedHashtagForm = htmlHeader(cssFilename, blockedHashtagCSS)
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


def htmlSuspended(baseDir: str) -> str:
    """Show the screen for suspended accounts
    """
    suspendedForm = ''
    cssFilename = baseDir + '/epicyon-suspended.css'
    if os.path.isfile(baseDir + '/suspended.css'):
        cssFilename = baseDir + '/suspended.css'
    with open(cssFilename, 'r') as cssFile:
        suspendedCSS = cssFile.read()
        suspendedForm = htmlHeader(cssFilename, suspendedCSS)
        suspendedForm += '<div><center>\n'
        suspendedForm += '  <p class="screentitle">Account Suspended</p>\n'
        suspendedForm += '  <p>See <a href="/terms">Terms of Service</a></p>\n'
        suspendedForm += '</center></div>\n'
        suspendedForm += htmlFooter()
    return suspendedForm


def htmlNewPost(mediaInstance: bool, translate: {},
                baseDir: str, httpPrefix: str,
                path: str, inReplyTo: str,
                mentions: [],
                reportUrl: str, pageNumber: int,
                nickname: str, domain: str,
                domainFull: str) -> str:
    """New post screen
    """
    iconsDir = getIconsDir(baseDir)
    replyStr = ''

    showPublicOnDropdown = True
    messageBoxHeight = 400

    if not path.endswith('/newshare'):
        if not path.endswith('/newreport'):
            if not inReplyTo or path.endswith('/newreminder'):
                newPostText = '<p class="new-post-text">' + \
                    translate['Write your post text below.'] + '</p>\n'
            else:
                newPostText = \
                    '<p class="new-post-text">' + \
                    translate['Write your reply to'] + \
                    ' <a href="' + inReplyTo + '">' + \
                    translate['this post'] + '</a></p>\n'
                replyStr = '<input type="hidden" ' + \
                    'name="replyTo" value="' + inReplyTo + '">\n'

                # if replying to a non-public post then also make
                # this post non-public
                if not isPublicPostFromUrl(baseDir, nickname, domain,
                                           inReplyTo):
                    newPostPath = path
                    if '?' in newPostPath:
                        newPostPath = newPostPath.split('?')[0]
                    if newPostPath.endswith('/newpost'):
                        path = path.replace('/newpost', '/newfollowers')
                    elif newPostPath.endswith('/newunlisted'):
                        path = path.replace('/newunlisted', '/newfollowers')
                    showPublicOnDropdown = False
        else:
            newPostText = \
                '<p class="new-post-text">' + \
                translate['Write your report below.'] + '</p>\n'

            # custom report header with any additional instructions
            if os.path.isfile(baseDir + '/accounts/report.txt'):
                with open(baseDir + '/accounts/report.txt', 'r') as file:
                    customReportText = file.read()
                    if '</p>' not in customReportText:
                        customReportText = \
                            '<p class="login-subtext">' + \
                            customReportText + '</p>\n'
                        repStr = '<p class="login-subtext">'
                        customReportText = \
                            customReportText.replace('<p>', repStr)
                        newPostText += customReportText

            idx = 'This message only goes to moderators, even if it ' + \
                'mentions other fediverse addresses.'
            newPostText += \
                '<p class="new-post-subtext">' + translate[idx] + '</p>\n' + \
                '<p class="new-post-subtext">' + translate['Also see'] + \
                ' <a href="/terms">' + \
                translate['Terms of Service'] + '</a></p>\n'
    else:
        newPostText = \
            '<p class="new-post-text">' + \
            translate['Enter the details for your shared item below.'] + \
            '</p>\n'

    if path.endswith('/newquestion'):
        newPostText = \
            '<p class="new-post-text">' + \
            translate['Enter the choices for your question below.'] + \
            '</p>\n'

    if os.path.isfile(baseDir + '/accounts/newpost.txt'):
        with open(baseDir + '/accounts/newpost.txt', 'r') as file:
            newPostText = \
                '<p class="new-post-text">' + file.read() + '</p>\n'

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        newPostCSS = cssFile.read()
        if httpPrefix != 'https':
            newPostCSS = newPostCSS.replace('https://',
                                            httpPrefix + '://')

    if '?' in path:
        path = path.split('?')[0]
    pathBase = path.replace('/newreport', '').replace('/newpost', '')
    pathBase = pathBase.replace('/newblog', '').replace('/newshare', '')
    pathBase = pathBase.replace('/newunlisted', '')
    pathBase = pathBase.replace('/newevent', '')
    pathBase = pathBase.replace('/newreminder', '')
    pathBase = pathBase.replace('/newfollowers', '').replace('/newdm', '')

    newPostImageSection = '    <div class="container">'
    if not path.endswith('/newevent'):
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Image description'] + '</label>\n'
    else:
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Event banner image description'] + '</label>\n'
    newPostImageSection += \
        '      <input type="text" name="imageDescription">\n'

    if path.endswith('/newevent'):
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Banner image'] + '</label>\n'
        newPostImageSection += \
            '      <input type="file" id="attachpic" name="attachpic"'
        newPostImageSection += \
            '            accept=".png, .jpg, .jpeg, .gif, .webp, .avif">\n'
    else:
        newPostImageSection += \
            '      <input type="file" id="attachpic" name="attachpic"'
        newPostImageSection += \
            '            accept=".png, .jpg, .jpeg, .gif, ' + \
            '.webp, .avif, .mp4, .webm, .ogv, .mp3, .ogg">\n'
    newPostImageSection += '    </div>\n'

    scopeIcon = 'scope_public.png'
    scopeDescription = translate['Public']
    placeholderSubject = \
        translate['Subject or Content Warning (optional)'] + '...'
    placeholderMentions = ''
    if inReplyTo:
        # mentionsAndContent = getMentionsString(content)
        placeholderMentions = \
            translate['Replying to'] + '...'
    placeholderMessage = translate['Write something'] + '...'
    extraFields = ''
    endpoint = 'newpost'
    if path.endswith('/newblog'):
        placeholderSubject = translate['Title']
        scopeIcon = 'scope_blog.png'
        scopeDescription = translate['Blog']
        endpoint = 'newblog'
    elif path.endswith('/newunlisted'):
        scopeIcon = 'scope_unlisted.png'
        scopeDescription = translate['Unlisted']
        endpoint = 'newunlisted'
    elif path.endswith('/newfollowers'):
        scopeIcon = 'scope_followers.png'
        scopeDescription = translate['Followers']
        endpoint = 'newfollowers'
    elif path.endswith('/newdm'):
        scopeIcon = 'scope_dm.png'
        scopeDescription = translate['DM']
        endpoint = 'newdm'
    elif path.endswith('/newreminder'):
        scopeIcon = 'scope_reminder.png'
        scopeDescription = translate['Reminder']
        endpoint = 'newreminder'
    elif path.endswith('/newevent'):
        scopeIcon = 'scope_event.png'
        scopeDescription = translate['Event']
        endpoint = 'newevent'
        placeholderSubject = translate['Event name']
        placeholderMessage = translate['Describe the event'] + '...'
    elif path.endswith('/newreport'):
        scopeIcon = 'scope_report.png'
        scopeDescription = translate['Report']
        endpoint = 'newreport'
    elif path.endswith('/newquestion'):
        scopeIcon = 'scope_question.png'
        scopeDescription = translate['Question']
        placeholderMessage = translate['Enter your question'] + '...'
        endpoint = 'newquestion'
        extraFields = '<div class="container">\n'
        extraFields += '  <label class="labels">' + \
            translate['Possible answers'] + ':</label><br>\n'
        for questionCtr in range(8):
            extraFields += \
                '  <input type="text" class="questionOption" placeholder="' + \
                str(questionCtr + 1) + \
                '" name="questionOption' + str(questionCtr) + '"><br>\n'
        extraFields += \
            '  <label class="labels">' + \
            translate['Duration of listing in days'] + \
            ':</label> <input type="number" name="duration" ' + \
            'min="1" max="365" step="1" value="14"><br>\n'
        extraFields += '</div>'
    elif path.endswith('/newshare'):
        scopeIcon = 'scope_share.png'
        scopeDescription = translate['Shared Item']
        placeholderSubject = translate['Name of the shared item'] + '...'
        placeholderMessage = \
            translate['Description of the item being shared'] + '...'
        endpoint = 'newshare'
        extraFields = '<div class="container">\n'
        extraFields += \
            '  <label class="labels">' + \
            translate['Type of shared item. eg. hat'] + ':</label>\n'
        extraFields += \
            '  <input type="text" class="itemType" name="itemType">\n'
        extraFields += \
            '  <br><label class="labels">' + \
            translate['Category of shared item. eg. clothing'] + ':</label>\n'
        extraFields += \
            '  <input type="text" class="category" name="category">\n'
        extraFields += \
            '  <br><label class="labels">' + \
            translate['Duration of listing in days'] + ':</label>\n'
        extraFields += '  <input type="number" name="duration" ' + \
            'min="1" max="365" step="1" value="14">\n'
        extraFields += '</div>\n'
        extraFields += '<div class="container">\n'
        extraFields += \
            '<label class="labels">' + \
            translate['City or location of the shared item'] + ':</label>\n'
        extraFields += '<input type="text" name="location">\n'
        extraFields += '</div>\n'

    dateAndLocation = ''
    if endpoint != 'newshare' and \
       endpoint != 'newreport' and \
       endpoint != 'newquestion':
        dateAndLocation = '<div class="container">\n'

        if endpoint == 'newevent':
            # event status
            dateAndLocation += '<label class="labels">' + \
                translate['Status of the event'] + ':</label><br>\n'
            dateAndLocation += '<input type="radio" id="tentative" ' + \
                'name="eventStatus" value="tentative">\n'
            dateAndLocation += '<label class="labels" for="tentative">' + \
                translate['Tentative'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="confirmed" ' + \
                'name="eventStatus" value="confirmed" checked>\n'
            dateAndLocation += '<label class="labels" for="confirmed">' + \
                translate['Confirmed'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="cancelled" ' + \
                'name="eventStatus" value="cancelled">\n'
            dateAndLocation += '<label class="labels" for="cancelled">' + \
                translate['Cancelled'] + '</label><br>\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # maximum attendees
            dateAndLocation += '<label class="labels" ' + \
                'for="maximumAttendeeCapacity">' + \
                translate['Maximum attendees'] + ':</label>\n'
            dateAndLocation += '<input type="number" ' + \
                'id="maximumAttendeeCapacity" ' + \
                'name="maximumAttendeeCapacity" min="1" max="999999" ' + \
                'value="100">\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # event joining options
            dateAndLocation += '<label class="labels">' + \
                translate['Joining'] + ':</label><br>\n'
            dateAndLocation += '<input type="radio" id="free" ' + \
                'name="joinMode" value="free" checked>\n'
            dateAndLocation += '<label class="labels" for="free">' + \
                translate['Anyone can join'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="restricted" ' + \
                'name="joinMode" value="restricted">\n'
            dateAndLocation += '<label class="labels" for="female">' + \
                translate['Apply to join'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="invite" ' + \
                'name="joinMode" value="invite">\n'
            dateAndLocation += '<label class="labels" for="other">' + \
                translate['Invitation only'] + '</label>\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # Event posts don't allow replies - they're just an announcement.
            # They also have a few more checkboxes
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="privateEvent"><label class="labels"> ' + \
                translate['This is a private event.'] + '</label></p>\n'
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="anonymousParticipationEnabled">' + \
                '<label class="labels"> ' + \
                translate['Allow anonymous participation.'] + '</label></p>\n'
        else:
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="commentsEnabled" checked><label class="labels"> ' + \
                translate['Allow replies.'] + '</label></p>\n'

        if not inReplyTo and endpoint != 'newevent':
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="schedulePost"><label class="labels"> ' + \
                translate['This is a scheduled post.'] + '</label></p>\n'

        if endpoint != 'newevent':
            dateAndLocation += \
                '<p><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                iconsDir + '/calendar.png"/>\n'
            # select a date and time for this post
            dateAndLocation += '<label class="labels">' + \
                translate['Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="eventDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="eventTime"></label></p>\n'
        else:
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            dateAndLocation += \
                '<p><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                iconsDir + '/calendar.png"/>\n'
            # select start time for the event
            dateAndLocation += '<label class="labels">' + \
                translate['Start Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="eventDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="eventTime"></label></p>\n'
            # select end time for the event
            dateAndLocation += \
                '<br><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                iconsDir + '/calendar.png"/>\n'
            dateAndLocation += '<label class="labels">' + \
                translate['End Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="endDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="endTime"></label>\n'

        if endpoint == 'newevent':
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            dateAndLocation += '<br><label class="labels">' + \
                translate['Moderation policy or code of conduct'] + \
                ': </label>\n'
            dateAndLocation += \
                '    <textarea id="message" ' + \
                'name="repliesModerationOption" style="height:' + \
                str(messageBoxHeight) + 'px"></textarea>\n'
        dateAndLocation += '</div>\n'
        dateAndLocation += '<div class="container">\n'
        dateAndLocation += '<br><label class="labels">' + \
            translate['Location'] + ': </label>\n'
        dateAndLocation += '<input type="text" name="location">\n'
        if endpoint == 'newevent':
            dateAndLocation += '<br><label class="labels">' + \
                translate['Ticket URL'] + ': </label>\n'
            dateAndLocation += '<input type="text" name="ticketUrl">\n'
            dateAndLocation += '<br><label class="labels">' + \
                translate['Categories'] + ': </label>\n'
            dateAndLocation += '<input type="text" name="category">\n'
        dateAndLocation += '</div>\n'

    newPostForm = htmlHeader(cssFilename, newPostCSS)

    # only show the share option if this is not a reply
    shareOptionOnDropdown = ''
    questionOptionOnDropdown = ''
    if not replyStr:
        shareOptionOnDropdown = \
            '        <a href="' + pathBase + \
            '/newshare"><li><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_share.png"/><b>' + translate['Shares'] + \
            '</b><br>' + translate['Describe a shared item'] + '</li></a>\n'
        questionOptionOnDropdown = \
            '        <a href="' + pathBase + \
            '/newquestion"><li><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_question.png"/><b>' + translate['Question'] + \
            '</b><br>' + translate['Ask a question'] + '</li></a>\n'

    mentionsStr = ''
    for m in mentions:
        mentionNickname = getNicknameFromActor(m)
        if not mentionNickname:
            continue
        mentionDomain, mentionPort = getDomainFromActor(m)
        if not mentionDomain:
            continue
        if mentionPort:
            mentionsHandle = \
                '@' + mentionNickname + '@' + \
                mentionDomain + ':' + str(mentionPort)
        else:
            mentionsHandle = '@' + mentionNickname + '@' + mentionDomain
        if mentionsHandle not in mentionsStr:
            mentionsStr += mentionsHandle + ' '

    # build suffixes so that any replies or mentions are
    # preserved when switching between scopes
    dropdownNewPostSuffix = '/newpost'
    dropdownNewBlogSuffix = '/newblog'
    dropdownUnlistedSuffix = '/newunlisted'
    dropdownFollowersSuffix = '/newfollowers'
    dropdownDMSuffix = '/newdm'
    dropdownEventSuffix = '/newevent'
    dropdownReminderSuffix = '/newreminder'
    dropdownReportSuffix = '/newreport'
    if inReplyTo or mentions:
        dropdownNewPostSuffix = ''
        dropdownNewBlogSuffix = ''
        dropdownUnlistedSuffix = ''
        dropdownFollowersSuffix = ''
        dropdownDMSuffix = ''
        dropdownEventSuffix = ''
        dropdownReminderSuffix = ''
        dropdownReportSuffix = ''
    if inReplyTo:
        dropdownNewPostSuffix += '?replyto=' + inReplyTo
        dropdownNewBlogSuffix += '?replyto=' + inReplyTo
        dropdownUnlistedSuffix += '?replyto=' + inReplyTo
        dropdownFollowersSuffix += '?replyfollowers=' + inReplyTo
        dropdownDMSuffix += '?replydm=' + inReplyTo
    for mentionedActor in mentions:
        dropdownNewPostSuffix += '?mention=' + mentionedActor
        dropdownNewBlogSuffix += '?mention=' + mentionedActor
        dropdownUnlistedSuffix += '?mention=' + mentionedActor
        dropdownFollowersSuffix += '?mention=' + mentionedActor
        dropdownDMSuffix += '?mention=' + mentionedActor
        dropdownReportSuffix += '?mention=' + mentionedActor

    dropDownContent = ''
    if not reportUrl:
        dropDownContent += "<div class='msgscope-collapse collapse "
        dropDownContent += "right desktoponly' id='msgscope'>\n"
        dropDownContent += "  <ul class='nav msgscope-nav msgscope-right'>\n"
        dropDownContent += "  <li class=' ' style='position: relative;'>\n"
        dropDownContent += "  <div class='toggle-msgScope button-msgScope'>\n"
        dropDownContent += "    <input id='toggleMsgScope' "
        dropDownContent += "name='toggleMsgScope' type='checkbox'/>\n"
        dropDownContent += "    <label for='toggleMsgScope'>\n"
        dropDownContent += "      <div class='lined-thin'>\n"
        dropDownContent += '        <img loading="lazy" alt="" title="" src="/'
        dropDownContent += iconsDir + '/' + scopeIcon
        dropDownContent += '"/><b class="scope-desc">'
        dropDownContent += scopeDescription + '</b>\n'
        dropDownContent += "        <span class='caret'/>\n"
        dropDownContent += "      </div>\n"
        dropDownContent += "    </label>\n"
        dropDownContent += "    <div class='toggle-inside'>\n"
        dropDownContent += "      <ul aria-labelledby='dropdownMsgScope' "
        dropDownContent += "class='dropdown-menutoggle'>\n"

        if showPublicOnDropdown:
            dropDownContent += "        " \
                '<a href="' + pathBase + dropdownNewPostSuffix + \
                '"><li><img loading="lazy" alt="" title="" src="/' + \
                iconsDir + '/scope_public.png"/><b>' + \
                translate['Public'] + '</b><br>' + \
                translate['Visible to anyone'] + '</li></a>\n'
            dropDownContent += "        " \
                '<a href="' + pathBase + dropdownNewBlogSuffix + \
                '"><li><img loading="lazy" alt="" title="" src="/' + \
                iconsDir + '/edit.png"/><b>' + \
                translate['Blog'] + '</b><br>' + \
                translate['Publicly visible post'] + '</li></a>\n'
            dropDownContent += "        " \
                '<a href="' + pathBase + dropdownUnlistedSuffix + \
                '"><li><img loading="lazy" alt="" title="" src="/' + \
                iconsDir+'/scope_unlisted.png"/><b>' + \
                translate['Unlisted'] + '</b><br>' + \
                translate['Not on public timeline'] + '</li></a>\n'
        dropDownContent += "        " \
            '<a href="' + pathBase + dropdownFollowersSuffix + \
            '"><li><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_followers.png"/><b>' + \
            translate['Followers'] + '</b><br>' + \
            translate['Only to followers'] + '</li></a>\n'
        dropDownContent += "        " \
            '<a href="' + pathBase + dropdownDMSuffix + \
            '"><li><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_dm.png"/><b>' + translate['DM'] + \
            '</b><br>' + translate['Only to mentioned people'] + \
            '</li></a>\n'
        dropDownContent += "        " \
            '<a href="' + pathBase + dropdownReminderSuffix + \
            '"><li><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_reminder.png"/><b>' + translate['Reminder'] + \
            '</b><br>' + translate['Scheduled note to yourself'] + \
            '</li></a>\n'
        dropDownContent += "        " \
            '<a href="' + pathBase + dropdownEventSuffix + \
            '"><li><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_event.png"/><b>' + translate['Event'] + \
            '</b><br>' + translate['Create an event'] + \
            '</li></a>\n'
        dropDownContent += "        " \
            '<a href="' + pathBase + dropdownReportSuffix + \
            '"><li><img loading="lazy" alt="" title="" src="/' + iconsDir + \
            '/scope_report.png"/><b>' + translate['Report'] + \
            '</b><br>' + translate['Send to moderators'] + '</li></a>\n'
        dropDownContent += questionOptionOnDropdown + shareOptionOnDropdown
        dropDownContent += '      </ul>\n'
        dropDownContent += '    </div>\n'
        dropDownContent += '  </div>\n'
        dropDownContent += '  </li>\n'
        dropDownContent += '  </ul>\n'
        dropDownContent += '</div>\n'
    else:
        mentionsStr = 'Re: ' + reportUrl + '\n\n' + mentionsStr

    newPostForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + \
        path + '?' + endpoint + '?page=' + str(pageNumber) + '">\n'
    newPostForm += '  <div class="vertical-center">\n'
    newPostForm += \
        '    <label for="nickname"><b>' + newPostText + '</b></label>\n'
    newPostForm += '    <div class="container">\n'
    newPostForm += '      <table style="width:100%" border="0"><tr>\n'
    newPostForm += '<td>' + dropDownContent + '</td>\n'
    newPostForm += \
        '      <td><a href="' + pathBase + \
        '/searchemoji"><img loading="lazy" class="emojisearch" ' + \
        'src="/emoji/1F601.png" title="' + \
        translate['Search for emoji'] + '" alt="' + \
        translate['Search for emoji'] + '"/></a></td>\n'
    newPostForm += '      </tr>\n'
    newPostForm += '</table>\n'
    newPostForm += '    </div>\n'
    newPostForm += '    <div class="container"><center>\n'
    newPostForm += \
        '      <a href="' + pathBase + \
        '/inbox"><button class="cancelbtn">' + \
        translate['Go Back'] + '</button></a>\n'
    newPostForm += \
        '      <input type="submit" name="submitPost" value="' + \
        translate['Submit'] + '">\n'
    newPostForm += '    </center></div>\n'
    newPostForm += replyStr
    if mediaInstance and not replyStr:
        newPostForm += newPostImageSection

    newPostForm += \
        '    <label class="labels">' + placeholderSubject + '</label><br>'
    newPostForm += '    <input type="text" name="subject">'
    newPostForm += ''

    selectedStr = ' selected'
    if inReplyTo or endpoint == 'newdm':
        if inReplyTo:
            newPostForm += \
                '    <label class="labels">' + placeholderMentions + \
                '</label><br>\n'
        else:
            newPostForm += \
                '    <a href="/users/' + nickname + \
                '/followingaccounts" title="' + \
                translate['Show a list of addresses to send to'] + '">' \
                '<label class="labels">' + \
                translate['Send to'] + ':' + '</label> 📄</a><br>\n'
        newPostForm += \
            '    <input type="text" name="mentions" ' + \
            'list="followingHandles" value="' + mentionsStr + '" selected>\n'
        newPostForm += \
            htmlFollowingDataList(baseDir, nickname, domain, domainFull)
        newPostForm += ''
        selectedStr = ''

    newPostForm += \
        '    <br><label class="labels">' + placeholderMessage + '</label>'
    if mediaInstance:
        messageBoxHeight = 200

    if endpoint == 'newquestion':
        messageBoxHeight = 100
    elif endpoint == 'newblog':
        messageBoxHeight = 800

    newPostForm += \
        '    <textarea id="message" name="message" style="height:' + \
        str(messageBoxHeight) + 'px"' + selectedStr + '></textarea>\n'
    newPostForm += extraFields+dateAndLocation
    if not mediaInstance or replyStr:
        newPostForm += newPostImageSection
    newPostForm += '  </div>\n'
    newPostForm += '</form>\n'

    if not reportUrl:
        newPostForm = \
            newPostForm.replace('<body>', '<body onload="focusOnMessage()">')

    newPostForm += htmlFooter()
    return newPostForm


def getFontFromCss(css: str) -> (str, str):
    """Returns the font name and format
    """
    if ' url(' not in css:
        return None, None
    fontName = css.split(" url(")[1].split(")")[0].replace("'", '')
    fontFormat = css.split(" format('")[1].split("')")[0]
    return fontName, fontFormat


def htmlHeader(cssFilename: str, css: str, lang='en') -> str:
    htmlStr = '<!DOCTYPE html>\n'
    htmlStr += '<html lang="' + lang + '">\n'
    htmlStr += '  <head>\n'
    htmlStr += '    <meta charset="utf-8">\n'
    fontName, fontFormat = getFontFromCss(css)
    if fontName:
        htmlStr += '    <link rel="preload" as="font" type="' + \
            fontFormat + '" href="' + fontName + '" crossorigin>\n'
    htmlStr += '    <style>\n' + css + '</style>\n'
    htmlStr += '    <link rel="manifest" href="/manifest.json">\n'
    htmlStr += '    <meta name="theme-color" content="grey">\n'
    htmlStr += '    <title>Epicyon</title>\n'
    htmlStr += '  </head>\n'
    htmlStr += '  <body>\n'
    return htmlStr


def htmlFooter() -> str:
    htmlStr = '  </body>\n'
    htmlStr += '</html>\n'
    return htmlStr


def htmlProfilePosts(recentPostsCache: {}, maxRecentPosts: int,
                     translate: {},
                     baseDir: str, httpPrefix: str,
                     authorized: bool,
                     nickname: str, domain: str, port: int,
                     session, wfRequest: {}, personCache: {},
                     projectVersion: str,
                     YTReplacementDomain: str) -> str:
    """Shows posts on the profile screen
    These should only be public posts
    """
    iconsDir = getIconsDir(baseDir)
    profileStr = ''
    maxItems = 4
    ctr = 0
    currPage = 1
    while ctr < maxItems and currPage < 4:
        outboxFeed = \
            personBoxJson({}, session, baseDir, domain,
                          port,
                          '/users/' + nickname + '/outbox?page=' +
                          str(currPage),
                          httpPrefix,
                          10, 'outbox',
                          authorized)
        if not outboxFeed:
            break
        if len(outboxFeed['orderedItems']) == 0:
            break
        for item in outboxFeed['orderedItems']:
            if item['type'] == 'Create':
                postStr = \
                    individualPostAsHtml(True, recentPostsCache,
                                         maxRecentPosts,
                                         iconsDir, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         False, False, False, True, False)
                if postStr:
                    profileStr += postStr
                    ctr += 1
                    if ctr >= maxItems:
                        break
        currPage += 1
    return profileStr


def htmlProfileFollowing(translate: {}, baseDir: str, httpPrefix: str,
                         authorized: bool,
                         nickname: str, domain: str, port: int,
                         session, wfRequest: {}, personCache: {},
                         followingJson: {}, projectVersion: str,
                         buttons: [],
                         feedName: str, actor: str,
                         pageNumber: int,
                         maxItemsPerPage: int) -> str:
    """Shows following on the profile screen
    """
    profileStr = ''

    iconsDir = getIconsDir(baseDir)
    if authorized and pageNumber:
        if authorized and pageNumber > 1:
            # page up arrow
            profileStr += \
                '  <center>\n' + \
                '    <a href="' + actor + '/' + feedName + \
                '?page=' + str(pageNumber - 1) + \
                '"><img loading="lazy" class="pageicon" src="/' + \
                iconsDir + '/pageup.png" title="' + \
                translate['Page up'] + '" alt="' + \
                translate['Page up'] + '"></a>\n' + \
                '  </center>\n'

    for item in followingJson['orderedItems']:
        profileStr += \
            individualFollowAsHtml(translate, baseDir, session,
                                   wfRequest, personCache,
                                   domain, item, authorized, nickname,
                                   httpPrefix, projectVersion,
                                   buttons)
    if authorized and maxItemsPerPage and pageNumber:
        if len(followingJson['orderedItems']) >= maxItemsPerPage:
            # page down arrow
            profileStr += \
                '  <center>\n' + \
                '    <a href="' + actor + '/' + feedName + \
                '?page=' + str(pageNumber + 1) + \
                '"><img loading="lazy" class="pageicon" src="/' + \
                iconsDir + '/pagedown.png" title="' + \
                translate['Page down'] + '" alt="' + \
                translate['Page down'] + '"></a>\n' + \
                '  </center>\n'
    return profileStr


def htmlProfileRoles(translate: {}, nickname: str, domain: str,
                     rolesJson: {}) -> str:
    """Shows roles on the profile screen
    """
    profileStr = ''
    for project, rolesList in rolesJson.items():
        profileStr += \
            '<div class="roles">\n<h2>' + project + \
            '</h2>\n<div class="roles-inner">\n'
        for role in rolesList:
            profileStr += '<h3>' + role + '</h3>\n'
        profileStr += '</div></div>\n'
    if len(profileStr) == 0:
        profileStr += \
            '<p>@' + nickname + '@' + domain + ' has no roles assigned</p>\n'
    else:
        profileStr = '<div>' + profileStr + '</div>\n'
    return profileStr


def htmlProfileSkills(translate: {}, nickname: str, domain: str,
                      skillsJson: {}) -> str:
    """Shows skills on the profile screen
    """
    profileStr = ''
    for skill, level in skillsJson.items():
        profileStr += \
            '<div>' + skill + \
            '<br><div id="myProgress"><div id="myBar" style="width:' + \
            str(level) + '%"></div></div></div>\n<br>\n'
    if len(profileStr) > 0:
        profileStr = '<center><div class="skill-title">' + \
            profileStr + '</div></center>\n'
    return profileStr


def htmlIndividualShare(actor: str, item: {}, translate: {},
                        showContact: bool, removeButton: bool) -> str:
    """Returns an individual shared item as html
    """
    profileStr = '<div class="container">\n'
    profileStr += '<p class="share-title">' + item['displayName'] + '</p>\n'
    if item.get('imageUrl'):
        profileStr += '<a href="' + item['imageUrl'] + '">\n'
        profileStr += \
            '<img loading="lazy" src="' + item['imageUrl'] + \
            '" alt="' + translate['Item image'] + '">\n</a>\n'
    profileStr += '<p>' + item['summary'] + '</p>\n'
    profileStr += \
        '<p><b>' + translate['Type'] + ':</b> ' + item['itemType'] + ' '
    profileStr += \
        '<b>' + translate['Category'] + ':</b> ' + item['category'] + ' '
    profileStr += \
        '<b>' + translate['Location'] + ':</b> ' + item['location'] + '</p>\n'
    if showContact:
        contactActor = item['actor']
        profileStr += \
            '<p><a href="' + actor + \
            '?replydm=sharedesc:' + item['displayName'] + \
            '?mention=' + contactActor + '"><button class="button">' + \
            translate['Contact'] + '</button></a>\n'
    if removeButton:
        profileStr += \
            ' <a href="' + actor + '?rmshare=' + item['displayName'] + \
            '"><button class="button">' + \
            translate['Remove'] + '</button></a>\n'
    profileStr += '</div>\n'
    return profileStr


def htmlProfileShares(actor: str, translate: {},
                      nickname: str, domain: str, sharesJson: {}) -> str:
    """Shows shares on the profile screen
    """
    profileStr = ''
    for item in sharesJson['orderedItems']:
        profileStr += htmlIndividualShare(actor, item, translate, False, False)
    if len(profileStr) > 0:
        profileStr = '<div class="share-title">' + profileStr + '</div>\n'
    return profileStr


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
    startIndex = itemsPerPage*pageNumber
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


def htmlSharesTimeline(translate: {}, pageNumber: int, itemsPerPage: int,
                       baseDir: str, actor: str,
                       nickname: str, domain: str, port: int,
                       maxSharesPerAccount: int, httpPrefix: str) -> str:
    """Show shared items timeline as html
    """
    sharesJson, lastPage = \
        sharesTimelineJson(actor, pageNumber, itemsPerPage,
                           baseDir, maxSharesPerAccount)
    domainFull = domain
    if port != 80 and port != 443:
        if ':' not in domain:
            domainFull = domain + ':' + str(port)
    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    timelineStr = ''

    if pageNumber > 1:
        iconsDir = getIconsDir(baseDir)
        timelineStr += \
            '  <center>\n' + \
            '    <a href="' + actor + '/tlshares?page=' + \
            str(pageNumber - 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pageup.png" title="' + translate['Page up'] + \
            '" alt="' + translate['Page up'] + '"></a>\n' + \
            '  </center>\n'

    for published, item in sharesJson.items():
        showContactButton = False
        if item['actor'] != actor:
            showContactButton = True
        showRemoveButton = False
        if item['actor'] == actor:
            showRemoveButton = True
        timelineStr += \
            htmlIndividualShare(actor, item, translate,
                                showContactButton, showRemoveButton)

    if not lastPage:
        iconsDir = getIconsDir(baseDir)
        timelineStr += \
            '  <center>\n' + \
            '    <a href="' + actor + '/tlshares?page=' + \
            str(pageNumber + 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pagedown.png" title="' + translate['Page down'] + \
            '" alt="' + translate['Page down'] + '"></a>\n' + \
            '  </center>\n'

    return timelineStr


def htmlProfile(defaultTimeline: str,
                recentPostsCache: {}, maxRecentPosts: int,
                translate: {}, projectVersion: str,
                baseDir: str, httpPrefix: str, authorized: bool,
                profileJson: {}, selected: str,
                session, wfRequest: {}, personCache: {},
                YTReplacementDomain: str,
                extraJson=None,
                pageNumber=None, maxItemsPerPage=None) -> str:
    """Show the profile page as html
    """
    nickname = profileJson['preferredUsername']
    if not nickname:
        return ""
    domain, port = getDomainFromActor(profileJson['id'])
    if not domain:
        return ""
    displayName = \
        addEmojiToDisplayName(baseDir, httpPrefix,
                              nickname, domain,
                              profileJson['name'], True)
    domainFull = domain
    if port:
        domainFull = domain + ':' + str(port)
    profileDescription = \
        addEmojiToDisplayName(baseDir, httpPrefix,
                              nickname, domain,
                              profileJson['summary'], False)
    postsButton = 'button'
    followingButton = 'button'
    followersButton = 'button'
    rolesButton = 'button'
    skillsButton = 'button'
    sharesButton = 'button'
    if selected == 'posts':
        postsButton = 'buttonselected'
    elif selected == 'following':
        followingButton = 'buttonselected'
    elif selected == 'followers':
        followersButton = 'buttonselected'
    elif selected == 'roles':
        rolesButton = 'buttonselected'
    elif selected == 'skills':
        skillsButton = 'buttonselected'
    elif selected == 'shares':
        sharesButton = 'buttonselected'
    loginButton = ''

    followApprovalsSection = ''
    followApprovals = False
    linkToTimelineStart = ''
    linkToTimelineEnd = ''
    editProfileStr = ''
    logoutStr = ''
    actor = profileJson['id']
    usersPath = '/users/' + actor.split('/users/')[1]

    donateSection = ''
    donateUrl = getDonationUrl(profileJson)
    PGPpubKey = getPGPpubKey(profileJson)
    PGPfingerprint = getPGPfingerprint(profileJson)
    emailAddress = getEmailAddress(profileJson)
    xmppAddress = getXmppAddress(profileJson)
    matrixAddress = getMatrixAddress(profileJson)
    ssbAddress = getSSBAddress(profileJson)
    toxAddress = getToxAddress(profileJson)
    if donateUrl or xmppAddress or matrixAddress or \
       ssbAddress or toxAddress or PGPpubKey or \
       PGPfingerprint or emailAddress:
        donateSection = '<div class="container">\n'
        donateSection += '  <center>\n'
        if donateUrl:
            donateSection += \
                '    <p><a href="' + donateUrl + \
                '"><button class="donateButton">' + translate['Donate'] + \
                '</button></a></p>\n'
        if emailAddress:
            donateSection += \
                '<p>' + translate['Email'] + ': <a href="mailto:' + \
                emailAddress + '">' + emailAddress + '</a></p>\n'
        if xmppAddress:
            donateSection += \
                '<p>' + translate['XMPP'] + ': <a href="xmpp:' + \
                xmppAddress + '">'+xmppAddress + '</a></p>\n'
        if matrixAddress:
            donateSection += \
                '<p>' + translate['Matrix'] + ': ' + matrixAddress + '</p>\n'
        if ssbAddress:
            donateSection += \
                '<p>SSB: <label class="ssbaddr">' + \
                ssbAddress + '</label></p>\n'
        if toxAddress:
            donateSection += \
                '<p>Tox: <label class="toxaddr">' + \
                toxAddress + '</label></p>\n'
        if PGPfingerprint:
            donateSection += \
                '<p class="pgp">PGP: ' + \
                PGPfingerprint.replace('\n', '<br>') + '</p>\n'
        if PGPpubKey:
            donateSection += \
                '<p class="pgp">' + PGPpubKey.replace('\n', '<br>') + '</p>\n'
        donateSection += '  </center>\n'
        donateSection += '</div>\n'

    if not authorized:
        loginButton = \
            '<br><a href="/login"><button class="loginButton">' + \
            translate['Login'] + '</button></a>'
    else:
        editProfileStr = \
            '<a href="' + usersPath + \
            '/editprofile"><button class="button"><span>' + \
            translate['Edit'] + ' </span></button></a>'
        logoutStr = \
            '<a href="/logout"><button class="button"><span>' + \
            translate['Logout'] + ' </span></button></a>'
        linkToTimelineStart = \
            '<a href="/users/' + nickname + '/' + defaultTimeline + \
            '"><label class="transparent">' + \
            translate['Switch to timeline view'] + '</label></a>'
        linkToTimelineStart += \
            '<a href="/users/' + nickname + '/' + defaultTimeline + \
            '" title="' + translate['Switch to timeline view'] + \
            '" alt="' + translate['Switch to timeline view'] + '">'
        linkToTimelineEnd = '</a>'
        # are there any follow requests?
        followRequestsFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/followrequests.txt'
        if os.path.isfile(followRequestsFilename):
            with open(followRequestsFilename, 'r') as f:
                for line in f:
                    if len(line) > 0:
                        followApprovals = True
                        followersButton = 'buttonhighlighted'
                        if selected == 'followers':
                            followersButton = 'buttonselectedhighlighted'
                        break
        if selected == 'followers':
            if followApprovals:
                with open(followRequestsFilename, 'r') as f:
                    for followerHandle in f:
                        if len(line) > 0:
                            if '://' in followerHandle:
                                followerActor = followerHandle
                            else:
                                followerActor = \
                                    httpPrefix + '://' + \
                                    followerHandle.split('@')[1] + \
                                    '/users/' + followerHandle.split('@')[0]
                            basePath = '/users/' + nickname
                            followApprovalsSection += '<div class="container">'
                            followApprovalsSection += \
                                '<a href="' + followerActor + '">'
                            followApprovalsSection += \
                                '<span class="followRequestHandle">' + \
                                followerHandle + '</span></a>'
                            followApprovalsSection += \
                                '<a href="' + basePath + \
                                '/followapprove=' + followerHandle + '">'
                            followApprovalsSection += \
                                '<button class="followApprove">' + \
                                translate['Approve'] + '</button></a><br><br>'
                            followApprovalsSection += \
                                '<a href="' + basePath + \
                                '/followdeny=' + followerHandle + '">'
                            followApprovalsSection += \
                                '<button class="followDeny">' + \
                                translate['Deny'] + '</button></a>'
                            followApprovalsSection += '</div>'

    profileDescriptionShort = profileDescription
    if '\n' in profileDescription:
        if len(profileDescription.split('\n')) > 2:
            profileDescriptionShort = ''
    else:
        if '<br>' in profileDescription:
            if len(profileDescription.split('<br>')) > 2:
                profileDescriptionShort = ''
                profileDescription = profileDescription.replace('<br>', '\n')
    # keep the profile description short
    if len(profileDescriptionShort) > 256:
        profileDescriptionShort = ''
    # remove formatting from profile description used on title
    avatarDescription = ''
    if profileJson.get('summary'):
        avatarDescription = profileJson['summary'].replace('<br>', '\n')
        avatarDescription = avatarDescription.replace('<p>', '')
        avatarDescription = avatarDescription.replace('</p>', '')
    profileHeaderStr = '<div class="hero-image">'
    profileHeaderStr += '  <div class="hero-text">'
    profileHeaderStr += \
        '    <img loading="lazy" src="' + profileJson['icon']['url'] + \
        '" title="' + avatarDescription + '" alt="' + \
        avatarDescription + '" class="title">'
    profileHeaderStr += '    <h1>' + displayName + '</h1>'
    iconsDir = getIconsDir(baseDir)
    profileHeaderStr += \
        '<p><b>@' + nickname + '@' + domainFull + '</b><br>'
    profileHeaderStr += \
        '<a href="/users/' + nickname + \
        '/qrcode.png" alt="' + translate['QR Code'] + '" title="' + \
        translate['QR Code'] + '">' + \
        '<img class="qrcode" src="/' + iconsDir + '/qrcode.png" /></a></p>'
    profileHeaderStr += '    <p>' + profileDescriptionShort + '</p>'
    profileHeaderStr += loginButton
    profileHeaderStr += '  </div>'
    profileHeaderStr += '</div>'

    profileStr = \
        linkToTimelineStart + profileHeaderStr + \
        linkToTimelineEnd + donateSection
    profileStr += '<div class="container" id="buttonheader">\n'
    profileStr += '  <center>'
    profileStr += \
        '    <a href="' + usersPath + '#buttonheader"><button class="' + \
        postsButton + '"><span>' + translate['Posts'] + \
        ' </span></button></a>'
    profileStr += \
        '    <a href="' + usersPath + '/following#buttonheader">' + \
        '<button class="' + followingButton + '"><span>' + \
        translate['Following'] + ' </span></button></a>'
    profileStr += \
        '    <a href="' + usersPath + '/followers#buttonheader">' + \
        '<button class="' + followersButton + \
        '"><span>' + translate['Followers'] + ' </span></button></a>'
    profileStr += \
        '    <a href="' + usersPath + '/roles#buttonheader">' + \
        '<button class="' + rolesButton + '"><span>' + translate['Roles'] + \
        ' </span></button></a>'
    profileStr += \
        '    <a href="' + usersPath + '/skills#buttonheader">' + \
        '<button class="' + skillsButton + '"><span>' + \
        translate['Skills'] + ' </span></button></a>'
    profileStr += \
        '    <a href="' + usersPath + '/shares#buttonheader">' + \
        '<button class="' + sharesButton + '"><span>' + \
        translate['Shares'] + ' </span></button></a>'
    profileStr += editProfileStr + logoutStr
    profileStr += '  </center>'
    profileStr += '</div>'

    profileStr += followApprovalsSection

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = \
            cssFile.read().replace('image.png',
                                   profileJson['image']['url'])

        licenseStr = \
            '<a href="https://gitlab.com/bashrc2/epicyon">' + \
            '<img loading="lazy" class="license" alt="' + \
            translate['Get the source code'] + '" title="' + \
            translate['Get the source code'] + '" src="/icons/agpl.png" /></a>'

        if selected == 'posts':
            profileStr += \
                htmlProfilePosts(recentPostsCache, maxRecentPosts,
                                 translate,
                                 baseDir, httpPrefix, authorized,
                                 nickname, domain, port,
                                 session, wfRequest, personCache,
                                 projectVersion,
                                 YTReplacementDomain) + licenseStr
        if selected == 'following':
            profileStr += \
                htmlProfileFollowing(translate, baseDir, httpPrefix,
                                     authorized, nickname,
                                     domain, port, session,
                                     wfRequest, personCache, extraJson,
                                     projectVersion, ["unfollow"], selected,
                                     usersPath, pageNumber, maxItemsPerPage)
        if selected == 'followers':
            profileStr += \
                htmlProfileFollowing(translate, baseDir, httpPrefix,
                                     authorized, nickname,
                                     domain, port, session,
                                     wfRequest, personCache, extraJson,
                                     projectVersion, ["block"],
                                     selected, usersPath, pageNumber,
                                     maxItemsPerPage)
        if selected == 'roles':
            profileStr += \
                htmlProfileRoles(translate, nickname, domainFull, extraJson)
        if selected == 'skills':
            profileStr += \
                htmlProfileSkills(translate, nickname, domainFull, extraJson)
        if selected == 'shares':
            profileStr += \
                htmlProfileShares(actor, translate,
                                  nickname, domainFull,
                                  extraJson) + licenseStr
        profileStr = \
            htmlHeader(cssFilename, profileStyle) + profileStr + htmlFooter()
    return profileStr


def individualFollowAsHtml(translate: {},
                           baseDir: str, session, wfRequest: {},
                           personCache: {}, domain: str,
                           followUrl: str,
                           authorized: bool,
                           actorNickname: str,
                           httpPrefix: str,
                           projectVersion: str,
                           buttons=[]) -> str:
    """An individual follow entry on the profile screen
    """
    nickname = getNicknameFromActor(followUrl)
    domain, port = getDomainFromActor(followUrl)
    titleStr = '@' + nickname + '@' + domain
    avatarUrl = getPersonAvatarUrl(baseDir, followUrl, personCache, True)
    if not avatarUrl:
        avatarUrl = followUrl + '/avatar.png'
    if domain not in followUrl:
        (inboxUrl, pubKeyId, pubKey,
         fromPersonId, sharedInbox,
         avatarUrl2, displayName) = getPersonBox(baseDir, session, wfRequest,
                                                 personCache, projectVersion,
                                                 httpPrefix, nickname,
                                                 domain, 'outbox')
        if avatarUrl2:
            avatarUrl = avatarUrl2
        if displayName:
            titleStr = displayName + ' ' + titleStr

    buttonsStr = ''
    if authorized:
        for b in buttons:
            if b == 'block':
                buttonsStr += \
                    '<a href="/users/' + actorNickname + \
                    '?options=' + followUrl + \
                    ';1;' + avatarUrl + '"><button class="buttonunfollow">' + \
                    translate['Block'] + '</button></a>\n'
            if b == 'unfollow':
                buttonsStr += \
                    '<a href="/users/' + actorNickname + \
                    '?options=' + followUrl + \
                    ';1;' + avatarUrl + '"><button class="buttonunfollow">' + \
                    translate['Unfollow'] + '</button></a>\n'

    resultStr = '<div class="container">\n'
    resultStr += \
        '<a href="/users/' + actorNickname + '?options=' + \
        followUrl + ';1;' + avatarUrl + '">\n'
    resultStr += '<p><img loading="lazy" src="' + avatarUrl + '" alt=" ">'
    resultStr += titleStr + '</a>' + buttonsStr + '</p>\n'
    resultStr += '</div>\n'
    return resultStr


def addEmbeddedAudio(translate: {}, content: str) -> str:
    """Adds embedded audio for mp3/ogg
    """
    if not ('.mp3' in content or '.ogg' in content):
        return content

    if '<audio ' in content:
        return content

    extension = '.mp3'
    if '.ogg' in content:
        extension = '.ogg'

    words = content.strip('\n').split(' ')
    for w in words:
        if extension not in w:
            continue
        w = w.replace('href="', '').replace('">', '')
        if w.endswith('.'):
            w = w[:-1]
        if w.endswith('"'):
            w = w[:-1]
        if w.endswith(';'):
            w = w[:-1]
        if w.endswith(':'):
            w = w[:-1]
        if not w.endswith(extension):
            continue

        if not (w.startswith('http') or w.startswith('dat:') or
                w.startswith('hyper:') or w.startswith('i2p:') or
                w.startswith('gnunet:') or
                '/' in w):
            continue
        url = w
        content += '<center>\n<audio controls>\n'
        content += \
            '<source src="' + url + '" type="audio/' + \
            extension.replace('.', '') + '">'
        content += \
            translate['Your browser does not support the audio element.']
        content += '</audio>\n</center>\n'
    return content


def addEmbeddedVideo(translate: {}, content: str,
                     width=400, height=300) -> str:
    """Adds embedded video for mp4/webm/ogv
    """
    if not ('.mp4' in content or '.webm' in content or '.ogv' in content):
        return content

    if '<video ' in content:
        return content

    extension = '.mp4'
    if '.webm' in content:
        extension = '.webm'
    elif '.ogv' in content:
        extension = '.ogv'

    words = content.strip('\n').split(' ')
    for w in words:
        if extension not in w:
            continue
        w = w.replace('href="', '').replace('">', '')
        if w.endswith('.'):
            w = w[:-1]
        if w.endswith('"'):
            w = w[:-1]
        if w.endswith(';'):
            w = w[:-1]
        if w.endswith(':'):
            w = w[:-1]
        if not w.endswith(extension):
            continue
        if not (w.startswith('http') or w.startswith('dat:') or
                w.startswith('hyper:') or w.startswith('i2p:') or
                w.startswith('gnunet:') or
                '/' in w):
            continue
        url = w
        content += \
            '<center>\n<video width="' + str(width) + '" height="' + \
            str(height) + '" controls>\n'
        content += \
            '<source src="' + url + '" type="video/' + \
            extension.replace('.', '') + '">\n'
        content += \
            translate['Your browser does not support the video element.']
        content += '</video>\n</center>\n'
    return content


def addEmbeddedVideoFromSites(translate: {}, content: str,
                              width=400, height=300) -> str:
    """Adds embedded videos
    """
    if '>vimeo.com/' in content:
        url = content.split('>vimeo.com/')[1]
        if '<' in url:
            url = url.split('<')[0]
            content = \
                content + "<center>\n<iframe loading=\"lazy\" " + \
                "src=\"https://player.vimeo.com/video/" + \
                url + "\" width=\"" + str(width) + \
                "\" height=\"" + str(height) + \
                "\" frameborder=\"0\" allow=\"autoplay; " + \
                "fullscreen\" allowfullscreen></iframe>\n</center>\n"
            return content

    videoSite = 'https://www.youtube.com'
    if '"' + videoSite in content:
        url = content.split('"' + videoSite)[1]
        if '"' in url:
            url = url.split('"')[0].replace('/watch?v=', '/embed/')
            if '&' in url:
                url = url.split('&')[0]
            content = \
                content + "<center>\n<iframe loading=\"lazy\" src=\"" + \
                videoSite + url + "\" width=\"" + str(width) + \
                "\" height=\"" + str(height) + \
                "\" frameborder=\"0\" allow=\"autoplay; fullscreen\" " + \
                "allowfullscreen></iframe>\n</center>\n"
            return content

    invidiousSites = ('https://invidio.us',
                      'https://invidious.snopyta.org',
                      'http://c7hqkpkpemu6e7emz5b4vy' +
                      'z7idjgdvgaaa3dyimmeojqbgpea3xqjoid.onion',
                      'http://axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4' +
                      'bzzsg2ii4fv2iid.onion')
    for videoSite in invidiousSites:
        if '"' + videoSite in content:
            url = content.split('"' + videoSite)[1]
            if '"' in url:
                url = url.split('"')[0].replace('/watch?v=', '/embed/')
                if '&' in url:
                    url = url.split('&')[0]
                content = \
                    content + "<center>\n<iframe loading=\"lazy\" src=\"" + \
                    videoSite + url + "\" width=\"" + \
                    str(width) + "\" height=\"" + str(height) + \
                    "\" frameborder=\"0\" allow=\"autoplay; fullscreen\" " + \
                    "allowfullscreen></iframe>\n</center>\n"
                return content

    videoSite = 'https://media.ccc.de'
    if '"' + videoSite in content:
        url = content.split('"' + videoSite)[1]
        if '"' in url:
            url = url.split('"')[0]
            if not url.endswith('/oembed'):
                url = url + '/oembed'
            content = \
                content + "<center>\n<iframe loading=\"lazy\" src=\"" + \
                videoSite + url + "\" width=\"" + \
                str(width) + "\" height=\"" + str(height) + \
                "\" frameborder=\"0\" allow=\"fullscreen\" " + \
                "allowfullscreen></iframe>\n</center>\n"
            return content

    if '"https://' in content:
        # A selection of the current larger peertube sites, mostly
        # French and German language
        # These have been chosen based on reported numbers of users
        # and the content of each has not been reviewed, so mileage could vary
        peerTubeSites = ('peertube.mastodon.host', 'open.tube', 'share.tube',
                         'tube.tr4sk.me', 'videos.elbinario.net',
                         'hkvideo.live',
                         'peertube.snargol.com', 'tube.22decembre.eu',
                         'tube.fabrigli.fr', 'libretube.net', 'libre.video',
                         'peertube.linuxrocks.online', 'spacepub.space',
                         'video.ploud.jp', 'video.omniatv.com',
                         'peertube.servebeer.com',
                         'tube.tchncs.de', 'tubee.fr', 'video.alternanet.fr',
                         'devtube.dev-wiki.de', 'video.samedi.pm',
                         'video.irem.univ-paris-diderot.fr',
                         'peertube.openstreetmap.fr', 'video.antopie.org',
                         'scitech.video', 'tube.4aem.com', 'video.ploud.fr',
                         'peervideo.net', 'video.valme.io',
                         'videos.pair2jeux.tube',
                         'vault.mle.party', 'hostyour.tv',
                         'diode.zone', 'visionon.tv',
                         'artitube.artifaille.fr', 'peertube.fr',
                         'peertube.live',
                         'tube.ac-lyon.fr', 'www.yiny.org', 'betamax.video',
                         'tube.piweb.be', 'pe.ertu.be', 'peertube.social',
                         'videos.lescommuns.org', 'peertube.nogafa.org',
                         'skeptikon.fr', 'video.tedomum.net',
                         'tube.p2p.legal',
                         'sikke.fi', 'exode.me', 'peertube.video')
        for site in peerTubeSites:
            if '"https://' + site in content:
                url = content.split('"https://' + site)[1]
                if '"' in url:
                    url = url.split('"')[0].replace('/watch/', '/embed/')
                    content = \
                        content + "<center>\n<iframe loading=\"lazy\" " + \
                        "sandbox=\"allow-same-origin " + \
                        "allow-scripts\" src=\"https://" + \
                        site + url + "\" width=\"" + str(width) + \
                        "\" height=\"" + str(height) + \
                        "\" frameborder=\"0\" allow=\"autoplay; " + \
                        "fullscreen\" allowfullscreen></iframe>\n</center>\n"
                    return content
    return content


def addEmbeddedElements(translate: {}, content: str) -> str:
    """Adds embedded elements for various media types
    """
    content = addEmbeddedVideoFromSites(translate, content)
    content = addEmbeddedAudio(translate, content)
    return addEmbeddedVideo(translate, content)


def followerApprovalActive(baseDir: str, nickname: str, domain: str) -> bool:
    """Returns true if the given account requires follower approval
    """
    manuallyApprovesFollowers = False
    actorFilename = baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    if os.path.isfile(actorFilename):
        actorJson = loadJson(actorFilename)
        if actorJson:
            if actorJson.get('manuallyApprovesFollowers'):
                manuallyApprovesFollowers = \
                    actorJson['manuallyApprovesFollowers']
    return manuallyApprovesFollowers


def insertQuestion(baseDir: str, translate: {},
                   nickname: str, domain: str, port: int,
                   content: str,
                   postJsonObject: {}, pageNumber: int) -> str:
    """ Inserts question selection into a post
    """
    if not isQuestion(postJsonObject):
        return content
    if len(postJsonObject['object']['oneOf']) == 0:
        return content
    messageId = removeIdEnding(postJsonObject['id'])
    if '#' in messageId:
        messageId = messageId.split('#', 1)[0]
    pageNumberStr = ''
    if pageNumber:
        pageNumberStr = '?page=' + str(pageNumber)

    votesFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/questions.txt'

    showQuestionResults = False
    if os.path.isfile(votesFilename):
        if messageId in open(votesFilename).read():
            showQuestionResults = True

    if not showQuestionResults:
        # show the question options
        content += '<div class="question">'
        content += \
            '<form method="POST" action="/users/' + \
            nickname + '/question' + pageNumberStr + '">\n'
        content += \
            '<input type="hidden" name="messageId" value="' + \
            messageId + '">\n<br>\n'
        for choice in postJsonObject['object']['oneOf']:
            if not choice.get('type'):
                continue
            if not choice.get('name'):
                continue
            content += \
                '<input type="radio" name="answer" value="' + \
                choice['name'] + '"> ' + choice['name'] + '<br><br>\n'
        content += \
            '<input type="submit" value="' + \
            translate['Vote'] + '" class="vote"><br><br>\n'
        content += '</form>\n</div>\n'
    else:
        # show the responses to a question
        content += '<div class="questionresult">\n'

        # get the maximum number of votes
        maxVotes = 1
        for questionOption in postJsonObject['object']['oneOf']:
            if not questionOption.get('name'):
                continue
            if not questionOption.get('replies'):
                continue
            votes = 0
            try:
                votes = int(questionOption['replies']['totalItems'])
            except BaseException:
                pass
            if votes > maxVotes:
                maxVotes = int(votes+1)

        # show the votes as sliders
        questionCtr = 1
        for questionOption in postJsonObject['object']['oneOf']:
            if not questionOption.get('name'):
                continue
            if not questionOption.get('replies'):
                continue
            votes = 0
            try:
                votes = int(questionOption['replies']['totalItems'])
            except BaseException:
                pass
            votesPercent = str(int(votes * 100 / maxVotes))
            content += \
                '<p><input type="text" title="' + str(votes) + \
                '" name="skillName' + str(questionCtr) + \
                '" value="' + questionOption['name'] + \
                ' (' + str(votes) + ')" style="width:40%">\n'
            content += \
                '<input type="range" min="1" max="100" ' + \
                'class="slider" title="' + \
                str(votes) + '" name="skillValue' + str(questionCtr) + \
                '" value="' + votesPercent + '"></p>\n'
            questionCtr += 1
        content += '</div>\n'
    return content


def addEmojiToDisplayName(baseDir: str, httpPrefix: str,
                          nickname: str, domain: str,
                          displayName: str, inProfileName: bool) -> str:
    """Adds emoji icons to display names on individual posts
    """
    if ':' not in displayName:
        return displayName

    displayName = displayName.replace('<p>', '').replace('</p>', '')
    emojiTags = {}
    print('TAG: displayName before tags: ' + displayName)
    displayName = \
        addHtmlTags(baseDir, httpPrefix,
                    nickname, domain, displayName, [], emojiTags)
    displayName = displayName.replace('<p>', '').replace('</p>', '')
    print('TAG: displayName after tags: ' + displayName)
    # convert the emoji dictionary to a list
    emojiTagsList = []
    for tagName, tag in emojiTags.items():
        emojiTagsList.append(tag)
    print('TAG: emoji tags list: ' + str(emojiTagsList))
    if not inProfileName:
        displayName = \
            replaceEmojiFromTags(displayName, emojiTagsList, 'post header')
    else:
        displayName = \
            replaceEmojiFromTags(displayName, emojiTagsList, 'profile')
    print('TAG: displayName after tags 2: ' + displayName)

    # remove any stray emoji
    while ':' in displayName:
        if '://' in displayName:
            break
        emojiStr = displayName.split(':')[1]
        prevDisplayName = displayName
        displayName = displayName.replace(':' + emojiStr + ':', '').strip()
        if prevDisplayName == displayName:
            break
        print('TAG: displayName after tags 3: ' + displayName)
    print('TAG: displayName after tag replacements: ' + displayName)

    return displayName


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


def saveIndividualPostAsHtmlToCache(baseDir: str,
                                    nickname: str, domain: str,
                                    postJsonObject: {},
                                    postHtml: str) -> bool:
    """Saves the given html for a post to a cache file
    This is so that it can be quickly reloaded on subsequent
    refresh of the timeline
    """
    htmlPostCacheDir = \
        getCachedPostDirectory(baseDir, nickname, domain)
    cachedPostFilename = \
        getCachedPostFilename(baseDir, nickname, domain, postJsonObject)

    # create the cache directory if needed
    if not os.path.isdir(htmlPostCacheDir):
        os.mkdir(htmlPostCacheDir)

    try:
        with open(cachedPostFilename, 'w+') as fp:
            fp.write(postHtml)
            return True
    except Exception as e:
        print('ERROR: saving post to cache ' + str(e))
    return False


def preparePostFromHtmlCache(postHtml: str, boxName: str,
                             pageNumber: int) -> str:
    """Sets the page number on a cached html post
    """
    # if on the bookmarks timeline then remain there
    if boxName == 'tlbookmarks' or boxName == 'bookmarks':
        postHtml = postHtml.replace('?tl=inbox', '?tl=tlbookmarks')
        if '?page=' in postHtml:
            pageNumberStr = postHtml.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            postHtml = postHtml.replace('?page=' + pageNumberStr, '?page=-999')

    withPageNumber = postHtml.replace(';-999;', ';' + str(pageNumber) + ';')
    withPageNumber = withPageNumber.replace('?page=-999',
                                            '?page=' + str(pageNumber))
    return withPageNumber


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
           mediaType == 'image/gif':
            if attach['url'].endswith('.png') or \
               attach['url'].endswith('.jpg') or \
               attach['url'].endswith('.jpeg') or \
               attach['url'].endswith('.webp') or \
               attach['url'].endswith('.avif') or \
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


def individualPostAsHtml(allowDownloads: bool,
                         recentPostsCache: {}, maxRecentPosts: int,
                         iconsDir: str, translate: {},
                         pageNumber: int, baseDir: str,
                         session, wfRequest: {}, personCache: {},
                         nickname: str, domain: str, port: int,
                         postJsonObject: {},
                         avatarUrl: str, showAvatarOptions: bool,
                         allowDeletion: bool,
                         httpPrefix: str, projectVersion: str,
                         boxName: str, YTReplacementDomain: str,
                         showRepeats=True,
                         showIcons=False,
                         manuallyApprovesFollowers=False,
                         showPublicOnly=False,
                         storeToCache=True) -> str:
    """ Shows a single post as html
    """
    if not postJsonObject:
        return ''

    # benchmark
    postStartTime = time.time()

    postActor = postJsonObject['actor']

    # ZZZzzz
    if isPersonSnoozed(baseDir, nickname, domain, postActor):
        return ''

    # benchmark 1
    timeDiff = int((time.time() - postStartTime) * 1000)
    if timeDiff > 100:
        print('TIMING INDIV ' + boxName + ' 1 = ' + str(timeDiff))

    avatarPosition = ''
    messageId = ''
    if postJsonObject.get('id'):
        messageId = removeIdEnding(postJsonObject['id'])

    # benchmark 2
    timeDiff = int((time.time() - postStartTime) * 1000)
    if timeDiff > 100:
        print('TIMING INDIV ' + boxName + ' 2 = ' + str(timeDiff))

    messageIdStr = ''
    if messageId:
        messageIdStr = ';' + messageId

    fullDomain = domain
    if port:
        if port != 80 and port != 443:
            if ':' not in domain:
                fullDomain = domain + ':' + str(port)

    pageNumberParam = ''
    if pageNumber:
        pageNumberParam = '?page=' + str(pageNumber)

    if (not showPublicOnly and
        (storeToCache or boxName == 'bookmarks' or
         boxName == 'tlbookmarks') and
       boxName != 'tlmedia'):
        # update avatar if needed
        if not avatarUrl:
            avatarUrl = \
                getPersonAvatarUrl(baseDir, postActor, personCache,
                                   allowDownloads)

            # benchmark 2.1
            if not allowDownloads:
                timeDiff = int((time.time() - postStartTime) * 1000)
                if timeDiff > 100:
                    print('TIMING INDIV ' + boxName +
                          ' 2.1 = ' + str(timeDiff))

        updateAvatarImageCache(session, baseDir, httpPrefix,
                               postActor, avatarUrl, personCache,
                               allowDownloads)

        # benchmark 2.2
        if not allowDownloads:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName +
                      ' 2.2 = ' + str(timeDiff))

        postHtml = \
            loadIndividualPostAsHtmlFromCache(baseDir, nickname, domain,
                                              postJsonObject)
        if postHtml:
            postHtml = preparePostFromHtmlCache(postHtml, boxName, pageNumber)
            updateRecentPostsCache(recentPostsCache, maxRecentPosts,
                                   postJsonObject, postHtml)
            # benchmark 3
            if not allowDownloads:
                timeDiff = int((time.time() - postStartTime) * 1000)
                if timeDiff > 100:
                    print('TIMING INDIV ' + boxName +
                          ' 3 = ' + str(timeDiff))
            return postHtml

    # benchmark 4
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 4 = ' + str(timeDiff))

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

    # benchmark 5
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 5 = ' + str(timeDiff))

    if not avatarUrl:
        avatarUrl = postActor + '/avatar.png'

    if fullDomain not in postActor:
        (inboxUrl, pubKeyId, pubKey,
         fromPersonId, sharedInbox,
         avatarUrl2, displayName) = getPersonBox(baseDir, session, wfRequest,
                                                 personCache,
                                                 projectVersion, httpPrefix,
                                                 nickname, domain, 'outbox')
        # benchmark 6
        if not allowDownloads:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName + ' 6 = ' + str(timeDiff))

        if avatarUrl2:
            avatarUrl = avatarUrl2
        if displayName:
            if ':' in displayName:
                displayName = \
                    addEmojiToDisplayName(baseDir, httpPrefix,
                                          nickname, domain,
                                          displayName, False)

    # benchmark 7
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 7 = ' + str(timeDiff))

    avatarLink = '        <a class="imageAnchor" href="' + postActor + '">'
    avatarLink += \
        '    <img loading="lazy" src="' + avatarUrl + '" title="' + \
        translate['Show profile'] + '" alt=" "' + avatarPosition + '/></a>\n'

    if showAvatarOptions and \
       fullDomain + '/users/' + nickname not in postActor:
        avatarLink = \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?options=' + postActor + \
            ';' + str(pageNumber) + ';' + avatarUrl + messageIdStr + '">\n'
        avatarLink += \
            '        <img loading="lazy" title="' + \
            translate['Show options for this person'] + \
            '" src="' + avatarUrl + '" ' + avatarPosition + '/></a>\n'
    avatarImageInPost = \
        '      <div class="timeline-avatar">' + avatarLink.strip() + '</div>\n'

    # don't create new html within the bookmarks timeline
    # it should already have been created for the inbox
    if boxName == 'tlbookmarks' or boxName == 'bookmarks':
        return ''

    timelinePostBookmark = removeIdEnding(postJsonObject['id'])
    timelinePostBookmark = timelinePostBookmark.replace('://', '-')
    timelinePostBookmark = timelinePostBookmark.replace('/', '-')

    # If this is the inbox timeline then don't show the repeat icon on any DMs
    showRepeatIcon = showRepeats
    isPublicRepeat = False
    showDMicon = False
    if showRepeats:
        if isDM(postJsonObject):
            showDMicon = True
            showRepeatIcon = False
        else:
            if not isPublicPost(postJsonObject):
                isPublicRepeat = True

    titleStr = ''
    galleryStr = ''
    isAnnounced = False
    if postJsonObject['type'] == 'Announce':
        postJsonAnnounce = \
            downloadAnnounce(session, baseDir, httpPrefix,
                             nickname, domain, postJsonObject,
                             projectVersion, translate,
                             YTReplacementDomain)
        if not postJsonAnnounce:
            return ''
        postJsonObject = postJsonAnnounce
        isAnnounced = True

    # benchmark 8
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 8 = ' + str(timeDiff))

    if not isinstance(postJsonObject['object'], dict):
        return ''

    # if this post should be public then check its recipients
    if showPublicOnly:
        if not postContainsPublic(postJsonObject):
            return ''

    isModerationPost = False
    if postJsonObject['object'].get('moderationStatus'):
        isModerationPost = True
    containerClass = 'container'
    containerClassIcons = 'containericons'
    timeClass = 'time-right'
    actorNickname = getNicknameFromActor(postActor)
    if not actorNickname:
        # single user instance
        actorNickname = 'dev'
    actorDomain, actorPort = getDomainFromActor(postActor)

    displayName = getDisplayName(baseDir, postActor, personCache)
    if displayName:
        if ':' in displayName:
            displayName = \
                addEmojiToDisplayName(baseDir, httpPrefix,
                                      nickname, domain,
                                      displayName, False)
        titleStr += \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?options=' + postActor + \
            ';' + str(pageNumber) + ';' + avatarUrl + messageIdStr + \
            '">' + displayName + '</a>\n'
    else:
        if not messageId:
            # pprint(postJsonObject)
            print('ERROR: no messageId')
        if not actorNickname:
            # pprint(postJsonObject)
            print('ERROR: no actorNickname')
        if not actorDomain:
            # pprint(postJsonObject)
            print('ERROR: no actorDomain')
        titleStr += \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?options=' + postActor + \
            ';' + str(pageNumber) + ';' + avatarUrl + messageIdStr + \
            '">@' + actorNickname + '@' + actorDomain + '</a>\n'

    # benchmark 9
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 9 = ' + str(timeDiff))

    # Show a DM icon for DMs in the inbox timeline
    if showDMicon:
        titleStr = \
            titleStr + ' <img loading="lazy" src="/' + \
            iconsDir + '/dm.png" class="DMicon"/>\n'

    replyStr = ''
    # check if replying is permitted
    commentsEnabled = True
    if 'commentsEnabled' in postJsonObject['object']:
        if postJsonObject['object']['commentsEnabled'] is False:
            commentsEnabled = False
    if showIcons and commentsEnabled:
        # reply is permitted - create reply icon
        replyToLink = postJsonObject['object']['id']
        if postJsonObject['object'].get('attributedTo'):
            if isinstance(postJsonObject['object']['attributedTo'], str):
                replyToLink += \
                    '?mention=' + postJsonObject['object']['attributedTo']
        if postJsonObject['object'].get('content'):
            mentionedActors = \
                getMentionsFromHtml(postJsonObject['object']['content'])
            if mentionedActors:
                for actorUrl in mentionedActors:
                    if '?mention=' + actorUrl not in replyToLink:
                        replyToLink += '?mention=' + actorUrl
                        if len(replyToLink) > 500:
                            break
        replyToLink += pageNumberParam

        replyStr = ''
        if isPublicRepeat:
            replyStr += \
                '        <a class="imageAnchor" href="/users/' + \
                nickname + '?replyto=' + replyToLink + \
                '?actor=' + postJsonObject['actor'] + \
                '" title="' + translate['Reply to this post'] + '">\n'
        else:
            if isDM(postJsonObject):
                replyStr += \
                    '        ' + \
                    '<a class="imageAnchor" href="/users/' + nickname + \
                    '?replydm=' + replyToLink + \
                    '?actor=' + postJsonObject['actor'] + \
                    '" title="' + translate['Reply to this post'] + '">\n'
            else:
                replyStr += \
                    '        ' + \
                    '<a class="imageAnchor" href="/users/' + nickname + \
                    '?replyfollowers=' + replyToLink + \
                    '?actor=' + postJsonObject['actor'] + \
                    '" title="' + translate['Reply to this post'] + '">\n'

        replyStr += \
            '        ' + \
            '<img loading="lazy" title="' + \
            translate['Reply to this post'] + '" alt="' + \
            translate['Reply to this post'] + \
            ' |" src="/' + iconsDir + '/reply.png"/></a>\n'

    # benchmark 10
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 10 = ' + str(timeDiff))

    isEvent = isEventPost(postJsonObject)

    # benchmark 11
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 11 = ' + str(timeDiff))

    editStr = ''
    if fullDomain + '/users/' + nickname in postJsonObject['actor']:
        if '/statuses/' in postJsonObject['object']['id']:
            if isBlogPost(postJsonObject):
                if not isNewsPost(postJsonObject):
                    blogPostId = postJsonObject['object']['id']
                    editStr += \
                        '        ' + \
                        '<a class="imageAnchor" href="/users/' + \
                        nickname + \
                        '/tlblogs?editblogpost=' + \
                        blogPostId.split('/statuses/')[1] + \
                        '?actor=' + actorNickname + \
                        '" title="' + translate['Edit blog post'] + '">' + \
                        '<img loading="lazy" title="' + \
                        translate['Edit blog post'] + '" alt="' + \
                        translate['Edit blog post'] + \
                        ' |" src="/' + iconsDir + '/edit.png"/></a>\n'
            elif isEvent:
                eventPostId = postJsonObject['object']['id']
                editStr += \
                    '        ' + \
                    '<a class="imageAnchor" href="/users/' + nickname + \
                    '/tlblogs?editeventpost=' + \
                    eventPostId.split('/statuses/')[1] + \
                    '?actor=' + actorNickname + \
                    '" title="' + translate['Edit event'] + '">' + \
                    '<img loading="lazy" title="' + \
                    translate['Edit event'] + '" alt="' + \
                    translate['Edit event'] + \
                    ' |" src="/' + iconsDir + '/edit.png"/></a>\n'

    announceStr = ''
    if not isModerationPost and showRepeatIcon:
        # don't allow announce/repeat of your own posts
        announceIcon = 'repeat_inactive.png'
        announceLink = 'repeat'
        if not isPublicRepeat:
            announceLink = 'repeatprivate'
        announceTitle = translate['Repeat this post']
        if announcedByPerson(postJsonObject, nickname, fullDomain):
            announceIcon = 'repeat.png'
            if not isPublicRepeat:
                announceLink = 'unrepeatprivate'
            announceTitle = translate['Undo the repeat']
        announceStr = \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?' + announceLink + \
            '=' + postJsonObject['object']['id'] + pageNumberParam + \
            '?actor=' + postJsonObject['actor'] + \
            '?bm=' + timelinePostBookmark + \
            '?tl=' + boxName + '" title="' + announceTitle + '">\n'
        announceStr += \
            '          ' + \
            '<img loading="lazy" title="' + translate['Repeat this post'] + \
            '" alt="' + translate['Repeat this post'] + \
            ' |" src="/' + iconsDir + '/' + announceIcon + '"/></a>\n'

    # benchmark 12
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 12 = ' + str(timeDiff))

    # whether to show a like button
    hideLikeButtonFile = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/.hideLikeButton'
    showLikeButton = True
    if os.path.isfile(hideLikeButtonFile):
        showLikeButton = False

    likeStr = ''
    if not isModerationPost and showLikeButton:
        likeIcon = 'like_inactive.png'
        likeLink = 'like'
        likeTitle = translate['Like this post']
        likeCount = noOfLikes(postJsonObject)

        # benchmark 12.1
        if not allowDownloads:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName + ' 12.1 = ' + str(timeDiff))

        likeCountStr = ''
        if likeCount > 0:
            if likeCount <= 10:
                likeCountStr = ' (' + str(likeCount) + ')'
            else:
                likeCountStr = ' (10+)'
            if likedByPerson(postJsonObject, nickname, fullDomain):
                if likeCount == 1:
                    # liked by the reader only
                    likeCountStr = ''
                likeIcon = 'like.png'
                likeLink = 'unlike'
                likeTitle = translate['Undo the like']

        # benchmark 12.2
        if not allowDownloads:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName + ' 12.2 = ' + str(timeDiff))

        likeStr = ''
        if likeCountStr:
            # show the number of likes next to icon
            likeStr += '<label class="likesCount">'
            likeStr += likeCountStr.replace('(', '').replace(')', '').strip()
            likeStr += '</label>\n'
        likeStr += \
            '        <a class="imageAnchor" href="/users/' + nickname + '?' + \
            likeLink + '=' + postJsonObject['object']['id'] + \
            pageNumberParam + \
            '?actor=' + postJsonObject['actor'] + \
            '?bm=' + timelinePostBookmark + \
            '?tl=' + boxName + '" title="' + \
            likeTitle + likeCountStr + '">\n'
        likeStr += \
            '          ' + \
            '<img loading="lazy" title="' + likeTitle + likeCountStr + \
            '" alt="' + likeTitle + \
            ' |" src="/' + iconsDir + '/' + likeIcon + '"/></a>\n'

    # benchmark 12.5
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 12.5 = ' + str(timeDiff))

    bookmarkStr = ''
    if not isModerationPost:
        bookmarkIcon = 'bookmark_inactive.png'
        bookmarkLink = 'bookmark'
        bookmarkTitle = translate['Bookmark this post']
        if bookmarkedByPerson(postJsonObject, nickname, fullDomain):
            bookmarkIcon = 'bookmark.png'
            bookmarkLink = 'unbookmark'
            bookmarkTitle = translate['Undo the bookmark']
        # benchmark 12.6
        if not allowDownloads:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName + ' 12.6 = ' + str(timeDiff))
        bookmarkStr = \
            '        <a class="imageAnchor" href="/users/' + nickname + '?' + \
            bookmarkLink + '=' + postJsonObject['object']['id'] + \
            pageNumberParam + \
            '?actor=' + postJsonObject['actor'] + \
            '?bm=' + timelinePostBookmark + \
            '?tl=' + boxName + '" title="' + bookmarkTitle + '">\n'
        bookmarkStr += \
            '        ' + \
            '<img loading="lazy" title="' + bookmarkTitle + '" alt="' + \
            bookmarkTitle + ' |" src="/' + iconsDir + \
            '/' + bookmarkIcon + '"/></a>\n'

    # benchmark 12.9
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 12.9 = ' + str(timeDiff))

    isMuted = postIsMuted(baseDir, nickname, domain, postJsonObject, messageId)

    # benchmark 13
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 13 = ' + str(timeDiff))

    deleteStr = ''
    muteStr = ''
    if (allowDeletion or
        ('/' + fullDomain + '/' in postActor and
         messageId.startswith(postActor))):
        if '/users/' + nickname + '/' in messageId:
            if not isNewsPost(postJsonObject):
                deleteStr = \
                    '        <a class="imageAnchor" href="/users/' + \
                    nickname + \
                    '?delete=' + messageId + pageNumberParam + \
                    '" title="' + translate['Delete this post'] + '">\n'
                deleteStr += \
                    '          ' + \
                    '<img loading="lazy" alt="' + \
                    translate['Delete this post'] + \
                    ' |" title="' + translate['Delete this post'] + \
                    '" src="/' + iconsDir + '/delete.png"/></a>\n'
    else:
        if not isMuted:
            muteStr = \
                '        <a class="imageAnchor" href="/users/' + nickname + \
                '?mute=' + messageId + pageNumberParam + '?tl=' + boxName + \
                '?bm=' + timelinePostBookmark + \
                '" title="' + translate['Mute this post'] + '">\n'
            muteStr += \
                '          ' + \
                '<img loading="lazy" alt="' + \
                translate['Mute this post'] + \
                ' |" title="' + translate['Mute this post'] + \
                '" src="/' + iconsDir + '/mute.png"/></a>\n'
        else:
            muteStr = \
                '        <a class="imageAnchor" href="/users/' + \
                nickname + '?unmute=' + messageId + \
                pageNumberParam + '?tl=' + boxName + '?bm=' + \
                timelinePostBookmark + '" title="' + \
                translate['Undo mute'] + '">\n'
            muteStr += \
                '          ' + \
                '<img loading="lazy" alt="' + translate['Undo mute'] + \
                ' |" title="' + translate['Undo mute'] + \
                '" src="/' + iconsDir+'/unmute.png"/></a>\n'

    # benchmark 13.1
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 13.1 = ' + str(timeDiff))

    replyAvatarImageInPost = ''
    if showRepeatIcon:
        if isAnnounced:
            if postJsonObject['object'].get('attributedTo'):
                attributedTo = ''
                if isinstance(postJsonObject['object']['attributedTo'], str):
                    attributedTo = postJsonObject['object']['attributedTo']
                if attributedTo.startswith(postActor):
                    titleStr += \
                        '        <img loading="lazy" title="' + \
                        translate['announces'] + \
                        '" alt="' + translate['announces'] + \
                        '" src="/' + iconsDir + \
                        '/repeat_inactive.png" class="announceOrReply"/>\n'
                else:
                    # benchmark 13.2
                    if not allowDownloads:
                        timeDiff = int((time.time() - postStartTime) * 1000)
                        if timeDiff > 100:
                            print('TIMING INDIV ' + boxName +
                                  ' 13.2 = ' + str(timeDiff))
                    announceNickname = None
                    if attributedTo:
                        announceNickname = getNicknameFromActor(attributedTo)
                    if announceNickname:
                        announceDomain, announcePort = \
                            getDomainFromActor(attributedTo)
                        getPersonFromCache(baseDir, attributedTo,
                                           personCache, allowDownloads)
                        announceDisplayName = \
                            getDisplayName(baseDir, attributedTo, personCache)
                        if announceDisplayName:
                            # benchmark 13.3
                            if not allowDownloads:
                                timeDiff = \
                                    int((time.time() - postStartTime) * 1000)
                                if timeDiff > 100:
                                    print('TIMING INDIV ' + boxName +
                                          ' 13.3 = ' + str(timeDiff))

                            if ':' in announceDisplayName:
                                announceDisplayName = \
                                    addEmojiToDisplayName(baseDir, httpPrefix,
                                                          nickname, domain,
                                                          announceDisplayName,
                                                          False)
                            # benchmark 13.3.1
                            if not allowDownloads:
                                timeDiff = \
                                    int((time.time() - postStartTime) * 1000)
                                if timeDiff > 100:
                                    print('TIMING INDIV ' + boxName +
                                          ' 13.3.1 = ' + str(timeDiff))

                            titleStr += \
                                '          ' + \
                                '<img loading="lazy" title="' + \
                                translate['announces'] + '" alt="' + \
                                translate['announces'] + '" src="/' + \
                                iconsDir + '/repeat_inactive.png" ' + \
                                'class="announceOrReply"/>\n' + \
                                '        <a href="' + \
                                postJsonObject['object']['id'] + '">' + \
                                announceDisplayName + '</a>\n'
                            # show avatar of person replied to
                            announceActor = \
                                postJsonObject['object']['attributedTo']
                            announceAvatarUrl = \
                                getPersonAvatarUrl(baseDir, announceActor,
                                                   personCache, allowDownloads)

                            # benchmark 13.4
                            if not allowDownloads:
                                timeDiff = \
                                    int((time.time() - postStartTime) * 1000)
                                if timeDiff > 100:
                                    print('TIMING INDIV ' + boxName +
                                          ' 13.4 = ' + str(timeDiff))

                            if announceAvatarUrl:
                                idx = 'Show options for this person'
                                replyAvatarImageInPost = \
                                    '        ' \
                                    '<div class="timeline-avatar-reply">\n' \
                                    '            <a class="imageAnchor" ' + \
                                    'href="/users/' + nickname + \
                                    '?options=' + \
                                    announceActor + ';' + str(pageNumber) + \
                                    ';' + announceAvatarUrl + \
                                    messageIdStr + '">' \
                                    '<img loading="lazy" src="' + \
                                    announceAvatarUrl + '" ' \
                                    'title="' + translate[idx] + \
                                    '" alt=" "' + avatarPosition + \
                                    '/></a>\n    </div>\n'
                        else:
                            titleStr += \
                                '    <img loading="lazy" title="' + \
                                translate['announces'] + \
                                '" alt="' + translate['announces'] + \
                                '" src="/' + iconsDir + \
                                '/repeat_inactive.png" ' + \
                                'class="announceOrReply"/>\n' + \
                                '      <a href="' + \
                                postJsonObject['object']['id'] + '">@' + \
                                announceNickname + '@' + \
                                announceDomain + '</a>\n'
                    else:
                        titleStr += \
                            '    <img loading="lazy" title="' + \
                            translate['announces'] + '" alt="' + \
                            translate['announces'] + '" src="/' + iconsDir + \
                            '/repeat_inactive.png" ' + \
                            'class="announceOrReply"/>\n' + \
                            '      <a href="' + \
                            postJsonObject['object']['id'] + \
                            '">@unattributed</a>\n'
            else:
                titleStr += \
                    '    ' + \
                    '<img loading="lazy" title="' + translate['announces'] + \
                    '" alt="' + translate['announces'] + \
                    '" src="/' + iconsDir + \
                    '/repeat_inactive.png" ' + \
                    'class="announceOrReply"/>\n' + \
                    '      <a href="' + \
                    postJsonObject['object']['id'] + '">@unattributed</a>\n'
        else:
            if postJsonObject['object'].get('inReplyTo'):
                containerClassIcons = 'containericons darker'
                containerClass = 'container darker'
                if postJsonObject['object']['inReplyTo'].startswith(postActor):
                    titleStr += \
                        '    <img loading="lazy" title="' + \
                        translate['replying to themselves'] + \
                        '" alt="' + translate['replying to themselves'] + \
                        '" src="/' + iconsDir + \
                        '/reply.png" class="announceOrReply"/>\n'
                else:
                    if '/statuses/' in postJsonObject['object']['inReplyTo']:
                        inReplyTo = postJsonObject['object']['inReplyTo']
                        replyActor = inReplyTo.split('/statuses/')[0]
                        replyNickname = getNicknameFromActor(replyActor)
                        if replyNickname:
                            replyDomain, replyPort = \
                                getDomainFromActor(replyActor)
                            if replyNickname and replyDomain:
                                getPersonFromCache(baseDir, replyActor,
                                                   personCache,
                                                   allowDownloads)
                                replyDisplayName = \
                                    getDisplayName(baseDir, replyActor,
                                                   personCache)
                                if replyDisplayName:
                                    if ':' in replyDisplayName:
                                        # benchmark 13.5
                                        if not allowDownloads:
                                            timeDiff = \
                                                int((time.time() -
                                                     postStartTime) * 1000)
                                            if timeDiff > 100:
                                                print('TIMING INDIV ' +
                                                      boxName + ' 13.5 = ' +
                                                      str(timeDiff))
                                        repDisp = replyDisplayName
                                        replyDisplayName = \
                                            addEmojiToDisplayName(baseDir,
                                                                  httpPrefix,
                                                                  nickname,
                                                                  domain,
                                                                  repDisp,
                                                                  False)
                                        # benchmark 13.6
                                        if not allowDownloads:
                                            timeDiff = \
                                                int((time.time() -
                                                     postStartTime) * 1000)
                                            if timeDiff > 100:
                                                print('TIMING INDIV ' +
                                                      boxName + ' 13.6 = ' +
                                                      str(timeDiff))
                                    titleStr += \
                                        '        ' + \
                                        '<img loading="lazy" title="' + \
                                        translate['replying to'] + \
                                        '" alt="' + \
                                        translate['replying to'] + \
                                        '" src="/' + \
                                        iconsDir + '/reply.png" ' + \
                                        'class="announceOrReply"/>\n' + \
                                        '        ' + \
                                        '<a href="' + inReplyTo + \
                                        '">' + replyDisplayName + '</a>\n'

                                    # benchmark 13.7
                                    if not allowDownloads:
                                        timeDiff = int((time.time() -
                                                        postStartTime) * 1000)
                                        if timeDiff > 100:
                                            print('TIMING INDIV ' + boxName +
                                                  ' 13.7 = ' + str(timeDiff))

                                    # show avatar of person replied to
                                    replyAvatarUrl = \
                                        getPersonAvatarUrl(baseDir,
                                                           replyActor,
                                                           personCache,
                                                           allowDownloads)

                                    # benchmark 13.8
                                    if not allowDownloads:
                                        timeDiff = int((time.time() -
                                                        postStartTime) * 1000)
                                        if timeDiff > 100:
                                            print('TIMING INDIV ' + boxName +
                                                  ' 13.8 = ' + str(timeDiff))

                                    if replyAvatarUrl:
                                        replyAvatarImageInPost = \
                                            '        <div class=' + \
                                            '"timeline-avatar-reply">\n'
                                        replyAvatarImageInPost += \
                                            '          ' + \
                                            '<a class="imageAnchor" ' + \
                                            'href="/users/' + nickname + \
                                            '?options=' + replyActor + \
                                            ';' + str(pageNumber) + ';' + \
                                            replyAvatarUrl + \
                                            messageIdStr + '">\n'
                                        replyAvatarImageInPost += \
                                            '          ' + \
                                            '<img loading="lazy" src="' + \
                                            replyAvatarUrl + '" '
                                        replyAvatarImageInPost += \
                                            'title="' + \
                                            translate['Show profile']
                                        replyAvatarImageInPost += \
                                            '" alt=" "' + \
                                            avatarPosition + '/></a>\n' + \
                                            '        </div>\n'
                                else:
                                    inReplyTo = \
                                        postJsonObject['object']['inReplyTo']
                                    titleStr += \
                                        '        ' + \
                                        '<img loading="lazy" title="' + \
                                        translate['replying to'] + \
                                        '" alt="' + \
                                        translate['replying to'] + \
                                        '" src="/' + \
                                        iconsDir + '/reply.png" ' + \
                                        'class="announceOrReply"/>\n' + \
                                        '        <a href="' + \
                                        inReplyTo + '">@' + \
                                        replyNickname + '@' + \
                                        replyDomain + '</a>\n'
                        else:
                            titleStr += \
                                '        <img loading="lazy" title="' + \
                                translate['replying to'] + \
                                '" alt="' + \
                                translate['replying to'] + \
                                '" src="/' + \
                                iconsDir + \
                                '/reply.png" class="announceOrReply"/>\n' + \
                                '        <a href="' + \
                                postJsonObject['object']['inReplyTo'] + \
                                '">@unknown</a>\n'
                    else:
                        postDomain = \
                            postJsonObject['object']['inReplyTo']
                        prefixes = getProtocolPrefixes()
                        for prefix in prefixes:
                            postDomain = postDomain.replace(prefix, '')
                        if '/' in postDomain:
                            postDomain = postDomain.split('/', 1)[0]
                        if postDomain:
                            titleStr += \
                                '        <img loading="lazy" title="' + \
                                translate['replying to'] + \
                                '" alt="' + translate['replying to'] + \
                                '" src="/' + \
                                iconsDir + '/reply.png" ' + \
                                'class="announceOrReply"/>\n' + \
                                '        <a href="' + \
                                postJsonObject['object']['inReplyTo'] + \
                                '">' + postDomain + '</a>\n'

    # benchmark 14
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 14 = ' + str(timeDiff))

    attachmentStr, galleryStr = \
        getPostAttachmentsAsHtml(postJsonObject, boxName, translate,
                                 isMuted, avatarLink.strip(),
                                 replyStr, announceStr, likeStr,
                                 bookmarkStr, deleteStr, muteStr)

    publishedStr = ''
    if postJsonObject['object'].get('published'):
        publishedStr = postJsonObject['object']['published']
        if '.' not in publishedStr:
            if '+' not in publishedStr:
                datetimeObject = \
                    datetime.strptime(publishedStr, "%Y-%m-%dT%H:%M:%SZ")
            else:
                datetimeObject = \
                    datetime.strptime(publishedStr.split('+')[0] + 'Z',
                                      "%Y-%m-%dT%H:%M:%SZ")
        else:
            publishedStr = \
                publishedStr.replace('T', ' ').split('.')[0]
            datetimeObject = parse(publishedStr)
        publishedStr = datetimeObject.strftime("%a %b %d, %H:%M")

    # benchmark 15
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 15 = ' + str(timeDiff))

    publishedLink = messageId
    # blog posts should have no /statuses/ in their link
    if isBlogPost(postJsonObject):
        # is this a post to the local domain?
        if '://' + domain in messageId:
            publishedLink = messageId.replace('/statuses/', '/')
    # if this is a local link then make it relative so that it works
    # on clearnet or onion address
    if domain + '/users/' in publishedLink or \
       domain + ':' + str(port) + '/users/' in publishedLink:
        publishedLink = '/users/' + publishedLink.split('/users/')[1]

    if not isNewsPost(postJsonObject):
        footerStr = '<a href="' + publishedLink + \
            '" class="' + timeClass + '">' + publishedStr + '</a>\n'
    else:
        footerStr = publishedStr + '\n'

    # change the background color for DMs in inbox timeline
    if showDMicon:
        containerClassIcons = 'containericons dm'
        containerClass = 'container dm'

    if showIcons:
        footerStr = '\n      <div class="' + containerClassIcons + '">\n'
        footerStr += replyStr + announceStr + likeStr + bookmarkStr + \
            deleteStr + muteStr + editStr
        footerStr += '        <a href="' + publishedLink + '" class="' + \
            timeClass + '">' + publishedStr + '</a>\n'
        footerStr += '      </div>\n'

    postIsSensitive = False
    if postJsonObject['object'].get('sensitive'):
        # sensitive posts should have a summary
        if postJsonObject['object'].get('summary'):
            postIsSensitive = postJsonObject['object']['sensitive']
        else:
            # add a generic summary if none is provided
            postJsonObject['object']['summary'] = translate['Sensitive']

    # add an extra line if there is a content warning,
    # for better vertical spacing on mobile
    if postIsSensitive:
        footerStr = '<br>' + footerStr

    if not postJsonObject['object'].get('summary'):
        postJsonObject['object']['summary'] = ''

    if postJsonObject['object'].get('cipherText'):
        postJsonObject['object']['content'] = \
            E2EEdecryptMessageFromDevice(postJsonObject['object'])

    if not postJsonObject['object'].get('content'):
        return ''

    isPatch = isGitPatch(baseDir, nickname, domain,
                         postJsonObject['object']['type'],
                         postJsonObject['object']['summary'],
                         postJsonObject['object']['content'])

    # benchmark 16
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 16 = ' + str(timeDiff))

    if not isPatch:
        objectContent = \
            removeLongWords(postJsonObject['object']['content'], 40, [])
        objectContent = removeTextFormatting(objectContent)
        objectContent = \
            switchWords(baseDir, nickname, domain, objectContent)
        objectContent = htmlReplaceEmailQuote(objectContent)
        objectContent = htmlReplaceQuoteMarks(objectContent)
    else:
        objectContent = \
            postJsonObject['object']['content']

    if not postIsSensitive:
        contentStr = objectContent + attachmentStr
        contentStr = addEmbeddedElements(translate, contentStr)
        contentStr = insertQuestion(baseDir, translate,
                                    nickname, domain, port,
                                    contentStr, postJsonObject,
                                    pageNumber)
    else:
        postID = 'post' + str(createPassword(8))
        contentStr = ''
        if postJsonObject['object'].get('summary'):
            contentStr += \
                '<b>' + str(postJsonObject['object']['summary']) + '</b>\n '
            if isModerationPost:
                containerClass = 'container report'
        # get the content warning text
        cwContentStr = objectContent + attachmentStr
        if not isPatch:
            cwContentStr = addEmbeddedElements(translate, cwContentStr)
            cwContentStr = \
                insertQuestion(baseDir, translate, nickname, domain, port,
                               cwContentStr, postJsonObject, pageNumber)
        if not isBlogPost(postJsonObject):
            # get the content warning button
            contentStr += \
                getContentWarningButton(postID, translate, cwContentStr)
        else:
            contentStr += cwContentStr

    # benchmark 17
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 17 = ' + str(timeDiff))

    if postJsonObject['object'].get('tag') and not isPatch:
        contentStr = \
            replaceEmojiFromTags(contentStr,
                                 postJsonObject['object']['tag'],
                                 'content')

    if isMuted:
        contentStr = ''
    else:
        if not isPatch:
            contentStr = '      <div class="message">' + \
                contentStr + \
                '      </div>\n'
        else:
            contentStr = \
                '<div class="gitpatch"><pre><code>' + contentStr + \
                '</code></pre></div>\n'

    postHtml = ''
    if boxName != 'tlmedia':
        postHtml = '    <div id="' + timelinePostBookmark + \
            '" class="' + containerClass + '">\n'
        postHtml += avatarImageInPost
        postHtml += '      <div class="post-title">\n' + \
            '        ' + titleStr + \
            replyAvatarImageInPost + '      </div>\n'
        postHtml += contentStr + footerStr + '\n'
        postHtml += '    </div>\n'
    else:
        postHtml = galleryStr

    # benchmark 18
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 18 = ' + str(timeDiff))

    if not showPublicOnly and storeToCache and \
       boxName != 'tlmedia' and boxName != 'tlbookmarks' and \
       boxName != 'bookmarks':
        saveIndividualPostAsHtmlToCache(baseDir, nickname, domain,
                                        postJsonObject, postHtml)
        updateRecentPostsCache(recentPostsCache, maxRecentPosts,
                               postJsonObject, postHtml)

    # benchmark 19
    if not allowDownloads:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 19 = ' + str(timeDiff))

    return postHtml


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


def htmlHighlightLabel(label: str, highlight: bool) -> str:
    """If the give text should be highlighted then return
    the appropriate markup.
    This is so that in shell browsers, like lynx, it's possible
    to see if the replies or DM button are highlighted.
    """
    if not highlight:
        return label
    return '*' + label + '*'


def getLeftColumnContent(baseDir: str, nickname: str, domainFull: str,
                         httpPrefix: str, translate: {},
                         iconsDir: str, moderator: bool) -> str:
    """Returns html content for the left column
    """
    htmlStr = ''

    domain = domainFull
    if ':' in domain:
        domain = domain.split(':')

    leftColumnImageFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + \
        '/left_col_image.png'
    if not os.path.isfile(leftColumnImageFilename):
        theme = getConfigParam(baseDir, 'theme').lower()
        if theme == 'default':
            theme = ''
        else:
            theme = '_' + theme
        themeLeftColumnImageFilename = \
            baseDir + '/img/left_col_image' + theme + '.png'
        if os.path.isfile(themeLeftColumnImageFilename):
            copyfile(themeLeftColumnImageFilename, leftColumnImageFilename)

    # show the image at the top of the column
    editImageClass = 'leftColEdit'
    if os.path.isfile(leftColumnImageFilename):
        editImageClass = 'leftColEditImage'
        htmlStr += \
            '\n      <center>\n' + \
            '        <img class="leftColImg" loading="lazy" src="/users/' + \
            nickname + '/left_col_image.png" />\n' + \
            '      </center>\n'

    if editImageClass == 'leftColEdit':
        htmlStr += '\n      <center>\n'

    if moderator:
        # show the edit icon
        htmlStr += \
            '      <a href="' + \
            '/users/' + nickname + '/editlinks">' + \
            '<img class="' + editImageClass + \
            '" loading="lazy" alt="' + \
            translate['Edit Links'] + '" title="' + \
            translate['Edit Links'] + '" src="/' + \
            iconsDir + '/edit.png" /></a>\n'

    # RSS icon
    htmlStr += \
        '      <a href="' + \
        httpPrefix + '://' + domainFull + \
        '/blog/' + nickname + '/rss.xml">' + \
        '<img class="' + editImageClass + \
        '" loading="lazy" alt="' + \
        translate['RSS feed for this site'] + \
        '" title="' + translate['RSS feed for this site'] + \
        '" src="/' + iconsDir + '/rss.png" /></a>\n'

    if editImageClass == 'leftColEdit':
        htmlStr += '      </center>\n'
    else:
        htmlStr += '      <br>\n'

    linksFilename = baseDir + '/accounts/links.txt'
    if os.path.isfile(linksFilename):
        linksList = None
        with open(linksFilename, "r") as f:
            linksList = f.readlines()
        if linksList:
            for lineStr in linksList:
                if ' ' not in lineStr:
                    if '#' not in lineStr:
                        if '*' not in lineStr:
                            continue
                lineStr = lineStr.strip()
                words = lineStr.split(' ')
                # get the link
                linkStr = None
                for word in words:
                    if word == '#':
                        continue
                    if word == '*':
                        continue
                    if '://' in word:
                        linkStr = word
                        break
                if linkStr:
                    lineStr = lineStr.replace(linkStr, '').strip()
                    # avoid any dubious scripts being added
                    if '<' not in lineStr:
                        # remove trailing comma if present
                        if lineStr.endswith(','):
                            lineStr = lineStr[:len(lineStr)-1]
                        # add link to the returned html
                        htmlStr += \
                            '      <p><a href="' + linkStr + '">' + \
                            lineStr + '</a></p>\n'
                else:
                    if lineStr.startswith('#') or lineStr.startswith('*'):
                        lineStr = lineStr[1:].strip()
                        htmlStr += \
                            '      <h3 class="linksHeader">' + \
                            lineStr + '</h3>\n'
                    else:
                        htmlStr += \
                            '      <p>' + lineStr + '</p>\n'

    return htmlStr


def htmlNewswire(newswire: str, nickname: str, moderator: bool,
                 translate: {}) -> str:
    """Converts a newswire dict into html
    """
    htmlStr = ''
    for dateStr, item in newswire.items():
        dateStrLink = dateStr.replace(' ', 'T')
        dateStrLink = dateStrLink.replace('+00:00', '')
        if 'vote:' + nickname in item[2]:
            totalVotesStr = ''
            if moderator:
                # count the total votes for this item
                totalVotes = 0
                for line in item[2]:
                    if 'vote:' in line:
                        totalVotes += 1
                if totalVotes > 0:
                    totalVotesStr = ' +' + str(totalVotes)

            htmlStr += '<p class="newswireItemApproved">' + \
                '<a href="' + item[1] + '">' + item[0] + '</a>' + \
                totalVotesStr
            if moderator:
                htmlStr += \
                    ' ' + \
                    '<a href="/users/' + nickname + \
                    '/newswireunvote=' + dateStrLink + '" ' + \
                    'title="' + translate['Remove Vote'] + '">' + \
                    '<label class="newswireDateApproved">'
                htmlStr += dateStr.replace('+00:00', '') + '</label></a></p>'
            else:
                htmlStr += ' <label class="newswireDateApproved">'
                htmlStr += dateStr.replace('+00:00', '') + '</label></p>'
        else:
            totalVotesStr = ''
            if moderator:
                # count the total votes for this item
                totalVotes = 0
                for line in item[2]:
                    if 'vote:' in line:
                        totalVotes += 1
                if totalVotes > 0:
                    totalVotesStr = ' +' + str(totalVotes)

            htmlStr += '<p class="newswireItem">' + \
                '<a href="' + item[1] + '">' + item[0] + '</a>' + \
                totalVotesStr
            if moderator:
                htmlStr += \
                    ' ' + \
                    '<a href="/users/' + nickname + \
                    '/newswirevote=' + dateStrLink + '" ' + \
                    'title="' + translate['Vote'] + '">' + \
                    '<label class="newswireDate">'
                htmlStr += dateStr.replace('+00:00', '') + '</label></a></p>'
            else:
                htmlStr += ' <label class="newswireDate">'
                htmlStr += dateStr.replace('+00:00', '') + '</label></p>'
    return htmlStr


def getRightColumnContent(baseDir: str, nickname: str, domainFull: str,
                          httpPrefix: str, translate: {},
                          iconsDir: str, moderator: bool,
                          newswire: {}) -> str:
    """Returns html content for the right column
    """
    htmlStr = ''

    domain = domainFull
    if ':' in domain:
        domain = domain.split(':')

    rightColumnImageFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + \
        '/right_col_image.png'
    if not os.path.isfile(rightColumnImageFilename):
        theme = getConfigParam(baseDir, 'theme').lower()
        if theme == 'default':
            theme = ''
        else:
            theme = '_' + theme
        themeRightColumnImageFilename = \
            baseDir + '/img/right_col_image' + theme + '.png'
        if os.path.isfile(themeRightColumnImageFilename):
            copyfile(themeRightColumnImageFilename, rightColumnImageFilename)

    # show the image at the top of the column
    editImageClass = 'rightColEdit'
    if os.path.isfile(rightColumnImageFilename):
        editImageClass = 'rightColEditImage'
        htmlStr += \
            '\n      <center>\n' + \
            '          <img class="rightColImg" ' + \
            'loading="lazy" src="/users/' + \
            nickname + '/right_col_image.png" />\n' + \
            '      </center>\n'

    if editImageClass == 'rightColEdit':
        htmlStr += '\n      <center>\n'

    if moderator:
        if os.path.isfile(baseDir + '/accounts/newswiremoderation.txt'):
            # show the edit icon highlighted
            htmlStr += \
                '        <a href="' + \
                '/users/' + nickname + '/editnewswire">' + \
                '<img class="' + editImageClass + \
                '" loading="lazy" alt="' + \
                translate['Edit newswire'] + '" title="' + \
                translate['Edit newswire'] + '" src="/' + \
                iconsDir + '/edit_notify.png" /></a>\n'
        else:
            # show the edit icon
            htmlStr += \
                '        <a href="' + \
                '/users/' + nickname + '/editnewswire">' + \
                '<img class="' + editImageClass + \
                '" loading="lazy" alt="' + \
                translate['Edit newswire'] + '" title="' + \
                translate['Edit newswire'] + '" src="/' + \
                iconsDir + '/edit.png" /></a>\n'

    htmlStr += \
        '        <a href="/newswire.xml">' + \
        '<img class="' + editImageClass + \
        '" loading="lazy" alt="' + \
        translate['Newswire RSS Feed'] + '" title="' + \
        translate['Newswire RSS Feed'] + '" src="/' + \
        iconsDir + '/rss.png" /></a>\n'

    if editImageClass == 'rightColEdit':
        htmlStr += '      </center>\n'
    else:
        htmlStr += '      <br>\n'

    htmlStr += htmlNewswire(newswire, nickname, moderator, translate)
    return htmlStr


def htmlTimeline(defaultTimeline: str,
                 recentPostsCache: {}, maxRecentPosts: int,
                 translate: {}, pageNumber: int,
                 itemsPerPage: int, session, baseDir: str,
                 wfRequest: {}, personCache: {},
                 nickname: str, domain: str, port: int, timelineJson: {},
                 boxName: str, allowDeletion: bool,
                 httpPrefix: str, projectVersion: str,
                 manuallyApproveFollowers: bool,
                 minimal: bool,
                 YTReplacementDomain: str,
                 newswire: {}, moderator: bool) -> str:
    """Show the timeline as html
    """
    timelineStartTime = time.time()

    accountDir = baseDir + '/accounts/' + nickname + '@' + domain

    # should the calendar icon be highlighted?
    newCalendarEvent = False
    calendarImage = 'calendar.png'
    calendarPath = '/calendar'
    calendarFile = accountDir + '/.newCalendar'
    if os.path.isfile(calendarFile):
        newCalendarEvent = True
        calendarImage = 'calendar_notify.png'
        with open(calendarFile, 'r') as calfile:
            calendarPath = calfile.read().replace('##sent##', '')
            calendarPath = calendarPath.replace('\n', '').replace('\r', '')

    # should the DM button be highlighted?
    newDM = False
    dmFile = accountDir + '/.newDM'
    if os.path.isfile(dmFile):
        newDM = True
        if boxName == 'dm':
            os.remove(dmFile)

    # should the Replies button be highlighted?
    newReply = False
    replyFile = accountDir + '/.newReply'
    if os.path.isfile(replyFile):
        newReply = True
        if boxName == 'tlreplies':
            os.remove(replyFile)

    # should the Shares button be highlighted?
    newShare = False
    newShareFile = accountDir + '/.newShare'
    if os.path.isfile(newShareFile):
        newShare = True
        if boxName == 'tlshares':
            os.remove(newShareFile)

    # should the Moderation/reports button be highlighted?
    newReport = False
    newReportFile = accountDir + '/.newReport'
    if os.path.isfile(newReportFile):
        newReport = True
        if boxName == 'moderation':
            os.remove(newReportFile)

    # directory where icons are found
    # This changes depending upon theme
    iconsDir = getIconsDir(baseDir)

    # the css filename
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    # filename of the banner shown at the top
    bannerFile = 'banner.png'
    bannerFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/' + bannerFile
    if not os.path.isfile(bannerFilename):
        bannerFile = 'banner.jpg'
        bannerFilename = baseDir + '/accounts/' + \
            nickname + '@' + domain + '/' + bannerFile
    if not os.path.isfile(bannerFilename):
        bannerFile = 'banner.gif'
        bannerFilename = baseDir + '/accounts/' + \
            nickname + '@' + domain + '/' + bannerFile
    if not os.path.isfile(bannerFilename):
        bannerFile = 'banner.avif'
        bannerFilename = baseDir + '/accounts/' + \
            nickname + '@' + domain + '/' + bannerFile
    if not os.path.isfile(bannerFilename):
        bannerFile = 'banner.webp'

    # benchmark 1
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 1 = ' + str(timeDiff))

    with open(cssFilename, 'r') as cssFile:
        # load css
        profileStyle = \
            cssFile.read().replace('banner.png',
                                   '/users/' + nickname + '/' + bannerFile)
        # replace any https within the css with whatever prefix is needed
        if httpPrefix != 'https':
            profileStyle = \
                profileStyle.replace('https://',
                                     httpPrefix + '://')

    # is the user a moderator?
    if not moderator:
        moderator = isModerator(baseDir, nickname)

    # benchmark 2
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 2 = ' + str(timeDiff))

    # the appearance of buttons - highlighted or not
    inboxButton = 'button'
    blogsButton = 'button'
    newsButton = 'button'
    dmButton = 'button'
    if newDM:
        dmButton = 'buttonhighlighted'
    repliesButton = 'button'
    if newReply:
        repliesButton = 'buttonhighlighted'
    mediaButton = 'button'
    bookmarksButton = 'button'
    eventsButton = 'button'
    sentButton = 'button'
    sharesButton = 'button'
    if newShare:
        sharesButton = 'buttonhighlighted'
    moderationButton = 'button'
    if newReport:
        moderationButton = 'buttonhighlighted'
    if boxName == 'inbox':
        inboxButton = 'buttonselected'
    elif boxName == 'tlblogs':
        blogsButton = 'buttonselected'
    elif boxName == 'tlnews':
        newsButton = 'buttonselected'
    elif boxName == 'dm':
        dmButton = 'buttonselected'
        if newDM:
            dmButton = 'buttonselectedhighlighted'
    elif boxName == 'tlreplies':
        repliesButton = 'buttonselected'
        if newReply:
            repliesButton = 'buttonselectedhighlighted'
    elif boxName == 'tlmedia':
        mediaButton = 'buttonselected'
    elif boxName == 'outbox':
        sentButton = 'buttonselected'
    elif boxName == 'moderation':
        moderationButton = 'buttonselected'
        if newReport:
            moderationButton = 'buttonselectedhighlighted'
    elif boxName == 'tlshares':
        sharesButton = 'buttonselected'
        if newShare:
            sharesButton = 'buttonselectedhighlighted'
    elif boxName == 'tlbookmarks' or boxName == 'bookmarks':
        bookmarksButton = 'buttonselected'
    elif boxName == 'tlevents':
        eventsButton = 'buttonselected'

    # get the full domain, including any port number
    fullDomain = domain
    if port != 80 and port != 443:
        if ':' not in domain:
            fullDomain = domain + ':' + str(port)

    usersPath = '/users/' + nickname
    actor = httpPrefix + '://' + fullDomain + usersPath

    showIndividualPostIcons = True

    # show an icon for new follow approvals
    followApprovals = ''
    followRequestsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/followrequests.txt'
    if os.path.isfile(followRequestsFilename):
        with open(followRequestsFilename, 'r') as f:
            for line in f:
                if len(line) > 0:
                    # show follow approvals icon
                    followApprovals = \
                        '<a href="' + usersPath + \
                        '/followers#buttonheader">' + \
                        '<img loading="lazy" ' + \
                        'class="timelineicon" alt="' + \
                        translate['Approve follow requests'] + \
                        '" title="' + translate['Approve follow requests'] + \
                        '" src="/' + iconsDir + '/person.png"/></a>\n'
                    break

    # benchmark 3
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 3 = ' + str(timeDiff))

    # moderation / reports button
    moderationButtonStr = ''
    if moderator and not minimal:
        moderationButtonStr = \
            '<a href="' + usersPath + \
            '/moderation"><button class="' + \
            moderationButton + '"><span>' + \
            htmlHighlightLabel(translate['Mod'], newReport) + \
            ' </span></button></a>\n'

    # shares, bookmarks and events buttons
    sharesButtonStr = ''
    bookmarksButtonStr = ''
    eventsButtonStr = ''
    if not minimal:
        sharesButtonStr = \
            '<a href="' + usersPath + '/tlshares"><button class="' + \
            sharesButton + '"><span>' + \
            htmlHighlightLabel(translate['Shares'], newShare) + \
            ' </span></button></a>\n'

        bookmarksButtonStr = \
            '<a href="' + usersPath + '/tlbookmarks"><button class="' + \
            bookmarksButton + '"><span>' + translate['Bookmarks'] + \
            ' </span></button></a>\n'

        eventsButtonStr = \
            '<a href="' + usersPath + '/tlevents"><button class="' + \
            eventsButton + '"><span>' + translate['Events'] + \
            ' </span></button></a>\n'

    tlStr = htmlHeader(cssFilename, profileStyle)

    # benchmark 4
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 4 = ' + str(timeDiff))

    # what screen to go to when a new post is created
    if boxName == 'dm':
        newPostButtonStr = \
            '      <a class="imageAnchor" href="' + usersPath + \
            '/newdm"><img loading="lazy" src="/' + \
            iconsDir + '/newpost.png" title="' + \
            translate['Create a new DM'] + \
            '" alt="| ' + translate['Create a new DM'] + \
            '" class="timelineicon"/></a>\n'
    elif boxName == 'tlblogs' or boxName == 'tlnews':
        newPostButtonStr = \
            '        <a class="imageAnchor" href="' + usersPath + \
            '/newblog"><img loading="lazy" src="/' + \
            iconsDir + '/newpost.png" title="' + \
            translate['Create a new post'] + '" alt="| ' + \
            translate['Create a new post'] + \
            '" class="timelineicon"/></a>\n'
    elif boxName == 'tlevents':
        newPostButtonStr = \
            '        <a class="imageAnchor" href="' + usersPath + \
            '/newevent"><img loading="lazy" src="/' + \
            iconsDir + '/newpost.png" title="' + \
            translate['Create a new event'] + '" alt="| ' + \
            translate['Create a new event'] + \
            '" class="timelineicon"/></a>\n'
    else:
        if not manuallyApproveFollowers:
            newPostButtonStr = \
                '        <a class="imageAnchor" href="' + usersPath + \
                '/newpost"><img loading="lazy" src="/' + \
                iconsDir + '/newpost.png" title="' + \
                translate['Create a new post'] + '" alt="| ' + \
                translate['Create a new post'] + \
                '" class="timelineicon"/></a>\n'
        else:
            newPostButtonStr = \
                '        <a class="imageAnchor" href="' + usersPath + \
                '/newfollowers"><img loading="lazy" src="/' + \
                iconsDir + '/newpost.png" title="' + \
                translate['Create a new post'] + \
                '" alt="| ' + translate['Create a new post'] + \
                '" class="timelineicon"/></a>\n'

    # This creates a link to the profile page when viewed
    # in lynx, but should be invisible in a graphical web browser
    tlStr += \
        '<label class="transparent"><a href="/users/' + nickname + '">' + \
        translate['Switch to profile view'] + '</a></label>\n'

    # banner and row of buttons
    tlStr += \
        '<a href="/users/' + nickname + '" title="' + \
        translate['Switch to profile view'] + '" alt="' + \
        translate['Switch to profile view'] + '">\n'
    tlStr += '<div class="timeline-banner">'
    tlStr += '</div>\n</a>\n'

    # start the timeline
    tlStr += '<table class="timeline">\n'
    tlStr += '  <colgroup>\n'
    tlStr += '    <col span="1" class="column-left">\n'
    tlStr += '    <col span="1" class="column-center">\n'
    tlStr += '    <col span="1" class="column-right">\n'
    tlStr += '  </colgroup>\n'
    tlStr += '  <tbody>\n'
    tlStr += '    <tr>\n'

    domainFull = domain
    if port:
        if port != 80 and port != 443:
            domainFull = domain + ':' + str(port)

    # left column
    leftColumnStr = \
        getLeftColumnContent(baseDir, nickname, domainFull,
                             httpPrefix, translate, iconsDir,
                             moderator)
    tlStr += '  <td valign="top" class="col-left">' + \
        leftColumnStr + '  </td>\n'
    # center column containing posts
    tlStr += '  <td valign="top" class="col-center">\n'

    # start of the button header with inbox, outbox, etc
    tlStr += '    <div class="container">\n'
    # first button
    if defaultTimeline == 'tlmedia':
        tlStr += \
            '      <a href="' + usersPath + \
            '/tlmedia"><button class="' + \
            mediaButton + '"><span>' + translate['Media'] + \
            '</span></button></a>\n'
    elif defaultTimeline == 'tlblogs':
        tlStr += \
            '      <a href="' + usersPath + \
            '/tlblogs"><button class="' + \
            blogsButton + '"><span>' + translate['Blogs'] + \
            '</span></button></a>\n'
    elif defaultTimeline == 'tlnews':
        tlStr += \
            '      <a href="' + usersPath + \
            '/tlnews"><button class="' + \
            newsButton + '"><span>' + translate['News'] + \
            '</span></button></a>\n'
    else:
        tlStr += \
            '      <a href="' + usersPath + \
            '/inbox"><button class="' + \
            inboxButton + '"><span>' + \
            translate['Inbox'] + '</span></button></a>\n'

    tlStr += \
        '      <a href="' + usersPath + '/dm"><button class="' + dmButton + \
        '"><span>' + htmlHighlightLabel(translate['DM'], newDM) + \
        '</span></button></a>\n'

    tlStr += \
        '      <a href="' + usersPath + '/tlreplies"><button class="' + \
        repliesButton + '"><span>' + \
        htmlHighlightLabel(translate['Replies'], newReply) + \
        '</span></button></a>\n'

    # typically the media button
    if defaultTimeline != 'tlmedia':
        if not minimal:
            tlStr += \
                '      <a href="' + usersPath + \
                '/tlmedia"><button class="' + \
                mediaButton + '"><span>' + translate['Media'] + \
                '</span></button></a>\n'
    else:
        if not minimal:
            tlStr += \
                '      <a href="' + usersPath + \
                '/inbox"><button class="' + \
                inboxButton+'"><span>' + translate['Inbox'] + \
                '</span></button></a>\n'

    # typically the blogs button
    # but may change if this is a blogging oriented instance
    if defaultTimeline != 'tlblogs':
        if not minimal:
            tlStr += \
                '      <a href="' + usersPath + \
                '/tlblogs"><button class="' + \
                blogsButton + '"><span>' + translate['Blogs'] + \
                '</span></button></a>\n'
    else:
        if not minimal:
            tlStr += \
                '      <a href="' + usersPath + \
                '/inbox"><button class="' + \
                inboxButton + '"><span>' + translate['Inbox'] + \
                '</span></button></a>\n'

    # typically the news button
    # but may change if this is a news oriented instance
    if defaultTimeline != 'tlnews':
        if not minimal:
            tlStr += \
                '      <a href="' + usersPath + \
                '/tlnews"><button class="' + \
                newsButton + '"><span>' + translate['News'] + \
                '</span></button></a>\n'
    else:
        if not minimal:
            tlStr += \
                '      <a href="' + usersPath + \
                '/inbox"><button class="' + \
                inboxButton + '"><span>' + translate['Inbox'] + \
                '</span></button></a>\n'

    # button for the outbox
    tlStr += \
        '      <a href="' + usersPath + \
        '/outbox"><button class="' + \
        sentButton+'"><span>' + translate['Outbox'] + \
        '</span></button></a>\n'

    # add other buttons
    tlStr += \
        sharesButtonStr + bookmarksButtonStr + eventsButtonStr + \
        moderationButtonStr + newPostButtonStr

    # show todays events buttons on the first inbox page
    if boxName == 'inbox' and pageNumber == 1:
        if todaysEventsCheck(baseDir, nickname, domain):
            now = datetime.now()

            # happening today button
            tlStr += \
                '    <a href="' + usersPath + '/calendar?year=' + \
                str(now.year) + '?month=' + str(now.month) + \
                '?day=' + str(now.day) + '"><button class="buttonevent">' + \
                translate['Happening Today'] + '</button></a>\n'

            # happening this week button
            if thisWeeksEventsCheck(baseDir, nickname, domain):
                tlStr += \
                    '    <a href="' + usersPath + \
                    '/calendar"><button class="buttonevent">' + \
                    translate['Happening This Week'] + '</button></a>\n'
        else:
            # happening this week button
            if thisWeeksEventsCheck(baseDir, nickname, domain):
                tlStr += \
                    '    <a href="' + usersPath + \
                    '/calendar"><button class="buttonevent">' + \
                    translate['Happening This Week'] + '</button></a>\n'

    # the search button
    tlStr += \
        '        <a class="imageAnchor" href="' + usersPath + \
        '/search"><img loading="lazy" src="/' + \
        iconsDir + '/search.png" title="' + \
        translate['Search and follow'] + '" alt="| ' + \
        translate['Search and follow'] + '" class="timelineicon"/></a>\n'

    # benchmark 5
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 5 = ' + str(timeDiff))

    # the calendar button
    calendarAltText = translate['Calendar']
    if newCalendarEvent:
        # indicate that the calendar icon is highlighted
        calendarAltText = '*' + calendarAltText + '*'
    tlStr += \
        '        <a class="imageAnchor" href="' + usersPath + calendarPath + \
        '"><img loading="lazy" src="/' + iconsDir + '/' + \
        calendarImage + '" title="' + translate['Calendar'] + \
        '" alt="| ' + calendarAltText + '" class="timelineicon"/></a>\n'

    # the show/hide button, for a simpler header appearance
    tlStr += \
        '        <a class="imageAnchor" href="' + usersPath + '/minimal' + \
        '"><img loading="lazy" src="/' + iconsDir + \
        '/showhide.png" title="' + translate['Show/Hide Buttons'] + \
        '" alt="| ' + translate['Show/Hide Buttons'] + \
        '" class="timelineicon"/></a>\n'
    tlStr += followApprovals
    # end of the button header with inbox, outbox, etc
    tlStr += '    </div>\n'

    # second row of buttons for moderator actions
    if moderator and boxName == 'moderation':
        tlStr += \
            '<form method="POST" action="/users/' + \
            nickname + '/moderationaction">'
        tlStr += '<div class="container">\n'
        idx = 'Nickname or URL. Block using *@domain or nickname@domain'
        tlStr += \
            '    <b>' + translate[idx] + '</b><br>\n'
        tlStr += '    <input type="text" ' + \
            'name="moderationAction" value="" autofocus><br>\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Remove the above item'] + \
            '" name="submitRemove" value="' + \
            translate['Remove'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Suspend the above account nickname'] + \
            '" name="submitSuspend" value="' + translate['Suspend'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Remove a suspension for an account nickname'] + \
            '" name="submitUnsuspend" value="' + \
            translate['Unsuspend'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Block an account on another instance'] + \
            '" name="submitBlock" value="' + translate['Block'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Unblock an account on another instance'] + \
            '" name="submitUnblock" value="' + translate['Unblock'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Information about current blocks/suspensions'] + \
            '" name="submitInfo" value="' + translate['Info'] + '">\n'
        tlStr += '</div>\n</form>\n'

    # benchmark 6
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 6 = ' + str(timeDiff))

    if boxName == 'tlshares':
        maxSharesPerAccount = itemsPerPage
        return (tlStr +
                htmlSharesTimeline(translate, pageNumber, itemsPerPage,
                                   baseDir, actor, nickname, domain, port,
                                   maxSharesPerAccount, httpPrefix) +
                htmlFooter())

    # benchmark 7
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 7 = ' + str(timeDiff))

    # benchmark 8
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 8 = ' + str(timeDiff))

    # page up arrow
    if pageNumber > 1:
        tlStr += \
            '  <center>\n' + \
            '    <a href="' + usersPath + '/' + boxName + \
            '?page=' + str(pageNumber - 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pageup.png" title="' + \
            translate['Page up'] + '" alt="' + \
            translate['Page up'] + '"></a>\n' + \
            '  </center>\n'

    # show the posts
    itemCtr = 0
    if timelineJson:
        # if this is the media timeline then add an extra gallery container
        if boxName == 'tlmedia':
            if pageNumber > 1:
                tlStr += '<br>'
            tlStr += '<div class="galleryContainer">\n'

        # show each post in the timeline
        for item in timelineJson['orderedItems']:
            timelinePostStartTime = time.time()

            if item['type'] == 'Create' or \
               item['type'] == 'Announce' or \
               item['type'] == 'Update':
                # is the actor who sent this post snoozed?
                if isPersonSnoozed(baseDir, nickname, domain, item['actor']):
                    continue

                # is the post in the memory cache of recent ones?
                currTlStr = None
                if boxName != 'tlmedia' and \
                   recentPostsCache.get('index'):
                    postId = \
                        removeIdEnding(item['id']).replace('/', '#')
                    if postId in recentPostsCache['index']:
                        if not item.get('muted'):
                            if recentPostsCache['html'].get(postId):
                                currTlStr = recentPostsCache['html'][postId]
                                currTlStr = \
                                    preparePostFromHtmlCache(currTlStr,
                                                             boxName,
                                                             pageNumber)
                                # benchmark cache post
                                timeDiff = \
                                    int((time.time() -
                                         timelinePostStartTime) * 1000)
                                if timeDiff > 100:
                                    print('TIMELINE POST CACHE TIMING ' +
                                          boxName + ' = ' + str(timeDiff))

                if not currTlStr:
                    # benchmark cache post
                    timeDiff = \
                        int((time.time() -
                             timelinePostStartTime) * 1000)
                    if timeDiff > 100:
                        print('TIMELINE POST DISK TIMING START ' +
                              boxName + ' = ' + str(timeDiff))

                    # read the post from disk
                    currTlStr = \
                        individualPostAsHtml(False, recentPostsCache,
                                             maxRecentPosts,
                                             iconsDir, translate, pageNumber,
                                             baseDir, session, wfRequest,
                                             personCache,
                                             nickname, domain, port,
                                             item, None, True,
                                             allowDeletion,
                                             httpPrefix, projectVersion,
                                             boxName,
                                             YTReplacementDomain,
                                             boxName != 'dm',
                                             showIndividualPostIcons,
                                             manuallyApproveFollowers,
                                             False, True)
                    # benchmark cache post
                    timeDiff = \
                        int((time.time() -
                             timelinePostStartTime) * 1000)
                    if timeDiff > 100:
                        print('TIMELINE POST DISK TIMING ' +
                              boxName + ' = ' + str(timeDiff))

                if currTlStr:
                    itemCtr += 1
                    tlStr += currTlStr
        if boxName == 'tlmedia':
            tlStr += '</div>\n'

    # end of column-center
    tlStr += '  </td>\n'

    # right column
    rightColumnStr = getRightColumnContent(baseDir, nickname, domainFull,
                                           httpPrefix, translate, iconsDir,
                                           moderator, newswire)
    tlStr += '  <td valign="top" class="col-right">' + \
        rightColumnStr + '  </td>\n'
    tlStr += '  </tr>\n'

    # benchmark 9
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 9 = ' + str(timeDiff))

    # page down arrow
    if itemCtr > 2:
        tlStr += \
            '  <tr>\n' + \
            '    <td class="col-left"></td>\n' + \
            '    <td class="col-center">\n' + \
            '      <center>\n' + \
            '        <a href="' + usersPath + '/' + boxName + '?page=' + \
            str(pageNumber + 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pagedown.png" title="' + \
            translate['Page down'] + '" alt="' + \
            translate['Page down'] + '"></a>\n' + \
            '      </center>\n' + \
            '    </td>\n' + \
            '    <td class="col-right"></td>\n' + \
            '  </tr>\n'

    tlStr += '  </tbody>\n'
    tlStr += '</table>\n'
    tlStr += htmlFooter()
    return tlStr


def htmlShares(defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str, wfRequest: {}, personCache: {},
               nickname: str, domain: str, port: int,
               allowDeletion: bool,
               httpPrefix: str, projectVersion: str,
               YTReplacementDomain: str,
               newswire: {}) -> str:
    """Show the shares timeline as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, None,
                        'tlshares', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        False, YTReplacementDomain, newswire, False)


def htmlInbox(defaultTimeline: str,
              recentPostsCache: {}, maxRecentPosts: int,
              translate: {}, pageNumber: int, itemsPerPage: int,
              session, baseDir: str, wfRequest: {}, personCache: {},
              nickname: str, domain: str, port: int, inboxJson: {},
              allowDeletion: bool,
              httpPrefix: str, projectVersion: str,
              minimal: bool, YTReplacementDomain: str,
              newswire: {}) -> str:
    """Show the inbox as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson,
                        'inbox', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain, newswire, False)


def htmlBookmarks(defaultTimeline: str,
                  recentPostsCache: {}, maxRecentPosts: int,
                  translate: {}, pageNumber: int, itemsPerPage: int,
                  session, baseDir: str, wfRequest: {}, personCache: {},
                  nickname: str, domain: str, port: int, bookmarksJson: {},
                  allowDeletion: bool,
                  httpPrefix: str, projectVersion: str,
                  minimal: bool, YTReplacementDomain: str,
                  newswire: {}) -> str:
    """Show the bookmarks as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, bookmarksJson,
                        'tlbookmarks', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain, newswire, False)


def htmlEvents(defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str, wfRequest: {}, personCache: {},
               nickname: str, domain: str, port: int, bookmarksJson: {},
               allowDeletion: bool,
               httpPrefix: str, projectVersion: str,
               minimal: bool, YTReplacementDomain: str,
               newswire: {}) -> str:
    """Show the events as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, bookmarksJson,
                        'tlevents', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain, newswire, False)


def htmlInboxDMs(defaultTimeline: str,
                 recentPostsCache: {}, maxRecentPosts: int,
                 translate: {}, pageNumber: int, itemsPerPage: int,
                 session, baseDir: str, wfRequest: {}, personCache: {},
                 nickname: str, domain: str, port: int, inboxJson: {},
                 allowDeletion: bool,
                 httpPrefix: str, projectVersion: str,
                 minimal: bool, YTReplacementDomain: str,
                 newswire: {}) -> str:
    """Show the DM timeline as html
    """
    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'dm', allowDeletion,
                        httpPrefix, projectVersion, False, minimal,
                        YTReplacementDomain, newswire, False)


def htmlInboxReplies(defaultTimeline: str,
                     recentPostsCache: {}, maxRecentPosts: int,
                     translate: {}, pageNumber: int, itemsPerPage: int,
                     session, baseDir: str, wfRequest: {}, personCache: {},
                     nickname: str, domain: str, port: int, inboxJson: {},
                     allowDeletion: bool,
                     httpPrefix: str, projectVersion: str,
                     minimal: bool, YTReplacementDomain: str,
                     newswire: {}) -> str:
    """Show the replies timeline as html
    """
    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'tlreplies',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain, newswire, False)


def htmlInboxMedia(defaultTimeline: str,
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate: {}, pageNumber: int, itemsPerPage: int,
                   session, baseDir: str, wfRequest: {}, personCache: {},
                   nickname: str, domain: str, port: int, inboxJson: {},
                   allowDeletion: bool,
                   httpPrefix: str, projectVersion: str,
                   minimal: bool, YTReplacementDomain: str,
                   newswire: {}) -> str:
    """Show the media timeline as html
    """
    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'tlmedia',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain, newswire, False)


def htmlInboxBlogs(defaultTimeline: str,
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate: {}, pageNumber: int, itemsPerPage: int,
                   session, baseDir: str, wfRequest: {}, personCache: {},
                   nickname: str, domain: str, port: int, inboxJson: {},
                   allowDeletion: bool,
                   httpPrefix: str, projectVersion: str,
                   minimal: bool, YTReplacementDomain: str,
                   newswire: {}) -> str:
    """Show the blogs timeline as html
    """
    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'tlblogs',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain, newswire, False)


def htmlInboxNews(defaultTimeline: str,
                  recentPostsCache: {}, maxRecentPosts: int,
                  translate: {}, pageNumber: int, itemsPerPage: int,
                  session, baseDir: str, wfRequest: {}, personCache: {},
                  nickname: str, domain: str, port: int, inboxJson: {},
                  allowDeletion: bool,
                  httpPrefix: str, projectVersion: str,
                  minimal: bool, YTReplacementDomain: str,
                  newswire: {}, moderator: bool) -> str:
    """Show the news timeline as html
    """
    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'tlnews',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain, newswire, moderator)


def htmlModeration(defaultTimeline: str,
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate: {}, pageNumber: int, itemsPerPage: int,
                   session, baseDir: str, wfRequest: {}, personCache: {},
                   nickname: str, domain: str, port: int, inboxJson: {},
                   allowDeletion: bool,
                   httpPrefix: str, projectVersion: str,
                   YTReplacementDomain: str,
                   newswire: {}) -> str:
    """Show the moderation feed as html
    """
    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'moderation',
                        allowDeletion, httpPrefix, projectVersion, True, False,
                        YTReplacementDomain, newswire, False)


def htmlOutbox(defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str, wfRequest: {}, personCache: {},
               nickname: str, domain: str, port: int, outboxJson: {},
               allowDeletion: bool,
               httpPrefix: str, projectVersion: str,
               minimal: bool, YTReplacementDomain: str,
               newswire: {}) -> str:
    """Show the Outbox as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)
    return htmlTimeline(defaultTimeline, recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, outboxJson, 'outbox',
                        allowDeletion, httpPrefix, projectVersion,
                        manuallyApproveFollowers, minimal,
                        YTReplacementDomain, newswire, False)


def htmlIndividualPost(recentPostsCache: {}, maxRecentPosts: int,
                       translate: {},
                       baseDir: str, session, wfRequest: {}, personCache: {},
                       nickname: str, domain: str, port: int, authorized: bool,
                       postJsonObject: {}, httpPrefix: str,
                       projectVersion: str, likedBy: str,
                       YTReplacementDomain: str) -> str:
    """Show an individual post as html
    """
    iconsDir = getIconsDir(baseDir)
    postStr = ''
    if likedBy:
        likedByNickname = getNicknameFromActor(likedBy)
        likedByDomain, likedByPort = getDomainFromActor(likedBy)
        if likedByPort:
            if likedByPort != 80 and likedByPort != 443:
                likedByDomain += ':' + str(likedByPort)
        likedByHandle = likedByNickname + '@' + likedByDomain
        postStr += \
            '<p>' + translate['Liked by'] + \
            ' <a href="' + likedBy + '">@' + \
            likedByHandle + '</a>\n'

        domainFull = domain
        if port:
            if port != 80 and port != 443:
                domainFull = domain + ':' + str(port)
        actor = '/users/' + nickname
        followStr = '  <form method="POST" ' + \
            'accept-charset="UTF-8" action="' + actor + '/searchhandle">\n'
        followStr += \
            '    <input type="hidden" name="actor" value="' + actor + '">\n'
        followStr += \
            '    <input type="hidden" name="searchtext" value="' + \
            likedByHandle + '">\n'
        if not isFollowingActor(baseDir, nickname, domainFull, likedBy):
            followStr += '    <button type="submit" class="button" ' + \
                'name="submitSearch">' + translate['Follow'] + '</button>\n'
        followStr += '    <button type="submit" class="button" ' + \
            'name="submitBack">' + translate['Go Back'] + '</button>\n'
        followStr += '  </form>\n'
        postStr += followStr + '</p>\n'

    postStr += \
        individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                             iconsDir, translate, None,
                             baseDir, session, wfRequest, personCache,
                             nickname, domain, port, postJsonObject,
                             None, True, False,
                             httpPrefix, projectVersion, 'inbox',
                             YTReplacementDomain,
                             False, authorized, False, False, False)
    messageId = removeIdEnding(postJsonObject['id'])

    # show the previous posts
    if isinstance(postJsonObject['object'], dict):
        while postJsonObject['object'].get('inReplyTo'):
            postFilename = \
                locatePost(baseDir, nickname, domain,
                           postJsonObject['object']['inReplyTo'])
            if not postFilename:
                break
            postJsonObject = loadJson(postFilename)
            if postJsonObject:
                postStr = \
                    individualPostAsHtml(True, recentPostsCache,
                                         maxRecentPosts,
                                         iconsDir, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port,
                                         postJsonObject,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         False, authorized,
                                         False, False, False) + postStr

    # show the following posts
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if postFilename:
        # is there a replies file for this post?
        repliesFilename = postFilename.replace('.json', '.replies')
        if os.path.isfile(repliesFilename):
            # get items from the replies file
            repliesJson = {
                'orderedItems': []
            }
            populateRepliesJson(baseDir, nickname, domain,
                                repliesFilename, authorized, repliesJson)
            # add items to the html output
            for item in repliesJson['orderedItems']:
                postStr += \
                    individualPostAsHtml(True, recentPostsCache,
                                         maxRecentPosts,
                                         iconsDir, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         False, authorized,
                                         False, False, False)
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        postsCSS = cssFile.read()
        if httpPrefix != 'https':
            postsCSS = postsCSS.replace('https://',
                                        httpPrefix + '://')
    return htmlHeader(cssFilename, postsCSS) + postStr + htmlFooter()


def htmlPostReplies(recentPostsCache: {}, maxRecentPosts: int,
                    translate: {}, baseDir: str,
                    session, wfRequest: {}, personCache: {},
                    nickname: str, domain: str, port: int, repliesJson: {},
                    httpPrefix: str, projectVersion: str,
                    YTReplacementDomain: str) -> str:
    """Show the replies to an individual post as html
    """
    iconsDir = getIconsDir(baseDir)
    repliesStr = ''
    if repliesJson.get('orderedItems'):
        for item in repliesJson['orderedItems']:
            repliesStr += \
                individualPostAsHtml(True, recentPostsCache,
                                     maxRecentPosts,
                                     iconsDir, translate, None,
                                     baseDir, session, wfRequest, personCache,
                                     nickname, domain, port, item,
                                     None, True, False,
                                     httpPrefix, projectVersion, 'inbox',
                                     YTReplacementDomain,
                                     False, False, False, False, False)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        postsCSS = cssFile.read()
        if httpPrefix != 'https':
            postsCSS = postsCSS.replace('https://',
                                        httpPrefix + '://')
    return htmlHeader(cssFilename, postsCSS) + repliesStr + htmlFooter()


def htmlRemoveSharedItem(translate: {}, baseDir: str,
                         actor: str, shareName: str,
                         callingDomain: str) -> str:
    """Shows a screen asking to confirm the removal of a shared item
    """
    itemID = getValidSharedItemID(shareName)
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    domainFull = domain
    if port:
        if port != 80 and port != 443:
            domainFull = domain + ':' + str(port)
    sharesFile = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/shares.json'
    if not os.path.isfile(sharesFile):
        print('ERROR: no shares file ' + sharesFile)
        return None
    sharesJson = loadJson(sharesFile)
    if not sharesJson:
        print('ERROR: unable to load shares.json')
        return None
    if not sharesJson.get(itemID):
        print('ERROR: share named "' + itemID + '" is not in ' + sharesFile)
        return None
    sharedItemDisplayName = sharesJson[itemID]['displayName']
    sharedItemImageUrl = None
    if sharesJson[itemID].get('imageUrl'):
        sharedItemImageUrl = sharesJson[itemID]['imageUrl']

    if os.path.isfile(baseDir + '/img/shares-background.png'):
        if not os.path.isfile(baseDir + '/accounts/shares-background.png'):
            copyfile(baseDir + '/img/shares-background.png',
                     baseDir + '/accounts/shares-background.png')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    sharesStr = htmlHeader(cssFilename, profileStyle)
    sharesStr += '<div class="follow">\n'
    sharesStr += '  <div class="followAvatar">\n'
    sharesStr += '  <center>\n'
    if sharedItemImageUrl:
        sharesStr += '  <img loading="lazy" src="' + \
            sharedItemImageUrl + '"/>\n'
    sharesStr += \
        '  <p class="followText">' + translate['Remove'] + \
        ' ' + sharedItemDisplayName + ' ?</p>\n'
    postActor = getAltPath(actor, domainFull, callingDomain)
    sharesStr += '  <form method="POST" action="' + postActor + '/rmshare">\n'
    sharesStr += \
        '    <input type="hidden" name="actor" value="' + actor + '">\n'
    sharesStr += '    <input type="hidden" name="shareName" value="' + \
        shareName + '">\n'
    sharesStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    sharesStr += \
        '    <a href="' + actor + '/inbox' + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    sharesStr += '  </form>\n'
    sharesStr += '  </center>\n'
    sharesStr += '  </div>\n'
    sharesStr += '</div>\n'
    sharesStr += htmlFooter()
    return sharesStr


def htmlDeletePost(recentPostsCache: {}, maxRecentPosts: int,
                   translate, pageNumber: int,
                   session, baseDir: str, messageId: str,
                   httpPrefix: str, projectVersion: str,
                   wfRequest: {}, personCache: {},
                   callingDomain: str,
                   YTReplacementDomain: str) -> str:
    """Shows a screen asking to confirm the deletion of a post
    """
    if '/statuses/' not in messageId:
        return None
    iconsDir = getIconsDir(baseDir)
    actor = messageId.split('/statuses/')[0]
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    domainFull = domain
    if port:
        if port != 80 and port != 443:
            domainFull = domain + ':' + str(port)

    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        return None

    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return None

    if os.path.isfile(baseDir + '/img/delete-background.png'):
        if not os.path.isfile(baseDir + '/accounts/delete-background.png'):
            copyfile(baseDir + '/img/delete-background.png',
                     baseDir + '/accounts/delete-background.png')

    deletePostStr = None
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
        if httpPrefix != 'https':
            profileStyle = profileStyle.replace('https://',
                                                httpPrefix + '://')
        deletePostStr = htmlHeader(cssFilename, profileStyle)
        deletePostStr += \
            individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                                 iconsDir, translate, pageNumber,
                                 baseDir, session, wfRequest, personCache,
                                 nickname, domain, port, postJsonObject,
                                 None, True, False,
                                 httpPrefix, projectVersion, 'outbox',
                                 YTReplacementDomain,
                                 False, False, False, False, False)
        deletePostStr += '<center>'
        deletePostStr += \
            '  <p class="followText">' + \
            translate['Delete this post?'] + '</p>'

        postActor = getAltPath(actor, domainFull, callingDomain)
        deletePostStr += \
            '  <form method="POST" action="' + postActor + '/rmpost">\n'
        deletePostStr += \
            '    <input type="hidden" name="pageNumber" value="' + \
            str(pageNumber) + '">\n'
        deletePostStr += \
            '    <input type="hidden" name="messageId" value="' + \
            messageId + '">\n'
        deletePostStr += \
            '    <button type="submit" class="button" name="submitYes">' + \
            translate['Yes'] + '</button>\n'
        deletePostStr += \
            '    <a href="' + actor + '/inbox"><button class="button">' + \
            translate['No'] + '</button></a>\n'
        deletePostStr += '  </form>\n'
        deletePostStr += '</center>\n'
        deletePostStr += htmlFooter()
    return deletePostStr


def htmlCalendarDeleteConfirm(translate: {}, baseDir: str,
                              path: str, httpPrefix: str,
                              domainFull: str, postId: str, postTime: str,
                              year: int, monthNumber: int,
                              dayNumber: int, callingDomain: str) -> str:
    """Shows a screen asking to confirm the deletion of a calendar event
    """
    nickname = getNicknameFromActor(path)
    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    domain, port = getDomainFromActor(actor)
    messageId = actor + '/statuses/' + postId

    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        return None

    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return None

    if os.path.isfile(baseDir + '/img/delete-background.png'):
        if not os.path.isfile(baseDir + '/accounts/delete-background.png'):
            copyfile(baseDir + '/img/delete-background.png',
                     baseDir + '/accounts/delete-background.png')

    deletePostStr = None
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
        if httpPrefix != 'https':
            profileStyle = profileStyle.replace('https://',
                                                httpPrefix + '://')
        deletePostStr = htmlHeader(cssFilename, profileStyle)
        deletePostStr += \
            '<center><h1>' + postTime + ' ' + str(year) + '/' + \
            str(monthNumber) + \
            '/' + str(dayNumber) + '</h1></center>'
        deletePostStr += '<center>'
        deletePostStr += '  <p class="followText">' + \
            translate['Delete this event'] + '</p>'

        postActor = getAltPath(actor, domainFull, callingDomain)
        deletePostStr += \
            '  <form method="POST" action="' + postActor + '/rmpost">\n'
        deletePostStr += '    <input type="hidden" name="year" value="' + \
            str(year) + '">\n'
        deletePostStr += '    <input type="hidden" name="month" value="' + \
            str(monthNumber) + '">\n'
        deletePostStr += '    <input type="hidden" name="day" value="' + \
            str(dayNumber) + '">\n'
        deletePostStr += \
            '    <input type="hidden" name="pageNumber" value="1">\n'
        deletePostStr += \
            '    <input type="hidden" name="messageId" value="' + \
            messageId + '">\n'
        deletePostStr += \
            '    <button type="submit" class="button" name="submitYes">' + \
            translate['Yes'] + '</button>\n'
        deletePostStr += \
            '    <a href="' + actor + '/calendar?year=' + \
            str(year) + '?month=' + \
            str(monthNumber) + '"><button class="button">' + \
            translate['No'] + '</button></a>\n'
        deletePostStr += '  </form>\n'
        deletePostStr += '</center>\n'
        deletePostStr += htmlFooter()
    return deletePostStr


def htmlFollowConfirm(translate: {}, baseDir: str,
                      originPathStr: str,
                      followActor: str,
                      followProfileUrl: str) -> str:
    """Asks to confirm a follow
    """
    followDomain, port = getDomainFromActor(followActor)

    if os.path.isfile(baseDir + '/accounts/follow-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/follow-background.jpg'):
            copyfile(baseDir + '/accounts/follow-background-custom.jpg',
                     baseDir + '/accounts/follow-background.jpg')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr = htmlHeader(cssFilename, profileStyle)
    followStr += '<div class="follow">\n'
    followStr += '  <div class="followAvatar">\n'
    followStr += '  <center>\n'
    followStr += '  <a href="' + followActor + '">\n'
    followStr += '  <img loading="lazy" src="' + followProfileUrl + '"/></a>\n'
    followStr += \
        '  <p class="followText">' + translate['Follow'] + ' ' + \
        getNicknameFromActor(followActor) + '@' + followDomain + ' ?</p>\n'
    followStr += '  <form method="POST" action="' + \
        originPathStr + '/followconfirm">\n'
    followStr += '    <input type="hidden" name="actor" value="' + \
        followActor + '">\n'
    followStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    followStr += \
        '    <a href="' + originPathStr + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    followStr += '  </form>\n'
    followStr += '</center>\n'
    followStr += '</div>\n'
    followStr += '</div>\n'
    followStr += htmlFooter()
    return followStr


def htmlUnfollowConfirm(translate: {}, baseDir: str,
                        originPathStr: str,
                        followActor: str,
                        followProfileUrl: str) -> str:
    """Asks to confirm unfollowing an actor
    """
    followDomain, port = getDomainFromActor(followActor)

    if os.path.isfile(baseDir + '/accounts/follow-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/follow-background.jpg'):
            copyfile(baseDir + '/accounts/follow-background-custom.jpg',
                     baseDir + '/accounts/follow-background.jpg')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr = htmlHeader(cssFilename, profileStyle)
    followStr += '<div class="follow">\n'
    followStr += '  <div class="followAvatar">\n'
    followStr += '  <center>\n'
    followStr += '  <a href="' + followActor + '">\n'
    followStr += '  <img loading="lazy" src="' + followProfileUrl + '"/></a>\n'
    followStr += \
        '  <p class="followText">' + translate['Stop following'] + \
        ' ' + getNicknameFromActor(followActor) + \
        '@' + followDomain + ' ?</p>\n'
    followStr += '  <form method="POST" action="' + \
        originPathStr + '/unfollowconfirm">\n'
    followStr += '    <input type="hidden" name="actor" value="' + \
        followActor + '">\n'
    followStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    followStr += \
        '    <a href="' + originPathStr + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    followStr += '  </form>\n'
    followStr += '</center>\n'
    followStr += '</div>\n'
    followStr += '</div>\n'
    followStr += htmlFooter()
    return followStr


def htmlPersonOptions(translate: {}, baseDir: str,
                      domain: str, originPathStr: str,
                      optionsActor: str,
                      optionsProfileUrl: str,
                      optionsLink: str,
                      pageNumber: int,
                      donateUrl: str,
                      xmppAddress: str,
                      matrixAddress: str,
                      ssbAddress: str,
                      blogAddress: str,
                      toxAddress: str,
                      PGPpubKey: str,
                      PGPfingerprint: str,
                      emailAddress) -> str:
    """Show options for a person: view/follow/block/report
    """
    optionsDomain, optionsPort = getDomainFromActor(optionsActor)
    optionsDomainFull = optionsDomain
    if optionsPort:
        if optionsPort != 80 and optionsPort != 443:
            optionsDomainFull = optionsDomain + ':' + str(optionsPort)

    if os.path.isfile(baseDir + '/accounts/options-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/options-background.jpg'):
            copyfile(baseDir + '/accounts/options-background.jpg',
                     baseDir + '/accounts/options-background.jpg')

    followStr = 'Follow'
    blockStr = 'Block'
    nickname = None
    optionsNickname = None
    if originPathStr.startswith('/users/'):
        nickname = originPathStr.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
        followerDomain, followerPort = getDomainFromActor(optionsActor)
        if isFollowingActor(baseDir, nickname, domain, optionsActor):
            followStr = 'Unfollow'

        optionsNickname = getNicknameFromActor(optionsActor)
        optionsDomainFull = optionsDomain
        if optionsPort:
            if optionsPort != 80 and optionsPort != 443:
                optionsDomainFull = optionsDomain + ':' + str(optionsPort)
        if isBlocked(baseDir, nickname, domain,
                     optionsNickname, optionsDomainFull):
            blockStr = 'Block'

    optionsLinkStr = ''
    if optionsLink:
        optionsLinkStr = \
            '    <input type="hidden" name="postUrl" value="' + \
            optionsLink + '">\n'
    cssFilename = baseDir + '/epicyon-options.css'
    if os.path.isfile(baseDir + '/options.css'):
        cssFilename = baseDir + '/options.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
        profileStyle = \
            profileStyle.replace('--follow-text-entry-width: 90%;',
                                 '--follow-text-entry-width: 20%;')

    # To snooze, or not to snooze? That is the question
    snoozeButtonStr = 'Snooze'
    if nickname:
        if isPersonSnoozed(baseDir, nickname, domain, optionsActor):
            snoozeButtonStr = 'Unsnooze'

    donateStr = ''
    if donateUrl:
        donateStr = \
            '    <a href="' + donateUrl + \
            '"><button class="button" name="submitDonate">' + \
            translate['Donate'] + '</button></a>\n'

    optionsStr = htmlHeader(cssFilename, profileStyle)
    optionsStr += '<br><br>\n'
    optionsStr += '<div class="options">\n'
    optionsStr += '  <div class="optionsAvatar">\n'
    optionsStr += '  <center>\n'
    optionsStr += '  <a href="' + optionsActor + '">\n'
    optionsStr += '  <img loading="lazy" src="' + optionsProfileUrl + \
        '"/></a>\n'
    handle = getNicknameFromActor(optionsActor) + '@' + optionsDomain
    optionsStr += \
        '  <p class="optionsText">' + translate['Options for'] + \
        ' @' + handle + '</p>\n'
    if emailAddress:
        optionsStr += \
            '<p class="imText">' + translate['Email'] + \
            ': <a href="mailto:' + \
            emailAddress + '">' + emailAddress + '</a></p>\n'
    if xmppAddress:
        optionsStr += \
            '<p class="imText">' + translate['XMPP'] + \
            ': <a href="xmpp:' + xmppAddress + '">' + \
            xmppAddress + '</a></p>\n'
    if matrixAddress:
        optionsStr += \
            '<p class="imText">' + translate['Matrix'] + ': ' + \
            matrixAddress + '</p>\n'
    if ssbAddress:
        optionsStr += \
            '<p class="imText">SSB: ' + ssbAddress + '</p>\n'
    if blogAddress:
        optionsStr += \
            '<p class="imText">Blog: <a href="' + blogAddress + '">' + \
            blogAddress + '</a></p>\n'
    if toxAddress:
        optionsStr += \
            '<p class="imText">Tox: ' + toxAddress + '</p>\n'
    if PGPfingerprint:
        optionsStr += '<p class="pgp">PGP: ' + \
            PGPfingerprint.replace('\n', '<br>') + '</p>\n'
    if PGPpubKey:
        optionsStr += '<p class="pgp">' + \
            PGPpubKey.replace('\n', '<br>') + '</p>\n'
    optionsStr += '  <form method="POST" action="' + \
        originPathStr + '/personoptions">\n'
    optionsStr += '    <input type="hidden" name="pageNumber" value="' + \
        str(pageNumber) + '">\n'
    optionsStr += '    <input type="hidden" name="actor" value="' + \
        optionsActor + '">\n'
    optionsStr += '    <input type="hidden" name="avatarUrl" value="' + \
        optionsProfileUrl + '">\n'
    if optionsNickname:
        handle = optionsNickname + '@' + optionsDomainFull
        petname = getPetName(baseDir, nickname, domain, handle)
        optionsStr += \
            '    ' + translate['Petname'] + ': \n' + \
            '    <input type="text" name="optionpetname" value="' + \
            petname + '">\n' \
            '    <button type="submit" class="buttonsmall" ' + \
            'name="submitPetname">' + \
            translate['Submit'] + '</button><br>\n'

    if isFollowingActor(baseDir, nickname, domain, optionsActor):
        if receivingCalendarEvents(baseDir, nickname, domain,
                                   optionsNickname, optionsDomainFull):
            optionsStr += \
                '    <input type="checkbox" ' + \
                'class="profilecheckbox" name="onCalendar" checked> ' + \
                translate['Receive calendar events from this account'] + \
                '\n    <button type="submit" class="buttonsmall" ' + \
                'name="submitOnCalendar">' + \
                translate['Submit'] + '</button><br>\n'
        else:
            optionsStr += \
                '    <input type="checkbox" ' + \
                'class="profilecheckbox" name="onCalendar"> ' + \
                translate['Receive calendar events from this account'] + \
                '\n    <button type="submit" class="buttonsmall" ' + \
                'name="submitOnCalendar">' + \
                translate['Submit'] + '</button><br>\n'

    optionsStr += optionsLinkStr
    optionsStr += \
        '    <a href="/"><button type="button" class="buttonIcon" ' + \
        'name="submitBack">' + translate['Go Back'] + '</button></a>\n'
    optionsStr += \
        '    <button type="submit" class="button" name="submitView">' + \
        translate['View'] + '</button>\n'
    optionsStr += donateStr
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        followStr + '">' + translate[followStr] + '</button>\n'
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        blockStr + '">' + translate[blockStr] + '</button>\n'
    optionsStr += \
        '    <button type="submit" class="button" name="submitDM">' + \
        translate['DM'] + '</button>\n'
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        snoozeButtonStr + '">' + translate[snoozeButtonStr] + '</button>\n'
    optionsStr += \
        '    <button type="submit" class="button" name="submitReport">' + \
        translate['Report'] + '</button>\n'

    personNotes = ''
    personNotesFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + \
        '/notes/' + handle + '.txt'
    if os.path.isfile(personNotesFilename):
        with open(personNotesFilename, 'r') as fp:
            personNotes = fp.read()

    optionsStr += \
        '    <br><br>' + translate['Notes'] + ': \n'
    optionsStr += '    <button type="submit" class="buttonsmall" ' + \
        'name="submitPersonNotes">' + \
        translate['Submit'] + '</button><br>\n'
    optionsStr += \
        '    <textarea id="message" ' + \
        'name="optionnotes" style="height:400px">' + \
        personNotes + '</textarea>\n'

    optionsStr += '  </form>\n'
    optionsStr += '</center>\n'
    optionsStr += '</div>\n'
    optionsStr += '</div>\n'
    optionsStr += htmlFooter()
    return optionsStr


def htmlUnblockConfirm(translate: {}, baseDir: str,
                       originPathStr: str,
                       blockActor: str,
                       blockProfileUrl: str) -> str:
    """Asks to confirm unblocking an actor
    """
    blockDomain, port = getDomainFromActor(blockActor)

    if os.path.isfile(baseDir + '/img/block-background.png'):
        if not os.path.isfile(baseDir + '/accounts/block-background.png'):
            copyfile(baseDir + '/img/block-background.png',
                     baseDir + '/accounts/block-background.png')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    blockStr = htmlHeader(cssFilename, profileStyle)
    blockStr += '<div class="block">\n'
    blockStr += '  <div class="blockAvatar">\n'
    blockStr += '  <center>\n'
    blockStr += '  <a href="' + blockActor + '">\n'
    blockStr += '  <img loading="lazy" src="' + blockProfileUrl + '"/></a>\n'
    blockStr += \
        '  <p class="blockText">' + translate['Stop blocking'] + ' ' + \
        getNicknameFromActor(blockActor) + '@' + blockDomain + ' ?</p>\n'
    blockStr += '  <form method="POST" action="' + \
        originPathStr + '/unblockconfirm">\n'
    blockStr += '    <input type="hidden" name="actor" value="' + \
        blockActor + '">\n'
    blockStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    blockStr += \
        '    <a href="' + originPathStr + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    blockStr += '  </form>\n'
    blockStr += '</center>\n'
    blockStr += '</div>\n'
    blockStr += '</div>\n'
    blockStr += htmlFooter()
    return blockStr


def htmlSearchEmojiTextEntry(translate: {},
                             baseDir: str, path: str) -> str:
    """Search for an emoji by name
    """
    # emoji.json is generated so that it can be customized and the changes
    # will be retained even if default_emoji.json is subsequently updated
    if not os.path.isfile(baseDir + '/emoji/emoji.json'):
        copyfile(baseDir + '/emoji/default_emoji.json',
                 baseDir + '/emoji/emoji.json')

    actor = path.replace('/search', '')
    domain, port = getDomainFromActor(actor)

    if os.path.isfile(baseDir + '/img/search-background.png'):
        if not os.path.isfile(baseDir + '/accounts/search-background.png'):
            copyfile(baseDir + '/img/search-background.png',
                     baseDir + '/accounts/search-background.png')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    emojiStr = htmlHeader(cssFilename, profileStyle)
    emojiStr += '<div class="follow">\n'
    emojiStr += '  <div class="followAvatar">\n'
    emojiStr += '  <center>\n'
    emojiStr += \
        '  <p class="followText">' + \
        translate['Enter an emoji name to search for'] + '</p>\n'
    emojiStr += '  <form method="POST" action="' + \
        actor + '/searchhandleemoji">\n'
    emojiStr += '    <input type="hidden" name="actor" value="' + \
        actor + '">\n'
    emojiStr += '    <input type="text" name="searchtext" autofocus><br>\n'
    emojiStr += \
        '    <button type="submit" class="button" name="submitSearch">' + \
        translate['Submit'] + '</button>\n'
    emojiStr += '  </form>\n'
    emojiStr += '  </center>\n'
    emojiStr += '  </div>\n'
    emojiStr += '</div>\n'
    emojiStr += htmlFooter()
    return emojiStr


def weekDayOfMonthStart(monthNumber: int, year: int) -> int:
    """Gets the day number of the first day of the month
    1=sun, 7=sat
    """
    firstDayOfMonth = datetime(year, monthNumber, 1, 0, 0)
    return int(firstDayOfMonth.strftime("%w")) + 1


def htmlCalendarDay(translate: {},
                    baseDir: str, path: str,
                    year: int, monthNumber: int, dayNumber: int,
                    nickname: str, domain: str, dayEvents: [],
                    monthName: str, actor: str) -> str:
    """Show a day within the calendar
    """
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain
    calendarFile = accountDir + '/.newCalendar'
    if os.path.isfile(calendarFile):
        os.remove(calendarFile)

    cssFilename = baseDir + '/epicyon-calendar.css'
    if os.path.isfile(baseDir + '/calendar.css'):
        cssFilename = baseDir + '/calendar.css'
    with open(cssFilename, 'r') as cssFile:
        calendarStyle = cssFile.read()

    calActor = actor
    if '/users/' in actor:
        calActor = '/users/' + actor.split('/users/')[1]

    calendarStr = htmlHeader(cssFilename, calendarStyle)
    calendarStr += '<main><table class="calendar">\n'
    calendarStr += '<caption class="calendar__banner--month">\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(year) + \
        '?month=' + str(monthNumber) + '">\n'
    calendarStr += \
        '  <h1>' + str(dayNumber) + ' ' + monthName + \
        '</h1></a><br><span class="year">' + str(year) + '</span>\n'
    calendarStr += '</caption>\n'
    calendarStr += '<tbody>\n'

    iconsDir = getIconsDir(baseDir)

    if dayEvents:
        for eventPost in dayEvents:
            eventTime = None
            eventDescription = None
            eventPlace = None
            postId = None
            # get the time place and description
            for ev in eventPost:
                if ev['type'] == 'Event':
                    if ev.get('postId'):
                        postId = ev['postId']
                    if ev.get('startTime'):
                        eventDate = \
                            datetime.strptime(ev['startTime'],
                                              "%Y-%m-%dT%H:%M:%S%z")
                        eventTime = eventDate.strftime("%H:%M").strip()
                    if ev.get('name'):
                        eventDescription = ev['name'].strip()
                elif ev['type'] == 'Place':
                    if ev.get('name'):
                        eventPlace = ev['name']

            deleteButtonStr = ''
            if postId:
                deleteButtonStr = \
                    '<td class="calendar__day__icons"><a href="' + calActor + \
                    '/eventdelete?id=' + postId + '?year=' + str(year) + \
                    '?month=' + str(monthNumber) + '?day=' + str(dayNumber) + \
                    '?time=' + eventTime + \
                    '">\n<img class="calendardayicon" loading="lazy" alt="' + \
                    translate['Delete this event'] + ' |" title="' + \
                    translate['Delete this event'] + '" src="/' + \
                    iconsDir + '/delete.png" /></a></td>\n'

            if eventTime and eventDescription and eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="calendar__day__event">' + \
                    '<span class="place">' + \
                    eventPlace + '</span><br>' + eventDescription + \
                    '</td>' + deleteButtonStr + '</tr>\n'
            elif eventTime and eventDescription and not eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="calendar__day__event">' + \
                    eventDescription + '</td>' + deleteButtonStr + '</tr>\n'
            elif not eventTime and eventDescription and not eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time">' + \
                    '</td><td class="calendar__day__event">' + \
                    eventDescription + '</td>' + deleteButtonStr + '</tr>\n'
            elif not eventTime and eventDescription and eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time"></td>' + \
                    '<td class="calendar__day__event"><span class="place">' + \
                    eventPlace + '</span><br>' + eventDescription + \
                    '</td>' + deleteButtonStr + '</tr>\n'
            elif eventTime and not eventDescription and eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="calendar__day__event">' + \
                    '<span class="place">' + \
                    eventPlace + '</span></td>' + \
                    deleteButtonStr + '</tr>\n'

    calendarStr += '</tbody>\n'
    calendarStr += '</table></main>\n'
    calendarStr += htmlFooter()

    return calendarStr


def htmlCalendar(translate: {},
                 baseDir: str, path: str,
                 httpPrefix: str, domainFull: str) -> str:
    """Show the calendar for a person
    """
    iconsDir = getIconsDir(baseDir)
    domain = domainFull
    if ':' in domainFull:
        domain = domainFull.split(':')[0]

    monthNumber = 0
    dayNumber = None
    year = 1970
    actor = httpPrefix + '://' + domainFull + path.replace('/calendar', '')
    if '?' in actor:
        first = True
        for p in actor.split('?'):
            if not first:
                if '=' in p:
                    if p.split('=')[0] == 'year':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            year = int(numStr)
                    elif p.split('=')[0] == 'month':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            monthNumber = int(numStr)
                    elif p.split('=')[0] == 'day':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            dayNumber = int(numStr)
            first = False
        actor = actor.split('?')[0]

    currDate = datetime.now()
    if year == 1970 and monthNumber == 0:
        year = currDate.year
        monthNumber = currDate.month

    nickname = getNicknameFromActor(actor)

    if os.path.isfile(baseDir + '/img/calendar-background.png'):
        if not os.path.isfile(baseDir + '/accounts/calendar-background.png'):
            copyfile(baseDir + '/img/calendar-background.png',
                     baseDir + '/accounts/calendar-background.png')

    months = ('January', 'February', 'March', 'April',
              'May', 'June', 'July', 'August', 'September',
              'October', 'November', 'December')
    monthName = translate[months[monthNumber - 1]]

    if dayNumber:
        dayEvents = None
        events = \
            getTodaysEvents(baseDir, nickname, domain,
                            year, monthNumber, dayNumber)
        if events:
            if events.get(str(dayNumber)):
                dayEvents = events[str(dayNumber)]
        return htmlCalendarDay(translate, baseDir, path,
                               year, monthNumber, dayNumber,
                               nickname, domain, dayEvents,
                               monthName, actor)

    events = \
        getCalendarEvents(baseDir, nickname, domain, year, monthNumber)

    prevYear = year
    prevMonthNumber = monthNumber - 1
    if prevMonthNumber < 1:
        prevMonthNumber = 12
        prevYear = year - 1

    nextYear = year
    nextMonthNumber = monthNumber + 1
    if nextMonthNumber > 12:
        nextMonthNumber = 1
        nextYear = year + 1

    print('Calendar year=' + str(year) + ' month=' + str(monthNumber) +
          ' ' + str(weekDayOfMonthStart(monthNumber, year)))

    if monthNumber < 12:
        daysInMonth = \
            (date(year, monthNumber + 1, 1) - date(year, monthNumber, 1)).days
    else:
        daysInMonth = \
            (date(year + 1, 1, 1) - date(year, monthNumber, 1)).days
    # print('daysInMonth ' + str(monthNumber) + ': ' + str(daysInMonth))

    cssFilename = baseDir + '/epicyon-calendar.css'
    if os.path.isfile(baseDir + '/calendar.css'):
        cssFilename = baseDir + '/calendar.css'
    with open(cssFilename, 'r') as cssFile:
        calendarStyle = cssFile.read()

    calActor = actor
    if '/users/' in actor:
        calActor = '/users/' + actor.split('/users/')[1]

    calendarStr = htmlHeader(cssFilename, calendarStyle)
    calendarStr += '<main><table class="calendar">\n'
    calendarStr += '<caption class="calendar__banner--month">\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(prevYear) + \
        '?month=' + str(prevMonthNumber) + '">'
    calendarStr += \
        '  <img loading="lazy" alt="' + translate['Previous month'] + \
        '" title="' + translate['Previous month'] + '" src="/' + iconsDir + \
        '/prev.png" class="buttonprev"/></a>\n'
    calendarStr += '  <a href="' + calActor + '/inbox">'
    calendarStr += '  <h1>' + monthName + '</h1></a>\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(nextYear) + \
        '?month=' + str(nextMonthNumber) + '">'
    calendarStr += \
        '  <img loading="lazy" alt="' + translate['Next month'] + \
        '" title="' + translate['Next month'] + '" src="/' + iconsDir + \
        '/prev.png" class="buttonnext"/></a>\n'
    calendarStr += '</caption>\n'
    calendarStr += '<thead>\n'
    calendarStr += '<tr>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Sun'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Mon'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Tue'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Wed'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Thu'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Fri'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Sat'] + '</th>\n'
    calendarStr += '</tr>\n'
    calendarStr += '</thead>\n'
    calendarStr += '<tbody>\n'

    dayOfMonth = 0
    dow = weekDayOfMonthStart(monthNumber, year)
    for weekOfMonth in range(1, 7):
        if dayOfMonth == daysInMonth:
            continue
        calendarStr += '  <tr>\n'
        for dayNumber in range(1, 8):
            if (weekOfMonth > 1 and dayOfMonth < daysInMonth) or \
               (weekOfMonth == 1 and dayNumber >= dow):
                dayOfMonth += 1

                isToday = False
                if year == currDate.year:
                    if currDate.month == monthNumber:
                        if dayOfMonth == currDate.day:
                            isToday = True
                if events.get(str(dayOfMonth)):
                    url = calActor + '/calendar?year=' + \
                        str(year) + '?month=' + \
                        str(monthNumber) + '?day=' + str(dayOfMonth)
                    dayLink = '<a href="' + url + '">' + \
                        str(dayOfMonth) + '</a>'
                    # there are events for this day
                    if not isToday:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-event="">' + \
                            dayLink + '</td>\n'
                    else:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-today-event="">' + \
                            dayLink + '</td>\n'
                else:
                    # No events today
                    if not isToday:
                        calendarStr += \
                            '    <td class="calendar__day__cell">' + \
                            str(dayOfMonth) + '</td>\n'
                    else:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-today="">' + str(dayOfMonth) + '</td>\n'
            else:
                calendarStr += '    <td class="calendar__day__cell"></td>\n'
        calendarStr += '  </tr>\n'

    calendarStr += '</tbody>\n'
    calendarStr += '</table></main>\n'
    calendarStr += htmlFooter()
    return calendarStr


def removeOldHashtags(baseDir: str, maxMonths: int) -> str:
    """Remove old hashtags
    """
    if maxMonths > 11:
        maxMonths = 11
    maxDaysSinceEpoch = \
        (datetime.utcnow() - datetime(1970, 1 + maxMonths, 1)).days
    removeHashtags = []

    for subdir, dirs, files in os.walk(baseDir + '/tags'):
        for f in files:
            tagsFilename = os.path.join(baseDir + '/tags', f)
            if not os.path.isfile(tagsFilename):
                continue
            # get last modified datetime
            modTimesinceEpoc = os.path.getmtime(tagsFilename)
            lastModifiedDate = datetime.fromtimestamp(modTimesinceEpoc)
            fileDaysSinceEpoch = (lastModifiedDate - datetime(1970, 1, 1)).days

            # check of the file is too old
            if fileDaysSinceEpoch < maxDaysSinceEpoch:
                removeHashtags.append(tagsFilename)

    for removeFilename in removeHashtags:
        try:
            os.remove(removeFilename)
        except BaseException:
            pass


def htmlHashTagSwarm(baseDir: str, actor: str) -> str:
    """Returns a tag swarm of today's hashtags
    """
    currTime = datetime.utcnow()
    daysSinceEpoch = (currTime - datetime(1970, 1, 1)).days
    daysSinceEpochStr = str(daysSinceEpoch) + ' '
    tagSwarm = []

    for subdir, dirs, files in os.walk(baseDir + '/tags'):
        for f in files:
            tagsFilename = os.path.join(baseDir + '/tags', f)
            if not os.path.isfile(tagsFilename):
                continue
            # get last modified datetime
            modTimesinceEpoc = os.path.getmtime(tagsFilename)
            lastModifiedDate = datetime.fromtimestamp(modTimesinceEpoc)
            fileDaysSinceEpoch = (lastModifiedDate - datetime(1970, 1, 1)).days
            # check if the file was last modified today
            if fileDaysSinceEpoch != daysSinceEpoch:
                continue

            hashTagName = f.split('.')[0]
            if isBlockedHashtag(baseDir, hashTagName):
                continue
            if daysSinceEpochStr not in open(tagsFilename).read():
                continue
            with open(tagsFilename, 'r') as tagsFile:
                line = tagsFile.readline()
                lineCtr = 1
                tagCtr = 0
                maxLineCtr = 1
                while line:
                    if '  ' not in line:
                        line = tagsFile.readline()
                        lineCtr += 1
                        # don't read too many lines
                        if lineCtr >= maxLineCtr:
                            break
                        continue
                    postDaysSinceEpochStr = line.split('  ')[0]
                    if not postDaysSinceEpochStr.isdigit():
                        line = tagsFile.readline()
                        lineCtr += 1
                        # don't read too many lines
                        if lineCtr >= maxLineCtr:
                            break
                        continue
                    postDaysSinceEpoch = int(postDaysSinceEpochStr)
                    if postDaysSinceEpoch < daysSinceEpoch:
                        break
                    if postDaysSinceEpoch == daysSinceEpoch:
                        if tagCtr == 0:
                            tagSwarm.append(hashTagName)
                        tagCtr += 1

                    line = tagsFile.readline()
                    lineCtr += 1
                    # don't read too many lines
                    if lineCtr >= maxLineCtr:
                        break

    if not tagSwarm:
        return ''
    tagSwarm.sort()
    tagSwarmStr = ''
    ctr = 0
    for tagName in tagSwarm:
        tagSwarmStr += \
            '<a href="' + actor + '/tags/' + tagName + \
            '" class="hashtagswarm">' + tagName + '</a>\n'
        ctr += 1
    tagSwarmHtml = tagSwarmStr.strip() + '\n'
    return tagSwarmHtml


def htmlSearch(translate: {},
               baseDir: str, path: str, domain: str) -> str:
    """Search called from the timeline icon
    """
    actor = path.replace('/search', '')
    searchNickname = getNicknameFromActor(actor)

    if os.path.isfile(baseDir + '/img/search-background.png'):
        if not os.path.isfile(baseDir + '/accounts/search-background.png'):
            copyfile(baseDir + '/img/search-background.png',
                     baseDir + '/accounts/search-background.png')

    cssFilename = baseDir + '/epicyon-search.css'
    if os.path.isfile(baseDir + '/search.css'):
        cssFilename = baseDir + '/search.css'
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr = htmlHeader(cssFilename, profileStyle)

    # show a banner above the search box
    searchBannerFilename = \
        baseDir + '/accounts/' + searchNickname + '@' + domain + \
        '/search_banner.png'
    if not os.path.isfile(searchBannerFilename):
        theme = getConfigParam(baseDir, 'theme').lower()
        if theme == 'default':
            theme = ''
        else:
            theme = '_' + theme
        themeSearchBannerFilename = \
            baseDir + '/img/search_banner' + theme + '.png'
        if os.path.isfile(themeSearchBannerFilename):
            copyfile(themeSearchBannerFilename, searchBannerFilename)
    if os.path.isfile(searchBannerFilename):
        followStr += '<center>\n<div class="searchBanner">\n' + \
            '<br><br><br><br><br><br><br><br>' + \
            '<br><br><br><br><br><br><br><br>\n</div>\n</center>\n'

    # show the search box
    followStr += '<div class="follow">\n'
    followStr += '  <div class="followAvatar">\n'
    followStr += '  <center>\n'
    idx = 'Enter an address, shared item, !history, #hashtag, ' + \
        '*skill or :emoji: to search for'
    followStr += \
        '  <p class="followText">' + translate[idx] + '</p>\n'
    followStr += '  <form method="POST" ' + \
        'accept-charset="UTF-8" action="' + actor + '/searchhandle">\n'
    followStr += \
        '    <input type="hidden" name="actor" value="' + actor + '">\n'
    followStr += '    <input type="text" name="searchtext" autofocus><br>\n'
    followStr += '    <a href="/"><button type="button" class="button" ' + \
        'name="submitBack">' + translate['Go Back'] + '</button></a>\n'
    followStr += '    <button type="submit" class="button" ' + \
        'name="submitSearch">' + translate['Submit'] + '</button>\n'
    followStr += '  </form>\n'
    followStr += '  <p class="hashtagswarm">' + \
        htmlHashTagSwarm(baseDir, actor) + '</p>\n'
    followStr += '  </center>\n'
    followStr += '  </div>\n'
    followStr += '</div>\n'
    followStr += htmlFooter()
    return followStr


def htmlProfileAfterSearch(recentPostsCache: {}, maxRecentPosts: int,
                           translate: {},
                           baseDir: str, path: str, httpPrefix: str,
                           nickname: str, domain: str, port: int,
                           profileHandle: str,
                           session, cachedWebfingers: {}, personCache: {},
                           debug: bool, projectVersion: str,
                           YTReplacementDomain: str) -> str:
    """Show a profile page after a search for a fediverse address
    """
    if '/users/' in profileHandle or \
       '/accounts/' in profileHandle or \
       '/channel/' in profileHandle or \
       '/profile/' in profileHandle or \
       '/@' in profileHandle:
        searchNickname = getNicknameFromActor(profileHandle)
        searchDomain, searchPort = getDomainFromActor(profileHandle)
    else:
        if '@' not in profileHandle:
            print('DEBUG: no @ in ' + profileHandle)
            return None
        if profileHandle.startswith('@'):
            profileHandle = profileHandle[1:]
        if '@' not in profileHandle:
            print('DEBUG: no @ in ' + profileHandle)
            return None
        searchNickname = profileHandle.split('@')[0]
        searchDomain = profileHandle.split('@')[1]
        searchPort = None
        if ':' in searchDomain:
            searchPortStr = searchDomain.split(':')[1]
            if searchPortStr.isdigit():
                searchPort = int(searchPortStr)
            searchDomain = searchDomain.split(':')[0]
    if searchPort:
        print('DEBUG: Search for handle ' +
              str(searchNickname) + '@' + str(searchDomain) + ':' +
              str(searchPort))
    else:
        print('DEBUG: Search for handle ' +
              str(searchNickname) + '@' + str(searchDomain))
    if not searchNickname:
        print('DEBUG: No nickname found in ' + profileHandle)
        return None
    if not searchDomain:
        print('DEBUG: No domain found in ' + profileHandle)
        return None

    searchDomainFull = searchDomain
    if searchPort:
        if searchPort != 80 and searchPort != 443:
            if ':' not in searchDomain:
                searchDomainFull = searchDomain + ':' + str(searchPort)

    profileStr = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        wf = \
            webfingerHandle(session,
                            searchNickname + '@' + searchDomainFull,
                            httpPrefix, cachedWebfingers,
                            domain, projectVersion)
        if not wf:
            print('DEBUG: Unable to webfinger ' +
                  searchNickname + '@' + searchDomainFull)
            print('DEBUG: cachedWebfingers ' + str(cachedWebfingers))
            print('DEBUG: httpPrefix ' + httpPrefix)
            print('DEBUG: domain ' + domain)
            return None
        if not isinstance(wf, dict):
            print('WARN: Webfinger search for ' +
                  searchNickname + '@' + searchDomainFull +
                  ' did not return a dict. ' +
                  str(wf))
            return None

        personUrl = None
        if wf.get('errors'):
            personUrl = httpPrefix + '://' + \
                searchDomainFull + '/users/' + searchNickname

        profileStr = 'https://www.w3.org/ns/activitystreams'
        asHeader = {
            'Accept': 'application/activity+json; profile="' + profileStr + '"'
        }
        if not personUrl:
            personUrl = getUserUrl(wf)
        if not personUrl:
            # try single user instance
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
            personUrl = httpPrefix + '://' + searchDomainFull
        profileJson = \
            getJson(session, personUrl, asHeader, None,
                    projectVersion, httpPrefix, domain)
        if not profileJson:
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
            profileJson = \
                getJson(session, personUrl, asHeader, None,
                        projectVersion, httpPrefix, domain)
        if not profileJson:
            print('DEBUG: No actor returned from ' + personUrl)
            return None
        avatarUrl = ''
        if profileJson.get('icon'):
            if profileJson['icon'].get('url'):
                avatarUrl = profileJson['icon']['url']
        if not avatarUrl:
            avatarUrl = getPersonAvatarUrl(baseDir, personUrl,
                                           personCache, True)
        displayName = searchNickname
        if profileJson.get('name'):
            displayName = profileJson['name']
        profileDescription = ''
        if profileJson.get('summary'):
            profileDescription = profileJson['summary']
        outboxUrl = None
        if not profileJson.get('outbox'):
            if debug:
                pprint(profileJson)
                print('DEBUG: No outbox found')
            return None
        outboxUrl = profileJson['outbox']
        profileBackgroundImage = ''
        if profileJson.get('image'):
            if profileJson['image'].get('url'):
                profileBackgroundImage = profileJson['image']['url']

        profileStyle = cssFile.read().replace('image.png',
                                              profileBackgroundImage)
        if httpPrefix != 'https':
            profileStyle = profileStyle.replace('https://',
                                                httpPrefix + '://')
        # url to return to
        backUrl = path
        if not backUrl.endswith('/inbox'):
            backUrl += '/inbox'

        profileDescriptionShort = profileDescription
        if '\n' in profileDescription:
            if len(profileDescription.split('\n')) > 2:
                profileDescriptionShort = ''
        else:
            if '<br>' in profileDescription:
                if len(profileDescription.split('<br>')) > 2:
                    profileDescriptionShort = ''
        # keep the profile description short
        if len(profileDescriptionShort) > 256:
            profileDescriptionShort = ''
        # remove formatting from profile description used on title
        avatarDescription = ''
        if profileJson.get('summary'):
            if isinstance(profileJson['summary'], str):
                avatarDescription = \
                    profileJson['summary'].replace('<br>', '\n')
                avatarDescription = avatarDescription.replace('<p>', '')
                avatarDescription = avatarDescription.replace('</p>', '')
                if '<' in avatarDescription:
                    avatarDescription = removeHtml(avatarDescription)
        profileStr = ' <div class="hero-image">\n'
        profileStr += '  <div class="hero-text">\n'
        if avatarUrl:
            profileStr += \
                '    <img loading="lazy" src="' + avatarUrl + \
                '" alt="' + avatarDescription + '" title="' + \
                avatarDescription + '" class="title">\n'
        profileStr += '    <h1>' + displayName + '</h1>\n'
        profileStr += '    <p><b>@' + searchNickname + '@' + \
            searchDomainFull + '</b></p>\n'
        profileStr += '    <p>' + profileDescriptionShort + '</p>\n'
        profileStr += '  </div>\n'
        profileStr += '</div>\n'
        profileStr += '<div class="container">\n'
        profileStr += '  <form method="POST" action="' + \
            backUrl + '/followconfirm">\n'
        profileStr += '    <center>\n'
        profileStr += \
            '      <input type="hidden" name="actor" value="' + \
            personUrl + '">\n'
        profileStr += \
            '      <a href="' + backUrl + '"><button class="button">' + \
            translate['Go Back'] + '</button></a>\n'
        profileStr += \
            '      <button type="submit" class="button" name="submitYes">' + \
            translate['Follow'] + '</button>\n'
        profileStr += \
            '      <button type="submit" class="button" name="submitView">' + \
            translate['View'] + '</button>\n'
        profileStr += '    </center>\n'
        profileStr += '  </form>\n'
        profileStr += '</div>\n'

        iconsDir = getIconsDir(baseDir)
        i = 0
        for item in parseUserFeed(session, outboxUrl, asHeader,
                                  projectVersion, httpPrefix, domain):
            if not item.get('type'):
                continue
            if item['type'] != 'Create' and item['type'] != 'Announce':
                continue
            if not item.get('object'):
                continue
            profileStr += \
                individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                                     iconsDir, translate, None, baseDir,
                                     session, cachedWebfingers, personCache,
                                     nickname, domain, port,
                                     item, avatarUrl, False, False,
                                     httpPrefix, projectVersion, 'inbox',
                                     YTReplacementDomain,
                                     False, False, False, False, False)
            i += 1
            if i >= 20:
                break

    return htmlHeader(cssFilename, profileStyle) + profileStr + htmlFooter()
