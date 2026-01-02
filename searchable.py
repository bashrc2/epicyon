__filename__ = "searchable.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
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
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import get_full_domain
from utils import get_followers_list
from utils import get_mutuals_of_person


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


def _actor_in_searchable_by(searchable_by: str, following_list: []) -> bool:
    """Does the given actor within searchable_by exist within the given list?
    """
    data_actor = searchable_by.split('/followers')[0]

    if '"' in data_actor:
        data_actor = data_actor.split('"')[-1]

    if data_actor not in following_list:
        data_nickname = get_nickname_from_actor(data_actor)
        data_domain, data_port = get_domain_from_actor(data_actor)
        if not data_nickname or not data_domain:
            return False
        data_domain_full = get_full_domain(data_domain, data_port)
        data_handle = data_nickname + '@' + data_domain_full
        if data_handle not in following_list:
            return False
    return True


def _search_virtual_box_posts(base_dir: str, nickname: str, domain: str,
                              search_str: str, max_results: int,
                              box_name: str) -> []:
    """Searches through a virtual box, which is typically an index on the inbox
    """
    index_filename = \
        acct_dir(base_dir, nickname, domain) + '/' + box_name + '.index'
    if box_name == 'bookmarks':
        box_name = 'inbox'
    path = acct_dir(base_dir, nickname, domain) + '/' + box_name
    if not os.path.isdir(path):
        return []

    search_str = search_str.lower().strip()

    if '+' in search_str:
        search_words = search_str.split('+')
        for index, _ in enumerate(search_words):
            search_words[index] = search_words[index].strip()
        print('SEARCH: ' + str(search_words))
    else:
        search_words = [search_str]

    res: list[str] = []
    try:
        with open(index_filename, 'r', encoding='utf-8') as fp_index:
            post_filename = 'start'
            while post_filename:
                post_filename = fp_index.readline()
                if not post_filename:
                    break
                if '.json' not in post_filename:
                    break
                post_filename = path + '/' + post_filename.strip()
                if not os.path.isfile(post_filename):
                    continue
                with open(post_filename, 'r', encoding='utf-8') as fp_post:
                    data = fp_post.read().lower()

                    not_found = False
                    for keyword in search_words:
                        if keyword not in data:
                            not_found = True
                            break
                    if not_found:
                        continue

                    res.append(post_filename)
                    if len(res) >= max_results:
                        return res
    except OSError as exc:
        print('EX: _search_virtual_box_posts unable to read ' +
              index_filename + ' ' + str(exc))
    return res


def search_box_posts(base_dir: str, nickname: str, domain: str,
                     search_str: str, max_results: int,
                     box_name: str = 'outbox') -> []:
    """Search your posts and return a list of the filenames
    containing matching strings
    """
    path = acct_dir(base_dir, nickname, domain) + '/' + box_name
    # is this a virtual box, such as direct messages?
    if not os.path.isdir(path):
        if os.path.isfile(path + '.index'):
            return _search_virtual_box_posts(base_dir, nickname, domain,
                                             search_str, max_results, box_name)
        return []
    search_str = search_str.lower().strip()

    if '+' in search_str:
        search_words = search_str.split('+')
        for index, _ in enumerate(search_words):
            search_words[index] = search_words[index].strip()
        print('SEARCH: ' + str(search_words))
    else:
        search_words = [search_str]

    following_list: list[str] = []
    mutuals_list: list[str] = []
    check_searchable_by = False
    if box_name == 'inbox':
        check_searchable_by = True
        # https://codeberg.org/fediverse/fep/
        # src/branch/main/fep/268d/fep-268d.md
        # create a list containing all of the handles followed
        following_list = get_followers_list(base_dir, nickname, domain,
                                            'following.txt')
        # create a list containing all of the mutuals
        mutuals_list = get_mutuals_of_person(base_dir, nickname, domain)

    res: list[str] = []
    for root, _, fnames in os.walk(path):
        for fname in fnames:
            file_path = os.path.join(root, fname)
            try:
                with open(file_path, 'r', encoding='utf-8') as fp_post:
                    data = fp_post.read()
                    data_lower = data.lower()

                    not_found = False
                    for keyword in search_words:
                        if keyword not in data_lower:
                            not_found = True
                            break
                    if not_found:
                        continue

                    # if this is not an outbox/bookmarks search then is the
                    # post marked as being searchable?
                    # https://codeberg.org/fediverse/fep/
                    # src/branch/main/fep/268d/fep-268d.md
                    if check_searchable_by:
                        if '"searchableBy":' not in data:
                            continue
                        searchable_by = \
                            data.split('"searchableBy":')[1].strip()
                        if searchable_by.startswith('['):
                            searchable_by = searchable_by.split(']')[0]
                        if '"' in searchable_by:
                            searchable_by = searchable_by.split('"')[1]
                        elif "'" in searchable_by:
                            searchable_by = searchable_by.split("'")[1]
                        else:
                            continue
                        if '#Public' not in searchable_by:
                            if '/followers' in searchable_by and \
                               following_list:
                                if not _actor_in_searchable_by(searchable_by,
                                                               following_list):
                                    continue
                            elif '/mutuals' in searchable_by and mutuals_list:
                                if not _actor_in_searchable_by(searchable_by,
                                                               mutuals_list):
                                    continue
                            else:
                                continue

                    res.append(file_path)
                    if len(res) >= max_results:
                        return res
            except OSError as exc:
                print('EX: search_box_posts unable to read ' +
                      file_path + ' ' + str(exc))
        break
    return res
