__filename__ = "webapp_welcome_final.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
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

    finalText = 'Welcome to Epicyon'
    finalFilename = base_dir + '/accounts/welcome_final.md'
    if not os.path.isfile(finalFilename):
        defaultFilename = None
        if theme_name:
            defaultFilename = \
                base_dir + '/theme/' + theme_name + '/welcome/' + \
                'final_' + language + '.md'
            if not os.path.isfile(defaultFilename):
                defaultFilename = None
        if not defaultFilename:
            defaultFilename = \
                base_dir + '/defaultwelcome/final_' + language + '.md'
        if not os.path.isfile(defaultFilename):
            defaultFilename = base_dir + '/defaultwelcome/final_en.md'
        copyfile(defaultFilename, finalFilename)

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    if not instanceTitle:
        instanceTitle = 'Epicyon'

    if os.path.isfile(finalFilename):
        with open(finalFilename, 'r') as finalFile:
            finalText = finalFile.read()
            finalText = finalText.replace('INSTANCE', instanceTitle)
            finalText = markdown_to_html(remove_html(finalText))

    finalForm = ''
    cssFilename = base_dir + '/epicyon-welcome.css'
    if os.path.isfile(base_dir + '/welcome.css'):
        cssFilename = base_dir + '/welcome.css'

    finalForm = \
        html_header_with_external_style(cssFilename, instanceTitle, None)

    finalForm += \
        '<div class="container">' + finalText + '</div>\n' + \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" ' + \
        'action="/users/' + nickname + '/profiledata">\n' + \
        '<div class="container next">\n' + \
        '    <button type="submit" class="button" ' + \
        'name="previewAvatar">' + translate['Go Back'] + '</button>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="welcomeCompleteButton">' + translate['Next'] + '</button>\n' + \
        '</div>\n'

    finalForm += '</form>\n'
    finalForm += html_footer()
    return finalForm
