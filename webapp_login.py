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
from utils import get_config_param
from utils import no_of_accounts
from utils import get_nickname_validation_pattern
from webapp_utils import set_custom_background
from webapp_utils import html_header_with_website_markup
from webapp_utils import html_footer
from webapp_utils import html_keyboard_navigation
from theme import get_text_mode_logo


def html_get_login_credentials(loginParams: str,
                               last_login_time: int,
                               domain: str) -> (str, str, bool):
    """Receives login credentials via HTTPServer POST
    """
    if not loginParams.startswith('username='):
        return None, None, None
    # minimum time between login attempts
    curr_time = int(time.time())
    if curr_time < last_login_time+10:
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


def html_login(css_cache: {}, translate: {},
               base_dir: str,
               http_prefix: str, domain: str,
               system_language: str,
               autocomplete: bool) -> str:
    """Shows the login screen
    """
    accounts = no_of_accounts(base_dir)

    loginImage = 'login.png'
    loginImageFilename = None
    if os.path.isfile(base_dir + '/accounts/' + loginImage):
        loginImageFilename = base_dir + '/accounts/' + loginImage
    elif os.path.isfile(base_dir + '/accounts/login.jpg'):
        loginImage = 'login.jpg'
        loginImageFilename = base_dir + '/accounts/' + loginImage
    elif os.path.isfile(base_dir + '/accounts/login.jpeg'):
        loginImage = 'login.jpeg'
        loginImageFilename = base_dir + '/accounts/' + loginImage
    elif os.path.isfile(base_dir + '/accounts/login.gif'):
        loginImage = 'login.gif'
        loginImageFilename = base_dir + '/accounts/' + loginImage
    elif os.path.isfile(base_dir + '/accounts/login.svg'):
        loginImage = 'login.svg'
        loginImageFilename = base_dir + '/accounts/' + loginImage
    elif os.path.isfile(base_dir + '/accounts/login.webp'):
        loginImage = 'login.webp'
        loginImageFilename = base_dir + '/accounts/' + loginImage
    elif os.path.isfile(base_dir + '/accounts/login.avif'):
        loginImage = 'login.avif'
        loginImageFilename = base_dir + '/accounts/' + loginImage

    if not loginImageFilename:
        loginImageFilename = base_dir + '/accounts/' + loginImage
        copyfile(base_dir + '/img/login.png', loginImageFilename)

    textModeLogo = get_text_mode_logo(base_dir)
    textModeLogoHtml = html_keyboard_navigation(textModeLogo, {}, {})

    set_custom_background(base_dir, 'login-background-custom',
                          'login-background')

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
    if os.path.isfile(base_dir + '/accounts/login.txt'):
        # custom login message
        with open(base_dir + '/accounts/login.txt', 'r') as file:
            loginText = '<p class="login-text">' + file.read() + '</p>'

    cssFilename = base_dir + '/epicyon-login.css'
    if os.path.isfile(base_dir + '/login.css'):
        cssFilename = base_dir + '/login.css'

    # show the register button
    registerButtonStr = ''
    if get_config_param(base_dir, 'registration') == 'open':
        if int(get_config_param(base_dir, 'registrationsRemaining')) > 0:
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
        get_config_param(base_dir, 'instanceTitle')
    loginForm = \
        html_header_with_website_markup(cssFilename, instanceTitle,
                                        http_prefix, domain,
                                        system_language)

    nicknamePattern = get_nickname_validation_pattern()
    instanceTitle = get_config_param(base_dir, 'instanceTitle')
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
    loginForm += html_footer()
    return loginForm
