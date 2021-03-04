__filename__ = "speaker_client.py"
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
        html.unescape(sayText) + '"'
    # print(speakerCmd)
    os.system(speakerCmd)


def runSpeakerClient(baseDir: str, proxyType: str, httpPrefix: str,
                     nickname: str, domain: str, port: int, password: str,
                     screenreader: str, systemLanguage: str,
                     debug: bool) -> None:
    """Runs the screen reader client, which announces new inbox items via TTS
    """
    if screenreader == 'espeak':
        print('Setting up espeak')
        from espeak import espeak
    elif screenreader != 'picospeaker':
        print(screenreader + ' is not a supported TTS system')
        return

    print('Running ' + screenreader + ' for ' + nickname + '@' + domain)

    prevSay = ''
    while (1):
        session = createSession(proxyType)
        speakerJson = \
            getSpeakerFromServer(baseDir, session, nickname, password,
                                 domain, port, httpPrefix, True, __version__)
        if speakerJson:
            if speakerJson['say'] != prevSay:
                if speakerJson.get('name'):
                    nameStr = speakerJson['name']
                    gender = 'They/Them'
                    if speakerJson.get('gender'):
                        gender = speakerJson['gender']

                    # get the speech parameters
                    pitch = getSpeakerPitch(nameStr, screenreader, gender)
                    rate = getSpeakerRate(nameStr, screenreader)
                    srange = getSpeakerRange(nameStr)

                    # say the speaker's name
                    if screenreader == 'espeak':
                        _speakerEspeak(espeak, pitch, rate, srange, nameStr)
                    elif screenreader == 'picospeaker':
                        _speakerPicospeaker(pitch, rate,
                                            systemLanguage, nameStr)
                    time.sleep(2)

                    # append image description if needed
                    if not speakerJson.get('imageDescription'):
                        sayStr = speakerJson['say']
                        # echo spoken text to the screen
                        print(html.unescape(nameStr) + ': ' +
                              html.unescape(speakerJson['say']) + '\n')
                    else:
                        sayStr = speakerJson['say'] + '. ' + \
                            speakerJson['imageDescription']
                        # echo spoken text to the screen
                        print(html.unescape(nameStr) + ': ' +
                              html.unescape(speakerJson['say']) + '\n' +
                              html.unescape(speakerJson['imageDescription']))

                    # speak the post content
                    if screenreader == 'espeak':
                        _speakerEspeak(espeak, pitch, rate, srange, sayStr)
                    elif screenreader == 'picospeaker':
                        _speakerPicospeaker(pitch, rate,
                                            systemLanguage, sayStr)

                prevSay = speakerJson['say']

        # wait for a while, or until a key is pressed
        keyPress = _waitForKeypress(30, debug)
        if keyPress:
            if keyPress.startswith('/'):
                keyPress = keyPress[1:]
            if keyPress == 'q' or keyPress == 'quit' or keyPress == 'exit':
                break
