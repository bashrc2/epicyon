__filename__ = "newsdaemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
from newswire import getDictFromNewswire
from posts import createNewsPost
from utils import saveJson


def updateFeedsIndex(baseDir: str, filename: str) -> None:
    """Updates the index used for imported RSS feeds
    """
    indexFilename = baseDir + '/accounts/feeds.index'

    if os.path.isfile(indexFilename):
        if filename not in open(indexFilename).read():
            try:
                with open(indexFilename, 'r+') as feedsFile:
                    content = feedsFile.read()
                    feedsFile.seek(0, 0)
                    feedsFile.write(filename + '\n' + content)
                    print('DEBUG: feeds post added to index')
            except Exception as e:
                print('WARN: Failed to write entry to feeds posts index ' +
                      indexFilename + ' ' + str(e))
    else:
        feedsFile = open(indexFilename, 'w+')
        if feedsFile:
            feedsFile.write(filename + '\n')
            feedsFile.close()


def convertRSStoActivityPub(baseDir: str, httpPrefix: str,
                            domain: str, port: int,
                            newswire: {},
                            translate: {}) -> None:
    """Converts rss items in a newswire into posts
    """
    basePath = baseDir + '/accounts/feeds'
    if not os.path.isdir(basePath):
        os.mkdir(basePath)

    nickname = 'feeds'

    for dateStr, item in newswire.items():
        dateStr = dateStr.replace(' ', 'T')
        dateStr = dateStr.replace('+00:00', 'Z')

        filename = basePath + '/' + dateStr + '.json'
        if os.path.isfile(filename):
            continue

        rssTitle = item[0]
        url = item[1]
        rssDescription = ''
        if len(item) >= 4:
            rssDescription = item[4]
        if rssDescription:
            rssDescription += \
                '\n\n' + translate['Read more...'] + '\n' + url
        else:
            rssDescription = url
        blog = createNewsPost(baseDir,
                              nickname, domain, port,
                              httpPrefix, dateStr,
                              rssTitle, rssDescription,
                              None, None, None, False)
        if saveJson(blog, filename):
            updateFeedsIndex(baseDir, filename)


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
