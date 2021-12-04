__filename__ = "webapp_themeDesigner.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from utils import loadJson
from utils import getConfigParam
from utils import acctDir
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def htmlThemeDesigner(cssCache: {}, baseDir: str,
                      nickname: str, domain: str,
                      translate: {}, defaultTimeline: str,
                      themeName: str) -> str:
    """Edit theme settings
    """
    themeFilename = \
        acctDir(baseDir, nickname, domain) + '/theme/' + \
        themeName + '/theme.json'
    themeJson = {}
    if os.path.isfile(themeFilename):
        themeJson = loadJson(themeFilename)

    themeForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    themeForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    themeForm += '<div class="container">\n'

    themeForm += \
        '    <h1>' + translate['Theme Designer'] + '</h1>\n'

    themeForm += '  <form method="POST" action="' + \
        '/users/' + nickname + '/changeThemeSettings">\n'

    for variableName, value in themeJson.items():
        if variableName.endswith('-color') or \
           variableName.endswith('-text'):
            themeForm += \
                '<p><label class="labels">' + \
                variableName.replace('-', ' ') + '</label>'
            themeForm += \
                '<input type="color" name="themeSetting_' + \
                variableName + '" value="' + str(value) + '"></p>'

    themeForm += '  </form>\n'
    themeForm += '</div>\n'
    themeForm += htmlFooter()
    return themeForm
