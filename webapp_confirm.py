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
from utils import get_full_domain
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import locate_post
from utils import load_json
from utils import get_config_param
from utils import get_alt_path
from utils import acct_dir
from webapp_utils import set_custom_background
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_post import individual_post_as_html


def html_confirm_delete(css_cache: {},
                        recent_posts_cache: {}, max_recent_posts: int,
                        translate, pageNumber: int,
                        session, base_dir: str, messageId: str,
                        http_prefix: str, project_version: str,
                        cached_webfingers: {}, person_cache: {},
                        calling_domain: str,
                        yt_replace_domain: str,
                        twitter_replacement_domain: str,
                        show_published_date_only: bool,
                        peertube_instances: [],
                        allow_local_network_access: bool,
                        theme_name: str, system_language: str,
                        max_like_count: int, signing_priv_key_pem: str,
                        cw_lists: {}, lists_enabled: str) -> str:
    """Shows a screen asking to confirm the deletion of a post
    """
    if '/statuses/' not in messageId:
        return None
    actor = messageId.split('/statuses/')[0]
    nickname = get_nickname_from_actor(actor)
    domain, port = get_domain_from_actor(actor)
    domain_full = get_full_domain(domain, port)

    post_filename = locate_post(base_dir, nickname, domain, messageId)
    if not post_filename:
        return None

    post_json_object = load_json(post_filename)
    if not post_json_object:
        return None

    delete_postStr = None
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    delete_postStr = \
        html_header_with_external_style(cssFilename, instanceTitle, None)
    delete_postStr += \
        individual_post_as_html(signing_priv_key_pem,
                                True, recent_posts_cache, max_recent_posts,
                                translate, pageNumber,
                                base_dir, session,
                                cached_webfingers, person_cache,
                                nickname, domain, port, post_json_object,
                                None, True, False,
                                http_prefix, project_version, 'outbox',
                                yt_replace_domain,
                                twitter_replacement_domain,
                                show_published_date_only,
                                peertube_instances, allow_local_network_access,
                                theme_name, system_language, max_like_count,
                                False, False, False, False, False, False,
                                cw_lists, lists_enabled)
    delete_postStr += '<center>'
    delete_postStr += \
        '  <p class="followText">' + \
        translate['Delete this post?'] + '</p>'

    postActor = get_alt_path(actor, domain_full, calling_domain)
    delete_postStr += \
        '  <form method="POST" action="' + postActor + '/rmpost">\n'
    delete_postStr += \
        '    <input type="hidden" name="pageNumber" value="' + \
        str(pageNumber) + '">\n'
    delete_postStr += \
        '    <input type="hidden" name="messageId" value="' + \
        messageId + '">\n'
    delete_postStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    delete_postStr += \
        '    <a href="' + actor + '/inbox"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    delete_postStr += '  </form>\n'
    delete_postStr += '</center>\n'
    delete_postStr += html_footer()
    return delete_postStr


def html_confirm_remove_shared_item(css_cache: {}, translate: {},
                                    base_dir: str,
                                    actor: str, itemID: str,
                                    calling_domain: str,
                                    sharesFileType: str) -> str:
    """Shows a screen asking to confirm the removal of a shared item
    """
    nickname = get_nickname_from_actor(actor)
    domain, port = get_domain_from_actor(actor)
    domain_full = get_full_domain(domain, port)
    sharesFile = \
        acct_dir(base_dir, nickname, domain) + '/' + sharesFileType + '.json'
    if not os.path.isfile(sharesFile):
        print('ERROR: no ' + sharesFileType + ' file ' + sharesFile)
        return None
    sharesJson = load_json(sharesFile)
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

    set_custom_background(base_dir, 'shares-background', 'follow-background')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = get_config_param(base_dir, 'instanceTitle')
    sharesStr = html_header_with_external_style(cssFilename,
                                                instanceTitle, None)
    sharesStr += '<div class="follow">\n'
    sharesStr += '  <div class="followAvatar">\n'
    sharesStr += '  <center>\n'
    if sharedItemImageUrl:
        sharesStr += '  <img loading="lazy" src="' + \
            sharedItemImageUrl + '"/>\n'
    sharesStr += \
        '  <p class="followText">' + translate['Remove'] + \
        ' ' + sharedItemDisplayName + ' ?</p>\n'
    postActor = get_alt_path(actor, domain_full, calling_domain)
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
    sharesStr += html_footer()
    return sharesStr


def html_confirm_follow(css_cache: {}, translate: {}, base_dir: str,
                        originPathStr: str,
                        followActor: str,
                        followProfileUrl: str) -> str:
    """Asks to confirm a follow
    """
    followDomain, port = get_domain_from_actor(followActor)

    if os.path.isfile(base_dir + '/accounts/follow-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/follow-background.jpg'):
            copyfile(base_dir + '/accounts/follow-background-custom.jpg',
                     base_dir + '/accounts/follow-background.jpg')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = get_config_param(base_dir, 'instanceTitle')
    followStr = html_header_with_external_style(cssFilename,
                                                instanceTitle, None)
    followStr += '<div class="follow">\n'
    followStr += '  <div class="followAvatar">\n'
    followStr += '  <center>\n'
    followStr += '  <a href="' + followActor + '">\n'
    followStr += '  <img loading="lazy" src="' + followProfileUrl + '"/></a>\n'
    followStr += \
        '  <p class="followText">' + translate['Follow'] + ' ' + \
        get_nickname_from_actor(followActor) + '@' + followDomain + ' ?</p>\n'
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
    followStr += html_footer()
    return followStr


def html_confirm_unfollow(css_cache: {}, translate: {}, base_dir: str,
                          originPathStr: str,
                          followActor: str,
                          followProfileUrl: str) -> str:
    """Asks to confirm unfollowing an actor
    """
    followDomain, port = get_domain_from_actor(followActor)

    if os.path.isfile(base_dir + '/accounts/follow-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/follow-background.jpg'):
            copyfile(base_dir + '/accounts/follow-background-custom.jpg',
                     base_dir + '/accounts/follow-background.jpg')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = get_config_param(base_dir, 'instanceTitle')
    followStr = html_header_with_external_style(cssFilename,
                                                instanceTitle, None)
    followStr += '<div class="follow">\n'
    followStr += '  <div class="followAvatar">\n'
    followStr += '  <center>\n'
    followStr += '  <a href="' + followActor + '">\n'
    followStr += '  <img loading="lazy" src="' + followProfileUrl + '"/></a>\n'
    followStr += \
        '  <p class="followText">' + translate['Stop following'] + \
        ' ' + get_nickname_from_actor(followActor) + \
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
    followStr += html_footer()
    return followStr


def html_confirm_unblock(css_cache: {}, translate: {}, base_dir: str,
                         originPathStr: str,
                         blockActor: str,
                         blockProfileUrl: str) -> str:
    """Asks to confirm unblocking an actor
    """
    blockDomain, port = get_domain_from_actor(blockActor)

    set_custom_background(base_dir, 'block-background', 'follow-background')

    cssFilename = base_dir + '/epicyon-follow.css'
    if os.path.isfile(base_dir + '/follow.css'):
        cssFilename = base_dir + '/follow.css'

    instanceTitle = get_config_param(base_dir, 'instanceTitle')
    blockStr = html_header_with_external_style(cssFilename,
                                               instanceTitle, None)
    blockStr += '<div class="block">\n'
    blockStr += '  <div class="blockAvatar">\n'
    blockStr += '  <center>\n'
    blockStr += '  <a href="' + blockActor + '">\n'
    blockStr += '  <img loading="lazy" src="' + blockProfileUrl + '"/></a>\n'
    blockStr += \
        '  <p class="blockText">' + translate['Stop blocking'] + ' ' + \
        get_nickname_from_actor(blockActor) + '@' + blockDomain + ' ?</p>\n'
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
    blockStr += html_footer()
    return blockStr
