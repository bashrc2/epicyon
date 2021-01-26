__filename__ = "metadata.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson
from utils import noOfAccounts
from utils import noOfActiveAccountsMonthly


def metaDataNodeInfo(baseDir: str, registration: bool, version: str) -> {}:
    """ /nodeinfo/2.0 endpoint
    """
    activeAccounts = noOfAccounts(baseDir)
    activeAccountsMonthly = noOfActiveAccountsMonthly(baseDir, 1)
    activeAccountsHalfYear = noOfActiveAccountsMonthly(baseDir, 6)
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
                'activeHalfyear': activeAccountsHalfYear,
                'activeMonth': activeAccountsMonthly,
                'total': activeAccounts
            }
        },
        'version': '2.0'
    }
    return nodeinfo


def metaDataInstance(instanceTitle: str,
                     instanceDescriptionShort: str,
                     instanceDescription: str,
                     httpPrefix: str, baseDir: str,
                     adminNickname: str, domain: str, domainFull: str,
                     registration: bool, systemLanguage: str,
                     version: str) -> {}:
    """ /api/v1/instance endpoint
    """
    adminActorFilename = \
        baseDir + '/accounts/' + adminNickname + '@' + domain + '.json'
    if not os.path.isfile(adminActorFilename):
        return {}

    adminActor = loadJson(adminActorFilename, 0)
    if not adminActor:
        print('WARN: json load exception metaDataInstance')
        return {}

    isBot = False
    if adminActor['type'] != 'Person':
        isBot = True

    url = \
        httpPrefix + '://' + domainFull + '/@' + \
        adminActor['preferredUsername']

    instance = {
        'approval_required': False,
        'contact_account': {
            'acct': adminActor['preferredUsername'],
            'avatar': adminActor['icon']['url'],
            'avatar_static': adminActor['icon']['url'],
            'bot': isBot,
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
            'url': url,
            'username': adminActor['preferredUsername']
        },
        'description': instanceDescription,
        'email': 'admin@'+domain,
        'languages': [systemLanguage],
        'registrations': registration,
        'short_description': instanceDescriptionShort,
        'stats': {
            'domain_count': 2,
            'status_count': 1,
            'user_count': noOfAccounts(baseDir)
        },
        'thumbnail': httpPrefix+'://'+domainFull+'/login.png',
        'title': instanceTitle,
        'uri': domainFull,
        'urls': {},
        'version': version
    }

    return instance
