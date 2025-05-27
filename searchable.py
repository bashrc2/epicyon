__filename__ = "searchable.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

# Whether posts are searchable
# See https://codeberg.org/fediverse/fep/src/branch/main/fep/268d/fep-268d.md

import os
from utils import acct_dir
from utils import data_dir
from utils import text_in_file
from utils import is_account_dir


def load_searchable_by_default(base_dir: str) -> {}:
    """loads the searchable_by states for each account
    """
    result = {}
    dir_str = data_dir(base_dir)
    for _, dirs, _ in os.walk(dir_str):
        for account in dirs:
            if not is_account_dir(account):
                continue
            nickname = account.split('@')[0]
            filename = os.path.join(dir_str, account) + '/.searchableByDefault'
            if os.path.isfile(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as fp_search:
                        result[nickname] = fp_search.read().strip()
                except OSError:
                    print('EX: unable to load searchableByDefault ' + filename)
        break
    return result


def set_searchable_by(base_dir: str, nickname: str, domain: str,
                      searchable_by: str) -> None:
    """Sets the searchable_by state for an account from the dropdown on
    new post screen
    """
    if not searchable_by:
        return
    filename = acct_dir(base_dir, nickname, domain) + '/.searchableByDefault'

    # already the same state?
    if os.path.isfile(filename):
        if text_in_file(searchable_by, filename, True):
            return

    # write the new state
    try:
        with open(filename, 'w+', encoding='utf-8') as fp_search:
            fp_search.write(searchable_by)
    except OSError:
        print('EX: unable to write searchableByDropdown ' + filename)
