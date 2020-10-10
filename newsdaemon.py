__filename__ = "newsdaemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
import datetime
import urllib.parse
from collections import OrderedDict
from newswire import getDictFromNewswire
from posts import createNewsPost
from utils import loadJson
from utils import saveJson
from utils import getStatusNumber


def updateFeedsOutboxIndex(baseDir: str, domain: str, postId: str) -> None:
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


def saveArrivedTime(baseDir: str, postFilename: str, arrived: str) -> None:
    """Saves the time when an rss post arrived to a file
    """
    arrivedFile = open(postFilename + '.arrived', 'w+')
    if arrivedFile:
        arrivedFile.write(arrived)
        arrivedFile.close()


def convertRSStoActivityPub(baseDir: str, httpPrefix: str,
                            domain: str, port: int,
                            newswire: {},
                            translate: {},
                            recentPostsCache: {}, maxRecentPosts: int,
                            session, cachedWebfingers: {},
                            personCache: {}) -> None:
    """Converts rss items in a newswire into posts
    """
    basePath = baseDir + '/accounts/news@' + domain + '/outbox'
    if not os.path.isdir(basePath):
        os.mkdir(basePath)

    # oldest items first
    newswireReverse = \
        OrderedDict(sorted(newswire.items(), reverse=False))

    for dateStr, item in newswireReverse.items():
        originalDateStr = dateStr
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
            # don't create the post if it already exists
            # set the url
            newswire[originalDateStr][1] = \
                '/users/news/statuses/' + statusNumber
            # set the filename
            newswire[originalDateStr][3] = filename
            continue

        rssTitle = urllib.parse.unquote_plus(item[0]).encode('utf-8')
        url = urllib.parse.unquote_plus(item[1]).encode('utf-8')
        rssDescription = ''

        # get the rss description if it exists
        rssDescription = item[4]

        # add the off-site link to the description
        if rssDescription:
            rssDescription += \
                '\n\n' + translate['Read more...'] + '\n' + url
        else:
            rssDescription = translate['Read more...'] + '\n' + url

        followersOnly = False
        useBlurhash = False
        # NOTE: the id when the post is created will not be
        # consistent (it's based on the current time, not the
        # published time), so we change that later
        blog = createNewsPost(baseDir,
                              domain, port, httpPrefix,
                              rssDescription, followersOnly, False,
                              None, None, None, useBlurhash,
                              rssTitle)
        if not blog:
            continue

        idStr = \
            httpPrefix + '://' + domain + '/users/news' + \
            '/statuses/' + statusNumber + '/replies'
        blog['news'] = True

        # note the time of arrival
        currTime = datetime.datetime.utcnow()
        blog['object']['arrived'] = currTime.strftime("%Y-%m-%dT%H:%M:%SZ")

        # change the id, based upon the published time
        blog['object']['replies']['id'] = idStr
        blog['object']['replies']['first']['partOf'] = idStr

        blog['id'] = newPostId + '/activity'
        blog['object']['id'] = newPostId
        blog['object']['atomUri'] = newPostId
        blog['object']['url'] = \
            httpPrefix + '://' + domain + '/@news/' + statusNumber
        blog['object']['published'] = dateStr

        postId = newPostId.replace('/', '#')

        moderated = item[5]

        # save the post and update the index
        if saveJson(blog, filename):
            updateFeedsOutboxIndex(baseDir, domain, postId + '.json')

            # Save a file containing the time when the post arrived
            # this can then later be used to construct the news timeline
            # excluding items during the voting period
            if moderated:
                saveArrivedTime(baseDir, filename, blog['object']['arrived'])
            else:
                if os.path.isfile(filename + '.arrived'):
                    os.remove(filename + '.arrived')

            # set the url
            newswire[originalDateStr][1] = \
                '/users/news/statuses/' + statusNumber
            # set the filename
            newswire[originalDateStr][3] = filename


def mergeWithPreviousNewswire(oldNewswire: {}, newNewswire: {}) -> None:
    """Preserve any votes or generated activitypub post filename
    as rss feeds are updated
    """
    for published, fields in oldNewswire.items():
        if not newNewswire.get(published):
            continue
        newNewswire[published][1] = fields[1]
        newNewswire[published][2] = fields[2]
        newNewswire[published][3] = fields[3]


def runNewswireDaemon(baseDir: str, httpd,
                      httpPrefix: str, domain: str, port: int,
                      translate: {}) -> None:
    """Periodically updates RSS feeds
    """
    newswireStateFilename = baseDir + '/accounts/.newswirestate.json'

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

        if not httpd.newswire:
            if os.path.isfile(newswireStateFilename):
                httpd.newswire = loadJson(newswireStateFilename)

        mergeWithPreviousNewswire(httpd.newswire, newNewswire)

        httpd.newswire = newNewswire
        saveJson(httpd.newswire, newswireStateFilename)
        print('Newswire updated')

        convertRSStoActivityPub(baseDir,
                                httpPrefix, domain, port,
                                newNewswire, translate,
                                httpd.recentPostsCache,
                                httpd.maxRecentPosts,
                                httpd.session,
                                httpd.cachedWebfingers,
                                httpd.personCache)
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
