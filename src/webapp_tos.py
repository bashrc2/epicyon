__filename__ = "webapp_tos.py"
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
from src.utils import local_actor_url
from src.webapp_utils import html_header_with_external_style
from src.webapp_utils import html_footer
from src.markdown import markdown_to_html
from src.data import load_string
from src.data import is_a_file


def html_terms_of_service(base_dir: str,
                          http_prefix: str, domain_full: str) -> str:
    """Show the terms of service screen
    """
    admin_nickname = get_config_param(base_dir, 'admin')
    dir_str = data_dir(base_dir)
    if not is_a_file(dir_str + '/tos.md'):
        copyfile(base_dir + '/default_tos.md',
                 dir_str + '/tos.md')

    if is_a_file(dir_str + '/login-background-custom.jpg'):
        if not is_a_file(dir_str + '/login-background.jpg'):
            copyfile(dir_str + '/login-background-custom.jpg',
                     dir_str + '/login-background.jpg')

    tos_text = 'Terms of Service go here.'
    if is_a_file(dir_str + '/tos.md'):
        tos_text_str = \
            load_string(dir_str + '/tos.md',
                        'EX: html_terms_of_service unable to read ' +
                        dir_str + '/tos.md')
        if tos_text_str:
            tos_text = markdown_to_html(tos_text_str)

    tos_form: str = ''
    css_filename = base_dir + '/epicyon-profile.css'
    if is_a_file(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    preload_images: list[str] = []
    tos_form = \
        html_header_with_external_style(css_filename, instance_title, None,
                                        preload_images)
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
