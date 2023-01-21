__filename__ = "webapp_about.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
from utils import get_config_param
from webapp_utils import html_header_with_website_markup
from webapp_utils import html_footer
from markdown import markdown_to_html


def html_about(base_dir: str, http_prefix: str,
               domain_full: str, onion_domain: str, translate: {},
               system_language: str) -> str:
    """Show the about screen
    """
    admin_nickname = get_config_param(base_dir, 'admin')
    if not os.path.isfile(base_dir + '/accounts/about.md'):
        copyfile(base_dir + '/default_about.md',
                 base_dir + '/accounts/about.md')

    if os.path.isfile(base_dir + '/accounts/login-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/login-background.jpg'):
            copyfile(base_dir + '/accounts/login-background-custom.jpg',
                     base_dir + '/accounts/login-background.jpg')

    about_text = 'Information about this instance goes here.'
    if os.path.isfile(base_dir + '/accounts/about.md'):
        with open(base_dir + '/accounts/about.md', 'r',
                  encoding='utf-8') as fp_about:
            about_text = markdown_to_html(fp_about.read())

    about_form = ''
    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    about_form = \
        html_header_with_website_markup(css_filename, instance_title,
                                        http_prefix, domain_full,
                                        system_language)
    about_form += '<div class="container">' + about_text + '</div>'
    if onion_domain:
        about_form += \
            '<div class="container"><center>\n' + \
            '<p class="administeredby">' + \
            'http://' + onion_domain + '</p>\n</center></div>\n'
    if admin_nickname:
        admin_actor = '/users/' + admin_nickname
        about_form += \
            '<div class="container"><center>\n' + \
            '<p class="administeredby">' + \
            translate['Administered by'] + ' <a href="' + \
            admin_actor + '">' + admin_nickname + '</a>. ' + \
            translate['Version'] + ' ' + __version__ + \
            '</p>\n</center></div>\n'
    about_form += html_footer()
    return about_form
