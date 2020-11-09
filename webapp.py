__filename__ = "webapp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import time
import os
from shutil import copyfile
from utils import getCSS
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import noOfAccounts
from utils import loadJson
from utils import getConfigParam
from posts import isEditor
from shares import getValidSharedItemID
from webapp_utils import getAltPath
from webapp_utils import getIconsDir
from webapp_utils import htmlHeader
from webapp_utils import htmlFooter
from webapp_post import individualPostAsHtml


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

            profileCSS = getCSS(baseDir, cssFilename, cssCache)
            if profileCSS:
                followingListHtml = htmlHeader(cssFilename, profileCSS)
                for followingAddress in followingList:
                    if followingAddress:
                        followingListHtml += \
                            '<h3>@' + followingAddress + '</h3>'
                followingListHtml += htmlFooter()
                msg = followingListHtml
        return msg
    return ''


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

    infoCSS = getCSS(baseDir, cssFilename, cssCache)
    if infoCSS:
        if httpPrefix != 'https':
            infoCSS = infoCSS.replace('https://',
                                      httpPrefix + '://')
        infoForm = htmlHeader(cssFilename, infoCSS)

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


def htmlEditNewsPost(cssCache: {}, translate: {}, baseDir: str, path: str,
                     domain: str, port: int,
                     httpPrefix: str, postUrl: str) -> str:
    """Edits a news post
    """
    if '/users/' not in path:
        return ''
    pathOriginal = path

    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''

    # is the user an editor?
    if not isEditor(baseDir, nickname):
        return ''

    postUrl = postUrl.replace('/', '#')
    postFilename = locatePost(baseDir, nickname, domain, postUrl)
    if not postFilename:
        return ''
    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return ''

    cssFilename = baseDir + '/epicyon-links.css'
    if os.path.isfile(baseDir + '/links.css'):
        cssFilename = baseDir + '/links.css'

    editCSS = getCSS(baseDir, cssFilename, cssCache)
    if editCSS:
        if httpPrefix != 'https':
            editCSS = \
                editCSS.replace('https://', httpPrefix + '://')

    editNewsPostForm = htmlHeader(cssFilename, editCSS)
    editNewsPostForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/newseditdata">\n'
    editNewsPostForm += \
        '  <div class="vertical-center">\n'
    editNewsPostForm += \
        '    <p class="new-post-text">' + translate['Edit News Post'] + '</p>'
    editNewsPostForm += \
        '    <div class="container">\n'
    editNewsPostForm += \
        '      <a href="' + pathOriginal + '/tlnews">' + \
        '<button class="cancelbtn">' + translate['Go Back'] + '</button></a>\n'
    editNewsPostForm += \
        '      <input type="submit" name="submitEditedNewsPost" value="' + \
        translate['Submit'] + '">\n'
    editNewsPostForm += \
        '    </div>\n'

    editNewsPostForm += \
        '<div class="container">'

    editNewsPostForm += \
        '  <input type="hidden" name="newsPostUrl" value="' + \
        postUrl + '">\n'

    newsPostTitle = postJsonObject['object']['summary']
    editNewsPostForm += \
        '  <input type="text" name="newsPostTitle" value="' + \
        newsPostTitle + '"><br>\n'

    newsPostContent = postJsonObject['object']['content']
    editNewsPostForm += \
        '  <textarea id="message" name="editedNewsPost" ' + \
        'style="height:600px">' + newsPostContent + '</textarea>'

    editNewsPostForm += \
        '</div>'

    editNewsPostForm += htmlFooter()
    return editNewsPostForm


def htmlGetLoginCredentials(loginParams: str,
                            lastLoginTime: int) -> (str, str, bool):
    """Receives login credentials via HTTPServer POST
    """
    if not loginParams.startswith('username='):
        return None, None, None
    # minimum time between login attempts
    currTime = int(time.time())
    if currTime < lastLoginTime+10:
        return None, None, None
    if '&' not in loginParams:
        return None, None, None
    loginArgs = loginParams.split('&')
    nickname = None
    password = None
    register = False
    for arg in loginArgs:
        if '=' in arg:
            if arg.split('=', 1)[0] == 'username':
                nickname = arg.split('=', 1)[1]
            elif arg.split('=', 1)[0] == 'password':
                password = arg.split('=', 1)[1]
            elif arg.split('=', 1)[0] == 'register':
                register = True
    return nickname, password, register


def htmlLogin(cssCache: {}, translate: {},
              baseDir: str, autocomplete=True) -> str:
    """Shows the login screen
    """
    accounts = noOfAccounts(baseDir)

    loginImage = 'login.png'
    loginImageFilename = None
    if os.path.isfile(baseDir + '/accounts/' + loginImage):
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.jpg'):
        loginImage = 'login.jpg'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.jpeg'):
        loginImage = 'login.jpeg'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.gif'):
        loginImage = 'login.gif'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.webp'):
        loginImage = 'login.webp'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.avif'):
        loginImage = 'login.avif'
        loginImageFilename = baseDir + '/accounts/' + loginImage

    if not loginImageFilename:
        loginImageFilename = baseDir + '/accounts/' + loginImage
        copyfile(baseDir + '/img/login.png', loginImageFilename)

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    if accounts > 0:
        loginText = \
            '<p class="login-text">' + \
            translate['Welcome. Please enter your login details below.'] + \
            '</p>'
    else:
        loginText = \
            '<p class="login-text">' + \
            translate['Please enter some credentials'] + '</p>'
        loginText += \
            '<p class="login-text">' + \
            translate['You will become the admin of this site.'] + \
            '</p>'
    if os.path.isfile(baseDir + '/accounts/login.txt'):
        # custom login message
        with open(baseDir + '/accounts/login.txt', 'r') as file:
            loginText = '<p class="login-text">' + file.read() + '</p>'

    cssFilename = baseDir + '/epicyon-login.css'
    if os.path.isfile(baseDir + '/login.css'):
        cssFilename = baseDir + '/login.css'

    loginCSS = getCSS(baseDir, cssFilename, cssCache)
    if not loginCSS:
        print('ERROR: login css file missing ' + cssFilename)
        return None

    # show the register button
    registerButtonStr = ''
    if getConfigParam(baseDir, 'registration') == 'open':
        if int(getConfigParam(baseDir, 'registrationsRemaining')) > 0:
            if accounts > 0:
                idx = 'Welcome. Please login or register a new account.'
                loginText = \
                    '<p class="login-text">' + \
                    translate[idx] + \
                    '</p>'
            registerButtonStr = \
                '<button type="submit" name="register">Register</button>'

    TOSstr = \
        '<p class="login-text"><a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>'
    TOSstr += \
        '<p class="login-text"><a href="/about">' + \
        translate['About this Instance'] + '</a></p>'

    loginButtonStr = ''
    if accounts > 0:
        loginButtonStr = \
            '<button type="submit" name="submit">' + \
            translate['Login'] + '</button>'

    autocompleteStr = ''
    if not autocomplete:
        autocompleteStr = 'autocomplete="off" value=""'

    loginForm = htmlHeader(cssFilename, loginCSS)
    loginForm += '<br>\n'
    loginForm += '<form method="POST" action="/login">\n'
    loginForm += '  <div class="imgcontainer">\n'
    loginForm += \
        '    <img loading="lazy" src="' + loginImage + \
        '" alt="login image" class="loginimage">\n'
    loginForm += loginText + TOSstr + '\n'
    loginForm += '  </div>\n'
    loginForm += '\n'
    loginForm += '  <div class="container">\n'
    loginForm += '    <label for="nickname"><b>' + \
        translate['Nickname'] + '</b></label>\n'
    loginForm += \
        '    <input type="text" ' + autocompleteStr + ' placeholder="' + \
        translate['Enter Nickname'] + '" name="username" required autofocus>\n'
    loginForm += '\n'
    loginForm += '    <label for="password"><b>' + \
        translate['Password'] + '</b></label>\n'
    loginForm += \
        '    <input type="password" ' + autocompleteStr + \
        ' placeholder="' + translate['Enter Password'] + \
        '" name="password" required>\n'
    loginForm += loginButtonStr + registerButtonStr + '\n'
    loginForm += '  </div>\n'
    loginForm += '</form>\n'
    loginForm += \
        '<a href="https://gitlab.com/bashrc2/epicyon">' + \
        '<img loading="lazy" class="license" title="' + \
        translate['Get the source code'] + '" alt="' + \
        translate['Get the source code'] + '" src="/icons/agpl.png" /></a>\n'
    loginForm += htmlFooter()
    return loginForm


def htmlTermsOfService(cssCache: {}, baseDir: str,
                       httpPrefix: str, domainFull: str) -> str:
    """Show the terms of service screen
    """
    adminNickname = getConfigParam(baseDir, 'admin')
    if not os.path.isfile(baseDir + '/accounts/tos.txt'):
        copyfile(baseDir + '/default_tos.txt',
                 baseDir + '/accounts/tos.txt')

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    TOSText = 'Terms of Service go here.'
    if os.path.isfile(baseDir + '/accounts/tos.txt'):
        with open(baseDir + '/accounts/tos.txt', 'r') as file:
            TOSText = file.read()

    TOSForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    termsCSS = getCSS(baseDir, cssFilename, cssCache)
    if termsCSS:
        if httpPrefix != 'https':
            termsCSS = termsCSS.replace('https://', httpPrefix+'://')

        TOSForm = htmlHeader(cssFilename, termsCSS)
        TOSForm += '<div class="container">' + TOSText + '</div>\n'
        if adminNickname:
            adminActor = httpPrefix + '://' + domainFull + \
                '/users/' + adminNickname
            TOSForm += \
                '<div class="container"><center>\n' + \
                '<p class="administeredby">Administered by <a href="' + \
                adminActor + '">' + adminNickname + '</a></p>\n' + \
                '</center></div>\n'
        TOSForm += htmlFooter()
    return TOSForm


def htmlAbout(cssCache: {}, baseDir: str, httpPrefix: str,
              domainFull: str, onionDomain: str) -> str:
    """Show the about screen
    """
    adminNickname = getConfigParam(baseDir, 'admin')
    if not os.path.isfile(baseDir + '/accounts/about.txt'):
        copyfile(baseDir + '/default_about.txt',
                 baseDir + '/accounts/about.txt')

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    aboutText = 'Information about this instance goes here.'
    if os.path.isfile(baseDir + '/accounts/about.txt'):
        with open(baseDir + '/accounts/about.txt', 'r') as aboutFile:
            aboutText = aboutFile.read()

    aboutForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    aboutCSS = getCSS(baseDir, cssFilename, cssCache)
    if aboutCSS:
        if httpPrefix != 'http':
            aboutCSS = aboutCSS.replace('https://',
                                        httpPrefix + '://')

        aboutForm = htmlHeader(cssFilename, aboutCSS)
        aboutForm += '<div class="container">' + aboutText + '</div>'
        if onionDomain:
            aboutForm += \
                '<div class="container"><center>\n' + \
                '<p class="administeredby">' + \
                'http://' + onionDomain + '</p>\n</center></div>\n'
        if adminNickname:
            adminActor = '/users/' + adminNickname
            aboutForm += \
                '<div class="container"><center>\n' + \
                '<p class="administeredby">Administered by <a href="' + \
                adminActor + '">' + adminNickname + '</a></p>\n' + \
                '</center></div>\n'
        aboutForm += htmlFooter()
    return aboutForm


def htmlHashtagBlocked(cssCache: {}, baseDir: str, translate: {}) -> str:
    """Show the screen for a blocked hashtag
    """
    blockedHashtagForm = ''
    cssFilename = baseDir + '/epicyon-suspended.css'
    if os.path.isfile(baseDir + '/suspended.css'):
        cssFilename = baseDir + '/suspended.css'

    blockedHashtagCSS = getCSS(baseDir, cssFilename, cssCache)
    if blockedHashtagCSS:
        blockedHashtagForm = htmlHeader(cssFilename, blockedHashtagCSS)
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


def htmlSuspended(cssCache: {}, baseDir: str) -> str:
    """Show the screen for suspended accounts
    """
    suspendedForm = ''
    cssFilename = baseDir + '/epicyon-suspended.css'
    if os.path.isfile(baseDir + '/suspended.css'):
        cssFilename = baseDir + '/suspended.css'

    suspendedCSS = getCSS(baseDir, cssFilename, cssCache)
    if suspendedCSS:
        suspendedForm = htmlHeader(cssFilename, suspendedCSS)
        suspendedForm += '<div><center>\n'
        suspendedForm += '  <p class="screentitle">Account Suspended</p>\n'
        suspendedForm += '  <p>See <a href="/terms">Terms of Service</a></p>\n'
        suspendedForm += '</center></div>\n'
        suspendedForm += htmlFooter()
    return suspendedForm


def htmlRemoveSharedItem(cssCache: {}, translate: {}, baseDir: str,
                         actor: str, shareName: str,
                         callingDomain: str) -> str:
    """Shows a screen asking to confirm the removal of a shared item
    """
    itemID = getValidSharedItemID(shareName)
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    domainFull = domain
    if port:
        if port != 80 and port != 443:
            domainFull = domain + ':' + str(port)
    sharesFile = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/shares.json'
    if not os.path.isfile(sharesFile):
        print('ERROR: no shares file ' + sharesFile)
        return None
    sharesJson = loadJson(sharesFile)
    if not sharesJson:
        print('ERROR: unable to load shares.json')
        return None
    if not sharesJson.get(itemID):
        print('ERROR: share named "' + itemID + '" is not in ' + sharesFile)
        return None
    sharedItemDisplayName = sharesJson[itemID]['displayName']
    sharedItemImageUrl = None
    if sharesJson[itemID].get('imageUrl'):
        sharedItemImageUrl = sharesJson[itemID]['imageUrl']

    if os.path.isfile(baseDir + '/img/shares-background.png'):
        if not os.path.isfile(baseDir + '/accounts/shares-background.png'):
            copyfile(baseDir + '/img/shares-background.png',
                     baseDir + '/accounts/shares-background.png')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    sharesStr = htmlHeader(cssFilename, profileStyle)
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
    sharesStr += '  <form method="POST" action="' + postActor + '/rmshare">\n'
    sharesStr += \
        '    <input type="hidden" name="actor" value="' + actor + '">\n'
    sharesStr += '    <input type="hidden" name="shareName" value="' + \
        shareName + '">\n'
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
    iconsDir = getIconsDir(baseDir)
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

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if profileStyle:
        if httpPrefix != 'https':
            profileStyle = profileStyle.replace('https://',
                                                httpPrefix + '://')
        deletePostStr = htmlHeader(cssFilename, profileStyle)
        deletePostStr += \
            individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                                 iconsDir, translate, pageNumber,
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


def htmlFollowConfirm(cssCache: {}, translate: {}, baseDir: str,
                      originPathStr: str,
                      followActor: str,
                      followProfileUrl: str) -> str:
    """Asks to confirm a follow
    """
    followDomain, port = getDomainFromActor(followActor)

    if os.path.isfile(baseDir + '/accounts/follow-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/follow-background.jpg'):
            copyfile(baseDir + '/accounts/follow-background-custom.jpg',
                     baseDir + '/accounts/follow-background.jpg')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    followStr = htmlHeader(cssFilename, profileStyle)
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


def htmlUnfollowConfirm(cssCache: {}, translate: {}, baseDir: str,
                        originPathStr: str,
                        followActor: str,
                        followProfileUrl: str) -> str:
    """Asks to confirm unfollowing an actor
    """
    followDomain, port = getDomainFromActor(followActor)

    if os.path.isfile(baseDir + '/accounts/follow-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/follow-background.jpg'):
            copyfile(baseDir + '/accounts/follow-background-custom.jpg',
                     baseDir + '/accounts/follow-background.jpg')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)

    followStr = htmlHeader(cssFilename, profileStyle)
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


def htmlUnblockConfirm(cssCache: {}, translate: {}, baseDir: str,
                       originPathStr: str,
                       blockActor: str,
                       blockProfileUrl: str) -> str:
    """Asks to confirm unblocking an actor
    """
    blockDomain, port = getDomainFromActor(blockActor)

    if os.path.isfile(baseDir + '/img/block-background.png'):
        if not os.path.isfile(baseDir + '/accounts/block-background.png'):
            copyfile(baseDir + '/img/block-background.png',
                     baseDir + '/accounts/block-background.png')

    cssFilename = baseDir + '/epicyon-follow.css'
    if os.path.isfile(baseDir + '/follow.css'):
        cssFilename = baseDir + '/follow.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)

    blockStr = htmlHeader(cssFilename, profileStyle)
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
