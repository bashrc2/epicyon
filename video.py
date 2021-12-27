__filename__ = "video.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

from utils import get_full_domain
from utils import getNicknameFromActor
from utils import get_domain_from_actor
from utils import remove_id_ending
from blocking import isBlocked
from filters import isFiltered


def convertVideoToNote(base_dir: str, nickname: str, domain: str,
                       system_language: str,
                       post_json_object: {}, blockedCache: {}) -> {}:
    """Converts a PeerTube Video ActivityPub(ish) object into
    a Note, so that it can then be displayed in a timeline
    """
    # check that the required fields are present
    requiredFields = (
        'type', '@context', 'id', 'published', 'to', 'cc',
        'attributedTo', 'commentsEnabled', 'content', 'sensitive',
        'name', 'url'
    )
    for fieldName in requiredFields:
        if not post_json_object.get(fieldName):
            return None

    if post_json_object['type'] != 'Video':
        return None

    # who is this attributed to ?
    attributedTo = None
    if isinstance(post_json_object['attributedTo'], str):
        attributedTo = post_json_object['attributedTo']
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
            attributedTo = entity['id']
            break
    if not attributedTo:
        return None

    # get the language of the video
    postLanguage = system_language
    if post_json_object.get('language'):
        if isinstance(post_json_object['language'], dict):
            if post_json_object['language'].get('identifier'):
                postLanguage = post_json_object['language']['identifier']

    # check that the attributed actor is not blocked
    postNickname = getNicknameFromActor(attributedTo)
    if not postNickname:
        return None
    postDomain, postDomainPort = get_domain_from_actor(attributedTo)
    if not postDomain:
        return None
    postDomainFull = get_full_domain(postDomain, postDomainPort)
    if isBlocked(base_dir, nickname, domain,
                 postNickname, postDomainFull, blockedCache):
        return None

    # check that the content is valid
    if isFiltered(base_dir, nickname, domain, post_json_object['name']):
        return None
    if isFiltered(base_dir, nickname, domain, post_json_object['content']):
        return None

    # get the content
    content = '<p><b>' + post_json_object['name'] + '</b></p>'
    if post_json_object.get('license'):
        if isinstance(post_json_object['license'], dict):
            if post_json_object['license'].get('name'):
                if isFiltered(base_dir, nickname, domain,
                              post_json_object['license']['name']):
                    return None
                content += '<p>' + post_json_object['license']['name'] + '</p>'
    content += post_json_object['content']

    conversationId = remove_id_ending(post_json_object['id'])

    mediaType = None
    mediaUrl = None
    mediaTorrent = None
    mediaMagnet = None
    for mediaLink in post_json_object['url']:
        if not isinstance(mediaLink, dict):
            continue
        if not mediaLink.get('mediaType'):
            continue
        if not mediaLink.get('href'):
            continue
        if mediaLink['mediaType'] == 'application/x-bittorrent':
            mediaTorrent = mediaLink['href']
        if mediaLink['href'].startswith('magnet:'):
            mediaMagnet = mediaLink['href']
        if mediaLink['mediaType'] != 'video/mp4' and \
           mediaLink['mediaType'] != 'video/ogv':
            continue
        if not mediaUrl:
            mediaType = mediaLink['mediaType']
            mediaUrl = mediaLink['href']

    if not mediaUrl:
        return None

    attachment = [{
            'mediaType': mediaType,
            'name': post_json_object['content'],
            'type': 'Document',
            'url': mediaUrl
    }]

    if mediaTorrent or mediaMagnet:
        content += '<p>'
        if mediaTorrent:
            content += '<a href="' + mediaTorrent + '">⇓</a> '
        if mediaMagnet:
            content += '<a href="' + mediaMagnet + '">🧲</a>'
        content += '</p>'

    newPostId = remove_id_ending(post_json_object['id'])
    newPost = {
        '@context': post_json_object['@context'],
        'id': newPostId + '/activity',
        'type': 'Create',
        'actor': attributedTo,
        'published': post_json_object['published'],
        'to': post_json_object['to'],
        'cc': post_json_object['cc'],
        'object': {
            'id': newPostId,
            'conversation': conversationId,
            'type': 'Note',
            'summary': None,
            'inReplyTo': None,
            'published': post_json_object['published'],
            'url': newPostId,
            'attributedTo': attributedTo,
            'to': post_json_object['to'],
            'cc': post_json_object['cc'],
            'sensitive': post_json_object['sensitive'],
            'atomUri': newPostId,
            'inReplyToAtomUri': None,
            'commentsEnabled': post_json_object['commentsEnabled'],
            'rejectReplies': not post_json_object['commentsEnabled'],
            'mediaType': 'text/html',
            'content': content,
            'contentMap': {
                postLanguage: content
            },
            'attachment': attachment,
            'tag': [],
            'replies': {
                'id': newPostId + '/replies',
                'type': 'Collection',
                'first': {
                    'type': 'CollectionPage',
                    'partOf': newPostId + '/replies',
                    'items': []
                }
            }
        }
    }

    return newPost
