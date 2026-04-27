__filename__ = "webapp_welcome.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Onboarding"

import os
from shutil import copyfile
from utils import data_dir
from utils import get_config_param
from utils import remove_html
from utils import acct_dir
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from markdown import markdown_to_html
from data import save_string
from data import load_string


def is_welcome_screen_complete(base_dir: str,
                               nickname: str, domain: str) -> bool:
    """Returns true if the welcome screen is complete for the given account
    """
    account_path = acct_dir(base_dir, nickname, domain)
    if not os.path.isdir(account_path):
        return False
    complete_filename = account_path + '/.welcome_complete'
    return os.path.isfile(complete_filename)


def welcome_screen_is_complete(base_dir: str,
                               nickname: str, domain: str) -> None:
    """Indicates that the welcome screen has been shown for a given account
    """
    account_path = acct_dir(base_dir, nickname, domain)
    if not os.path.isdir(account_path):
        return
    complete_filename = account_path + '/.welcome_complete'
    save_string('\n', complete_filename,
                'EX: welcome_screen_is_complete unable to write ' +
                complete_filename)


def html_welcome_screen(base_dir: str, nickname: str,
                        language: str, translate: {},
                        theme_name: str,
                        curr_screen: str = 'welcome') -> str:
    """Returns the welcome screen
    """
    # set a custom background for the welcome screen
    dir_str = data_dir(base_dir)
    if os.path.isfile(dir_str + '/welcome-background-custom.jpg'):
        if not os.path.isfile(dir_str + '/welcome-background.jpg'):
            copyfile(dir_str + '/welcome-background-custom.jpg',
                     dir_str + '/welcome-background.jpg')

    welcome_text = 'Welcome to Epicyon'
    welcome_filename = dir_str + '/' + curr_screen + '.md'
    if not os.path.isfile(welcome_filename):
        default_filename = None
        if theme_name:
            default_filename = \
                base_dir + '/theme/' + theme_name + '/welcome/' + \
                'welcome_' + language + '.md'
            if not os.path.isfile(default_filename):
                default_filename = None
        if not default_filename:
            default_filename = \
                base_dir + '/defaultwelcome/' + \
                curr_screen + '_' + language + '.md'
        if not os.path.isfile(default_filename):
            default_filename = \
                base_dir + '/defaultwelcome/' + curr_screen + '_en.md'
        copyfile(default_filename, welcome_filename)

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    if not instance_title:
        instance_title = 'Epicyon'

    if os.path.isfile(welcome_filename):
        welcome_text = load_string(welcome_filename,
                                   'EX: html_welcome_screen unable to read ' +
                                   welcome_filename)
        if welcome_text is not None:
            welcome_text = welcome_text.replace('INSTANCE', instance_title)
            welcome_text = markdown_to_html(remove_html(welcome_text))
        else:
            welcome_text: str = ''
    welcome_form: str = ''
    css_filename = base_dir + '/epicyon-welcome.css'
    if os.path.isfile(base_dir + '/welcome.css'):
        css_filename = base_dir + '/welcome.css'

    preload_images: list[str] = []
    welcome_form = \
        html_header_with_external_style(css_filename, instance_title, None,
                                        preload_images)
    welcome_form += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" ' + \
        'action="/users/' + nickname + '/profiledata">\n'
    welcome_form += '<div class="container">' + welcome_text + '</div>\n'
    welcome_form += '  <div class="container next">\n'
    welcome_form += \
        '    <button type="submit" class="button" ' + \
        'name="previewAvatar">' + translate['Next'] + '</button>\n'
    welcome_form += '  </div>\n'
    welcome_form += '</div>\n'
    welcome_form += '</form>\n'
    welcome_form += html_footer()
    return welcome_form
