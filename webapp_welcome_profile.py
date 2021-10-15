__filename__ = "webapp_welcome_profile.py"
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
from utils import loadJson
from utils import getConfigParam
from utils import getImageExtensions
from utils import getImageFormats
from utils import acctDir
from utils import localActorUrl
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import editTextField
from markdown import markdownToHtml


def htmlWelcomeProfile(baseDir: str, nickname: str, domain: str,
                       httpPrefix: str, domainFull: str,
                       language: str, translate: {},
                       themeName: str) -> str:
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
        defaultFilename = None
        if themeName:
            defaultFilename = \
                baseDir + '/theme/' + themeName + '/welcome/' + \
                'profile_' + language + '.md'
            if not os.path.isfile(defaultFilename):
                defaultFilename = None
        if not defaultFilename:
            defaultFilename = \
                baseDir + '/defaultwelcome/profile_' + language + '.md'
        if not os.path.isfile(defaultFilename):
            defaultFilename = baseDir + '/defaultwelcome/profile_en.md'
        copyfile(defaultFilename, profileFilename)

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    if not instanceTitle:
        instanceTitle = 'Epicyon'

    if os.path.isfile(profileFilename):
        with open(profileFilename, 'r') as profileFile:
            profileText = profileFile.read()
            profileText = profileText.replace('INSTANCE', instanceTitle)
            profileText = markdownToHtml(removeHtml(profileText))

    profileForm = ''
    cssFilename = baseDir + '/epicyon-welcome.css'
    if os.path.isfile(baseDir + '/welcome.css'):
        cssFilename = baseDir + '/welcome.css'

    profileForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    # get the url of the avatar
    for ext in getImageExtensions():
        avatarFilename = \
            acctDir(baseDir, nickname, domain) + '/avatar.' + ext
        if os.path.isfile(avatarFilename):
            break
    avatarUrl = \
        localActorUrl(httpPrefix, nickname, domainFull) + '/avatar.' + ext

    imageFormats = getImageFormats()
    profileForm += '<div class="container">' + profileText + '</div>\n'
    profileForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" ' + \
        'action="/users/' + nickname + '/profiledata">\n'
    profileForm += '<div class="container">\n'
    profileForm += '  <center>\n'
    profileForm += '    <img class="welcomeavatar" src="'
    profileForm += avatarUrl + '"><br>\n'
    profileForm += '    <input type="file" id="avatar" name="avatar" '
    profileForm += 'accept="' + imageFormats + '">\n'
    profileForm += '  </center>\n'
    profileForm += '</div>\n'

    profileForm += '<center>\n'
    profileForm += \
        '  <button type="submit" class="button" ' + \
        'name="previewAvatar">' + translate['Preview'] + '</button> '
    profileForm += '</center>\n'

    actorFilename = acctDir(baseDir, nickname, domain) + '.json'
    actorJson = loadJson(actorFilename)
    displayNickname = actorJson['name']
    profileForm += '<div class="container">\n'
    profileForm += \
        editTextField(translate['Nickname'], 'displayNickname',
                      displayNickname)

    bioStr = \
        actorJson['summary'].replace('<p>', '').replace('</p>', '')
    if not bioStr:
        bioStr = translate['Your bio']
    profileForm += '  <label class="labels">' + \
        translate['Your bio'] + '</label><br>\n'
    profileForm += '  <textarea id="message" name="bio" ' + \
        'style="height:130px" spellcheck="true">' + \
        bioStr + '</textarea>\n'
    profileForm += '</div>\n'

    profileForm += '<div class="container next">\n'
    profileForm += \
        '    <button type="submit" class="button" ' + \
        'name="initialWelcomeScreen">' + translate['Go Back'] + '</button> '
    profileForm += \
        '    <button type="submit" class="button" ' + \
        'name="finalWelcomeScreen">' + translate['Next'] + '</button>\n'
    profileForm += '</div>\n'

    profileForm += '</form>\n'
    profileForm += htmlFooter()
    return profileForm
