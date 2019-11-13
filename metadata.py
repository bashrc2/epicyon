__filename__ = "metadata.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import json
import commentjson

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

def metaDataInstance(instanceTitle: str, \
                     instanceDescriptionShort: str, \
                     instanceDescription: str, \
                     httpPrefix: str,baseDir: str, \
                     adminNickname: str,domain: str,domainFull: str, \
                     registration: bool,systemLanguage: str, \
                     version: str) -> {}:
    """ /api/v1/instance endpoint
    """
    adminActorFilename=baseDir+'/accounts/'+adminNickname+'@'+domain+'.json'
    if not os.path.isfile(adminActorFilename):
        return {}

    adminActor=None
    try:
        with open(adminActorFilename, 'r') as fp:
            adminActor=commentjson.load(fp)                
    except:
        print('WARN: commentjson exception metaDataInstance')

    if not adminActor:
        return {}

    instance = {
        'approval_required': False,
        'contact_account': {'acct': adminActor['preferredUsername'],
                            'avatar': adminActor['icon']['url'],
                            'avatar_static': adminActor['icon']['url'],
                            'bot': False,
                            'created_at': '2019-07-01T10:30:00Z',
                            'display_name': adminActor['name'],
                            'emojis': [],
                            'fields': [],
                            'followers_count': 1,
                            'following_count': 1,
                            'header': adminActor['image']['url'],
                            'header_static': adminActor['image']['url'],
                            'id': '1',
                            'last_status_at': '2019-07-01T10:30:00Z',
                            'locked': adminActor['manuallyApprovesFollowers'],
                            'note': '<p>Admin of '+domain+'</p>',
                            'statuses_count': 1,
                            'url': httpPrefix+'://'+domainFull+'/@'+adminActor['preferredUsername'],
                            'username': adminActor['preferredUsername']
        },
        'description': instanceDescription,
        'email': 'admin@'+domain,
        'languages': [systemLanguage],
        'registrations': registration,
        'short_description': instanceDescriptionShort,
        'stats': {
            'domain_count': 1,
            'status_count': 1,
            'user_count': 1
        },
        'thumbnail': httpPrefix+'://'+domainFull+'/login.png',
        'title': instanceTitle,
        'uri': domainFull,
        'urls': {},
        'version': version
    }
    
    return instance
