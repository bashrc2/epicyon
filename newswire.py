__filename__ = "newswire.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import requests
from socket import error as SocketError
import errno
from datetime import datetime
from collections import OrderedDict


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
        parsed = False
        try:
            publishedDate = \
                datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %z")
            result[str(publishedDate)] = [title, link]
            parsed = True
        except BaseException:
            pass
        if not parsed:
            try:
                publishedDate = \
                    datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S UT")
                result[str(publishedDate) + '+00:00'] = [title, link]
                parsed = True
            except BaseException:
                print('WARN: unrecognized RSS date format: ' + pubDate)
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


def getRSSFromSubscriptions(session, subscriptionsFilename: str) -> {}:
    """Gets rss feeds as a dictionary from a list of feeds stored in a file
    """
    if not os.path.isfile(subscriptionsFilename):
        return {}

    rssFeed = []
    with open(subscriptionsFilename, 'r') as fp:
        rssFeed = fp.readlines()
    result = {}
    for url in rssFeed:
        url = url.strip()
        if '://' not in url:
            continue
        if url.startswith('#'):
            continue
        result = dict(result.items() + getRSS(session, url).items())
    sortedResult = OrderedDict(sorted(result.items(), reverse=False))
    return sortedResult
