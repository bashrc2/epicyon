__filename__ = "session.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import requests
from utils import urlPermitted
import json
from socket import error as SocketError
import errno

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
            version='1.2.0', httpPrefix='https',
            domain='testdomain') -> {}:
    if not isinstance(url, str):
        print('url: ' + str(url))
        print('ERROR: getJson failed, url should be a string')
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
        print('WARN: getJson failed, no session specified for getJson')
    try:
        result = session.get(url, headers=sessionHeaders, params=sessionParams)
        return result.json()
    except requests.exceptions.RequestException as e:
        print('ERROR: getJson failed\nurl: ' + str(url) + ' ' +
              'headers: ' + str(sessionHeaders) + ' ' +
              'params: ' + str(sessionParams))
        print(e)
    except ValueError as e:
        print('ERROR: getJson failed\nurl: ' + str(url) + ' ' +
              'headers: ' + str(sessionHeaders) + ' ' +
              'params: ' + str(sessionParams) + ' ')
        print(e)
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: getJson failed, connection was reset during getJson')
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
            attachImageFilename.endswith('.svg') or
            attachImageFilename.endswith('.gif')):
        print('Image must be png, jpg, gif or svg')
        return None
    if not os.path.isfile(attachImageFilename):
        print('Image not found: ' + attachImageFilename)
        return None
    contentType = 'image/jpeg'
    if attachImageFilename.endswith('.png'):
        contentType = 'image/png'
    if attachImageFilename.endswith('.gif'):
        contentType = 'image/gif'
    if attachImageFilename.endswith('.svg'):
        contentType = 'image/svg+xml'
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
