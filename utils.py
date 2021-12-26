__filename__ = "utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import re
import time
import shutil
import datetime
import json
import idna
import locale
from pprint import pprint
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from followingCalendar import addPersonToCalendar

# posts containing these strings will always get screened out,
# both incoming and outgoing.
# Could include dubious clacks or admin dogwhistles
INVALID_CHARACTERS = (
    '卐', '卍', '࿕', '࿖', '࿗', '࿘', 'ϟϟ', '🏳️‍🌈🚫', '⚡⚡'
)


def local_actor_url(http_prefix: str, nickname: str, domain_full: str) -> str:
    """Returns the url for an actor on this instance
    """
    return http_prefix + '://' + domain_full + '/users/' + nickname


def get_actor_languages_list(actor_json: {}) -> []:
    """Returns a list containing languages used by the given actor
    """
    if not actor_json.get('attachment'):
        return []
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('languages'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        if isinstance(property_value['value'], list):
            lang_list = property_value['value']
            lang_list.sort()
            return lang_list
        elif isinstance(property_value['value'], str):
            lang_str = property_value['value']
            lang_list_temp = []
            if ',' in lang_str:
                lang_list_temp = lang_str.split(',')
            elif ';' in lang_str:
                lang_list_temp = lang_str.split(';')
            elif '/' in lang_str:
                lang_list_temp = lang_str.split('/')
            elif '+' in lang_str:
                lang_list_temp = lang_str.split('+')
            elif ' ' in lang_str:
                lang_list_temp = lang_str.split(' ')
            lang_list = []
            for lang in lang_list_temp:
                lang = lang.strip()
                if lang not in lang_list:
                    lang_list.append(lang)
            lang_list.sort()
            return lang_list
    return []


def get_content_from_post(post_json_object: {}, system_language: str,
                          languages_understood: []) -> str:
    """Returns the content from the post in the given language
    including searching for a matching entry within contentMap
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    if not this_post_json.get('content'):
        return ''
    content = ''
    if this_post_json.get('contentMap'):
        if isinstance(this_post_json['contentMap'], dict):
            if this_post_json['contentMap'].get(system_language):
                sys_lang = this_post_json['contentMap'][system_language]
                if isinstance(sys_lang, str):
                    return this_post_json['contentMap'][system_language]
            else:
                # is there a contentMap entry for one of
                # the understood languages?
                for lang in languages_understood:
                    if this_post_json['contentMap'].get(lang):
                        return this_post_json['contentMap'][lang]
    else:
        if isinstance(this_post_json['content'], str):
            content = this_post_json['content']
    return content


def get_base_content_from_post(post_json_object: {},
                               system_language: str) -> str:
    """Returns the content from the post in the given language
    """
    this_post_json = post_json_object
    if has_object_dict(post_json_object):
        this_post_json = post_json_object['object']
    if not this_post_json.get('content'):
        return ''
    return this_post_json['content']


def acct_dir(base_dir: str, nickname: str, domain: str) -> str:
    return base_dir + '/accounts/' + nickname + '@' + domain


def is_featured_writer(base_dir: str, nickname: str, domain: str) -> bool:
    """Is the given account a featured writer, appearing in the features
    timeline on news instances?
    """
    features_blocked_filename = \
        acct_dir(base_dir, nickname, domain) + '/.nofeatures'
    return not os.path.isfile(features_blocked_filename)


def refresh_newswire(base_dir: str):
    """Causes the newswire to be updates after a change to user accounts
    """
    refresh_newswire_filename = base_dir + '/accounts/.refresh_newswire'
    if os.path.isfile(refresh_newswire_filename):
        return
    with open(refresh_newswire_filename, 'w+') as refresh_file:
        refresh_file.write('\n')


def get_sha_256(msg: str):
    """Returns a SHA256 hash of the given string
    """
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(msg)
    return digest.finalize()


def get_sha_512(msg: str):
    """Returns a SHA512 hash of the given string
    """
    digest = hashes.Hash(hashes.SHA512(), backend=default_backend())
    digest.update(msg)
    return digest.finalize()


def _local_network_host(host: str) -> bool:
    """Returns true if the given host is on the local network
    """
    if host.startswith('localhost') or \
       host.startswith('192.') or \
       host.startswith('127.') or \
       host.startswith('10.'):
        return True
    return False


def decoded_host(host: str) -> str:
    """Convert hostname to internationalized domain
    https://en.wikipedia.org/wiki/Internationalized_domain_name
    """
    if ':' not in host:
        # eg. mydomain:8000
        if not _local_network_host(host):
            if not host.endswith('.onion'):
                if not host.endswith('.i2p'):
                    return idna.decode(host)
    return host


def get_locked_account(actor_json: {}) -> bool:
    """Returns whether the given account requires follower approval
    """
    if not actor_json.get('manuallyApprovesFollowers'):
        return False
    if actor_json['manuallyApprovesFollowers'] is True:
        return True
    return False


def has_users_path(path_str: str) -> bool:
    """Whether there is a /users/ path (or equivalent) in the given string
    """
    users_list = get_user_paths()
    for users_str in users_list:
        if users_str in path_str:
            return True
    if '://' in path_str:
        domain = path_str.split('://')[1]
        if '/' in domain:
            domain = domain.split('/')[0]
        if '://' + domain + '/' not in path_str:
            return False
        nickname = path_str.split('://' + domain + '/')[1]
        if '/' in nickname or '.' in nickname:
            return False
        return True
    return False


def valid_post_date(published: str, max_age_days: int, debug: bool) -> bool:
    """Returns true if the published date is recent and is not in the future
    """
    baseline_time = datetime.datetime(1970, 1, 1)

    daysDiff = datetime.datetime.utcnow() - baseline_time
    now_days_since_epoch = daysDiff.days

    try:
        post_time_object = \
            datetime.datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
    except BaseException:
        if debug:
            print('EX: valid_post_date invalid published date ' +
                  str(published))
        return False

    days_diff = post_time_object - baseline_time
    post_days_since_epoch = days_diff.days

    if post_days_since_epoch > now_days_since_epoch:
        if debug:
            print("Inbox post has a published date in the future!")
        return False

    if now_days_since_epoch - post_days_since_epoch >= max_age_days:
        if debug:
            print("Inbox post is not recent enough")
        return False
    return True


def get_full_domain(domain: str, port: int) -> str:
    """Returns the full domain name, including port number
    """
    if not port:
        return domain
    if ':' in domain:
        return domain
    if port == 80 or port == 443:
        return domain
    return domain + ':' + str(port)


def isDormant(base_dir: str, nickname: str, domain: str, actor: str,
              dormant_months: int) -> bool:
    """Is the given followed actor dormant, from the standpoint
    of the given account
    """
    lastSeenFilename = acct_dir(base_dir, nickname, domain) + \
        '/lastseen/' + actor.replace('/', '#') + '.txt'

    if not os.path.isfile(lastSeenFilename):
        return False

    daysSinceEpochStr = None
    try:
        with open(lastSeenFilename, 'r') as lastSeenFile:
            daysSinceEpochStr = lastSeenFile.read()
    except OSError:
        print('EX: failed to read last seen ' + lastSeenFilename)
        return False

    if daysSinceEpochStr:
        daysSinceEpoch = int(daysSinceEpochStr)
        currTime = datetime.datetime.utcnow()
        currDaysSinceEpoch = (currTime - datetime.datetime(1970, 1, 1)).days
        timeDiffMonths = \
            int((currDaysSinceEpoch - daysSinceEpoch) / 30)
        if timeDiffMonths >= dormant_months:
            return True
    return False


def isEditor(base_dir: str, nickname: str) -> bool:
    """Returns true if the given nickname is an editor
    """
    editorsFile = base_dir + '/accounts/editors.txt'

    if not os.path.isfile(editorsFile):
        adminName = getConfigParam(base_dir, 'admin')
        if not adminName:
            return False
        if adminName == nickname:
            return True
        return False

    with open(editorsFile, 'r') as f:
        lines = f.readlines()
        if len(lines) == 0:
            adminName = getConfigParam(base_dir, 'admin')
            if not adminName:
                return False
            if adminName == nickname:
                return True
        for editor in lines:
            editor = editor.strip('\n').strip('\r')
            if editor == nickname:
                return True
    return False


def isArtist(base_dir: str, nickname: str) -> bool:
    """Returns true if the given nickname is an artist
    """
    artistsFile = base_dir + '/accounts/artists.txt'

    if not os.path.isfile(artistsFile):
        adminName = getConfigParam(base_dir, 'admin')
        if not adminName:
            return False
        if adminName == nickname:
            return True
        return False

    with open(artistsFile, 'r') as f:
        lines = f.readlines()
        if len(lines) == 0:
            adminName = getConfigParam(base_dir, 'admin')
            if not adminName:
                return False
            if adminName == nickname:
                return True
        for artist in lines:
            artist = artist.strip('\n').strip('\r')
            if artist == nickname:
                return True
    return False


def getVideoExtensions() -> []:
    """Returns a list of the possible video file extensions
    """
    return ('mp4', 'webm', 'ogv')


def getAudioExtensions() -> []:
    """Returns a list of the possible audio file extensions
    """
    return ('mp3', 'ogg', 'flac')


def getImageExtensions() -> []:
    """Returns a list of the possible image file extensions
    """
    return ('png', 'jpg', 'jpeg', 'gif', 'webp', 'avif', 'svg', 'ico')


def getImageMimeType(imageFilename: str) -> str:
    """Returns the mime type for the given image
    """
    extensionsToMime = {
        'png': 'png',
        'jpg': 'jpeg',
        'gif': 'gif',
        'avif': 'avif',
        'svg': 'svg+xml',
        'webp': 'webp',
        'ico': 'x-icon'
    }
    for ext, mimeExt in extensionsToMime.items():
        if imageFilename.endswith('.' + ext):
            return 'image/' + mimeExt
    return 'image/png'


def getImageExtensionFromMimeType(contentType: str) -> str:
    """Returns the image extension from a mime type, such as image/jpeg
    """
    imageMedia = {
        'png': 'png',
        'jpeg': 'jpg',
        'gif': 'gif',
        'svg+xml': 'svg',
        'webp': 'webp',
        'avif': 'avif',
        'x-icon': 'ico'
    }
    for mimeExt, ext in imageMedia.items():
        if contentType.endswith(mimeExt):
            return ext
    return 'png'


def getMediaExtensions() -> []:
    """Returns a list of the possible media file extensions
    """
    return getImageExtensions() + getVideoExtensions() + getAudioExtensions()


def getImageFormats() -> str:
    """Returns a string of permissable image formats
    used when selecting an image for a new post
    """
    imageExt = getImageExtensions()

    imageFormats = ''
    for ext in imageExt:
        if imageFormats:
            imageFormats += ', '
        imageFormats += '.' + ext
    return imageFormats


def isImageFile(filename: str) -> bool:
    """Is the given filename an image?
    """
    for ext in getImageExtensions():
        if filename.endswith('.' + ext):
            return True
    return False


def getMediaFormats() -> str:
    """Returns a string of permissable media formats
    used when selecting an attachment for a new post
    """
    mediaExt = getMediaExtensions()

    mediaFormats = ''
    for ext in mediaExt:
        if mediaFormats:
            mediaFormats += ', '
        mediaFormats += '.' + ext
    return mediaFormats


def removeHtml(content: str) -> str:
    """Removes html links from the given content.
    Used to ensure that profile descriptions don't contain dubious content
    """
    if '<' not in content:
        return content
    removing = False
    content = content.replace('<a href', ' <a href')
    content = content.replace('<q>', '"').replace('</q>', '"')
    content = content.replace('</p>', '\n\n').replace('<br>', '\n')
    result = ''
    for ch in content:
        if ch == '<':
            removing = True
        elif ch == '>':
            removing = False
        elif not removing:
            result += ch

    plainText = result.replace('  ', ' ')

    # insert spaces after full stops
    strLen = len(plainText)
    result = ''
    for i in range(strLen):
        result += plainText[i]
        if plainText[i] == '.' and i < strLen - 1:
            if plainText[i + 1] >= 'A' and plainText[i + 1] <= 'Z':
                result += ' '

    result = result.replace('  ', ' ').strip()
    return result


def firstParagraphFromString(content: str) -> str:
    """Get the first paragraph from a blog post
    to be used as a summary in the newswire feed
    """
    if '<p>' not in content or '</p>' not in content:
        return removeHtml(content)
    paragraph = content.split('<p>')[1]
    if '</p>' in paragraph:
        paragraph = paragraph.split('</p>')[0]
    return removeHtml(paragraph)


def isSystemAccount(nickname: str) -> bool:
    """Returns true if the given nickname is a system account
    """
    if nickname == 'news' or nickname == 'inbox':
        return True
    return False


def _createConfig(base_dir: str) -> None:
    """Creates a configuration file
    """
    configFilename = base_dir + '/config.json'
    if os.path.isfile(configFilename):
        return
    configJson = {
    }
    saveJson(configJson, configFilename)


def setConfigParam(base_dir: str, variableName: str, variableValue) -> None:
    """Sets a configuration value
    """
    _createConfig(base_dir)
    configFilename = base_dir + '/config.json'
    configJson = {}
    if os.path.isfile(configFilename):
        configJson = loadJson(configFilename)
    configJson[variableName] = variableValue
    saveJson(configJson, configFilename)


def getConfigParam(base_dir: str, variableName: str):
    """Gets a configuration value
    """
    _createConfig(base_dir)
    configFilename = base_dir + '/config.json'
    configJson = loadJson(configFilename)
    if configJson:
        if variableName in configJson:
            return configJson[variableName]
    return None


def isSuspended(base_dir: str, nickname: str) -> bool:
    """Returns true if the given nickname is suspended
    """
    adminNickname = getConfigParam(base_dir, 'admin')
    if not adminNickname:
        return False
    if nickname == adminNickname:
        return False

    suspendedFilename = base_dir + '/accounts/suspended.txt'
    if os.path.isfile(suspendedFilename):
        with open(suspendedFilename, 'r') as f:
            lines = f.readlines()
        for suspended in lines:
            if suspended.strip('\n').strip('\r') == nickname:
                return True
    return False


def getFollowersList(base_dir: str,
                     nickname: str, domain: str,
                     followFile='following.txt') -> []:
    """Returns a list of followers for the given account
    """
    filename = acct_dir(base_dir, nickname, domain) + '/' + followFile

    if not os.path.isfile(filename):
        return []

    with open(filename, 'r') as f:
        lines = f.readlines()
        for i in range(len(lines)):
            lines[i] = lines[i].strip()
        return lines
    return []


def getFollowersOfPerson(base_dir: str,
                         nickname: str, domain: str,
                         followFile='following.txt') -> []:
    """Returns a list containing the followers of the given person
    Used by the shared inbox to know who to send incoming mail to
    """
    followers = []
    domain = removeDomainPort(domain)
    handle = nickname + '@' + domain
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        return followers
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for account in dirs:
            filename = os.path.join(subdir, account) + '/' + followFile
            if account == handle or \
               account.startswith('inbox@') or \
               account.startswith('news@'):
                continue
            if not os.path.isfile(filename):
                continue
            with open(filename, 'r') as followingfile:
                for followingHandle in followingfile:
                    followingHandle2 = followingHandle.replace('\n', '')
                    followingHandle2 = followingHandle2.replace('\r', '')
                    if followingHandle2 == handle:
                        if account not in followers:
                            followers.append(account)
                        break
        break
    return followers


def removeIdEnding(idStr: str) -> str:
    """Removes endings such as /activity and /undo
    """
    if idStr.endswith('/activity'):
        idStr = idStr[:-len('/activity')]
    elif idStr.endswith('/undo'):
        idStr = idStr[:-len('/undo')]
    elif idStr.endswith('/event'):
        idStr = idStr[:-len('/event')]
    elif idStr.endswith('/replies'):
        idStr = idStr[:-len('/replies')]
    if idStr.endswith('#Create'):
        idStr = idStr.split('#Create')[0]
    return idStr


def removeHashFromPostId(postId: str) -> str:
    """Removes any has from a post id
    """
    if '#' not in postId:
        return postId
    return postId.split('#')[0]


def getProtocolPrefixes() -> []:
    """Returns a list of valid prefixes
    """
    return ('https://', 'http://', 'ftp://',
            'dat://', 'i2p://', 'gnunet://',
            'hyper://', 'gemini://', 'gopher://')


def getLinkPrefixes() -> []:
    """Returns a list of valid web link prefixes
    """
    return ('https://', 'http://', 'ftp://',
            'dat://', 'i2p://', 'gnunet://', 'payto://',
            'hyper://', 'gemini://', 'gopher://', 'briar:')


def removeAvatarFromCache(base_dir: str, actorStr: str) -> None:
    """Removes any existing avatar entries from the cache
    This avoids duplicate entries with differing extensions
    """
    avatarFilenameExtensions = getImageExtensions()
    for extension in avatarFilenameExtensions:
        avatarFilename = \
            base_dir + '/cache/avatars/' + actorStr + '.' + extension
        if os.path.isfile(avatarFilename):
            try:
                os.remove(avatarFilename)
            except OSError:
                print('EX: removeAvatarFromCache ' +
                      'unable to delete cached avatar ' + str(avatarFilename))


def saveJson(jsonObject: {}, filename: str) -> bool:
    """Saves json to a file
    """
    tries = 0
    while tries < 5:
        try:
            with open(filename, 'w+') as fp:
                fp.write(json.dumps(jsonObject))
                return True
        except OSError:
            print('EX: saveJson ' + str(tries))
            time.sleep(1)
            tries += 1
    return False


def loadJson(filename: str, delaySec: int = 2, maxTries: int = 5) -> {}:
    """Makes a few attempts to load a json formatted file
    """
    jsonObject = None
    tries = 0
    while tries < maxTries:
        try:
            with open(filename, 'r') as fp:
                data = fp.read()
                jsonObject = json.loads(data)
                break
        except BaseException:
            print('EX: loadJson exception ' + str(filename))
            if delaySec > 0:
                time.sleep(delaySec)
            tries += 1
    return jsonObject


def loadJsonOnionify(filename: str, domain: str, onion_domain: str,
                     delaySec: int = 2) -> {}:
    """Makes a few attempts to load a json formatted file
    This also converts the domain name to the onion domain
    """
    jsonObject = None
    tries = 0
    while tries < 5:
        try:
            with open(filename, 'r') as fp:
                data = fp.read()
                if data:
                    data = data.replace(domain, onion_domain)
                    data = data.replace('https:', 'http:')
                    print('*****data: ' + data)
                jsonObject = json.loads(data)
                break
        except BaseException:
            print('EX: loadJsonOnionify exception ' + str(filename))
            if delaySec > 0:
                time.sleep(delaySec)
            tries += 1
    return jsonObject


def getStatusNumber(publishedStr: str = None) -> (str, str):
    """Returns the status number and published date
    """
    if not publishedStr:
        currTime = datetime.datetime.utcnow()
    else:
        currTime = \
            datetime.datetime.strptime(publishedStr, '%Y-%m-%dT%H:%M:%SZ')
    daysSinceEpoch = (currTime - datetime.datetime(1970, 1, 1)).days
    # status is the number of seconds since epoch
    statusNumber = \
        str(((daysSinceEpoch * 24 * 60 * 60) +
             (currTime.hour * 60 * 60) +
             (currTime.minute * 60) +
             currTime.second) * 1000 +
            int(currTime.microsecond / 1000))
    # See https://github.com/tootsuite/mastodon/blob/
    # 995f8b389a66ab76ec92d9a240de376f1fc13a38/lib/mastodon/snowflake.rb
    # use the leftover microseconds as the sequence number
    sequenceId = currTime.microsecond % 1000
    # shift by 16bits "sequence data"
    statusNumber = str((int(statusNumber) << 16) + sequenceId)
    published = currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    return statusNumber, published


def evilIncarnate() -> []:
    return ('fedilist.com', 'gab.com', 'gabfed.com', 'spinster.xyz',
            'kiwifarms.cc', 'djitter.com')


def isEvil(domain: str) -> bool:
    # https://www.youtube.com/watch?v=5qw1hcevmdU
    if not isinstance(domain, str):
        print('WARN: Malformed domain ' + str(domain))
        return True
    # if a domain contains any of these strings then it is
    # declaring itself to be hostile
    evilEmporium = (
        'nazi', 'extremis', 'extreemis', 'gendercritic',
        'kiwifarm', 'illegal', 'raplst', 'rapist',
        'antivax', 'plandemic'
    )
    for hostileStr in evilEmporium:
        if hostileStr in domain:
            return True
    evilDomains = evilIncarnate()
    for concentratedEvil in evilDomains:
        if domain.endswith(concentratedEvil):
            return True
    return False


def containsInvalidChars(jsonStr: str) -> bool:
    """Does the given json string contain invalid characters?
    """
    for isInvalid in INVALID_CHARACTERS:
        if isInvalid in jsonStr:
            return True
    return False


def removeInvalidChars(text: str) -> str:
    """Removes any invalid characters from a string
    """
    for isInvalid in INVALID_CHARACTERS:
        if isInvalid not in text:
            continue
        text = text.replace(isInvalid, '')
    return text


def createPersonDir(nickname: str, domain: str, base_dir: str,
                    dirname: str) -> str:
    """Create a directory for a person
    """
    handle = nickname + '@' + domain
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        os.mkdir(base_dir + '/accounts/' + handle)
    boxDir = base_dir + '/accounts/' + handle + '/' + dirname
    if not os.path.isdir(boxDir):
        os.mkdir(boxDir)
    return boxDir


def createOutboxDir(nickname: str, domain: str, base_dir: str) -> str:
    """Create an outbox for a person
    """
    return createPersonDir(nickname, domain, base_dir, 'outbox')


def createInboxQueueDir(nickname: str, domain: str, base_dir: str) -> str:
    """Create an inbox queue and returns the feed filename and directory
    """
    return createPersonDir(nickname, domain, base_dir, 'queue')


def domainPermitted(domain: str, federation_list: []):
    if len(federation_list) == 0:
        return True
    domain = removeDomainPort(domain)
    if domain in federation_list:
        return True
    return False


def urlPermitted(url: str, federation_list: []):
    if isEvil(url):
        return False
    if not federation_list:
        return True
    for domain in federation_list:
        if domain in url:
            return True
    return False


def getLocalNetworkAddresses() -> []:
    """Returns patterns for local network address detection
    """
    return ('localhost', '127.0.', '192.168', '10.0.')


def isLocalNetworkAddress(ipAddress: str) -> bool:
    """
    """
    localIPs = getLocalNetworkAddresses()
    for ipAddr in localIPs:
        if ipAddress.startswith(ipAddr):
            return True
    return False


def _isDangerousString(content: str, allow_local_network_access: bool,
                       separators: [], invalidStrings: []) -> bool:
    """Returns true if the given string is dangerous
    """
    for separatorStyle in separators:
        startChar = separatorStyle[0]
        endChar = separatorStyle[1]
        if startChar not in content:
            continue
        if endChar not in content:
            continue
        contentSections = content.split(startChar)
        invalidPartials = ()
        if not allow_local_network_access:
            invalidPartials = getLocalNetworkAddresses()
        for markup in contentSections:
            if endChar not in markup:
                continue
            markup = markup.split(endChar)[0].strip()
            for partialMatch in invalidPartials:
                if partialMatch in markup:
                    return True
            if ' ' not in markup:
                for badStr in invalidStrings:
                    if badStr in markup:
                        return True
            else:
                for badStr in invalidStrings:
                    if badStr + ' ' in markup:
                        return True
    return False


def dangerousMarkup(content: str, allow_local_network_access: bool) -> bool:
    """Returns true if the given content contains dangerous html markup
    """
    separators = [['<', '>'], ['&lt;', '&gt;']]
    invalidStrings = [
        'script', 'noscript', 'code', 'pre',
        'canvas', 'style', 'abbr',
        'frame', 'iframe', 'html', 'body',
        'hr', 'allow-popups', 'allow-scripts'
    ]
    return _isDangerousString(content, allow_local_network_access,
                              separators, invalidStrings)


def dangerousSVG(content: str, allow_local_network_access: bool) -> bool:
    """Returns true if the given svg file content contains dangerous scripts
    """
    separators = [['<', '>'], ['&lt;', '&gt;']]
    invalidStrings = [
        'script'
    ]
    return _isDangerousString(content, allow_local_network_access,
                              separators, invalidStrings)


def getDisplayName(base_dir: str, actor: str, person_cache: {}) -> str:
    """Returns the display name for the given actor
    """
    if '/statuses/' in actor:
        actor = actor.split('/statuses/')[0]
    if not person_cache.get(actor):
        return None
    nameFound = None
    if person_cache[actor].get('actor'):
        if person_cache[actor]['actor'].get('name'):
            nameFound = person_cache[actor]['actor']['name']
    else:
        # Try to obtain from the cached actors
        cachedActorFilename = \
            base_dir + '/cache/actors/' + (actor.replace('/', '#')) + '.json'
        if os.path.isfile(cachedActorFilename):
            actor_json = loadJson(cachedActorFilename, 1)
            if actor_json:
                if actor_json.get('name'):
                    nameFound = actor_json['name']
    if nameFound:
        if dangerousMarkup(nameFound, False):
            nameFound = "*ADVERSARY*"
    return nameFound


def _genderFromString(translate: {}, text: str) -> str:
    """Given some text, does it contain a gender description?
    """
    gender = None
    if not text:
        return None
    textOrig = text
    text = text.lower()
    if translate['He/Him'].lower() in text or \
       translate['boy'].lower() in text:
        gender = 'He/Him'
    elif (translate['She/Her'].lower() in text or
          translate['girl'].lower() in text):
        gender = 'She/Her'
    elif 'him' in text or 'male' in text:
        gender = 'He/Him'
    elif 'her' in text or 'she' in text or \
         'fem' in text or 'woman' in text:
        gender = 'She/Her'
    elif 'man' in text or 'He' in textOrig:
        gender = 'He/Him'
    return gender


def getGenderFromBio(base_dir: str, actor: str, person_cache: {},
                     translate: {}) -> str:
    """Tries to ascertain gender from bio description
    This is for use by text-to-speech for pitch setting
    """
    defaultGender = 'They/Them'
    if '/statuses/' in actor:
        actor = actor.split('/statuses/')[0]
    if not person_cache.get(actor):
        return defaultGender
    bioFound = None
    if translate:
        pronounStr = translate['pronoun'].lower()
    else:
        pronounStr = 'pronoun'
    actor_json = None
    if person_cache[actor].get('actor'):
        actor_json = person_cache[actor]['actor']
    else:
        # Try to obtain from the cached actors
        cachedActorFilename = \
            base_dir + '/cache/actors/' + (actor.replace('/', '#')) + '.json'
        if os.path.isfile(cachedActorFilename):
            actor_json = loadJson(cachedActorFilename, 1)
    if not actor_json:
        return defaultGender
    # is gender defined as a profile tag?
    if actor_json.get('attachment'):
        tagsList = actor_json['attachment']
        if isinstance(tagsList, list):
            # look for a gender field name
            for tag in tagsList:
                if not isinstance(tag, dict):
                    continue
                if not tag.get('name') or not tag.get('value'):
                    continue
                if tag['name'].lower() == \
                   translate['gender'].lower():
                    bioFound = tag['value']
                    break
                elif tag['name'].lower().startswith(pronounStr):
                    bioFound = tag['value']
                    break
            # the field name could be anything,
            # just look at the value
            if not bioFound:
                for tag in tagsList:
                    if not isinstance(tag, dict):
                        continue
                    if not tag.get('name') or not tag.get('value'):
                        continue
                    gender = _genderFromString(translate, tag['value'])
                    if gender:
                        return gender
    # if not then use the bio
    if not bioFound and actor_json.get('summary'):
        bioFound = actor_json['summary']
    if not bioFound:
        return defaultGender
    gender = _genderFromString(translate, bioFound)
    if not gender:
        gender = defaultGender
    return gender


def getNicknameFromActor(actor: str) -> str:
    """Returns the nickname from an actor url
    """
    if actor.startswith('@'):
        actor = actor[1:]
    usersPaths = get_user_paths()
    for possiblePath in usersPaths:
        if possiblePath in actor:
            nickStr = actor.split(possiblePath)[1].replace('@', '')
            if '/' not in nickStr:
                return nickStr
            else:
                return nickStr.split('/')[0]
    if '/@' in actor:
        # https://domain/@nick
        nickStr = actor.split('/@')[1]
        if '/' in nickStr:
            nickStr = nickStr.split('/')[0]
        return nickStr
    elif '@' in actor:
        nickStr = actor.split('@')[0]
        return nickStr
    elif '://' in actor:
        domain = actor.split('://')[1]
        if '/' in domain:
            domain = domain.split('/')[0]
        if '://' + domain + '/' not in actor:
            return None
        nickStr = actor.split('://' + domain + '/')[1]
        if '/' in nickStr or '.' in nickStr:
            return None
        return nickStr
    return None


def get_user_paths() -> []:
    """Returns possible user paths
    e.g. /users/nickname, /channel/nickname
    """
    return ('/users/', '/profile/', '/accounts/', '/channel/', '/u/',
            '/c/', '/video-channels/')


def getGroupPaths() -> []:
    """Returns possible group paths
    e.g. https://lemmy/c/groupname
    """
    return ['/c/', '/video-channels/']


def getDomainFromActor(actor: str) -> (str, int):
    """Returns the domain name from an actor url
    """
    if actor.startswith('@'):
        actor = actor[1:]
    port = None
    prefixes = getProtocolPrefixes()
    usersPaths = get_user_paths()
    for possiblePath in usersPaths:
        if possiblePath in actor:
            domain = actor.split(possiblePath)[0]
            for prefix in prefixes:
                domain = domain.replace(prefix, '')
            break
    if '/@' in actor:
        domain = actor.split('/@')[0]
        for prefix in prefixes:
            domain = domain.replace(prefix, '')
    elif '@' in actor:
        domain = actor.split('@')[1].strip()
    else:
        domain = actor
        for prefix in prefixes:
            domain = domain.replace(prefix, '')
        if '/' in actor:
            domain = domain.split('/')[0]
    if ':' in domain:
        port = getPortFromDomain(domain)
        domain = removeDomainPort(domain)
    return domain, port


def _setDefaultPetName(base_dir: str, nickname: str, domain: str,
                       followNickname: str, followDomain: str) -> None:
    """Sets a default petname
    This helps especially when using onion or i2p address
    """
    domain = removeDomainPort(domain)
    userPath = acct_dir(base_dir, nickname, domain)
    petnamesFilename = userPath + '/petnames.txt'

    petnameLookupEntry = followNickname + ' ' + \
        followNickname + '@' + followDomain + '\n'
    if not os.path.isfile(petnamesFilename):
        # if there is no existing petnames lookup file
        with open(petnamesFilename, 'w+') as petnamesFile:
            petnamesFile.write(petnameLookupEntry)
        return

    with open(petnamesFilename, 'r') as petnamesFile:
        petnamesStr = petnamesFile.read()
        if petnamesStr:
            petnamesList = petnamesStr.split('\n')
            for pet in petnamesList:
                if pet.startswith(followNickname + ' '):
                    # petname already exists
                    return
    # petname doesn't already exist
    with open(petnamesFilename, 'a+') as petnamesFile:
        petnamesFile.write(petnameLookupEntry)


def followPerson(base_dir: str, nickname: str, domain: str,
                 followNickname: str, followDomain: str,
                 federation_list: [], debug: bool,
                 group_account: bool,
                 followFile: str = 'following.txt') -> bool:
    """Adds a person to the follow list
    """
    followDomainStrLower = followDomain.lower().replace('\n', '')
    if not domainPermitted(followDomainStrLower,
                           federation_list):
        if debug:
            print('DEBUG: follow of domain ' +
                  followDomain + ' not permitted')
        return False
    if debug:
        print('DEBUG: follow of domain ' + followDomain)

    if ':' in domain:
        domainOnly = removeDomainPort(domain)
        handle = nickname + '@' + domainOnly
    else:
        handle = nickname + '@' + domain

    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('WARN: account for ' + handle + ' does not exist')
        return False

    if ':' in followDomain:
        followDomainOnly = removeDomainPort(followDomain)
        handleToFollow = followNickname + '@' + followDomainOnly
    else:
        handleToFollow = followNickname + '@' + followDomain

    if group_account:
        handleToFollow = '!' + handleToFollow

    # was this person previously unfollowed?
    unfollowedFilename = base_dir + '/accounts/' + handle + '/unfollowed.txt'
    if os.path.isfile(unfollowedFilename):
        if handleToFollow in open(unfollowedFilename).read():
            # remove them from the unfollowed file
            newLines = ''
            with open(unfollowedFilename, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if handleToFollow not in line:
                        newLines += line
            with open(unfollowedFilename, 'w+') as f:
                f.write(newLines)

    if not os.path.isdir(base_dir + '/accounts'):
        os.mkdir(base_dir + '/accounts')
    handleToFollow = followNickname + '@' + followDomain
    if group_account:
        handleToFollow = '!' + handleToFollow
    filename = base_dir + '/accounts/' + handle + '/' + followFile
    if os.path.isfile(filename):
        if handleToFollow in open(filename).read():
            if debug:
                print('DEBUG: follow already exists')
            return True
        # prepend to follow file
        try:
            with open(filename, 'r+') as f:
                content = f.read()
                if handleToFollow + '\n' not in content:
                    f.seek(0, 0)
                    f.write(handleToFollow + '\n' + content)
                    print('DEBUG: follow added')
        except Exception as ex:
            print('WARN: Failed to write entry to follow file ' +
                  filename + ' ' + str(ex))
    else:
        # first follow
        if debug:
            print('DEBUG: ' + handle +
                  ' creating new following file to follow ' + handleToFollow +
                  ', filename is ' + filename)
        with open(filename, 'w+') as f:
            f.write(handleToFollow + '\n')

    if followFile.endswith('following.txt'):
        # Default to adding new follows to the calendar.
        # Possibly this could be made optional
        # if following a person add them to the list of
        # calendar follows
        print('DEBUG: adding ' +
              followNickname + '@' + followDomain + ' to calendar of ' +
              nickname + '@' + domain)
        addPersonToCalendar(base_dir, nickname, domain,
                            followNickname, followDomain)
        # add a default petname
        _setDefaultPetName(base_dir, nickname, domain,
                           followNickname, followDomain)
    return True


def votesOnNewswireItem(status: []) -> int:
    """Returns the number of votes on a newswire item
    """
    totalVotes = 0
    for line in status:
        if 'vote:' in line:
            totalVotes += 1
    return totalVotes


def locateNewsVotes(base_dir: str, domain: str,
                    postUrl: str) -> str:
    """Returns the votes filename for a news post
    within the news user account
    """
    postUrl = \
        postUrl.strip().replace('\n', '').replace('\r', '')

    # if this post in the shared inbox?
    postUrl = removeIdEnding(postUrl.strip()).replace('/', '#')

    if postUrl.endswith('.json'):
        postUrl = postUrl + '.votes'
    else:
        postUrl = postUrl + '.json.votes'

    accountDir = base_dir + '/accounts/news@' + domain + '/'
    postFilename = accountDir + 'outbox/' + postUrl
    if os.path.isfile(postFilename):
        return postFilename

    return None


def locateNewsArrival(base_dir: str, domain: str,
                      postUrl: str) -> str:
    """Returns the arrival time for a news post
    within the news user account
    """
    postUrl = \
        postUrl.strip().replace('\n', '').replace('\r', '')

    # if this post in the shared inbox?
    postUrl = removeIdEnding(postUrl.strip()).replace('/', '#')

    if postUrl.endswith('.json'):
        postUrl = postUrl + '.arrived'
    else:
        postUrl = postUrl + '.json.arrived'

    accountDir = base_dir + '/accounts/news@' + domain + '/'
    postFilename = accountDir + 'outbox/' + postUrl
    if os.path.isfile(postFilename):
        with open(postFilename, 'r') as arrivalFile:
            arrival = arrivalFile.read()
            if arrival:
                arrivalDate = \
                    datetime.datetime.strptime(arrival,
                                               "%Y-%m-%dT%H:%M:%SZ")
                return arrivalDate

    return None


def clearFromPostCaches(base_dir: str, recentPostsCache: {},
                        postId: str) -> None:
    """Clears cached html for the given post, so that edits
    to news will appear
    """
    filename = '/postcache/' + postId + '.html'
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if acct.startswith('inbox@'):
                continue
            cacheDir = os.path.join(base_dir + '/accounts', acct)
            postFilename = cacheDir + filename
            if os.path.isfile(postFilename):
                try:
                    os.remove(postFilename)
                except OSError:
                    print('EX: clearFromPostCaches file not removed ' +
                          str(postFilename))
            # if the post is in the recent posts cache then remove it
            if recentPostsCache.get('index'):
                if postId in recentPostsCache['index']:
                    recentPostsCache['index'].remove(postId)
            if recentPostsCache.get('json'):
                if recentPostsCache['json'].get(postId):
                    del recentPostsCache['json'][postId]
            if recentPostsCache.get('html'):
                if recentPostsCache['html'].get(postId):
                    del recentPostsCache['html'][postId]
        break


def locatePost(base_dir: str, nickname: str, domain: str,
               postUrl: str, replies: bool = False) -> str:
    """Returns the filename for the given status post url
    """
    if not replies:
        extension = 'json'
    else:
        extension = 'replies'

    # if this post in the shared inbox?
    postUrl = removeIdEnding(postUrl.strip()).replace('/', '#')

    # add the extension
    postUrl = postUrl + '.' + extension

    # search boxes
    boxes = ('inbox', 'outbox', 'tlblogs')
    accountDir = acct_dir(base_dir, nickname, domain) + '/'
    for boxName in boxes:
        postFilename = accountDir + boxName + '/' + postUrl
        if os.path.isfile(postFilename):
            return postFilename

    # check news posts
    accountDir = base_dir + '/accounts/news' + '@' + domain + '/'
    postFilename = accountDir + 'outbox/' + postUrl
    if os.path.isfile(postFilename):
        return postFilename

    # is it in the announce cache?
    postFilename = base_dir + '/cache/announce/' + nickname + '/' + postUrl
    if os.path.isfile(postFilename):
        return postFilename

    # print('WARN: unable to locate ' + nickname + ' ' + postUrl)
    return None


def _getPublishedDate(post_json_object: {}) -> str:
    """Returns the published date on the given post
    """
    published = None
    if post_json_object.get('published'):
        published = post_json_object['published']
    elif has_object_dict(post_json_object):
        if post_json_object['object'].get('published'):
            published = post_json_object['object']['published']
    if not published:
        return None
    if not isinstance(published, str):
        return None
    return published


def getReplyIntervalHours(base_dir: str, nickname: str, domain: str,
                          default_reply_interval_hrs: int) -> int:
    """Returns the reply interval for the given account.
    The reply interval is the number of hours after a post being made
    during which replies are allowed
    """
    replyIntervalFilename = \
        acct_dir(base_dir, nickname, domain) + '/.replyIntervalHours'
    if os.path.isfile(replyIntervalFilename):
        with open(replyIntervalFilename, 'r') as fp:
            hoursStr = fp.read()
            if hoursStr.isdigit():
                return int(hoursStr)
    return default_reply_interval_hrs


def setReplyIntervalHours(base_dir: str, nickname: str, domain: str,
                          replyIntervalHours: int) -> bool:
    """Sets the reply interval for the given account.
    The reply interval is the number of hours after a post being made
    during which replies are allowed
    """
    replyIntervalFilename = \
        acct_dir(base_dir, nickname, domain) + '/.replyIntervalHours'
    with open(replyIntervalFilename, 'w+') as fp:
        try:
            fp.write(str(replyIntervalHours))
            return True
        except BaseException:
            print('EX: setReplyIntervalHours unable to save reply interval ' +
                  str(replyIntervalFilename) + ' ' +
                  str(replyIntervalHours))
            pass
    return False


def canReplyTo(base_dir: str, nickname: str, domain: str,
               postUrl: str, replyIntervalHours: int,
               currDateStr: str = None,
               post_json_object: {} = None) -> bool:
    """Is replying to the given post permitted?
    This is a spam mitigation feature, so that spammers can't
    add a lot of replies to old post which you don't notice.
    """
    if '/statuses/' not in postUrl:
        return True
    if not post_json_object:
        postFilename = locatePost(base_dir, nickname, domain, postUrl)
        if not postFilename:
            return False
        post_json_object = loadJson(postFilename)
    if not post_json_object:
        return False
    published = _getPublishedDate(post_json_object)
    if not published:
        return False
    try:
        pubDate = datetime.datetime.strptime(published, '%Y-%m-%dT%H:%M:%SZ')
    except BaseException:
        print('EX: canReplyTo unrecognized published date ' + str(published))
        return False
    if not currDateStr:
        currDate = datetime.datetime.utcnow()
    else:
        try:
            currDate = datetime.datetime.strptime(currDateStr,
                                                  '%Y-%m-%dT%H:%M:%SZ')
        except BaseException:
            print('EX: canReplyTo unrecognized current date ' +
                  str(currDateStr))
            return False
    hoursSincePublication = int((currDate - pubDate).total_seconds() / 3600)
    if hoursSincePublication < 0 or \
       hoursSincePublication >= replyIntervalHours:
        return False
    return True


def _removeAttachment(base_dir: str, http_prefix: str, domain: str,
                      postJson: {}):
    if not postJson.get('attachment'):
        return
    if not postJson['attachment'][0].get('url'):
        return
    attachmentUrl = postJson['attachment'][0]['url']
    if not attachmentUrl:
        return
    mediaFilename = base_dir + '/' + \
        attachmentUrl.replace(http_prefix + '://' + domain + '/', '')
    if os.path.isfile(mediaFilename):
        try:
            os.remove(mediaFilename)
        except OSError:
            print('EX: _removeAttachment unable to delete media file ' +
                  str(mediaFilename))
    etagFilename = mediaFilename + '.etag'
    if os.path.isfile(etagFilename):
        try:
            os.remove(etagFilename)
        except OSError:
            print('EX: _removeAttachment unable to delete etag file ' +
                  str(etagFilename))
    postJson['attachment'] = []


def removeModerationPostFromIndex(base_dir: str, postUrl: str,
                                  debug: bool) -> None:
    """Removes a url from the moderation index
    """
    moderationIndexFile = base_dir + '/accounts/moderation.txt'
    if not os.path.isfile(moderationIndexFile):
        return
    postId = removeIdEnding(postUrl)
    if postId in open(moderationIndexFile).read():
        with open(moderationIndexFile, 'r') as f:
            lines = f.readlines()
            with open(moderationIndexFile, 'w+') as f:
                for line in lines:
                    if line.strip("\n").strip("\r") != postId:
                        f.write(line)
                    else:
                        if debug:
                            print('DEBUG: removed ' + postId +
                                  ' from moderation index')


def _isReplyToBlogPost(base_dir: str, nickname: str, domain: str,
                       post_json_object: str):
    """Is the given post a reply to a blog post?
    """
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('inReplyTo'):
        return False
    if not isinstance(post_json_object['object']['inReplyTo'], str):
        return False
    blogsIndexFilename = \
        acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogsIndexFilename):
        return False
    postId = removeIdEnding(post_json_object['object']['inReplyTo'])
    postId = postId.replace('/', '#')
    if postId in open(blogsIndexFilename).read():
        return True
    return False


def _deletePostRemoveReplies(base_dir: str, nickname: str, domain: str,
                             http_prefix: str, postFilename: str,
                             recentPostsCache: {}, debug: bool) -> None:
    """Removes replies when deleting a post
    """
    repliesFilename = postFilename.replace('.json', '.replies')
    if not os.path.isfile(repliesFilename):
        return
    if debug:
        print('DEBUG: removing replies to ' + postFilename)
    with open(repliesFilename, 'r') as f:
        for replyId in f:
            replyFile = locatePost(base_dir, nickname, domain, replyId)
            if not replyFile:
                continue
            if os.path.isfile(replyFile):
                deletePost(base_dir, http_prefix,
                           nickname, domain, replyFile, debug,
                           recentPostsCache)
    # remove the replies file
    try:
        os.remove(repliesFilename)
    except OSError:
        print('EX: _deletePostRemoveReplies unable to delete replies file ' +
              str(repliesFilename))


def _isBookmarked(base_dir: str, nickname: str, domain: str,
                  postFilename: str) -> bool:
    """Returns True if the given post is bookmarked
    """
    bookmarksIndexFilename = \
        acct_dir(base_dir, nickname, domain) + '/bookmarks.index'
    if os.path.isfile(bookmarksIndexFilename):
        bookmarkIndex = postFilename.split('/')[-1] + '\n'
        if bookmarkIndex in open(bookmarksIndexFilename).read():
            return True
    return False


def removePostFromCache(post_json_object: {}, recentPostsCache: {}) -> None:
    """ if the post exists in the recent posts cache then remove it
    """
    if not recentPostsCache:
        return

    if not post_json_object.get('id'):
        return

    if not recentPostsCache.get('index'):
        return

    postId = post_json_object['id']
    if '#' in postId:
        postId = postId.split('#', 1)[0]
    postId = removeIdEnding(postId).replace('/', '#')
    if postId not in recentPostsCache['index']:
        return

    if recentPostsCache.get('index'):
        if postId in recentPostsCache['index']:
            recentPostsCache['index'].remove(postId)

    if recentPostsCache.get('json'):
        if recentPostsCache['json'].get(postId):
            del recentPostsCache['json'][postId]

    if recentPostsCache.get('html'):
        if recentPostsCache['html'].get(postId):
            del recentPostsCache['html'][postId]


def _deleteCachedHtml(base_dir: str, nickname: str, domain: str,
                      post_json_object: {}):
    """Removes cached html file for the given post
    """
    cachedPostFilename = \
        getCachedPostFilename(base_dir, nickname, domain, post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                print('EX: _deleteCachedHtml ' +
                      'unable to delete cached post file ' +
                      str(cachedPostFilename))


def _deleteHashtagsOnPost(base_dir: str, post_json_object: {}) -> None:
    """Removes hashtags when a post is deleted
    """
    removeHashtagIndex = False
    if has_object_dict(post_json_object):
        if post_json_object['object'].get('content'):
            if '#' in post_json_object['object']['content']:
                removeHashtagIndex = True

    if not removeHashtagIndex:
        return

    if not post_json_object['object'].get('id') or \
       not post_json_object['object'].get('tag'):
        return

    # get the id of the post
    postId = removeIdEnding(post_json_object['object']['id'])
    for tag in post_json_object['object']['tag']:
        if not tag.get('type'):
            continue
        if tag['type'] != 'Hashtag':
            continue
        if not tag.get('name'):
            continue
        # find the index file for this tag
        tagIndexFilename = base_dir + '/tags/' + tag['name'][1:] + '.txt'
        if not os.path.isfile(tagIndexFilename):
            continue
        # remove postId from the tag index file
        lines = None
        with open(tagIndexFilename, 'r') as f:
            lines = f.readlines()
        if not lines:
            continue
        newlines = ''
        for fileLine in lines:
            if postId in fileLine:
                # skip over the deleted post
                continue
            newlines += fileLine
        if not newlines.strip():
            # if there are no lines then remove the hashtag file
            try:
                os.remove(tagIndexFilename)
            except OSError:
                print('EX: _deleteHashtagsOnPost unable to delete tag index ' +
                      str(tagIndexFilename))
        else:
            # write the new hashtag index without the given post in it
            with open(tagIndexFilename, 'w+') as f:
                f.write(newlines)


def _deleteConversationPost(base_dir: str, nickname: str, domain: str,
                            post_json_object: {}) -> None:
    """Deletes a post from a conversation
    """
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('conversation'):
        return False
    if not post_json_object['object'].get('id'):
        return False
    conversationDir = acct_dir(base_dir, nickname, domain) + '/conversation'
    conversationId = post_json_object['object']['conversation']
    conversationId = conversationId.replace('/', '#')
    postId = post_json_object['object']['id']
    conversationFilename = conversationDir + '/' + conversationId
    if not os.path.isfile(conversationFilename):
        return False
    conversationStr = ''
    with open(conversationFilename, 'r') as fp:
        conversationStr = fp.read()
    if postId + '\n' not in conversationStr:
        return False
    conversationStr = conversationStr.replace(postId + '\n', '')
    if conversationStr:
        with open(conversationFilename, 'w+') as fp:
            fp.write(conversationStr)
    else:
        if os.path.isfile(conversationFilename + '.muted'):
            try:
                os.remove(conversationFilename + '.muted')
            except OSError:
                print('EX: _deleteConversationPost ' +
                      'unable to remove conversation ' +
                      str(conversationFilename) + '.muted')
        try:
            os.remove(conversationFilename)
        except OSError:
            print('EX: _deleteConversationPost ' +
                  'unable to remove conversation ' +
                  str(conversationFilename))


def deletePost(base_dir: str, http_prefix: str,
               nickname: str, domain: str, postFilename: str,
               debug: bool, recentPostsCache: {}) -> None:
    """Recursively deletes a post and its replies and attachments
    """
    post_json_object = loadJson(postFilename, 1)
    if not post_json_object:
        # remove any replies
        _deletePostRemoveReplies(base_dir, nickname, domain,
                                 http_prefix, postFilename,
                                 recentPostsCache, debug)
        # finally, remove the post itself
        try:
            os.remove(postFilename)
        except OSError:
            if debug:
                print('EX: deletePost unable to delete post ' +
                      str(postFilename))
        return

    # don't allow deletion of bookmarked posts
    if _isBookmarked(base_dir, nickname, domain, postFilename):
        return

    # don't remove replies to blog posts
    if _isReplyToBlogPost(base_dir, nickname, domain,
                          post_json_object):
        return

    # remove from recent posts cache in memory
    removePostFromCache(post_json_object, recentPostsCache)

    # remove from conversation index
    _deleteConversationPost(base_dir, nickname, domain, post_json_object)

    # remove any attachment
    _removeAttachment(base_dir, http_prefix, domain, post_json_object)

    extensions = ('votes', 'arrived', 'muted', 'tts', 'reject')
    for ext in extensions:
        extFilename = postFilename + '.' + ext
        if os.path.isfile(extFilename):
            try:
                os.remove(extFilename)
            except OSError:
                print('EX: deletePost unable to remove ext ' +
                      str(extFilename))

    # remove cached html version of the post
    _deleteCachedHtml(base_dir, nickname, domain, post_json_object)

    hasObject = False
    if post_json_object.get('object'):
        hasObject = True

    # remove from moderation index file
    if hasObject:
        if has_object_dict(post_json_object):
            if post_json_object['object'].get('moderationStatus'):
                if post_json_object.get('id'):
                    postId = removeIdEnding(post_json_object['id'])
                    removeModerationPostFromIndex(base_dir, postId, debug)

    # remove any hashtags index entries
    if hasObject:
        _deleteHashtagsOnPost(base_dir, post_json_object)

    # remove any replies
    _deletePostRemoveReplies(base_dir, nickname, domain,
                             http_prefix, postFilename,
                             recentPostsCache, debug)
    # finally, remove the post itself
    try:
        os.remove(postFilename)
    except OSError:
        if debug:
            print('EX: deletePost unable to delete post ' + str(postFilename))


def isValidLanguage(text: str) -> bool:
    """Returns true if the given text contains a valid
    natural language string
    """
    naturalLanguages = {
        "Latin": [65, 866],
        "Cyrillic": [1024, 1274],
        "Greek": [880, 1280],
        "isArmenian": [1328, 1424],
        "isHebrew": [1424, 1536],
        "Arabic": [1536, 1792],
        "Syriac": [1792, 1872],
        "Thaan": [1920, 1984],
        "Devanagari": [2304, 2432],
        "Bengali": [2432, 2560],
        "Gurmukhi": [2560, 2688],
        "Gujarati": [2688, 2816],
        "Oriya": [2816, 2944],
        "Tamil": [2944, 3072],
        "Telugu": [3072, 3200],
        "Kannada": [3200, 3328],
        "Malayalam": [3328, 3456],
        "Sinhala": [3456, 3584],
        "Thai": [3584, 3712],
        "Lao": [3712, 3840],
        "Tibetan": [3840, 4096],
        "Myanmar": [4096, 4256],
        "Georgian": [4256, 4352],
        "HangulJamo": [4352, 4608],
        "Cherokee": [5024, 5120],
        "UCAS": [5120, 5760],
        "Ogham": [5760, 5792],
        "Runic": [5792, 5888],
        "Khmer": [6016, 6144],
        "Mongolian": [6144, 6320]
    }
    for langName, langRange in naturalLanguages.items():
        okLang = True
        for ch in text:
            if ch.isdigit():
                continue
            if ord(ch) not in range(langRange[0], langRange[1]):
                okLang = False
                break
        if okLang:
            return True
    return False


def _getReservedWords() -> str:
    return ('inbox', 'dm', 'outbox', 'following',
            'public', 'followers', 'category',
            'channel', 'calendar', 'video-channels',
            'tlreplies', 'tlmedia', 'tlblogs',
            'tlblogs', 'tlfeatures',
            'moderation', 'moderationaction',
            'activity', 'undo', 'pinned',
            'actor', 'Actor',
            'reply', 'replies', 'question', 'like',
            'likes', 'users', 'statuses', 'tags',
            'accounts', 'headers',
            'channels', 'profile', 'u', 'c',
            'updates', 'repeat', 'announce',
            'shares', 'fonts', 'icons', 'avatars',
            'welcome', 'helpimages',
            'bookmark', 'bookmarks', 'tlbookmarks',
            'ignores', 'linksmobile', 'newswiremobile',
            'minimal', 'search', 'eventdelete',
            'searchemoji', 'catalog', 'conversationId',
            'mention', 'http', 'https',
            'ontologies', 'data')


def getNicknameValidationPattern() -> str:
    """Returns a html text input validation pattern for nickname
    """
    reservedNames = _getReservedWords()
    pattern = ''
    for word in reservedNames:
        if pattern:
            pattern += '(?!.*\\b' + word + '\\b)'
        else:
            pattern = '^(?!.*\\b' + word + '\\b)'
    return pattern + '.*${1,30}'


def _isReservedName(nickname: str) -> bool:
    """Is the given nickname reserved for some special function?
    """
    reservedNames = _getReservedWords()
    if nickname in reservedNames:
        return True
    return False


def validNickname(domain: str, nickname: str) -> bool:
    """Is the given nickname valid?
    """
    if len(nickname) == 0:
        return False
    if len(nickname) > 30:
        return False
    if not isValidLanguage(nickname):
        return False
    forbiddenChars = ('.', ' ', '/', '?', ':', ';', '@', '#', '!')
    for c in forbiddenChars:
        if c in nickname:
            return False
    # this should only apply for the shared inbox
    if nickname == domain:
        return False
    if _isReservedName(nickname):
        return False
    return True


def noOfAccounts(base_dir: str) -> bool:
    """Returns the number of accounts on the system
    """
    accountCtr = 0
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for account in dirs:
            if isAccountDir(account):
                accountCtr += 1
        break
    return accountCtr


def noOfActiveAccountsMonthly(base_dir: str, months: int) -> bool:
    """Returns the number of accounts on the system this month
    """
    accountCtr = 0
    currTime = int(time.time())
    monthSeconds = int(60*60*24*30*months)
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for account in dirs:
            if not isAccountDir(account):
                continue
            lastUsedFilename = \
                base_dir + '/accounts/' + account + '/.lastUsed'
            if not os.path.isfile(lastUsedFilename):
                continue
            with open(lastUsedFilename, 'r') as lastUsedFile:
                lastUsed = lastUsedFile.read()
                if lastUsed.isdigit():
                    timeDiff = (currTime - int(lastUsed))
                    if timeDiff < monthSeconds:
                        accountCtr += 1
        break
    return accountCtr


def isPublicPostFromUrl(base_dir: str, nickname: str, domain: str,
                        postUrl: str) -> bool:
    """Returns whether the given url is a public post
    """
    postFilename = locatePost(base_dir, nickname, domain, postUrl)
    if not postFilename:
        return False
    post_json_object = loadJson(postFilename, 1)
    if not post_json_object:
        return False
    return isPublicPost(post_json_object)


def isPublicPost(post_json_object: {}) -> bool:
    """Returns true if the given post is public
    """
    if not post_json_object.get('type'):
        return False
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('to'):
        return False
    for recipient in post_json_object['object']['to']:
        if recipient.endswith('#Public'):
            return True
    return False


def copytree(src: str, dst: str, symlinks: str = False, ignore: bool = None):
    """Copy a directory
    """
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def getCachedPostDirectory(base_dir: str, nickname: str, domain: str) -> str:
    """Returns the directory where the html post cache exists
    """
    htmlPostCacheDir = acct_dir(base_dir, nickname, domain) + '/postcache'
    return htmlPostCacheDir


def getCachedPostFilename(base_dir: str, nickname: str, domain: str,
                          post_json_object: {}) -> str:
    """Returns the html cache filename for the given post
    """
    cachedPostDir = getCachedPostDirectory(base_dir, nickname, domain)
    if not os.path.isdir(cachedPostDir):
        # print('ERROR: invalid html cache directory ' + cachedPostDir)
        return None
    if '@' not in cachedPostDir:
        # print('ERROR: invalid html cache directory ' + cachedPostDir)
        return None
    cachedPostId = removeIdEnding(post_json_object['id'])
    cachedPostFilename = cachedPostDir + '/' + cachedPostId.replace('/', '#')
    return cachedPostFilename + '.html'


def updateRecentPostsCache(recentPostsCache: {}, max_recent_posts: int,
                           post_json_object: {}, htmlStr: str) -> None:
    """Store recent posts in memory so that they can be quickly recalled
    """
    if not post_json_object.get('id'):
        return
    postId = post_json_object['id']
    if '#' in postId:
        postId = postId.split('#', 1)[0]
    postId = removeIdEnding(postId).replace('/', '#')
    if recentPostsCache.get('index'):
        if postId in recentPostsCache['index']:
            return
        recentPostsCache['index'].append(postId)
        post_json_object['muted'] = False
        recentPostsCache['json'][postId] = json.dumps(post_json_object)
        recentPostsCache['html'][postId] = htmlStr

        while len(recentPostsCache['html'].items()) > max_recent_posts:
            postId = recentPostsCache['index'][0]
            recentPostsCache['index'].pop(0)
            if recentPostsCache['json'].get(postId):
                del recentPostsCache['json'][postId]
            if recentPostsCache['html'].get(postId):
                del recentPostsCache['html'][postId]
    else:
        recentPostsCache['index'] = [postId]
        recentPostsCache['json'] = {}
        recentPostsCache['html'] = {}
        recentPostsCache['json'][postId] = json.dumps(post_json_object)
        recentPostsCache['html'][postId] = htmlStr


def fileLastModified(filename: str) -> str:
    """Returns the date when a file was last modified
    """
    t = os.path.getmtime(filename)
    modifiedTime = datetime.datetime.fromtimestamp(t)
    return modifiedTime.strftime("%Y-%m-%dT%H:%M:%SZ")


def getCSS(base_dir: str, cssFilename: str, cssCache: {}) -> str:
    """Retrieves the css for a given file, or from a cache
    """
    # does the css file exist?
    if not os.path.isfile(cssFilename):
        return None

    lastModified = fileLastModified(cssFilename)

    # has this already been loaded into the cache?
    if cssCache.get(cssFilename):
        if cssCache[cssFilename][0] == lastModified:
            # file hasn't changed, so return the version in the cache
            return cssCache[cssFilename][1]

    with open(cssFilename, 'r') as fpCSS:
        css = fpCSS.read()
        if cssCache.get(cssFilename):
            # alter the cache contents
            cssCache[cssFilename][0] = lastModified
            cssCache[cssFilename][1] = css
        else:
            # add entry to the cache
            cssCache[cssFilename] = [lastModified, css]
        return css

    return None


def isBlogPost(post_json_object: {}) -> bool:
    """Is the given post a blog post?
    """
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if not hasObjectStringType(post_json_object, False):
        return False
    if not post_json_object['object'].get('content'):
        return False
    if post_json_object['object']['type'] != 'Article':
        return False
    return True


def isNewsPost(post_json_object: {}) -> bool:
    """Is the given post a blog post?
    """
    return post_json_object.get('news')


def _searchVirtualBoxPosts(base_dir: str, nickname: str, domain: str,
                           searchStr: str, maxResults: int,
                           boxName: str) -> []:
    """Searches through a virtual box, which is typically an index on the inbox
    """
    indexFilename = \
        acct_dir(base_dir, nickname, domain) + '/' + boxName + '.index'
    if boxName == 'bookmarks':
        boxName = 'inbox'
    path = acct_dir(base_dir, nickname, domain) + '/' + boxName
    if not os.path.isdir(path):
        return []

    searchStr = searchStr.lower().strip()

    if '+' in searchStr:
        searchWords = searchStr.split('+')
        for index in range(len(searchWords)):
            searchWords[index] = searchWords[index].strip()
        print('SEARCH: ' + str(searchWords))
    else:
        searchWords = [searchStr]

    res = []
    with open(indexFilename, 'r') as indexFile:
        postFilename = 'start'
        while postFilename:
            postFilename = indexFile.readline()
            if not postFilename:
                break
            if '.json' not in postFilename:
                break
            postFilename = path + '/' + postFilename.strip()
            if not os.path.isfile(postFilename):
                continue
            with open(postFilename, 'r') as postFile:
                data = postFile.read().lower()

                notFound = False
                for keyword in searchWords:
                    if keyword not in data:
                        notFound = True
                        break
                if notFound:
                    continue

                res.append(postFilename)
                if len(res) >= maxResults:
                    return res
    return res


def searchBoxPosts(base_dir: str, nickname: str, domain: str,
                   searchStr: str, maxResults: int,
                   boxName='outbox') -> []:
    """Search your posts and return a list of the filenames
    containing matching strings
    """
    path = acct_dir(base_dir, nickname, domain) + '/' + boxName
    # is this a virtual box, such as direct messages?
    if not os.path.isdir(path):
        if os.path.isfile(path + '.index'):
            return _searchVirtualBoxPosts(base_dir, nickname, domain,
                                          searchStr, maxResults, boxName)
        return []
    searchStr = searchStr.lower().strip()

    if '+' in searchStr:
        searchWords = searchStr.split('+')
        for index in range(len(searchWords)):
            searchWords[index] = searchWords[index].strip()
        print('SEARCH: ' + str(searchWords))
    else:
        searchWords = [searchStr]

    res = []
    for root, dirs, fnames in os.walk(path):
        for fname in fnames:
            filePath = os.path.join(root, fname)
            with open(filePath, 'r') as postFile:
                data = postFile.read().lower()

                notFound = False
                for keyword in searchWords:
                    if keyword not in data:
                        notFound = True
                        break
                if notFound:
                    continue

                res.append(filePath)
                if len(res) >= maxResults:
                    return res
        break
    return res


def getFileCaseInsensitive(path: str) -> str:
    """Returns a case specific filename given a case insensitive version of it
    """
    if os.path.isfile(path):
        return path
    if path != path.lower():
        if os.path.isfile(path.lower()):
            return path.lower()
    return None


def undoLikesCollectionEntry(recentPostsCache: {},
                             base_dir: str, postFilename: str, objectUrl: str,
                             actor: str, domain: str, debug: bool,
                             post_json_object: {}) -> None:
    """Undoes a like for a particular actor
    """
    if not post_json_object:
        post_json_object = loadJson(postFilename)
    if not post_json_object:
        return
    # remove any cached version of this post so that the
    # like icon is changed
    nickname = getNicknameFromActor(actor)
    cachedPostFilename = getCachedPostFilename(base_dir, nickname,
                                               domain, post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                print('EX: undoLikesCollectionEntry ' +
                      'unable to delete cached post ' +
                      str(cachedPostFilename))
    removePostFromCache(post_json_object, recentPostsCache)

    if not post_json_object.get('type'):
        return
    if post_json_object['type'] != 'Create':
        return
    obj = post_json_object
    if has_object_dict(post_json_object):
        obj = post_json_object['object']
    if not obj.get('likes'):
        return
    if not isinstance(obj['likes'], dict):
        return
    if not obj['likes'].get('items'):
        return
    totalItems = 0
    if obj['likes'].get('totalItems'):
        totalItems = obj['likes']['totalItems']
    itemFound = False
    for likeItem in obj['likes']['items']:
        if likeItem.get('actor'):
            if likeItem['actor'] == actor:
                if debug:
                    print('DEBUG: like was removed for ' + actor)
                obj['likes']['items'].remove(likeItem)
                itemFound = True
                break
    if not itemFound:
        return
    if totalItems == 1:
        if debug:
            print('DEBUG: likes was removed from post')
        del obj['likes']
    else:
        itlen = len(obj['likes']['items'])
        obj['likes']['totalItems'] = itlen

    saveJson(post_json_object, postFilename)


def undoReactionCollectionEntry(recentPostsCache: {},
                                base_dir: str, postFilename: str,
                                objectUrl: str,
                                actor: str, domain: str, debug: bool,
                                post_json_object: {},
                                emojiContent: str) -> None:
    """Undoes an emoji reaction for a particular actor
    """
    if not post_json_object:
        post_json_object = loadJson(postFilename)
    if not post_json_object:
        return
    # remove any cached version of this post so that the
    # like icon is changed
    nickname = getNicknameFromActor(actor)
    cachedPostFilename = getCachedPostFilename(base_dir, nickname,
                                               domain, post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                print('EX: undoReactionCollectionEntry ' +
                      'unable to delete cached post ' +
                      str(cachedPostFilename))
    removePostFromCache(post_json_object, recentPostsCache)

    if not post_json_object.get('type'):
        return
    if post_json_object['type'] != 'Create':
        return
    obj = post_json_object
    if has_object_dict(post_json_object):
        obj = post_json_object['object']
    if not obj.get('reactions'):
        return
    if not isinstance(obj['reactions'], dict):
        return
    if not obj['reactions'].get('items'):
        return
    totalItems = 0
    if obj['reactions'].get('totalItems'):
        totalItems = obj['reactions']['totalItems']
    itemFound = False
    for likeItem in obj['reactions']['items']:
        if likeItem.get('actor'):
            if likeItem['actor'] == actor and \
               likeItem['content'] == emojiContent:
                if debug:
                    print('DEBUG: emoji reaction was removed for ' + actor)
                obj['reactions']['items'].remove(likeItem)
                itemFound = True
                break
    if not itemFound:
        return
    if totalItems == 1:
        if debug:
            print('DEBUG: emoji reaction was removed from post')
        del obj['reactions']
    else:
        itlen = len(obj['reactions']['items'])
        obj['reactions']['totalItems'] = itlen

    saveJson(post_json_object, postFilename)


def undoAnnounceCollectionEntry(recentPostsCache: {},
                                base_dir: str, postFilename: str,
                                actor: str, domain: str, debug: bool) -> None:
    """Undoes an announce for a particular actor by removing it from
    the "shares" collection within a post. Note that the "shares"
    collection has no relation to shared items in shares.py. It's
    shares of posts, not shares of physical objects.
    """
    post_json_object = loadJson(postFilename)
    if not post_json_object:
        return
    # remove any cached version of this announce so that the announce
    # icon is changed
    nickname = getNicknameFromActor(actor)
    cachedPostFilename = getCachedPostFilename(base_dir, nickname, domain,
                                               post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                if debug:
                    print('EX: undoAnnounceCollectionEntry ' +
                          'unable to delete cached post ' +
                          str(cachedPostFilename))
    removePostFromCache(post_json_object, recentPostsCache)

    if not post_json_object.get('type'):
        return
    if post_json_object['type'] != 'Create':
        return
    if not has_object_dict(post_json_object):
        if debug:
            pprint(post_json_object)
            print('DEBUG: post has no object')
        return
    if not post_json_object['object'].get('shares'):
        return
    if not post_json_object['object']['shares'].get('items'):
        return
    totalItems = 0
    if post_json_object['object']['shares'].get('totalItems'):
        totalItems = post_json_object['object']['shares']['totalItems']
    itemFound = False
    for announceItem in post_json_object['object']['shares']['items']:
        if announceItem.get('actor'):
            if announceItem['actor'] == actor:
                if debug:
                    print('DEBUG: Announce was removed for ' + actor)
                anIt = announceItem
                post_json_object['object']['shares']['items'].remove(anIt)
                itemFound = True
                break
    if not itemFound:
        return
    if totalItems == 1:
        if debug:
            print('DEBUG: shares (announcements) ' +
                  'was removed from post')
        del post_json_object['object']['shares']
    else:
        itlen = len(post_json_object['object']['shares']['items'])
        post_json_object['object']['shares']['totalItems'] = itlen

    saveJson(post_json_object, postFilename)


def updateAnnounceCollection(recentPostsCache: {},
                             base_dir: str, postFilename: str,
                             actor: str,
                             nickname: str, domain: str, debug: bool) -> None:
    """Updates the announcements collection within a post
    Confusingly this is known as "shares", but isn't the
    same as shared items within shares.py
    It's shares of posts, not shares of physical objects.
    """
    post_json_object = loadJson(postFilename)
    if not post_json_object:
        return
    # remove any cached version of this announce so that the announce
    # icon is changed
    cachedPostFilename = getCachedPostFilename(base_dir, nickname, domain,
                                               post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                if debug:
                    print('EX: updateAnnounceCollection ' +
                          'unable to delete cached post ' +
                          str(cachedPostFilename))
    removePostFromCache(post_json_object, recentPostsCache)

    if not has_object_dict(post_json_object):
        if debug:
            pprint(post_json_object)
            print('DEBUG: post ' + postFilename + ' has no object')
        return
    postUrl = removeIdEnding(post_json_object['id']) + '/shares'
    if not post_json_object['object'].get('shares'):
        if debug:
            print('DEBUG: Adding initial shares (announcements) to ' +
                  postUrl)
        announcementsJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'id': postUrl,
            'type': 'Collection',
            "totalItems": 1,
            'items': [{
                'type': 'Announce',
                'actor': actor
            }]
        }
        post_json_object['object']['shares'] = announcementsJson
    else:
        if post_json_object['object']['shares'].get('items'):
            sharesItems = post_json_object['object']['shares']['items']
            for announceItem in sharesItems:
                if announceItem.get('actor'):
                    if announceItem['actor'] == actor:
                        return
            newAnnounce = {
                'type': 'Announce',
                'actor': actor
            }
            post_json_object['object']['shares']['items'].append(newAnnounce)
            itlen = len(post_json_object['object']['shares']['items'])
            post_json_object['object']['shares']['totalItems'] = itlen
        else:
            if debug:
                print('DEBUG: shares (announcements) section of post ' +
                      'has no items list')

    if debug:
        print('DEBUG: saving post with shares (announcements) added')
        pprint(post_json_object)
    saveJson(post_json_object, postFilename)


def weekDayOfMonthStart(monthNumber: int, year: int) -> int:
    """Gets the day number of the first day of the month
    1=sun, 7=sat
    """
    firstDayOfMonth = datetime.datetime(year, monthNumber, 1, 0, 0)
    return int(firstDayOfMonth.strftime("%w")) + 1


def mediaFileMimeType(filename: str) -> str:
    """Given a media filename return its mime type
    """
    if '.' not in filename:
        return 'image/png'
    extensions = {
        'json': 'application/json',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        'avif': 'image/avif',
        'ico': 'image/x-icon',
        'mp3': 'audio/mpeg',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'mp4': 'video/mp4',
        'ogv': 'video/ogv'
    }
    fileExt = filename.split('.')[-1]
    if not extensions.get(fileExt):
        return 'image/png'
    return extensions[fileExt]


def isRecentPost(post_json_object: {}, maxDays: int) -> bool:
    """ Is the given post recent?
    """
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('published'):
        return False
    if not isinstance(post_json_object['object']['published'], str):
        return False
    currTime = datetime.datetime.utcnow()
    daysSinceEpoch = (currTime - datetime.datetime(1970, 1, 1)).days
    recently = daysSinceEpoch - maxDays

    publishedDateStr = post_json_object['object']['published']
    try:
        publishedDate = \
            datetime.datetime.strptime(publishedDateStr,
                                       "%Y-%m-%dT%H:%M:%SZ")
    except BaseException:
        print('EX: isRecentPost unrecognized published date ' +
              str(publishedDateStr))
        return False

    publishedDaysSinceEpoch = \
        (publishedDate - datetime.datetime(1970, 1, 1)).days
    if publishedDaysSinceEpoch < recently:
        return False
    return True


def camelCaseSplit(text: str) -> str:
    """ Splits CamelCase into "Camel Case"
    """
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|' +
                          '(?<=[A-Z])(?=[A-Z][a-z])|$)', text)
    if not matches:
        return text
    resultStr = ''
    for word in matches:
        resultStr += word.group(0) + ' '
    return resultStr.strip()


def rejectPostId(base_dir: str, nickname: str, domain: str,
                 postId: str, recentPostsCache: {}) -> None:
    """ Marks the given post as rejected,
    for example an announce which is too old
    """
    postFilename = locatePost(base_dir, nickname, domain, postId)
    if not postFilename:
        return

    if recentPostsCache.get('index'):
        # if this is a full path then remove the directories
        indexFilename = postFilename
        if '/' in postFilename:
            indexFilename = postFilename.split('/')[-1]

        # filename of the post without any extension or path
        # This should also correspond to any index entry in
        # the posts cache
        postUrl = \
            indexFilename.replace('\n', '').replace('\r', '')
        postUrl = postUrl.replace('.json', '').strip()

        if postUrl in recentPostsCache['index']:
            if recentPostsCache['json'].get(postUrl):
                del recentPostsCache['json'][postUrl]
            if recentPostsCache['html'].get(postUrl):
                del recentPostsCache['html'][postUrl]

    with open(postFilename + '.reject', 'w+') as rejectFile:
        rejectFile.write('\n')


def isDM(post_json_object: {}) -> bool:
    """Returns true if the given post is a DM
    """
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if post_json_object['object']['type'] != 'Note' and \
       post_json_object['object']['type'] != 'Page' and \
       post_json_object['object']['type'] != 'Patch' and \
       post_json_object['object']['type'] != 'EncryptedMessage' and \
       post_json_object['object']['type'] != 'Article':
        return False
    if post_json_object['object'].get('moderationStatus'):
        return False
    fields = ('to', 'cc')
    for f in fields:
        if not post_json_object['object'].get(f):
            continue
        for toAddress in post_json_object['object'][f]:
            if toAddress.endswith('#Public'):
                return False
            if toAddress.endswith('followers'):
                return False
    return True


def isReply(post_json_object: {}, actor: str) -> bool:
    """Returns true if the given post is a reply to the given actor
    """
    if post_json_object['type'] != 'Create':
        return False
    if not has_object_dict(post_json_object):
        return False
    if post_json_object['object'].get('moderationStatus'):
        return False
    if post_json_object['object']['type'] != 'Note' and \
       post_json_object['object']['type'] != 'Page' and \
       post_json_object['object']['type'] != 'EncryptedMessage' and \
       post_json_object['object']['type'] != 'Article':
        return False
    if post_json_object['object'].get('inReplyTo'):
        if isinstance(post_json_object['object']['inReplyTo'], str):
            if post_json_object['object']['inReplyTo'].startswith(actor):
                return True
    if not post_json_object['object'].get('tag'):
        return False
    if not isinstance(post_json_object['object']['tag'], list):
        return False
    for tag in post_json_object['object']['tag']:
        if not tag.get('type'):
            continue
        if tag['type'] == 'Mention':
            if not tag.get('href'):
                continue
            if actor in tag['href']:
                return True
    return False


def containsPGPPublicKey(content: str) -> bool:
    """Returns true if the given content contains a PGP public key
    """
    if '--BEGIN PGP PUBLIC KEY BLOCK--' in content:
        if '--END PGP PUBLIC KEY BLOCK--' in content:
            return True
    return False


def isPGPEncrypted(content: str) -> bool:
    """Returns true if the given content is PGP encrypted
    """
    if '--BEGIN PGP MESSAGE--' in content:
        if '--END PGP MESSAGE--' in content:
            return True
    return False


def invalidCiphertext(content: str) -> bool:
    """Returns true if the given content contains an invalid key
    """
    if '----BEGIN ' in content or '----END ' in content:
        if not containsPGPPublicKey(content) and \
           not isPGPEncrypted(content):
            return True
    return False


def loadTranslationsFromFile(base_dir: str, language: str) -> ({}, str):
    """Returns the translations dictionary
    """
    if not os.path.isdir(base_dir + '/translations'):
        print('ERROR: translations directory not found')
        return None, None
    if not language:
        system_language = locale.getdefaultlocale()[0]
    else:
        system_language = language
    if not system_language:
        system_language = 'en'
    if '_' in system_language:
        system_language = system_language.split('_')[0]
    while '/' in system_language:
        system_language = system_language.split('/')[1]
    if '.' in system_language:
        system_language = system_language.split('.')[0]
    translationsFile = base_dir + '/translations/' + \
        system_language + '.json'
    if not os.path.isfile(translationsFile):
        system_language = 'en'
        translationsFile = base_dir + '/translations/' + \
            system_language + '.json'
    return loadJson(translationsFile), system_language


def dmAllowedFromDomain(base_dir: str,
                        nickname: str, domain: str,
                        sendingActorDomain: str) -> bool:
    """When a DM is received and the .followDMs flag file exists
    Then optionally some domains can be specified as allowed,
    regardless of individual follows.
    i.e. Mostly you only want DMs from followers, but there are
    a few particular instances that you trust
    """
    dmAllowedInstancesFilename = \
        acct_dir(base_dir, nickname, domain) + '/dmAllowedInstances.txt'
    if not os.path.isfile(dmAllowedInstancesFilename):
        return False
    if sendingActorDomain + '\n' in open(dmAllowedInstancesFilename).read():
        return True
    return False


def getOccupationSkills(actor_json: {}) -> []:
    """Returns the list of skills for an actor
    """
    if 'hasOccupation' not in actor_json:
        return []
    if not isinstance(actor_json['hasOccupation'], list):
        return []
    for occupationItem in actor_json['hasOccupation']:
        if not isinstance(occupationItem, dict):
            continue
        if not occupationItem.get('@type'):
            continue
        if not occupationItem['@type'] == 'Occupation':
            continue
        if not occupationItem.get('skills'):
            continue
        if isinstance(occupationItem['skills'], list):
            return occupationItem['skills']
        elif isinstance(occupationItem['skills'], str):
            return [occupationItem['skills']]
        break
    return []


def getOccupationName(actor_json: {}) -> str:
    """Returns the occupation name an actor
    """
    if not actor_json.get('hasOccupation'):
        return ""
    if not isinstance(actor_json['hasOccupation'], list):
        return ""
    for occupationItem in actor_json['hasOccupation']:
        if not isinstance(occupationItem, dict):
            continue
        if not occupationItem.get('@type'):
            continue
        if occupationItem['@type'] != 'Occupation':
            continue
        if not occupationItem.get('name'):
            continue
        if isinstance(occupationItem['name'], str):
            return occupationItem['name']
        break
    return ""


def setOccupationName(actor_json: {}, name: str) -> bool:
    """Sets the occupation name of an actor
    """
    if not actor_json.get('hasOccupation'):
        return False
    if not isinstance(actor_json['hasOccupation'], list):
        return False
    for index in range(len(actor_json['hasOccupation'])):
        occupationItem = actor_json['hasOccupation'][index]
        if not isinstance(occupationItem, dict):
            continue
        if not occupationItem.get('@type'):
            continue
        if occupationItem['@type'] != 'Occupation':
            continue
        occupationItem['name'] = name
        return True
    return False


def setOccupationSkillsList(actor_json: {}, skillsList: []) -> bool:
    """Sets the occupation skills for an actor
    """
    if 'hasOccupation' not in actor_json:
        return False
    if not isinstance(actor_json['hasOccupation'], list):
        return False
    for index in range(len(actor_json['hasOccupation'])):
        occupationItem = actor_json['hasOccupation'][index]
        if not isinstance(occupationItem, dict):
            continue
        if not occupationItem.get('@type'):
            continue
        if occupationItem['@type'] != 'Occupation':
            continue
        occupationItem['skills'] = skillsList
        return True
    return False


def isAccountDir(dirName: str) -> bool:
    """Is the given directory an account within /accounts ?
    """
    if '@' not in dirName:
        return False
    if 'inbox@' in dirName or 'news@' in dirName:
        return False
    return True


def permittedDir(path: str) -> bool:
    """These are special paths which should not be accessible
       directly via GET or POST
    """
    if path.startswith('/wfendpoints') or \
       path.startswith('/keys') or \
       path.startswith('/accounts'):
        return False
    return True


def userAgentDomain(userAgent: str, debug: bool) -> str:
    """If the User-Agent string contains a domain
    then return it
    """
    if '+http' not in userAgent:
        return None
    agentDomain = userAgent.split('+http')[1].strip()
    if '://' in agentDomain:
        agentDomain = agentDomain.split('://')[1]
    if '/' in agentDomain:
        agentDomain = agentDomain.split('/')[0]
    if ')' in agentDomain:
        agentDomain = agentDomain.split(')')[0].strip()
    if ' ' in agentDomain:
        agentDomain = agentDomain.replace(' ', '')
    if ';' in agentDomain:
        agentDomain = agentDomain.replace(';', '')
    if '.' not in agentDomain:
        return None
    if debug:
        print('User-Agent Domain: ' + agentDomain)
    return agentDomain


def has_object_dict(post_json_object: {}) -> bool:
    """Returns true if the given post has an object dict
    """
    if post_json_object.get('object'):
        if isinstance(post_json_object['object'], dict):
            return True
    return False


def getAltPath(actor: str, domain_full: str, callingDomain: str) -> str:
    """Returns alternate path from the actor
    eg. https://clearnetdomain/path becomes http://oniondomain/path
    """
    postActor = actor
    if callingDomain not in actor and domain_full in actor:
        if callingDomain.endswith('.onion') or \
           callingDomain.endswith('.i2p'):
            postActor = \
                'http://' + callingDomain + actor.split(domain_full)[1]
            print('Changed POST domain from ' + actor + ' to ' + postActor)
    return postActor


def getActorPropertyUrl(actor_json: {}, propertyName: str) -> str:
    """Returns a url property from an actor
    """
    if not actor_json.get('attachment'):
        return ''
    propertyName = propertyName.lower()
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith(propertyName):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = property_value['value'].strip()
        prefixes = getProtocolPrefixes()
        prefixFound = False
        for prefix in prefixes:
            if property_value['value'].startswith(prefix):
                prefixFound = True
                break
        if not prefixFound:
            continue
        if '.' not in property_value['value']:
            continue
        if ' ' in property_value['value']:
            continue
        if ',' in property_value['value']:
            continue
        return property_value['value']
    return ''


def removeDomainPort(domain: str) -> str:
    """If the domain has a port appended then remove it
    eg. mydomain.com:80 becomes mydomain.com
    """
    if ':' in domain:
        if domain.startswith('did:'):
            return domain
        domain = domain.split(':')[0]
    return domain


def getPortFromDomain(domain: str) -> int:
    """If the domain has a port number appended then return it
    eg. mydomain.com:80 returns 80
    """
    if ':' in domain:
        if domain.startswith('did:'):
            return None
        portStr = domain.split(':')[1]
        if portStr.isdigit():
            return int(portStr)
    return None


def validUrlPrefix(url: str) -> bool:
    """Does the given url have a valid prefix?
    """
    if '/' not in url:
        return False
    prefixes = ('https:', 'http:', 'hyper:', 'i2p:', 'gnunet:')
    for pre in prefixes:
        if url.startswith(pre):
            return True
    return False


def removeLineEndings(text: str) -> str:
    """Removes any newline from the end of a string
    """
    text = text.replace('\n', '')
    text = text.replace('\r', '')
    return text.strip()


def validPassword(password: str) -> bool:
    """Returns true if the given password is valid
    """
    if len(password) < 8:
        return False
    return True


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def dateStringToSeconds(dateStr: str) -> int:
    """Converts a date string (eg "published") into seconds since epoch
    """
    try:
        expiryTime = \
            datetime.datetime.strptime(dateStr, '%Y-%m-%dT%H:%M:%SZ')
    except BaseException:
        print('EX: dateStringToSeconds unable to parse date ' + str(dateStr))
        return None
    return int(datetime.datetime.timestamp(expiryTime))


def dateSecondsToString(dateSec: int) -> str:
    """Converts a date in seconds since epoch to a string
    """
    thisDate = datetime.datetime.fromtimestamp(dateSec)
    return thisDate.strftime("%Y-%m-%dT%H:%M:%SZ")


def hasGroupType(base_dir: str, actor: str, person_cache: {},
                 debug: bool = False) -> bool:
    """Does the given actor url have a group type?
    """
    # does the actor path clearly indicate that this is a group?
    # eg. https://lemmy/c/groupname
    groupPaths = getGroupPaths()
    for grpPath in groupPaths:
        if grpPath in actor:
            if debug:
                print('grpPath ' + grpPath + ' in ' + actor)
            return True
    # is there a cached actor which can be examined for Group type?
    return isGroupActor(base_dir, actor, person_cache, debug)


def isGroupActor(base_dir: str, actor: str, person_cache: {},
                 debug: bool = False) -> bool:
    """Is the given actor a group?
    """
    if person_cache:
        if person_cache.get(actor):
            if person_cache[actor].get('actor'):
                if person_cache[actor]['actor'].get('type'):
                    if person_cache[actor]['actor']['type'] == 'Group':
                        if debug:
                            print('Cached actor ' + actor + ' has Group type')
                        return True
                return False
    if debug:
        print('Actor ' + actor + ' not in cache')
    cachedActorFilename = \
        base_dir + '/cache/actors/' + (actor.replace('/', '#')) + '.json'
    if not os.path.isfile(cachedActorFilename):
        if debug:
            print('Cached actor file not found ' + cachedActorFilename)
        return False
    if '"type": "Group"' in open(cachedActorFilename).read():
        if debug:
            print('Group type found in ' + cachedActorFilename)
        return True
    return False


def isGroupAccount(base_dir: str, nickname: str, domain: str) -> bool:
    """Returns true if the given account is a group
    """
    accountFilename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(accountFilename):
        return False
    if '"type": "Group"' in open(accountFilename).read():
        return True
    return False


def getCurrencies() -> {}:
    """Returns a dictionary of currencies
    """
    return {
        "CA$": "CAD",
        "J$": "JMD",
        "£": "GBP",
        "€": "EUR",
        "؋": "AFN",
        "ƒ": "AWG",
        "₼": "AZN",
        "Br": "BYN",
        "BZ$": "BZD",
        "$b": "BOB",
        "KM": "BAM",
        "P": "BWP",
        "лв": "BGN",
        "R$": "BRL",
        "៛": "KHR",
        "$U": "UYU",
        "RD$": "DOP",
        "$": "USD",
        "₡": "CRC",
        "kn": "HRK",
        "₱": "CUP",
        "Kč": "CZK",
        "kr": "NOK",
        "¢": "GHS",
        "Q": "GTQ",
        "L": "HNL",
        "Ft": "HUF",
        "Rp": "IDR",
        "₹": "INR",
        "﷼": "IRR",
        "₪": "ILS",
        "¥": "JPY",
        "₩": "KRW",
        "₭": "LAK",
        "ден": "MKD",
        "RM": "MYR",
        "₨": "MUR",
        "₮": "MNT",
        "MT": "MZN",
        "C$": "NIO",
        "₦": "NGN",
        "Gs": "PYG",
        "zł": "PLN",
        "lei": "RON",
        "₽": "RUB",
        "Дин": "RSD",
        "S": "SOS",
        "R": "ZAR",
        "CHF": "CHF",
        "NT$": "TWD",
        "฿": "THB",
        "TT$": "TTD",
        "₴": "UAH",
        "Bs": "VEF",
        "₫": "VND",
        "Z$": "ZQD"
    }


def getSupportedLanguages(base_dir: str) -> []:
    """Returns a list of supported languages
    """
    translationsDir = base_dir + '/translations'
    languagesStr = []
    for _, _, files in os.walk(translationsDir):
        for f in files:
            if not f.endswith('.json'):
                continue
            lang = f.split('.')[0]
            if len(lang) == 2:
                languagesStr.append(lang)
        break
    return languagesStr


def getCategoryTypes(base_dir: str) -> []:
    """Returns the list of ontologies
    """
    ontologyDir = base_dir + '/ontology'
    categories = []
    for _, _, files in os.walk(ontologyDir):
        for f in files:
            if not f.endswith('.json'):
                continue
            if '#' in f or '~' in f:
                continue
            if f.startswith('custom'):
                continue
            ontologyFilename = f.split('.')[0]
            if 'Types' in ontologyFilename:
                categories.append(ontologyFilename.replace('Types', ''))
        break
    return categories


def getSharesFilesList() -> []:
    """Returns the possible shares files
    """
    return ('shares', 'wanted')


def replaceUsersWithAt(actor: str) -> str:
    """ https://domain/users/nick becomes https://domain/@nick
    """
    uPaths = get_user_paths()
    for path in uPaths:
        if path in actor:
            actor = actor.replace(path, '/@')
            break
    return actor


def hasActor(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have an actor?
    """
    if post_json_object.get('actor'):
        if '#' in post_json_object['actor']:
            return False
        return True
    if debug:
        if post_json_object.get('type'):
            msg = post_json_object['type'] + ' has missing actor'
            if post_json_object.get('id'):
                msg += ' ' + post_json_object['id']
            print(msg)
    return False


def hasObjectStringType(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have a type field within an object dict?
    """
    if not has_object_dict(post_json_object):
        if debug:
            print('hasObjectStringType no object found')
        return False
    if post_json_object['object'].get('type'):
        if isinstance(post_json_object['object']['type'], str):
            return True
        elif debug:
            if post_json_object.get('type'):
                print('DEBUG: ' + post_json_object['type'] +
                      ' type within object is not a string')
    if debug:
        print('No type field within object ' + post_json_object['id'])
    return False


def hasObjectStringObject(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have an object string field within an object dict?
    """
    if not has_object_dict(post_json_object):
        if debug:
            print('hasObjectStringType no object found')
        return False
    if post_json_object['object'].get('object'):
        if isinstance(post_json_object['object']['object'], str):
            return True
        elif debug:
            if post_json_object.get('type'):
                print('DEBUG: ' + post_json_object['type'] +
                      ' object within dict is not a string')
    if debug:
        print('No object field within dict ' + post_json_object['id'])
    return False


def hasObjectString(post_json_object: {}, debug: bool) -> bool:
    """Does the given post have an object string field?
    """
    if post_json_object.get('object'):
        if isinstance(post_json_object['object'], str):
            return True
        elif debug:
            if post_json_object.get('type'):
                print('DEBUG: ' + post_json_object['type'] +
                      ' object is not a string')
    if debug:
        print('No object field within post ' + post_json_object['id'])
    return False


def getNewPostEndpoints() -> []:
    """Returns a list of endpoints for new posts
    """
    return (
        'newpost', 'newblog', 'newunlisted', 'newfollowers', 'newdm',
        'newreminder', 'newreport', 'newquestion', 'newshare', 'newwanted',
        'editblogpost'
    )


def getFavFilenameFromUrl(base_dir: str, faviconUrl: str) -> str:
    """Returns the cached filename for a favicon based upon its url
    """
    if '://' in faviconUrl:
        faviconUrl = faviconUrl.split('://')[1]
    if '/favicon.' in faviconUrl:
        faviconUrl = faviconUrl.replace('/favicon.', '.')
    return base_dir + '/favicons/' + faviconUrl.replace('/', '-')
