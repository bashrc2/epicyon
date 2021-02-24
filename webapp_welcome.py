__filename__ = "webapp_welcome.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from utils import getConfigParam
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import markdownToHtml


def welcomeScreenShown(baseDir: str, nickname: str, domain: str):
    """Indicates that the welcome screen has been shown for a given account
    """
    shownFilename = baseDir + '/accounts/.welcome_shown'
    shownFile = open(shownFilename, 'w+')
    if shownFile:
        shownFile.write('\n')
        shownFile.close()


def htmlWelcomeScreen(baseDir: str, nickname: str, domain: str,
                      language: str, translate: {}) -> str:
    """Returns the welcome screen
    """
    # set a custom background for the welcome screen
    if os.path.isfile(baseDir + '/accounts/welcome-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/welcome-background.jpg'):
            copyfile(baseDir + '/accounts/welcome-background-custom.jpg',
                     baseDir + '/accounts/welcome-background.jpg')

    welcomeText = 'Welcome to Epicyon'
    welcomeFilename = baseDir + '/accounts/welcome.txt'
    if not os.path.isfile(welcomeFilename):
        defaultFilename = baseDir + '/defaultwelcome/' + language + '.txt'
        if os.path.isfile(defaultFilename):
            copyfile(defaultFilename, welcomeFilename)
    if os.path.isfile(welcomeFilename):
        with open(baseDir + '/accounts/welcome.txt', 'r') as welcomeFile:
            welcomeText = markdownToHtml(welcomeFile.read())

    welcomeForm = ''
    cssFilename = baseDir + '/epicyon-welcome.css'
    if os.path.isfile(baseDir + '/welcome.css'):
        cssFilename = baseDir + '/welcome.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    welcomeForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    welcomeForm += '<div class="container">' + welcomeText + '</div>\n'
    welcomeForm += '  <div class="container next">\n'
    welcomeForm += '    <button type="submit" name="submit">' + \
        translate['Next'] + '</button>\n'
    welcomeForm += '  </div>\n'
    welcomeForm += '</div>\n'
    welcomeForm += htmlFooter()
    return welcomeForm
