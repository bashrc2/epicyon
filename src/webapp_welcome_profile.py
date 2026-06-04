__filename__ = "webapp_welcome_profile.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Onboarding"

from shutil import copyfile
from src.utils import replace_strings
from src.utils import data_dir
from src.utils import remove_html
from src.utils import load_json
from src.utils import get_config_param
from src.utils import acct_dir
from src.utils import local_actor_url
from src.formats import get_image_formats
from src.formats import get_image_extensions
from src.webapp_utils import html_header_with_external_style
from src.webapp_utils import html_footer
from src.webapp_utils import edit_text_field
from src.markdown import markdown_to_html
from src.data import load_string
from src.data import is_a_file


def html_welcome_profile(base_dir: str, nickname: str, domain: str,
                         http_prefix: str, domain_full: str,
                         language: str, translate: {},
                         theme_name: str) -> str:
    """Returns the welcome profile screen to set avatar and bio
    """
    # set a custom background for the welcome screen
    dir_str = data_dir(base_dir)
    if is_a_file(dir_str + '/welcome-background-custom.jpg'):
        if not is_a_file(dir_str + '/welcome-background.jpg'):
            copyfile(dir_str + '/welcome-background-custom.jpg',
                     dir_str + '/welcome-background.jpg')

    profile_text = 'Welcome to Epicyon'
    profile_filename = dir_str + '/welcome_profile.md'
    if not is_a_file(profile_filename):
        default_filename = None
        if theme_name:
            default_filename = \
                base_dir + '/theme/' + theme_name + '/welcome/' + \
                'profile_' + language + '.md'
            if not is_a_file(default_filename):
                default_filename = None
        if not default_filename:
            default_filename = \
                base_dir + '/defaultwelcome/profile_' + language + '.md'
        if not is_a_file(default_filename):
            default_filename = base_dir + '/defaultwelcome/profile_en.md'
        copyfile(default_filename, profile_filename)

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    if not instance_title:
        instance_title = 'Epicyon'

    if is_a_file(profile_filename):
        profile_text = load_string(profile_filename,
                                   'EX: html_welcome_profile unable to read ' +
                                   profile_filename)
        if profile_text is not None:
            profile_text = profile_text.replace('INSTANCE', instance_title)
            profile_text = markdown_to_html(remove_html(profile_text))
        else:
            profile_text: str = ''

    profile_form: str = ''
    css_filename = base_dir + '/epicyon-welcome.css'
    if is_a_file(base_dir + '/welcome.css'):
        css_filename = base_dir + '/welcome.css'

    preload_images: list[str] = []
    profile_form = \
        html_header_with_external_style(css_filename, instance_title, None,
                                        preload_images)

    # get the url of the avatar
    ext = 'png'
    for ext in get_image_extensions():
        avatar_filename = \
            acct_dir(base_dir, nickname, domain) + '/avatar.' + ext
        if is_a_file(avatar_filename):
            break
    avatar_url = \
        local_actor_url(http_prefix, nickname, domain_full) + \
        '/avatar.' + ext

    image_formats = get_image_formats()
    profile_form += '<div class="container">' + profile_text + '</div>\n'
    profile_form += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" ' + \
        'action="/users/' + nickname + '/profiledata">\n'
    profile_form += '<div class="container">\n'
    profile_form += '  <center>\n'
    profile_form += '    <img class="welcomeavatar" src="'
    profile_form += avatar_url + '"><br>\n'
    profile_form += '    <input type="file" id="avatar" name="avatar" '
    profile_form += 'accept="' + image_formats + '">\n'
    profile_form += '  </center>\n'
    profile_form += '</div>\n'

    profile_form += '<center>\n'
    profile_form += \
        '  <button type="submit" class="button" ' + \
        'name="previewAvatar">' + translate['Preview'] + '</button> '
    profile_form += '</center>\n'

    actor_filename = acct_dir(base_dir, nickname, domain) + '.json'
    actor_json = load_json(actor_filename)
    display_nickname = actor_json['name']
    profile_form += '<div class="container">\n'
    profile_form += \
        edit_text_field(translate['Nickname'], 'displayNickname',
                        display_nickname)

    bio_str: str = ''
    if actor_json.get('summary'):
        replacements = {
            '<p>': '',
            '</p>': ''
        }
        bio_str = replace_strings(actor_json['summary'], replacements)
    if not bio_str:
        bio_str = translate['Your bio']
    profile_form += '  <label class="labels">' + \
        translate['Your bio'] + '</label><br>\n'
    profile_form += '  <textarea id="message" name="bio" ' + \
        'style="height:130px" spellcheck="true">' + \
        bio_str + '</textarea>\n'
    profile_form += '</div>\n'

    profile_form += '<div class="container next">\n'
    profile_form += \
        '    <button type="submit" class="button" ' + \
        'name="initialWelcomeScreen">' + translate['Go Back'] + '</button> '
    profile_form += \
        '    <button type="submit" class="button" ' + \
        'name="finalWelcomeScreen">' + translate['Next'] + '</button>\n'
    profile_form += '</div>\n'

    profile_form += '</form>\n'
    profile_form += html_footer()
    return profile_form
