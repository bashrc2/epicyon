__filename__ = "webapp_deleteconfirm.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import loadJson
from webapp_utils import getAltPath
from webapp_utils import getIconsWebPath
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_post import individualPostAsHtml


def htmlDeletePost(cssCache: {},
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate, pageNumber: int,
                   session, baseDir: str, messageId: str,
                   httpPrefix: str, projectVersion: str,
                   wfRequest: {}, personCache: {},
                   callingDomain: str,
                   YTReplacementDomain: str,
                   showPublishedDateOnly: bool) -> str:
    """Shows a screen asking to confirm the deletion of a post
    """
    if '/statuses/' not in messageId:
        return None
    iconsPath = getIconsWebPath(baseDir)
    actor = messageId.split('/statuses/')[0]
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    domainFull = domain
    if port:
        if port != 80 and port != 443:
            domainFull = domain + ':' + str(port)

    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        return None

    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return None

    if os.path.isfile(baseDir + '/img/delete-background.png'):
        if not os.path.isfile(baseDir + '/accounts/delete-background.png'):
            copyfile(baseDir + '/img/delete-background.png',
                     baseDir + '/accounts/delete-background.png')

    deletePostStr = None
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    deletePostStr = htmlHeaderWithExternalStyle(cssFilename)
    deletePostStr += \
        individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                             iconsPath, translate, pageNumber,
                             baseDir, session, wfRequest, personCache,
                             nickname, domain, port, postJsonObject,
                             None, True, False,
                             httpPrefix, projectVersion, 'outbox',
                             YTReplacementDomain,
                             showPublishedDateOnly,
                             False, False, False, False, False)
    deletePostStr += '<center>'
    deletePostStr += \
        '  <p class="followText">' + \
        translate['Delete this post?'] + '</p>'

    postActor = getAltPath(actor, domainFull, callingDomain)
    deletePostStr += \
        '  <form method="POST" action="' + postActor + '/rmpost">\n'
    deletePostStr += \
        '    <input type="hidden" name="pageNumber" value="' + \
        str(pageNumber) + '">\n'
    deletePostStr += \
        '    <input type="hidden" name="messageId" value="' + \
        messageId + '">\n'
    deletePostStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    deletePostStr += \
        '    <a href="' + actor + '/inbox"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    deletePostStr += '  </form>\n'
    deletePostStr += '</center>\n'
    deletePostStr += htmlFooter()
    return deletePostStr
