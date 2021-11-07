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
from utils import removeHtml
from utils import getConfigParam
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from markdown import markdownToHtml


def htmlWelcomeFinal(baseDir: str, nickname: str, domain: str,
                     httpPrefix: str, domainFull: str,
                     language: str, translate: {},
                     themeName: str) -> str:
    """Returns the final welcome screen after first login
    """
    # set a custom background for the welcome screen
    if os.path.isfile(baseDir + '/accounts/welcome-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/welcome-background.jpg'):
            copyfile(baseDir + '/accounts/welcome-background-custom.jpg',
                     baseDir + '/accounts/welcome-background.jpg')

    finalText = 'Welcome to Epicyon'
    finalFilename = baseDir + '/accounts/welcome_final.md'
    if not os.path.isfile(finalFilename):
        defaultFilename = None
        if themeName:
            defaultFilename = \
                baseDir + '/theme/' + themeName + '/welcome/' + \
                'final_' + language + '.md'
            if not os.path.isfile(defaultFilename):
                defaultFilename = None
        if not defaultFilename:
            defaultFilename = \
                baseDir + '/defaultwelcome/final_' + language + '.md'
        if not os.path.isfile(defaultFilename):
            defaultFilename = baseDir + '/defaultwelcome/final_en.md'
        copyfile(defaultFilename, finalFilename)

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    if not instanceTitle:
        instanceTitle = 'Epicyon'

    if os.path.isfile(finalFilename):
        with open(finalFilename, 'r') as finalFile:
            finalText = finalFile.read()
            finalText = finalText.replace('INSTANCE', instanceTitle)
            finalText = markdownToHtml(removeHtml(finalText))

    finalForm = ''
    cssFilename = baseDir + '/epicyon-welcome.css'
    if os.path.isfile(baseDir + '/welcome.css'):
        cssFilename = baseDir + '/welcome.css'

    finalForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

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
    finalForm += htmlFooter()
    return finalForm
