__filename__ = "languages.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"
__module_group__ = "Core"

import os
from utils import acctDir
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
        return propertyValue['value']
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
        languageFilename = baseDir + '/translations/' + lang + '.json'
        if os.path.isfile(languageFilename):
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
    if msgObject.get('object'):
        if isinstance(msgObject['object'], dict):
            msgObject = messageJson['object']
    if not msgObject.get('contentMap'):
        return True
    if not isinstance(msgObject['contentMap'], dict):
        return True
    if msgObject['contentMap'].get(systemLanguage):
        return True
    actorFilename = acctDir(baseDir, nickname, domain)
    if not os.path.isfile(actorFilename):
        return False
    personUrl = httpPrefix + '://' + domainFull + '/users/' + nickname
    actorJson = getPersonFromCache(baseDir, personUrl, personCache, False)
    if not actorJson:
        print('WARN: unable to load actor to check languages ' + actorFilename)
        return False
    languagesUnderstood = _getActorLanguagesList(actorJson)
    if not languagesUnderstood:
        return True
    for lang in languagesUnderstood:
        if msgObject['contentMap'].get(lang):
            return True
    return False
