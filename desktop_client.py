__filename__ = "desktop_client.py"
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
import urllib.parse
from pathlib import Path
from random import randint
from utils import loadTranslationsFromFile
from utils import removeHtml
from utils import getStatusNumber
from utils import loadJson
from utils import saveJson
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import getFullDomain
from utils import isPGPEncrypted
from session import createSession
from speaker import speakableText
from speaker import getSpeakerPitch
from speaker import getSpeakerRate
from speaker import getSpeakerRange
from like import sendLikeViaServer
from like import sendUndoLikeViaServer
from follow import sendFollowRequestViaServer
from follow import sendUnfollowRequestViaServer
from posts import sendPostViaServer
from posts import c2sBoxJson
from announce import sendAnnounceViaServer
from pgp import pgpDecrypt
from pgp import hasLocalPGPkey
from pgp import pgpEncryptToActor
from pgp import pgpPublicKeyUpload


def _desktopHelp() -> None:
    """Shows help
    """
    indent = '   '
    print('')
    print(indent + 'Commands:')
    print('')
    print(indent + 'quit                         ' +
          'Exit from the desktop client')
    print(indent + 'show dm|sent|inbox|replies   ' +
          'Show a timeline')
    print(indent + 'mute                         ' +
          'Turn off the screen reader')
    print(indent + 'speak                        ' +
          'Turn on the screen reader')
    print(indent + 'sounds on                    ' +
          'Turn on notification sounds')
    print(indent + 'sounds off                   ' +
          'Turn off notification sounds')
    print(indent + 'rp                           ' +
          'Repeat the last post')
    print(indent + 'like                         ' +
          'Like the last post')
    print(indent + 'unlike                       ' +
          'Unlike the last post')
    print(indent + 'reply                        ' +
          'Reply to the last post')
    print(indent + 'post                         ' +
          'Create a new post')
    print(indent + 'post to [handle]             ' +
          'Create a new direct message')
    print(indent + 'announce/boost               ' +
          'Boost the last post')
    print(indent + 'follow [handle]              ' +
          'Make a follow request')
    print(indent + 'unfollow [handle]            ' +
          'Stop following the give handle')
    print(indent + 'next                         ' +
          'Next page in the timeline')
    print(indent + 'prev                         ' +
          'Previous page in the timeline')
    print(indent + 'read [post number]           ' +
          'Read a post from a timeline')
    print(indent + 'open [post number]           ' +
          'Open web links within a timeline post')
    print('')


def _desktopClearScreen() -> None:
    """Clears the screen
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def _desktopShowBanner() -> None:
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


def _desktopWaitForCmd(timeout: int, debug: bool) -> str:
    """Waits for a command to be entered with a timeout
    Returns the command, or None on timeout
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
    """TTS using picospeaker
    """
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


def _desktopReplyToPost(session, postId: str,
                        baseDir: str, nickname: str, password: str,
                        domain: str, port: int, httpPrefix: str,
                        cachedWebfingers: {}, personCache: {},
                        debug: bool, subject: str,
                        screenreader: str, systemLanguage: str,
                        espeak) -> None:
    """Use the desktop client to send a reply to the most recent post
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


def _desktopNewPost(session,
                    baseDir: str, nickname: str, password: str,
                    domain: str, port: int, httpPrefix: str,
                    cachedWebfingers: {}, personCache: {},
                    debug: bool,
                    screenreader: str, systemLanguage: str,
                    espeak) -> None:
    """Use the desktop client to create a new post
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


def _safeMessage(content: str) -> str:
    """Removes anything potentially unsafe from a string
    """
    return content.replace('`', '').replace('$(', '$ (')


def _timelineIsEmpty(boxJson: {}) -> bool:
    """Returns true if the given timeline is empty
    """
    empty = False
    if not boxJson:
        empty = True
    else:
        if not isinstance(boxJson, dict):
            empty = True
        elif not boxJson.get('orderedItems'):
            empty = True
    return empty


def _getFirstItemId(boxJson: {}) -> str:
    """Returns the id of the first item in the timeline
    """
    if _timelineIsEmpty(boxJson):
        return
    if len(boxJson['orderedItems']) == 0:
        return
    return boxJson['orderedItems'][0]['id']


def _textOnlyContent(content: str) -> str:
    """Remove formatting from the given string
    """
    content = urllib.parse.unquote_plus(content)
    content = html.unescape(content)
    return removeHtml(content)


def _readLocalBoxPost(baseDir: str, boxName: str,
                      pageNumber: int, index: int, boxJson: {},
                      systemLanguage: str,
                      screenreader: str, espeak,
                      translate: {}) -> {}:
    """Reads a post from the given timeline
    Returns the speaker json
    """
    if _timelineIsEmpty(boxJson):
        return

    postJsonObject = _desktopGetBoxPostObject(boxJson, index)
    if not postJsonObject:
        return
    actor = postJsonObject['object']['attributedTo']
    nameStr = getNicknameFromActor(actor)
    gender = 'They/Them'

    content = _textOnlyContent(postJsonObject['object']['content'])
    sayStr = 'Reading ' + boxName + ' post ' + str(index) + \
        ' from page ' + str(pageNumber) + '.'
    sayStr2 = sayStr.replace(' dm ', ' DM ')
    _sayCommand(sayStr, sayStr2, screenreader, systemLanguage, espeak)

    if isPGPEncrypted(content):
        sayStr = 'Encrypted message. Please enter your passphrase.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        content = pgpDecrypt(content, actor)
        if isPGPEncrypted(content):
            sayStr = 'Message could not be decrypted'
            _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
            return

    content = _safeMessage(content)
    messageStr = speakableText(baseDir, content, translate)

    if screenreader:
        time.sleep(2)

    # say the speaker's name
    _sayCommand(nameStr, nameStr, screenreader,
                systemLanguage, espeak,
                nameStr, gender)

    if screenreader:
        time.sleep(2)

    # speak the post content
    _sayCommand(content, messageStr, screenreader,
                systemLanguage, espeak,
                nameStr, gender)
    return postJsonObject


def _desktopGetBoxPostObject(boxJson: {}, index: int) -> {}:
    """Gets the post with the given index from the timeline
    """
    ctr = 0
    for postJsonObject in boxJson['orderedItems']:
        if not postJsonObject.get('object'):
            continue
        if not isinstance(postJsonObject['object'], dict):
            continue
        if not postJsonObject['object'].get('published'):
            continue
        if not postJsonObject['object'].get('content'):
            continue
        ctr += 1
        if ctr == index:
            return postJsonObject
    return None


def _desktopShowBoxJson(boxName: str, boxJson: {},
                        screenreader: str, systemLanguage: str, espeak,
                        pageNumber=1,
                        newReplies=False,
                        newDMs=False) -> bool:
    """Shows online timeline
    """
    indent = '   '

    # title
    _desktopClearScreen()
    _desktopShowBanner()

    notificationIcons = ''
    titleStr = '\33[7m' + boxName.upper() + '\33[0m'
    # titleStr += ' page ' + str(pageNumber)
    if notificationIcons:
        while len(titleStr) < 95 - len(notificationIcons):
            titleStr += ' '
        titleStr += notificationIcons
    print(indent + titleStr + '\n')

    if _timelineIsEmpty(boxJson):
        boxStr = boxName
        if boxName == 'dm':
            boxStr = 'DM'
        sayStr = indent + 'You have no ' + boxStr + ' posts yet.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        print('')
        return False

    ctr = 1
    for postJsonObject in boxJson['orderedItems']:
        if not postJsonObject.get('object'):
            continue
        if not isinstance(postJsonObject['object'], dict):
            continue
        if not postJsonObject['object'].get('published'):
            continue
        if not postJsonObject['object'].get('content'):
            continue
        published = postJsonObject['published'].replace('T', ' ')
        posStr = str(ctr)
        while len(posStr) < 2:
            posStr += ' '
        authorActor = postJsonObject['object']['attributedTo']
        name = getNicknameFromActor(authorActor)
        if len(name) > 16:
            name = name[:16]
        else:
            while len(name) < 16:
                name += ' '
        content = _textOnlyContent(postJsonObject['object']['content'])
        if isPGPEncrypted(content):
            content = '🔒' + content
        elif '://' in content:
            content = '🔗' + content
        if len(content) > 40:
            content = content[:40]
        else:
            while len(content) < 40:
                content += ' '
        print(indent + str(posStr) + ' | ' + name + ' | ' +
              published + ' | ' + content)
        ctr += 1

    print('')

    # say the post number range
    sayStr = indent + boxName + ' page ' + str(pageNumber) + \
        ' containing ' + str(ctr - 1) + ' posts. '
    if newDMs and boxName != 'dm':
        sayStr += \
            'Use \33[3mshow dm\33[0m to view direct messages.'
    elif newReplies and boxName != 'replies':
        sayStr += \
            'Use \33[3mshow replies\33[0m to view reply posts.'
    else:
        sayStr += \
            'Use the \33[3mnext\33[0m and ' + \
            '\33[3mprev\33[0m commands to navigate.'
    sayStr2 = sayStr.replace('\33[3m', '').replace('\33[0m', '')
    sayStr2 = sayStr2.replace('show dm', 'show DM')
    sayStr2 = sayStr2.replace('dm post', 'Direct message post')
    _sayCommand(sayStr, sayStr2, screenreader, systemLanguage, espeak)
    print('')
    return True


def _desktopNewDM(session, toHandle: str,
                  baseDir: str, nickname: str, password: str,
                  domain: str, port: int, httpPrefix: str,
                  cachedWebfingers: {}, personCache: {},
                  debug: bool,
                  screenreader: str, systemLanguage: str,
                  espeak) -> None:
    """Use the desktop client to create a new direct message
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
        _desktopNewDMbase(session, handle,
                          baseDir, nickname, password,
                          domain, port, httpPrefix,
                          cachedWebfingers, personCache,
                          debug,
                          screenreader, systemLanguage,
                          espeak)


def _desktopStoreMsg(speakerJson: {}, boxName: str) -> None:
    """Stores a message in your home directory for later reading
    which could be offline
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


def _desktopNewDMbase(session, toHandle: str,
                      baseDir: str, nickname: str, password: str,
                      domain: str, port: int, httpPrefix: str,
                      cachedWebfingers: {}, personCache: {},
                      debug: bool,
                      screenreader: str, systemLanguage: str,
                      espeak) -> None:
    """Use the desktop client to create a new direct message
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
        _desktopStoreMsg(speakerJson, 'sent')
        sayStr = 'Direct message sent'
    else:
        sayStr = 'Direct message failed'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)


def runDesktopClient(baseDir: str, proxyType: str, httpPrefix: str,
                     nickname: str, domain: str, port: int,
                     password: str, screenreader: str,
                     systemLanguage: str,
                     notificationSounds: bool,
                     notificationType: str,
                     noKeyPress: bool,
                     storeInboxPosts: bool,
                     showNewPosts: bool,
                     language: str,
                     debug: bool) -> None:
    """Runs the desktop and screen reader client,
    which announces new inbox items
    """
    indent = '   '
    if showNewPosts:
        indent = ''

    _desktopClearScreen()
    _desktopShowBanner()

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

    currTimeline = 'inbox'
    pageNumber = 1

    postJsonObject = {}
    originalScreenReader = screenreader
    # domainFull = getFullDomain(domain, port)
    # actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    # prevSay = ''
    # prevCalendar = False
    # prevFollow = False
    # prevLike = ''
    # prevShare = False
    # dmSoundFilename = 'dm.ogg'
    # replySoundFilename = 'reply.ogg'
    # calendarSoundFilename = 'calendar.ogg'
    # followSoundFilename = 'follow.ogg'
    # likeSoundFilename = 'like.ogg'
    # shareSoundFilename = 'share.ogg'
    # player = 'ffplay'
    nameStr = None
    gender = None
    messageStr = None
    content = None
    cachedWebfingers = {}
    personCache = {}
    newRepliesExist = False
    newDMsExist = False
    pgpKeyUpload = False

    sayStr = indent + 'Loading translations file'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)
    translate, systemLanguage = \
        loadTranslationsFromFile(baseDir, language)

    sayStr = indent + 'Connecting...'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)
    session = createSession(proxyType)

    sayStr = indent + '/q or /quit to exit'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)
    prevTimelineFirstId = ''
    while (1):
        if not pgpKeyUpload:
            sayStr = indent + 'Uploading PGP public key'
            _sayCommand(sayStr, sayStr, screenreader,
                        systemLanguage, espeak)
            pgpPublicKeyUpload(baseDir, session,
                               nickname, password,
                               domain, port, httpPrefix,
                               cachedWebfingers, personCache,
                               debug, False)
            sayStr = indent + 'PGP public key uploaded'
            _sayCommand(sayStr, sayStr, screenreader,
                        systemLanguage, espeak)
            pgpKeyUpload = True

        boxJson = c2sBoxJson(baseDir, session,
                             nickname, password,
                             domain, port, httpPrefix,
                             currTimeline, pageNumber,
                             debug)

        if boxJson:
            timelineFirstId = _getFirstItemId(boxJson)
            if timelineFirstId != prevTimelineFirstId:
                _desktopClearScreen()
                _desktopShowBoxJson(currTimeline, boxJson,
                                    None, systemLanguage, espeak,
                                    pageNumber,
                                    newRepliesExist,
                                    newDMsExist)
            prevTimelineFirstId = timelineFirstId

        # wait for a while, or until a key is pressed
        if noKeyPress:
            time.sleep(10)
        else:
            commandStr = _desktopWaitForCmd(30, debug)
        if commandStr:
            if commandStr.startswith('/'):
                commandStr = commandStr[1:]
            if commandStr == 'q' or \
               commandStr == 'quit' or \
               commandStr == 'exit':
                sayStr = 'Quit'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                if screenreader:
                    commandStr = _desktopWaitForCmd(2, debug)
                break
            elif commandStr.startswith('show dm'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'dm'
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug)
                if boxJson:
                    _desktopShowBoxJson(currTimeline, boxJson,
                                        screenreader, systemLanguage, espeak,
                                        pageNumber,
                                        newRepliesExist, newDMsExist)
                newDMsExist = False
            elif commandStr.startswith('show rep'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'replies'
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug)
                if boxJson:
                    _desktopShowBoxJson(currTimeline, boxJson,
                                        screenreader, systemLanguage, espeak,
                                        pageNumber,
                                        newRepliesExist, newDMsExist)
                # Turn off the replies indicator
                newRepliesExist = False
            elif commandStr.startswith('show sen'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'outbox'
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug)
                if boxJson:
                    _desktopShowBoxJson(currTimeline, boxJson,
                                        screenreader, systemLanguage, espeak,
                                        pageNumber,
                                        newRepliesExist, newDMsExist)
            elif (commandStr == 'show' or commandStr.startswith('show in') or
                  commandStr == 'clear'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'inbox'
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug)
                if boxJson:
                    _desktopShowBoxJson(currTimeline, boxJson,
                                        screenreader, systemLanguage, espeak,
                                        pageNumber,
                                        newRepliesExist, newDMsExist)
            elif commandStr.startswith('next'):
                pageNumber += 1
                prevTimelineFirstId = ''
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug)
                if boxJson:
                    _desktopShowBoxJson(currTimeline, boxJson,
                                        screenreader, systemLanguage, espeak,
                                        pageNumber,
                                        newRepliesExist, newDMsExist)
            elif commandStr.startswith('prev'):
                pageNumber -= 1
                if pageNumber < 1:
                    pageNumber = 1
                prevTimelineFirstId = ''
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug)
                if boxJson:
                    _desktopShowBoxJson(currTimeline, boxJson,
                                        screenreader, systemLanguage, espeak,
                                        pageNumber,
                                        newRepliesExist, newDMsExist)
            elif commandStr.startswith('read ') or commandStr == 'read':
                if commandStr == 'read':
                    postIndexStr = '1'
                else:
                    postIndexStr = commandStr.split('read ')[1]
                if boxJson and postIndexStr.isdigit():
                    postIndex = int(postIndexStr)
                    postJsonObject = \
                        _readLocalBoxPost(baseDir, currTimeline,
                                          pageNumber, postIndex, boxJson,
                                          systemLanguage, screenreader,
                                          espeak, translate)
                print('')
            elif commandStr == 'reply' or commandStr == 'r':
                if postJsonObject:
                    if postJsonObject.get('id'):
                        postId = postJsonObject['id']
                        subject = None
                        if postJsonObject['object'].get('summary'):
                            subject = postJsonObject['object']['summary']
                        sessionReply = createSession(proxyType)
                        _desktopReplyToPost(sessionReply, postId,
                                            baseDir, nickname, password,
                                            domain, port, httpPrefix,
                                            cachedWebfingers, personCache,
                                            debug, subject,
                                            screenreader, systemLanguage,
                                            espeak)
                print('')
            elif (commandStr == 'post' or commandStr == 'p' or
                  commandStr == 'send' or
                  commandStr.startswith('dm ') or
                  commandStr.startswith('direct message ') or
                  commandStr.startswith('post ') or
                  commandStr.startswith('send ')):
                sessionPost = createSession(proxyType)
                if commandStr.startswith('dm ') or \
                   commandStr.startswith('direct message ') or \
                   commandStr.startswith('post ') or \
                   commandStr.startswith('send '):
                    commandStr = commandStr.replace(' to ', ' ')
                    commandStr = commandStr.replace(' dm ', ' ')
                    commandStr = commandStr.replace(' DM ', ' ')
                    # direct message
                    toHandle = None
                    if commandStr.startswith('post '):
                        toHandle = commandStr.split('post ', 1)[1]
                    elif commandStr.startswith('send '):
                        toHandle = commandStr.split('send ', 1)[1]
                    elif commandStr.startswith('dm '):
                        toHandle = commandStr.split('dm ', 1)[1]
                    elif commandStr.startswith('direct message '):
                        toHandle = commandStr.split('direct message ', 1)[1]
                    if toHandle:
                        _desktopNewDM(sessionPost, toHandle,
                                      baseDir, nickname, password,
                                      domain, port, httpPrefix,
                                      cachedWebfingers, personCache,
                                      debug,
                                      screenreader, systemLanguage,
                                      espeak)
                else:
                    # public post
                    _desktopNewPost(sessionPost,
                                    baseDir, nickname, password,
                                    domain, port, httpPrefix,
                                    cachedWebfingers, personCache,
                                    debug,
                                    screenreader, systemLanguage,
                                    espeak)
                print('')
            elif commandStr == 'like':
                if postJsonObject:
                    if postJsonObject.get('id'):
                        likeActor = postJsonObject['object']['attributedTo']
                        sayStr = 'Liking post by ' + \
                            getNicknameFromActor(likeActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionLike = createSession(proxyType)
                        sendLikeViaServer(baseDir, sessionLike,
                                          nickname, password,
                                          domain, port, httpPrefix,
                                          postJsonObject['id'],
                                          cachedWebfingers, personCache,
                                          False, __version__)
                print('')
            elif commandStr == 'unlike' or commandStr == 'undo like':
                if postJsonObject:
                    if postJsonObject.get('id'):
                        unlikeActor = postJsonObject['object']['attributedTo']
                        sayStr = \
                            'Undoing like of post by ' + \
                            getNicknameFromActor(unlikeActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionUnlike = createSession(proxyType)
                        sendUndoLikeViaServer(baseDir, sessionUnlike,
                                              nickname, password,
                                              domain, port, httpPrefix,
                                              postJsonObject['id'],
                                              cachedWebfingers, personCache,
                                              False, __version__)
                print('')
            elif (commandStr == 'announce' or
                  commandStr == 'boost' or
                  commandStr == 'retweet'):
                if postJsonObject:
                    if postJsonObject.get('id'):
                        postId = postJsonObject['id']
                        announceActor = \
                            postJsonObject['object']['attributedTo']
                        sayStr = 'Announcing post by ' + \
                            getNicknameFromActor(announceActor)
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
            elif commandStr.startswith('follow '):
                followHandle = commandStr.replace('follow ', '').strip()
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
            elif (commandStr.startswith('unfollow ') or
                  commandStr.startswith('stop following ')):
                followHandle = commandStr.replace('unfollow ', '').strip()
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
            elif (commandStr == 'repeat' or commandStr == 'replay' or
                  commandStr == 'rp' or commandStr == 'again' or
                  commandStr == 'say again'):
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
            elif (commandStr == 'sounds on' or
                  commandStr == 'sound on' or
                  commandStr == 'sound'):
                sayStr = 'Notification sounds on'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                notificationSounds = True
            elif (commandStr == 'sounds off' or
                  commandStr == 'sound off' or
                  commandStr == 'nosound'):
                sayStr = 'Notification sounds off'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                notificationSounds = False
            elif (commandStr == 'speak' or
                  commandStr == 'screen reader on' or
                  commandStr == 'speaker on' or
                  commandStr == 'talker on' or
                  commandStr == 'reader on'):
                if originalScreenReader:
                    screenreader = originalScreenReader
                    sayStr = 'Screen reader on'
                    _sayCommand(sayStr, sayStr, screenreader,
                                systemLanguage, espeak)
                else:
                    print('No --screenreader option was specified')
            elif (commandStr == 'mute' or
                  commandStr == 'screen reader off' or
                  commandStr == 'speaker off' or
                  commandStr == 'talker off' or
                  commandStr == 'reader off'):
                if originalScreenReader:
                    screenreader = None
                    sayStr = 'Screen reader off'
                    _sayCommand(sayStr, sayStr, originalScreenReader,
                                systemLanguage, espeak)
                else:
                    print('No --screenreader option was specified')
            elif commandStr.startswith('open'):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
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
            elif commandStr.startswith('h'):
                _desktopHelp()
