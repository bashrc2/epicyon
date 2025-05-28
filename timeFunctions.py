__filename__ = "timeFunctions.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import time
import datetime
from dateutil.tz import tz
from utils import acct_dir
from utils import data_dir
from utils import has_object_dict


def convert_published_to_local_timezone(published, timezone: str) -> str:
    """Converts a post published time into local time
    """
    to_zone = None
    from_zone = tz.gettz('UTC')
    if timezone:
        try:
            to_zone = tz.gettz(timezone)
        except BaseException:
            pass
    if not timezone or not to_zone:
        return published

    utc = published.replace(tzinfo=from_zone)
    local_time = utc.astimezone(to_zone)
    return local_time


def _utc_mktime(utc_tuple):
    """Returns number of seconds elapsed since epoch
    Note that no timezone are taken into consideration.
    utc tuple must be: (year, month, day, hour, minute, second)
    """

    if len(utc_tuple) == 6:
        utc_tuple += (0, 0, 0)
    return time.mktime(utc_tuple) - time.mktime((1970, 1, 1, 0, 0, 0, 0, 0, 0))


def _datetime_to_timestamp(dtime):
    """Converts a datetime object to UTC timestamp"""
    return int(_utc_mktime(dtime.timetuple()))


def date_utcnow():
    """returns the time now
    """
    return datetime.datetime.now(datetime.timezone.utc)


def date_from_numbers(year: int, month: int, day: int,
                      hour: int, mins: int):
    """returns an offset-aware datetime
    """
    return datetime.datetime(year, month, day, hour, mins, 0,
                             tzinfo=datetime.timezone.utc)


def date_from_string_format(date_str: str, formats: []):
    """returns an offset-aware datetime from a string date
    """
    if not formats:
        formats = ("%a, %d %b %Y %H:%M:%S %Z",
                   "%a, %d %b %Y %H:%M:%S %z",
                   "%Y-%m-%dT%H:%M:%S%z")
    dtime = None
    for date_format in formats:
        try:
            dtime = \
                datetime.datetime.strptime(date_str, date_format)
        except BaseException:
            continue
        break
    if not dtime:
        return None
    if not dtime.tzinfo:
        dtime = dtime.replace(tzinfo=datetime.timezone.utc)
    return dtime


def date_epoch():
    """returns an offset-aware version of epoch
    """
    return date_from_numbers(1970, 1, 1, 0, 0)


def date_string_to_seconds(date_str: str) -> int:
    """Converts a date string (eg "published") into seconds since epoch
    """
    expiry_time = \
        date_from_string_format(date_str, ['%Y-%m-%dT%H:%M:%S%z'])
    if not expiry_time:
        print('EX: date_string_to_seconds unable to parse date ' +
              str(date_str))
        return None
    return _datetime_to_timestamp(expiry_time)


def date_seconds_to_string(date_sec: int) -> str:
    """Converts a date in seconds since epoch to a string
    """
    this_date = \
        datetime.datetime.fromtimestamp(date_sec, datetime.timezone.utc)
    if not this_date.tzinfo:
        this_date = this_date.replace(tzinfo=datetime.timezone.utc)
    this_date_tz = this_date.astimezone(datetime.timezone.utc)
    return this_date_tz.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_account_timezone(base_dir: str, nickname: str, domain: str) -> str:
    """Returns the timezone for the given account
    """
    tz_filename = \
        acct_dir(base_dir, nickname, domain) + '/timezone.txt'
    if not os.path.isfile(tz_filename):
        return None
    timezone = None
    try:
        with open(tz_filename, 'r', encoding='utf-8') as fp_timezone:
            timezone = fp_timezone.read().strip()
    except OSError:
        print('EX: get_account_timezone unable to read ' + tz_filename)
    return timezone


def set_account_timezone(base_dir: str, nickname: str, domain: str,
                         timezone: str) -> None:
    """Sets the timezone for the given account
    """
    tz_filename = \
        acct_dir(base_dir, nickname, domain) + '/timezone.txt'
    timezone = timezone.strip()
    try:
        with open(tz_filename, 'w+', encoding='utf-8') as fp_timezone:
            fp_timezone.write(timezone)
    except OSError:
        print('EX: set_account_timezone unable to write ' +
              tz_filename)


def load_account_timezones(base_dir: str) -> {}:
    """Returns a dictionary containing the preferred timezone for each account
    """
    account_timezone = {}
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
        for acct in dirs:
            if '@' not in acct:
                continue
            if acct.startswith('inbox@') or acct.startswith('Actor@'):
                continue
            acct_directory = os.path.join(dir_str, acct)
            tz_filename = acct_directory + '/timezone.txt'
            if not os.path.isfile(tz_filename):
                continue
            timezone = None
            try:
                with open(tz_filename, 'r', encoding='utf-8') as fp_timezone:
                    timezone = fp_timezone.read().strip()
            except OSError:
                print('EX: load_account_timezones unable to read ' +
                      tz_filename)
            if timezone:
                nickname = acct.split('@')[0]
                account_timezone[nickname] = timezone
        break
    return account_timezone


def week_day_of_month_start(month_number: int, year: int) -> int:
    """Gets the day number of the first day of the month
    1=sun, 7=sat
    """
    first_day_of_month = date_from_numbers(year, month_number, 1, 0, 0)
    return int(first_day_of_month.strftime("%w")) + 1


def valid_post_date(published: str, max_age_days: int, debug: bool) -> bool:
    """Returns true if the published date is recent and is not in the future
    """
    baseline_time = date_epoch()

    days_diff = date_utcnow() - baseline_time
    now_days_since_epoch = days_diff.days

    post_time_object = \
        date_from_string_format(published, ["%Y-%m-%dT%H:%M:%S%z"])
    if not post_time_object:
        if debug:
            print('EX: valid_post_date invalid published date ' +
                  str(published))
        return False

    days_diff = post_time_object - baseline_time
    post_days_since_epoch = days_diff.days

    if post_days_since_epoch > now_days_since_epoch:
        if debug:
            print("Inbox post has a published date in the future!")
        return False

    if now_days_since_epoch - post_days_since_epoch >= max_age_days:
        if debug:
            print("Inbox post is not recent enough")
        return False
    return True


def time_days_ago(datestr: str) -> int:
    """returns the number of days ago for the given date
    """
    date1 = \
        date_from_string_format(datestr,
                                ["%Y-%m-%dT%H:%M:%S%z"])
    if not date1:
        return 0
    date_diff = date_utcnow() - date1
    return date_diff.days


def get_published_date(post_json_object: {}) -> str:
    """Returns the published date on the given post
    """
    published = None
    if post_json_object.get('published'):
        published = post_json_object['published']
    elif has_object_dict(post_json_object):
        if post_json_object['object'].get('published'):
            published = post_json_object['object']['published']
    if not published:
        return None
    if not isinstance(published, str):
        return None
    return published
