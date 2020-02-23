__filename__ = "happening.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import time
import os
from datetime import datetime

from utils import loadJson
from utils import locatePost
from utils import daysInMonth
from utils import mergeDicts

def getTodaysEvents(baseDir: str,nickname: str,domain: str, \
                    currYear=None,currMonthNumber=None,currDayOfMonth=None) -> {}:
    """Retrieves calendar events for today
    Returns a dictionary of lists containing Event and Place activities
    """
    now=datetime.now()
    if not currYear:
        year=now.year
    else:
        year=currYear
    if not currMonthNumber:
        monthNumber=now.month
    else:
        monthNumber=currMonthNumber
    if not currDayOfMonth:
        dayNumber=now.day
    else:
        dayNumber=currDayOfMonth

    calendarFilename= \
        baseDir+'/accounts/'+nickname+'@'+domain+ \
        '/calendar/'+str(year)+'/'+str(monthNumber)+'.txt'
    events={}
    if not os.path.isfile(calendarFilename):
        return events

    calendarPostIds=[]
    recreateEventsFile=False
    with open(calendarFilename,'r') as eventsFile: 
        for postId in eventsFile:
            postId=postId.replace('\n','')
            postFilename=locatePost(baseDir,nickname,domain,postId)
            if not postFilename:
                recreateEventsFile=True
                continue

            postJsonObject=loadJson(postFilename)
            if not postJsonObject:
                continue
            if not postJsonObject.get('object'):
                continue
            if not isinstance(postJsonObject['object'], dict):
                continue
            if not postJsonObject['object'].get('tag'):
                continue

            postEvent=[]
            dayOfMonth=None
            for tag in postJsonObject['object']['tag']:
                if not tag.get('type'):
                    continue
                if tag['type']!='Event' and tag['type']!='Place':
                    continue
                if tag['type']=='Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    eventTime= \
                        datetime.strptime(tag['startTime'], \
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(eventTime.strftime("%Y"))==year and \
                       int(eventTime.strftime("%m"))==monthNumber and \
                       int(eventTime.strftime("%d"))==dayNumber:
                        dayOfMonth=str(int(eventTime.strftime("%d")))
                        # link to the id so that the event can be easily deleted
                        tag['postId']=postId
                        postEvent.append(tag)
                else:
                    # tag is a place
                    postEvent.append(tag)
            if postEvent and dayOfMonth:
                calendarPostIds.append(postId)
                if not events.get(dayOfMonth):
                    events[dayOfMonth]=[]
                events[dayOfMonth].append(postEvent)

    # if some posts have been deleted then regenerate the calendar file
    if recreateEventsFile:
        calendarFile=open(calendarFilename, "w")
        for postId in calendarPostIds:
            calendarFile.write(postId+'\n')
        calendarFile.close()

    return events

def todaysEventsCheck(baseDir: str,nickname: str,domain: str) -> bool:
    """Are there calendar events today?
    """
    now=datetime.now()
    year=now.year
    monthNumber=now.month
    dayNumber=now.day

    calendarFilename= \
        baseDir+'/accounts/'+nickname+'@'+domain+ \
        '/calendar/'+str(year)+'/'+str(monthNumber)+'.txt'
    if not os.path.isfile(calendarFilename):
        return False

    eventsExist=False
    with open(calendarFilename,'r') as eventsFile: 
        for postId in eventsFile:
            postId=postId.replace('\n','')
            postFilename=locatePost(baseDir,nickname,domain,postId)
            if not postFilename:
                continue

            postJsonObject=loadJson(postFilename)
            if not postJsonObject:
                continue
            if not postJsonObject.get('object'):
                continue
            if not isinstance(postJsonObject['object'], dict):
                continue
            if not postJsonObject['object'].get('tag'):
                continue

            for tag in postJsonObject['object']['tag']:
                if not tag.get('type'):
                    continue
                if tag['type']!='Event' and tag['type']!='Place':
                    continue
                if tag['type']=='Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    eventTime= \
                        datetime.strptime(tag['startTime'], \
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(eventTime.strftime("%Y"))==year and \
                       int(eventTime.strftime("%m"))==monthNumber and \
                       int(eventTime.strftime("%d"))==dayNumber:
                        eventsExist=True
                        break

    return eventsExist

def thisWeeksEventsCheck(baseDir: str,nickname: str,domain: str) -> bool:
    """Are there calendar events this week?
    """
    now=datetime.now()
    year=now.year
    monthNumber=now.month
    dayNumber=now.day

    calendarFilename= \
        baseDir+'/accounts/'+nickname+'@'+domain+ \
        '/calendar/'+str(year)+'/'+str(monthNumber)+'.txt'
    if not os.path.isfile(calendarFilename):
        return False

    eventsExist=False
    with open(calendarFilename,'r') as eventsFile: 
        for postId in eventsFile:
            postId=postId.replace('\n','')
            postFilename=locatePost(baseDir,nickname,domain,postId)
            if not postFilename:
                continue

            postJsonObject=loadJson(postFilename)
            if not postJsonObject:
                continue
            if not postJsonObject.get('object'):
                continue
            if not isinstance(postJsonObject['object'], dict):
                continue
            if not postJsonObject['object'].get('tag'):
                continue

            for tag in postJsonObject['object']['tag']:
                if not tag.get('type'):
                    continue
                if tag['type']!='Event' and tag['type']!='Place':
                    continue
                if tag['type']=='Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    eventTime= \
                        datetime.strptime(tag['startTime'], \
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(eventTime.strftime("%Y"))==year and \
                       int(eventTime.strftime("%m"))==monthNumber and \
                       (int(eventTime.strftime("%d"))>dayNumber and \
                        int(eventTime.strftime("%d"))<=dayNumber+6):
                        eventsExist=True                            
                        break

    return eventsExist

def getThisWeeksEvents(baseDir: str,nickname: str,domain: str) -> {}:
    """Retrieves calendar events for this week
    Returns a dictionary indexed by day number of lists containing Event and Place activities
    Note: currently not used but could be with a weekly calendar screen
    """
    now=datetime.now()
    year=now.year
    monthNumber=now.month
    dayNumber=now.day

    calendarFilename= \
        baseDir+'/accounts/'+nickname+'@'+domain+ \
        '/calendar/'+str(year)+'/'+str(monthNumber)+'.txt'

    events={}
    if not os.path.isfile(calendarFilename):
        return events

    calendarPostIds=[]
    recreateEventsFile=False
    with open(calendarFilename,'r') as eventsFile: 
        for postId in eventsFile:
            postId=postId.replace('\n','')
            postFilename=locatePost(baseDir,nickname,domain,postId)
            if not postFilename:
                recreateEventsFile=True
                continue

            postJsonObject=loadJson(postFilename)
            if not postJsonObject:
                continue
            if not postJsonObject.get('object'):
                continue
            if not isinstance(postJsonObject['object'], dict):
                continue
            if not postJsonObject['object'].get('tag'):
                continue

            postEvent=[]
            dayOfMonth=None
            weekDayIndex=None
            for tag in postJsonObject['object']['tag']:
                if not tag.get('type'):
                    continue
                if tag['type']!='Event' and tag['type']!='Place':
                    continue
                if tag['type']=='Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    eventTime= \
                        datetime.strptime(tag['startTime'], \
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(eventTime.strftime("%Y"))==year and \
                       int(eventTime.strftime("%m"))==monthNumber and \
                       (int(eventTime.strftime("%d"))>=dayNumber and \
                        int(eventTime.strftime("%d"))<=dayNumber+6):
                        dayOfMonth=str(int(eventTime.strftime("%d")))
                        weekDayIndex=dayOfMonth-dayNumber
                        postEvent.append(tag)
                else:
                    # tag is a place
                    postEvent.append(tag)
            if postEvent and weekDayIndex:
                calendarPostIds.append(postId)
                if not events.get(dayOfMonth):
                    events[weekDayIndex]=[]
                events[dayOfMonth].append(postEvent)

    # if some posts have been deleted then regenerate the calendar file
    if recreateEventsFile:
        calendarFile=open(calendarFilename, "w")
        for postId in calendarPostIds:
            calendarFile.write(postId+'\n')
        calendarFile.close()

    lastDayOfMonth=daysInMonth(year,monthNumber)
    if dayNumber+6 > lastDayOfMonth:
        monthNumber+=1
        if monthNumber>12:
            monthNumber=1
            year+=1
        for d in range(1,dayNumber+6-lastDayOfMonth):
            dailyEvents= \
                getTodaysEvents(baseDir,nickname,domain,year,monthNumber,d)
            if dailyEvents:
                if dailyEvents.get(d):
                    newEvents={}
                    newEvents[d+(7-(dayNumber+6-lastDayOfMonth))]=dailyEvents[d]
                    events=mergeDicts(events,newEvents)

    return events

def getCalendarEvents(baseDir: str,nickname: str,domain: str, \
                      year: int,monthNumber: int) -> {}:
    """Retrieves calendar events
    Returns a dictionary indexed by day number of lists containing Event and Place activities
    """
    calendarFilename= \
        baseDir+'/accounts/'+nickname+'@'+domain+ \
        '/calendar/'+str(year)+'/'+str(monthNumber)+'.txt'

    events={}
    if not os.path.isfile(calendarFilename):
        return events

    calendarPostIds=[]
    recreateEventsFile=False
    with open(calendarFilename,'r') as eventsFile: 
        for postId in eventsFile:
            postId=postId.replace('\n','')
            postFilename=locatePost(baseDir,nickname,domain,postId)
            if not postFilename:
                recreateEventsFile=True
                continue
            
            postJsonObject=loadJson(postFilename)
            if not postJsonObject:
                continue
            if not postJsonObject.get('object'):
                continue
            if not isinstance(postJsonObject['object'], dict):
                continue
            if not postJsonObject['object'].get('tag'):
                continue

            postEvent=[]
            dayOfMonth=None
            for tag in postJsonObject['object']['tag']:
                if not tag.get('type'):
                    continue
                if tag['type']!='Event' and tag['type']!='Place':
                    continue
                if tag['type']=='Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    eventTime= \
                        datetime.strptime(tag['startTime'], \
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(eventTime.strftime("%Y"))==year and \
                       int(eventTime.strftime("%m"))==monthNumber:
                        dayOfMonth=str(int(eventTime.strftime("%d")))
                        postEvent.append(tag)
                else:
                    # tag is a place
                    postEvent.append(tag)

            if postEvent and dayOfMonth:
                calendarPostIds.append(postId)
                if not events.get(dayOfMonth):
                    events[dayOfMonth]=[]
                events[dayOfMonth].append(postEvent)

    # if some posts have been deleted then regenerate the calendar file
    if recreateEventsFile:
        calendarFile=open(calendarFilename, "w")
        for postId in calendarPostIds:
            calendarFile.write(postId+'\n')
        calendarFile.close()
    
    return events
