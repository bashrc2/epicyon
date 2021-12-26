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
from utils import is_group_account
from utils import has_object_dict
from utils import getOccupationName
from utils import get_locked_account
from utils import get_full_domain
from utils import is_artist
from utils import is_dormant
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import isSystemAccount
from utils import removeHtml
from utils import load_json
from utils import get_config_param
from utils import get_image_formats
from utils import acct_dir
from utils import get_supported_languages
from utils import local_actor_url
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


def _validProfilePreviewPost(post_json_object: {},
                             personUrl: str) -> (bool, {}):
    """Returns true if the given post should appear on a person/group profile
    after searching for a handle
    """
    isAnnouncedFeedItem = False
    if isCreateInsideAnnounce(post_json_object):
        isAnnouncedFeedItem = True
        post_json_object = post_json_object['object']
    if not post_json_object.get('type'):
        return False, None
    if post_json_object['type'] == 'Create':
        if not has_object_dict(post_json_object):
            return False, None
    if post_json_object['type'] != 'Create' and \
       post_json_object['type'] != 'Announce':
        if post_json_object['type'] != 'Note' and \
           post_json_object['type'] != 'Page':
            return False, None
        if not post_json_object.get('to'):
            return False, None
        if not post_json_object.get('id'):
            return False, None
        # wrap in create
        cc = []
        if post_json_object.get('cc'):
            cc = post_json_object['cc']
        newPostJsonObject = {
            'object': post_json_object,
            'to': post_json_object['to'],
            'cc': cc,
            'id': post_json_object['id'],
            'actor': personUrl,
            'type': 'Create'
        }
        post_json_object = newPostJsonObject
    if not post_json_object.get('actor'):
        return False, None
    if not isAnnouncedFeedItem:
        if post_json_object['actor'] != personUrl and \
           post_json_object['object']['type'] != 'Page':
            return False, None
    return True, post_json_object


def htmlProfileAfterSearch(cssCache: {},
                           recentPostsCache: {}, max_recent_posts: int,
                           translate: {},
                           base_dir: str, path: str, http_prefix: str,
                           nickname: str, domain: str, port: int,
                           profileHandle: str,
                           session, cached_webfingers: {}, person_cache: {},
                           debug: bool, project_version: str,
                           yt_replace_domain: str,
                           twitter_replacement_domain: str,
                           show_published_date_only: bool,
                           defaultTimeline: str,
                           peertube_instances: [],
                           allow_local_network_access: bool,
                           theme_name: str,
                           accessKeys: {},
                           system_language: str,
                           max_like_count: int,
                           signing_priv_key_pem: str,
                           cw_lists: {}, lists_enabled: str) -> str:
    """Show a profile page after a search for a fediverse address
    """
    http = False
    gnunet = False
    if http_prefix == 'http':
        http = True
    elif http_prefix == 'gnunet':
        gnunet = True
    profile_json, asHeader = \
        getActorJson(domain, profileHandle, http, gnunet, debug, False,
                     signing_priv_key_pem, session)
    if not profile_json:
        return None

    personUrl = profile_json['id']
    searchDomain, searchPort = getDomainFromActor(personUrl)
    if not searchDomain:
        return None
    searchNickname = getNicknameFromActor(personUrl)
    if not searchNickname:
        return None
    searchDomainFull = get_full_domain(searchDomain, searchPort)

    profileStr = ''
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    isGroup = False
    if profile_json.get('type'):
        if profile_json['type'] == 'Group':
            isGroup = True

    avatarUrl = ''
    if profile_json.get('icon'):
        if profile_json['icon'].get('url'):
            avatarUrl = profile_json['icon']['url']
    if not avatarUrl:
        avatarUrl = getPersonAvatarUrl(base_dir, personUrl,
                                       person_cache, True)
    displayName = searchNickname
    if profile_json.get('name'):
        displayName = profile_json['name']

    lockedAccount = get_locked_account(profile_json)
    if lockedAccount:
        displayName += '🔒'
    movedTo = ''
    if profile_json.get('movedTo'):
        movedTo = profile_json['movedTo']
        if '"' in movedTo:
            movedTo = movedTo.split('"')[1]
        displayName += ' ⌂'

    followsYou = \
        isFollowerOfPerson(base_dir,
                           nickname, domain,
                           searchNickname,
                           searchDomainFull)

    profileDescription = ''
    if profile_json.get('summary'):
        profileDescription = profile_json['summary']
    outboxUrl = None
    if not profile_json.get('outbox'):
        if debug:
            pprint(profile_json)
            print('DEBUG: No outbox found')
        return None
    outboxUrl = profile_json['outbox']

    # profileBackgroundImage = ''
    # if profile_json.get('image'):
    #     if profile_json['image'].get('url'):
    #         profileBackgroundImage = profile_json['image']['url']

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
    if profile_json.get('summary'):
        if isinstance(profile_json['summary'], str):
            avatarDescription = \
                profile_json['summary'].replace('<br>', '\n')
            avatarDescription = avatarDescription.replace('<p>', '')
            avatarDescription = avatarDescription.replace('</p>', '')
            if '<' in avatarDescription:
                avatarDescription = removeHtml(avatarDescription)

    imageUrl = ''
    if profile_json.get('image'):
        if profile_json['image'].get('url'):
            imageUrl = profile_json['image']['url']

    alsoKnownAs = None
    if profile_json.get('alsoKnownAs'):
        alsoKnownAs = profile_json['alsoKnownAs']

    joinedDate = None
    if profile_json.get('published'):
        if 'T' in profile_json['published']:
            joinedDate = profile_json['published']

    profileStr = \
        _getProfileHeaderAfterSearch(base_dir,
                                     nickname, defaultTimeline,
                                     searchNickname,
                                     searchDomainFull,
                                     translate,
                                     displayName, followsYou,
                                     profileDescriptionShort,
                                     avatarUrl, imageUrl,
                                     movedTo, profile_json['id'],
                                     alsoKnownAs, accessKeys,
                                     joinedDate)

    domain_full = get_full_domain(domain, port)

    followIsPermitted = True
    if not profile_json.get('followers'):
        # no followers collection specified within actor
        followIsPermitted = False
    elif searchNickname == 'news' and searchDomainFull == domain_full:
        # currently the news actor is not something you can follow
        followIsPermitted = False
    elif searchNickname == nickname and searchDomainFull == domain_full:
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
        parseUserFeed(signing_priv_key_pem,
                      session, outboxUrl, asHeader, project_version,
                      http_prefix, domain, debug)
    if userFeed:
        i = 0
        for item in userFeed:
            showItem, post_json_object = \
                _validProfilePreviewPost(item, personUrl)
            if not showItem:
                continue

            profileStr += \
                individualPostAsHtml(signing_priv_key_pem,
                                     True, recentPostsCache,
                                     max_recent_posts,
                                     translate, None, base_dir,
                                     session, cached_webfingers, person_cache,
                                     nickname, domain, port,
                                     post_json_object, avatarUrl,
                                     False, False,
                                     http_prefix, project_version, 'inbox',
                                     yt_replace_domain,
                                     twitter_replacement_domain,
                                     show_published_date_only,
                                     peertube_instances,
                                     allow_local_network_access,
                                     theme_name, system_language,
                                     max_like_count,
                                     False, False, False, False, False, False,
                                     cw_lists, lists_enabled)
            i += 1
            if i >= 8:
                break

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    return htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None) + \
        profileStr + htmlFooter()


def _getProfileHeader(base_dir: str, http_prefix: str,
                      nickname: str, domain: str,
                      domain_full: str, translate: {},
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
        '    <p><b>@' + nickname + '@' + domain_full + '</b><br>\n'
    if joinedDate:
        htmlStr += \
            '    <p>' + translate['Joined'] + ' ' + \
            joinedDate.split('T')[0] + '<br>\n'
    if movedTo:
        newNickname = getNicknameFromActor(movedTo)
        newDomain, newPort = getDomainFromActor(movedTo)
        newDomainFull = get_full_domain(newDomain, newPort)
        if newNickname and newDomain:
            htmlStr += \
                '    <p>' + translate['New account'] + ': ' + \
                '<a href="' + movedTo + '">@' + \
                newNickname + '@' + newDomainFull + '</a><br>\n'
    elif alsoKnownAs:
        otherAccountsHtml = \
            '    <p>' + translate['Other accounts'] + ': '

        actor = local_actor_url(http_prefix, nickname, domain_full)
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
        newDomainFull = get_full_domain(newDomain, newPort)
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


def htmlProfile(signing_priv_key_pem: str,
                rss_icon_at_top: bool,
                cssCache: {}, icons_as_buttons: bool,
                defaultTimeline: str,
                recentPostsCache: {}, max_recent_posts: int,
                translate: {}, project_version: str,
                base_dir: str, http_prefix: str, authorized: bool,
                profile_json: {}, selected: str,
                session, cached_webfingers: {}, person_cache: {},
                yt_replace_domain: str,
                twitter_replacement_domain: str,
                show_published_date_only: bool,
                newswire: {}, theme: str, dormant_months: int,
                peertube_instances: [],
                allow_local_network_access: bool,
                text_mode_banner: str,
                debug: bool, accessKeys: {}, city: str,
                system_language: str, max_like_count: int,
                shared_items_federated_domains: [],
                extraJson: {}, pageNumber: int,
                maxItemsPerPage: int,
                cw_lists: {}, lists_enabled: str,
                content_license_url: str) -> str:
    """Show the profile page as html
    """
    nickname = profile_json['preferredUsername']
    if not nickname:
        return ""
    if isSystemAccount(nickname):
        return htmlFrontScreen(signing_priv_key_pem,
                               rss_icon_at_top,
                               cssCache, icons_as_buttons,
                               defaultTimeline,
                               recentPostsCache, max_recent_posts,
                               translate, project_version,
                               base_dir, http_prefix, authorized,
                               profile_json, selected,
                               session, cached_webfingers, person_cache,
                               yt_replace_domain,
                               twitter_replacement_domain,
                               show_published_date_only,
                               newswire, theme, extraJson,
                               allow_local_network_access, accessKeys,
                               system_language, max_like_count,
                               shared_items_federated_domains, None,
                               pageNumber, maxItemsPerPage, cw_lists,
                               lists_enabled)

    domain, port = getDomainFromActor(profile_json['id'])
    if not domain:
        return ""
    displayName = \
        addEmojiToDisplayName(session, base_dir, http_prefix,
                              nickname, domain,
                              profile_json['name'], True)
    domain_full = get_full_domain(domain, port)
    profileDescription = \
        addEmojiToDisplayName(session, base_dir, http_prefix,
                              nickname, domain,
                              profile_json['summary'], False)
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
    actor = profile_json['id']
    usersPath = '/users/' + actor.split('/users/')[1]

    donateSection = ''
    donateUrl = getDonationUrl(profile_json)
    websiteUrl = getWebsite(profile_json, translate)
    blogAddress = getBlogAddress(profile_json)
    EnigmaPubKey = getEnigmaPubKey(profile_json)
    PGPpubKey = getPGPpubKey(profile_json)
    PGPfingerprint = getPGPfingerprint(profile_json)
    emailAddress = getEmailAddress(profile_json)
    xmppAddress = getXmppAddress(profile_json)
    matrixAddress = getMatrixAddress(profile_json)
    ssbAddress = getSSBAddress(profile_json)
    toxAddress = getToxAddress(profile_json)
    briarAddress = getBriarAddress(profile_json)
    jamiAddress = getJamiAddress(profile_json)
    cwtchAddress = getCwtchAddress(profile_json)
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
            acct_dir(base_dir, nickname, domain) + '/followrequests.txt'
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
                                    local_actor_url(http_prefix, nick, dom)

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
    if profile_json.get('summary'):
        avatarDescription = profile_json['summary'].replace('<br>', '\n')
        avatarDescription = avatarDescription.replace('<p>', '')
        avatarDescription = avatarDescription.replace('</p>', '')

    movedTo = ''
    if profile_json.get('movedTo'):
        movedTo = profile_json['movedTo']
        if '"' in movedTo:
            movedTo = movedTo.split('"')[1]

    alsoKnownAs = None
    if profile_json.get('alsoKnownAs'):
        alsoKnownAs = profile_json['alsoKnownAs']

    joinedDate = None
    if profile_json.get('published'):
        if 'T' in profile_json['published']:
            joinedDate = profile_json['published']
    occupationName = None
    if profile_json.get('hasOccupation'):
        occupationName = getOccupationName(profile_json)

    avatarUrl = profile_json['icon']['url']
    # use alternate path for local avatars to avoid any caching issues
    if '://' + domain_full + '/system/accounts/avatars/' in avatarUrl:
        avatarUrl = \
            avatarUrl.replace('://' + domain_full +
                              '/system/accounts/avatars/',
                              '://' + domain_full + '/users/')

    # get pinned post content
    accountDir = acct_dir(base_dir, nickname, domain)
    pinnedFilename = accountDir + '/pinToProfile.txt'
    pinnedContent = None
    if os.path.isfile(pinnedFilename):
        with open(pinnedFilename, 'r') as pinFile:
            pinnedContent = pinFile.read()

    profileHeaderStr = \
        _getProfileHeader(base_dir, http_prefix,
                          nickname, domain,
                          domain_full, translate,
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
    if is_group_account(base_dir, nickname, domain):
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
    if is_artist(base_dir, nickname):
        menuThemeDesigner = \
            htmlHideFromScreenReader('🎨') + ' ' + translate['Theme Designer']
        navLinks[menuThemeDesigner] = userPathStr + '/themedesigner'
    navAccessKeys = {}
    for variableName, key in accessKeys.items():
        if not locals().get(variableName):
            continue
        navAccessKeys[locals()[variableName]] = key

    profileStr = htmlKeyboardNavigation(text_mode_banner,
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
            _htmlProfilePosts(recentPostsCache, max_recent_posts,
                              translate,
                              base_dir, http_prefix, authorized,
                              nickname, domain, port,
                              session, cached_webfingers, person_cache,
                              project_version,
                              yt_replace_domain,
                              twitter_replacement_domain,
                              show_published_date_only,
                              peertube_instances,
                              allow_local_network_access,
                              theme, system_language,
                              max_like_count,
                              signing_priv_key_pem,
                              cw_lists, lists_enabled) + licenseStr
    if not isGroup:
        if selected == 'following':
            profileStr += \
                _htmlProfileFollowing(translate, base_dir, http_prefix,
                                      authorized, nickname,
                                      domain, port, session,
                                      cached_webfingers,
                                      person_cache, extraJson,
                                      project_version, ["unfollow"], selected,
                                      usersPath, pageNumber, maxItemsPerPage,
                                      dormant_months, debug,
                                      signing_priv_key_pem)
    if selected == 'followers':
        profileStr += \
            _htmlProfileFollowing(translate, base_dir, http_prefix,
                                  authorized, nickname,
                                  domain, port, session,
                                  cached_webfingers,
                                  person_cache, extraJson,
                                  project_version, ["block"],
                                  selected, usersPath, pageNumber,
                                  maxItemsPerPage, dormant_months, debug,
                                  signing_priv_key_pem)
    if not isGroup:
        if selected == 'roles':
            profileStr += \
                _htmlProfileRoles(translate, nickname, domain_full,
                                  extraJson)
        elif selected == 'skills':
            profileStr += \
                _htmlProfileSkills(translate, nickname, domain_full, extraJson)
#       elif selected == 'shares':
#           profileStr += \
#                _htmlProfileShares(actor, translate,
#                                   nickname, domain_full,
#                                   extraJson, 'shares') + licenseStr
#        elif selected == 'wanted':
#            profileStr += \
#                _htmlProfileShares(actor, translate,
#                                   nickname, domain_full,
#                                   extraJson, 'wanted') + licenseStr
    # end of #timeline
    profileStr += '</div>'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    profileStr = \
        htmlHeaderWithPersonMarkup(cssFilename, instanceTitle,
                                   profile_json, city,
                                   content_license_url) + \
        profileStr + htmlFooter()
    return profileStr


def _htmlProfilePosts(recentPostsCache: {}, max_recent_posts: int,
                      translate: {},
                      base_dir: str, http_prefix: str,
                      authorized: bool,
                      nickname: str, domain: str, port: int,
                      session, cached_webfingers: {}, person_cache: {},
                      project_version: str,
                      yt_replace_domain: str,
                      twitter_replacement_domain: str,
                      show_published_date_only: bool,
                      peertube_instances: [],
                      allow_local_network_access: bool,
                      theme_name: str, system_language: str,
                      max_like_count: int,
                      signing_priv_key_pem: str,
                      cw_lists: {}, lists_enabled: str) -> str:
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
                    individualPostAsHtml(signing_priv_key_pem,
                                         True, recentPostsCache,
                                         max_recent_posts,
                                         translate, None,
                                         base_dir, session, cached_webfingers,
                                         person_cache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         http_prefix, project_version, 'inbox',
                                         yt_replace_domain,
                                         twitter_replacement_domain,
                                         show_published_date_only,
                                         peertube_instances,
                                         allow_local_network_access,
                                         theme_name, system_language,
                                         max_like_count,
                                         False, False, False,
                                         True, False, False,
                                         cw_lists, lists_enabled)
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
                          session, cached_webfingers: {}, person_cache: {},
                          followingJson: {}, project_version: str,
                          buttons: [],
                          feedName: str, actor: str,
                          pageNumber: int,
                          maxItemsPerPage: int,
                          dormant_months: int, debug: bool,
                          signing_priv_key_pem: str) -> str:
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
                is_dormant(base_dir, nickname, domain, followingActor,
                           dormant_months)

        profileStr += \
            _individualFollowAsHtml(signing_priv_key_pem,
                                    translate, base_dir, session,
                                    cached_webfingers, person_cache,
                                    domain, followingActor,
                                    authorized, nickname,
                                    http_prefix, project_version, dormant,
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
    for theme_name in themes:
        translatedThemeName = theme_name
        if translate.get(theme_name):
            translatedThemeName = translate[theme_name]
        themesDropdown += '    <option value="' + \
            theme_name.lower() + '">' + \
            translatedThemeName + '</option>'
    themesDropdown += '  </select><br>'
    if os.path.isfile(base_dir + '/fonts/custom.woff') or \
       os.path.isfile(base_dir + '/fonts/custom.woff2') or \
       os.path.isfile(base_dir + '/fonts/custom.otf') or \
       os.path.isfile(base_dir + '/fonts/custom.ttf'):
        themesDropdown += \
            editCheckBox(translate['Remove the custom font'],
                         'removeCustomFont', False)
    theme_name = get_config_param(base_dir, 'theme')
    themesDropdown = \
        themesDropdown.replace('<option value="' + theme_name + '">',
                               '<option value="' + theme_name +
                               '" selected>')
    return themesDropdown


def _htmlEditProfileGraphicDesign(base_dir: str, translate: {}) -> str:
    """Graphic design section on Edit Profile screen
    """
    themeFormats = '.zip, .gz'

    graphicsStr = beginEditSection(translate['Graphic Design'])

    low_bandwidth = get_config_param(base_dir, 'low_bandwidth')
    if not low_bandwidth:
        low_bandwidth = False
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
        editCheckBox(translate['Low Bandwidth'], 'low_bandwidth',
                     bool(low_bandwidth))

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
    twitter_replacement_domain = get_config_param(base_dir, "twitterdomain")
    if not twitter_replacement_domain:
        twitter_replacement_domain = ''
    twitterStr += \
        editTextField(translate['Twitter Replacement Domain'],
                      'twitterdomain', twitter_replacement_domain)
    twitterStr += endEditSection()
    return twitterStr


def _htmlEditProfileInstance(base_dir: str, translate: {},
                             peertube_instances: [],
                             media_instanceStr: str,
                             blogs_instanceStr: str,
                             news_instanceStr: str) -> (str, str, str, str):
    """Edit profile instance settings
    """
    imageFormats = get_image_formats()

    # Instance details section
    instanceDescription = \
        get_config_param(base_dir, 'instanceDescription')
    customSubmitText = \
        get_config_param(base_dir, 'customSubmitText')
    instanceDescriptionShort = \
        get_config_param(base_dir, 'instanceDescriptionShort')
    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    content_license_url = \
        get_config_param(base_dir, 'content_license_url')
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
    if get_config_param(base_dir, "show_node_info_accounts"):
        instanceStr += \
            editCheckBox(nodeInfoStr, 'show_node_info_accounts', True)
    else:
        instanceStr += \
            editCheckBox(nodeInfoStr, 'show_node_info_accounts', False)

    nodeInfoStr = \
        translate['Show version number within instance metadata']
    if get_config_param(base_dir, "show_node_info_version"):
        instanceStr += \
            editCheckBox(nodeInfoStr, 'show_node_info_version', True)
    else:
        instanceStr += \
            editCheckBox(nodeInfoStr, 'show_node_info_version', False)

    if get_config_param(base_dir, "verify_all_signatures"):
        instanceStr += \
            editCheckBox(translate['Verify all signatures'],
                         'verifyallsignatures', True)
    else:
        instanceStr += \
            editCheckBox(translate['Verify all signatures'],
                         'verifyallsignatures', False)

    instanceStr += translate['Enabling broch mode'] + '<br>\n'
    if get_config_param(base_dir, "broch_mode"):
        instanceStr += \
            editCheckBox(translate['Broch mode'], 'broch_mode', True)
    else:
        instanceStr += \
            editCheckBox(translate['Broch mode'], 'broch_mode', False)
    # Instance type
    instanceStr += \
        '  <br><label class="labels">' + \
        translate['Type of instance'] + '</label><br>\n'
    instanceStr += \
        editCheckBox(translate['This is a media instance'],
                     'media_instance', media_instanceStr)
    instanceStr += \
        editCheckBox(translate['This is a blogging instance'],
                     'blogs_instance', blogs_instanceStr)
    instanceStr += \
        editCheckBox(translate['This is a news instance'],
                     'news_instance', news_instanceStr)

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
    peertube_instancesStr = ''
    for url in peertube_instances:
        peertube_instancesStr += url + '\n'
    peertubeStr += \
        editTextArea(translate['Peertube Instances'], 'ptInstances',
                     peertube_instancesStr, 200, '', False)
    peertubeStr += \
        '      <br>\n'
    yt_replace_domain = get_config_param(base_dir, "youtubedomain")
    if not yt_replace_domain:
        yt_replace_domain = ''
    peertubeStr += \
        editTextField(translate['YouTube Replacement Domain'],
                      'ytdomain', yt_replace_domain)
    peertubeStr += endEditSection()

    libretranslateUrl = get_config_param(base_dir, 'libretranslateUrl')
    libretranslateApiKey = get_config_param(base_dir, 'libretranslateApiKey')
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
        acct_dir(base_dir, nickname, domain) + '/gitprojects.txt'
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
    shared_items_federated_domainsStr = \
        get_config_param(base_dir, 'shared_items_federated_domains')
    if shared_items_federated_domainsStr:
        shared_items_federated_domainsList = \
            shared_items_federated_domainsStr.split(',')
        for sharedFederatedDomain in shared_items_federated_domainsList:
            sharedItemsStr += sharedFederatedDomain.strip() + '\n'

    editProfileForm = beginEditSection(translate['Shares'])
    idx = 'List of domains which can access the shared items catalog'
    editProfileForm += \
        editTextArea(translate[idx], 'shareDomainList',
                     sharedItemsStr, 200, '', False)
    editProfileForm += endEditSection()
    return editProfileForm


def _htmlEditProfileFiltering(base_dir: str, nickname: str, domain: str,
                              user_agents_blocked: str,
                              translate: {}, replyIntervalHours: int,
                              cw_lists: {}, lists_enabled: str) -> str:
    """Filtering and blocking section of edit profile screen
    """
    filterStr = ''
    filterFilename = \
        acct_dir(base_dir, nickname, domain) + '/filters.txt'
    if os.path.isfile(filterFilename):
        with open(filterFilename, 'r') as filterfile:
            filterStr = filterfile.read()

    filterBioStr = ''
    filterBioFilename = \
        acct_dir(base_dir, nickname, domain) + '/filters_bio.txt'
    if os.path.isfile(filterBioFilename):
        with open(filterBioFilename, 'r') as filterfile:
            filterBioStr = filterfile.read()

    switchStr = ''
    switchFilename = \
        acct_dir(base_dir, nickname, domain) + '/replacewords.txt'
    if os.path.isfile(switchFilename):
        with open(switchFilename, 'r') as switchfile:
            switchStr = switchfile.read()

    autoTags = ''
    autoTagsFilename = \
        acct_dir(base_dir, nickname, domain) + '/autotags.txt'
    if os.path.isfile(autoTagsFilename):
        with open(autoTagsFilename, 'r') as autoTagsFile:
            autoTags = autoTagsFile.read()

    autoCW = ''
    autoCWFilename = \
        acct_dir(base_dir, nickname, domain) + '/autocw.txt'
    if os.path.isfile(autoCWFilename):
        with open(autoCWFilename, 'r') as autoCWFile:
            autoCW = autoCWFile.read()

    blockedStr = ''
    blockedFilename = \
        acct_dir(base_dir, nickname, domain) + '/blocking.txt'
    if os.path.isfile(blockedFilename):
        with open(blockedFilename, 'r') as blockedfile:
            blockedStr = blockedfile.read()

    dmAllowedInstancesStr = ''
    dmAllowedInstancesFilename = \
        acct_dir(base_dir, nickname, domain) + '/dmAllowedInstances.txt'
    if os.path.isfile(dmAllowedInstancesFilename):
        with open(dmAllowedInstancesFilename, 'r') as dmAllowedInstancesFile:
            dmAllowedInstancesStr = dmAllowedInstancesFile.read()

    allowedInstancesStr = ''
    allowedInstancesFilename = \
        acct_dir(base_dir, nickname, domain) + '/allowedinstances.txt'
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
    cityFilename = acct_dir(base_dir, nickname, domain) + '/city.txt'
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

        user_agents_blockedStr = ''
        for ua in user_agents_blocked:
            if user_agents_blockedStr:
                user_agents_blockedStr += '\n'
            user_agents_blockedStr += ua
        editProfileForm += \
            editTextArea(translate['Blocked User Agents'],
                         'user_agents_blockedStr', user_agents_blockedStr,
                         200, '', False)

        cw_listsStr = ''
        for name, item in cw_lists.items():
            variableName = getCWlistVariable(name)
            listIsEnabled = False
            if lists_enabled:
                if name in lists_enabled:
                    listIsEnabled = True
            if translate.get(name):
                name = translate[name]
            cw_listsStr += editCheckBox(name, variableName, listIsEnabled)
        if cw_listsStr:
            idx = 'Add content warnings for the following sites'
            editProfileForm += \
                '<label class="labels">' + translate[idx] + ':</label>\n' + \
                '<br>' + cw_listsStr

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


def _htmlEditProfileBackground(news_instance: bool, translate: {}) -> str:
    """Background images section of edit profile screen
    """
    idx = 'The files attached below should be no larger than ' + \
        '10MB in total uploaded at once.'
    editProfileForm = \
        beginEditSection(translate['Background Images']) + \
        '      <label class="labels">' + translate[idx] + '</label><br><br>\n'

    if not news_instance:
        imageFormats = get_image_formats()
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


def _get_supported_languagesSorted(base_dir: str) -> str:
    """Returns a list of supported languages
    """
    lang_list = get_supported_languages(base_dir)
    if not lang_list:
        return ''
    lang_list.sort()
    languagesStr = ''
    for lang in lang_list:
        if languagesStr:
            languagesStr += ' / ' + lang
        else:
            languagesStr = lang
    return languagesStr


def _htmlEditProfileMain(base_dir: str, displayNickname: str, bioStr: str,
                         movedTo: str, donateUrl: str, websiteUrl: str,
                         blogAddress: str, actor_json: {},
                         translate: {}) -> str:
    """main info on edit profile screen
    """
    imageFormats = get_image_formats()

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
    if actor_json.get('hasOccupation'):
        occupationName = getOccupationName(actor_json)

    editProfileForm += \
        editTextField(translate['Occupation'], 'occupationName',
                      occupationName)

    alsoKnownAsStr = ''
    if actor_json.get('alsoKnownAs'):
        alsoKnownAs = actor_json['alsoKnownAs']
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

    languagesListStr = _get_supported_languagesSorted(base_dir)
    showLanguages = getActorLanguages(actor_json)
    editProfileForm += \
        editTextField(translate['Languages'], 'showLanguages',
                      showLanguages, languagesListStr)

    editProfileForm += '    </div>\n'
    return editProfileForm


def _htmlEditProfileTopBanner(base_dir: str,
                              nickname: str, domain: str, domain_full: str,
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
        ' ' + nickname + '@' + domain_full + '</h1>'
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
                    peertube_instances: [],
                    text_mode_banner: str, city: str,
                    user_agents_blocked: str,
                    accessKeys: {},
                    default_reply_interval_hrs: int,
                    cw_lists: {}, lists_enabled: str) -> str:
    """Shows the edit profile screen
    """
    path = path.replace('/inbox', '').replace('/outbox', '')
    path = path.replace('/shares', '').replace('/wanted', '')
    nickname = getNicknameFromActor(path)
    if not nickname:
        return ''
    domain_full = get_full_domain(domain, port)

    actorFilename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        return ''

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        getBannerFile(base_dir, nickname, domain, theme)

    displayNickname = nickname
    isBot = isGroup = followDMs = removeTwitter = ''
    notifyLikes = notifyReactions = ''
    hideLikeButton = hideReactionButton = media_instanceStr = ''
    blogs_instanceStr = news_instanceStr = movedTo = twitterStr = ''
    bioStr = donateUrl = websiteUrl = emailAddress = ''
    PGPpubKey = EnigmaPubKey = ''
    PGPfingerprint = xmppAddress = matrixAddress = ''
    ssbAddress = blogAddress = toxAddress = jamiAddress = ''
    cwtchAddress = briarAddress = manuallyApprovesFollowers = ''

    actor_json = load_json(actorFilename)
    if actor_json:
        if actor_json.get('movedTo'):
            movedTo = actor_json['movedTo']
        donateUrl = getDonationUrl(actor_json)
        websiteUrl = getWebsite(actor_json, translate)
        xmppAddress = getXmppAddress(actor_json)
        matrixAddress = getMatrixAddress(actor_json)
        ssbAddress = getSSBAddress(actor_json)
        blogAddress = getBlogAddress(actor_json)
        toxAddress = getToxAddress(actor_json)
        briarAddress = getBriarAddress(actor_json)
        jamiAddress = getJamiAddress(actor_json)
        cwtchAddress = getCwtchAddress(actor_json)
        emailAddress = getEmailAddress(actor_json)
        EnigmaPubKey = getEnigmaPubKey(actor_json)
        PGPpubKey = getPGPpubKey(actor_json)
        PGPfingerprint = getPGPfingerprint(actor_json)
        if actor_json.get('name'):
            if not isFiltered(base_dir, nickname, domain, actor_json['name']):
                displayNickname = actor_json['name']
        if actor_json.get('summary'):
            bioStr = \
                actor_json['summary'].replace('<p>', '').replace('</p>', '')
            if isFiltered(base_dir, nickname, domain, bioStr):
                bioStr = ''
        if actor_json.get('manuallyApprovesFollowers'):
            if actor_json['manuallyApprovesFollowers']:
                manuallyApprovesFollowers = 'checked'
            else:
                manuallyApprovesFollowers = ''
        if actor_json.get('type'):
            if actor_json['type'] == 'Service':
                isBot = 'checked'
                isGroup = ''
            elif actor_json['type'] == 'Group':
                isGroup = 'checked'
                isBot = ''
    accountDir = acct_dir(base_dir, nickname, domain)
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

    media_instance = get_config_param(base_dir, "media_instance")
    if media_instance:
        if media_instance is True:
            media_instanceStr = 'checked'
            blogs_instanceStr = news_instanceStr = ''

    news_instance = get_config_param(base_dir, "news_instance")
    if news_instance:
        if news_instance is True:
            news_instanceStr = 'checked'
            blogs_instanceStr = media_instanceStr = ''

    blogs_instance = get_config_param(base_dir, "blogs_instance")
    if blogs_instance:
        if blogs_instance is True:
            blogs_instanceStr = 'checked'
            media_instanceStr = news_instanceStr = ''

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

    adminNickname = get_config_param(base_dir, 'admin')

    if is_artist(base_dir, nickname) or \
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
                                         peertube_instances,
                                         media_instanceStr,
                                         blogs_instanceStr,
                                         news_instanceStr)
            systemMonitorStr = _htmlSystemMonitor(nickname, translate)

    instanceTitle = get_config_param(base_dir, 'instanceTitle')
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
    editProfileForm += htmlKeyboardNavigation(text_mode_banner,
                                              navLinks, navAccessKeys)

    # top banner
    editProfileForm += \
        _htmlEditProfileTopBanner(base_dir, nickname, domain, domain_full,
                                  defaultTimeline, bannerFile,
                                  path, accessKeys, translate)

    # main info
    editProfileForm += \
        _htmlEditProfileMain(base_dir, displayNickname, bioStr,
                             movedTo, donateUrl, websiteUrl,
                             blogAddress, actor_json, translate)

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
    editProfileForm += _htmlEditProfileBackground(news_instance, translate)

    # Change password
    editProfileForm += _htmlEditProfileChangePassword(translate)

    # automatic translations
    editProfileForm += libretranslateStr

    # system monitor
    editProfileForm += systemMonitorStr

    # Filtering and blocking section
    replyIntervalHours = getReplyIntervalHours(base_dir, nickname, domain,
                                               default_reply_interval_hrs)
    editProfileForm += \
        _htmlEditProfileFiltering(base_dir, nickname, domain,
                                  user_agents_blocked, translate,
                                  replyIntervalHours,
                                  cw_lists, lists_enabled)

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


def _individualFollowAsHtml(signing_priv_key_pem: str,
                            translate: {},
                            base_dir: str, session,
                            cached_webfingers: {},
                            person_cache: {}, domain: str,
                            followUrl: str,
                            authorized: bool,
                            actorNickname: str,
                            http_prefix: str,
                            project_version: str,
                            dormant: bool,
                            debug: bool,
                            buttons=[]) -> str:
    """An individual follow entry on the profile screen
    """
    followUrlNickname = getNicknameFromActor(followUrl)
    followUrlDomain, followUrlPort = getDomainFromActor(followUrl)
    followUrlDomainFull = get_full_domain(followUrlDomain, followUrlPort)
    titleStr = '@' + followUrlNickname + '@' + followUrlDomainFull
    avatarUrl = getPersonAvatarUrl(base_dir, followUrl, person_cache, True)
    if not avatarUrl:
        avatarUrl = followUrl + '/avatar.png'

    displayName = getDisplayName(base_dir, followUrl, person_cache)
    isGroup = False
    if not displayName:
        # lookup the correct webfinger for the followUrl
        followUrlHandle = followUrlNickname + '@' + followUrlDomainFull
        followUrlWf = \
            webfingerHandle(session, followUrlHandle, http_prefix,
                            cached_webfingers,
                            domain, __version__, debug, False,
                            signing_priv_key_pem)

        originDomain = domain
        (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl2,
         displayName, isGroup) = getPersonBox(signing_priv_key_pem,
                                              originDomain,
                                              base_dir, session,
                                              followUrlWf,
                                              person_cache, project_version,
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
                   is_group_account(base_dir,
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
