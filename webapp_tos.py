__filename__ = "webapp_tos.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
from utils import getConfigParam
from utils import localActorUrl
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from markdown import markdownToHtml


def htmlTermsOfService(cssCache: {}, base_dir: str,
                       httpPrefix: str, domainFull: str) -> str:
    """Show the terms of service screen
    """
    adminNickname = getConfigParam(base_dir, 'admin')
    if not os.path.isfile(base_dir + '/accounts/tos.md'):
        copyfile(base_dir + '/default_tos.md',
                 base_dir + '/accounts/tos.md')

    if os.path.isfile(base_dir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/login-background.jpg'):
            copyfile(base_dir + '/accounts/login-background-custom.jpg',
                     base_dir + '/accounts/login-background.jpg')

    TOSText = 'Terms of Service go here.'
    if os.path.isfile(base_dir + '/accounts/tos.md'):
        with open(base_dir + '/accounts/tos.md', 'r') as file:
            TOSText = markdownToHtml(file.read())

    TOSForm = ''
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(base_dir, 'instanceTitle')
    TOSForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    TOSForm += '<div class="container">' + TOSText + '</div>\n'
    if adminNickname:
        adminActor = localActorUrl(httpPrefix, adminNickname, domainFull)
        TOSForm += \
            '<div class="container"><center>\n' + \
            '<p class="administeredby">Administered by <a href="' + \
            adminActor + '">' + adminNickname + '</a></p>\n' + \
            '</center></div>\n'
    TOSForm += htmlFooter()
    return TOSForm
