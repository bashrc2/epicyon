__filename__ = "webapp_accesskeys.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Accessibility"

import os
from utils import is_account_dir
from utils import load_json
from utils import get_config_param
from utils import acct_dir
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer


def load_access_keys_for_accounts(base_dir: str, keyShortcuts: {},
                                  access_keysTemplate: {}) -> None:
    """Loads key shortcuts for each account
    """
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            accountDir = os.path.join(base_dir + '/accounts', acct)
            access_keysFilename = accountDir + '/access_keys.json'
            if not os.path.isfile(access_keysFilename):
                continue
            nickname = acct.split('@')[0]
            access_keys = load_json(access_keysFilename)
            if access_keys:
                keyShortcuts[nickname] = access_keysTemplate.copy()
                for variableName, key in access_keysTemplate.items():
                    if access_keys.get(variableName):
                        keyShortcuts[nickname][variableName] = \
                            access_keys[variableName]
        break


def html_access_keys(css_cache: {}, base_dir: str,
                     nickname: str, domain: str,
                     translate: {}, access_keys: {},
                     defaultAccessKeys: {},
                     default_timeline: str) -> str:
    """Show and edit key shortcuts
    """
    access_keysFilename = \
        acct_dir(base_dir, nickname, domain) + '/access_keys.json'
    if os.path.isfile(access_keysFilename):
        access_keysFromFile = load_json(access_keysFilename)
        if access_keysFromFile:
            access_keys = access_keysFromFile

    access_keysForm = ''
    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    access_keysForm = \
        html_header_with_external_style(css_filename, instanceTitle, None)
    access_keysForm += '<div class="container">\n'

    access_keysForm += \
        '    <h1>' + translate['Key Shortcuts'] + '</h1>\n'
    access_keysForm += \
        '<p>' + translate['These access keys may be used'] + \
        '<label class="labels"></label></p>'

    access_keysForm += '  <form method="POST" action="' + \
        '/users/' + nickname + '/changeAccessKeys">\n'

    timelineKey = access_keys['menuTimeline']
    submitKey = access_keys['submitButton']
    access_keysForm += \
        '    <center>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="submitAccessKeysCancel" accesskey="' + timelineKey + '">' + \
        translate['Go Back'] + '</button>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="submitAccessKeys" accesskey="' + submitKey + '">' + \
        translate['Submit'] + '</button>\n    </center>\n'

    access_keysForm += '    <table class="accesskeys">\n'
    access_keysForm += '      <colgroup>\n'
    access_keysForm += '        <col span="1" class="accesskeys-left">\n'
    access_keysForm += '        <col span="1" class="accesskeys-center">\n'
    access_keysForm += '      </colgroup>\n'
    access_keysForm += '      <tbody>\n'

    for variableName, key in defaultAccessKeys.items():
        if not translate.get(variableName):
            continue
        keyStr = '<tr>'
        keyStr += \
            '<td><label class="labels">' + \
            translate[variableName] + '</label></td>'
        if access_keys.get(variableName):
            key = access_keys[variableName]
        if len(key) > 1:
            key = key[0]
        keyStr += \
            '<td><input type="text" ' + \
            'name="' + variableName.replace(' ', '_') + '" ' + \
            'value="' + key + '">'
        keyStr += '</td></tr>\n'
        access_keysForm += keyStr

    access_keysForm += '      </tbody>\n'
    access_keysForm += '    </table>\n'
    access_keysForm += '  </form>\n'
    access_keysForm += '</div>\n'
    access_keysForm += html_footer()
    return access_keysForm
