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


def isWelcomeScreenComplete(baseDir: str, nickname: str, domain: str) -> bool:
    """Returns true if the welcome screen is complete for the given account
    """
    accountPath = baseDir + '/accounts/' + nickname + '@' + domain
    if not os.path.isdir(accountPath):
        return
    completeFilename = accountPath + '/.welcome_complete'
    return os.path.isfile(completeFilename)


def welcomeScreenIsComplete(baseDir: str, nickname: str, domain: str) -> None:
    """Indicates that the welcome screen has been shown for a given account
    """
    accountPath = baseDir + '/accounts/' + nickname + '@' + domain
    if not os.path.isdir(accountPath):
        return
    completeFilename = accountPath + '/.welcome_complete'
    completeFile = open(completeFilename, 'w+')
    if completeFile:
        completeFile.write('\n')
        completeFile.close()


def htmlWelcomeScreen(baseDir: str,
                      language: str, translate: {}) -> str:
    """Returns the welcome screen
    """
    # set a custom background for the welcome screen
    if os.path.isfile(baseDir + '/accounts/welcome-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/welcome-background.jpg'):
            copyfile(baseDir + '/accounts/welcome-background-custom.jpg',
                     baseDir + '/accounts/welcome-background.jpg')

    welcomeText = 'Welcome to Epicyon'
    welcomeFilename = baseDir + '/accounts/welcome.md'
    if not os.path.isfile(welcomeFilename):
        defaultFilename = baseDir + '/defaultwelcome/' + language + '.md'
        if os.path.isfile(defaultFilename):
            copyfile(defaultFilename, welcomeFilename)
    if os.path.isfile(welcomeFilename):
        with open(baseDir + '/accounts/welcome.md', 'r') as welcomeFile:
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
    welcomeForm += '    <a href="/welcome_profile">'
    welcomeForm += '      <button>' + translate['Next'] + '</button></a>\n'
    welcomeForm += '  </div>\n'
    welcomeForm += '</div>\n'
    welcomeForm += htmlFooter()
    return welcomeForm
