__filename__ = "schedule.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
import datetime
from utils import getStatusNumber
from utils import loadJson
from outbox import postMessageToOutbox


def _updatePostSchedule(baseDir: str, handle: str, httpd,
                        maxScheduledPosts: int) -> None:
    """Checks if posts are due to be delivered and if so moves them to the outbox
    """
    scheduleIndexFilename = baseDir + '/accounts/' + handle + '/schedule.index'
    if not os.path.isfile(scheduleIndexFilename):
        return

    # get the current time as an int
    currTime = datetime.datetime.utcnow()
    daysSinceEpoch = (currTime - datetime.datetime(1970, 1, 1)).days

    scheduleDir = baseDir + '/accounts/' + handle + '/scheduled/'
    indexLines = []
    deleteSchedulePost = False
    nickname = handle.split('@')[0]
    with open(scheduleIndexFilename, 'r') as fp:
        for line in fp:
            if ' ' not in line:
                continue
            dateStr = line.split(' ')[0]
            if 'T' not in dateStr:
                continue
            postId = line.split(' ', 1)[1].replace('\n', '').replace('\r', '')
            postFilename = scheduleDir + postId + '.json'
            if deleteSchedulePost:
                # delete extraneous scheduled posts
                if os.path.isfile(postFilename):
                    os.remove(postFilename)
                continue
            # create the new index file
            indexLines.append(line)
            # convert string date to int
            postTime = \
                datetime.datetime.strptime(dateStr, "%Y-%m-%dT%H:%M:%S%z")
            postTime = postTime.replace(tzinfo=None)
            postDaysSinceEpoch = \
                (postTime - datetime.datetime(1970, 1, 1)).days
            if daysSinceEpoch < postDaysSinceEpoch:
                continue
            if daysSinceEpoch == postDaysSinceEpoch:
                if currTime.time().hour < postTime.time().hour:
                    continue
                if currTime.time().minute < postTime.time().minute:
                    continue
            if not os.path.isfile(postFilename):
                print('WARN: schedule missing postFilename=' + postFilename)
                indexLines.remove(line)
                continue
            # load post
            postJsonObject = loadJson(postFilename)
            if not postJsonObject:
                print('WARN: schedule json not loaded')
                indexLines.remove(line)
                continue

            # set the published time
            # If this is not recent then http checks on the receiving side
            # will reject it
            statusNumber, published = getStatusNumber()
            if postJsonObject.get('published'):
                postJsonObject['published'] = published
            if postJsonObject.get('object'):
                if isinstance(postJsonObject['object'], dict):
                    if postJsonObject['object'].get('published'):
                        postJsonObject['published'] = published

            print('Sending scheduled post ' + postId)

            if nickname:
                httpd.postToNickname = nickname
            if not postMessageToOutbox(postJsonObject, nickname,
                                       httpd, baseDir,
                                       httpd.httpPrefix,
                                       httpd.domain,
                                       httpd.domainFull,
                                       httpd.onionDomain,
                                       httpd.i2pDomain,
                                       httpd.port,
                                       httpd.recentPostsCache,
                                       httpd.followersThreads,
                                       httpd.federationList,
                                       httpd.sendThreads,
                                       httpd.postLog,
                                       httpd.cachedWebfingers,
                                       httpd.personCache,
                                       httpd.allowDeletion,
                                       httpd.proxyType,
                                       httpd.projectVersion,
                                       httpd.debug,
                                       httpd.YTReplacementDomain,
                                       httpd.showPublishedDateOnly,
                                       httpd.allowLocalNetworkAccess):
                indexLines.remove(line)
                os.remove(postFilename)
                continue

            # move to the outbox
            outboxPostFilename = \
                postFilename.replace('/scheduled/', '/outbox/')
            os.rename(postFilename, outboxPostFilename)

            print('Scheduled post sent ' + postId)

            indexLines.remove(line)
            if len(indexLines) > maxScheduledPosts:
                deleteSchedulePost = True

    # write the new schedule index file
    scheduleIndexFile = \
        baseDir + '/accounts/' + handle + '/schedule.index'
    scheduleFile = open(scheduleIndexFile, "w+")
    if scheduleFile:
        for line in indexLines:
            scheduleFile.write(line)
        scheduleFile.close()


def runPostSchedule(baseDir: str, httpd, maxScheduledPosts: int):
    """Dispatches scheduled posts
    """
    while True:
        time.sleep(60)
        # for each account
        for subdir, dirs, files in os.walk(baseDir + '/accounts'):
            for account in dirs:
                if '@' not in account:
                    continue
                if account.startswith('inbox@'):
                    continue
                if account.startswith('news@'):
                    continue
                # scheduled posts index for this account
                scheduleIndexFilename = \
                    baseDir + '/accounts/' + account + '/schedule.index'
                if not os.path.isfile(scheduleIndexFilename):
                    continue
                _updatePostSchedule(baseDir, account, httpd, maxScheduledPosts)
        break


def runPostScheduleWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the scheduled post thread running even if it dies
    """
    print('Starting scheduled post watchdog')
    postScheduleOriginal = \
        httpd.thrPostSchedule.clone(runPostSchedule)
    httpd.thrPostSchedule.start()
    while True:
        time.sleep(20)
        if not httpd.thrPostSchedule.is_alive():
            httpd.thrPostSchedule.kill()
            httpd.thrPostSchedule = \
                postScheduleOriginal.clone(runPostSchedule)
            httpd.thrPostSchedule.start()
            print('Restarting scheduled posts...')


def removeScheduledPosts(baseDir: str, nickname: str, domain: str) -> None:
    """Removes any scheduled posts
    """
    # remove the index
    scheduleIndexFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/schedule.index'
    if os.path.isfile(scheduleIndexFilename):
        os.remove(scheduleIndexFilename)
    # remove the scheduled posts
    scheduledDir = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/scheduled'
    if not os.path.isdir(scheduledDir):
        return
    for scheduledPostFilename in os.listdir(scheduledDir):
        filePath = os.path.join(scheduledDir, scheduledPostFilename)
        try:
            if os.path.isfile(filePath):
                os.remove(filePath)
        except BaseException:
            pass
