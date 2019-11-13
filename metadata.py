__filename__ = "metadata.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json

def metaDataNodeInfo(registration: bool,version: str) -> {}:
    """ /nodeinfo/2.0 endpoint
    """
    nodeinfo = {
        'openRegistrations': registration,
        'protocols': ['activitypub'],
        'software': {
            'name': 'epicyon',
            'version': version
        },
        'usage': {
            'localPosts': 1,
            'users': {
                'activeHalfyear': 1,
                'activeMonth': 1,
                'total': 1
            }
        },
        'version': '2.0'
    }
    return nodeinfo
