__filename__ = "webapp_hashtagswarm.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from datetime import datetime
from utils import getNicknameFromActor
from utils import getConfigParam
from categories import getHashtagCategories
from categories import getHashtagCategory
from webapp_utils import getSearchBannerFile
from webapp_utils import getContentWarningButton
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def getHashtagCategoriesFeed(baseDir: str,
                             hashtagCategories=None) -> str:
    """Returns an rss feed for hashtag categories
    """
    if not hashtagCategories:
        hashtagCategories = getHashtagCategories(baseDir)
    if not hashtagCategories:
        return None

    rssStr = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n"
    rssStr += "<rss version=\"2.0\">\n"
    rssStr += '<channel>\n'
    rssStr += '    <title>#categories</title>\n'

    rssDateStr = \
        datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S UT")

    for categoryStr, hashtagList in hashtagCategories.items():
        rssStr += '<item>\n'
        rssStr += '  <title>' + categoryStr + '</title>\n'
        listStr = ''
        for hashtag in hashtagList:
            listStr += hashtag + ' '
        rssStr += '  <description>' + listStr.strip() + '</description>\n'
        rssStr += '  <link/>\n'
        rssStr += '  <pubDate>' + rssDateStr + '</pubDate>\n'
        rssStr += '</item>\n'

    rssStr += '</channel>\n'
    rssStr += '</rss>\n'
    return rssStr


def _getHashtagDomainMax(domainHistogram: {}) -> str:
    """Returns the domain with the maximum number of hashtags
    """
    maxCount = 1
    maxDomain = None
    for domain, count in domainHistogram.items():
        if count > maxCount:
            maxDomain = domain
            maxCount = count
    return maxDomain


def _getHashtagDomainHistogram(domainHistogram: {}, translate: {}) -> str:
    """Returns the html for a histogram of domains
    from which hashtags are coming
    """
    totalCount = 0
    for domain, count in domainHistogram.items():
        totalCount += count
    if totalCount == 0:
        return ''

    htmlStr = ''
    histogramHeaderStr = '<br><br><center>\n'
    histogramHeaderStr += '  <h1>' + translate['Hashtag origins'] + '</h1>\n'
    histogramHeaderStr += '  <table class="domainHistogram">\n'
    histogramHeaderStr += '    <colgroup>\n'
    histogramHeaderStr += '      <col span="1" class="domainHistogramLeft">\n'
    histogramHeaderStr += '      <col span="1" class="domainHistogramRight">\n'
    histogramHeaderStr += '    </colgroup>\n'
    histogramHeaderStr += '    <tbody>\n'
    histogramHeaderStr += '      <tr>\n'

    leftColStr = ''
    rightColStr = ''

    for i in range(len(domainHistogram)):
        domain = _getHashtagDomainMax(domainHistogram)
        if not domain:
            break
        percent = int(domainHistogram[domain] * 100 / totalCount)
        if histogramHeaderStr:
            htmlStr += histogramHeaderStr
            histogramHeaderStr = None
        leftColStr += str(percent) + '%<br>'
        rightColStr += domain + '<br>'
        del domainHistogram[domain]

    if htmlStr:
        htmlStr += '        <td>' + leftColStr + '</td>\n'
        htmlStr += '        <td>' + rightColStr + '</td>\n'
        htmlStr += '      </tr>\n'
        htmlStr += '    </tbody>\n'
        htmlStr += '  </table>\n'
        htmlStr += '</center>\n'

    return htmlStr


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
    # tagSwarmHtml += _getHashtagDomainHistogram(domainHistogram, translate)
    return tagSwarmHtml


def htmlSearchHashtagCategory(cssCache: {}, translate: {},
                              baseDir: str, path: str, domain: str,
                              theme: str) -> str:
    """Show hashtags after selecting a category on the main search screen
    """
    actor = path.split('/category/')[0]
    categoryStr = path.split('/category/')[1].strip()
    searchNickname = getNicknameFromActor(actor)

    if os.path.isfile(baseDir + '/img/search-background.png'):
        if not os.path.isfile(baseDir + '/accounts/search-background.png'):
            copyfile(baseDir + '/img/search-background.png',
                     baseDir + '/accounts/search-background.png')

    cssFilename = baseDir + '/epicyon-search.css'
    if os.path.isfile(baseDir + '/search.css'):
        cssFilename = baseDir + '/search.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    htmlStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    # show a banner above the search box
    searchBannerFile, searchBannerFilename = \
        getSearchBannerFile(baseDir, searchNickname, domain, theme)

    if os.path.isfile(searchBannerFilename):
        htmlStr += '<a href="' + actor + '/search">\n'
        htmlStr += '<img loading="lazy" class="timeline-banner" src="' + \
            actor + '/' + searchBannerFile + '" alt="" /></a>\n'

    htmlStr += '<div class="follow">'
    htmlStr += '<center><br><br><br>'
    htmlStr += '<h1><a href="' + actor + '/search"><b>'
    htmlStr += translate['Category'] + ': ' + categoryStr + '</b></a></h1>'

    hashtagsDict = getHashtagCategories(baseDir, True, categoryStr)
    if hashtagsDict:
        for categoryStr2, hashtagList in hashtagsDict.items():
            hashtagList.sort()
            for tagName in hashtagList:
                htmlStr += \
                    '<a href="' + actor + '/tags/' + tagName + \
                    '" class="hashtagswarm">' + tagName + '</a>\n'

    htmlStr += '</center>'
    htmlStr += '</div>'
    htmlStr += htmlFooter()
    return htmlStr
