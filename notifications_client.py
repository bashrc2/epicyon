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
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import getFullDomain
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


def runNotificationsClient(baseDir: str, proxyType: str, httpPrefix: str,
                           nickname: str, domain: str, port: int,
                           password: str, screenreader: str,
                           systemLanguage: str,
                           notificationSounds: bool,
                           notificationType: str,
                           debug: bool) -> None:
    """Runs the notifications and screen reader client,
    which announces new inbox items
    """
    espeak = None
    if screenreader:
        if screenreader == 'espeak':
            print('Setting up espeak')
            from espeak import espeak
        elif screenreader != 'picospeaker':
            print(screenreader + ' is not a supported TTS system')
            return

        sayStr = 'Running ' + screenreader + ' for ' + nickname + '@' + domain
        _sayCommand(sayStr, sayStr, screenreader,
                    systemLanguage, espeak)
    else:
        print('Running desktop notifications for ' + nickname + '@' + domain)
    if notificationSounds:
        sayStr = 'Notification sounds on'
    else:
        sayStr = 'Notification sounds off'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)
    sayStr = '/q or /quit to exit'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)
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
    while (1):
        session = createSession(proxyType)
        speakerJson = \
            getSpeakerFromServer(baseDir, session, nickname, password,
                                 domain, port, httpPrefix, True, __version__)
        if speakerJson:
            if speakerJson.get('notify'):
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

                        content = messageStr
                        if speakerJson.get('content'):
                            content = speakerJson['content']

                        # say the speaker's name
                        _sayCommand(nameStr, nameStr, screenreader,
                                    systemLanguage, espeak,
                                    nameStr, gender)

                        time.sleep(2)

                        # speak the post content
                        _sayCommand(content, messageStr, screenreader,
                                    systemLanguage, espeak,
                                    nameStr, gender)

                        print('')

                    prevSay = speakerJson['say']

        # wait for a while, or until a key is pressed
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
            elif keyPress == 'post' or keyPress == 'p':
                sessionPost = createSession(proxyType)
                _notificationNewPost(sessionPost,
                                     baseDir, nickname, password,
                                     domain, port, httpPrefix,
                                     cachedWebfingers, personCache,
                                     debug,
                                     screenreader, systemLanguage,
                                     espeak)
                print('')
            elif keyPress == 'like':
                if nameStr and gender and messageStr:
                    sayStr = 'Liking post by ' + nameStr
                    _sayCommand(sayStr, sayStr,
                                screenreader,
                                systemLanguage, espeak)
                    sessionLike = createSession(proxyType)
                    sendLikeViaServer(baseDir, sessionLike,
                                      nickname, password,
                                      domain, port,
                                      httpPrefix, speakerJson['id'],
                                      cachedWebfingers, personCache,
                                      True, __version__)
                    print('')
            elif keyPress == 'unlike' or keyPress == 'undo like':
                if nameStr and gender and messageStr:
                    sayStr = 'Undoing like of post by ' + nameStr
                    _sayCommand(sayStr, sayStr,
                                screenreader,
                                systemLanguage, espeak)
                    sessionUnlike = createSession(proxyType)
                    sendUndoLikeViaServer(baseDir, sessionUnlike,
                                          nickname, password,
                                          domain, port,
                                          httpPrefix, speakerJson['id'],
                                          cachedWebfingers, personCache,
                                          True, __version__)
                    print('')
            elif (keyPress == 'announce' or
                  keyPress == 'boost' or
                  keyPress == 'retweet'):
                if speakerJson.get('id'):
                    if nameStr and gender and messageStr:
                        postId = speakerJson['id']
                        sayStr = 'Announcing post by ' + nameStr
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
                  keyPress == 'rp'):
                if nameStr and gender and messageStr and content:
                    sayStr = 'Repeating ' + nameStr, screenreader
                    _sayCommand(sayStr, sayStr,
                                systemLanguage, espeak,
                                nameStr, gender)
                    time.sleep(2)
                    _sayCommand(content, messageStr, screenreader,
                                systemLanguage, espeak,
                                nameStr, gender)
                    print('')
            elif keyPress == 'sounds on' or keyPress == 'sound':
                sayStr = 'Notification sounds on'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                notificationSounds = True
            elif keyPress == 'sounds off' or keyPress == 'nosound':
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
