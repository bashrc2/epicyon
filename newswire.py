__filename__ = "newswire.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface Columns"

import os
import json
import requests
from socket import error as SocketError
import errno
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from collections import OrderedDict
from utils import validPostDate
from categories import setHashtagCategory
from utils import dangerousSVG
from utils import getFavFilenameFromUrl
from utils import getBaseContentFromPost
from utils import hasObjectDict
from utils import firstParagraphFromString
from utils import isPublicPost
from utils import locatePost
from utils import loadJson
from utils import saveJson
from utils import isSuspended
from utils import containsInvalidChars
from utils import removeHtml
from utils import isAccountDir
from utils import acctDir
from utils import local_actor_url
from blocking import isBlockedDomain
from blocking import isBlockedHashtag
from filters import isFiltered
from session import downloadImageAnyMimeType


def _removeCDATA(text: str) -> str:
    """Removes any CDATA from the given text
    """
    if 'CDATA[' in text:
        text = text.split('CDATA[')[1]
        if ']' in text:
            text = text.split(']')[0]
    return text


def rss2Header(http_prefix: str,
               nickname: str, domain_full: str,
               title: str, translate: {}) -> str:
    """Header for an RSS 2.0 feed
    """
    rssStr = \
        "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" + \
        "<rss version=\"2.0\">" + \
        '<channel>'

    if title.startswith('News'):
        rssStr += \
            '    <title>Newswire</title>' + \
            '    <link>' + http_prefix + '://' + domain_full + \
            '/newswire.xml' + '</link>'
    elif title.startswith('Site'):
        rssStr += \
            '    <title>' + domain_full + '</title>' + \
            '    <link>' + http_prefix + '://' + domain_full + \
            '/blog/rss.xml' + '</link>'
    else:
        rssStr += \
            '    <title>' + translate[title] + '</title>' + \
            '    <link>' + \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '/rss.xml' + '</link>'
    return rssStr


def rss2Footer() -> str:
    """Footer for an RSS 2.0 feed
    """
    rssStr = '</channel></rss>'
    return rssStr


def getNewswireTags(text: str, maxTags: int) -> []:
    """Returns a list of hashtags found in the given text
    """
    if '#' not in text:
        return []
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
        if not wrd.startswith('#'):
            continue
        if len(wrd) <= 1:
            continue
        if wrd in tags:
            continue
        tags.append(wrd)
        if len(tags) >= maxTags:
            break
    return tags


def limitWordLengths(text: str, maxWordLength: int) -> str:
    """Limits the maximum length of words so that the newswire
    column cannot become too wide
    """
    if ' ' not in text:
        return text
    words = text.split(' ')
    result = ''
    for wrd in words:
        if len(wrd) > maxWordLength:
            wrd = wrd[:maxWordLength]
        if result:
            result += ' '
        result += wrd
    return result


def getNewswireFaviconUrl(url: str) -> str:
    """Returns a favicon url from the given article link
    """
    if '://' not in url:
        return '/newswire_favicon.ico'
    if url.startswith('http://'):
        if not (url.endswith('.onion') or url.endswith('.i2p')):
            return '/newswire_favicon.ico'
    domain = url.split('://')[1]
    if '/' not in domain:
        return url + '/favicon.ico'
    else:
        domain = domain.split('/')[0]
    return url.split('://')[0] + '://' + domain + '/favicon.ico'


def _downloadNewswireFeedFavicon(session, base_dir: str,
                                 link: str, debug: bool) -> bool:
    """Downloads the favicon for the given feed link
    """
    favUrl = getNewswireFaviconUrl(link)
    if '://' not in link:
        return False
    timeoutSec = 10
    imageData, mimeType = \
        downloadImageAnyMimeType(session, favUrl, timeoutSec, debug)
    if not imageData or not mimeType:
        return False

    # update the favicon url
    extensionsToMime = {
        'ico': 'x-icon',
        'png': 'png',
        'jpg': 'jpeg',
        'gif': 'gif',
        'avif': 'avif',
        'svg': 'svg+xml',
        'webp': 'webp'
    }
    for ext, mimeExt in extensionsToMime.items():
        if 'image/' + mimeExt in mimeType:
            favUrl = favUrl.replace('.ico', '.' + ext)
            break

    # create cached favicons directory if needed
    if not os.path.isdir(base_dir + '/favicons'):
        os.mkdir(base_dir + '/favicons')

    # check svg for dubious scripts
    if favUrl.endswith('.svg'):
        imageDataStr = str(imageData)
        if dangerousSVG(imageDataStr, False):
            return False

    # save to the cache
    favFilename = getFavFilenameFromUrl(base_dir, favUrl)
    if os.path.isfile(favFilename):
        return True
    try:
        with open(favFilename, 'wb+') as fp:
            fp.write(imageData)
    except OSError:
        print('EX: failed writing favicon ' + favFilename)
        return False

    return True


def _addNewswireDictEntry(base_dir: str, domain: str,
                          newswire: {}, dateStr: str,
                          title: str, link: str,
                          votesStatus: str, postFilename: str,
                          description: str, moderated: bool,
                          mirrored: bool,
                          tags: [],
                          maxTags: int, session, debug: bool) -> None:
    """Update the newswire dictionary
    """
    # remove any markup
    title = removeHtml(title)
    description = removeHtml(description)

    allText = title + ' ' + description

    # check that none of the text is filtered against
    if isFiltered(base_dir, None, None, allText):
        return

    title = limitWordLengths(title, 13)

    if tags is None:
        tags = []

    # extract hashtags from the text of the feed post
    postTags = getNewswireTags(allText, maxTags)

    # combine the tags into a single list
    for tag in tags:
        if tag in postTags:
            continue
        if len(postTags) < maxTags:
            postTags.append(tag)

    # check that no tags are blocked
    for tag in postTags:
        if isBlockedHashtag(base_dir, tag):
            return

    _downloadNewswireFeedFavicon(session, base_dir, link, debug)

    newswire[dateStr] = [
        title,
        link,
        votesStatus,
        postFilename,
        description,
        moderated,
        postTags,
        mirrored
    ]


def _validFeedDate(pubDate: str, debug: bool = False) -> bool:
    # convert from YY-MM-DD HH:MM:SS+00:00 to
    # YY-MM-DDTHH:MM:SSZ
    postDate = pubDate.replace(' ', 'T').replace('+00:00', 'Z')
    return validPostDate(postDate, 90, debug)


def parseFeedDate(pubDate: str) -> str:
    """Returns a UTC date string based on the given date string
    This tries a number of formats to see which work
    """
    formats = ("%a, %d %b %Y %H:%M:%S %z",
               "%a, %d %b %Y %H:%M:%S Z",
               "%a, %d %b %Y %H:%M:%S GMT",
               "%a, %d %b %Y %H:%M:%S EST",
               "%a, %d %b %Y %H:%M:%S PST",
               "%a, %d %b %Y %H:%M:%S AST",
               "%a, %d %b %Y %H:%M:%S CST",
               "%a, %d %b %Y %H:%M:%S MST",
               "%a, %d %b %Y %H:%M:%S AKST",
               "%a, %d %b %Y %H:%M:%S HST",
               "%a, %d %b %Y %H:%M:%S UT",
               "%Y-%m-%dT%H:%M:%SZ",
               "%Y-%m-%dT%H:%M:%S%z")
    publishedDate = None
    for dateFormat in formats:
        if ',' in pubDate and ',' not in dateFormat:
            continue
        if ',' not in pubDate and ',' in dateFormat:
            continue
        if 'Z' in pubDate and 'Z' not in dateFormat:
            continue
        if 'Z' not in pubDate and 'Z' in dateFormat:
            continue
        if 'EST' not in pubDate and 'EST' in dateFormat:
            continue
        if 'GMT' not in pubDate and 'GMT' in dateFormat:
            continue
        if 'EST' in pubDate and 'EST' not in dateFormat:
            continue
        if 'UT' not in pubDate and 'UT' in dateFormat:
            continue
        if 'UT' in pubDate and 'UT' not in dateFormat:
            continue

        try:
            publishedDate = datetime.strptime(pubDate, dateFormat)
        except BaseException:
            continue

        if publishedDate:
            if pubDate.endswith(' EST'):
                hoursAdded = timedelta(hours=5)
                publishedDate = publishedDate + hoursAdded
            break

    pubDateStr = None
    if publishedDate:
        offset = publishedDate.utcoffset()
        if offset:
            publishedDate = publishedDate - offset
        # convert local date to UTC
        publishedDate = publishedDate.replace(tzinfo=timezone.utc)
        pubDateStr = str(publishedDate)
        if not pubDateStr.endswith('+00:00'):
            pubDateStr += '+00:00'
    else:
        print('WARN: unrecognized date format: ' + pubDate)

    return pubDateStr


def loadHashtagCategories(base_dir: str, language: str) -> None:
    """Loads an rss file containing hashtag categories
    """
    hashtagCategoriesFilename = base_dir + '/categories.xml'
    if not os.path.isfile(hashtagCategoriesFilename):
        hashtagCategoriesFilename = \
            base_dir + '/defaultcategories/' + language + '.xml'
        if not os.path.isfile(hashtagCategoriesFilename):
            return

    with open(hashtagCategoriesFilename, 'r') as fp:
        xmlStr = fp.read()
        _xml2StrToHashtagCategories(base_dir, xmlStr, 1024, True)


def _xml2StrToHashtagCategories(base_dir: str, xmlStr: str,
                                maxCategoriesFeedItemSizeKb: int,
                                force: bool = False) -> None:
    """Updates hashtag categories based upon an rss feed
    """
    rssItems = xmlStr.split('<item>')
    maxBytes = maxCategoriesFeedItemSizeKb * 1024
    for rssItem in rssItems:
        if not rssItem:
            continue
        if len(rssItem) > maxBytes:
            print('WARN: rss categories feed item is too big')
            continue
        if '<title>' not in rssItem:
            continue
        if '</title>' not in rssItem:
            continue
        if '<description>' not in rssItem:
            continue
        if '</description>' not in rssItem:
            continue
        categoryStr = rssItem.split('<title>')[1]
        categoryStr = categoryStr.split('</title>')[0].strip()
        if not categoryStr:
            continue
        if 'CDATA' in categoryStr:
            continue
        hashtagListStr = rssItem.split('<description>')[1]
        hashtagListStr = hashtagListStr.split('</description>')[0].strip()
        if not hashtagListStr:
            continue
        if 'CDATA' in hashtagListStr:
            continue
        hashtagList = hashtagListStr.split(' ')
        if not isBlockedHashtag(base_dir, categoryStr):
            for hashtag in hashtagList:
                setHashtagCategory(base_dir, hashtag, categoryStr,
                                   False, force)


def _xml2StrToDict(base_dir: str, domain: str, xmlStr: str,
                   moderated: bool, mirrored: bool,
                   maxPostsPerSource: int,
                   max_feed_item_size_kb: int,
                   maxCategoriesFeedItemSizeKb: int,
                   session, debug: bool) -> {}:
    """Converts an xml RSS 2.0 string to a dictionary
    """
    if '<item>' not in xmlStr:
        return {}
    result = {}

    # is this an rss feed containing hashtag categories?
    if '<title>#categories</title>' in xmlStr:
        _xml2StrToHashtagCategories(base_dir, xmlStr,
                                    maxCategoriesFeedItemSizeKb)
        return {}

    rssItems = xmlStr.split('<item>')
    postCtr = 0
    maxBytes = max_feed_item_size_kb * 1024
    for rssItem in rssItems:
        if not rssItem:
            continue
        if len(rssItem) > maxBytes:
            print('WARN: rss feed item is too big')
            continue
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
        title = _removeCDATA(title.split('</title>')[0])
        title = removeHtml(title)
        description = ''
        if '<description>' in rssItem and '</description>' in rssItem:
            description = rssItem.split('<description>')[1]
            description = removeHtml(description.split('</description>')[0])
        else:
            if '<media:description>' in rssItem and \
               '</media:description>' in rssItem:
                description = rssItem.split('<media:description>')[1]
                description = description.split('</media:description>')[0]
                description = removeHtml(description)
        link = rssItem.split('<link>')[1]
        link = link.split('</link>')[0]
        if '://' not in link:
            continue
        itemDomain = link.split('://')[1]
        if '/' in itemDomain:
            itemDomain = itemDomain.split('/')[0]
        if isBlockedDomain(base_dir, itemDomain):
            continue
        pubDate = rssItem.split('<pubDate>')[1]
        pubDate = pubDate.split('</pubDate>')[0]

        pubDateStr = parseFeedDate(pubDate)
        if pubDateStr:
            if _validFeedDate(pubDateStr):
                postFilename = ''
                votesStatus = []
                _addNewswireDictEntry(base_dir, domain,
                                      result, pubDateStr,
                                      title, link,
                                      votesStatus, postFilename,
                                      description, moderated,
                                      mirrored, [], 32, session, debug)
                postCtr += 1
                if postCtr >= maxPostsPerSource:
                    break
    if postCtr > 0:
        print('Added ' + str(postCtr) +
              ' rss 2.0 feed items to newswire')
    return result


def _xml1StrToDict(base_dir: str, domain: str, xmlStr: str,
                   moderated: bool, mirrored: bool,
                   maxPostsPerSource: int,
                   max_feed_item_size_kb: int,
                   maxCategoriesFeedItemSizeKb: int,
                   session, debug: bool) -> {}:
    """Converts an xml RSS 1.0 string to a dictionary
    https://validator.w3.org/feed/docs/rss1.html
    """
    itemStr = '<item'
    if itemStr not in xmlStr:
        return {}
    result = {}

    # is this an rss feed containing hashtag categories?
    if '<title>#categories</title>' in xmlStr:
        _xml2StrToHashtagCategories(base_dir, xmlStr,
                                    maxCategoriesFeedItemSizeKb)
        return {}

    rssItems = xmlStr.split(itemStr)
    postCtr = 0
    maxBytes = max_feed_item_size_kb * 1024
    for rssItem in rssItems:
        if not rssItem:
            continue
        if len(rssItem) > maxBytes:
            print('WARN: rss 1.0 feed item is too big')
            continue
        if rssItem.startswith('s>'):
            continue
        if '<title>' not in rssItem:
            continue
        if '</title>' not in rssItem:
            continue
        if '<link>' not in rssItem:
            continue
        if '</link>' not in rssItem:
            continue
        if '<dc:date>' not in rssItem:
            continue
        if '</dc:date>' not in rssItem:
            continue
        title = rssItem.split('<title>')[1]
        title = _removeCDATA(title.split('</title>')[0])
        title = removeHtml(title)
        description = ''
        if '<description>' in rssItem and '</description>' in rssItem:
            description = rssItem.split('<description>')[1]
            description = removeHtml(description.split('</description>')[0])
        else:
            if '<media:description>' in rssItem and \
               '</media:description>' in rssItem:
                description = rssItem.split('<media:description>')[1]
                description = description.split('</media:description>')[0]
                description = removeHtml(description)
        link = rssItem.split('<link>')[1]
        link = link.split('</link>')[0]
        if '://' not in link:
            continue
        itemDomain = link.split('://')[1]
        if '/' in itemDomain:
            itemDomain = itemDomain.split('/')[0]
        if isBlockedDomain(base_dir, itemDomain):
            continue
        pubDate = rssItem.split('<dc:date>')[1]
        pubDate = pubDate.split('</dc:date>')[0]

        pubDateStr = parseFeedDate(pubDate)
        if pubDateStr:
            if _validFeedDate(pubDateStr):
                postFilename = ''
                votesStatus = []
                _addNewswireDictEntry(base_dir, domain,
                                      result, pubDateStr,
                                      title, link,
                                      votesStatus, postFilename,
                                      description, moderated,
                                      mirrored, [], 32, session, debug)
                postCtr += 1
                if postCtr >= maxPostsPerSource:
                    break
    if postCtr > 0:
        print('Added ' + str(postCtr) +
              ' rss 1.0 feed items to newswire')
    return result


def _atomFeedToDict(base_dir: str, domain: str, xmlStr: str,
                    moderated: bool, mirrored: bool,
                    maxPostsPerSource: int,
                    max_feed_item_size_kb: int,
                    session, debug: bool) -> {}:
    """Converts an atom feed string to a dictionary
    """
    if '<entry>' not in xmlStr:
        return {}
    result = {}
    atomItems = xmlStr.split('<entry>')
    postCtr = 0
    maxBytes = max_feed_item_size_kb * 1024
    for atomItem in atomItems:
        if not atomItem:
            continue
        if len(atomItem) > maxBytes:
            print('WARN: atom feed item is too big')
            continue
        if '<title>' not in atomItem:
            continue
        if '</title>' not in atomItem:
            continue
        if '<link>' not in atomItem:
            continue
        if '</link>' not in atomItem:
            continue
        if '<updated>' not in atomItem:
            continue
        if '</updated>' not in atomItem:
            continue
        title = atomItem.split('<title>')[1]
        title = _removeCDATA(title.split('</title>')[0])
        title = removeHtml(title)
        description = ''
        if '<summary>' in atomItem and '</summary>' in atomItem:
            description = atomItem.split('<summary>')[1]
            description = removeHtml(description.split('</summary>')[0])
        else:
            if '<media:description>' in atomItem and \
               '</media:description>' in atomItem:
                description = atomItem.split('<media:description>')[1]
                description = description.split('</media:description>')[0]
                description = removeHtml(description)
        link = atomItem.split('<link>')[1]
        link = link.split('</link>')[0]
        if '://' not in link:
            continue
        itemDomain = link.split('://')[1]
        if '/' in itemDomain:
            itemDomain = itemDomain.split('/')[0]
        if isBlockedDomain(base_dir, itemDomain):
            continue
        pubDate = atomItem.split('<updated>')[1]
        pubDate = pubDate.split('</updated>')[0]

        pubDateStr = parseFeedDate(pubDate)
        if pubDateStr:
            if _validFeedDate(pubDateStr):
                postFilename = ''
                votesStatus = []
                _addNewswireDictEntry(base_dir, domain,
                                      result, pubDateStr,
                                      title, link,
                                      votesStatus, postFilename,
                                      description, moderated,
                                      mirrored, [], 32, session, debug)
                postCtr += 1
                if postCtr >= maxPostsPerSource:
                    break
    if postCtr > 0:
        print('Added ' + str(postCtr) +
              ' atom feed items to newswire')
    return result


def _jsonFeedV1ToDict(base_dir: str, domain: str, xmlStr: str,
                      moderated: bool, mirrored: bool,
                      maxPostsPerSource: int,
                      max_feed_item_size_kb: int,
                      session, debug: bool) -> {}:
    """Converts a json feed string to a dictionary
    See https://jsonfeed.org/version/1.1
    """
    if '"items"' not in xmlStr:
        return {}
    try:
        feedJson = json.loads(xmlStr)
    except BaseException:
        print('EX: _jsonFeedV1ToDict unable to load json ' + str(xmlStr))
        return {}
    maxBytes = max_feed_item_size_kb * 1024
    if not feedJson.get('version'):
        return {}
    if not feedJson['version'].startswith('https://jsonfeed.org/version/1'):
        return {}
    if not feedJson.get('items'):
        return {}
    if not isinstance(feedJson['items'], list):
        return {}
    postCtr = 0
    result = {}
    for jsonFeedItem in feedJson['items']:
        if not jsonFeedItem:
            continue
        if not isinstance(jsonFeedItem, dict):
            continue
        if not jsonFeedItem.get('url'):
            continue
        if not isinstance(jsonFeedItem['url'], str):
            continue
        if not jsonFeedItem.get('date_published'):
            if not jsonFeedItem.get('date_modified'):
                continue
        if not jsonFeedItem.get('content_text'):
            if not jsonFeedItem.get('content_html'):
                continue
        if jsonFeedItem.get('content_html'):
            if not isinstance(jsonFeedItem['content_html'], str):
                continue
            title = removeHtml(jsonFeedItem['content_html'])
        else:
            if not isinstance(jsonFeedItem['content_text'], str):
                continue
            title = removeHtml(jsonFeedItem['content_text'])
        if len(title) > maxBytes:
            print('WARN: json feed title is too long')
            continue
        description = ''
        if jsonFeedItem.get('description'):
            if not isinstance(jsonFeedItem['description'], str):
                continue
            description = removeHtml(jsonFeedItem['description'])
            if len(description) > maxBytes:
                print('WARN: json feed description is too long')
                continue
            if jsonFeedItem.get('tags'):
                if isinstance(jsonFeedItem['tags'], list):
                    for tagName in jsonFeedItem['tags']:
                        if not isinstance(tagName, str):
                            continue
                        if ' ' in tagName:
                            continue
                        if not tagName.startswith('#'):
                            tagName = '#' + tagName
                        if tagName not in description:
                            description += ' ' + tagName

        link = jsonFeedItem['url']
        if '://' not in link:
            continue
        if len(link) > maxBytes:
            print('WARN: json feed link is too long')
            continue
        itemDomain = link.split('://')[1]
        if '/' in itemDomain:
            itemDomain = itemDomain.split('/')[0]
        if isBlockedDomain(base_dir, itemDomain):
            continue
        if jsonFeedItem.get('date_published'):
            if not isinstance(jsonFeedItem['date_published'], str):
                continue
            pubDate = jsonFeedItem['date_published']
        else:
            if not isinstance(jsonFeedItem['date_modified'], str):
                continue
            pubDate = jsonFeedItem['date_modified']

        pubDateStr = parseFeedDate(pubDate)
        if pubDateStr:
            if _validFeedDate(pubDateStr):
                postFilename = ''
                votesStatus = []
                _addNewswireDictEntry(base_dir, domain,
                                      result, pubDateStr,
                                      title, link,
                                      votesStatus, postFilename,
                                      description, moderated,
                                      mirrored, [], 32, session, debug)
                postCtr += 1
                if postCtr >= maxPostsPerSource:
                    break
    if postCtr > 0:
        print('Added ' + str(postCtr) +
              ' json feed items to newswire')
    return result


def _atomFeedYTToDict(base_dir: str, domain: str, xmlStr: str,
                      moderated: bool, mirrored: bool,
                      maxPostsPerSource: int,
                      max_feed_item_size_kb: int,
                      session, debug: bool) -> {}:
    """Converts an atom-style YouTube feed string to a dictionary
    """
    if '<entry>' not in xmlStr:
        return {}
    if isBlockedDomain(base_dir, 'www.youtube.com'):
        return {}
    result = {}
    atomItems = xmlStr.split('<entry>')
    postCtr = 0
    maxBytes = max_feed_item_size_kb * 1024
    for atomItem in atomItems:
        if not atomItem:
            continue
        if not atomItem.strip():
            continue
        if len(atomItem) > maxBytes:
            print('WARN: atom feed item is too big')
            continue
        if '<title>' not in atomItem:
            continue
        if '</title>' not in atomItem:
            continue
        if '<published>' not in atomItem:
            continue
        if '</published>' not in atomItem:
            continue
        if '<yt:videoId>' not in atomItem:
            continue
        if '</yt:videoId>' not in atomItem:
            continue
        title = atomItem.split('<title>')[1]
        title = _removeCDATA(title.split('</title>')[0])
        description = ''
        if '<media:description>' in atomItem and \
           '</media:description>' in atomItem:
            description = atomItem.split('<media:description>')[1]
            description = description.split('</media:description>')[0]
            description = removeHtml(description)
        elif '<summary>' in atomItem and '</summary>' in atomItem:
            description = atomItem.split('<summary>')[1]
            description = description.split('</summary>')[0]
            description = removeHtml(description)
        link = atomItem.split('<yt:videoId>')[1]
        link = link.split('</yt:videoId>')[0]
        link = 'https://www.youtube.com/watch?v=' + link.strip()
        pubDate = atomItem.split('<published>')[1]
        pubDate = pubDate.split('</published>')[0]

        pubDateStr = parseFeedDate(pubDate)
        if pubDateStr:
            if _validFeedDate(pubDateStr):
                postFilename = ''
                votesStatus = []
                _addNewswireDictEntry(base_dir, domain,
                                      result, pubDateStr,
                                      title, link,
                                      votesStatus, postFilename,
                                      description, moderated, mirrored,
                                      [], 32, session, debug)
                postCtr += 1
                if postCtr >= maxPostsPerSource:
                    break
    if postCtr > 0:
        print('Added ' + str(postCtr) + ' YouTube feed items to newswire')
    return result


def _xmlStrToDict(base_dir: str, domain: str, xmlStr: str,
                  moderated: bool, mirrored: bool,
                  maxPostsPerSource: int,
                  max_feed_item_size_kb: int,
                  maxCategoriesFeedItemSizeKb: int,
                  session, debug: bool) -> {}:
    """Converts an xml string to a dictionary
    """
    if '<yt:videoId>' in xmlStr and '<yt:channelId>' in xmlStr:
        print('YouTube feed: reading')
        return _atomFeedYTToDict(base_dir, domain,
                                 xmlStr, moderated, mirrored,
                                 maxPostsPerSource, max_feed_item_size_kb,
                                 session, debug)
    elif 'rss version="2.0"' in xmlStr:
        return _xml2StrToDict(base_dir, domain,
                              xmlStr, moderated, mirrored,
                              maxPostsPerSource, max_feed_item_size_kb,
                              maxCategoriesFeedItemSizeKb,
                              session, debug)
    elif '<?xml version="1.0"' in xmlStr:
        return _xml1StrToDict(base_dir, domain,
                              xmlStr, moderated, mirrored,
                              maxPostsPerSource, max_feed_item_size_kb,
                              maxCategoriesFeedItemSizeKb,
                              session, debug)
    elif 'xmlns="http://www.w3.org/2005/Atom"' in xmlStr:
        return _atomFeedToDict(base_dir, domain,
                               xmlStr, moderated, mirrored,
                               maxPostsPerSource, max_feed_item_size_kb,
                               session, debug)
    elif 'https://jsonfeed.org/version/1' in xmlStr:
        return _jsonFeedV1ToDict(base_dir, domain,
                                 xmlStr, moderated, mirrored,
                                 maxPostsPerSource, max_feed_item_size_kb,
                                 session, debug)
    return {}


def _YTchannelToAtomFeed(url: str) -> str:
    """Converts a YouTube channel url into an atom feed url
    """
    if 'youtube.com/channel/' not in url:
        return url
    channelId = url.split('youtube.com/channel/')[1].strip()
    channelUrl = \
        'https://www.youtube.com/feeds/videos.xml?channel_id=' + channelId
    print('YouTube feed: ' + channelUrl)
    return channelUrl


def getRSS(base_dir: str, domain: str, session, url: str,
           moderated: bool, mirrored: bool,
           maxPostsPerSource: int, maxFeedSizeKb: int,
           max_feed_item_size_kb: int,
           maxCategoriesFeedItemSizeKb: int, debug: bool) -> {}:
    """Returns an RSS url as a dict
    """
    if not isinstance(url, str):
        print('url: ' + str(url))
        print('ERROR: getRSS url should be a string')
        return None
    headers = {
        'Accept': 'text/xml, application/xml; charset=UTF-8'
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
    url = _YTchannelToAtomFeed(url)
    try:
        result = session.get(url, headers=sessionHeaders, params=sessionParams)
        if result:
            if int(len(result.text) / 1024) < maxFeedSizeKb and \
               not containsInvalidChars(result.text):
                return _xmlStrToDict(base_dir, domain, result.text,
                                     moderated, mirrored,
                                     maxPostsPerSource,
                                     max_feed_item_size_kb,
                                     maxCategoriesFeedItemSizeKb,
                                     session, debug)
            else:
                print('WARN: feed is too large, ' +
                      'or contains invalid characters: ' + url)
        else:
            print('WARN: no result returned for feed ' + url)
    except requests.exceptions.RequestException as ex:
        print('WARN: getRSS failed\nurl: ' + str(url) + ', ' +
              'headers: ' + str(sessionHeaders) + ', ' +
              'params: ' + str(sessionParams) + ', ' + str(ex))
    except ValueError as ex:
        print('WARN: getRSS failed\nurl: ' + str(url) + ', ' +
              'headers: ' + str(sessionHeaders) + ', ' +
              'params: ' + str(sessionParams) + ', ' + str(ex))
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('WARN: connection was reset during getRSS ' + str(ex))
        else:
            print('WARN: getRSS, ' + str(ex))
    return None


def getRSSfromDict(base_dir: str, newswire: {},
                   http_prefix: str, domain_full: str,
                   title: str, translate: {}) -> str:
    """Returns an rss feed from the current newswire dict.
    This allows other instances to subscribe to the same newswire
    """
    rssStr = rss2Header(http_prefix,
                        None, domain_full,
                        'Newswire', translate)
    if not newswire:
        return ''
    for published, fields in newswire.items():
        if '+00:00' in published:
            published = published.replace('+00:00', 'Z').strip()
            published = published.replace(' ', 'T')
        else:
            publishedWithOffset = \
                datetime.strptime(published, "%Y-%m-%d %H:%M:%S%z")
            published = publishedWithOffset.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            pubDate = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
        except Exception as ex:
            print('WARN: Unable to convert date ' + published + ' ' + str(ex))
            continue
        rssStr += \
            '<item>\n' + \
            '  <title>' + fields[0] + '</title>\n'
        description = removeHtml(firstParagraphFromString(fields[4]))
        rssStr += '  <description>' + description + '</description>\n'
        url = fields[1]
        if '://' not in url:
            if domain_full not in url:
                url = http_prefix + '://' + domain_full + url
        rssStr += '  <link>' + url + '</link>\n'

        rssDateStr = pubDate.strftime("%a, %d %b %Y %H:%M:%S UT")
        rssStr += \
            '  <pubDate>' + rssDateStr + '</pubDate>\n' + \
            '</item>\n'
    rssStr += rss2Footer()
    return rssStr


def _isNewswireBlogPost(post_json_object: {}) -> bool:
    """Is the given object a blog post?
    There isn't any difference between a blog post and a newswire blog post
    but we may here need to check for different properties than
    isBlogPost does
    """
    if not post_json_object:
        return False
    if not hasObjectDict(post_json_object):
        return False
    if post_json_object['object'].get('summary') and \
       post_json_object['object'].get('url') and \
       post_json_object['object'].get('content') and \
       post_json_object['object'].get('published'):
        return isPublicPost(post_json_object)
    return False


def _getHashtagsFromPost(post_json_object: {}) -> []:
    """Returns a list of any hashtags within a post
    """
    if not hasObjectDict(post_json_object):
        return []
    if not post_json_object['object'].get('tag'):
        return []
    if not isinstance(post_json_object['object']['tag'], list):
        return []
    tags = []
    for tg in post_json_object['object']['tag']:
        if not isinstance(tg, dict):
            continue
        if not tg.get('name'):
            continue
        if not tg.get('type'):
            continue
        if tg['type'] != 'Hashtag':
            continue
        if tg['name'] not in tags:
            tags.append(tg['name'])
    return tags


def _addAccountBlogsToNewswire(base_dir: str, nickname: str, domain: str,
                               newswire: {},
                               maxBlogsPerAccount: int,
                               indexFilename: str,
                               maxTags: int, system_language: str,
                               session, debug: bool) -> None:
    """Adds blogs for the given account to the newswire
    """
    if not os.path.isfile(indexFilename):
        return
    # local blog entries are unmoderated by default
    moderated = False

    # local blogs can potentially be moderated
    moderatedFilename = \
        acctDir(base_dir, nickname, domain) + '/.newswiremoderated'
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
                    locatePost(base_dir, nickname,
                               domain, postUrl, False)
                if not fullPostFilename:
                    print('Unable to locate post for newswire ' + postUrl)
                    ctr += 1
                    if ctr >= maxBlogsPerAccount:
                        break
                    continue

                post_json_object = None
                if fullPostFilename:
                    post_json_object = loadJson(fullPostFilename)
                if _isNewswireBlogPost(post_json_object):
                    published = post_json_object['object']['published']
                    published = published.replace('T', ' ')
                    published = published.replace('Z', '+00:00')
                    votes = []
                    if os.path.isfile(fullPostFilename + '.votes'):
                        votes = loadJson(fullPostFilename + '.votes')
                    content = \
                        getBaseContentFromPost(post_json_object,
                                               system_language)
                    description = firstParagraphFromString(content)
                    description = removeHtml(description)
                    tagsFromPost = _getHashtagsFromPost(post_json_object)
                    summary = post_json_object['object']['summary']
                    _addNewswireDictEntry(base_dir, domain,
                                          newswire, published,
                                          summary,
                                          post_json_object['object']['url'],
                                          votes, fullPostFilename,
                                          description, moderated, False,
                                          tagsFromPost,
                                          maxTags, session, debug)

            ctr += 1
            if ctr >= maxBlogsPerAccount:
                break


def _addBlogsToNewswire(base_dir: str, domain: str, newswire: {},
                        maxBlogsPerAccount: int,
                        maxTags: int, system_language: str,
                        session, debug: bool) -> None:
    """Adds blogs from each user account into the newswire
    """
    moderationDict = {}

    # go through each account
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if not isAccountDir(handle):
                continue

            nickname = handle.split('@')[0]

            # has this account been suspended?
            if isSuspended(base_dir, nickname):
                continue

            if os.path.isfile(base_dir + '/accounts/' + handle +
                              '/.nonewswire'):
                continue

            # is there a blogs timeline for this account?
            accountDir = os.path.join(base_dir + '/accounts', handle)
            blogsIndex = accountDir + '/tlblogs.index'
            if os.path.isfile(blogsIndex):
                domain = handle.split('@')[1]
                _addAccountBlogsToNewswire(base_dir, nickname, domain,
                                           newswire, maxBlogsPerAccount,
                                           blogsIndex, maxTags,
                                           system_language, session,
                                           debug)
        break

    # sort the moderation dict into chronological order, latest first
    sortedModerationDict = \
        OrderedDict(sorted(moderationDict.items(), reverse=True))
    # save the moderation queue details for later display
    newswireModerationFilename = base_dir + '/accounts/newswiremoderation.txt'
    if sortedModerationDict:
        saveJson(sortedModerationDict, newswireModerationFilename)
    else:
        # remove the file if there is nothing to moderate
        if os.path.isfile(newswireModerationFilename):
            try:
                os.remove(newswireModerationFilename)
            except OSError:
                print('EX: _addBlogsToNewswire unable to delete ' +
                      str(newswireModerationFilename))


def getDictFromNewswire(session, base_dir: str, domain: str,
                        maxPostsPerSource: int, maxFeedSizeKb: int,
                        maxTags: int, max_feed_item_size_kb: int,
                        max_newswire_posts: int,
                        maxCategoriesFeedItemSizeKb: int,
                        system_language: str, debug: bool) -> {}:
    """Gets rss feeds as a dictionary from newswire file
    """
    subscriptionsFilename = base_dir + '/accounts/newswire.txt'
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

        # should this feed content be mirrored?
        mirrored = False
        if '!' in url:
            mirrored = True
            url = url.replace('!', '').strip()

        itemsList = getRSS(base_dir, domain, session, url,
                           moderated, mirrored,
                           maxPostsPerSource, maxFeedSizeKb,
                           max_feed_item_size_kb,
                           maxCategoriesFeedItemSizeKb, debug)
        if itemsList:
            for dateStr, item in itemsList.items():
                result[dateStr] = item

    # add blogs from each user account
    _addBlogsToNewswire(base_dir, domain, result,
                        maxPostsPerSource, maxTags, system_language,
                        session, debug)

    # sort into chronological order, latest first
    sortedResult = OrderedDict(sorted(result.items(), reverse=True))

    # are there too many posts? If so then remove the oldest ones
    noOfPosts = len(sortedResult.items())
    if noOfPosts > max_newswire_posts:
        ctr = 0
        removals = []
        for dateStr, item in sortedResult.items():
            ctr += 1
            if ctr > max_newswire_posts:
                removals.append(dateStr)
        for r in removals:
            sortedResult.pop(r)

    return sortedResult
