__filename__ = "webapp_headerbuttons.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"


import os
import time
from datetime import datetime
from happening import todaysEventsCheck
from happening import thisWeeksEventsCheck
from webapp_utils import htmlHighlightLabel


def headerButtonsTimeline(defaultTimeline: str,
                          boxName: str,
                          pageNumber: int,
                          translate: {},
                          usersPath: str,
                          mediaButton: str,
                          blogsButton: str,
                          featuresButton: str,
                          newsButton: str,
                          inboxButton: str,
                          dmButton: str,
                          newDM: str,
                          repliesButton: str,
                          newReply: str,
                          minimal: bool,
                          sentButton: str,
                          sharesButtonStr: str,
                          bookmarksButtonStr: str,
                          eventsButtonStr: str,
                          moderationButtonStr: str,
                          newPostButtonStr: str,
                          baseDir: str,
                          nickname: str, domain: str,
                          timelineStartTime,
                          newCalendarEvent: bool,
                          calendarPath: str,
                          calendarImage: str,
                          followApprovals: str,
                          iconsAsButtons: bool) -> str:
    """Returns the header at the top of the timeline, containing
    buttons for inbox, outbox, search, calendar, etc
    """
    # start of the button header with inbox, outbox, etc
    tlStr = '<div class="containerHeader"><nav>\n'
    # first button
    if defaultTimeline == 'tlmedia':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlmedia"><button class="' + \
            mediaButton + '"><span>' + translate['Media'] + \
            '</span></button></a>'
    elif defaultTimeline == 'tlblogs':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlblogs"><button class="' + \
            blogsButton + '"><span>' + translate['Blogs'] + \
            '</span></button></a>'
    elif defaultTimeline == 'tlfeatures':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlfeatures"><button class="' + \
            featuresButton + '"><span>' + translate['Features'] + \
            '</span></button></a>'
    else:
        tlStr += \
            '<a href="' + usersPath + \
            '/inbox"><button class="' + \
            inboxButton + '"><span>' + \
            translate['Inbox'] + '</span></button></a>'

    # if this is a news instance and we are viewing the news timeline
    featuresHeader = False
    if defaultTimeline == 'tlfeatures' and boxName == 'tlfeatures':
        featuresHeader = True

    if not featuresHeader:
        tlStr += \
            '<a href="' + usersPath + \
            '/dm"><button class="' + dmButton + \
            '"><span>' + htmlHighlightLabel(translate['DM'], newDM) + \
            '</span></button></a>'

        repliesIndexFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/tlreplies.index'
        if os.path.isfile(repliesIndexFilename):
            tlStr += \
                '<a href="' + usersPath + '/tlreplies"><button class="' + \
                repliesButton + '"><span>' + \
                htmlHighlightLabel(translate['Replies'], newReply) + \
                '</span></button></a>'

    # typically the media button
    if defaultTimeline != 'tlmedia':
        if not minimal and not featuresHeader:
            tlStr += \
                '<a href="' + usersPath + \
                '/tlmedia"><button class="' + \
                mediaButton + '"><span>' + translate['Media'] + \
                '</span></button></a>'
    else:
        if not minimal:
            tlStr += \
                '<a href="' + usersPath + \
                '/inbox"><button class="' + \
                inboxButton+'"><span>' + translate['Inbox'] + \
                '</span></button></a>'

    if not featuresHeader:
        # typically the blogs button
        # but may change if this is a blogging oriented instance
        if defaultTimeline != 'tlblogs':
            if not minimal:
                titleStr = translate['Blogs']
                if defaultTimeline == 'tlfeatures':
                    titleStr = translate['Article']
                tlStr += \
                    '<a href="' + usersPath + \
                    '/tlblogs"><button class="' + \
                    blogsButton + '"><span>' + titleStr + \
                    '</span></button></a>'
        else:
            if not minimal:
                tlStr += \
                    '<a href="' + usersPath + \
                    '/inbox"><button class="' + \
                    inboxButton + '"><span>' + translate['Inbox'] + \
                    '</span></button></a>'

    # typically the news button
    # but may change if this is a news oriented instance
    if defaultTimeline == 'tlfeatures':
        if not featuresHeader:
            tlStr += \
                '<a href="' + usersPath + \
                '/inbox"><button class="' + \
                inboxButton + '"><span>' + translate['Inbox'] + \
                '</span></button></a>'

    # show todays events buttons on the first inbox page
    happeningStr = ''
    if boxName == 'inbox' and pageNumber == 1:
        if todaysEventsCheck(baseDir, nickname, domain):
            now = datetime.now()

            # happening today button
            if not iconsAsButtons:
                happeningStr += \
                    '<a href="' + usersPath + '/calendar?year=' + \
                    str(now.year) + '?month=' + str(now.month) + \
                    '?day=' + str(now.day) + '">' + \
                    '<button class="buttonevent">' + \
                    translate['Happening Today'] + '</button></a>'
            else:
                happeningStr += \
                    '<a href="' + usersPath + '/calendar?year=' + \
                    str(now.year) + '?month=' + str(now.month) + \
                    '?day=' + str(now.day) + '">' + \
                    '<button class="button">' + \
                    translate['Happening Today'] + '</button></a>'

            # happening this week button
            if thisWeeksEventsCheck(baseDir, nickname, domain):
                if not iconsAsButtons:
                    happeningStr += \
                        '<a href="' + usersPath + \
                        '/calendar"><button class="buttonevent">' + \
                        translate['Happening This Week'] + '</button></a>'
                else:
                    happeningStr += \
                        '<a href="' + usersPath + \
                        '/calendar"><button class="button">' + \
                        translate['Happening This Week'] + '</button></a>'
        else:
            # happening this week button
            if thisWeeksEventsCheck(baseDir, nickname, domain):
                if not iconsAsButtons:
                    happeningStr += \
                        '<a href="' + usersPath + \
                        '/calendar"><button class="buttonevent">' + \
                        translate['Happening This Week'] + '</button></a>'
                else:
                    happeningStr += \
                        '<a href="' + usersPath + \
                        '/calendar"><button class="button">' + \
                        translate['Happening This Week'] + '</button></a>'

    if not featuresHeader:
        # button for the outbox
        tlStr += \
            '<a href="' + usersPath + \
            '/outbox"><button class="' + \
            sentButton + '"><span>' + translate['Outbox'] + \
            '</span></button></a>'

        # add other buttons
        tlStr += \
            sharesButtonStr + bookmarksButtonStr + eventsButtonStr + \
            moderationButtonStr + happeningStr + newPostButtonStr

    if not featuresHeader:
        if not iconsAsButtons:
            # the search icon
            tlStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/search"><img loading="lazy" src="/' + \
                'icons/search.png" title="' + \
                translate['Search and follow'] + '" alt="| ' + \
                translate['Search and follow'] + \
                '" class="timelineicon"/></a>'
        else:
            # the search button
            tlStr += \
                '<a href="' + usersPath + \
                '/search"><button class="button">' + \
                '<span>' + translate['Search'] + \
                '</span></button></a>'

    # benchmark 5
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' + boxName + ' 5 = ' + str(timeDiff))

    # the calendar button
    if not featuresHeader:
        calendarAltText = translate['Calendar']
        if newCalendarEvent:
            # indicate that the calendar icon is highlighted
            calendarAltText = '*' + calendarAltText + '*'
        if not iconsAsButtons:
            tlStr += \
                '      <a class="imageAnchor" href="' + \
                usersPath + calendarPath + \
                '"><img loading="lazy" src="/icons/' + \
                calendarImage + '" title="' + translate['Calendar'] + \
                '" alt="| ' + calendarAltText + \
                '" class="timelineicon"/></a>\n'
        else:
            tlStr += \
                '<a href="' + usersPath + calendarPath + \
                '"><button class="button">' + \
                '<span>' + translate['Calendar'] + \
                '</span></button></a>'

    if not featuresHeader:
        # the show/hide button, for a simpler header appearance
        if not iconsAsButtons:
            tlStr += \
                '      <a class="imageAnchor" href="' + \
                usersPath + '/minimal' + \
                '"><img loading="lazy" src="/icons' + \
                '/showhide.png" title="' + translate['Show/Hide Buttons'] + \
                '" alt="| ' + translate['Show/Hide Buttons'] + \
                '" class="timelineicon"/></a>\n'
        else:
            tlStr += \
                '<a href="' + usersPath + '/minimal' + \
                '"><button class="button">' + \
                '<span>' + translate['Show/Hide Buttons'] + \
                '</span></button></a>'

    if featuresHeader:
        tlStr += \
            '<a href="' + usersPath + '/inbox">' + \
            '<button class="button">' + \
            '<span>' + translate['User'] + '</span></button></a>'

    # the newswire button to show right column links
    if not iconsAsButtons:
        tlStr += \
            '<a class="imageAnchorMobile" href="' + \
            usersPath + '/newswiremobile">' + \
            '<img loading="lazy" src="/icons' + \
            '/newswire.png" title="' + translate['News'] + \
            '" alt="| ' + translate['News'] + \
            '" class="timelineicon"/></a>'
    else:
        # NOTE: deliberately no \n at end of line
        tlStr += \
            '<a href="' + \
            usersPath + '/newswiremobile' + \
            '"><button class="buttonMobile">' + \
            '<span>' + translate['Newswire'] + \
            '</span></button></a>'

    # the links button to show left column links
    if not iconsAsButtons:
        tlStr += \
            '<a class="imageAnchorMobile" href="' + \
            usersPath + '/linksmobile">' + \
            '<img loading="lazy" src="/icons' + \
            '/links.png" title="' + translate['Edit Links'] + \
            '" alt="| ' + translate['Edit Links'] + \
            '" class="timelineicon"/></a>'
    else:
        # NOTE: deliberately no \n at end of line
        tlStr += \
            '<a href="' + \
            usersPath + '/linksmobile' + \
            '"><button class="buttonMobile">' + \
            '<span>' + translate['Links'] + \
            '</span></button></a>'

    if featuresHeader:
        tlStr += \
            '<a href="' + usersPath + '/editprofile">' + \
            '<button class="buttonDesktop">' + \
            '<span>' + translate['Settings'] + '</span></button></a>'

    if not featuresHeader:
        tlStr += followApprovals

    if not iconsAsButtons:
        # end of headericons div
        tlStr += '</div>'

    # end of the button header with inbox, outbox, etc
    tlStr += '    </nav></div>\n'
    return tlStr
