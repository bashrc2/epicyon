__filename__ = "webapp_about.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from utils import getCSS
from utils import getConfigParam
from webapp_utils import htmlHeader
from webapp_utils import htmlFooter


def htmlAbout(cssCache: {}, baseDir: str, httpPrefix: str,
              domainFull: str, onionDomain: str) -> str:
    """Show the about screen
    """
    adminNickname = getConfigParam(baseDir, 'admin')
    if not os.path.isfile(baseDir + '/accounts/about.txt'):
        copyfile(baseDir + '/default_about.txt',
                 baseDir + '/accounts/about.txt')

    if os.path.isfile(baseDir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/login-background.jpg'):
            copyfile(baseDir + '/accounts/login-background-custom.jpg',
                     baseDir + '/accounts/login-background.jpg')

    aboutText = 'Information about this instance goes here.'
    if os.path.isfile(baseDir + '/accounts/about.txt'):
        with open(baseDir + '/accounts/about.txt', 'r') as aboutFile:
            aboutText = aboutFile.read()

    aboutForm = ''
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    aboutCSS = getCSS(baseDir, cssFilename, cssCache)
    if aboutCSS:
        if httpPrefix != 'http':
            aboutCSS = aboutCSS.replace('https://',
                                        httpPrefix + '://')

        aboutForm = htmlHeader(cssFilename, aboutCSS)
        aboutForm += '<div class="container">' + aboutText + '</div>'
        if onionDomain:
            aboutForm += \
                '<div class="container"><center>\n' + \
                '<p class="administeredby">' + \
                'http://' + onionDomain + '</p>\n</center></div>\n'
        if adminNickname:
            adminActor = '/users/' + adminNickname
            aboutForm += \
                '<div class="container"><center>\n' + \
                '<p class="administeredby">Administered by <a href="' + \
                adminActor + '">' + adminNickname + '</a></p>\n' + \
                '</center></div>\n'
        aboutForm += htmlFooter()
    return aboutForm
