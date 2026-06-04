__filename__ = "webapp_welcome_final.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Onboarding"

from shutil import copyfile
from src.utils import data_dir
from src.utils import remove_html
from src.utils import get_config_param
from src.webapp_utils import html_header_with_external_style
from src.webapp_utils import html_footer
from src.markdown import markdown_to_html
from src.data import load_string
from src.data import is_a_file


def html_welcome_final(base_dir: str, nickname: str,
                       language: str, translate: {},
                       theme_name: str) -> str:
    """Returns the final welcome screen after first login
    """
    # set a custom background for the welcome screen
    dir_str = data_dir(base_dir)
    if is_a_file(dir_str + '/welcome-background-custom.jpg'):
        if not is_a_file(dir_str + '/welcome-background.jpg'):
            copyfile(dir_str + '/welcome-background-custom.jpg',
                     dir_str + '/welcome-background.jpg')

    final_text = 'Welcome to Epicyon'
    final_filename = dir_str + '/welcome_final.md'
    if not is_a_file(final_filename):
        default_filename = None
        if theme_name:
            default_filename = \
                base_dir + '/theme/' + theme_name + '/welcome/' + \
                'final_' + language + '.md'
            if not is_a_file(default_filename):
                default_filename = None
        if not default_filename:
            default_filename = \
                base_dir + '/defaultwelcome/final_' + language + '.md'
        if not is_a_file(default_filename):
            default_filename = base_dir + '/defaultwelcome/final_en.md'
        copyfile(default_filename, final_filename)

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    if not instance_title:
        instance_title = 'Epicyon'

    if is_a_file(final_filename):
        final_text = load_string(final_filename,
                                 'EX: html_welcome_final unable to read ' +
                                 final_filename)
        if final_text is not None:
            final_text = final_text.replace('INSTANCE', instance_title)
            final_text = markdown_to_html(remove_html(final_text))
        else:
            final_text: str = ''

    final_form: str = ''
    css_filename = base_dir + '/epicyon-welcome.css'
    if is_a_file(base_dir + '/welcome.css'):
        css_filename = base_dir + '/welcome.css'

    preload_images: list[str] = []
    final_form = \
        html_header_with_external_style(css_filename, instance_title, None,
                                        preload_images)

    final_form += \
        '<div class="container">' + final_text + '</div>\n' + \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" ' + \
        'action="/users/' + nickname + '/profiledata">\n' + \
        '<div class="container next">\n' + \
        '    <button type="submit" class="button" ' + \
        'name="previewAvatar">' + translate['Go Back'] + '</button>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="welcomeCompleteButton">' + translate['Next'] + '</button>\n' + \
        '</div>\n'

    final_form += '</form>\n'
    final_form += html_footer()
    return final_form
