__filename__ = "webapp_podcast.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface Columns"

import os
import html
import urllib.parse
from shutil import copyfile
from utils import get_config_param
from utils import remove_html
from media import path_is_audio
from content import safe_web_text
from webapp_utils import get_broken_link_substitute
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_utils import html_keyboard_navigation


def _html_podcast_performers(podcast_properties: {}) -> str:
    """Returns html for performers of a podcast
    """
    if not podcast_properties:
        return ''
    if not podcast_properties.get('persons'):
        return ''

    # list of performers
    podcast_str = '<div class="performers">\n'
    podcast_str += '  <center>\n'
    podcast_str += '<ul>\n'
    for performer in podcast_properties['persons']:
        if not performer.get('text'):
            continue
        performer_name = performer['text']
        performer_title = performer_name

        if performer.get('role'):
            performer_title += ' (' + performer['role'] + ')'
        if performer.get('group'):
            performer_title += ', <i>' + performer['group'] + '</i>'
        performer_title = remove_html(performer_title)

        performer_url = ''
        if performer.get('href'):
            performer_url = performer['href']

        performer_img = ''
        if performer.get('img'):
            performer_img = performer['img']

        podcast_str += '  <li>\n'
        podcast_str += '    <figure>\n'
        podcast_str += '      <a href="' + performer_url + '">\n'
        podcast_str += \
            '        <img loading="lazy" src="' + performer_img + \
            '" alt="" />\n'
        podcast_str += \
            '      <figcaption>' + performer_title + '</figcaption>\n'
        podcast_str += '      </a>\n'
        podcast_str += '    </figure>\n'
        podcast_str += '  </li>\n'

    podcast_str += '</ul>\n'
    podcast_str += '</div>\n'
    return podcast_str


def _html_podcast_soundbites(link_url: str, extension: str,
                             podcast_properties: {},
                             translate: {}) -> str:
    """Returns html for podcast soundbites
    """
    if not podcast_properties:
        return ''
    if not podcast_properties.get('soundbites'):
        return ''

    podcast_str = '<div class="performers">\n'
    podcast_str += '  <center>\n'
    podcast_str += '<ul>\n'
    ctr = 1
    for performer in podcast_properties['soundbites']:
        if not performer.get('startTime'):
            continue
        if not performer['startTime'].isdigit():
            continue
        if not performer.get('duration'):
            continue
        if not performer['duration'].isdigit():
            continue
        end_time = str(float(performer['startTime']) +
                       float(performer['duration']))

        podcast_str += '  <li>\n'
        preview_url = \
            link_url + '#t=' + performer['startTime'] + ',' + end_time
        soundbite_title = translate['Preview']
        if ctr > 0:
            soundbite_title += ' ' + str(ctr)
        podcast_str += \
            '    <audio controls>\n' + \
            '    <p>' + soundbite_title + '</p>\n' + \
            '    <source src="' + preview_url + '" type="audio/' + \
            extension.replace('.', '') + '">' + \
            translate['Your browser does not support the audio element.'] + \
            '</audio>\n'
        podcast_str += '  </li>\n'
        ctr += 1

    podcast_str += '</ul>\n'
    podcast_str += '</div>\n'
    return podcast_str


def html_podcast_episode(css_cache: {}, translate: {},
                         base_dir: str, nickname: str, domain: str,
                         newswire_item: [], theme: str,
                         default_timeline: str,
                         text_mode_banner: str, access_keys: {}) -> str:
    """Returns html for a podcast episode, giebn an item from the newswire
    """
    css_filename = base_dir + '/epicyon-podcast.css'
    if os.path.isfile(base_dir + '/podcast.css'):
        css_filename = base_dir + '/podcast.css'

    if os.path.isfile(base_dir + '/accounts/podcast-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/podcast-background.jpg'):
            copyfile(base_dir + '/accounts/podcast-background.jpg',
                     base_dir + '/accounts/podcast-background.jpg')

    instance_title = get_config_param(base_dir, 'instanceTitle')
    podcast_str = \
        html_header_with_external_style(css_filename, instance_title, None)

    podcast_properties = newswire_item[8]
    image_url = ''
    image_src = 'src'
    if podcast_properties.get('images'):
        if podcast_properties['images'].get('srcset'):
            image_url = podcast_properties['images']['srcset']
            image_src = 'srcset'
    if not image_url and podcast_properties.get('image'):
        image_url = podcast_properties['image']

    link_url = newswire_item[1]

    podcast_str += html_keyboard_navigation(text_mode_banner, {}, {})
    podcast_str += '<br><br>\n'
    podcast_str += '<div class="options">\n'
    podcast_str += '  <div class="optionsAvatar">\n'
    podcast_str += '  <center>\n'
    podcast_str += '  <a href="' + link_url + '">\n'
    if image_src == 'srcset':
        podcast_str += '  <img loading="lazy" srcset="' + image_url + \
            '" alt="" ' + get_broken_link_substitute() + '/></a>\n'
    else:
        podcast_str += '  <img loading="lazy" src="' + image_url + \
            '" alt="" ' + get_broken_link_substitute() + '/></a>\n'
    podcast_str += '  </center>\n'
    podcast_str += '  </div>\n'

    podcast_str += '  <center>\n'
    audio_extension = None
    if path_is_audio(link_url):
        if '.mp3' in link_url:
            audio_extension = 'mpeg'
        else:
            audio_extension = 'ogg'
    else:
        if podcast_properties.get('linkMimeType'):
            if 'audio' in podcast_properties['linkMimeType']:
                audio_extension = \
                    podcast_properties['linkMimeType'].split('/')[1]
    # show widgets for soundbites
    if audio_extension:
        podcast_str += _html_podcast_soundbites(link_url, audio_extension,
                                                podcast_properties,
                                                translate)

        # podcast player widget
        podcast_str += \
            '  <audio controls>\n' + \
            '    <source src="' + link_url + '" type="audio/' + \
            audio_extension.replace('.', '') + '">' + \
            translate['Your browser does not support the audio element.'] + \
            '\n  </audio>\n'
    elif podcast_properties.get('linkMimeType'):
        if '/youtube' in podcast_properties['linkMimeType']:
            video_site = 'https://www.youtube.com'
            url = link_url.replace('/watch?v=', '/embed/')
            if '&' in url:
                url = url.split('&')[0]
            if '?utm_' in url:
                url = url.split('?utm_')[0]
            podcast_str += \
                "  <iframe loading=\"lazy\" src=\"" + \
                url + "\" width=\"90%\" " + \
                "frameborder=\"0\" allow=\"autoplay; fullscreen\" " + \
                "allowfullscreen>\n  </iframe>\n"
        elif 'video' in podcast_properties['linkMimeType']:
            video_mime_type = podcast_properties['linkMimeType']
            video_msg = 'Your browser does not support the video element.'
            podcast_str += \
                '  <figure id="videoContainer" ' + \
                'data-fullscreen="false">\n' + \
                '    <video id="video" controls preload="metadata">\n' + \
                '<source src="' + link_url + '" ' + \
                'type="' + video_mime_type + '">' + \
                translate[video_msg] + '</video>\n  </figure>\n'

    podcast_title = \
        remove_html(html.unescape(urllib.parse.unquote_plus(newswire_item[0])))
    if podcast_title:
        podcast_str += \
            '<p><label class="podcast-title">' + podcast_title + \
            '</label></p>\n'
    if newswire_item[4]:
        podcast_description = \
            html.unescape(urllib.parse.unquote_plus(newswire_item[4]))
        podcast_description = safe_web_text(podcast_description)
        if podcast_description:
            podcast_str += '<p>' + podcast_description + '</p>\n'

    # donate button
    if podcast_properties.get('funding'):
        if podcast_properties['funding'].get('url'):
            donate_url = podcast_properties['funding']['url']
            podcast_str += \
                '<p><a href="' + donate_url + \
                '"><button class="donateButton">' + translate['Donate'] + \
                '</button></a></p>\n'

    if podcast_properties['categories']:
        podcast_str += '<p>'
        tags_str = ''
        for tag in podcast_properties['categories']:
            tag_link = '/users/' + nickname + '/tags/' + tag.replace('#', '')
            tags_str += '<a href="' + tag_link + '">' + tag + '</a> '
        podcast_str += tags_str.strip() + '</p>\n'

    podcast_str += _html_podcast_performers(podcast_properties)

    podcast_str += '  </center>\n'
    podcast_str += '</div>\n'

    podcast_str += html_footer()
    return podcast_str
