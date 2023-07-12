__filename__ = "video.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

from utils import remove_html
from utils import get_full_domain
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import remove_id_ending
from blocking import is_blocked
from filters import is_filtered


def convert_video_to_note(base_dir: str, nickname: str, domain: str,
                          system_language: str,
                          post_json_object: {}, blocked_cache: {}) -> {}:
    """Converts a PeerTube Video ActivityPub(ish) object into
    a Note, so that it can then be displayed in a timeline
    """
    # check that the required fields are present
    required_fields = (
        'type', '@context', 'id', 'published', 'to', 'cc',
        'attributedTo', 'commentsEnabled', 'content', 'sensitive',
        'name', 'url'
    )
    for field_name in required_fields:
        if not post_json_object.get(field_name):
            return None

    if post_json_object['type'] != 'Video':
        return None

    # who is this attributed to ?
    attributed_to = None
    if isinstance(post_json_object['attributedTo'], str):
        attributed_to = post_json_object['attributedTo']
    elif isinstance(post_json_object['attributedTo'], list):
        for entity in post_json_object['attributedTo']:
            if not isinstance(entity, dict):
                continue
            if not entity.get('type'):
                continue
            if entity['type'] != 'Person':
                continue
            if not entity.get('id'):
                continue
            attributed_to = entity['id']
            break
    if not attributed_to:
        return None

    # get the language of the video
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
                  post_nickname, post_domain_full, blocked_cache):
        return None

    # check that the content is valid
    if is_filtered(base_dir, nickname, domain, post_json_object['name'],
                   system_language):
        return None
    if is_filtered(base_dir, nickname, domain, post_json_object['content'],
                   system_language):
        return None

    # get the content
    content = '<p><b>' + post_json_object['name'] + '</b></p>'
    if post_json_object.get('license'):
        if isinstance(post_json_object['license'], dict):
            if post_json_object['license'].get('name'):
                if is_filtered(base_dir, nickname, domain,
                               post_json_object['license']['name'],
                               system_language):
                    return None
                content += '<p>' + post_json_object['license']['name'] + '</p>'
    post_content = post_json_object['content']
    if 'contentMap' in post_json_object:
        if post_json_object['contentMap'].get(system_language):
            post_content = post_json_object['contentMap'][system_language]
    content += post_content

    conversation_id = remove_id_ending(post_json_object['id'])

    media_type = None
    media_url = None
    media_torrent = None
    media_magnet = None
    for media_link in post_json_object['url']:
        if not isinstance(media_link, dict):
            continue
        if not media_link.get('mediaType'):
            continue
        if not media_link.get('href'):
            continue
        if media_link['mediaType'] == 'application/x-bittorrent':
            media_torrent = remove_html(media_link['href'])
        if media_link['href'].startswith('magnet:'):
            media_magnet = remove_html(media_link['href'])
        if media_link['mediaType'] != 'video/mp4' and \
           media_link['mediaType'] != 'video/ogv':
            continue
        if not media_url:
            media_type = media_link['mediaType']
            media_url = remove_html(media_link['href'])

    if not media_url:
        return None

    attachment = [{
            'mediaType': media_type,
            'name': post_json_object['content'],
            'type': 'Document',
            'url': media_url
    }]

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
        '@context': post_json_object['@context'],
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
            'cc': post_json_object['cc'],
            'sensitive': post_json_object['sensitive'],
            'atomUri': new_post_id,
            'inReplyToAtomUri': None,
            'commentsEnabled': post_json_object['commentsEnabled'],
            'rejectReplies': not post_json_object['commentsEnabled'],
            'mediaType': 'text/html',
            'content': content,
            'contentMap': {
                post_language: content
            },
            'attachment': attachment,
            'tag': [],
            'replies': {
                'id': new_post_id + '/replies',
                'type': 'Collection',
                'first': {
                    'type': 'CollectionPage',
                    'partOf': new_post_id + '/replies',
                    'items': []
                }
            }
        }
    }

    return new_post
