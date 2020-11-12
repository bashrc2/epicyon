__filename__ = "webapp_moderation.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from webapp_timeline import htmlTimeline
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


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
                   authorized: bool) -> str:
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
                        authorized)


def htmlModerationInfo(cssCache: {}, translate: {},
                       baseDir: str, httpPrefix: str) -> str:
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
        '<center><h1>' + \
        translate['Moderation Information'] + \
        '</h1></center>'

    infoShown = False
    suspendedFilename = baseDir + '/accounts/suspended.txt'
    if os.path.isfile(suspendedFilename):
        with open(suspendedFilename, "r") as f:
            suspendedStr = f.read()
            infoForm += '<div class="container">'
            infoForm += '  <br><b>' + \
                translate['Suspended accounts'] + '</b>'
            infoForm += '  <br>' + \
                translate['These are currently suspended']
            infoForm += \
                '  <textarea id="message" ' + \
                'name="suspended" style="height:200px">' + \
                suspendedStr + '</textarea>'
            infoForm += '</div>'
            infoShown = True

    blockingFilename = baseDir + '/accounts/blocking.txt'
    if os.path.isfile(blockingFilename):
        with open(blockingFilename, "r") as f:
            blockedStr = f.read()
            infoForm += '<div class="container">'
            infoForm += \
                '  <br><b>' + \
                translate['Blocked accounts and hashtags'] + '</b>'
            infoForm += \
                '  <br>' + \
                translate[msgStr1]
            infoForm += \
                '  <textarea id="message" ' + \
                'name="blocked" style="height:700px">' + \
                blockedStr + '</textarea>'
            infoForm += '</div>'
            infoShown = True
    if not infoShown:
        infoForm += \
            '<center><p>' + \
            translate[msgStr2] + \
            '</p></center>'
    infoForm += htmlFooter()
    return infoForm
