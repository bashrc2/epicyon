__filename__ = "textmode.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
from utils import data_dir


def text_mode_browser(ua_str: str) -> bool:
    """Does the user agent indicate a text mode browser?
    """
    if ua_str:
        text_mode_agents = ('Lynx/', 'w3m/', 'Links (', 'Emacs/', 'ELinks')
        for agent in text_mode_agents:
            if agent in ua_str:
                return True
    return False


def text_mode_removals(text: str, translate: {}) -> str:
    """Removes some elements of a post when displaying in a text mode browser
    """
    text = text.replace(translate['SHOW MORE'], '')
    text = text.replace(translate['mitm'], '👁 ')
    return text


def text_mode_replacements(text: str, translate: {}) -> str:
    """Replaces some elements of a post when displaying in a text mode browser
    """
    text = text.replace('">⇆ ', '">' + translate['Mutual'] + ' ')
    return text


def get_text_mode_banner(base_dir: str) -> str:
    """Returns the banner used for shell browsers, like Lynx
    """
    text_mode_banner_filename = data_dir(base_dir) + '/banner.txt'
    if os.path.isfile(text_mode_banner_filename):
        with open(text_mode_banner_filename, 'r',
                  encoding='utf-8') as fp_text:
            banner_str = fp_text.read()
            if banner_str:
                return banner_str.replace('\n', '<br>')
    return None


def get_text_mode_logo(base_dir: str) -> str:
    """Returns the login screen logo used for shell browsers, like Lynx
    """
    text_mode_logo_filename = data_dir(base_dir) + '/logo.txt'
    if not os.path.isfile(text_mode_logo_filename):
        text_mode_logo_filename = base_dir + '/img/logo.txt'

    with open(text_mode_logo_filename, 'r', encoding='utf-8') as fp_text:
        logo_str = fp_text.read()
        if logo_str:
            return logo_str.replace('\n', '<br>')
    return None


def set_text_mode_theme(base_dir: str, name: str) -> None:
    # set the text mode logo which appears on the login screen
    # in browsers such as Lynx
    text_mode_logo_filename = \
        base_dir + '/theme/' + name + '/logo.txt'
    dir_str = data_dir(base_dir)
    if os.path.isfile(text_mode_logo_filename):
        try:
            copyfile(text_mode_logo_filename, dir_str + '/logo.txt')
        except OSError:
            print('EX: set_text_mode_theme unable to copy ' +
                  text_mode_logo_filename + ' ' +
                  dir_str + '/logo.txt')
    else:
        dir_str = data_dir(base_dir)
        try:
            copyfile(base_dir + '/img/logo.txt', dir_str + '/logo.txt')
        except OSError:
            print('EX: set_text_mode_theme unable to copy ' +
                  base_dir + '/img/logo.txt ' + dir_str + '/logo.txt')

    # set the text mode banner which appears in browsers such as Lynx
    text_mode_banner_filename = \
        base_dir + '/theme/' + name + '/banner.txt'
    if os.path.isfile(dir_str + '/banner.txt'):
        try:
            os.remove(dir_str + '/banner.txt')
        except OSError:
            print('EX: set_text_mode_theme unable to delete ' +
                  dir_str + '/banner.txt')
    if os.path.isfile(text_mode_banner_filename):
        try:
            copyfile(text_mode_banner_filename, dir_str + '/banner.txt')
        except OSError:
            print('EX: set_text_mode_theme unable to copy ' +
                  text_mode_banner_filename + ' ' +
                  dir_str + '/banner.txt')
