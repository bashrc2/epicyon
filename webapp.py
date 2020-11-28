__filename__ = "webapp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def htmlFollowingList(cssCache: {}, baseDir: str,
                      followingFilename: str) -> str:
    """Returns a list of handles being followed
    """
    with open(followingFilename, 'r') as followingFile:
        msg = followingFile.read()
        followingList = msg.split('\n')
        followingList.sort()
        if followingList:
            cssFilename = baseDir + '/epicyon-profile.css'
            if os.path.isfile(baseDir + '/epicyon.css'):
                cssFilename = baseDir + '/epicyon.css'

            followingListHtml = htmlHeaderWithExternalStyle(cssFilename)
            for followingAddress in followingList:
                if followingAddress:
                    followingListHtml += \
                        '<h3>@' + followingAddress + '</h3>'
            followingListHtml += htmlFooter()
            msg = followingListHtml
        return msg
    return ''


def htmlHashtagBlocked(cssCache: {}, baseDir: str, translate: {}) -> str:
    """Show the screen for a blocked hashtag
    """
    blockedHashtagForm = ''
    cssFilename = baseDir + '/epicyon-suspended.css'
    if os.path.isfile(baseDir + '/suspended.css'):
        cssFilename = baseDir + '/suspended.css'

    blockedHashtagForm = htmlHeaderWithExternalStyle(cssFilename)
    blockedHashtagForm += '<div><center>\n'
    blockedHashtagForm += \
        '  <p class="screentitle">' + \
        translate['Hashtag Blocked'] + '</p>\n'
    blockedHashtagForm += \
        '  <p>See <a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>\n'
    blockedHashtagForm += '</center></div>\n'
    blockedHashtagForm += htmlFooter()
    return blockedHashtagForm
