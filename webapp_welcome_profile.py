__filename__ = "webapp_welcome_profile.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from utils import getConfigParam
from utils import getImageExtensions
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import markdownToHtml


def htmlWelcomeProfile(baseDir: str, nickname: str, domain: str,
                       httpPrefix: str, domainFull: str,
                       language: str, translate: {},
                       prevScreen='welcome') -> str:
    """Returns the welcome profile screen to set avatar and bio
    """
    # set a custom background for the welcome screen
    if os.path.isfile(baseDir + '/accounts/welcome-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/welcome-background.jpg'):
            copyfile(baseDir + '/accounts/welcome-background-custom.jpg',
                     baseDir + '/accounts/welcome-background.jpg')

    profileText = 'Welcome to Epicyon'
    profileFilename = baseDir + '/accounts/welcome_profile.md'
    if not os.path.isfile(profileFilename):
        defaultFilename = \
            baseDir + '/defaultwelcome/profile_' + language + '.md'
        if not os.path.isfile(defaultFilename):
            defaultFilename = baseDir + '/defaultwelcome/profile_en.md'
        copyfile(defaultFilename, profileFilename)
    if os.path.isfile(profileFilename):
        with open(profileFilename, 'r') as profileFile:
            profileText = markdownToHtml(profileFile.read())

    profileForm = ''
    cssFilename = baseDir + '/epicyon-welcome.css'
    if os.path.isfile(baseDir + '/welcome.css'):
        cssFilename = baseDir + '/welcome.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    profileForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    # get the url of the avatar
    for ext in getImageExtensions():
        avatarFilename = \
            baseDir + '/accounts/' + nickname + '@' + domain + '/avatar.' + ext
        if os.path.isfile(avatarFilename):
            break
    avatarUrl = \
        httpPrefix + '://' + domainFull + \
        '/users/' + nickname + '/avatar.' + ext

    profileForm += '<center>\n'
    profileForm += '<img class="welcomeavatar" src="' + avatarUrl + '">\n'
    profileForm += '</center>\n'
    profileForm += '<div class="container">' + profileText + '</div>\n'
    profileForm += '  <div class="container next">\n'
    profileForm += '    <a href="/' + prevScreen + '">\n'
    profileForm += '      <button>' + translate['Go Back'] + '</button></a>\n'
    profileForm += '    <a href="/welcome_complete">\n'
    profileForm += '      <button>' + translate['Next'] + '</button></a>\n'
    profileForm += '  </div>\n'
    profileForm += '</div>\n'
    profileForm += htmlFooter()
    return profileForm
