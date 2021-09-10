__filename__ = "metadata.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Metadata"

import os
from utils import isAccountDir
from utils import loadJson
from utils import noOfAccounts
from utils import noOfActiveAccountsMonthly


def _getStatusCount(baseDir: str) -> int:
    """Get the total number of posts
    """
    statusCtr = 0
    accountsDir = baseDir + '/accounts'
    for subdir, dirs, files in os.walk(accountsDir):
        for acct in dirs:
            if not isAccountDir(acct):
                continue
            acctDir = os.path.join(accountsDir, acct + '/outbox')
            for subdir2, dirs2, files2 in os.walk(acctDir):
                statusCtr += len(files2)
                break
        break
    return statusCtr


def metaDataNodeInfo(baseDir: str,
                     aboutUrl: str,
                     termsOfServiceUrl: str,
                     registration: bool, version: str,
                     showAccounts: bool) -> {}:
    """ /nodeinfo/2.0 endpoint
    Also see https://socialhub.activitypub.rocks/t/
    fep-f1d5-nodeinfo-in-fediverse-software/1190/4

    Note that there are security considerations with this. If an adversary
    sees a lot of accounts and "local" posts then the instance may be
    considered a higher priority target.
    Also exposure of the version number and number of accounts could be
    sensitive
    """
    if showAccounts:
        activeAccounts = noOfAccounts(baseDir)
        activeAccountsMonthly = noOfActiveAccountsMonthly(baseDir, 1)
        activeAccountsHalfYear = noOfActiveAccountsMonthly(baseDir, 6)
        localPosts = _getStatusCount(baseDir)
    else:
        activeAccounts = 1
        activeAccountsMonthly = 1
        activeAccountsHalfYear = 1
        localPosts = 1

    nodeinfo = {
        'openRegistrations': registration,
        'protocols': ['activitypub'],
        'software': {
            'name': 'epicyon',
            'version': version
        },
        'documents': {
            'about': aboutUrl,
            'terms': termsOfServiceUrl
        },
        'usage': {
            'localPosts': localPosts,
            'users': {
                'activeHalfyear': activeAccountsHalfYear,
                'activeMonth': activeAccountsMonthly,
                'total': activeAccounts
            }
        },
        'version': '2.0'
    }
    return nodeinfo


def metaDataInstance(showAccounts: bool,
                     instanceTitle: str,
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

    if showAccounts:
        activeAccounts = noOfAccounts(baseDir)
        localPosts = _getStatusCount(baseDir)
    else:
        activeAccounts = 1
        localPosts = 1

    instance = {
        'approval_required': False,
        'contact_account': {
            'acct': adminActor['preferredUsername'],
            'avatar': adminActor['icon']['url'],
            'avatar_static': adminActor['icon']['url'],
            'bot': isBot,
            'display_name': adminActor['name'],
            'header': adminActor['image']['url'],
            'header_static': adminActor['image']['url'],
            'locked': adminActor['manuallyApprovesFollowers'],
            'note': '<p>Admin of ' + domain + '</p>',
            'url': url,
            'username': adminActor['preferredUsername']
        },
        'description': instanceDescription,
        'languages': [systemLanguage],
        'registrations': registration,
        'short_description': instanceDescriptionShort,
        'stats': {
            'domain_count': 1,
            'status_count': localPosts,
            'user_count': activeAccounts
        },
        'thumbnail': httpPrefix + '://' + domainFull + '/login.png',
        'title': instanceTitle,
        'uri': domainFull,
        'urls': {},
        'version': version
    }

    return instance


def metadataCustomEmoji(baseDir: str,
                        httpPrefix: str, domainFull: str) -> {}:
    """Returns the custom emoji
    Endpoint /api/v1/custom_emojis
    See https://docs.joinmastodon.org/methods/instance/custom_emojis
    """
    result = []
    emojisUrl = httpPrefix + '://' + domainFull + '/emoji'
    for subdir, dirs, files in os.walk(baseDir + '/emoji'):
        for f in files:
            if len(f) < 3:
                continue
            if f[0].isdigit() or f[1].isdigit():
                continue
            if not f.endswith('.png'):
                continue
            url = os.path.join(emojisUrl, f)
            result.append({
                "shortcode": f.replace('.png', ''),
                "url": url,
                "static_url": url,
                "visible_in_picker": True
            })
        break
    return result
