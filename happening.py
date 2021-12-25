__filename__ = "happening.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
from uuid import UUID
from datetime import datetime
from datetime import timedelta

from utils import isPublicPost
from utils import loadJson
from utils import saveJson
from utils import locatePost
from utils import hasObjectDict
from utils import acctDir


def _validUuid(testUuid: str, version: int):
    """Check if uuid_to_test is a valid UUID
    """
    try:
        uuid_obj = UUID(testUuid, version=version)
    except ValueError:
        return False

    return str(uuid_obj) == testUuid


def _removeEventFromTimeline(eventId: str, tlEventsFilename: str) -> None:
    """Removes the given event Id from the timeline
    """
    if eventId + '\n' not in open(tlEventsFilename).read():
        return
    with open(tlEventsFilename, 'r') as fp:
        eventsTimeline = fp.read().replace(eventId + '\n', '')
        try:
            with open(tlEventsFilename, 'w+') as fp2:
                fp2.write(eventsTimeline)
        except OSError:
            print('EX: ERROR: unable to save events timeline')


def saveEventPost(base_dir: str, handle: str, postId: str,
                  eventJson: {}) -> bool:
    """Saves an event to the calendar and/or the events timeline
    If an event has extra fields, as per Mobilizon,
    Then it is saved as a separate entity and added to the
    events timeline
    See https://framagit.org/framasoft/mobilizon/-/blob/
    master/lib/federation/activity_stream/converter/event.ex
    """
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('WARN: Account does not exist at ' +
              base_dir + '/accounts/' + handle)
    calendarPath = base_dir + '/accounts/' + handle + '/calendar'
    if not os.path.isdir(calendarPath):
        os.mkdir(calendarPath)

    # get the year, month and day from the event
    eventTime = datetime.strptime(eventJson['startTime'],
                                  "%Y-%m-%dT%H:%M:%S%z")
    eventYear = int(eventTime.strftime("%Y"))
    if eventYear < 2020 or eventYear >= 2100:
        return False
    eventMonthNumber = int(eventTime.strftime("%m"))
    if eventMonthNumber < 1 or eventMonthNumber > 12:
        return False
    eventDayOfMonth = int(eventTime.strftime("%d"))
    if eventDayOfMonth < 1 or eventDayOfMonth > 31:
        return False

    if eventJson.get('name') and eventJson.get('actor') and \
       eventJson.get('uuid') and eventJson.get('content'):
        if not _validUuid(eventJson['uuid'], 4):
            return False
        print('Mobilizon type event')
        # if this is a full description of an event then save it
        # as a separate json file
        eventsPath = base_dir + '/accounts/' + handle + '/events'
        if not os.path.isdir(eventsPath):
            os.mkdir(eventsPath)
        eventsYearPath = \
            base_dir + '/accounts/' + handle + '/events/' + str(eventYear)
        if not os.path.isdir(eventsYearPath):
            os.mkdir(eventsYearPath)
        eventId = str(eventYear) + '-' + eventTime.strftime("%m") + '-' + \
            eventTime.strftime("%d") + '_' + eventJson['uuid']
        eventFilename = eventsYearPath + '/' + eventId + '.json'

        saveJson(eventJson, eventFilename)
        # save to the events timeline
        tlEventsFilename = base_dir + '/accounts/' + handle + '/events.txt'

        if os.path.isfile(tlEventsFilename):
            _removeEventFromTimeline(eventId, tlEventsFilename)
            try:
                with open(tlEventsFilename, 'r+') as tlEventsFile:
                    content = tlEventsFile.read()
                    if eventId + '\n' not in content:
                        tlEventsFile.seek(0, 0)
                        tlEventsFile.write(eventId + '\n' + content)
            except OSError as ex:
                print('EX: Failed to write entry to events file ' +
                      tlEventsFilename + ' ' + str(ex))
                return False
        else:
            try:
                with open(tlEventsFilename, 'w+') as tlEventsFile:
                    tlEventsFile.write(eventId + '\n')
            except OSError:
                print('EX: unable to write ' + tlEventsFilename)

    # create a directory for the calendar year
    if not os.path.isdir(calendarPath + '/' + str(eventYear)):
        os.mkdir(calendarPath + '/' + str(eventYear))

    # calendar month file containing event post Ids
    calendarFilename = calendarPath + '/' + str(eventYear) + \
        '/' + str(eventMonthNumber) + '.txt'

    # Does this event post already exist within the calendar month?
    if os.path.isfile(calendarFilename):
        if postId in open(calendarFilename).read():
            # Event post already exists
            return False

    # append the post Id to the file for the calendar month
    try:
        with open(calendarFilename, 'a+') as calendarFile:
            calendarFile.write(postId + '\n')
    except OSError:
        print('EX: unable to append ' + calendarFilename)

    # create a file which will trigger a notification that
    # a new event has been added
    calNotifyFilename = base_dir + '/accounts/' + handle + '/.newCalendar'
    notifyStr = \
        '/calendar?year=' + str(eventYear) + '?month=' + \
        str(eventMonthNumber) + '?day=' + str(eventDayOfMonth)
    try:
        with open(calNotifyFilename, 'w+') as calendarNotificationFile:
            calendarNotificationFile.write(notifyStr)
    except OSError:
        print('EX: unable to write ' + calNotifyFilename)
        return False
    return True


def _isHappeningEvent(tag: {}) -> bool:
    """Is this tag an Event or Place ActivityStreams type?
    """
    if not tag.get('type'):
        return False
    if tag['type'] != 'Event' and tag['type'] != 'Place':
        return False
    return True


def _isHappeningPost(postJsonObject: {}) -> bool:
    """Is this a post with tags?
    """
    if not postJsonObject:
        return False
    if not hasObjectDict(postJsonObject):
        return False
    if not postJsonObject['object'].get('tag'):
        return False
    return True


def getTodaysEvents(base_dir: str, nickname: str, domain: str,
                    currYear: int, currMonthNumber: int,
                    currDayOfMonth: int) -> {}:
    """Retrieves calendar events for today
    Returns a dictionary of lists containing Event and Place activities
    """
    now = datetime.now()
    if not currYear:
        year = now.year
    else:
        year = currYear
    if not currMonthNumber:
        monthNumber = now.month
    else:
        monthNumber = currMonthNumber
    if not currDayOfMonth:
        dayNumber = now.day
    else:
        dayNumber = currDayOfMonth

    calendarFilename = \
        acctDir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(monthNumber) + '.txt'
    events = {}
    if not os.path.isfile(calendarFilename):
        return events

    calendarPostIds = []
    recreateEventsFile = False
    with open(calendarFilename, 'r') as eventsFile:
        for postId in eventsFile:
            postId = postId.replace('\n', '').replace('\r', '')
            postFilename = locatePost(base_dir, nickname, domain, postId)
            if not postFilename:
                recreateEventsFile = True
                continue

            postJsonObject = loadJson(postFilename)
            if not _isHappeningPost(postJsonObject):
                continue

            publicEvent = isPublicPost(postJsonObject)

            postEvent = []
            dayOfMonth = None
            for tag in postJsonObject['object']['tag']:
                if not _isHappeningEvent(tag):
                    continue
                # this tag is an event or a place
                if tag['type'] == 'Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    eventTime = \
                        datetime.strptime(tag['startTime'],
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(eventTime.strftime("%Y")) == year and \
                       int(eventTime.strftime("%m")) == monthNumber and \
                       int(eventTime.strftime("%d")) == dayNumber:
                        dayOfMonth = str(int(eventTime.strftime("%d")))
                        if '#statuses#' in postId:
                            # link to the id so that the event can be
                            # easily deleted
                            tag['postId'] = postId.split('#statuses#')[1]
                            tag['sender'] = postId.split('#statuses#')[0]
                            tag['sender'] = tag['sender'].replace('#', '/')
                            tag['public'] = publicEvent
                        postEvent.append(tag)
                else:
                    # tag is a place
                    postEvent.append(tag)
            if postEvent and dayOfMonth:
                calendarPostIds.append(postId)
                if not events.get(dayOfMonth):
                    events[dayOfMonth] = []
                events[dayOfMonth].append(postEvent)

    # if some posts have been deleted then regenerate the calendar file
    if recreateEventsFile:
        try:
            with open(calendarFilename, 'w+') as calendarFile:
                for postId in calendarPostIds:
                    calendarFile.write(postId + '\n')
        except OSError:
            print('EX: unable to write ' + calendarFilename)

    return events


def dayEventsCheck(base_dir: str, nickname: str, domain: str,
                   currDate) -> bool:
    """Are there calendar events for the given date?
    """
    year = currDate.year
    monthNumber = currDate.month
    dayNumber = currDate.day

    calendarFilename = \
        acctDir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(monthNumber) + '.txt'
    if not os.path.isfile(calendarFilename):
        return False

    eventsExist = False
    with open(calendarFilename, 'r') as eventsFile:
        for postId in eventsFile:
            postId = postId.replace('\n', '').replace('\r', '')
            postFilename = locatePost(base_dir, nickname, domain, postId)
            if not postFilename:
                continue

            postJsonObject = loadJson(postFilename)
            if not _isHappeningPost(postJsonObject):
                continue

            for tag in postJsonObject['object']['tag']:
                if not _isHappeningEvent(tag):
                    continue
                # this tag is an event or a place
                if tag['type'] != 'Event':
                    continue
                # tag is an event
                if not tag.get('startTime'):
                    continue
                eventTime = \
                    datetime.strptime(tag['startTime'],
                                      "%Y-%m-%dT%H:%M:%S%z")
                if int(eventTime.strftime("%d")) != dayNumber:
                    continue
                if int(eventTime.strftime("%m")) != monthNumber:
                    continue
                if int(eventTime.strftime("%Y")) != year:
                    continue
                eventsExist = True
                break

    return eventsExist


def getThisWeeksEvents(base_dir: str, nickname: str, domain: str) -> {}:
    """Retrieves calendar events for this week
    Returns a dictionary indexed by day number of lists containing
    Event and Place activities
    Note: currently not used but could be with a weekly calendar screen
    """
    now = datetime.now()
    endOfWeek = now + timedelta(7)
    year = now.year
    monthNumber = now.month

    calendarFilename = \
        acctDir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(monthNumber) + '.txt'

    events = {}
    if not os.path.isfile(calendarFilename):
        return events

    calendarPostIds = []
    recreateEventsFile = False
    with open(calendarFilename, 'r') as eventsFile:
        for postId in eventsFile:
            postId = postId.replace('\n', '').replace('\r', '')
            postFilename = locatePost(base_dir, nickname, domain, postId)
            if not postFilename:
                recreateEventsFile = True
                continue

            postJsonObject = loadJson(postFilename)
            if not _isHappeningPost(postJsonObject):
                continue

            postEvent = []
            weekDayIndex = None
            for tag in postJsonObject['object']['tag']:
                if not _isHappeningEvent(tag):
                    continue
                # this tag is an event or a place
                if tag['type'] == 'Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    eventTime = \
                        datetime.strptime(tag['startTime'],
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if eventTime >= now and eventTime <= endOfWeek:
                        weekDayIndex = (eventTime - now).days()
                        postEvent.append(tag)
                else:
                    # tag is a place
                    postEvent.append(tag)
            if postEvent and weekDayIndex:
                calendarPostIds.append(postId)
                if not events.get(weekDayIndex):
                    events[weekDayIndex] = []
                events[weekDayIndex].append(postEvent)

    # if some posts have been deleted then regenerate the calendar file
    if recreateEventsFile:
        try:
            with open(calendarFilename, 'w+') as calendarFile:
                for postId in calendarPostIds:
                    calendarFile.write(postId + '\n')
        except OSError:
            print('EX: unable to write ' + calendarFilename)

    return events


def getCalendarEvents(base_dir: str, nickname: str, domain: str,
                      year: int, monthNumber: int) -> {}:
    """Retrieves calendar events
    Returns a dictionary indexed by day number of lists containing
    Event and Place activities
    """
    calendarFilename = \
        acctDir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(monthNumber) + '.txt'

    events = {}
    if not os.path.isfile(calendarFilename):
        return events

    calendarPostIds = []
    recreateEventsFile = False
    with open(calendarFilename, 'r') as eventsFile:
        for postId in eventsFile:
            postId = postId.replace('\n', '').replace('\r', '')
            postFilename = locatePost(base_dir, nickname, domain, postId)
            if not postFilename:
                recreateEventsFile = True
                continue

            postJsonObject = loadJson(postFilename)
            if not _isHappeningPost(postJsonObject):
                continue

            postEvent = []
            dayOfMonth = None
            for tag in postJsonObject['object']['tag']:
                if not _isHappeningEvent(tag):
                    continue
                # this tag is an event or a place
                if tag['type'] == 'Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    eventTime = \
                        datetime.strptime(tag['startTime'],
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(eventTime.strftime("%Y")) == year and \
                       int(eventTime.strftime("%m")) == monthNumber:
                        dayOfMonth = str(int(eventTime.strftime("%d")))
                        postEvent.append(tag)
                else:
                    # tag is a place
                    postEvent.append(tag)

            if postEvent and dayOfMonth:
                calendarPostIds.append(postId)
                if not events.get(dayOfMonth):
                    events[dayOfMonth] = []
                events[dayOfMonth].append(postEvent)

    # if some posts have been deleted then regenerate the calendar file
    if recreateEventsFile:
        try:
            with open(calendarFilename, 'w+') as calendarFile:
                for postId in calendarPostIds:
                    calendarFile.write(postId + '\n')
        except OSError:
            print('EX: unable to write ' + calendarFilename)

    return events


def removeCalendarEvent(base_dir: str, nickname: str, domain: str,
                        year: int, monthNumber: int, messageId: str) -> None:
    """Removes a calendar event
    """
    calendarFilename = \
        acctDir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(monthNumber) + '.txt'
    if not os.path.isfile(calendarFilename):
        return
    if '/' in messageId:
        messageId = messageId.replace('/', '#')
    if messageId not in open(calendarFilename).read():
        return
    lines = None
    with open(calendarFilename, 'r') as f:
        lines = f.readlines()
    if not lines:
        return
    try:
        with open(calendarFilename, 'w+') as f:
            for line in lines:
                if messageId not in line:
                    f.write(line)
    except OSError:
        print('EX: unable to write ' + calendarFilename)
