__filename__ = "metadata.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Metadata"

import os
from utils import is_account_dir
from utils import load_json
from utils import no_of_accounts
from utils import no_of_active_accounts_monthly


def _get_status_count(base_dir: str) -> int:
    """Get the total number of posts
    """
    status_ctr = 0
    accounts_dir = base_dir + '/accounts'
    for _, dirs, _ in os.walk(accounts_dir):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            acct_dir = os.path.join(accounts_dir, acct + '/outbox')
            for _, _, files2 in os.walk(acct_dir):
                status_ctr += len(files2)
                break
        break
    return status_ctr


def meta_data_node_info(base_dir: str,
                        about_url: str,
                        terms_of_service_url: str,
                        registration: bool, version: str,
                        show_accounts: bool) -> {}:
    """ /nodeinfo/2.0 endpoint
    Also see https://socialhub.activitypub.rocks/t/
    fep-f1d5-nodeinfo-in-fediverse-software/1190/4

    Note that there are security considerations with this. If an adversary
    sees a lot of accounts and "local" posts then the instance may be
    considered a higher priority target.
    Also exposure of the version number and number of accounts could be
    sensitive
    """
    if show_accounts:
        active_accounts = no_of_accounts(base_dir)
        active_accounts_monthly = no_of_active_accounts_monthly(base_dir, 1)
        active_accounts_half_year = no_of_active_accounts_monthly(base_dir, 6)
        local_posts = _get_status_count(base_dir)
    else:
        active_accounts = 1
        active_accounts_monthly = 1
        active_accounts_half_year = 1
        local_posts = 1

    nodeinfo = {
        'openRegistrations': registration,
        'protocols': ['activitypub'],
        'services': {
            'outbound': ['rss2.0']
        },
        'software': {
            'name': 'epicyon',
            'version': version
        },
        'documents': {
            'about': about_url,
            'terms': terms_of_service_url
        },
        'usage': {
            'localPosts': local_posts,
            'users': {
                'activeHalfyear': active_accounts_half_year,
                'activeMonth': active_accounts_monthly,
                'total': active_accounts
            }
        },
        'metadata': {},
        'version': '2.0'
    }
    return nodeinfo


def meta_data_instance(show_accounts: bool,
                       instance_title: str,
                       instance_description_short: str,
                       instance_description: str,
                       http_prefix: str, base_dir: str,
                       admin_nickname: str, domain: str, domain_full: str,
                       registration: bool, system_language: str,
                       version: str) -> {}:
    """ /api/v1/instance endpoint
    """
    admin_actor_filename = \
        base_dir + '/accounts/' + admin_nickname + '@' + domain + '.json'
    if not os.path.isfile(admin_actor_filename):
        return {}

    admin_actor = load_json(admin_actor_filename, 0)
    if not admin_actor:
        print('WARN: json load exception meta_data_instance')
        return {}

    rules_list = []
    rules_filename = \
        base_dir + '/accounts/tos.md'
    if os.path.isfile(rules_filename):
        with open(rules_filename, 'r', encoding='utf-8') as fp_rules:
            rules_lines = fp_rules.readlines()
            rule_ctr = 1
            for line in rules_lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    continue
                rules_list.append({
                    'id': str(rule_ctr),
                    'text': line
                })
                rule_ctr += 1

    is_bot = False
    is_group = False
    if admin_actor['type'] == 'Group':
        is_group = True
    elif admin_actor['type'] != 'Person':
        is_bot = True

    url = \
        http_prefix + '://' + domain_full + '/@' + \
        admin_actor['preferredUsername']

    if show_accounts:
        active_accounts = no_of_accounts(base_dir)
        local_posts = _get_status_count(base_dir)
    else:
        active_accounts = 1
        local_posts = 1

    created_at = ''
    if admin_actor.get('published'):
        created_at = admin_actor['published']

    instance = {
        'approval_required': False,
        'invites_enabled': False,
        'registrations': registration,
        'contact_account': {
            'acct': admin_actor['preferredUsername'],
            'created_at': created_at,
            'avatar': admin_actor['icon']['url'],
            'avatar_static': admin_actor['icon']['url'],
            'header': admin_actor['image']['url'],
            'header_static': admin_actor['image']['url'],
            'bot': is_bot,
            'discoverable': True,
            'group': is_group,
            'display_name': admin_actor['name'],
            'locked': admin_actor['manuallyApprovesFollowers'],
            'note': '<p>Admin of ' + domain + '</p>',
            'url': url,
            'username': admin_actor['preferredUsername']
        },
        'description': instance_description,
        'languages': [system_language],
        'short_description': instance_description_short,
        'stats': {
            'domain_count': 2,
            'status_count': local_posts,
            'user_count': active_accounts
        },
        'thumbnail': http_prefix + '://' + domain_full + '/login.png',
        'title': instance_title,
        'uri': domain_full,
        'urls': {},
        'version': version,
        'rules': rules_list,
        'configuration': {
            'statuses': {
                'max_media_attachments': 1
            },
            'media_attachments': {
                'supported_mime_types': [
                    'image/jpeg',
                    'image/jxl',
                    'image/png',
                    'image/gif',
                    'image/webp',
                    'image/avif',
                    'image/heic',
                    'image/svg+xml',
                    'video/webm',
                    'video/mp4',
                    'video/ogv',
                    'audio/ogg',
                    'audio/wav',
                    'audio/x-wav',
                    'audio/x-pn-wave',
                    'audio/vnd.wave',
                    'audio/opus',
                    'audio/speex',
                    'audio/x-speex',
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


def metadata_custom_emoji(base_dir: str,
                          http_prefix: str, domain_full: str) -> {}:
    """Returns the custom emoji
    Endpoint /api/v1/custom_emojis
    See https://docs.joinmastodon.org/methods/instance/custom_emojis
    """
    result = []
    emojis_url = http_prefix + '://' + domain_full + '/emoji'
    for _, _, files in os.walk(base_dir + '/emoji'):
        for fname in files:
            if len(fname) < 3:
                continue
            if fname[0].isdigit() or fname[1].isdigit():
                continue
            if not fname.endswith('.png'):
                continue
            url = os.path.join(emojis_url, fname)
            result.append({
                "shortcode": fname.replace('.png', ''),
                "url": url,
                "static_url": url,
                "visible_in_picker": True
            })
        break
    return result
