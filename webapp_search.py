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
from utils import get_base_content_from_post
from utils import isAccountDir
from utils import get_config_param
from utils import get_full_domain
from utils import is_editor
from utils import load_json
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import locatePost
from utils import isPublicPost
from utils import firstParagraphFromString
from utils import searchBoxPosts
from utils import getAltPath
from utils import acct_dir
from utils import local_actor_url
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
                    base_dir: str, http_prefix: str,
                    searchStr: str) -> str:
    """Search results for emoji
    """
    # emoji.json is generated so that it can be customized and the changes
    # will be retained even if default_emoji.json is subsequently updated
    if not os.path.isfile(base_dir + '/emoji/emoji.json'):
        copyfile(base_dir + '/emoji/default_emoji.json',
                 base_dir + '/emoji/emoji.json')

    searchStr = searchStr.lower().replace(':', '').strip('\n').strip('\r')
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    emojiLookupFilename = base_dir + '/emoji/emoji.json'
    customEmojiLookupFilename = base_dir + '/emojicustom/emoji.json'

    # create header
    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    emojiForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    emojiForm += '<center><h1>' + \
        translate['Emoji Search'] + \
        '</h1></center>'

    # does the lookup file exist?
    if not os.path.isfile(emojiLookupFilename):
        emojiForm += '<center><h5>' + \
            translate['No results'] + '</h5></center>'
        emojiForm += htmlFooter()
        return emojiForm

    emojiJson = load_json(emojiLookupFilename)
    if emojiJson:
        if os.path.isfile(customEmojiLookupFilename):
            customEmojiJson = load_json(customEmojiLookupFilename)
            if customEmojiJson:
                emojiJson = dict(emojiJson, **customEmojiJson)

        results = {}
        for emojiName, filename in emojiJson.items():
            if searchStr in emojiName:
                results[emojiName] = filename + '.png'
        for emojiName, filename in emojiJson.items():
            if emojiName in searchStr:
                results[emojiName] = filename + '.png'

        if not results:
            emojiForm += '<center><h5>' + \
                translate['No results'] + '</h5></center>'

        headingShown = False
        emojiForm += '<center>'
        msgStr1 = translate['Copy the text then paste it into your post']
        msgStr2 = ':<img loading="lazy" class="searchEmoji" src="/emoji/'
        for emojiName, filename in results.items():
            if not os.path.isfile(base_dir + '/emoji/' + filename):
                if not os.path.isfile(base_dir + '/emojicustom/' + filename):
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


def _htmlSearchResultSharePage(actor: str, domain_full: str,
                               callingDomain: str, pageNumber: int,
                               searchStrLower: str, translate: {},
                               previous: bool) -> str:
    """Returns the html for the previous button on shared items search results
    """
    postActor = getAltPath(actor, domain_full, callingDomain)
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


def _htmlSharesResult(base_dir: str,
                      sharesJson: {}, pageNumber: int, resultsPerPage: int,
                      searchStrLowerList: [], currPage: int, ctr: int,
                      callingDomain: str, http_prefix: str, domain_full: str,
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
                    htmlSearchResultShare(base_dir, sharedItem, translate,
                                          http_prefix, domain_full,
                                          contactNickname,
                                          name, actor, sharesFileType,
                                          sharedItem['category'])
                if not resultsExist and currPage > 1:
                    # show the previous page button
                    sharedItemsForm += \
                        _htmlSearchResultSharePage(actor, domain_full,
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
                        _htmlSearchResultSharePage(actor, domain_full,
                                                   callingDomain,
                                                   pageNumber,
                                                   searchStrLower,
                                                   translate, False)
                    return resultsExist, currPage, ctr, sharedItemsForm
                ctr = 0
    return resultsExist, currPage, ctr, sharedItemsForm


def htmlSearchSharedItems(cssCache: {}, translate: {},
                          base_dir: str, searchStr: str,
                          pageNumber: int,
                          resultsPerPage: int,
                          http_prefix: str,
                          domain_full: str, actor: str,
                          callingDomain: str,
                          shared_items_federated_domains: [],
                          sharesFileType: str) -> str:
    """Search results for shared items
    """
    currPage = 1
    ctr = 0
    sharedItemsForm = ''
    searchStrLower = urllib.parse.unquote(searchStr)
    searchStrLower = searchStrLower.lower().strip('\n').strip('\r')
    searchStrLowerList = searchStrLower.split('+')
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    sharedItemsForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    if sharesFileType == 'shares':
        titleStr = translate['Shared Items Search']
    else:
        titleStr = translate['Wanted Items Search']
    sharedItemsForm += \
        '<center><h1>' + \
        '<a href="' + actor + '/search">' + titleStr + '</a></h1></center>'
    resultsExist = False
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if not isAccountDir(handle):
                continue
            contactNickname = handle.split('@')[0]
            sharesFilename = base_dir + '/accounts/' + handle + \
                '/' + sharesFileType + '.json'
            if not os.path.isfile(sharesFilename):
                continue

            sharesJson = load_json(sharesFilename)
            if not sharesJson:
                continue

            (resultsExist, currPage, ctr,
             resultStr) = _htmlSharesResult(base_dir, sharesJson, pageNumber,
                                            resultsPerPage,
                                            searchStrLowerList,
                                            currPage, ctr,
                                            callingDomain, http_prefix,
                                            domain_full,
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
        catalogsDir = base_dir + '/cache/catalogs'
    else:
        catalogsDir = base_dir + '/cache/wantedItems'
    if currPage <= pageNumber and os.path.isdir(catalogsDir):
        for subdir, dirs, files in os.walk(catalogsDir):
            for f in files:
                if '#' in f:
                    continue
                if not f.endswith('.' + sharesFileType + '.json'):
                    continue
                federatedDomain = f.split('.')[0]
                if federatedDomain not in shared_items_federated_domains:
                    continue
                sharesFilename = catalogsDir + '/' + f
                sharesJson = load_json(sharesFilename)
                if not sharesJson:
                    continue

                (resultsExist, currPage, ctr,
                 resultStr) = _htmlSharesResult(base_dir, sharesJson,
                                                pageNumber,
                                                resultsPerPage,
                                                searchStrLowerList,
                                                currPage, ctr,
                                                callingDomain, http_prefix,
                                                domain_full,
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
                             base_dir: str, path: str) -> str:
    """Search for an emoji by name
    """
    # emoji.json is generated so that it can be customized and the changes
    # will be retained even if default_emoji.json is subsequently updated
    if not os.path.isfile(base_dir + '/emoji/emoji.json'):
        copyfile(base_dir + '/emoji/default_emoji.json',
                 base_dir + '/emoji/emoji.json')

    actor = path.replace('/search', '')
    domain, port = getDomainFromActor(actor)

    setCustomBackground(base_dir, 'search-background', 'follow-background')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    emojiStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
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
               base_dir: str, path: str, domain: str,
               defaultTimeline: str, theme: str,
               text_mode_banner: str, accessKeys: {}) -> str:
    """Search called from the timeline icon
    """
    actor = path.replace('/search', '')
    searchNickname = getNicknameFromActor(actor)

    setCustomBackground(base_dir, 'search-background', 'follow-background')

    cssFilename = base_dir + '/epicyon-search.css'
    if os.path.isfile(base_dir + '/search.css'):
        cssFilename = base_dir + '/search.css'

    instanceTitle = get_config_param(base_dir, 'instanceTitle')
    followStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

    # show a banner above the search box
    searchBannerFile, searchBannerFilename = \
        getSearchBannerFile(base_dir, searchNickname, domain, theme)

    text_mode_bannerStr = htmlKeyboardNavigation(text_mode_banner, {}, {})
    if text_mode_bannerStr is None:
        text_mode_bannerStr = ''

    if os.path.isfile(searchBannerFilename):
        timelineKey = accessKeys['menuTimeline']
        usersPath = '/users/' + searchNickname
        followStr += \
            '<header>\n' + text_mode_bannerStr + \
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
        acct_dir(base_dir, searchNickname, domain) + '/.hashtagSwarm'
    swarmStr = ''
    if os.path.isfile(cachedHashtagSwarmFilename):
        try:
            with open(cachedHashtagSwarmFilename, 'r') as fp:
                swarmStr = fp.read()
        except OSError:
            print('EX: htmlSearch unable to read cached hashtag swarm ' +
                  cachedHashtagSwarmFilename)
    if not swarmStr:
        swarmStr = htmlHashTagSwarm(base_dir, actor, translate)
        if swarmStr:
            try:
                with open(cachedHashtagSwarmFilename, 'w+') as fp:
                    fp.write(swarmStr)
            except OSError:
                print('EX: htmlSearch unable to save cached hashtag swarm ' +
                      cachedHashtagSwarmFilename)

    followStr += '  <p class="hashtagswarm">' + swarmStr + '</p>\n'
    followStr += '  </center>\n'
    followStr += '  </div>\n'
    followStr += '</div>\n'
    followStr += htmlFooter()
    return followStr


def htmlSkillsSearch(actor: str,
                     cssCache: {}, translate: {}, base_dir: str,
                     http_prefix: str,
                     skillsearch: str, instanceOnly: bool,
                     postsPerPage: int) -> str:
    """Show a page containing search results for a skill
    """
    if skillsearch.startswith('*'):
        skillsearch = skillsearch[1:].strip()

    skillsearch = skillsearch.lower().strip('\n').strip('\r')

    results = []
    # search instance accounts
    for subdir, dirs, files in os.walk(base_dir + '/accounts/'):
        for f in files:
            if not f.endswith('.json'):
                continue
            if not isAccountDir(f):
                continue
            actorFilename = os.path.join(subdir, f)
            actor_json = load_json(actorFilename)
            if actor_json:
                if actor_json.get('id') and \
                   noOfActorSkills(actor_json) > 0 and \
                   actor_json.get('name') and \
                   actor_json.get('icon'):
                    actor = actor_json['id']
                    actorSkillsList = actor_json['hasOccupation']['skills']
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
                            actor_json['name'] + \
                            ';' + actor_json['icon']['url']
                        if indexStr not in results:
                            results.append(indexStr)
        break
    if not instanceOnly:
        # search actor cache
        for subdir, dirs, files in os.walk(base_dir + '/cache/actors/'):
            for f in files:
                if not f.endswith('.json'):
                    continue
                if not isAccountDir(f):
                    continue
                actorFilename = os.path.join(subdir, f)
                cachedActorJson = load_json(actorFilename)
                if cachedActorJson:
                    if cachedActorJson.get('actor'):
                        actor_json = cachedActorJson['actor']
                        if actor_json.get('id') and \
                           noOfActorSkills(actor_json) > 0 and \
                           actor_json.get('name') and \
                           actor_json.get('icon'):
                            actor = actor_json['id']
                            actorSkillsList = \
                                actor_json['hasOccupation']['skills']
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
                                    actor_json['name'] + \
                                    ';' + actor_json['icon']['url']
                                if indexStr not in results:
                                    results.append(indexStr)
            break

    results.sort(reverse=True)

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    skillSearchForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
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


def htmlHistorySearch(cssCache: {}, translate: {}, base_dir: str,
                      http_prefix: str,
                      nickname: str, domain: str,
                      historysearch: str,
                      postsPerPage: int, pageNumber: int,
                      project_version: str,
                      recentPostsCache: {},
                      max_recent_posts: int,
                      session,
                      cached_webfingers,
                      person_cache: {},
                      port: int,
                      yt_replace_domain: str,
                      twitter_replacement_domain: str,
                      show_published_date_only: bool,
                      peertube_instances: [],
                      allow_local_network_access: bool,
                      theme_name: str, boxName: str,
                      system_language: str,
                      max_like_count: int,
                      signing_priv_key_pem: str,
                      cw_lists: {},
                      lists_enabled: str) -> str:
    """Show a page containing search results for your post history
    """
    if historysearch.startswith("'"):
        historysearch = historysearch[1:].strip()

    historysearch = historysearch.lower().strip('\n').strip('\r')

    boxFilenames = \
        searchBoxPosts(base_dir, nickname, domain,
                       historysearch, postsPerPage, boxName)

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    historySearchForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

    # add the page title
    domain_full = get_full_domain(domain, port)
    actor = local_actor_url(http_prefix, nickname, domain_full)
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

    separatorStr = htmlPostSeparator(base_dir, None)

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
        post_json_object = load_json(postFilename)
        if not post_json_object:
            index += 1
            continue
        showIndividualPostIcons = True
        allow_deletion = False
        postStr = \
            individualPostAsHtml(signing_priv_key_pem,
                                 True, recentPostsCache,
                                 max_recent_posts,
                                 translate, None,
                                 base_dir, session, cached_webfingers,
                                 person_cache,
                                 nickname, domain, port,
                                 post_json_object,
                                 None, True, allow_deletion,
                                 http_prefix, project_version,
                                 'search',
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 peertube_instances,
                                 allow_local_network_access,
                                 theme_name, system_language, max_like_count,
                                 showIndividualPostIcons,
                                 showIndividualPostIcons,
                                 False, False, False, False,
                                 cw_lists, lists_enabled)
        if postStr:
            historySearchForm += separatorStr + postStr
        index += 1

    historySearchForm += htmlFooter()
    return historySearchForm


def htmlHashtagSearch(cssCache: {},
                      nickname: str, domain: str, port: int,
                      recentPostsCache: {}, max_recent_posts: int,
                      translate: {},
                      base_dir: str, hashtag: str, pageNumber: int,
                      postsPerPage: int,
                      session, cached_webfingers: {}, person_cache: {},
                      http_prefix: str, project_version: str,
                      yt_replace_domain: str,
                      twitter_replacement_domain: str,
                      show_published_date_only: bool,
                      peertube_instances: [],
                      allow_local_network_access: bool,
                      theme_name: str, system_language: str,
                      max_like_count: int,
                      signing_priv_key_pem: str,
                      cw_lists: {}, lists_enabled: str) -> str:
    """Show a page containing search results for a hashtag
    or after selecting a hashtag from the swarm
    """
    if hashtag.startswith('#'):
        hashtag = hashtag[1:]
    hashtag = urllib.parse.unquote(hashtag)
    hashtagIndexFile = base_dir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtagIndexFile):
        if hashtag != hashtag.lower():
            hashtag = hashtag.lower()
            hashtagIndexFile = base_dir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtagIndexFile):
        print('WARN: hashtag file not found ' + hashtagIndexFile)
        return None

    separatorStr = htmlPostSeparator(base_dir, None)

    # check that the directory for the nickname exists
    if nickname:
        accountDir = acct_dir(base_dir, nickname, domain)
        if not os.path.isdir(accountDir):
            nickname = None

    # read the index
    with open(hashtagIndexFile, 'r') as f:
        lines = f.readlines()

    # read the css
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

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
        get_config_param(base_dir, 'instanceTitle')
    hashtagSearchForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
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
    if is_editor(base_dir, nickname):
        category = getHashtagCategory(base_dir, hashtag)
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
        postFilename = locatePost(base_dir, nickname, domain, postId)
        if not postFilename:
            index += 1
            continue
        post_json_object = load_json(postFilename)
        if not post_json_object:
            index += 1
            continue
        if not isPublicPost(post_json_object):
            index += 1
            continue
        showIndividualPostIcons = False
        if nickname:
            showIndividualPostIcons = True
        allow_deletion = False
        showRepeats = showIndividualPostIcons
        showIcons = showIndividualPostIcons
        manuallyApprovesFollowers = False
        showPublicOnly = False
        storeToCache = False
        allowDownloads = True
        avatarUrl = None
        showAvatarOptions = True
        postStr = \
            individualPostAsHtml(signing_priv_key_pem,
                                 allowDownloads, recentPostsCache,
                                 max_recent_posts,
                                 translate, None,
                                 base_dir, session, cached_webfingers,
                                 person_cache,
                                 nickname, domain, port,
                                 post_json_object,
                                 avatarUrl, showAvatarOptions,
                                 allow_deletion,
                                 http_prefix, project_version,
                                 'search',
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 peertube_instances,
                                 allow_local_network_access,
                                 theme_name, system_language, max_like_count,
                                 showRepeats, showIcons,
                                 manuallyApprovesFollowers,
                                 showPublicOnly,
                                 storeToCache, False, cw_lists,
                                 lists_enabled)
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
                     recentPostsCache: {}, max_recent_posts: int,
                     translate: {},
                     base_dir: str, hashtag: str,
                     postsPerPage: int,
                     session, cached_webfingers: {}, person_cache: {},
                     http_prefix: str, project_version: str,
                     yt_replace_domain: str,
                     twitter_replacement_domain: str,
                     system_language: str) -> str:
    """Show an rss feed for a hashtag
    """
    if hashtag.startswith('#'):
        hashtag = hashtag[1:]
    hashtag = urllib.parse.unquote(hashtag)
    hashtagIndexFile = base_dir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtagIndexFile):
        if hashtag != hashtag.lower():
            hashtag = hashtag.lower()
            hashtagIndexFile = base_dir + '/tags/' + hashtag + '.txt'
    if not os.path.isfile(hashtagIndexFile):
        print('WARN: hashtag file not found ' + hashtagIndexFile)
        return None

    # check that the directory for the nickname exists
    if nickname:
        accountDir = acct_dir(base_dir, nickname, domain)
        if not os.path.isdir(accountDir):
            nickname = None

    # read the index
    lines = []
    with open(hashtagIndexFile, 'r') as f:
        lines = f.readlines()
    if not lines:
        return None

    domain_full = get_full_domain(domain, port)

    maxFeedLength = 10
    hashtagFeed = \
        rss2TagHeader(hashtag, http_prefix, domain_full)
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
        postFilename = locatePost(base_dir, nickname, domain, postId)
        if not postFilename:
            index += 1
            if index >= maxFeedLength:
                break
            continue
        post_json_object = load_json(postFilename)
        if post_json_object:
            if not isPublicPost(post_json_object):
                index += 1
                if index >= maxFeedLength:
                    break
                continue
            # add to feed
            if post_json_object['object'].get('content') and \
               post_json_object['object'].get('attributedTo') and \
               post_json_object['object'].get('published'):
                published = post_json_object['object']['published']
                pubDate = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                rssDateStr = pubDate.strftime("%a, %d %b %Y %H:%M:%S UT")
                hashtagFeed += '     <item>'
                hashtagFeed += \
                    '         <author>' + \
                    post_json_object['object']['attributedTo'] + \
                    '</author>'
                if post_json_object['object'].get('summary'):
                    hashtagFeed += \
                        '         <title>' + \
                        post_json_object['object']['summary'] + \
                        '</title>'
                description = \
                    get_base_content_from_post(post_json_object,
                                               system_language)
                description = firstParagraphFromString(description)
                hashtagFeed += \
                    '         <description>' + description + '</description>'
                hashtagFeed += \
                    '         <pubDate>' + rssDateStr + '</pubDate>'
                if post_json_object['object'].get('attachment'):
                    for attach in post_json_object['object']['attachment']:
                        if not attach.get('url'):
                            continue
                        hashtagFeed += \
                            '         <link>' + attach['url'] + '</link>'
                hashtagFeed += '     </item>'
        index += 1
        if index >= maxFeedLength:
            break

    return hashtagFeed + rss2TagFooter()
