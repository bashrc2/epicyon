__filename__ = "session.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Session"

import os
import requests
from utils import url_permitted
from utils import is_image_file
from httpsig import create_signed_header
import json
from socket import error as SocketError
import errno
from http.client import HTTPConnection


def create_session(proxy_type: str):
    session = None
    try:
        session = requests.session()
    except requests.exceptions.RequestException as ex:
        print('EX: requests error during create_session ' + str(ex))
        return None
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: connection was reset during create_session ' +
                  str(ex))
        else:
            print('EX: socket error during create_session ' + str(ex))
        return None
    except ValueError as ex:
        print('EX: error during create_session ' + str(ex))
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


def url_exists(session, url: str, timeout_sec: int = 3,
               http_prefix: str = 'https', domain: str = 'testdomain') -> bool:
    if not isinstance(url, str):
        print('url: ' + str(url))
        print('ERROR: url_exists failed, url should be a string')
        return False
    session_params = {}
    session_headers = {}
    session_headers['User-Agent'] = 'Epicyon/' + __version__
    if domain:
        session_headers['User-Agent'] += \
            '; +' + http_prefix + '://' + domain + '/'
    if not session:
        print('WARN: url_exists failed, no session specified')
        return True
    try:
        result = session.get(url, headers=session_headers,
                             params=session_params,
                             timeout=timeout_sec)
        if result:
            if result.status_code == 200 or \
               result.status_code == 304:
                return True
            print('url_exists for ' + url + ' returned ' +
                  str(result.status_code))
    except BaseException:
        print('EX: url_exists GET failed ' + str(url))
    return False


def _get_json_request(session, url: str, domain_full: str, session_headers: {},
                      session_params: {}, timeout_sec: int,
                      signing_priv_key_pem: str, quiet: bool, debug: bool,
                      return_json: bool) -> {}:
    """http GET for json
    """
    try:
        result = session.get(url, headers=session_headers,
                             params=session_params, timeout=timeout_sec)
        if result.status_code != 200:
            if result.status_code == 401:
                print("WARN: get_json " + url + ' rejected by secure mode')
            elif result.status_code == 403:
                print('WARN: get_json Forbidden url: ' + url)
            elif result.status_code == 404:
                print('WARN: get_json Not Found url: ' + url)
            elif result.status_code == 410:
                print('WARN: get_json no longer available url: ' + url)
            else:
                session_headers2 = session_headers.copy()
                if session_headers2.get('Authorization'):
                    session_headers2['Authorization'] = 'REDACTED'
                print('WARN: get_json url: ' + url +
                      ' failed with error code ' +
                      str(result.status_code) +
                      ' headers: ' + str(session_headers2))
        if return_json:
            return result.json()
        return result.content
    except requests.exceptions.RequestException as ex:
        session_headers2 = session_headers.copy()
        if session_headers2.get('Authorization'):
            session_headers2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('EX: get_json failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(session_headers2) + ', ' +
                  'params: ' + str(session_params) + ', ' + str(ex))
    except ValueError as ex:
        session_headers2 = session_headers.copy()
        if session_headers2.get('Authorization'):
            session_headers2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('EX: get_json failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(session_headers2) + ', ' +
                  'params: ' + str(session_params) + ', ' + str(ex))
    except SocketError as ex:
        if not quiet:
            if ex.errno == errno.ECONNRESET:
                print('EX: get_json failed, ' +
                      'connection was reset during get_json ' + str(ex))
    return None


def _get_json_signed(session, url: str, domain_full: str, session_headers: {},
                     session_params: {}, timeout_sec: int,
                     signing_priv_key_pem: str, quiet: bool,
                     debug: bool) -> {}:
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
    to_domain_full = url.split('://')[1]
    if '/' in to_domain_full:
        to_domain_full = to_domain_full.split('/')[0]

    if ':' in domain_full:
        domain = domain_full.split(':')[0]
        port = domain_full.split(':')[1]
    else:
        domain = domain_full
        if http_prefix == 'https':
            port = 443
        else:
            port = 80

    if ':' in to_domain_full:
        to_domain = to_domain_full.split(':')[0]
        to_port = to_domain_full.split(':')[1]
    else:
        to_domain = to_domain_full
        if http_prefix == 'https':
            to_port = 443
        else:
            to_port = 80

    if debug:
        print('Signed GET domain: ' + domain + ' ' + str(port))
        print('Signed GET to_domain: ' + to_domain + ' ' + str(to_port))
        print('Signed GET url: ' + url)
        print('Signed GET http_prefix: ' + http_prefix)
    message_str = ''
    with_digest = False
    if to_domain_full + '/' in url:
        path = '/' + url.split(to_domain_full + '/')[1]
    else:
        path = '/actor'
    content_type = 'application/activity+json'
    if session_headers.get('Accept'):
        content_type = session_headers['Accept']
    signature_header_json = \
        create_signed_header(None, signing_priv_key_pem, 'actor', domain, port,
                             to_domain, to_port, path, http_prefix,
                             with_digest, message_str, content_type)
    if debug:
        print('Signed GET signature_header_json ' + str(signature_header_json))
    # update the session headers from the signature headers
    session_headers['Host'] = signature_header_json['host']
    session_headers['Date'] = signature_header_json['date']
    session_headers['Accept'] = signature_header_json['accept']
    session_headers['Signature'] = signature_header_json['signature']
    session_headers['Content-Length'] = '0'
    if debug:
        print('Signed GET session_headers ' + str(session_headers))

    return_json = True
    if 'json' not in content_type:
        return_json = False
    return _get_json_request(session, url, domain_full, session_headers,
                             session_params, timeout_sec, None, quiet,
                             debug, return_json)


def get_json(signing_priv_key_pem: str,
             session, url: str, headers: {}, params: {}, debug: bool,
             version: str = __version__, http_prefix: str = 'https',
             domain: str = 'testdomain',
             timeout_sec: int = 20, quiet: bool = False) -> {}:
    if not isinstance(url, str):
        if debug and not quiet:
            print('url: ' + str(url))
            print('ERROR: get_json failed, url should be a string')
        return None
    session_params = {}
    session_headers = {}
    if headers:
        session_headers = headers
    if params:
        session_params = params
    session_headers['User-Agent'] = 'Epicyon/' + version
    if domain:
        session_headers['User-Agent'] += \
            '; +' + http_prefix + '://' + domain + '/'
    if not session:
        if not quiet:
            print('WARN: get_json failed, no session specified for get_json')
        return None

    if debug:
        HTTPConnection.debuglevel = 1

    if signing_priv_key_pem:
        return _get_json_signed(session, url, domain,
                                session_headers, session_params,
                                timeout_sec, signing_priv_key_pem,
                                quiet, debug)
    return _get_json_request(session, url, domain, session_headers,
                             session_params, timeout_sec,
                             None, quiet, debug, True)


def get_vcard(xml_format: bool,
              session, url: str, params: {}, debug: bool,
              version: str = __version__, http_prefix: str = 'https',
              domain: str = 'testdomain',
              timeout_sec: int = 20, quiet: bool = False) -> {}:
    if not isinstance(url, str):
        if debug and not quiet:
            print('url: ' + str(url))
            print('ERROR: get_vcard failed, url should be a string')
        return None
    headers = {
        'Accept': 'text/vcard'
    }
    if xml_format:
        headers['Accept'] = 'application/vcard+xml'
    session_params = {}
    session_headers = {}
    if headers:
        session_headers = headers
    if params:
        session_params = params
    session_headers['User-Agent'] = 'Epicyon/' + version
    if domain:
        session_headers['User-Agent'] += \
            '; +' + http_prefix + '://' + domain + '/'
    if not session:
        if not quiet:
            print('WARN: get_vcard failed, no session specified for get_vcard')
        return None

    if debug:
        HTTPConnection.debuglevel = 1

    try:
        result = session.get(url, headers=session_headers,
                             params=session_params, timeout=timeout_sec)
        if result.status_code != 200:
            if result.status_code == 401:
                print("WARN: get_vcard " + url + ' rejected by secure mode')
            elif result.status_code == 403:
                print('WARN: get_vcard Forbidden url: ' + url)
            elif result.status_code == 404:
                print('WARN: get_vcard Not Found url: ' + url)
            elif result.status_code == 410:
                print('WARN: get_vcard no longer available url: ' + url)
            else:
                session_headers2 = session_headers.copy()
                if session_headers2.get('Authorization'):
                    session_headers2['Authorization'] = 'REDACTED'
                print('WARN: get_vcard url: ' + url +
                      ' failed with error code ' +
                      str(result.status_code) +
                      ' headers: ' + str(session_headers2))
        return result.content.decode('utf-8')
    except requests.exceptions.RequestException as ex:
        session_headers2 = session_headers.copy()
        if session_headers2.get('Authorization'):
            session_headers2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('EX: get_vcard failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(session_headers2) + ', ' +
                  'params: ' + str(session_params) + ', ' + str(ex))
    except ValueError as ex:
        session_headers2 = session_headers.copy()
        if session_headers2.get('Authorization'):
            session_headers2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('EX: get_vcard failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(session_headers2) + ', ' +
                  'params: ' + str(session_params) + ', ' + str(ex))
    except SocketError as ex:
        if not quiet:
            if ex.errno == errno.ECONNRESET:
                print('EX: get_vcard failed, ' +
                      'connection was reset during get_vcard ' + str(ex))
    return None


def download_html(signing_priv_key_pem: str,
                  session, url: str, headers: {}, params: {}, debug: bool,
                  version: str = __version__, http_prefix: str = 'https',
                  domain: str = 'testdomain',
                  timeout_sec: int = 20, quiet: bool = False) -> {}:
    if not isinstance(url, str):
        if debug and not quiet:
            print('url: ' + str(url))
            print('ERROR: download_html failed, url should be a string')
        return None
    session_params = {}
    session_headers = {}
    if headers:
        session_headers = headers
    if params:
        session_params = params
    session_headers['Accept'] = 'text/html'
    session_headers['User-Agent'] = 'Epicyon/' + version
    if domain:
        session_headers['User-Agent'] += \
            '; +' + http_prefix + '://' + domain + '/'
    if not session:
        if not quiet:
            print('WARN: download_html failed, ' +
                  'no session specified for download_html')
        return None

    if debug:
        HTTPConnection.debuglevel = 1

    if signing_priv_key_pem:
        return _get_json_signed(session, url, domain,
                                session_headers, session_params,
                                timeout_sec, signing_priv_key_pem,
                                quiet, debug)
    return _get_json_request(session, url, domain, session_headers,
                             session_params, timeout_sec,
                             None, quiet, debug, False)


def post_json(http_prefix: str, domain_full: str,
              session, post_json_object: {}, federation_list: [],
              inbox_url: str, headers: {}, timeout_sec: int = 60,
              quiet: bool = False) -> str:
    """Post a json message to the inbox of another person
    """
    # check that we are posting to a permitted domain
    if not url_permitted(inbox_url, federation_list):
        if not quiet:
            print('post_json: ' + inbox_url + ' not permitted')
        return None

    session_headers = headers
    session_headers['User-Agent'] = 'Epicyon/' + __version__
    session_headers['User-Agent'] += \
        '; +' + http_prefix + '://' + domain_full + '/'

    try:
        post_result = \
            session.post(url=inbox_url,
                         data=json.dumps(post_json_object),
                         headers=headers, timeout=timeout_sec)
    except requests.Timeout as ex:
        if not quiet:
            print('EX: post_json timeout ' + inbox_url + ' ' +
                  json.dumps(post_json_object) + ' ' + str(headers))
            print(ex)
        return ''
    except requests.exceptions.RequestException as ex:
        if not quiet:
            print('EX: post_json requests failed ' + inbox_url + ' ' +
                  json.dumps(post_json_object) + ' ' + str(headers) +
                  ' ' + str(ex))
        return None
    except SocketError as ex:
        if not quiet and ex.errno == errno.ECONNRESET:
            print('EX: connection was reset during post_json')
        return None
    except ValueError as ex:
        if not quiet:
            print('EX: post_json failed ' + inbox_url + ' ' +
                  json.dumps(post_json_object) + ' ' + str(headers) +
                  ' ' + str(ex))
        return None
    if post_result:
        return post_result.text
    return None


def post_json_string(session, post_jsonStr: str,
                     federation_list: [],
                     inbox_url: str,
                     headers: {},
                     debug: bool,
                     timeout_sec: int = 30,
                     quiet: bool = False) -> (bool, bool, int):
    """Post a json message string to the inbox of another person
    The second boolean returned is true if the send if unauthorized
    NOTE: Here we post a string rather than the original json so that
    conversions between string and json format don't invalidate
    the message body digest of http signatures
    """
    # check that we are posting to a permitted domain
    if not url_permitted(inbox_url, federation_list):
        if not quiet:
            print('post_json_string: ' + inbox_url + ' not permitted')
        return False, True, 0

    try:
        post_result = \
            session.post(url=inbox_url, data=post_jsonStr,
                         headers=headers, timeout=timeout_sec)
    except requests.exceptions.RequestException as ex:
        if not quiet:
            print('EX: error during post_json_string requests ' + str(ex))
        return None, None, 0
    except SocketError as ex:
        if not quiet and ex.errno == errno.ECONNRESET:
            print('EX: connection was reset during post_json_string')
        if not quiet:
            print('EX: post_json_string failed ' + inbox_url + ' ' +
                  post_jsonStr + ' ' + str(headers))
        return None, None, 0
    except ValueError as ex:
        if not quiet:
            print('EX: error during post_json_string ' + str(ex))
        return None, None, 0
    if post_result.status_code < 200 or post_result.status_code > 202:
        if post_result.status_code >= 400 and \
           post_result.status_code <= 405 and \
           post_result.status_code != 404:
            if not quiet:
                print('WARN: Post to ' + inbox_url +
                      ' is unauthorized. Code ' +
                      str(post_result.status_code))
            return False, True, post_result.status_code

        if not quiet:
            print('WARN: Failed to post to ' + inbox_url +
                  ' with headers ' + str(headers) +
                  ' status code ' + str(post_result.status_code))
        return False, False, post_result.status_code
    return True, False, 0


def post_image(session, attach_image_filename: str, federation_list: [],
               inbox_url: str, headers: {}) -> str:
    """Post an image to the inbox of another person or outbox via c2s
    """
    # check that we are posting to a permitted domain
    if not url_permitted(inbox_url, federation_list):
        print('post_json: ' + inbox_url + ' not permitted')
        return None

    if not is_image_file(attach_image_filename):
        print('Image must be png, jpg, jxl, webp, avif, gif or svg')
        return None
    if not os.path.isfile(attach_image_filename):
        print('Image not found: ' + attach_image_filename)
        return None
    content_type = 'image/jpeg'
    if attach_image_filename.endswith('.png'):
        content_type = 'image/png'
    elif attach_image_filename.endswith('.gif'):
        content_type = 'image/gif'
    elif attach_image_filename.endswith('.webp'):
        content_type = 'image/webp'
    elif attach_image_filename.endswith('.avif'):
        content_type = 'image/avif'
    elif attach_image_filename.endswith('.jxl'):
        content_type = 'image/jxl'
    elif attach_image_filename.endswith('.svg'):
        content_type = 'image/svg+xml'
    headers['Content-type'] = content_type

    with open(attach_image_filename, 'rb') as av_file:
        media_binary = av_file.read()
        try:
            post_result = session.post(url=inbox_url, data=media_binary,
                                       headers=headers)
        except requests.exceptions.RequestException as ex:
            print('EX: error during post_image requests ' + str(ex))
            return None
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('EX: connection was reset during post_image')
            print('ERROR: post_image failed ' + inbox_url + ' ' +
                  str(headers) + ' ' + str(ex))
            return None
        except ValueError as ex:
            print('EX: error during post_image ' + str(ex))
            return None
        if post_result:
            return post_result.text
    return None


def _looks_like_url(url: str) -> bool:
    """Does the given string look like a url
    """
    if not url:
        return False
    if '.' not in url:
        return False
    if '://' not in url:
        return False
    return True


def download_image(session, base_dir: str, url: str,
                   image_filename: str, debug: bool,
                   force: bool = False) -> bool:
    """Downloads an image with an expected mime type
    """
    if not _looks_like_url(url):
        if debug:
            print('WARN: download_image, ' +
                  url + ' does not look like a url')
        return None

    # try different image types
    image_formats = {
        'png': 'png',
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'jxl': 'jxl',
        'gif': 'gif',
        'svg': 'svg+xml',
        'webp': 'webp',
        'avif': 'avif',
        'ico': 'x-icon'
    }
    session_headers = None
    for im_format, mime_type in image_formats.items():
        if url.endswith('.' + im_format) or \
           '.' + im_format + '?' in url:
            session_headers = {
                'Accept': 'image/' + mime_type
            }
            break

    if not session_headers:
        if debug:
            print('download_image: no session headers')
        return False

    if not os.path.isfile(image_filename) or force:
        try:
            if debug:
                print('Downloading image url: ' + url)
            result = session.get(url,
                                 headers=session_headers,
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
                        print('EX: download_image unable to delete ' +
                              image_filename)
            else:
                with open(image_filename, 'wb') as im_file:
                    im_file.write(result.content)
                    if debug:
                        print('Image downloaded from ' + url)
                    return True
        except BaseException as ex:
            print('EX: Failed to download image: ' +
                  str(url) + ' ' + str(ex))
    return False


def download_image_any_mime_type(session, url: str,
                                 timeout_sec: int, debug: bool):
    """http GET for an image with any mime type
    """
    # check that this looks like a url
    if not _looks_like_url(url):
        if debug:
            print('WARN: download_image_any_mime_type, ' +
                  url + ' does not look like a url')
        return None, None

    mime_type = None
    content_type = None
    result = None
    session_headers = {
        'Accept': 'image/x-icon, image/png, image/webp, image/jpeg, image/gif'
    }
    try:
        result = session.get(url, headers=session_headers, timeout=timeout_sec)
    except requests.exceptions.RequestException as ex:
        print('EX: download_image_any_mime_type failed1: ' +
              str(url) + ', ' + str(ex))
        return None, None
    except ValueError as ex:
        print('EX: download_image_any_mime_type failed2: ' +
              str(url) + ', ' + str(ex))
        return None, None
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('EX: download_image_any_mime_type failed, ' +
                  'connection was reset ' + str(ex))
        return None, None

    if not result:
        return None, None

    if result.status_code != 200:
        print('WARN: download_image_any_mime_type: ' + url +
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

    image_formats = {
        'ico': 'x-icon',
        'png': 'png',
        'jpg': 'jpeg',
        'jxl': 'jxl',
        'jpeg': 'jpeg',
        'gif': 'gif',
        'svg': 'svg+xml',
        'webp': 'webp',
        'avif': 'avif'
    }
    for _, m_type in image_formats.items():
        if 'image/' + m_type in content_type:
            mime_type = 'image/' + m_type
    return result.content, mime_type


def get_method(method_name: str, xml_str: str,
               session, url: str, params: {}, headers: {}, debug: bool,
               version: str = __version__, http_prefix: str = 'https',
               domain: str = 'testdomain',
               timeout_sec: int = 20, quiet: bool = False) -> {}:
    if method_name not in ("REPORT", "PUT", "PROPFIND"):
        print("Unrecognized method: " + method_name)
        return None
    if not isinstance(url, str):
        if debug and not quiet:
            print('url: ' + str(url))
            print('ERROR: get_method failed, url should be a string')
        return None
    if not headers:
        headers = {
            'Accept': 'application/xml'
        }
    else:
        headers['Accept'] = 'application/xml'
    session_params = {}
    session_headers = {}
    if headers:
        session_headers = headers
    if params:
        session_params = params
    session_headers['User-Agent'] = 'Epicyon/' + version
    if domain:
        session_headers['User-Agent'] += \
            '; +' + http_prefix + '://' + domain + '/'
    if not session:
        if not quiet:
            print('WARN: get_method failed, ' +
                  'no session specified for get_vcard')
        return None

    if debug:
        HTTPConnection.debuglevel = 1

    try:
        result = session.request(method_name, url, headers=session_headers,
                                 data=xml_str,
                                 params=session_params, timeout=timeout_sec)
        if result.status_code != 200 and result.status_code != 207:
            if result.status_code == 401:
                print("WARN: get_method " + url + ' rejected by secure mode')
            elif result.status_code == 403:
                print('WARN: get_method Forbidden url: ' + url)
            elif result.status_code == 404:
                print('WARN: get_method Not Found url: ' + url)
            elif result.status_code == 410:
                print('WARN: get_method no longer available url: ' + url)
            else:
                session_headers2 = session_headers.copy()
                if session_headers2.get('Authorization'):
                    session_headers2['Authorization'] = 'REDACTED'
                print('WARN: get_method url: ' + url +
                      ' failed with error code ' +
                      str(result.status_code) +
                      ' headers: ' + str(session_headers2))
        return result.content.decode('utf-8')
    except requests.exceptions.RequestException as ex:
        session_headers2 = session_headers.copy()
        if session_headers2.get('Authorization'):
            session_headers2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('EX: get_method failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(session_headers2) + ', ' +
                  'params: ' + str(session_params) + ', ' + str(ex))
    except ValueError as ex:
        session_headers2 = session_headers.copy()
        if session_headers2.get('Authorization'):
            session_headers2['Authorization'] = 'REDACTED'
        if debug and not quiet:
            print('EX: get_method failed, url: ' + str(url) + ', ' +
                  'headers: ' + str(session_headers2) + ', ' +
                  'params: ' + str(session_params) + ', ' + str(ex))
    except SocketError as ex:
        if not quiet:
            if ex.errno == errno.ECONNRESET:
                print('EX: get_method failed, ' +
                      'connection was reset during get_vcard ' + str(ex))
    return None
