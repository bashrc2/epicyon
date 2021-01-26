__filename__ = "followingCalendar.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os


def receivingCalendarEvents(baseDir: str, nickname: str, domain: str,
                            followingNickname: str,
                            followingDomain: str) -> bool:
    """Returns true if receiving calendar events from the given
    account from following.txt
    """
    if followingNickname == nickname and followingDomain == domain:
        # reminder post
        return True
    calendarFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/followingCalendar.txt'
    handle = followingNickname + '@' + followingDomain
    if not os.path.isfile(calendarFilename):
        followingFilename = baseDir + '/accounts/' + \
            nickname + '@' + domain + '/following.txt'
        if not os.path.isfile(followingFilename):
            return False
        # create a new calendar file from the following file
        with open(followingFilename, 'r') as followingFile:
            followingHandles = followingFile.read()
            with open(calendarFilename, 'w+') as fp:
                fp.write(followingHandles)
    return handle + '\n' in open(calendarFilename).read()


def _receiveCalendarEvents(baseDir: str, nickname: str, domain: str,
                           followingNickname: str,
                           followingDomain: str,
                           add: bool) -> None:
    """Adds or removes a handle from the following.txt list into a list
    indicating whether to receive calendar events from that account
    """
    # check that a following file exists
    if ':' in domain:
        domain = domain.split(':')[0]
    followingFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/following.txt'
    if not os.path.isfile(followingFilename):
        print("WARN: following.txt doesn't exist for " +
              nickname + '@' + domain)
        return
    handle = followingNickname + '@' + followingDomain

    # check that you are following this handle
    if handle + '\n' not in open(followingFilename).read():
        print('WARN: ' + handle + ' is not in ' + followingFilename)
        return

    calendarFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/followingCalendar.txt'

    # get the contents of the calendar file, which is
    # a set of handles
    followingHandles = ''
    if os.path.isfile(calendarFilename):
        print('Calendar file exists')
        with open(calendarFilename, 'r') as calendarFile:
            followingHandles = calendarFile.read()
    else:
        # create a new calendar file from the following file
        print('Creating calendar file ' + calendarFilename)
        followingHandles = ''
        with open(followingFilename, 'r') as followingFile:
            followingHandles = followingFile.read()
        if add:
            with open(calendarFilename, 'w+') as fp:
                fp.write(followingHandles + handle + '\n')

    # already in the calendar file?
    if handle + '\n' in followingHandles:
        print(handle + ' exists in followingCalendar.txt')
        if add:
            # already added
            return
        # remove from calendar file
        followingHandles = followingHandles.replace(handle + '\n', '')
        with open(calendarFilename, 'w+') as fp:
            fp.write(followingHandles)
    else:
        print(handle + ' not in followingCalendar.txt')
        # not already in the calendar file
        if add:
            # append to the list of handles
            followingHandles += handle + '\n'
            with open(calendarFilename, 'w+') as fp:
                fp.write(followingHandles)


def addPersonToCalendar(baseDir: str, nickname: str, domain: str,
                        followingNickname: str,
                        followingDomain: str) -> None:
    _receiveCalendarEvents(baseDir, nickname, domain,
                           followingNickname, followingDomain, True)


def removePersonFromCalendar(baseDir: str, nickname: str, domain: str,
                             followingNickname: str,
                             followingDomain: str) -> None:
    _receiveCalendarEvents(baseDir, nickname, domain,
                           followingNickname, followingDomain, False)
