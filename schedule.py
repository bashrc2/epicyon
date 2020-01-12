__filename__ = "schedule.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import datetime

def addSchedulePost(baseDir: str,nickname: str,domain: str, \
                    eventDateStr: str,postId: str) -> None:
    """Adds a scheduled post to the index
    """
    handle=nickname+'@'+domain
    scheduleIndexFilename=baseDir+'/accounts/'+handle+'/schedule.index'

    indexStr=eventDateStr+' '+postId
    if os.path.isfile(scheduleIndexFilename):
        if indexStr not in open(scheduleIndexFilename).read():
            try:
                with open(scheduleIndexFilename, 'r+') as scheduleFile:
                    content = scheduleFile.read()
                    scheduleFile.seek(0, 0)
                    scheduleFile.write(indexStr+'\n'+content)
                    if debug:
                        print('DEBUG: scheduled post added to index')
            except Exception as e:
                print('WARN: Failed to write entry to scheduled posts index '+ \
                      scheduleIndexFilename+' '+str(e))
    else:
        scheduleFile=open(scheduleIndexFilename,'w')
        if scheduleFile:
            scheduleFile.write(indexStr+'\n')
            scheduleFile.close()        

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
            if ' ' not in line:
                continue
            dateStr=line.split(' ')[0]
            if 'T' not in dateStr:
                continue
            postId=line.split(' ',1)[1].replace('\n','')
            postFilename=scheduleDir+postId+'.json'
            if deleteSchedulePost:
                # delete extraneous scheduled posts
                if os.path.isfile(postFilename):
                    os.remove(postFilename)
                continue
            # create the new index file
            indexLines.append(line)
            # convert string date to int
            postTime= \
                datetime.datetime.strptime(dateStr,"%Y-%m-%dT%H:%M:%S%z")
            postDaysSinceEpoch= \
                (postTime - datetime.datetime(1970,1,1)).days
            if daysSinceEpoch < postDaysSinceEpoch:
                continue
            if currTime.time().hour < postTime.time().hour:
                continue
            if currTime.time().minute < postTime.time().minute:
                continue
            if not os.path.isfile(postFilename):
                indexLines.remove(line)
                continue
            # load post
            postJsonObject=loadJson(postFilename)
            if not postJsonObject:
                indexLines.remove(line)
                continue

            print('Sending scheduled post '+postId)

            if not httpd._postToOutbox(postJsonObject,__version__,nickname):
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
                if not os.path.isdir(scheduleIndexFilename):
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
