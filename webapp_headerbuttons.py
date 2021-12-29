__filename__ = "webapp_headerbuttons.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"


import os
import time
from utils import acct_dir
from datetime import datetime
from datetime import timedelta
from happening import day_events_check
from webapp_utils import html_highlight_label


def header_buttons_timeline(defaultTimeline: str,
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
                            wantedButtonStr: str,
                            bookmarksButtonStr: str,
                            eventsButtonStr: str,
                            moderationButtonStr: str,
                            newPostButtonStr: str,
                            base_dir: str,
                            nickname: str, domain: str,
                            timelineStartTime,
                            newCalendarEvent: bool,
                            calendarPath: str,
                            calendarImage: str,
                            followApprovals: str,
                            icons_as_buttons: bool,
                            accessKeys: {}) -> str:
    """Returns the header at the top of the timeline, containing
    buttons for inbox, outbox, search, calendar, etc
    """
    # start of the button header with inbox, outbox, etc
    tlStr = '<div class="containerHeader"><nav>\n'
    # first button
    if defaultTimeline == 'tlmedia':
        tlStr += \
            '<a href="' + usersPath + '/tlmedia" tabindex="-1" ' + \
            'accesskey="' + accessKeys['menuMedia'] + '"' + \
            '><button class="' + \
            mediaButton + '"><span>' + translate['Media'] + \
            '</span></button></a>'
    elif defaultTimeline == 'tlblogs':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlblogs" tabindex="-1"><button class="' + \
            blogsButton + '"><span>' + translate['Blogs'] + \
            '</span></button></a>'
    elif defaultTimeline == 'tlfeatures':
        tlStr += \
            '<a href="' + usersPath + \
            '/tlfeatures" tabindex="-1"><button class="' + \
            featuresButton + '"><span>' + translate['Features'] + \
            '</span></button></a>'
    else:
        tlStr += \
            '<a href="' + usersPath + \
            '/inbox" tabindex="-1"><button class="' + \
            inboxButton + '"><span>' + \
            translate['Inbox'] + '</span></button></a>'

    # if this is a news instance and we are viewing the news timeline
    featuresHeader = False
    if defaultTimeline == 'tlfeatures' and boxName == 'tlfeatures':
        featuresHeader = True

    if not featuresHeader:
        tlStr += \
            '<a href="' + usersPath + \
            '/dm" tabindex="-1"><button class="' + dmButton + \
            '"><span>' + html_highlight_label(translate['DM'], newDM) + \
            '</span></button></a>'

        repliesIndexFilename = \
            acct_dir(base_dir, nickname, domain) + '/tlreplies.index'
        if os.path.isfile(repliesIndexFilename):
            tlStr += \
                '<a href="' + usersPath + '/tlreplies" tabindex="-1">' + \
                '<button class="' + repliesButton + '"><span>' + \
                html_highlight_label(translate['Replies'], newReply) + \
                '</span></button></a>'

    # typically the media button
    if defaultTimeline != 'tlmedia':
        if not minimal and not featuresHeader:
            tlStr += \
                '<a href="' + usersPath + '/tlmedia" tabindex="-1" ' + \
                'accesskey="' + accessKeys['menuMedia'] + '">' + \
                '<button class="' + \
                mediaButton + '"><span>' + translate['Media'] + \
                '</span></button></a>'
    else:
        if not minimal:
            tlStr += \
                '<a href="' + usersPath + \
                '/inbox" tabindex="-1"><button class="' + \
                inboxButton + '"><span>' + translate['Inbox'] + \
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
                    '/tlblogs" tabindex="-1"><button class="' + \
                    blogsButton + '"><span>' + titleStr + \
                    '</span></button></a>'
        else:
            if not minimal:
                tlStr += \
                    '<a href="' + usersPath + \
                    '/inbox" tabindex="-1"><button class="' + \
                    inboxButton + '"><span>' + translate['Inbox'] + \
                    '</span></button></a>'

    # typically the news button
    # but may change if this is a news oriented instance
    if defaultTimeline == 'tlfeatures':
        if not featuresHeader:
            tlStr += \
                '<a href="' + usersPath + \
                '/inbox" tabindex="-1"><button class="' + \
                inboxButton + '"><span>' + translate['Inbox'] + \
                '</span></button></a>'

    # show todays events buttons on the first inbox page
    happeningStr = ''
    if boxName == 'inbox' and pageNumber == 1:
        now = datetime.now()
        tomorrow = datetime.now() + timedelta(1)
        twodays = datetime.now() + timedelta(2)
        if day_events_check(base_dir, nickname, domain, now):
            # happening today button
            if not icons_as_buttons:
                happeningStr += \
                    '<a href="' + usersPath + '/calendar?year=' + \
                    str(now.year) + '?month=' + str(now.month) + \
                    '?day=' + str(now.day) + '" tabindex="-1">' + \
                    '<button class="buttonevent">' + \
                    translate['Happening Today'] + '</button></a>'
            else:
                happeningStr += \
                    '<a href="' + usersPath + '/calendar?year=' + \
                    str(now.year) + '?month=' + str(now.month) + \
                    '?day=' + str(now.day) + '" tabindex="-1">' + \
                    '<button class="button">' + \
                    translate['Happening Today'] + '</button></a>'

        elif day_events_check(base_dir, nickname, domain, tomorrow):
            # happening tomorrow button
            if not icons_as_buttons:
                happeningStr += \
                    '<a href="' + usersPath + '/calendar?year=' + \
                    str(tomorrow.year) + '?month=' + str(tomorrow.month) + \
                    '?day=' + str(tomorrow.day) + '" tabindex="-1">' + \
                    '<button class="buttonevent">' + \
                    translate['Happening Tomorrow'] + '</button></a>'
            else:
                happeningStr += \
                    '<a href="' + usersPath + '/calendar?year=' + \
                    str(tomorrow.year) + '?month=' + str(tomorrow.month) + \
                    '?day=' + str(tomorrow.day) + '" tabindex="-1">' + \
                    '<button class="button">' + \
                    translate['Happening Tomorrow'] + '</button></a>'
        elif day_events_check(base_dir, nickname, domain, twodays):
            if not icons_as_buttons:
                happeningStr += \
                    '<a href="' + usersPath + \
                    '/calendar" tabindex="-1">' + \
                    '<button class="buttonevent">' + \
                    translate['Happening This Week'] + '</button></a>'
            else:
                happeningStr += \
                    '<a href="' + usersPath + \
                    '/calendar" tabindex="-1">' + \
                    '<button class="button">' + \
                    translate['Happening This Week'] + '</button></a>'

    if not featuresHeader:
        # button for the outbox
        tlStr += \
            '<a href="' + usersPath + '/outbox"><button class="' + \
            sentButton + '" tabindex="-1"><span>' + translate['Sent'] + \
            '</span></button></a>'

        # add other buttons
        tlStr += \
            sharesButtonStr + wantedButtonStr + bookmarksButtonStr + \
            eventsButtonStr + \
            moderationButtonStr + happeningStr + newPostButtonStr

    if not featuresHeader:
        if not icons_as_buttons:
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
                '/search" tabindex="-1"><button class="button">' + \
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
        if not icons_as_buttons:
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
                '" tabindex="-1"><button class="button">' + \
                '<span>' + translate['Calendar'] + \
                '</span></button></a>'

    if not featuresHeader:
        # the show/hide button, for a simpler header appearance
        if not icons_as_buttons:
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
                '" tabindex="-1"><button class="button">' + \
                '<span>' + translate['Show/Hide Buttons'] + \
                '</span></button></a>'

    if featuresHeader:
        tlStr += \
            '<a href="' + usersPath + '/inbox" tabindex="-1">' + \
            '<button class="button">' + \
            '<span>' + translate['User'] + '</span></button></a>'

    # the newswire button to show right column links
    if not icons_as_buttons:
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
            '" tabindex="-1"><button class="buttonMobile">' + \
            '<span>' + translate['Newswire'] + \
            '</span></button></a>'

    # the links button to show left column links
    if not icons_as_buttons:
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
            '" tabindex="-1"><button class="buttonMobile">' + \
            '<span>' + translate['Links'] + \
            '</span></button></a>'

    if featuresHeader:
        tlStr += \
            '<a href="' + usersPath + '/editprofile" tabindex="-1">' + \
            '<button class="buttonDesktop">' + \
            '<span>' + translate['Settings'] + '</span></button></a>'

    if not featuresHeader:
        tlStr += followApprovals

    if not icons_as_buttons:
        # end of headericons div
        tlStr += '</div>'

    # end of the button header with inbox, outbox, etc
    tlStr += '    </nav></div>\n'
    return tlStr
