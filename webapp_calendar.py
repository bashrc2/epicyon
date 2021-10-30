__filename__ = "webapp_calendar.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Calendar"

import os
from datetime import datetime
from datetime import date
from utils import getDisplayName
from utils import getConfigParam
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import loadJson
from utils import weekDayOfMonthStart
from utils import getAltPath
from utils import removeDomainPort
from utils import acctDir
from utils import localActorUrl
from utils import replaceUsersWithAt
from happening import getTodaysEvents
from happening import getCalendarEvents
from webapp_utils import setCustomBackground
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import htmlHideFromScreenReader
from webapp_utils import htmlKeyboardNavigation


def htmlCalendarDeleteConfirm(cssCache: {}, translate: {}, baseDir: str,
                              path: str, httpPrefix: str,
                              domainFull: str, postId: str, postTime: str,
                              year: int, monthNumber: int,
                              dayNumber: int, callingDomain: str) -> str:
    """Shows a screen asking to confirm the deletion of a calendar event
    """
    nickname = getNicknameFromActor(path)
    actor = localActorUrl(httpPrefix, nickname, domainFull)
    domain, port = getDomainFromActor(actor)
    messageId = actor + '/statuses/' + postId

    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if not postFilename:
        return None

    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        return None

    setCustomBackground(baseDir, 'delete-background')

    deletePostStr = None
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    deletePostStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    deletePostStr += \
        '<center><h1>' + postTime + ' ' + str(year) + '/' + \
        str(monthNumber) + \
        '/' + str(dayNumber) + '</h1></center>'
    deletePostStr += '<center>'
    deletePostStr += '  <p class="followText">' + \
        translate['Delete this event'] + '</p>'

    postActor = getAltPath(actor, domainFull, callingDomain)
    deletePostStr += \
        '  <form method="POST" action="' + postActor + '/rmpost">\n'
    deletePostStr += '    <input type="hidden" name="year" value="' + \
        str(year) + '">\n'
    deletePostStr += '    <input type="hidden" name="month" value="' + \
        str(monthNumber) + '">\n'
    deletePostStr += '    <input type="hidden" name="day" value="' + \
        str(dayNumber) + '">\n'
    deletePostStr += \
        '    <input type="hidden" name="pageNumber" value="1">\n'
    deletePostStr += \
        '    <input type="hidden" name="messageId" value="' + \
        messageId + '">\n'
    deletePostStr += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    deletePostStr += \
        '    <a href="' + actor + '/calendar?year=' + \
        str(year) + '?month=' + \
        str(monthNumber) + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    deletePostStr += '  </form>\n'
    deletePostStr += '</center>\n'
    deletePostStr += htmlFooter()
    return deletePostStr


def _htmlCalendarDay(personCache: {}, cssCache: {}, translate: {},
                     baseDir: str, path: str,
                     year: int, monthNumber: int, dayNumber: int,
                     nickname: str, domain: str, dayEvents: [],
                     monthName: str, actor: str) -> str:
    """Show a day within the calendar
    """
    accountDir = acctDir(baseDir, nickname, domain)
    calendarFile = accountDir + '/.newCalendar'
    if os.path.isfile(calendarFile):
        try:
            os.remove(calendarFile)
        except BaseException:
            print('EX: _htmlCalendarDay unable to delete ' + calendarFile)
            pass

    cssFilename = baseDir + '/epicyon-calendar.css'
    if os.path.isfile(baseDir + '/calendar.css'):
        cssFilename = baseDir + '/calendar.css'

    calActor = actor
    if '/users/' in actor:
        calActor = '/users/' + actor.split('/users/')[1]

    instanceTitle = getConfigParam(baseDir, 'instanceTitle')
    calendarStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    calendarStr += '<main><table class="calendar">\n'
    calendarStr += '<caption class="calendar__banner--month">\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(year) + \
        '?month=' + str(monthNumber) + '">\n'
    calendarStr += \
        '  <h1>' + str(dayNumber) + ' ' + monthName + \
        '</h1></a><br><span class="year">' + str(year) + '</span>\n'
    calendarStr += '</caption>\n'
    calendarStr += '<tbody>\n'

    if dayEvents:
        for eventPost in dayEvents:
            eventTime = None
            eventDescription = None
            eventPlace = None
            postId = None
            senderName = ''
            senderActor = None
            eventIsPublic = False
            # get the time place and description
            for ev in eventPost:
                if ev['type'] == 'Event':
                    if ev.get('postId'):
                        postId = ev['postId']
                    if ev.get('startTime'):
                        eventDate = \
                            datetime.strptime(ev['startTime'],
                                              "%Y-%m-%dT%H:%M:%S%z")
                        eventTime = eventDate.strftime("%H:%M").strip()
                    if 'public' in ev:
                        if ev['public'] is True:
                            eventIsPublic = True
                    if ev.get('sender'):
                        # get display name from sending actor
                        if ev.get('sender'):
                            senderActor = ev['sender']
                            dispName = \
                                getDisplayName(baseDir, senderActor,
                                               personCache)
                            if dispName:
                                senderName = \
                                    '<a href="' + senderActor + '">' + \
                                    dispName + '</a>: '
                    if ev.get('name'):
                        eventDescription = ev['name'].strip()
                elif ev['type'] == 'Place':
                    if ev.get('name'):
                        eventPlace = ev['name']

            # prepend a link to the sender of the calendar item
            if senderName and eventDescription:
                # if the sender is also mentioned within the event
                # description then this is a reminder
                senderActor2 = replaceUsersWithAt(senderActor)
                if senderActor not in eventDescription and \
                   senderActor2 not in eventDescription:
                    eventDescription = senderName + eventDescription
                else:
                    eventDescription = \
                        translate['Reminder'] + ': ' + eventDescription

            deleteButtonStr = ''
            if postId:
                deleteButtonStr = \
                    '<td class="calendar__day__icons"><a href="' + calActor + \
                    '/eventdelete?id=' + postId + '?year=' + str(year) + \
                    '?month=' + str(monthNumber) + '?day=' + str(dayNumber) + \
                    '?time=' + eventTime + \
                    '">\n<img class="calendardayicon" loading="lazy" alt="' + \
                    translate['Delete this event'] + ' |" title="' + \
                    translate['Delete this event'] + '" src="/' + \
                    'icons/delete.png" /></a></td>\n'

            eventClass = 'calendar__day__event'
            calItemClass = 'calItem'
            if eventIsPublic:
                eventClass = 'calendar__day__event__public'
                calItemClass = 'calItemPublic'
            if eventTime and eventDescription and eventPlace:
                calendarStr += \
                    '<tr class="' + calItemClass + '">' + \
                    '<td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="' + eventClass + '">' + \
                    '<span class="place">' + \
                    eventPlace + '</span><br>' + eventDescription + \
                    '</td>' + deleteButtonStr + '</tr>\n'
            elif eventTime and eventDescription and not eventPlace:
                calendarStr += \
                    '<tr class="' + calItemClass + '">' + \
                    '<td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="' + eventClass + '">' + \
                    eventDescription + '</td>' + deleteButtonStr + '</tr>\n'
            elif not eventTime and eventDescription and not eventPlace:
                calendarStr += \
                    '<tr class="' + calItemClass + '">' + \
                    '<td class="calendar__day__time">' + \
                    '</td><td class="' + eventClass + '">' + \
                    eventDescription + '</td>' + deleteButtonStr + '</tr>\n'
            elif not eventTime and eventDescription and eventPlace:
                calendarStr += \
                    '<tr class="' + calItemClass + '">' + \
                    '<td class="calendar__day__time"></td>' + \
                    '<td class="' + eventClass + '"><span class="place">' + \
                    eventPlace + '</span><br>' + eventDescription + \
                    '</td>' + deleteButtonStr + '</tr>\n'
            elif eventTime and not eventDescription and eventPlace:
                calendarStr += \
                    '<tr class="' + calItemClass + '">' + \
                    '<td class="calendar__day__time"><b>' + eventTime + \
                    '</b></td><td class="' + eventClass + '">' + \
                    '<span class="place">' + \
                    eventPlace + '</span></td>' + \
                    deleteButtonStr + '</tr>\n'

    calendarStr += '</tbody>\n'
    calendarStr += '</table></main>\n'
    calendarStr += htmlFooter()

    return calendarStr


def htmlCalendar(personCache: {}, cssCache: {}, translate: {},
                 baseDir: str, path: str,
                 httpPrefix: str, domainFull: str,
                 textModeBanner: str, accessKeys: {}) -> str:
    """Show the calendar for a person
    """
    domain = removeDomainPort(domainFull)

    monthNumber = 0
    dayNumber = None
    year = 1970
    actor = httpPrefix + '://' + domainFull + path.replace('/calendar', '')
    if '?' in actor:
        first = True
        for p in actor.split('?'):
            if not first:
                if '=' in p:
                    if p.split('=')[0] == 'year':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            year = int(numStr)
                    elif p.split('=')[0] == 'month':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            monthNumber = int(numStr)
                    elif p.split('=')[0] == 'day':
                        numStr = p.split('=')[1]
                        if numStr.isdigit():
                            dayNumber = int(numStr)
            first = False
        actor = actor.split('?')[0]

    currDate = datetime.now()
    if year == 1970 and monthNumber == 0:
        year = currDate.year
        monthNumber = currDate.month

    nickname = getNicknameFromActor(actor)

    setCustomBackground(baseDir, 'calendar-background')

    months = ('January', 'February', 'March', 'April',
              'May', 'June', 'July', 'August', 'September',
              'October', 'November', 'December')
    monthName = translate[months[monthNumber - 1]]

    if dayNumber:
        dayEvents = None
        events = \
            getTodaysEvents(baseDir, nickname, domain,
                            year, monthNumber, dayNumber)
        if events:
            if events.get(str(dayNumber)):
                dayEvents = events[str(dayNumber)]
        return _htmlCalendarDay(personCache, cssCache,
                                translate, baseDir, path,
                                year, monthNumber, dayNumber,
                                nickname, domain, dayEvents,
                                monthName, actor)

    events = \
        getCalendarEvents(baseDir, nickname, domain, year, monthNumber)

    prevYear = year
    prevMonthNumber = monthNumber - 1
    if prevMonthNumber < 1:
        prevMonthNumber = 12
        prevYear = year - 1

    nextYear = year
    nextMonthNumber = monthNumber + 1
    if nextMonthNumber > 12:
        nextMonthNumber = 1
        nextYear = year + 1

    print('Calendar year=' + str(year) + ' month=' + str(monthNumber) +
          ' ' + str(weekDayOfMonthStart(monthNumber, year)))

    if monthNumber < 12:
        daysInMonth = \
            (date(year, monthNumber + 1, 1) - date(year, monthNumber, 1)).days
    else:
        daysInMonth = \
            (date(year + 1, 1, 1) - date(year, monthNumber, 1)).days
    # print('daysInMonth ' + str(monthNumber) + ': ' + str(daysInMonth))

    cssFilename = baseDir + '/epicyon-calendar.css'
    if os.path.isfile(baseDir + '/calendar.css'):
        cssFilename = baseDir + '/calendar.css'

    calActor = actor
    if '/users/' in actor:
        calActor = '/users/' + actor.split('/users/')[1]

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    headerStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    # the main graphical calendar as a table
    calendarStr = '<main><table class="calendar">\n'
    calendarStr += '<caption class="calendar__banner--month">\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(prevYear) + \
        '?month=' + str(prevMonthNumber) + '" ' + \
        'accesskey="' + accessKeys['Page up'] + '">'
    calendarStr += \
        '  <img loading="lazy" alt="' + translate['Previous month'] + \
        '" title="' + translate['Previous month'] + '" src="/icons' + \
        '/prev.png" class="buttonprev"/></a>\n'
    calendarStr += '  <a href="' + calActor + '/inbox" title="'
    calendarStr += translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + accessKeys['menuTimeline'] + '">'
    calendarStr += '  <h1>' + monthName + '</h1></a>\n'
    calendarStr += \
        '  <a href="' + calActor + '/calendar?year=' + str(nextYear) + \
        '?month=' + str(nextMonthNumber) + '" ' + \
        'accesskey="' + accessKeys['Page down'] + '">'
    calendarStr += \
        '  <img loading="lazy" alt="' + translate['Next month'] + \
        '" title="' + translate['Next month'] + '" src="/icons' + \
        '/prev.png" class="buttonnext"/></a>\n'
    calendarStr += '</caption>\n'
    calendarStr += '<thead>\n'
    calendarStr += '<tr>\n'
    days = ('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat')
    for d in days:
        calendarStr += '  <th scope="col" class="calendar__day__header">' + \
            translate[d] + '</th>\n'
    calendarStr += '</tr>\n'
    calendarStr += '</thead>\n'
    calendarStr += '<tbody>\n'

    # beginning of the links used for accessibility
    navLinks = {}
    timelineLinkStr = htmlHideFromScreenReader('🏠') + ' ' + \
        translate['Switch to timeline view']
    navLinks[timelineLinkStr] = calActor + '/inbox'

    dayOfMonth = 0
    dow = weekDayOfMonthStart(monthNumber, year)
    for weekOfMonth in range(1, 7):
        if dayOfMonth == daysInMonth:
            continue
        calendarStr += '  <tr>\n'
        for dayNumber in range(1, 8):
            if (weekOfMonth > 1 and dayOfMonth < daysInMonth) or \
               (weekOfMonth == 1 and dayNumber >= dow):
                dayOfMonth += 1

                isToday = False
                if year == currDate.year:
                    if currDate.month == monthNumber:
                        if dayOfMonth == currDate.day:
                            isToday = True
                if events.get(str(dayOfMonth)):
                    url = calActor + '/calendar?year=' + \
                        str(year) + '?month=' + \
                        str(monthNumber) + '?day=' + str(dayOfMonth)
                    dayDescription = monthName + ' ' + str(dayOfMonth)
                    dayLink = '<a href="' + url + '" ' + \
                        'title="' + dayDescription + '">' + \
                        str(dayOfMonth) + '</a>'
                    # accessibility menu links
                    menuOptionStr = \
                        htmlHideFromScreenReader('📅') + ' ' + \
                        dayDescription
                    navLinks[menuOptionStr] = url
                    # there are events for this day
                    if not isToday:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-event="">' + \
                            dayLink + '</td>\n'
                    else:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-today-event="">' + \
                            dayLink + '</td>\n'
                else:
                    # No events today
                    if not isToday:
                        calendarStr += \
                            '    <td class="calendar__day__cell">' + \
                            str(dayOfMonth) + '</td>\n'
                    else:
                        calendarStr += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-today="">' + str(dayOfMonth) + '</td>\n'
            else:
                calendarStr += '    <td class="calendar__day__cell"></td>\n'
        calendarStr += '  </tr>\n'

    calendarStr += '</tbody>\n'
    calendarStr += '</table></main>\n'

    # end of the links used for accessibility
    nextMonthStr = \
        htmlHideFromScreenReader('→') + ' ' + translate['Next month']
    navLinks[nextMonthStr] = calActor + '/calendar?year=' + str(nextYear) + \
        '?month=' + str(nextMonthNumber)
    prevMonthStr = \
        htmlHideFromScreenReader('←') + ' ' + translate['Previous month']
    navLinks[prevMonthStr] = calActor + '/calendar?year=' + str(prevYear) + \
        '?month=' + str(prevMonthNumber)
    navAccessKeys = {
    }
    screenReaderCal = \
        htmlKeyboardNavigation(textModeBanner, navLinks, navAccessKeys,
                               monthName)

    return headerStr + screenReaderCal + calendarStr + htmlFooter()
