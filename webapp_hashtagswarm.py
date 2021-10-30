__filename__ = "webapp_hashtagswarm.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from datetime import datetime
from utils import getNicknameFromActor
from utils import getConfigParam
from categories import getHashtagCategories
from categories import getHashtagCategory
from webapp_utils import setCustomBackground
from webapp_utils import getSearchBannerFile
from webapp_utils import getContentWarningButton
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def getHashtagCategoriesFeed(baseDir: str,
                             hashtagCategories: {} = None) -> str:
    """Returns an rss feed for hashtag categories
    """
    if not hashtagCategories:
        hashtagCategories = getHashtagCategories(baseDir)
    if not hashtagCategories:
        return None

    rssStr = \
        "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n" + \
        "<rss version=\"2.0\">\n" + \
        '<channel>\n' + \
        '    <title>#categories</title>\n'

    rssDateStr = \
        datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S UT")

    for categoryStr, hashtagList in hashtagCategories.items():
        rssStr += \
            '<item>\n' + \
            '  <title>' + categoryStr + '</title>\n'
        listStr = ''
        for hashtag in hashtagList:
            if ':' in hashtag:
                continue
            if '&' in hashtag:
                continue
            listStr += hashtag + ' '
        rssStr += \
            '  <description>' + listStr.strip() + '</description>\n' + \
            '  <link/>\n' + \
            '  <pubDate>' + rssDateStr + '</pubDate>\n' + \
            '</item>\n'

    rssStr += \
        '</channel>\n' + \
        '</rss>\n'
    return rssStr


def htmlHashTagSwarm(baseDir: str, actor: str, translate: {}) -> str:
    """Returns a tag swarm of today's hashtags
    """
    maxTagLength = 42
    currTime = datetime.utcnow()
    daysSinceEpoch = (currTime - datetime(1970, 1, 1)).days
    daysSinceEpochStr = str(daysSinceEpoch) + ' '
    daysSinceEpochStr2 = str(daysSinceEpoch - 1) + ' '
    recently = daysSinceEpoch - 1
    tagSwarm = []
    categorySwarm = []
    domainHistogram = {}

    # Load the blocked hashtags into memory.
    # This avoids needing to repeatedly load the blocked file for each hashtag
    blockedStr = ''
    globalBlockingFilename = baseDir + '/accounts/blocking.txt'
    if os.path.isfile(globalBlockingFilename):
        with open(globalBlockingFilename, 'r') as fp:
            blockedStr = fp.read()

    for subdir, dirs, files in os.walk(baseDir + '/tags'):
        for f in files:
            if not f.endswith('.txt'):
                continue
            tagsFilename = os.path.join(baseDir + '/tags', f)
            if not os.path.isfile(tagsFilename):
                continue

            # get last modified datetime
            modTimesinceEpoc = os.path.getmtime(tagsFilename)
            lastModifiedDate = datetime.fromtimestamp(modTimesinceEpoc)
            fileDaysSinceEpoch = (lastModifiedDate - datetime(1970, 1, 1)).days

            # check if the file was last modified within the previous
            # two days
            if fileDaysSinceEpoch < recently:
                continue

            hashTagName = f.split('.')[0]
            if len(hashTagName) > maxTagLength:
                # NoIncrediblyLongAndBoringHashtagsShownHere
                continue
            if '#' in hashTagName or \
               '&' in hashTagName or \
               '"' in hashTagName or \
               "'" in hashTagName:
                continue
            if '#' + hashTagName + '\n' in blockedStr:
                continue
            with open(tagsFilename, 'r') as fp:
                # only read one line, which saves time and memory
                lastTag = fp.readline()
                if not lastTag.startswith(daysSinceEpochStr):
                    if not lastTag.startswith(daysSinceEpochStr2):
                        continue
            with open(tagsFilename, 'r') as tagsFile:
                while True:
                    line = tagsFile.readline()
                    if not line:
                        break
                    elif '  ' not in line:
                        break
                    sections = line.split('  ')
                    if len(sections) != 3:
                        break
                    postDaysSinceEpochStr = sections[0]
                    if not postDaysSinceEpochStr.isdigit():
                        break
                    postDaysSinceEpoch = int(postDaysSinceEpochStr)
                    if postDaysSinceEpoch < recently:
                        break
                    else:
                        postUrl = sections[2]
                        if '##' not in postUrl:
                            break
                        postDomain = postUrl.split('##')[1]
                        if '#' in postDomain:
                            postDomain = postDomain.split('#')[0]

                        if domainHistogram.get(postDomain):
                            domainHistogram[postDomain] = \
                                domainHistogram[postDomain] + 1
                        else:
                            domainHistogram[postDomain] = 1
                        tagSwarm.append(hashTagName)
                        categoryFilename = \
                            tagsFilename.replace('.txt', '.category')
                        if os.path.isfile(categoryFilename):
                            categoryStr = \
                                getHashtagCategory(baseDir, hashTagName)
                            if len(categoryStr) < maxTagLength:
                                if '#' not in categoryStr and \
                                   '&' not in categoryStr and \
                                   '"' not in categoryStr and \
                                   "'" not in categoryStr:
                                    if categoryStr not in categorySwarm:
                                        categorySwarm.append(categoryStr)
                        break
        break

    if not tagSwarm:
        return ''
    tagSwarm.sort()

    # swarm of categories
    categorySwarmStr = ''
    if categorySwarm:
        if len(categorySwarm) > 3:
            categorySwarm.sort()
            for categoryStr in categorySwarm:
                categorySwarmStr += \
                    '<a href="' + actor + '/category/' + categoryStr + \
                    '" class="hashtagswarm"><b>' + categoryStr + '</b></a>\n'
            categorySwarmStr += '<br>\n'

    # swarm of tags
    tagSwarmStr = ''
    for tagName in tagSwarm:
        tagSwarmStr += \
            '<a href="' + actor + '/tags/' + tagName + \
            '" class="hashtagswarm">' + tagName + '</a>\n'

    if categorySwarmStr:
        tagSwarmStr = \
            getContentWarningButton('alltags', translate, tagSwarmStr)

    tagSwarmHtml = categorySwarmStr + tagSwarmStr.strip() + '\n'
    return tagSwarmHtml


def htmlSearchHashtagCategory(cssCache: {}, translate: {},
                              baseDir: str, path: str, domain: str,
                              theme: str) -> str:
    """Show hashtags after selecting a category on the main search screen
    """
    actor = path.split('/category/')[0]
    categoryStr = path.split('/category/')[1].strip()
    searchNickname = getNicknameFromActor(actor)

    backgroundExt = setCustomBackground(baseDir, 'search-background')

    cssFilename = baseDir + '/epicyon-search.css'
    if os.path.isfile(baseDir + '/search.css'):
        cssFilename = baseDir + '/search.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    htmlStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    if backgroundExt:
        if backgroundExt != 'jpg':
            htmlStr = htmlStr.replace('"follow-background.jpg"',
                                      '"follow-background.' +
                                      backgroundExt + '"')

    # show a banner above the search box
    searchBannerFile, searchBannerFilename = \
        getSearchBannerFile(baseDir, searchNickname, domain, theme)

    if os.path.isfile(searchBannerFilename):
        htmlStr += '<a href="' + actor + '/search">\n'
        htmlStr += '<img loading="lazy" class="timeline-banner" src="' + \
            actor + '/' + searchBannerFile + '" alt="" /></a>\n'

    htmlStr += \
        '<div class="follow">' + \
        '<center><br><br><br>' + \
        '<h1><a href="' + actor + '/search"><b>' + \
        translate['Category'] + ': ' + categoryStr + '</b></a></h1>'

    hashtagsDict = getHashtagCategories(baseDir, True, categoryStr)
    if hashtagsDict:
        for categoryStr2, hashtagList in hashtagsDict.items():
            hashtagList.sort()
            for tagName in hashtagList:
                htmlStr += \
                    '<a href="' + actor + '/tags/' + tagName + \
                    '" class="hashtagswarm">' + tagName + '</a>\n'

    htmlStr += \
        '</center>' + \
        '</div>'
    htmlStr += htmlFooter()
    return htmlStr
