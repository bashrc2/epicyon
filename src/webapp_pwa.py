__filename__ = "webapp_pwa.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

from src.utils import remove_html
from src.data import load_string
from src.data import is_a_file


def _get_variable_from_css(css_str: str, variable: str) -> str:
    """Gets a variable value from the css file text
    """
    if '--' + variable + ':' not in css_str:
        return None
    value: str = css_str.split('--' + variable + ':')[1]
    if ';' in value:
        value = value.split(';')[0].strip()
    value = remove_html(value)
    if ' ' in value:
        value = None
    return value


def get_pwa_theme_colors(css_filename: str) -> (str, str):
    """Gets the theme/statusbar color for progressive web apps
    """
    default_pwa_theme_color: str = 'apple-mobile-web-app-status-bar-style'
    pwa_theme_color: str = default_pwa_theme_color

    default_pwa_theme_background_color: str = 'black-translucent'
    pwa_theme_background_color: str = default_pwa_theme_background_color

    if not is_a_file(css_filename):
        return pwa_theme_color, pwa_theme_background_color

    css_str: str = load_string(css_filename,
                               'EX: get_pwa_theme_colors unable to read ' +
                               css_filename)
    if css_str is None:
        css_str: str = ''

    pwa_theme_color = \
        _get_variable_from_css(css_str, 'pwa-theme-color')
    if not pwa_theme_color:
        pwa_theme_color = default_pwa_theme_color

    pwa_theme_background_color = \
        _get_variable_from_css(css_str, 'pwa-theme-background-color')
    if not pwa_theme_background_color:
        pwa_theme_background_color = default_pwa_theme_background_color

    return pwa_theme_color, pwa_theme_background_color


def pwa_manifest(base_dir: str) -> {}:
    """Returns progressive web app manifest
    """
    css_filename: str = base_dir + '/epicyon.css'
    pwa_theme_color, pwa_theme_background_color = \
        get_pwa_theme_colors(css_filename)

    app1: str = "https://f-droid.org/en/packages/eu.siacs.conversations"
    app2: str = "https://staging.f-droid.org/en/packages/im.vector.app"
    app3: str = \
        "https://f-droid.org/en/packages/" + \
        "com.stoutner.privacybrowser.standard"
    return {
        "name": "Epicyon",
        "short_name": "Epicyon",
        "start_url": "/index.html",
        "display": "standalone",
        "background_color": pwa_theme_background_color,
        "theme_color": pwa_theme_color,
        "orientation": "portrait-primary",
        "categories": ["microblog", "fediverse", "activitypub"],
        "screenshots": [
            {
                "src": "/mobile.jpg",
                "sizes": "418x851",
                "type": "image/jpeg"
            },
            {
                "src": "/mobile_person.jpg",
                "sizes": "429x860",
                "type": "image/jpeg"
            },
            {
                "src": "/mobile_search.jpg",
                "sizes": "422x861",
                "type": "image/jpeg"
            }
        ],
        "icons": [
            {
                "src": "/logo72.png",
                "type": "image/png",
                "sizes": "72x72"
            },
            {
                "src": "/logo96.png",
                "type": "image/png",
                "sizes": "96x96"
            },
            {
                "src": "/logo128.png",
                "type": "image/png",
                "sizes": "128x128"
            },
            {
                "src": "/logo144.png",
                "type": "image/png",
                "sizes": "144x144"
            },
            {
                "src": "/logo150.png",
                "type": "image/png",
                "sizes": "150x150"
            },
            {
                "src": "/apple-touch-icon.png",
                "type": "image/png",
                "sizes": "180x180"
            },
            {
                "src": "/logo192.png",
                "type": "image/png",
                "sizes": "192x192"
            },
            {
                "src": "/logo256.png",
                "type": "image/png",
                "sizes": "256x256"
            },
            {
                "src": "/logo512.png",
                "type": "image/png",
                "sizes": "512x512"
            }
        ],
        "related_applications": [
            {
                "platform": "fdroid",
                "url": app1
            },
            {
                "platform": "fdroid",
                "url": app2
            },
            {
                "platform": "fdroid",
                "url": app3
            }
        ],
        "protocol_handlers": [
            {
                "protocol": "web+ap",
                "url": "?target=%s"
            },
            {
                "protocol": "web+epicyon",
                "url": "?target=%s"
            }
        ]
    }
