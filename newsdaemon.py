__filename__ = "newsdaemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
from collections import OrderedDict
from newswire import getDictFromNewswire
from posts import createBlogPost
from utils import saveJson
from utils import getStatusNumber


def updateFeedsIndex(baseDir: str, domain: str, postId: str) -> None:
    """Updates the index used for imported RSS feeds
    """
    basePath = baseDir + '/accounts/news@' + domain
    indexFilename = basePath + '/outbox.index'

    if os.path.isfile(indexFilename):
        if postId not in open(indexFilename).read():
            try:
                with open(indexFilename, 'r+') as feedsFile:
                    content = feedsFile.read()
                    feedsFile.seek(0, 0)
                    feedsFile.write(postId + '\n' + content)
                    print('DEBUG: feeds post added to index')
            except Exception as e:
                print('WARN: Failed to write entry to feeds posts index ' +
                      indexFilename + ' ' + str(e))
    else:
        feedsFile = open(indexFilename, 'w+')
        if feedsFile:
            feedsFile.write(postId + '\n')
            feedsFile.close()


def convertRSStoActivityPub(baseDir: str, httpPrefix: str,
                            domain: str, port: int,
                            newswire: {},
                            translate: {}) -> None:
    """Converts rss items in a newswire into posts
    """
    basePath = baseDir + '/accounts/news@' + domain + '/outbox'
    if not os.path.isdir(basePath):
        os.mkdir(basePath)

    newswireReverse = \
        OrderedDict(sorted(newswire.items(), reverse=False))

    for dateStr, item in newswireReverse.items():
        # convert the date to the format used by ActivityPub
        dateStr = dateStr.replace(' ', 'T')
        dateStr = dateStr.replace('+00:00', 'Z')

        statusNumber, published = getStatusNumber(dateStr)
        newPostId = \
            httpPrefix + '://' + domain + \
            '/users/news/statuses/' + statusNumber

        # file where the post is stored
        filename = basePath + '/' + newPostId.replace('/', '#') + '.json'
        if os.path.isfile(filename):
            # if a local post exists as html then change the link
            # to the local one
            htmlFilename = filename.replace('.json', '.html')
            if os.path.isfile(htmlFilename):
                item[1] = '/users/news/statuses/' + statusNumber + '.html'
            # don't create the post if it already exists
            continue

        rssTitle = item[0]
        url = item[1]
        rssDescription = ''

        # get the rss description if it exists
        if len(item) >= 5:
            rssDescription = item[4]

        # add the off-site link to the description
        if rssDescription:
            rssDescription += \
                '\n\n' + translate['Read more...'] + '\n' + url
        else:
            rssDescription = url

        followersOnly = False
        useBlurhash = False
        blog = createBlogPost(baseDir,
                              'news', domain, port, httpPrefix,
                              rssDescription, followersOnly, False,
                              False,
                              None, None, None, useBlurhash,
                              None, None, rssTitle,
                              False,
                              None, None, None)
        if not blog:
            continue

        idStr = \
            httpPrefix + '://' + domain + '/users/news' + \
            '/statuses/' + statusNumber + '/replies'
        blog['object']['replies']['id'] = idStr
        blog['object']['replies']['first']['partOf'] = idStr

        blog['id'] = newPostId + '/activity'
        blog['object']['id'] = newPostId
        blog['object']['atomUri'] = newPostId
        blog['object']['url'] = \
            httpPrefix + '://' + domain + '/@news/' + statusNumber
        blog['object']['published'] = dateStr

        postId = newPostId.replace('/', '#')

        # save the post and update the index
        if saveJson(blog, filename):
            updateFeedsIndex(baseDir, domain, postId + '.json')


def runNewswireDaemon(baseDir: str, httpd,
                      httpPrefix: str, domain: str, port: int,
                      translate: {}) -> None:
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

        convertRSStoActivityPub(baseDir,
                                httpPrefix, domain, port,
                                newNewswire, translate)
        print('Newswire feed converted to ActivityPub')

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
