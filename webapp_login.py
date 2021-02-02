__filename__ = "webapp_login.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
from shutil import copyfile
from utils import getConfigParam
from utils import noOfAccounts
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def htmlGetLoginCredentials(loginParams: str,
                            lastLoginTime: int) -> (str, str, bool):
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
        if '=' in arg:
            if arg.split('=', 1)[0] == 'username':
                nickname = arg.split('=', 1)[1]
            elif arg.split('=', 1)[0] == 'password':
                password = arg.split('=', 1)[1]
            elif arg.split('=', 1)[0] == 'register':
                register = True
    return nickname, password, register


def htmlLogin(cssCache: {}, translate: {},
              baseDir: str, autocomplete=True) -> str:
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
            translate['Please enter some credentials'] + '</p>'
        loginText += \
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
        translate['About this Instance'] + '</a></p>'
    TOSstr += \
        '<p class="login-text"><a href="/terms">' + \
        translate['Terms of Service'] + '</a></p>'

    loginButtonStr = ''
    if accounts > 0:
        loginButtonStr = \
            '<button type="submit" name="submit">' + \
            translate['Login'] + '</button>'

    autocompleteStr = ''
    if not autocomplete:
        autocompleteStr = 'autocomplete="off" value=""'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    loginForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    loginForm += '<br>\n'
    loginForm += '<form method="POST" action="/login">\n'
    loginForm += '  <div class="imgcontainer">\n'
    instanceTitle = getConfigParam(baseDir, 'instanceTitle')
    if not instanceTitle:
        instanceTitle = "Epicyon"
    loginForm += \
        '    <img loading="lazy" src="' + loginImage + \
        '" alt="' + instanceTitle + '" class="loginimage">\n'
    loginForm += loginText + TOSstr + '\n'
    loginForm += '  </div>\n'
    loginForm += '\n'
    loginForm += '  <div class="container">\n'
    loginForm += '    <label for="nickname"><b>' + \
        translate['Nickname'] + '</b></label>\n'
    loginForm += \
        '    <input type="text" ' + autocompleteStr + ' placeholder="' + \
        translate['Enter Nickname'] + '" name="username" required autofocus>\n'
    loginForm += '\n'
    loginForm += '    <label for="password"><b>' + \
        translate['Password'] + '</b></label>\n'
    loginForm += \
        '    <input type="password" ' + autocompleteStr + \
        ' placeholder="' + translate['Enter Password'] + \
        '" name="password" required>\n'
    loginForm += loginButtonStr + registerButtonStr + '\n'
    loginForm += '  </div>\n'
    loginForm += '</form>\n'
    loginForm += \
        '<a href="https://gitlab.com/bashrc2/epicyon">' + \
        '<img loading="lazy" class="license" title="' + \
        translate['Get the source code'] + '" alt="' + \
        translate['Get the source code'] + '" src="/icons/agpl.png" /></a>\n'
    loginForm += htmlFooter()
    return loginForm
