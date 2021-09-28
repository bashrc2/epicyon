__filename__ = "speaker.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Accessibility"

import os
import html
import random
import urllib.parse
from utils import removeIdEnding
from utils import isDM
from utils import isReply
from utils import camelCaseSplit
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import getGenderFromBio
from utils import getDisplayName
from utils import removeHtml
from utils import loadJson
from utils import saveJson
from utils import isPGPEncrypted
from utils import hasObjectDict
from utils import acctDir
from utils import localActorUrl
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
        rangeMin = -6
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
        return random.randint(-40, -20)
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
            "XMPP": "X-M-P-P",
            "xmpp": "X-M-P-P",
            "sql": "S-Q-L",
            ".js": " dot J-S",
            "PSQL": "Postgres S-Q-L",
            "SQL": "S-Q-L",
            "gdpr": "G-D-P-R",
            "kde": "K-D-E",
            "AGPL": "Affearo G-P-L",
            "agpl": "Affearo G-P-L",
            "GPL": "G-P-L",
            "gpl": "G-P-L",
            "coop": "co-op",
            "KMail": "K-Mail",
            "kmail": "K-Mail",
            "gmail": "G-mail",
            "Gmail": "G-mail",
            "OpenPGP": "Open P-G-P",
            "Tor": "Toor",
            "memes": "meemes",
            "Memes": "Meemes",
            "rofl": "roll on the floor laughing",
            "ROFL": "roll on the floor laughing",
            "fwiw": "for what it's worth",
            "fyi": "for your information",
            "irl": "in real life",
            "IRL": "in real life",
            "imho": "in my opinion",
            "fediverse": "fediiverse",
            "Fediverse": "Fediiverse",
            " foss ": " free and open source software ",
            " floss ": " free libre and open source software ",
            " FOSS ": "free and open source software",
            " FLOSS ": "free libre and open source software",
            " oss ": " open source software ",
            " OSS ": " open source software ",
            "🤔": ". " + translate["thinking emoji"],
            "RT @": "Re-Tweet ",
            "#nowplaying": translate["hashtag"] + " now-playing",
            "#NowPlaying": translate["hashtag"] + " now-playing",
            "#": translate["hashtag"] + ' ',
            ":D": '. ' + translate["laughing"],
            ":-D": '. ' + translate["laughing"],
            ":)": '. ' + translate["smile"],
            ";)": '. ' + translate["wink"],
            ":(": '. ' + translate["sad face"],
            ":-)": '. ' + translate["smile"],
            ":-(": '. ' + translate["sad face"],
            ";-)": '. ' + translate["wink"],
            ":O": '. ' + translate['shocked'],
            "?": "? ",
            '"': "'",
            "*": "",
            "(": ",",
            ")": ","
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
    text = text.replace('?v=', '__v=')
    for ch in speakerRemoveChars:
        text = text.replace(ch, ' ')
    text = text.replace('__v=', '?v=')
    replacements = {}
    wordsList = text.split(' ')
    if translate.get('Linked'):
        linkedStr = translate['Linked']
    else:
        linkedStr = 'Linked'
    prevWord = ''
    for word in wordsList:
        if word.startswith('v='):
            replacements[word] = ''
        if word.startswith(':'):
            if word.endswith(':'):
                replacements[word] = ', emowji ' + word.replace(':', '') + ','
                continue
        if word.startswith('@') and not prevWord.endswith('RT'):
            # replace mentions, but not re-tweets
            if translate.get('mentioning'):
                replacements[word] = \
                    translate['mentioning'] + ' ' + word[1:] + ', '
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
    if ':' not in sayText:
        return sayText
    text = sayText
    for ch in speakerRemoveChars:
        text = text.replace(ch, ' ')
    wordsList = text.split(' ')
    replacements = {}
    for word in wordsList:
        if word.startswith(':'):
            if word.endswith(':'):
                replacements[word] = ''
    for replaceStr, newStr in replacements.items():
        sayText = sayText.replace(replaceStr, newStr)
    return sayText.replace('  ', ' ').strip()


def _speakerEndpointJson(displayName: str, summary: str,
                         content: str, sayContent: str,
                         imageDescription: str,
                         links: [], gender: str, postId: str,
                         postDM: bool, postReply: bool,
                         followRequestsExist: bool,
                         followRequestsList: [],
                         likedBy: str, published: str, postCal: bool,
                         postShare: bool, themeName: str,
                         isDirect: bool, replyToYou: bool) -> {}:
    """Returns a json endpoint for the TTS speaker
    """
    speakerJson = {
        "name": displayName,
        "summary": summary,
        "content": content,
        "say": sayContent,
        "published": published,
        "imageDescription": imageDescription,
        "detectedLinks": links,
        "id": postId,
        "direct": isDirect,
        "replyToYou": replyToYou,
        "notify": {
            "theme": themeName,
            "dm": postDM,
            "reply": postReply,
            "followRequests": followRequestsExist,
            "followRequestsList": followRequestsList,
            "likedBy": likedBy,
            "calendar": postCal,
            "share": postShare
        }
    }
    if gender:
        speakerJson['gender'] = gender
    return speakerJson


def _SSMLheader(systemLanguage: str, instanceTitle: str) -> str:
    """Returns a header for an SSML document
    """
    return '<?xml version="1.0"?>\n' + \
        '<speak xmlns="http://www.w3.org/2001/10/synthesis"\n' + \
        '       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' + \
        '       xsi:schemaLocation="http://www.w3.org/2001/10/synthesis\n' + \
        '         http://www.w3.org/TR/speech-synthesis11/synthesis.xsd"\n' + \
        '       version="1.1">\n' + \
        '  <metadata>\n' + \
        '    <dc:title xml:lang="' + systemLanguage + '">' + \
        instanceTitle + ' inbox</dc:title>\n' + \
        '  </metadata>\n'


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
    return _SSMLheader(langShort, instanceTitle) + \
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
        acctDir(baseDir, nickname, domain) + '/speaker.json'
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


def speakableText(baseDir: str, content: str, translate: {}) -> (str, []):
    """Convert the given text to a speakable version
    which includes changes for prononciation
    """
    content = str(content)
    if isPGPEncrypted(content):
        return content, []

    # replace some emoji before removing html
    if ' <3' in content:
        content = content.replace(' <3', ' ' + translate['heart'])
    content = removeHtml(htmlReplaceQuoteMarks(content))
    detectedLinks = []
    content = speakerReplaceLinks(content, translate, detectedLinks)
    # replace all double spaces
    while '  ' in content:
        content = content.replace('  ', ' ')
    content = content.replace(' . ', '. ').strip()
    sayContent = _speakerPronounce(baseDir, content, translate)
    # replace all double spaces
    while '  ' in sayContent:
        sayContent = sayContent.replace('  ', ' ')
    return sayContent.replace(' . ', '. ').strip(), detectedLinks


def _postToSpeakerJson(baseDir: str, httpPrefix: str,
                       nickname: str, domain: str, domainFull: str,
                       postJsonObject: {}, personCache: {},
                       translate: {}, announcingActor: str,
                       themeName: str) -> {}:
    """Converts an ActivityPub post into some Json containing
    speech synthesis parameters.
    NOTE: There currently appears to be no standardized json
    format for speech synthesis
    """
    if not hasObjectDict(postJsonObject):
        return
    if not postJsonObject['object'].get('content'):
        return
    if not isinstance(postJsonObject['object']['content'], str):
        return
    detectedLinks = []
    content = urllib.parse.unquote_plus(postJsonObject['object']['content'])
    content = html.unescape(content)
    content = content.replace('<p>', '').replace('</p>', ' ')
    if not isPGPEncrypted(content):
        # replace some emoji before removing html
        if ' <3' in content:
            content = content.replace(' <3', ' ' + translate['heart'])
        content = removeHtml(htmlReplaceQuoteMarks(content))
        content = speakerReplaceLinks(content, translate, detectedLinks)
        # replace all double spaces
        while '  ' in content:
            content = content.replace('  ', ' ')
        content = content.replace(' . ', '. ').strip()
        sayContent = content
        sayContent = _speakerPronounce(baseDir, content, translate)
        # replace all double spaces
        while '  ' in sayContent:
            sayContent = sayContent.replace('  ', ' ')
        sayContent = sayContent.replace(' . ', '. ').strip()
    else:
        sayContent = content

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

    isDirect = isDM(postJsonObject)
    actor = localActorUrl(httpPrefix, nickname, domainFull)
    replyToYou = isReply(postJsonObject, actor)

    published = ''
    if postJsonObject['object'].get('published'):
        published = postJsonObject['object']['published']

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
    speakerName = speakerName.replace('_', ' ')
    speakerName = camelCaseSplit(speakerName)
    gender = getGenderFromBio(baseDir, postJsonObject['actor'],
                              personCache, translate)
    if announcingActor:
        announcedNickname = getNicknameFromActor(announcingActor)
        announcedDomain, announcedport = getDomainFromActor(announcingActor)
        if announcedNickname and announcedDomain:
            announcedHandle = announcedNickname + '@' + announcedDomain
            sayContent = \
                translate['announces'] + ' ' + \
                announcedHandle + '. ' + sayContent
            content = \
                translate['announces'] + ' ' + \
                announcedHandle + '. ' + content
    postId = None
    if postJsonObject['object'].get('id'):
        postId = removeIdEnding(postJsonObject['object']['id'])

    followRequestsExist = False
    followRequestsList = []
    accountsDir = acctDir(baseDir, nickname, domainFull)
    approveFollowsFilename = accountsDir + '/followrequests.txt'
    if os.path.isfile(approveFollowsFilename):
        with open(approveFollowsFilename, 'r') as fp:
            follows = fp.readlines()
            if len(follows) > 0:
                followRequestsExist = True
                for i in range(len(follows)):
                    follows[i] = follows[i].strip()
                followRequestsList = follows
    postDM = False
    dmFilename = accountsDir + '/.newDM'
    if os.path.isfile(dmFilename):
        postDM = True
    postReply = False
    replyFilename = accountsDir + '/.newReply'
    if os.path.isfile(replyFilename):
        postReply = True
    likedBy = ''
    likeFilename = accountsDir + '/.newLike'
    if os.path.isfile(likeFilename):
        with open(likeFilename, 'r') as fp:
            likedBy = fp.read()
    calendarFilename = accountsDir + '/.newCalendar'
    postCal = os.path.isfile(calendarFilename)
    shareFilename = accountsDir + '/.newShare'
    postShare = os.path.isfile(shareFilename)

    return _speakerEndpointJson(speakerName, summary,
                                content, sayContent, imageDescription,
                                detectedLinks, gender, postId,
                                postDM, postReply,
                                followRequestsExist,
                                followRequestsList,
                                likedBy, published,
                                postCal, postShare, themeName,
                                isDirect, replyToYou)


def updateSpeaker(baseDir: str, httpPrefix: str,
                  nickname: str, domain: str, domainFull: str,
                  postJsonObject: {}, personCache: {},
                  translate: {}, announcingActor: str,
                  themeName: str) -> None:
    """ Generates a json file which can be used for TTS announcement
    of incoming inbox posts
    """
    speakerJson = \
        _postToSpeakerJson(baseDir, httpPrefix,
                           nickname, domain, domainFull,
                           postJsonObject, personCache,
                           translate, announcingActor,
                           themeName)
    speakerFilename = acctDir(baseDir, nickname, domain) + '/speaker.json'
    saveJson(speakerJson, speakerFilename)
