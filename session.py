__filename__ = "session.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Session"

import os
import requests
from utils import urlPermitted
from utils import isImageFile
from httpsig import createSignedHeader
import json
from socket import error as SocketError
import errno
from http.client import HTTPConnection

baseDirectory = None


def createSession(proxyType: str):
    session = None
    try:
        session = requests.session()
    except requests.exceptions.RequestException as e:
        print('WARN: requests error during createSession ' + str(e))
        return None
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during createSession ' + str(e))
        else:
            print('WARN: socket error during createSession ' + str(e))
        return None
    except ValueError as e:
        print('WARN: error during createSession ' + str(e))
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


def urlExists(session, url: str, timeoutSec: int = 3,
              httpPrefix: str = 'https', domain: str = 'testdomain') -> bool:
    if not isinstance(url, str):
        print('url: ' + str(url))
        print('ERROR: urlExists failed, url should be a string')
        return False
    sessionParams = {}
    sessionHeaders = {}
    sessionHeaders['User-Agent'] = 'Epicyon/' + __version__
    if domain:
        sessionHeaders['User-Agent'] += \
            '; +' + httpPrefix + '://' + domain + '/'
    if not session:
        print('WARN: urlExists failed, no session specified')
        return True
    try:
        result = session.get(url, headers=sessionHeaders,
                             params=sessionParams,
                             timeout=timeoutSec)
        if result:
            if result.status_code == 200 or \
               result.status_code == 304:
                return True
            else:
                print('urlExists for ' + url + ' returned ' +
                      str(result.status_code))
    except BaseException:
        print('EX: urlExists GET failed ' + str(url))
        pass
    return False


def _getJsonRequest(session, url: str, domainFull: str, sessionHeaders: {},
                    sessionParams: {}, timeoutSec: int,
                    signingPrivateKeyPem: str, quiet: bool, debug: bool) -> {}:
    """http GET for json
    """
    try:
        result = session.get(url, headers=sessionHeaders,
                             params=sessionParams, timeout=timeoutSec)
        if result.status_code != 200:
            if result.status_code == 401:
                print("WARN: getJson " + url + ' rejected by secure mode')
            elif result.status_code == 403:
                print('WARN: getJson Forbidden url: ' + url)
            elif result.status_code == 404:
                print('WARN: getJson Not Found url: ' + url)
            elif result.status_code == 410:
                print('WARN: getJson no longer available url: ' + url)
            else:
                print('WARN: getJson url: ' + url +
                      ' failed with error code ' +
                      str(result.status_code) +
                      ' headers: ' + str(sessionHeaders))
        return result.json()
    except requests.exceptions.RequestException as e:
        sessionHeaders2 = sessionHeaders.copy()
        if sessionHeaders2.get('Authorization'):
            sessionHeaders2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('ERROR: getJson failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(sessionHeaders2) + ', ' +
                  'params: ' + str(sessionParams) + ', ' + str(e))
    except ValueError as e:
        sessionHeaders2 = sessionHeaders.copy()
        if sessionHeaders2.get('Authorization'):
            sessionHeaders2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('ERROR: getJson failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(sessionHeaders2) + ', ' +
                  'params: ' + str(sessionParams) + ', ' + str(e))
    except SocketError as e:
        if not quiet:
            if e.errno == errno.ECONNRESET:
                print('WARN: getJson failed, ' +
                      'connection was reset during getJson ' + str(e))
    return None


def _getJsonSigned(session, url: str, domainFull: str, sessionHeaders: {},
                   sessionParams: {}, timeoutSec: int,
                   signingPrivateKeyPem: str, quiet: bool, debug: bool) -> {}:
    """Authorized fetch - a signed version of GET
    """
    if not domainFull:
        if debug:
            print('No sending domain for signed GET')
        return None
    if '://' not in url:
        print('Invalid url: ' + url)
        return None
    httpPrefix = url.split('://')[0]
    toDomainFull = url.split('://')[1]
    if '/' in toDomainFull:
        toDomainFull = toDomainFull.split('/')[0]

    if ':' in domainFull:
        domain = domainFull.split(':')[0]
        port = domainFull.split(':')[1]
    else:
        domain = domainFull
        if httpPrefix == 'https':
            port = 443
        else:
            port = 80

    if ':' in toDomainFull:
        toDomain = toDomainFull.split(':')[0]
        toPort = toDomainFull.split(':')[1]
    else:
        toDomain = toDomainFull
        if httpPrefix == 'https':
            toPort = 443
        else:
            toPort = 80

    if debug:
        print('Signed GET domain: ' + domain + ' ' + str(port))
        print('Signed GET toDomain: ' + toDomain + ' ' + str(toPort))
        print('Signed GET url: ' + url)
        print('Signed GET httpPrefix: ' + httpPrefix)
    messageStr = ''
    withDigest = False
    if toDomainFull + '/' in url:
        path = '/' + url.split(toDomainFull + '/')[1]
    else:
        path = '/actor'
    contentType = 'application/activity+json'
    if sessionHeaders.get('Accept'):
        contentType = sessionHeaders['Accept']
    signatureHeaderJson = \
        createSignedHeader(None, signingPrivateKeyPem, 'actor', domain, port,
                           toDomain, toPort, path, httpPrefix, withDigest,
                           messageStr, contentType)
    if debug:
        print('Signed GET signatureHeaderJson ' + str(signatureHeaderJson))
    # update the session headers from the signature headers
    sessionHeaders['Host'] = signatureHeaderJson['host']
    sessionHeaders['Date'] = signatureHeaderJson['date']
    sessionHeaders['Accept'] = signatureHeaderJson['accept']
    sessionHeaders['Signature'] = signatureHeaderJson['signature']
    sessionHeaders['Content-Length'] = '0'
    if debug:
        print('Signed GET sessionHeaders ' + str(sessionHeaders))

    return _getJsonRequest(session, url, domainFull, sessionHeaders,
                           sessionParams, timeoutSec, None, quiet, debug)


def getJson(signingPrivateKeyPem: str,
            session, url: str, headers: {}, params: {}, debug: bool,
            version: str = '1.2.0', httpPrefix: str = 'https',
            domain: str = 'testdomain',
            timeoutSec: int = 20, quiet: bool = False) -> {}:
    if not isinstance(url, str):
        if debug and not quiet:
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
        if not quiet:
            print('WARN: getJson failed, no session specified for getJson')
        return None

    if debug:
        HTTPConnection.debuglevel = 1

    if signingPrivateKeyPem:
        return _getJsonSigned(session, url, domain,
                              sessionHeaders, sessionParams,
                              timeoutSec, signingPrivateKeyPem,
                              quiet, debug)
    else:
        return _getJsonRequest(session, url, domain, sessionHeaders,
                               sessionParams, timeoutSec,
                               None, quiet, debug)


def postJson(httpPrefix: str, domainFull: str,
             session, postJsonObject: {}, federationList: [],
             inboxUrl: str, headers: {}, timeoutSec: int = 60,
             quiet: bool = False) -> str:
    """Post a json message to the inbox of another person
    """
    # check that we are posting to a permitted domain
    if not urlPermitted(inboxUrl, federationList):
        if not quiet:
            print('postJson: ' + inboxUrl + ' not permitted')
        return None

    sessionHeaders = headers
    sessionHeaders['User-Agent'] = 'Epicyon/' + __version__
    sessionHeaders['User-Agent'] += \
        '; +' + httpPrefix + '://' + domainFull + '/'

    try:
        postResult = \
            session.post(url=inboxUrl,
                         data=json.dumps(postJsonObject),
                         headers=headers, timeout=timeoutSec)
    except requests.Timeout as e:
        if not quiet:
            print('ERROR: postJson timeout ' + inboxUrl + ' ' +
                  json.dumps(postJsonObject) + ' ' + str(headers))
            print(e)
        return ''
    except requests.exceptions.RequestException as e:
        if not quiet:
            print('ERROR: postJson requests failed ' + inboxUrl + ' ' +
                  json.dumps(postJsonObject) + ' ' + str(headers) +
                  ' ' + str(e))
        return None
    except SocketError as e:
        if not quiet and e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during postJson')
        return None
    except ValueError as e:
        if not quiet:
            print('ERROR: postJson failed ' + inboxUrl + ' ' +
                  json.dumps(postJsonObject) + ' ' + str(headers) +
                  ' ' + str(e))
        return None
    if postResult:
        return postResult.text
    return None


def postJsonString(session, postJsonStr: str,
                   federationList: [],
                   inboxUrl: str,
                   headers: {},
                   debug: bool,
                   timeoutSec: int = 30,
                   quiet: bool = False) -> (bool, bool, int):
    """Post a json message string to the inbox of another person
    The second boolean returned is true if the send is unauthorized
    NOTE: Here we post a string rather than the original json so that
    conversions between string and json format don't invalidate
    the message body digest of http signatures
    """
    try:
        postResult = \
            session.post(url=inboxUrl, data=postJsonStr,
                         headers=headers, timeout=timeoutSec)
    except requests.exceptions.RequestException as e:
        if not quiet:
            print('WARN: error during postJsonString requests ' + str(e))
        return None, None, 0
    except SocketError as e:
        if not quiet and e.errno == errno.ECONNRESET:
            print('WARN: connection was reset during postJsonString')
        if not quiet:
            print('ERROR: postJsonString failed ' + inboxUrl + ' ' +
                  postJsonStr + ' ' + str(headers))
        return None, None, 0
    except ValueError as e:
        if not quiet:
            print('WARN: error during postJsonString ' + str(e))
        return None, None, 0
    if postResult.status_code < 200 or postResult.status_code > 202:
        if postResult.status_code >= 400 and \
           postResult.status_code <= 405 and \
           postResult.status_code != 404:
            if not quiet:
                print('WARN: Post to ' + inboxUrl +
                      ' is unauthorized. Code ' +
                      str(postResult.status_code))
            return False, True, postResult.status_code
        else:
            if not quiet:
                print('WARN: Failed to post to ' + inboxUrl +
                      ' with headers ' + str(headers) +
                      ' status code ' + str(postResult.status_code))
            return False, False, postResult.status_code
    return True, False, 0


def postImage(session, attachImageFilename: str, federationList: [],
              inboxUrl: str, headers: {}) -> str:
    """Post an image to the inbox of another person or outbox via c2s
    """
    # check that we are posting to a permitted domain
    if not urlPermitted(inboxUrl, federationList):
        print('postJson: ' + inboxUrl + ' not permitted')
        return None

    if not isImageFile(attachImageFilename):
        print('Image must be png, jpg, webp, avif, gif or svg')
        return None
    if not os.path.isfile(attachImageFilename):
        print('Image not found: ' + attachImageFilename)
        return None
    contentType = 'image/jpeg'
    if attachImageFilename.endswith('.png'):
        contentType = 'image/png'
    elif attachImageFilename.endswith('.gif'):
        contentType = 'image/gif'
    elif attachImageFilename.endswith('.webp'):
        contentType = 'image/webp'
    elif attachImageFilename.endswith('.avif'):
        contentType = 'image/avif'
    elif attachImageFilename.endswith('.svg'):
        contentType = 'image/svg+xml'
    headers['Content-type'] = contentType

    with open(attachImageFilename, 'rb') as avFile:
        mediaBinary = avFile.read()
        try:
            postResult = session.post(url=inboxUrl, data=mediaBinary,
                                      headers=headers)
        except requests.exceptions.RequestException as e:
            print('WARN: error during postImage requests ' + str(e))
            return None
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: connection was reset during postImage')
            print('ERROR: postImage failed ' + inboxUrl + ' ' +
                  str(headers) + ' ' + str(e))
            return None
        except ValueError as e:
            print('WARN: error during postImage ' + str(e))
            return None
        if postResult:
            return postResult.text
    return None


def downloadImage(session, baseDir: str, url: str,
                  imageFilename: str, debug: bool,
                  force: bool = False) -> bool:
    """Downloads an image with an expected mime type
    """
    if not url:
        return None

    # try different image types
    imageFormats = {
        'png': 'png',
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'gif': 'gif',
        'svg': 'svg+xml',
        'webp': 'webp',
        'avif': 'avif',
        'ico': 'x-icon'
    }
    sessionHeaders = None
    for imFormat, mimeType in imageFormats.items():
        if url.endswith('.' + imFormat) or \
           '.' + imFormat + '?' in url:
            sessionHeaders = {
                'Accept': 'image/' + mimeType
            }
            break

    if not sessionHeaders:
        if debug:
            print('downloadImage: no session headers')
        return False

    if not os.path.isfile(imageFilename) or force:
        try:
            if debug:
                print('Downloading image url: ' + url)
            result = session.get(url,
                                 headers=sessionHeaders,
                                 params=None)
            if result.status_code < 200 or \
               result.status_code > 202:
                if debug:
                    print('Image download failed with status ' +
                          str(result.status_code))
                # remove partial download
                if os.path.isfile(imageFilename):
                    try:
                        os.remove(imageFilename)
                    except OSError:
                        print('EX: downloadImage unable to delete ' +
                              imageFilename)
            else:
                with open(imageFilename, 'wb') as f:
                    f.write(result.content)
                    if debug:
                        print('Image downloaded from ' + url)
                    return True
        except Exception as e:
            print('EX: Failed to download image: ' +
                  str(url) + ' ' + str(e))
    return False


def downloadImageAnyMimeType(session, url: str, timeoutSec: int, debug: bool):
    """http GET for an image with any mime type
    """
    mimeType = None
    contentType = None
    result = None
    sessionHeaders = {
        'Accept': 'image/x-icon; image/png'
    }
    try:
        result = session.get(url, headers=sessionHeaders, timeout=timeoutSec)
    except requests.exceptions.RequestException as e:
        print('ERROR: downloadImageAnyMimeType failed: ' +
              str(url) + ', ' + str(e))
        return None, None
    except ValueError as e:
        print('ERROR: downloadImageAnyMimeType failed: ' +
              str(url) + ', ' + str(e))
        return None, None
    except SocketError as e:
        if e.errno == errno.ECONNRESET:
            print('WARN: downloadImageAnyMimeType failed, ' +
                  'connection was reset ' + str(e))
        return None, None

    if not result:
        return None, None

    if result.status_code != 200:
        print('WARN: downloadImageAnyMimeType: ' + url +
              ' failed with error code ' + str(result.status_code))
        return None, None

    if result.headers.get('content-type'):
        contentType = result.headers['content-type']
    elif result.headers.get('Content-type'):
        contentType = result.headers['Content-type']
    elif result.headers.get('Content-Type'):
        contentType = result.headers['Content-Type']

    if not contentType:
        return None, None

    imageFormats = {
        'ico': 'x-icon',
        'png': 'png',
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'gif': 'gif',
        'svg': 'svg+xml',
        'webp': 'webp',
        'avif': 'avif'
    }
    for imFormat, mType in imageFormats.items():
        if 'image/' + mType in contentType:
            mimeType = 'image/' + mType
    return result.content, mimeType
