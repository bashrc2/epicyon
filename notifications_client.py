__filename__ = "notifications_client.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import html
import time
import sys
import select
import webbrowser
from pathlib import Path
from random import randint
from utils import getStatusNumber
from utils import loadJson
from utils import saveJson
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import getFullDomain
from utils import isPGPEncrypted
from session import createSession
from speaker import getSpeakerFromServer
from speaker import getSpeakerPitch
from speaker import getSpeakerRate
from speaker import getSpeakerRange
from like import sendLikeViaServer
from like import sendUndoLikeViaServer
from follow import sendFollowRequestViaServer
from follow import sendUnfollowRequestViaServer
from posts import sendPostViaServer
from announce import sendAnnounceViaServer
from pgp import pgpDecrypt
from pgp import hasLocalPGPkey
from pgp import pgpEncryptToActor


def _clearScreen() -> None:
    """Clears the screen
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def _showDesktopBanner() -> None:
    """Shows the banner at the top
    """
    bannerFilename = 'banner.txt'
    if not os.path.isfile(bannerFilename):
        bannerTheme = 'starlight'
        bannerFilename = 'theme/' + bannerTheme + '/banner.txt'
        if not os.path.isfile(bannerFilename):
            return
    with open(bannerFilename, 'r') as bannerFile:
        banner = bannerFile.read()
        if banner:
            print(banner + '\n')


def _waitForKeypress(timeout: int, debug: bool) -> str:
    """Waits for a keypress with a timeout
    Returns the key pressed, or None on timeout
    """
    i, o, e = select.select([sys.stdin], [], [], timeout)

    if (i):
        text = sys.stdin.readline().strip()
        if debug:
            print("Text entered: " + text)
        return text
    else:
        if debug:
            print("Timeout")
        return None


def _speakerEspeak(espeak, pitch: int, rate: int, srange: int,
                   sayText: str) -> None:
    """Speaks the given text with espeak
    """
    espeak.set_parameter(espeak.Parameter.Pitch, pitch)
    espeak.set_parameter(espeak.Parameter.Rate, rate)
    espeak.set_parameter(espeak.Parameter.Range, srange)
    espeak.synth(html.unescape(sayText))


def _speakerPicospeaker(pitch: int, rate: int, systemLanguage: str,
                        sayText: str) -> None:
    speakerLang = 'en-GB'
    if systemLanguage:
        if systemLanguage.startswith('fr'):
            speakerLang = 'fr-FR'
        elif systemLanguage.startswith('es'):
            speakerLang = 'es-ES'
        elif systemLanguage.startswith('de'):
            speakerLang = 'de-DE'
        elif systemLanguage.startswith('it'):
            speakerLang = 'it-IT'
    speakerCmd = 'picospeaker ' + \
        '-l ' + speakerLang + \
        ' -r ' + str(rate) + \
        ' -p ' + str(pitch) + ' "' + \
        html.unescape(sayText) + '" 2> /dev/null'
    os.system(speakerCmd)


def _playNotificationSound(soundFilename: str, player='ffplay') -> None:
    """Plays a sound
    """
    if not os.path.isfile(soundFilename):
        return

    if player == 'ffplay':
        os.system('ffplay ' + soundFilename +
                  ' -autoexit -hide_banner -nodisp 2> /dev/null')


def _desktopNotification(notificationType: str,
                         title: str, message: str) -> None:
    """Shows a desktop notification
    """
    if not notificationType:
        return

    if notificationType == 'notify-send':
        # Ubuntu
        os.system('notify-send "' + title + '" "' + message + '"')
    elif notificationType == 'zenity':
        # Zenity
        os.system('zenity --notification --title "' + title +
                  '" --text="' + message + '"')
    elif notificationType == 'osascript':
        # Mac
        os.system("osascript -e 'display notification \"" +
                  message + "\" with title \"" + title + "\"'")
    elif notificationType == 'New-BurntToastNotification':
        # Windows
        os.system("New-BurntToastNotification -Text \"" +
                  title + "\", '" + message + "'")


def _textToSpeech(sayStr: str, screenreader: str,
                  pitch: int, rate: int, srange: int,
                  systemLanguage: str, espeak=None) -> None:
    """Say something via TTS
    """
    # speak the post content
    if screenreader == 'espeak':
        _speakerEspeak(espeak, pitch, rate, srange, sayStr)
    elif screenreader == 'picospeaker':
        _speakerPicospeaker(pitch, rate,
                            systemLanguage, sayStr)


def _sayCommand(content: str, sayStr: str, screenreader: str,
                systemLanguage: str,
                espeak=None,
                speakerName='screen reader',
                speakerGender='They/Them') -> None:
    """Speaks a command
    """
    print(content)
    if not screenreader:
        return

    pitch = getSpeakerPitch(speakerName,
                            screenreader, speakerGender)
    rate = getSpeakerRate(speakerName, screenreader)
    srange = getSpeakerRange(speakerName)

    _textToSpeech(sayStr, screenreader,
                  pitch, rate, srange,
                  systemLanguage, espeak)


def _notificationReplyToPost(session, postId: str,
                             baseDir: str, nickname: str, password: str,
                             domain: str, port: int, httpPrefix: str,
                             cachedWebfingers: {}, personCache: {},
                             debug: bool, subject: str,
                             screenreader: str, systemLanguage: str,
                             espeak) -> None:
    """Use the notification client to send a reply to the most recent post
    """
    if '://' not in postId:
        return
    toNickname = getNicknameFromActor(postId)
    toDomain, toPort = getDomainFromActor(postId)
    sayStr = 'Replying to ' + toNickname + '@' + toDomain
    _sayCommand(sayStr, sayStr,
                screenreader, systemLanguage, espeak)
    sayStr = 'Type your reply message, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    replyMessage = input()
    if not replyMessage:
        sayStr = 'No reply was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    replyMessage = replyMessage.strip()
    if not replyMessage:
        sayStr = 'No reply was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    sayStr = 'You entered this reply:'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    _sayCommand(replyMessage, replyMessage, screenreader,
                systemLanguage, espeak)
    sayStr = 'Send this reply, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning reply'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    ccUrl = None
    followersOnly = False
    attach = None
    mediaType = None
    attachedImageDescription = None
    isArticle = False
    subject = None
    commentsEnabled = True
    sayStr = 'Sending reply'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    if sendPostViaServer(__version__,
                         baseDir, session, nickname, password,
                         domain, port,
                         toNickname, toDomain, toPort, ccUrl,
                         httpPrefix, replyMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription,
                         cachedWebfingers, personCache, isArticle,
                         debug, postId, postId, subject) == 0:
        sayStr = 'Reply sent'
    else:
        sayStr = 'Reply failed'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)


def _notificationNewPost(session,
                         baseDir: str, nickname: str, password: str,
                         domain: str, port: int, httpPrefix: str,
                         cachedWebfingers: {}, personCache: {},
                         debug: bool,
                         screenreader: str, systemLanguage: str,
                         espeak) -> None:
    """Use the notification client to create a new post
    """
    sayStr = 'Create new post'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    sayStr = 'Type your post, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    newMessage = input()
    if not newMessage:
        sayStr = 'No post was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    newMessage = newMessage.strip()
    if not newMessage:
        sayStr = 'No post was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    sayStr = 'You entered this public post:'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    _sayCommand(newMessage, newMessage, screenreader, systemLanguage, espeak)
    sayStr = 'Send this post, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning new post'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    ccUrl = None
    followersOnly = False
    attach = None
    mediaType = None
    attachedImageDescription = None
    isArticle = False
    subject = None
    commentsEnabled = True
    subject = None
    sayStr = 'Sending'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    if sendPostViaServer(__version__,
                         baseDir, session, nickname, password,
                         domain, port,
                         None, '#Public', port, ccUrl,
                         httpPrefix, newMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription,
                         cachedWebfingers, personCache, isArticle,
                         debug, None, None, subject) == 0:
        sayStr = 'Post sent'
    else:
        sayStr = 'Post failed'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)


def _getSpeakerJsonFromIndex(boxName: str, index: int) -> {}:
    """Returns the json for the given post index
    """
    homeDir = str(Path.home())
    if not os.path.isdir(homeDir + '/.config'):
        os.mkdir(homeDir + '/.config')
    if not os.path.isdir(homeDir + '/.config/epicyon'):
        os.mkdir(homeDir + '/.config/epicyon')
    msgDir = homeDir + '/.config/epicyon/' + boxName
    if not os.path.isdir(msgDir):
        os.mkdir(msgDir)
    indexList = []
    for subdir, dirs, files in os.walk(msgDir):
        for f in files:
            if not f.endswith('.json'):
                continue
            indexList.append(f)
    indexList.sort(reverse=True)

    index -= 1
    if index <= 0:
        index = 0
    if len(indexList) <= index:
        return None

    publishedYear = indexList[index].split('-')[0]
    publishedMonth = indexList[index].split('-')[1]
    speakerJsonFilename = \
        os.path.join(msgDir,
                     publishedYear + '/' +
                     publishedMonth + '/' +
                     indexList[index])
    if not os.path.isfile(speakerJsonFilename):
        return None
    return loadJson(speakerJsonFilename)


def _readLocalBoxPost(boxName: str, index: int,
                      systemLanguage: str,
                      screenreader: str, espeak) -> {}:
    """Reads a post from the given timeline
    Returns the speaker json
    """
    speakerJson = _getSpeakerJsonFromIndex(boxName, index)
    if not speakerJson:
        return

    nameStr = speakerJson['name']
    gender = 'They/Them'
    if speakerJson.get('gender'):
        gender = speakerJson['gender']

    # append image description if needed
    if not speakerJson.get('imageDescription'):
        messageStr = speakerJson['say']
    else:
        messageStr = speakerJson['say'] + '. ' + \
            speakerJson['imageDescription']

    content = messageStr
    if speakerJson.get('content'):
        content = speakerJson['content']

    sayStr = 'Reading ' + boxName + ' post ' + str(index) + '.'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)

    time.sleep(2)

    # say the speaker's name
    _sayCommand(nameStr, nameStr, screenreader,
                systemLanguage, espeak,
                nameStr, gender)

    time.sleep(2)

    # speak the post content
    _sayCommand(content, messageStr, screenreader,
                systemLanguage, espeak,
                nameStr, gender)
    return speakerJson


def _showLocalBox(notifyJson: {}, boxName: str,
                  screenreader: str, systemLanguage: str, espeak,
                  startPostIndex=0, noOfPosts=10) -> None:
    """Shows locally stored posts for a given subdirectory
    """
    indent = '   '
    homeDir = str(Path.home())
    if not os.path.isdir(homeDir + '/.config'):
        os.mkdir(homeDir + '/.config')
    if not os.path.isdir(homeDir + '/.config/epicyon'):
        os.mkdir(homeDir + '/.config/epicyon')
    msgDir = homeDir + '/.config/epicyon/' + boxName
    if not os.path.isdir(msgDir):
        os.mkdir(msgDir)
    index = []
    for subdir, dirs, files in os.walk(msgDir):
        for f in files:
            if not f.endswith('.json'):
                continue
            index.append(f)
    if not index:
        sayStr = 'You have no ' + boxName + ' posts yet.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        print('')
        return

    # title
    _clearScreen()
    _showDesktopBanner()
    notificationIcons = ''
    if notifyJson:
        if notifyJson.get('followRequests'):
            notificationIcons += ' 👤'
        if notifyJson.get('dm'):
            notificationIcons += ' 📩'
        if notifyJson.get('reply'):
            notificationIcons += ' 📨'
        if notifyJson.get('calendar'):
            notificationIcons += ' 📅'
        if notifyJson.get('share'):
            notificationIcons += ' 🤝'
        if notifyJson.get('likedBy'):
            if '##sent##' not in notifyJson['likedBy']:
                notificationIcons += ' ❤'
    titleStr = boxName.upper()
    if notificationIcons:
        while len(titleStr) < 89 - len(notificationIcons):
            titleStr += ' '
        titleStr += notificationIcons
    print(indent + titleStr + '\n')

    maxPostIndex = len(index)
    index.sort(reverse=True)
    ctr = 0
    for pos in range(startPostIndex, startPostIndex + noOfPosts):
        if pos >= maxPostIndex:
            break
        publishedYear = index[pos].split('-')[0]
        publishedMonth = index[pos].split('-')[1]
        speakerJsonFilename = \
            os.path.join(msgDir,
                         publishedYear + '/' +
                         publishedMonth + '/' + index[pos])
        if not os.path.isfile(speakerJsonFilename):
            continue
        speakerJson = loadJson(speakerJsonFilename)
        if not speakerJson.get('published'):
            continue
        published = speakerJson['published'].replace('T', ' ')
        posStr = str(pos + 1) + '.'
        while len(posStr) < 3:
            posStr += ' '
        if speakerJson.get('name'):
            name = speakerJson['name']
        else:
            name = ''
        name = (name[:14]) if len(name) > 14 else name
        while len(name) < 16:
            name += ' '
        content = speakerJson['content']
        if speakerJson.get('detectedLinks'):
            if len(speakerJson['detectedLinks']) > 0:
                content = '🔗' + content
        content = (content[:38]) if len(content) > 38 else content
        while len(content) < 40:
            content += ' '
        print(indent + str(posStr) + ' | ' + str(name) + ' | ' +
              str(published) + ' | ' + str(content) + ' |')
        ctr += 1

    print('')

    sayStr = indent + boxName + ' posts ' + str(startPostIndex + 1) + \
        ' to ' + str(startPostIndex + ctr) + '. '
    sayStr += 'Use the next and prev commands to navigate.'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)

    print('')


def _notificationNewDM(session, toHandle: str,
                       baseDir: str, nickname: str, password: str,
                       domain: str, port: int, httpPrefix: str,
                       cachedWebfingers: {}, personCache: {},
                       debug: bool,
                       screenreader: str, systemLanguage: str,
                       espeak) -> None:
    """Use the notification client to create a new direct message
    which can include multiple destination handles
    """
    if ' ' in toHandle:
        handlesList = toHandle.split(' ')
    elif ',' in toHandle:
        handlesList = toHandle.split(',')
    elif ';' in toHandle:
        handlesList = toHandle.split(';')
    else:
        handlesList = [toHandle]

    for handle in handlesList:
        handle = handle.strip()
        _notificationNewDMbase(session, handle,
                               baseDir, nickname, password,
                               domain, port, httpPrefix,
                               cachedWebfingers, personCache,
                               debug,
                               screenreader, systemLanguage,
                               espeak)


def _storeMessage(speakerJson: {}, boxName: str) -> None:
    """Stores a message in your home directory for later reading
    """
    if not speakerJson.get('published'):
        return
    homeDir = str(Path.home())
    if not os.path.isdir(homeDir + '/.config'):
        os.mkdir(homeDir + '/.config')
    if not os.path.isdir(homeDir + '/.config/epicyon'):
        os.mkdir(homeDir + '/.config/epicyon')
    msgDir = homeDir + '/.config/epicyon/' + boxName
    if not os.path.isdir(msgDir):
        os.mkdir(msgDir)
    publishedYear = speakerJson['published'].split('-')[0]
    yearDir = msgDir + '/' + publishedYear
    if not os.path.isdir(yearDir):
        os.mkdir(yearDir)
    publishedMonth = speakerJson['published'].split('-')[1]
    monthDir = yearDir + '/' + publishedMonth
    if not os.path.isdir(monthDir):
        os.mkdir(monthDir)

    msgFilename = monthDir + '/' + speakerJson['published'] + '.json'
    saveJson(speakerJson, msgFilename)


def _notificationNewDMbase(session, toHandle: str,
                           baseDir: str, nickname: str, password: str,
                           domain: str, port: int, httpPrefix: str,
                           cachedWebfingers: {}, personCache: {},
                           debug: bool,
                           screenreader: str, systemLanguage: str,
                           espeak) -> None:
    """Use the notification client to create a new direct message
    """
    toPort = port
    if '://' in toHandle:
        toNickname = getNicknameFromActor(toHandle)
        toDomain, toPort = getDomainFromActor(toHandle)
        toHandle = toNickname + '@' + toDomain
    else:
        if toHandle.startswith('@'):
            toHandle = toHandle[1:]
        toNickname = toHandle.split('@')[0]
        toDomain = toHandle.split('@')[1]

    sayStr = 'Create new direct message to ' + toHandle
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    sayStr = 'Type your direct message, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    newMessage = input()
    if not newMessage:
        sayStr = 'No direct message was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    newMessage = newMessage.strip()
    if not newMessage:
        sayStr = 'No direct message was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    sayStr = 'You entered this direct message to ' + toHandle + ':'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    _sayCommand(newMessage, newMessage, screenreader, systemLanguage, espeak)
    ccUrl = None
    followersOnly = False
    attach = None
    mediaType = None
    attachedImageDescription = None
    isArticle = False
    subject = None
    commentsEnabled = True
    subject = None

    # if there is a local PGP key then attempt to encrypt the DM
    # using the PGP public key of the recipient
    newMessageOriginal = newMessage
    if hasLocalPGPkey():
        sayStr = \
            'Local PGP key detected...' + \
            'Fetching PGP public key for ' + toHandle
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        paddedMessage = newMessage
        if len(paddedMessage) < 32:
            # add some padding before and after
            # This is to guard against cribs based on small messages, like "Hi"
            for before in range(randint(1, 16)):
                paddedMessage = ' ' + paddedMessage
            for after in range(randint(1, 16)):
                paddedMessage += ' '
        cipherText = \
            pgpEncryptToActor(paddedMessage, toHandle)
        if not cipherText:
            sayStr = \
                toHandle + ' has no PGP public key. ' + \
                'Your message will be sent in clear text'
            _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        else:
            newMessage = cipherText
            sayStr = 'Message encrypted'
            _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)

    sayStr = 'Send this direct message, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning new direct message'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return

    sayStr = 'Sending'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    if sendPostViaServer(__version__,
                         baseDir, session, nickname, password,
                         domain, port,
                         toNickname, toDomain, toPort, ccUrl,
                         httpPrefix, newMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription,
                         cachedWebfingers, personCache, isArticle,
                         debug, None, None, subject) == 0:
        # store the DM locally
        statusNumber, published = getStatusNumber()
        postId = \
            httpPrefix + '://' + getFullDomain(domain, port) + \
            '/users/' + nickname + '/statuses/' + statusNumber
        speakerJson = {
            "name": nickname,
            "summary": "",
            "content": newMessageOriginal,
            "say": newMessageOriginal,
            "published": published,
            "imageDescription": "",
            "detectedLinks": [],
            "id": postId,
            "direct": True
        }
        _storeMessage(speakerJson, 'sent')
        sayStr = 'Direct message sent'
    else:
        sayStr = 'Direct message failed'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)


def runNotificationsClient(baseDir: str, proxyType: str, httpPrefix: str,
                           nickname: str, domain: str, port: int,
                           password: str, screenreader: str,
                           systemLanguage: str,
                           notificationSounds: bool,
                           notificationType: str,
                           noKeyPress: bool,
                           storeInboxPosts: bool,
                           showNewPosts: bool,
                           debug: bool) -> None:
    """Runs the notifications and screen reader client,
    which announces new inbox items
    """
    indent = '   '
    if showNewPosts:
        indent = ''

    _clearScreen()
    _showDesktopBanner()

    espeak = None
    if screenreader:
        if screenreader == 'espeak':
            print('Setting up espeak')
            from espeak import espeak
        elif screenreader != 'picospeaker':
            print(screenreader + ' is not a supported TTS system')
            return

        sayStr = indent + 'Running ' + screenreader + ' for ' + \
            nickname + '@' + domain
        _sayCommand(sayStr, sayStr, screenreader,
                    systemLanguage, espeak)
    else:
        print(indent + 'Running desktop notifications for ' +
              nickname + '@' + domain)
    if notificationSounds:
        sayStr = indent + 'Notification sounds on'
    else:
        sayStr = indent + 'Notification sounds off'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)
    sayStr = indent + '/q or /quit to exit'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)

    currTimeline = ''
    currInboxIndex = 0
    if not showNewPosts:
        print('')
        currInboxIndex = 0
        _showLocalBox(None, 'inbox',
                      screenreader, systemLanguage, espeak,
                      currInboxIndex, 10)
        currTimeline = 'inbox'
    print('')
    keyPress = _waitForKeypress(2, debug)

    originalScreenReader = screenreader
    domainFull = getFullDomain(domain, port)
    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    prevSay = ''
    prevDM = False
    prevReply = False
    prevCalendar = False
    prevFollow = False
    prevLike = ''
    prevShare = False
    dmSoundFilename = 'dm.ogg'
    replySoundFilename = 'reply.ogg'
    calendarSoundFilename = 'calendar.ogg'
    followSoundFilename = 'follow.ogg'
    likeSoundFilename = 'like.ogg'
    shareSoundFilename = 'share.ogg'
    player = 'ffplay'
    nameStr = None
    gender = None
    messageStr = None
    content = None
    cachedWebfingers = {}
    personCache = {}
    currDMIndex = 0
    currSentIndex = 0
    while (1):
        session = createSession(proxyType)
        notifyJson = None
        speakerJson = \
            getSpeakerFromServer(baseDir, session, nickname, password,
                                 domain, port, httpPrefix, True, __version__)
        if speakerJson:
            if speakerJson.get('notify'):
                notifyJson = speakerJson['notify']
                title = 'Epicyon'
                if speakerJson['notify'].get('title'):
                    title = speakerJson['notify']['title']
                soundsDir = 'theme/default/sounds'
                if speakerJson['notify'].get('theme'):
                    if isinstance(speakerJson['notify']['theme'], str):
                        soundsDir = \
                            'theme/' + \
                            speakerJson['notify']['theme'] + '/sounds'
                        if not os.path.isdir(soundsDir):
                            soundsDir = 'theme/default/sounds'
                if speakerJson['notify']['dm'] != prevDM:
                    if speakerJson['notify']['dm'] is True:
                        if notificationSounds:
                            _playNotificationSound(soundsDir + '/' +
                                                   dmSoundFilename, player)
                        _desktopNotification(notificationType, title,
                                             'New direct message ' +
                                             actor + '/dm')
                    prevDM = speakerJson['notify']['dm']
                elif speakerJson['notify']['reply'] != prevReply:
                    if speakerJson['notify']['reply'] is True:
                        if notificationSounds:
                            _playNotificationSound(soundsDir + '/' +
                                                   replySoundFilename,
                                                   player)
                        _desktopNotification(notificationType, title,
                                             'New reply ' +
                                             actor + '/tlreplies')
                        prevReply = speakerJson['notify']['reply']
                elif speakerJson['notify']['calendar'] != prevCalendar:
                    if speakerJson['notify']['calendar'] is True:
                        if notificationSounds:
                            _playNotificationSound(soundsDir + '/' +
                                                   calendarSoundFilename,
                                                   player)
                        _desktopNotification(notificationType, title,
                                             'New calendar event ' +
                                             actor + '/calendar')
                    prevCalendar = speakerJson['notify']['calendar']
                elif speakerJson['notify']['followRequests'] != prevFollow:
                    if speakerJson['notify']['followRequests'] is True:
                        if notificationSounds:
                            _playNotificationSound(soundsDir + '/' +
                                                   followSoundFilename,
                                                   player)
                        _desktopNotification(notificationType, title,
                                             'New follow request ' +
                                             actor + '/followers#buttonheader')
                    prevFollow = speakerJson['notify']['followRequests']
                elif speakerJson['notify']['likedBy'] != prevLike:
                    if '##sent##' not in speakerJson['notify']['likedBy']:
                        if notificationSounds:
                            _playNotificationSound(soundsDir + '/' +
                                                   likeSoundFilename, player)
                        _desktopNotification(notificationType, title,
                                             'New like ' +
                                             speakerJson['notify']['likedBy'])
                    prevLike = speakerJson['notify']['likedBy']
                elif speakerJson['notify']['share'] != prevShare:
                    if speakerJson['notify']['share'] is True:
                        if notificationSounds:
                            _playNotificationSound(soundsDir + '/' +
                                                   shareSoundFilename,
                                                   player)
                        _desktopNotification(notificationType, title,
                                             'New shared item ' +
                                             actor + '/shares')
                    prevShare = speakerJson['notify']['share']

            if speakerJson.get('say'):
                if speakerJson['say'] != prevSay:
                    if speakerJson.get('name'):
                        nameStr = speakerJson['name']
                        gender = 'They/Them'
                        if speakerJson.get('gender'):
                            gender = speakerJson['gender']

                        # append image description if needed
                        if not speakerJson.get('imageDescription'):
                            messageStr = speakerJson['say']
                        else:
                            messageStr = speakerJson['say'] + '. ' + \
                                speakerJson['imageDescription']
                        encryptedMessage = False
                        if speakerJson.get('id') and \
                           isPGPEncrypted(messageStr):
                            encryptedMessage = True
                            messageStr = pgpDecrypt(messageStr,
                                                    speakerJson['id'])

                        content = messageStr
                        if speakerJson.get('content'):
                            if not encryptedMessage:
                                content = speakerJson['content']
                            else:
                                content = '🔓 ' + messageStr

                        if showNewPosts:
                            # say the speaker's name
                            _sayCommand(nameStr, nameStr, screenreader,
                                        systemLanguage, espeak,
                                        nameStr, gender)

                            time.sleep(2)

                            # speak the post content
                            _sayCommand(content, messageStr, screenreader,
                                        systemLanguage, espeak,
                                        nameStr, gender)

                        # store incoming post
                        if encryptedMessage:
                            speakerJson['content'] = content
                            speakerJson['say'] = messageStr
                            speakerJson['decrypted'] = True
                            _storeMessage(speakerJson, 'dm')
                        elif speakerJson.get('direct'):
                            speakerJson['decrypted'] = False
                            _storeMessage(speakerJson, 'dm')
                        else:
                            speakerJson['decrypted'] = False
                            if storeInboxPosts:
                                _storeMessage(speakerJson, 'inbox')

                        if not showNewPosts:
                            _clearScreen()
                            _showLocalBox(notifyJson, currTimeline,
                                          None, systemLanguage, espeak,
                                          currInboxIndex, 10)
                        else:
                            print('')

                    prevSay = speakerJson['say']

        # wait for a while, or until a key is pressed
        if noKeyPress:
            time.sleep(10)
        else:
            keyPress = _waitForKeypress(30, debug)
        if keyPress:
            if keyPress.startswith('/'):
                keyPress = keyPress[1:]
            if keyPress == 'q' or keyPress == 'quit' or keyPress == 'exit':
                sayStr = 'Quit'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                if screenreader:
                    keyPress = _waitForKeypress(2, debug)
                break
            elif keyPress.startswith('show dm'):
                currDMIndex = 0
                _showLocalBox(notifyJson, 'dm',
                              screenreader, systemLanguage, espeak,
                              currDMIndex, 10)
                currTimeline = 'dm'
            elif keyPress.startswith('show sen'):
                currSentIndex = 0
                _showLocalBox(notifyJson, 'sent',
                              screenreader, systemLanguage, espeak,
                              currSentIndex, 10)
                currTimeline = 'sent'
            elif (keyPress == 'show' or keyPress.startswith('show in') or
                  keyPress == 'clear'):
                currInboxIndex = 0
                _showLocalBox(notifyJson, 'inbox',
                              screenreader, systemLanguage, espeak,
                              currInboxIndex, 10)
                currTimeline = 'inbox'
            elif keyPress.startswith('next'):
                if currTimeline == 'dm':
                    currDMIndex += 10
                    _showLocalBox(notifyJson, 'dm',
                                  screenreader, systemLanguage, espeak,
                                  currDMIndex, 10)
                elif currTimeline == 'sent':
                    currSentIndex += 10
                    _showLocalBox(notifyJson, 'sent',
                                  screenreader, systemLanguage, espeak,
                                  currSentIndex, 10)
                elif currTimeline == 'inbox':
                    currInboxIndex += 10
                    _showLocalBox(notifyJson, 'inbox',
                                  screenreader, systemLanguage, espeak,
                                  currInboxIndex, 10)
            elif keyPress.startswith('prev'):
                if currTimeline == 'dm':
                    currDMIndex -= 10
                    if currDMIndex < 0:
                        currDMIndex = 0
                    _showLocalBox(notifyJson, 'dm',
                                  screenreader, systemLanguage, espeak,
                                  currDMIndex, 10)
                elif currTimeline == 'sent':
                    currSentIndex -= 10
                    if currSentIndex < 0:
                        currSentIndex = 0
                    _showLocalBox(notifyJson, 'sent',
                                  screenreader, systemLanguage, espeak,
                                  currSentIndex, 10)
                elif currTimeline == 'inbox':
                    currInboxIndex -= 10
                    if currInboxIndex < 0:
                        currInboxIndex = 0
                    _showLocalBox(notifyJson, 'inbox',
                                  screenreader, systemLanguage, espeak,
                                  currInboxIndex, 10)
            elif keyPress.startswith('read '):
                postIndexStr = keyPress.split('read ')[1]
                if postIndexStr.isdigit():
                    postIndex = int(postIndexStr)
                    speakerJson = \
                        _readLocalBoxPost(currTimeline, postIndex,
                                          systemLanguage, screenreader,
                                          espeak)
                print('')
            elif keyPress == 'reply' or keyPress == 'r':
                if speakerJson.get('id'):
                    postId = speakerJson['id']
                    subject = None
                    if speakerJson.get('summary'):
                        subject = speakerJson['summary']
                    sessionReply = createSession(proxyType)
                    _notificationReplyToPost(sessionReply, postId,
                                             baseDir, nickname, password,
                                             domain, port, httpPrefix,
                                             cachedWebfingers, personCache,
                                             debug, subject,
                                             screenreader, systemLanguage,
                                             espeak)
                print('')
            elif (keyPress == 'post' or keyPress == 'p' or
                  keyPress == 'send' or
                  keyPress.startswith('dm ') or
                  keyPress.startswith('direct message ') or
                  keyPress.startswith('post ') or
                  keyPress.startswith('send ')):
                sessionPost = createSession(proxyType)
                if keyPress.startswith('dm ') or \
                   keyPress.startswith('direct message ') or \
                   keyPress.startswith('post ') or \
                   keyPress.startswith('send '):
                    keyPress = keyPress.replace(' to ', ' ')
                    keyPress = keyPress.replace(' dm ', ' ')
                    keyPress = keyPress.replace(' DM ', ' ')
                    # direct message
                    toHandle = None
                    if keyPress.startswith('post '):
                        toHandle = keyPress.split('post ', 1)[1]
                    elif keyPress.startswith('send '):
                        toHandle = keyPress.split('send ', 1)[1]
                    elif keyPress.startswith('dm '):
                        toHandle = keyPress.split('dm ', 1)[1]
                    elif keyPress.startswith('direct message '):
                        toHandle = keyPress.split('direct message ', 1)[1]
                    if toHandle:
                        _notificationNewDM(sessionPost, toHandle,
                                           baseDir, nickname, password,
                                           domain, port, httpPrefix,
                                           cachedWebfingers, personCache,
                                           debug,
                                           screenreader, systemLanguage,
                                           espeak)
                else:
                    # public post
                    _notificationNewPost(sessionPost,
                                         baseDir, nickname, password,
                                         domain, port, httpPrefix,
                                         cachedWebfingers, personCache,
                                         debug,
                                         screenreader, systemLanguage,
                                         espeak)
                print('')
            elif keyPress == 'like':
                if speakerJson.get('id'):
                    sayStr = 'Liking post by ' + speakerJson['name']
                    _sayCommand(sayStr, sayStr,
                                screenreader,
                                systemLanguage, espeak)
                    sessionLike = createSession(proxyType)
                    sendLikeViaServer(baseDir, sessionLike,
                                      nickname, password,
                                      domain, port,
                                      httpPrefix, speakerJson['id'],
                                      cachedWebfingers, personCache,
                                      False, __version__)
                    print('')
            elif keyPress == 'unlike' or keyPress == 'undo like':
                if speakerJson.get('id'):
                    sayStr = 'Undoing like of post by ' + speakerJson['name']
                    _sayCommand(sayStr, sayStr,
                                screenreader,
                                systemLanguage, espeak)
                    sessionUnlike = createSession(proxyType)
                    sendUndoLikeViaServer(baseDir, sessionUnlike,
                                          nickname, password,
                                          domain, port,
                                          httpPrefix, speakerJson['id'],
                                          cachedWebfingers, personCache,
                                          False, __version__)
                    print('')
            elif (keyPress == 'announce' or
                  keyPress == 'boost' or
                  keyPress == 'retweet'):
                if speakerJson.get('id'):
                    postId = speakerJson['id']
                    sayStr = 'Announcing post by ' + speakerJson['name']
                    _sayCommand(sayStr, sayStr,
                                screenreader,
                                systemLanguage, espeak)
                    sessionAnnounce = createSession(proxyType)
                    sendAnnounceViaServer(baseDir, sessionAnnounce,
                                          nickname, password,
                                          domain, port,
                                          httpPrefix, postId,
                                          cachedWebfingers, personCache,
                                          True, __version__)
                    print('')
            elif keyPress.startswith('follow '):
                followHandle = keyPress.replace('follow ', '').strip()
                if followHandle.startswith('@'):
                    followHandle = followHandle[1:]
                if '@' in followHandle or '://' in followHandle:
                    followNickname = getNicknameFromActor(followHandle)
                    followDomain, followPort = \
                        getDomainFromActor(followHandle)
                    if followNickname and followDomain:
                        sayStr = 'Sending follow request to ' + \
                            followNickname + '@' + followDomain
                        _sayCommand(sayStr, sayStr,
                                    screenreader, systemLanguage, espeak)
                        sessionFollow = createSession(proxyType)
                        sendFollowRequestViaServer(baseDir, sessionFollow,
                                                   nickname, password,
                                                   domain, port,
                                                   followNickname,
                                                   followDomain,
                                                   followPort,
                                                   httpPrefix,
                                                   cachedWebfingers,
                                                   personCache,
                                                   debug, __version__)
                    else:
                        sayStr = followHandle + ' is not valid'
                        _sayCommand(sayStr,
                                    screenreader, systemLanguage, espeak)
                    print('')
            elif (keyPress.startswith('unfollow ') or
                  keyPress.startswith('stop following ')):
                followHandle = keyPress.replace('unfollow ', '').strip()
                followHandle = followHandle.replace('stop following ', '')
                if followHandle.startswith('@'):
                    followHandle = followHandle[1:]
                if '@' in followHandle or '://' in followHandle:
                    followNickname = getNicknameFromActor(followHandle)
                    followDomain, followPort = \
                        getDomainFromActor(followHandle)
                    if followNickname and followDomain:
                        sayStr = 'Stop following ' + \
                            followNickname + '@' + followDomain
                        _sayCommand(sayStr, sayStr,
                                    screenreader, systemLanguage, espeak)
                        sessionUnfollow = createSession(proxyType)
                        sendUnfollowRequestViaServer(baseDir, sessionUnfollow,
                                                     nickname, password,
                                                     domain, port,
                                                     followNickname,
                                                     followDomain,
                                                     followPort,
                                                     httpPrefix,
                                                     cachedWebfingers,
                                                     personCache,
                                                     debug, __version__)
                    else:
                        sayStr = followHandle + ' is not valid'
                        _sayCommand(sayStr, sayStr,
                                    screenreader, systemLanguage, espeak)
                    print('')
            elif (keyPress == 'repeat' or keyPress == 'replay' or
                  keyPress == 'rp' or keyPress == 'again' or
                  keyPress == 'say again'):
                if screenreader and nameStr and \
                   gender and messageStr and content:
                    sayStr = 'Repeating ' + nameStr
                    _sayCommand(sayStr, sayStr, screenreader,
                                systemLanguage, espeak,
                                nameStr, gender)
                    time.sleep(2)
                    _sayCommand(content, messageStr, screenreader,
                                systemLanguage, espeak,
                                nameStr, gender)
                    print('')
            elif (keyPress == 'sounds on' or
                  keyPress == 'sound on' or
                  keyPress == 'sound'):
                sayStr = 'Notification sounds on'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                notificationSounds = True
            elif (keyPress == 'sounds off' or
                  keyPress == 'sound off' or
                  keyPress == 'nosound'):
                sayStr = 'Notification sounds off'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                notificationSounds = False
            elif (keyPress == 'speak' or
                  keyPress == 'screen reader on' or
                  keyPress == 'speaker on' or
                  keyPress == 'talker on' or
                  keyPress == 'reader on'):
                if originalScreenReader:
                    screenreader = originalScreenReader
                    sayStr = 'Screen reader on'
                    _sayCommand(sayStr, sayStr, screenreader,
                                systemLanguage, espeak)
                else:
                    print('No --screenreader option was specified')
            elif (keyPress == 'mute' or
                  keyPress == 'screen reader off' or
                  keyPress == 'speaker off' or
                  keyPress == 'talker off' or
                  keyPress == 'reader off'):
                if originalScreenReader:
                    screenreader = None
                    sayStr = 'Screen reader off'
                    _sayCommand(sayStr, sayStr, originalScreenReader,
                                systemLanguage, espeak)
                else:
                    print('No --screenreader option was specified')
            elif keyPress.startswith('open'):
                currIndex = 0
                if ' ' in keyPress:
                    postIndex = keyPress.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                speakerJson = \
                    _getSpeakerJsonFromIndex(currTimeline, currIndex)
                if not speakerJson:
                    speakerJson = {}
                linkOpened = False
                if speakerJson.get('detectedLinks'):
                    if len(speakerJson['detectedLinks']) > 0:
                        for url in speakerJson['detectedLinks']:
                            if '://' in url:
                                webbrowser.open(url)
                                linkOpened = True
                        if linkOpened:
                            sayStr = 'Opened web links'
                            _sayCommand(sayStr, sayStr, originalScreenReader,
                                        systemLanguage, espeak)
                if not linkOpened:
                    sayStr = 'There are no web links to open.'
                    _sayCommand(sayStr, sayStr, originalScreenReader,
                                systemLanguage, espeak)
                print('')
