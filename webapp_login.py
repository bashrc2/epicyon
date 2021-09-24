__filename__ = "webapp_login.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
import time
from shutil import copyfile
from utils import getConfigParam
from utils import noOfAccounts
from utils import getNicknameValidationPattern
from webapp_utils import htmlHeaderWithWebsiteMarkup
from webapp_utils import htmlFooter
from webapp_utils import htmlKeyboardNavigation
from theme import getTextModeLogo


def htmlGetLoginCredentials(loginParams: str,
                            lastLoginTime: int,
                            domain: str) -> (str, str, bool):
    """Receives login credentials via HTTPServer POST
    """
    if not loginParams.startswith('username='):
        return None, None, None
    # minimum time between login attempts
    currTime = int(time.time())
    if currTime < lastLoginTime+10:
        return None, None, None
    if '&' not in loginParams:
        return None, None, None
    loginArgs = loginParams.split('&')
    nickname = None
    password = None
    register = False
    for arg in loginArgs:
        if '=' not in arg:
            continue
        if arg.split('=', 1)[0] == 'username':
            nickname = arg.split('=', 1)[1]
            if nickname.startswith('@'):
                nickname = nickname[1:]
            if '@' in nickname:
                # the full nickname@domain has been entered
                nickname = nickname.split('@')[0]
        elif arg.split('=', 1)[0] == 'password':
            password = arg.split('=', 1)[1]
        elif arg.split('=', 1)[0] == 'register':
            register = True
    return nickname, password, register


def htmlLogin(cssCache: {}, translate: {},
              baseDir: str,
              httpPrefix: str, domain: str,
              systemLanguage: str,
              autocomplete: bool) -> str:
    """Shows the login screen
    """
    accounts = noOfAccounts(baseDir)

    loginImage = 'login.png'
    loginImageFilename = None
    if os.path.isfile(baseDir + '/accounts/' + loginImage):
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.jpg'):
        loginImage = 'login.jpg'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.jpeg'):
        loginImage = 'login.jpeg'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.gif'):
        loginImage = 'login.gif'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.svg'):
        loginImage = 'login.svg'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.webp'):
        loginImage = 'login.webp'
        loginImageFilename = baseDir + '/accounts/' + loginImage
    elif os.path.isfile(baseDir + '/accounts/login.avif'):
        loginImage = 'login.avif'
        loginImageFilename = baseDir + '/accounts/' + loginImage

    if not loginImageFilename:
        loginImageFilename = baseDir + '/accounts/' + loginImage
        copyfile(baseDir + '/img/login.png', loginImageFilename)

    textModeLogo = getTextModeLogo(baseDir)
    textModeLogoHtml = htmlKeyboardNavigation(textModeLogo, {}, {})

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    if accounts > 0:
        loginText = \
            '<p class="login-text">' + \
            translate['Welcome. Please enter your login details below.'] + \
            '</p>'
    else:
        loginText = \
            '<p class="login-text">' + \
            translate['Please enter some credentials'] + '</p>' + \
            '<p class="login-text">' + \
            translate['You will become the admin of this site.'] + \
            '</p>'
    if os.path.isfile(baseDir + '/accounts/login.txt'):
        # custom login message
        with open(baseDir + '/accounts/login.txt', 'r') as file:
            loginText = '<p class="login-text">' + file.read() + '</p>'

    cssFilename = baseDir + '/epicyon-login.css'
    if os.path.isfile(baseDir + '/login.css'):
        cssFilename = baseDir + '/login.css'

    # show the register button
    registerButtonStr = ''
    if getConfigParam(baseDir, 'registration') == 'open':
        if int(getConfigParam(baseDir, 'registrationsRemaining')) > 0:
            if accounts > 0:
                idx = 'Welcome. Please login or register a new account.'
                loginText = \
                    '<p class="login-text">' + \
                    translate[idx] + \
                    '</p>'
            registerButtonStr = \
                '<button type="submit" name="register">Register</button>'

    TOSstr = \
        '<p class="login-text"><a href="/about">' + \
        translate['About this Instance'] + '</a></p>' + \
        '<p class="login-text"><a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>'

    loginButtonStr = ''
    if accounts > 0:
        loginButtonStr = \
            '<button type="submit" name="submit">' + \
            translate['Login'] + '</button>'

    autocompleteNicknameStr = 'autocomplete="username"'
    autocompletePasswordStr = 'autocomplete="current-password"'
    if not autocomplete:
        autocompleteNicknameStr = 'autocomplete="username" value=""'
        autocompletePasswordStr = 'autocomplete="off" value=""'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    loginForm = \
        htmlHeaderWithWebsiteMarkup(cssFilename, instanceTitle,
                                    httpPrefix, domain,
                                    systemLanguage)
    nicknamePattern = getNicknameValidationPattern()
    instanceTitle = getConfigParam(baseDir, 'instanceTitle')
    loginForm += \
        '<br>\n' + \
        '<form method="POST" action="/login">\n' + \
        '  <div class="imgcontainer">\n' + \
        textModeLogoHtml + '\n' + \
        '    <img loading="lazy" src="' + loginImage + \
        '" alt="' + instanceTitle + '" class="loginimage">\n' + \
        loginText + TOSstr + '\n' + \
        '  </div>\n' + \
        '\n' + \
        '  <div class="container">\n' + \
        '    <label for="nickname"><b>' + \
        translate['Nickname'] + '</b></label>\n' + \
        '    <input type="text" ' + autocompleteNicknameStr + \
        ' placeholder="' + translate['Enter Nickname'] + '" ' + \
        'pattern="' + nicknamePattern + '" name="username" ' + \
        'required autofocus>\n' + \
        '\n' + \
        '    <label for="password"><b>' + \
        translate['Password'] + '</b></label>\n' + \
        '    <input type="password" ' + autocompletePasswordStr + \
        ' placeholder="' + translate['Enter Password'] + '" ' + \
        'pattern="{8,256}" name="password" required>\n' + \
        loginButtonStr + registerButtonStr + '\n' + \
        '  </div>\n' + \
        '</form>\n' + \
        '<a href="https://gitlab.com/bashrc2/epicyon">' + \
        '<img loading="lazy" class="license" title="' + \
        translate['Get the source code'] + '" alt="' + \
        translate['Get the source code'] + '" src="/icons/agpl.png" /></a>\n'
    loginForm += htmlFooter()
    return loginForm
