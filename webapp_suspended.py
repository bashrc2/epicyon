__filename__ = "webapp_suspended.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from utils import getConfigParam
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def htmlSuspended(cssCache: {}, base_dir: str) -> str:
    """Show the screen for suspended accounts
    """
    suspendedForm = ''
    cssFilename = base_dir + '/epicyon-suspended.css'
    if os.path.isfile(base_dir + '/suspended.css'):
        cssFilename = base_dir + '/suspended.css'

    instanceTitle = \
        getConfigParam(base_dir, 'instanceTitle')
    suspendedForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    suspendedForm += \
        '<div><center>\n' + \
        '  <p class="screentitle">Account Suspended</p>\n' + \
        '  <p>See <a href="/terms">Terms of Service</a></p>\n' + \
        '</center></div>\n'
    suspendedForm += htmlFooter()
    return suspendedForm
