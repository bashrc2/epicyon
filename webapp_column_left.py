__filename__ = "webapp_column_left.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface Columns"

import os
from utils import getConfigParam
from utils import getNicknameFromActor
from utils import isEditor
from utils import removeDomainPort
from utils import localActorUrl
from webapp_utils import sharesTimelineJson
from webapp_utils import htmlPostSeparator
from webapp_utils import getLeftImageFile
from webapp_utils import headerButtonsFrontScreen
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import getBannerFile
from shares import shareCategoryIcon


def _linksExist(baseDir: str) -> bool:
    """Returns true if links have been created
    """
    linksFilename = baseDir + '/accounts/links.txt'
    return os.path.isfile(linksFilename)


def _getLeftColumnShares(baseDir: str,
                         httpPrefix: str, domain: str, domainFull: str,
                         nickname: str,
                         maxSharesInLeftColumn: int,
                         translate: {},
                         sharedItemsFederatedDomains: []) -> []:
    """get any shares and turn them into the left column links format
    """
    pageNumber = 1
    actor = localActorUrl(httpPrefix, nickname, domainFull)
    # NOTE: this could potentially be slow if the number of federated
    # shared items is large
    sharesJson, lastPage = \
        sharesTimelineJson(actor, pageNumber, maxSharesInLeftColumn,
                           baseDir, domain, nickname, maxSharesInLeftColumn,
                           sharedItemsFederatedDomains, 'shares')
    if not sharesJson:
        return []

    linksList = []
    ctr = 0
    for published, item in sharesJson.items():
        sharedesc = item['displayName']
        if '<' in sharedesc or '?' in sharedesc:
            continue
        shareId = item['shareId']
        # selecting this link calls htmlShowShare
        shareLink = actor + '?showshare=' + shareId
        if item.get('category'):
            shareLink += '?category=' + item['category']
            shareCategory = shareCategoryIcon(item['category'])

        linksList.append(shareCategory + sharedesc + ' ' + shareLink)
        ctr += 1
        if ctr >= maxSharesInLeftColumn:
            break

    if linksList:
        linksList = ['* ' + translate['Shares']] + linksList
    return linksList


def _getLeftColumnWanted(baseDir: str,
                         httpPrefix: str, domain: str, domainFull: str,
                         nickname: str,
                         maxSharesInLeftColumn: int,
                         translate: {},
                         sharedItemsFederatedDomains: []) -> []:
    """get any wanted items and turn them into the left column links format
    """
    pageNumber = 1
    actor = localActorUrl(httpPrefix, nickname, domainFull)
    # NOTE: this could potentially be slow if the number of federated
    # wanted items is large
    sharesJson, lastPage = \
        sharesTimelineJson(actor, pageNumber, maxSharesInLeftColumn,
                           baseDir, domain, nickname, maxSharesInLeftColumn,
                           sharedItemsFederatedDomains, 'wanted')
    if not sharesJson:
        return []

    linksList = []
    ctr = 0
    for published, item in sharesJson.items():
        sharedesc = item['displayName']
        if '<' in sharedesc or ';' in sharedesc:
            continue
        shareId = item['shareId']
        # selecting this link calls htmlShowShare
        shareLink = actor + '?showwanted=' + shareId
        linksList.append(sharedesc + ' ' + shareLink)
        ctr += 1
        if ctr >= maxSharesInLeftColumn:
            break

    if linksList:
        linksList = ['* ' + translate['Wanted']] + linksList
    return linksList


def getLeftColumnContent(baseDir: str, nickname: str, domainFull: str,
                         httpPrefix: str, translate: {},
                         editor: bool,
                         showBackButton: bool, timelinePath: str,
                         rssIconAtTop: bool, showHeaderImage: bool,
                         frontPage: bool, theme: str,
                         accessKeys: {},
                         sharedItemsFederatedDomains: []) -> str:
    """Returns html content for the left column
    """
    htmlStr = ''

    separatorStr = htmlPostSeparator(baseDir, 'left')
    domain = removeDomainPort(domainFull)

    editImageClass = ''
    if showHeaderImage:
        leftImageFile, leftColumnImageFilename = \
            getLeftImageFile(baseDir, nickname, domain, theme)

        # show the image at the top of the column
        editImageClass = 'leftColEdit'
        if os.path.isfile(leftColumnImageFilename):
            editImageClass = 'leftColEditImage'
            htmlStr += \
                '\n      <center>\n        <img class="leftColImg" ' + \
                'alt="" loading="lazy" src="/users/' + \
                nickname + '/' + leftImageFile + '" />\n' + \
                '      </center>\n'

    if showBackButton:
        htmlStr += \
            '      <div>      <a href="' + timelinePath + '">' + \
            '<button class="cancelbtn">' + \
            translate['Go Back'] + '</button></a>\n'

    if (editor or rssIconAtTop) and not showHeaderImage:
        htmlStr += '<div class="columnIcons">'

    if editImageClass == 'leftColEdit':
        htmlStr += '\n      <center>\n'

    htmlStr += '      <div class="leftColIcons">\n'
    if editor:
        # show the edit icon
        htmlStr += \
            '      <a href="/users/' + nickname + '/editlinks" ' + \
            'accesskey="' + accessKeys['menuEdit'] + '">' + \
            '<img class="' + editImageClass + '" loading="lazy" alt="' + \
            translate['Edit Links'] + ' | " title="' + \
            translate['Edit Links'] + '" src="/icons/edit.png" /></a>\n'

    # RSS icon
    if nickname != 'news':
        # rss feed for this account
        rssUrl = httpPrefix + '://' + domainFull + \
            '/blog/' + nickname + '/rss.xml'
    else:
        # rss feed for all accounts on the instance
        rssUrl = httpPrefix + '://' + domainFull + '/blog/rss.xml'
    if not frontPage:
        rssTitle = translate['RSS feed for your blog']
    else:
        rssTitle = translate['RSS feed for this site']
    rssIconStr = \
        '      <a href="' + rssUrl + '"><img class="' + editImageClass + \
        '" loading="lazy" alt="' + rssTitle + '" title="' + rssTitle + \
        '" src="/icons/logorss.png" /></a>\n'
    if rssIconAtTop:
        htmlStr += rssIconStr
    htmlStr += '      </div>\n'

    if editImageClass == 'leftColEdit':
        htmlStr += '      </center>\n'

    if (editor or rssIconAtTop) and not showHeaderImage:
        htmlStr += '</div><br>'

    # if showHeaderImage:
    #     htmlStr += '<br>'

    # flag used not to show the first separator
    firstSeparatorAdded = False

    linksFilename = baseDir + '/accounts/links.txt'
    linksFileContainsEntries = False
    linksList = None
    if os.path.isfile(linksFilename):
        with open(linksFilename, 'r') as f:
            linksList = f.readlines()

    if not frontPage:
        # show a number of shares
        maxSharesInLeftColumn = 3
        sharesList = \
            _getLeftColumnShares(baseDir,
                                 httpPrefix, domain, domainFull, nickname,
                                 maxSharesInLeftColumn, translate,
                                 sharedItemsFederatedDomains)
        if linksList and sharesList:
            linksList = sharesList + linksList

        wantedList = \
            _getLeftColumnWanted(baseDir,
                                 httpPrefix, domain, domainFull, nickname,
                                 maxSharesInLeftColumn, translate,
                                 sharedItemsFederatedDomains)
        if linksList and wantedList:
            linksList = wantedList + linksList

    newTabStr = ' target="_blank" rel="nofollow noopener noreferrer"'
    if linksList:
        htmlStr += '<nav>\n'
        for lineStr in linksList:
            if ' ' not in lineStr:
                if '#' not in lineStr:
                    if '*' not in lineStr:
                        if not lineStr.startswith('['):
                            if not lineStr.startswith('=> '):
                                continue
            lineStr = lineStr.strip()
            linkStr = None
            if not lineStr.startswith('['):
                words = lineStr.split(' ')
                # get the link
                for word in words:
                    if word == '#':
                        continue
                    if word == '*':
                        continue
                    if word == '=>':
                        continue
                    if '://' in word:
                        linkStr = word
                        break
            else:
                # markdown link
                if ']' not in lineStr:
                    continue
                if '(' not in lineStr:
                    continue
                if ')' not in lineStr:
                    continue
                linkStr = lineStr.split('(')[1]
                if ')' not in linkStr:
                    continue
                linkStr = linkStr.split(')')[0]
                if '://' not in linkStr:
                    continue
                lineStr = lineStr.split('[')[1]
                if ']' not in lineStr:
                    continue
                lineStr = lineStr.split(']')[0]
            if linkStr:
                lineStr = lineStr.replace(linkStr, '').strip()
                # avoid any dubious scripts being added
                if '<' not in lineStr:
                    # remove trailing comma if present
                    if lineStr.endswith(','):
                        lineStr = lineStr[:len(lineStr)-1]
                    # add link to the returned html
                    if '?showshare=' not in linkStr and \
                       '?showwarning=' not in linkStr:
                        htmlStr += \
                            '      <p><a href="' + linkStr + \
                            '"' + newTabStr + '>' + \
                            lineStr + '</a></p>\n'
                    else:
                        htmlStr += \
                            '      <p><a href="' + linkStr + \
                            '">' + lineStr + '</a></p>\n'
                    linksFileContainsEntries = True
                elif lineStr.startswith('=> '):
                    # gemini style link
                    lineStr = lineStr.replace('=> ', '')
                    lineStr = lineStr.replace(linkStr, '')
                    # add link to the returned html
                    if '?showshare=' not in linkStr and \
                       '?showwarning=' not in linkStr:
                        htmlStr += \
                            '      <p><a href="' + linkStr + \
                            '"' + newTabStr + '>' + \
                            lineStr.strip() + '</a></p>\n'
                    else:
                        htmlStr += \
                            '      <p><a href="' + linkStr + \
                            '">' + lineStr.strip() + '</a></p>\n'
                    linksFileContainsEntries = True
            else:
                if lineStr.startswith('#') or lineStr.startswith('*'):
                    lineStr = lineStr[1:].strip()
                    if firstSeparatorAdded:
                        htmlStr += separatorStr
                    firstSeparatorAdded = True
                    htmlStr += \
                        '      <h3 class="linksHeader">' + \
                        lineStr + '</h3>\n'
                else:
                    htmlStr += \
                        '      <p>' + lineStr + '</p>\n'
                linksFileContainsEntries = True
        htmlStr += '</nav>\n'

    if firstSeparatorAdded:
        htmlStr += separatorStr
    htmlStr += \
        '<p class="login-text"><a href="/users/' + nickname + \
        '/catalog.csv">' + translate['Shares Catalog'] + '</a></p>'
    htmlStr += \
        '<p class="login-text"><a href="/users/' + \
        nickname + '/accesskeys" accesskey="' + \
        accessKeys['menuKeys'] + '">' + \
        translate['Key Shortcuts'] + '</a></p>'
    htmlStr += \
        '<p class="login-text"><a href="/about">' + \
        translate['About this Instance'] + '</a></p>'
    htmlStr += \
        '<p class="login-text"><a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>'

    if linksFileContainsEntries and not rssIconAtTop:
        htmlStr += '<br><div class="columnIcons">' + rssIconStr + '</div>'

    return htmlStr


def htmlLinksMobile(cssCache: {}, baseDir: str,
                    nickname: str, domainFull: str,
                    httpPrefix: str, translate,
                    timelinePath: str, authorized: bool,
                    rssIconAtTop: bool,
                    iconsAsButtons: bool,
                    defaultTimeline: str,
                    theme: str, accessKeys: {},
                    sharedItemsFederatedDomains: []) -> str:
    """Show the left column links within mobile view
    """
    htmlStr = ''

    # the css filename
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    # is the user a site editor?
    if nickname == 'news':
        editor = False
    else:
        editor = isEditor(baseDir, nickname)

    domain = removeDomainPort(domainFull)

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    htmlStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, theme)
    htmlStr += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" ' + \
        'accesskey="' + accessKeys['menuTimeline'] + '">' + \
        '<img loading="lazy" class="timeline-banner" ' + \
        'alt="' + translate['Switch to timeline view'] + '" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    htmlStr += '<div class="col-left-mobile">\n'
    htmlStr += '<center>' + \
        headerButtonsFrontScreen(translate, nickname,
                                 'links', authorized,
                                 iconsAsButtons) + '</center>'
    if _linksExist(baseDir):
        htmlStr += \
            getLeftColumnContent(baseDir, nickname, domainFull,
                                 httpPrefix, translate,
                                 editor,
                                 False, timelinePath,
                                 rssIconAtTop, False, False,
                                 theme, accessKeys,
                                 sharedItemsFederatedDomains)
    else:
        if editor:
            htmlStr += '<br><br><br>\n<center>\n  '
            htmlStr += translate['Select the edit icon to add web links']
            htmlStr += '\n</center>\n'

    # end of col-left-mobile
    htmlStr += '</div>\n'

    htmlStr += '</div>\n' + htmlFooter()
    return htmlStr


def htmlEditLinks(cssCache: {}, translate: {}, baseDir: str, path: str,
                  domain: str, port: int, httpPrefix: str,
                  defaultTimeline: str, theme: str,
                  accessKeys: {}) -> str:
    """Shows the edit links screen
    """
    if '/users/' not in path:
        return ''
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '').replace('/wanted', '')

    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''

    # is the user a moderator?
    if not isEditor(baseDir, nickname):
        return ''

    cssFilename = baseDir + '/epicyon-links.css'
    if os.path.isfile(baseDir + '/links.css'):
        cssFilename = baseDir + '/links.css'

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, theme)

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    editLinksForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    # top banner
    editLinksForm += \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + accessKeys['menuTimeline'] + '">\n'
    editLinksForm += \
        '<img loading="lazy" class="timeline-banner" ' + \
        'alt = "" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" /></a>\n' + \
        '</header>\n'

    editLinksForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/linksdata">\n'
    editLinksForm += \
        '  <div class="vertical-center">\n'
    editLinksForm += \
        '    <div class="containerSubmitNewPost">\n'
    editLinksForm += \
        '      <h1>' + translate['Edit Links'] + '</h1>'
    editLinksForm += \
        '      <input type="submit" name="submitLinks" value="' + \
        translate['Submit'] + '" ' + \
        'accesskey="' + accessKeys['submitButton'] + '">\n'
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
        '  <textarea id="message" name="editedLinks" ' + \
        'style="height:80vh" spellcheck="false">' + linksStr + '</textarea>'
    editLinksForm += \
        '</div>'

    # the admin can edit terms of service and about text
    adminNickname = getConfigParam(baseDir, 'admin')
    if adminNickname:
        if nickname == adminNickname:
            aboutFilename = baseDir + '/accounts/about.md'
            aboutStr = ''
            if os.path.isfile(aboutFilename):
                with open(aboutFilename, 'r') as fp:
                    aboutStr = fp.read()

            editLinksForm += \
                '<div class="container">'
            editLinksForm += \
                '  ' + \
                translate['About this Instance'] + \
                '<br>'
            editLinksForm += \
                '  <textarea id="message" name="editedAbout" ' + \
                'style="height:100vh" spellcheck="true" autocomplete="on">' + \
                aboutStr + '</textarea>'
            editLinksForm += \
                '</div>'

            TOSFilename = baseDir + '/accounts/tos.md'
            TOSStr = ''
            if os.path.isfile(TOSFilename):
                with open(TOSFilename, 'r') as fp:
                    TOSStr = fp.read()

            editLinksForm += \
                '<div class="container">'
            editLinksForm += \
                '  ' + \
                translate['Terms of Service'] + \
                '<br>'
            editLinksForm += \
                '  <textarea id="message" name="editedTOS" ' + \
                'style="height:100vh" spellcheck="true" autocomplete="on">' + \
                TOSStr + '</textarea>'
            editLinksForm += \
                '</div>'

    editLinksForm += htmlFooter()
    return editLinksForm
