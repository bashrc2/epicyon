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
from utils import locatePost
from utils import loadJson
from utils import saveJson
from utils import isSuspended
from utils import containsInvalidChars
from blocking import isBlockedDomain


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
        rssStr += '    <link>' + httpPrefix + '://' + domainFull + \
            '/newswire.xml' + '</link>'
    elif title.startswith('Site'):
        rssStr += '    <title>' + domainFull + '</title>'
        rssStr += '    <link>' + httpPrefix + '://' + domainFull + \
            '/blog/rss.xml' + '</link>'
    else:
        rssStr += '    <title>' + translate[title] + '</title>'
        rssStr += '    <link>' + httpPrefix + '://' + domainFull + \
            '/users/' + nickname + '/rss.xml' + '</link>'
    return rssStr


def rss2Footer() -> str:
    """Footer for an RSS 2.0 feed
    """
    rssStr = '</channel>'
    rssStr += '</rss>'
    return rssStr


def getNewswireTags(text: str) -> []:
    """Returns a list of hashtags found in the given text
    """
    if ' ' not in text:
        return []
    textSimplified = \
        text.replace(',', ' ').replace(';', ' ').replace('- ', ' ')
    textSimplified = textSimplified.replace('. ', ' ').strip()
    if textSimplified.endswith('.'):
        textSimplified = textSimplified[:len(textSimplified)-1]
    words = textSimplified.split(' ')
    tags = []
    for wrd in words:
        if wrd.startswith('#'):
            if len(wrd) > 1:
                if wrd not in tags:
                    tags.append(wrd)
    return tags


def addNewswireDictEntry(newswire: {}, dateStr: str,
                         title: str, link: str,
                         votesStatus: str, postFilename: str,
                         description: str, moderated: bool) -> None:
    """Update the newswire dictionary
    """
    newswire[dateStr] = [title, link,
                         votesStatus, postFilename,
                         description, moderated,
                         getNewswireTags(title + ' ' + description)]


def xml2StrToDict(baseDir: str, xmlStr: str, moderated: bool,
                  maxPostsPerSource: int) -> {}:
    """Converts an xml 2.0 string to a dictionary
    """
    if '<item>' not in xmlStr:
        return {}
    result = {}
    rssItems = xmlStr.split('<item>')
    postCtr = 0
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
        description = ''
        if '<description>' in rssItem and '</description>' in rssItem:
            description = rssItem.split('<description>')[1]
            description = description.split('</description>')[0]
        link = rssItem.split('<link>')[1]
        link = link.split('</link>')[0]
        if '://' not in link:
            continue
        domain = link.split('://')[1]
        if '/' in domain:
            domain = domain.split('/')[0]
        if isBlockedDomain(baseDir, domain):
            continue
        pubDate = rssItem.split('<pubDate>')[1]
        pubDate = pubDate.split('</pubDate>')[0]
        parsed = False
        try:
            publishedDate = \
                datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %z")
            postFilename = ''
            votesStatus = []
            addNewswireDictEntry(result, str(publishedDate),
                                 title, link,
                                 votesStatus, postFilename,
                                 description, moderated)
            postCtr += 1
            if postCtr >= maxPostsPerSource:
                break
            parsed = True
        except BaseException:
            pass
        if not parsed:
            try:
                publishedDate = \
                    datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S UT")
                postFilename = ''
                votesStatus = []
                addNewswireDictEntry(result, str(publishedDate) + '+00:00',
                                     title, link,
                                     votesStatus, postFilename,
                                     description, moderated)
                postCtr += 1
                if postCtr >= maxPostsPerSource:
                    break
                parsed = True
            except BaseException:
                print('WARN: unrecognized RSS date format: ' + pubDate)
                pass
    return result


def atomFeedToDict(baseDir: str, xmlStr: str, moderated: bool,
                   maxPostsPerSource: int) -> {}:
    """Converts an atom feed string to a dictionary
    """
    if '<entry>' not in xmlStr:
        return {}
    result = {}
    rssItems = xmlStr.split('<entry>')
    postCtr = 0
    for rssItem in rssItems:
        if '<title>' not in rssItem:
            continue
        if '</title>' not in rssItem:
            continue
        if '<link>' not in rssItem:
            continue
        if '</link>' not in rssItem:
            continue
        if '<updated>' not in rssItem:
            continue
        if '</updated>' not in rssItem:
            continue
        title = rssItem.split('<title>')[1]
        title = title.split('</title>')[0]
        description = ''
        if '<summary>' in rssItem and '</summary>' in rssItem:
            description = rssItem.split('<summary>')[1]
            description = description.split('</summary>')[0]
        link = rssItem.split('<link>')[1]
        link = link.split('</link>')[0]
        if '://' not in link:
            continue
        domain = link.split('://')[1]
        if '/' in domain:
            domain = domain.split('/')[0]
        if isBlockedDomain(baseDir, domain):
            continue
        pubDate = rssItem.split('<updated>')[1]
        pubDate = pubDate.split('</updated>')[0]
        parsed = False
        try:
            publishedDate = \
                datetime.strptime(pubDate, "%Y-%m-%dT%H:%M:%SZ")
            postFilename = ''
            votesStatus = []
            addNewswireDictEntry(result, str(publishedDate),
                                 title, link,
                                 votesStatus, postFilename,
                                 description, moderated)
            postCtr += 1
            if postCtr >= maxPostsPerSource:
                break
            parsed = True
        except BaseException:
            pass
        if not parsed:
            try:
                publishedDate = \
                    datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S UT")
                postFilename = ''
                votesStatus = []
                addNewswireDictEntry(result, str(publishedDate) + '+00:00',
                                     title, link,
                                     votesStatus, postFilename,
                                     description, moderated)
                postCtr += 1
                if postCtr >= maxPostsPerSource:
                    break
                parsed = True
            except BaseException:
                print('WARN: unrecognized atom feed date format: ' + pubDate)
                pass
    return result


def xmlStrToDict(baseDir: str, xmlStr: str, moderated: bool,
                 maxPostsPerSource: int) -> {}:
    """Converts an xml string to a dictionary
    """
    if 'rss version="2.0"' in xmlStr:
        return xml2StrToDict(baseDir, xmlStr, moderated, maxPostsPerSource)
    elif 'xmlns="http://www.w3.org/2005/Atom"' in xmlStr:
        return atomFeedToDict(baseDir, xmlStr, moderated, maxPostsPerSource)
    return {}


def getRSS(baseDir: str, session, url: str, moderated: bool,
           maxPostsPerSource: int,
           maxFeedSizeKb: int) -> {}:
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
        if result:
            if int(len(result.text) / 1024) < maxFeedSizeKb and \
               not containsInvalidChars(result.text):
                return xmlStrToDict(baseDir, result.text, moderated,
                                    maxPostsPerSource)
            else:
                print('WARN: feed is too large: ' + url)
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
        url = fields[1]
        if domainFull not in url:
            url = httpPrefix + '://' + domainFull + url
        rssStr += '  <link>' + url + '</link>\n'

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
    # local blog entries are unmoderated by default
    moderated = False

    # local blogs can potentially be moderated
    moderatedFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + \
        '/.newswiremoderated'
    if os.path.isfile(moderatedFilename):
        moderated = True

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
                    votes = []
                    if os.path.isfile(fullPostFilename + '.votes'):
                        votes = loadJson(fullPostFilename + '.votes')
                    description = ''
                    addNewswireDictEntry(newswire, published,
                                         postJsonObject['object']['summary'],
                                         postJsonObject['object']['url'],
                                         votes, fullPostFilename,
                                         description, moderated)

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

            if os.path.isfile(baseDir + '/accounts/' + handle +
                              '/.nonewswire'):
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


def getDictFromNewswire(session, baseDir: str,
                        maxPostsPerSource: int, maxFeedSizeKb: int) -> {}:
    """Gets rss feeds as a dictionary from newswire file
    """
    subscriptionsFilename = baseDir + '/accounts/newswire.txt'
    if not os.path.isfile(subscriptionsFilename):
        return {}

    maxPostsPerSource = 5

    # add rss feeds
    rssFeed = []
    with open(subscriptionsFilename, 'r') as fp:
        rssFeed = fp.readlines()
    result = {}
    for url in rssFeed:
        url = url.strip()

        # Does this contain a url?
        if '://' not in url:
            continue

        # is this a comment?
        if url.startswith('#'):
            continue

        # should this feed be moderated?
        moderated = False
        if '*' in url:
            moderated = True
            url = url.replace('*', '').strip()

        itemsList = getRSS(baseDir, session, url, moderated,
                           maxPostsPerSource, maxFeedSizeKb)
        for dateStr, item in itemsList.items():
            result[dateStr] = item

    # add blogs from each user account
    addBlogsToNewswire(baseDir, result, maxPostsPerSource)

    # sort into chronological order, latest first
    sortedResult = OrderedDict(sorted(result.items(), reverse=True))
    return sortedResult
