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
from utils import isPublicPostFromUrl
from utils import loadJson
from utils import getConfigParam
from posts import isEditor
from shares import getValidSharedItemID
from webapp_utils import getAltPath
from webapp_utils import getIconsDir
from webapp_utils import getBannerFile
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


def htmlFollowingDataList(baseDir: str, nickname: str,
                          domain: str, domainFull: str) -> str:
    """Returns a datalist of handles being followed
    """
    listStr = '<datalist id="followingHandles">\n'
    followingFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/following.txt'
    if os.path.isfile(followingFilename):
        with open(followingFilename, 'r') as followingFile:
            msg = followingFile.read()
            # add your own handle, so that you can send DMs
            # to yourself as reminders
            msg += nickname + '@' + domainFull + '\n'
            # include petnames
            petnamesFilename = \
                baseDir + '/accounts/' + \
                nickname + '@' + domain + '/petnames.txt'
            if os.path.isfile(petnamesFilename):
                followingList = []
                with open(petnamesFilename, 'r') as petnamesFile:
                    petStr = petnamesFile.read()
                    # extract each petname and append it
                    petnamesList = petStr.split('\n')
                    for pet in petnamesList:
                        followingList.append(pet.split(' ')[0])
                # add the following.txt entries
                followingList += msg.split('\n')
            else:
                # no petnames list exists - just use following.txt
                followingList = msg.split('\n')
            followingList.sort()
            if followingList:
                for followingAddress in followingList:
                    if followingAddress:
                        listStr += \
                            '<option>@' + followingAddress + '</option>\n'
    listStr += '</datalist>\n'
    return listStr


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


def htmlNewPostDropDown(scopeIcon: str, scopeDescription: str,
                        replyStr: str,
                        translate: {},
                        iconsDir: str,
                        showPublicOnDropdown: bool,
                        defaultTimeline: str,
                        pathBase: str,
                        dropdownNewPostSuffix: str,
                        dropdownNewBlogSuffix: str,
                        dropdownUnlistedSuffix: str,
                        dropdownFollowersSuffix: str,
                        dropdownDMSuffix: str,
                        dropdownReminderSuffix: str,
                        dropdownEventSuffix: str,
                        dropdownReportSuffix: str) -> str:
    """Returns the html for a drop down list of new post types
    """
    dropDownContent = '<div class="newPostDropdown">\n'
    dropDownContent += '  <input type="checkbox" ' + \
        'id="my-newPostDropdown" value="" name="my-checkbox">\n'
    dropDownContent += '  <label for="my-newPostDropdown"\n'
    dropDownContent += '     data-toggle="newPostDropdown">\n'
    dropDownContent += '  <img loading="lazy" alt="" title="" src="/' + \
        iconsDir + '/' + scopeIcon + '"/><b>' + \
        scopeDescription + '</b></label>\n'
    dropDownContent += '  <ul>\n'

    if showPublicOnDropdown:
        dropDownContent += \
            '<li><a href="' + pathBase + dropdownNewPostSuffix + \
            '"><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_public.png"/><b>' + \
            translate['Public'] + '</b><br>' + \
            translate['Visible to anyone'] + '</a></li>\n'
        if defaultTimeline == 'tlnews':
            dropDownContent += \
                '<li><a href="' + pathBase + dropdownNewBlogSuffix + \
                '"><img loading="lazy" alt="" title="" src="/' + \
                iconsDir + '/scope_blog.png"/><b>' + \
                translate['Article'] + '</b><br>' + \
                translate['Create an article'] + '</a></li>\n'
        else:
            dropDownContent += \
                '<li><a href="' + pathBase + dropdownNewBlogSuffix + \
                '"><img loading="lazy" alt="" title="" src="/' + \
                iconsDir + '/scope_blog.png"/><b>' + \
                translate['Blog'] + '</b><br>' + \
                translate['Publicly visible post'] + '</a></li>\n'
        dropDownContent += \
            '<li><a href="' + pathBase + dropdownUnlistedSuffix + \
            '"><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_unlisted.png"/><b>' + \
            translate['Unlisted'] + '</b><br>' + \
            translate['Not on public timeline'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownFollowersSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        iconsDir + '/scope_followers.png"/><b>' + \
        translate['Followers'] + '</b><br>' + \
        translate['Only to followers'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownDMSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        iconsDir + '/scope_dm.png"/><b>' + \
        translate['DM'] + '</b><br>' + \
        translate['Only to mentioned people'] + '</a></li>\n'

    dropDownContent += \
        '<li><a href="' + pathBase + dropdownReminderSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        iconsDir + '/scope_reminder.png"/><b>' + \
        translate['Reminder'] + '</b><br>' + \
        translate['Scheduled note to yourself'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownEventSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        iconsDir + '/scope_event.png"/><b>' + \
        translate['Event'] + '</b><br>' + \
        translate['Create an event'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownReportSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        iconsDir + '/scope_report.png"/><b>' + \
        translate['Report'] + '</b><br>' + \
        translate['Send to moderators'] + '</a></li>\n'

    if not replyStr:
        dropDownContent += \
            '<li><a href="' + pathBase + \
            '/newshare"><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_share.png"/><b>' + \
            translate['Shares'] + '</b><br>' + \
            translate['Describe a shared item'] + '</a></li>\n'
        dropDownContent += \
            '<li><a href="' + pathBase + \
            '/newquestion"><img loading="lazy" alt="" title="" src="/' + \
            iconsDir + '/scope_question.png"/><b>' + \
            translate['Question'] + '</b><br>' + \
            translate['Ask a question'] + '</a></li>\n'

    dropDownContent += '  </ul>\n'
    dropDownContent += '</div>\n'
    return dropDownContent


def htmlNewPost(cssCache: {}, mediaInstance: bool, translate: {},
                baseDir: str, httpPrefix: str,
                path: str, inReplyTo: str,
                mentions: [],
                reportUrl: str, pageNumber: int,
                nickname: str, domain: str,
                domainFull: str,
                defaultTimeline: str, newswire: {}) -> str:
    """New post screen
    """
    iconsDir = getIconsDir(baseDir)
    replyStr = ''

    showPublicOnDropdown = True
    messageBoxHeight = 400

    # filename of the banner shown at the top
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)

    if not path.endswith('/newshare'):
        if not path.endswith('/newreport'):
            if not inReplyTo or path.endswith('/newreminder'):
                newPostText = '<p class="new-post-text">' + \
                    translate['Write your post text below.'] + '</p>\n'
            else:
                newPostText = \
                    '<p class="new-post-text">' + \
                    translate['Write your reply to'] + \
                    ' <a href="' + inReplyTo + '">' + \
                    translate['this post'] + '</a></p>\n'
                replyStr = '<input type="hidden" ' + \
                    'name="replyTo" value="' + inReplyTo + '">\n'

                # if replying to a non-public post then also make
                # this post non-public
                if not isPublicPostFromUrl(baseDir, nickname, domain,
                                           inReplyTo):
                    newPostPath = path
                    if '?' in newPostPath:
                        newPostPath = newPostPath.split('?')[0]
                    if newPostPath.endswith('/newpost'):
                        path = path.replace('/newpost', '/newfollowers')
                    elif newPostPath.endswith('/newunlisted'):
                        path = path.replace('/newunlisted', '/newfollowers')
                    showPublicOnDropdown = False
        else:
            newPostText = \
                '<p class="new-post-text">' + \
                translate['Write your report below.'] + '</p>\n'

            # custom report header with any additional instructions
            if os.path.isfile(baseDir + '/accounts/report.txt'):
                with open(baseDir + '/accounts/report.txt', 'r') as file:
                    customReportText = file.read()
                    if '</p>' not in customReportText:
                        customReportText = \
                            '<p class="login-subtext">' + \
                            customReportText + '</p>\n'
                        repStr = '<p class="login-subtext">'
                        customReportText = \
                            customReportText.replace('<p>', repStr)
                        newPostText += customReportText

            idx = 'This message only goes to moderators, even if it ' + \
                'mentions other fediverse addresses.'
            newPostText += \
                '<p class="new-post-subtext">' + translate[idx] + '</p>\n' + \
                '<p class="new-post-subtext">' + translate['Also see'] + \
                ' <a href="/terms">' + \
                translate['Terms of Service'] + '</a></p>\n'
    else:
        newPostText = \
            '<p class="new-post-text">' + \
            translate['Enter the details for your shared item below.'] + \
            '</p>\n'

    if path.endswith('/newquestion'):
        newPostText = \
            '<p class="new-post-text">' + \
            translate['Enter the choices for your question below.'] + \
            '</p>\n'

    if os.path.isfile(baseDir + '/accounts/newpost.txt'):
        with open(baseDir + '/accounts/newpost.txt', 'r') as file:
            newPostText = \
                '<p class="new-post-text">' + file.read() + '</p>\n'

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    newPostCSS = getCSS(baseDir, cssFilename, cssCache)
    if newPostCSS:
        if httpPrefix != 'https':
            newPostCSS = newPostCSS.replace('https://',
                                            httpPrefix + '://')

    if '?' in path:
        path = path.split('?')[0]
    pathBase = path.replace('/newreport', '').replace('/newpost', '')
    pathBase = pathBase.replace('/newblog', '').replace('/newshare', '')
    pathBase = pathBase.replace('/newunlisted', '')
    pathBase = pathBase.replace('/newevent', '')
    pathBase = pathBase.replace('/newreminder', '')
    pathBase = pathBase.replace('/newfollowers', '').replace('/newdm', '')

    newPostImageSection = '    <div class="container">'
    if not path.endswith('/newevent'):
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Image description'] + '</label>\n'
    else:
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Event banner image description'] + '</label>\n'
    newPostImageSection += \
        '      <input type="text" name="imageDescription">\n'

    if path.endswith('/newevent'):
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Banner image'] + '</label>\n'
        newPostImageSection += \
            '      <input type="file" id="attachpic" name="attachpic"'
        newPostImageSection += \
            '            accept=".png, .jpg, .jpeg, .gif, .webp, .avif">\n'
    else:
        newPostImageSection += \
            '      <input type="file" id="attachpic" name="attachpic"'
        newPostImageSection += \
            '            accept=".png, .jpg, .jpeg, .gif, ' + \
            '.webp, .avif, .mp4, .webm, .ogv, .mp3, .ogg">\n'
    newPostImageSection += '    </div>\n'

    scopeIcon = 'scope_public.png'
    scopeDescription = translate['Public']
    placeholderSubject = \
        translate['Subject or Content Warning (optional)'] + '...'
    placeholderMentions = ''
    if inReplyTo:
        # mentionsAndContent = getMentionsString(content)
        placeholderMentions = \
            translate['Replying to'] + '...'
    placeholderMessage = translate['Write something'] + '...'
    extraFields = ''
    endpoint = 'newpost'
    if path.endswith('/newblog'):
        placeholderSubject = translate['Title']
        scopeIcon = 'scope_blog.png'
        if defaultTimeline != 'tlnews':
            scopeDescription = translate['Blog']
        else:
            scopeDescription = translate['Article']
        endpoint = 'newblog'
    elif path.endswith('/newunlisted'):
        scopeIcon = 'scope_unlisted.png'
        scopeDescription = translate['Unlisted']
        endpoint = 'newunlisted'
    elif path.endswith('/newfollowers'):
        scopeIcon = 'scope_followers.png'
        scopeDescription = translate['Followers']
        endpoint = 'newfollowers'
    elif path.endswith('/newdm'):
        scopeIcon = 'scope_dm.png'
        scopeDescription = translate['DM']
        endpoint = 'newdm'
    elif path.endswith('/newreminder'):
        scopeIcon = 'scope_reminder.png'
        scopeDescription = translate['Reminder']
        endpoint = 'newreminder'
    elif path.endswith('/newevent'):
        scopeIcon = 'scope_event.png'
        scopeDescription = translate['Event']
        endpoint = 'newevent'
        placeholderSubject = translate['Event name']
        placeholderMessage = translate['Describe the event'] + '...'
    elif path.endswith('/newreport'):
        scopeIcon = 'scope_report.png'
        scopeDescription = translate['Report']
        endpoint = 'newreport'
    elif path.endswith('/newquestion'):
        scopeIcon = 'scope_question.png'
        scopeDescription = translate['Question']
        placeholderMessage = translate['Enter your question'] + '...'
        endpoint = 'newquestion'
        extraFields = '<div class="container">\n'
        extraFields += '  <label class="labels">' + \
            translate['Possible answers'] + ':</label><br>\n'
        for questionCtr in range(8):
            extraFields += \
                '  <input type="text" class="questionOption" placeholder="' + \
                str(questionCtr + 1) + \
                '" name="questionOption' + str(questionCtr) + '"><br>\n'
        extraFields += \
            '  <label class="labels">' + \
            translate['Duration of listing in days'] + \
            ':</label> <input type="number" name="duration" ' + \
            'min="1" max="365" step="1" value="14"><br>\n'
        extraFields += '</div>'
    elif path.endswith('/newshare'):
        scopeIcon = 'scope_share.png'
        scopeDescription = translate['Shared Item']
        placeholderSubject = translate['Name of the shared item'] + '...'
        placeholderMessage = \
            translate['Description of the item being shared'] + '...'
        endpoint = 'newshare'
        extraFields = '<div class="container">\n'
        extraFields += \
            '  <label class="labels">' + \
            translate['Type of shared item. eg. hat'] + ':</label>\n'
        extraFields += \
            '  <input type="text" class="itemType" name="itemType">\n'
        extraFields += \
            '  <br><label class="labels">' + \
            translate['Category of shared item. eg. clothing'] + ':</label>\n'
        extraFields += \
            '  <input type="text" class="category" name="category">\n'
        extraFields += \
            '  <br><label class="labels">' + \
            translate['Duration of listing in days'] + ':</label>\n'
        extraFields += '  <input type="number" name="duration" ' + \
            'min="1" max="365" step="1" value="14">\n'
        extraFields += '</div>\n'
        extraFields += '<div class="container">\n'
        extraFields += \
            '<label class="labels">' + \
            translate['City or location of the shared item'] + ':</label>\n'
        extraFields += '<input type="text" name="location">\n'
        extraFields += '</div>\n'

    citationsStr = ''
    if endpoint == 'newblog':
        citationsFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/.citations.txt'
        if os.path.isfile(citationsFilename):
            citationsStr = '<div class="container">\n'
            citationsStr += '<p><label class="labels">' + \
                translate['Citations'] + ':</label></p>\n'
            citationsStr += '  <ul>\n'
            citationsSeparator = '#####'
            with open(citationsFilename, "r") as f:
                citations = f.readlines()
                for line in citations:
                    if citationsSeparator not in line:
                        continue
                    sections = line.strip().split(citationsSeparator)
                    if len(sections) != 3:
                        continue
                    title = sections[1]
                    link = sections[2]
                    citationsStr += \
                        '    <li><a href="' + link + '"><cite>' + \
                        title + '</cite></a></li>'
            citationsStr += '  </ul>\n'
            citationsStr += '</div>\n'

    dateAndLocation = ''
    if endpoint != 'newshare' and \
       endpoint != 'newreport' and \
       endpoint != 'newquestion':
        dateAndLocation = '<div class="container">\n'

        if endpoint == 'newevent':
            # event status
            dateAndLocation += '<label class="labels">' + \
                translate['Status of the event'] + ':</label><br>\n'
            dateAndLocation += '<input type="radio" id="tentative" ' + \
                'name="eventStatus" value="tentative">\n'
            dateAndLocation += '<label class="labels" for="tentative">' + \
                translate['Tentative'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="confirmed" ' + \
                'name="eventStatus" value="confirmed" checked>\n'
            dateAndLocation += '<label class="labels" for="confirmed">' + \
                translate['Confirmed'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="cancelled" ' + \
                'name="eventStatus" value="cancelled">\n'
            dateAndLocation += '<label class="labels" for="cancelled">' + \
                translate['Cancelled'] + '</label><br>\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # maximum attendees
            dateAndLocation += '<label class="labels" ' + \
                'for="maximumAttendeeCapacity">' + \
                translate['Maximum attendees'] + ':</label>\n'
            dateAndLocation += '<input type="number" ' + \
                'id="maximumAttendeeCapacity" ' + \
                'name="maximumAttendeeCapacity" min="1" max="999999" ' + \
                'value="100">\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # event joining options
            dateAndLocation += '<label class="labels">' + \
                translate['Joining'] + ':</label><br>\n'
            dateAndLocation += '<input type="radio" id="free" ' + \
                'name="joinMode" value="free" checked>\n'
            dateAndLocation += '<label class="labels" for="free">' + \
                translate['Anyone can join'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="restricted" ' + \
                'name="joinMode" value="restricted">\n'
            dateAndLocation += '<label class="labels" for="female">' + \
                translate['Apply to join'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="invite" ' + \
                'name="joinMode" value="invite">\n'
            dateAndLocation += '<label class="labels" for="other">' + \
                translate['Invitation only'] + '</label>\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # Event posts don't allow replies - they're just an announcement.
            # They also have a few more checkboxes
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="privateEvent"><label class="labels"> ' + \
                translate['This is a private event.'] + '</label></p>\n'
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="anonymousParticipationEnabled">' + \
                '<label class="labels"> ' + \
                translate['Allow anonymous participation.'] + '</label></p>\n'
        else:
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="commentsEnabled" checked><label class="labels"> ' + \
                translate['Allow replies.'] + '</label></p>\n'

        if not inReplyTo and endpoint != 'newevent':
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="schedulePost"><label class="labels"> ' + \
                translate['This is a scheduled post.'] + '</label></p>\n'

        if endpoint != 'newevent':
            dateAndLocation += \
                '<p><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                iconsDir + '/calendar.png"/>\n'
            # select a date and time for this post
            dateAndLocation += '<label class="labels">' + \
                translate['Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="eventDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="eventTime"></label></p>\n'
        else:
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            dateAndLocation += \
                '<p><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                iconsDir + '/calendar.png"/>\n'
            # select start time for the event
            dateAndLocation += '<label class="labels">' + \
                translate['Start Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="eventDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="eventTime"></label></p>\n'
            # select end time for the event
            dateAndLocation += \
                '<br><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                iconsDir + '/calendar.png"/>\n'
            dateAndLocation += '<label class="labels">' + \
                translate['End Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="endDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="endTime"></label>\n'

        if endpoint == 'newevent':
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            dateAndLocation += '<br><label class="labels">' + \
                translate['Moderation policy or code of conduct'] + \
                ': </label>\n'
            dateAndLocation += \
                '    <textarea id="message" ' + \
                'name="repliesModerationOption" style="height:' + \
                str(messageBoxHeight) + 'px"></textarea>\n'
        dateAndLocation += '</div>\n'
        dateAndLocation += '<div class="container">\n'
        dateAndLocation += '<br><label class="labels">' + \
            translate['Location'] + ': </label>\n'
        dateAndLocation += '<input type="text" name="location">\n'
        if endpoint == 'newevent':
            dateAndLocation += '<br><label class="labels">' + \
                translate['Ticket URL'] + ': </label>\n'
            dateAndLocation += '<input type="text" name="ticketUrl">\n'
            dateAndLocation += '<br><label class="labels">' + \
                translate['Categories'] + ': </label>\n'
            dateAndLocation += '<input type="text" name="category">\n'
        dateAndLocation += '</div>\n'

    newPostForm = htmlHeader(cssFilename, newPostCSS)

    newPostForm += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '">\n'
    newPostForm += '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    mentionsStr = ''
    for m in mentions:
        mentionNickname = getNicknameFromActor(m)
        if not mentionNickname:
            continue
        mentionDomain, mentionPort = getDomainFromActor(m)
        if not mentionDomain:
            continue
        if mentionPort:
            mentionsHandle = \
                '@' + mentionNickname + '@' + \
                mentionDomain + ':' + str(mentionPort)
        else:
            mentionsHandle = '@' + mentionNickname + '@' + mentionDomain
        if mentionsHandle not in mentionsStr:
            mentionsStr += mentionsHandle + ' '

    # build suffixes so that any replies or mentions are
    # preserved when switching between scopes
    dropdownNewPostSuffix = '/newpost'
    dropdownNewBlogSuffix = '/newblog'
    dropdownUnlistedSuffix = '/newunlisted'
    dropdownFollowersSuffix = '/newfollowers'
    dropdownDMSuffix = '/newdm'
    dropdownEventSuffix = '/newevent'
    dropdownReminderSuffix = '/newreminder'
    dropdownReportSuffix = '/newreport'
    if inReplyTo or mentions:
        dropdownNewPostSuffix = ''
        dropdownNewBlogSuffix = ''
        dropdownUnlistedSuffix = ''
        dropdownFollowersSuffix = ''
        dropdownDMSuffix = ''
        dropdownEventSuffix = ''
        dropdownReminderSuffix = ''
        dropdownReportSuffix = ''
    if inReplyTo:
        dropdownNewPostSuffix += '?replyto=' + inReplyTo
        dropdownNewBlogSuffix += '?replyto=' + inReplyTo
        dropdownUnlistedSuffix += '?replyto=' + inReplyTo
        dropdownFollowersSuffix += '?replyfollowers=' + inReplyTo
        dropdownDMSuffix += '?replydm=' + inReplyTo
    for mentionedActor in mentions:
        dropdownNewPostSuffix += '?mention=' + mentionedActor
        dropdownNewBlogSuffix += '?mention=' + mentionedActor
        dropdownUnlistedSuffix += '?mention=' + mentionedActor
        dropdownFollowersSuffix += '?mention=' + mentionedActor
        dropdownDMSuffix += '?mention=' + mentionedActor
        dropdownReportSuffix += '?mention=' + mentionedActor

    dropDownContent = ''
    if not reportUrl:
        dropDownContent = \
            htmlNewPostDropDown(scopeIcon, scopeDescription,
                                replyStr,
                                translate,
                                iconsDir,
                                showPublicOnDropdown,
                                defaultTimeline,
                                pathBase,
                                dropdownNewPostSuffix,
                                dropdownNewBlogSuffix,
                                dropdownUnlistedSuffix,
                                dropdownFollowersSuffix,
                                dropdownDMSuffix,
                                dropdownReminderSuffix,
                                dropdownEventSuffix,
                                dropdownReportSuffix)
    else:
        mentionsStr = 'Re: ' + reportUrl + '\n\n' + mentionsStr

    newPostForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + \
        path + '?' + endpoint + '?page=' + str(pageNumber) + '">\n'
    newPostForm += '  <div class="vertical-center">\n'
    newPostForm += \
        '    <label for="nickname"><b>' + newPostText + '</b></label>\n'
    newPostForm += '    <div class="containerNewPost">\n'
    newPostForm += '      <table style="width:100%" border="0"><tr>\n'
    newPostForm += '<td>' + dropDownContent + '</td>\n'

    newPostForm += \
        '      <td><a href="' + pathBase + \
        '/searchemoji"><img loading="lazy" class="emojisearch" ' + \
        'src="/emoji/1F601.png" title="' + \
        translate['Search for emoji'] + '" alt="' + \
        translate['Search for emoji'] + '"/></a></td>\n'
    newPostForm += '      </tr>\n'
    newPostForm += '</table>\n'
    newPostForm += '    </div>\n'

    newPostForm += '    <div class="containerSubmitNewPost"><center>\n'

    # newPostForm += \
    #     '      <a href="' + pathBase + \
    #     '/inbox"><button class="cancelbtn">' + \
    #     translate['Go Back'] + '</button></a>\n'

    # for a new blog if newswire items exist then add a citations button
    if newswire and path.endswith('/newblog'):
        newPostForm += \
            '      <input type="submit" name="submitCitations" value="' + \
            translate['Citations'] + '">\n'

    newPostForm += \
        '      <input type="submit" name="submitPost" value="' + \
        translate['Submit'] + '">\n'

    newPostForm += '    </center></div>\n'

    newPostForm += replyStr
    if mediaInstance and not replyStr:
        newPostForm += newPostImageSection

    newPostForm += \
        '    <label class="labels">' + placeholderSubject + '</label><br>'
    newPostForm += '    <input type="text" name="subject">'
    newPostForm += ''

    selectedStr = ' selected'
    if inReplyTo or endpoint == 'newdm':
        if inReplyTo:
            newPostForm += \
                '    <label class="labels">' + placeholderMentions + \
                '</label><br>\n'
        else:
            newPostForm += \
                '    <a href="/users/' + nickname + \
                '/followingaccounts" title="' + \
                translate['Show a list of addresses to send to'] + '">' \
                '<label class="labels">' + \
                translate['Send to'] + ':' + '</label> 📄</a><br>\n'
        newPostForm += \
            '    <input type="text" name="mentions" ' + \
            'list="followingHandles" value="' + mentionsStr + '" selected>\n'
        newPostForm += \
            htmlFollowingDataList(baseDir, nickname, domain, domainFull)
        newPostForm += ''
        selectedStr = ''

    newPostForm += \
        '    <br><label class="labels">' + placeholderMessage + '</label>'
    if mediaInstance:
        messageBoxHeight = 200

    if endpoint == 'newquestion':
        messageBoxHeight = 100
    elif endpoint == 'newblog':
        messageBoxHeight = 800

    newPostForm += \
        '    <textarea id="message" name="message" style="height:' + \
        str(messageBoxHeight) + 'px"' + selectedStr + '></textarea>\n'
    newPostForm += extraFields + citationsStr + dateAndLocation
    if not mediaInstance or replyStr:
        newPostForm += newPostImageSection
    newPostForm += '  </div>\n'
    newPostForm += '</form>\n'

    if not reportUrl:
        newPostForm = \
            newPostForm.replace('<body>', '<body onload="focusOnMessage()">')

    newPostForm += htmlFooter()
    return newPostForm


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
