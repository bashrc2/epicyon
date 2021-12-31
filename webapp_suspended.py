__filename__ = "webapp_suspended.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from utils import get_config_param
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer


def html_suspended(css_cache: {}, base_dir: str) -> str:
    """Show the screen for suspended accounts
    """
    suspendedForm = ''
    css_filename = base_dir + '/epicyon-suspended.css'
    if os.path.isfile(base_dir + '/suspended.css'):
        css_filename = base_dir + '/suspended.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    suspendedForm = \
        html_header_with_external_style(css_filename, instanceTitle, None)
    suspendedForm += \
        '<div><center>\n' + \
        '  <p class="screentitle">Account Suspended</p>\n' + \
        '  <p>See <a href="/terms">Terms of Service</a></p>\n' + \
        '</center></div>\n'
    suspendedForm += html_footer()
    return suspendedForm
