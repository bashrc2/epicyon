__filename__ = "webapp_about.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

from shutil import copyfile
from src.utils import data_dir
from src.utils import get_config_param
from src.webapp_utils import html_header_with_website_markup
from src.webapp_utils import html_footer
from src.markdown import markdown_to_html
from src.data import load_string
from src.data import is_a_file


def html_about(base_dir: str, http_prefix: str,
               domain_full: str, onion_domain: str, translate: {},
               system_language: str) -> str:
    """Show the about screen
    """
    admin_nickname = get_config_param(base_dir, 'admin')
    dir_str = data_dir(base_dir)
    if not is_a_file(dir_str + '/about.md'):
        copyfile(base_dir + '/default_about.md',
                 dir_str + '/about.md')

    if is_a_file(dir_str + '/login-background-custom.jpg'):
        if not is_a_file(dir_str + '/login-background.jpg'):
            copyfile(dir_str + '/login-background-custom.jpg',
                     dir_str + '/login-background.jpg')

    about_text = 'Information about this instance goes here.'
    if is_a_file(dir_str + '/about.md'):
        about_text = load_string(dir_str + '/about.md',
                                 'EX: html_about unable to read ' +
                                 dir_str + '/about.md')
        if about_text:
            about_text = markdown_to_html(about_text)

    about_form: str = ''
    css_filename = base_dir + '/epicyon-profile.css'
    if is_a_file(base_dir + '/epicyon.css'):
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
