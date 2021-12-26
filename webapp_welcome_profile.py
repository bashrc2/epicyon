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
from utils import get_config_param
from utils import get_image_extensions
from utils import getImageFormats
from utils import acct_dir
from utils import local_actor_url
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import editTextField
from markdown import markdownToHtml


def htmlWelcomeProfile(base_dir: str, nickname: str, domain: str,
                       http_prefix: str, domain_full: str,
                       language: str, translate: {},
                       theme_name: str) -> str:
    """Returns the welcome profile screen to set avatar and bio
    """
    # set a custom background for the welcome screen
    if os.path.isfile(base_dir + '/accounts/welcome-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/welcome-background.jpg'):
            copyfile(base_dir + '/accounts/welcome-background-custom.jpg',
                     base_dir + '/accounts/welcome-background.jpg')

    profileText = 'Welcome to Epicyon'
    profileFilename = base_dir + '/accounts/welcome_profile.md'
    if not os.path.isfile(profileFilename):
        defaultFilename = None
        if theme_name:
            defaultFilename = \
                base_dir + '/theme/' + theme_name + '/welcome/' + \
                'profile_' + language + '.md'
            if not os.path.isfile(defaultFilename):
                defaultFilename = None
        if not defaultFilename:
            defaultFilename = \
                base_dir + '/defaultwelcome/profile_' + language + '.md'
        if not os.path.isfile(defaultFilename):
            defaultFilename = base_dir + '/defaultwelcome/profile_en.md'
        copyfile(defaultFilename, profileFilename)

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    if not instanceTitle:
        instanceTitle = 'Epicyon'

    if os.path.isfile(profileFilename):
        with open(profileFilename, 'r') as profileFile:
            profileText = profileFile.read()
            profileText = profileText.replace('INSTANCE', instanceTitle)
            profileText = markdownToHtml(removeHtml(profileText))

    profileForm = ''
    cssFilename = base_dir + '/epicyon-welcome.css'
    if os.path.isfile(base_dir + '/welcome.css'):
        cssFilename = base_dir + '/welcome.css'

    profileForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

    # get the url of the avatar
    for ext in get_image_extensions():
        avatarFilename = \
            acct_dir(base_dir, nickname, domain) + '/avatar.' + ext
        if os.path.isfile(avatarFilename):
            break
    avatarUrl = \
        local_actor_url(http_prefix, nickname, domain_full) + '/avatar.' + ext

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

    actorFilename = acct_dir(base_dir, nickname, domain) + '.json'
    actor_json = loadJson(actorFilename)
    displayNickname = actor_json['name']
    profileForm += '<div class="container">\n'
    profileForm += \
        editTextField(translate['Nickname'], 'displayNickname',
                      displayNickname)

    bioStr = \
        actor_json['summary'].replace('<p>', '').replace('</p>', '')
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
