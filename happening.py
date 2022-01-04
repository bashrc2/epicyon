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

from utils import is_public_post
from utils import load_json
from utils import save_json
from utils import locate_post
from utils import has_object_dict
from utils import acct_dir


def _valid_uuid(test_uuid: str, version: int):
    """Check if uuid_to_test is a valid UUID
    """
    try:
        uuid_obj = UUID(test_uuid, version=version)
    except ValueError:
        return False

    return str(uuid_obj) == test_uuid


def _remove_event_from_timeline(event_id: str,
                                tl_events_filename: str) -> None:
    """Removes the given event Id from the timeline
    """
    if event_id + '\n' not in open(tl_events_filename).read():
        return
    with open(tl_events_filename, 'r') as fp_tl:
        events_timeline = fp_tl.read().replace(event_id + '\n', '')
        try:
            with open(tl_events_filename, 'w+') as fp2:
                fp2.write(events_timeline)
        except OSError:
            print('EX: ERROR: unable to save events timeline')


def save_event_post(base_dir: str, handle: str, post_id: str,
                    event_json: {}) -> bool:
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
    calendar_path = base_dir + '/accounts/' + handle + '/calendar'
    if not os.path.isdir(calendar_path):
        os.mkdir(calendar_path)

    # get the year, month and day from the event
    event_time = datetime.strptime(event_json['startTime'],
                                   "%Y-%m-%dT%H:%M:%S%z")
    event_year = int(event_time.strftime("%Y"))
    if event_year < 2020 or event_year >= 2100:
        return False
    event_month_number = int(event_time.strftime("%m"))
    if event_month_number < 1 or event_month_number > 12:
        return False
    event_day_of_month = int(event_time.strftime("%d"))
    if event_day_of_month < 1 or event_day_of_month > 31:
        return False

    if event_json.get('name') and event_json.get('actor') and \
       event_json.get('uuid') and event_json.get('content'):
        if not _valid_uuid(event_json['uuid'], 4):
            return False
        print('Mobilizon type event')
        # if this is a full description of an event then save it
        # as a separate json file
        events_path = base_dir + '/accounts/' + handle + '/events'
        if not os.path.isdir(events_path):
            os.mkdir(events_path)
        events_year_path = \
            base_dir + '/accounts/' + handle + '/events/' + str(event_year)
        if not os.path.isdir(events_year_path):
            os.mkdir(events_year_path)
        event_id = str(event_year) + '-' + event_time.strftime("%m") + '-' + \
            event_time.strftime("%d") + '_' + event_json['uuid']
        event_filename = events_year_path + '/' + event_id + '.json'

        save_json(event_json, event_filename)
        # save to the events timeline
        tl_events_filename = base_dir + '/accounts/' + handle + '/events.txt'

        if os.path.isfile(tl_events_filename):
            _remove_event_from_timeline(event_id, tl_events_filename)
            try:
                with open(tl_events_filename, 'r+') as tl_events_file:
                    content = tl_events_file.read()
                    if event_id + '\n' not in content:
                        tl_events_file.seek(0, 0)
                        tl_events_file.write(event_id + '\n' + content)
            except OSError as ex:
                print('EX: Failed to write entry to events file ' +
                      tl_events_filename + ' ' + str(ex))
                return False
        else:
            try:
                with open(tl_events_filename, 'w+') as tl_events_file:
                    tl_events_file.write(event_id + '\n')
            except OSError:
                print('EX: unable to write ' + tl_events_filename)

    # create a directory for the calendar year
    if not os.path.isdir(calendar_path + '/' + str(event_year)):
        os.mkdir(calendar_path + '/' + str(event_year))

    # calendar month file containing event post Ids
    calendar_filename = calendar_path + '/' + str(event_year) + \
        '/' + str(event_month_number) + '.txt'

    # Does this event post already exist within the calendar month?
    if os.path.isfile(calendar_filename):
        if post_id in open(calendar_filename).read():
            # Event post already exists
            return False

    # append the post Id to the file for the calendar month
    try:
        with open(calendar_filename, 'a+') as calendar_file:
            calendar_file.write(post_id + '\n')
    except OSError:
        print('EX: unable to append ' + calendar_filename)

    # create a file which will trigger a notification that
    # a new event has been added
    cal_notify_filename = base_dir + '/accounts/' + handle + '/.newCalendar'
    notify_str = \
        '/calendar?year=' + str(event_year) + '?month=' + \
        str(event_month_number) + '?day=' + str(event_day_of_month)
    try:
        with open(cal_notify_filename, 'w+') as cal_file:
            cal_file.write(notify_str)
    except OSError:
        print('EX: unable to write ' + cal_notify_filename)
        return False
    return True


def _is_happening_event(tag: {}) -> bool:
    """Is this tag an Event or Place ActivityStreams type?
    """
    if not tag.get('type'):
        return False
    if tag['type'] != 'Event' and tag['type'] != 'Place':
        return False
    return True


def _is_happening_post(post_json_object: {}) -> bool:
    """Is this a post with tags?
    """
    if not post_json_object:
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('tag'):
        return False
    return True


def get_todays_events(base_dir: str, nickname: str, domain: str,
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
        month_number = now.month
    else:
        month_number = currMonthNumber
    if not currDayOfMonth:
        day_number = now.day
    else:
        day_number = currDayOfMonth

    calendar_filename = \
        acct_dir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(month_number) + '.txt'
    events = {}
    if not os.path.isfile(calendar_filename):
        return events

    calendar_post_ids = []
    recreate_events_file = False
    with open(calendar_filename, 'r') as events_file:
        for post_id in events_file:
            post_id = post_id.replace('\n', '').replace('\r', '')
            post_filename = locate_post(base_dir, nickname, domain, post_id)
            if not post_filename:
                recreate_events_file = True
                continue

            post_json_object = load_json(post_filename)
            if not _is_happening_post(post_json_object):
                continue

            public_event = is_public_post(post_json_object)

            post_event = []
            day_of_month = None
            for tag in post_json_object['object']['tag']:
                if not _is_happening_event(tag):
                    continue
                # this tag is an event or a place
                if tag['type'] == 'Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    event_time = \
                        datetime.strptime(tag['startTime'],
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(event_time.strftime("%Y")) == year and \
                       int(event_time.strftime("%m")) == month_number and \
                       int(event_time.strftime("%d")) == day_number:
                        day_of_month = str(int(event_time.strftime("%d")))
                        if '#statuses#' in post_id:
                            # link to the id so that the event can be
                            # easily deleted
                            tag['post_id'] = post_id.split('#statuses#')[1]
                            tag['sender'] = post_id.split('#statuses#')[0]
                            tag['sender'] = tag['sender'].replace('#', '/')
                            tag['public'] = public_event
                        post_event.append(tag)
                else:
                    # tag is a place
                    post_event.append(tag)
            if post_event and day_of_month:
                calendar_post_ids.append(post_id)
                if not events.get(day_of_month):
                    events[day_of_month] = []
                events[day_of_month].append(post_event)

    # if some posts have been deleted then regenerate the calendar file
    if recreate_events_file:
        try:
            with open(calendar_filename, 'w+') as calendar_file:
                for post_id in calendar_post_ids:
                    calendar_file.write(post_id + '\n')
        except OSError:
            print('EX: unable to write ' + calendar_filename)

    return events


def day_events_check(base_dir: str, nickname: str, domain: str,
                     currDate) -> bool:
    """Are there calendar events for the given date?
    """
    year = currDate.year
    month_number = currDate.month
    day_number = currDate.day

    calendar_filename = \
        acct_dir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(month_number) + '.txt'
    if not os.path.isfile(calendar_filename):
        return False

    events_exist = False
    with open(calendar_filename, 'r') as events_file:
        for post_id in events_file:
            post_id = post_id.replace('\n', '').replace('\r', '')
            post_filename = locate_post(base_dir, nickname, domain, post_id)
            if not post_filename:
                continue

            post_json_object = load_json(post_filename)
            if not _is_happening_post(post_json_object):
                continue

            for tag in post_json_object['object']['tag']:
                if not _is_happening_event(tag):
                    continue
                # this tag is an event or a place
                if tag['type'] != 'Event':
                    continue
                # tag is an event
                if not tag.get('startTime'):
                    continue
                event_time = \
                    datetime.strptime(tag['startTime'],
                                      "%Y-%m-%dT%H:%M:%S%z")
                if int(event_time.strftime("%d")) != day_number:
                    continue
                if int(event_time.strftime("%m")) != month_number:
                    continue
                if int(event_time.strftime("%Y")) != year:
                    continue
                events_exist = True
                break

    return events_exist


def get_this_weeks_events(base_dir: str, nickname: str, domain: str) -> {}:
    """Retrieves calendar events for this week
    Returns a dictionary indexed by day number of lists containing
    Event and Place activities
    Note: currently not used but could be with a weekly calendar screen
    """
    now = datetime.now()
    end_of_week = now + timedelta(7)
    year = now.year
    month_number = now.month

    calendar_filename = \
        acct_dir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(month_number) + '.txt'

    events = {}
    if not os.path.isfile(calendar_filename):
        return events

    calendar_post_ids = []
    recreate_events_file = False
    with open(calendar_filename, 'r') as events_file:
        for post_id in events_file:
            post_id = post_id.replace('\n', '').replace('\r', '')
            post_filename = locate_post(base_dir, nickname, domain, post_id)
            if not post_filename:
                recreate_events_file = True
                continue

            post_json_object = load_json(post_filename)
            if not _is_happening_post(post_json_object):
                continue

            post_event = []
            week_day_index = None
            for tag in post_json_object['object']['tag']:
                if not _is_happening_event(tag):
                    continue
                # this tag is an event or a place
                if tag['type'] == 'Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    event_time = \
                        datetime.strptime(tag['startTime'],
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if event_time >= now and event_time <= end_of_week:
                        week_day_index = (event_time - now).days()
                        post_event.append(tag)
                else:
                    # tag is a place
                    post_event.append(tag)
            if post_event and week_day_index:
                calendar_post_ids.append(post_id)
                if not events.get(week_day_index):
                    events[week_day_index] = []
                events[week_day_index].append(post_event)

    # if some posts have been deleted then regenerate the calendar file
    if recreate_events_file:
        try:
            with open(calendar_filename, 'w+') as calendar_file:
                for post_id in calendar_post_ids:
                    calendar_file.write(post_id + '\n')
        except OSError:
            print('EX: unable to write ' + calendar_filename)

    return events


def get_calendar_events(base_dir: str, nickname: str, domain: str,
                        year: int, month_number: int) -> {}:
    """Retrieves calendar events
    Returns a dictionary indexed by day number of lists containing
    Event and Place activities
    """
    calendar_filename = \
        acct_dir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(month_number) + '.txt'

    events = {}
    if not os.path.isfile(calendar_filename):
        return events

    calendar_post_ids = []
    recreate_events_file = False
    with open(calendar_filename, 'r') as events_file:
        for post_id in events_file:
            post_id = post_id.replace('\n', '').replace('\r', '')
            post_filename = locate_post(base_dir, nickname, domain, post_id)
            if not post_filename:
                recreate_events_file = True
                continue

            post_json_object = load_json(post_filename)
            if not _is_happening_post(post_json_object):
                continue

            post_event = []
            day_of_month = None
            for tag in post_json_object['object']['tag']:
                if not _is_happening_event(tag):
                    continue
                # this tag is an event or a place
                if tag['type'] == 'Event':
                    # tag is an event
                    if not tag.get('startTime'):
                        continue
                    event_time = \
                        datetime.strptime(tag['startTime'],
                                          "%Y-%m-%dT%H:%M:%S%z")
                    if int(event_time.strftime("%Y")) == year and \
                       int(event_time.strftime("%m")) == month_number:
                        day_of_month = str(int(event_time.strftime("%d")))
                        post_event.append(tag)
                else:
                    # tag is a place
                    post_event.append(tag)

            if post_event and day_of_month:
                calendar_post_ids.append(post_id)
                if not events.get(day_of_month):
                    events[day_of_month] = []
                events[day_of_month].append(post_event)

    # if some posts have been deleted then regenerate the calendar file
    if recreate_events_file:
        try:
            with open(calendar_filename, 'w+') as calendar_file:
                for post_id in calendar_post_ids:
                    calendar_file.write(post_id + '\n')
        except OSError:
            print('EX: unable to write ' + calendar_filename)

    return events


def remove_calendar_event(base_dir: str, nickname: str, domain: str,
                          year: int, month_number: int,
                          message_id: str) -> None:
    """Removes a calendar event
    """
    calendar_filename = \
        acct_dir(base_dir, nickname, domain) + \
        '/calendar/' + str(year) + '/' + str(month_number) + '.txt'
    if not os.path.isfile(calendar_filename):
        return
    if '/' in message_id:
        message_id = message_id.replace('/', '#')
    if message_id not in open(calendar_filename).read():
        return
    lines = None
    with open(calendar_filename, 'r') as fp_cal:
        lines = fp_cal.readlines()
    if not lines:
        return
    try:
        with open(calendar_filename, 'w+') as fp_cal:
            for line in lines:
                if message_id not in line:
                    fp_cal.write(line)
    except OSError:
        print('EX: unable to write ' + calendar_filename)
