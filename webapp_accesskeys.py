__filename__ = "webapp_accesskeys.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson
from utils import getConfigParam
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def loadAccessKeysForAccounts(baseDir: str, keyShortcuts: {}) -> None:
    """Loads key shortcuts for each account
    """
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if 'inbox@' in acct or 'news@' in acct:
                continue
            accountDir = os.path.join(baseDir + '/accounts', acct)
            accessKeysFilename = accountDir + '/accessKeys.json'
            if not os.path.isfile(accessKeysFilename):
                continue
            nickname = acct.split('@')[0]
            accessKeys = loadJson(accessKeysFilename)
            if accessKeys:
                keyShortcuts[nickname] = accessKeys
        break


def htmlAccessKeys(cssCache: {}, baseDir: str,
                   nickname: str, domain: str,
                   translate: {}, accessKeys: {},
                   defaultAccessKeys: {}) -> str:
    """Show and edit key shortcuts
    """
    accessKeysFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/accessKeys.json'
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
    accessKeysForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    accessKeysForm += '<div class="container">\n'

    accessKeysForm += \
        '    <h1>' + translate['Key Shortcuts'] + '</h1>\n'

    accessKeysForm += '  <form method="POST" action="' + \
        '/users/' + nickname + '/changeAccessKeys">\n'

    accessKeysForm += \
        '    <center>' + \
        '<button type="submit" class="button" name="submitAccessKeys">' + \
        translate['Submit'] + '</button></center>\n'

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
        keyStr += \
            '<td><input type="text" value="' + key + '" style="width:1ch">'
        keyStr += '</td></tr>'
        accessKeysForm += keyStr

    accessKeysForm += '      </tbody>\n'
    accessKeysForm += '    </table>\n'
    accessKeysForm += '  </form>\n'
    accessKeysForm += '</div>\n'
    accessKeysForm += htmlFooter()
    return accessKeysForm
