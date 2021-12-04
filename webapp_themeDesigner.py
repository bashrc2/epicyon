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
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import getBannerFile


def htmlThemeDesigner(cssCache: {}, baseDir: str,
                      nickname: str, domain: str,
                      translate: {}, defaultTimeline: str,
                      themeName: str, accessKeys: {}) -> str:
    """Edit theme settings
    """
    themeFilename = baseDir + '/theme/' + themeName + '/theme.json'
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
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, themeName)
    themeForm += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" ' + \
        'accesskey="' + accessKeys['menuTimeline'] + '">' + \
        '<img loading="lazy" class="timeline-banner" ' + \
        'title="' + translate['Switch to timeline view'] + '" ' + \
        'alt="' + translate['Switch to timeline view'] + '" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" /></a>\n'
    themeForm += '<div class="container">\n'

    themeForm += \
        '    <h1>' + translate['Theme Designer'] + '</h1>\n'

    themeForm += '  <form method="POST" action="' + \
        '/users/' + nickname + '/changeThemeSettings">\n'

    themeForm += '    <table class="accesskeys">\n'
    themeForm += '      <colgroup>\n'
    themeForm += '        <col span="1" class="accesskeys-left">\n'
    themeForm += '        <col span="1" class="accesskeys-center">\n'
    themeForm += '      </colgroup>\n'
    themeForm += '      <tbody>\n'

    for variableName, value in themeJson.items():
        if variableName.endswith('-color') or \
           variableName.endswith('-text'):
            themeForm += \
                '      <tr><td><label class="labels">' + \
                variableName.replace('-', ' ') + '</label></td>'
            themeForm += \
                '<td><input type="color" name="themeSetting_' + \
                variableName + '" value="' + str(value) + \
                '"></p></td></tr>\n'

    themeForm += '    </table>\n'
    themeForm += '  </form>\n'
    themeForm += '</div>\n'
    themeForm += htmlFooter()
    return themeForm
