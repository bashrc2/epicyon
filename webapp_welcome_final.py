__filename__ = "webapp_welcome_final.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Onboarding"

import os
from shutil import copyfile
from utils import remove_html
from utils import get_config_param
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from markdown import markdown_to_html


def html_welcome_final(base_dir: str, nickname: str, domain: str,
                       http_prefix: str, domain_full: str,
                       language: str, translate: {},
                       theme_name: str) -> str:
    """Returns the final welcome screen after first login
    """
    # set a custom background for the welcome screen
    if os.path.isfile(base_dir + '/accounts/welcome-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/welcome-background.jpg'):
            copyfile(base_dir + '/accounts/welcome-background-custom.jpg',
                     base_dir + '/accounts/welcome-background.jpg')

    final_text = 'Welcome to Epicyon'
    final_filename = base_dir + '/accounts/welcome_final.md'
    if not os.path.isfile(final_filename):
        default_filename = None
        if theme_name:
            default_filename = \
                base_dir + '/theme/' + theme_name + '/welcome/' + \
                'final_' + language + '.md'
            if not os.path.isfile(default_filename):
                default_filename = None
        if not default_filename:
            default_filename = \
                base_dir + '/defaultwelcome/final_' + language + '.md'
        if not os.path.isfile(default_filename):
            default_filename = base_dir + '/defaultwelcome/final_en.md'
        copyfile(default_filename, final_filename)

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    if not instance_title:
        instance_title = 'Epicyon'

    if os.path.isfile(final_filename):
        with open(final_filename, 'r') as final_file:
            final_text = final_file.read()
            final_text = final_text.replace('INSTANCE', instance_title)
            final_text = markdown_to_html(remove_html(final_text))

    final_form = ''
    css_filename = base_dir + '/epicyon-welcome.css'
    if os.path.isfile(base_dir + '/welcome.css'):
        css_filename = base_dir + '/welcome.css'

    final_form = \
        html_header_with_external_style(css_filename, instance_title, None)

    final_form += \
        '<div class="container">' + final_text + '</div>\n' + \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" ' + \
        'action="/users/' + nickname + '/profiledata">\n' + \
        '<div class="container next">\n' + \
        '    <button type="submit" class="button" ' + \
        'name="previewAvatar">' + translate['Go Back'] + '</button>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="welcomeCompleteButton">' + translate['Next'] + '</button>\n' + \
        '</div>\n'

    final_form += '</form>\n'
    final_form += html_footer()
    return final_form
