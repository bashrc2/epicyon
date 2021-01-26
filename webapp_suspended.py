__filename__ = "webapp_suspended.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import getConfigParam
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def htmlSuspended(cssCache: {}, baseDir: str) -> str:
    """Show the screen for suspended accounts
    """
    suspendedForm = ''
    cssFilename = baseDir + '/epicyon-suspended.css'
    if os.path.isfile(baseDir + '/suspended.css'):
        cssFilename = baseDir + '/suspended.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    suspendedForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    suspendedForm += '<div><center>\n'
    suspendedForm += '  <p class="screentitle">Account Suspended</p>\n'
    suspendedForm += '  <p>See <a href="/terms">Terms of Service</a></p>\n'
    suspendedForm += '</center></div>\n'
    suspendedForm += htmlFooter()
    return suspendedForm
