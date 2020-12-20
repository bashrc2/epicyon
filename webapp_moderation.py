__filename__ = "webapp_moderation.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson
from utils import getNicknameFromActor
from utils import getDomainFromActor
from posts import getPublicPostInfo
from webapp_timeline import htmlTimeline
# from webapp_utils import getPersonAvatarUrl
from webapp_utils import getContentWarningButton
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from blocking import isBlockedDomain


def htmlModeration(cssCache: {}, defaultTimeline: str,
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate: {}, pageNumber: int, itemsPerPage: int,
                   session, baseDir: str, wfRequest: {}, personCache: {},
                   nickname: str, domain: str, port: int, inboxJson: {},
                   allowDeletion: bool,
                   httpPrefix: str, projectVersion: str,
                   YTReplacementDomain: str,
                   showPublishedDateOnly: bool,
                   newswire: {}, positiveVoting: bool,
                   showPublishAsIcon: bool,
                   fullWidthTimelineButtonHeader: bool,
                   iconsAsButtons: bool,
                   rssIconAtTop: bool,
                   publishButtonAtTop: bool,
                   authorized: bool, moderationActionStr: str) -> str:
    """Show the moderation feed as html
    This is what you see when selecting the "mod" timeline
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'moderation',
                        allowDeletion, httpPrefix, projectVersion, True, False,
                        YTReplacementDomain, showPublishedDateOnly,
                        newswire, False, False, positiveVoting,
                        showPublishAsIcon, fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, moderationActionStr)


def htmlAccountInfo(cssCache: {}, translate: {},
                    baseDir: str, httpPrefix: str,
                    nickname: str, domain: str, port: int,
                    searchHandle: str, debug: bool) -> str:
    """Shows which domains a search handle interacts with.
    This screen is shown if a moderator enters a handle and selects info
    on the moderation screen
    """
    msgStr1 = 'This account interacts with the following instances'

    infoForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    infoForm = htmlHeaderWithExternalStyle(cssFilename)

    searchNickname = getNicknameFromActor(searchHandle)
    searchDomain, searchPort = getDomainFromActor(searchHandle)

    searchHandle = searchNickname + '@' + searchDomain
    infoForm += \
        '<center><h1><a href="/users/' + nickname + '/moderation">' + \
        translate['Account Information'] + ':</a> <a href="' + \
        httpPrefix + '://' + searchDomain + '/users/' + searchNickname + \
        '">' + searchHandle + '</a></h1><br>'

    infoForm += translate[msgStr1] + '</center><br><br>'

    proxyType = 'tor'
    if not os.path.isfile('/usr/bin/tor'):
        proxyType = None
    if domain.endswith('.i2p'):
        proxyType = None
    domainDict = getPublicPostInfo(None,
                                   baseDir, searchNickname, searchDomain,
                                   proxyType, searchPort,
                                   httpPrefix, debug,
                                   __version__)
    infoForm += '<div class="accountInfoDomains">'
    usersPath = '/users/' + nickname + '/accountinfo'
    ctr = 1
    for postDomain, blockedPostUrls in domainDict.items():
        infoForm += '<a href="' + \
            httpPrefix + '://' + postDomain + '">' + postDomain + '</a> '
        if isBlockedDomain(baseDir, postDomain):
            blockedPostsLinks = ''
            urlCtr = 0
            for url in blockedPostUrls:
                if urlCtr > 0:
                    blockedPostsLinks += '<br>'
                blockedPostsLinks += \
                    '<a href="' + url + '">' + url + '</a>'
                urlCtr += 1
            blockedPostsHtml = ''
            if blockedPostsLinks:
                blockedPostsHtml = \
                    getContentWarningButton('blockNumber' + str(ctr),
                                            translate, blockedPostsLinks)
                ctr += 1

            infoForm += \
                '<a href="' + usersPath + '?unblockdomain=' + postDomain + \
                '?handle=' + searchHandle + '">'
            infoForm += '<button class="buttonhighlighted"><span>' + \
                translate['Unblock'] + '</span></button></a> ' + \
                blockedPostsHtml
        else:
            infoForm += \
                '<a href="' + usersPath + '?blockdomain=' + postDomain + \
                '?handle=' + searchHandle + '">'
            if postDomain != domain:
                infoForm += '<button class="button"><span>' + \
                    translate['Block'] + '</span></button>'
            infoForm += '</a>'
        infoForm += '<br>'

    infoForm += '</div>'
    infoForm += htmlFooter()
    return infoForm


def htmlModerationInfo(cssCache: {}, translate: {},
                       baseDir: str, httpPrefix: str,
                       nickname: str) -> str:
    msgStr1 = \
        'These are globally blocked for all accounts on this instance'
    msgStr2 = \
        'Any blocks or suspensions made by moderators will be shown here.'

    infoForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    infoForm = htmlHeaderWithExternalStyle(cssFilename)

    infoForm += \
        '<center><h1><a href="/users/' + nickname + '/moderation">' + \
        translate['Moderation Information'] + \
        '</a></h1></center><br>'

    infoShown = False

    cols = 5
    infoForm += '<div class="container">\n'
    infoForm += '<table class="accountsTable">\n'
    infoForm += '  <colgroup>\n'
    for col in range(cols):
        infoForm += '    <col span="1" class="accountsTableCol">\n'
    infoForm += '  </colgroup>\n'
    infoForm += '<tr>\n'
    col = 0
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if 'inbox@' in acct or 'news@' in acct:
                continue
            accountDir = os.path.join(baseDir + '/accounts', acct)
            acctNickname = acct.split('@')[0]
            actorJson = loadJson(accountDir + '.json')
            if not actorJson:
                continue
            actor = actorJson['id']
            avatarUrl = ''
            if actorJson.get('icon'):
                if actorJson['icon'].get('url'):
                    avatarUrl = actorJson['icon']['url']
            acctUrl = \
                '/users/' + nickname + '?options=' + actor + ';1;' + \
                avatarUrl.replace('/', '-')
            infoForm += '<td>\n<a href="' + acctUrl + '">'
            infoForm += '<img style="width:90%" src="' + avatarUrl + '" />'
            infoForm += '<br>' + acctNickname + '</a>\n</td>\n'
            col += 1
            if col == cols:
                # new row of accounts
                infoForm += '</tr>\n<tr>\n'
        break
    infoForm += '</tr>\n</table>\n'
    infoForm += '</div>\n'

    suspendedFilename = baseDir + '/accounts/suspended.txt'
    if os.path.isfile(suspendedFilename):
        with open(suspendedFilename, "r") as f:
            suspendedStr = f.read()
            infoForm += '<div class="container">\n'
            infoForm += '  <br><b>' + \
                translate['Suspended accounts'] + '</b>'
            infoForm += '  <br>' + \
                translate['These are currently suspended']
            infoForm += \
                '  <textarea id="message" ' + \
                'name="suspended" style="height:200px">' + \
                suspendedStr + '</textarea>\n'
            infoForm += '</div>\n'
            infoShown = True

    blockingFilename = baseDir + '/accounts/blocking.txt'
    if os.path.isfile(blockingFilename):
        with open(blockingFilename, "r") as f:
            blockedStr = f.read()
            infoForm += '<div class="container">\n'
            infoForm += \
                '  <br><b>' + \
                translate['Blocked accounts and hashtags'] + '</b>'
            infoForm += \
                '  <br>' + \
                translate[msgStr1]
            infoForm += \
                '  <textarea id="message" ' + \
                'name="blocked" style="height:700px">' + \
                blockedStr + '</textarea>\n'
            infoForm += '</div>\n'
            infoShown = True

    filtersFilename = baseDir + '/accounts/filters.txt'
    if os.path.isfile(filtersFilename):
        with open(filtersFilename, "r") as f:
            filteredStr = f.read()
            infoForm += '<div class="container">\n'
            infoForm += \
                '  <br><b>' + \
                translate['Filtered words'] + '</b>'
            infoForm += \
                '  <textarea id="message" ' + \
                'name="filtered" style="height:700px">' + \
                filteredStr + '</textarea>\n'
            infoForm += '</div>\n'
            infoShown = True

    if not infoShown:
        infoForm += \
            '<center><p>' + \
            translate[msgStr2] + \
            '</p></center>\n'
    infoForm += htmlFooter()
    return infoForm
