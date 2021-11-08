__filename__ = "webapp_utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
from collections import OrderedDict
from session import getJson
from utils import isAccountDir
from utils import removeHtml
from utils import getProtocolPrefixes
from utils import loadJson
from utils import getCachedPostFilename
from utils import getConfigParam
from utils import acctDir
from utils import getNicknameFromActor
from utils import isfloat
from utils import getAudioExtensions
from utils import getVideoExtensions
from utils import getImageExtensions
from utils import localActorUrl
from cache import storePersonInCache
from content import addHtmlTags
from content import replaceEmojiFromTags
from person import getPersonAvatarUrl
from posts import isModerator
from blocking import isBlocked


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
            followingListHtml = \
                htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
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
    blockedHashtagForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
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


def getContentWarningButton(postID: str, translate: {},
                            content: str) -> str:
    """Returns the markup for a content warning button
    """
    return '       <details><summary class="cw">' + \
        translate['SHOW MORE'] + '</summary>' + \
        '<div id="' + postID + '">' + content + \
        '</div></details>\n'


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


def updateAvatarImageCache(signingPrivateKeyPem: str,
                           session, baseDir: str, httpPrefix: str,
                           actor: str, avatarUrl: str,
                           personCache: {}, allowDownloads: bool,
                           force: bool = False, debug: bool = False) -> str:
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
            if debug:
                print('avatar image url: ' + avatarUrl)
            result = session.get(avatarUrl,
                                 headers=sessionHeaders,
                                 params=None)
            if result.status_code < 200 or \
               result.status_code > 202:
                if debug:
                    print('Avatar image download failed with status ' +
                          str(result.status_code))
                # remove partial download
                if os.path.isfile(avatarImageFilename):
                    try:
                        os.remove(avatarImageFilename)
                    except BaseException:
                        print('EX: updateAvatarImageCache unable to delete ' +
                              avatarImageFilename)
                        pass
            else:
                with open(avatarImageFilename, 'wb') as f:
                    f.write(result.content)
                    if debug:
                        print('avatar image downloaded for ' + actor)
                    return avatarImageFilename.replace(baseDir + '/cache', '')
        except Exception as e:
            print('EX: Failed to download avatar image: ' +
                  str(avatarUrl) + ' ' + str(e))
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
            getJson(signingPrivateKeyPem, session, actor, sessionHeaders, None,
                    debug, __version__, httpPrefix, None)
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


def scheduledPostsExist(baseDir: str, nickname: str, domain: str) -> bool:
    """Returns true if there are posts scheduled to be delivered
    """
    scheduleIndexFilename = \
        acctDir(baseDir, nickname, domain) + '/schedule.index'
    if not os.path.isfile(scheduleIndexFilename):
        return False
    if '#users#' in open(scheduleIndexFilename).read():
        return True
    return False


def sharesTimelineJson(actor: str, pageNumber: int, itemsPerPage: int,
                       baseDir: str, domain: str, nickname: str,
                       maxSharesPerAccount: int,
                       sharedItemsFederatedDomains: [],
                       sharesFileType: str) -> ({}, bool):
    """Get a page on the shared items timeline as json
    maxSharesPerAccount helps to avoid one person dominating the timeline
    by sharing a large number of things
    """
    allSharesJson = {}
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if not isAccountDir(handle):
                continue
            accountDir = baseDir + '/accounts/' + handle
            sharesFilename = accountDir + '/' + sharesFileType + '.json'
            if not os.path.isfile(sharesFilename):
                continue
            sharesJson = loadJson(sharesFilename)
            if not sharesJson:
                continue
            accountNickname = handle.split('@')[0]
            # Don't include shared items from blocked accounts
            if accountNickname != nickname:
                if isBlocked(baseDir, nickname, domain,
                             accountNickname, domain, None):
                    continue
            # actor who owns this share
            owner = actor.split('/users/')[0] + '/users/' + accountNickname
            ctr = 0
            for itemID, item in sharesJson.items():
                # assign owner to the item
                item['actor'] = owner
                item['shareId'] = itemID
                allSharesJson[str(item['published'])] = item
                ctr += 1
                if ctr >= maxSharesPerAccount:
                    break
        break
    if sharedItemsFederatedDomains:
        if sharesFileType == 'shares':
            catalogsDir = baseDir + '/cache/catalogs'
        else:
            catalogsDir = baseDir + '/cache/wantedItems'
        if os.path.isdir(catalogsDir):
            for subdir, dirs, files in os.walk(catalogsDir):
                for f in files:
                    if '#' in f:
                        continue
                    if not f.endswith('.' + sharesFileType + '.json'):
                        continue
                    federatedDomain = f.split('.')[0]
                    if federatedDomain not in sharedItemsFederatedDomains:
                        continue
                    sharesFilename = catalogsDir + '/' + f
                    sharesJson = loadJson(sharesFilename)
                    if not sharesJson:
                        continue
                    ctr = 0
                    for itemID, item in sharesJson.items():
                        # assign owner to the item
                        if '--shareditems--' not in itemID:
                            continue
                        shareActor = itemID.split('--shareditems--')[0]
                        shareActor = shareActor.replace('___', '://')
                        shareActor = shareActor.replace('--', '/')
                        shareNickname = getNicknameFromActor(shareActor)
                        if isBlocked(baseDir, nickname, domain,
                                     shareNickname, federatedDomain, None):
                            continue
                        item['actor'] = shareActor
                        item['shareId'] = itemID
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
            return bannerFile, bannerFilename
    # if not found then use the default image
    theme = 'default'
    directory = baseDir + '/theme/' + theme
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
    accountDir = acctDir(baseDir, nickname, domain)
    return _getImageFile(baseDir, 'banner', accountDir,
                         nickname, domain, theme)


def getSearchBannerFile(baseDir: str,
                        nickname: str, domain: str, theme: str) -> (str, str):
    accountDir = acctDir(baseDir, nickname, domain)
    return _getImageFile(baseDir, 'search_banner', accountDir,
                         nickname, domain, theme)


def getLeftImageFile(baseDir: str,
                     nickname: str, domain: str, theme: str) -> (str, str):
    accountDir = acctDir(baseDir, nickname, domain)
    return _getImageFile(baseDir, 'left_col_image', accountDir,
                         nickname, domain, theme)


def getRightImageFile(baseDir: str,
                      nickname: str, domain: str, theme: str) -> (str, str):
    accountDir = acctDir(baseDir, nickname, domain)
    return _getImageFile(baseDir, 'right_col_image',
                         accountDir, nickname, domain, theme)


def htmlHeaderWithExternalStyle(cssFilename: str, instanceTitle: str,
                                metadata: str, lang='en') -> str:
    if metadata is None:
        metadata = ''
    cssFile = '/' + cssFilename.split('/')[-1]
    htmlStr = \
        '<!DOCTYPE html>\n' + \
        '<html lang="' + lang + '">\n' + \
        '  <head>\n' + \
        '    <meta charset="utf-8">\n' + \
        '    <link rel="stylesheet" media="all" ' + \
        'href="' + cssFile + '">\n' + \
        '    <link rel="manifest" href="/manifest.json">\n' + \
        '    <link href="/favicon.ico" rel="icon" type="image/x-icon">\n' + \
        '    <meta content="/browserconfig.xml" ' + \
        'name="msapplication-config">\n' + \
        '    <meta content="yes" name="apple-mobile-web-app-capable">\n' + \
        '    <link href="/apple-touch-icon.png" rel="apple-touch-icon" ' + \
        'sizes="180x180">\n' + \
        '    <meta name="theme-color" content="grey">\n' + \
        metadata + \
        '    <title>' + instanceTitle + '</title>\n' + \
        '  </head>\n' + \
        '  <body>\n'
    return htmlStr


def htmlHeaderWithPersonMarkup(cssFilename: str, instanceTitle: str,
                               actorJson: {}, city: str,
                               contentLicenseUrl: str,
                               lang='en') -> str:
    """html header which includes person markup
    https://schema.org/Person
    """
    if not actorJson:
        htmlStr = \
            htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None, lang)
        return htmlStr

    cityMarkup = ''
    if city:
        city = city.lower().title()
        addComma = ''
        countryMarkup = ''
        if ',' in city:
            country = city.split(',', 1)[1].strip().title()
            city = city.split(',', 1)[0]
            countryMarkup = \
                '          "addressCountry": "' + country + '"\n'
            addComma = ','
        cityMarkup = \
            '        "address": {\n' + \
            '          "@type": "PostalAddress",\n' + \
            '          "addressLocality": "' + city + '"' + addComma + '\n' + \
            countryMarkup + \
            '        },\n'

    skillsMarkup = ''
    if actorJson.get('hasOccupation'):
        if isinstance(actorJson['hasOccupation'], list):
            skillsMarkup = '        "hasOccupation": [\n'
            firstEntry = True
            for skillDict in actorJson['hasOccupation']:
                if skillDict['@type'] == 'Role':
                    if not firstEntry:
                        skillsMarkup += ',\n'
                    sk = skillDict['hasOccupation']
                    roleName = sk['name']
                    if not roleName:
                        roleName = 'member'
                    category = \
                        sk['occupationalCategory']['codeValue']
                    categoryUrl = \
                        'https://www.onetonline.org/link/summary/' + category
                    skillsMarkup += \
                        '        {\n' + \
                        '          "@type": "Role",\n' + \
                        '          "hasOccupation": {\n' + \
                        '            "@type": "Occupation",\n' + \
                        '            "name": "' + roleName + '",\n' + \
                        '            "description": ' + \
                        '"Fediverse instance role",\n' + \
                        '            "occupationLocation": {\n' + \
                        '              "@type": "City",\n' + \
                        '              "name": "' + city + '"\n' + \
                        '            },\n' + \
                        '            "occupationalCategory": {\n' + \
                        '              "@type": "CategoryCode",\n' + \
                        '              "inCodeSet": {\n' + \
                        '                "@type": "CategoryCodeSet",\n' + \
                        '                "name": "O*Net-SOC",\n' + \
                        '                "dateModified": "2019",\n' + \
                        '                ' + \
                        '"url": "https://www.onetonline.org/"\n' + \
                        '              },\n' + \
                        '              "codeValue": "' + category + '",\n' + \
                        '              "url": "' + categoryUrl + '"\n' + \
                        '            }\n' + \
                        '          }\n' + \
                        '        }'
                elif skillDict['@type'] == 'Occupation':
                    if not firstEntry:
                        skillsMarkup += ',\n'
                    ocName = skillDict['name']
                    if not ocName:
                        ocName = 'member'
                    skillsList = skillDict['skills']
                    skillsListStr = '['
                    for skillStr in skillsList:
                        if skillsListStr != '[':
                            skillsListStr += ', '
                        skillsListStr += '"' + skillStr + '"'
                    skillsListStr += ']'
                    skillsMarkup += \
                        '        {\n' + \
                        '          "@type": "Occupation",\n' + \
                        '          "name": "' + ocName + '",\n' + \
                        '          "description": ' + \
                        '"Fediverse instance occupation",\n' + \
                        '          "occupationLocation": {\n' + \
                        '            "@type": "City",\n' + \
                        '            "name": "' + city + '"\n' + \
                        '          },\n' + \
                        '          "skills": ' + skillsListStr + '\n' + \
                        '        }'
                firstEntry = False
            skillsMarkup += '\n        ],\n'

    description = removeHtml(actorJson['summary'])
    nameStr = removeHtml(actorJson['name'])
    domainFull = actorJson['id'].split('://')[1].split('/')[0]
    handle = actorJson['preferredUsername'] + '@' + domainFull

    personMarkup = \
        '      "about": {\n' + \
        '        "@type" : "Person",\n' + \
        '        "name": "' + nameStr + '",\n' + \
        '        "image": "' + actorJson['icon']['url'] + '",\n' + \
        '        "description": "' + description + '",\n' + \
        cityMarkup + skillsMarkup + \
        '        "url": "' + actorJson['id'] + '"\n' + \
        '      },\n'

    profileMarkup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context":"https://schema.org",\n' + \
        '      "@type": "ProfilePage",\n' + \
        '      "mainEntityOfPage": {\n' + \
        '        "@type": "WebPage",\n' + \
        "        \"@id\": \"" + actorJson['id'] + "\"\n" + \
        '      },\n' + personMarkup + \
        '      "accountablePerson": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + nameStr + '"\n' + \
        '      },\n' + \
        '      "copyrightHolder": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + nameStr + '"\n' + \
        '      },\n' + \
        '      "name": "' + nameStr + '",\n' + \
        '      "image": "' + actorJson['icon']['url'] + '",\n' + \
        '      "description": "' + description + '",\n' + \
        '      "license": "' + contentLicenseUrl + '"\n' + \
        '    }\n' + \
        '    </script>\n'

    description = removeHtml(description)
    ogMetadata = \
        "    <meta content=\"profile\" property=\"og:type\" />\n" + \
        "    <meta content=\"" + description + \
        "\" name='description'>\n" + \
        "    <meta content=\"" + actorJson['url'] + \
        "\" property=\"og:url\" />\n" + \
        "    <meta content=\"" + domainFull + \
        "\" property=\"og:site_name\" />\n" + \
        "    <meta content=\"" + nameStr + " (@" + handle + \
        ")\" property=\"og:title\" />\n" + \
        "    <meta content=\"" + description + \
        "\" property=\"og:description\" />\n" + \
        "    <meta content=\"" + actorJson['icon']['url'] + \
        "\" property=\"og:image\" />\n" + \
        "    <meta content=\"400\" property=\"og:image:width\" />\n" + \
        "    <meta content=\"400\" property=\"og:image:height\" />\n" + \
        "    <meta content=\"summary\" property=\"twitter:card\" />\n" + \
        "    <meta content=\"" + handle + \
        "\" property=\"profile:username\" />\n"
    if actorJson.get('attachment'):
        ogTags = (
            'email', 'openpgp', 'blog', 'xmpp', 'matrix', 'briar',
            'jami', 'cwtch', 'languages'
        )
        for attachJson in actorJson['attachment']:
            if not attachJson.get('name'):
                continue
            if not attachJson.get('value'):
                continue
            name = attachJson['name'].lower()
            value = attachJson['value']
            for ogTag in ogTags:
                if name != ogTag:
                    continue
                ogMetadata += \
                    "    <meta content=\"" + value + \
                    "\" property=\"og:" + ogTag + "\" />\n"

    htmlStr = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle,
                                    ogMetadata + profileMarkup, lang)
    return htmlStr


def htmlHeaderWithWebsiteMarkup(cssFilename: str, instanceTitle: str,
                                httpPrefix: str, domain: str,
                                systemLanguage: str) -> str:
    """html header which includes website markup
    https://schema.org/WebSite
    """
    licenseUrl = 'https://www.gnu.org/licenses/agpl-3.0.rdf'

    # social networking category
    genreUrl = 'http://vocab.getty.edu/aat/300312270'

    websiteMarkup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context" : "http://schema.org",\n' + \
        '      "@type" : "WebSite",\n' + \
        '      "name": "' + instanceTitle + '",\n' + \
        '      "url": "' + httpPrefix + '://' + domain + '",\n' + \
        '      "license": "' + licenseUrl + '",\n' + \
        '      "inLanguage": "' + systemLanguage + '",\n' + \
        '      "isAccessibleForFree": true,\n' + \
        '      "genre": "' + genreUrl + '",\n' + \
        '      "accessMode": ["textual", "visual"],\n' + \
        '      "accessModeSufficient": ["textual"],\n' + \
        '      "accessibilityAPI" : ["ARIA"],\n' + \
        '      "accessibilityControl" : [\n' + \
        '        "fullKeyboardControl",\n' + \
        '        "fullTouchControl",\n' + \
        '        "fullMouseControl"\n' + \
        '      ],\n' + \
        '      "encodingFormat" : [\n' + \
        '        "text/html", "image/png", "image/webp",\n' + \
        '        "image/jpeg", "image/gif", "text/css"\n' + \
        '      ]\n' + \
        '    }\n' + \
        '    </script>\n'

    ogMetadata = \
        '    <meta content="Epicyon hosted on ' + domain + \
        '" property="og:site_name" />\n' + \
        '    <meta content="' + httpPrefix + '://' + domain + \
        '/about" property="og:url" />\n' + \
        '    <meta content="website" property="og:type" />\n' + \
        '    <meta content="' + instanceTitle + \
        '" property="og:title" />\n' + \
        '    <meta content="' + httpPrefix + '://' + domain + \
        '/logo.png" property="og:image" />\n' + \
        '    <meta content="' + systemLanguage + \
        '" property="og:locale" />\n' + \
        '    <meta content="summary_large_image" property="twitter:card" />\n'

    htmlStr = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle,
                                    ogMetadata + websiteMarkup,
                                    systemLanguage)
    return htmlStr


def htmlHeaderWithBlogMarkup(cssFilename: str, instanceTitle: str,
                             httpPrefix: str, domain: str, nickname: str,
                             systemLanguage: str,
                             published: str, modified: str,
                             title: str, snippet: str,
                             translate: {}, url: str,
                             contentLicenseUrl: str) -> str:
    """html header which includes blog post markup
    https://schema.org/BlogPosting
    """
    authorUrl = localActorUrl(httpPrefix, nickname, domain)
    aboutUrl = httpPrefix + '://' + domain + '/about.html'

    # license for content on the site may be different from
    # the software license

    blogMarkup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context" : "http://schema.org",\n' + \
        '      "@type" : "BlogPosting",\n' + \
        '      "headline": "' + title + '",\n' + \
        '      "datePublished": "' + published + '",\n' + \
        '      "dateModified": "' + modified + '",\n' + \
        '      "author": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + nickname + '",\n' + \
        '        "sameAs": "' + authorUrl + '"\n' + \
        '      },\n' + \
        '      "publisher": {\n' + \
        '        "@type": "WebSite",\n' + \
        '        "name": "' + instanceTitle + '",\n' + \
        '        "sameAs": "' + aboutUrl + '"\n' + \
        '      },\n' + \
        '      "license": "' + contentLicenseUrl + '",\n' + \
        '      "description": "' + snippet + '"\n' + \
        '    }\n' + \
        '    </script>\n'

    ogMetadata = \
        '    <meta property="og:locale" content="' + \
        systemLanguage + '" />\n' + \
        '    <meta property="og:type" content="article" />\n' + \
        '    <meta property="og:title" content="' + title + '" />\n' + \
        '    <meta property="og:url" content="' + url + '" />\n' + \
        '    <meta content="Epicyon hosted on ' + domain + \
        '" property="og:site_name" />\n' + \
        '    <meta property="article:published_time" content="' + \
        published + '" />\n' + \
        '    <meta property="article:modified_time" content="' + \
        modified + '" />\n'

    htmlStr = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle,
                                    ogMetadata + blogMarkup, systemLanguage)
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
            print('ERROR: loadIndividualPostAsHtmlFromCache ' +
                  str(tries) + ' ' + str(e))
            # no sleep
            tries += 1
    if postHtml:
        return postHtml


def addEmojiToDisplayName(session, baseDir: str, httpPrefix: str,
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
            replaceEmojiFromTags(session, baseDir,
                                 displayName, emojiTagsList, 'post header',
                                 False)
    else:
        displayName = \
            replaceEmojiFromTags(session, baseDir,
                                 displayName, emojiTagsList, 'profile',
                                 False)
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


def _isImageMimeType(mimeType: str) -> bool:
    """Is the given mime type an image?
    """
    if mimeType == 'image/svg+xml':
        return True
    if not mimeType.startswith('image/'):
        return False
    extensions = getImageExtensions()
    ext = mimeType.split('/')[1]
    if ext in extensions:
        return True
    return False


def _isVideoMimeType(mimeType: str) -> bool:
    """Is the given mime type a video?
    """
    if not mimeType.startswith('video/'):
        return False
    extensions = getVideoExtensions()
    ext = mimeType.split('/')[1]
    if ext in extensions:
        return True
    return False


def _isAudioMimeType(mimeType: str) -> bool:
    """Is the given mime type an audio file?
    """
    if mimeType == 'audio/mpeg':
        return True
    if not mimeType.startswith('audio/'):
        return False
    extensions = getAudioExtensions()
    ext = mimeType.split('/')[1]
    if ext in extensions:
        return True
    return False


def _isAttachedImage(attachmentFilename: str) -> bool:
    """Is the given attachment filename an image?
    """
    if '.' not in attachmentFilename:
        return False
    imageExt = (
        'png', 'jpg', 'jpeg', 'webp', 'avif', 'svg', 'gif'
    )
    ext = attachmentFilename.split('.')[-1]
    if ext in imageExt:
        return True
    return False


def _isAttachedVideo(attachmentFilename: str) -> bool:
    """Is the given attachment filename a video?
    """
    if '.' not in attachmentFilename:
        return False
    videoExt = (
        'mp4', 'webm', 'ogv'
    )
    ext = attachmentFilename.split('.')[-1]
    if ext in videoExt:
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
    attachmentStr = ''
    mediaStyleAdded = False
    for attach in postJsonObject['object']['attachment']:
        if not (attach.get('mediaType') and attach.get('url')):
            continue

        mediaType = attach['mediaType']
        imageDescription = ''
        if attach.get('name'):
            imageDescription = attach['name'].replace('"', "'")
        if _isImageMimeType(mediaType):
            imageUrl = attach['url']
            if _isAttachedImage(attach['url']) and 'svg' not in mediaType:
                if not attachmentStr:
                    attachmentStr += '<div class="media">\n'
                    mediaStyleAdded = True

                if attachmentCtr > 0:
                    attachmentStr += '<br>'
                if boxName == 'tlmedia':
                    galleryStr += '<div class="gallery">\n'
                    if not isMuted:
                        galleryStr += '  <a href="' + imageUrl + '">\n'
                        galleryStr += \
                            '    <img loading="lazy" src="' + \
                            imageUrl + '" alt="" title="">\n'
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

                attachmentStr += '<a href="' + imageUrl + '">'
                attachmentStr += \
                    '<img loading="lazy" src="' + imageUrl + \
                    '" alt="' + imageDescription + '" title="' + \
                    imageDescription + '" class="attachment"></a>\n'
                attachmentCtr += 1
        elif _isVideoMimeType(mediaType):
            if _isAttachedVideo(attach['url']):
                extension = attach['url'].split('.')[-1]
                if attachmentCtr > 0:
                    attachmentStr += '<br>'
                if boxName == 'tlmedia':
                    galleryStr += '<div class="gallery">\n'
                    if not isMuted:
                        galleryStr += '  <a href="' + attach['url'] + '">\n'
                        galleryStr += \
                            '    <figure id="videoContainer" ' + \
                            'data-fullscreen="false">\n' + \
                            '    <video id="video" controls ' + \
                            'preload="metadata">\n'
                        galleryStr += \
                            '      <source src="' + attach['url'] + \
                            '" alt="' + imageDescription + \
                            '" title="' + imageDescription + \
                            '" class="attachment" type="video/' + \
                            extension + '">'
                        idx = 'Your browser does not support the video tag.'
                        galleryStr += translate[idx]
                        galleryStr += '    </video>\n'
                        galleryStr += '    </figure>\n'
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
                    '<center><figure id="videoContainer" ' + \
                    'data-fullscreen="false">\n' + \
                    '    <video id="video" controls ' + \
                    'preload="metadata">\n'
                attachmentStr += \
                    '<source src="' + attach['url'] + '" alt="' + \
                    imageDescription + '" title="' + imageDescription + \
                    '" class="attachment" type="video/' + \
                    extension + '">'
                attachmentStr += \
                    translate['Your browser does not support the video tag.']
                attachmentStr += '</video></figure></center>'
                attachmentCtr += 1
        elif _isAudioMimeType(mediaType):
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
                        deleteStr + muteStr + '\n'
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
    if mediaStyleAdded:
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
                      avatarUrl: str, allowDownloads: bool,
                      signingPrivateKeyPem: str) -> str:
    """Returns the avatar image url
    """
    # get the avatar image url for the post actor
    if not avatarUrl:
        avatarUrl = \
            getPersonAvatarUrl(baseDir, postActor, personCache,
                               allowDownloads)
        avatarUrl = \
            updateAvatarImageCache(signingPrivateKeyPem,
                                   session, baseDir, httpPrefix,
                                   postActor, avatarUrl, personCache,
                                   allowDownloads)
    else:
        updateAvatarImageCache(signingPrivateKeyPem,
                               session, baseDir, httpPrefix,
                               postActor, avatarUrl, personCache,
                               allowDownloads)

    if not avatarUrl:
        avatarUrl = postActor + '/avatar.png'

    return avatarUrl


def htmlHideFromScreenReader(htmlStr: str) -> str:
    """Returns html which is hidden from screen readers
    """
    return '<span aria-hidden="true">' + htmlStr + '</span>'


def htmlKeyboardNavigation(banner: str, links: {}, accessKeys: {},
                           subHeading: str = None,
                           usersPath: str = None, translate: {} = None,
                           followApprovals: bool = False) -> str:
    """Given a set of links return the html for keyboard navigation
    """
    htmlStr = '<div class="transparent"><ul>\n'

    if banner:
        htmlStr += '<pre aria-label="">\n' + banner + '\n<br><br></pre>\n'

    if subHeading:
        htmlStr += '<strong><label class="transparent">' + \
            subHeading + '</label></strong><br>\n'

    # show new follower approvals
    if usersPath and translate and followApprovals:
        htmlStr += '<strong><label class="transparent">' + \
            '<a href="' + usersPath + '/followers#timeline">' + \
            translate['Approve follow requests'] + '</a>' + \
            '</label></strong><br><br>\n'

    # show the list of links
    for title, url in links.items():
        accessKeyStr = ''
        if accessKeys.get(title):
            accessKeyStr = 'accesskey="' + accessKeys[title] + '"'

        htmlStr += '<li><label class="transparent">' + \
            '<a href="' + str(url) + '" ' + accessKeyStr + '>' + \
            str(title) + '</a></label></li>\n'
    htmlStr += '</ul></div>\n'
    return htmlStr


def beginEditSection(label: str) -> str:
    """returns the html for begining a dropdown section on edit profile screen
    """
    return \
        '    <details><summary class="cw">' + label + '</summary>\n' + \
        '<div class="container">'


def endEditSection() -> str:
    """returns the html for ending a dropdown section on edit profile screen
    """
    return '    </div></details>\n'


def editTextField(label: str, name: str, value: str = "",
                  placeholder: str = "", required: bool = False) -> str:
    """Returns html for editing a text field
    """
    if value is None:
        value = ''
    placeholderStr = ''
    if placeholder:
        placeholderStr = ' placeholder="' + placeholder + '"'
    requiredStr = ''
    if required:
        requiredStr = ' required'
    return \
        '<label class="labels">' + label + '</label><br>\n' + \
        '      <input type="text" name="' + name + '" value="' + \
        value + '"' + placeholderStr + requiredStr + '>\n'


def editNumberField(label: str, name: str, value: int,
                    minValue: int, maxValue: int,
                    placeholder: int) -> str:
    """Returns html for editing an integer number field
    """
    if value is None:
        value = ''
    placeholderStr = ''
    if placeholder:
        placeholderStr = ' placeholder="' + str(placeholder) + '"'
    return \
        '<label class="labels">' + label + '</label><br>\n' + \
        '      <input type="number" name="' + name + '" value="' + \
        str(value) + '"' + placeholderStr + ' ' + \
        'min="' + str(minValue) + '" max="' + str(maxValue) + '" step="1">\n'


def editCurrencyField(label: str, name: str, value: str,
                      placeholder: str, required: bool) -> str:
    """Returns html for editing a currency field
    """
    if value is None:
        value = '0.00'
    placeholderStr = ''
    if placeholder:
        if placeholder.isdigit():
            placeholderStr = ' placeholder="' + str(placeholder) + '"'
    requiredStr = ''
    if required:
        requiredStr = ' required'
    return \
        '<label class="labels">' + label + '</label><br>\n' + \
        '      <input type="text" name="' + name + '" value="' + \
        str(value) + '"' + placeholderStr + ' ' + \
        ' pattern="^\\d{1,3}(,\\d{3})*(\\.\\d+)?" data-type="currency"' + \
        requiredStr + '>\n'


def editCheckBox(label: str, name: str, checked: bool) -> str:
    """Returns html for editing a checkbox field
    """
    checkedStr = ''
    if checked:
        checkedStr = ' checked'

    return \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="' + name + '"' + checkedStr + '> ' + label + '<br>\n'


def editTextArea(label: str, name: str, value: str,
                 height: int, placeholder: str, spellcheck: bool) -> str:
    """Returns html for editing a textarea field
    """
    if value is None:
        value = ''
    text = ''
    if label:
        text = '<label class="labels">' + label + '</label><br>\n'
    text += \
        '      <textarea id="message" placeholder=' + \
        '"' + placeholder + '" '
    text += 'name="' + name + '" '
    text += 'style="height:' + str(height) + 'px" '
    text += 'spellcheck="' + str(spellcheck).lower() + '">'
    text += value + '</textarea>\n'
    return text


def htmlSearchResultShare(baseDir: str, sharedItem: {}, translate: {},
                          httpPrefix: str, domainFull: str,
                          contactNickname: str, itemID: str,
                          actor: str, sharesFileType: str,
                          category: str) -> str:
    """Returns the html for an individual shared item
    """
    sharedItemsForm = '<div class="container">\n'
    sharedItemsForm += \
        '<p class="share-title">' + sharedItem['displayName'] + '</p>\n'
    if sharedItem.get('imageUrl'):
        sharedItemsForm += \
            '<a href="' + sharedItem['imageUrl'] + '">\n'
        sharedItemsForm += \
            '<img loading="lazy" src="' + sharedItem['imageUrl'] + \
            '" alt="Item image"></a>\n'
    sharedItemsForm += '<p>' + sharedItem['summary'] + '</p>\n<p>'
    if sharedItem.get('itemQty'):
        if sharedItem['itemQty'] > 1:
            sharedItemsForm += \
                '<b>' + translate['Quantity'] + \
                ':</b> ' + str(sharedItem['itemQty']) + '<br>'
    sharedItemsForm += \
        '<b>' + translate['Type'] + ':</b> ' + sharedItem['itemType'] + '<br>'
    sharedItemsForm += \
        '<b>' + translate['Category'] + ':</b> ' + \
        sharedItem['category'] + '<br>'
    if sharedItem.get('location'):
        sharedItemsForm += \
            '<b>' + translate['Location'] + ':</b> ' + \
            sharedItem['location'] + '<br>'
    contactTitleStr = translate['Contact']
    if sharedItem.get('itemPrice') and \
       sharedItem.get('itemCurrency'):
        if isfloat(sharedItem['itemPrice']):
            if float(sharedItem['itemPrice']) > 0:
                sharedItemsForm += \
                    ' <b>' + translate['Price'] + \
                    ':</b> ' + sharedItem['itemPrice'] + \
                    ' ' + sharedItem['itemCurrency']
                contactTitleStr = translate['Buy']
    sharedItemsForm += '</p>\n'
    contactActor = \
        localActorUrl(httpPrefix, contactNickname, domainFull)
    buttonStyleStr = 'button'
    if category == 'accommodation':
        contactTitleStr = translate['Request to stay']
        buttonStyleStr = 'contactbutton'

    sharedItemsForm += \
        '<p>' + \
        '<a href="' + actor + '?replydm=sharedesc:' + \
        sharedItem['displayName'] + '?mention=' + contactActor + \
        '?category=' + category + \
        '"><button class="' + buttonStyleStr + '">' + contactTitleStr + \
        '</button></a>\n' + \
        '<a href="' + contactActor + '"><button class="button">' + \
        translate['Profile'] + '</button></a>\n'

    # should the remove button be shown?
    showRemoveButton = False
    nickname = getNicknameFromActor(actor)
    if actor.endswith('/users/' + contactNickname):
        showRemoveButton = True
    elif isModerator(baseDir, nickname):
        showRemoveButton = True
    else:
        adminNickname = getConfigParam(baseDir, 'admin')
        if adminNickname:
            if actor.endswith('/users/' + adminNickname):
                showRemoveButton = True

    if showRemoveButton:
        if sharesFileType == 'shares':
            sharedItemsForm += \
                ' <a href="' + actor + '?rmshare=' + \
                itemID + '"><button class="button">' + \
                translate['Remove'] + '</button></a>\n'
        else:
            sharedItemsForm += \
                ' <a href="' + actor + '?rmwanted=' + \
                itemID + '"><button class="button">' + \
                translate['Remove'] + '</button></a>\n'
    sharedItemsForm += '</p></div>\n'
    return sharedItemsForm


def htmlShowShare(baseDir: str, domain: str, nickname: str,
                  httpPrefix: str, domainFull: str,
                  itemID: str, translate: {},
                  sharedItemsFederatedDomains: [],
                  defaultTimeline: str, theme: str,
                  sharesFileType: str, category: str) -> str:
    """Shows an individual shared item after selecting it from the left column
    """
    sharesJson = None

    shareUrl = itemID.replace('___', '://').replace('--', '/')
    contactNickname = getNicknameFromActor(shareUrl)
    if not contactNickname:
        return None

    if '://' + domainFull + '/' in shareUrl:
        # shared item on this instance
        sharesFilename = \
            acctDir(baseDir, contactNickname, domain) + '/' + \
            sharesFileType + '.json'
        if not os.path.isfile(sharesFilename):
            return None
        sharesJson = loadJson(sharesFilename)
    else:
        # federated shared item
        if sharesFileType == 'shares':
            catalogsDir = baseDir + '/cache/catalogs'
        else:
            catalogsDir = baseDir + '/cache/wantedItems'
        if not os.path.isdir(catalogsDir):
            return None
        for subdir, dirs, files in os.walk(catalogsDir):
            for f in files:
                if '#' in f:
                    continue
                if not f.endswith('.' + sharesFileType + '.json'):
                    continue
                federatedDomain = f.split('.')[0]
                if federatedDomain not in sharedItemsFederatedDomains:
                    continue
                sharesFilename = catalogsDir + '/' + f
                sharesJson = loadJson(sharesFilename)
                if not sharesJson:
                    continue
                if sharesJson.get(itemID):
                    break
            break

    if not sharesJson:
        return None
    if not sharesJson.get(itemID):
        return None
    sharedItem = sharesJson[itemID]
    actor = localActorUrl(httpPrefix, nickname, domainFull)

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, theme)

    shareStr = \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + \
        defaultTimeline + '" title="" alt="">\n'
    shareStr += '<img loading="lazy" class="timeline-banner" ' + \
        'alt="" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" /></a>\n' + \
        '</header><br>\n'
    shareStr += \
        htmlSearchResultShare(baseDir, sharedItem, translate, httpPrefix,
                              domainFull, contactNickname, itemID,
                              actor, sharesFileType, category)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'
    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')

    return htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None) + \
        shareStr + htmlFooter()


def setCustomBackground(baseDir: str, background: str,
                        newBackground: str) -> str:
    """Sets a custom background
    Returns the extension, if found
    """
    ext = 'jpg'
    if os.path.isfile(baseDir + '/img/' + background + '.' + ext):
        if not newBackground:
            newBackground = background
        if not os.path.isfile(baseDir + '/accounts/' +
                              newBackground + '.' + ext):
            copyfile(baseDir + '/img/' + background + '.' + ext,
                     baseDir + '/accounts/' + newBackground + '.' + ext)
        return ext
    return None
