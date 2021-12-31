__filename__ = "webapp_utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
from collections import OrderedDict
from session import get_json
from utils import is_account_dir
from utils import remove_html
from utils import get_protocol_prefixes
from utils import load_json
from utils import get_cached_post_filename
from utils import get_config_param
from utils import acct_dir
from utils import get_nickname_from_actor
from utils import is_float
from utils import get_audio_extensions
from utils import get_video_extensions
from utils import get_image_extensions
from utils import local_actor_url
from cache import store_person_in_cache
from content import add_html_tags
from content import replace_emoji_from_tags
from person import get_person_avatar_url
from posts import is_moderator
from blocking import is_blocked


def get_broken_link_substitute() -> str:
    """Returns html used to show a default image if the link to
    an image is broken
    """
    return " onerror=\"this.onerror=null; this.src='" + \
        "/icons/avatar_default.png'\""


def html_following_list(css_cache: {}, base_dir: str,
                        followingFilename: str) -> str:
    """Returns a list of handles being followed
    """
    with open(followingFilename, 'r') as followingFile:
        msg = followingFile.read()
        followingList = msg.split('\n')
        followingList.sort()
        if followingList:
            cssFilename = base_dir + '/epicyon-profile.css'
            if os.path.isfile(base_dir + '/epicyon.css'):
                cssFilename = base_dir + '/epicyon.css'

            instanceTitle = \
                get_config_param(base_dir, 'instanceTitle')
            followingListHtml = \
                html_header_with_external_style(cssFilename,
                                                instanceTitle, None)
            for followingAddress in followingList:
                if followingAddress:
                    followingListHtml += \
                        '<h3>@' + followingAddress + '</h3>'
            followingListHtml += html_footer()
            msg = followingListHtml
        return msg
    return ''


def html_hashtag_blocked(css_cache: {}, base_dir: str, translate: {}) -> str:
    """Show the screen for a blocked hashtag
    """
    blockedHashtagForm = ''
    cssFilename = base_dir + '/epicyon-suspended.css'
    if os.path.isfile(base_dir + '/suspended.css'):
        cssFilename = base_dir + '/suspended.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    blockedHashtagForm = \
        html_header_with_external_style(cssFilename, instanceTitle, None)
    blockedHashtagForm += '<div><center>\n'
    blockedHashtagForm += \
        '  <p class="screentitle">' + \
        translate['Hashtag Blocked'] + '</p>\n'
    blockedHashtagForm += \
        '  <p>See <a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>\n'
    blockedHashtagForm += '</center></div>\n'
    blockedHashtagForm += html_footer()
    return blockedHashtagForm


def header_buttons_front_screen(translate: {},
                                nickname: str, boxName: str,
                                authorized: bool,
                                icons_as_buttons: bool) -> str:
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
        if icons_as_buttons:
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
                '<img loading="lazy" src="/icons' + \
                '/newswire.png" title="' + translate['Newswire'] + \
                '" alt="| ' + translate['Newswire'] + '"/></a>\n'
            headerStr += \
                '        <a href="' + \
                '/users/news/linksmobile">' + \
                '<img loading="lazy" src="/icons' + \
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


def get_content_warning_button(postID: str, translate: {},
                               content: str) -> str:
    """Returns the markup for a content warning button
    """
    return '       <details><summary class="cw">' + \
        translate['SHOW MORE'] + '</summary>' + \
        '<div id="' + postID + '">' + content + \
        '</div></details>\n'


def _set_actor_property_url(actor_json: {},
                            property_name: str, url: str) -> None:
    """Sets a url for the given actor property
    """
    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    property_nameLower = property_name.lower()

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith(property_nameLower):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)

    prefixes = get_protocol_prefixes()
    prefixFound = False
    for prefix in prefixes:
        if url.startswith(prefix):
            prefixFound = True
            break
    if not prefixFound:
        return
    if '.' not in url:
        return
    if ' ' in url:
        return
    if ',' in url:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith(property_nameLower):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = url
        return

    newAddress = {
        "name": property_name,
        "type": "PropertyValue",
        "value": url
    }
    actor_json['attachment'].append(newAddress)


def set_blog_address(actor_json: {}, blog_address: str) -> None:
    """Sets an blog address for the given actor
    """
    _set_actor_property_url(actor_json, 'Blog', remove_html(blog_address))


def update_avatar_image_cache(signing_priv_key_pem: str,
                              session, base_dir: str, http_prefix: str,
                              actor: str, avatarUrl: str,
                              person_cache: {}, allowDownloads: bool,
                              force: bool = False, debug: bool = False) -> str:
    """Updates the cached avatar for the given actor
    """
    if not avatarUrl:
        return None
    actorStr = actor.replace('/', '-')
    avatarImagePath = base_dir + '/cache/avatars/' + actorStr

    # try different image types
    imageFormats = {
        'png': 'png',
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'gif': 'gif',
        'svg': 'svg+xml',
        'webp': 'webp',
        'avif': 'avif'
    }
    avatarImageFilename = None
    for imFormat, mimeType in imageFormats.items():
        if avatarUrl.endswith('.' + imFormat) or \
           '.' + imFormat + '?' in avatarUrl:
            sessionHeaders = {
                'Accept': 'image/' + mimeType
            }
            avatarImageFilename = avatarImagePath + '.' + imFormat

    if not avatarImageFilename:
        return None

    if (not os.path.isfile(avatarImageFilename) or force) and allowDownloads:
        try:
            if debug:
                print('avatar image url: ' + avatarUrl)
            result = session.get(avatarUrl,
                                 headers=sessionHeaders,
                                 params=None)
            if result.status_code < 200 or \
               result.status_code > 202:
                if debug:
                    print('Avatar image download failed with status ' +
                          str(result.status_code))
                # remove partial download
                if os.path.isfile(avatarImageFilename):
                    try:
                        os.remove(avatarImageFilename)
                    except OSError:
                        print('EX: ' +
                              'update_avatar_image_cache unable to delete ' +
                              avatarImageFilename)
            else:
                with open(avatarImageFilename, 'wb') as f:
                    f.write(result.content)
                    if debug:
                        print('avatar image downloaded for ' + actor)
                    return avatarImageFilename.replace(base_dir + '/cache', '')
        except Exception as ex:
            print('EX: Failed to download avatar image: ' +
                  str(avatarUrl) + ' ' + str(ex))
        prof = 'https://www.w3.org/ns/activitystreams'
        if '/channel/' not in actor or '/accounts/' not in actor:
            sessionHeaders = {
                'Accept': 'application/activity+json; profile="' + prof + '"'
            }
        else:
            sessionHeaders = {
                'Accept': 'application/ld+json; profile="' + prof + '"'
            }
        personJson = \
            get_json(signing_priv_key_pem, session, actor,
                     sessionHeaders, None,
                     debug, __version__, http_prefix, None)
        if personJson:
            if not personJson.get('id'):
                return None
            if not personJson.get('publicKey'):
                return None
            if not personJson['publicKey'].get('publicKeyPem'):
                return None
            if personJson['id'] != actor:
                return None
            if not person_cache.get(actor):
                return None
            if person_cache[actor]['actor']['publicKey']['publicKeyPem'] != \
               personJson['publicKey']['publicKeyPem']:
                print("ERROR: " +
                      "public keys don't match when downloading actor for " +
                      actor)
                return None
            store_person_in_cache(base_dir, actor, personJson, person_cache,
                                  allowDownloads)
            return get_person_avatar_url(base_dir, actor, person_cache,
                                         allowDownloads)
        return None
    return avatarImageFilename.replace(base_dir + '/cache', '')


def scheduled_posts_exist(base_dir: str, nickname: str, domain: str) -> bool:
    """Returns true if there are posts scheduled to be delivered
    """
    scheduleIndexFilename = \
        acct_dir(base_dir, nickname, domain) + '/schedule.index'
    if not os.path.isfile(scheduleIndexFilename):
        return False
    if '#users#' in open(scheduleIndexFilename).read():
        return True
    return False


def shares_timeline_json(actor: str, pageNumber: int, itemsPerPage: int,
                         base_dir: str, domain: str, nickname: str,
                         maxSharesPerAccount: int,
                         shared_items_federated_domains: [],
                         sharesFileType: str) -> ({}, bool):
    """Get a page on the shared items timeline as json
    maxSharesPerAccount helps to avoid one person dominating the timeline
    by sharing a large number of things
    """
    allSharesJson = {}
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if not is_account_dir(handle):
                continue
            accountDir = base_dir + '/accounts/' + handle
            sharesFilename = accountDir + '/' + sharesFileType + '.json'
            if not os.path.isfile(sharesFilename):
                continue
            sharesJson = load_json(sharesFilename)
            if not sharesJson:
                continue
            accountNickname = handle.split('@')[0]
            # Don't include shared items from blocked accounts
            if accountNickname != nickname:
                if is_blocked(base_dir, nickname, domain,
                              accountNickname, domain, None):
                    continue
            # actor who owns this share
            owner = actor.split('/users/')[0] + '/users/' + accountNickname
            ctr = 0
            for itemID, item in sharesJson.items():
                # assign owner to the item
                item['actor'] = owner
                item['shareId'] = itemID
                allSharesJson[str(item['published'])] = item
                ctr += 1
                if ctr >= maxSharesPerAccount:
                    break
        break
    if shared_items_federated_domains:
        if sharesFileType == 'shares':
            catalogsDir = base_dir + '/cache/catalogs'
        else:
            catalogsDir = base_dir + '/cache/wantedItems'
        if os.path.isdir(catalogsDir):
            for subdir, dirs, files in os.walk(catalogsDir):
                for f in files:
                    if '#' in f:
                        continue
                    if not f.endswith('.' + sharesFileType + '.json'):
                        continue
                    federatedDomain = f.split('.')[0]
                    if federatedDomain not in shared_items_federated_domains:
                        continue
                    sharesFilename = catalogsDir + '/' + f
                    sharesJson = load_json(sharesFilename)
                    if not sharesJson:
                        continue
                    ctr = 0
                    for itemID, item in sharesJson.items():
                        # assign owner to the item
                        if '--shareditems--' not in itemID:
                            continue
                        shareActor = itemID.split('--shareditems--')[0]
                        shareActor = shareActor.replace('___', '://')
                        shareActor = shareActor.replace('--', '/')
                        shareNickname = get_nickname_from_actor(shareActor)
                        if is_blocked(base_dir, nickname, domain,
                                      shareNickname, federatedDomain, None):
                            continue
                        item['actor'] = shareActor
                        item['shareId'] = itemID
                        allSharesJson[str(item['published'])] = item
                        ctr += 1
                        if ctr >= maxSharesPerAccount:
                            break
                break
    # sort the shared items in descending order of publication date
    sharesJson = OrderedDict(sorted(allSharesJson.items(), reverse=True))
    lastPage = False
    startIndex = itemsPerPage * pageNumber
    maxIndex = len(sharesJson.items())
    if maxIndex < itemsPerPage:
        lastPage = True
    if startIndex >= maxIndex - itemsPerPage:
        lastPage = True
        startIndex = maxIndex - itemsPerPage
        if startIndex < 0:
            startIndex = 0
    ctr = 0
    resultJson = {}
    for published, item in sharesJson.items():
        if ctr >= startIndex + itemsPerPage:
            break
        if ctr < startIndex:
            ctr += 1
            continue
        resultJson[published] = item
        ctr += 1
    return resultJson, lastPage


def post_contains_public(post_json_object: {}) -> bool:
    """Does the given post contain #Public
    """
    containsPublic = False
    if not post_json_object['object'].get('to'):
        return containsPublic

    for toAddress in post_json_object['object']['to']:
        if toAddress.endswith('#Public'):
            containsPublic = True
            break
        if not containsPublic:
            if post_json_object['object'].get('cc'):
                for toAddress in post_json_object['object']['cc']:
                    if toAddress.endswith('#Public'):
                        containsPublic = True
                        break
    return containsPublic


def _get_image_file(base_dir: str, name: str, directory: str,
                    nickname: str, domain: str, theme: str) -> (str, str):
    """
    returns the filenames for an image with the given name
    """
    bannerExtensions = get_image_extensions()
    bannerFile = ''
    bannerFilename = ''
    for ext in bannerExtensions:
        bannerFileTest = name + '.' + ext
        bannerFilenameTest = directory + '/' + bannerFileTest
        if os.path.isfile(bannerFilenameTest):
            bannerFile = name + '_' + theme + '.' + ext
            bannerFilename = bannerFilenameTest
            return bannerFile, bannerFilename
    # if not found then use the default image
    theme = 'default'
    directory = base_dir + '/theme/' + theme
    for ext in bannerExtensions:
        bannerFileTest = name + '.' + ext
        bannerFilenameTest = directory + '/' + bannerFileTest
        if os.path.isfile(bannerFilenameTest):
            bannerFile = name + '_' + theme + '.' + ext
            bannerFilename = bannerFilenameTest
            break
    return bannerFile, bannerFilename


def get_banner_file(base_dir: str,
                    nickname: str, domain: str, theme: str) -> (str, str):
    accountDir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'banner', accountDir,
                           nickname, domain, theme)


def get_search_banner_file(base_dir: str,
                           nickname: str, domain: str,
                           theme: str) -> (str, str):
    accountDir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'search_banner', accountDir,
                           nickname, domain, theme)


def get_left_image_file(base_dir: str,
                        nickname: str, domain: str, theme: str) -> (str, str):
    accountDir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'left_col_image', accountDir,
                           nickname, domain, theme)


def get_right_image_file(base_dir: str,
                         nickname: str, domain: str, theme: str) -> (str, str):
    accountDir = acct_dir(base_dir, nickname, domain)
    return _get_image_file(base_dir, 'right_col_image',
                           accountDir, nickname, domain, theme)


def html_header_with_external_style(cssFilename: str, instanceTitle: str,
                                    metadata: str, lang='en') -> str:
    if metadata is None:
        metadata = ''
    cssFile = '/' + cssFilename.split('/')[-1]
    htmlStr = \
        '<!DOCTYPE html>\n' + \
        '<html lang="' + lang + '">\n' + \
        '  <head>\n' + \
        '    <meta charset="utf-8">\n' + \
        '    <link rel="stylesheet" media="all" ' + \
        'href="' + cssFile + '">\n' + \
        '    <link rel="manifest" href="/manifest.json">\n' + \
        '    <link href="/favicon.ico" rel="icon" type="image/x-icon">\n' + \
        '    <meta content="/browserconfig.xml" ' + \
        'name="msapplication-config">\n' + \
        '    <meta content="yes" name="apple-mobile-web-app-capable">\n' + \
        '    <link href="/apple-touch-icon.png" rel="apple-touch-icon" ' + \
        'sizes="180x180">\n' + \
        '    <meta name="theme-color" content="grey">\n' + \
        metadata + \
        '    <title>' + instanceTitle + '</title>\n' + \
        '  </head>\n' + \
        '  <body>\n'
    return htmlStr


def html_header_with_person_markup(cssFilename: str, instanceTitle: str,
                                   actor_json: {}, city: str,
                                   content_license_url: str,
                                   lang='en') -> str:
    """html header which includes person markup
    https://schema.org/Person
    """
    if not actor_json:
        htmlStr = \
            html_header_with_external_style(cssFilename,
                                            instanceTitle, None, lang)
        return htmlStr

    cityMarkup = ''
    if city:
        city = city.lower().title()
        addComma = ''
        countryMarkup = ''
        if ',' in city:
            country = city.split(',', 1)[1].strip().title()
            city = city.split(',', 1)[0]
            countryMarkup = \
                '          "addressCountry": "' + country + '"\n'
            addComma = ','
        cityMarkup = \
            '        "address": {\n' + \
            '          "@type": "PostalAddress",\n' + \
            '          "addressLocality": "' + city + '"' + addComma + '\n' + \
            countryMarkup + \
            '        },\n'

    skillsMarkup = ''
    if actor_json.get('hasOccupation'):
        if isinstance(actor_json['hasOccupation'], list):
            skillsMarkup = '        "hasOccupation": [\n'
            firstEntry = True
            for skillDict in actor_json['hasOccupation']:
                if skillDict['@type'] == 'Role':
                    if not firstEntry:
                        skillsMarkup += ',\n'
                    sk = skillDict['hasOccupation']
                    roleName = sk['name']
                    if not roleName:
                        roleName = 'member'
                    category = \
                        sk['occupationalCategory']['codeValue']
                    categoryUrl = \
                        'https://www.onetonline.org/link/summary/' + category
                    skillsMarkup += \
                        '        {\n' + \
                        '          "@type": "Role",\n' + \
                        '          "hasOccupation": {\n' + \
                        '            "@type": "Occupation",\n' + \
                        '            "name": "' + roleName + '",\n' + \
                        '            "description": ' + \
                        '"Fediverse instance role",\n' + \
                        '            "occupationLocation": {\n' + \
                        '              "@type": "City",\n' + \
                        '              "name": "' + city + '"\n' + \
                        '            },\n' + \
                        '            "occupationalCategory": {\n' + \
                        '              "@type": "CategoryCode",\n' + \
                        '              "inCodeSet": {\n' + \
                        '                "@type": "CategoryCodeSet",\n' + \
                        '                "name": "O*Net-SOC",\n' + \
                        '                "dateModified": "2019",\n' + \
                        '                ' + \
                        '"url": "https://www.onetonline.org/"\n' + \
                        '              },\n' + \
                        '              "codeValue": "' + category + '",\n' + \
                        '              "url": "' + categoryUrl + '"\n' + \
                        '            }\n' + \
                        '          }\n' + \
                        '        }'
                elif skillDict['@type'] == 'Occupation':
                    if not firstEntry:
                        skillsMarkup += ',\n'
                    ocName = skillDict['name']
                    if not ocName:
                        ocName = 'member'
                    skillsList = skillDict['skills']
                    skillsListStr = '['
                    for skillStr in skillsList:
                        if skillsListStr != '[':
                            skillsListStr += ', '
                        skillsListStr += '"' + skillStr + '"'
                    skillsListStr += ']'
                    skillsMarkup += \
                        '        {\n' + \
                        '          "@type": "Occupation",\n' + \
                        '          "name": "' + ocName + '",\n' + \
                        '          "description": ' + \
                        '"Fediverse instance occupation",\n' + \
                        '          "occupationLocation": {\n' + \
                        '            "@type": "City",\n' + \
                        '            "name": "' + city + '"\n' + \
                        '          },\n' + \
                        '          "skills": ' + skillsListStr + '\n' + \
                        '        }'
                firstEntry = False
            skillsMarkup += '\n        ],\n'

    description = remove_html(actor_json['summary'])
    nameStr = remove_html(actor_json['name'])
    domain_full = actor_json['id'].split('://')[1].split('/')[0]
    handle = actor_json['preferredUsername'] + '@' + domain_full

    personMarkup = \
        '      "about": {\n' + \
        '        "@type" : "Person",\n' + \
        '        "name": "' + nameStr + '",\n' + \
        '        "image": "' + actor_json['icon']['url'] + '",\n' + \
        '        "description": "' + description + '",\n' + \
        cityMarkup + skillsMarkup + \
        '        "url": "' + actor_json['id'] + '"\n' + \
        '      },\n'

    profileMarkup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context":"https://schema.org",\n' + \
        '      "@type": "ProfilePage",\n' + \
        '      "mainEntityOfPage": {\n' + \
        '        "@type": "WebPage",\n' + \
        "        \"@id\": \"" + actor_json['id'] + "\"\n" + \
        '      },\n' + personMarkup + \
        '      "accountablePerson": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + nameStr + '"\n' + \
        '      },\n' + \
        '      "copyrightHolder": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + nameStr + '"\n' + \
        '      },\n' + \
        '      "name": "' + nameStr + '",\n' + \
        '      "image": "' + actor_json['icon']['url'] + '",\n' + \
        '      "description": "' + description + '",\n' + \
        '      "license": "' + content_license_url + '"\n' + \
        '    }\n' + \
        '    </script>\n'

    description = remove_html(description)
    ogMetadata = \
        "    <meta content=\"profile\" property=\"og:type\" />\n" + \
        "    <meta content=\"" + description + \
        "\" name='description'>\n" + \
        "    <meta content=\"" + actor_json['url'] + \
        "\" property=\"og:url\" />\n" + \
        "    <meta content=\"" + domain_full + \
        "\" property=\"og:site_name\" />\n" + \
        "    <meta content=\"" + nameStr + " (@" + handle + \
        ")\" property=\"og:title\" />\n" + \
        "    <meta content=\"" + description + \
        "\" property=\"og:description\" />\n" + \
        "    <meta content=\"" + actor_json['icon']['url'] + \
        "\" property=\"og:image\" />\n" + \
        "    <meta content=\"400\" property=\"og:image:width\" />\n" + \
        "    <meta content=\"400\" property=\"og:image:height\" />\n" + \
        "    <meta content=\"summary\" property=\"twitter:card\" />\n" + \
        "    <meta content=\"" + handle + \
        "\" property=\"profile:username\" />\n"
    if actor_json.get('attachment'):
        ogTags = (
            'email', 'openpgp', 'blog', 'xmpp', 'matrix', 'briar',
            'jami', 'cwtch', 'languages'
        )
        for attachJson in actor_json['attachment']:
            if not attachJson.get('name'):
                continue
            if not attachJson.get('value'):
                continue
            name = attachJson['name'].lower()
            value = attachJson['value']
            for ogTag in ogTags:
                if name != ogTag:
                    continue
                ogMetadata += \
                    "    <meta content=\"" + value + \
                    "\" property=\"og:" + ogTag + "\" />\n"

    htmlStr = \
        html_header_with_external_style(cssFilename, instanceTitle,
                                        ogMetadata + profileMarkup, lang)
    return htmlStr


def html_header_with_website_markup(cssFilename: str, instanceTitle: str,
                                    http_prefix: str, domain: str,
                                    system_language: str) -> str:
    """html header which includes website markup
    https://schema.org/WebSite
    """
    licenseUrl = 'https://www.gnu.org/licenses/agpl-3.0.rdf'

    # social networking category
    genreUrl = 'http://vocab.getty.edu/aat/300312270'

    websiteMarkup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context" : "http://schema.org",\n' + \
        '      "@type" : "WebSite",\n' + \
        '      "name": "' + instanceTitle + '",\n' + \
        '      "url": "' + http_prefix + '://' + domain + '",\n' + \
        '      "license": "' + licenseUrl + '",\n' + \
        '      "inLanguage": "' + system_language + '",\n' + \
        '      "isAccessibleForFree": true,\n' + \
        '      "genre": "' + genreUrl + '",\n' + \
        '      "accessMode": ["textual", "visual"],\n' + \
        '      "accessModeSufficient": ["textual"],\n' + \
        '      "accessibilityAPI" : ["ARIA"],\n' + \
        '      "accessibilityControl" : [\n' + \
        '        "fullKeyboardControl",\n' + \
        '        "fullTouchControl",\n' + \
        '        "fullMouseControl"\n' + \
        '      ],\n' + \
        '      "encodingFormat" : [\n' + \
        '        "text/html", "image/png", "image/webp",\n' + \
        '        "image/jpeg", "image/gif", "text/css"\n' + \
        '      ]\n' + \
        '    }\n' + \
        '    </script>\n'

    ogMetadata = \
        '    <meta content="Epicyon hosted on ' + domain + \
        '" property="og:site_name" />\n' + \
        '    <meta content="' + http_prefix + '://' + domain + \
        '/about" property="og:url" />\n' + \
        '    <meta content="website" property="og:type" />\n' + \
        '    <meta content="' + instanceTitle + \
        '" property="og:title" />\n' + \
        '    <meta content="' + http_prefix + '://' + domain + \
        '/logo.png" property="og:image" />\n' + \
        '    <meta content="' + system_language + \
        '" property="og:locale" />\n' + \
        '    <meta content="summary_large_image" property="twitter:card" />\n'

    htmlStr = \
        html_header_with_external_style(cssFilename, instanceTitle,
                                        ogMetadata + websiteMarkup,
                                        system_language)
    return htmlStr


def html_header_with_blog_markup(cssFilename: str, instanceTitle: str,
                                 http_prefix: str, domain: str, nickname: str,
                                 system_language: str,
                                 published: str, modified: str,
                                 title: str, snippet: str,
                                 translate: {}, url: str,
                                 content_license_url: str) -> str:
    """html header which includes blog post markup
    https://schema.org/BlogPosting
    """
    authorUrl = local_actor_url(http_prefix, nickname, domain)
    aboutUrl = http_prefix + '://' + domain + '/about.html'

    # license for content on the site may be different from
    # the software license

    blogMarkup = \
        '    <script id="initial-state" type="application/ld+json">\n' + \
        '    {\n' + \
        '      "@context" : "http://schema.org",\n' + \
        '      "@type" : "BlogPosting",\n' + \
        '      "headline": "' + title + '",\n' + \
        '      "datePublished": "' + published + '",\n' + \
        '      "dateModified": "' + modified + '",\n' + \
        '      "author": {\n' + \
        '        "@type": "Person",\n' + \
        '        "name": "' + nickname + '",\n' + \
        '        "sameAs": "' + authorUrl + '"\n' + \
        '      },\n' + \
        '      "publisher": {\n' + \
        '        "@type": "WebSite",\n' + \
        '        "name": "' + instanceTitle + '",\n' + \
        '        "sameAs": "' + aboutUrl + '"\n' + \
        '      },\n' + \
        '      "license": "' + content_license_url + '",\n' + \
        '      "description": "' + snippet + '"\n' + \
        '    }\n' + \
        '    </script>\n'

    ogMetadata = \
        '    <meta property="og:locale" content="' + \
        system_language + '" />\n' + \
        '    <meta property="og:type" content="article" />\n' + \
        '    <meta property="og:title" content="' + title + '" />\n' + \
        '    <meta property="og:url" content="' + url + '" />\n' + \
        '    <meta content="Epicyon hosted on ' + domain + \
        '" property="og:site_name" />\n' + \
        '    <meta property="article:published_time" content="' + \
        published + '" />\n' + \
        '    <meta property="article:modified_time" content="' + \
        modified + '" />\n'

    htmlStr = \
        html_header_with_external_style(cssFilename, instanceTitle,
                                        ogMetadata + blogMarkup,
                                        system_language)
    return htmlStr


def html_footer() -> str:
    htmlStr = '  </body>\n'
    htmlStr += '</html>\n'
    return htmlStr


def load_individual_post_as_html_from_cache(base_dir: str,
                                            nickname: str, domain: str,
                                            post_json_object: {}) -> str:
    """If a cached html version of the given post exists then load it and
    return the html text
    This is much quicker than generating the html from the json object
    """
    cachedPostFilename = \
        get_cached_post_filename(base_dir, nickname, domain, post_json_object)

    postHtml = ''
    if not cachedPostFilename:
        return postHtml

    if not os.path.isfile(cachedPostFilename):
        return postHtml

    tries = 0
    while tries < 3:
        try:
            with open(cachedPostFilename, 'r') as file:
                postHtml = file.read()
                break
        except Exception as ex:
            print('ERROR: load_individual_post_as_html_from_cache ' +
                  str(tries) + ' ' + str(ex))
            # no sleep
            tries += 1
    if postHtml:
        return postHtml


def add_emoji_to_display_name(session, base_dir: str, http_prefix: str,
                              nickname: str, domain: str,
                              displayName: str, inProfileName: bool) -> str:
    """Adds emoji icons to display names or CW on individual posts
    """
    if ':' not in displayName:
        return displayName

    displayName = displayName.replace('<p>', '').replace('</p>', '')
    emojiTags = {}
#    print('TAG: displayName before tags: ' + displayName)
    displayName = \
        add_html_tags(base_dir, http_prefix,
                      nickname, domain, displayName, [], emojiTags)
    displayName = displayName.replace('<p>', '').replace('</p>', '')
#    print('TAG: displayName after tags: ' + displayName)
    # convert the emoji dictionary to a list
    emojiTagsList = []
    for tagName, tag in emojiTags.items():
        emojiTagsList.append(tag)
#    print('TAG: emoji tags list: ' + str(emojiTagsList))
    if not inProfileName:
        displayName = \
            replace_emoji_from_tags(session, base_dir,
                                    displayName, emojiTagsList, 'post header',
                                    False)
    else:
        displayName = \
            replace_emoji_from_tags(session, base_dir,
                                    displayName, emojiTagsList, 'profile',
                                    False)
#    print('TAG: displayName after tags 2: ' + displayName)

    # remove any stray emoji
    while ':' in displayName:
        if '://' in displayName:
            break
        emojiStr = displayName.split(':')[1]
        prevDisplayName = displayName
        displayName = displayName.replace(':' + emojiStr + ':', '').strip()
        if prevDisplayName == displayName:
            break
#        print('TAG: displayName after tags 3: ' + displayName)
#    print('TAG: displayName after tag replacements: ' + displayName)

    return displayName


def _is_image_mime_type(mimeType: str) -> bool:
    """Is the given mime type an image?
    """
    if mimeType == 'image/svg+xml':
        return True
    if not mimeType.startswith('image/'):
        return False
    extensions = get_image_extensions()
    ext = mimeType.split('/')[1]
    if ext in extensions:
        return True
    return False


def _is_video_mime_type(mimeType: str) -> bool:
    """Is the given mime type a video?
    """
    if not mimeType.startswith('video/'):
        return False
    extensions = get_video_extensions()
    ext = mimeType.split('/')[1]
    if ext in extensions:
        return True
    return False


def _is_audio_mime_type(mimeType: str) -> bool:
    """Is the given mime type an audio file?
    """
    if mimeType == 'audio/mpeg':
        return True
    if not mimeType.startswith('audio/'):
        return False
    extensions = get_audio_extensions()
    ext = mimeType.split('/')[1]
    if ext in extensions:
        return True
    return False


def _is_attached_image(attachmentFilename: str) -> bool:
    """Is the given attachment filename an image?
    """
    if '.' not in attachmentFilename:
        return False
    imageExt = (
        'png', 'jpg', 'jpeg', 'webp', 'avif', 'svg', 'gif'
    )
    ext = attachmentFilename.split('.')[-1]
    if ext in imageExt:
        return True
    return False


def _is_attached_video(attachmentFilename: str) -> bool:
    """Is the given attachment filename a video?
    """
    if '.' not in attachmentFilename:
        return False
    videoExt = (
        'mp4', 'webm', 'ogv'
    )
    ext = attachmentFilename.split('.')[-1]
    if ext in videoExt:
        return True
    return False


def get_post_attachments_as_html(post_json_object: {}, boxName: str,
                                 translate: {},
                                 is_muted: bool, avatarLink: str,
                                 replyStr: str, announceStr: str, likeStr: str,
                                 bookmarkStr: str, deleteStr: str,
                                 muteStr: str) -> (str, str):
    """Returns a string representing any attachments
    """
    attachmentStr = ''
    galleryStr = ''
    if not post_json_object['object'].get('attachment'):
        return attachmentStr, galleryStr

    if not isinstance(post_json_object['object']['attachment'], list):
        return attachmentStr, galleryStr

    attachmentCtr = 0
    attachmentStr = ''
    mediaStyleAdded = False
    for attach in post_json_object['object']['attachment']:
        if not (attach.get('mediaType') and attach.get('url')):
            continue

        mediaType = attach['mediaType']
        imageDescription = ''
        if attach.get('name'):
            imageDescription = attach['name'].replace('"', "'")
        if _is_image_mime_type(mediaType):
            imageUrl = attach['url']
            if _is_attached_image(attach['url']) and 'svg' not in mediaType:
                if not attachmentStr:
                    attachmentStr += '<div class="media">\n'
                    mediaStyleAdded = True

                if attachmentCtr > 0:
                    attachmentStr += '<br>'
                if boxName == 'tlmedia':
                    galleryStr += '<div class="gallery">\n'
                    if not is_muted:
                        galleryStr += '  <a href="' + imageUrl + '">\n'
                        galleryStr += \
                            '    <img loading="lazy" src="' + \
                            imageUrl + '" alt="" title="">\n'
                        galleryStr += '  </a>\n'
                    if post_json_object['object'].get('url'):
                        imagePostUrl = post_json_object['object']['url']
                    else:
                        imagePostUrl = post_json_object['object']['id']
                    if imageDescription and not is_muted:
                        galleryStr += \
                            '  <a href="' + imagePostUrl + \
                            '" class="gallerytext"><div ' + \
                            'class="gallerytext">' + \
                            imageDescription + '</div></a>\n'
                    else:
                        galleryStr += \
                            '<label class="transparent">---</label><br>'
                    galleryStr += '  <div class="mediaicons">\n'
                    galleryStr += \
                        '    ' + replyStr+announceStr + likeStr + \
                        bookmarkStr + deleteStr + muteStr + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '  <div class="mediaavatar">\n'
                    galleryStr += '    ' + avatarLink + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '</div>\n'

                attachmentStr += '<a href="' + imageUrl + '">'
                attachmentStr += \
                    '<img loading="lazy" src="' + imageUrl + \
                    '" alt="' + imageDescription + '" title="' + \
                    imageDescription + '" class="attachment"></a>\n'
                attachmentCtr += 1
        elif _is_video_mime_type(mediaType):
            if _is_attached_video(attach['url']):
                extension = attach['url'].split('.')[-1]
                if attachmentCtr > 0:
                    attachmentStr += '<br>'
                if boxName == 'tlmedia':
                    galleryStr += '<div class="gallery">\n'
                    if not is_muted:
                        galleryStr += '  <a href="' + attach['url'] + '">\n'
                        galleryStr += \
                            '    <figure id="videoContainer" ' + \
                            'data-fullscreen="false">\n' + \
                            '    <video id="video" controls ' + \
                            'preload="metadata">\n'
                        galleryStr += \
                            '      <source src="' + attach['url'] + \
                            '" alt="' + imageDescription + \
                            '" title="' + imageDescription + \
                            '" class="attachment" type="video/' + \
                            extension + '">'
                        idx = 'Your browser does not support the video tag.'
                        galleryStr += translate[idx]
                        galleryStr += '    </video>\n'
                        galleryStr += '    </figure>\n'
                        galleryStr += '  </a>\n'
                    if post_json_object['object'].get('url'):
                        videoPostUrl = post_json_object['object']['url']
                    else:
                        videoPostUrl = post_json_object['object']['id']
                    if imageDescription and not is_muted:
                        galleryStr += \
                            '  <a href="' + videoPostUrl + \
                            '" class="gallerytext"><div ' + \
                            'class="gallerytext">' + \
                            imageDescription + '</div></a>\n'
                    else:
                        galleryStr += \
                            '<label class="transparent">---</label><br>'
                    galleryStr += '  <div class="mediaicons">\n'
                    galleryStr += \
                        '    ' + replyStr + announceStr + likeStr + \
                        bookmarkStr + deleteStr + muteStr + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '  <div class="mediaavatar">\n'
                    galleryStr += '    ' + avatarLink + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '</div>\n'

                attachmentStr += \
                    '<center><figure id="videoContainer" ' + \
                    'data-fullscreen="false">\n' + \
                    '    <video id="video" controls ' + \
                    'preload="metadata">\n'
                attachmentStr += \
                    '<source src="' + attach['url'] + '" alt="' + \
                    imageDescription + '" title="' + imageDescription + \
                    '" class="attachment" type="video/' + \
                    extension + '">'
                attachmentStr += \
                    translate['Your browser does not support the video tag.']
                attachmentStr += '</video></figure></center>'
                attachmentCtr += 1
        elif _is_audio_mime_type(mediaType):
            extension = '.mp3'
            if attach['url'].endswith('.ogg'):
                extension = '.ogg'
            if attach['url'].endswith(extension):
                if attachmentCtr > 0:
                    attachmentStr += '<br>'
                if boxName == 'tlmedia':
                    galleryStr += '<div class="gallery">\n'
                    if not is_muted:
                        galleryStr += '  <a href="' + attach['url'] + '">\n'
                        galleryStr += '    <audio controls>\n'
                        galleryStr += \
                            '      <source src="' + attach['url'] + \
                            '" alt="' + imageDescription + \
                            '" title="' + imageDescription + \
                            '" class="attachment" type="audio/' + \
                            extension.replace('.', '') + '">'
                        idx = 'Your browser does not support the audio tag.'
                        galleryStr += translate[idx]
                        galleryStr += '    </audio>\n'
                        galleryStr += '  </a>\n'
                    if post_json_object['object'].get('url'):
                        audioPostUrl = post_json_object['object']['url']
                    else:
                        audioPostUrl = post_json_object['object']['id']
                    if imageDescription and not is_muted:
                        galleryStr += \
                            '  <a href="' + audioPostUrl + \
                            '" class="gallerytext"><div ' + \
                            'class="gallerytext">' + \
                            imageDescription + '</div></a>\n'
                    else:
                        galleryStr += \
                            '<label class="transparent">---</label><br>'
                    galleryStr += '  <div class="mediaicons">\n'
                    galleryStr += \
                        '    ' + replyStr + announceStr + \
                        likeStr + bookmarkStr + \
                        deleteStr + muteStr + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '  <div class="mediaavatar">\n'
                    galleryStr += '    ' + avatarLink + '\n'
                    galleryStr += '  </div>\n'
                    galleryStr += '</div>\n'

                attachmentStr += '<center>\n<audio controls>\n'
                attachmentStr += \
                    '<source src="' + attach['url'] + '" alt="' + \
                    imageDescription + '" title="' + imageDescription + \
                    '" class="attachment" type="audio/' + \
                    extension.replace('.', '') + '">'
                attachmentStr += \
                    translate['Your browser does not support the audio tag.']
                attachmentStr += '</audio>\n</center>\n'
                attachmentCtr += 1
    if mediaStyleAdded:
        attachmentStr += '</div>'
    return attachmentStr, galleryStr


def html_post_separator(base_dir: str, column: str) -> str:
    """Returns the html for a timeline post separator image
    """
    theme = get_config_param(base_dir, 'theme')
    filename = 'separator.png'
    separatorClass = "postSeparatorImage"
    if column:
        separatorClass = "postSeparatorImage" + column.title()
        filename = 'separator_' + column + '.png'
    separatorImageFilename = \
        base_dir + '/theme/' + theme + '/icons/' + filename
    separatorStr = ''
    if os.path.isfile(separatorImageFilename):
        separatorStr = \
            '<div class="' + separatorClass + '"><center>' + \
            '<img src="/icons/' + filename + '" ' + \
            'alt="" /></center></div>\n'
    return separatorStr


def html_highlight_label(label: str, highlight: bool) -> str:
    """If the given text should be highlighted then return
    the appropriate markup.
    This is so that in shell browsers, like lynx, it's possible
    to see if the replies or DM button are highlighted.
    """
    if not highlight:
        return label
    return '*' + str(label) + '*'


def get_avatar_image_url(session,
                         base_dir: str, http_prefix: str,
                         postActor: str, person_cache: {},
                         avatarUrl: str, allowDownloads: bool,
                         signing_priv_key_pem: str) -> str:
    """Returns the avatar image url
    """
    # get the avatar image url for the post actor
    if not avatarUrl:
        avatarUrl = \
            get_person_avatar_url(base_dir, postActor, person_cache,
                                  allowDownloads)
        avatarUrl = \
            update_avatar_image_cache(signing_priv_key_pem,
                                      session, base_dir, http_prefix,
                                      postActor, avatarUrl, person_cache,
                                      allowDownloads)
    else:
        update_avatar_image_cache(signing_priv_key_pem,
                                  session, base_dir, http_prefix,
                                  postActor, avatarUrl, person_cache,
                                  allowDownloads)

    if not avatarUrl:
        avatarUrl = postActor + '/avatar.png'

    return avatarUrl


def html_hide_from_screen_reader(htmlStr: str) -> str:
    """Returns html which is hidden from screen readers
    """
    return '<span aria-hidden="true">' + htmlStr + '</span>'


def html_keyboard_navigation(banner: str, links: {}, accessKeys: {},
                             subHeading: str = None,
                             usersPath: str = None, translate: {} = None,
                             followApprovals: bool = False) -> str:
    """Given a set of links return the html for keyboard navigation
    """
    htmlStr = '<div class="transparent"><ul>\n'

    if banner:
        htmlStr += '<pre aria-label="">\n' + banner + '\n<br><br></pre>\n'

    if subHeading:
        htmlStr += '<strong><label class="transparent">' + \
            subHeading + '</label></strong><br>\n'

    # show new follower approvals
    if usersPath and translate and followApprovals:
        htmlStr += '<strong><label class="transparent">' + \
            '<a href="' + usersPath + '/followers#timeline">' + \
            translate['Approve follow requests'] + '</a>' + \
            '</label></strong><br><br>\n'

    # show the list of links
    for title, url in links.items():
        accessKeyStr = ''
        if accessKeys.get(title):
            accessKeyStr = 'accesskey="' + accessKeys[title] + '"'

        htmlStr += '<li><label class="transparent">' + \
            '<a href="' + str(url) + '" ' + accessKeyStr + '>' + \
            str(title) + '</a></label></li>\n'
    htmlStr += '</ul></div>\n'
    return htmlStr


def begin_edit_section(label: str) -> str:
    """returns the html for begining a dropdown section on edit profile screen
    """
    return \
        '    <details><summary class="cw">' + label + '</summary>\n' + \
        '<div class="container">'


def end_edit_section() -> str:
    """returns the html for ending a dropdown section on edit profile screen
    """
    return '    </div></details>\n'


def edit_text_field(label: str, name: str, value: str = "",
                    placeholder: str = "", required: bool = False) -> str:
    """Returns html for editing a text field
    """
    if value is None:
        value = ''
    placeholderStr = ''
    if placeholder:
        placeholderStr = ' placeholder="' + placeholder + '"'
    requiredStr = ''
    if required:
        requiredStr = ' required'
    textFieldStr = ''
    if label:
        textFieldStr = \
            '<label class="labels">' + label + '</label><br>\n'
    textFieldStr += \
        '      <input type="text" name="' + name + '" value="' + \
        value + '"' + placeholderStr + requiredStr + '>\n'
    return textFieldStr


def edit_number_field(label: str, name: str, value: int,
                      minValue: int, maxValue: int,
                      placeholder: int) -> str:
    """Returns html for editing an integer number field
    """
    if value is None:
        value = ''
    placeholderStr = ''
    if placeholder:
        placeholderStr = ' placeholder="' + str(placeholder) + '"'
    return \
        '<label class="labels">' + label + '</label><br>\n' + \
        '      <input type="number" name="' + name + '" value="' + \
        str(value) + '"' + placeholderStr + ' ' + \
        'min="' + str(minValue) + '" max="' + str(maxValue) + '" step="1">\n'


def edit_currency_field(label: str, name: str, value: str,
                        placeholder: str, required: bool) -> str:
    """Returns html for editing a currency field
    """
    if value is None:
        value = '0.00'
    placeholderStr = ''
    if placeholder:
        if placeholder.isdigit():
            placeholderStr = ' placeholder="' + str(placeholder) + '"'
    requiredStr = ''
    if required:
        requiredStr = ' required'
    return \
        '<label class="labels">' + label + '</label><br>\n' + \
        '      <input type="text" name="' + name + '" value="' + \
        str(value) + '"' + placeholderStr + ' ' + \
        ' pattern="^\\d{1,3}(,\\d{3})*(\\.\\d+)?" data-type="currency"' + \
        requiredStr + '>\n'


def edit_check_box(label: str, name: str, checked: bool) -> str:
    """Returns html for editing a checkbox field
    """
    checkedStr = ''
    if checked:
        checkedStr = ' checked'

    return \
        '      <input type="checkbox" class="profilecheckbox" ' + \
        'name="' + name + '"' + checkedStr + '> ' + label + '<br>\n'


def edit_text_area(label: str, name: str, value: str,
                   height: int, placeholder: str, spellcheck: bool) -> str:
    """Returns html for editing a textarea field
    """
    if value is None:
        value = ''
    text = ''
    if label:
        text = '<label class="labels">' + label + '</label><br>\n'
    text += \
        '      <textarea id="message" placeholder=' + \
        '"' + placeholder + '" '
    text += 'name="' + name + '" '
    text += 'style="height:' + str(height) + 'px" '
    text += 'spellcheck="' + str(spellcheck).lower() + '">'
    text += value + '</textarea>\n'
    return text


def html_search_result_share(base_dir: str, sharedItem: {}, translate: {},
                             http_prefix: str, domain_full: str,
                             contactNickname: str, itemID: str,
                             actor: str, sharesFileType: str,
                             category: str) -> str:
    """Returns the html for an individual shared item
    """
    sharedItemsForm = '<div class="container">\n'
    sharedItemsForm += \
        '<p class="share-title">' + sharedItem['displayName'] + '</p>\n'
    if sharedItem.get('imageUrl'):
        sharedItemsForm += \
            '<a href="' + sharedItem['imageUrl'] + '">\n'
        sharedItemsForm += \
            '<img loading="lazy" src="' + sharedItem['imageUrl'] + \
            '" alt="Item image"></a>\n'
    sharedItemsForm += '<p>' + sharedItem['summary'] + '</p>\n<p>'
    if sharedItem.get('itemQty'):
        if sharedItem['itemQty'] > 1:
            sharedItemsForm += \
                '<b>' + translate['Quantity'] + \
                ':</b> ' + str(sharedItem['itemQty']) + '<br>'
    sharedItemsForm += \
        '<b>' + translate['Type'] + ':</b> ' + sharedItem['itemType'] + '<br>'
    sharedItemsForm += \
        '<b>' + translate['Category'] + ':</b> ' + \
        sharedItem['category'] + '<br>'
    if sharedItem.get('location'):
        sharedItemsForm += \
            '<b>' + translate['Location'] + ':</b> ' + \
            sharedItem['location'] + '<br>'
    contactTitleStr = translate['Contact']
    if sharedItem.get('itemPrice') and \
       sharedItem.get('itemCurrency'):
        if is_float(sharedItem['itemPrice']):
            if float(sharedItem['itemPrice']) > 0:
                sharedItemsForm += \
                    ' <b>' + translate['Price'] + \
                    ':</b> ' + sharedItem['itemPrice'] + \
                    ' ' + sharedItem['itemCurrency']
                contactTitleStr = translate['Buy']
    sharedItemsForm += '</p>\n'
    contactActor = \
        local_actor_url(http_prefix, contactNickname, domain_full)
    buttonStyleStr = 'button'
    if category == 'accommodation':
        contactTitleStr = translate['Request to stay']
        buttonStyleStr = 'contactbutton'

    sharedItemsForm += \
        '<p>' + \
        '<a href="' + actor + '?replydm=sharedesc:' + \
        sharedItem['displayName'] + '?mention=' + contactActor + \
        '?category=' + category + \
        '"><button class="' + buttonStyleStr + '">' + contactTitleStr + \
        '</button></a>\n' + \
        '<a href="' + contactActor + '"><button class="button">' + \
        translate['Profile'] + '</button></a>\n'

    # should the remove button be shown?
    showRemoveButton = False
    nickname = get_nickname_from_actor(actor)
    if actor.endswith('/users/' + contactNickname):
        showRemoveButton = True
    elif is_moderator(base_dir, nickname):
        showRemoveButton = True
    else:
        adminNickname = get_config_param(base_dir, 'admin')
        if adminNickname:
            if actor.endswith('/users/' + adminNickname):
                showRemoveButton = True

    if showRemoveButton:
        if sharesFileType == 'shares':
            sharedItemsForm += \
                ' <a href="' + actor + '?rmshare=' + \
                itemID + '"><button class="button">' + \
                translate['Remove'] + '</button></a>\n'
        else:
            sharedItemsForm += \
                ' <a href="' + actor + '?rmwanted=' + \
                itemID + '"><button class="button">' + \
                translate['Remove'] + '</button></a>\n'
    sharedItemsForm += '</p></div>\n'
    return sharedItemsForm


def html_show_share(base_dir: str, domain: str, nickname: str,
                    http_prefix: str, domain_full: str,
                    itemID: str, translate: {},
                    shared_items_federated_domains: [],
                    defaultTimeline: str, theme: str,
                    sharesFileType: str, category: str) -> str:
    """Shows an individual shared item after selecting it from the left column
    """
    sharesJson = None

    shareUrl = itemID.replace('___', '://').replace('--', '/')
    contactNickname = get_nickname_from_actor(shareUrl)
    if not contactNickname:
        return None

    if '://' + domain_full + '/' in shareUrl:
        # shared item on this instance
        sharesFilename = \
            acct_dir(base_dir, contactNickname, domain) + '/' + \
            sharesFileType + '.json'
        if not os.path.isfile(sharesFilename):
            return None
        sharesJson = load_json(sharesFilename)
    else:
        # federated shared item
        if sharesFileType == 'shares':
            catalogsDir = base_dir + '/cache/catalogs'
        else:
            catalogsDir = base_dir + '/cache/wantedItems'
        if not os.path.isdir(catalogsDir):
            return None
        for subdir, dirs, files in os.walk(catalogsDir):
            for f in files:
                if '#' in f:
                    continue
                if not f.endswith('.' + sharesFileType + '.json'):
                    continue
                federatedDomain = f.split('.')[0]
                if federatedDomain not in shared_items_federated_domains:
                    continue
                sharesFilename = catalogsDir + '/' + f
                sharesJson = load_json(sharesFilename)
                if not sharesJson:
                    continue
                if sharesJson.get(itemID):
                    break
            break

    if not sharesJson:
        return None
    if not sharesJson.get(itemID):
        return None
    sharedItem = sharesJson[itemID]
    actor = local_actor_url(http_prefix, nickname, domain_full)

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        get_banner_file(base_dir, nickname, domain, theme)

    shareStr = \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + \
        defaultTimeline + '" title="" alt="">\n'
    shareStr += '<img loading="lazy" class="timeline-banner" ' + \
        'alt="" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" /></a>\n' + \
        '</header><br>\n'
    shareStr += \
        html_search_result_share(base_dir, sharedItem, translate, http_prefix,
                                 domain_full, contactNickname, itemID,
                                 actor, sharesFileType, category)

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'
    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')

    return html_header_with_external_style(cssFilename,
                                           instanceTitle, None) + \
        shareStr + html_footer()


def set_custom_background(base_dir: str, background: str,
                          newBackground: str) -> str:
    """Sets a custom background
    Returns the extension, if found
    """
    ext = 'jpg'
    if os.path.isfile(base_dir + '/img/' + background + '.' + ext):
        if not newBackground:
            newBackground = background
        if not os.path.isfile(base_dir + '/accounts/' +
                              newBackground + '.' + ext):
            copyfile(base_dir + '/img/' + background + '.' + ext,
                     base_dir + '/accounts/' + newBackground + '.' + ext)
        return ext
    return None
