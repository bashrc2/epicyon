__filename__ = "webapp_tos.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
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

    tos_text = 'Terms of Service go here.'
    if os.path.isfile(base_dir + '/accounts/tos.md'):
        with open(base_dir + '/accounts/tos.md', 'r') as file:
            tos_text = markdown_to_html(file.read())

    tos_form = ''
    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    tos_form = \
        html_header_with_external_style(css_filename, instance_title, None)
    tos_form += '<div class="container">' + tos_text + '</div>\n'
    if admin_nickname:
        admin_actor = local_actor_url(http_prefix, admin_nickname, domain_full)
        tos_form += \
            '<div class="container"><center>\n' + \
            '<p class="administeredby">Administered by <a href="' + \
            admin_actor + '">' + admin_nickname + '</a></p>\n' + \
            '</center></div>\n'
    tos_form += html_footer()
    return tos_form
