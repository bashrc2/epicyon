__filename__ = "session.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import requests
from utils import urlPermitted
import json
from socket import error as SocketError
import errno
from datetime import datetime

baseDirectory = None


def createSession(proxyType: str):
    session = None
    try:
        session = requests.session()
    except requests.exceptions.RequestException as e:
        print('WARN: requests error during createSession')
        print(e)
        return None
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during createSession')
        else:
            print('WARN: socket error during createSession')
        print(e)
        return None
    except ValueError as e:
        print('WARN: error during createSession')
        print(e)
        return None
    if not session:
        return None
    if proxyType == 'tor':
        session.proxies = {}
        session.proxies['http'] = 'socks5h://localhost:9050'
        session.proxies['https'] = 'socks5h://localhost:9050'
    elif proxyType == 'i2p':
        session.proxies = {}
        session.proxies['http'] = 'socks5h://localhost:4447'
        session.proxies['https'] = 'socks5h://localhost:4447'
    elif proxyType == 'gnunet':
        session.proxies = {}
        session.proxies['http'] = 'socks5h://localhost:7777'
        session.proxies['https'] = 'socks5h://localhost:7777'
    # print('New session created with proxy ' + str(proxyType))
    return session


def getJson(session, url: str, headers: {}, params: {},
            version='1.1.0', httpPrefix='https',
            domain='testdomain') -> {}:
    if not isinstance(url, str):
        print('url: ' + str(url))
        print('ERROR: getJson url should be a string')
        return None
    sessionParams = {}
    sessionHeaders = {}
    if headers:
        sessionHeaders = headers
    if params:
        sessionParams = params
    sessionHeaders['User-Agent'] = 'Epicyon/' + version
    if domain:
        sessionHeaders['User-Agent'] += \
            '; +' + httpPrefix + '://' + domain + '/'
    if not session:
        print('WARN: no session specified for getJson')
    try:
        result = session.get(url, headers=sessionHeaders, params=sessionParams)
        return result.json()
    except requests.exceptions.RequestException as e:
        print('ERROR: getJson failed\nurl: ' + str(url) + '\n' +
              'headers: ' + str(sessionHeaders) + '\n' +
              'params: ' + str(sessionParams) + '\n')
        print(e)
    except ValueError as e:
        print('ERROR: getJson failed\nurl: ' + str(url) + '\n' +
              'headers: ' + str(sessionHeaders) + '\n' +
              'params: ' + str(sessionParams) + '\n')
        print(e)
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during getJson')
        print(e)
    return None


def xml2StrToDict(xmlStr: str) -> {}:
    """Converts an xml 2.0 string to a dictionary
    """
    if '<item>' not in xmlStr:
        return {}
    result = {}
    rssItems = xmlStr.split('<item>')
    for rssItem in rssItems:
        if '<title>' not in rssItem:
            continue
        if '</title>' not in rssItem:
            continue
        if '<link>' not in rssItem:
            continue
        if '</link>' not in rssItem:
            continue
        if '<pubDate>' not in rssItem:
            continue
        if '</pubDate>' not in rssItem:
            continue
        title = rssItem.split('<title>')[1]
        title = title.split('</title>')[0]
        link = rssItem.split('<link>')[1]
        link = link.split('</link>')[0]
        pubDate = rssItem.split('<pubDate>')[1]
        pubDate = pubDate.split('</pubDate>')[0]
        try:
            publishedDate = \
                datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %z")
            result[str(publishedDate)] = [title, link]
        except BaseException:
            pass
    return result


def xmlStrToDict(xmlStr: str) -> {}:
    """Converts an xml string to a dictionary
    """
    if 'rss version="2.0"' in xmlStr:
        return xml2StrToDict(xmlStr)
    return {}


def getRSS(session, url: str) -> {}:
    """Returns an RSS url as a dict
    """
    if not isinstance(url, str):
        print('url: ' + str(url))
        print('ERROR: getRSS url should be a string')
        return None
    headers = {
        'Accept': 'text/xml; charset=UTF-8'
    }
    params = None
    sessionParams = {}
    sessionHeaders = {}
    if headers:
        sessionHeaders = headers
    if params:
        sessionParams = params
    sessionHeaders['User-Agent'] = \
        'Mozilla/5.0 (X11; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0'
    if not session:
        print('WARN: no session specified for getRSS')
    try:
        result = session.get(url, headers=sessionHeaders, params=sessionParams)
        return xmlStrToDict(result.text)
    except requests.exceptions.RequestException as e:
        print('ERROR: getRSS failed\nurl: ' + str(url) + '\n' +
              'headers: ' + str(sessionHeaders) + '\n' +
              'params: ' + str(sessionParams) + '\n')
        print(e)
    except ValueError as e:
        print('ERROR: getRSS failed\nurl: ' + str(url) + '\n' +
              'headers: ' + str(sessionHeaders) + '\n' +
              'params: ' + str(sessionParams) + '\n')
        print(e)
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during getRSS')
        print(e)
    return None


def postJson(session, postJsonObject: {}, federationList: [],
             inboxUrl: str, headers: {}) -> str:
    """Post a json message to the inbox of another person
    """
    # check that we are posting to a permitted domain
    if not urlPermitted(inboxUrl, federationList):
        print('postJson: ' + inboxUrl + ' not permitted')
        return None

    try:
        postResult = \
            session.post(url=inboxUrl,
                         data=json.dumps(postJsonObject),
                         headers=headers)
    except requests.exceptions.RequestException as e:
        print('ERROR: postJson requests failed ' + inboxUrl + ' ' +
              json.dumps(postJsonObject) + ' ' + str(headers))
        print(e)
        return None
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during postJson')
        return None
    except ValueError as e:
        print('ERROR: postJson failed ' + inboxUrl + ' ' +
              json.dumps(postJsonObject) + ' ' + str(headers))
        print(e)
        return None
    if postResult:
        return postResult.text
    return None


def postJsonString(session, postJsonStr: str,
                   federationList: [],
                   inboxUrl: str,
                   headers: {},
                   debug: bool) -> (bool, bool):
    """Post a json message string to the inbox of another person
    The second boolean returned is true if the send is unauthorized
    NOTE: Here we post a string rather than the original json so that
    conversions between string and json format don't invalidate
    the message body digest of http signatures
    """
    try:
        postResult = \
            session.post(url=inboxUrl, data=postJsonStr, headers=headers)
    except requests.exceptions.RequestException as e:
        print('WARN: error during postJsonString requests')
        print(e)
        return None, None
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during postJsonString')
        print('ERROR: postJsonString failed ' + inboxUrl + ' ' +
              postJsonStr + ' ' + str(headers))
        return None, None
    except ValueError as e:
        print('WARN: error during postJsonString')
        print(e)
        return None, None
    if postResult.status_code < 200 or postResult.status_code > 202:
        if postResult.status_code >= 400 and \
           postResult.status_code <= 405 and \
           postResult.status_code != 404:
            print('WARN: Post to ' + inboxUrl + ' is unauthorized. Code ' +
                  str(postResult.status_code))
            return False, True
        else:
            print('WARN: Failed to post to ' + inboxUrl +
                  ' with headers ' + str(headers))
            print('status code ' + str(postResult.status_code))
            return False, False
    return True, False


def postImage(session, attachImageFilename: str, federationList: [],
              inboxUrl: str, headers: {}) -> str:
    """Post an image to the inbox of another person or outbox via c2s
    """
    # check that we are posting to a permitted domain
    if not urlPermitted(inboxUrl, federationList):
        print('postJson: ' + inboxUrl + ' not permitted')
        return None

    if not (attachImageFilename.endswith('.jpg') or
            attachImageFilename.endswith('.jpeg') or
            attachImageFilename.endswith('.png') or
            attachImageFilename.endswith('.gif')):
        print('Image must be png, jpg, or gif')
        return None
    if not os.path.isfile(attachImageFilename):
        print('Image not found: ' + attachImageFilename)
        return None
    contentType = 'image/jpeg'
    if attachImageFilename.endswith('.png'):
        contentType = 'image/png'
    if attachImageFilename.endswith('.gif'):
        contentType = 'image/gif'
    headers['Content-type'] = contentType

    with open(attachImageFilename, 'rb') as avFile:
        mediaBinary = avFile.read()
        try:
            postResult = session.post(url=inboxUrl, data=mediaBinary,
                                      headers=headers)
        except requests.exceptions.RequestException as e:
            print('WARN: error during postImage requests')
            print(e)
            return None
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: connection was reset during postImage')
            print('ERROR: postImage failed ' + inboxUrl + ' ' +
                  str(headers))
            print(e)
            return None
        except ValueError as e:
            print('WARN: error during postImage')
            print(e)
            return None
        if postResult:
            return postResult.text
    return None
