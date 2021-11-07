__filename__ = "webapp_accesskeys.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Accessibility"

import os
from utils import isAccountDir
from utils import loadJson
from utils import getConfigParam
from utils import acctDir
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def loadAccessKeysForAccounts(baseDir: str, keyShortcuts: {},
                              accessKeysTemplate: {}) -> None:
    """Loads key shortcuts for each account
    """
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for acct in dirs:
            if not isAccountDir(acct):
                continue
            accountDir = os.path.join(baseDir + '/accounts', acct)
            accessKeysFilename = accountDir + '/accessKeys.json'
            if not os.path.isfile(accessKeysFilename):
                continue
            nickname = acct.split('@')[0]
            accessKeys = loadJson(accessKeysFilename)
            if accessKeys:
                keyShortcuts[nickname] = accessKeysTemplate.copy()
                for variableName, key in accessKeysTemplate.items():
                    if accessKeys.get(variableName):
                        keyShortcuts[nickname][variableName] = \
                            accessKeys[variableName]
        break


def htmlAccessKeys(cssCache: {}, baseDir: str,
                   nickname: str, domain: str,
                   translate: {}, accessKeys: {},
                   defaultAccessKeys: {},
                   defaultTimeline: str) -> str:
    """Show and edit key shortcuts
    """
    accessKeysFilename = \
        acctDir(baseDir, nickname, domain) + '/accessKeys.json'
    if os.path.isfile(accessKeysFilename):
        accessKeysFromFile = loadJson(accessKeysFilename)
        if accessKeysFromFile:
            accessKeys = accessKeysFromFile

    accessKeysForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    accessKeysForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    accessKeysForm += '<div class="container">\n'

    accessKeysForm += \
        '    <h1>' + translate['Key Shortcuts'] + '</h1>\n'
    accessKeysForm += \
        '<p>' + translate['These access keys may be used'] + \
        '<label class="labels"></label></p>'

    accessKeysForm += '  <form method="POST" action="' + \
        '/users/' + nickname + '/changeAccessKeys">\n'

    timelineKey = accessKeys['menuTimeline']
    submitKey = accessKeys['submitButton']
    accessKeysForm += \
        '    <center>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="submitAccessKeysCancel" accesskey="' + timelineKey + '">' + \
        translate['Go Back'] + '</button>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="submitAccessKeys" accesskey="' + submitKey + '">' + \
        translate['Submit'] + '</button>\n    </center>\n'

    accessKeysForm += '    <table class="accesskeys">\n'
    accessKeysForm += '      <colgroup>\n'
    accessKeysForm += '        <col span="1" class="accesskeys-left">\n'
    accessKeysForm += '        <col span="1" class="accesskeys-center">\n'
    accessKeysForm += '      </colgroup>\n'
    accessKeysForm += '      <tbody>\n'

    for variableName, key in defaultAccessKeys.items():
        if not translate.get(variableName):
            continue
        keyStr = '<tr>'
        keyStr += \
            '<td><label class="labels">' + \
            translate[variableName] + '</label></td>'
        if accessKeys.get(variableName):
            key = accessKeys[variableName]
        if len(key) > 1:
            key = key[0]
        keyStr += \
            '<td><input type="text" ' + \
            'name="' + variableName.replace(' ', '_') + '" ' + \
            'value="' + key + '">'
        keyStr += '</td></tr>\n'
        accessKeysForm += keyStr

    accessKeysForm += '      </tbody>\n'
    accessKeysForm += '    </table>\n'
    accessKeysForm += '  </form>\n'
    accessKeysForm += '</div>\n'
    accessKeysForm += htmlFooter()
    return accessKeysForm
