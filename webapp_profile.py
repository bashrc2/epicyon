__filename__ = "webapp_profile.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from pprint import pprint
from webfinger import webfingerHandle
from utils import getDisplayName
from utils import isGroupAccount
from utils import hasObjectDict
from utils import getOccupationName
from utils import getLockedAccount
from utils import getFullDomain
from utils import isArtist
from utils import isDormant
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import isSystemAccount
from utils import removeHtml
from utils import loadJson
from utils import getConfigParam
from utils import getImageFormats
from utils import acctDir
from utils import getSupportedLanguages
from utils import localActorUrl
from utils import getReplyIntervalHours
from languages import getActorLanguages
from skills import getSkills
from theme import getThemesList
from person import personBoxJson
from person import getActorJson
from person import getPersonAvatarUrl
from posts import getPersonBox
from posts import isModerator
from posts import parseUserFeed
from posts import isCreateInsideAnnounce
from donate import getDonationUrl
from donate import getWebsite
from xmpp import getXmppAddress
from matrix import getMatrixAddress
from ssb import getSSBAddress
from pgp import getEmailAddress
from pgp import getPGPfingerprint
from pgp import getPGPpubKey
from enigma import getEnigmaPubKey
from tox import getToxAddress
from briar import getBriarAddress
from jami import getJamiAddress
from cwtch import getCwtchAddress
from filters import isFiltered
from follow import isFollowerOfPerson
from follow import getFollowerDomains
from webapp_frontscreen import htmlFrontScreen
from webapp_utils import htmlKeyboardNavigation
from webapp_utils import htmlHideFromScreenReader
from webapp_utils import scheduledPostsExist
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlHeaderWithPersonMarkup
from webapp_utils import htmlFooter
from webapp_utils import addEmojiToDisplayName
from webapp_utils import getBannerFile
from webapp_utils import htmlPostSeparator
from webapp_utils import editCheckBox
from webapp_utils import editTextField
from webapp_utils import editTextArea
from webapp_utils import beginEditSection
from webapp_utils import endEditSection
from blog import getBlogAddress
from webapp_post import individualPostAsHtml
from webapp_timeline import htmlIndividualShare
from blocking import getCWlistVariable


def _validProfilePreviewPost(postJsonObject: {},
                             personUrl: str) -> (bool, {}):
    """Returns true if the given post should appear on a person/group profile
    after searching for a handle
    """
    isAnnouncedFeedItem = False
    if isCreateInsideAnnounce(postJsonObject):
        isAnnouncedFeedItem = True
        postJsonObject = postJsonObject['object']
    if not postJsonObject.get('type'):
        return False, None
    if postJsonObject['type'] == 'Create':
        if not hasObjectDict(postJsonObject):
            return False, None
    if postJsonObject['type'] != 'Create' and \
       postJsonObject['type'] != 'Announce':
        if postJsonObject['type'] != 'Note' and \
           postJsonObject['type'] != 'Page':
            return False, None
        if not postJsonObject.get('to'):
            return False, None
        if not postJsonObject.get('id'):
            return False, None
        # wrap in create
        cc = []
        if postJsonObject.get('cc'):
            cc = postJsonObject['cc']
        newPostJsonObject = {
            'object': postJsonObject,
            'to': postJsonObject['to'],
            'cc': cc,
            'id': postJsonObject['id'],
            'actor': personUrl,
            'type': 'Create'
        }
        postJsonObject = newPostJsonObject
    if not postJsonObject.get('actor'):
        return False, None
    if not isAnnouncedFeedItem:
        if postJsonObject['actor'] != personUrl and \
           postJsonObject['object']['type'] != 'Page':
            return False, None
    return True, postJsonObject


def htmlProfileAfterSearch(cssCache: {},
                           recentPostsCache: {}, maxRecentPosts: int,
                           translate: {},
                           base_dir: str, path: str, http_prefix: str,
                           nickname: str, domain: str, port: int,
                           profileHandle: str,
                           session, cachedWebfingers: {}, personCache: {},
                           debug: bool, projectVersion: str,
                           yt_replace_domain: str,
                           twitterReplacementDomain: str,
                           showPublishedDateOnly: bool,
                           defaultTimeline: str,
                           peertubeInstances: [],
                           allowLocalNetworkAccess: bool,
                           themeName: str,
                           accessKeys: {},
                           systemLanguage: str,
                           maxLikeCount: int,
                           signingPrivateKeyPem: str,
                           CWlists: {}, listsEnabled: str) -> str:
    """Show a profile page after a search for a fediverse address
    """
    http = False
    gnunet = False
    if http_prefix == 'http':
        http = True
    elif http_prefix == 'gnunet':
        gnunet = True
    profileJson, asHeader = \
        getActorJson(domain, profileHandle, http, gnunet, debug, False,
                     signingPrivateKeyPem, session)
    if not profileJson:
        return None

    personUrl = profileJson['id']
    searchDomain, searchPort = getDomainFromActor(personUrl)
    if not searchDomain:
        return None
    searchNickname = getNicknameFromActor(personUrl)
    if not searchNickname:
        return None
    searchDomainFull = getFullDomain(searchDomain, searchPort)

    profileStr = ''
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    isGroup = False
    if profileJson.get('type'):
        if profileJson['type'] == 'Group':
            isGroup = True

    avatarUrl = ''
    if profileJson.get('icon'):
        if profileJson['icon'].get('url'):
            avatarUrl = profileJson['icon']['url']
    if not avatarUrl:
        avatarUrl = getPersonAvatarUrl(base_dir, personUrl,
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
        if '"' in movedTo:
            movedTo = movedTo.split('"')[1]
        displayName += ' ⌂'

    followsYou = \
        isFollowerOfPerson(base_dir,
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

    joinedDate = None
    if profileJson.get('published'):
        if 'T' in profileJson['published']:
            joinedDate = profileJson['published']

    profileStr = \
        _getProfileHeaderAfterSearch(base_dir,
                                     nickname, defaultTimeline,
                                     searchNickname,
                                     searchDomainFull,
                                     translate,
                                     displayName, followsYou,
                                     profileDescriptionShort,
                                     avatarUrl, imageUrl,
                                     movedTo, profileJson['id'],
                                     alsoKnownAs, accessKeys,
                                     joinedDate)

    domainFull = getFullDomain(domain, port)

    followIsPermitted = True
    if not profileJson.get('followers'):
        # no followers collection specified within actor
        followIsPermitted = False
    elif searchNickname == 'news' and searchDomainFull == domainFull:
        # currently the news actor is not something you can follow
        followIsPermitted = False
    elif searchNickname == nickname and searchDomainFull == domainFull:
        # don't follow yourself!
        followIsPermitted = False

    if followIsPermitted:
        followStr = 'Follow'
        if isGroup:
            followStr = 'Join'

        profileStr += \
            '<div class="container">\n' + \
            '  <form method="POST" action="' + \
            backUrl + '/followconfirm">\n' + \
            '    <center>\n' + \
            '      <input type="hidden" name="actor" value="' + \
            personUrl + '">\n' + \
            '      <button type="submit" class="button" name="submitYes" ' + \
            'accesskey="' + accessKeys['followButton'] + '">' + \
            translate[followStr] + '</button>\n' + \
            '      <button type="submit" class="button" name="submitView" ' + \
            'accesskey="' + accessKeys['viewButton'] + '">' + \
            translate['View'] + '</button>\n' + \
            '    </center>\n' + \
            '  </form>\n' + \
            '</div>\n'
    else:
        profileStr += \
            '<div class="container">\n' + \
            '  <form method="POST" action="' + \
            backUrl + '/followconfirm">\n' + \
            '    <center>\n' + \
            '      <input type="hidden" name="actor" value="' + \
            personUrl + '">\n' + \
            '      <button type="submit" class="button" name="submitView" ' + \
            'accesskey="' + accessKeys['viewButton'] + '">' + \
            translate['View'] + '</button>\n' + \
            '    </center>\n' + \
            '  </form>\n' + \
            '</div>\n'

    userFeed = \
        parseUserFeed(signingPrivateKeyPem,
                      session, outboxUrl, asHeader, projectVersion,
                      http_prefix, domain, debug)
    if userFeed:
        i = 0
        for item in userFeed:
            showItem, postJsonObject = \
                _validProfilePreviewPost(item, personUrl)
            if not showItem:
                continue

            profileStr += \
                individualPostAsHtml(signingPrivateKeyPem,
                                     True, recentPostsCache, maxRecentPosts,
                                     translate, None, base_dir,
                                     session, cachedWebfingers, personCache,
                                     nickname, domain, port,
                                     postJsonObject, avatarUrl, False, False,
                                     http_prefix, projectVersion, 'inbox',
                                     yt_replace_domain,
                                     twitterReplacementDomain,
                                     showPublishedDateOnly,
                                     peertubeInstances,
                                     allowLocalNetworkAccess,
                                     themeName, systemLanguage, maxLikeCount,
                                     False, False, False, False, False, False,
                                     CWlists, listsEnabled)
            i += 1
            if i >= 8:
                break

    instanceTitle = \
        getConfigParam(base_dir, 'instanceTitle')
    return htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None) + \
        profileStr + htmlFooter()


def _getProfileHeader(base_dir: str, http_prefix: str,
                      nickname: str, domain: str,
                      domainFull: str, translate: {},
                      defaultTimeline: str,
                      displayName: str,
                      avatarDescription: str,
                      profileDescriptionShort: str,
                      loginButton: str, avatarUrl: str,
                      theme: str, movedTo: str,
                      alsoKnownAs: [],
                      pinnedContent: str,
                      accessKeys: {},
                      joinedDate: str,
                      occupationName: str) -> str:
    """The header of the profile screen, containing background
    image and avatar
    """
    htmlStr = \
        '\n\n    <figure class="profileHeader">\n' + \
        '      <a href="/users/' + \
        nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '">\n' + \
        '        <img class="profileBackground" ' + \
        'alt="" ' + \
        'src="/users/' + nickname + '/image_' + theme + '.png" /></a>\n' + \
        '      <figcaption>\n' + \
        '        <a href="/users/' + \
        nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '">\n' + \
        '          <img loading="lazy" src="' + avatarUrl + '" ' + \
        'alt=""  class="title"></a>\n'

    occupationStr = ''
    if occupationName:
        occupationStr += \
            '        <b>' + occupationName + '</b><br>\n'

    htmlStr += '        <h1>' + displayName + '</h1>\n' + occupationStr

    htmlStr += \
        '    <p><b>@' + nickname + '@' + domainFull + '</b><br>\n'
    if joinedDate:
        htmlStr += \
            '    <p>' + translate['Joined'] + ' ' + \
            joinedDate.split('T')[0] + '<br>\n'
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

        actor = localActorUrl(http_prefix, nickname, domainFull)
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
        '" src="/icons/qrcode.png" /></a></p>\n' + \
        '        <p>' + profileDescriptionShort + '</p>\n' + loginButton
    if pinnedContent:
        htmlStr += pinnedContent.replace('<p>', '<p>📎', 1)
    htmlStr += \
        '      </figcaption>\n' + \
        '    </figure>\n\n'
    return htmlStr


def _getProfileHeaderAfterSearch(base_dir: str,
                                 nickname: str, defaultTimeline: str,
                                 searchNickname: str,
                                 searchDomainFull: str,
                                 translate: {},
                                 displayName: str,
                                 followsYou: bool,
                                 profileDescriptionShort: str,
                                 avatarUrl: str, imageUrl: str,
                                 movedTo: str, actor: str,
                                 alsoKnownAs: [],
                                 accessKeys: {},
                                 joinedDate: str) -> str:
    """The header of a searched for handle, containing background
    image and avatar
    """
    if not imageUrl:
        imageUrl = '/defaultprofilebackground'
    htmlStr = \
        '\n\n    <figure class="profileHeader">\n' + \
        '      <a href="/users/' + \
        nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + accessKeys['menuTimeline'] + '">\n' + \
        '        <img class="profileBackground" ' + \
        'alt="" ' + \
        'src="' + imageUrl + '" /></a>\n' + \
        '      <figcaption>\n'
    if avatarUrl:
        htmlStr += \
            '      <a href="/users/' + \
            nickname + '/' + defaultTimeline + '" title="' + \
            translate['Switch to timeline view'] + '">\n' + \
            '          <img loading="lazy" src="' + avatarUrl + '" ' + \
            'alt="" class="title"></a>\n'
    if not displayName:
        displayName = searchNickname
    htmlStr += \
        '        <h1>' + displayName + '</h1>\n' + \
        '    <p><b>@' + searchNickname + '@' + searchDomainFull + '</b><br>\n'
    if joinedDate:
        htmlStr += '        <p>' + translate['Joined'] + ' ' + \
            joinedDate.split('T')[0] + '</p>\n'
    if followsYou:
        htmlStr += '        <p><b>' + translate['Follows you'] + '</b></p>\n'
    if movedTo:
        newNickname = getNicknameFromActor(movedTo)
        newDomain, newPort = getDomainFromActor(movedTo)
        newDomainFull = getFullDomain(newDomain, newPort)
        if newNickname and newDomain:
            newHandle = newNickname + '@' + newDomainFull
            htmlStr += '        <p>' + translate['New account'] + \
                ': <a href="' + movedTo + '">@' + newHandle + '</a></p>\n'
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

    htmlStr += \
        '        <p>' + profileDescriptionShort + '</p>\n' + \
        '      </figcaption>\n' + \
        '    </figure>\n\n'
    return htmlStr


def htmlProfile(signingPrivateKeyPem: str,
                rssIconAtTop: bool,
                cssCache: {}, iconsAsButtons: bool,
                defaultTimeline: str,
                recentPostsCache: {}, maxRecentPosts: int,
                translate: {}, projectVersion: str,
                base_dir: str, http_prefix: str, authorized: bool,
                profileJson: {}, selected: str,
                session, cachedWebfingers: {}, personCache: {},
                yt_replace_domain: str,
                twitterReplacementDomain: str,
                showPublishedDateOnly: bool,
                newswire: {}, theme: str, dormantMonths: int,
                peertubeInstances: [],
                allowLocalNetworkAccess: bool,
                textModeBanner: str,
                debug: bool, accessKeys: {}, city: str,
                systemLanguage: str, maxLikeCount: int,
                sharedItemsFederatedDomains: [],
                extraJson: {}, pageNumber: int,
                maxItemsPerPage: int,
                CWlists: {}, listsEnabled: str,
                content_license_url: str) -> str:
    """Show the profile page as html
    """
    nickname = profileJson['preferredUsername']
    if not nickname:
        return ""
    if isSystemAccount(nickname):
        return htmlFrontScreen(signingPrivateKeyPem,
                               rssIconAtTop,
                               cssCache, iconsAsButtons,
                               defaultTimeline,
                               recentPostsCache, maxRecentPosts,
                               translate, projectVersion,
                               base_dir, http_prefix, authorized,
                               profileJson, selected,
                               session, cachedWebfingers, personCache,
                               yt_replace_domain,
                               twitterReplacementDomain,
                               showPublishedDateOnly,
                               newswire, theme, extraJson,
                               allowLocalNetworkAccess, accessKeys,
                               systemLanguage, maxLikeCount,
                               sharedItemsFederatedDomains, None,
                               pageNumber, maxItemsPerPage, CWlists,
                               listsEnabled)

    domain, port = getDomainFromActor(profileJson['id'])
    if not domain:
        return ""
    displayName = \
        addEmojiToDisplayName(session, base_dir, http_prefix,
                              nickname, domain,
                              profileJson['name'], True)
    domainFull = getFullDomain(domain, port)
    profileDescription = \
        addEmojiToDisplayName(session, base_dir, http_prefix,
                              nickname, domain,
                              profileJson['summary'], False)
    postsButton = 'button'
    followingButton = 'button'
    followersButton = 'button'
    rolesButton = 'button'
    skillsButton = 'button'
    sharesButton = 'button'
    wantedButton = 'button'
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
    elif selected == 'wanted':
        wantedButton = 'buttonselected'
    loginButton = ''

    followApprovalsSection = ''
    followApprovals = False
    editProfileStr = ''
    logoutStr = ''
    actor = profileJson['id']
    usersPath = '/users/' + actor.split('/users/')[1]

    donateSection = ''
    donateUrl = getDonationUrl(profileJson)
    websiteUrl = getWebsite(profileJson, translate)
    blogAddress = getBlogAddress(profileJson)
    EnigmaPubKey = getEnigmaPubKey(profileJson)
    PGPpubKey = getPGPpubKey(profileJson)
    PGPfingerprint = getPGPfingerprint(profileJson)
    emailAddress = getEmailAddress(profileJson)
    xmppAddress = getXmppAddress(profileJson)
    matrixAddress = getMatrixAddress(profileJson)
    ssbAddress = getSSBAddress(profileJson)
    toxAddress = getToxAddress(profileJson)
    briarAddress = getBriarAddress(profileJson)
    jamiAddress = getJamiAddress(profileJson)
    cwtchAddress = getCwtchAddress(profileJson)
    if donateUrl or websiteUrl or xmppAddress or matrixAddress or \
       ssbAddress or toxAddress or briarAddress or \
       jamiAddress or cwtchAddress or PGPpubKey or EnigmaPubKey or \
       PGPfingerprint or emailAddress:
        donateSection = '<div class="container">\n'
        donateSection += '  <center>\n'
        if donateUrl and not isSystemAccount(nickname):
            donateSection += \
                '    <p><a href="' + donateUrl + \
                '"><button class="donateButton">' + translate['Donate'] + \
                '</button></a></p>\n'
        if websiteUrl:
            donateSection += \
                '<p>' + translate['Website'] + ': <a href="' + \
                websiteUrl + '">' + websiteUrl + '</a></p>\n'
        if emailAddress:
            donateSection += \
                '<p>' + translate['Email'] + ': <a href="mailto:' + \
                emailAddress + '">' + emailAddress + '</a></p>\n'
        if blogAddress:
            donateSection += \
                '<p>Blog: <a href="' + \
                blogAddress + '">' + blogAddress + '</a></p>\n'
        if xmppAddress:
            donateSection += \
                '<p>' + translate['XMPP'] + ': <a href="xmpp:' + \
                xmppAddress + '">' + xmppAddress + '</a></p>\n'
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
        if cwtchAddress:
            donateSection += \
                '<p>Cwtch: <label class="toxaddr">' + \
                cwtchAddress + '</label></p>\n'
        if EnigmaPubKey:
            donateSection += \
                '<p>Enigma: <label class="toxaddr">' + \
                EnigmaPubKey + '</label></p>\n'
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
            acctDir(base_dir, nickname, domain) + '/followrequests.txt'
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
                currFollowerDomains = \
                    getFollowerDomains(base_dir, nickname, domain)
                with open(followRequestsFilename, 'r') as f:
                    for followerHandle in f:
                        if len(line) > 0:
                            followerHandle = followerHandle.replace('\n', '')
                            if '://' in followerHandle:
                                followerActor = followerHandle
                            else:
                                nick = followerHandle.split('@')[0]
                                dom = followerHandle.split('@')[1]
                                followerActor = \
                                    localActorUrl(http_prefix, nick, dom)

                            # is this a new domain?
                            # if so then append a new instance indicator
                            followerDomain, _ = \
                                getDomainFromActor(followerActor)
                            newFollowerDomain = ''
                            if followerDomain not in currFollowerDomains:
                                newFollowerDomain = ' ✨'

                            basePath = '/users/' + nickname
                            followApprovalsSection += '<div class="container">'
                            followApprovalsSection += \
                                '<a href="' + followerActor + '">'
                            followApprovalsSection += \
                                '<span class="followRequestHandle">' + \
                                followerHandle + \
                                newFollowerDomain + '</span></a>'

                            # show Approve and Deny buttons
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
        if '"' in movedTo:
            movedTo = movedTo.split('"')[1]

    alsoKnownAs = None
    if profileJson.get('alsoKnownAs'):
        alsoKnownAs = profileJson['alsoKnownAs']

    joinedDate = None
    if profileJson.get('published'):
        if 'T' in profileJson['published']:
            joinedDate = profileJson['published']
    occupationName = None
    if profileJson.get('hasOccupation'):
        occupationName = getOccupationName(profileJson)

    avatarUrl = profileJson['icon']['url']
    # use alternate path for local avatars to avoid any caching issues
    if '://' + domainFull + '/system/accounts/avatars/' in avatarUrl:
        avatarUrl = \
            avatarUrl.replace('://' + domainFull + '/system/accounts/avatars/',
                              '://' + domainFull + '/users/')

    # get pinned post content
    accountDir = acctDir(base_dir, nickname, domain)
    pinnedFilename = accountDir + '/pinToProfile.txt'
    pinnedContent = None
    if os.path.isfile(pinnedFilename):
        with open(pinnedFilename, 'r') as pinFile:
            pinnedContent = pinFile.read()

    profileHeaderStr = \
        _getProfileHeader(base_dir, http_prefix,
                          nickname, domain,
                          domainFull, translate,
                          defaultTimeline, displayName,
                          avatarDescription,
                          profileDescriptionShort,
                          loginButton, avatarUrl, theme,
                          movedTo, alsoKnownAs,
                          pinnedContent, accessKeys,
                          joinedDate, occupationName)

    # keyboard navigation
    userPathStr = '/users/' + nickname
    deft = defaultTimeline
    isGroup = False
    followersStr = translate['Followers']
    if isGroupAccount(base_dir, nickname, domain):
        isGroup = True
        followersStr = translate['Members']
    menuTimeline = \
        htmlHideFromScreenReader('🏠') + ' ' + \
        translate['Switch to timeline view']
    menuEdit = \
        htmlHideFromScreenReader('✍') + ' ' + translate['Edit']
    if not isGroup:
        menuFollowing = \
            htmlHideFromScreenReader('👥') + ' ' + translate['Following']
    menuFollowers = \
        htmlHideFromScreenReader('👪') + ' ' + followersStr
    if not isGroup:
        menuRoles = \
            htmlHideFromScreenReader('🤚') + ' ' + translate['Roles']
        menuSkills = \
            htmlHideFromScreenReader('🛠') + ' ' + translate['Skills']
    menuLogout = \
        htmlHideFromScreenReader('❎') + ' ' + translate['Logout']
    navLinks = {
        menuTimeline: userPathStr + '/' + deft,
        menuEdit: userPathStr + '/editprofile',
        menuFollowing: userPathStr + '/following#timeline',
        menuFollowers: userPathStr + '/followers#timeline',
        menuRoles: userPathStr + '/roles#timeline',
        menuSkills: userPathStr + '/skills#timeline',
        menuLogout: '/logout'
    }
    if isArtist(base_dir, nickname):
        menuThemeDesigner = \
            htmlHideFromScreenReader('🎨') + ' ' + translate['Theme Designer']
        navLinks[menuThemeDesigner] = userPathStr + '/themedesigner'
    navAccessKeys = {}
    for variableName, key in accessKeys.items():
        if not locals().get(variableName):
            continue
        navAccessKeys[locals()[variableName]] = key

    profileStr = htmlKeyboardNavigation(textModeBanner,
                                        navLinks, navAccessKeys)

    profileStr += profileHeaderStr + donateSection
    profileStr += '<div class="container" id="buttonheader">\n'
    profileStr += '  <center>'
    profileStr += \
        '    <a href="' + usersPath + '#buttonheader"><button class="' + \
        postsButton + '"><span>' + translate['Posts'] + \
        ' </span></button></a>'
    if not isGroup:
        profileStr += \
            '    <a href="' + usersPath + '/following#buttonheader">' + \
            '<button class="' + followingButton + '"><span>' + \
            translate['Following'] + ' </span></button></a>'
    profileStr += \
        '    <a href="' + usersPath + '/followers#buttonheader">' + \
        '<button class="' + followersButton + \
        '"><span>' + followersStr + ' </span></button></a>'
    if not isGroup:
        profileStr += \
            '    <a href="' + usersPath + '/roles#buttonheader">' + \
            '<button class="' + rolesButton + '"><span>' + \
            translate['Roles'] + \
            ' </span></button></a>'
        profileStr += \
            '    <a href="' + usersPath + '/skills#buttonheader">' + \
            '<button class="' + skillsButton + '"><span>' + \
            translate['Skills'] + ' </span></button></a>'
#    profileStr += \
#        '    <a href="' + usersPath + '/shares#buttonheader">' + \
#        '<button class="' + sharesButton + '"><span>' + \
#        translate['Shares'] + ' </span></button></a>'
#    profileStr += \
#        '    <a href="' + usersPath + '/wanted#buttonheader">' + \
#        '<button class="' + wantedButton + '"><span>' + \
#        translate['Wanted'] + ' </span></button></a>'
    profileStr += logoutStr + editProfileStr
    profileStr += '  </center>'
    profileStr += '</div>'

    # start of #timeline
    profileStr += '<div id="timeline">\n'

    profileStr += followApprovalsSection

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    licenseStr = \
        '<a href="https://gitlab.com/bashrc2/epicyon">' + \
        '<img loading="lazy" class="license" alt="' + \
        translate['Get the source code'] + '" title="' + \
        translate['Get the source code'] + '" src="/icons/agpl.png" /></a>'

    if selected == 'posts':
        profileStr += \
            _htmlProfilePosts(recentPostsCache, maxRecentPosts,
                              translate,
                              base_dir, http_prefix, authorized,
                              nickname, domain, port,
                              session, cachedWebfingers, personCache,
                              projectVersion,
                              yt_replace_domain,
                              twitterReplacementDomain,
                              showPublishedDateOnly,
                              peertubeInstances,
                              allowLocalNetworkAccess,
                              theme, systemLanguage,
                              maxLikeCount,
                              signingPrivateKeyPem,
                              CWlists, listsEnabled) + licenseStr
    if not isGroup:
        if selected == 'following':
            profileStr += \
                _htmlProfileFollowing(translate, base_dir, http_prefix,
                                      authorized, nickname,
                                      domain, port, session,
                                      cachedWebfingers, personCache, extraJson,
                                      projectVersion, ["unfollow"], selected,
                                      usersPath, pageNumber, maxItemsPerPage,
                                      dormantMonths, debug,
                                      signingPrivateKeyPem)
    if selected == 'followers':
        profileStr += \
            _htmlProfileFollowing(translate, base_dir, http_prefix,
                                  authorized, nickname,
                                  domain, port, session,
                                  cachedWebfingers, personCache, extraJson,
                                  projectVersion, ["block"],
                                  selected, usersPath, pageNumber,
                                  maxItemsPerPage, dormantMonths, debug,
                                  signingPrivateKeyPem)
    if not isGroup:
        if selected == 'roles':
            profileStr += \
                _htmlProfileRoles(translate, nickname, domainFull,
                                  extraJson)
        elif selected == 'skills':
            profileStr += \
                _htmlProfileSkills(translate, nickname, domainFull, extraJson)
#       elif selected == 'shares':
#           profileStr += \
#                _htmlProfileShares(actor, translate,
#                                   nickname, domainFull,
#                                   extraJson, 'shares') + licenseStr
#        elif selected == 'wanted':
#            profileStr += \
#                _htmlProfileShares(actor, translate,
#                                   nickname, domainFull,
#                                   extraJson, 'wanted') + licenseStr
    # end of #timeline
    profileStr += '</div>'

    instanceTitle = \
        getConfigParam(base_dir, 'instanceTitle')
    profileStr = \
        htmlHeaderWithPersonMarkup(cssFilename, instanceTitle,
                                   profileJson, city,
                                   content_license_url) + \
        profileStr + htmlFooter()
    return profileStr


def _htmlProfilePosts(recentPostsCache: {}, maxRecentPosts: int,
                      translate: {},
                      base_dir: str, http_prefix: str,
                      authorized: bool,
                      nickname: str, domain: str, port: int,
                      session, cachedWebfingers: {}, personCache: {},
                      projectVersion: str,
                      yt_replace_domain: str,
                      twitterReplacementDomain: str,
                      showPublishedDateOnly: bool,
                      peertubeInstances: [],
                      allowLocalNetworkAccess: bool,
                      themeName: str, systemLanguage: str,
                      maxLikeCount: int,
                      signingPrivateKeyPem: str,
                      CWlists: {}, listsEnabled: str) -> str:
    """Shows posts on the profile screen
    These should only be public posts
    """
    separatorStr = htmlPostSeparator(base_dir, None)
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
            personBoxJson({}, session, base_dir, domain,
                          port,
                          outboxFeedPathStr,
                          http_prefix,
                          10, boxName,
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
                                         base_dir, session, cachedWebfingers,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         http_prefix, projectVersion, 'inbox',
                                         yt_replace_domain,
                                         twitterReplacementDomain,
                                         showPublishedDateOnly,
                                         peertubeInstances,
                                         allowLocalNetworkAccess,
                                         themeName, systemLanguage,
                                         maxLikeCount,
                                         False, False, False,
                                         True, False, False,
                                         CWlists, listsEnabled)
                if postStr:
                    profileStr += postStr + separatorStr
                    ctr += 1
                    if ctr >= maxItems:
                        break
        currPage += 1
    return profileStr


def _htmlProfileFollowing(translate: {}, base_dir: str, http_prefix: str,
                          authorized: bool,
                          nickname: str, domain: str, port: int,
                          session, cachedWebfingers: {}, personCache: {},
                          followingJson: {}, projectVersion: str,
                          buttons: [],
                          feedName: str, actor: str,
                          pageNumber: int,
                          maxItemsPerPage: int,
                          dormantMonths: int, debug: bool,
                          signingPrivateKeyPem: str) -> str:
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
                isDormant(base_dir, nickname, domain, followingActor,
                          dormantMonths)

        profileStr += \
            _individualFollowAsHtml(signingPrivateKeyPem,
                                    translate, base_dir, session,
                                    cachedWebfingers, personCache,
                                    domain, followingActor,
                                    authorized, nickname,
                                    http_prefix, projectVersion, dormant,
                                    debug, buttons)

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
                      rolesList: []) -> str:
    """Shows roles on the profile screen
    """
    profileStr = ''
    profileStr += \
        '<div class="roles">\n<div class="roles-inner">\n'
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
                       nickname: str, domain: str, sharesJson: {},
                       sharesFileType: str) -> str:
    """Shows shares on the profile screen
    """
    profileStr = ''
    for item in sharesJson['orderedItems']:
        profileStr += htmlIndividualShare(domain, item['shareId'],
                                          actor, item, translate, False, False,
                                          sharesFileType)
    if len(profileStr) > 0:
        profileStr = '<div class="share-title">' + profileStr + '</div>\n'
    return profileStr


def _grayscaleEnabled(base_dir: str) -> bool:
    """Is grayscale UI enabled?
    """
    return os.path.isfile(base_dir + '/accounts/.grayscale')


def _htmlThemesDropdown(base_dir: str, translate: {}) -> str:
    """Returns the html for theme selection dropdown
    """
    # Themes section
    themes = getThemesList(base_dir)
    themesDropdown = '  <label class="labels">' + \
        translate['Theme'] + '</label><br>\n'
    grayscale = _grayscaleEnabled(base_dir)
    themesDropdown += \
        editCheckBox(translate['Grayscale'], 'grayscale', grayscale)
    themesDropdown += '  <select id="themeDropdown" ' + \
        'name="themeDropdown" class="theme">'
    for themeName in themes:
        translatedThemeName = themeName
        if translate.get(themeName):
            translatedThemeName = translate[themeName]
        themesDropdown += '    <option value="' + \
            themeName.lower() + '">' + \
            translatedThemeName + '</option>'
    themesDropdown += '  </select><br>'
    if os.path.isfile(base_dir + '/fonts/custom.woff') or \
       os.path.isfile(base_dir + '/fonts/custom.woff2') or \
       os.path.isfile(base_dir + '/fonts/custom.otf') or \
       os.path.isfile(base_dir + '/fonts/custom.ttf'):
        themesDropdown += \
            editCheckBox(translate['Remove the custom font'],
                         'removeCustomFont', False)
    themeName = getConfigParam(base_dir, 'theme')
    themesDropdown = \
        themesDropdown.replace('<option value="' + themeName + '">',
                               '<option value="' + themeName +
                               '" selected>')
    return themesDropdown


def _htmlEditProfileGraphicDesign(base_dir: str, translate: {}) -> str:
    """Graphic design section on Edit Profile screen
    """
    themeFormats = '.zip, .gz'

    graphicsStr = beginEditSection(translate['Graphic Design'])

    lowBandwidth = getConfigParam(base_dir, 'lowBandwidth')
    if not lowBandwidth:
        lowBandwidth = False
    graphicsStr += _htmlThemesDropdown(base_dir, translate)
    graphicsStr += \
        '      <label class="labels">' + \
        translate['Import Theme'] + '</label>\n'
    graphicsStr += '      <input type="file" id="importTheme" '
    graphicsStr += 'name="submitImportTheme" '
    graphicsStr += 'accept="' + themeFormats + '">\n'
    graphicsStr += \
        '      <label class="labels">' + \
        translate['Export Theme'] + '</label><br>\n'
    graphicsStr += \
        '      <button type="submit" class="button" ' + \
        'name="submitExportTheme">➤</button><br>\n'
    graphicsStr += \
        editCheckBox(translate['Low Bandwidth'], 'lowBandwidth',
                     bool(lowBandwidth))

    graphicsStr += endEditSection()
    return graphicsStr


def _htmlEditProfileTwitter(base_dir: str, translate: {},
                            removeTwitter: str) -> str:
    """Edit twitter settings within profile
    """
    # Twitter section
    twitterStr = beginEditSection(translate['Twitter'])
    twitterStr += \
        editCheckBox(translate['Remove Twitter posts'],
                     'removeTwitter', removeTwitter)
    twitterReplacementDomain = getConfigParam(base_dir, "twitterdomain")
    if not twitterReplacementDomain:
        twitterReplacementDomain = ''
    twitterStr += \
        editTextField(translate['Twitter Replacement Domain'],
                      'twitterdomain', twitterReplacementDomain)
    twitterStr += endEditSection()
    return twitterStr


def _htmlEditProfileInstance(base_dir: str, translate: {},
                             peertubeInstances: [],
                             mediaInstanceStr: str,
                             blogsInstanceStr: str,
                             newsInstanceStr: str) -> (str, str, str, str):
    """Edit profile instance settings
    """
    imageFormats = getImageFormats()

    # Instance details section
    instanceDescription = \
        getConfigParam(base_dir, 'instanceDescription')
    customSubmitText = \
        getConfigParam(base_dir, 'customSubmitText')
    instanceDescriptionShort = \
        getConfigParam(base_dir, 'instanceDescriptionShort')
    instanceTitle = \
        getConfigParam(base_dir, 'instanceTitle')
    content_license_url = \
        getConfigParam(base_dir, 'content_license_url')
    if not content_license_url:
        content_license_url = 'https://creativecommons.org/licenses/by/4.0'

    instanceStr = beginEditSection(translate['Instance Settings'])

    instanceStr += \
        editTextField(translate['Instance Title'],
                      'instanceTitle', instanceTitle)
    instanceStr += '<br>\n'
    instanceStr += \
        editTextField(translate['Instance Short Description'],
                      'instanceDescriptionShort', instanceDescriptionShort)
    instanceStr += '<br>\n'
    instanceStr += \
        editTextArea(translate['Instance Description'],
                     'instanceDescription', instanceDescription, 200,
                     '', True)
    instanceStr += \
        editTextField(translate['Content License'],
                      'content_license_url', content_license_url)
    instanceStr += '<br>\n'
    instanceStr += \
        editTextField(translate['Custom post submit button text'],
                      'customSubmitText', customSubmitText)
    instanceStr += '<br>\n'
    instanceStr += \
        '  <label class="labels">' + \
        translate['Instance Logo'] + '</label>' + \
        '  <input type="file" id="instanceLogo" name="instanceLogo"' + \
        '      accept="' + imageFormats + '"><br>\n' + \
        '  <br><label class="labels">' + \
        translate['Security'] + '</label><br>\n'

    nodeInfoStr = \
        translate['Show numbers of accounts within instance metadata']
    if getConfigParam(base_dir, "showNodeInfoAccounts"):
        instanceStr += \
            editCheckBox(nodeInfoStr, 'showNodeInfoAccounts', True)
    else:
        instanceStr += \
            editCheckBox(nodeInfoStr, 'showNodeInfoAccounts', False)

    nodeInfoStr = \
        translate['Show version number within instance metadata']
    if getConfigParam(base_dir, "showNodeInfoVersion"):
        instanceStr += \
            editCheckBox(nodeInfoStr, 'showNodeInfoVersion', True)
    else:
        instanceStr += \
            editCheckBox(nodeInfoStr, 'showNodeInfoVersion', False)

    if getConfigParam(base_dir, "verifyAllSignatures"):
        instanceStr += \
            editCheckBox(translate['Verify all signatures'],
                         'verifyallsignatures', True)
    else:
        instanceStr += \
            editCheckBox(translate['Verify all signatures'],
                         'verifyallsignatures', False)

    instanceStr += translate['Enabling broch mode'] + '<br>\n'
    if getConfigParam(base_dir, "brochMode"):
        instanceStr += \
            editCheckBox(translate['Broch mode'], 'brochMode', True)
    else:
        instanceStr += \
            editCheckBox(translate['Broch mode'], 'brochMode', False)
    # Instance type
    instanceStr += \
        '  <br><label class="labels">' + \
        translate['Type of instance'] + '</label><br>\n'
    instanceStr += \
        editCheckBox(translate['This is a media instance'],
                     'mediaInstance', mediaInstanceStr)
    instanceStr += \
        editCheckBox(translate['This is a blogging instance'],
                     'blogsInstance', blogsInstanceStr)
    instanceStr += \
        editCheckBox(translate['This is a news instance'],
                     'newsInstance', newsInstanceStr)

    instanceStr += endEditSection()

    # Role assignments section
    moderators = ''
    moderatorsFile = base_dir + '/accounts/moderators.txt'
    if os.path.isfile(moderatorsFile):
        with open(moderatorsFile, 'r') as f:
            moderators = f.read()
    # site moderators
    roleAssignStr = \
        beginEditSection(translate['Role Assignment']) + \
        '  <b><label class="labels">' + \
        translate['Moderators'] + '</label></b><br>\n' + \
        '  ' + \
        translate['A list of moderator nicknames. One per line.'] + \
        '  <textarea id="message" name="moderators" placeholder="' + \
        translate['List of moderator nicknames'] + \
        '..." style="height:200px" spellcheck="false">' + \
        moderators + '</textarea>'

    # site editors
    editors = ''
    editorsFile = base_dir + '/accounts/editors.txt'
    if os.path.isfile(editorsFile):
        with open(editorsFile, 'r') as f:
            editors = f.read()
    roleAssignStr += \
        '  <b><label class="labels">' + \
        translate['Site Editors'] + '</label></b><br>\n' + \
        '  ' + \
        translate['A list of editor nicknames. One per line.'] + \
        '  <textarea id="message" name="editors" placeholder="" ' + \
        'style="height:200px" spellcheck="false">' + \
        editors + '</textarea>'

    # counselors
    counselors = ''
    counselorsFile = base_dir + '/accounts/counselors.txt'
    if os.path.isfile(counselorsFile):
        with open(counselorsFile, 'r') as f:
            counselors = f.read()
    roleAssignStr += \
        editTextArea(translate['Counselors'], 'counselors', counselors,
                     200, '', False)

    # artists
    artists = ''
    artistsFile = base_dir + '/accounts/artists.txt'
    if os.path.isfile(artistsFile):
        with open(artistsFile, 'r') as f:
            artists = f.read()
    roleAssignStr += \
        editTextArea(translate['Artists'], 'artists', artists,
                     200, '', False)
    roleAssignStr += endEditSection()

    # Video section
    peertubeStr = beginEditSection(translate['Video Settings'])
    peertubeInstancesStr = ''
    for url in peertubeInstances:
        peertubeInstancesStr += url + '\n'
    peertubeStr += \
        editTextArea(translate['Peertube Instances'], 'ptInstances',
                     peertubeInstancesStr, 200, '', False)
    peertubeStr += \
        '      <br>\n'
    yt_replace_domain = getConfigParam(base_dir, "youtubedomain")
    if not yt_replace_domain:
        yt_replace_domain = ''
    peertubeStr += \
        editTextField(translate['YouTube Replacement Domain'],
                      'ytdomain', yt_replace_domain)
    peertubeStr += endEditSection()

    libretranslateUrl = getConfigParam(base_dir, 'libretranslateUrl')
    libretranslateApiKey = getConfigParam(base_dir, 'libretranslateApiKey')
    libretranslateStr = \
        _htmlEditProfileLibreTranslate(translate,
                                       libretranslateUrl,
                                       libretranslateApiKey)

    return instanceStr, roleAssignStr, peertubeStr, libretranslateStr


def _htmlEditProfileDangerZone(translate: {}) -> str:
    """danger zone section of Edit Profile screen
    """
    editProfileForm = beginEditSection(translate['Danger Zone'])

    editProfileForm += \
        '      <b><label class="labels">' + \
        translate['Danger Zone'] + '</label></b><br>\n'

    editProfileForm += \
        editCheckBox(translate['Deactivate this account'],
                     'deactivateThisAccount', False)

    editProfileForm += endEditSection()
    return editProfileForm


def _htmlSystemMonitor(nickname: str, translate: {}) -> str:
    """Links to performance graphs
    """
    systemMonitorStr = beginEditSection(translate['System Monitor'])
    systemMonitorStr += '<p><a href="/users/' + nickname + \
        '/performance?graph=get">📊 GET</a></p>'
    systemMonitorStr += '<p><a href="/users/' + nickname + \
        '/performance?graph=post">📊 POST</a></p>'
    systemMonitorStr += endEditSection()
    return systemMonitorStr


def _htmlEditProfileSkills(base_dir: str, nickname: str, domain: str,
                           translate: {}) -> str:
    """skills section of Edit Profile screen
    """
    skills = getSkills(base_dir, nickname, domain)
    skillsStr = ''
    skillCtr = 1
    if skills:
        for skillDesc, skillValue in skills.items():
            if isFiltered(base_dir, nickname, domain, skillDesc):
                continue
            skillsStr += \
                '<p><input type="text" placeholder="' + translate['Skill'] + \
                ' ' + str(skillCtr) + '" name="skillName' + str(skillCtr) + \
                '" value="' + skillDesc + '" style="width:40%">' + \
                '<input type="range" min="1" max="100" ' + \
                'class="slider" name="skillValue' + \
                str(skillCtr) + '" value="' + str(skillValue) + '"></p>'
            skillCtr += 1

    skillsStr += \
        '<p><input type="text" placeholder="Skill ' + str(skillCtr) + \
        '" name="skillName' + str(skillCtr) + \
        '" value="" style="width:40%">' + \
        '<input type="range" min="1" max="100" ' + \
        'class="slider" name="skillValue' + \
        str(skillCtr) + '" value="50"></p>' + endEditSection()

    idx = 'If you want to participate within organizations then you ' + \
        'can indicate some skills that you have and approximate ' + \
        'proficiency levels. This helps organizers to construct ' + \
        'teams with an appropriate combination of skills.'
    editProfileForm = \
        beginEditSection(translate['Skills']) + \
        '      <b><label class="labels">' + \
        translate['Skills'] + '</label></b><br>\n' + \
        '      <label class="labels">' + \
        translate[idx] + '</label>\n' + skillsStr
    return editProfileForm


def _htmlEditProfileGitProjects(base_dir: str, nickname: str, domain: str,
                                translate: {}) -> str:
    """git projects section of edit profile screen
    """
    gitProjectsStr = ''
    gitProjectsFilename = \
        acctDir(base_dir, nickname, domain) + '/gitprojects.txt'
    if os.path.isfile(gitProjectsFilename):
        with open(gitProjectsFilename, 'r') as gitProjectsFile:
            gitProjectsStr = gitProjectsFile.read()

    editProfileForm = beginEditSection(translate['Git Projects'])
    idx = 'List of project names that you wish to receive git patches for'
    editProfileForm += \
        editTextArea(translate[idx], 'gitProjects', gitProjectsStr,
                     100, '', False)
    editProfileForm += endEditSection()
    return editProfileForm


def _htmlEditProfileSharedItems(base_dir: str, nickname: str, domain: str,
                                translate: {}) -> str:
    """shared items section of edit profile screen
    """
    sharedItemsStr = ''
    sharedItemsFederatedDomainsStr = \
        getConfigParam(base_dir, 'sharedItemsFederatedDomains')
    if sharedItemsFederatedDomainsStr:
        sharedItemsFederatedDomainsList = \
            sharedItemsFederatedDomainsStr.split(',')
        for sharedFederatedDomain in sharedItemsFederatedDomainsList:
            sharedItemsStr += sharedFederatedDomain.strip() + '\n'

    editProfileForm = beginEditSection(translate['Shares'])
    idx = 'List of domains which can access the shared items catalog'
    editProfileForm += \
        editTextArea(translate[idx], 'shareDomainList',
                     sharedItemsStr, 200, '', False)
    editProfileForm += endEditSection()
    return editProfileForm


def _htmlEditProfileFiltering(base_dir: str, nickname: str, domain: str,
                              userAgentsBlocked: str,
                              translate: {}, replyIntervalHours: int,
                              CWlists: {}, listsEnabled: str) -> str:
    """Filtering and blocking section of edit profile screen
    """
    filterStr = ''
    filterFilename = \
        acctDir(base_dir, nickname, domain) + '/filters.txt'
    if os.path.isfile(filterFilename):
        with open(filterFilename, 'r') as filterfile:
            filterStr = filterfile.read()

    filterBioStr = ''
    filterBioFilename = \
        acctDir(base_dir, nickname, domain) + '/filters_bio.txt'
    if os.path.isfile(filterBioFilename):
        with open(filterBioFilename, 'r') as filterfile:
            filterBioStr = filterfile.read()

    switchStr = ''
    switchFilename = \
        acctDir(base_dir, nickname, domain) + '/replacewords.txt'
    if os.path.isfile(switchFilename):
        with open(switchFilename, 'r') as switchfile:
            switchStr = switchfile.read()

    autoTags = ''
    autoTagsFilename = \
        acctDir(base_dir, nickname, domain) + '/autotags.txt'
    if os.path.isfile(autoTagsFilename):
        with open(autoTagsFilename, 'r') as autoTagsFile:
            autoTags = autoTagsFile.read()

    autoCW = ''
    autoCWFilename = \
        acctDir(base_dir, nickname, domain) + '/autocw.txt'
    if os.path.isfile(autoCWFilename):
        with open(autoCWFilename, 'r') as autoCWFile:
            autoCW = autoCWFile.read()

    blockedStr = ''
    blockedFilename = \
        acctDir(base_dir, nickname, domain) + '/blocking.txt'
    if os.path.isfile(blockedFilename):
        with open(blockedFilename, 'r') as blockedfile:
            blockedStr = blockedfile.read()

    dmAllowedInstancesStr = ''
    dmAllowedInstancesFilename = \
        acctDir(base_dir, nickname, domain) + '/dmAllowedInstances.txt'
    if os.path.isfile(dmAllowedInstancesFilename):
        with open(dmAllowedInstancesFilename, 'r') as dmAllowedInstancesFile:
            dmAllowedInstancesStr = dmAllowedInstancesFile.read()

    allowedInstancesStr = ''
    allowedInstancesFilename = \
        acctDir(base_dir, nickname, domain) + '/allowedinstances.txt'
    if os.path.isfile(allowedInstancesFilename):
        with open(allowedInstancesFilename, 'r') as allowedInstancesFile:
            allowedInstancesStr = allowedInstancesFile.read()

    editProfileForm = beginEditSection(translate['Filtering and Blocking'])

    idx = 'Hours after posting during which replies are allowed'
    editProfileForm += \
        '  <label class="labels">' + \
        translate[idx] + \
        ':</label> <input type="number" name="replyhours" ' + \
        'min="0" max="999999999999" step="1" ' + \
        'value="' + str(replyIntervalHours) + '"><br>\n'

    editProfileForm += \
        '<label class="labels">' + \
        translate['City for spoofed GPS image metadata'] + \
        '</label><br>\n'

    city = ''
    cityFilename = acctDir(base_dir, nickname, domain) + '/city.txt'
    if os.path.isfile(cityFilename):
        with open(cityFilename, 'r') as fp:
            city = fp.read().replace('\n', '')
    locationsFilename = base_dir + '/custom_locations.txt'
    if not os.path.isfile(locationsFilename):
        locationsFilename = base_dir + '/locations.txt'
    cities = []
    with open(locationsFilename, 'r') as f:
        cities = f.readlines()
        cities.sort()
    editProfileForm += '  <select id="cityDropdown" ' + \
        'name="cityDropdown" class="theme">\n'
    city = city.lower()
    for cityName in cities:
        if ':' not in cityName:
            continue
        citySelected = ''
        cityName = cityName.split(':')[0]
        cityName = cityName.lower()
        if city:
            if city in cityName:
                citySelected = ' selected'
        editProfileForm += \
            '    <option value="' + cityName + \
            '"' + citySelected.title() + '>' + \
            cityName + '</option>\n'
    editProfileForm += '  </select><br>\n'

    editProfileForm += \
        '      <b><label class="labels">' + \
        translate['Filtered words'] + '</label></b>\n' + \
        '      <br><label class="labels">' + \
        translate['One per line'] + '</label>\n' + \
        '      <textarea id="message" ' + \
        'name="filteredWords" style="height:200px" spellcheck="false">' + \
        filterStr + '</textarea>\n' + \
        '      <br><b><label class="labels">' + \
        translate['Filtered words within bio'] + '</label></b>\n' + \
        '      <br><label class="labels">' + \
        translate['One per line'] + '</label>\n' + \
        '      <textarea id="message" ' + \
        'name="filteredWordsBio" style="height:200px" spellcheck="false">' + \
        filterBioStr + '</textarea>\n' + \
        '      <br><b><label class="labels">' + \
        translate['Word Replacements'] + '</label></b>\n' + \
        '      <br><label class="labels">A -> B</label>\n' + \
        '      <textarea id="message" name="switchWords" ' + \
        'style="height:200px" spellcheck="false">' + \
        switchStr + '</textarea>\n' + \
        '      <br><b><label class="labels">' + \
        translate['Autogenerated Hashtags'] + '</label></b>\n' + \
        '      <br><label class="labels">A -> #B</label>\n' + \
        '      <textarea id="message" name="autoTags" ' + \
        'style="height:200px" spellcheck="false">' + \
        autoTags + '</textarea>\n' + \
        '      <br><b><label class="labels">' + \
        translate['Autogenerated Content Warnings'] + '</label></b>\n' + \
        '      <br><label class="labels">A -> B</label>\n' + \
        '      <textarea id="message" name="autoCW" ' + \
        'style="height:200px" spellcheck="true">' + autoCW + '</textarea>\n'

    idx = 'Blocked accounts, one per line, in the form ' + \
        'nickname@domain or *@blockeddomain'
    editProfileForm += \
        editTextArea(translate['Blocked accounts'], 'blocked', blockedStr,
                     200, '', False)

    idx = 'Direct messages are always allowed from these instances.'
    editProfileForm += \
        editTextArea(translate['Direct Message permitted instances'],
                     'dmAllowedInstances', dmAllowedInstancesStr,
                     200, '', False)

    idx = 'Federate only with a defined set of instances. ' + \
        'One domain name per line.'
    editProfileForm += \
        '      <br><b><label class="labels">' + \
        translate['Federation list'] + '</label></b>\n' + \
        '      <br><label class="labels">' + \
        translate[idx] + '</label>\n' + \
        '      <textarea id="message" name="allowedInstances" ' + \
        'style="height:200px" spellcheck="false">' + \
        allowedInstancesStr + '</textarea>\n'

    if isModerator(base_dir, nickname):
        editProfileForm += \
            '<a href="/users/' + nickname + '/crawlers">' + \
            translate['Known Web Crawlers'] + '</a><br>\n'

        userAgentsBlockedStr = ''
        for ua in userAgentsBlocked:
            if userAgentsBlockedStr:
                userAgentsBlockedStr += '\n'
            userAgentsBlockedStr += ua
        editProfileForm += \
            editTextArea(translate['Blocked User Agents'],
                         'userAgentsBlockedStr', userAgentsBlockedStr,
                         200, '', False)

        CWlistsStr = ''
        for name, item in CWlists.items():
            variableName = getCWlistVariable(name)
            listIsEnabled = False
            if listsEnabled:
                if name in listsEnabled:
                    listIsEnabled = True
            if translate.get(name):
                name = translate[name]
            CWlistsStr += editCheckBox(name, variableName, listIsEnabled)
        if CWlistsStr:
            idx = 'Add content warnings for the following sites'
            editProfileForm += \
                '<label class="labels">' + translate[idx] + ':</label>\n' + \
                '<br>' + CWlistsStr

    editProfileForm += endEditSection()
    return editProfileForm


def _htmlEditProfileChangePassword(translate: {}) -> str:
    """Change password section of edit profile screen
    """
    editProfileForm = \
        beginEditSection(translate['Change Password']) + \
        '<label class="labels">' + translate['Change Password'] + \
        '</label><br>\n' + \
        '      <input type="password" name="password" ' + \
        'value=""><br>\n' + \
        '<label class="labels">' + translate['Confirm Password'] + \
        '</label><br>\n' + \
        '      <input type="password" name="passwordconfirm" value="">\n' + \
        endEditSection()
    return editProfileForm


def _htmlEditProfileLibreTranslate(translate: {},
                                   libretranslateUrl: str,
                                   libretranslateApiKey: str) -> str:
    """Change automatic translation settings
    """
    editProfileForm = beginEditSection('LibreTranslate')

    editProfileForm += \
        editTextField('URL', 'libretranslateUrl', libretranslateUrl,
                      'http://0.0.0.0:5000')
    editProfileForm += \
        editTextField('API Key', 'libretranslateApiKey', libretranslateApiKey)

    editProfileForm += endEditSection()
    return editProfileForm


def _htmlEditProfileBackground(newsInstance: bool, translate: {}) -> str:
    """Background images section of edit profile screen
    """
    idx = 'The files attached below should be no larger than ' + \
        '10MB in total uploaded at once.'
    editProfileForm = \
        beginEditSection(translate['Background Images']) + \
        '      <label class="labels">' + translate[idx] + '</label><br><br>\n'

    if not newsInstance:
        imageFormats = getImageFormats()
        editProfileForm += \
            '      <label class="labels">' + \
            translate['Background image'] + '</label>\n' + \
            '      <input type="file" id="image" name="image"' + \
            '            accept="' + imageFormats + '">\n' + \
            '      <br><label class="labels">' + \
            translate['Timeline banner image'] + '</label>\n' + \
            '      <input type="file" id="banner" name="banner"' + \
            '            accept="' + imageFormats + '">\n' + \
            '      <br><label class="labels">' + \
            translate['Search banner image'] + '</label>\n' + \
            '      <input type="file" id="search_banner" ' + \
            'name="search_banner"' + \
            '            accept="' + imageFormats + '">\n' + \
            '      <br><label class="labels">' + \
            translate['Left column image'] + '</label>\n' + \
            '      <input type="file" id="left_col_image" ' + \
            'name="left_col_image"' + \
            '            accept="' + imageFormats + '">\n' + \
            '      <br><label class="labels">' + \
            translate['Right column image'] + '</label>\n' + \
            '      <input type="file" id="right_col_image" ' + \
            'name="right_col_image"' + \
            '            accept="' + imageFormats + '">\n'

    editProfileForm += endEditSection()
    return editProfileForm


def _htmlEditProfileContactInfo(nickname: str,
                                emailAddress: str,
                                xmppAddress: str,
                                matrixAddress: str,
                                ssbAddress: str,
                                toxAddress: str,
                                briarAddress: str,
                                jamiAddress: str,
                                cwtchAddress: str,
                                translate: {}) -> str:
    """Contact Information section of edit profile screen
    """
    editProfileForm = beginEditSection(translate['Contact Details'])

    editProfileForm += editTextField(translate['Email'],
                                     'email', emailAddress)
    editProfileForm += editTextField(translate['XMPP'],
                                     'xmppAddress', xmppAddress)
    editProfileForm += editTextField(translate['Matrix'],
                                     'matrixAddress', matrixAddress)
    editProfileForm += editTextField('SSB', 'ssbAddress', ssbAddress)
    editProfileForm += editTextField('Tox', 'toxAddress', toxAddress)
    editProfileForm += editTextField('Briar', 'briarAddress', briarAddress)
    editProfileForm += editTextField('Jami', 'jamiAddress', jamiAddress)
    editProfileForm += editTextField('Cwtch', 'cwtchAddress', cwtchAddress)
    editProfileForm += \
        '<a href="/users/' + nickname + \
        '/followingaccounts"><label class="labels">' + \
        translate['Following'] + '</label></a><br>\n'

    editProfileForm += endEditSection()
    return editProfileForm


def _htmlEditProfileEncryptionKeys(PGPfingerprint: str,
                                   PGPpubKey: str,
                                   EnigmaPubKey: str,
                                   translate: {}) -> str:
    """Contact Information section of edit profile screen
    """
    editProfileForm = beginEditSection(translate['Encryption Keys'])

    enigmaUrl = 'https://github.com/enigma-reloaded/enigma-reloaded'
    editProfileForm += \
        editTextField('<a href="' + enigmaUrl + '">Enigma</a>',
                      'enigmapubkey', EnigmaPubKey)
    editProfileForm += editTextField(translate['PGP Fingerprint'],
                                     'openpgp', PGPfingerprint)
    editProfileForm += \
        editTextArea(translate['PGP'], 'pgp', PGPpubKey, 600,
                     '-----BEGIN PGP PUBLIC KEY BLOCK-----', False)

    editProfileForm += endEditSection()
    return editProfileForm


def _htmlEditProfileOptions(isAdmin: bool,
                            manuallyApprovesFollowers: str,
                            isBot: str, isGroup: str,
                            followDMs: str, removeTwitter: str,
                            notifyLikes: str, notifyReactions: str,
                            hideLikeButton: str,
                            hideReactionButton: str,
                            translate: {}) -> str:
    """option checkboxes section of edit profile screen
    """
    editProfileForm = '    <div class="container">\n'
    editProfileForm += \
        editCheckBox(translate['Approve follower requests'],
                     'approveFollowers', manuallyApprovesFollowers)
    editProfileForm += \
        editCheckBox(translate['This is a bot account'],
                     'isBot', isBot)
    if isAdmin:
        editProfileForm += \
            editCheckBox(translate['This is a group account'],
                         'isGroup', isGroup)
    editProfileForm += \
        editCheckBox(translate['Only people I follow can send me DMs'],
                     'followDMs', followDMs)
    editProfileForm += \
        editCheckBox(translate['Remove Twitter posts'],
                     'removeTwitter', removeTwitter)
    editProfileForm += \
        editCheckBox(translate['Notify when posts are liked'],
                     'notifyLikes', notifyLikes)
    editProfileForm += \
        editCheckBox(translate['Notify on emoji reactions'],
                     'notifyReactions', notifyReactions)
    editProfileForm += \
        editCheckBox(translate["Don't show the Like button"],
                     'hideLikeButton', hideLikeButton)
    editProfileForm += \
        editCheckBox(translate["Don't show the Reaction button"],
                     'hideReactionButton', hideReactionButton)
    editProfileForm += '    </div>\n'
    return editProfileForm


def _getSupportedLanguagesSorted(base_dir: str) -> str:
    """Returns a list of supported languages
    """
    langList = getSupportedLanguages(base_dir)
    if not langList:
        return ''
    langList.sort()
    languagesStr = ''
    for lang in langList:
        if languagesStr:
            languagesStr += ' / ' + lang
        else:
            languagesStr = lang
    return languagesStr


def _htmlEditProfileMain(base_dir: str, displayNickname: str, bioStr: str,
                         movedTo: str, donateUrl: str, websiteUrl: str,
                         blogAddress: str, actorJson: {},
                         translate: {}) -> str:
    """main info on edit profile screen
    """
    imageFormats = getImageFormats()

    editProfileForm = '    <div class="container">\n'

    editProfileForm += \
        editTextField(translate['Nickname'], 'displayNickname',
                      displayNickname)

    editProfileForm += \
        editTextArea(translate['Your bio'], 'bio', bioStr, 200, '', True)

    editProfileForm += \
        '      <label class="labels">' + translate['Avatar image'] + \
        '</label>\n' + \
        '      <input type="file" id="avatar" name="avatar"' + \
        '            accept="' + imageFormats + '">\n'

    occupationName = ''
    if actorJson.get('hasOccupation'):
        occupationName = getOccupationName(actorJson)

    editProfileForm += \
        editTextField(translate['Occupation'], 'occupationName',
                      occupationName)

    alsoKnownAsStr = ''
    if actorJson.get('alsoKnownAs'):
        alsoKnownAs = actorJson['alsoKnownAs']
        ctr = 0
        for altActor in alsoKnownAs:
            if ctr > 0:
                alsoKnownAsStr += ', '
            ctr += 1
            alsoKnownAsStr += altActor

    editProfileForm += \
        editTextField(translate['Other accounts'], 'alsoKnownAs',
                      alsoKnownAsStr, 'https://...')

    editProfileForm += \
        editTextField(translate['Moved to new account address'], 'movedTo',
                      movedTo, 'https://...')

    editProfileForm += \
        editTextField(translate['Donations link'], 'donateUrl',
                      donateUrl, 'https://...')

    editProfileForm += \
        editTextField(translate['Website'], 'websiteUrl',
                      websiteUrl, 'https://...')

    editProfileForm += \
        editTextField('Blog', 'blogAddress', blogAddress, 'https://...')

    languagesListStr = _getSupportedLanguagesSorted(base_dir)
    showLanguages = getActorLanguages(actorJson)
    editProfileForm += \
        editTextField(translate['Languages'], 'showLanguages',
                      showLanguages, languagesListStr)

    editProfileForm += '    </div>\n'
    return editProfileForm


def _htmlEditProfileTopBanner(base_dir: str,
                              nickname: str, domain: str, domainFull: str,
                              defaultTimeline: str, bannerFile: str,
                              path: str, accessKeys: {}, translate: {}) -> str:
    """top banner on edit profile screen
    """
    editProfileForm = \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '">' + \
        '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" alt="" /></a>\n'

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
        '        <input type="submit" name="submitProfile" ' + \
        'accesskey="' + accessKeys['submitButton'] + '" ' + \
        'value="' + translate['Submit'] + '">\n' + \
        '      </center>\n'
    editProfileForm += '    </div>\n'

    if scheduledPostsExist(base_dir, nickname, domain):
        editProfileForm += '    <div class="container">\n'
        editProfileForm += \
            editCheckBox(translate['Remove scheduled posts'],
                         'removeScheduledPosts', False)
        editProfileForm += '    </div>\n'
    return editProfileForm


def htmlEditProfile(cssCache: {}, translate: {}, base_dir: str, path: str,
                    domain: str, port: int, http_prefix: str,
                    defaultTimeline: str, theme: str,
                    peertubeInstances: [],
                    textModeBanner: str, city: str,
                    userAgentsBlocked: str,
                    accessKeys: {},
                    defaultReplyIntervalHours: int,
                    CWlists: {}, listsEnabled: str) -> str:
    """Shows the edit profile screen
    """
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '').replace('/wanted', '')
    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''
    domainFull = getFullDomain(domain, port)

    actorFilename = acctDir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        return ''

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        getBannerFile(base_dir, nickname, domain, theme)

    displayNickname = nickname
    isBot = isGroup = followDMs = removeTwitter = ''
    notifyLikes = notifyReactions = ''
    hideLikeButton = hideReactionButton = mediaInstanceStr = ''
    blogsInstanceStr = newsInstanceStr = movedTo = twitterStr = ''
    bioStr = donateUrl = websiteUrl = emailAddress = ''
    PGPpubKey = EnigmaPubKey = ''
    PGPfingerprint = xmppAddress = matrixAddress = ''
    ssbAddress = blogAddress = toxAddress = jamiAddress = ''
    cwtchAddress = briarAddress = manuallyApprovesFollowers = ''

    actorJson = loadJson(actorFilename)
    if actorJson:
        if actorJson.get('movedTo'):
            movedTo = actorJson['movedTo']
        donateUrl = getDonationUrl(actorJson)
        websiteUrl = getWebsite(actorJson, translate)
        xmppAddress = getXmppAddress(actorJson)
        matrixAddress = getMatrixAddress(actorJson)
        ssbAddress = getSSBAddress(actorJson)
        blogAddress = getBlogAddress(actorJson)
        toxAddress = getToxAddress(actorJson)
        briarAddress = getBriarAddress(actorJson)
        jamiAddress = getJamiAddress(actorJson)
        cwtchAddress = getCwtchAddress(actorJson)
        emailAddress = getEmailAddress(actorJson)
        EnigmaPubKey = getEnigmaPubKey(actorJson)
        PGPpubKey = getPGPpubKey(actorJson)
        PGPfingerprint = getPGPfingerprint(actorJson)
        if actorJson.get('name'):
            if not isFiltered(base_dir, nickname, domain, actorJson['name']):
                displayNickname = actorJson['name']
        if actorJson.get('summary'):
            bioStr = \
                actorJson['summary'].replace('<p>', '').replace('</p>', '')
            if isFiltered(base_dir, nickname, domain, bioStr):
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
    accountDir = acctDir(base_dir, nickname, domain)
    if os.path.isfile(accountDir + '/.followDMs'):
        followDMs = 'checked'
    if os.path.isfile(accountDir + '/.removeTwitter'):
        removeTwitter = 'checked'
    if os.path.isfile(accountDir + '/.notifyLikes'):
        notifyLikes = 'checked'
    if os.path.isfile(accountDir + '/.notifyReactions'):
        notifyReactions = 'checked'
    if os.path.isfile(accountDir + '/.hideLikeButton'):
        hideLikeButton = 'checked'
    if os.path.isfile(accountDir + '/.hideReactionButton'):
        hideReactionButton = 'checked'

    mediaInstance = getConfigParam(base_dir, "mediaInstance")
    if mediaInstance:
        if mediaInstance is True:
            mediaInstanceStr = 'checked'
            blogsInstanceStr = newsInstanceStr = ''

    newsInstance = getConfigParam(base_dir, "newsInstance")
    if newsInstance:
        if newsInstance is True:
            newsInstanceStr = 'checked'
            blogsInstanceStr = mediaInstanceStr = ''

    blogsInstance = getConfigParam(base_dir, "blogsInstance")
    if blogsInstance:
        if blogsInstance is True:
            blogsInstanceStr = 'checked'
            mediaInstanceStr = newsInstanceStr = ''

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceStr = ''
    roleAssignStr = ''
    peertubeStr = ''
    libretranslateStr = ''
    systemMonitorStr = ''
    graphicsStr = ''
    sharesFederationStr = ''

    adminNickname = getConfigParam(base_dir, 'admin')

    if isArtist(base_dir, nickname) or \
       path.startswith('/users/' + str(adminNickname) + '/'):
        graphicsStr = _htmlEditProfileGraphicDesign(base_dir, translate)

    isAdmin = False
    if adminNickname:
        if path.startswith('/users/' + adminNickname + '/'):
            isAdmin = True
            twitterStr = \
                _htmlEditProfileTwitter(base_dir, translate, removeTwitter)
            # shared items section
            sharesFederationStr = \
                _htmlEditProfileSharedItems(base_dir, nickname,
                                            domain, translate)
            instanceStr, roleAssignStr, peertubeStr, libretranslateStr = \
                _htmlEditProfileInstance(base_dir, translate,
                                         peertubeInstances,
                                         mediaInstanceStr,
                                         blogsInstanceStr,
                                         newsInstanceStr)
            systemMonitorStr = _htmlSystemMonitor(nickname, translate)

    instanceTitle = getConfigParam(base_dir, 'instanceTitle')
    editProfileForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

    # keyboard navigation
    userPathStr = '/users/' + nickname
    userTimalineStr = '/users/' + nickname + '/' + defaultTimeline
    menuTimeline = \
        htmlHideFromScreenReader('🏠') + ' ' + \
        translate['Switch to timeline view']
    menuProfile = \
        htmlHideFromScreenReader('👤') + ' ' + \
        translate['Switch to profile view']
    navLinks = {
        menuProfile: userPathStr,
        menuTimeline: userTimalineStr
    }
    navAccessKeys = {
        menuProfile: 'p',
        menuTimeline: 't'
    }
    editProfileForm += htmlKeyboardNavigation(textModeBanner,
                                              navLinks, navAccessKeys)

    # top banner
    editProfileForm += \
        _htmlEditProfileTopBanner(base_dir, nickname, domain, domainFull,
                                  defaultTimeline, bannerFile,
                                  path, accessKeys, translate)

    # main info
    editProfileForm += \
        _htmlEditProfileMain(base_dir, displayNickname, bioStr,
                             movedTo, donateUrl, websiteUrl,
                             blogAddress, actorJson, translate)

    # Option checkboxes
    editProfileForm += \
        _htmlEditProfileOptions(isAdmin, manuallyApprovesFollowers,
                                isBot, isGroup, followDMs, removeTwitter,
                                notifyLikes, notifyReactions,
                                hideLikeButton, hideReactionButton,
                                translate)

    # Contact information
    editProfileForm += \
        _htmlEditProfileContactInfo(nickname, emailAddress,
                                    xmppAddress, matrixAddress,
                                    ssbAddress, toxAddress,
                                    briarAddress, jamiAddress,
                                    cwtchAddress, translate)

    # Encryption Keys
    editProfileForm += \
        _htmlEditProfileEncryptionKeys(PGPfingerprint,
                                       PGPpubKey, EnigmaPubKey, translate)

    # Customize images and banners
    editProfileForm += _htmlEditProfileBackground(newsInstance, translate)

    # Change password
    editProfileForm += _htmlEditProfileChangePassword(translate)

    # automatic translations
    editProfileForm += libretranslateStr

    # system monitor
    editProfileForm += systemMonitorStr

    # Filtering and blocking section
    replyIntervalHours = getReplyIntervalHours(base_dir, nickname, domain,
                                               defaultReplyIntervalHours)
    editProfileForm += \
        _htmlEditProfileFiltering(base_dir, nickname, domain,
                                  userAgentsBlocked, translate,
                                  replyIntervalHours,
                                  CWlists, listsEnabled)

    # git projects section
    editProfileForm += \
        _htmlEditProfileGitProjects(base_dir, nickname, domain, translate)

    # Skills section
    editProfileForm += \
        _htmlEditProfileSkills(base_dir, nickname, domain, translate)

    editProfileForm += roleAssignStr + peertubeStr + graphicsStr
    editProfileForm += sharesFederationStr + twitterStr + instanceStr

    # danger zone section
    editProfileForm += _htmlEditProfileDangerZone(translate)

    editProfileForm += '    <div class="container">\n'
    editProfileForm += \
        '      <center>\n' + \
        '        <input type="submit" name="submitProfile" value="' + \
        translate['Submit'] + '">\n' + \
        '      </center>\n'
    editProfileForm += '    </div>\n'

    editProfileForm += '  </div>\n'
    editProfileForm += '</form>\n'
    editProfileForm += htmlFooter()
    return editProfileForm


def _individualFollowAsHtml(signingPrivateKeyPem: str,
                            translate: {},
                            base_dir: str, session,
                            cachedWebfingers: {},
                            personCache: {}, domain: str,
                            followUrl: str,
                            authorized: bool,
                            actorNickname: str,
                            http_prefix: str,
                            projectVersion: str,
                            dormant: bool,
                            debug: bool,
                            buttons=[]) -> str:
    """An individual follow entry on the profile screen
    """
    followUrlNickname = getNicknameFromActor(followUrl)
    followUrlDomain, followUrlPort = getDomainFromActor(followUrl)
    followUrlDomainFull = getFullDomain(followUrlDomain, followUrlPort)
    titleStr = '@' + followUrlNickname + '@' + followUrlDomainFull
    avatarUrl = getPersonAvatarUrl(base_dir, followUrl, personCache, True)
    if not avatarUrl:
        avatarUrl = followUrl + '/avatar.png'

    displayName = getDisplayName(base_dir, followUrl, personCache)
    isGroup = False
    if not displayName:
        # lookup the correct webfinger for the followUrl
        followUrlHandle = followUrlNickname + '@' + followUrlDomainFull
        followUrlWf = \
            webfingerHandle(session, followUrlHandle, http_prefix,
                            cachedWebfingers,
                            domain, __version__, debug, False,
                            signingPrivateKeyPem)

        originDomain = domain
        (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl2,
         displayName, isGroup) = getPersonBox(signingPrivateKeyPem,
                                              originDomain,
                                              base_dir, session,
                                              followUrlWf,
                                              personCache, projectVersion,
                                              http_prefix, followUrlNickname,
                                              domain, 'outbox', 43036)
        if avatarUrl2:
            avatarUrl = avatarUrl2

    if displayName:
        displayName = \
            addEmojiToDisplayName(None, base_dir, http_prefix,
                                  actorNickname, domain,
                                  displayName, False)
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
            elif b == 'unfollow':
                unfollowStr = 'Unfollow'
                if isGroup or \
                   isGroupAccount(base_dir,
                                  followUrlNickname, followUrlDomain):
                    unfollowStr = 'Leave'
                buttonsStr += \
                    '<a href="/users/' + actorNickname + \
                    '?options=' + followUrl + \
                    ';1;' + avatarUrl + '"><button class="buttonunfollow">' + \
                    translate[unfollowStr] + '</button></a>\n'

    resultStr = '<div class="container">\n'
    resultStr += \
        '<a href="/users/' + actorNickname + '?options=' + \
        followUrl + ';1;' + avatarUrl + '">\n'
    resultStr += '<p><img loading="lazy" src="' + avatarUrl + '" alt=" ">'
    resultStr += titleStr + '</a>' + buttonsStr + '</p>\n'
    resultStr += '</div>\n'
    return resultStr
