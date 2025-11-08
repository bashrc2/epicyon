__filename__ = "torrent.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

from utils import remove_html
from utils import get_full_domain
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import remove_id_ending
from utils import get_attributed_to
from utils import get_content_from_post
from utils import dangerous_markup
from utils import license_link_from_name
from utils import get_media_url_from_torrent
from utils import resembles_url
from blocking import is_blocked
from filters import is_filtered
from conversation import post_id_to_convthread_id


def convert_torrent_to_note(base_dir: str, nickname: str, domain: str,
                            system_language: str,
                            post_json_object: {}, blocked_cache: {},
                            block_federated: [],
                            languages_understood: []) -> {}:
    """Converts a Torrent ActivityPub(ish) object into
    a Note, so that it can then be displayed in a timeline
    https://socialhub.activitypub.rocks/t/
    fep-d8c8-bittorrent-torrent-objects/8309/6
    """
    if not post_json_object.get('type'):
        return None

    if not isinstance(post_json_object['type'], str):
        return None

    if post_json_object['type'] != 'Torrent':
        return None

    # check that the required fields are present
    required_fields = (
        'id', 'published', 'to', 'attributedTo', 'content'
    )
    for field_name in required_fields:
        if not post_json_object.get(field_name):
            print('REJECT: torrent ' + str(post_json_object))
            return None

    # who is this attributed to ?
    attributed_to = None
    if isinstance(post_json_object['attributedTo'], str):
        attributed_to = get_attributed_to(post_json_object['attributedTo'])
    if not attributed_to:
        return None

    # get the language of the torrent
    post_language = system_language
    if post_json_object.get('language'):
        if isinstance(post_json_object['language'], dict):
            if post_json_object['language'].get('identifier'):
                post_language = post_json_object['language']['identifier']

    # check that the attributed actor is not blocked
    post_nickname = get_nickname_from_actor(attributed_to)
    if not post_nickname:
        return None
    post_domain, post_domain_port = get_domain_from_actor(attributed_to)
    if not post_domain:
        return None
    post_domain_full = get_full_domain(post_domain, post_domain_port)
    if is_blocked(base_dir, nickname, domain,
                  post_nickname, post_domain_full,
                  blocked_cache, block_federated):
        return None

    # check that the content is valid
    if is_filtered(base_dir, nickname, domain, post_json_object['content'],
                   system_language):
        return None

    # get the content
    content = ''
    if post_json_object.get('license'):
        if isinstance(post_json_object['license'], dict):
            if post_json_object['license'].get('name'):
                if is_filtered(base_dir, nickname, domain,
                               post_json_object['license']['name'],
                               system_language):
                    return None
                content += '<p>' + post_json_object['license']['name'] + '</p>'
    content += \
        get_content_from_post(post_json_object, system_language,
                              languages_understood, "content")
    if not content:
        return None

    conversation_id = remove_id_ending(post_json_object['id'])
    conversation_id = post_id_to_convthread_id(conversation_id,
                                               post_json_object['published'])

    media_type, media_url, media_torrent, media_magnet = \
        get_media_url_from_torrent(post_json_object)

    if not media_url:
        return None

    attachment = [{
            'mediaType': media_type,
            'name': post_json_object['content'],
            'type': 'Document',
            'url': media_url
    }]

    comments_enabled = True
    if 'commentsEnabled' in post_json_object:
        if isinstance(post_json_object['commentsEnabled'], bool):
            comments_enabled = post_json_object['commentsEnabled']

    sensitive = False
    if 'sensitive' in post_json_object:
        if isinstance(post_json_object['sensitive'], bool):
            sensitive = post_json_object['sensitive']

    cc: list[str] = []
    if 'cc' in post_json_object:
        if isinstance(post_json_object['cc'], list):
            cc = post_json_object['cc']

    if media_torrent or media_magnet:
        content += '<p>'
        if media_torrent:
            content += '<a href="' + media_torrent + '">⇓</a> '
        if media_magnet:
            content += '<a href="' + media_magnet + '">🧲</a>'
        content += '</p>'

    new_post_id2 = remove_html(post_json_object['id'])
    new_post_id = remove_id_ending(new_post_id2)
    new_post = {
        'id': new_post_id + '/activity',
        'type': 'Create',
        'actor': attributed_to,
        'published': post_json_object['published'],
        'to': post_json_object['to'],
        'cc': post_json_object['cc'],
        'object': {
            'id': new_post_id,
            'conversation': conversation_id,
            'context': conversation_id,
            'type': 'Note',
            'summary': None,
            'inReplyTo': None,
            'published': post_json_object['published'],
            'url': new_post_id,
            'attributedTo': attributed_to,
            'to': post_json_object['to'],
            'cc': cc,
            'sensitive': sensitive,
            'atomUri': new_post_id,
            'inReplyToAtomUri': None,
            'commentsEnabled': comments_enabled,
            'rejectReplies': not comments_enabled,
            'mediaType': 'text/html',
            'content': content,
            'contentMap': {
                post_language: content
            },
            'attachment': attachment,
            'tag': [],
            'replies': {
                'id': new_post_id + '/replies',
                'repliesOf': new_post_id,
                'type': 'Collection',
                'first': {
                    'type': 'CollectionPage',
                    'partOf': new_post_id + '/replies',
                    'items': []
                }
            }
        }
    }
    if post_json_object.get('@context'):
        new_post['@context'] = post_json_object['@context']

    if post_json_object.get('support'):
        support_str = post_json_object['support']
        if isinstance(support_str, str):
            if not dangerous_markup(support_str, False, []):
                if not is_filtered(base_dir, nickname, domain, support_str,
                                   system_language):
                    new_post['object']['support'] = support_str
                    # if this is a link
                    if resembles_url(support_str):
                        # add a buy link
                        new_post['object']['attachment'].append({
                            'type': 'Link',
                            'mediaType': 'text/html',
                            'href': support_str,
                            'rel': 'support',
                            'name': 'Support'
                        })

    if post_json_object.get('license'):
        if isinstance(post_json_object['license'], dict):
            if post_json_object['license'].get('name'):
                if isinstance(post_json_object['license']['name'], str):
                    license_str = post_json_object['license']['name']
                    content_license_url = \
                        license_link_from_name(license_str)
                    if content_license_url:
                        new_post['object']['attachment'].append({
                            "type": "PropertyValue",
                            "name": "license",
                            "value": content_license_url
                        })

    return new_post
