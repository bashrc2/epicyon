__filename__ = "speaker.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import html
import random
import urllib.parse
from auth import createBasicAuthHeader
from session import getJson
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import getGenderFromBio
from utils import getDisplayName
from utils import removeHtml
from utils import loadJson
from utils import saveJson
from utils import getFullDomain
from content import htmlReplaceQuoteMarks

speakerRemoveChars = ('.\n', '. ', ',', ';', '?', '!')


def getSpeakerPitch(displayName: str, screenreader: str, gender) -> int:
    """Returns the speech synthesis pitch for the given name
    """
    random.seed(displayName)
    rangeMin = 1
    rangeMax = 100
    if 'She' in gender:
        rangeMin = 50
    elif 'Him' in gender:
        rangeMax = 50
    if screenreader == 'picospeaker':
        rangeMin = -8
        rangeMax = 3
        if 'She' in gender:
            rangeMin = -1
        elif 'Him' in gender:
            rangeMax = -1
    return random.randint(rangeMin, rangeMax)


def getSpeakerRate(displayName: str, screenreader: str) -> int:
    """Returns the speech synthesis rate for the given name
    """
    random.seed(displayName)
    if screenreader == 'picospeaker':
        return random.randint(0, 10)
    return random.randint(50, 120)


def getSpeakerRange(displayName: str) -> int:
    """Returns the speech synthesis range for the given name
    """
    random.seed(displayName)
    return random.randint(300, 800)


def _speakerPronounce(baseDir: str, sayText: str, translate: {}) -> str:
    """Screen readers may not always pronounce correctly, so you
    can have a file which specifies conversions. File should contain
    line items such as:
    Epicyon -> Epi-cyon
    """
    pronounceFilename = baseDir + '/accounts/speaker_pronounce.txt'
    convertDict = {}
    if translate:
        convertDict = {
            "Epicyon": "Epi-cyon",
            "espeak": "e-speak",
            "emoji": "emowji",
            "clearnet": "clear-net",
            "https": "H-T-T-P-S",
            "HTTPS": "H-T-T-P-S",
            "Tor": "Toor",
            "🤔": ". " + translate["thinking emoji"],
            "RT @": "Re-Tweet ",
            "#": translate["hashtag"],
            ":D": '. ' + translate["laughing"],
            ":-D": '. ' + translate["laughing"],
            ":)": '. ' + translate["smile"],
            ";)": '. ' + translate["wink"],
            ":(": '. ' + translate["sad face"],
            ":-)": '. ' + translate["smile"],
            ":-(": '. ' + translate["sad face"],
            ";-)": '. ' + translate["wink"],
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
    text = sayText
    for ch in speakerRemoveChars:
        text = text.replace(ch, ' ')
    replacements = {}
    wordsList = text.split(' ')
    if translate.get('Linked'):
        linkedStr = translate['Linked']
    else:
        linkedStr = 'Linked'
    prevWord = ''
    for word in wordsList:
        if word.startswith(':'):
            if word.endswith(':'):
                replacements[word] = ', emowji ' + word.replace(':', '') + ','
                continue
        # replace mentions, but not re-tweets
        if word.startswith('@') and not prevWord.endswith('RT'):
            if translate.get('mentioning'):
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


def _addSSMLemphasis(sayText: str) -> str:
    """Adds emphasis to *emphasised* text
    """
    if '*' not in sayText:
        return sayText
    text = sayText
    for ch in speakerRemoveChars:
        text = text.replace(ch, ' ')
    wordsList = text.split(' ')
    replacements = {}
    for word in wordsList:
        if word.startswith('*'):
            if word.endswith('*'):
                replacements[word] = \
                    '<emphasis level="strong">' + \
                    word.replace('*', '') + \
                    '</emphasis>'
    for replaceStr, newStr in replacements.items():
        sayText = sayText.replace(replaceStr, newStr)
    return sayText


def _removeEmojiFromText(sayText: str) -> str:
    """Removes :emoji: from the given text
    """
    if '*' not in sayText:
        return sayText
    text = sayText
    for ch in speakerRemoveChars:
        text = text.replace(ch, ' ')
    wordsList = text.split(' ')
    replacements = {}
    for word in wordsList:
        if word.startswith(':'):
            if word.endswith(':'):
                replacements[word] = word.replace('*', '')
    for replaceStr, newStr in replacements.items():
        sayText = sayText.replace(replaceStr, newStr)
    return sayText.replace('  ', ' ').strip()


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


def _speakerEndpointJson(displayName: str, summary: str,
                         content: str, imageDescription: str,
                         links: [], gender: str) -> {}:
    """Returns a json endpoint for the TTS speaker
    """
    speakerJson = {
        "name": displayName,
        "summary": summary,
        "say": content,
        "imageDescription": imageDescription,
        "detectedLinks": links
    }
    if gender:
        speakerJson['gender'] = gender
    return speakerJson


def _speakerEndpointSSML(displayName: str, summary: str,
                         content: str, imageDescription: str,
                         links: [], language: str,
                         instanceTitle: str,
                         gender: str) -> str:
    """Returns an SSML endpoint for the TTS speaker
    https://en.wikipedia.org/wiki/Speech_Synthesis_Markup_Language
    https://www.w3.org/TR/speech-synthesis/
    """
    langShort = 'en'
    if language:
        langShort = language[:2]
    if not gender:
        gender = 'neutral'
    else:
        if langShort == 'en':
            gender = gender.lower()
            if 'he/him' in gender:
                gender = 'male'
            elif 'she/her' in gender:
                gender = 'female'
            else:
                gender = 'neutral'

    content = _addSSMLemphasis(content)
    voiceParams = 'name="' + displayName + '" gender="' + gender + '"'
    return '<?xml version="1.0"?>\n' + \
        '<speak xmlns="http://www.w3.org/2001/10/synthesis"\n' + \
        '       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' + \
        '       xsi:schemaLocation="http://www.w3.org/2001/10/synthesis\n' + \
        '         http://www.w3.org/TR/speech-synthesis11/synthesis.xsd"\n' + \
        '       version="1.1">\n' + \
        '  <metadata>\n' + \
        '    <dc:title xml:lang="' + langShort + '">' + \
        instanceTitle + ' inbox</dc:title>\n' + \
        '  </metadata>\n' + \
        '  <p>\n' + \
        '    <s xml:lang="' + language + '">\n' + \
        '      <voice ' + voiceParams + '>\n' + \
        '        ' + content + '\n' + \
        '      </voice>\n' + \
        '    </s>\n' + \
        '  </p>\n' + \
        '</speak>\n'


def getSSMLbox(baseDir: str, path: str,
               domain: str,
               systemLanguage: str,
               instanceTitle: str,
               boxName: str) -> str:
    """Returns SSML for the given timeline
    """
    nickname = path.split('/users/')[1]
    if '/' in nickname:
        nickname = nickname.split('/')[0]
    speakerFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/speaker.json'
    if not os.path.isfile(speakerFilename):
        return None
    speakerJson = loadJson(speakerFilename)
    if not speakerJson:
        return None
    gender = None
    if speakerJson.get('gender'):
        gender = speakerJson['gender']
    return _speakerEndpointSSML(speakerJson['name'],
                                speakerJson['summary'],
                                speakerJson['say'],
                                speakerJson['imageDescription'],
                                speakerJson['detectedLinks'],
                                systemLanguage,
                                instanceTitle, gender)


def updateSpeaker(baseDir: str, nickname: str, domain: str,
                  postJsonObject: {}, personCache: {},
                  translate: {}, announcingActor: str) -> None:
    """ Generates a json file which can be used for TTS announcement
    of incoming inbox posts
    """
    if not postJsonObject.get('object'):
        return
    if not isinstance(postJsonObject['object'], dict):
        return
    if not postJsonObject['object'].get('content'):
        return
    if not isinstance(postJsonObject['object']['content'], str):
        return
    speakerFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/speaker.json'
    detectedLinks = []
    content = urllib.parse.unquote_plus(postJsonObject['object']['content'])
    content = html.unescape(content)
    content = content.replace('<p>', '').replace('</p>', ' ')
    content = removeHtml(htmlReplaceQuoteMarks(content))
    content = speakerReplaceLinks(content, translate, detectedLinks)
    content = _speakerPronounce(baseDir, content, translate)

    imageDescription = ''
    if postJsonObject['object'].get('attachment'):
        attachList = postJsonObject['object']['attachment']
        if isinstance(attachList, list):
            for img in attachList:
                if not isinstance(img, dict):
                    continue
                if img.get('name'):
                    if isinstance(img['name'], str):
                        imageDescription += \
                            img['name'] + '. '

    summary = ''
    if postJsonObject['object'].get('summary'):
        if isinstance(postJsonObject['object']['summary'], str):
            summary = \
                urllib.parse.unquote_plus(postJsonObject['object']['summary'])
            summary = html.unescape(summary)

    speakerName = \
        getDisplayName(baseDir, postJsonObject['actor'], personCache)
    if not speakerName:
        return
    speakerName = _removeEmojiFromText(speakerName)
    gender = getGenderFromBio(baseDir, postJsonObject['actor'],
                              personCache, translate)
    if announcingActor:
        announcedNickname = getNicknameFromActor(announcingActor)
        announcedDomain, announcedport = getDomainFromActor(announcingActor)
        if announcedNickname and announcedDomain:
            announcedHandle = announcedNickname + '@' + announcedDomain
            content = \
                translate['announces'] + ' ' + announcedHandle + '. ' + content
    speakerJson = _speakerEndpointJson(speakerName, summary,
                                       content, imageDescription,
                                       detectedLinks, gender)
    saveJson(speakerJson, speakerFilename)
