__filename__ = "webapp_login.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
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
from webapp_utils import text_mode_browser
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
    login_args = loginParams.split('&')
    nickname = None
    password = None
    register = False
    for arg in login_args:
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


def html_login(translate: {},
               base_dir: str,
               http_prefix: str, domain: str,
               system_language: str,
               autocomplete: bool,
               ua_str: str) -> str:
    """Shows the login screen
    """
    accounts = no_of_accounts(base_dir)

    login_image = 'login.png'
    login_image_filename = None
    if os.path.isfile(base_dir + '/accounts/' + login_image):
        login_image_filename = base_dir + '/accounts/' + login_image
    elif os.path.isfile(base_dir + '/accounts/login.jpg'):
        login_image = 'login.jpg'
        login_image_filename = base_dir + '/accounts/' + login_image
    elif os.path.isfile(base_dir + '/accounts/login.jpeg'):
        login_image = 'login.jpeg'
        login_image_filename = base_dir + '/accounts/' + login_image
    elif os.path.isfile(base_dir + '/accounts/login.gif'):
        login_image = 'login.gif'
        login_image_filename = base_dir + '/accounts/' + login_image
    elif os.path.isfile(base_dir + '/accounts/login.svg'):
        login_image = 'login.svg'
        login_image_filename = base_dir + '/accounts/' + login_image
    elif os.path.isfile(base_dir + '/accounts/login.webp'):
        login_image = 'login.webp'
        login_image_filename = base_dir + '/accounts/' + login_image
    elif os.path.isfile(base_dir + '/accounts/login.avif'):
        login_image = 'login.avif'
        login_image_filename = base_dir + '/accounts/' + login_image
    elif os.path.isfile(base_dir + '/accounts/login.jxl'):
        login_image = 'login.jxl'
        login_image_filename = base_dir + '/accounts/' + login_image

    if not login_image_filename:
        login_image_filename = base_dir + '/accounts/' + login_image
        copyfile(base_dir + '/img/login.png', login_image_filename)

    text_mode_logo = get_text_mode_logo(base_dir)
    text_mode_logo_html = html_keyboard_navigation(text_mode_logo, {}, {})

    set_custom_background(base_dir, 'login-background-custom',
                          'login-background')

    if accounts > 0:
        login_text = \
            '<p class="login-text">' + \
            translate['Welcome. Please enter your login details below.'] + \
            '</p>'
    else:
        login_text = \
            '<p class="login-text">' + \
            translate['Please enter some credentials'] + '</p>' + \
            '<p class="login-text">' + \
            translate['You will become the admin of this site.'] + \
            '</p>'
    if os.path.isfile(base_dir + '/accounts/login.txt'):
        # custom login message
        with open(base_dir + '/accounts/login.txt', 'r',
                  encoding='utf-8') as file:
            login_text = '<p class="login-text">' + file.read() + '</p>'

    css_filename = base_dir + '/epicyon-login.css'
    if os.path.isfile(base_dir + '/login.css'):
        css_filename = base_dir + '/login.css'

    # show the register button
    register_button_str = ''
    if get_config_param(base_dir, 'registration') == 'open':
        if int(get_config_param(base_dir, 'registrationsRemaining')) > 0:
            if accounts > 0:
                idx = 'Welcome. Please login or register a new account.'
                login_text = \
                    '<p class="login-text">' + \
                    translate[idx] + \
                    '</p>'
            register_button_str = \
                '<button type="submit" name="register" tabindex="1">' + \
                translate['Register'] + '</button>'

    tos_str = \
        '<p class="login-text"><a href="/about" tabindex="2">' + \
        translate['About this Instance'] + '</a></p>' + \
        '<p class="login-text"><a href="/terms" tabindex="2">' + \
        translate['Terms of Service'] + '</a></p>'

    login_button_str = ''
    if accounts > 0:
        login_button_str = \
            '<button type="submit" name="submit" tabindex="1">' + \
            translate['Login'] + '</button>'

    autocomplete_nickname_str = 'autocomplete="username"'
    autocomplete_password_str = 'autocomplete="current-password"'
    if not autocomplete:
        autocomplete_nickname_str = 'autocomplete="username" value=""'
        autocomplete_password_str = 'autocomplete="off" value=""'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    login_form = \
        html_header_with_website_markup(css_filename, instance_title,
                                        http_prefix, domain,
                                        system_language)

    nickname_pattern = get_nickname_validation_pattern()
    instance_title = get_config_param(base_dir, 'instanceTitle')
    login_form += \
        '<br>\n' + \
        '<form method="POST" action="/login">\n' + \
        '  <div class="imgcontainer">\n' + \
        text_mode_logo_html + '\n' + \
        '    <img loading="lazy" decoding="async" src="' + login_image + \
        '" alt="' + instance_title + '" class="loginimage">\n' + \
        login_text + tos_str + '\n' + \
        '  </div>\n' + \
        '\n' + \
        '  <div class="container">\n' + \
        '    <label for="nickname"><b>' + \
        translate['Nickname'] + '</b></label>\n' + \
        '    <input type="text" ' + autocomplete_nickname_str + \
        ' placeholder="' + translate['Enter Nickname'] + '" ' + \
        'pattern="' + nickname_pattern + '" name="username" tabindex="1" ' + \
        'required autofocus>'
    in_text_mode = text_mode_browser(ua_str)
    if in_text_mode:
        login_form += '<br>'
    login_form += \
        '\n\n' + \
        '    <label for="password"><b>' + \
        translate['Password'] + '</b></label>\n' + \
        '    <input type="password" ' + autocomplete_password_str + \
        ' placeholder="' + translate['Enter Password'] + '" ' + \
        'pattern="{8,256}" name="password" tabindex="1" required>'
    if in_text_mode:
        login_form += '<br><br>'
    login_form += \
        '\n' + login_button_str + register_button_str + '\n' + \
        '  </div>\n' + \
        '</form>\n' + \
        '<a href="https://gitlab.com/bashrc2/epicyon" tabindex="2">' + \
        '<img loading="lazy" decoding="async" class="license" title="' + \
        translate['Get the source code'] + '" alt="' + \
        translate['Get the source code'] + '" src="/icons/agpl.png" /></a>\n'
    login_form += html_footer()
    return login_form
