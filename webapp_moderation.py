__filename__ = "webapp_moderation.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Moderation"

import os
from utils import is_artist
from utils import is_account_dir
from utils import get_full_domain
from utils import is_editor
from utils import load_json
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import get_config_param
from utils import local_actor_url
from posts import download_follow_collection
from posts import get_public_post_info
from posts import is_moderator
from webapp_timeline import html_timeline
# from webapp_utils import get_person_avatar_url
from webapp_utils import get_content_warning_button
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from blocking import is_blocked_domain
from blocking import is_blocked
from session import create_session


def html_moderation(css_cache: {}, defaultTimeline: str,
                    recent_posts_cache: {}, max_recent_posts: int,
                    translate: {}, pageNumber: int, itemsPerPage: int,
                    session, base_dir: str, wfRequest: {}, person_cache: {},
                    nickname: str, domain: str, port: int, inboxJson: {},
                    allow_deletion: bool,
                    http_prefix: str, project_version: str,
                    yt_replace_domain: str,
                    twitter_replacement_domain: str,
                    show_published_date_only: bool,
                    newswire: {}, positive_voting: bool,
                    show_publish_as_icon: bool,
                    full_width_tl_button_header: bool,
                    icons_as_buttons: bool,
                    rss_icon_at_top: bool,
                    publish_button_at_top: bool,
                    authorized: bool, moderationActionStr: str,
                    theme: str, peertube_instances: [],
                    allow_local_network_access: bool,
                    text_mode_banner: str,
                    accessKeys: {}, system_language: str,
                    max_like_count: int,
                    shared_items_federated_domains: [],
                    signing_priv_key_pem: str,
                    cw_lists: {}, lists_enabled: str) -> str:
    """Show the moderation feed as html
    This is what you see when selecting the "mod" timeline
    """
    artist = is_artist(base_dir, nickname)
    return html_timeline(css_cache, defaultTimeline,
                         recent_posts_cache, max_recent_posts,
                         translate, pageNumber,
                         itemsPerPage, session, base_dir,
                         wfRequest, person_cache,
                         nickname, domain, port, inboxJson, 'moderation',
                         allow_deletion, http_prefix,
                         project_version, True, False,
                         yt_replace_domain,
                         twitter_replacement_domain,
                         show_published_date_only,
                         newswire, False, False, artist, positive_voting,
                         show_publish_as_icon,
                         full_width_tl_button_header,
                         icons_as_buttons, rss_icon_at_top,
                         publish_button_at_top,
                         authorized, moderationActionStr, theme,
                         peertube_instances, allow_local_network_access,
                         text_mode_banner, accessKeys, system_language,
                         max_like_count, shared_items_federated_domains,
                         signing_priv_key_pem, cw_lists, lists_enabled)


def html_account_info(css_cache: {}, translate: {},
                      base_dir: str, http_prefix: str,
                      nickname: str, domain: str, port: int,
                      searchHandle: str, debug: bool,
                      system_language: str, signing_priv_key_pem: str) -> str:
    """Shows which domains a search handle interacts with.
    This screen is shown if a moderator enters a handle and selects info
    on the moderation screen
    """
    signing_priv_key_pem = None
    msgStr1 = 'This account interacts with the following instances'

    infoForm = ''
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    infoForm = \
        html_header_with_external_style(cssFilename, instanceTitle, None)

    searchNickname = get_nickname_from_actor(searchHandle)
    searchDomain, searchPort = get_domain_from_actor(searchHandle)

    searchHandle = searchNickname + '@' + searchDomain
    searchActor = \
        local_actor_url(http_prefix, searchNickname, searchDomain)
    infoForm += \
        '<center><h1><a href="/users/' + nickname + '/moderation">' + \
        translate['Account Information'] + ':</a> <a href="' + searchActor + \
        '">' + searchHandle + '</a></h1><br>\n'

    infoForm += translate[msgStr1] + '</center><br><br>\n'

    proxy_type = 'tor'
    if not os.path.isfile('/usr/bin/tor'):
        proxy_type = None
    if domain.endswith('.i2p'):
        proxy_type = None

    session = create_session(proxy_type)

    wordFrequency = {}
    originDomain = None
    domainDict = get_public_post_info(session,
                                      base_dir, searchNickname, searchDomain,
                                      originDomain,
                                      proxy_type, searchPort,
                                      http_prefix, debug,
                                      __version__, wordFrequency,
                                      system_language,
                                      signing_priv_key_pem)

    # get a list of any blocked followers
    followersList = \
        download_follow_collection(signing_priv_key_pem,
                                   'followers', session,
                                   http_prefix, searchActor, 1, 5, debug)
    blockedFollowers = []
    for followerActor in followersList:
        followerNickname = get_nickname_from_actor(followerActor)
        followerDomain, followerPort = get_domain_from_actor(followerActor)
        followerDomainFull = get_full_domain(followerDomain, followerPort)
        if is_blocked(base_dir, nickname, domain,
                      followerNickname, followerDomainFull):
            blockedFollowers.append(followerActor)

    # get a list of any blocked following
    followingList = \
        download_follow_collection(signing_priv_key_pem,
                                   'following', session,
                                   http_prefix, searchActor, 1, 5, debug)
    blockedFollowing = []
    for followingActor in followingList:
        followingNickname = get_nickname_from_actor(followingActor)
        followingDomain, followingPort = get_domain_from_actor(followingActor)
        followingDomainFull = get_full_domain(followingDomain, followingPort)
        if is_blocked(base_dir, nickname, domain,
                      followingNickname, followingDomainFull):
            blockedFollowing.append(followingActor)

    infoForm += '<div class="accountInfoDomains">\n'
    usersPath = '/users/' + nickname + '/accountinfo'
    ctr = 1
    for postDomain, blockedPostUrls in domainDict.items():
        infoForm += '<a href="' + \
            http_prefix + '://' + postDomain + '" ' + \
            'target="_blank" rel="nofollow noopener noreferrer">' + \
            postDomain + '</a> '
        if is_blocked_domain(base_dir, postDomain):
            blockedPostsLinks = ''
            urlCtr = 0
            for url in blockedPostUrls:
                if urlCtr > 0:
                    blockedPostsLinks += '<br>'
                blockedPostsLinks += \
                    '<a href="' + url + '" ' + \
                    'target="_blank" rel="nofollow noopener noreferrer">' + \
                    url + '</a>'
                urlCtr += 1
            blockedPostsHtml = ''
            if blockedPostsLinks:
                blockNoStr = 'blockNumber' + str(ctr)
                blockedPostsHtml = \
                    get_content_warning_button(blockNoStr,
                                               translate, blockedPostsLinks)
                ctr += 1

            infoForm += \
                '<a href="' + usersPath + '?unblockdomain=' + postDomain + \
                '?handle=' + searchHandle + '">'
            infoForm += '<button class="buttonhighlighted"><span>' + \
                translate['Unblock'] + '</span></button></a> ' + \
                blockedPostsHtml + '\n'
        else:
            infoForm += \
                '<a href="' + usersPath + '?blockdomain=' + postDomain + \
                '?handle=' + searchHandle + '">'
            if postDomain != domain:
                infoForm += '<button class="button"><span>' + \
                    translate['Block'] + '</span></button>'
            infoForm += '</a>\n'
        infoForm += '<br>\n'

    infoForm += '</div>\n'

    if blockedFollowing:
        blockedFollowing.sort()
        infoForm += '<div class="accountInfoDomains">\n'
        infoForm += '<h1>' + translate['Blocked following'] + '</h1>\n'
        infoForm += \
            '<p>' + \
            translate['Receives posts from the following accounts'] + \
            ':</p>\n'
        for actor in blockedFollowing:
            followingNickname = get_nickname_from_actor(actor)
            followingDomain, followingPort = get_domain_from_actor(actor)
            followingDomainFull = \
                get_full_domain(followingDomain, followingPort)
            infoForm += '<a href="' + actor + '" ' + \
                'target="_blank" rel="nofollow noopener noreferrer">' + \
                followingNickname + '@' + followingDomainFull + \
                '</a><br><br>\n'
        infoForm += '</div>\n'

    if blockedFollowers:
        blockedFollowers.sort()
        infoForm += '<div class="accountInfoDomains">\n'
        infoForm += '<h1>' + translate['Blocked followers'] + '</h1>\n'
        infoForm += \
            '<p>' + \
            translate['Sends out posts to the following accounts'] + \
            ':</p>\n'
        for actor in blockedFollowers:
            followerNickname = get_nickname_from_actor(actor)
            followerDomain, followerPort = get_domain_from_actor(actor)
            followerDomainFull = get_full_domain(followerDomain, followerPort)
            infoForm += '<a href="' + actor + '" ' + \
                'target="_blank" rel="nofollow noopener noreferrer">' + \
                followerNickname + '@' + followerDomainFull + '</a><br><br>\n'
        infoForm += '</div>\n'

    if wordFrequency:
        maxCount = 1
        for word, count in wordFrequency.items():
            if count > maxCount:
                maxCount = count
        minimumWordCount = int(maxCount / 2)
        if minimumWordCount >= 3:
            infoForm += '<div class="accountInfoDomains">\n'
            infoForm += '<h1>' + translate['Word frequencies'] + '</h1>\n'
            wordSwarm = ''
            ctr = 0
            for word, count in wordFrequency.items():
                if count >= minimumWordCount:
                    if ctr > 0:
                        wordSwarm += ' '
                    if count < maxCount - int(maxCount / 4):
                        wordSwarm += word
                    else:
                        if count != maxCount:
                            wordSwarm += '<b>' + word + '</b>'
                        else:
                            wordSwarm += '<b><i>' + word + '</i></b>'
                    ctr += 1
            infoForm += wordSwarm
            infoForm += '</div>\n'

    infoForm += html_footer()
    return infoForm


def html_moderation_info(css_cache: {}, translate: {},
                         base_dir: str, http_prefix: str,
                         nickname: str) -> str:
    msgStr1 = \
        'These are globally blocked for all accounts on this instance'
    msgStr2 = \
        'Any blocks or suspensions made by moderators will be shown here.'

    infoForm = ''
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    infoForm = html_header_with_external_style(cssFilename,
                                               instanceTitle, None)

    infoForm += \
        '<center><h1><a href="/users/' + nickname + '/moderation">' + \
        translate['Moderation Information'] + \
        '</a></h1></center><br>'

    infoShown = False

    accounts = []
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            accounts.append(acct)
        break
    accounts.sort()

    cols = 5
    if len(accounts) > 10:
        infoForm += '<details><summary><b>' + translate['Show Accounts']
        infoForm += '</b></summary>\n'
    infoForm += '<div class="container">\n'
    infoForm += '<table class="accountsTable">\n'
    infoForm += '  <colgroup>\n'
    for col in range(cols):
        infoForm += '    <col span="1" class="accountsTableCol">\n'
    infoForm += '  </colgroup>\n'
    infoForm += '<tr>\n'

    col = 0
    for acct in accounts:
        acctNickname = acct.split('@')[0]
        accountDir = os.path.join(base_dir + '/accounts', acct)
        actor_json = load_json(accountDir + '.json')
        if not actor_json:
            continue
        actor = actor_json['id']
        avatarUrl = ''
        ext = ''
        if actor_json.get('icon'):
            if actor_json['icon'].get('url'):
                avatarUrl = actor_json['icon']['url']
                if '.' in avatarUrl:
                    ext = '.' + avatarUrl.split('.')[-1]
        acctUrl = \
            '/users/' + nickname + '?options=' + actor + ';1;' + \
            '/members/' + acctNickname + ext
        infoForm += '<td>\n<a href="' + acctUrl + '">'
        infoForm += '<img loading="lazy" style="width:90%" '
        infoForm += 'src="' + avatarUrl + '" />'
        infoForm += '<br><center>'
        if is_moderator(base_dir, acctNickname):
            infoForm += '<b><u>' + acctNickname + '</u></b>'
        else:
            infoForm += acctNickname
        if is_editor(base_dir, acctNickname):
            infoForm += ' ✍'
        infoForm += '</center></a>\n</td>\n'
        col += 1
        if col == cols:
            # new row of accounts
            infoForm += '</tr>\n<tr>\n'
    infoForm += '</tr>\n</table>\n'
    infoForm += '</div>\n'
    if len(accounts) > 10:
        infoForm += '</details>\n'

    suspendedFilename = base_dir + '/accounts/suspended.txt'
    if os.path.isfile(suspendedFilename):
        with open(suspendedFilename, 'r') as f:
            suspendedStr = f.read()
            infoForm += '<div class="container">\n'
            infoForm += '  <br><b>' + \
                translate['Suspended accounts'] + '</b>'
            infoForm += '  <br>' + \
                translate['These are currently suspended']
            infoForm += \
                '  <textarea id="message" ' + \
                'name="suspended" style="height:200px" spellcheck="false">' + \
                suspendedStr + '</textarea>\n'
            infoForm += '</div>\n'
            infoShown = True

    blockingFilename = base_dir + '/accounts/blocking.txt'
    if os.path.isfile(blockingFilename):
        with open(blockingFilename, 'r') as f:
            blockedStr = f.read()
            infoForm += '<div class="container">\n'
            infoForm += \
                '  <br><b>' + \
                translate['Blocked accounts and hashtags'] + '</b>'
            infoForm += \
                '  <br>' + \
                translate[msgStr1]
            infoForm += \
                '  <textarea id="message" ' + \
                'name="blocked" style="height:700px" spellcheck="false">' + \
                blockedStr + '</textarea>\n'
            infoForm += '</div>\n'
            infoShown = True

    filtersFilename = base_dir + '/accounts/filters.txt'
    if os.path.isfile(filtersFilename):
        with open(filtersFilename, 'r') as f:
            filteredStr = f.read()
            infoForm += '<div class="container">\n'
            infoForm += \
                '  <br><b>' + \
                translate['Filtered words'] + '</b>'
            infoForm += \
                '  <textarea id="message" ' + \
                'name="filtered" style="height:700px" spellcheck="true">' + \
                filteredStr + '</textarea>\n'
            infoForm += '</div>\n'
            infoShown = True

    if not infoShown:
        infoForm += \
            '<center><p>' + \
            translate[msgStr2] + \
            '</p></center>\n'
    infoForm += html_footer()
    return infoForm
