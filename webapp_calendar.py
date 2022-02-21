__filename__ = "webapp_calendar.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Calendar"

import os
from datetime import datetime
from datetime import date
from utils import get_display_name
from utils import get_config_param
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import locate_post
from utils import load_json
from utils import week_day_of_month_start
from utils import get_alt_path
from utils import remove_domain_port
from utils import acct_dir
from utils import local_actor_url
from utils import replace_users_with_at
from happening import get_todays_events
from happening import get_calendar_events
from happening import get_todays_events_icalendar
from happening import get_month_events_icalendar
from webapp_utils import set_custom_background
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_utils import html_hide_from_screen_reader
from webapp_utils import html_keyboard_navigation


def html_calendar_delete_confirm(css_cache: {}, translate: {}, base_dir: str,
                                 path: str, http_prefix: str,
                                 domain_full: str, post_id: str,
                                 post_time: str,
                                 year: int, month_number: int,
                                 day_number: int, calling_domain: str) -> str:
    """Shows a screen asking to confirm the deletion of a calendar event
    """
    nickname = get_nickname_from_actor(path)
    actor = local_actor_url(http_prefix, nickname, domain_full)
    domain, _ = get_domain_from_actor(actor)
    message_id = actor + '/statuses/' + post_id

    post_filename = locate_post(base_dir, nickname, domain, message_id)
    if not post_filename:
        return None

    post_json_object = load_json(post_filename)
    if not post_json_object:
        return None

    delete_post_str = None
    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    delete_post_str = \
        html_header_with_external_style(css_filename, instance_title, None)
    delete_post_str += \
        '<center><h1>' + post_time + ' ' + str(year) + '/' + \
        str(month_number) + \
        '/' + str(day_number) + '</h1></center>'
    delete_post_str += '<center>'
    delete_post_str += '  <p class="followText">' + \
        translate['Delete this event'] + '</p>'

    post_actor = get_alt_path(actor, domain_full, calling_domain)
    delete_post_str += \
        '  <form method="POST" action="' + post_actor + '/rmpost">\n'
    delete_post_str += '    <input type="hidden" name="year" value="' + \
        str(year) + '">\n'
    delete_post_str += '    <input type="hidden" name="month" value="' + \
        str(month_number) + '">\n'
    delete_post_str += '    <input type="hidden" name="day" value="' + \
        str(day_number) + '">\n'
    delete_post_str += \
        '    <input type="hidden" name="pageNumber" value="1">\n'
    delete_post_str += \
        '    <input type="hidden" name="messageId" value="' + \
        message_id + '">\n'
    delete_post_str += \
        '    <button type="submit" class="button" name="submitYes">' + \
        translate['Yes'] + '</button>\n'
    delete_post_str += \
        '    <a href="' + actor + '/calendar?year=' + \
        str(year) + '?month=' + \
        str(month_number) + '"><button class="button">' + \
        translate['No'] + '</button></a>\n'
    delete_post_str += '  </form>\n'
    delete_post_str += '</center>\n'
    delete_post_str += html_footer()
    return delete_post_str


def _html_calendar_day(person_cache: {}, css_cache: {}, translate: {},
                       base_dir: str, path: str,
                       year: int, month_number: int, day_number: int,
                       nickname: str, domain: str, day_events: [],
                       month_name: str, actor: str) -> str:
    """Show a day within the calendar
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    calendar_file = account_dir + '/.newCalendar'
    if os.path.isfile(calendar_file):
        try:
            os.remove(calendar_file)
        except OSError:
            print('EX: _html_calendar_day unable to delete ' + calendar_file)

    css_filename = base_dir + '/epicyon-calendar.css'
    if os.path.isfile(base_dir + '/calendar.css'):
        css_filename = base_dir + '/calendar.css'

    cal_actor = actor
    if '/users/' in actor:
        cal_actor = '/users/' + actor.split('/users/')[1]

    instance_title = get_config_param(base_dir, 'instanceTitle')
    calendar_str = \
        html_header_with_external_style(css_filename, instance_title, None)
    calendar_str += '<main><table class="calendar">\n'
    calendar_str += '<caption class="calendar__banner--month">\n'
    calendar_str += \
        '  <a href="' + cal_actor + '/calendar?year=' + str(year) + \
        '?month=' + str(month_number) + '">\n'
    calendar_str += \
        '  <h1>' + str(day_number) + ' ' + month_name + \
        '</h1></a><br><span class="year">' + str(year) + '</span>\n'
    calendar_str += '</caption>\n'
    calendar_str += '<tbody>\n'

    if day_events:
        for event_post in day_events:
            event_time = None
            event_description = None
            event_place = None
            post_id = None
            sender_name = ''
            sender_actor = None
            event_is_public = False
            # get the time place and description
            for evnt in event_post:
                if evnt['type'] == 'Event':
                    if evnt.get('post_id'):
                        post_id = evnt['post_id']
                    if evnt.get('startTime'):
                        event_date = \
                            datetime.strptime(evnt['startTime'],
                                              "%Y-%m-%dT%H:%M:%S%z")
                        event_time = event_date.strftime("%H:%M").strip()
                    if 'public' in evnt:
                        if evnt['public'] is True:
                            event_is_public = True
                    if evnt.get('sender'):
                        # get display name from sending actor
                        if evnt.get('sender'):
                            sender_actor = evnt['sender']
                            disp_name = \
                                get_display_name(base_dir, sender_actor,
                                                 person_cache)
                            if disp_name:
                                sender_name = \
                                    '<a href="' + sender_actor + '">' + \
                                    disp_name + '</a>: '
                    if evnt.get('name'):
                        event_description = evnt['name'].strip()
                elif evnt['type'] == 'Place':
                    if evnt.get('name'):
                        event_place = evnt['name']

            # prepend a link to the sender of the calendar item
            if sender_name and event_description:
                # if the sender is also mentioned within the event
                # description then this is a reminder
                sender_actor2 = replace_users_with_at(sender_actor)
                if sender_actor not in event_description and \
                   sender_actor2 not in event_description:
                    event_description = sender_name + event_description
                else:
                    event_description = \
                        translate['Reminder'] + ': ' + event_description

            delete_button_str = ''
            if post_id:
                delete_button_str = \
                    '<td class="calendar__day__icons"><a href="' + \
                    cal_actor + \
                    '/eventdelete?eventid=' + post_id + \
                    '?year=' + str(year) + \
                    '?month=' + str(month_number) + \
                    '?day=' + str(day_number) + \
                    '?time=' + event_time + \
                    '">\n<img class="calendardayicon" loading="lazy" alt="' + \
                    translate['Delete this event'] + ' |" title="' + \
                    translate['Delete this event'] + '" src="/' + \
                    'icons/delete.png" /></a></td>\n'

            event_class = 'calendar__day__event'
            cal_item_class = 'calItem'
            if event_is_public:
                event_class = 'calendar__day__event__public'
                cal_item_class = 'calItemPublic'
            if event_time and event_description and event_place:
                calendar_str += \
                    '<tr class="' + cal_item_class + '">' + \
                    '<td class="calendar__day__time"><b>' + event_time + \
                    '</b></td><td class="' + event_class + '">' + \
                    '<span class="place">' + \
                    event_place + '</span><br>' + event_description + \
                    '</td>' + delete_button_str + '</tr>\n'
            elif event_time and event_description and not event_place:
                calendar_str += \
                    '<tr class="' + cal_item_class + '">' + \
                    '<td class="calendar__day__time"><b>' + event_time + \
                    '</b></td><td class="' + event_class + '">' + \
                    event_description + '</td>' + delete_button_str + '</tr>\n'
            elif not event_time and event_description and not event_place:
                calendar_str += \
                    '<tr class="' + cal_item_class + '">' + \
                    '<td class="calendar__day__time">' + \
                    '</td><td class="' + event_class + '">' + \
                    event_description + '</td>' + delete_button_str + '</tr>\n'
            elif not event_time and event_description and event_place:
                calendar_str += \
                    '<tr class="' + cal_item_class + '">' + \
                    '<td class="calendar__day__time"></td>' + \
                    '<td class="' + event_class + '"><span class="place">' + \
                    event_place + '</span><br>' + event_description + \
                    '</td>' + delete_button_str + '</tr>\n'
            elif event_time and not event_description and event_place:
                calendar_str += \
                    '<tr class="' + cal_item_class + '">' + \
                    '<td class="calendar__day__time"><b>' + event_time + \
                    '</b></td><td class="' + event_class + '">' + \
                    '<span class="place">' + \
                    event_place + '</span></td>' + \
                    delete_button_str + '</tr>\n'

    # icalendar download link
    calendar_str += \
        '    <a href="/users/' + path + '?ical=true" ' + \
        'download="icalendar.ics">' + \
        '<img class="ical" src="/icons/ical.png" ' + \
        'title="iCalendar" alt="iCalendar" /></a>\n'

    calendar_str += '</tbody>\n'
    calendar_str += '</table></main>\n'
    calendar_str += html_footer()

    return calendar_str


def html_calendar(person_cache: {}, css_cache: {}, translate: {},
                  base_dir: str, path: str,
                  http_prefix: str, domain_full: str,
                  text_mode_banner: str, access_keys: {},
                  icalendar: bool) -> str:
    """Show the calendar for a person
    """
    domain = remove_domain_port(domain_full)

    month_number = 0
    day_number = None
    year = 1970
    actor = http_prefix + '://' + domain_full + path.replace('/calendar', '')
    if '?' in actor:
        first = True
        for part in actor.split('?'):
            if not first:
                if '=' in part:
                    if part.split('=')[0] == 'year':
                        num_str = part.split('=')[1]
                        if num_str.isdigit():
                            year = int(num_str)
                    elif part.split('=')[0] == 'month':
                        num_str = part.split('=')[1]
                        if num_str.isdigit():
                            month_number = int(num_str)
                    elif part.split('=')[0] == 'day':
                        num_str = part.split('=')[1]
                        if num_str.isdigit():
                            day_number = int(num_str)
                    elif part.split('=')[0] == 'ical':
                        bool_str = part.split('=')[1]
                        if bool_str.lower().startswith('t'):
                            icalendar = True
            first = False
        actor = actor.split('?')[0]

    curr_date = datetime.now()
    if year == 1970 and month_number == 0:
        year = curr_date.year
        month_number = curr_date.month

    nickname = get_nickname_from_actor(actor)

    set_custom_background(base_dir, 'calendar-background',
                          'calendar-background')

    months = (
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    )
    month_name = translate[months[month_number - 1]]

    if day_number:
        if icalendar:
            return get_todays_events_icalendar(base_dir,
                                               nickname, domain,
                                               year, month_number,
                                               day_number,
                                               person_cache)

        day_events = None
        events = \
            get_todays_events(base_dir, nickname, domain,
                              year, month_number, day_number)
        if events:
            if events.get(str(day_number)):
                day_events = events[str(day_number)]
        return _html_calendar_day(person_cache, css_cache,
                                  translate, base_dir, path,
                                  year, month_number, day_number,
                                  nickname, domain, day_events,
                                  month_name, actor)

    if icalendar:
        return get_month_events_icalendar(base_dir, nickname, domain,
                                          year, month_number, person_cache)

    events = \
        get_calendar_events(base_dir, nickname, domain, year, month_number)

    prev_year = year
    prev_month_number = month_number - 1
    if prev_month_number < 1:
        prev_month_number = 12
        prev_year = year - 1

    next_year = year
    next_month_number = month_number + 1
    if next_month_number > 12:
        next_month_number = 1
        next_year = year + 1

    print('Calendar year=' + str(year) + ' month=' + str(month_number) +
          ' ' + str(week_day_of_month_start(month_number, year)))

    if month_number < 12:
        days_in_month = \
            (date(year, month_number + 1, 1) -
             date(year, month_number, 1)).days
    else:
        days_in_month = \
            (date(year + 1, 1, 1) - date(year, month_number, 1)).days
    # print('days_in_month ' + str(month_number) + ': ' + str(days_in_month))

    css_filename = base_dir + '/epicyon-calendar.css'
    if os.path.isfile(base_dir + '/calendar.css'):
        css_filename = base_dir + '/calendar.css'

    cal_actor = actor
    if '/users/' in actor:
        cal_actor = '/users/' + actor.split('/users/')[1]

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    header_str = \
        html_header_with_external_style(css_filename, instance_title, None)

    # the main graphical calendar as a table
    calendar_str = '<main><table class="calendar">\n'
    calendar_str += '<caption class="calendar__banner--month">\n'
    calendar_str += \
        '  <a href="' + cal_actor + '/calendar?year=' + str(prev_year) + \
        '?month=' + str(prev_month_number) + '" ' + \
        'accesskey="' + access_keys['Page up'] + '">'
    calendar_str += \
        '  <img loading="lazy" alt="' + translate['Previous month'] + \
        '" title="' + translate['Previous month'] + '" src="/icons' + \
        '/prev.png" class="buttonprev"/></a>\n'
    calendar_str += '  <a href="' + cal_actor + '/inbox" title="'
    calendar_str += translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + access_keys['menuTimeline'] + '">'
    calendar_str += '  <h1>' + month_name + '</h1></a>\n'
    calendar_str += \
        '  <a href="' + cal_actor + '/calendar?year=' + str(next_year) + \
        '?month=' + str(next_month_number) + '" ' + \
        'accesskey="' + access_keys['Page down'] + '">'
    calendar_str += \
        '  <img loading="lazy" alt="' + translate['Next month'] + \
        '" title="' + translate['Next month'] + '" src="/icons' + \
        '/prev.png" class="buttonnext"/></a>\n'
    calendar_str += '</caption>\n'
    calendar_str += '<thead>\n'
    calendar_str += '<tr>\n'
    days = ('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat')
    for day in days:
        calendar_str += '  <th scope="col" class="calendar__day__header">' + \
            translate[day] + '</th>\n'
    calendar_str += '</tr>\n'
    calendar_str += '</thead>\n'
    calendar_str += '<tbody>\n'

    # beginning of the links used for accessibility
    nav_links = {}
    timeline_link_str = html_hide_from_screen_reader('🏠') + ' ' + \
        translate['Switch to timeline view']
    nav_links[timeline_link_str] = cal_actor + '/inbox'

    day_of_month = 0
    dow = week_day_of_month_start(month_number, year)
    for week_of_month in range(1, 7):
        if day_of_month == days_in_month:
            continue
        calendar_str += '  <tr>\n'
        for day_number in range(1, 8):
            if (week_of_month > 1 and day_of_month < days_in_month) or \
               (week_of_month == 1 and day_number >= dow):
                day_of_month += 1

                is_today = False
                if year == curr_date.year:
                    if curr_date.month == month_number:
                        if day_of_month == curr_date.day:
                            is_today = True
                if events.get(str(day_of_month)):
                    url = cal_actor + '/calendar?year=' + \
                        str(year) + '?month=' + \
                        str(month_number) + '?day=' + str(day_of_month)
                    day_description = month_name + ' ' + str(day_of_month)
                    day_link = '<a href="' + url + '" ' + \
                        'title="' + day_description + '">' + \
                        str(day_of_month) + '</a>'
                    # accessibility menu links
                    menu_option_str = \
                        html_hide_from_screen_reader('📅') + ' ' + \
                        day_description
                    nav_links[menu_option_str] = url
                    # there are events for this day
                    if not is_today:
                        calendar_str += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-event="">' + \
                            day_link + '</td>\n'
                    else:
                        calendar_str += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-today-event="">' + \
                            day_link + '</td>\n'
                else:
                    # No events today
                    if not is_today:
                        calendar_str += \
                            '    <td class="calendar__day__cell">' + \
                            str(day_of_month) + '</td>\n'
                    else:
                        calendar_str += \
                            '    <td class="calendar__day__cell" ' + \
                            'data-today="">' + str(day_of_month) + '</td>\n'
            else:
                calendar_str += '    <td class="calendar__day__cell"></td>\n'
        calendar_str += '  </tr>\n'

    calendar_str += '</tbody>\n'
    calendar_str += '</table></main>\n'

    # end of the links used for accessibility
    next_month_str = \
        html_hide_from_screen_reader('→') + ' ' + translate['Next month']
    nav_links[next_month_str] = \
        cal_actor + '/calendar?year=' + str(next_year) + \
        '?month=' + str(next_month_number)
    prev_month_str = \
        html_hide_from_screen_reader('←') + ' ' + translate['Previous month']
    nav_links[prev_month_str] = \
        cal_actor + '/calendar?year=' + str(prev_year) + \
        '?month=' + str(prev_month_number)
    nav_access_keys = {
    }
    screen_reader_cal = \
        html_keyboard_navigation(text_mode_banner, nav_links, nav_access_keys,
                                 month_name)

    new_event_str = \
        '<br><center>\n<p>\n' + \
        '<a href="' + cal_actor + '/newreminder">➕ ' + \
        translate['Add to the calendar'] + '</a>\n</p>\n</center>\n'

    calendar_icon_str += \
        '    <a href="/users/' + path + '?ical=true" ' + \
        'download="icalendar.ics">' + \
        '<img class="ical" src="/icons/ical.png" ' + \
        'title="iCalendar" alt="iCalendar" /></a>\n'

    cal_str = \
        header_str + screen_reader_cal + calendar_str + \
        new_event_str + calendar_icon_str + html_footer()

    return cal_str
