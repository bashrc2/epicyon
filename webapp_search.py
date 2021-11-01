__filename__ = "webapp_search.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
import urllib.parse
from datetime import datetime
from utils import getBaseContentFromPost
from utils import isAccountDir
from utils import getConfigParam
from utils import getFullDomain
from utils import isEditor
from utils import loadJson
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import locatePost
from utils import isPublicPost
from utils import firstParagraphFromString
from utils import searchBoxPosts
from utils import getAltPath
from utils import acctDir
from utils import localActorUrl
from skills import noOfActorSkills
from skills import getSkillsFromList
from categories import getHashtagCategory
from feeds import rss2TagHeader
from feeds import rss2TagFooter
from webapp_utils import setCustomBackground
from webapp_utils import htmlKeyboardNavigation
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import getSearchBannerFile
from webapp_utils import htmlPostSeparator
from webapp_utils import htmlSearchResultShare
from webapp_post import individualPostAsHtml
from webapp_hashtagswarm import htmlHashTagSwarm


def htmlSearchEmoji(cssCache: {}, translate: {},
                    baseDir: str, httpPrefix: str,
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

    emojiLookupFilename = baseDir + '/emoji/emoji.json'
    customEmojiLookupFilename = baseDir + '/emojicustom/emoji.json'

    # create header
    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    emojiForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
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
        if os.path.isfile(customEmojiLookupFilename):
            customEmojiJson = loadJson(customEmojiLookupFilename)
            if customEmojiJson:
                emojiJson = dict(emojiJson, **customEmojiJson)
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
            if not os.path.isfile(baseDir + '/emoji/' + filename):
                if not os.path.isfile(baseDir + '/customemoji/' + filename):
                    continue
            if not headingShown:
                emojiForm += \
                    '<center><h5>' + msgStr1 + '</h5></center>'
                headingShown = True
            emojiForm += \
                '<h3>:' + emojiName + msgStr2 + filename + '"/></h3>'
        emojiForm += '</center>'

    emojiForm += htmlFooter()
    return emojiForm


def _matchSharedItem(searchStrLowerList: [],
                     sharedItem: {}) -> bool:
    """Returns true if the shared item matches search criteria
    """
    for searchSubstr in searchStrLowerList:
        searchSubstr = searchSubstr.strip()
        if sharedItem.get('location'):
            if searchSubstr in sharedItem['location'].lower():
                return True
        if searchSubstr in sharedItem['summary'].lower():
            return True
        elif searchSubstr in sharedItem['displayName'].lower():
            return True
        elif searchSubstr in sharedItem['category'].lower():
            return True
    return False


def _htmlSearchResultSharePage(actor: str, domainFull: str,
                               callingDomain: str, pageNumber: int,
                               searchStrLower: str, translate: {},
                               previous: bool) -> str:
    """Returns the html for the previous button on shared items search results
    """
    postActor = getAltPath(actor, domainFull, callingDomain)
    # previous page link, needs to be a POST
    if previous:
        pageNumber -= 1
        titleStr = translate['Page up']
        imageUrl = 'pageup.png'
    else:
        pageNumber += 1
        titleStr = translate['Page down']
        imageUrl = 'pagedown.png'
    sharedItemsForm = \
        '<form method="POST" action="' + postActor + '/searchhandle?page=' + \
        str(pageNumber) + '">\n'
    sharedItemsForm += \
        '  <input type="hidden" ' + 'name="actor" value="' + actor + '">\n'
    sharedItemsForm += \
        '  <input type="hidden" ' + 'name="searchtext" value="' + \
        searchStrLower + '"><br>\n'
    sharedItemsForm += \
        '  <center>\n' + '    <a href="' + actor + \
        '" type="submit" name="submitSearch">\n'
    sharedItemsForm += \
        '    <img loading="lazy" ' + 'class="pageicon" src="/icons' + \
        '/' + imageUrl + '" title="' + titleStr + \
        '" alt="' + titleStr + '"/></a>\n'
    sharedItemsForm += '  </center>\n'
    sharedItemsForm += '</form>\n'
    return sharedItemsForm


def _htmlSharesResult(baseDir: str,
                      sharesJson: {}, pageNumber: int, resultsPerPage: int,
                      searchStrLowerList: [], currPage: int, ctr: int,
                      callingDomain: str, httpPrefix: str, domainFull: str,
                      contactNickname: str, actor: str,
                      resultsExist: bool, searchStrLower: str, translate: {},
                      sharesFileType: str) -> (bool, int, int, str):
    """Result for shared items search
    """
    sharedItemsForm = ''
    if currPage > pageNumber:
        return resultsExist, currPage, ctr, sharedItemsForm

    for name, sharedItem in sharesJson.items():
        if _matchSharedItem(searchStrLowerList, sharedItem):
            if currPage == pageNumber:
                # show individual search result
                sharedItemsForm += \
                    htmlSearchResultShare(baseDir, sharedItem, translate,
                                          httpPrefix, domainFull,
                                          contactNickname,
                                          name, actor, sharesFileType,
                                          sharedItem['category'])
                if not resultsExist and currPage > 1:
                    # show the previous page button
                    sharedItemsForm += \
                        _htmlSearchResultSharePage(actor, domainFull,
                                                   callingDomain,
                                                   pageNumber,
                                                   searchStrLower,
                                                   translate, True)
                resultsExist = True
            ctr += 1
            if ctr >= resultsPerPage:
                currPage += 1
                if currPage > pageNumber:
                    # show the next page button
                    sharedItemsForm += \
                        _htmlSearchResultSharePage(actor, domainFull,
                                                   callingDomain,
                                                   pageNumber,
                                                   searchStrLower,
                                                   translate, False)
                    return resultsExist, currPage, ctr, sharedItemsForm
                ctr = 0
    return resultsExist, currPage, ctr, sharedItemsForm


def htmlSearchSharedItems(cssCache: {}, translate: {},
                          baseDir: str, searchStr: str,
                          pageNumber: int,
                          resultsPerPage: int,
                          httpPrefix: str,
                          domainFull: str, actor: str,
                          callingDomain: str,
                          sharedItemsFederatedDomains: [],
                          sharesFileType: str) -> str:
    """Search results for shared items
    """
    currPage = 1
    ctr = 0
    sharedItemsForm = ''
    searchStrLower = urllib.parse.unquote(searchStr)
    searchStrLower = searchStrLower.lower().strip('\n').strip('\r')
    searchStrLowerList = searchStrLower.split('+')
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    sharedItemsForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    if sharesFileType == 'shares':
        titleStr = translate['Shared Items Search']
    else:
        titleStr = translate['Wanted Items Search']
    sharedItemsForm += \
        '<center><h1>' + \
        '<a href="' + actor + '/search">' + titleStr + '</a></h1></center>'
    resultsExist = False
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if not isAccountDir(handle):
                continue
            contactNickname = handle.split('@')[0]
            sharesFilename = baseDir + '/accounts/' + handle + \
                '/' + sharesFileType + '.json'
            if not os.path.isfile(sharesFilename):
                continue

            sharesJson = loadJson(sharesFilename)
            if not sharesJson:
                continue

            (resultsExist, currPage, ctr,
             resultStr) = _htmlSharesResult(baseDir, sharesJson, pageNumber,
                                            resultsPerPage,
                                            searchStrLowerList,
                                            currPage, ctr,
                                            callingDomain, httpPrefix,
                                            domainFull,
                                            contactNickname,
                                            actor, resultsExist,
                                            searchStrLower, translate,
                                            sharesFileType)
            sharedItemsForm += resultStr

            if currPage > pageNumber:
                break
        break

    # search federated shared items
    if sharesFileType == 'shares':
        catalogsDir = baseDir + '/cache/catalogs'
    else:
        catalogsDir = baseDir + '/cache/wantedItems'
    if currPage <= pageNumber and os.path.isdir(catalogsDir):
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

                (resultsExist, currPage, ctr,
                 resultStr) = _htmlSharesResult(baseDir, sharesJson,
                                                pageNumber,
                                                resultsPerPage,
                                                searchStrLowerList,
                                                currPage, ctr,
                                                callingDomain, httpPrefix,
                                                domainFull,
                                                contactNickname,
                                                actor, resultsExist,
                                                searchStrLower, translate,
                                                sharesFileType)
                sharedItemsForm += resultStr

                if currPage > pageNumber:
                    break
            break

    if not resultsExist:
        sharedItemsForm += \
            '<center><h5>' + translate['No results'] + '</h5></center>\n'
    sharedItemsForm += htmlFooter()
    return sharedItemsForm


def htmlSearchEmojiTextEntry(cssCache: {}, translate: {},
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

    setCustomBackground(baseDir, 'search-background', 'follow-background')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    emojiStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    emojiStr += '<div class="follow">\n'
    emojiStr += '  <div class="followAvatar">\n'
    emojiStr += '  <center>\n'
    emojiStr += \
        '  <p class="followText">' + \
        translate['Enter an emoji name to search for'] + '</p>\n'
    emojiStr += '  <form role="search" method="POST" action="' + \
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


def htmlSearch(cssCache: {}, translate: {},
               baseDir: str, path: str, domain: str,
               defaultTimeline: str, theme: str,
               textModeBanner: str, accessKeys: {}) -> str:
    """Search called from the timeline icon
    """
    actor = path.replace('/search', '')
    searchNickname = getNicknameFromActor(actor)

    setCustomBackground(baseDir, 'search-background', 'follow-background')

    cssFilename = baseDir + '/epicyon-search.css'
    if os.path.isfile(baseDir + '/search.css'):
        cssFilename = baseDir + '/search.css'

    instanceTitle = getConfigParam(baseDir, 'instanceTitle')
    followStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    # show a banner above the search box
    searchBannerFile, searchBannerFilename = \
        getSearchBannerFile(baseDir, searchNickname, domain, theme)

    textModeBannerStr = htmlKeyboardNavigation(textModeBanner, {}, {})
    if textModeBannerStr is None:
        textModeBannerStr = ''

    if os.path.isfile(searchBannerFilename):
        timelineKey = accessKeys['menuTimeline']
        usersPath = '/users/' + searchNickname
        followStr += \
            '<header>\n' + textModeBannerStr + \
            '<a href="' + usersPath + '/' + defaultTimeline + '" title="' + \
            translate['Switch to timeline view'] + '" alt="' + \
            translate['Switch to timeline view'] + '" ' + \
            'accesskey="' + timelineKey + '">\n'
        followStr += '<img loading="lazy" class="timeline-banner" src="' + \
            usersPath + '/' + searchBannerFile + '" alt="" /></a>\n' + \
            '</header>\n'

    # show the search box
    followStr += '<div class="follow">\n'
    followStr += '  <div class="followAvatar">\n'
    followStr += '  <center>\n'
    followStr += \
        '  <p class="followText">' + translate['Search screen text'] + '</p>\n'
    followStr += '  <form role="search" method="POST" ' + \
        'accept-charset="UTF-8" action="' + actor + '/searchhandle">\n'
    followStr += \
        '    <input type="hidden" name="actor" value="' + actor + '">\n'
    followStr += '    <input type="text" name="searchtext" autofocus><br>\n'
    submitKey = accessKeys['submitButton']
    followStr += '    <button type="submit" class="button" ' + \
        'name="submitSearch" accesskey="' + submitKey + '">' + \
        translate['Submit'] + '</button>\n'
    followStr += '  </form>\n'

    cachedHashtagSwarmFilename = \
        acctDir(baseDir, searchNickname, domain) + '/.hashtagSwarm'
    swarmStr = ''
    if os.path.isfile(cachedHashtagSwarmFilename):
        try:
            with open(cachedHashtagSwarmFilename, 'r') as fp:
                swarmStr = fp.read()
        except BaseException:
            print('EX: htmlSearch unable to read cached hashtag swarm ' +
                  cachedHashtagSwarmFilename)
            pass
    if not swarmStr:
        swarmStr = htmlHashTagSwarm(baseDir, actor, translate)
        if swarmStr:
            try:
                with open(cachedHashtagSwarmFilename, 'w+') as fp:
                    fp.write(swarmStr)
            except BaseException:
                print('EX: htmlSearch unable to save cached hashtag swarm ' +
                      cachedHashtagSwarmFilename)
                pass

    followStr += '  <p class="hashtagswarm">' + swarmStr + '</p>\n'
    followStr += '  </center>\n'
    followStr += '  </div>\n'
    followStr += '</div>\n'
    followStr += htmlFooter()
    return followStr


def htmlSkillsSearch(actor: str,
                     cssCache: {}, translate: {}, baseDir: str,
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
            if not isAccountDir(f):
                continue
            actorFilename = os.path.join(subdir, f)
            actorJson = loadJson(actorFilename)
            if actorJson:
                if actorJson.get('id') and \
                   noOfActorSkills(actorJson) > 0 and \
                   actorJson.get('name') and \
                   actorJson.get('icon'):
                    actor = actorJson['id']
                    actorSkillsList = actorJson['hasOccupation']['skills']
                    skills = getSkillsFromList(actorSkillsList)
                    for skillName, skillLevel in skills.items():
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
        break
    if not instanceOnly:
        # search actor cache
        for subdir, dirs, files in os.walk(baseDir + '/cache/actors/'):
            for f in files:
                if not f.endswith('.json'):
                    continue
                if not isAccountDir(f):
                    continue
                actorFilename = os.path.join(subdir, f)
                cachedActorJson = loadJson(actorFilename)
                if cachedActorJson:
                    if cachedActorJson.get('actor'):
                        actorJson = cachedActorJson['actor']
                        if actorJson.get('id') and \
                           noOfActorSkills(actorJson) > 0 and \
                           actorJson.get('name') and \
                           actorJson.get('icon'):
                            actor = actorJson['id']
                            actorSkillsList = \
                                actorJson['hasOccupation']['skills']
                            skills = getSkillsFromList(actorSkillsList)
                            for skillName, skillLevel in skills.items():
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
            break

    results.sort(reverse=True)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    skillSearchForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    skillSearchForm += \
        '<center><h1><a href = "' + actor + '/search">' + \
        translate['Skills search'] + ': ' + \
        skillsearch + \
        '</a></h1></center>'

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
                '" alt="" /><span class="search-result-text">' + actorName + \
                '</span></a></div>'
            ctr += 1
            if ctr >= postsPerPage:
                break
        skillSearchForm += '</center>'
    skillSearchForm += htmlFooter()
    return skillSearchForm


def htmlHistorySearch(cssCache: {}, translate: {}, baseDir: str,
                      httpPrefix: str,
                      nickname: str, domain: str,
                      historysearch: str,
                      postsPerPage: int, pageNumber: int,
                      projectVersion: str,
                      recentPostsCache: {},
                      maxRecentPosts: int,
                      session,
                      cachedWebfingers,
                      personCache: {},
                      port: int,
                      YTReplacementDomain: str,
                      twitterReplacementDomain: str,
                      showPublishedDateOnly: bool,
                      peertubeInstances: [],
                      allowLocalNetworkAccess: bool,
                      themeName: str, boxName: str,
                      systemLanguage: str,
                      maxLikeCount: int,
                      signingPrivateKeyPem: str,
                      CWlists: {},
                      listsEnabled: str) -> str:
    """Show a page containing search results for your post history
    """
    if historysearch.startswith("'"):
        historysearch = historysearch[1:].strip()

    historysearch = historysearch.lower().strip('\n').strip('\r')

    boxFilenames = \
        searchBoxPosts(baseDir, nickname, domain,
                       historysearch, postsPerPage, boxName)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    historySearchForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    # add the page title
    domainFull = getFullDomain(domain, port)
    actor = localActorUrl(httpPrefix, nickname, domainFull)
    historySearchTitle = '🔍 ' + translate['Your Posts']
    if boxName == 'bookmarks':
        historySearchTitle = '🔍 ' + translate['Bookmarks']

    historySearchForm += \
        '<center><h1><a href="' + actor + '/search">' + \
        historySearchTitle + '</a></h1></center>'

    if len(boxFilenames) == 0:
        historySearchForm += \
            '<center><h5>' + translate['No results'] + \
            '</h5></center>'
        return historySearchForm

    separatorStr = htmlPostSeparator(baseDir, None)

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
        postStr = \
            individualPostAsHtml(signingPrivateKeyPem,
                                 True, recentPostsCache,
                                 maxRecentPosts,
                                 translate, None,
                                 baseDir, session, cachedWebfingers,
                                 personCache,
                                 nickname, domain, port,
                                 postJsonObject,
                                 None, True, allowDeletion,
                                 httpPrefix, projectVersion,
                                 'search',
                                 YTReplacementDomain,
                                 twitterReplacementDomain,
                                 showPublishedDateOnly,
                                 peertubeInstances,
                                 allowLocalNetworkAccess,
                                 themeName, systemLanguage, maxLikeCount,
                                 showIndividualPostIcons,
                                 showIndividualPostIcons,
                                 False, False, False, False,
                                 CWlists, listsEnabled)
        if postStr:
            historySearchForm += separatorStr + postStr
        index += 1

    historySearchForm += htmlFooter()
    return historySearchForm


def htmlHashtagSearch(cssCache: {},
                      nickname: str, domain: str, port: int,
                      recentPostsCache: {}, maxRecentPosts: int,
                      translate: {},
                      baseDir: str, hashtag: str, pageNumber: int,
                      postsPerPage: int,
                      session, cachedWebfingers: {}, personCache: {},
                      httpPrefix: str, projectVersion: str,
                      YTReplacementDomain: str,
                      twitterReplacementDomain: str,
                      showPublishedDateOnly: bool,
                      peertubeInstances: [],
                      allowLocalNetworkAccess: bool,
                      themeName: str, systemLanguage: str,
                      maxLikeCount: int,
                      signingPrivateKeyPem: str,
                      CWlists: {}, listsEnabled: str) -> str:
    """Show a page containing search results for a hashtag
    or after selecting a hashtag from the swarm
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

    separatorStr = htmlPostSeparator(baseDir, None)

    # check that the directory for the nickname exists
    if nickname:
        accountDir = acctDir(baseDir, nickname, domain)
        if not os.path.isdir(accountDir):
            nickname = None

    # read the index
    with open(hashtagIndexFile, 'r') as f:
        lines = f.readlines()

    # read the css
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

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
    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    hashtagSearchForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    if nickname:
        hashtagSearchForm += '<center>\n' + \
            '<h1><a href="/users/' + nickname + '/search">#' + \
            hashtag + '</a></h1>\n'
    else:
        hashtagSearchForm += '<center>\n' + \
            '<h1>#' + hashtag + '</h1>\n'

    # RSS link for hashtag feed
    hashtagSearchForm += '<a href="/tags/rss2/' + hashtag + '">'
    hashtagSearchForm += \
        '<img style="width:3%;min-width:50px" ' + \
        'loading="lazy" alt="RSS 2.0" title="RSS 2.0" src="/' + \
        'icons/logorss.png" /></a></center>\n'

    # edit the category for this hashtag
    if isEditor(baseDir, nickname):
        category = getHashtagCategory(baseDir, hashtag)
        hashtagSearchForm += '<div class="hashtagCategoryContainer">\n'
        hashtagSearchForm += '  <form enctype="multipart/form-data" ' + \
            'method="POST" accept-charset="UTF-8" action="' + \
            '/users/' + nickname + '/tags/' + hashtag + \
            '/sethashtagcategory">\n'
        hashtagSearchForm += '    <center>\n'
        hashtagSearchForm += translate['Category']
        hashtagSearchForm += \
            '      <input type="text" style="width: 20ch" ' + \
            'name="hashtagCategory" value="' + category + '">\n'
        hashtagSearchForm += \
            '      <button type="submit" class="button" name="submitYes">' + \
            translate['Submit'] + '</button>\n'
        hashtagSearchForm += '    </center>\n'
        hashtagSearchForm += '  </form>\n'
        hashtagSearchForm += '</div>\n'

    if startIndex > 0:
        # previous page link
        hashtagSearchForm += \
            '  <center>\n' + \
            '    <a href="/users/' + nickname + \
            '/tags/' + hashtag + '?page=' + \
            str(pageNumber - 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            'icons/pageup.png" title="' + \
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
        if not postJsonObject:
            index += 1
            continue
        if not isPublicPost(postJsonObject):
            index += 1
            continue
        showIndividualPostIcons = False
        if nickname:
            showIndividualPostIcons = True
        allowDeletion = False
        showRepeats = showIndividualPostIcons
        showIcons = showIndividualPostIcons
        manuallyApprovesFollowers = False
        showPublicOnly = False
        storeToCache = False
        allowDownloads = True
        avatarUrl = None
        showAvatarOptions = True
        postStr = \
            individualPostAsHtml(signingPrivateKeyPem,
                                 allowDownloads, recentPostsCache,
                                 maxRecentPosts,
                                 translate, None,
                                 baseDir, session, cachedWebfingers,
                                 personCache,
                                 nickname, domain, port,
                                 postJsonObject,
                                 avatarUrl, showAvatarOptions,
                                 allowDeletion,
                                 httpPrefix, projectVersion,
                                 'search',
                                 YTReplacementDomain,
                                 twitterReplacementDomain,
                                 showPublishedDateOnly,
                                 peertubeInstances,
                                 allowLocalNetworkAccess,
                                 themeName, systemLanguage, maxLikeCount,
                                 showRepeats, showIcons,
                                 manuallyApprovesFollowers,
                                 showPublicOnly,
                                 storeToCache, False, CWlists,
                                 listsEnabled)
        if postStr:
            hashtagSearchForm += separatorStr + postStr
        index += 1

    if endIndex < noOfLines - 1:
        # next page link
        hashtagSearchForm += \
            '  <center>\n' + \
            '    <a href="/users/' + nickname + '/tags/' + hashtag + \
            '?page=' + str(pageNumber + 1) + \
            '"><img loading="lazy" class="pageicon" src="/icons' + \
            '/pagedown.png" title="' + translate['Page down'] + \
            '" alt="' + translate['Page down'] + '"></a>' + \
            '  </center>'
    hashtagSearchForm += htmlFooter()
    return hashtagSearchForm


def rssHashtagSearch(nickname: str, domain: str, port: int,
                     recentPostsCache: {}, maxRecentPosts: int,
                     translate: {},
                     baseDir: str, hashtag: str,
                     postsPerPage: int,
                     session, cachedWebfingers: {}, personCache: {},
                     httpPrefix: str, projectVersion: str,
                     YTReplacementDomain: str,
                     twitterReplacementDomain: str,
                     systemLanguage: str) -> str:
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
        accountDir = acctDir(baseDir, nickname, domain)
        if not os.path.isdir(accountDir):
            nickname = None

    # read the index
    lines = []
    with open(hashtagIndexFile, 'r') as f:
        lines = f.readlines()
    if not lines:
        return None

    domainFull = getFullDomain(domain, port)

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
                description = \
                    getBaseContentFromPost(postJsonObject, systemLanguage)
                description = firstParagraphFromString(description)
                hashtagFeed += \
                    '         <description>' + description + '</description>'
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
