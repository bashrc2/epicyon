__filename__ = "schedule.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
import datetime
from utils import loadJson
from outbox import postMessageToOutbox

def updatePostSchedule(baseDir: str,handle: str,httpd,maxScheduledPosts: int) -> None:
    """Checks if posts are due to be delivered and if so moves them to the outbox
    """
    scheduleIndexFilename=baseDir+'/accounts/'+handle+'/schedule.index'
    if not os.path.isfile(scheduleIndexFilename):
        return

    # get the current time as an int
    currTime=datetime.datetime.utcnow()
    daysSinceEpoch=(currTime - datetime.datetime(1970,1,1)).days

    scheduleDir=baseDir+'/accounts/'+handle+'/scheduled/'
    indexLines=[]
    deleteSchedulePost=False
    nickname=handle.split('@')[0]
    with open(scheduleIndexFilename, 'r') as fp:
        for line in fp:
            print('DEBUG: schedule line='+line)
            if ' ' not in line:
                continue
            dateStr=line.split(' ')[0]
            if 'T' not in dateStr:
                continue
            postId=line.split(' ',1)[1].replace('\n','')
            postFilename=scheduleDir+postId+'.json'
            print('DEBUG: schedule postFilename '+postFilename)
            if deleteSchedulePost:
                # delete extraneous scheduled posts
                if os.path.isfile(postFilename):
                    os.remove(postFilename)
                continue
            # create the new index file
            indexLines.append(line)
            # convert string date to int
            print('DEBUG: schedule date='+dateStr)
            postTime= \
                datetime.datetime.strptime(dateStr,"%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)
            postDaysSinceEpoch= \
                (postTime - datetime.datetime(1970,1,1)).days
            print('DEBUG: schedule postTime hour='+str(postTime.time().hour))
            print('DEBUG: schedule postTime minute='+str(postTime.time().minute))
            print('DEBUG: schedule daysSinceEpoch='+str(daysSinceEpoch))
            print('DEBUG: schedule postDaysSinceEpoch='+str(postDaysSinceEpoch))
            if daysSinceEpoch < postDaysSinceEpoch:
                print('DEBUG: schedule not yet date')
                continue
            if currTime.time().hour < postTime.time().hour:
                print('DEBUG: schedule not yet hour')
                continue
            if currTime.time().minute < postTime.time().minute:
                print('DEBUG: schedule not yet minute')
                continue
            if not os.path.isfile(postFilename):
                print('WARN: schedule postFilename='+postFilename)
                indexLines.remove(line)
                continue
            # load post
            postJsonObject=loadJson(postFilename)
            if not postJsonObject:
                print('WARN: schedule json not loaded')
                indexLines.remove(line)
                continue

            print('Sending scheduled post '+postId)

            if not postMessageToOutbox(postJsonObject,nickname, \
                                       httpd.server,baseDir, \
                                       httpd.server.httpPrefix, \
                                       httpd.server.domain, \
                                       httpd.server.domainFull, \
                                       httpd.server.port, \
                                       httpd.server.recentPostsCache, \
                                       httpd.server.followersThreads, \
                                       httpd.server.federationList, \
                                       httpd.server.sendThreads, \
                                       httpd.server.postLog, \
                                       httpd.server.cachedWebfingers, \
                                       httpd.server.personCache, \
                                       httpd.server.allowDeletion, \
                                       httpd.server.useTor, \
                                       httpd.server.projectVersion, \
                                       httpd.server.debug):
                indexLines.remove(line)
                continue

            # move to the outbox
            outboxPostFilename= \
                postFilename.replace('/scheduled/','/outbox/')
            os.rename(postFilename,outboxPostFilename)

            print('Scheduled post sent '+postId)

            indexLines.remove(line)
            if len(indexLines)>maxScheduledPosts:
                deleteSchedulePost=True

    # write the new schedule index file
    scheduleIndexFile=baseDir+'/accounts/'+handle+'/schedule.index'
    scheduleFile=open(scheduleIndexFile, "w+")
    if scheduleFile:
        for line in indexLines:
            scheduleFile.write(line)
        scheduleFile.close()

def runPostSchedule(baseDir: str,httpd,maxScheduledPosts: int):
    """Dispatches scheduled posts
    """
    while True:
        time.sleep(60)
        # for each account
        for subdir,dirs,files in os.walk(baseDir+'/accounts'):
            for account in dirs:
                if '@' not in account:
                    continue
                # scheduled posts index for this account
                scheduleIndexFilename=baseDir+'/accounts/'+account+'/schedule.index'
                if not os.path.isfile(scheduleIndexFilename):
                    continue
                updatePostSchedule(baseDir,account,httpd,maxScheduledPosts)

def runPostScheduleWatchdog(projectVersion: str,httpd) -> None:
    """This tries to keep the scheduled post thread running even if it dies
    """
    print('Starting scheduled post watchdog')
    postScheduleOriginal= \
        httpd.thrPostSchedule.clone(runPostSchedule)
    httpd.thrPostSchedule.start()
    while True:
        time.sleep(20) 
        if not httpd.thrPostSchedule.isAlive():
            httpd.thrPostSchedule.kill()
            httpd.thrPostSchedule= \
                postScheduleOriginal.clone(runPostSchedule)
            httpd.thrPostSchedule.start()
            print('Restarting scheduled posts...')
