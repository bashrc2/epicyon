__filename__ = "followingCalendar.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Calendar"

import os


def _dirAcct(base_dir: str, nickname: str, domain: str) -> str:
    return base_dir + '/accounts/' + nickname + '@' + domain


def _portDomainRemove(domain: str) -> str:
    """If the domain has a port appended then remove it
    eg. mydomain.com:80 becomes mydomain.com
    same as removeDomainPort in utils.py
    """
    if ':' in domain:
        if domain.startswith('did:'):
            return domain
        domain = domain.split(':')[0]
    return domain


def receivingCalendarEvents(base_dir: str, nickname: str, domain: str,
                            followingNickname: str,
                            followingDomain: str) -> bool:
    """Returns true if receiving calendar events from the given
    account from following.txt
    """
    if followingNickname == nickname and followingDomain == domain:
        # reminder post
        return True
    calendarFilename = \
        _dirAcct(base_dir, nickname, domain) + '/followingCalendar.txt'
    handle = followingNickname + '@' + followingDomain
    if not os.path.isfile(calendarFilename):
        followingFilename = \
            _dirAcct(base_dir, nickname, domain) + '/following.txt'
        if not os.path.isfile(followingFilename):
            return False
        # create a new calendar file from the following file
        followingHandles = None
        try:
            with open(followingFilename, 'r') as followingFile:
                followingHandles = followingFile.read()
        except OSError:
            print('EX: receivingCalendarEvents ' + followingFilename)
        if followingHandles:
            try:
                with open(calendarFilename, 'w+') as fp:
                    fp.write(followingHandles)
            except OSError:
                print('EX: receivingCalendarEvents 2 ' + calendarFilename)
    return handle + '\n' in open(calendarFilename).read()


def _receiveCalendarEvents(base_dir: str, nickname: str, domain: str,
                           followingNickname: str,
                           followingDomain: str,
                           add: bool) -> None:
    """Adds or removes a handle from the following.txt list into a list
    indicating whether to receive calendar events from that account
    """
    # check that a following file exists
    domain = _portDomainRemove(domain)
    followingFilename = _dirAcct(base_dir, nickname, domain) + '/following.txt'
    if not os.path.isfile(followingFilename):
        print("WARN: following.txt doesn't exist for " +
              nickname + '@' + domain)
        return
    handle = followingNickname + '@' + followingDomain

    # check that you are following this handle
    if handle + '\n' not in open(followingFilename).read():
        print('WARN: ' + handle + ' is not in ' + followingFilename)
        return

    calendarFilename = \
        _dirAcct(base_dir, nickname, domain) + '/followingCalendar.txt'

    # get the contents of the calendar file, which is
    # a set of handles
    followingHandles = ''
    if os.path.isfile(calendarFilename):
        print('Calendar file exists')
        try:
            with open(calendarFilename, 'r') as calendarFile:
                followingHandles = calendarFile.read()
        except OSError:
            print('EX: _receiveCalendarEvents ' + calendarFilename)
    else:
        # create a new calendar file from the following file
        print('Creating calendar file ' + calendarFilename)
        followingHandles = ''
        try:
            with open(followingFilename, 'r') as followingFile:
                followingHandles = followingFile.read()
        except OSError:
            print('EX: _receiveCalendarEvents 2 ' + calendarFilename)
        if add:
            try:
                with open(calendarFilename, 'w+') as fp:
                    fp.write(followingHandles + handle + '\n')
            except OSError:
                print('EX: unable to write ' + calendarFilename)

    # already in the calendar file?
    if handle + '\n' in followingHandles:
        print(handle + ' exists in followingCalendar.txt')
        if add:
            # already added
            return
        # remove from calendar file
        followingHandles = followingHandles.replace(handle + '\n', '')
        try:
            with open(calendarFilename, 'w+') as fp:
                fp.write(followingHandles)
        except OSError:
            print('EX: _receiveCalendarEvents 3 ' + calendarFilename)
    else:
        print(handle + ' not in followingCalendar.txt')
        # not already in the calendar file
        if add:
            # append to the list of handles
            followingHandles += handle + '\n'
            try:
                with open(calendarFilename, 'w+') as fp:
                    fp.write(followingHandles)
            except OSError:
                print('EX: _receiveCalendarEvents 4 ' + calendarFilename)


def addPersonToCalendar(base_dir: str, nickname: str, domain: str,
                        followingNickname: str,
                        followingDomain: str) -> None:
    _receiveCalendarEvents(base_dir, nickname, domain,
                           followingNickname, followingDomain, True)


def removePersonFromCalendar(base_dir: str, nickname: str, domain: str,
                             followingNickname: str,
                             followingDomain: str) -> None:
    _receiveCalendarEvents(base_dir, nickname, domain,
                           followingNickname, followingDomain, False)
