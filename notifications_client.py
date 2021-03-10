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
from utils import getFullDomain
from session import createSession
from speaker import getSpeakerFromServer
from speaker import getSpeakerPitch
from speaker import getSpeakerRate
from speaker import getSpeakerRange


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
                  ' -autoexit -hide_banner -nodisp')


def _desktopNotification(notificationType: str,
                         title: str, message: str) -> None:
    """Shows a desktop notification
    """
    if not notificationType:
        return

    if notificationType == 'notify-send':
        # Ubuntu
        os.system('notify-send "' + title + '" "' + message + '"')
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


def _sayCommand(sayStr: str, screenreader: str,
                systemLanguage: str,
                espeak=None,
                speakerName='screen reader',
                speakerGender='They/Them') -> None:
    """Speaks a command
    """
    print(sayStr)
    if not screenreader:
        return

    pitch = getSpeakerPitch(speakerName,
                            screenreader, speakerGender)
    rate = getSpeakerRate(speakerName, screenreader)
    srange = getSpeakerRange(speakerName)

    _textToSpeech(sayStr, screenreader,
                  pitch, rate, srange,
                  systemLanguage, espeak)


def runNotificationsClient(baseDir: str, proxyType: str, httpPrefix: str,
                           nickname: str, domain: str, port: int,
                           password: str, screenreader: str,
                           systemLanguage: str,
                           notificationSounds: bool,
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
        _sayCommand(sayStr, screenreader,
                    systemLanguage, espeak)
    else:
        print('Running desktop notifications for ' + nickname + '@' + domain)
    if notificationSounds:
        sayStr = 'Notification sounds on'
    else:
        sayStr = 'Notification sounds off'
    _sayCommand(sayStr, screenreader,
                systemLanguage, espeak)
    sayStr = '/q or /quit to exit'
    _sayCommand(sayStr, screenreader,
                systemLanguage, espeak)

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
    notificationType = 'notify-send'
    nameStr = None
    gender = None
    messageStr = None
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

                        # say the speaker's name
                        _sayCommand(nameStr, screenreader,
                                    systemLanguage, espeak,
                                    nameStr, gender)

                        time.sleep(2)

                        # speak the post content
                        _sayCommand(messageStr, screenreader,
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
                _sayCommand(sayStr, screenreader,
                            systemLanguage, espeak)
                keyPress = _waitForKeypress(2, debug)
                break
            elif keyPress == 'repeat' or keyPress == 'rp':
                if nameStr and gender and messageStr:
                    _sayCommand('Repeating ' + nameStr, screenreader,
                                systemLanguage, espeak,
                                nameStr, gender)
                    time.sleep(2)
                    _sayCommand(messageStr, screenreader,
                                systemLanguage, espeak,
                                nameStr, gender)
                    print('')
            elif keyPress == 'sounds on' or keyPress == 'sound':
                sayStr = 'Notification sounds on'
                _sayCommand(sayStr, screenreader,
                            systemLanguage, espeak)
                notificationSounds = True
            elif keyPress == 'sounds off' or keyPress == 'nosound':
                sayStr = 'Notification sounds off'
                _sayCommand(sayStr, screenreader,
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
                    _sayCommand(sayStr, screenreader,
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
                    _sayCommand(sayStr, originalScreenReader,
                                systemLanguage, espeak)
                else:
                    print('No --screenreader option was specified')
