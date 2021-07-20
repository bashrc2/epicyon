__filename__ = "languages.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"
__module_group__ = "Core"

import os
import json
from urllib import request, parse
from utils import removeHtml
from utils import acctDir
from utils import hasObjectDict
from utils import getConfigParam
from cache import getPersonFromCache


def _getActorLanguagesList(actorJson: {}) -> []:
    """Returns a list containing languages used by the given actor
    """
    if not actorJson.get('attachment'):
        return []
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('languages'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if not isinstance(propertyValue['value'], list):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        langList = propertyValue['value']
        langList.sort()
        return langList
    return []


def getActorLanguages(actorJson: {}) -> str:
    """Returns a string containing languages used by the given actor
    """
    langList = _getActorLanguagesList(actorJson)
    if not langList:
        return ''
    languagesStr = ''
    for lang in langList:
        if languagesStr:
            languagesStr += ' / ' + lang
        else:
            languagesStr = lang
    return languagesStr


def setActorLanguages(baseDir: str, actorJson: {}, languagesStr: str) -> None:
    """Sets the languages used by the given actor
    """
    separator = ','
    if '/' in languagesStr:
        separator = '/'
    elif ';' in languagesStr:
        separator = ';'
    langList = languagesStr.lower().split(separator)
    langList2 = []
    for lang in langList:
        lang = lang.strip()
        if baseDir:
            languageFilename = baseDir + '/translations/' + lang + '.json'
            if os.path.isfile(languageFilename):
                langList2.append(lang)
        else:
            langList2.append(lang)

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('languages'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)

    if not langList2:
        return

    newLanguages = {
        "name": "Languages",
        "type": "PropertyValue",
        "value": langList2
    }
    actorJson['attachment'].append(newLanguages)


def understoodPostLanguage(baseDir: str, nickname: str, domain: str,
                           messageJson: {}, systemLanguage: str,
                           httpPrefix: str, domainFull: str,
                           personCache: {}) -> bool:
    """Returns true if the post is written in a language
    understood by this account
    """
    msgObject = messageJson
    if hasObjectDict(messageJson):
        msgObject = messageJson['object']
    if not msgObject.get('contentMap'):
        return True
    if not isinstance(msgObject['contentMap'], dict):
        return True
    if msgObject['contentMap'].get(systemLanguage):
        return True
    personUrl = httpPrefix + '://' + domainFull + '/users/' + nickname
    actorJson = getPersonFromCache(baseDir, personUrl, personCache, False)
    if not actorJson:
        print('WARN: unable to load actor to check languages ' + personUrl)
        return False
    languagesUnderstood = _getActorLanguagesList(actorJson)
    if not languagesUnderstood:
        return True
    for lang in languagesUnderstood:
        if msgObject['contentMap'].get(lang):
            return True
    # is the language for this post supported by libretranslate?
    libretranslateUrl = getConfigParam(baseDir, "libretranslateUrl")
    if libretranslateUrl:
        libretranslateApiKey = getConfigParam(baseDir, "libretranslateApiKey")
        langList = \
            _libretranslateLanguages(libretranslateUrl, libretranslateApiKey)
        for lang in langList:
            if msgObject['contentMap'].get(lang):
                return True
    return False


def _libretranslateLanguages(url: str, apiKey: str = None) -> []:
    """Returns a list of supported languages
    """
    if not url.endswith('/languages'):
        if not url.endswith('/'):
            url += "/languages"
        else:
            url += "languages"

    params = dict()

    if apiKey:
        params["api_key"] = apiKey

    urlParams = parse.urlencode(params)

    req = request.Request(url, data=urlParams.encode())

    response = request.urlopen(req)

    response_str = response.read().decode()

    result = json.loads(response_str)
    if not result:
        return []
    if not isinstance(result, list):
        return []

    langList = []
    for lang in result:
        if not isinstance(lang, dict):
            continue
        if not lang.get('code'):
            continue
        langCode = lang['code']
        if len(langCode) != 2:
            continue
        langList.append(langCode)
    langList.sort()
    return langList


def getLinksFromContent(content: str) -> []:
    """Returns a list of links within the given content
    """
    if '<a href' not in content:
        return []
    sections = content.split('<a href')
    first = True
    links = []
    for subsection in sections:
        if first:
            first = False
            continue
        if '"' not in subsection:
            continue
        url = subsection.split('"')[1].strip()
        if '://' in url and '.' in url:
            if url not in links:
                links.append(url)
    return links


def _libretranslate(url: str, text: str,
                    source: str, target: str, apiKey: str = None) -> str:
    """Translate string using libretranslate
    """

    if not url.endswith('/translate'):
        if not url.endswith('/'):
            url += "/translate"
        else:
            url += "translate"

    # get any links from the text
    links = getLinksFromContent(text)

    # LibreTranslate doesn't like markup
    text = removeHtml(text)

    ltParams = {
        "q": text,
        "source": source,
        "target": target
    }

    if apiKey:
        ltParams["api_key"] = apiKey

    urlParams = parse.urlencode(ltParams)

    req = request.Request(url, data=urlParams.encode())
    response = request.urlopen(req)

    response_str = response.read().decode()

    translatedText = \
        '<p>' + json.loads(response_str)['translatedText'] + '</p>'

    # append links form the original text
    if links:
        for url in links:
            urlDesc = url
            if len(urlDesc) > 30:
                urlDesc = urlDesc[:30]
            translatedText += \
                '<p><a href="' + url + \
                '" rel="nofollow noopener noreferrer" target="_blank">' + \
                urlDesc + '</a></p>'
    return translatedText


def autoTranslatePost(baseDir: str, postJsonObject: {},
                      systemLanguage: str, translate: {}) -> str:
    """Tries to automatically translate the given post
    """
    if not hasObjectDict(postJsonObject):
        return ''
    msgObject = postJsonObject['object']
    if not msgObject.get('contentMap'):
        return ''
    if not isinstance(msgObject['contentMap'], dict):
        return ''

    # is the language for this post supported by libretranslate?
    libretranslateUrl = getConfigParam(baseDir, "libretranslateUrl")
    if not libretranslateUrl:
        return ''
    libretranslateApiKey = getConfigParam(baseDir, "libretranslateApiKey")
    langList = \
        _libretranslateLanguages(libretranslateUrl, libretranslateApiKey)
    for lang in langList:
        if msgObject['contentMap'].get(lang):
            translatedText = \
                _libretranslate(libretranslateUrl,
                                msgObject['contentMap'][lang],
                                lang, systemLanguage,
                                libretranslateApiKey)
            if translatedText:
                translatedText = \
                    '<p>' + translate['Translated'].upper() + '</p>' + \
                    translatedText
            return translatedText
    return ''
