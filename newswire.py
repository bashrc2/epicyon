__filename__ = "newswire.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
import requests
from socket import error as SocketError
import errno
from datetime import datetime
from collections import OrderedDict
from utils import locatePost
from utils import loadJson
from utils import saveJson
from utils import isSuspended
# from utils import getConfigParam


def rss2Header(httpPrefix: str,
               nickname: str, domainFull: str,
               title: str, translate: {}) -> str:
    """Header for an RSS 2.0 feed
    """
    rssStr = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
    rssStr += "<rss version=\"2.0\">"
    rssStr += '<channel>'
    if title.startswith('News'):
        rssStr += '    <title>Newswire</title>'
    else:
        rssStr += '    <title>' + translate[title] + '</title>'
    if title.startswith('News'):
        rssStr += '    <link>' + httpPrefix + '://' + domainFull + \
            '/newswire.xml' + '</link>'
    else:
        rssStr += '    <link>' + httpPrefix + '://' + domainFull + \
            '/users/' + nickname + '/rss.xml' + '</link>'
    return rssStr


def rss2Footer() -> str:
    """Footer for an RSS 2.0 feed
    """
    rssStr = '</channel>'
    rssStr += '</rss>'
    return rssStr


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
            result[str(publishedDate)] = [title, link, []]
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


def getRSSfromDict(baseDir: str, newswire: {},
                   httpPrefix: str, domainFull: str,
                   title: str, translate: {}) -> str:
    """Returns an rss feed from the current newswire dict.
    This allows other instances to subscribe to the same newswire
    """
    rssStr = rss2Header(httpPrefix,
                        None, domainFull,
                        'Newswire', translate)
    for published, fields in newswire.items():
        published = published.replace('+00:00', 'Z').strip()
        published = published.replace(' ', 'T')
        try:
            pubDate = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
        except BaseException:
            continue
        rssStr += '<item>\n'
        rssStr += '  <title>' + fields[0] + '</title>\n'
        rssStr += '  <link>' + fields[1] + '</link>\n'

        rssDateStr = pubDate.strftime("%a, %d %b %Y %H:%M:%S UT")
        rssStr += '  <pubDate>' + rssDateStr + '</pubDate>\n'
        rssStr += '</item>\n'
    rssStr += rss2Footer()
    return rssStr


def isaBlogPost(postJsonObject: {}) -> bool:
    """Is the given object a blog post?
    """
    if not postJsonObject:
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if postJsonObject['object'].get('summary') and \
       postJsonObject['object'].get('url') and \
       postJsonObject['object'].get('published'):
        return True
    return False


def addAccountBlogsToNewswire(baseDir: str, nickname: str, domain: str,
                              newswire: {},
                              maxBlogsPerAccount: int,
                              indexFilename: str) -> None:
    """Adds blogs for the given account to the newswire
    """
    if not os.path.isfile(indexFilename):
        return
    with open(indexFilename, 'r') as indexFile:
        postFilename = 'start'
        ctr = 0
        while postFilename:
            postFilename = indexFile.readline()
            if postFilename:
                # if this is a full path then remove the directories
                if '/' in postFilename:
                    postFilename = postFilename.split('/')[-1]

                # filename of the post without any extension or path
                # This should also correspond to any index entry in
                # the posts cache
                postUrl = \
                    postFilename.replace('\n', '').replace('\r', '')
                postUrl = postUrl.replace('.json', '').strip()

                # read the post from file
                fullPostFilename = \
                    locatePost(baseDir, nickname,
                               domain, postUrl, False)
                if not fullPostFilename:
                    print('Unable to locate post ' + postUrl)
                    ctr += 1
                    if ctr >= maxBlogsPerAccount:
                        break
                    continue

                postJsonObject = None
                if fullPostFilename:
                    postJsonObject = loadJson(fullPostFilename)
                if isaBlogPost(postJsonObject):
                    published = postJsonObject['object']['published']
                    published = published.replace('T', ' ')
                    published = published.replace('Z', '+00:00')
                    newswire[published] = \
                        [postJsonObject['object']['summary'],
                         postJsonObject['object']['url'], []]

            ctr += 1
            if ctr >= maxBlogsPerAccount:
                break


def addBlogsToNewswire(baseDir: str, newswire: {},
                       maxBlogsPerAccount: int) -> None:
    """Adds blogs from each user account into the newswire
    """
    moderationDict = {}

    # go through each account
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if '@' not in handle:
                continue
            if 'inbox@' in handle:
                continue

            nickname = handle.split('@')[0]

            # has this account been suspended?
            if isSuspended(baseDir, nickname):
                continue

            # is there a blogs timeline for this account?
            accountDir = os.path.join(baseDir + '/accounts', handle)
            blogsIndex = accountDir + '/tlblogs.index'
            if os.path.isfile(blogsIndex):
                domain = handle.split('@')[1]
                addAccountBlogsToNewswire(baseDir, nickname, domain,
                                          newswire, maxBlogsPerAccount,
                                          blogsIndex)

    # sort the moderation dict into chronological order, latest first
    sortedModerationDict = \
        OrderedDict(sorted(moderationDict.items(), reverse=True))
    # save the moderation queue details for later display
    newswireModerationFilename = baseDir + '/accounts/newswiremoderation.txt'
    if sortedModerationDict:
        saveJson(sortedModerationDict, newswireModerationFilename)
    else:
        # remove the file if there is nothing to moderate
        if os.path.isfile(newswireModerationFilename):
            os.remove(newswireModerationFilename)


def getDictFromNewswire(session, baseDir: str) -> {}:
    """Gets rss feeds as a dictionary from newswire file
    """
    subscriptionsFilename = baseDir + '/accounts/newswire.txt'
    if not os.path.isfile(subscriptionsFilename):
        return {}

    # add rss feeds
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
        itemsList = getRSS(session, url)
        for dateStr, item in itemsList.items():
            result[dateStr] = item

    # add blogs from each user account
    addBlogsToNewswire(baseDir, result, 5)

    # sort into chronological order, latest first
    sortedResult = OrderedDict(sorted(result.items(), reverse=True))
    return sortedResult


def runNewswireDaemon(baseDir: str, httpd, unused: str):
    """Periodically updates RSS feeds
    """
    # initial sleep to allow the system to start up
    time.sleep(50)
    while True:
        # has the session been created yet?
        if not httpd.session:
            print('Newswire daemon waiting for session')
            time.sleep(60)
            continue

        # try to update the feeds
        newNewswire = None
        try:
            newNewswire = getDictFromNewswire(httpd.session, baseDir)
        except Exception as e:
            print('WARN: unable to update newswire ' + str(e))
            time.sleep(120)
            continue

        httpd.newswire = newNewswire
        print('Newswire updated')
        # wait a while before the next feeds update
        time.sleep(1200)


def runNewswireWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the newswire update thread running even if it dies
    """
    print('Starting newswire watchdog')
    newswireOriginal = \
        httpd.thrPostSchedule.clone(runNewswireDaemon)
    httpd.thrNewswireDaemon.start()
    while True:
        time.sleep(50)
        if not httpd.thrNewswireDaemon.isAlive():
            httpd.thrNewswireDaemon.kill()
            httpd.thrNewswireDaemon = \
                newswireOriginal.clone(runNewswireDaemon)
            httpd.thrNewswireDaemon.start()
            print('Restarting newswire daemon...')
