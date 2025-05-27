__filename__ = "status.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"
__accounts_data_path__ = None
__accounts_data_path_tests__ = False

from utils import date_utcnow
from utils import date_from_string_format
from utils import remove_html
from utils import standardize_text

MAX_STATUS_LENGTH = 100


def get_actor_status(profile_json: {}) -> str:
    """returns the actor status if it exists
    https://codeberg.org/fediverse/fep/src/branch/main/fep/82f6/fep-82f6.md
    """
    if not profile_json.get('sm:status'):
        return ''
    status = ''
    if isinstance(profile_json['sm:status'], str):
        status = profile_json['sm:status']
    elif isinstance(profile_json['sm:status'], dict):
        if profile_json['sm:status'].get('content'):
            possible_status = profile_json['sm:status']['content']
            if isinstance(status, str):
                status = possible_status
    if status:
        status = remove_html(status)
        if len(status) > MAX_STATUS_LENGTH:
            status = status[:MAX_STATUS_LENGTH]
        status = standardize_text(status)
    return status


def actor_status_expired(actor_status_json: {}) -> bool:
    """Has the given actor status expired?
    """
    if not actor_status_json.get('endTime'):
        return False
    if not isinstance(actor_status_json['endTime'], str):
        return False
    if 'T' not in actor_status_json['endTime'] or \
       ':' not in actor_status_json['endTime']:
        return False
    date_formats = (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S%Z"
    )
    status_end_time = None
    try:
        status_end_time = \
            date_from_string_format(actor_status_json['endTime'],
                                    date_formats)
    except BaseException:
        return False
    if not status_end_time:
        return False
    curr_time = date_utcnow()
    if status_end_time < curr_time:
        return True
    return False
