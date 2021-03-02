__filename__ = "speaker.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import random
from auth import createBasicAuthHeader
from session import getJson
from utils import getFullDomain


def getSpeakerPitch(displayName: str, screenreader: str) -> int:
    """Returns the speech synthesis pitch for the given name
    """
    random.seed(displayName)
    if screenreader == 'picospeaker':
        return random.randint(-9, 3)
    return random.randint(1, 100)


def getSpeakerRate(displayName: str, screenreader: str) -> int:
    """Returns the speech synthesis rate for the given name
    """
    random.seed(displayName)
    if screenreader == 'picospeaker':
        return random.randint(0, 20)
    return random.randint(50, 120)


def getSpeakerRange(displayName: str) -> int:
    """Returns the speech synthesis range for the given name
    """
    random.seed(displayName)
    return random.randint(300, 800)


def speakerPronounce(baseDir: str, sayText: str, translate: {}) -> str:
    """Screen readers may not always pronounce correctly, so you
    can have a file which specifies conversions. File should contain
    line items such as:
    Epicyon -> Epi-cyon
    """
    pronounceFilename = baseDir + '/accounts/speaker_pronounce.txt'
    convertDict = {
        "Epicyon": "Epi-cyon",
        "espeak": "e-speak",
        "clearnet": "clear-net",
        "RT @": "Re-Tweet ",
        "#": translate["hashtag"],
        ":)": translate["smile"],
        ";)": translate["wink"],
        ":-)": translate["smile"],
        ";-)": translate["wink"],
        "*": ""
    }
    if os.path.isfile(pronounceFilename):
        with open(pronounceFilename, 'r') as fp:
            pronounceList = fp.readlines()
            for conversion in pronounceList:
                separator = None
                if '->' in conversion:
                    separator = '->'
                elif ';' in conversion:
                    separator = ';'
                elif ':' in conversion:
                    separator = ':'
                elif ',' in conversion:
                    separator = ','
                if not separator:
                    continue

                text = conversion.split(separator)[0].strip()
                converted = conversion.split(separator)[1].strip()
                convertDict[text] = converted
    for text, converted in convertDict.items():
        if text in sayText:
            sayText = sayText.replace(text, converted)
    return sayText


def speakerReplaceLinks(sayText: str, translate: {},
                        detectedLinks: []) -> str:
    """Replaces any links in the given text with "link to [domain]".
    Instead of reading out potentially very long and meaningless links
    """
    removeChars = ('.\n', '. ', ',', ';', '?', '!')
    text = sayText
    for ch in removeChars:
        text = text.replace(ch, ' ')
    replacements = {}
    wordsList = text.split(' ')
    linkedStr = translate['Linked']
    prevWord = ''
    for word in wordsList:
        # replace mentions, but not re-tweets
        if word.startswith('@') and not prevWord.endswith('RT'):
            replacements[word] = \
                translate['mentioning'] + ' ' + word[1:] + ','
        prevWord = word

        domain = None
        domainFull = None
        if 'https://' in word:
            domain = word.split('https://')[1]
            domainFull = 'https://' + domain
        elif 'http://' in word:
            domain = word.split('http://')[1]
            domainFull = 'http://' + domain
        if not domain:
            continue
        if '/' in domain:
            domain = domain.split('/')[0]
        if domain.startswith('www.'):
            domain = domain.replace('www.', '')
        replacements[domainFull] = '. ' + linkedStr + ' ' + domain + '.'
        detectedLinks.append(domainFull)
    for replaceStr, newStr in replacements.items():
        sayText = sayText.replace(replaceStr, newStr)
    return sayText.replace('..', '.')


def getSpeakerFromServer(baseDir: str, session,
                         nickname: str, password: str,
                         domain: str, port: int,
                         httpPrefix: str,
                         debug: bool, projectVersion: str) -> {}:
    """Returns some json which contains the latest inbox
    entry in a minimal format suitable for a text-to-speech reader
    """
    if not session:
        print('WARN: No session for getSpeakerFromServer')
        return 6

    domainFull = getFullDomain(domain, port)

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }

    url = \
        httpPrefix + '://' + \
        domainFull + '/users/' + nickname + '/speaker'

    speakerJson = \
        getJson(session, url, headers, None,
                __version__, httpPrefix, domain)
    return speakerJson
