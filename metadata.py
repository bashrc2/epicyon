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


def _getStatusCount(base_dir: str) -> int:
    """Get the total number of posts
    """
    statusCtr = 0
    accountsDir = base_dir + '/accounts'
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


def metaDataNodeInfo(base_dir: str,
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
        activeAccounts = noOfAccounts(base_dir)
        activeAccountsMonthly = noOfActiveAccountsMonthly(base_dir, 1)
        activeAccountsHalfYear = noOfActiveAccountsMonthly(base_dir, 6)
        localPosts = _getStatusCount(base_dir)
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
                     http_prefix: str, base_dir: str,
                     adminNickname: str, domain: str, domainFull: str,
                     registration: bool, system_language: str,
                     version: str) -> {}:
    """ /api/v1/instance endpoint
    """
    adminActorFilename = \
        base_dir + '/accounts/' + adminNickname + '@' + domain + '.json'
    if not os.path.isfile(adminActorFilename):
        return {}

    adminActor = loadJson(adminActorFilename, 0)
    if not adminActor:
        print('WARN: json load exception metaDataInstance')
        return {}

    rulesList = []
    rulesFilename = \
        base_dir + '/accounts/tos.md'
    if os.path.isfile(rulesFilename):
        with open(rulesFilename, 'r') as fp:
            rulesLines = fp.readlines()
            ruleCtr = 1
            for line in rulesLines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    continue
                rulesList.append({
                    'id': str(ruleCtr),
                    'text': line
                })
                ruleCtr += 1

    isBot = False
    isGroup = False
    if adminActor['type'] == 'Group':
        isGroup = True
    elif adminActor['type'] != 'Person':
        isBot = True

    url = \
        http_prefix + '://' + domainFull + '/@' + \
        adminActor['preferredUsername']

    if showAccounts:
        activeAccounts = noOfAccounts(base_dir)
        localPosts = _getStatusCount(base_dir)
    else:
        activeAccounts = 1
        localPosts = 1

    createdAt = ''
    if adminActor.get('published'):
        createdAt = adminActor['published']

    instance = {
        'approval_required': False,
        'invites_enabled': False,
        'registrations': registration,
        'contact_account': {
            'acct': adminActor['preferredUsername'],
            'created_at': createdAt,
            'avatar': adminActor['icon']['url'],
            'avatar_static': adminActor['icon']['url'],
            'header': adminActor['image']['url'],
            'header_static': adminActor['image']['url'],
            'bot': isBot,
            'discoverable': True,
            'group': isGroup,
            'display_name': adminActor['name'],
            'locked': adminActor['manuallyApprovesFollowers'],
            'note': '<p>Admin of ' + domain + '</p>',
            'url': url,
            'username': adminActor['preferredUsername']
        },
        'description': instanceDescription,
        'languages': [system_language],
        'short_description': instanceDescriptionShort,
        'stats': {
            'domain_count': 2,
            'status_count': localPosts,
            'user_count': activeAccounts
        },
        'thumbnail': http_prefix + '://' + domainFull + '/login.png',
        'title': instanceTitle,
        'uri': domainFull,
        'urls': {},
        'version': version,
        'rules': rulesList,
        'configuration': {
            'statuses': {
                'max_media_attachments': 1
            },
            'media_attachments': {
                'supported_mime_types': [
                    'image/jpeg',
                    'image/png',
                    'image/gif',
                    'image/webp',
                    'image/avif',
                    'image/svg+xml',
                    'video/webm',
                    'video/mp4',
                    'video/ogv',
                    'audio/ogg',
                    'audio/flac',
                    'audio/mpeg'
                ],
                'image_size_limit': 10485760,
                'image_matrix_limit': 16777216,
                'video_size_limit': 41943040,
                'video_frame_rate_limit': 60,
                'video_matrix_limit': 2304000
            }
        }
    }

    return instance


def metadataCustomEmoji(base_dir: str,
                        http_prefix: str, domainFull: str) -> {}:
    """Returns the custom emoji
    Endpoint /api/v1/custom_emojis
    See https://docs.joinmastodon.org/methods/instance/custom_emojis
    """
    result = []
    emojisUrl = http_prefix + '://' + domainFull + '/emoji'
    for subdir, dirs, files in os.walk(base_dir + '/emoji'):
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
