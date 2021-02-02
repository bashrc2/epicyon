__filename__ = "utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
import shutil
import datetime
import json
from socket import error as SocketError
import errno
import urllib.request
import idna
from pprint import pprint
from calendar import monthrange
from followingCalendar import addPersonToCalendar


def _localNetworkHost(host: str) -> bool:
    """Returns true if the given host is on the local network
    """
    if host.startswith('localhost') or \
       host.startswith('192.') or \
       host.startswith('127.') or \
       host.startswith('10.'):
        return True
    return False


def decodedHost(host: str) -> str:
    """Convert hostname to internationalized domain
    https://en.wikipedia.org/wiki/Internationalized_domain_name
    """
    if ':' not in host:
        # eg. mydomain:8000
        if not _localNetworkHost(host):
            if not host.endswith('.onion'):
                if not host.endswith('.i2p'):
                    return idna.decode(host)
    return host


def getLockedAccount(actorJson: {}) -> bool:
    """Returns whether the given account requires follower approval
    """
    if not actorJson.get('manuallyApprovesFollowers'):
        return False
    if actorJson['manuallyApprovesFollowers'] is True:
        return True
    return False


def hasUsersPath(pathStr: str) -> bool:
    """Whether there is a /users/ path (or equivalent) in the given string
    """
    usersList = ('users', 'accounts', 'channel', 'profile')
    for usersStr in usersList:
        if '/' + usersStr + '/' in pathStr:
            return True
    return False


def validPostDate(published: str, maxAgeDays=7) -> bool:
    """Returns true if the published date is recent and is not in the future
    """
    baselineTime = datetime.datetime(1970, 1, 1)

    daysDiff = datetime.datetime.utcnow() - baselineTime
    nowDaysSinceEpoch = daysDiff.days

    try:
        postTimeObject = \
            datetime.datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
    except BaseException:
        return False

    daysDiff = postTimeObject - baselineTime
    postDaysSinceEpoch = daysDiff.days

    if postDaysSinceEpoch > nowDaysSinceEpoch:
        print("Inbox post has a published date in the future!")
        return False

    if nowDaysSinceEpoch - postDaysSinceEpoch >= maxAgeDays:
        print("Inbox post is not recent enough")
        return False
    return True


def getFullDomain(domain: str, port: int) -> str:
    """Returns the full domain name, including port number
    """
    if not port:
        return domain
    if ':' in domain:
        return domain
    if port == 80 or port == 443:
        return domain
    return domain + ':' + str(port)


def isDormant(baseDir: str, nickname: str, domain: str, actor: str,
              dormantMonths=3) -> bool:
    """Is the given followed actor dormant, from the standpoint
    of the given account
    """
    lastSeenFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + \
        '/lastseen/' + actor.replace('/', '#') + '.txt'

    if not os.path.isfile(lastSeenFilename):
        return False

    with open(lastSeenFilename, 'r') as lastSeenFile:
        daysSinceEpochStr = lastSeenFile.read()
        daysSinceEpoch = int(daysSinceEpochStr)
        currTime = datetime.datetime.utcnow()
        currDaysSinceEpoch = (currTime - datetime.datetime(1970, 1, 1)).days
        timeDiffMonths = \
            int((currDaysSinceEpoch - daysSinceEpoch) / 30)
        if timeDiffMonths >= dormantMonths:
            return True
    return False


def isEditor(baseDir: str, nickname: str) -> bool:
    """Returns true if the given nickname is an editor
    """
    editorsFile = baseDir + '/accounts/editors.txt'

    if not os.path.isfile(editorsFile):
        adminName = getConfigParam(baseDir, 'admin')
        if not adminName:
            return False
        if adminName == nickname:
            return True
        return False

    with open(editorsFile, "r") as f:
        lines = f.readlines()
        if len(lines) == 0:
            adminName = getConfigParam(baseDir, 'admin')
            if not adminName:
                return False
            if adminName == nickname:
                return True
        for editor in lines:
            editor = editor.strip('\n').strip('\r')
            if editor == nickname:
                return True
    return False


def getImageExtensions() -> []:
    """Returns a list of the possible image file extensions
    """
    return ('png', 'jpg', 'jpeg', 'gif', 'webp', 'avif', 'svg')


def getVideoExtensions() -> []:
    """Returns a list of the possible video file extensions
    """
    return ('mp4', 'webm', 'ogv')


def getAudioExtensions() -> []:
    """Returns a list of the possible audio file extensions
    """
    return ('mp3', 'ogg')


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
    content = content.replace('<q>', '"').replace('</q>', '"')
    result = ''
    for ch in content:
        if ch == '<':
            removing = True
        elif ch == '>':
            removing = False
        elif not removing:
            result += ch
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


def _createConfig(baseDir: str) -> None:
    """Creates a configuration file
    """
    configFilename = baseDir + '/config.json'
    if os.path.isfile(configFilename):
        return
    configJson = {
    }
    saveJson(configJson, configFilename)


def setConfigParam(baseDir: str, variableName: str, variableValue) -> None:
    """Sets a configuration value
    """
    _createConfig(baseDir)
    configFilename = baseDir + '/config.json'
    configJson = {}
    if os.path.isfile(configFilename):
        configJson = loadJson(configFilename)
    configJson[variableName] = variableValue
    saveJson(configJson, configFilename)


def getConfigParam(baseDir: str, variableName: str):
    """Gets a configuration value
    """
    _createConfig(baseDir)
    configFilename = baseDir + '/config.json'
    configJson = loadJson(configFilename)
    if configJson:
        if variableName in configJson:
            return configJson[variableName]
    return None


def isSuspended(baseDir: str, nickname: str) -> bool:
    """Returns true if the given nickname is suspended
    """
    adminNickname = getConfigParam(baseDir, 'admin')
    if not adminNickname:
        return False
    if nickname == adminNickname:
        return False

    suspendedFilename = baseDir + '/accounts/suspended.txt'
    if os.path.isfile(suspendedFilename):
        with open(suspendedFilename, "r") as f:
            lines = f.readlines()
        for suspended in lines:
            if suspended.strip('\n').strip('\r') == nickname:
                return True
    return False


def getFollowersList(baseDir: str,
                     nickname: str, domain: str,
                     followFile='following.txt') -> []:
    """Returns a list of followers for the given account
    """
    filename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/' + followFile

    if not os.path.isfile(filename):
        return []

    with open(filename, "r") as f:
        lines = f.readlines()
        for i in range(len(lines)):
            lines[i] = lines[i].strip()
        return lines
    return []


def getFollowersOfPerson(baseDir: str,
                         nickname: str, domain: str,
                         followFile='following.txt') -> []:
    """Returns a list containing the followers of the given person
    Used by the shared inbox to know who to send incoming mail to
    """
    followers = []
    if ':' in domain:
        domain = domain.split(':')[0]
    handle = nickname + '@' + domain
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        return followers
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for account in dirs:
            filename = os.path.join(subdir, account) + '/' + followFile
            if account == handle or account.startswith('inbox@'):
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
    return idStr


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
            'dat://', 'i2p://', 'gnunet://',
            'hyper://', 'gemini://', 'gopher://', 'briar:')


def removeAvatarFromCache(baseDir: str, actorStr: str) -> None:
    """Removes any existing avatar entries from the cache
    This avoids duplicate entries with differing extensions
    """
    avatarFilenameExtensions = getImageExtensions()
    for extension in avatarFilenameExtensions:
        avatarFilename = \
            baseDir + '/cache/avatars/' + actorStr + '.' + extension
        if os.path.isfile(avatarFilename):
            os.remove(avatarFilename)


def saveJson(jsonObject: {}, filename: str) -> bool:
    """Saves json to a file
    """
    tries = 0
    while tries < 5:
        try:
            with open(filename, 'w+') as fp:
                fp.write(json.dumps(jsonObject))
                return True
        except BaseException:
            print('WARN: saveJson ' + str(tries))
            time.sleep(1)
            tries += 1
    return False


def loadJson(filename: str, delaySec=2, maxTries=5) -> {}:
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
            print('WARN: loadJson exception')
            if delaySec > 0:
                time.sleep(delaySec)
            tries += 1
    return jsonObject


def loadJsonOnionify(filename: str, domain: str, onionDomain: str,
                     delaySec=2) -> {}:
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
                    data = data.replace(domain, onionDomain)
                    data = data.replace('https:', 'http:')
                    print('*****data: ' + data)
                jsonObject = json.loads(data)
                break
        except BaseException:
            print('WARN: loadJson exception')
            if delaySec > 0:
                time.sleep(delaySec)
            tries += 1
    return jsonObject


def getStatusNumber(publishedStr=None) -> (str, str):
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
    return ('gab.com', 'gabfed.com', 'spinster.xyz',
            'kiwifarms.cc', 'djitter.com')


def isEvil(domain: str) -> bool:
    if not isinstance(domain, str):
        print('WARN: Malformed domain ' + str(domain))
        return True
    # https://www.youtube.com/watch?v=5qw1hcevmdU
    evilDomains = evilIncarnate()
    for concentratedEvil in evilDomains:
        if domain.endswith(concentratedEvil):
            return True
    return False


def containsInvalidChars(jsonStr: str) -> bool:
    """Does the given json string contain invalid characters?
    e.g. dubious clacks/admin dogwhistles
    """
    invalidStrings = {
        '卐', '卍', '࿕', '࿖', '࿗', '࿘'
    }
    for isInvalid in invalidStrings:
        if isInvalid in jsonStr:
            return True
    return False


def createPersonDir(nickname: str, domain: str, baseDir: str,
                    dirname: str) -> str:
    """Create a directory for a person
    """
    handle = nickname + '@' + domain
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        os.mkdir(baseDir + '/accounts/' + handle)
    boxDir = baseDir + '/accounts/' + handle + '/' + dirname
    if not os.path.isdir(boxDir):
        os.mkdir(boxDir)
    return boxDir


def createOutboxDir(nickname: str, domain: str, baseDir: str) -> str:
    """Create an outbox for a person
    """
    return createPersonDir(nickname, domain, baseDir, 'outbox')


def createInboxQueueDir(nickname: str, domain: str, baseDir: str) -> str:
    """Create an inbox queue and returns the feed filename and directory
    """
    return createPersonDir(nickname, domain, baseDir, 'queue')


def domainPermitted(domain: str, federationList: []):
    if len(federationList) == 0:
        return True
    if ':' in domain:
        domain = domain.split(':')[0]
    if domain in federationList:
        return True
    return False


def urlPermitted(url: str, federationList: []):
    if isEvil(url):
        return False
    if not federationList:
        return True
    for domain in federationList:
        if domain in url:
            return True
    return False


def dangerousMarkup(content: str, allowLocalNetworkAccess: bool) -> bool:
    """Returns true if the given content contains dangerous html markup
    """
    if '<' not in content:
        return False
    if '>' not in content:
        return False
    contentSections = content.split('<')
    invalidPartials = ()
    if not allowLocalNetworkAccess:
        invalidPartials = ('localhost', '127.0.', '192.168', '10.0.')
    invalidStrings = ('script', 'canvas', 'style', 'abbr',
                      'frame', 'iframe', 'html', 'body',
                      'hr', 'allow-popups', 'allow-scripts')
    for markup in contentSections:
        if '>' not in markup:
            continue
        markup = markup.split('>')[0].strip()
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


def getDisplayName(baseDir: str, actor: str, personCache: {}) -> str:
    """Returns the display name for the given actor
    """
    if '/statuses/' in actor:
        actor = actor.split('/statuses/')[0]
    if not personCache.get(actor):
        return None
    nameFound = None
    if personCache[actor].get('actor'):
        if personCache[actor]['actor'].get('name'):
            nameFound = personCache[actor]['actor']['name']
    else:
        # Try to obtain from the cached actors
        cachedActorFilename = \
            baseDir + '/cache/actors/' + (actor.replace('/', '#')) + '.json'
        if os.path.isfile(cachedActorFilename):
            actorJson = loadJson(cachedActorFilename, 1)
            if actorJson:
                if actorJson.get('name'):
                    nameFound = actorJson['name']
    if nameFound:
        if dangerousMarkup(nameFound, False):
            nameFound = "*ADVERSARY*"
    return nameFound


def getNicknameFromActor(actor: str) -> str:
    """Returns the nickname from an actor url
    """
    if actor.startswith('@'):
        actor = actor[1:]
    if '/users/' not in actor:
        if '/profile/' in actor:
            nickStr = actor.split('/profile/')[1].replace('@', '')
            if '/' not in nickStr:
                return nickStr
            else:
                return nickStr.split('/')[0]
        elif '/channel/' in actor:
            nickStr = actor.split('/channel/')[1].replace('@', '')
            if '/' not in nickStr:
                return nickStr
            else:
                return nickStr.split('/')[0]
        elif '/accounts/' in actor:
            nickStr = actor.split('/accounts/')[1].replace('@', '')
            if '/' not in nickStr:
                return nickStr
            else:
                return nickStr.split('/')[0]
        elif '/@' in actor:
            # https://domain/@nick
            nickStr = actor.split('/@')[1]
            if '/' in nickStr:
                nickStr = nickStr.split('/')[0]
            return nickStr
        elif '@' in actor:
            nickStr = actor.split('@')[0]
            return nickStr
        return None
    nickStr = actor.split('/users/')[1].replace('@', '')
    if '/' not in nickStr:
        return nickStr
    else:
        return nickStr.split('/')[0]


def getDomainFromActor(actor: str) -> (str, int):
    """Returns the domain name from an actor url
    """
    if actor.startswith('@'):
        actor = actor[1:]
    port = None
    prefixes = getProtocolPrefixes()
    if '/profile/' in actor:
        domain = actor.split('/profile/')[0]
        for prefix in prefixes:
            domain = domain.replace(prefix, '')
    elif '/accounts/' in actor:
        domain = actor.split('/accounts/')[0]
        for prefix in prefixes:
            domain = domain.replace(prefix, '')
    elif '/channel/' in actor:
        domain = actor.split('/channel/')[0]
        for prefix in prefixes:
            domain = domain.replace(prefix, '')
    elif '/users/' in actor:
        domain = actor.split('/users/')[0]
        for prefix in prefixes:
            domain = domain.replace(prefix, '')
    elif '/@' in actor:
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
        portStr = domain.split(':')[1]
        if not portStr.isdigit():
            return None, None
        port = int(portStr)
        domain = domain.split(':')[0]
    return domain, port


def _setDefaultPetName(baseDir: str, nickname: str, domain: str,
                       followNickname: str, followDomain: str) -> None:
    """Sets a default petname
    This helps especially when using onion or i2p address
    """
    if ':' in domain:
        domain = domain.split(':')[0]
    userPath = baseDir + '/accounts/' + nickname + '@' + domain
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


def followPerson(baseDir: str, nickname: str, domain: str,
                 followNickname: str, followDomain: str,
                 federationList: [], debug: bool,
                 followFile='following.txt') -> bool:
    """Adds a person to the follow list
    """
    followDomainStrLower = followDomain.lower().replace('\n', '')
    if not domainPermitted(followDomainStrLower,
                           federationList):
        if debug:
            print('DEBUG: follow of domain ' +
                  followDomain + ' not permitted')
        return False
    if debug:
        print('DEBUG: follow of domain ' + followDomain)

    if ':' in domain:
        handle = nickname + '@' + domain.split(':')[0]
    else:
        handle = nickname + '@' + domain

    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('WARN: account for ' + handle + ' does not exist')
        return False

    if ':' in followDomain:
        handleToFollow = followNickname + '@' + followDomain.split(':')[0]
    else:
        handleToFollow = followNickname + '@' + followDomain

    # was this person previously unfollowed?
    unfollowedFilename = baseDir + '/accounts/' + handle + '/unfollowed.txt'
    if os.path.isfile(unfollowedFilename):
        if handleToFollow in open(unfollowedFilename).read():
            # remove them from the unfollowed file
            newLines = ''
            with open(unfollowedFilename, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if handleToFollow not in line:
                        newLines += line
            with open(unfollowedFilename, 'w+') as f:
                f.write(newLines)

    if not os.path.isdir(baseDir + '/accounts'):
        os.mkdir(baseDir + '/accounts')
    handleToFollow = followNickname + '@' + followDomain
    filename = baseDir + '/accounts/' + handle + '/' + followFile
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
        except Exception as e:
            print('WARN: Failed to write entry to follow file ' +
                  filename + ' ' + str(e))
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
        addPersonToCalendar(baseDir, nickname, domain,
                            followNickname, followDomain)
        # add a default petname
        _setDefaultPetName(baseDir, nickname, domain,
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


def locateNewsVotes(baseDir: str, domain: str,
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

    accountDir = baseDir + '/accounts/news@' + domain + '/'
    postFilename = accountDir + 'outbox/' + postUrl
    if os.path.isfile(postFilename):
        return postFilename

    return None


def locateNewsArrival(baseDir: str, domain: str,
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

    accountDir = baseDir + '/accounts/news@' + domain + '/'
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


def clearFromPostCaches(baseDir: str, recentPostsCache: {},
                        postId: str) -> None:
    """Clears cached html for the given post, so that edits
    to news will appear
    """
    filename = '/postcache/' + postId + '.html'
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if 'inbox@' in acct:
                continue
            cacheDir = os.path.join(baseDir + '/accounts', acct)
            postFilename = cacheDir + filename
            if os.path.isfile(postFilename):
                try:
                    os.remove(postFilename)
                except BaseException:
                    print('WARN: clearFromPostCaches file not removed ' +
                          postFilename)
                    pass
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


def locatePost(baseDir: str, nickname: str, domain: str,
               postUrl: str, replies=False) -> str:
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
    boxes = ('inbox', 'outbox', 'tlblogs', 'tlevents')
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain + '/'
    for boxName in boxes:
        postFilename = accountDir + boxName + '/' + postUrl
        if os.path.isfile(postFilename):
            return postFilename

    # check news posts
    accountDir = baseDir + '/accounts/news' + '@' + domain + '/'
    postFilename = accountDir + 'outbox/' + postUrl
    if os.path.isfile(postFilename):
        return postFilename

    # is it in the announce cache?
    postFilename = baseDir + '/cache/announce/' + nickname + '/' + postUrl
    if os.path.isfile(postFilename):
        return postFilename

    # print('WARN: unable to locate ' + nickname + ' ' + postUrl)
    return None


def _removeAttachment(baseDir: str, httpPrefix: str, domain: str,
                      postJson: {}):
    if not postJson.get('attachment'):
        return
    if not postJson['attachment'][0].get('url'):
        return
#    if port:
#        if port != 80 and port != 443:
#            if ':' not in domain:
#                domain = domain + ':' + str(port)
    attachmentUrl = postJson['attachment'][0]['url']
    if not attachmentUrl:
        return
    mediaFilename = baseDir + '/' + \
        attachmentUrl.replace(httpPrefix + '://' + domain + '/', '')
    if os.path.isfile(mediaFilename):
        os.remove(mediaFilename)
    etagFilename = mediaFilename + '.etag'
    if os.path.isfile(etagFilename):
        os.remove(etagFilename)
    postJson['attachment'] = []


def removeModerationPostFromIndex(baseDir: str, postUrl: str,
                                  debug: bool) -> None:
    """Removes a url from the moderation index
    """
    moderationIndexFile = baseDir + '/accounts/moderation.txt'
    if not os.path.isfile(moderationIndexFile):
        return
    postId = removeIdEnding(postUrl)
    if postId in open(moderationIndexFile).read():
        with open(moderationIndexFile, "r") as f:
            lines = f.readlines()
            with open(moderationIndexFile, "w+") as f:
                for line in lines:
                    if line.strip("\n").strip("\r") != postId:
                        f.write(line)
                    else:
                        if debug:
                            print('DEBUG: removed ' + postId +
                                  ' from moderation index')


def _isReplyToBlogPost(baseDir: str, nickname: str, domain: str,
                       postJsonObject: str):
    """Is the given post a reply to a blog post?
    """
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if not postJsonObject['object'].get('inReplyTo'):
        return False
    if not isinstance(postJsonObject['object']['inReplyTo'], str):
        return False
    blogsIndexFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/tlblogs.index'
    if not os.path.isfile(blogsIndexFilename):
        return False
    postId = removeIdEnding(postJsonObject['object']['inReplyTo'])
    postId = postId.replace('/', '#')
    if postId in open(blogsIndexFilename).read():
        return True
    return False


def deletePost(baseDir: str, httpPrefix: str,
               nickname: str, domain: str, postFilename: str,
               debug: bool, recentPostsCache: {}) -> None:
    """Recursively deletes a post and its replies and attachments
    """
    postJsonObject = loadJson(postFilename, 1)
    if postJsonObject:
        # don't allow deletion of bookmarked posts
        bookmarksIndexFilename = \
            baseDir + '/accounts/' + nickname + '@' + domain + \
            '/bookmarks.index'
        if os.path.isfile(bookmarksIndexFilename):
            bookmarkIndex = postFilename.split('/')[-1] + '\n'
            if bookmarkIndex in open(bookmarksIndexFilename).read():
                return

        # don't remove replies to blog posts
        if _isReplyToBlogPost(baseDir, nickname, domain,
                              postJsonObject):
            return

        # remove from recent posts cache in memory
        if recentPostsCache:
            postId = \
                removeIdEnding(postJsonObject['id']).replace('/', '#')
            if recentPostsCache.get('index'):
                if postId in recentPostsCache['index']:
                    recentPostsCache['index'].remove(postId)
            if recentPostsCache.get('json'):
                if recentPostsCache['json'].get(postId):
                    del recentPostsCache['json'][postId]
            if recentPostsCache.get('html'):
                if recentPostsCache['html'].get(postId):
                    del recentPostsCache['html'][postId]

        # remove any attachment
        _removeAttachment(baseDir, httpPrefix, domain, postJsonObject)

        extensions = ('votes', 'arrived', 'muted')
        for ext in extensions:
            extFilename = postFilename + '.' + ext
            if os.path.isfile(extFilename):
                os.remove(extFilename)

        # remove cached html version of the post
        cachedPostFilename = \
            getCachedPostFilename(baseDir, nickname, domain, postJsonObject)
        if cachedPostFilename:
            if os.path.isfile(cachedPostFilename):
                os.remove(cachedPostFilename)
        # removePostFromCache(postJsonObject,recentPostsCache)

        hasObject = False
        if postJsonObject.get('object'):
            hasObject = True

        # remove from moderation index file
        if hasObject:
            if isinstance(postJsonObject['object'], dict):
                if postJsonObject['object'].get('moderationStatus'):
                    if postJsonObject.get('id'):
                        postId = removeIdEnding(postJsonObject['id'])
                        removeModerationPostFromIndex(baseDir, postId, debug)

        # remove any hashtags index entries
        removeHashtagIndex = False
        if hasObject:
            if hasObject and isinstance(postJsonObject['object'], dict):
                if postJsonObject['object'].get('content'):
                    if '#' in postJsonObject['object']['content']:
                        removeHashtagIndex = True
        if removeHashtagIndex:
            if postJsonObject['object'].get('id') and \
               postJsonObject['object'].get('tag'):
                # get the id of the post
                postId = removeIdEnding(postJsonObject['object']['id'])
                for tag in postJsonObject['object']['tag']:
                    if tag['type'] != 'Hashtag':
                        continue
                    if not tag.get('name'):
                        continue
                    # find the index file for this tag
                    tagIndexFilename = \
                        baseDir + '/tags/' + tag['name'][1:] + '.txt'
                    if not os.path.isfile(tagIndexFilename):
                        continue
                    # remove postId from the tag index file
                    lines = None
                    with open(tagIndexFilename, "r") as f:
                        lines = f.readlines()
                    if lines:
                        newlines = ''
                        for fileLine in lines:
                            if postId in fileLine:
                                continue
                            newlines += fileLine
                        if not newlines.strip():
                            # if there are no lines then remove the
                            # hashtag file
                            os.remove(tagIndexFilename)
                        else:
                            with open(tagIndexFilename, "w+") as f:
                                f.write(newlines)

    # remove any replies
    repliesFilename = postFilename.replace('.json', '.replies')
    if os.path.isfile(repliesFilename):
        if debug:
            print('DEBUG: removing replies to ' + postFilename)
        with open(repliesFilename, 'r') as f:
            for replyId in f:
                replyFile = locatePost(baseDir, nickname, domain, replyId)
                if replyFile:
                    if os.path.isfile(replyFile):
                        deletePost(baseDir, httpPrefix,
                                   nickname, domain, replyFile, debug,
                                   recentPostsCache)
        # remove the replies file
        os.remove(repliesFilename)
    # finally, remove the post itself
    os.remove(postFilename)


def validNickname(domain: str, nickname: str) -> bool:
    forbiddenChars = ('.', ' ', '/', '?', ':', ';', '@', '#')
    for c in forbiddenChars:
        if c in nickname:
            return False
    # this should only apply for the shared inbox
    if nickname == domain:
        return False
    reservedNames = ('inbox', 'dm', 'outbox', 'following',
                     'public', 'followers', 'category',
                     'channel', 'calendar',
                     'tlreplies', 'tlmedia', 'tlblogs',
                     'tlevents', 'tlblogs', 'tlfeatures',
                     'moderation', 'moderationaction',
                     'activity', 'undo', 'pinned',
                     'reply', 'replies', 'question', 'like',
                     'likes', 'users', 'statuses', 'tags',
                     'accounts', 'channels', 'profile',
                     'updates', 'repeat', 'announce',
                     'shares', 'fonts', 'icons', 'avatars')
    if nickname in reservedNames:
        return False
    return True


def noOfAccounts(baseDir: str) -> bool:
    """Returns the number of accounts on the system
    """
    accountCtr = 0
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for account in dirs:
            if '@' in account:
                if not account.startswith('inbox@'):
                    accountCtr += 1
        break
    return accountCtr


def noOfActiveAccountsMonthly(baseDir: str, months: int) -> bool:
    """Returns the number of accounts on the system this month
    """
    accountCtr = 0
    currTime = int(time.time())
    monthSeconds = int(60*60*24*30*months)
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for account in dirs:
            if '@' in account:
                if not account.startswith('inbox@'):
                    lastUsedFilename = \
                        baseDir + '/accounts/' + account + '/.lastUsed'
                    if os.path.isfile(lastUsedFilename):
                        with open(lastUsedFilename, 'r') as lastUsedFile:
                            lastUsed = lastUsedFile.read()
                            if lastUsed.isdigit():
                                timeDiff = (currTime - int(lastUsed))
                                if timeDiff < monthSeconds:
                                    accountCtr += 1
        break
    return accountCtr


def isPublicPostFromUrl(baseDir: str, nickname: str, domain: str,
                        postUrl: str) -> bool:
    """Returns whether the given url is a public post
    """
    postFilename = locatePost(baseDir, nickname, domain, postUrl)
    if not postFilename:
        return False
    postJsonObject = loadJson(postFilename, 1)
    if not postJsonObject:
        return False
    return isPublicPost(postJsonObject)


def isPublicPost(postJsonObject: {}) -> bool:
    """Returns true if the given post is public
    """
    if not postJsonObject.get('type'):
        return False
    if postJsonObject['type'] != 'Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if not postJsonObject['object'].get('to'):
        return False
    for recipient in postJsonObject['object']['to']:
        if recipient.endswith('#Public'):
            return True
    return False


def copytree(src: str, dst: str, symlinks=False, ignore=None):
    """Copy a directory
    """
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def getCachedPostDirectory(baseDir: str, nickname: str, domain: str) -> str:
    """Returns the directory where the html post cache exists
    """
    htmlPostCacheDir = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/postcache'
    return htmlPostCacheDir


def getCachedPostFilename(baseDir: str, nickname: str, domain: str,
                          postJsonObject: {}) -> str:
    """Returns the html cache filename for the given post
    """
    cachedPostDir = getCachedPostDirectory(baseDir, nickname, domain)
    if not os.path.isdir(cachedPostDir):
        # print('ERROR: invalid html cache directory '+cachedPostDir)
        return None
    if '@' not in cachedPostDir:
        # print('ERROR: invalid html cache directory '+cachedPostDir)
        return None
    cachedPostId = removeIdEnding(postJsonObject['id'])
    cachedPostFilename = cachedPostDir + '/' + cachedPostId.replace('/', '#')
    return cachedPostFilename + '.html'


def removePostFromCache(postJsonObject: {}, recentPostsCache: {}):
    """ if the post exists in the recent posts cache then remove it
    """
    if not postJsonObject.get('id'):
        return

    if not recentPostsCache.get('index'):
        return

    postId = postJsonObject['id']
    if '#' in postId:
        postId = postId.split('#', 1)[0]
    postId = removeIdEnding(postId).replace('/', '#')
    if postId not in recentPostsCache['index']:
        return

    if recentPostsCache['json'].get(postId):
        del recentPostsCache['json'][postId]
    if recentPostsCache['html'].get(postId):
        del recentPostsCache['html'][postId]
    recentPostsCache['index'].remove(postId)


def updateRecentPostsCache(recentPostsCache: {}, maxRecentPosts: int,
                           postJsonObject: {}, htmlStr: str) -> None:
    """Store recent posts in memory so that they can be quickly recalled
    """
    if not postJsonObject.get('id'):
        return
    postId = postJsonObject['id']
    if '#' in postId:
        postId = postId.split('#', 1)[0]
    postId = removeIdEnding(postId).replace('/', '#')
    if recentPostsCache.get('index'):
        if postId in recentPostsCache['index']:
            return
        recentPostsCache['index'].append(postId)
        postJsonObject['muted'] = False
        recentPostsCache['json'][postId] = json.dumps(postJsonObject)
        recentPostsCache['html'][postId] = htmlStr

        while len(recentPostsCache['html'].items()) > maxRecentPosts:
            postId = recentPostsCache['index'][0]
            recentPostsCache['index'].pop(0)
            del recentPostsCache['json'][postId]
            del recentPostsCache['html'][postId]
    else:
        recentPostsCache['index'] = [postId]
        recentPostsCache['json'] = {}
        recentPostsCache['html'] = {}
        recentPostsCache['json'][postId] = json.dumps(postJsonObject)
        recentPostsCache['html'][postId] = htmlStr


def fileLastModified(filename: str) -> str:
    """Returns the date when a file was last modified
    """
    t = os.path.getmtime(filename)
    modifiedTime = datetime.datetime.fromtimestamp(t)
    return modifiedTime.strftime("%Y-%m-%dT%H:%M:%SZ")


def getCSS(baseDir: str, cssFilename: str, cssCache: {}) -> str:
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


def daysInMonth(year: int, monthNumber: int) -> int:
    """Returns the number of days in the month
    """
    if monthNumber < 1 or monthNumber > 12:
        return None
    daysRange = monthrange(year, monthNumber)
    return daysRange[1]


def mergeDicts(dict1: {}, dict2: {}) -> {}:
    """Merges two dictionaries
    """
    res = {**dict1, **dict2}
    return res


def isEventPost(messageJson: {}) -> bool:
    """Is the given post a mobilizon-type event activity?
    See https://framagit.org/framasoft/mobilizon/-/blob/
    master/lib/federation/activity_stream/converter/event.ex
    """
    if not messageJson.get('id'):
        return False
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
        return False
    if not messageJson['object'].get('type'):
        return False
    if messageJson['object']['type'] != 'Event':
        return False
    print('Event arriving')
    if not messageJson['object'].get('startTime'):
        print('No event start time')
        return False
    if not messageJson['object'].get('actor'):
        print('No event actor')
        return False
    if not messageJson['object'].get('content'):
        print('No event content')
        return False
    if not messageJson['object'].get('name'):
        print('No event name')
        return False
    if not messageJson['object'].get('uuid'):
        print('No event UUID')
        return False
    print('Event detected')
    return True


def isBlogPost(postJsonObject: {}) -> bool:
    """Is the given post a blog post?
    """
    if postJsonObject['type'] != 'Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if not postJsonObject['object'].get('type'):
        return False
    if not postJsonObject['object'].get('content'):
        return False
    if postJsonObject['object']['type'] != 'Article':
        return False
    return True


def isNewsPost(postJsonObject: {}) -> bool:
    """Is the given post a blog post?
    """
    return postJsonObject.get('news')


def searchBoxPosts(baseDir: str, nickname: str, domain: str,
                   searchStr: str, maxResults: int,
                   boxName='outbox') -> []:
    """Search your posts and return a list of the filenames
    containing matching strings
    """
    path = baseDir + '/accounts/' + nickname + '@' + domain + '/' + boxName
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
    # directory, filename = os.path.split(path)
    # directory, filename = (directory or '.'), filename.lower()
    # for f in os.listdir(directory):
    #     if f.lower() == filename:
    #         newpath = os.path.join(directory, f)
    #         if os.path.isfile(newpath):
    #             return newpath
    return None


def undoLikesCollectionEntry(recentPostsCache: {},
                             baseDir: str, postFilename: str, objectUrl: str,
                             actor: str, domain: str, debug: bool) -> None:
    """Undoes a like for a particular actor
    """
    postJsonObject = loadJson(postFilename)
    if postJsonObject:
        # remove any cached version of this post so that the
        # like icon is changed
        nickname = getNicknameFromActor(actor)
        cachedPostFilename = getCachedPostFilename(baseDir, nickname,
                                                   domain, postJsonObject)
        if cachedPostFilename:
            if os.path.isfile(cachedPostFilename):
                os.remove(cachedPostFilename)
        removePostFromCache(postJsonObject, recentPostsCache)

        if not postJsonObject.get('type'):
            return
        if postJsonObject['type'] != 'Create':
            return
        if not postJsonObject.get('object'):
            if debug:
                pprint(postJsonObject)
                print('DEBUG: post '+objectUrl+' has no object')
            return
        if not isinstance(postJsonObject['object'], dict):
            return
        if not postJsonObject['object'].get('likes'):
            return
        if not isinstance(postJsonObject['object']['likes'], dict):
            return
        if not postJsonObject['object']['likes'].get('items'):
            return
        totalItems = 0
        if postJsonObject['object']['likes'].get('totalItems'):
            totalItems = postJsonObject['object']['likes']['totalItems']
        itemFound = False
        for likeItem in postJsonObject['object']['likes']['items']:
            if likeItem.get('actor'):
                if likeItem['actor'] == actor:
                    if debug:
                        print('DEBUG: like was removed for ' + actor)
                    postJsonObject['object']['likes']['items'].remove(likeItem)
                    itemFound = True
                    break
        if itemFound:
            if totalItems == 1:
                if debug:
                    print('DEBUG: likes was removed from post')
                del postJsonObject['object']['likes']
            else:
                itlen = len(postJsonObject['object']['likes']['items'])
                postJsonObject['object']['likes']['totalItems'] = itlen

            saveJson(postJsonObject, postFilename)


def updateLikesCollection(recentPostsCache: {},
                          baseDir: str, postFilename: str,
                          objectUrl: str,
                          actor: str, domain: str, debug: bool) -> None:
    """Updates the likes collection within a post
    """
    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return
    # remove any cached version of this post so that the
    # like icon is changed
    nickname = getNicknameFromActor(actor)
    cachedPostFilename = getCachedPostFilename(baseDir, nickname,
                                               domain, postJsonObject)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            os.remove(cachedPostFilename)
    removePostFromCache(postJsonObject, recentPostsCache)

    if not postJsonObject.get('object'):
        if debug:
            pprint(postJsonObject)
            print('DEBUG: post ' + objectUrl + ' has no object')
        return
    if not isinstance(postJsonObject['object'], dict):
        return
    if not objectUrl.endswith('/likes'):
        objectUrl = objectUrl + '/likes'
    if not postJsonObject['object'].get('likes'):
        if debug:
            print('DEBUG: Adding initial like to ' + objectUrl)
        likesJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'id': objectUrl,
            'type': 'Collection',
            "totalItems": 1,
            'items': [{
                'type': 'Like',
                'actor': actor
            }]
        }
        postJsonObject['object']['likes'] = likesJson
    else:
        if not postJsonObject['object']['likes'].get('items'):
            postJsonObject['object']['likes']['items'] = []
        for likeItem in postJsonObject['object']['likes']['items']:
            if likeItem.get('actor'):
                if likeItem['actor'] == actor:
                    # already liked
                    return
        newLike = {
            'type': 'Like',
            'actor': actor
        }
        postJsonObject['object']['likes']['items'].append(newLike)
        itlen = len(postJsonObject['object']['likes']['items'])
        postJsonObject['object']['likes']['totalItems'] = itlen

    if debug:
        print('DEBUG: saving post with likes added')
        pprint(postJsonObject)
    saveJson(postJsonObject, postFilename)


def undoAnnounceCollectionEntry(recentPostsCache: {},
                                baseDir: str, postFilename: str,
                                actor: str, domain: str, debug: bool) -> None:
    """Undoes an announce for a particular actor by removing it from
    the "shares" collection within a post. Note that the "shares"
    collection has no relation to shared items in shares.py. It's
    shares of posts, not shares of physical objects.
    """
    postJsonObject = loadJson(postFilename)
    if postJsonObject:
        # remove any cached version of this announce so that the announce
        # icon is changed
        nickname = getNicknameFromActor(actor)
        cachedPostFilename = getCachedPostFilename(baseDir, nickname, domain,
                                                   postJsonObject)
        if cachedPostFilename:
            if os.path.isfile(cachedPostFilename):
                os.remove(cachedPostFilename)
        removePostFromCache(postJsonObject, recentPostsCache)

        if not postJsonObject.get('type'):
            return
        if postJsonObject['type'] != 'Create':
            return
        if not postJsonObject.get('object'):
            if debug:
                pprint(postJsonObject)
                print('DEBUG: post has no object')
            return
        if not isinstance(postJsonObject['object'], dict):
            return
        if not postJsonObject['object'].get('shares'):
            return
        if not postJsonObject['object']['shares'].get('items'):
            return
        totalItems = 0
        if postJsonObject['object']['shares'].get('totalItems'):
            totalItems = postJsonObject['object']['shares']['totalItems']
        itemFound = False
        for announceItem in postJsonObject['object']['shares']['items']:
            if announceItem.get('actor'):
                if announceItem['actor'] == actor:
                    if debug:
                        print('DEBUG: Announce was removed for ' + actor)
                    anIt = announceItem
                    postJsonObject['object']['shares']['items'].remove(anIt)
                    itemFound = True
                    break
        if itemFound:
            if totalItems == 1:
                if debug:
                    print('DEBUG: shares (announcements) ' +
                          'was removed from post')
                del postJsonObject['object']['shares']
            else:
                itlen = len(postJsonObject['object']['shares']['items'])
                postJsonObject['object']['shares']['totalItems'] = itlen

            saveJson(postJsonObject, postFilename)


def updateAnnounceCollection(recentPostsCache: {},
                             baseDir: str, postFilename: str,
                             actor: str, domain: str, debug: bool) -> None:
    """Updates the announcements collection within a post
    Confusingly this is known as "shares", but isn't the
    same as shared items within shares.py
    It's shares of posts, not shares of physical objects.
    """
    postJsonObject = loadJson(postFilename)
    if postJsonObject:
        # remove any cached version of this announce so that the announce
        # icon is changed
        nickname = getNicknameFromActor(actor)
        cachedPostFilename = getCachedPostFilename(baseDir, nickname, domain,
                                                   postJsonObject)
        if cachedPostFilename:
            if os.path.isfile(cachedPostFilename):
                os.remove(cachedPostFilename)
        removePostFromCache(postJsonObject, recentPostsCache)

        if not postJsonObject.get('object'):
            if debug:
                pprint(postJsonObject)
                print('DEBUG: post ' + postFilename + ' has no object')
            return
        if not isinstance(postJsonObject['object'], dict):
            return
        postUrl = removeIdEnding(postJsonObject['id']) + '/shares'
        if not postJsonObject['object'].get('shares'):
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
            postJsonObject['object']['shares'] = announcementsJson
        else:
            if postJsonObject['object']['shares'].get('items'):
                sharesItems = postJsonObject['object']['shares']['items']
                for announceItem in sharesItems:
                    if announceItem.get('actor'):
                        if announceItem['actor'] == actor:
                            return
                newAnnounce = {
                    'type': 'Announce',
                    'actor': actor
                }
                postJsonObject['object']['shares']['items'].append(newAnnounce)
                itlen = len(postJsonObject['object']['shares']['items'])
                postJsonObject['object']['shares']['totalItems'] = itlen
            else:
                if debug:
                    print('DEBUG: shares (announcements) section of post ' +
                          'has no items list')

        if debug:
            print('DEBUG: saving post with shares (announcements) added')
            pprint(postJsonObject)
        saveJson(postJsonObject, postFilename)


def siteIsActive(url: str) -> bool:
    """Returns true if the current url is resolvable.
    This can be used to check that an instance is online before
    trying to send posts to it.
    """
    if not url.startswith('http'):
        return False
    if '.onion/' in url or '.i2p/' in url or \
       url.endswith('.onion') or \
       url.endswith('.i2p'):
        # skip this check for onion and i2p
        return True
    try:
        req = urllib.request.Request(url)
        urllib.request.urlopen(req, timeout=10)  # nosec
        return True
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during siteIsActive')
    return False


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
        'mp3': 'audio/mpeg',
        'ogg': 'audio/ogg',
        'mp4': 'video/mp4',
        'ogv': 'video/ogv'
    }
    fileExt = filename.split('.')[-1]
    if not extensions.get(fileExt):
        return 'image/png'
    return extensions[fileExt]
