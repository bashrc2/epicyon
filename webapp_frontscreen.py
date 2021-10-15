__filename__ = "webapp_frontscreen.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

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
                          twitterReplacementDomain: str,
                          showPublishedDateOnly: bool,
                          peertubeInstances: [],
                          allowLocalNetworkAccess: bool,
                          themeName: str, systemLanguage: str,
                          maxLikeCount: int,
                          signingPrivateKeyPem: str) -> str:
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
                    individualPostAsHtml(signingPrivateKeyPem,
                                         True, recentPostsCache,
                                         maxRecentPosts,
                                         translate, None,
                                         baseDir, session,
                                         cachedWebfingers,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         twitterReplacementDomain,
                                         showPublishedDateOnly,
                                         peertubeInstances,
                                         allowLocalNetworkAccess,
                                         themeName, systemLanguage,
                                         maxLikeCount,
                                         False, False, False,
                                         True, False, False)
                if postStr:
                    profileStr += postStr + separatorStr
                    ctr += 1
                    if ctr >= maxItems:
                        break
        currPage += 1
    return profileStr


def htmlFrontScreen(signingPrivateKeyPem: str,
                    rssIconAtTop: bool,
                    cssCache: {}, iconsAsButtons: bool,
                    defaultTimeline: str,
                    recentPostsCache: {}, maxRecentPosts: int,
                    translate: {}, projectVersion: str,
                    baseDir: str, httpPrefix: str, authorized: bool,
                    profileJson: {}, selected: str,
                    session, cachedWebfingers: {}, personCache: {},
                    YTReplacementDomain: str,
                    twitterReplacementDomain: str,
                    showPublishedDateOnly: bool,
                    newswire: {}, theme: str,
                    peertubeInstances: [],
                    allowLocalNetworkAccess: bool,
                    accessKeys: {},
                    systemLanguage: str, maxLikeCount: int,
                    sharedItemsFederatedDomains: [],
                    extraJson: {} = None,
                    pageNumber: int = None,
                    maxItemsPerPage: int = None) -> str:
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

    profileHeaderStr += \
        '<table class="timeline">\n' + \
        '  <colgroup>\n' + \
        '    <col span="1" class="column-left">\n' + \
        '    <col span="1" class="column-center">\n' + \
        '    <col span="1" class="column-right">\n' + \
        '  </colgroup>\n' + \
        '  <tbody>\n' + \
        '    <tr>\n' + \
        '      <td valign="top" class="col-left">\n'
    profileHeaderStr += \
        getLeftColumnContent(baseDir, 'news', domainFull,
                             httpPrefix, translate,
                             False, False, None, rssIconAtTop, True,
                             True, theme, accessKeys,
                             sharedItemsFederatedDomains)
    profileHeaderStr += \
        '      </td>\n' + \
        '      <td valign="top" class="col-center">\n'

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
                              twitterReplacementDomain,
                              showPublishedDateOnly,
                              peertubeInstances,
                              allowLocalNetworkAccess,
                              theme, systemLanguage,
                              maxLikeCount,
                              signingPrivateKeyPem) + licenseStr

    # Footer which is only used for system accounts
    profileFooterStr = '      </td>\n'
    profileFooterStr += '      <td valign="top" class="col-right">\n'
    profileFooterStr += \
        getRightColumnContent(baseDir, 'news', domainFull,
                              httpPrefix, translate,
                              False, False, newswire, False,
                              False, None, False, False,
                              False, True, authorized, True, theme,
                              defaultTimeline, accessKeys)
    profileFooterStr += \
        '      </td>\n' + \
        '  </tr>\n' + \
        '  </tbody>\n' + \
        '</table>\n'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    profileStr = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle) + \
        profileStr + profileFooterStr + htmlFooter()
    return profileStr
