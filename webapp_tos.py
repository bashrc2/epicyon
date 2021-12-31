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
from utils import get_config_param
from utils import local_actor_url
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from markdown import markdown_to_html


def html_terms_of_service(css_cache: {}, base_dir: str,
                          http_prefix: str, domain_full: str) -> str:
    """Show the terms of service screen
    """
    admin_nickname = get_config_param(base_dir, 'admin')
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
            TOSText = markdown_to_html(file.read())

    TOSForm = ''
    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    TOSForm = \
        html_header_with_external_style(css_filename, instanceTitle, None)
    TOSForm += '<div class="container">' + TOSText + '</div>\n'
    if admin_nickname:
        adminActor = local_actor_url(http_prefix, admin_nickname, domain_full)
        TOSForm += \
            '<div class="container"><center>\n' + \
            '<p class="administeredby">Administered by <a href="' + \
            adminActor + '">' + admin_nickname + '</a></p>\n' + \
            '</center></div>\n'
    TOSForm += html_footer()
    return TOSForm
