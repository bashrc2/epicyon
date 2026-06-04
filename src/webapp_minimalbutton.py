__filename__ = "webapp_minimalbutton.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

from src.utils import acct_dir
from src.data import erase_file
from src.data import save_flag_file
from src.data import is_a_file
from src.data import is_a_dir


def is_minimal(base_dir: str, domain: str, nickname: str) -> bool:
    """Returns true if minimal buttons should be shown
       for the given account
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    if not is_a_dir(account_dir):
        return True
    minimal_filename = account_dir + '/.notminimal'
    if is_a_file(minimal_filename):
        return False
    return True


def set_minimal(base_dir: str, domain: str, nickname: str,
                minimal: bool) -> None:
    """Sets whether an account should display minimal buttons
    """
    account_dir = acct_dir(base_dir, nickname, domain)
    if not is_a_dir(account_dir):
        return
    minimal_filename = account_dir + '/.notminimal'
    minimal_file_exists = is_a_file(minimal_filename)
    if minimal and minimal_file_exists:
        erase_file(minimal_filename,
                   'EX: set_minimal unable to delete ' + minimal_filename)
    elif not minimal and not minimal_file_exists:
        save_flag_file(minimal_filename,
                       'EX: unable to write minimal ' + minimal_filename)
