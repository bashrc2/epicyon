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

base_directory = None


def createSession(proxy_type: str):
    session = None
    try:
        session = requests.session()
    except requests.exceptions.RequestException as ex:
        print('WARN: requests error during createSession ' + str(ex))
        return None
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('WARN: connection was reset during createSession ' + str(ex))
        else:
            print('WARN: socket error during createSession ' + str(ex))
        return None
    except ValueError as ex:
        print('WARN: error during createSession ' + str(ex))
        return None
    if not session:
        return None
    if proxy_type == 'tor':
        session.proxies = {}
        session.proxies['http'] = 'socks5h://localhost:9050'
        session.proxies['https'] = 'socks5h://localhost:9050'
    elif proxy_type == 'i2p':
        session.proxies = {}
        session.proxies['http'] = 'socks5h://localhost:4447'
        session.proxies['https'] = 'socks5h://localhost:4447'
    elif proxy_type == 'gnunet':
        session.proxies = {}
        session.proxies['http'] = 'socks5h://localhost:7777'
        session.proxies['https'] = 'socks5h://localhost:7777'
    # print('New session created with proxy ' + str(proxy_type))
    return session


def urlExists(session, url: str, timeoutSec: int = 3,
              http_prefix: str = 'https', domain: str = 'testdomain') -> bool:
    if not isinstance(url, str):
        print('url: ' + str(url))
        print('ERROR: urlExists failed, url should be a string')
        return False
    sessionParams = {}
    sessionHeaders = {}
    sessionHeaders['User-Agent'] = 'Epicyon/' + __version__
    if domain:
        sessionHeaders['User-Agent'] += \
            '; +' + http_prefix + '://' + domain + '/'
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


def _getJsonRequest(session, url: str, domain_full: str, sessionHeaders: {},
                    sessionParams: {}, timeoutSec: int,
                    signing_priv_key_pem: str, quiet: bool, debug: bool,
                    returnJson: bool) -> {}:
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
        if returnJson:
            return result.json()
        return result.content
    except requests.exceptions.RequestException as ex:
        sessionHeaders2 = sessionHeaders.copy()
        if sessionHeaders2.get('Authorization'):
            sessionHeaders2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('ERROR: getJson failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(sessionHeaders2) + ', ' +
                  'params: ' + str(sessionParams) + ', ' + str(ex))
    except ValueError as ex:
        sessionHeaders2 = sessionHeaders.copy()
        if sessionHeaders2.get('Authorization'):
            sessionHeaders2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('ERROR: getJson failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(sessionHeaders2) + ', ' +
                  'params: ' + str(sessionParams) + ', ' + str(ex))
    except SocketError as ex:
        if not quiet:
            if ex.errno == errno.ECONNRESET:
                print('WARN: getJson failed, ' +
                      'connection was reset during getJson ' + str(ex))
    return None


def _getJsonSigned(session, url: str, domain_full: str, sessionHeaders: {},
                   sessionParams: {}, timeoutSec: int,
                   signing_priv_key_pem: str, quiet: bool, debug: bool) -> {}:
    """Authorized fetch - a signed version of GET
    """
    if not domain_full:
        if debug:
            print('No sending domain for signed GET')
        return None
    if '://' not in url:
        print('Invalid url: ' + url)
        return None
    http_prefix = url.split('://')[0]
    toDomainFull = url.split('://')[1]
    if '/' in toDomainFull:
        toDomainFull = toDomainFull.split('/')[0]

    if ':' in domain_full:
        domain = domain_full.split(':')[0]
        port = domain_full.split(':')[1]
    else:
        domain = domain_full
        if http_prefix == 'https':
            port = 443
        else:
            port = 80

    if ':' in toDomainFull:
        toDomain = toDomainFull.split(':')[0]
        toPort = toDomainFull.split(':')[1]
    else:
        toDomain = toDomainFull
        if http_prefix == 'https':
            toPort = 443
        else:
            toPort = 80

    if debug:
        print('Signed GET domain: ' + domain + ' ' + str(port))
        print('Signed GET toDomain: ' + toDomain + ' ' + str(toPort))
        print('Signed GET url: ' + url)
        print('Signed GET http_prefix: ' + http_prefix)
    messageStr = ''
    withDigest = False
    if toDomainFull + '/' in url:
        path = '/' + url.split(toDomainFull + '/')[1]
    else:
        path = '/actor'
    content_type = 'application/activity+json'
    if sessionHeaders.get('Accept'):
        content_type = sessionHeaders['Accept']
    signatureHeaderJson = \
        createSignedHeader(None, signing_priv_key_pem, 'actor', domain, port,
                           toDomain, toPort, path, http_prefix, withDigest,
                           messageStr, content_type)
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

    returnJson = True
    if 'json' not in content_type:
        returnJson = False
    return _getJsonRequest(session, url, domain_full, sessionHeaders,
                           sessionParams, timeoutSec, None, quiet,
                           debug, returnJson)


def getJson(signing_priv_key_pem: str,
            session, url: str, headers: {}, params: {}, debug: bool,
            version: str = '1.2.0', http_prefix: str = 'https',
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
            '; +' + http_prefix + '://' + domain + '/'
    if not session:
        if not quiet:
            print('WARN: getJson failed, no session specified for getJson')
        return None

    if debug:
        HTTPConnection.debuglevel = 1

    if signing_priv_key_pem:
        return _getJsonSigned(session, url, domain,
                              sessionHeaders, sessionParams,
                              timeoutSec, signing_priv_key_pem,
                              quiet, debug)
    else:
        return _getJsonRequest(session, url, domain, sessionHeaders,
                               sessionParams, timeoutSec,
                               None, quiet, debug, True)


def downloadHtml(signing_priv_key_pem: str,
                 session, url: str, headers: {}, params: {}, debug: bool,
                 version: str = '1.2.0', http_prefix: str = 'https',
                 domain: str = 'testdomain',
                 timeoutSec: int = 20, quiet: bool = False) -> {}:
    if not isinstance(url, str):
        if debug and not quiet:
            print('url: ' + str(url))
            print('ERROR: downloadHtml failed, url should be a string')
        return None
    sessionParams = {}
    sessionHeaders = {}
    if headers:
        sessionHeaders = headers
    if params:
        sessionParams = params
    sessionHeaders['Accept'] = 'text/html'
    sessionHeaders['User-Agent'] = 'Epicyon/' + version
    if domain:
        sessionHeaders['User-Agent'] += \
            '; +' + http_prefix + '://' + domain + '/'
    if not session:
        if not quiet:
            print('WARN: downloadHtml failed, ' +
                  'no session specified for downloadHtml')
        return None

    if debug:
        HTTPConnection.debuglevel = 1

    if signing_priv_key_pem:
        return _getJsonSigned(session, url, domain,
                              sessionHeaders, sessionParams,
                              timeoutSec, signing_priv_key_pem,
                              quiet, debug)
    else:
        return _getJsonRequest(session, url, domain, sessionHeaders,
                               sessionParams, timeoutSec,
                               None, quiet, debug, False)


def postJson(http_prefix: str, domain_full: str,
             session, post_json_object: {}, federation_list: [],
             inboxUrl: str, headers: {}, timeoutSec: int = 60,
             quiet: bool = False) -> str:
    """Post a json message to the inbox of another person
    """
    # check that we are posting to a permitted domain
    if not urlPermitted(inboxUrl, federation_list):
        if not quiet:
            print('postJson: ' + inboxUrl + ' not permitted')
        return None

    sessionHeaders = headers
    sessionHeaders['User-Agent'] = 'Epicyon/' + __version__
    sessionHeaders['User-Agent'] += \
        '; +' + http_prefix + '://' + domain_full + '/'

    try:
        postResult = \
            session.post(url=inboxUrl,
                         data=json.dumps(post_json_object),
                         headers=headers, timeout=timeoutSec)
    except requests.Timeout as ex:
        if not quiet:
            print('ERROR: postJson timeout ' + inboxUrl + ' ' +
                  json.dumps(post_json_object) + ' ' + str(headers))
            print(ex)
        return ''
    except requests.exceptions.RequestException as ex:
        if not quiet:
            print('ERROR: postJson requests failed ' + inboxUrl + ' ' +
                  json.dumps(post_json_object) + ' ' + str(headers) +
                  ' ' + str(ex))
        return None
    except SocketError as ex:
        if not quiet and ex.errno == errno.ECONNRESET:
            print('WARN: connection was reset during postJson')
        return None
    except ValueError as ex:
        if not quiet:
            print('ERROR: postJson failed ' + inboxUrl + ' ' +
                  json.dumps(post_json_object) + ' ' + str(headers) +
                  ' ' + str(ex))
        return None
    if postResult:
        return postResult.text
    return None


def postJsonString(session, postJsonStr: str,
                   federation_list: [],
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
    except requests.exceptions.RequestException as ex:
        if not quiet:
            print('WARN: error during postJsonString requests ' + str(ex))
        return None, None, 0
    except SocketError as ex:
        if not quiet and ex.errno == errno.ECONNRESET:
            print('WARN: connection was reset during postJsonString')
        if not quiet:
            print('ERROR: postJsonString failed ' + inboxUrl + ' ' +
                  postJsonStr + ' ' + str(headers))
        return None, None, 0
    except ValueError as ex:
        if not quiet:
            print('WARN: error during postJsonString ' + str(ex))
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


def postImage(session, attachImageFilename: str, federation_list: [],
              inboxUrl: str, headers: {}) -> str:
    """Post an image to the inbox of another person or outbox via c2s
    """
    # check that we are posting to a permitted domain
    if not urlPermitted(inboxUrl, federation_list):
        print('postJson: ' + inboxUrl + ' not permitted')
        return None

    if not isImageFile(attachImageFilename):
        print('Image must be png, jpg, webp, avif, gif or svg')
        return None
    if not os.path.isfile(attachImageFilename):
        print('Image not found: ' + attachImageFilename)
        return None
    content_type = 'image/jpeg'
    if attachImageFilename.endswith('.png'):
        content_type = 'image/png'
    elif attachImageFilename.endswith('.gif'):
        content_type = 'image/gif'
    elif attachImageFilename.endswith('.webp'):
        content_type = 'image/webp'
    elif attachImageFilename.endswith('.avif'):
        content_type = 'image/avif'
    elif attachImageFilename.endswith('.svg'):
        content_type = 'image/svg+xml'
    headers['Content-type'] = content_type

    with open(attachImageFilename, 'rb') as avFile:
        mediaBinary = avFile.read()
        try:
            postResult = session.post(url=inboxUrl, data=mediaBinary,
                                      headers=headers)
        except requests.exceptions.RequestException as ex:
            print('WARN: error during postImage requests ' + str(ex))
            return None
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: connection was reset during postImage')
            print('ERROR: postImage failed ' + inboxUrl + ' ' +
                  str(headers) + ' ' + str(ex))
            return None
        except ValueError as ex:
            print('WARN: error during postImage ' + str(ex))
            return None
        if postResult:
            return postResult.text
    return None


def downloadImage(session, base_dir: str, url: str,
                  image_filename: str, debug: bool,
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

    if not os.path.isfile(image_filename) or force:
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
                if os.path.isfile(image_filename):
                    try:
                        os.remove(image_filename)
                    except OSError:
                        print('EX: downloadImage unable to delete ' +
                              image_filename)
            else:
                with open(image_filename, 'wb') as f:
                    f.write(result.content)
                    if debug:
                        print('Image downloaded from ' + url)
                    return True
        except Exception as ex:
            print('EX: Failed to download image: ' +
                  str(url) + ' ' + str(ex))
    return False


def downloadImageAnyMimeType(session, url: str, timeoutSec: int, debug: bool):
    """http GET for an image with any mime type
    """
    mimeType = None
    content_type = None
    result = None
    sessionHeaders = {
        'Accept': 'image/x-icon, image/png, image/webp, image/jpeg, image/gif'
    }
    try:
        result = session.get(url, headers=sessionHeaders, timeout=timeoutSec)
    except requests.exceptions.RequestException as ex:
        print('ERROR: downloadImageAnyMimeType failed: ' +
              str(url) + ', ' + str(ex))
        return None, None
    except ValueError as ex:
        print('ERROR: downloadImageAnyMimeType failed: ' +
              str(url) + ', ' + str(ex))
        return None, None
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('WARN: downloadImageAnyMimeType failed, ' +
                  'connection was reset ' + str(ex))
        return None, None

    if not result:
        return None, None

    if result.status_code != 200:
        print('WARN: downloadImageAnyMimeType: ' + url +
              ' failed with error code ' + str(result.status_code))
        return None, None

    if result.headers.get('content-type'):
        content_type = result.headers['content-type']
    elif result.headers.get('Content-type'):
        content_type = result.headers['Content-type']
    elif result.headers.get('Content-Type'):
        content_type = result.headers['Content-Type']

    if not content_type:
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
        if 'image/' + mType in content_type:
            mimeType = 'image/' + mType
    return result.content, mimeType
