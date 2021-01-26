__filename__ = "webapp_tos.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from utils import getConfigParam
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def htmlTermsOfService(cssCache: {}, baseDir: str,
                       httpPrefix: str, domainFull: str) -> str:
    """Show the terms of service screen
    """
    adminNickname = getConfigParam(baseDir, 'admin')
    if not os.path.isfile(baseDir + '/accounts/tos.txt'):
        copyfile(baseDir + '/default_tos.txt',
                 baseDir + '/accounts/tos.txt')

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    TOSText = 'Terms of Service go here.'
    if os.path.isfile(baseDir + '/accounts/tos.txt'):
        with open(baseDir + '/accounts/tos.txt', 'r') as file:
            TOSText = file.read()

    TOSForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    TOSForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    TOSForm += '<div class="container">' + TOSText + '</div>\n'
    if adminNickname:
        adminActor = httpPrefix + '://' + domainFull + \
            '/users/' + adminNickname
        TOSForm += \
            '<div class="container"><center>\n' + \
            '<p class="administeredby">Administered by <a href="' + \
            adminActor + '">' + adminNickname + '</a></p>\n' + \
            '</center></div>\n'
    TOSForm += htmlFooter()
    return TOSForm
