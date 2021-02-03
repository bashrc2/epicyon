__filename__ = "webapp_frontscreen.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import isSystemAccount
from utils import getDomainFromActor
from utils import getConfigParam
from person import personBoxJson
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import getBannerFile
from webapp_utils import htmlPostSeparator
from webapp_utils import headerButtonsFrontScreen
from webapp_column_left import getLeftColumnContent
from webapp_column_right import getRightColumnContent
from webapp_post import individualPostAsHtml


def _htmlFrontScreenPosts(recentPostsCache: {}, maxRecentPosts: int,
                          translate: {},
                          baseDir: str, httpPrefix: str,
                          nickname: str, domain: str, port: int,
                          session, cachedWebfingers: {}, personCache: {},
                          projectVersion: str,
                          YTReplacementDomain: str,
                          showPublishedDateOnly: bool,
                          peertubeInstances: [],
                          allowLocalNetworkAccess: bool) -> str:
    """Shows posts on the front screen of a news instance
    These should only be public blog posts from the features timeline
    which is the blog timeline of the news actor
    """
    separatorStr = htmlPostSeparator(baseDir, None)
    profileStr = ''
    maxItems = 4
    ctr = 0
    currPage = 1
    boxName = 'tlfeatures'
    authorized = True
    while ctr < maxItems and currPage < 4:
        outboxFeedPathStr = \
            '/users/' + nickname + '/' + boxName + \
            '?page=' + str(currPage)
        outboxFeed = \
            personBoxJson({}, session, baseDir, domain, port,
                          outboxFeedPathStr,
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
                                         translate, None,
                                         baseDir, session,
                                         cachedWebfingers,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
                                         peertubeInstances,
                                         allowLocalNetworkAccess,
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
                    session, cachedWebfingers: {}, personCache: {},
                    YTReplacementDomain: str,
                    showPublishedDateOnly: bool,
                    newswire: {}, theme: str,
                    peertubeInstances: [],
                    allowLocalNetworkAccess: bool,
                    extraJson=None,
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

    loginButton = headerButtonsFrontScreen(translate, nickname,
                                           'features', authorized,
                                           iconsAsButtons)

    # If this is the news account then show a different banner
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, theme)
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
    profileHeaderStr += \
        getLeftColumnContent(baseDir, 'news', domainFull,
                             httpPrefix, translate,
                             False, False, None, rssIconAtTop, True,
                             True, theme)
    profileHeaderStr += '      </td>\n'
    profileHeaderStr += '      <td valign="top" class="col-center">\n'

    profileStr = profileHeaderStr

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    licenseStr = ''
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, theme)
    profileStr += \
        _htmlFrontScreenPosts(recentPostsCache, maxRecentPosts,
                              translate,
                              baseDir, httpPrefix,
                              nickname, domain, port,
                              session, cachedWebfingers, personCache,
                              projectVersion,
                              YTReplacementDomain,
                              showPublishedDateOnly,
                              peertubeInstances,
                              allowLocalNetworkAccess) + licenseStr

    # Footer which is only used for system accounts
    profileFooterStr = '      </td>\n'
    profileFooterStr += '      <td valign="top" class="col-right">\n'
    profileFooterStr += \
        getRightColumnContent(baseDir, 'news', domainFull,
                              httpPrefix, translate,
                              False, False, newswire, False,
                              False, None, False, False,
                              False, True, authorized, True, theme)
    profileFooterStr += '      </td>\n'
    profileFooterStr += '  </tr>\n'
    profileFooterStr += '  </tbody>\n'
    profileFooterStr += '</table>\n'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    profileStr = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle) + \
        profileStr + profileFooterStr + htmlFooter()
    return profileStr
