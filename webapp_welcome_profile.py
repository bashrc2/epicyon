__filename__ = "webapp_welcome_profile.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from utils import loadJson
from utils import getConfigParam
from utils import getImageExtensions
from utils import getImageFormats
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import markdownToHtml


def htmlWelcomeProfile(baseDir: str, nickname: str, domain: str,
                       httpPrefix: str, domainFull: str,
                       language: str, translate: {}) -> str:
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

    imageFormats = getImageFormats()
    profileForm += '<div class="container">' + profileText + '</div>\n'    
    profileForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" ' + \
        'action="/users/' + nickname + '/welcomeprofile">\n'    
    profileForm += '<center>\n'
    profileForm += '  <img class="welcomeavatar" src="'
    profileForm += avatarUrl + '"><br>\n'
    profileForm += '  <input type="file" id="avatar" name="avatar" '
    profileForm += 'accept="' + imageFormats + '">\n'

    profileForm += '</center>\n'

    actorFilename = baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    actorJson = loadJson(actorFilename)
    displayNickname = actorJson['name']
    profileForm += '  <label class="labels">' + \
        translate['Nickname'] + '</label><br>\n'
    profileForm += '  <input type="text" name="displayNickname" value="' + \
        displayNickname + '"><br>\n'

    bioStr = \
        actorJson['summary'].replace('<p>', '').replace('</p>', '')
    profileForm += '  <label class="labels">' + \
        translate['Your bio'] + '</label><br>\n'
    profileForm += '  <textarea id="message" name="bio" ' + \
        'style="height:200px">' + bioStr + '</textarea>\n'

    profileForm += '  <div class="container next">\n'
    profileForm += \
        '    <button type="submit" class="button" ' + \
        'name="prevWelcomeScreen">' + translate['Go Back'] + '</button>\n'
    profileForm += \
        '    <button type="submit" class="button" ' + \
        'name="nextWelcomeScreen">' + translate['Next'] + '</button>\n'
    profileForm += '  </div>\n'

    profileForm += '</form>\n'
    profileForm += htmlFooter()
    return profileForm
