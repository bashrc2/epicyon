__filename__ = "webapp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import time
import os
from datetime import datetime
from datetime import date
from shutil import copyfile
from pprint import pprint
from person import personBoxJson
from person import isPersonSnoozed
from pgp import getEmailAddress
from pgp import getPGPpubKey
from pgp import getPGPfingerprint
from xmpp import getXmppAddress
from ssb import getSSBAddress
from tox import getToxAddress
from matrix import getMatrixAddress
from donate import getDonationUrl
from utils import weekDayOfMonthStart
from utils import getCSS
from utils import isSystemAccount
from utils import removeIdEnding
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import noOfAccounts
from utils import isPublicPostFromUrl
from utils import loadJson
from utils import getConfigParam
from utils import votesOnNewswireItem
from utils import removeHtml
from follow import isFollowingActor
from follow import followerApprovalActive
from webfinger import webfingerHandle
from posts import getPersonBox
from posts import getUserUrl
from posts import parseUserFeed
from posts import populateRepliesJson
from posts import isModerator
from posts import isEditor
from session import getJson
from blocking import isBlocked
from content import removeLongWords
from skills import getSkills
from shares import getValidSharedItemID
from happening import todaysEventsCheck
from happening import thisWeeksEventsCheck
from happening import getCalendarEvents
from happening import getTodaysEvents
from theme import getThemesList
from petnames import getPetName
from followingCalendar import receivingCalendarEvents
from webapp_utils import getAltPath
from webapp_utils import getBlogAddress
from webapp_utils import getPersonAvatarUrl
from webapp_utils import getIconsDir
from webapp_utils import scheduledPostsExist
from webapp_utils import sharesTimelineJson
from webapp_utils import getImageFile
from webapp_utils import getBannerFile
from webapp_utils import getLeftImageFile
from webapp_utils import getRightImageFile
from webapp_utils import htmlHeader
from webapp_utils import htmlFooter
from webapp_utils import addEmojiToDisplayName
from webapp_utils import htmlPostSeparator
from webapp_post import individualPostAsHtml
from webapp_post import preparePostFromHtmlCache


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


def htmlEditLinks(cssCache: {}, translate: {}, baseDir: str, path: str,
                  domain: str, port: int, httpPrefix: str,
                  defaultTimeline: str) -> str:
    """Shows the edit links screen
    """
    if '/users/' not in path:
        return ''
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '')

    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''

    # is the user a moderator?
    if not isEditor(baseDir, nickname):
        return ''

    cssFilename = baseDir + '/epicyon-links.css'
    if os.path.isfile(baseDir + '/links.css'):
        cssFilename = baseDir + '/links.css'

    editCSS = getCSS(baseDir, cssFilename, cssCache)
    if editCSS:
        if httpPrefix != 'https':
            editCSS = \
                editCSS.replace('https://', httpPrefix + '://')

    # filename of the banner shown at the top
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)

    editLinksForm = htmlHeader(cssFilename, editCSS)

    # top banner
    editLinksForm += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '">\n'
    editLinksForm += '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    editLinksForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/linksdata">\n'
    editLinksForm += \
        '  <div class="vertical-center">\n'
    editLinksForm += \
        '    <p class="new-post-text">' + translate['Edit Links'] + '</p>'
    editLinksForm += \
        '    <div class="container">\n'
    # editLinksForm += \
    #     '      <a href="' + pathOriginal + '"><button class="cancelbtn">' + \
    #     translate['Go Back'] + '</button></a>\n'
    editLinksForm += \
        '      <center>\n' + \
        '        <input type="submit" name="submitLinks" value="' + \
        translate['Submit'] + '">\n' + \
        '      </center>\n'
    editLinksForm += \
        '    </div>\n'

    linksFilename = baseDir + '/accounts/links.txt'
    linksStr = ''
    if os.path.isfile(linksFilename):
        with open(linksFilename, 'r') as fp:
            linksStr = fp.read()

    editLinksForm += \
        '<div class="container">'
    editLinksForm += \
        '  ' + \
        translate['One link per line. Description followed by the link.'] + \
        '<br>'
    editLinksForm += \
        '  <textarea id="message" name="editedLinks" style="height:80vh">' + \
        linksStr + '</textarea>'
    editLinksForm += \
        '</div>'

    editLinksForm += htmlFooter()
    return editLinksForm


def htmlEditNewswire(cssCache: {}, translate: {}, baseDir: str, path: str,
                     domain: str, port: int, httpPrefix: str,
                     defaultTimeline: str) -> str:
    """Shows the edit newswire screen
    """
    if '/users/' not in path:
        return ''
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '')

    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''

    # is the user a moderator?
    if not isModerator(baseDir, nickname):
        return ''

    cssFilename = baseDir + '/epicyon-links.css'
    if os.path.isfile(baseDir + '/links.css'):
        cssFilename = baseDir + '/links.css'

    editCSS = getCSS(baseDir, cssFilename, cssCache)
    if editCSS:
        if httpPrefix != 'https':
            editCSS = \
                editCSS.replace('https://', httpPrefix + '://')

    # filename of the banner shown at the top
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)

    editNewswireForm = htmlHeader(cssFilename, editCSS)

    # top banner
    editNewswireForm += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '">\n'
    editNewswireForm += '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    editNewswireForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/newswiredata">\n'
    editNewswireForm += \
        '  <div class="vertical-center">\n'
    editNewswireForm += \
        '    <p class="new-post-text">' + translate['Edit newswire'] + '</p>'
    editNewswireForm += \
        '    <div class="container">\n'
    # editNewswireForm += \
    #     '      <a href="' + pathOriginal + '"><button class="cancelbtn">' + \
    #     translate['Go Back'] + '</button></a>\n'
    editNewswireForm += \
        '      <center>\n' + \
        '      <input type="submit" name="submitNewswire" value="' + \
        translate['Submit'] + '">\n' + \
        '      </center>\n'
    editNewswireForm += \
        '    </div>\n'

    newswireFilename = baseDir + '/accounts/newswire.txt'
    newswireStr = ''
    if os.path.isfile(newswireFilename):
        with open(newswireFilename, 'r') as fp:
            newswireStr = fp.read()

    editNewswireForm += \
        '<div class="container">'

    editNewswireForm += \
        '  ' + \
        translate['Add RSS feed links below.'] + \
        '<br>'
    editNewswireForm += \
        '  <textarea id="message" name="editedNewswire" ' + \
        'style="height:80vh">' + newswireStr + '</textarea>'

    filterStr = ''
    filterFilename = \
        baseDir + '/accounts/news@' + domain + '/filters.txt'
    if os.path.isfile(filterFilename):
        with open(filterFilename, 'r') as filterfile:
            filterStr = filterfile.read()

    editNewswireForm += \
        '      <br><b><label class="labels">' + \
        translate['Filtered words'] + '</label></b>\n'
    editNewswireForm += '      <br><label class="labels">' + \
        translate['One per line'] + '</label>'
    editNewswireForm += '      <textarea id="message" ' + \
        'name="filteredWordsNewswire" style="height:50vh">' + \
        filterStr + '</textarea>\n'

    hashtagRulesStr = ''
    hashtagRulesFilename = \
        baseDir + '/accounts/hashtagrules.txt'
    if os.path.isfile(hashtagRulesFilename):
        with open(hashtagRulesFilename, 'r') as rulesfile:
            hashtagRulesStr = rulesfile.read()

    editNewswireForm += \
        '      <br><b><label class="labels">' + \
        translate['News tagging rules'] + '</label></b>\n'
    editNewswireForm += '      <br><label class="labels">' + \
        translate['One per line'] + '.</label>\n'
    editNewswireForm += \
        '      <a href="' + \
        'https://gitlab.com/bashrc2/epicyon/-/raw/main/hashtagrules.txt' + \
        '">' + translate['See instructions'] + '</a>\n'
    editNewswireForm += '      <textarea id="message" ' + \
        'name="hashtagRulesList" style="height:80vh">' + \
        hashtagRulesStr + '</textarea>\n'

    editNewswireForm += \
        '</div>'

    editNewswireForm += htmlFooter()
    return editNewswireForm


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


def htmlEditProfile(cssCache: {}, translate: {}, baseDir: str, path: str,
                    domain: str, port: int, httpPrefix: str,
                    defaultTimeline: str) -> str:
    """Shows the edit profile screen
    """
    imageFormats = '.png, .jpg, .jpeg, .gif, .webp, .avif'
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '')
    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''
    domainFull = domain
    if port:
        if port != 80 and port != 443:
            if ':' not in domain:
                domainFull = domain + ':' + str(port)

    actorFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    if not os.path.isfile(actorFilename):
        return ''

    # filename of the banner shown at the top
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)

    isBot = ''
    isGroup = ''
    followDMs = ''
    removeTwitter = ''
    notifyLikes = ''
    hideLikeButton = ''
    mediaInstanceStr = ''
    blogsInstanceStr = ''
    newsInstanceStr = ''
    displayNickname = nickname
    bioStr = ''
    donateUrl = ''
    emailAddress = ''
    PGPpubKey = ''
    PGPfingerprint = ''
    xmppAddress = ''
    matrixAddress = ''
    ssbAddress = ''
    blogAddress = ''
    toxAddress = ''
    manuallyApprovesFollowers = ''
    actorJson = loadJson(actorFilename)
    if actorJson:
        donateUrl = getDonationUrl(actorJson)
        xmppAddress = getXmppAddress(actorJson)
        matrixAddress = getMatrixAddress(actorJson)
        ssbAddress = getSSBAddress(actorJson)
        blogAddress = getBlogAddress(actorJson)
        toxAddress = getToxAddress(actorJson)
        emailAddress = getEmailAddress(actorJson)
        PGPpubKey = getPGPpubKey(actorJson)
        PGPfingerprint = getPGPfingerprint(actorJson)
        if actorJson.get('name'):
            displayNickname = actorJson['name']
        if actorJson.get('summary'):
            bioStr = \
                actorJson['summary'].replace('<p>', '').replace('</p>', '')
        if actorJson.get('manuallyApprovesFollowers'):
            if actorJson['manuallyApprovesFollowers']:
                manuallyApprovesFollowers = 'checked'
            else:
                manuallyApprovesFollowers = ''
        if actorJson.get('type'):
            if actorJson['type'] == 'Service':
                isBot = 'checked'
                isGroup = ''
            elif actorJson['type'] == 'Group':
                isGroup = 'checked'
                isBot = ''
    if os.path.isfile(baseDir + '/accounts/' +
                      nickname + '@' + domain + '/.followDMs'):
        followDMs = 'checked'
    if os.path.isfile(baseDir + '/accounts/' +
                      nickname + '@' + domain + '/.removeTwitter'):
        removeTwitter = 'checked'
    if os.path.isfile(baseDir + '/accounts/' +
                      nickname + '@' + domain + '/.notifyLikes'):
        notifyLikes = 'checked'
    if os.path.isfile(baseDir + '/accounts/' +
                      nickname + '@' + domain + '/.hideLikeButton'):
        hideLikeButton = 'checked'

    mediaInstance = getConfigParam(baseDir, "mediaInstance")
    if mediaInstance:
        if mediaInstance is True:
            mediaInstanceStr = 'checked'
            blogsInstanceStr = ''
            newsInstanceStr = ''

    newsInstance = getConfigParam(baseDir, "newsInstance")
    if newsInstance:
        if newsInstance is True:
            newsInstanceStr = 'checked'
            blogsInstanceStr = ''
            mediaInstanceStr = ''

    blogsInstance = getConfigParam(baseDir, "blogsInstance")
    if blogsInstance:
        if blogsInstance is True:
            blogsInstanceStr = 'checked'
            mediaInstanceStr = ''
            newsInstanceStr = ''

    filterStr = ''
    filterFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/filters.txt'
    if os.path.isfile(filterFilename):
        with open(filterFilename, 'r') as filterfile:
            filterStr = filterfile.read()

    switchStr = ''
    switchFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/replacewords.txt'
    if os.path.isfile(switchFilename):
        with open(switchFilename, 'r') as switchfile:
            switchStr = switchfile.read()

    autoTags = ''
    autoTagsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/autotags.txt'
    if os.path.isfile(autoTagsFilename):
        with open(autoTagsFilename, 'r') as autoTagsFile:
            autoTags = autoTagsFile.read()

    autoCW = ''
    autoCWFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/autocw.txt'
    if os.path.isfile(autoCWFilename):
        with open(autoCWFilename, 'r') as autoCWFile:
            autoCW = autoCWFile.read()

    blockedStr = ''
    blockedFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/blocking.txt'
    if os.path.isfile(blockedFilename):
        with open(blockedFilename, 'r') as blockedfile:
            blockedStr = blockedfile.read()

    allowedInstancesStr = ''
    allowedInstancesFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/allowedinstances.txt'
    if os.path.isfile(allowedInstancesFilename):
        with open(allowedInstancesFilename, 'r') as allowedInstancesFile:
            allowedInstancesStr = allowedInstancesFile.read()

    gitProjectsStr = ''
    gitProjectsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/gitprojects.txt'
    if os.path.isfile(gitProjectsFilename):
        with open(gitProjectsFilename, 'r') as gitProjectsFile:
            gitProjectsStr = gitProjectsFile.read()

    skills = getSkills(baseDir, nickname, domain)
    skillsStr = ''
    skillCtr = 1
    if skills:
        for skillDesc, skillValue in skills.items():
            skillsStr += \
                '<p><input type="text" placeholder="' + translate['Skill'] + \
                ' ' + str(skillCtr) + '" name="skillName' + str(skillCtr) + \
                '" value="' + skillDesc + '" style="width:40%">'
            skillsStr += \
                '<input type="range" min="1" max="100" ' + \
                'class="slider" name="skillValue' + \
                str(skillCtr) + '" value="' + str(skillValue) + '"></p>'
            skillCtr += 1

    skillsStr += \
        '<p><input type="text" placeholder="Skill ' + str(skillCtr) + \
        '" name="skillName' + str(skillCtr) + \
        '" value="" style="width:40%">'
    skillsStr += \
        '<input type="range" min="1" max="100" ' + \
        'class="slider" name="skillValue' + \
        str(skillCtr) + '" value="50"></p>'

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    editProfileCSS = getCSS(baseDir, cssFilename, cssCache)
    if editProfileCSS:
        if httpPrefix != 'https':
            editProfileCSS = \
                editProfileCSS.replace('https://', httpPrefix + '://')

    moderatorsStr = ''
    themesDropdown = ''
    instanceStr = ''

    adminNickname = getConfigParam(baseDir, 'admin')
    if adminNickname:
        if path.startswith('/users/' + adminNickname + '/'):
            instanceDescription = \
                getConfigParam(baseDir, 'instanceDescription')
            instanceDescriptionShort = \
                getConfigParam(baseDir, 'instanceDescriptionShort')
            instanceTitle = \
                getConfigParam(baseDir, 'instanceTitle')
            instanceStr += '<div class="container">'
            instanceStr += \
                '  <label class="labels">' + \
                translate['Instance Title'] + '</label>'
            if instanceTitle:
                instanceStr += \
                    '  <input type="text" name="instanceTitle" value="' + \
                    instanceTitle + '"><br>'
            else:
                instanceStr += \
                    '  <input type="text" name="instanceTitle" value=""><br>'
            instanceStr += \
                '  <label class="labels">' + \
                translate['Instance Short Description'] + '</label>'
            if instanceDescriptionShort:
                instanceStr += \
                    '  <input type="text" ' + \
                    'name="instanceDescriptionShort" value="' + \
                    instanceDescriptionShort + '"><br>'
            else:
                instanceStr += \
                    '  <input type="text" ' + \
                    'name="instanceDescriptionShort" value=""><br>'
            instanceStr += \
                '  <label class="labels">' + \
                translate['Instance Description'] + '</label>'
            if instanceDescription:
                instanceStr += \
                    '  <textarea id="message" name="instanceDescription" ' + \
                    'style="height:200px">' + \
                    instanceDescription + '</textarea>'
            else:
                instanceStr += \
                    '  <textarea id="message" name="instanceDescription" ' + \
                    'style="height:200px"></textarea>'
            instanceStr += \
                '  <label class="labels">' + \
                translate['Instance Logo'] + '</label>'
            instanceStr += \
                '  <input type="file" id="instanceLogo" name="instanceLogo"'
            instanceStr += '      accept="' + imageFormats + '">'
            instanceStr += '</div>'

            moderators = ''
            moderatorsFile = baseDir + '/accounts/moderators.txt'
            if os.path.isfile(moderatorsFile):
                with open(moderatorsFile, "r") as f:
                    moderators = f.read()
            moderatorsStr = '<div class="container">'
            moderatorsStr += '  <b>' + translate['Moderators'] + '</b><br>'
            moderatorsStr += '  ' + \
                translate['A list of moderator nicknames. One per line.']
            moderatorsStr += \
                '  <textarea id="message" name="moderators" placeholder="' + \
                translate['List of moderator nicknames'] + \
                '..." style="height:200px">' + moderators + '</textarea>'
            moderatorsStr += '</div>'

            editors = ''
            editorsFile = baseDir + '/accounts/editors.txt'
            if os.path.isfile(editorsFile):
                with open(editorsFile, "r") as f:
                    editors = f.read()
            editorsStr = '<div class="container">'
            editorsStr += '  <b>' + translate['Site Editors'] + '</b><br>'
            editorsStr += '  ' + \
                translate['A list of editor nicknames. One per line.']
            editorsStr += \
                '  <textarea id="message" name="editors" placeholder="" ' + \
                'style="height:200px">' + editors + '</textarea>'
            editorsStr += '</div>'

            themes = getThemesList()
            themesDropdown = '<div class="container">'
            themesDropdown += '  <b>' + translate['Theme'] + '</b><br>'
            grayscaleFilename = \
                baseDir + '/accounts/.grayscale'
            grayscale = ''
            if os.path.isfile(grayscaleFilename):
                grayscale = 'checked'
            themesDropdown += \
                '      <input type="checkbox" class="profilecheckbox" ' + \
                'name="grayscale" ' + grayscale + \
                '> ' + translate['Grayscale'] + '<br>'
            themesDropdown += '  <select id="themeDropdown" ' + \
                'name="themeDropdown" class="theme">'
            for themeName in themes:
                themesDropdown += '    <option value="' + \
                    themeName.lower() + '">' + \
                    translate[themeName] + '</option>'
            themesDropdown += '  </select><br>'
            if os.path.isfile(baseDir + '/fonts/custom.woff') or \
               os.path.isfile(baseDir + '/fonts/custom.woff2') or \
               os.path.isfile(baseDir + '/fonts/custom.otf') or \
               os.path.isfile(baseDir + '/fonts/custom.ttf'):
                themesDropdown += \
                    '      <input type="checkbox" class="profilecheckbox" ' + \
                    'name="removeCustomFont"> ' + \
                    translate['Remove the custom font'] + '<br>'
            themesDropdown += '</div>'
            themeName = getConfigParam(baseDir, 'theme')
            themesDropdown = \
                themesDropdown.replace('<option value="' + themeName + '">',
                                       '<option value="' + themeName +
                                       '" selected>')

    editProfileForm = htmlHeader(cssFilename, editProfileCSS)

    # top banner
    editProfileForm += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '">\n'
    editProfileForm += '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    editProfileForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + path + '/profiledata">\n'
    editProfileForm += '  <div class="vertical-center">\n'
    editProfileForm += \
        '    <p class="new-post-text">' + translate['Profile for'] + \
        ' ' + nickname + '@' + domainFull + '</p>'
    editProfileForm += '    <div class="container">\n'
    # editProfileForm += \
    #     '      <a href="' + pathOriginal + '"><button class="cancelbtn">' + \
    #     translate['Go Back'] + '</button></a>\n'
    editProfileForm += \
        '      <center>\n' + \
        '        <input type="submit" name="submitProfile" value="' + \
        translate['Submit'] + '">\n' + \
        '      </center>\n'
    editProfileForm += '    </div>\n'

    if scheduledPostsExist(baseDir, nickname, domain):
        editProfileForm += '    <div class="container">\n'
        editProfileForm += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="removeScheduledPosts"> ' + \
            translate['Remove scheduled posts'] + '<br>\n'
        editProfileForm += '    </div>\n'

    editProfileForm += '    <div class="container">\n'
    editProfileForm += '      <label class="labels">' + \
        translate['Nickname'] + '</label>\n'
    editProfileForm += \
        '      <input type="text" name="displayNickname" value="' + \
        displayNickname + '"><br>\n'
    editProfileForm += \
        '      <label class="labels">' + translate['Your bio'] + '</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="bio" style="height:200px">' + \
        bioStr + '</textarea>\n'
    editProfileForm += '<label class="labels">' + \
        translate['Donations link'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" placeholder="https://..." ' + \
        'name="donateUrl" value="' + donateUrl + '">\n'
    editProfileForm += \
        '<label class="labels">' + translate['XMPP'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="xmppAddress" value="' + \
        xmppAddress + '">\n'
    editProfileForm += '<label class="labels">' + \
        translate['Matrix'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="matrixAddress" value="' + \
        matrixAddress+'">\n'

    editProfileForm += '<label class="labels">SSB</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="ssbAddress" value="' + \
        ssbAddress + '">\n'

    editProfileForm += '<label class="labels">Blog</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="blogAddress" value="' + \
        blogAddress + '">\n'

    editProfileForm += '<label class="labels">Tox</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="toxAddress" value="' + \
        toxAddress + '">\n'
    editProfileForm += '<label class="labels">' + \
        translate['Email'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="email" value="' + emailAddress + '">\n'
    editProfileForm += \
        '<label class="labels">' + \
        translate['PGP Fingerprint'] + '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="openpgp" value="' + \
        PGPfingerprint + '">\n'
    editProfileForm += \
        '<label class="labels">' + translate['PGP'] + '</label><br>\n'
    editProfileForm += \
        '      <textarea id="message" placeholder=' + \
        '"-----BEGIN PGP PUBLIC KEY BLOCK-----" name="pgp" ' + \
        'style="height:100px">' + PGPpubKey + '</textarea>\n'
    editProfileForm += '<a href="/users/' + nickname + \
        '/followingaccounts"><label class="labels">' + \
        translate['Following'] + '</label></a><br>\n'
    editProfileForm += '    </div>\n'
    editProfileForm += '    <div class="container">\n'
    idx = 'The files attached below should be no larger than ' + \
        '10MB in total uploaded at once.'
    editProfileForm += \
        '      <label class="labels">' + translate[idx] + '</label><br><br>\n'
    editProfileForm += \
        '      <label class="labels">' + translate['Avatar image'] + \
        '</label>\n'
    editProfileForm += \
        '      <input type="file" id="avatar" name="avatar"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += \
        '      <br><label class="labels">' + \
        translate['Background image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="image" name="image"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '      <br><label class="labels">' + \
        translate['Timeline banner image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="banner" name="banner"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '      <br><label class="labels">' + \
        translate['Search banner image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="search_banner" '
    editProfileForm += 'name="search_banner"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '      <br><label class="labels">' + \
        translate['Left column image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="left_col_image" '
    editProfileForm += 'name="left_col_image"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '      <br><label class="labels">' + \
        translate['Right column image'] + '</label>\n'
    editProfileForm += '      <input type="file" id="right_col_image" '
    editProfileForm += 'name="right_col_image"'
    editProfileForm += '            accept="' + imageFormats + '">\n'

    editProfileForm += '    </div>\n'
    editProfileForm += '    <div class="container">\n'
    editProfileForm += \
        '<label class="labels">' + translate['Change Password'] + \
        '</label><br>\n'
    editProfileForm += '      <input type="text" name="password" ' + \
        'value=""><br>\n'
    editProfileForm += \
        '<label class="labels">' + translate['Confirm Password'] + \
        '</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="passwordconfirm" value="">\n'
    editProfileForm += '    </div>\n'

    if path.startswith('/users/' + adminNickname + '/'):
        editProfileForm += '    <div class="container">\n'
        editProfileForm += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="mediaInstance" ' + mediaInstanceStr + '> ' + \
            translate['This is a media instance'] + '<br>\n'
        editProfileForm += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="blogsInstance" ' + blogsInstanceStr + '> ' + \
            translate['This is a blogging instance'] + '<br>\n'
        editProfileForm += \
            '      <input type="checkbox" class="profilecheckbox" ' + \
            'name="newsInstance" ' + newsInstanceStr + '> ' + \
            translate['This is a news instance'] + '<br>\n'
        editProfileForm += '    </div>\n'

    editProfileForm += '    <div class="container">\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="approveFollowers" ' + manuallyApprovesFollowers + \
        '> ' + translate['Approve follower requests'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" ' + \
        'class="profilecheckbox" name="isBot" ' + \
        isBot + '> ' + translate['This is a bot account'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" ' + \
        'class="profilecheckbox" name="isGroup" ' + isGroup + '> ' + \
        translate['This is a group account'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="followDMs" ' + followDMs + '> ' + \
        translate['Only people I follow can send me DMs'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="removeTwitter" ' + removeTwitter + '> ' + \
        translate['Remove Twitter posts'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="notifyLikes" ' + notifyLikes + '> ' + \
        translate['Notify when posts are liked'] + '<br>\n'
    editProfileForm += \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="hideLikeButton" ' + hideLikeButton + '> ' + \
        translate["Don't show the Like button"] + '<br>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Filtered words'] + '</label></b>\n'
    editProfileForm += '      <br><label class="labels">' + \
        translate['One per line'] + '</label>\n'
    editProfileForm += '      <textarea id="message" ' + \
        'name="filteredWords" style="height:200px">' + \
        filterStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Word Replacements'] + '</label></b>\n'
    editProfileForm += '      <br><label class="labels">A -> B</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="switchWords" ' + \
        'style="height:200px">' + switchStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Autogenerated Hashtags'] + '</label></b>\n'
    editProfileForm += '      <br><label class="labels">A -> #B</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="autoTags" ' + \
        'style="height:200px">' + autoTags + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Autogenerated Content Warnings'] + '</label></b>\n'
    editProfileForm += '      <br><label class="labels">A -> B</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="autoCW" ' + \
        'style="height:200px">' + autoCW + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Blocked accounts'] + '</label></b>\n'
    idx = 'Blocked accounts, one per line, in the form ' + \
        'nickname@domain or *@blockeddomain'
    editProfileForm += \
        '      <br><label class="labels">' + translate[idx] + '</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="blocked" style="height:200px">' + \
        blockedStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Federation list'] + '</label></b>\n'
    idx = 'Federate only with a defined set of instances. ' + \
        'One domain name per line.'
    editProfileForm += \
        '      <br><label class="labels">' + \
        translate[idx] + '</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="allowedInstances" ' + \
        'style="height:200px">' + allowedInstancesStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Git Projects'] + '</label></b>\n'
    idx = 'List of project names that you wish to receive git patches for'
    editProfileForm += \
        '      <br><label class="labels">' + \
        translate[idx] + '</label>\n'
    editProfileForm += \
        '      <textarea id="message" name="gitProjects" ' + \
        'style="height:100px">' + gitProjectsStr + '</textarea>\n'

    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['YouTube Replacement Domain'] + '</label></b>\n'
    YTReplacementDomain = getConfigParam(baseDir, "youtubedomain")
    if not YTReplacementDomain:
        YTReplacementDomain = ''
    editProfileForm += \
        '      <input type="text" name="ytdomain" value="' + \
        YTReplacementDomain + '">\n'

    editProfileForm += '    </div>\n'
    editProfileForm += '    <div class="container">\n'
    editProfileForm += \
        '      <b><label class="labels">' + \
        translate['Skills'] + '</label></b><br>\n'
    idx = 'If you want to participate within organizations then you ' + \
        'can indicate some skills that you have and approximate ' + \
        'proficiency levels. This helps organizers to construct ' + \
        'teams with an appropriate combination of skills.'
    editProfileForm += '      <label class="labels">' + \
        translate[idx] + '</label>\n'
    editProfileForm += skillsStr + themesDropdown
    editProfileForm += moderatorsStr + editorsStr
    editProfileForm += '    </div>\n' + instanceStr
    editProfileForm += '    <div class="container">\n'
    editProfileForm += '      <b><label class="labels">' + \
        translate['Danger Zone'] + '</label></b><br>\n'
    editProfileForm += \
        '      <input type="checkbox" class=dangercheckbox" ' + \
        'name="deactivateThisAccount"> ' + \
        translate['Deactivate this account'] + '<br>\n'
    editProfileForm += '    </div>\n'
    editProfileForm += '  </div>\n'
    editProfileForm += '</form>\n'
    editProfileForm += htmlFooter()
    return editProfileForm


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


def htmlProfilePosts(recentPostsCache: {}, maxRecentPosts: int,
                     translate: {},
                     baseDir: str, httpPrefix: str,
                     authorized: bool,
                     nickname: str, domain: str, port: int,
                     session, wfRequest: {}, personCache: {},
                     projectVersion: str,
                     YTReplacementDomain: str,
                     showPublishedDateOnly: bool) -> str:
    """Shows posts on the profile screen
    These should only be public posts
    """
    iconsDir = getIconsDir(baseDir)
    separatorStr = htmlPostSeparator(baseDir, None)
    profileStr = ''
    maxItems = 4
    ctr = 0
    currPage = 1
    while ctr < maxItems and currPage < 4:
        outboxFeed = \
            personBoxJson({}, session, baseDir, domain,
                          port,
                          '/users/' + nickname + '/outbox?page=' +
                          str(currPage),
                          httpPrefix,
                          10, 'outbox',
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
                                         iconsDir, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
                                         False, False, False, True, False)
                if postStr:
                    profileStr += separatorStr + postStr
                    ctr += 1
                    if ctr >= maxItems:
                        break
        currPage += 1
    return profileStr


def htmlProfileFollowing(translate: {}, baseDir: str, httpPrefix: str,
                         authorized: bool,
                         nickname: str, domain: str, port: int,
                         session, wfRequest: {}, personCache: {},
                         followingJson: {}, projectVersion: str,
                         buttons: [],
                         feedName: str, actor: str,
                         pageNumber: int,
                         maxItemsPerPage: int) -> str:
    """Shows following on the profile screen
    """
    profileStr = ''

    iconsDir = getIconsDir(baseDir)
    if authorized and pageNumber:
        if authorized and pageNumber > 1:
            # page up arrow
            profileStr += \
                '  <center>\n' + \
                '    <a href="' + actor + '/' + feedName + \
                '?page=' + str(pageNumber - 1) + \
                '"><img loading="lazy" class="pageicon" src="/' + \
                iconsDir + '/pageup.png" title="' + \
                translate['Page up'] + '" alt="' + \
                translate['Page up'] + '"></a>\n' + \
                '  </center>\n'

    for item in followingJson['orderedItems']:
        profileStr += \
            individualFollowAsHtml(translate, baseDir, session,
                                   wfRequest, personCache,
                                   domain, item, authorized, nickname,
                                   httpPrefix, projectVersion,
                                   buttons)
    if authorized and maxItemsPerPage and pageNumber:
        if len(followingJson['orderedItems']) >= maxItemsPerPage:
            # page down arrow
            profileStr += \
                '  <center>\n' + \
                '    <a href="' + actor + '/' + feedName + \
                '?page=' + str(pageNumber + 1) + \
                '"><img loading="lazy" class="pageicon" src="/' + \
                iconsDir + '/pagedown.png" title="' + \
                translate['Page down'] + '" alt="' + \
                translate['Page down'] + '"></a>\n' + \
                '  </center>\n'
    return profileStr


def htmlProfileRoles(translate: {}, nickname: str, domain: str,
                     rolesJson: {}) -> str:
    """Shows roles on the profile screen
    """
    profileStr = ''
    for project, rolesList in rolesJson.items():
        profileStr += \
            '<div class="roles">\n<h2>' + project + \
            '</h2>\n<div class="roles-inner">\n'
        for role in rolesList:
            profileStr += '<h3>' + role + '</h3>\n'
        profileStr += '</div></div>\n'
    if len(profileStr) == 0:
        profileStr += \
            '<p>@' + nickname + '@' + domain + ' has no roles assigned</p>\n'
    else:
        profileStr = '<div>' + profileStr + '</div>\n'
    return profileStr


def htmlProfileSkills(translate: {}, nickname: str, domain: str,
                      skillsJson: {}) -> str:
    """Shows skills on the profile screen
    """
    profileStr = ''
    for skill, level in skillsJson.items():
        profileStr += \
            '<div>' + skill + \
            '<br><div id="myProgress"><div id="myBar" style="width:' + \
            str(level) + '%"></div></div></div>\n<br>\n'
    if len(profileStr) > 0:
        profileStr = '<center><div class="skill-title">' + \
            profileStr + '</div></center>\n'
    return profileStr


def htmlIndividualShare(actor: str, item: {}, translate: {},
                        showContact: bool, removeButton: bool) -> str:
    """Returns an individual shared item as html
    """
    profileStr = '<div class="container">\n'
    profileStr += '<p class="share-title">' + item['displayName'] + '</p>\n'
    if item.get('imageUrl'):
        profileStr += '<a href="' + item['imageUrl'] + '">\n'
        profileStr += \
            '<img loading="lazy" src="' + item['imageUrl'] + \
            '" alt="' + translate['Item image'] + '">\n</a>\n'
    profileStr += '<p>' + item['summary'] + '</p>\n'
    profileStr += \
        '<p><b>' + translate['Type'] + ':</b> ' + item['itemType'] + ' '
    profileStr += \
        '<b>' + translate['Category'] + ':</b> ' + item['category'] + ' '
    profileStr += \
        '<b>' + translate['Location'] + ':</b> ' + item['location'] + '</p>\n'
    if showContact:
        contactActor = item['actor']
        profileStr += \
            '<p><a href="' + actor + \
            '?replydm=sharedesc:' + item['displayName'] + \
            '?mention=' + contactActor + '"><button class="button">' + \
            translate['Contact'] + '</button></a>\n'
    if removeButton:
        profileStr += \
            ' <a href="' + actor + '?rmshare=' + item['displayName'] + \
            '"><button class="button">' + \
            translate['Remove'] + '</button></a>\n'
    profileStr += '</div>\n'
    return profileStr


def htmlProfileShares(actor: str, translate: {},
                      nickname: str, domain: str, sharesJson: {}) -> str:
    """Shows shares on the profile screen
    """
    profileStr = ''
    for item in sharesJson['orderedItems']:
        profileStr += htmlIndividualShare(actor, item, translate, False, False)
    if len(profileStr) > 0:
        profileStr = '<div class="share-title">' + profileStr + '</div>\n'
    return profileStr


def htmlSharesTimeline(translate: {}, pageNumber: int, itemsPerPage: int,
                       baseDir: str, actor: str,
                       nickname: str, domain: str, port: int,
                       maxSharesPerAccount: int, httpPrefix: str) -> str:
    """Show shared items timeline as html
    """
    sharesJson, lastPage = \
        sharesTimelineJson(actor, pageNumber, itemsPerPage,
                           baseDir, maxSharesPerAccount)
    domainFull = domain
    if port != 80 and port != 443:
        if ':' not in domain:
            domainFull = domain + ':' + str(port)
    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    timelineStr = ''

    if pageNumber > 1:
        iconsDir = getIconsDir(baseDir)
        timelineStr += \
            '  <center>\n' + \
            '    <a href="' + actor + '/tlshares?page=' + \
            str(pageNumber - 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pageup.png" title="' + translate['Page up'] + \
            '" alt="' + translate['Page up'] + '"></a>\n' + \
            '  </center>\n'

    separatorStr = htmlPostSeparator(baseDir, None)
    for published, item in sharesJson.items():
        showContactButton = False
        if item['actor'] != actor:
            showContactButton = True
        showRemoveButton = False
        if item['actor'] == actor:
            showRemoveButton = True
        timelineStr += separatorStr + \
            htmlIndividualShare(actor, item, translate,
                                showContactButton, showRemoveButton)

    if not lastPage:
        iconsDir = getIconsDir(baseDir)
        timelineStr += \
            '  <center>\n' + \
            '    <a href="' + actor + '/tlshares?page=' + \
            str(pageNumber + 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pagedown.png" title="' + translate['Page down'] + \
            '" alt="' + translate['Page down'] + '"></a>\n' + \
            '  </center>\n'

    return timelineStr


def htmlProfile(rssIconAtTop: bool,
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
    """Show the profile page as html
    """
    nickname = profileJson['preferredUsername']
    if not nickname:
        return ""
    domain, port = getDomainFromActor(profileJson['id'])
    if not domain:
        return ""
    displayName = \
        addEmojiToDisplayName(baseDir, httpPrefix,
                              nickname, domain,
                              profileJson['name'], True)
    domainFull = domain
    if port:
        domainFull = domain + ':' + str(port)
    profileDescription = \
        addEmojiToDisplayName(baseDir, httpPrefix,
                              nickname, domain,
                              profileJson['summary'], False)
    postsButton = 'button'
    followingButton = 'button'
    followersButton = 'button'
    rolesButton = 'button'
    skillsButton = 'button'
    sharesButton = 'button'
    if selected == 'posts':
        postsButton = 'buttonselected'
    elif selected == 'following':
        followingButton = 'buttonselected'
    elif selected == 'followers':
        followersButton = 'buttonselected'
    elif selected == 'roles':
        rolesButton = 'buttonselected'
    elif selected == 'skills':
        skillsButton = 'buttonselected'
    elif selected == 'shares':
        sharesButton = 'buttonselected'
    loginButton = ''

    followApprovalsSection = ''
    followApprovals = False
    linkToTimelineStart = ''
    linkToTimelineEnd = ''
    editProfileStr = ''
    logoutStr = ''
    actor = profileJson['id']
    usersPath = '/users/' + actor.split('/users/')[1]

    donateSection = ''
    donateUrl = getDonationUrl(profileJson)
    PGPpubKey = getPGPpubKey(profileJson)
    PGPfingerprint = getPGPfingerprint(profileJson)
    emailAddress = getEmailAddress(profileJson)
    xmppAddress = getXmppAddress(profileJson)
    matrixAddress = getMatrixAddress(profileJson)
    ssbAddress = getSSBAddress(profileJson)
    toxAddress = getToxAddress(profileJson)
    if donateUrl or xmppAddress or matrixAddress or \
       ssbAddress or toxAddress or PGPpubKey or \
       PGPfingerprint or emailAddress:
        donateSection = '<div class="container">\n'
        donateSection += '  <center>\n'
        if donateUrl and not isSystemAccount(nickname):
            donateSection += \
                '    <p><a href="' + donateUrl + \
                '"><button class="donateButton">' + translate['Donate'] + \
                '</button></a></p>\n'
        if emailAddress:
            donateSection += \
                '<p>' + translate['Email'] + ': <a href="mailto:' + \
                emailAddress + '">' + emailAddress + '</a></p>\n'
        if xmppAddress:
            donateSection += \
                '<p>' + translate['XMPP'] + ': <a href="xmpp:' + \
                xmppAddress + '">'+xmppAddress + '</a></p>\n'
        if matrixAddress:
            donateSection += \
                '<p>' + translate['Matrix'] + ': ' + matrixAddress + '</p>\n'
        if ssbAddress:
            donateSection += \
                '<p>SSB: <label class="ssbaddr">' + \
                ssbAddress + '</label></p>\n'
        if toxAddress:
            donateSection += \
                '<p>Tox: <label class="toxaddr">' + \
                toxAddress + '</label></p>\n'
        if PGPfingerprint:
            donateSection += \
                '<p class="pgp">PGP: ' + \
                PGPfingerprint.replace('\n', '<br>') + '</p>\n'
        if PGPpubKey:
            donateSection += \
                '<p class="pgp">' + PGPpubKey.replace('\n', '<br>') + '</p>\n'
        donateSection += '  </center>\n'
        donateSection += '</div>\n'

    iconsDir = getIconsDir(baseDir)
    if not authorized:
        loginButton = headerButtonsFrontScreen(translate, nickname,
                                               'features', authorized,
                                               iconsAsButtons, iconsDir)
    else:
        editProfileStr = \
            '<a class="imageAnchor" href="' + usersPath + '/editprofile">' + \
            '<img loading="lazy" src="/' + iconsDir + \
            '/edit.png" title="' + translate['Edit'] + \
            '" alt="| ' + translate['Edit'] + '" class="timelineicon"/></a>\n'

        logoutStr = \
            '<a class="imageAnchor" href="/logout">' + \
            '<img loading="lazy" src="/' + iconsDir + \
            '/logout.png" title="' + translate['Logout'] + \
            '" alt="| ' + translate['Logout'] + \
            '" class="timelineicon"/></a>\n'

        linkToTimelineStart = \
            '<a href="/users/' + nickname + '/' + defaultTimeline + \
            '"><label class="transparent">' + \
            translate['Switch to timeline view'] + '</label></a>'
        linkToTimelineStart += \
            '<a href="/users/' + nickname + '/' + defaultTimeline + \
            '" title="' + translate['Switch to timeline view'] + \
            '" alt="' + translate['Switch to timeline view'] + '">'
        linkToTimelineEnd = '</a>'
        # are there any follow requests?
        followRequestsFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/followrequests.txt'
        if os.path.isfile(followRequestsFilename):
            with open(followRequestsFilename, 'r') as f:
                for line in f:
                    if len(line) > 0:
                        followApprovals = True
                        followersButton = 'buttonhighlighted'
                        if selected == 'followers':
                            followersButton = 'buttonselectedhighlighted'
                        break
        if selected == 'followers':
            if followApprovals:
                with open(followRequestsFilename, 'r') as f:
                    for followerHandle in f:
                        if len(line) > 0:
                            if '://' in followerHandle:
                                followerActor = followerHandle
                            else:
                                followerActor = \
                                    httpPrefix + '://' + \
                                    followerHandle.split('@')[1] + \
                                    '/users/' + followerHandle.split('@')[0]
                            basePath = '/users/' + nickname
                            followApprovalsSection += '<div class="container">'
                            followApprovalsSection += \
                                '<a href="' + followerActor + '">'
                            followApprovalsSection += \
                                '<span class="followRequestHandle">' + \
                                followerHandle + '</span></a>'
                            followApprovalsSection += \
                                '<a href="' + basePath + \
                                '/followapprove=' + followerHandle + '">'
                            followApprovalsSection += \
                                '<button class="followApprove">' + \
                                translate['Approve'] + '</button></a><br><br>'
                            followApprovalsSection += \
                                '<a href="' + basePath + \
                                '/followdeny=' + followerHandle + '">'
                            followApprovalsSection += \
                                '<button class="followDeny">' + \
                                translate['Deny'] + '</button></a>'
                            followApprovalsSection += '</div>'

    profileDescriptionShort = profileDescription
    if '\n' in profileDescription:
        if len(profileDescription.split('\n')) > 2:
            profileDescriptionShort = ''
    else:
        if '<br>' in profileDescription:
            if len(profileDescription.split('<br>')) > 2:
                profileDescriptionShort = ''
                profileDescription = profileDescription.replace('<br>', '\n')
    # keep the profile description short
    if len(profileDescriptionShort) > 256:
        profileDescriptionShort = ''
    # remove formatting from profile description used on title
    avatarDescription = ''
    if profileJson.get('summary'):
        avatarDescription = profileJson['summary'].replace('<br>', '\n')
        avatarDescription = avatarDescription.replace('<p>', '')
        avatarDescription = avatarDescription.replace('</p>', '')

    # If this is the news account then show a different banner
    if isSystemAccount(nickname):
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
        iconsDir = getIconsDir(baseDir)
        profileHeaderStr += \
            getLeftColumnContent(baseDir, 'news', domainFull,
                                 httpPrefix, translate,
                                 iconsDir, False,
                                 False, None, rssIconAtTop, True,
                                 True)
        profileHeaderStr += '      </td>\n'
        profileHeaderStr += '      <td valign="top" class="col-center">\n'
    else:
        profileHeaderStr = '<div class="hero-image">\n'
        profileHeaderStr += '  <div class="hero-text">\n'
        profileHeaderStr += \
            '    <img loading="lazy" src="' + profileJson['icon']['url'] + \
            '" title="' + avatarDescription + '" alt="' + \
            avatarDescription + '" class="title">\n'
        profileHeaderStr += '    <h1>' + displayName + '</h1>\n'
        iconsDir = getIconsDir(baseDir)
        profileHeaderStr += \
            '<p><b>@' + nickname + '@' + domainFull + '</b><br>'
        profileHeaderStr += \
            '<a href="/users/' + nickname + \
            '/qrcode.png" alt="' + translate['QR Code'] + '" title="' + \
            translate['QR Code'] + '">' + \
            '<img class="qrcode" src="/' + iconsDir + \
            '/qrcode.png" /></a></p>\n'
        profileHeaderStr += '    <p>' + profileDescriptionShort + '</p>\n'
        profileHeaderStr += loginButton
        profileHeaderStr += '  </div>\n'
        profileHeaderStr += '</div>\n'

    profileStr = \
        linkToTimelineStart + profileHeaderStr + \
        linkToTimelineEnd + donateSection
    if not isSystemAccount(nickname):
        profileStr += '<div class="container" id="buttonheader">\n'
        profileStr += '  <center>'
        profileStr += \
            '    <a href="' + usersPath + '#buttonheader"><button class="' + \
            postsButton + '"><span>' + translate['Posts'] + \
            ' </span></button></a>'
        profileStr += \
            '    <a href="' + usersPath + '/following#buttonheader">' + \
            '<button class="' + followingButton + '"><span>' + \
            translate['Following'] + ' </span></button></a>'
        profileStr += \
            '    <a href="' + usersPath + '/followers#buttonheader">' + \
            '<button class="' + followersButton + \
            '"><span>' + translate['Followers'] + ' </span></button></a>'
        profileStr += \
            '    <a href="' + usersPath + '/roles#buttonheader">' + \
            '<button class="' + rolesButton + '"><span>' + \
            translate['Roles'] + \
            ' </span></button></a>'
        profileStr += \
            '    <a href="' + usersPath + '/skills#buttonheader">' + \
            '<button class="' + skillsButton + '"><span>' + \
            translate['Skills'] + ' </span></button></a>'
        profileStr += \
            '    <a href="' + usersPath + '/shares#buttonheader">' + \
            '<button class="' + sharesButton + '"><span>' + \
            translate['Shares'] + ' </span></button></a>'
        profileStr += logoutStr + editProfileStr
        profileStr += '  </center>'
        profileStr += '</div>'

    profileStr += followApprovalsSection

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if profileStyle:
        profileStyle = \
            profileStyle.replace('image.png',
                                 profileJson['image']['url'])
        if isSystemAccount(nickname):
            bannerFile, bannerFilename = \
                getBannerFile(baseDir, nickname, domain)
            profileStyle = \
                profileStyle.replace('banner.png',
                                     '/users/' + nickname + '/' + bannerFile)

        licenseStr = \
            '<a href="https://gitlab.com/bashrc2/epicyon">' + \
            '<img loading="lazy" class="license" alt="' + \
            translate['Get the source code'] + '" title="' + \
            translate['Get the source code'] + '" src="/icons/agpl.png" /></a>'

        if selected == 'posts':
            profileStr += \
                htmlProfilePosts(recentPostsCache, maxRecentPosts,
                                 translate,
                                 baseDir, httpPrefix, authorized,
                                 nickname, domain, port,
                                 session, wfRequest, personCache,
                                 projectVersion,
                                 YTReplacementDomain,
                                 showPublishedDateOnly) + licenseStr
        if selected == 'following':
            profileStr += \
                htmlProfileFollowing(translate, baseDir, httpPrefix,
                                     authorized, nickname,
                                     domain, port, session,
                                     wfRequest, personCache, extraJson,
                                     projectVersion, ["unfollow"], selected,
                                     usersPath, pageNumber, maxItemsPerPage)
        if selected == 'followers':
            profileStr += \
                htmlProfileFollowing(translate, baseDir, httpPrefix,
                                     authorized, nickname,
                                     domain, port, session,
                                     wfRequest, personCache, extraJson,
                                     projectVersion, ["block"],
                                     selected, usersPath, pageNumber,
                                     maxItemsPerPage)
        if selected == 'roles':
            profileStr += \
                htmlProfileRoles(translate, nickname, domainFull, extraJson)
        if selected == 'skills':
            profileStr += \
                htmlProfileSkills(translate, nickname, domainFull, extraJson)
        if selected == 'shares':
            profileStr += \
                htmlProfileShares(actor, translate,
                                  nickname, domainFull,
                                  extraJson) + licenseStr

        # Footer which is only used for system accounts
        profileFooterStr = ''
        if isSystemAccount(nickname):
            profileFooterStr = '      </td>\n'
            profileFooterStr += '      <td valign="top" class="col-right">\n'
            iconsDir = getIconsDir(baseDir)
            profileFooterStr += \
                getRightColumnContent(baseDir, 'news', domainFull,
                                      httpPrefix, translate,
                                      iconsDir, False, False,
                                      newswire, False,
                                      False, None, False, False,
                                      False, True, authorized, True)
            profileFooterStr += '      </td>\n'
            profileFooterStr += '  </tr>\n'
            profileFooterStr += '  </tbody>\n'
            profileFooterStr += '</table>\n'

        profileStr = \
            htmlHeader(cssFilename, profileStyle) + \
            profileStr + profileFooterStr + htmlFooter()
    return profileStr


def individualFollowAsHtml(translate: {},
                           baseDir: str, session, wfRequest: {},
                           personCache: {}, domain: str,
                           followUrl: str,
                           authorized: bool,
                           actorNickname: str,
                           httpPrefix: str,
                           projectVersion: str,
                           buttons=[]) -> str:
    """An individual follow entry on the profile screen
    """
    nickname = getNicknameFromActor(followUrl)
    domain, port = getDomainFromActor(followUrl)
    titleStr = '@' + nickname + '@' + domain
    avatarUrl = getPersonAvatarUrl(baseDir, followUrl, personCache, True)
    if not avatarUrl:
        avatarUrl = followUrl + '/avatar.png'
    if domain not in followUrl:
        (inboxUrl, pubKeyId, pubKey,
         fromPersonId, sharedInbox,
         avatarUrl2, displayName) = getPersonBox(baseDir, session, wfRequest,
                                                 personCache, projectVersion,
                                                 httpPrefix, nickname,
                                                 domain, 'outbox')
        if avatarUrl2:
            avatarUrl = avatarUrl2
        if displayName:
            titleStr = displayName + ' ' + titleStr

    buttonsStr = ''
    if authorized:
        for b in buttons:
            if b == 'block':
                buttonsStr += \
                    '<a href="/users/' + actorNickname + \
                    '?options=' + followUrl + \
                    ';1;' + avatarUrl + '"><button class="buttonunfollow">' + \
                    translate['Block'] + '</button></a>\n'
            if b == 'unfollow':
                buttonsStr += \
                    '<a href="/users/' + actorNickname + \
                    '?options=' + followUrl + \
                    ';1;' + avatarUrl + '"><button class="buttonunfollow">' + \
                    translate['Unfollow'] + '</button></a>\n'

    resultStr = '<div class="container">\n'
    resultStr += \
        '<a href="/users/' + actorNickname + '?options=' + \
        followUrl + ';1;' + avatarUrl + '">\n'
    resultStr += '<p><img loading="lazy" src="' + avatarUrl + '" alt=" ">'
    resultStr += titleStr + '</a>' + buttonsStr + '</p>\n'
    resultStr += '</div>\n'
    return resultStr


def htmlHighlightLabel(label: str, highlight: bool) -> str:
    """If the give text should be highlighted then return
    the appropriate markup.
    This is so that in shell browsers, like lynx, it's possible
    to see if the replies or DM button are highlighted.
    """
    if not highlight:
        return label
    return '*' + str(label) + '*'


def getLeftColumnContent(baseDir: str, nickname: str, domainFull: str,
                         httpPrefix: str, translate: {},
                         iconsDir: str, editor: bool,
                         showBackButton: bool, timelinePath: str,
                         rssIconAtTop: bool, showHeaderImage: bool,
                         frontPage: bool) -> str:
    """Returns html content for the left column
    """
    htmlStr = ''

    separatorStr = htmlPostSeparator(baseDir, 'left')
    domain = domainFull
    if ':' in domain:
        domain = domain.split(':')

    editImageClass = ''
    if showHeaderImage:
        leftImageFile, leftColumnImageFilename = \
            getLeftImageFile(baseDir, nickname, domain)
        if not os.path.isfile(leftColumnImageFilename):
            theme = getConfigParam(baseDir, 'theme').lower()
            if theme == 'default':
                theme = ''
            else:
                theme = '_' + theme
            themeLeftImageFile, themeLeftColumnImageFilename = \
                getImageFile(baseDir, 'left_col_image', baseDir + '/img',
                             nickname, domain)
            if os.path.isfile(themeLeftColumnImageFilename):
                leftColumnImageFilename = \
                    baseDir + '/accounts/' + \
                    nickname + '@' + domain + '/' + themeLeftImageFile
                copyfile(themeLeftColumnImageFilename,
                         leftColumnImageFilename)
                leftImageFile = themeLeftImageFile

        # show the image at the top of the column
        editImageClass = 'leftColEdit'
        if os.path.isfile(leftColumnImageFilename):
            editImageClass = 'leftColEditImage'
            htmlStr += \
                '\n      <center>\n' + \
                '        <img class="leftColImg" ' + \
                'loading="lazy" src="/users/' + \
                nickname + '/' + leftImageFile + '" />\n' + \
                '      </center>\n'

    if showBackButton:
        htmlStr += \
            '      <div>' + \
            '      <a href="' + timelinePath + '">' + \
            '<button class="cancelbtn">' + \
            translate['Go Back'] + '</button></a>\n'

    if (editor or rssIconAtTop) and not showHeaderImage:
        htmlStr += '<div class="columnIcons">'

    if editImageClass == 'leftColEdit':
        htmlStr += '\n      <center>\n'

    htmlStr += '      <div class="leftColIcons">\n'
    if editor:
        # show the edit icon
        htmlStr += \
            '      <a href="' + \
            '/users/' + nickname + '/editlinks">' + \
            '<img class="' + editImageClass + \
            '" loading="lazy" alt="' + \
            translate['Edit Links'] + '" title="' + \
            translate['Edit Links'] + '" src="/' + \
            iconsDir + '/edit.png" /></a>\n'

    # RSS icon
    if nickname != 'news':
        # rss feed for this account
        rssUrl = httpPrefix + '://' + domainFull + \
            '/blog/' + nickname + '/rss.xml'
    else:
        # rss feed for all accounts on the instance
        rssUrl = httpPrefix + '://' + domainFull + '/blog/rss.xml'
    if not frontPage:
        rssTitle = translate['RSS feed for your blog']
    else:
        rssTitle = translate['RSS feed for this site']
    rssIconStr = \
        '      <a href="' + rssUrl + '">' + \
        '<img class="' + editImageClass + \
        '" loading="lazy" alt="' + rssTitle + \
        '" title="' + rssTitle + \
        '" src="/' + iconsDir + '/logorss.png" /></a>\n'
    if rssIconAtTop:
        htmlStr += rssIconStr
    htmlStr += '      </div>\n'

    if editImageClass == 'leftColEdit':
        htmlStr += '      </center>\n'

    if (editor or rssIconAtTop) and not showHeaderImage:
        htmlStr += '</div><br>'

    # if showHeaderImage:
    #     htmlStr += '<br>'

    linksFilename = baseDir + '/accounts/links.txt'
    linksFileContainsEntries = False
    if os.path.isfile(linksFilename):
        linksList = None
        with open(linksFilename, "r") as f:
            linksList = f.readlines()
        if linksList:
            for lineStr in linksList:
                if ' ' not in lineStr:
                    if '#' not in lineStr:
                        if '*' not in lineStr:
                            continue
                lineStr = lineStr.strip()
                words = lineStr.split(' ')
                # get the link
                linkStr = None
                for word in words:
                    if word == '#':
                        continue
                    if word == '*':
                        continue
                    if '://' in word:
                        linkStr = word
                        break
                if linkStr:
                    lineStr = lineStr.replace(linkStr, '').strip()
                    # avoid any dubious scripts being added
                    if '<' not in lineStr:
                        # remove trailing comma if present
                        if lineStr.endswith(','):
                            lineStr = lineStr[:len(lineStr)-1]
                        # add link to the returned html
                        htmlStr += \
                            '      <p><a href="' + linkStr + '">' + \
                            lineStr + '</a></p>\n'
                        linksFileContainsEntries = True
                else:
                    if lineStr.startswith('#') or lineStr.startswith('*'):
                        lineStr = lineStr[1:].strip()
                        htmlStr += separatorStr
                        htmlStr += \
                            '      <h3 class="linksHeader">' + \
                            lineStr + '</h3>\n'
                    else:
                        htmlStr += \
                            '      <p>' + lineStr + '</p>\n'
                    linksFileContainsEntries = True

    if linksFileContainsEntries and not rssIconAtTop:
        htmlStr += '<br><div class="columnIcons">' + rssIconStr + '</div>'
    return htmlStr


def votesIndicator(totalVotes: int, positiveVoting: bool) -> str:
    """Returns an indicator of the number of votes on a newswire item
    """
    if totalVotes <= 0:
        return ''
    totalVotesStr = ' '
    for v in range(totalVotes):
        if positiveVoting:
            totalVotesStr += '✓'
        else:
            totalVotesStr += '✗'
    return totalVotesStr


def htmlNewswire(baseDir: str, newswire: {}, nickname: str, moderator: bool,
                 translate: {}, positiveVoting: bool, iconsDir: str) -> str:
    """Converts a newswire dict into html
    """
    separatorStr = htmlPostSeparator(baseDir, 'right')
    htmlStr = ''
    for dateStr, item in newswire.items():
        publishedDate = \
            datetime.strptime(dateStr, "%Y-%m-%d %H:%M:%S%z")
        dateShown = publishedDate.strftime("%Y-%m-%d %H:%M")

        dateStrLink = dateStr.replace('T', ' ')
        dateStrLink = dateStrLink.replace('Z', '')
        moderatedItem = item[5]
        htmlStr += separatorStr
        if moderatedItem and 'vote:' + nickname in item[2]:
            totalVotesStr = ''
            totalVotes = 0
            if moderator:
                totalVotes = votesOnNewswireItem(item[2])
                totalVotesStr = \
                    votesIndicator(totalVotes, positiveVoting)

            title = removeLongWords(item[0], 16, []).replace('\n', '<br>')
            htmlStr += '<p class="newswireItemVotedOn">' + \
                '<a href="' + item[1] + '">' + \
                '<span class="newswireItemVotedOn">' + title + \
                '</span></a>' + totalVotesStr
            if moderator:
                htmlStr += \
                    ' ' + dateShown + '<a href="/users/' + nickname + \
                    '/newswireunvote=' + dateStrLink + '" ' + \
                    'title="' + translate['Remove Vote'] + '">'
                htmlStr += '<img loading="lazy" class="voteicon" src="/' + \
                    iconsDir + '/vote.png" /></a></p>\n'
            else:
                htmlStr += ' <span class="newswireDateVotedOn">'
                htmlStr += dateShown + '</span></p>\n'
        else:
            totalVotesStr = ''
            totalVotes = 0
            if moderator:
                if moderatedItem:
                    totalVotes = votesOnNewswireItem(item[2])
                    # show a number of ticks or crosses for how many
                    # votes for or against
                    totalVotesStr = \
                        votesIndicator(totalVotes, positiveVoting)

            title = removeLongWords(item[0], 16, []).replace('\n', '<br>')
            if moderator and moderatedItem:
                htmlStr += '<p class="newswireItemModerated">' + \
                    '<a href="' + item[1] + '">' + \
                    title + '</a>' + totalVotesStr
                htmlStr += ' ' + dateShown
                htmlStr += '<a href="/users/' + nickname + \
                    '/newswirevote=' + dateStrLink + '" ' + \
                    'title="' + translate['Vote'] + '">'
                htmlStr += '<img class="voteicon" src="/' + \
                    iconsDir + '/vote.png" /></a>'
                htmlStr += '</p>\n'
            else:
                htmlStr += '<p class="newswireItem">' + \
                    '<a href="' + item[1] + '">' + \
                    title + '</a>' + \
                    totalVotesStr
                htmlStr += ' <span class="newswireDate">'
                htmlStr += dateShown + '</span></p>\n'
    return htmlStr


def htmlCitations(baseDir: str, nickname: str, domain: str,
                  httpPrefix: str, defaultTimeline: str,
                  translate: {}, newswire: {}, cssCache: {},
                  blogTitle: str, blogContent: str,
                  blogImageFilename: str,
                  blogImageAttachmentMediaType: str,
                  blogImageDescription: str) -> str:
    """Show the citations screen when creating a blog
    """
    htmlStr = ''

    # create a list of dates for citations
    # these can then be used to re-select checkboxes later
    citationsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/.citations.txt'
    citationsSelected = []
    if os.path.isfile(citationsFilename):
        citationsSeparator = '#####'
        with open(citationsFilename, "r") as f:
            citations = f.readlines()
            for line in citations:
                if citationsSeparator not in line:
                    continue
                sections = line.strip().split(citationsSeparator)
                if len(sections) != 3:
                    continue
                dateStr = sections[0]
                citationsSelected.append(dateStr)

    # the css filename
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if profileStyle:
        # replace any https within the css with whatever prefix is needed
        if httpPrefix != 'https':
            profileStyle = \
                profileStyle.replace('https://', httpPrefix + '://')

    # iconsDir = getIconsDir(baseDir)

    htmlStr = htmlHeader(cssFilename, profileStyle)

    # top banner
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)
    htmlStr += \
        '<a href="/users/' + nickname + '/newblog" title="' + \
        translate['Go Back'] + '" alt="' + \
        translate['Go Back'] + '">\n'
    htmlStr += '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    htmlStr += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="/users/' + nickname + \
        '/citationsdata">\n'
    htmlStr += '  <center>\n'
    htmlStr += translate['Choose newswire items ' +
                         'referenced in your article'] + '<br>'
    if blogTitle is None:
        blogTitle = ''
    htmlStr += \
        '    <input type="hidden" name="blogTitle" value="' + \
        blogTitle + '">\n'
    if blogContent is None:
        blogContent = ''
    htmlStr += \
        '    <input type="hidden" name="blogContent" value="' + \
        blogContent + '">\n'
    # submit button
    htmlStr += \
        '    <input type="submit" name="submitCitations" value="' + \
        translate['Submit'] + '">\n'
    htmlStr += '  </center>\n'

    citationsSeparator = '#####'

    # list of newswire items
    if newswire:
        ctr = 0
        for dateStr, item in newswire.items():
            # should this checkbox be selected?
            selectedStr = ''
            if dateStr in citationsSelected:
                selectedStr = ' checked'

            publishedDate = \
                datetime.strptime(dateStr, "%Y-%m-%d %H:%M:%S%z")
            dateShown = publishedDate.strftime("%Y-%m-%d %H:%M")

            title = removeLongWords(item[0], 16, []).replace('\n', '<br>')
            link = item[1]

            citationValue = \
                dateStr + citationsSeparator + \
                title + citationsSeparator + \
                link
            htmlStr += \
                '<input type="checkbox" name="newswire' + str(ctr) + \
                '" value="' + citationValue + '"' + selectedStr + '/>' + \
                '<a href="' + link + '"><cite>' + title + '</cite></a> '
            htmlStr += '<span class="newswireDate">' + \
                dateShown + '</span><br>\n'
            ctr += 1

    htmlStr += '</form>\n'
    return htmlStr + htmlFooter()


def getRightColumnContent(baseDir: str, nickname: str, domainFull: str,
                          httpPrefix: str, translate: {},
                          iconsDir: str, moderator: bool, editor: bool,
                          newswire: {}, positiveVoting: bool,
                          showBackButton: bool, timelinePath: str,
                          showPublishButton: bool,
                          showPublishAsIcon: bool,
                          rssIconAtTop: bool,
                          publishButtonAtTop: bool,
                          authorized: bool,
                          showHeaderImage: bool) -> str:
    """Returns html content for the right column
    """
    htmlStr = ''

    domain = domainFull
    if ':' in domain:
        domain = domain.split(':')

    if authorized:
        # only show the publish button if logged in, otherwise replace it with
        # a login button
        publishButtonStr = \
            '        <a href="' + \
            '/users/' + nickname + '/newblog" ' + \
            'title="' + translate['Publish a news article'] + '">' + \
            '<button class="publishbtn">' + \
            translate['Publish'] + '</button></a>\n'
    else:
        # if not logged in then replace the publish button with
        # a login button
        publishButtonStr = \
            '        <a href="/login"><button class="publishbtn">' + \
            translate['Login'] + '</button></a>\n'

    # show publish button at the top if needed
    if publishButtonAtTop:
        htmlStr += '<center>' + publishButtonStr + '</center>'

    # show a column header image, eg. title of the theme or newswire banner
    editImageClass = ''
    if showHeaderImage:
        rightImageFile, rightColumnImageFilename = \
            getRightImageFile(baseDir, nickname, domain)
        if not os.path.isfile(rightColumnImageFilename):
            theme = getConfigParam(baseDir, 'theme').lower()
            if theme == 'default':
                theme = ''
            else:
                theme = '_' + theme
            themeRightImageFile, themeRightColumnImageFilename = \
                getImageFile(baseDir, 'right_col_image', baseDir + '/img',
                             nickname, domain)
            if os.path.isfile(themeRightColumnImageFilename):
                rightColumnImageFilename = \
                    baseDir + '/accounts/' + \
                    nickname + '@' + domain + '/' + themeRightImageFile
                copyfile(themeRightColumnImageFilename,
                         rightColumnImageFilename)
                rightImageFile = themeRightImageFile

        # show the image at the top of the column
        editImageClass = 'rightColEdit'
        if os.path.isfile(rightColumnImageFilename):
            editImageClass = 'rightColEditImage'
            htmlStr += \
                '\n      <center>\n' + \
                '          <img class="rightColImg" ' + \
                'loading="lazy" src="/users/' + \
                nickname + '/' + rightImageFile + '" />\n' + \
                '      </center>\n'

    if (showPublishButton or editor or rssIconAtTop) and not showHeaderImage:
        htmlStr += '<div class="columnIcons">'

    if editImageClass == 'rightColEdit':
        htmlStr += '\n      <center>\n'

    # whether to show a back icon
    # This is probably going to be osolete soon
    if showBackButton:
        htmlStr += \
            '      <a href="' + timelinePath + '">' + \
            '<button class="cancelbtn">' + \
            translate['Go Back'] + '</button></a>\n'

    if showPublishButton and not publishButtonAtTop:
        if not showPublishAsIcon:
            htmlStr += publishButtonStr

    # show the edit icon
    if editor:
        if os.path.isfile(baseDir + '/accounts/newswiremoderation.txt'):
            # show the edit icon highlighted
            htmlStr += \
                '        <a href="' + \
                '/users/' + nickname + '/editnewswire">' + \
                '<img class="' + editImageClass + \
                '" loading="lazy" alt="' + \
                translate['Edit newswire'] + '" title="' + \
                translate['Edit newswire'] + '" src="/' + \
                iconsDir + '/edit_notify.png" /></a>\n'
        else:
            # show the edit icon
            htmlStr += \
                '        <a href="' + \
                '/users/' + nickname + '/editnewswire">' + \
                '<img class="' + editImageClass + \
                '" loading="lazy" alt="' + \
                translate['Edit newswire'] + '" title="' + \
                translate['Edit newswire'] + '" src="/' + \
                iconsDir + '/edit.png" /></a>\n'

    # show the RSS icon
    rssIconStr = \
        '        <a href="/newswire.xml">' + \
        '<img class="' + editImageClass + \
        '" loading="lazy" alt="' + \
        translate['Newswire RSS Feed'] + '" title="' + \
        translate['Newswire RSS Feed'] + '" src="/' + \
        iconsDir + '/logorss.png" /></a>\n'
    if rssIconAtTop:
        htmlStr += rssIconStr

    # show publish icon at top
    if showPublishButton:
        if showPublishAsIcon:
            htmlStr += \
                '        <a href="' + \
                '/users/' + nickname + '/newblog">' + \
                '<img class="' + editImageClass + \
                '" loading="lazy" alt="' + \
                translate['Publish a news article'] + '" title="' + \
                translate['Publish a news article'] + '" src="/' + \
                iconsDir + '/publish.png" /></a>\n'

    if editImageClass == 'rightColEdit':
        htmlStr += '      </center>\n'
    else:
        if showHeaderImage:
            htmlStr += '      <br>\n'

    if (showPublishButton or editor or rssIconAtTop) and not showHeaderImage:
        htmlStr += '</div><br>'

    # show the newswire lines
    newswireContentStr = \
        htmlNewswire(baseDir, newswire, nickname, moderator, translate,
                     positiveVoting, iconsDir)
    htmlStr += newswireContentStr

    # show the rss icon at the bottom, typically on the right hand side
    if newswireContentStr and not rssIconAtTop:
        htmlStr += '<br><div class="columnIcons">' + rssIconStr + '</div>'
    return htmlStr


def htmlLinksMobile(cssCache: {}, baseDir: str,
                    nickname: str, domainFull: str,
                    httpPrefix: str, translate,
                    timelinePath: str, authorized: bool,
                    rssIconAtTop: bool,
                    iconsAsButtons: bool,
                    defaultTimeline: str) -> str:
    """Show the left column links within mobile view
    """
    htmlStr = ''

    # the css filename
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if profileStyle:
        # replace any https within the css with whatever prefix is needed
        if httpPrefix != 'https':
            profileStyle = \
                profileStyle.replace('https://', httpPrefix + '://')

    iconsDir = getIconsDir(baseDir)

    # is the user a site editor?
    if nickname == 'news':
        editor = False
    else:
        editor = isEditor(baseDir, nickname)

    domain = domainFull
    if ':' in domain:
        domain = domain.split(':')[0]

    htmlStr = htmlHeader(cssFilename, profileStyle)
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)
    htmlStr += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '">' + \
        '<img loading="lazy" class="timeline-banner" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    htmlStr += '<center>' + \
        headerButtonsFrontScreen(translate, nickname,
                                 'links', authorized,
                                 iconsAsButtons, iconsDir) + '</center>'
    htmlStr += \
        getLeftColumnContent(baseDir, nickname, domainFull,
                             httpPrefix, translate,
                             iconsDir, editor,
                             False, timelinePath,
                             rssIconAtTop, False, False)
    htmlStr += '</div>\n' + htmlFooter()
    return htmlStr


def htmlNewswireMobile(cssCache: {}, baseDir: str, nickname: str,
                       domain: str, domainFull: str,
                       httpPrefix: str, translate: {},
                       newswire: {},
                       positiveVoting: bool,
                       timelinePath: str,
                       showPublishAsIcon: bool,
                       authorized: bool,
                       rssIconAtTop: bool,
                       iconsAsButtons: bool,
                       defaultTimeline: str) -> str:
    """Shows the mobile version of the newswire right column
    """
    htmlStr = ''

    # the css filename
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if profileStyle:
        # replace any https within the css with whatever prefix is needed
        if httpPrefix != 'https':
            profileStyle = \
                profileStyle.replace('https://',
                                     httpPrefix + '://')

    iconsDir = getIconsDir(baseDir)

    if nickname == 'news':
        editor = False
        moderator = False
    else:
        # is the user a moderator?
        moderator = isModerator(baseDir, nickname)

        # is the user a site editor?
        editor = isEditor(baseDir, nickname)

    showPublishButton = editor

    htmlStr = htmlHeader(cssFilename, profileStyle)

    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)
    htmlStr += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '">' + \
        '<img loading="lazy" class="timeline-banner" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" /></a>\n'

    htmlStr += '<center>' + \
        headerButtonsFrontScreen(translate, nickname,
                                 'newswire', authorized,
                                 iconsAsButtons, iconsDir) + '</center>'
    htmlStr += \
        getRightColumnContent(baseDir, nickname, domainFull,
                              httpPrefix, translate,
                              iconsDir, moderator, editor,
                              newswire, positiveVoting,
                              False, timelinePath, showPublishButton,
                              showPublishAsIcon, rssIconAtTop, False,
                              authorized, False)
    htmlStr += htmlFooter()
    return htmlStr


def headerButtonsFrontScreen(translate: {},
                             nickname: str, boxName: str,
                             authorized: bool,
                             iconsAsButtons: bool,
                             iconsDir: bool) -> str:
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
                '<img loading="lazy" src="/' + iconsDir + \
                '/newswire.png" title="' + translate['Newswire'] + \
                '" alt="| ' + translate['Newswire'] + '"/></a>\n'
            headerStr += \
                '        <a href="' + \
                '/users/news/linksmobile">' + \
                '<img loading="lazy" src="/' + iconsDir + \
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


def headerButtonsTimeline(defaultTimeline: str,
                          boxName: str,
                          pageNumber: int,
                          translate: {},
                          usersPath: str,
                          mediaButton: str,
                          blogsButton: str,
                          newsButton: str,
                          inboxButton: str,
                          dmButton: str,
                          newDM: str,
                          repliesButton: str,
                          newReply: str,
                          minimal: bool,
                          sentButton: str,
                          sharesButtonStr: str,
                          bookmarksButtonStr: str,
                          eventsButtonStr: str,
                          moderationButtonStr: str,
                          newPostButtonStr: str,
                          baseDir: str,
                          nickname: str, domain: str,
                          iconsDir: str,
                          timelineStartTime,
                          newCalendarEvent: bool,
                          calendarPath: str,
                          calendarImage: str,
                          followApprovals: str,
                          iconsAsButtons: bool) -> str:
    """Returns the header at the top of the timeline, containing
    buttons for inbox, outbox, search, calendar, etc
    """
    # start of the button header with inbox, outbox, etc
    tlStr = '<div class="containerHeader">\n'
    # first button
    if defaultTimeline == 'tlmedia':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlmedia"><button class="' + \
            mediaButton + '"><span>' + translate['Media'] + \
            '</span></button></a>'
    elif defaultTimeline == 'tlblogs':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlblogs"><button class="' + \
            blogsButton + '"><span>' + translate['Blogs'] + \
            '</span></button></a>'
    elif defaultTimeline == 'tlnews':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlnews"><button class="' + \
            newsButton + '"><span>' + translate['Features'] + \
            '</span></button></a>'
    else:
        tlStr += \
            '<a href="' + usersPath + \
            '/inbox"><button class="' + \
            inboxButton + '"><span>' + \
            translate['Inbox'] + '</span></button></a>'

    # if this is a news instance and we are viewing the news timeline
    newsHeader = False
    if defaultTimeline == 'tlnews' and boxName == 'tlnews':
        newsHeader = True

    if not newsHeader:
        tlStr += \
            '<a href="' + usersPath + \
            '/dm"><button class="' + dmButton + \
            '"><span>' + htmlHighlightLabel(translate['DM'], newDM) + \
            '</span></button></a>'

        tlStr += \
            '<a href="' + usersPath + '/tlreplies"><button class="' + \
            repliesButton + '"><span>' + \
            htmlHighlightLabel(translate['Replies'], newReply) + \
            '</span></button></a>'

    # typically the media button
    if defaultTimeline != 'tlmedia':
        if not minimal and not newsHeader:
            tlStr += \
                '<a href="' + usersPath + \
                '/tlmedia"><button class="' + \
                mediaButton + '"><span>' + translate['Media'] + \
                '</span></button></a>'
    else:
        if not minimal:
            tlStr += \
                '<a href="' + usersPath + \
                '/inbox"><button class="' + \
                inboxButton+'"><span>' + translate['Inbox'] + \
                '</span></button></a>'

    isFeaturesTimeline = \
        defaultTimeline == 'tlnews' and boxName == 'tlnews'

    if not isFeaturesTimeline:
        # typically the blogs button
        # but may change if this is a blogging oriented instance
        if defaultTimeline != 'tlblogs':
            if not minimal and not isFeaturesTimeline:
                titleStr = translate['Blogs']
                if defaultTimeline == 'tlnews':
                    titleStr = translate['Article']
                tlStr += \
                    '<a href="' + usersPath + \
                    '/tlblogs"><button class="' + \
                    blogsButton + '"><span>' + titleStr + \
                    '</span></button></a>'
        else:
            if not minimal:
                tlStr += \
                    '<a href="' + usersPath + \
                    '/inbox"><button class="' + \
                    inboxButton + '"><span>' + translate['Inbox'] + \
                    '</span></button></a>'

    # typically the news button
    # but may change if this is a news oriented instance
    if defaultTimeline != 'tlnews':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlnews"><button class="' + \
            newsButton + '"><span>' + translate['News'] + \
            '</span></button></a>'
    else:
        if not newsHeader:
            tlStr += \
                '<a href="' + usersPath + \
                '/inbox"><button class="' + \
                inboxButton + '"><span>' + translate['Inbox'] + \
                '</span></button></a>'

    # show todays events buttons on the first inbox page
    happeningStr = ''
    if boxName == 'inbox' and pageNumber == 1:
        if todaysEventsCheck(baseDir, nickname, domain):
            now = datetime.now()

            # happening today button
            if not iconsAsButtons:
                happeningStr += \
                    '<a href="' + usersPath + '/calendar?year=' + \
                    str(now.year) + '?month=' + str(now.month) + \
                    '?day=' + str(now.day) + '">' + \
                    '<button class="buttonevent">' + \
                    translate['Happening Today'] + '</button></a>'
            else:
                happeningStr += \
                    '<a href="' + usersPath + '/calendar?year=' + \
                    str(now.year) + '?month=' + str(now.month) + \
                    '?day=' + str(now.day) + '">' + \
                    '<button class="button">' + \
                    translate['Happening Today'] + '</button></a>'

            # happening this week button
            if thisWeeksEventsCheck(baseDir, nickname, domain):
                if not iconsAsButtons:
                    happeningStr += \
                        '<a href="' + usersPath + \
                        '/calendar"><button class="buttonevent">' + \
                        translate['Happening This Week'] + '</button></a>'
                else:
                    happeningStr += \
                        '<a href="' + usersPath + \
                        '/calendar"><button class="button">' + \
                        translate['Happening This Week'] + '</button></a>'
        else:
            # happening this week button
            if thisWeeksEventsCheck(baseDir, nickname, domain):
                if not iconsAsButtons:
                    happeningStr += \
                        '<a href="' + usersPath + \
                        '/calendar"><button class="buttonevent">' + \
                        translate['Happening This Week'] + '</button></a>'
                else:
                    happeningStr += \
                        '<a href="' + usersPath + \
                        '/calendar"><button class="button">' + \
                        translate['Happening This Week'] + '</button></a>'

    if not newsHeader:
        # button for the outbox
        tlStr += \
            '<a href="' + usersPath + \
            '/outbox"><button class="' + \
            sentButton + '"><span>' + translate['Outbox'] + \
            '</span></button></a>'

        # add other buttons
        tlStr += \
            sharesButtonStr + bookmarksButtonStr + eventsButtonStr + \
            moderationButtonStr + happeningStr + newPostButtonStr

    if not newsHeader:
        if not iconsAsButtons:
            # the search icon
            tlStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/search"><img loading="lazy" src="/' + \
                iconsDir + '/search.png" title="' + \
                translate['Search and follow'] + '" alt="| ' + \
                translate['Search and follow'] + \
                '" class="timelineicon"/></a>'
        else:
            # the search button
            tlStr += \
                '<a href="' + usersPath + \
                '/search"><button class="button">' + \
                '<span>' + translate['Search'] + \
                '</span></button></a>'

    # benchmark 5
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 5 = ' + str(timeDiff))

    # the calendar button
    if not isFeaturesTimeline:
        calendarAltText = translate['Calendar']
        if newCalendarEvent:
            # indicate that the calendar icon is highlighted
            calendarAltText = '*' + calendarAltText + '*'
        if not iconsAsButtons:
            tlStr += \
                '      <a class="imageAnchor" href="' + \
                usersPath + calendarPath + \
                '"><img loading="lazy" src="/' + iconsDir + '/' + \
                calendarImage + '" title="' + translate['Calendar'] + \
                '" alt="| ' + calendarAltText + \
                '" class="timelineicon"/></a>\n'
        else:
            tlStr += \
                '<a href="' + usersPath + calendarPath + \
                '"><button class="button">' + \
                '<span>' + translate['Calendar'] + \
                '</span></button></a>'

    if not newsHeader:
        # the show/hide button, for a simpler header appearance
        if not iconsAsButtons:
            tlStr += \
                '      <a class="imageAnchor" href="' + \
                usersPath + '/minimal' + \
                '"><img loading="lazy" src="/' + iconsDir + \
                '/showhide.png" title="' + translate['Show/Hide Buttons'] + \
                '" alt="| ' + translate['Show/Hide Buttons'] + \
                '" class="timelineicon"/></a>\n'
        else:
            tlStr += \
                '<a href="' + usersPath + '/minimal' + \
                '"><button class="button">' + \
                '<span>' + translate['Expand'] + \
                '</span></button></a>'

    if newsHeader:
        tlStr += \
            '<a href="' + usersPath + '/inbox">' + \
            '<button class="button">' + \
            '<span>' + translate['User'] + '</span></button></a>'

    # the newswire button to show right column links
    if not iconsAsButtons:
        tlStr += \
            '<a class="imageAnchorMobile" href="' + \
            usersPath + '/newswiremobile">' + \
            '<img loading="lazy" src="/' + iconsDir + \
            '/newswire.png" title="' + translate['News'] + \
            '" alt="| ' + translate['News'] + \
            '" class="timelineicon"/></a>'
    else:
        # NOTE: deliberately no \n at end of line
        tlStr += \
            '<a href="' + \
            usersPath + '/newswiremobile' + \
            '"><button class="buttonMobile">' + \
            '<span>' + translate['Newswire'] + \
            '</span></button></a>'

    # the links button to show left column links
    if not iconsAsButtons:
        tlStr += \
            '<a class="imageAnchorMobile" href="' + \
            usersPath + '/linksmobile">' + \
            '<img loading="lazy" src="/' + iconsDir + \
            '/links.png" title="' + translate['Edit Links'] + \
            '" alt="| ' + translate['Edit Links'] + \
            '" class="timelineicon"/></a>'
        # end of headericons div
        tlStr += '</div>'
    else:
        # NOTE: deliberately no \n at end of line
        tlStr += \
            '<a href="' + \
            usersPath + '/linksmobile' + \
            '"><button class="buttonMobile">' + \
            '<span>' + translate['Links'] + \
            '</span></button></a>'

    if newsHeader:
        tlStr += \
            '<a href="' + usersPath + '/editprofile">' + \
            '<button class="buttonDesktop">' + \
            '<span>' + translate['Settings'] + '</span></button></a>'

    if not newsHeader:
        tlStr += followApprovals
    # end of the button header with inbox, outbox, etc
    tlStr += '    </div>\n'
    return tlStr


def htmlTimeline(cssCache: {}, defaultTimeline: str,
                 recentPostsCache: {}, maxRecentPosts: int,
                 translate: {}, pageNumber: int,
                 itemsPerPage: int, session, baseDir: str,
                 wfRequest: {}, personCache: {},
                 nickname: str, domain: str, port: int, timelineJson: {},
                 boxName: str, allowDeletion: bool,
                 httpPrefix: str, projectVersion: str,
                 manuallyApproveFollowers: bool,
                 minimal: bool,
                 YTReplacementDomain: str,
                 showPublishedDateOnly: bool,
                 newswire: {}, moderator: bool,
                 editor: bool,
                 positiveVoting: bool,
                 showPublishAsIcon: bool,
                 fullWidthTimelineButtonHeader: bool,
                 iconsAsButtons: bool,
                 rssIconAtTop: bool,
                 publishButtonAtTop: bool,
                 authorized: bool) -> str:
    """Show the timeline as html
    """
    timelineStartTime = time.time()

    accountDir = baseDir + '/accounts/' + nickname + '@' + domain

    # should the calendar icon be highlighted?
    newCalendarEvent = False
    calendarImage = 'calendar.png'
    calendarPath = '/calendar'
    calendarFile = accountDir + '/.newCalendar'
    if os.path.isfile(calendarFile):
        newCalendarEvent = True
        calendarImage = 'calendar_notify.png'
        with open(calendarFile, 'r') as calfile:
            calendarPath = calfile.read().replace('##sent##', '')
            calendarPath = calendarPath.replace('\n', '').replace('\r', '')

    # should the DM button be highlighted?
    newDM = False
    dmFile = accountDir + '/.newDM'
    if os.path.isfile(dmFile):
        newDM = True
        if boxName == 'dm':
            os.remove(dmFile)

    # should the Replies button be highlighted?
    newReply = False
    replyFile = accountDir + '/.newReply'
    if os.path.isfile(replyFile):
        newReply = True
        if boxName == 'tlreplies':
            os.remove(replyFile)

    # should the Shares button be highlighted?
    newShare = False
    newShareFile = accountDir + '/.newShare'
    if os.path.isfile(newShareFile):
        newShare = True
        if boxName == 'tlshares':
            os.remove(newShareFile)

    # should the Moderation/reports button be highlighted?
    newReport = False
    newReportFile = accountDir + '/.newReport'
    if os.path.isfile(newReportFile):
        newReport = True
        if boxName == 'moderation':
            os.remove(newReportFile)

    # directory where icons are found
    # This changes depending upon theme
    iconsDir = getIconsDir(baseDir)

    separatorStr = ''
    if boxName != 'tlmedia':
        separatorStr = htmlPostSeparator(baseDir, None)

    # the css filename
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    # filename of the banner shown at the top
    bannerFile, bannerFilename = getBannerFile(baseDir, nickname, domain)

    # benchmark 1
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 1 = ' + str(timeDiff))

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if not profileStyle:
        print('ERROR: css file not found ' + cssFilename)
        return None

    # replace any https within the css with whatever prefix is needed
    if httpPrefix != 'https':
        profileStyle = \
            profileStyle.replace('https://',
                                 httpPrefix + '://')

    # is the user a moderator?
    if not moderator:
        moderator = isModerator(baseDir, nickname)

    # is the user a site editor?
    if not editor:
        editor = isEditor(baseDir, nickname)

    # benchmark 2
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 2 = ' + str(timeDiff))

    # the appearance of buttons - highlighted or not
    inboxButton = 'button'
    blogsButton = 'button'
    newsButton = 'button'
    dmButton = 'button'
    if newDM:
        dmButton = 'buttonhighlighted'
    repliesButton = 'button'
    if newReply:
        repliesButton = 'buttonhighlighted'
    mediaButton = 'button'
    bookmarksButton = 'button'
    eventsButton = 'button'
    sentButton = 'button'
    sharesButton = 'button'
    if newShare:
        sharesButton = 'buttonhighlighted'
    moderationButton = 'button'
    if newReport:
        moderationButton = 'buttonhighlighted'
    if boxName == 'inbox':
        inboxButton = 'buttonselected'
    elif boxName == 'tlblogs':
        blogsButton = 'buttonselected'
    elif boxName == 'tlnews':
        newsButton = 'buttonselected'
    elif boxName == 'dm':
        dmButton = 'buttonselected'
        if newDM:
            dmButton = 'buttonselectedhighlighted'
    elif boxName == 'tlreplies':
        repliesButton = 'buttonselected'
        if newReply:
            repliesButton = 'buttonselectedhighlighted'
    elif boxName == 'tlmedia':
        mediaButton = 'buttonselected'
    elif boxName == 'outbox':
        sentButton = 'buttonselected'
    elif boxName == 'moderation':
        moderationButton = 'buttonselected'
        if newReport:
            moderationButton = 'buttonselectedhighlighted'
    elif boxName == 'tlshares':
        sharesButton = 'buttonselected'
        if newShare:
            sharesButton = 'buttonselectedhighlighted'
    elif boxName == 'tlbookmarks' or boxName == 'bookmarks':
        bookmarksButton = 'buttonselected'
    elif boxName == 'tlevents':
        eventsButton = 'buttonselected'

    # get the full domain, including any port number
    fullDomain = domain
    if port != 80 and port != 443:
        if ':' not in domain:
            fullDomain = domain + ':' + str(port)

    usersPath = '/users/' + nickname
    actor = httpPrefix + '://' + fullDomain + usersPath

    showIndividualPostIcons = True

    # show an icon for new follow approvals
    followApprovals = ''
    followRequestsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/followrequests.txt'
    if os.path.isfile(followRequestsFilename):
        with open(followRequestsFilename, 'r') as f:
            for line in f:
                if len(line) > 0:
                    # show follow approvals icon
                    followApprovals = \
                        '<a href="' + usersPath + \
                        '/followers#buttonheader">' + \
                        '<img loading="lazy" ' + \
                        'class="timelineicon" alt="' + \
                        translate['Approve follow requests'] + \
                        '" title="' + translate['Approve follow requests'] + \
                        '" src="/' + iconsDir + '/person.png"/></a>\n'
                    break

    # benchmark 3
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 3 = ' + str(timeDiff))

    # moderation / reports button
    moderationButtonStr = ''
    if moderator and not minimal:
        moderationButtonStr = \
            '<a href="' + usersPath + \
            '/moderation"><button class="' + \
            moderationButton + '"><span>' + \
            htmlHighlightLabel(translate['Mod'], newReport) + \
            ' </span></button></a>'

    # shares, bookmarks and events buttons
    sharesButtonStr = ''
    bookmarksButtonStr = ''
    eventsButtonStr = ''
    if not minimal:
        sharesButtonStr = \
            '<a href="' + usersPath + '/tlshares"><button class="' + \
            sharesButton + '"><span>' + \
            htmlHighlightLabel(translate['Shares'], newShare) + \
            '</span></button></a>'

        bookmarksButtonStr = \
            '<a href="' + usersPath + '/tlbookmarks"><button class="' + \
            bookmarksButton + '"><span>' + translate['Bookmarks'] + \
            '</span></button></a>'

        eventsButtonStr = \
            '<a href="' + usersPath + '/tlevents"><button class="' + \
            eventsButton + '"><span>' + translate['Events'] + \
            '</span></button></a>'

    tlStr = htmlHeader(cssFilename, profileStyle)

    # benchmark 4
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 4 = ' + str(timeDiff))

    # if this is a news instance and we are viewing the news timeline
    newsHeader = False
    if defaultTimeline == 'tlnews' and boxName == 'tlnews':
        newsHeader = True

    newPostButtonStr = ''
    # start of headericons div
    if not newsHeader:
        if not iconsAsButtons:
            newPostButtonStr += '<div class="headericons">'

    # what screen to go to when a new post is created
    if boxName == 'dm':
        if not iconsAsButtons:
            newPostButtonStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/newdm"><img loading="lazy" src="/' + \
                iconsDir + '/newpost.png" title="' + \
                translate['Create a new DM'] + \
                '" alt="| ' + translate['Create a new DM'] + \
                '" class="timelineicon"/></a>\n'
        else:
            newPostButtonStr += \
                '<a href="' + usersPath + '/newdm">' + \
                '<button class="button"><span>' + \
                translate['Post'] + ' </span></button></a>'
    elif boxName == 'tlblogs' or boxName == 'tlnews':
        if not iconsAsButtons:
            newPostButtonStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/newblog"><img loading="lazy" src="/' + \
                iconsDir + '/newpost.png" title="' + \
                translate['Create a new post'] + '" alt="| ' + \
                translate['Create a new post'] + \
                '" class="timelineicon"/></a>\n'
        else:
            newPostButtonStr += \
                '<a href="' + usersPath + '/newblog">' + \
                '<button class="button"><span>' + \
                translate['Post'] + '</span></button></a>'
    elif boxName == 'tlevents':
        if not iconsAsButtons:
            newPostButtonStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/newevent"><img loading="lazy" src="/' + \
                iconsDir + '/newpost.png" title="' + \
                translate['Create a new event'] + '" alt="| ' + \
                translate['Create a new event'] + \
                '" class="timelineicon"/></a>\n'
        else:
            newPostButtonStr += \
                '<a href="' + usersPath + '/newevent">' + \
                '<button class="button"><span>' + \
                translate['Post'] + '</span></button></a>'
    else:
        if not manuallyApproveFollowers:
            if not iconsAsButtons:
                newPostButtonStr += \
                    '<a class="imageAnchor" href="' + usersPath + \
                    '/newpost"><img loading="lazy" src="/' + \
                    iconsDir + '/newpost.png" title="' + \
                    translate['Create a new post'] + '" alt="| ' + \
                    translate['Create a new post'] + \
                    '" class="timelineicon"/></a>\n'
            else:
                newPostButtonStr += \
                    '<a href="' + usersPath + '/newpost">' + \
                    '<button class="button"><span>' + \
                    translate['Post'] + '</span></button></a>'
        else:
            if not iconsAsButtons:
                newPostButtonStr += \
                    '<a class="imageAnchor" href="' + usersPath + \
                    '/newfollowers"><img loading="lazy" src="/' + \
                    iconsDir + '/newpost.png" title="' + \
                    translate['Create a new post'] + \
                    '" alt="| ' + translate['Create a new post'] + \
                    '" class="timelineicon"/></a>\n'
            else:
                newPostButtonStr += \
                    '<a href="' + usersPath + '/newfollowers">' + \
                    '<button class="button"><span>' + \
                    translate['Post'] + '</span></button></a>'

    # This creates a link to the profile page when viewed
    # in lynx, but should be invisible in a graphical web browser
    tlStr += \
        '<div class="transparent"><label class="transparent">' + \
        '<a href="/users/' + nickname + '">' + \
        translate['Switch to profile view'] + '</a></label></div>\n'

    # banner and row of buttons
    tlStr += \
        '<a href="/users/' + nickname + '" title="' + \
        translate['Switch to profile view'] + '" alt="' + \
        translate['Switch to profile view'] + '">\n'
    tlStr += '<img loading="lazy" class="timeline-banner" src="' + \
        usersPath + '/' + bannerFile + '" /></a>\n'

    if fullWidthTimelineButtonHeader:
        tlStr += \
            headerButtonsTimeline(defaultTimeline, boxName, pageNumber,
                                  translate, usersPath, mediaButton,
                                  blogsButton, newsButton, inboxButton,
                                  dmButton, newDM, repliesButton,
                                  newReply, minimal, sentButton,
                                  sharesButtonStr, bookmarksButtonStr,
                                  eventsButtonStr, moderationButtonStr,
                                  newPostButtonStr, baseDir, nickname,
                                  domain, iconsDir, timelineStartTime,
                                  newCalendarEvent, calendarPath,
                                  calendarImage, followApprovals,
                                  iconsAsButtons)

    # start the timeline
    tlStr += '<table class="timeline">\n'
    tlStr += '  <colgroup>\n'
    tlStr += '    <col span="1" class="column-left">\n'
    tlStr += '    <col span="1" class="column-center">\n'
    tlStr += '    <col span="1" class="column-right">\n'
    tlStr += '  </colgroup>\n'
    tlStr += '  <tbody>\n'
    tlStr += '    <tr>\n'

    domainFull = domain
    if port:
        if port != 80 and port != 443:
            domainFull = domain + ':' + str(port)

    # left column
    leftColumnStr = \
        getLeftColumnContent(baseDir, nickname, domainFull,
                             httpPrefix, translate, iconsDir,
                             editor, False, None, rssIconAtTop,
                             True, False)
    tlStr += '  <td valign="top" class="col-left">' + \
        leftColumnStr + '  </td>\n'
    # center column containing posts
    tlStr += '  <td valign="top" class="col-center">\n'

    if not fullWidthTimelineButtonHeader:
        tlStr += \
            headerButtonsTimeline(defaultTimeline, boxName, pageNumber,
                                  translate, usersPath, mediaButton,
                                  blogsButton, newsButton, inboxButton,
                                  dmButton, newDM, repliesButton,
                                  newReply, minimal, sentButton,
                                  sharesButtonStr, bookmarksButtonStr,
                                  eventsButtonStr, moderationButtonStr,
                                  newPostButtonStr, baseDir, nickname,
                                  domain, iconsDir, timelineStartTime,
                                  newCalendarEvent, calendarPath,
                                  calendarImage, followApprovals,
                                  iconsAsButtons)

    # second row of buttons for moderator actions
    if moderator and boxName == 'moderation':
        tlStr += \
            '<form method="POST" action="/users/' + \
            nickname + '/moderationaction">'
        tlStr += '<div class="container">\n'
        idx = 'Nickname or URL. Block using *@domain or nickname@domain'
        tlStr += \
            '    <b>' + translate[idx] + '</b><br>\n'
        tlStr += '    <input type="text" ' + \
            'name="moderationAction" value="" autofocus><br>\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Remove the above item'] + \
            '" name="submitRemove" value="' + \
            translate['Remove'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Suspend the above account nickname'] + \
            '" name="submitSuspend" value="' + translate['Suspend'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Remove a suspension for an account nickname'] + \
            '" name="submitUnsuspend" value="' + \
            translate['Unsuspend'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Block an account on another instance'] + \
            '" name="submitBlock" value="' + translate['Block'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Unblock an account on another instance'] + \
            '" name="submitUnblock" value="' + translate['Unblock'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Information about current blocks/suspensions'] + \
            '" name="submitInfo" value="' + translate['Info'] + '">\n'
        tlStr += '</div>\n</form>\n'

    # benchmark 6
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 6 = ' + str(timeDiff))

    if boxName == 'tlshares':
        maxSharesPerAccount = itemsPerPage
        return (tlStr +
                htmlSharesTimeline(translate, pageNumber, itemsPerPage,
                                   baseDir, actor, nickname, domain, port,
                                   maxSharesPerAccount, httpPrefix) +
                htmlFooter())

    # benchmark 7
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 7 = ' + str(timeDiff))

    # benchmark 8
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 8 = ' + str(timeDiff))

    # page up arrow
    if pageNumber > 1:
        tlStr += \
            '  <center>\n' + \
            '    <a href="' + usersPath + '/' + boxName + \
            '?page=' + str(pageNumber - 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pageup.png" title="' + \
            translate['Page up'] + '" alt="' + \
            translate['Page up'] + '"></a>\n' + \
            '  </center>\n'

    # show the posts
    itemCtr = 0
    if timelineJson:
        # if this is the media timeline then add an extra gallery container
        if boxName == 'tlmedia':
            if pageNumber > 1:
                tlStr += '<br>'
            tlStr += '<div class="galleryContainer">\n'

        # show each post in the timeline
        for item in timelineJson['orderedItems']:
            timelinePostStartTime = time.time()

            if item['type'] == 'Create' or \
               item['type'] == 'Announce' or \
               item['type'] == 'Update':
                # is the actor who sent this post snoozed?
                if isPersonSnoozed(baseDir, nickname, domain, item['actor']):
                    continue

                # is the post in the memory cache of recent ones?
                currTlStr = None
                if boxName != 'tlmedia' and \
                   recentPostsCache.get('index'):
                    postId = \
                        removeIdEnding(item['id']).replace('/', '#')
                    if postId in recentPostsCache['index']:
                        if not item.get('muted'):
                            if recentPostsCache['html'].get(postId):
                                currTlStr = recentPostsCache['html'][postId]
                                currTlStr = \
                                    preparePostFromHtmlCache(currTlStr,
                                                             boxName,
                                                             pageNumber)
                                # benchmark cache post
                                timeDiff = \
                                    int((time.time() -
                                         timelinePostStartTime) * 1000)
                                if timeDiff > 100:
                                    print('TIMELINE POST CACHE TIMING ' +
                                          boxName + ' = ' + str(timeDiff))

                if not currTlStr:
                    # benchmark cache post
                    timeDiff = \
                        int((time.time() -
                             timelinePostStartTime) * 1000)
                    if timeDiff > 100:
                        print('TIMELINE POST DISK TIMING START ' +
                              boxName + ' = ' + str(timeDiff))

                    # read the post from disk
                    currTlStr = \
                        individualPostAsHtml(False, recentPostsCache,
                                             maxRecentPosts,
                                             iconsDir, translate, pageNumber,
                                             baseDir, session, wfRequest,
                                             personCache,
                                             nickname, domain, port,
                                             item, None, True,
                                             allowDeletion,
                                             httpPrefix, projectVersion,
                                             boxName,
                                             YTReplacementDomain,
                                             showPublishedDateOnly,
                                             boxName != 'dm',
                                             showIndividualPostIcons,
                                             manuallyApproveFollowers,
                                             False, True)
                    # benchmark cache post
                    timeDiff = \
                        int((time.time() -
                             timelinePostStartTime) * 1000)
                    if timeDiff > 100:
                        print('TIMELINE POST DISK TIMING ' +
                              boxName + ' = ' + str(timeDiff))

                if currTlStr:
                    itemCtr += 1
                    if separatorStr:
                        tlStr += separatorStr
                    tlStr += currTlStr
        if boxName == 'tlmedia':
            tlStr += '</div>\n'

    # page down arrow
    if itemCtr > 2:
        tlStr += \
            '      <center>\n' + \
            '        <a href="' + usersPath + '/' + boxName + '?page=' + \
            str(pageNumber + 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            iconsDir + '/pagedown.png" title="' + \
            translate['Page down'] + '" alt="' + \
            translate['Page down'] + '"></a>\n' + \
            '      </center>\n'

    # end of column-center
    tlStr += '  </td>\n'

    # right column
    rightColumnStr = getRightColumnContent(baseDir, nickname, domainFull,
                                           httpPrefix, translate, iconsDir,
                                           moderator, editor,
                                           newswire, positiveVoting,
                                           False, None, True,
                                           showPublishAsIcon,
                                           rssIconAtTop, publishButtonAtTop,
                                           authorized, True)
    tlStr += '  <td valign="top" class="col-right">' + \
        rightColumnStr + '  </td>\n'
    tlStr += '  </tr>\n'

    # benchmark 9
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 9 = ' + str(timeDiff))

    tlStr += '  </tbody>\n'
    tlStr += '</table>\n'
    tlStr += htmlFooter()
    return tlStr


def htmlShares(cssCache: {}, defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str, wfRequest: {}, personCache: {},
               nickname: str, domain: str, port: int,
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
    """Show the shares timeline as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, None,
                        'tlshares', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        False, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlInbox(cssCache: {}, defaultTimeline: str,
              recentPostsCache: {}, maxRecentPosts: int,
              translate: {}, pageNumber: int, itemsPerPage: int,
              session, baseDir: str, wfRequest: {}, personCache: {},
              nickname: str, domain: str, port: int, inboxJson: {},
              allowDeletion: bool,
              httpPrefix: str, projectVersion: str,
              minimal: bool, YTReplacementDomain: str,
              showPublishedDateOnly: bool,
              newswire: {}, positiveVoting: bool,
              showPublishAsIcon: bool,
              fullWidthTimelineButtonHeader: bool,
              iconsAsButtons: bool,
              rssIconAtTop: bool,
              publishButtonAtTop: bool,
              authorized: bool) -> str:
    """Show the inbox as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson,
                        'inbox', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlBookmarks(cssCache: {}, defaultTimeline: str,
                  recentPostsCache: {}, maxRecentPosts: int,
                  translate: {}, pageNumber: int, itemsPerPage: int,
                  session, baseDir: str, wfRequest: {}, personCache: {},
                  nickname: str, domain: str, port: int, bookmarksJson: {},
                  allowDeletion: bool,
                  httpPrefix: str, projectVersion: str,
                  minimal: bool, YTReplacementDomain: str,
                  showPublishedDateOnly: bool,
                  newswire: {}, positiveVoting: bool,
                  showPublishAsIcon: bool,
                  fullWidthTimelineButtonHeader: bool,
                  iconsAsButtons: bool,
                  rssIconAtTop: bool,
                  publishButtonAtTop: bool,
                  authorized: bool) -> str:
    """Show the bookmarks as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, bookmarksJson,
                        'tlbookmarks', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlEvents(cssCache: {}, defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str, wfRequest: {}, personCache: {},
               nickname: str, domain: str, port: int, bookmarksJson: {},
               allowDeletion: bool,
               httpPrefix: str, projectVersion: str,
               minimal: bool, YTReplacementDomain: str,
               showPublishedDateOnly: bool,
               newswire: {}, positiveVoting: bool,
               showPublishAsIcon: bool,
               fullWidthTimelineButtonHeader: bool,
               iconsAsButtons: bool,
               rssIconAtTop: bool,
               publishButtonAtTop: bool,
               authorized: bool) -> str:
    """Show the events as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, bookmarksJson,
                        'tlevents', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlInboxDMs(cssCache: {}, defaultTimeline: str,
                 recentPostsCache: {}, maxRecentPosts: int,
                 translate: {}, pageNumber: int, itemsPerPage: int,
                 session, baseDir: str, wfRequest: {}, personCache: {},
                 nickname: str, domain: str, port: int, inboxJson: {},
                 allowDeletion: bool,
                 httpPrefix: str, projectVersion: str,
                 minimal: bool, YTReplacementDomain: str,
                 showPublishedDateOnly: bool,
                 newswire: {}, positiveVoting: bool,
                 showPublishAsIcon: bool,
                 fullWidthTimelineButtonHeader: bool,
                 iconsAsButtons: bool,
                 rssIconAtTop: bool,
                 publishButtonAtTop: bool,
                 authorized: bool) -> str:
    """Show the DM timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'dm', allowDeletion,
                        httpPrefix, projectVersion, False, minimal,
                        YTReplacementDomain, showPublishedDateOnly,
                        newswire, False, False, positiveVoting,
                        showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlInboxReplies(cssCache: {}, defaultTimeline: str,
                     recentPostsCache: {}, maxRecentPosts: int,
                     translate: {}, pageNumber: int, itemsPerPage: int,
                     session, baseDir: str, wfRequest: {}, personCache: {},
                     nickname: str, domain: str, port: int, inboxJson: {},
                     allowDeletion: bool,
                     httpPrefix: str, projectVersion: str,
                     minimal: bool, YTReplacementDomain: str,
                     showPublishedDateOnly: bool,
                     newswire: {}, positiveVoting: bool,
                     showPublishAsIcon: bool,
                     fullWidthTimelineButtonHeader: bool,
                     iconsAsButtons: bool,
                     rssIconAtTop: bool,
                     publishButtonAtTop: bool,
                     authorized: bool) -> str:
    """Show the replies timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'tlreplies',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlInboxMedia(cssCache: {}, defaultTimeline: str,
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate: {}, pageNumber: int, itemsPerPage: int,
                   session, baseDir: str, wfRequest: {}, personCache: {},
                   nickname: str, domain: str, port: int, inboxJson: {},
                   allowDeletion: bool,
                   httpPrefix: str, projectVersion: str,
                   minimal: bool, YTReplacementDomain: str,
                   showPublishedDateOnly: bool,
                   newswire: {}, positiveVoting: bool,
                   showPublishAsIcon: bool,
                   fullWidthTimelineButtonHeader: bool,
                   iconsAsButtons: bool,
                   rssIconAtTop: bool,
                   publishButtonAtTop: bool,
                   authorized: bool) -> str:
    """Show the media timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'tlmedia',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlInboxBlogs(cssCache: {}, defaultTimeline: str,
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate: {}, pageNumber: int, itemsPerPage: int,
                   session, baseDir: str, wfRequest: {}, personCache: {},
                   nickname: str, domain: str, port: int, inboxJson: {},
                   allowDeletion: bool,
                   httpPrefix: str, projectVersion: str,
                   minimal: bool, YTReplacementDomain: str,
                   showPublishedDateOnly: bool,
                   newswire: {}, positiveVoting: bool,
                   showPublishAsIcon: bool,
                   fullWidthTimelineButtonHeader: bool,
                   iconsAsButtons: bool,
                   rssIconAtTop: bool,
                   publishButtonAtTop: bool,
                   authorized: bool) -> str:
    """Show the blogs timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'tlblogs',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlInboxNews(cssCache: {}, defaultTimeline: str,
                  recentPostsCache: {}, maxRecentPosts: int,
                  translate: {}, pageNumber: int, itemsPerPage: int,
                  session, baseDir: str, wfRequest: {}, personCache: {},
                  nickname: str, domain: str, port: int, inboxJson: {},
                  allowDeletion: bool,
                  httpPrefix: str, projectVersion: str,
                  minimal: bool, YTReplacementDomain: str,
                  showPublishedDateOnly: bool,
                  newswire: {}, moderator: bool, editor: bool,
                  positiveVoting: bool, showPublishAsIcon: bool,
                  fullWidthTimelineButtonHeader: bool,
                  iconsAsButtons: bool,
                  rssIconAtTop: bool,
                  publishButtonAtTop: bool,
                  authorized: bool) -> str:
    """Show the news timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, inboxJson, 'tlnews',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, moderator, editor,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


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


def htmlOutbox(cssCache: {}, defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str, wfRequest: {}, personCache: {},
               nickname: str, domain: str, port: int, outboxJson: {},
               allowDeletion: bool,
               httpPrefix: str, projectVersion: str,
               minimal: bool, YTReplacementDomain: str,
               showPublishedDateOnly: bool,
               newswire: {}, positiveVoting: bool,
               showPublishAsIcon: bool,
               fullWidthTimelineButtonHeader: bool,
               iconsAsButtons: bool,
               rssIconAtTop: bool,
               publishButtonAtTop: bool,
               authorized: bool) -> str:
    """Show the Outbox as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir, wfRequest, personCache,
                        nickname, domain, port, outboxJson, 'outbox',
                        allowDeletion, httpPrefix, projectVersion,
                        manuallyApproveFollowers, minimal,
                        YTReplacementDomain, showPublishedDateOnly,
                        newswire, False, False, positiveVoting,
                        showPublishAsIcon, fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized)


def htmlIndividualPost(cssCache: {},
                       recentPostsCache: {}, maxRecentPosts: int,
                       translate: {},
                       baseDir: str, session, wfRequest: {}, personCache: {},
                       nickname: str, domain: str, port: int, authorized: bool,
                       postJsonObject: {}, httpPrefix: str,
                       projectVersion: str, likedBy: str,
                       YTReplacementDomain: str,
                       showPublishedDateOnly: bool) -> str:
    """Show an individual post as html
    """
    iconsDir = getIconsDir(baseDir)
    postStr = ''
    if likedBy:
        likedByNickname = getNicknameFromActor(likedBy)
        likedByDomain, likedByPort = getDomainFromActor(likedBy)
        if likedByPort:
            if likedByPort != 80 and likedByPort != 443:
                likedByDomain += ':' + str(likedByPort)
        likedByHandle = likedByNickname + '@' + likedByDomain
        postStr += \
            '<p>' + translate['Liked by'] + \
            ' <a href="' + likedBy + '">@' + \
            likedByHandle + '</a>\n'

        domainFull = domain
        if port:
            if port != 80 and port != 443:
                domainFull = domain + ':' + str(port)
        actor = '/users/' + nickname
        followStr = '  <form method="POST" ' + \
            'accept-charset="UTF-8" action="' + actor + '/searchhandle">\n'
        followStr += \
            '    <input type="hidden" name="actor" value="' + actor + '">\n'
        followStr += \
            '    <input type="hidden" name="searchtext" value="' + \
            likedByHandle + '">\n'
        if not isFollowingActor(baseDir, nickname, domainFull, likedBy):
            followStr += '    <button type="submit" class="button" ' + \
                'name="submitSearch">' + translate['Follow'] + '</button>\n'
        followStr += '    <button type="submit" class="button" ' + \
            'name="submitBack">' + translate['Go Back'] + '</button>\n'
        followStr += '  </form>\n'
        postStr += followStr + '</p>\n'

    postStr += \
        individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                             iconsDir, translate, None,
                             baseDir, session, wfRequest, personCache,
                             nickname, domain, port, postJsonObject,
                             None, True, False,
                             httpPrefix, projectVersion, 'inbox',
                             YTReplacementDomain,
                             showPublishedDateOnly,
                             False, authorized, False, False, False)
    messageId = removeIdEnding(postJsonObject['id'])

    # show the previous posts
    if isinstance(postJsonObject['object'], dict):
        while postJsonObject['object'].get('inReplyTo'):
            postFilename = \
                locatePost(baseDir, nickname, domain,
                           postJsonObject['object']['inReplyTo'])
            if not postFilename:
                break
            postJsonObject = loadJson(postFilename)
            if postJsonObject:
                postStr = \
                    individualPostAsHtml(True, recentPostsCache,
                                         maxRecentPosts,
                                         iconsDir, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port,
                                         postJsonObject,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
                                         False, authorized,
                                         False, False, False) + postStr

    # show the following posts
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if postFilename:
        # is there a replies file for this post?
        repliesFilename = postFilename.replace('.json', '.replies')
        if os.path.isfile(repliesFilename):
            # get items from the replies file
            repliesJson = {
                'orderedItems': []
            }
            populateRepliesJson(baseDir, nickname, domain,
                                repliesFilename, authorized, repliesJson)
            # add items to the html output
            for item in repliesJson['orderedItems']:
                postStr += \
                    individualPostAsHtml(True, recentPostsCache,
                                         maxRecentPosts,
                                         iconsDir, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
                                         False, authorized,
                                         False, False, False)
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    postsCSS = getCSS(baseDir, cssFilename, cssCache)
    if postsCSS:
        if httpPrefix != 'https':
            postsCSS = postsCSS.replace('https://',
                                        httpPrefix + '://')
    return htmlHeader(cssFilename, postsCSS) + postStr + htmlFooter()


def htmlPostReplies(cssCache: {},
                    recentPostsCache: {}, maxRecentPosts: int,
                    translate: {}, baseDir: str,
                    session, wfRequest: {}, personCache: {},
                    nickname: str, domain: str, port: int, repliesJson: {},
                    httpPrefix: str, projectVersion: str,
                    YTReplacementDomain: str,
                    showPublishedDateOnly: bool) -> str:
    """Show the replies to an individual post as html
    """
    iconsDir = getIconsDir(baseDir)
    repliesStr = ''
    if repliesJson.get('orderedItems'):
        for item in repliesJson['orderedItems']:
            repliesStr += \
                individualPostAsHtml(True, recentPostsCache,
                                     maxRecentPosts,
                                     iconsDir, translate, None,
                                     baseDir, session, wfRequest, personCache,
                                     nickname, domain, port, item,
                                     None, True, False,
                                     httpPrefix, projectVersion, 'inbox',
                                     YTReplacementDomain,
                                     showPublishedDateOnly,
                                     False, False, False, False, False)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    postsCSS = getCSS(baseDir, cssFilename, cssCache)
    if postsCSS:
        if httpPrefix != 'https':
            postsCSS = postsCSS.replace('https://',
                                        httpPrefix + '://')
    return htmlHeader(cssFilename, postsCSS) + repliesStr + htmlFooter()


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


def htmlCalendarDeleteConfirm(cssCache: {}, translate: {}, baseDir: str,
                              path: str, httpPrefix: str,
                              domainFull: str, postId: str, postTime: str,
                              year: int, monthNumber: int,
                              dayNumber: int, callingDomain: str) -> str:
    """Shows a screen asking to confirm the deletion of a calendar event
    """
    nickname = getNicknameFromActor(path)
    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    domain, port = getDomainFromActor(actor)
    messageId = actor + '/statuses/' + postId

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
            '<center><h1>' + postTime + ' ' + str(year) + '/' + \
            str(monthNumber) + \
            '/' + str(dayNumber) + '</h1></center>'
        deletePostStr += '<center>'
        deletePostStr += '  <p class="followText">' + \
            translate['Delete this event'] + '</p>'

        postActor = getAltPath(actor, domainFull, callingDomain)
        deletePostStr += \
            '  <form method="POST" action="' + postActor + '/rmpost">\n'
        deletePostStr += '    <input type="hidden" name="year" value="' + \
            str(year) + '">\n'
        deletePostStr += '    <input type="hidden" name="month" value="' + \
            str(monthNumber) + '">\n'
        deletePostStr += '    <input type="hidden" name="day" value="' + \
            str(dayNumber) + '">\n'
        deletePostStr += \
            '    <input type="hidden" name="pageNumber" value="1">\n'
        deletePostStr += \
            '    <input type="hidden" name="messageId" value="' + \
            messageId + '">\n'
        deletePostStr += \
            '    <button type="submit" class="button" name="submitYes">' + \
            translate['Yes'] + '</button>\n'
        deletePostStr += \
            '    <a href="' + actor + '/calendar?year=' + \
            str(year) + '?month=' + \
            str(monthNumber) + '"><button class="button">' + \
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


def htmlPersonOptions(cssCache: {}, translate: {}, baseDir: str,
                      domain: str, domainFull: str,
                      originPathStr: str,
                      optionsActor: str,
                      optionsProfileUrl: str,
                      optionsLink: str,
                      pageNumber: int,
                      donateUrl: str,
                      xmppAddress: str,
                      matrixAddress: str,
                      ssbAddress: str,
                      blogAddress: str,
                      toxAddress: str,
                      PGPpubKey: str,
                      PGPfingerprint: str,
                      emailAddress) -> str:
    """Show options for a person: view/follow/block/report
    """
    optionsDomain, optionsPort = getDomainFromActor(optionsActor)
    optionsDomainFull = optionsDomain
    if optionsPort:
        if optionsPort != 80 and optionsPort != 443:
            optionsDomainFull = optionsDomain + ':' + str(optionsPort)

    if os.path.isfile(baseDir + '/accounts/options-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/options-background.jpg'):
            copyfile(baseDir + '/accounts/options-background.jpg',
                     baseDir + '/accounts/options-background.jpg')

    followStr = 'Follow'
    blockStr = 'Block'
    nickname = None
    optionsNickname = None
    if originPathStr.startswith('/users/'):
        nickname = originPathStr.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
        followerDomain, followerPort = getDomainFromActor(optionsActor)
        if isFollowingActor(baseDir, nickname, domain, optionsActor):
            followStr = 'Unfollow'

        optionsNickname = getNicknameFromActor(optionsActor)
        optionsDomainFull = optionsDomain
        if optionsPort:
            if optionsPort != 80 and optionsPort != 443:
                optionsDomainFull = optionsDomain + ':' + str(optionsPort)
        if isBlocked(baseDir, nickname, domain,
                     optionsNickname, optionsDomainFull):
            blockStr = 'Block'

    optionsLinkStr = ''
    if optionsLink:
        optionsLinkStr = \
            '    <input type="hidden" name="postUrl" value="' + \
            optionsLink + '">\n'
    cssFilename = baseDir + '/epicyon-options.css'
    if os.path.isfile(baseDir + '/options.css'):
        cssFilename = baseDir + '/options.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if profileStyle:
        profileStyle = \
            profileStyle.replace('--follow-text-entry-width: 90%;',
                                 '--follow-text-entry-width: 20%;')

    if not os.path.isfile(baseDir + '/accounts/' +
                          'options-background.jpg'):
        profileStyle = \
            profileStyle.replace('background-image: ' +
                                 'url("options-background.jpg");',
                                 'background-image: none;')

    # To snooze, or not to snooze? That is the question
    snoozeButtonStr = 'Snooze'
    if nickname:
        if isPersonSnoozed(baseDir, nickname, domain, optionsActor):
            snoozeButtonStr = 'Unsnooze'

    donateStr = ''
    if donateUrl:
        donateStr = \
            '    <a href="' + donateUrl + \
            '"><button class="button" name="submitDonate">' + \
            translate['Donate'] + '</button></a>\n'

    optionsStr = htmlHeader(cssFilename, profileStyle)
    optionsStr += '<br><br>\n'
    optionsStr += '<div class="options">\n'
    optionsStr += '  <div class="optionsAvatar">\n'
    optionsStr += '  <center>\n'
    optionsStr += '  <a href="' + optionsActor + '">\n'
    optionsStr += '  <img loading="lazy" src="' + optionsProfileUrl + \
        '"/></a>\n'
    handle = getNicknameFromActor(optionsActor) + '@' + optionsDomain
    optionsStr += \
        '  <p class="optionsText">' + translate['Options for'] + \
        ' @' + handle + '</p>\n'
    if emailAddress:
        optionsStr += \
            '<p class="imText">' + translate['Email'] + \
            ': <a href="mailto:' + \
            emailAddress + '">' + emailAddress + '</a></p>\n'
    if xmppAddress:
        optionsStr += \
            '<p class="imText">' + translate['XMPP'] + \
            ': <a href="xmpp:' + xmppAddress + '">' + \
            xmppAddress + '</a></p>\n'
    if matrixAddress:
        optionsStr += \
            '<p class="imText">' + translate['Matrix'] + ': ' + \
            matrixAddress + '</p>\n'
    if ssbAddress:
        optionsStr += \
            '<p class="imText">SSB: ' + ssbAddress + '</p>\n'
    if blogAddress:
        optionsStr += \
            '<p class="imText">Blog: <a href="' + blogAddress + '">' + \
            blogAddress + '</a></p>\n'
    if toxAddress:
        optionsStr += \
            '<p class="imText">Tox: ' + toxAddress + '</p>\n'
    if PGPfingerprint:
        optionsStr += '<p class="pgp">PGP: ' + \
            PGPfingerprint.replace('\n', '<br>') + '</p>\n'
    if PGPpubKey:
        optionsStr += '<p class="pgp">' + \
            PGPpubKey.replace('\n', '<br>') + '</p>\n'
    optionsStr += '  <form method="POST" action="' + \
        originPathStr + '/personoptions">\n'
    optionsStr += '    <input type="hidden" name="pageNumber" value="' + \
        str(pageNumber) + '">\n'
    optionsStr += '    <input type="hidden" name="actor" value="' + \
        optionsActor + '">\n'
    optionsStr += '    <input type="hidden" name="avatarUrl" value="' + \
        optionsProfileUrl + '">\n'
    if optionsNickname:
        handle = optionsNickname + '@' + optionsDomainFull
        petname = getPetName(baseDir, nickname, domain, handle)
        optionsStr += \
            '    ' + translate['Petname'] + ': \n' + \
            '    <input type="text" name="optionpetname" value="' + \
            petname + '">\n' \
            '    <button type="submit" class="buttonsmall" ' + \
            'name="submitPetname">' + \
            translate['Submit'] + '</button><br>\n'

    # checkbox for receiving calendar events
    if isFollowingActor(baseDir, nickname, domain, optionsActor):
        checkboxStr = \
            '    <input type="checkbox" ' + \
            'class="profilecheckbox" name="onCalendar" checked> ' + \
            translate['Receive calendar events from this account'] + \
            '\n    <button type="submit" class="buttonsmall" ' + \
            'name="submitOnCalendar">' + \
            translate['Submit'] + '</button><br>\n'
        if not receivingCalendarEvents(baseDir, nickname, domain,
                                       optionsNickname, optionsDomainFull):
            checkboxStr = checkboxStr.replace(' checked>', '>')
        optionsStr += checkboxStr

    # checkbox for permission to post to newswire
    if optionsDomainFull == domainFull:
        if isModerator(baseDir, nickname) and \
           not isModerator(baseDir, optionsNickname):
            newswireBlockedFilename = \
                baseDir + '/accounts/' + \
                optionsNickname + '@' + optionsDomain + '/.nonewswire'
            checkboxStr = \
                '    <input type="checkbox" ' + \
                'class="profilecheckbox" name="postsToNews" checked> ' + \
                translate['Allow news posts'] + \
                '\n    <button type="submit" class="buttonsmall" ' + \
                'name="submitPostToNews">' + \
                translate['Submit'] + '</button><br>\n'
            if os.path.isfile(newswireBlockedFilename):
                checkboxStr = checkboxStr.replace(' checked>', '>')
            optionsStr += checkboxStr

    optionsStr += optionsLinkStr
    optionsStr += \
        '    <a href="/"><button type="button" class="buttonIcon" ' + \
        'name="submitBack">' + translate['Go Back'] + '</button></a>'
    optionsStr += \
        '    <button type="submit" class="button" name="submitView">' + \
        translate['View'] + '</button>'
    optionsStr += donateStr
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        followStr + '">' + translate[followStr] + '</button>'
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        blockStr + '">' + translate[blockStr] + '</button>'
    optionsStr += \
        '    <button type="submit" class="button" name="submitDM">' + \
        translate['DM'] + '</button>'
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        snoozeButtonStr + '">' + translate[snoozeButtonStr] + '</button>'
    optionsStr += \
        '    <button type="submit" class="button" name="submitReport">' + \
        translate['Report'] + '</button>'

    personNotes = ''
    personNotesFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + \
        '/notes/' + handle + '.txt'
    if os.path.isfile(personNotesFilename):
        with open(personNotesFilename, 'r') as fp:
            personNotes = fp.read()

    optionsStr += \
        '    <br><br>' + translate['Notes'] + ': \n'
    optionsStr += '    <button type="submit" class="buttonsmall" ' + \
        'name="submitPersonNotes">' + \
        translate['Submit'] + '</button><br>\n'
    optionsStr += \
        '    <textarea id="message" ' + \
        'name="optionnotes" style="height:400px">' + \
        personNotes + '</textarea>\n'

    optionsStr += '  </form>\n'
    optionsStr += '</center>\n'
    optionsStr += '</div>\n'
    optionsStr += '</div>\n'
    optionsStr += htmlFooter()
    return optionsStr


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


def htmlCalendarDay(cssCache: {}, translate: {},
                    baseDir: str, path: str,
                    year: int, monthNumber: int, dayNumber: int,
                    nickname: str, domain: str, dayEvents: [],
                    monthName: str, actor: str) -> str:
    """Show a day within the calendar
    """
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain
    calendarFile = accountDir + '/.newCalendar'
    if os.path.isfile(calendarFile):
        os.remove(calendarFile)

    cssFilename = baseDir + '/epicyon-calendar.css'
    if os.path.isfile(baseDir + '/calendar.css'):
        cssFilename = baseDir + '/calendar.css'

    calendarStyle = getCSS(baseDir, cssFilename, cssCache)

    calActor = actor
    if '/users/' in actor:
        calActor = '/users/' + actor.split('/users/')[1]

    calendarStr = htmlHeader(cssFilename, calendarStyle)
    calendarStr += '<main><table class="calendar">\n'
    calendarStr += '<caption class="calendar__banner--month">\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(year) + \
        '?month=' + str(monthNumber) + '">\n'
    calendarStr += \
        '  <h1>' + str(dayNumber) + ' ' + monthName + \
        '</h1></a><br><span class="year">' + str(year) + '</span>\n'
    calendarStr += '</caption>\n'
    calendarStr += '<tbody>\n'

    iconsDir = getIconsDir(baseDir)

    if dayEvents:
        for eventPost in dayEvents:
            eventTime = None
            eventDescription = None
            eventPlace = None
            postId = None
            # get the time place and description
            for ev in eventPost:
                if ev['type'] == 'Event':
                    if ev.get('postId'):
                        postId = ev['postId']
                    if ev.get('startTime'):
                        eventDate = \
                            datetime.strptime(ev['startTime'],
                                              "%Y-%m-%dT%H:%M:%S%z")
                        eventTime = eventDate.strftime("%H:%M").strip()
                    if ev.get('name'):
                        eventDescription = ev['name'].strip()
                elif ev['type'] == 'Place':
                    if ev.get('name'):
                        eventPlace = ev['name']

            deleteButtonStr = ''
            if postId:
                deleteButtonStr = \
                    '<td class="calendar__day__icons"><a href="' + calActor + \
                    '/eventdelete?id=' + postId + '?year=' + str(year) + \
                    '?month=' + str(monthNumber) + '?day=' + str(dayNumber) + \
                    '?time=' + eventTime + \
                    '">\n<img class="calendardayicon" loading="lazy" alt="' + \
                    translate['Delete this event'] + ' |" title="' + \
                    translate['Delete this event'] + '" src="/' + \
                    iconsDir + '/delete.png" /></a></td>\n'

            if eventTime and eventDescription and eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="calendar__day__event">' + \
                    '<span class="place">' + \
                    eventPlace + '</span><br>' + eventDescription + \
                    '</td>' + deleteButtonStr + '</tr>\n'
            elif eventTime and eventDescription and not eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="calendar__day__event">' + \
                    eventDescription + '</td>' + deleteButtonStr + '</tr>\n'
            elif not eventTime and eventDescription and not eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time">' + \
                    '</td><td class="calendar__day__event">' + \
                    eventDescription + '</td>' + deleteButtonStr + '</tr>\n'
            elif not eventTime and eventDescription and eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time"></td>' + \
                    '<td class="calendar__day__event"><span class="place">' + \
                    eventPlace + '</span><br>' + eventDescription + \
                    '</td>' + deleteButtonStr + '</tr>\n'
            elif eventTime and not eventDescription and eventPlace:
                calendarStr += \
                    '<tr><td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="calendar__day__event">' + \
                    '<span class="place">' + \
                    eventPlace + '</span></td>' + \
                    deleteButtonStr + '</tr>\n'

    calendarStr += '</tbody>\n'
    calendarStr += '</table></main>\n'
    calendarStr += htmlFooter()

    return calendarStr


def htmlCalendar(cssCache: {}, translate: {},
                 baseDir: str, path: str,
                 httpPrefix: str, domainFull: str) -> str:
    """Show the calendar for a person
    """
    iconsDir = getIconsDir(baseDir)
    domain = domainFull
    if ':' in domainFull:
        domain = domainFull.split(':')[0]

    monthNumber = 0
    dayNumber = None
    year = 1970
    actor = httpPrefix + '://' + domainFull + path.replace('/calendar', '')
    if '?' in actor:
        first = True
        for p in actor.split('?'):
            if not first:
                if '=' in p:
                    if p.split('=')[0] == 'year':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            year = int(numStr)
                    elif p.split('=')[0] == 'month':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            monthNumber = int(numStr)
                    elif p.split('=')[0] == 'day':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            dayNumber = int(numStr)
            first = False
        actor = actor.split('?')[0]

    currDate = datetime.now()
    if year == 1970 and monthNumber == 0:
        year = currDate.year
        monthNumber = currDate.month

    nickname = getNicknameFromActor(actor)

    if os.path.isfile(baseDir + '/img/calendar-background.png'):
        if not os.path.isfile(baseDir + '/accounts/calendar-background.png'):
            copyfile(baseDir + '/img/calendar-background.png',
                     baseDir + '/accounts/calendar-background.png')

    months = ('January', 'February', 'March', 'April',
              'May', 'June', 'July', 'August', 'September',
              'October', 'November', 'December')
    monthName = translate[months[monthNumber - 1]]

    if dayNumber:
        dayEvents = None
        events = \
            getTodaysEvents(baseDir, nickname, domain,
                            year, monthNumber, dayNumber)
        if events:
            if events.get(str(dayNumber)):
                dayEvents = events[str(dayNumber)]
        return htmlCalendarDay(cssCache, translate, baseDir, path,
                               year, monthNumber, dayNumber,
                               nickname, domain, dayEvents,
                               monthName, actor)

    events = \
        getCalendarEvents(baseDir, nickname, domain, year, monthNumber)

    prevYear = year
    prevMonthNumber = monthNumber - 1
    if prevMonthNumber < 1:
        prevMonthNumber = 12
        prevYear = year - 1

    nextYear = year
    nextMonthNumber = monthNumber + 1
    if nextMonthNumber > 12:
        nextMonthNumber = 1
        nextYear = year + 1

    print('Calendar year=' + str(year) + ' month=' + str(monthNumber) +
          ' ' + str(weekDayOfMonthStart(monthNumber, year)))

    if monthNumber < 12:
        daysInMonth = \
            (date(year, monthNumber + 1, 1) - date(year, monthNumber, 1)).days
    else:
        daysInMonth = \
            (date(year + 1, 1, 1) - date(year, monthNumber, 1)).days
    # print('daysInMonth ' + str(monthNumber) + ': ' + str(daysInMonth))

    cssFilename = baseDir + '/epicyon-calendar.css'
    if os.path.isfile(baseDir + '/calendar.css'):
        cssFilename = baseDir + '/calendar.css'

    calendarStyle = getCSS(baseDir, cssFilename, cssCache)

    calActor = actor
    if '/users/' in actor:
        calActor = '/users/' + actor.split('/users/')[1]

    calendarStr = htmlHeader(cssFilename, calendarStyle)
    calendarStr += '<main><table class="calendar">\n'
    calendarStr += '<caption class="calendar__banner--month">\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(prevYear) + \
        '?month=' + str(prevMonthNumber) + '">'
    calendarStr += \
        '  <img loading="lazy" alt="' + translate['Previous month'] + \
        '" title="' + translate['Previous month'] + '" src="/' + iconsDir + \
        '/prev.png" class="buttonprev"/></a>\n'
    calendarStr += '  <a href="' + calActor + '/inbox" title="'
    calendarStr += translate['Switch to timeline view'] + '">'
    calendarStr += '  <h1>' + monthName + '</h1></a>\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(nextYear) + \
        '?month=' + str(nextMonthNumber) + '">'
    calendarStr += \
        '  <img loading="lazy" alt="' + translate['Next month'] + \
        '" title="' + translate['Next month'] + '" src="/' + iconsDir + \
        '/prev.png" class="buttonnext"/></a>\n'
    calendarStr += '</caption>\n'
    calendarStr += '<thead>\n'
    calendarStr += '<tr>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Sun'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Mon'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Tue'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Wed'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Thu'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Fri'] + '</th>\n'
    calendarStr += '  <th class="calendar__day__header">' + \
        translate['Sat'] + '</th>\n'
    calendarStr += '</tr>\n'
    calendarStr += '</thead>\n'
    calendarStr += '<tbody>\n'

    dayOfMonth = 0
    dow = weekDayOfMonthStart(monthNumber, year)
    for weekOfMonth in range(1, 7):
        if dayOfMonth == daysInMonth:
            continue
        calendarStr += '  <tr>\n'
        for dayNumber in range(1, 8):
            if (weekOfMonth > 1 and dayOfMonth < daysInMonth) or \
               (weekOfMonth == 1 and dayNumber >= dow):
                dayOfMonth += 1

                isToday = False
                if year == currDate.year:
                    if currDate.month == monthNumber:
                        if dayOfMonth == currDate.day:
                            isToday = True
                if events.get(str(dayOfMonth)):
                    url = calActor + '/calendar?year=' + \
                        str(year) + '?month=' + \
                        str(monthNumber) + '?day=' + str(dayOfMonth)
                    dayLink = '<a href="' + url + '">' + \
                        str(dayOfMonth) + '</a>'
                    # there are events for this day
                    if not isToday:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-event="">' + \
                            dayLink + '</td>\n'
                    else:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-today-event="">' + \
                            dayLink + '</td>\n'
                else:
                    # No events today
                    if not isToday:
                        calendarStr += \
                            '    <td class="calendar__day__cell">' + \
                            str(dayOfMonth) + '</td>\n'
                    else:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-today="">' + str(dayOfMonth) + '</td>\n'
            else:
                calendarStr += '    <td class="calendar__day__cell"></td>\n'
        calendarStr += '  </tr>\n'

    calendarStr += '</tbody>\n'
    calendarStr += '</table></main>\n'
    calendarStr += htmlFooter()
    return calendarStr


def htmlProfileAfterSearch(cssCache: {},
                           recentPostsCache: {}, maxRecentPosts: int,
                           translate: {},
                           baseDir: str, path: str, httpPrefix: str,
                           nickname: str, domain: str, port: int,
                           profileHandle: str,
                           session, cachedWebfingers: {}, personCache: {},
                           debug: bool, projectVersion: str,
                           YTReplacementDomain: str,
                           showPublishedDateOnly: bool) -> str:
    """Show a profile page after a search for a fediverse address
    """
    if '/users/' in profileHandle or \
       '/accounts/' in profileHandle or \
       '/channel/' in profileHandle or \
       '/profile/' in profileHandle or \
       '/@' in profileHandle:
        searchNickname = getNicknameFromActor(profileHandle)
        searchDomain, searchPort = getDomainFromActor(profileHandle)
    else:
        if '@' not in profileHandle:
            print('DEBUG: no @ in ' + profileHandle)
            return None
        if profileHandle.startswith('@'):
            profileHandle = profileHandle[1:]
        if '@' not in profileHandle:
            print('DEBUG: no @ in ' + profileHandle)
            return None
        searchNickname = profileHandle.split('@')[0]
        searchDomain = profileHandle.split('@')[1]
        searchPort = None
        if ':' in searchDomain:
            searchPortStr = searchDomain.split(':')[1]
            if searchPortStr.isdigit():
                searchPort = int(searchPortStr)
            searchDomain = searchDomain.split(':')[0]
    if searchPort:
        print('DEBUG: Search for handle ' +
              str(searchNickname) + '@' + str(searchDomain) + ':' +
              str(searchPort))
    else:
        print('DEBUG: Search for handle ' +
              str(searchNickname) + '@' + str(searchDomain))
    if not searchNickname:
        print('DEBUG: No nickname found in ' + profileHandle)
        return None
    if not searchDomain:
        print('DEBUG: No domain found in ' + profileHandle)
        return None

    searchDomainFull = searchDomain
    if searchPort:
        if searchPort != 80 and searchPort != 443:
            if ':' not in searchDomain:
                searchDomainFull = searchDomain + ':' + str(searchPort)

    profileStr = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if profileStyle:
        wf = \
            webfingerHandle(session,
                            searchNickname + '@' + searchDomainFull,
                            httpPrefix, cachedWebfingers,
                            domain, projectVersion)
        if not wf:
            print('DEBUG: Unable to webfinger ' +
                  searchNickname + '@' + searchDomainFull)
            print('DEBUG: cachedWebfingers ' + str(cachedWebfingers))
            print('DEBUG: httpPrefix ' + httpPrefix)
            print('DEBUG: domain ' + domain)
            return None
        if not isinstance(wf, dict):
            print('WARN: Webfinger search for ' +
                  searchNickname + '@' + searchDomainFull +
                  ' did not return a dict. ' +
                  str(wf))
            return None

        personUrl = None
        if wf.get('errors'):
            personUrl = httpPrefix + '://' + \
                searchDomainFull + '/users/' + searchNickname

        profileStr = 'https://www.w3.org/ns/activitystreams'
        asHeader = {
            'Accept': 'application/activity+json; profile="' + profileStr + '"'
        }
        if not personUrl:
            personUrl = getUserUrl(wf)
        if not personUrl:
            # try single user instance
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
            personUrl = httpPrefix + '://' + searchDomainFull
        profileJson = \
            getJson(session, personUrl, asHeader, None,
                    projectVersion, httpPrefix, domain)
        if not profileJson:
            asHeader = {
                'Accept': 'application/ld+json; profile="' + profileStr + '"'
            }
            profileJson = \
                getJson(session, personUrl, asHeader, None,
                        projectVersion, httpPrefix, domain)
        if not profileJson:
            print('DEBUG: No actor returned from ' + personUrl)
            return None
        avatarUrl = ''
        if profileJson.get('icon'):
            if profileJson['icon'].get('url'):
                avatarUrl = profileJson['icon']['url']
        if not avatarUrl:
            avatarUrl = getPersonAvatarUrl(baseDir, personUrl,
                                           personCache, True)
        displayName = searchNickname
        if profileJson.get('name'):
            displayName = profileJson['name']
        profileDescription = ''
        if profileJson.get('summary'):
            profileDescription = profileJson['summary']
        outboxUrl = None
        if not profileJson.get('outbox'):
            if debug:
                pprint(profileJson)
                print('DEBUG: No outbox found')
            return None
        outboxUrl = profileJson['outbox']
        profileBackgroundImage = ''
        if profileJson.get('image'):
            if profileJson['image'].get('url'):
                profileBackgroundImage = profileJson['image']['url']

        profileStyle = profileStyle.replace('image.png',
                                            profileBackgroundImage)
        if httpPrefix != 'https':
            profileStyle = profileStyle.replace('https://',
                                                httpPrefix + '://')
        # url to return to
        backUrl = path
        if not backUrl.endswith('/inbox'):
            backUrl += '/inbox'

        profileDescriptionShort = profileDescription
        if '\n' in profileDescription:
            if len(profileDescription.split('\n')) > 2:
                profileDescriptionShort = ''
        else:
            if '<br>' in profileDescription:
                if len(profileDescription.split('<br>')) > 2:
                    profileDescriptionShort = ''
        # keep the profile description short
        if len(profileDescriptionShort) > 256:
            profileDescriptionShort = ''
        # remove formatting from profile description used on title
        avatarDescription = ''
        if profileJson.get('summary'):
            if isinstance(profileJson['summary'], str):
                avatarDescription = \
                    profileJson['summary'].replace('<br>', '\n')
                avatarDescription = avatarDescription.replace('<p>', '')
                avatarDescription = avatarDescription.replace('</p>', '')
                if '<' in avatarDescription:
                    avatarDescription = removeHtml(avatarDescription)
        profileStr = ' <div class="hero-image">\n'
        profileStr += '  <div class="hero-text">\n'
        if avatarUrl:
            profileStr += \
                '    <img loading="lazy" src="' + avatarUrl + \
                '" alt="' + avatarDescription + '" title="' + \
                avatarDescription + '" class="title">\n'
        profileStr += '    <h1>' + displayName + '</h1>\n'
        profileStr += '    <p><b>@' + searchNickname + '@' + \
            searchDomainFull + '</b></p>\n'
        profileStr += '    <p>' + profileDescriptionShort + '</p>\n'
        profileStr += '  </div>\n'
        profileStr += '</div>\n'
        profileStr += '<div class="container">\n'
        profileStr += '  <form method="POST" action="' + \
            backUrl + '/followconfirm">\n'
        profileStr += '    <center>\n'
        profileStr += \
            '      <input type="hidden" name="actor" value="' + \
            personUrl + '">\n'
        profileStr += \
            '      <a href="' + backUrl + '"><button class="button">' + \
            translate['Go Back'] + '</button></a>\n'
        profileStr += \
            '      <button type="submit" class="button" name="submitYes">' + \
            translate['Follow'] + '</button>\n'
        profileStr += \
            '      <button type="submit" class="button" name="submitView">' + \
            translate['View'] + '</button>\n'
        profileStr += '    </center>\n'
        profileStr += '  </form>\n'
        profileStr += '</div>\n'

        iconsDir = getIconsDir(baseDir)
        i = 0
        for item in parseUserFeed(session, outboxUrl, asHeader,
                                  projectVersion, httpPrefix, domain):
            if not item.get('type'):
                continue
            if item['type'] != 'Create' and item['type'] != 'Announce':
                continue
            if not item.get('object'):
                continue
            profileStr += \
                individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                                     iconsDir, translate, None, baseDir,
                                     session, cachedWebfingers, personCache,
                                     nickname, domain, port,
                                     item, avatarUrl, False, False,
                                     httpPrefix, projectVersion, 'inbox',
                                     YTReplacementDomain,
                                     showPublishedDateOnly,
                                     False, False, False, False, False)
            i += 1
            if i >= 20:
                break

    return htmlHeader(cssFilename, profileStyle) + profileStr + htmlFooter()
