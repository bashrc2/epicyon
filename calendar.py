__filename__ = "calendar.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
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
    calendarFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/followingCalendar.txt'
    handle = followingNickname + '@' + followingDomain
    if not os.path.isfile(calendarFilename):
        return False
    return handle + '\n' in open(calendarFilename).read()


def receiveCalendarEvents(baseDir: str, nickname: str, domain: str,
                          followingNickname: str,
                          followingDomain: str,
                          add: bool) -> None:
    """Adds or removes a handle from the following.txt list into a list
    indicating whether to receive calendar events from that account
    """
    # check that a following file exists
    followingFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/following.txt'
    if not os.path.isfile(followingFilename):
        return
    handle = followingNickname + '@' + followingDomain

    # check that you are following this handle
    if handle + '\n' not in open(followingFilename).read():
        return

    calendarFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/followingCalendar.txt'

    # get the contents of the calendar file, which is
    # a set of handles
    followingHandles = ''
    if os.path.isfile(calendarFilename):
        with open(calendarFilename, 'r') as calendarFile:
            followingHandles = calendarFile.read()
    else:
        # create a new calendar file from the following file
        with open(followingFilename, 'r') as followingFile:
            followingHandles = followingFile.read()
            with open(calendarFilename, 'w') as fp:
                fp.write(followingHandles)

    # already in the calendar file?
    if handle + '\n' in followingHandles:
        if add:
            # already added
            return
        # remove from calendar file
        followingHandles = followingHandles.replace(handle + '\n', '')
        with open(calendarFilename, 'w') as fp:
            fp.write(followingHandles)
    else:
        # not already in the calendar file
        if add:
            # append to the list of handles
            followingHandles += handle + '\n'
            with open(calendarFilename, 'w') as fp:
                fp.write(followingHandles)


def addPersonToCalendar(baseDir: str, nickname: str, domain: str,
                        followingNickname: str,
                        followingDomain: str) -> None:
    receiveCalendarEvents(baseDir, nickname, domain,
                          followingNickname, followingDomain, True)


def removePersonFromCalendar(baseDir: str, nickname: str, domain: str,
                             followingNickname: str,
                             followingDomain: str) -> None:
    receiveCalendarEvents(baseDir, nickname, domain,
                          followingNickname, followingDomain, False)
