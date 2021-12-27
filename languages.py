__filename__ = "languages.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import json
from urllib import request, parse
from utils import get_actor_languages_list
from utils import remove_html
from utils import has_object_dict
from utils import get_config_param
from utils import local_actor_url
from cache import getPersonFromCache


def getActorLanguages(actor_json: {}) -> str:
    """Returns a string containing languages used by the given actor
    """
    lang_list = get_actor_languages_list(actor_json)
    if not lang_list:
        return ''
    languagesStr = ''
    for lang in lang_list:
        if languagesStr:
            languagesStr += ' / ' + lang
        else:
            languagesStr = lang
    return languagesStr


def setActorLanguages(base_dir: str, actor_json: {},
                      languagesStr: str) -> None:
    """Sets the languages used by the given actor
    """
    separator = ','
    if '/' in languagesStr:
        separator = '/'
    elif ',' in languagesStr:
        separator = ','
    elif ';' in languagesStr:
        separator = ';'
    elif '+' in languagesStr:
        separator = '+'
    elif ' ' in languagesStr:
        separator = ' '
    lang_list = languagesStr.lower().split(separator)
    lang_list2 = ''
    for lang in lang_list:
        lang = lang.strip()
        if base_dir:
            languageFilename = base_dir + '/translations/' + lang + '.json'
            if os.path.isfile(languageFilename):
                if lang_list2:
                    lang_list2 += ', ' + lang.strip()
                else:
                    lang_list2 += lang.strip()
        else:
            if lang_list2:
                lang_list2 += ', ' + lang.strip()
            else:
                lang_list2 += lang.strip()

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('languages'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)

    if not lang_list2:
        return

    newLanguages = {
        "name": "Languages",
        "type": "PropertyValue",
        "value": lang_list2
    }
    actor_json['attachment'].append(newLanguages)


def understoodPostLanguage(base_dir: str, nickname: str, domain: str,
                           message_json: {}, system_language: str,
                           http_prefix: str, domain_full: str,
                           person_cache: {}) -> bool:
    """Returns true if the post is written in a language
    understood by this account
    """
    msgObject = message_json
    if has_object_dict(message_json):
        msgObject = message_json['object']
    if not msgObject.get('contentMap'):
        return True
    if not isinstance(msgObject['contentMap'], dict):
        return True
    if msgObject['contentMap'].get(system_language):
        return True
    personUrl = local_actor_url(http_prefix, nickname, domain_full)
    actor_json = getPersonFromCache(base_dir, personUrl, person_cache, False)
    if not actor_json:
        print('WARN: unable to load actor to check languages ' + personUrl)
        return False
    languages_understood = get_actor_languages_list(actor_json)
    if not languages_understood:
        return True
    for lang in languages_understood:
        if msgObject['contentMap'].get(lang):
            return True
    # is the language for this post supported by libretranslate?
    libretranslateUrl = get_config_param(base_dir, "libretranslateUrl")
    if libretranslateUrl:
        libretranslateApiKey = \
            get_config_param(base_dir, "libretranslateApiKey")
        lang_list = \
            libretranslateLanguages(libretranslateUrl, libretranslateApiKey)
        for lang in lang_list:
            if msgObject['contentMap'].get(lang):
                return True
    return False


def libretranslateLanguages(url: str, apiKey: str = None) -> []:
    """Returns a list of supported languages
    """
    if not url:
        return []
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

    lang_list = []
    for lang in result:
        if not isinstance(lang, dict):
            continue
        if not lang.get('code'):
            continue
        langCode = lang['code']
        if len(langCode) != 2:
            continue
        lang_list.append(langCode)
    lang_list.sort()
    return lang_list


def getLinksFromContent(content: str) -> {}:
    """Returns a list of links within the given content
    """
    if '<a href' not in content:
        return {}
    sections = content.split('<a href')
    first = True
    links = {}
    for subsection in sections:
        if first:
            first = False
            continue
        if '"' not in subsection:
            continue
        url = subsection.split('"')[1].strip()
        if '://' in url and '.' in url and \
           '>' in subsection:
            if url not in links:
                linkText = subsection.split('>')[1]
                if '<' in linkText:
                    linkText = linkText.split('<')[0]
                    links[linkText] = url
    return links


def addLinksToContent(content: str, links: {}) -> str:
    """Adds links back into plain text
    """
    for linkText, url in links.items():
        urlDesc = url
        if linkText.startswith('@') and linkText in content:
            content = \
                content.replace(linkText,
                                '<a href="' + url +
                                '" rel="nofollow noopener ' +
                                'noreferrer" target="_blank">' +
                                linkText + '</a>')
        else:
            if len(urlDesc) > 40:
                urlDesc = urlDesc[:40]
            content += \
                '<p><a href="' + url + \
                '" rel="nofollow noopener noreferrer" target="_blank">' + \
                urlDesc + '</a></p>'
    return content


def libretranslate(url: str, text: str,
                   source: str, target: str, apiKey: str = None) -> str:
    """Translate string using libretranslate
    """
    if not url:
        return None

    if not url.endswith('/translate'):
        if not url.endswith('/'):
            url += "/translate"
        else:
            url += "translate"

    originalText = text

    # get any links from the text
    links = getLinksFromContent(text)

    # LibreTranslate doesn't like markup
    text = remove_html(text)

    # remove any links from plain text version of the content
    for _, url in links.items():
        text = text.replace(url, '')

    ltParams = {
        "q": text,
        "source": source,
        "target": target
    }

    if apiKey:
        ltParams["api_key"] = apiKey

    urlParams = parse.urlencode(ltParams)

    req = request.Request(url, data=urlParams.encode())
    try:
        response = request.urlopen(req)
    except BaseException:
        print('EX: Unable to translate: ' + text)
        return originalText

    response_str = response.read().decode()

    translatedText = \
        '<p>' + json.loads(response_str)['translatedText'] + '</p>'

    # append links form the original text
    if links:
        translatedText = addLinksToContent(translatedText, links)
    return translatedText


def autoTranslatePost(base_dir: str, post_json_object: {},
                      system_language: str, translate: {}) -> str:
    """Tries to automatically translate the given post
    """
    if not has_object_dict(post_json_object):
        return ''
    msgObject = post_json_object['object']
    if not msgObject.get('contentMap'):
        return ''
    if not isinstance(msgObject['contentMap'], dict):
        return ''

    # is the language for this post supported by libretranslate?
    libretranslateUrl = get_config_param(base_dir, "libretranslateUrl")
    if not libretranslateUrl:
        return ''
    libretranslateApiKey = get_config_param(base_dir, "libretranslateApiKey")
    lang_list = \
        libretranslateLanguages(libretranslateUrl, libretranslateApiKey)
    for lang in lang_list:
        if msgObject['contentMap'].get(lang):
            content = msgObject['contentMap'][lang]
            translatedText = \
                libretranslate(libretranslateUrl, content,
                               lang, system_language,
                               libretranslateApiKey)
            if translatedText:
                if remove_html(translatedText) == remove_html(content):
                    return content
                translatedText = \
                    '<p>' + translate['Translated'].upper() + '</p>' + \
                    translatedText
            return translatedText
    return ''
