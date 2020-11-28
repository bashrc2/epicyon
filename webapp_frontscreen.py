__filename__ = "webapp_frontscreen.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import isSystemAccount
from utils import getDomainFromActor
from person import personBoxJson
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import getIconsWebPath
from webapp_utils import getBannerFile
from webapp_utils import htmlPostSeparator
from webapp_column_left import getLeftColumnContent
from webapp_column_right import getRightColumnContent
from webapp_post import individualPostAsHtml


def headerButtonsFrontScreen(translate: {},
                             nickname: str, boxName: str,
                             authorized: bool,
                             iconsAsButtons: bool,
                             iconsPath: bool) -> str:
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
                '<img loading="lazy" src="/' + iconsPath + \
                '/newswire.png" title="' + translate['Newswire'] + \
                '" alt="| ' + translate['Newswire'] + '"/></a>\n'
            headerStr += \
                '        <a href="' + \
                '/users/news/linksmobile">' + \
                '<img loading="lazy" src="/' + iconsPath + \
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


def htmlFrontScreenPosts(recentPostsCache: {}, maxRecentPosts: int,
                         translate: {},
                         baseDir: str, httpPrefix: str,
                         nickname: str, domain: str, port: int,
                         session, wfRequest: {}, personCache: {},
                         projectVersion: str,
                         YTReplacementDomain: str,
                         showPublishedDateOnly: bool) -> str:
    """Shows posts on the front screen of a news instance
    These should only be public blog posts from the features timeline
    which is the blog timeline of the news actor
    """
    iconsPath = getIconsWebPath(baseDir)
    separatorStr = htmlPostSeparator(baseDir, None)
    profileStr = ''
    maxItems = 4
    ctr = 0
    currPage = 1
    boxName = 'tlfeatures'
    authorized = True
    while ctr < maxItems and currPage < 4:
        outboxFeed = \
            personBoxJson({}, session, baseDir, domain, port,
                          '/users/' + nickname + '/' + boxName +
                          '?page=' + str(currPage),
                          httpPrefix, 10, boxName,
                          authorized, 0, False, 0)
        if not outboxFeed:
            break
        if len(outboxFeed['orderedItems']) == 0:
            break
        for item in outboxFeed['orderedItems']:
            if item['type'] == 'Create':
                postStr = \
                    individualPostAsHtml(True, recentPostsCache,
                                         maxRecentPosts,
                                         iconsPath, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
                                         False, False, False, True, False)
                if postStr:
                    profileStr += postStr + separatorStr
                    ctr += 1
                    if ctr >= maxItems:
                        break
        currPage += 1
    return profileStr


def htmlFrontScreen(rssIconAtTop: bool,
                    cssCache: {}, iconsAsButtons: bool,
                    defaultTimeline: str,
                    recentPostsCache: {}, maxRecentPosts: int,
                    translate: {}, projectVersion: str,
                    baseDir: str, httpPrefix: str, authorized: bool,
                    profileJson: {}, selected: str,
                    session, wfRequest: {}, personCache: {},
                    YTReplacementDomain: str,
                    showPublishedDateOnly: bool,
                    newswire: {}, extraJson=None,
                    pageNumber=None, maxItemsPerPage=None) -> str:
    """Show the news instance front screen
    """
    nickname = profileJson['preferredUsername']
    if not nickname:
        return ""
    if not isSystemAccount(nickname):
        return ""
    domain, port = getDomainFromActor(profileJson['id'])
    if not domain:
        return ""
    domainFull = domain
    if port:
        domainFull = domain + ':' + str(port)

    iconsPath = getIconsWebPath(baseDir)
    loginButton = headerButtonsFrontScreen(translate, nickname,
                                           'features', authorized,
                                           iconsAsButtons, iconsPath)

    # If this is the news account then show a different banner
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)
    profileHeaderStr = \
        '<img loading="lazy" class="timeline-banner" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" />\n'
    if loginButton:
        profileHeaderStr += '<center>' + loginButton + '</center>\n'

    profileHeaderStr += '<table class="timeline">\n'
    profileHeaderStr += '  <colgroup>\n'
    profileHeaderStr += '    <col span="1" class="column-left">\n'
    profileHeaderStr += '    <col span="1" class="column-center">\n'
    profileHeaderStr += '    <col span="1" class="column-right">\n'
    profileHeaderStr += '  </colgroup>\n'
    profileHeaderStr += '  <tbody>\n'
    profileHeaderStr += '    <tr>\n'
    profileHeaderStr += '      <td valign="top" class="col-left">\n'
    iconsPath = getIconsWebPath(baseDir)
    profileHeaderStr += \
        getLeftColumnContent(baseDir, 'news', domainFull,
                             httpPrefix, translate,
                             iconsPath, False,
                             False, None, rssIconAtTop, True,
                             True)
    profileHeaderStr += '      </td>\n'
    profileHeaderStr += '      <td valign="top" class="col-center">\n'

    profileStr = profileHeaderStr

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    licenseStr = ''
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain)
    profileStr += \
        htmlFrontScreenPosts(recentPostsCache, maxRecentPosts,
                             translate,
                             baseDir, httpPrefix,
                             nickname, domain, port,
                             session, wfRequest, personCache,
                             projectVersion,
                             YTReplacementDomain,
                             showPublishedDateOnly) + licenseStr

    # Footer which is only used for system accounts
    profileFooterStr = '      </td>\n'
    profileFooterStr += '      <td valign="top" class="col-right">\n'
    iconsPath = getIconsWebPath(baseDir)
    profileFooterStr += \
        getRightColumnContent(baseDir, 'news', domainFull,
                              httpPrefix, translate,
                              iconsPath, False, False,
                              newswire, False,
                              False, None, False, False,
                              False, True, authorized, True)
    profileFooterStr += '      </td>\n'
    profileFooterStr += '  </tr>\n'
    profileFooterStr += '  </tbody>\n'
    profileFooterStr += '</table>\n'

    profileStr = \
        htmlHeaderWithExternalStyle(cssFilename) + \
        profileStr + profileFooterStr + htmlFooter()
    return profileStr
