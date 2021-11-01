__filename__ = "content.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import email.parser
import urllib.parse
from shutil import copyfile
from utils import dangerousSVG
from utils import removeDomainPort
from utils import isValidLanguage
from utils import getImageExtensions
from utils import loadJson
from utils import fileLastModified
from utils import getLinkPrefixes
from utils import dangerousMarkup
from utils import isPGPEncrypted
from utils import containsPGPPublicKey
from utils import acctDir
from utils import isfloat
from utils import getCurrencies
from utils import removeHtml
from petnames import getPetName


def removeHtmlTag(htmlStr: str, tag: str) -> str:
    """Removes a given tag from a html string
    """
    tagFound = True
    while tagFound:
        matchStr = ' ' + tag + '="'
        if matchStr not in htmlStr:
            tagFound = False
            break
        sections = htmlStr.split(matchStr, 1)
        if '"' not in sections[1]:
            tagFound = False
            break
        htmlStr = sections[0] + sections[1].split('"', 1)[1]
    return htmlStr


def _removeQuotesWithinQuotes(content: str) -> str:
    """Removes any blockquote inside blockquote
    """
    if '<blockquote>' not in content:
        return content
    if '</blockquote>' not in content:
        return content
    ctr = 1
    found = True
    while found:
        prefix = content.split('<blockquote>', ctr)[0] + '<blockquote>'
        quotedStr = content.split('<blockquote>', ctr)[1]
        if '</blockquote>' not in quotedStr:
            found = False
        else:
            endStr = quotedStr.split('</blockquote>')[1]
            quotedStr = quotedStr.split('</blockquote>')[0]
            if '<blockquote>' not in endStr:
                found = False
            if '<blockquote>' in quotedStr:
                quotedStr = quotedStr.replace('<blockquote>', '')
                content = prefix + quotedStr + '</blockquote>' + endStr
        ctr += 1
    return content


def htmlReplaceEmailQuote(content: str) -> str:
    """Replaces an email style quote "> Some quote" with html blockquote
    """
    if isPGPEncrypted(content) or containsPGPPublicKey(content):
        return content
    # replace quote paragraph
    if '<p>&quot;' in content:
        if '&quot;</p>' in content:
            if content.count('<p>&quot;') == content.count('&quot;</p>'):
                content = content.replace('<p>&quot;', '<p><blockquote>')
                content = content.replace('&quot;</p>', '</blockquote></p>')
    if '>\u201c' in content:
        if '\u201d<' in content:
            if content.count('>\u201c') == content.count('\u201d<'):
                content = content.replace('>\u201c', '><blockquote>')
                content = content.replace('\u201d<', '</blockquote><')
    # replace email style quote
    if '>&gt; ' not in content:
        return content
    contentStr = content.replace('<p>', '')
    contentLines = contentStr.split('</p>')
    newContent = ''
    for lineStr in contentLines:
        if not lineStr:
            continue
        if '>&gt; ' not in lineStr:
            if lineStr.startswith('&gt; '):
                lineStr = lineStr.replace('&gt; ', '<blockquote>')
                lineStr = lineStr.replace('&gt;', '<br>')
                newContent += '<p>' + lineStr + '</blockquote></p>'
            else:
                newContent += '<p>' + lineStr + '</p>'
        else:
            lineStr = lineStr.replace('>&gt; ', '><blockquote>')
            if lineStr.startswith('&gt;'):
                lineStr = lineStr.replace('&gt;', '<blockquote>', 1)
            else:
                lineStr = lineStr.replace('&gt;', '<br>')
            newContent += '<p>' + lineStr + '</blockquote></p>'
    return _removeQuotesWithinQuotes(newContent)


def htmlReplaceQuoteMarks(content: str) -> str:
    """Replaces quotes with html formatting
    "hello" becomes <q>hello</q>
    """
    if isPGPEncrypted(content) or containsPGPPublicKey(content):
        return content
    if '"' not in content:
        if '&quot;' not in content:
            return content

    # only if there are a few quote marks
    if content.count('"') > 4:
        return content
    if content.count('&quot;') > 4:
        return content

    newContent = content
    if '"' in content:
        sections = content.split('"')
        if len(sections) > 1:
            newContent = ''
            openQuote = True
            markup = False
            for ch in content:
                currChar = ch
                if ch == '<':
                    markup = True
                elif ch == '>':
                    markup = False
                elif ch == '"' and not markup:
                    if openQuote:
                        currChar = '“'
                    else:
                        currChar = '”'
                    openQuote = not openQuote
                newContent += currChar

    if '&quot;' in newContent:
        openQuote = True
        content = newContent
        newContent = ''
        ctr = 0
        sections = content.split('&quot;')
        noOfSections = len(sections)
        for s in sections:
            newContent += s
            if ctr < noOfSections - 1:
                if openQuote:
                    newContent += '“'
                else:
                    newContent += '”'
                openQuote = not openQuote
            ctr += 1
    return newContent


def dangerousCSS(filename: str, allowLocalNetworkAccess: bool) -> bool:
    """Returns true is the css file contains code which
    can create security problems
    """
    if not os.path.isfile(filename):
        return False

    with open(filename, 'r') as fp:
        content = fp.read().lower()

        cssMatches = ('behavior:', ':expression', '?php', '.php',
                      'google', 'regexp', 'localhost',
                      '127.0.', '192.168', '10.0.', '@import')
        for cssmatch in cssMatches:
            if cssmatch in content:
                return True

        # search for non-local web links
        if 'url(' in content:
            urlList = content.split('url(')
            ctr = 0
            for urlStr in urlList:
                if ctr > 0:
                    if ')' in urlStr:
                        urlStr = urlStr.split(')')[0]
                        if 'http' in urlStr:
                            print('ERROR: non-local web link in CSS ' +
                                  filename)
                            return True
                ctr += 1

        # an attacker can include html inside of the css
        # file as a comment and this may then be run from the html
        if dangerousMarkup(content, allowLocalNetworkAccess):
            return True
    return False


def switchWords(baseDir: str, nickname: str, domain: str, content: str,
                rules: [] = []) -> str:
    """Performs word replacements. eg. Trump -> The Orange Menace
    """
    if isPGPEncrypted(content) or containsPGPPublicKey(content):
        return content

    if not rules:
        switchWordsFilename = \
            acctDir(baseDir, nickname, domain) + '/replacewords.txt'
        if not os.path.isfile(switchWordsFilename):
            return content
        with open(switchWordsFilename, 'r') as fp:
            rules = fp.readlines()

    for line in rules:
        replaceStr = line.replace('\n', '').replace('\r', '')
        splitters = ('->', ':', ',', ';', '-')
        wordTransform = None
        for splitStr in splitters:
            if splitStr in replaceStr:
                wordTransform = replaceStr.split(splitStr)
                break
        if not wordTransform:
            continue
        if len(wordTransform) == 2:
            replaceStr1 = wordTransform[0].strip().replace('"', '')
            replaceStr2 = wordTransform[1].strip().replace('"', '')
            content = content.replace(replaceStr1, replaceStr2)
    return content


def replaceEmojiFromTags(content: str, tag: [], messageType: str) -> str:
    """Uses the tags to replace :emoji: with html image markup
    """
    for tagItem in tag:
        if not tagItem.get('type'):
            continue
        if tagItem['type'] != 'Emoji':
            continue
        if not tagItem.get('name'):
            continue
        if not tagItem.get('icon'):
            continue
        if not tagItem['icon'].get('url'):
            continue
        if '/' not in tagItem['icon']['url']:
            continue
        if tagItem['name'] not in content:
            continue
        iconName = tagItem['icon']['url'].split('/')[-1]
        if iconName:
            if len(iconName) > 1:
                if iconName[0].isdigit():
                    if '.' in iconName:
                        iconName = iconName.split('.')[0]
                        # see https://unicode.org/
                        # emoji/charts/full-emoji-list.html
                        if '-' not in iconName:
                            # a single code
                            try:
                                replaceChar = chr(int("0x" + iconName, 16))
                                content = content.replace(tagItem['name'],
                                                          replaceChar)
                            except BaseException:
                                print('EX: replaceEmojiFromTags name ' +
                                      str(iconName) + ' ' +
                                      tagItem['name'] + ' ' +
                                      tagItem['icon']['url'])
                                pass
                        else:
                            # sequence of codes
                            iconCodes = iconName.split('-')
                            iconCodeSequence = ''
                            for icode in iconCodes:
                                try:
                                    iconCodeSequence += chr(int("0x" +
                                                                icode, 16))
                                except BaseException:
                                    iconCodeSequence = ''
                                    print('EX: replaceEmojiFromTags code ' +
                                          str(icode) + ' ' +
                                          tagItem['name'] + ' ' +
                                          tagItem['icon']['url'])
                                    break
                            if iconCodeSequence:
                                content = content.replace(tagItem['name'],
                                                          iconCodeSequence)

        htmlClass = 'emoji'
        if messageType == 'post header':
            htmlClass = 'emojiheader'
        if messageType == 'profile':
            htmlClass = 'emojiprofile'
        emojiHtml = "<img src=\"" + tagItem['icon']['url'] + "\" alt=\"" + \
            tagItem['name'].replace(':', '') + \
            "\" align=\"middle\" class=\"" + htmlClass + "\"/>"
        content = content.replace(tagItem['name'], emojiHtml)
    return content


def _addMusicTag(content: str, tag: str) -> str:
    """If a music link is found then ensure that the post is
    tagged appropriately
    """
    if '#podcast' in content or '#documentary' in content:
        return content
    if '#' not in tag:
        tag = '#' + tag
    if tag in content:
        return content
    musicSites = ('soundcloud.com', 'bandcamp.com')
    musicSiteFound = False
    for site in musicSites:
        if site + '/' in content:
            musicSiteFound = True
            break
    if not musicSiteFound:
        return content
    return ':music: ' + content + ' ' + tag + ' '


def addWebLinks(content: str) -> str:
    """Adds markup for web links
    """
    if ':' not in content:
        return content

    prefixes = getLinkPrefixes()

    # do any of these prefixes exist within the content?
    prefixFound = False
    for prefix in prefixes:
        if prefix in content:
            prefixFound = True
            break

    # if there are no prefixes then just keep the content we have
    if not prefixFound:
        return content

    maxLinkLength = 40
    content = content.replace('\r', '')
    words = content.replace('\n', ' --linebreak-- ').split(' ')
    replaceDict = {}
    for w in words:
        if ':' not in w:
            continue
        # does the word begin with a prefix?
        prefixFound = False
        for prefix in prefixes:
            if w.startswith(prefix):
                prefixFound = True
                break
        if not prefixFound:
            continue
        # the word contains a prefix
        if w.endswith('.') or w.endswith(';'):
            w = w[:-1]
        markup = '<a href="' + w + \
            '" rel="nofollow noopener noreferrer" target="_blank">'
        for prefix in prefixes:
            if w.startswith(prefix):
                markup += '<span class="invisible">' + prefix + '</span>'
                break
        linkText = w
        for prefix in prefixes:
            linkText = linkText.replace(prefix, '')
        # prevent links from becoming too long
        if len(linkText) > maxLinkLength:
            markup += '<span class="ellipsis">' + \
                linkText[:maxLinkLength] + '</span>'
            markup += '<span class="invisible">' + \
                linkText[maxLinkLength:] + '</span></a>'
        else:
            markup += '<span class="ellipsis">' + linkText + '</span></a>'
        replaceDict[w] = markup

    # do the replacements
    for url, markup in replaceDict.items():
        content = content.replace(url, markup)

    # replace any line breaks
    content = content.replace(' --linebreak-- ', '<br>')

    return content


def validHashTag(hashtag: str) -> bool:
    """Returns true if the give hashtag contains valid characters
    """
    # long hashtags are not valid
    if len(hashtag) >= 32:
        return False
    validChars = set('0123456789' +
                     'abcdefghijklmnopqrstuvwxyz' +
                     'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
                     '¡¿ÄäÀàÁáÂâÃãÅåǍǎĄąĂăÆæĀā' +
                     'ÇçĆćĈĉČčĎđĐďðÈèÉéÊêËëĚěĘęĖėĒē' +
                     'ĜĝĢģĞğĤĥÌìÍíÎîÏïıĪīĮįĴĵĶķ' +
                     'ĹĺĻļŁłĽľĿŀÑñŃńŇňŅņÖöÒòÓóÔôÕõŐőØøŒœ' +
                     'ŔŕŘřẞßŚśŜŝŞşŠšȘșŤťŢţÞþȚțÜüÙùÚúÛûŰűŨũŲųŮůŪū' +
                     'ŴŵÝýŸÿŶŷŹźŽžŻż')
    if set(hashtag).issubset(validChars):
        return True
    if isValidLanguage(hashtag):
        return True
    return False


def _addHashTags(wordStr: str, httpPrefix: str, domain: str,
                 replaceHashTags: {}, postHashtags: {}) -> bool:
    """Detects hashtags and adds them to the replacements dict
    Also updates the hashtags list to be added to the post
    """
    if replaceHashTags.get(wordStr):
        return True
    hashtag = wordStr[1:]
    if not validHashTag(hashtag):
        return False
    hashtagUrl = httpPrefix + "://" + domain + "/tags/" + hashtag
    postHashtags[hashtag] = {
        'href': hashtagUrl,
        'name': '#' + hashtag,
        'type': 'Hashtag'
    }
    replaceHashTags[wordStr] = "<a href=\"" + hashtagUrl + \
        "\" class=\"mention hashtag\" rel=\"tag\">#<span>" + \
        hashtag + "</span></a>"
    return True


def _addEmoji(baseDir: str, wordStr: str,
              httpPrefix: str, domain: str,
              replaceEmoji: {}, postTags: {},
              emojiDict: {}) -> bool:
    """Detects Emoji and adds them to the replacements dict
    Also updates the tags list to be added to the post
    """
    if not wordStr.startswith(':'):
        return False
    if not wordStr.endswith(':'):
        return False
    if len(wordStr) < 3:
        return False
    if replaceEmoji.get(wordStr):
        return True
    # remove leading and trailing : characters
    emoji = wordStr[1:]
    emoji = emoji[:-1]
    # is the text of the emoji valid?
    if not validHashTag(emoji):
        return False
    if not emojiDict.get(emoji):
        return False
    emojiFilename = baseDir + '/emoji/' + emojiDict[emoji] + '.png'
    if not os.path.isfile(emojiFilename):
        return False
    emojiUrl = httpPrefix + "://" + domain + \
        "/emoji/" + emojiDict[emoji] + '.png'
    postTags[emoji] = {
        'icon': {
            'mediaType': 'image/png',
            'type': 'Image',
            'url': emojiUrl
        },
        'name': ':' + emoji + ':',
        "updated": fileLastModified(emojiFilename),
        "id": emojiUrl.replace('.png', ''),
        'type': 'Emoji'
    }
    return True


def tagExists(tagType: str, tagName: str, tags: {}) -> bool:
    """Returns true if a tag exists in the given dict
    """
    for tag in tags:
        if tag['name'] == tagName and tag['type'] == tagType:
            return True
    return False


def _addMention(wordStr: str, httpPrefix: str, following: str, petnames: str,
                replaceMentions: {}, recipients: [], tags: {}) -> bool:
    """Detects mentions and adds them to the replacements dict and
    recipients list
    """
    possibleHandle = wordStr[1:]
    # @nick
    if following and '@' not in possibleHandle:
        # fall back to a best effort match against the following list
        # if no domain was specified. eg. @nick
        possibleNickname = possibleHandle
        for follow in following:
            if '@' not in follow:
                continue
            followNick = follow.split('@')[0]
            if possibleNickname == followNick:
                followStr = follow.replace('\n', '').replace('\r', '')
                replaceDomain = followStr.split('@')[1]
                recipientActor = httpPrefix + "://" + \
                    replaceDomain + "/@" + possibleNickname
                if recipientActor not in recipients:
                    recipients.append(recipientActor)
                tags[wordStr] = {
                    'href': recipientActor,
                    'name': wordStr,
                    'type': 'Mention'
                }
                replaceMentions[wordStr] = \
                    "<span class=\"h-card\"><a href=\"" + httpPrefix + \
                    "://" + replaceDomain + "/@" + possibleNickname + \
                    "\" class=\"u-url mention\">@<span>" + possibleNickname + \
                    "</span></a></span>"
                return True
        # try replacing petnames with mentions
        followCtr = 0
        for follow in following:
            if '@' not in follow:
                followCtr += 1
                continue
            pet = petnames[followCtr].replace('\n', '')
            if pet:
                if possibleNickname == pet:
                    followStr = follow.replace('\n', '').replace('\r', '')
                    replaceNickname = followStr.split('@')[0]
                    replaceDomain = followStr.split('@')[1]
                    recipientActor = httpPrefix + "://" + \
                        replaceDomain + "/@" + replaceNickname
                    if recipientActor not in recipients:
                        recipients.append(recipientActor)
                    tags[wordStr] = {
                        'href': recipientActor,
                        'name': wordStr,
                        'type': 'Mention'
                    }
                    replaceMentions[wordStr] = \
                        "<span class=\"h-card\"><a href=\"" + httpPrefix + \
                        "://" + replaceDomain + "/@" + replaceNickname + \
                        "\" class=\"u-url mention\">@<span>" + \
                        replaceNickname + "</span></a></span>"
                    return True
            followCtr += 1
        return False
    possibleNickname = None
    possibleDomain = None
    if '@' not in possibleHandle:
        return False
    possibleNickname = possibleHandle.split('@')[0]
    if not possibleNickname:
        return False
    possibleDomain = \
        possibleHandle.split('@')[1].strip('\n').strip('\r')
    if not possibleDomain:
        return False
    if following:
        for follow in following:
            if follow.replace('\n', '').replace('\r', '') != possibleHandle:
                continue
            recipientActor = httpPrefix + "://" + \
                possibleDomain + "/@" + possibleNickname
            if recipientActor not in recipients:
                recipients.append(recipientActor)
            tags[wordStr] = {
                'href': recipientActor,
                'name': wordStr,
                'type': 'Mention'
            }
            replaceMentions[wordStr] = \
                "<span class=\"h-card\"><a href=\"" + httpPrefix + \
                "://" + possibleDomain + "/@" + possibleNickname + \
                "\" class=\"u-url mention\">@<span>" + possibleNickname + \
                "</span></a></span>"
            return True
    # @nick@domain
    if not (possibleDomain == 'localhost' or '.' in possibleDomain):
        return False
    recipientActor = httpPrefix + "://" + \
        possibleDomain + "/@" + possibleNickname
    if recipientActor not in recipients:
        recipients.append(recipientActor)
    tags[wordStr] = {
        'href': recipientActor,
        'name': wordStr,
        'type': 'Mention'
    }
    replaceMentions[wordStr] = \
        "<span class=\"h-card\"><a href=\"" + httpPrefix + \
        "://" + possibleDomain + "/@" + possibleNickname + \
        "\" class=\"u-url mention\">@<span>" + possibleNickname + \
        "</span></a></span>"
    return True


def replaceContentDuplicates(content: str) -> str:
    """Replaces invalid duplicates within content
    """
    if isPGPEncrypted(content) or containsPGPPublicKey(content):
        return content
    while '<<' in content:
        content = content.replace('<<', '<')
    while '>>' in content:
        content = content.replace('>>', '>')
    content = content.replace('<\\p>', '')
    return content


def removeTextFormatting(content: str) -> str:
    """Removes markup for bold, italics, etc
    """
    if isPGPEncrypted(content) or containsPGPPublicKey(content):
        return content
    if '<' not in content:
        return content
    removeMarkup = ('b', 'i', 'ul', 'ol', 'li', 'em', 'strong',
                    'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5')
    for markup in removeMarkup:
        content = content.replace('<' + markup + '>', '')
        content = content.replace('</' + markup + '>', '')
        content = content.replace('<' + markup.upper() + '>', '')
        content = content.replace('</' + markup.upper() + '>', '')
    return content


def removeLongWords(content: str, maxWordLength: int,
                    longWordsList: []) -> str:
    """Breaks up long words so that on mobile screens this doesn't
    disrupt the layout
    """
    if isPGPEncrypted(content) or containsPGPPublicKey(content):
        return content
    content = replaceContentDuplicates(content)
    if ' ' not in content:
        # handle a single very long string with no spaces
        contentStr = content.replace('<p>', '').replace(r'<\p>', '')
        if '://' not in contentStr:
            if len(contentStr) > maxWordLength:
                if '<p>' in content:
                    content = '<p>' + contentStr[:maxWordLength] + r'<\p>'
                else:
                    content = content[:maxWordLength]
                return content
    words = content.split(' ')
    if not longWordsList:
        longWordsList = []
        for wordStr in words:
            if len(wordStr) > maxWordLength:
                if wordStr not in longWordsList:
                    longWordsList.append(wordStr)
    for wordStr in longWordsList:
        if wordStr.startswith('<p>'):
            wordStr = wordStr.replace('<p>', '')
        if wordStr.startswith('<'):
            continue
        if len(wordStr) == 76:
            if wordStr.upper() == wordStr:
                # tox address
                continue
        if '=\"' in wordStr:
            continue
        if '@' in wordStr:
            if '@@' not in wordStr:
                continue
        if '=.ed25519' in wordStr:
            continue
        if '.onion' in wordStr:
            continue
        if '.i2p' in wordStr:
            continue
        if 'https:' in wordStr:
            continue
        elif 'http:' in wordStr:
            continue
        elif 'i2p:' in wordStr:
            continue
        elif 'gnunet:' in wordStr:
            continue
        elif 'dat:' in wordStr:
            continue
        elif 'rad:' in wordStr:
            continue
        elif 'hyper:' in wordStr:
            continue
        elif 'briar:' in wordStr:
            continue
        if '<' in wordStr:
            replaceWord = wordStr.split('<', 1)[0]
            # if len(replaceWord) > maxWordLength:
            #     replaceWord = replaceWord[:maxWordLength]
            content = content.replace(wordStr, replaceWord)
            wordStr = replaceWord
        if '/' in wordStr:
            continue
        if len(wordStr[maxWordLength:]) < maxWordLength:
            content = content.replace(wordStr,
                                      wordStr[:maxWordLength] + '\n' +
                                      wordStr[maxWordLength:])
        else:
            content = content.replace(wordStr,
                                      wordStr[:maxWordLength])
    if content.startswith('<p>'):
        if not content.endswith('</p>'):
            content = content.strip() + '</p>'
    return content


def _loadAutoTags(baseDir: str, nickname: str, domain: str) -> []:
    """Loads automatic tags file and returns a list containing
    the lines of the file
    """
    filename = acctDir(baseDir, nickname, domain) + '/autotags.txt'
    if not os.path.isfile(filename):
        return []
    with open(filename, 'r') as f:
        return f.readlines()
    return []


def _autoTag(baseDir: str, nickname: str, domain: str,
             wordStr: str, autoTagList: [],
             appendTags: []):
    """Generates a list of tags to be automatically appended to the content
    """
    for tagRule in autoTagList:
        if wordStr not in tagRule:
            continue
        if '->' not in tagRule:
            continue
        rulematch = tagRule.split('->')[0].strip()
        if rulematch != wordStr:
            continue
        tagName = tagRule.split('->')[1].strip()
        if tagName.startswith('#'):
            if tagName not in appendTags:
                appendTags.append(tagName)
        else:
            if '#' + tagName not in appendTags:
                appendTags.append('#' + tagName)


def addHtmlTags(baseDir: str, httpPrefix: str,
                nickname: str, domain: str, content: str,
                recipients: [], hashtags: {},
                isJsonContent: bool = False) -> str:
    """ Replaces plaintext mentions such as @nick@domain into html
    by matching against known following accounts
    """
    if content.startswith('<p>'):
        content = htmlReplaceEmailQuote(content)
        return htmlReplaceQuoteMarks(content)
    maxWordLength = 40
    content = content.replace('\r', '')
    content = content.replace('\n', ' --linebreak-- ')
    content = _addMusicTag(content, 'nowplaying')
    contentSimplified = \
        content.replace(',', ' ').replace(';', ' ').replace('- ', ' ')
    contentSimplified = contentSimplified.replace('. ', ' ').strip()
    if contentSimplified.endswith('.'):
        contentSimplified = contentSimplified[:len(contentSimplified)-1]
    words = contentSimplified.split(' ')

    # remove . for words which are not mentions
    newWords = []
    for wordIndex in range(0, len(words)):
        wordStr = words[wordIndex]
        if wordStr.endswith('.'):
            if not wordStr.startswith('@'):
                wordStr = wordStr[:-1]
        if wordStr.startswith('.'):
            wordStr = wordStr[1:]
        newWords.append(wordStr)
    words = newWords

    replaceMentions = {}
    replaceHashTags = {}
    replaceEmoji = {}
    emojiDict = {}
    originalDomain = domain
    domain = removeDomainPort(domain)
    followingFilename = acctDir(baseDir, nickname, domain) + '/following.txt'

    # read the following list so that we can detect just @nick
    # in addition to @nick@domain
    following = None
    petnames = None
    if '@' in words:
        if os.path.isfile(followingFilename):
            with open(followingFilename, 'r') as f:
                following = f.readlines()
                for handle in following:
                    pet = getPetName(baseDir, nickname, domain, handle)
                    if pet:
                        petnames.append(pet + '\n')

    # extract mentions and tags from words
    longWordsList = []
    prevWordStr = ''
    autoTagsList = _loadAutoTags(baseDir, nickname, domain)
    appendTags = []
    for wordStr in words:
        wordLen = len(wordStr)
        if wordLen > 2:
            if wordLen > maxWordLength:
                longWordsList.append(wordStr)
            firstChar = wordStr[0]
            if firstChar == '@':
                if _addMention(wordStr, httpPrefix, following, petnames,
                               replaceMentions, recipients, hashtags):
                    prevWordStr = ''
                    continue
            elif firstChar == '#':
                # remove any endings from the hashtag
                hashTagEndings = ('.', ':', ';', '-', '\n')
                for ending in hashTagEndings:
                    if wordStr.endswith(ending):
                        wordStr = wordStr[:len(wordStr) - 1]
                        break

                if _addHashTags(wordStr, httpPrefix, originalDomain,
                                replaceHashTags, hashtags):
                    prevWordStr = ''
                    continue
            elif ':' in wordStr:
                wordStr2 = wordStr.split(':')[1]
#                print('TAG: emoji located - ' + wordStr)
                if not emojiDict:
                    # emoji.json is generated so that it can be customized and
                    # the changes will be retained even if default_emoji.json
                    # is subsequently updated
                    if not os.path.isfile(baseDir + '/emoji/emoji.json'):
                        copyfile(baseDir + '/emoji/default_emoji.json',
                                 baseDir + '/emoji/emoji.json')
                emojiDict = loadJson(baseDir + '/emoji/emoji.json')

#                print('TAG: looking up emoji for :' + wordStr2 + ':')
                _addEmoji(baseDir, ':' + wordStr2 + ':', httpPrefix,
                          originalDomain, replaceEmoji, hashtags,
                          emojiDict)
            else:
                if _autoTag(baseDir, nickname, domain, wordStr,
                            autoTagsList, appendTags):
                    prevWordStr = ''
                    continue
                if prevWordStr:
                    if _autoTag(baseDir, nickname, domain,
                                prevWordStr + ' ' + wordStr,
                                autoTagsList, appendTags):
                        prevWordStr = ''
                        continue
            prevWordStr = wordStr

    # add any auto generated tags
    for appended in appendTags:
        content = content + ' ' + appended
        _addHashTags(appended, httpPrefix, originalDomain,
                     replaceHashTags, hashtags)

    # replace words with their html versions
    for wordStr, replaceStr in replaceMentions.items():
        content = content.replace(wordStr, replaceStr)
    for wordStr, replaceStr in replaceHashTags.items():
        content = content.replace(wordStr, replaceStr)
    if not isJsonContent:
        for wordStr, replaceStr in replaceEmoji.items():
            content = content.replace(wordStr, replaceStr)

    content = addWebLinks(content)
    if longWordsList:
        content = removeLongWords(content, maxWordLength, longWordsList)
    content = limitRepeatedWords(content, 6)
    content = content.replace(' --linebreak-- ', '</p><p>')
    content = htmlReplaceEmailQuote(content)
    return '<p>' + htmlReplaceQuoteMarks(content) + '</p>'


def getMentionsFromHtml(htmlText: str,
                        matchStr="<span class=\"h-card\"><a href=\"") -> []:
    """Extracts mentioned actors from the given html content string
    """
    mentions = []
    if matchStr not in htmlText:
        return mentions
    mentionsList = htmlText.split(matchStr)
    for mentionStr in mentionsList:
        if '"' not in mentionStr:
            continue
        actorStr = mentionStr.split('"')[0]
        if actorStr.startswith('http') or \
           actorStr.startswith('gnunet') or \
           actorStr.startswith('i2p') or \
           actorStr.startswith('hyper') or \
           actorStr.startswith('dat:'):
            if actorStr not in mentions:
                mentions.append(actorStr)
    return mentions


def extractMediaInFormPOST(postBytes, boundary, name: str):
    """Extracts the binary encoding for image/video/audio within a http
    form POST
    Returns the media bytes and the remaining bytes
    """
    imageStartBoundary = b'Content-Disposition: form-data; name="' + \
        name.encode('utf8', 'ignore') + b'";'
    imageStartLocation = postBytes.find(imageStartBoundary)
    if imageStartLocation == -1:
        return None, postBytes

    # bytes after the start boundary appears
    mediaBytes = postBytes[imageStartLocation:]

    # look for the next boundary
    imageEndBoundary = boundary.encode('utf8', 'ignore')
    imageEndLocation = mediaBytes.find(imageEndBoundary)
    if imageEndLocation == -1:
        # no ending boundary
        return mediaBytes, postBytes[:imageStartLocation]

    # remaining bytes after the end of the image
    remainder = mediaBytes[imageEndLocation:]

    # remove bytes after the end boundary
    mediaBytes = mediaBytes[:imageEndLocation]

    # return the media and the before+after bytes
    return mediaBytes, postBytes[:imageStartLocation] + remainder


def saveMediaInFormPOST(mediaBytes, debug: bool,
                        filenameBase: str = None) -> (str, str):
    """Saves the given media bytes extracted from http form POST
    Returns the filename and attachment type
    """
    if not mediaBytes:
        if filenameBase:
            # remove any existing files
            extensionTypes = getImageExtensions()
            for ex in extensionTypes:
                possibleOtherFormat = filenameBase + '.' + ex
                if os.path.isfile(possibleOtherFormat):
                    try:
                        os.remove(possibleOtherFormat)
                    except BaseException:
                        if debug:
                            print('EX: saveMediaInFormPOST ' +
                                  'unable to delete other ' +
                                  str(possibleOtherFormat))
                        pass
            if os.path.isfile(filenameBase):
                try:
                    os.remove(filenameBase)
                except BaseException:
                    if debug:
                        print('EX: saveMediaInFormPOST ' +
                              'unable to delete ' +
                              str(filenameBase))
                    pass

        if debug:
            print('DEBUG: No media found within POST')
        return None, None

    mediaLocation = -1
    searchStr = ''
    filename = None

    # directly search the binary array for the beginning
    # of an image
    extensionList = {
        'png': 'image/png',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        'avif': 'image/avif',
        'mp4': 'video/mp4',
        'ogv': 'video/ogv',
        'mp3': 'audio/mpeg',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'zip': 'application/zip'
    }
    detectedExtension = None
    for extension, contentType in extensionList.items():
        searchStr = b'Content-Type: ' + contentType.encode('utf8', 'ignore')
        mediaLocation = mediaBytes.find(searchStr)
        if mediaLocation > -1:
            # image/video/audio binaries
            if extension == 'jpeg':
                extension = 'jpg'
            elif extension == 'mpeg':
                extension = 'mp3'
            if filenameBase:
                filename = filenameBase + '.' + extension
            attachmentMediaType = \
                searchStr.decode().split('/')[0].replace('Content-Type: ', '')
            detectedExtension = extension
            break

    if not filename:
        return None, None

    # locate the beginning of the image, after any
    # carriage returns
    startPos = mediaLocation + len(searchStr)
    for offset in range(1, 8):
        if mediaBytes[startPos+offset] != 10:
            if mediaBytes[startPos+offset] != 13:
                startPos += offset
                break

    # remove any existing image files with a different format
    if detectedExtension != 'zip':
        extensionTypes = getImageExtensions()
        for ex in extensionTypes:
            if ex == detectedExtension:
                continue
            possibleOtherFormat = \
                filename.replace('.temp', '').replace('.' +
                                                      detectedExtension, '.' +
                                                      ex)
            if os.path.isfile(possibleOtherFormat):
                try:
                    os.remove(possibleOtherFormat)
                except BaseException:
                    if debug:
                        print('EX: saveMediaInFormPOST ' +
                              'unable to delete other 2 ' +
                              str(possibleOtherFormat))
                    pass

    # don't allow scripts within svg files
    if detectedExtension == 'svg':
        svgStr = mediaBytes[startPos:]
        svgStr = svgStr.decode()
        if dangerousSVG(svgStr, False):
            return None, None

    with open(filename, 'wb') as fp:
        fp.write(mediaBytes[startPos:])

    if not os.path.isfile(filename):
        print('WARN: Media file could not be written to file: ' + filename)
        return None, None
    print('Uploaded media file written: ' + filename)

    return filename, attachmentMediaType


def extractTextFieldsInPOST(postBytes, boundary: str, debug: bool,
                            unitTestData: str = None) -> {}:
    """Returns a dictionary containing the text fields of a http form POST
    The boundary argument comes from the http header
    """
    if not unitTestData:
        msgBytes = email.parser.BytesParser().parsebytes(postBytes)
        messageFields = msgBytes.get_payload(decode=True).decode('utf-8')
    else:
        messageFields = unitTestData

    if debug:
        print('DEBUG: POST arriving ' + messageFields)

    messageFields = messageFields.split(boundary)
    fields = {}
    fieldsWithSemicolonAllowed = (
        'message', 'bio', 'autoCW', 'password', 'passwordconfirm',
        'instanceDescription', 'instanceDescriptionShort',
        'subject', 'location', 'imageDescription'
    )
    # examine each section of the POST, separated by the boundary
    for f in messageFields:
        if f == '--':
            continue
        if ' name="' not in f:
            continue
        postStr = f.split(' name="', 1)[1]
        if '"' not in postStr:
            continue
        postKey = postStr.split('"', 1)[0]
        postValueStr = postStr.split('"', 1)[1]
        if ';' in postValueStr:
            if postKey not in fieldsWithSemicolonAllowed and \
               not postKey.startswith('edited'):
                continue
        if '\r\n' not in postValueStr:
            continue
        postLines = postValueStr.split('\r\n')
        postValue = ''
        if len(postLines) > 2:
            for line in range(2, len(postLines)-1):
                if line > 2:
                    postValue += '\n'
                postValue += postLines[line]
        fields[postKey] = urllib.parse.unquote(postValue)
    return fields


def limitRepeatedWords(text: str, maxRepeats: int) -> str:
    """Removes words which are repeated many times
    """
    words = text.replace('\n', ' ').split(' ')
    repeatCtr = 0
    repeatedText = ''
    replacements = {}
    prevWord = ''
    for word in words:
        if word == prevWord:
            repeatCtr += 1
            if repeatedText:
                repeatedText += ' ' + word
            else:
                repeatedText = word + ' ' + word
        else:
            if repeatCtr > maxRepeats:
                newText = ((prevWord + ' ') * maxRepeats).strip()
                replacements[prevWord] = [repeatedText, newText]
            repeatCtr = 0
            repeatedText = ''
        prevWord = word

    if repeatCtr > maxRepeats:
        newText = ((prevWord + ' ') * maxRepeats).strip()
        replacements[prevWord] = [repeatedText, newText]

    for word, item in replacements.items():
        text = text.replace(item[0], item[1])
    return text


def getPriceFromString(priceStr: str) -> (str, str):
    """Returns the item price and currency
    """
    currencies = getCurrencies()
    for symbol, name in currencies.items():
        if symbol in priceStr:
            price = priceStr.replace(symbol, '')
            if isfloat(price):
                return price, name
        elif name in priceStr:
            price = priceStr.replace(name, '')
            if isfloat(price):
                return price, name
    if isfloat(priceStr):
        return priceStr, "EUR"
    return "0.00", "EUR"


def _wordsSimilarityHistogram(words: []) -> {}:
    """Returns a histogram for word combinations
    """
    histogram = {}
    for index in range(1, len(words)):
        combinedWords = words[index - 1] + words[index]
        if histogram.get(combinedWords):
            histogram[combinedWords] += 1
        else:
            histogram[combinedWords] = 1
    return histogram


def _wordsSimilarityWordsList(content: str) -> []:
    """Returns a list of words for the given content
    """
    removePunctuation = ('.', ',', ';', '-', ':', '"')
    content = removeHtml(content).lower()
    for p in removePunctuation:
        content = content.replace(p, ' ')
        content = content.replace('  ', ' ')
    return content.split(' ')


def wordsSimilarity(content1: str, content2: str, minWords: int) -> int:
    """Returns percentage similarity
    """
    if content1 == content2:
        return 100

    words1 = _wordsSimilarityWordsList(content1)
    if len(words1) < minWords:
        return 0

    words2 = _wordsSimilarityWordsList(content2)
    if len(words2) < minWords:
        return 0

    histogram1 = _wordsSimilarityHistogram(words1)
    histogram2 = _wordsSimilarityHistogram(words2)

    diff = 0
    for combinedWords, hits in histogram1.items():
        if not histogram2.get(combinedWords):
            diff += 1
        else:
            diff += abs(histogram2[combinedWords] - histogram1[combinedWords])
    return 100 - int(diff * 100 / len(histogram1.items()))


def containsInvalidLocalLinks(content: str) -> bool:
    """Returns true if the given content has invalid links
    """
    invalidStrings = (
        'mute', 'unmute', 'editeventpost', 'notifypost',
        'delete', 'options', 'page', 'repeat',
        'bm', 'tl', 'actor', 'unrepeat',
        'unannounce', 'like', 'unlike', 'bookmark',
        'unbookmark', 'likedBy', 'id', 'time',
        'year', 'month', 'day', 'editnewpost',
        'graph', 'showshare', 'category', 'showwanted',
        'rmshare', 'rmwanted', 'repeatprivate',
        'unrepeatprivate', 'replyto',
        'replyfollowers', 'replydm', 'editblogpost',
        'handle', 'blockdomain'
    )
    for invStr in invalidStrings:
        if '?' + invStr + '=' in content:
            return True
    return False
