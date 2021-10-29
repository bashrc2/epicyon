__filename__ = "siteactive.py"
__author__ = "Bob Mottram"
__credits__ = ["webchk"]
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import http.client
from urllib.parse import urlparse
import ssl


class Result:
    """Holds result of an URL check.

    The redirect attribute is a Result object that the URL was redirected to.

    The sitemap_urls attribute will contain a list of Result object if url
    is a sitemap file and http_response() was run with parse set to True.
    """
    def __init__(self, url):
        self.url = url
        self.status = 0
        self.desc = ''
        self.headers = None
        self.latency = 0
        self.content = ''
        self.redirect = None
        self.sitemap_urls = None

    def __repr__(self):
        if self.status == 0:
            return '{} ... {}'.format(self.url, self.desc)
        return '{} ... {} {} ({})'.format(
            self.url, self.status, self.desc, self.latency
        )

    def fill_headers(self, headers):
        """Takes a list of tuples and converts it a dictionary."""
        self.headers = {h[0]: h[1] for h in headers}


def _siteActiveParseUrl(url):
    """Returns an object with properties representing

    scheme:   URL scheme specifier
    netloc:   Network location part
    path:     Hierarchical path
    params:   Parameters for last path element
    query:    Query component
    fragment: Fragment identifier
    username: User name
    password: Password
    hostname: Host name (lower case)
    port:     Port number as integer, if present
    """
    loc = urlparse(url)

    # if the scheme (http, https ...) is not available urlparse wont work
    if loc.scheme == "":
        url = "http://" + url
        loc = urlparse(url)
    return loc


def _siteACtiveHttpConnect(loc, timeout: int):
    """Connects to the host and returns an HTTP or HTTPS connections."""
    if loc.scheme == "https":
        ssl_context = ssl.SSLContext()
        return http.client.HTTPSConnection(
            loc.netloc, context=ssl_context, timeout=timeout)
    return http.client.HTTPConnection(loc.netloc, timeout=timeout)


def _siteActiveHttpRequest(loc, timeout: int):
    """Performs a HTTP request and return response in a Result object.
    """
    conn = _siteACtiveHttpConnect(loc, timeout)
    method = 'HEAD'

    conn.request(method, loc.path)
    resp = conn.getresponse()

    result = Result(loc.geturl())
    result.status = resp.status
    result.desc = resp.reason
    result.fill_headers(resp.getheaders())

    conn.close()
    return result


def siteIsActive(url: str, timeout: int) -> bool:
    """Returns true if the current url is resolvable.
    This can be used to check that an instance is online before
    trying to send posts to it.
    """
    if not url.startswith('http'):
        return False
    if '.onion/' in url or '.i2p/' in url or \
       url.endswith('.onion') or \
       url.endswith('.i2p'):
        # skip this check for onion and i2p
        return True

    loc = _siteActiveParseUrl(url)
    result = Result(url=url)

    try:
        result = _siteActiveHttpRequest(loc, timeout)

        if 400 <= result.status < 500:
            return result

        return True

    except BaseException:
        print('EX: siteIsActive ' + str(loc))
        pass
    return False
