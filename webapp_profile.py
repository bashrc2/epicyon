__filename__ = "webapp_profile.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from pprint import pprint
from utils import getLockedAccount
from utils import hasUsersPath
from utils import getFullDomain
from utils import isDormant
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import isSystemAccount
from utils import removeHtml
from utils import loadJson
from utils import getConfigParam
from utils import getImageFormats
from skills import getSkills
from theme import getThemesList
from person import personBoxJson
from webfinger import webfingerHandle
from session import getJson
from posts import parseUserFeed
from posts import getUserUrl
from posts import getPersonBox
from donate import getDonationUrl
from xmpp import getXmppAddress
from matrix import getMatrixAddress
from ssb import getSSBAddress
from pgp import getEmailAddress
from pgp import getPGPfingerprint
from pgp import getPGPpubKey
from tox import getToxAddress
from briar import getBriarAddress
from jami import getJamiAddress
from filters import isFiltered
from follow import isFollowerOfPerson
from webapp_frontscreen import htmlFrontScreen
from webapp_utils import scheduledPostsExist
from webapp_utils import getPersonAvatarUrl
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import addEmojiToDisplayName
from webapp_utils import getBannerFile
from webapp_utils import htmlPostSeparator
from webapp_utils import getBlogAddress
from webapp_post import individualPostAsHtml
from webapp_timeline import htmlIndividualShare


def htmlProfileAfterSearch(cssCache: {},
                           recentPostsCache: {}, maxRecentPosts: int,
                           translate: {},
                           baseDir: str, path: str, httpPrefix: str,
                           nickname: str, domain: str, port: int,
                           profileHandle: str,
                           session, cachedWebfingers: {}, personCache: {},
                           debug: bool, projectVersion: str,
                           YTReplacementDomain: str,
                           showPublishedDateOnly: bool,
                           defaultTimeline: str,
                           peertubeInstances: [],
                           allowLocalNetworkAccess: bool) -> str:
    """Show a profile page after a search for a fediverse address
    """
    if hasUsersPath(profileHandle) or '/@' in profileHandle:
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

    searchDomainFull = getFullDomain(searchDomain, searchPort)

    profileStr = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

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

    lockedAccount = getLockedAccount(profileJson)
    if lockedAccount:
        displayName += '🔒'
    movedTo = ''
    if profileJson.get('movedTo'):
        movedTo = profileJson['movedTo']
        displayName += ' ⌂'

    followsYou = \
        isFollowerOfPerson(baseDir,
                           nickname, domain,
                           searchNickname,
                           searchDomainFull)

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

    # profileBackgroundImage = ''
    # if profileJson.get('image'):
    #     if profileJson['image'].get('url'):
    #         profileBackgroundImage = profileJson['image']['url']

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

    imageUrl = ''
    if profileJson.get('image'):
        if profileJson['image'].get('url'):
            imageUrl = profileJson['image']['url']

    alsoKnownAs = None
    if profileJson.get('alsoKnownAs'):
        alsoKnownAs = profileJson['alsoKnownAs']

    profileStr = \
        _getProfileHeaderAfterSearch(baseDir,
                                     nickname, defaultTimeline,
                                     searchNickname,
                                     searchDomainFull,
                                     translate,
                                     displayName, followsYou,
                                     profileDescriptionShort,
                                     avatarUrl, imageUrl,
                                     movedTo, profileJson['id'],
                                     alsoKnownAs)

    domainFull = getFullDomain(domain, port)

    followIsPermitted = True
    if searchNickname == 'news' and searchDomainFull == domainFull:
        # currently the news actor is not something you can follow
        followIsPermitted = False
    elif searchNickname == nickname and searchDomainFull == domainFull:
        # don't follow yourself!
        followIsPermitted = False

    if followIsPermitted:
        profileStr += '<div class="container">\n'
        profileStr += '  <form method="POST" action="' + \
            backUrl + '/followconfirm">\n'
        profileStr += '    <center>\n'
        profileStr += \
            '      <input type="hidden" name="actor" value="' + \
            personUrl + '">\n'
        profileStr += \
            '      <button type="submit" class="button" name="submitYes">' + \
            translate['Follow'] + '</button>\n'
        profileStr += \
            '      <button type="submit" class="button" name="submitView">' + \
            translate['View'] + '</button>\n'
        profileStr += '    </center>\n'
        profileStr += '  </form>\n'
        profileStr += '</div>\n'

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
                                 translate, None, baseDir,
                                 session, cachedWebfingers, personCache,
                                 nickname, domain, port,
                                 item, avatarUrl, False, False,
                                 httpPrefix, projectVersion, 'inbox',
                                 YTReplacementDomain,
                                 showPublishedDateOnly,
                                 peertubeInstances, allowLocalNetworkAccess,
                                 False, False, False, False, False)
        i += 1
        if i >= 20:
            break

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    return htmlHeaderWithExternalStyle(cssFilename, instanceTitle) + \
        profileStr + htmlFooter()


def _getProfileHeader(baseDir: str, httpPrefix: str,
                      nickname: str, domain: str,
                      domainFull: str, translate: {},
                      defaultTimeline: str,
                      displayName: str,
                      avatarDescription: str,
                      profileDescriptionShort: str,
                      loginButton: str, avatarUrl: str,
                      theme: str, movedTo: str,
                      alsoKnownAs: [],
                      pinnedContent) -> str:
    """The header of the profile screen, containing background
    image and avatar
    """
    htmlStr = '\n\n    <figure class="profileHeader">\n'
    htmlStr += '      <a href="/users/' + \
        nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '">\n'
    htmlStr += '        <img class="profileBackground" ' + \
        'alt="" ' + \
        'src="/users/' + nickname + '/image_' + theme + '.png" /></a>\n'
    htmlStr += '      <figcaption>\n'
    htmlStr += \
        '        <a href="/users/' + \
        nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '">\n' + \
        '          <img loading="lazy" src="' + avatarUrl + '" ' + \
        'alt=""  class="title"></a>\n'
    htmlStr += '        <h1>' + displayName + '</h1>\n'
    htmlStr += \
        '    <p><b>@' + nickname + '@' + domainFull + '</b><br>\n'
    if movedTo:
        newNickname = getNicknameFromActor(movedTo)
        newDomain, newPort = getDomainFromActor(movedTo)
        newDomainFull = getFullDomain(newDomain, newPort)
        if newNickname and newDomain:
            htmlStr += \
                '    <p>' + translate['New account'] + ': ' + \
                '<a href="' + movedTo + '">@' + \
                newNickname + '@' + newDomainFull + '</a><br>\n'
    elif alsoKnownAs:
        otherAccountsHtml = \
            '    <p>' + translate['Other accounts'] + ': '

        actor = httpPrefix + '://' + domainFull + '/users/' + nickname
        ctr = 0
        if isinstance(alsoKnownAs, list):
            for altActor in alsoKnownAs:
                if altActor == actor:
                    continue
                if ctr > 0:
                    otherAccountsHtml += ' '
                ctr += 1
                altDomain, altPort = getDomainFromActor(altActor)
                otherAccountsHtml += \
                    '<a href="' + altActor + '">' + altDomain + '</a>'
        elif isinstance(alsoKnownAs, str):
            if alsoKnownAs != actor:
                ctr += 1
                altDomain, altPort = getDomainFromActor(alsoKnownAs)
                otherAccountsHtml += \
                    '<a href="' + alsoKnownAs + '">' + altDomain + '</a>'
        otherAccountsHtml += '</p>\n'
        if ctr > 0:
            htmlStr += otherAccountsHtml
    htmlStr += \
        '    <a href="/users/' + nickname + \
        '/qrcode.png" alt="' + translate['QR Code'] + '" title="' + \
        translate['QR Code'] + '">' + \
        '<img class="qrcode" alt="' + translate['QR Code'] + \
        '" src="/icons/qrcode.png" /></a></p>\n'
    htmlStr += '        <p>' + profileDescriptionShort + '</p>\n'
    htmlStr += loginButton
    if pinnedContent:
        htmlStr += pinnedContent.replace('<p>', '<p>📎', 1)
    htmlStr += '      </figcaption>\n'
    htmlStr += '    </figure>\n\n'
    return htmlStr


def _getProfileHeaderAfterSearch(baseDir: str,
                                 nickname: str, defaultTimeline: str,
                                 searchNickname: str,
                                 searchDomainFull: str,
                                 translate: {},
                                 displayName: str,
                                 followsYou: bool,
                                 profileDescriptionShort: str,
                                 avatarUrl: str, imageUrl: str,
                                 movedTo: str, actor: str,
                                 alsoKnownAs: []) -> str:
    """The header of a searched for handle, containing background
    image and avatar
    """
    htmlStr = '\n\n    <figure class="profileHeader">\n'
    htmlStr += '      <a href="/users/' + \
        nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '">\n'
    htmlStr += '        <img class="profileBackground" ' + \
        'alt="" ' + \
        'src="' + imageUrl + '" /></a>\n'
    htmlStr += '      <figcaption>\n'
    if avatarUrl:
        htmlStr += '      <a href="/users/' + \
            nickname + '/' + defaultTimeline + '" title="' + \
            translate['Switch to timeline view'] + '">\n'
        htmlStr += \
            '          <img loading="lazy" src="' + avatarUrl + '" ' + \
            'alt="" class="title"></a>\n'
    htmlStr += '        <h1>' + displayName + '</h1>\n'
    htmlStr += \
        '    <p><b>@' + searchNickname + '@' + searchDomainFull + '</b><br>\n'
    if followsYou:
        htmlStr += '        <p><b>' + translate['Follows you'] + '</b></p>\n'
    if movedTo:
        newNickname = getNicknameFromActor(movedTo)
        newDomain, newPort = getDomainFromActor(movedTo)
        newDomainFull = getFullDomain(newDomain, newPort)
        if newNickname and newDomain:
            newHandle = newNickname + '@' + newDomainFull
            htmlStr += '        <p>' + translate['New account'] + \
                ': < a href="' + movedTo + '">@' + newHandle + '</a></p>\n'
    elif alsoKnownAs:
        otherAccountshtml = \
            '        <p>' + translate['Other accounts'] + ': '

        ctr = 0
        if isinstance(alsoKnownAs, list):
            for altActor in alsoKnownAs:
                if altActor == actor:
                    continue
                if ctr > 0:
                    otherAccountshtml += ' '
                ctr += 1
                altDomain, altPort = getDomainFromActor(altActor)
                otherAccountshtml += \
                    '<a href="' + altActor + '">' + altDomain + '</a>'
        elif isinstance(alsoKnownAs, str):
            if alsoKnownAs != actor:
                ctr += 1
                altDomain, altPort = getDomainFromActor(alsoKnownAs)
                otherAccountshtml += \
                    '<a href="' + alsoKnownAs + '">' + altDomain + '</a>'

        otherAccountshtml += '</p>\n'
        if ctr > 0:
            htmlStr += otherAccountshtml

    htmlStr += '        <p>' + profileDescriptionShort + '</p>\n'
    htmlStr += '      </figcaption>\n'
    htmlStr += '    </figure>\n\n'
    return htmlStr


def htmlProfile(rssIconAtTop: bool,
                cssCache: {}, iconsAsButtons: bool,
                defaultTimeline: str,
                recentPostsCache: {}, maxRecentPosts: int,
                translate: {}, projectVersion: str,
                baseDir: str, httpPrefix: str, authorized: bool,
                profileJson: {}, selected: str,
                session, cachedWebfingers: {}, personCache: {},
                YTReplacementDomain: str,
                showPublishedDateOnly: bool,
                newswire: {}, theme: str, dormantMonths: int,
                peertubeInstances: [],
                allowLocalNetworkAccess: bool,
                extraJson=None, pageNumber=None,
                maxItemsPerPage=None) -> str:
    """Show the profile page as html
    """
    nickname = profileJson['preferredUsername']
    if not nickname:
        return ""
    if isSystemAccount(nickname):
        return htmlFrontScreen(rssIconAtTop,
                               cssCache, iconsAsButtons,
                               defaultTimeline,
                               recentPostsCache, maxRecentPosts,
                               translate, projectVersion,
                               baseDir, httpPrefix, authorized,
                               profileJson, selected,
                               session, cachedWebfingers, personCache,
                               YTReplacementDomain,
                               showPublishedDateOnly,
                               newswire, theme, extraJson,
                               allowLocalNetworkAccess,
                               pageNumber, maxItemsPerPage)

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
    briarAddress = getBriarAddress(profileJson)
    jamiAddress = getJamiAddress(profileJson)
    if donateUrl or xmppAddress or matrixAddress or \
       ssbAddress or toxAddress or briarAddress or \
       jamiAddress or PGPpubKey or \
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
        if briarAddress:
            if briarAddress.startswith('briar://'):
                donateSection += \
                    '<p><label class="toxaddr">' + \
                    briarAddress + '</label></p>\n'
            else:
                donateSection += \
                    '<p>briar://<label class="toxaddr">' + \
                    briarAddress + '</label></p>\n'
        if jamiAddress:
            donateSection += \
                '<p>Jami: <label class="toxaddr">' + \
                jamiAddress + '</label></p>\n'
        if PGPfingerprint:
            donateSection += \
                '<p class="pgp">PGP: ' + \
                PGPfingerprint.replace('\n', '<br>') + '</p>\n'
        if PGPpubKey:
            donateSection += \
                '<p class="pgp">' + PGPpubKey.replace('\n', '<br>') + '</p>\n'
        donateSection += '  </center>\n'
        donateSection += '</div>\n'

    if authorized:
        editProfileStr = \
            '<a class="imageAnchor" href="' + usersPath + '/editprofile">' + \
            '<img loading="lazy" src="/icons' + \
            '/edit.png" title="' + translate['Edit'] + \
            '" alt="| ' + translate['Edit'] + '" class="timelineicon"/></a>\n'

        logoutStr = \
            '<a class="imageAnchor" href="/logout">' + \
            '<img loading="lazy" src="/icons' + \
            '/logout.png" title="' + translate['Logout'] + \
            '" alt="| ' + translate['Logout'] + \
            '" class="timelineicon"/></a>\n'

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

    movedTo = ''
    if profileJson.get('movedTo'):
        movedTo = profileJson['movedTo']

    alsoKnownAs = None
    if profileJson.get('alsoKnownAs'):
        alsoKnownAs = profileJson['alsoKnownAs']

    avatarUrl = profileJson['icon']['url']

    # get pinned post content
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain
    pinnedFilename = accountDir + '/pinToProfile.txt'
    pinnedContent = None
    if os.path.isfile(pinnedFilename):
        with open(pinnedFilename, 'r') as pinFile:
            pinnedContent = pinFile.read()

    profileHeaderStr = \
        _getProfileHeader(baseDir, httpPrefix,
                          nickname, domain,
                          domainFull, translate,
                          defaultTimeline, displayName,
                          avatarDescription,
                          profileDescriptionShort,
                          loginButton, avatarUrl, theme,
                          movedTo, alsoKnownAs,
                          pinnedContent)

    # Links for keyboard navigation
    profileStr = \
        '<div class="transparent">' + \
        '<label class="transparent">' + \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '">' + \
        translate['Switch to timeline view'] + '</a></label> | ' + \
        '<label class="transparent">' + \
        '<a class="skip-main" href="#buttonheader">' + \
        translate['Skip to timeline'] + '</a></label>' + \
        '</div>\n'

    profileStr += profileHeaderStr + donateSection
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

    licenseStr = \
        '<a href="https://gitlab.com/bashrc2/epicyon">' + \
        '<img loading="lazy" class="license" alt="' + \
        translate['Get the source code'] + '" title="' + \
        translate['Get the source code'] + '" src="/icons/agpl.png" /></a>'

    if selected == 'posts':
        profileStr += \
            _htmlProfilePosts(recentPostsCache, maxRecentPosts,
                              translate,
                              baseDir, httpPrefix, authorized,
                              nickname, domain, port,
                              session, cachedWebfingers, personCache,
                              projectVersion,
                              YTReplacementDomain,
                              showPublishedDateOnly,
                              peertubeInstances,
                              allowLocalNetworkAccess) + licenseStr
    elif selected == 'following':
        profileStr += \
            _htmlProfileFollowing(translate, baseDir, httpPrefix,
                                  authorized, nickname,
                                  domain, port, session,
                                  cachedWebfingers, personCache, extraJson,
                                  projectVersion, ["unfollow"], selected,
                                  usersPath, pageNumber, maxItemsPerPage,
                                  dormantMonths)
    elif selected == 'followers':
        profileStr += \
            _htmlProfileFollowing(translate, baseDir, httpPrefix,
                                  authorized, nickname,
                                  domain, port, session,
                                  cachedWebfingers, personCache, extraJson,
                                  projectVersion, ["block"],
                                  selected, usersPath, pageNumber,
                                  maxItemsPerPage, dormantMonths)
    elif selected == 'roles':
        profileStr += \
            _htmlProfileRoles(translate, nickname, domainFull,
                              extraJson)
    elif selected == 'skills':
        profileStr += \
            _htmlProfileSkills(translate, nickname, domainFull, extraJson)
    elif selected == 'shares':
        profileStr += \
            _htmlProfileShares(actor, translate,
                               nickname, domainFull,
                               extraJson) + licenseStr

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    profileStr = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle) + \
        profileStr + htmlFooter()
    return profileStr


def _htmlProfilePosts(recentPostsCache: {}, maxRecentPosts: int,
                      translate: {},
                      baseDir: str, httpPrefix: str,
                      authorized: bool,
                      nickname: str, domain: str, port: int,
                      session, cachedWebfingers: {}, personCache: {},
                      projectVersion: str,
                      YTReplacementDomain: str,
                      showPublishedDateOnly: bool,
                      peertubeInstances: [],
                      allowLocalNetworkAccess: bool) -> str:
    """Shows posts on the profile screen
    These should only be public posts
    """
    separatorStr = htmlPostSeparator(baseDir, None)
    profileStr = ''
    maxItems = 4
    ctr = 0
    currPage = 1
    boxName = 'outbox'
    while ctr < maxItems and currPage < 4:
        outboxFeedPathStr = \
            '/users/' + nickname + '/' + boxName + '?page=' + \
            str(currPage)
        outboxFeed = \
            personBoxJson({}, session, baseDir, domain,
                          port,
                          outboxFeedPathStr,
                          httpPrefix,
                          10, boxName,
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
                                         baseDir, session, cachedWebfingers,
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


def _htmlProfileFollowing(translate: {}, baseDir: str, httpPrefix: str,
                          authorized: bool,
                          nickname: str, domain: str, port: int,
                          session, cachedWebfingers: {}, personCache: {},
                          followingJson: {}, projectVersion: str,
                          buttons: [],
                          feedName: str, actor: str,
                          pageNumber: int,
                          maxItemsPerPage: int,
                          dormantMonths: int) -> str:
    """Shows following on the profile screen
    """
    profileStr = ''

    if authorized and pageNumber:
        if authorized and pageNumber > 1:
            # page up arrow
            profileStr += \
                '  <center>\n' + \
                '    <a href="' + actor + '/' + feedName + \
                '?page=' + str(pageNumber - 1) + '#buttonheader' + \
                '"><img loading="lazy" class="pageicon" src="/' + \
                'icons/pageup.png" title="' + \
                translate['Page up'] + '" alt="' + \
                translate['Page up'] + '"></a>\n' + \
                '  </center>\n'

    for followingActor in followingJson['orderedItems']:
        # is this a dormant followed account?
        dormant = False
        if authorized and feedName == 'following':
            dormant = \
                isDormant(baseDir, nickname, domain, followingActor,
                          dormantMonths)

        profileStr += \
            _individualFollowAsHtml(translate, baseDir, session,
                                    cachedWebfingers, personCache,
                                    domain, followingActor,
                                    authorized, nickname,
                                    httpPrefix, projectVersion, dormant,
                                    buttons)

    if authorized and maxItemsPerPage and pageNumber:
        if len(followingJson['orderedItems']) >= maxItemsPerPage:
            # page down arrow
            profileStr += \
                '  <center>\n' + \
                '    <a href="' + actor + '/' + feedName + \
                '?page=' + str(pageNumber + 1) + '#buttonheader' + \
                '"><img loading="lazy" class="pageicon" src="/' + \
                'icons/pagedown.png" title="' + \
                translate['Page down'] + '" alt="' + \
                translate['Page down'] + '"></a>\n' + \
                '  </center>\n'
    return profileStr


def _htmlProfileRoles(translate: {}, nickname: str, domain: str,
                      rolesJson: {}) -> str:
    """Shows roles on the profile screen
    """
    profileStr = ''
    for project, rolesList in rolesJson.items():
        profileStr += \
            '<div class="roles">\n<h2>' + project + \
            '</h2>\n<div class="roles-inner">\n'
        for role in rolesList:
            if translate.get(role):
                profileStr += '<h3>' + translate[role] + '</h3>\n'
            else:
                profileStr += '<h3>' + role + '</h3>\n'
        profileStr += '</div></div>\n'
    if len(profileStr) == 0:
        profileStr += \
            '<p>@' + nickname + '@' + domain + ' has no roles assigned</p>\n'
    else:
        profileStr = '<div>' + profileStr + '</div>\n'
    return profileStr


def _htmlProfileSkills(translate: {}, nickname: str, domain: str,
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


def _htmlProfileShares(actor: str, translate: {},
                       nickname: str, domain: str, sharesJson: {}) -> str:
    """Shows shares on the profile screen
    """
    profileStr = ''
    for item in sharesJson['orderedItems']:
        profileStr += htmlIndividualShare(actor, item, translate, False, False)
    if len(profileStr) > 0:
        profileStr = '<div class="share-title">' + profileStr + '</div>\n'
    return profileStr


def htmlEditProfile(cssCache: {}, translate: {}, baseDir: str, path: str,
                    domain: str, port: int, httpPrefix: str,
                    defaultTimeline: str, theme: str,
                    peertubeInstances: []) -> str:
    """Shows the edit profile screen
    """
    imageFormats = getImageFormats()
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '')
    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''
    domainFull = getFullDomain(domain, port)

    actorFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    if not os.path.isfile(actorFilename):
        return ''

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, theme)

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
    briarAddress = ''
    manuallyApprovesFollowers = ''
    movedTo = ''
    actorJson = loadJson(actorFilename)
    if actorJson:
        if actorJson.get('movedTo'):
            movedTo = actorJson['movedTo']
        donateUrl = getDonationUrl(actorJson)
        xmppAddress = getXmppAddress(actorJson)
        matrixAddress = getMatrixAddress(actorJson)
        ssbAddress = getSSBAddress(actorJson)
        blogAddress = getBlogAddress(actorJson)
        toxAddress = getToxAddress(actorJson)
        briarAddress = getBriarAddress(actorJson)
        jamiAddress = getJamiAddress(actorJson)
        emailAddress = getEmailAddress(actorJson)
        PGPpubKey = getPGPpubKey(actorJson)
        PGPfingerprint = getPGPfingerprint(actorJson)
        if actorJson.get('name'):
            if not isFiltered(baseDir, nickname, domain, actorJson['name']):
                displayNickname = actorJson['name']
        if actorJson.get('summary'):
            bioStr = \
                actorJson['summary'].replace('<p>', '').replace('</p>', '')
            if isFiltered(baseDir, nickname, domain, bioStr):
                bioStr = ''
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
            if isFiltered(baseDir, nickname, domain, skillDesc):
                continue
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

    moderatorsStr = ''
    themesDropdown = ''
    instanceStr = ''
    editorsStr = ''
    peertubeStr = ''

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
            if getConfigParam(baseDir, "verifyAllSignatures"):
                instanceStr += \
                    '      <input type="checkbox" class="profilecheckbox" ' + \
                    'name="verifyallsignatures" checked> ' + \
                    translate['Verify all signatures'] + '<br>\n'
            else:
                instanceStr += \
                    '      <input type="checkbox" class="profilecheckbox" ' + \
                    'name="verifyallsignatures"> ' + \
                    translate['Verify all signatures'] + '<br>\n'
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

            themes = getThemesList(baseDir)
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

            peertubeStr = \
                '      <br><b><label class="labels">' + \
                translate['Peertube Instances'] + '</label></b>\n'
            idx = 'Show video previews for the following Peertube sites.'
            peertubeStr += \
                '      <br><label class="labels">' + \
                translate[idx] + '</label>\n'
            peertubeInstancesStr = ''
            for url in peertubeInstances:
                peertubeInstancesStr += url + '\n'
            peertubeStr += \
                '      <textarea id="message" name="ptInstances" ' + \
                'style="height:200px">' + peertubeInstancesStr + \
                '</textarea>\n'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    editProfileForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

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
        '    <h1>' + translate['Profile for'] + \
        ' ' + nickname + '@' + domainFull + '</h1>'
    editProfileForm += '    <div class="container">\n'
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

    alsoKnownAsStr = ''
    if actorJson.get('alsoKnownAs'):
        alsoKnownAs = actorJson['alsoKnownAs']
        ctr = 0
        for altActor in alsoKnownAs:
            if ctr > 0:
                alsoKnownAsStr += ', '
            ctr += 1
            alsoKnownAsStr += altActor

    editProfileForm += '<label class="labels">' + \
        translate['Other accounts'] + ':</label><br>\n'
    editProfileForm += \
        '      <input type="text" placeholder="https://..." ' + \
        'name="alsoKnownAs" value="' + alsoKnownAsStr + '">\n'

    editProfileForm += '<label class="labels">' + \
        translate['Moved to new account address'] + ':</label><br>\n'
    editProfileForm += \
        '      <input type="text" placeholder="https://..." ' + \
        'name="movedTo" value="' + movedTo + '">\n'
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

    editProfileForm += '<label class="labels">Briar</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="briarAddress" value="' + \
        briarAddress + '">\n'

    editProfileForm += '<label class="labels">Jami</label><br>\n'
    editProfileForm += \
        '      <input type="text" name="jamiAddress" value="' + \
        jamiAddress + '">\n'

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

    if not newsInstance:
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
    editProfileForm += moderatorsStr + editorsStr + peertubeStr
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


def _individualFollowAsHtml(translate: {},
                            baseDir: str, session,
                            cachedWebfingers: {},
                            personCache: {}, domain: str,
                            followUrl: str,
                            authorized: bool,
                            actorNickname: str,
                            httpPrefix: str,
                            projectVersion: str,
                            dormant: bool,
                            buttons=[]) -> str:
    """An individual follow entry on the profile screen
    """
    followUrlNickname = getNicknameFromActor(followUrl)
    followUrlDomain, followUrlPort = getDomainFromActor(followUrl)
    followUrlDomainFull = getFullDomain(followUrlDomain, followUrlPort)
    titleStr = '@' + followUrlNickname + '@' + followUrlDomainFull
    avatarUrl = getPersonAvatarUrl(baseDir, followUrl, personCache, True)
    if not avatarUrl:
        avatarUrl = followUrl + '/avatar.png'

    # lookup the correct webfinger for the followUrl
    followUrlHandle = followUrlNickname + '@' + followUrlDomainFull
    followUrlWf = \
        webfingerHandle(session, followUrlHandle, httpPrefix,
                        cachedWebfingers,
                        domain, __version__)

    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox,
     avatarUrl2, displayName) = getPersonBox(baseDir, session,
                                             followUrlWf,
                                             personCache, projectVersion,
                                             httpPrefix, followUrlNickname,
                                             domain, 'outbox', 43036)
    if avatarUrl2:
        avatarUrl = avatarUrl2
    if displayName:
        titleStr = displayName

    if dormant:
        titleStr += ' 💤'

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
