__filename__ = "webapp_column_left.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from utils import getConfigParam
from utils import getNicknameFromActor
from posts import isEditor
from webapp_utils import htmlPostSeparator
from webapp_utils import getLeftImageFile
from webapp_utils import getImageFile
from webapp_utils import headerButtonsFrontScreen
from webapp_utils import getIconsWebPath
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import getBannerFile


def getLeftColumnContent(baseDir: str, nickname: str, domainFull: str,
                         httpPrefix: str, translate: {},
                         iconsPath: str, editor: bool,
                         showBackButton: bool, timelinePath: str,
                         rssIconAtTop: bool, showHeaderImage: bool,
                         frontPage: bool) -> str:
    """Returns html content for the left column
    """
    htmlStr = ''

    separatorStr = htmlPostSeparator(baseDir, 'left')
    domain = domainFull
    if ':' in domain:
        domain = domain.split(':')

    editImageClass = ''
    if showHeaderImage:
        leftImageFile, leftColumnImageFilename = \
            getLeftImageFile(baseDir, nickname, domain)
        if not os.path.isfile(leftColumnImageFilename):
            theme = getConfigParam(baseDir, 'theme').lower()
            if theme == 'default':
                theme = ''
            else:
                theme = '_' + theme
            themeLeftImageFile, themeLeftColumnImageFilename = \
                getImageFile(baseDir, 'left_col_image', baseDir + '/img',
                             nickname, domain)
            if os.path.isfile(themeLeftColumnImageFilename):
                leftColumnImageFilename = \
                    baseDir + '/accounts/' + \
                    nickname + '@' + domain + '/' + themeLeftImageFile
                copyfile(themeLeftColumnImageFilename,
                         leftColumnImageFilename)
                leftImageFile = themeLeftImageFile

        # show the image at the top of the column
        editImageClass = 'leftColEdit'
        if os.path.isfile(leftColumnImageFilename):
            editImageClass = 'leftColEditImage'
            htmlStr += \
                '\n      <center>\n' + \
                '        <img class="leftColImg" ' + \
                'loading="lazy" src="/users/' + \
                nickname + '/' + leftImageFile + '" />\n' + \
                '      </center>\n'

    if showBackButton:
        htmlStr += \
            '      <div>' + \
            '      <a href="' + timelinePath + '">' + \
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
            '      <a href="' + \
            '/users/' + nickname + '/editlinks">' + \
            '<img class="' + editImageClass + \
            '" loading="lazy" alt="' + \
            translate['Edit Links'] + '" title="' + \
            translate['Edit Links'] + '" src="/' + \
            iconsPath + '/edit.png" /></a>\n'

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
        '      <a href="' + rssUrl + '">' + \
        '<img class="' + editImageClass + \
        '" loading="lazy" alt="' + rssTitle + \
        '" title="' + rssTitle + \
        '" src="/' + iconsPath + '/logorss.png" /></a>\n'
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

    if firstSeparatorAdded:
        htmlStr += separatorStr
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
                    defaultTimeline: str) -> str:
    """Show the left column links within mobile view
    """
    htmlStr = ''

    # the css filename
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    iconsPath = getIconsWebPath(baseDir)

    # is the user a site editor?
    if nickname == 'news':
        editor = False
    else:
        editor = isEditor(baseDir, nickname)

    domain = domainFull
    if ':' in domain:
        domain = domain.split(':')[0]

    htmlStr = htmlHeaderWithExternalStyle(cssFilename)
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)
    htmlStr += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '">' + \
        '<img loading="lazy" class="timeline-banner" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    htmlStr += '<div class="col-left-mobile">\n'
    htmlStr += '<center>' + \
        headerButtonsFrontScreen(translate, nickname,
                                 'links', authorized,
                                 iconsAsButtons, iconsPath) + '</center>'
    htmlStr += \
        getLeftColumnContent(baseDir, nickname, domainFull,
                             httpPrefix, translate,
                             iconsPath, editor,
                             False, timelinePath,
                             rssIconAtTop, False, False)

    # end of col-left-mobile
    htmlStr += '</div>\n'

    htmlStr += '</div>\n' + htmlFooter()
    return htmlStr


def htmlEditLinks(cssCache: {}, translate: {}, baseDir: str, path: str,
                  domain: str, port: int, httpPrefix: str,
                  defaultTimeline: str) -> str:
    """Shows the edit links screen
    """
    if '/users/' not in path:
        return ''
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '')

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
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)

    editLinksForm = htmlHeaderWithExternalStyle(cssFilename)

    # top banner
    editLinksForm += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '">\n'
    editLinksForm += '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" /></a>\n'

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
        '      <center>\n' + \
        '        <input type="submit" name="submitLinks" value="' + \
        translate['Submit'] + '">\n' + \
        '      </center>\n'
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
        '  <textarea id="message" name="editedLinks" style="height:80vh">' + \
        linksStr + '</textarea>'
    editLinksForm += \
        '</div>'

    # the admin can edit terms of service and about text
    adminNickname = getConfigParam(baseDir, 'admin')
    if adminNickname:
        if nickname == adminNickname:
            aboutFilename = baseDir + '/accounts/about.txt'
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
                'style="height:100vh">' + aboutStr + '</textarea>'
            editLinksForm += \
                '</div>'

            TOSFilename = baseDir + '/accounts/tos.txt'
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
                'style="height:100vh">' + TOSStr + '</textarea>'
            editLinksForm += \
                '</div>'

    editLinksForm += htmlFooter()
    return editLinksForm
