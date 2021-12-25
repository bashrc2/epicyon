__filename__ = "webapp_confirm.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
from utils import getFullDomain
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import loadJson
from utils import getConfigParam
from utils import getAltPath
from utils import acctDir
from webapp_utils import setCustomBackground
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_post import individualPostAsHtml


def htmlConfirmDelete(cssCache: {},
                      recentPostsCache: {}, maxRecentPosts: int,
                      translate, pageNumber: int,
                      session, base_dir: str, messageId: str,
                      http_prefix: str, projectVersion: str,
                      cachedWebfingers: {}, personCache: {},
                      callingDomain: str,
                      yt_replace_domain: str,
                      twitterReplacementDomain: str,
                      show_published_date_only: bool,
                      peertubeInstances: [],
                      allow_local_network_access: bool,
                      themeName: str, systemLanguage: str,
                      max_like_count: int, signingPrivateKeyPem: str,
                      CWlists: {}, lists_enabled: str) -> str:
    """Shows a screen asking to confirm the deletion of a post
    """
    if '/statuses/' not in messageId:
        return None
    actor = messageId.split('/statuses/')[0]
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    domainFull = getFullDomain(domain, port)

    postFilename = locatePost(base_dir, nickname, domain, messageId)
    if not postFilename:
        return None

    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return None

    deletePostStr = None
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(base_dir, 'instanceTitle')
    deletePostStr = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    deletePostStr += \
        individualPostAsHtml(signingPrivateKeyPem,
                             True, recentPostsCache, maxRecentPosts,
                             translate, pageNumber,
                             base_dir, session, cachedWebfingers, personCache,
                             nickname, domain, port, postJsonObject,
                             None, True, False,
                             http_prefix, projectVersion, 'outbox',
                             yt_replace_domain,
                             twitterReplacementDomain,
                             show_published_date_only,
                             peertubeInstances, allow_local_network_access,
                             themeName, systemLanguage, max_like_count,
                             False, False, False, False, False, False,
                             CWlists, lists_enabled)
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


def htmlConfirmRemoveSharedItem(cssCache: {}, translate: {}, base_dir: str,
                                actor: str, itemID: str,
                                callingDomain: str,
                                sharesFileType: str) -> str:
    """Shows a screen asking to confirm the removal of a shared item
    """
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    domainFull = getFullDomain(domain, port)
    sharesFile = \
        acctDir(base_dir, nickname, domain) + '/' + sharesFileType + '.json'
    if not os.path.isfile(sharesFile):
        print('ERROR: no ' + sharesFileType + ' file ' + sharesFile)
        return None
    sharesJson = loadJson(sharesFile)
    if not sharesJson:
        print('ERROR: unable to load ' + sharesFileType + '.json')
        return None
    if not sharesJson.get(itemID):
        print('ERROR: share named "' + itemID + '" is not in ' + sharesFile)
        return None
    sharedItemDisplayName = sharesJson[itemID]['displayName']
    sharedItemImageUrl = None
    if sharesJson[itemID].get('imageUrl'):
        sharedItemImageUrl = sharesJson[itemID]['imageUrl']

    setCustomBackground(base_dir, 'shares-background', 'follow-background')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = getConfigParam(base_dir, 'instanceTitle')
    sharesStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    sharesStr += '<div class="follow">\n'
    sharesStr += '  <div class="followAvatar">\n'
    sharesStr += '  <center>\n'
    if sharedItemImageUrl:
        sharesStr += '  <img loading="lazy" src="' + \
            sharedItemImageUrl + '"/>\n'
    sharesStr += \
        '  <p class="followText">' + translate['Remove'] + \
        ' ' + sharedItemDisplayName + ' ?</p>\n'
    postActor = getAltPath(actor, domainFull, callingDomain)
    if sharesFileType == 'shares':
        endpoint = 'rmshare'
    else:
        endpoint = 'rmwanted'
    sharesStr += \
        '  <form method="POST" action="' + postActor + '/' + endpoint + '">\n'
    sharesStr += \
        '    <input type="hidden" name="actor" value="' + actor + '">\n'
    sharesStr += '    <input type="hidden" name="itemID" value="' + \
        itemID + '">\n'
    sharesStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    sharesStr += \
        '    <a href="' + actor + '/inbox' + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    sharesStr += '  </form>\n'
    sharesStr += '  </center>\n'
    sharesStr += '  </div>\n'
    sharesStr += '</div>\n'
    sharesStr += htmlFooter()
    return sharesStr


def htmlConfirmFollow(cssCache: {}, translate: {}, base_dir: str,
                      originPathStr: str,
                      followActor: str,
                      followProfileUrl: str) -> str:
    """Asks to confirm a follow
    """
    followDomain, port = getDomainFromActor(followActor)

    if os.path.isfile(base_dir + '/accounts/follow-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/follow-background.jpg'):
            copyfile(base_dir + '/accounts/follow-background-custom.jpg',
                     base_dir + '/accounts/follow-background.jpg')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = getConfigParam(base_dir, 'instanceTitle')
    followStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    followStr += '<div class="follow">\n'
    followStr += '  <div class="followAvatar">\n'
    followStr += '  <center>\n'
    followStr += '  <a href="' + followActor + '">\n'
    followStr += '  <img loading="lazy" src="' + followProfileUrl + '"/></a>\n'
    followStr += \
        '  <p class="followText">' + translate['Follow'] + ' ' + \
        getNicknameFromActor(followActor) + '@' + followDomain + ' ?</p>\n'
    followStr += '  <form method="POST" action="' + \
        originPathStr + '/followconfirm">\n'
    followStr += '    <input type="hidden" name="actor" value="' + \
        followActor + '">\n'
    followStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    followStr += \
        '    <a href="' + originPathStr + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    followStr += '  </form>\n'
    followStr += '</center>\n'
    followStr += '</div>\n'
    followStr += '</div>\n'
    followStr += htmlFooter()
    return followStr


def htmlConfirmUnfollow(cssCache: {}, translate: {}, base_dir: str,
                        originPathStr: str,
                        followActor: str,
                        followProfileUrl: str) -> str:
    """Asks to confirm unfollowing an actor
    """
    followDomain, port = getDomainFromActor(followActor)

    if os.path.isfile(base_dir + '/accounts/follow-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/follow-background.jpg'):
            copyfile(base_dir + '/accounts/follow-background-custom.jpg',
                     base_dir + '/accounts/follow-background.jpg')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = getConfigParam(base_dir, 'instanceTitle')
    followStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    followStr += '<div class="follow">\n'
    followStr += '  <div class="followAvatar">\n'
    followStr += '  <center>\n'
    followStr += '  <a href="' + followActor + '">\n'
    followStr += '  <img loading="lazy" src="' + followProfileUrl + '"/></a>\n'
    followStr += \
        '  <p class="followText">' + translate['Stop following'] + \
        ' ' + getNicknameFromActor(followActor) + \
        '@' + followDomain + ' ?</p>\n'
    followStr += '  <form method="POST" action="' + \
        originPathStr + '/unfollowconfirm">\n'
    followStr += '    <input type="hidden" name="actor" value="' + \
        followActor + '">\n'
    followStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    followStr += \
        '    <a href="' + originPathStr + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    followStr += '  </form>\n'
    followStr += '</center>\n'
    followStr += '</div>\n'
    followStr += '</div>\n'
    followStr += htmlFooter()
    return followStr


def htmlConfirmUnblock(cssCache: {}, translate: {}, base_dir: str,
                       originPathStr: str,
                       blockActor: str,
                       blockProfileUrl: str) -> str:
    """Asks to confirm unblocking an actor
    """
    blockDomain, port = getDomainFromActor(blockActor)

    setCustomBackground(base_dir, 'block-background', 'follow-background')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = getConfigParam(base_dir, 'instanceTitle')
    blockStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    blockStr += '<div class="block">\n'
    blockStr += '  <div class="blockAvatar">\n'
    blockStr += '  <center>\n'
    blockStr += '  <a href="' + blockActor + '">\n'
    blockStr += '  <img loading="lazy" src="' + blockProfileUrl + '"/></a>\n'
    blockStr += \
        '  <p class="blockText">' + translate['Stop blocking'] + ' ' + \
        getNicknameFromActor(blockActor) + '@' + blockDomain + ' ?</p>\n'
    blockStr += '  <form method="POST" action="' + \
        originPathStr + '/unblockconfirm">\n'
    blockStr += '    <input type="hidden" name="actor" value="' + \
        blockActor + '">\n'
    blockStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    blockStr += \
        '    <a href="' + originPathStr + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    blockStr += '  </form>\n'
    blockStr += '</center>\n'
    blockStr += '</div>\n'
    blockStr += '</div>\n'
    blockStr += htmlFooter()
    return blockStr
