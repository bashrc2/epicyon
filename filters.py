__filename__ = "filters.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Moderation"

import os
import fnmatch
from utils import data_dir
from utils import acct_dir
from utils import text_in_file
from utils import remove_eol
from unicodetext import standardize_text
from unicodetext import remove_inverted_text
from unicodetext import remove_square_capitals
from data import append_string
from data import save_string
from data import load_list


def add_filter(base_dir: str, nickname: str, domain: str, words: str) -> bool:
    """Adds a filter for particular words within the content of a
    incoming posts
    """
    filters_filename = acct_dir(base_dir, nickname, domain) + '/filters.txt'
    if os.path.isfile(filters_filename):
        if text_in_file(words, filters_filename):
            return False
    if not append_string(words + '\n', filters_filename,
                         'EX: unable to append filters ' + filters_filename):
        return False
    return True


def add_global_filter(base_dir: str, words: str) -> bool:
    """Adds a global filter for particular words within
    the content of a incoming posts
    """
    if not words:
        return False
    if len(words) < 2:
        return False
    filters_filename = data_dir(base_dir) + '/filters.txt'
    if os.path.isfile(filters_filename):
        if text_in_file(words, filters_filename):
            return False
    if not append_string(words + '\n', filters_filename,
                         'EX: unable to append filters ' + filters_filename):
        return False
    return True


def remove_filter(base_dir: str, nickname: str, domain: str,
                  words: str) -> bool:
    """Removes a word filter
    """
    filters_filename = acct_dir(base_dir, nickname, domain) + '/filters.txt'
    if not os.path.isfile(filters_filename):
        return False
    if not text_in_file(words, filters_filename):
        return False
    new_filters_filename = filters_filename + '.new'

    filters_list: list[str] = \
        load_list(filters_filename,
                  'EX: unable to remove filter ' +
                  filters_filename + ' 1 [ex]')
    if filters_list is None:
        return False

    text: str = ''
    for line in filters_list:
        line = remove_eol(line)
        if line != words:
            text += line + '\n'
    save_string(text, new_filters_filename,
                'EX: unable to remove filter ' +
                filters_filename + ' 2 [ex]')

    if os.path.isfile(new_filters_filename):
        try:
            os.rename(new_filters_filename, filters_filename)
            return True
        except OSError:
            print('EX: remove_filter could not rename ' +
                  new_filters_filename + ' -> ' + filters_filename)
    return False


def remove_global_filter(base_dir: str, words: str) -> bool:
    """Removes a global word filter
    """
    filters_filename = data_dir(base_dir) + '/filters.txt'
    if not os.path.isfile(filters_filename):
        return False
    if not text_in_file(words, filters_filename):
        return False
    new_filters_filename = filters_filename + '.new'

    global_list: list[str] = \
        load_list(filters_filename,
                  'EX: unable to remove global filter ' +
                  filters_filename + ' [ex]')
    if global_list is None:
        return False

    text: str = ''
    for line in global_list:
        line = remove_eol(line)
        if line != words:
            text += line + '\n'
    save_string(text, new_filters_filename,
                'EX: unable to remove global filter ' +
                filters_filename + ' 2 [ex]')

    if os.path.isfile(new_filters_filename):
        try:
            os.rename(new_filters_filename, filters_filename)
            return True
        except OSError:
            print('EX: remove_global_filter could not rename ' +
                  new_filters_filename + ' -> ' + filters_filename)
    return False


def _is_twitter_post(content: str) -> bool:
    """Returns true if the given post content is a retweet or twitter crosspost
    """
    features = (
        '/x.com', '/twitter.', '/nitter.',
        '@twitter.', '@nitter.', '@x.com',
        '>RT <', '_tw<', '_tw@', 'tweet', 'Tweet', '🐦🔗'
    )
    for feat in features:
        if feat in content:
            return True
    return False


def filtered_match(filter_str: str, content: str) -> bool:
    """Does the given filter match the content?
    """
    if '*' not in filter_str:
        if filter_str in content:
            return True
    elif fnmatch.fnmatchcase(content, filter_str):
        return True

    return False


def _is_filtered_base(filename: str, content: str,
                      system_language: str) -> bool:
    """Uses the given file containing filtered words to check
    the given content
    """
    if not os.path.isfile(filename):
        return False

    content = remove_inverted_text(content, system_language)
    content = remove_square_capitals(content, system_language)

    # convert any fancy characters to ordinary ones
    content = standardize_text(content)

    filtered_list: list[str] = \
        load_list(filename,
                  'EX: _is_filtered_base ' + filename + ' [ex]')
    if filtered_list is not None:
        for line in filtered_list:
            filter_str = remove_eol(line)
            if not filter_str:
                continue
            if len(filter_str) < 2:
                continue
            if '+' not in filter_str:
                if filtered_match(filter_str, content):
                    return True
            else:
                filter_words = filter_str.replace('"', '').split('+')
                for filter_wrd in filter_words:
                    if not filtered_match(filter_wrd, content):
                        return False
                return True
    return False


def is_filtered_globally(base_dir: str, content: str,
                         system_language: str) -> bool:
    """Is the given content globally filtered?
    """
    global_filters_filename = data_dir(base_dir) + '/filters.txt'
    if _is_filtered_base(global_filters_filename, content,
                         system_language):
        return True
    return False


def is_filtered_bio(base_dir: str,
                    nickname: str, domain: str, bio: str,
                    system_language: str) -> bool:
    """Should the given actor bio be filtered out?
    """
    if is_filtered_globally(base_dir, bio, system_language):
        return True

    if not nickname or not domain:
        return False

    account_filters_filename = \
        acct_dir(base_dir, nickname, domain) + '/filters_bio.txt'
    return _is_filtered_base(account_filters_filename, bio, system_language)


def is_filtered(base_dir: str, nickname: str, domain: str,
                content: str, system_language: str) -> bool:
    """Should the given content be filtered out?
    This is a simple type of filter which just matches words, not a regex
    You can add individual words or use word1+word2 to indicate that two
    words must be present although not necessarily adjacent
    """
    if is_filtered_globally(base_dir, content, system_language):
        return True

    if not nickname or not domain:
        return False

    # optionally remove retweets
    remove_twitter = acct_dir(base_dir, nickname, domain) + '/.removeTwitter'
    if os.path.isfile(remove_twitter):
        if _is_twitter_post(content):
            return True

    account_filters_filename = \
        acct_dir(base_dir, nickname, domain) + '/filters.txt'
    return _is_filtered_base(account_filters_filename, content,
                             system_language)


def is_question_filtered(base_dir: str, nickname: str, domain: str,
                         system_language: str, question_json: {}) -> bool:
    """is the given question filtered based on its options?
    """
    if question_json.get('oneOf'):
        question_options = question_json['oneOf']
    else:
        question_options = question_json['object']['oneOf']
    for option in question_options:
        if option.get('name'):
            if is_filtered(base_dir, nickname, domain, option['name'],
                           system_language):
                return True
    return False
