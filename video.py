__filename__ = "video.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

from utils import getFullDomain
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import removeIdEnding
from blocking import isBlocked
from filters import isFiltered


def convertVideoToNote(base_dir: str, nickname: str, domain: str,
                       systemLanguage: str,
                       postJsonObject: {}, blockedCache: {}) -> {}:
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
        if not postJsonObject.get(fieldName):
            return None

    if postJsonObject['type'] != 'Video':
        return None

    # who is this attributed to ?
    attributedTo = None
    if isinstance(postJsonObject['attributedTo'], str):
        attributedTo = postJsonObject['attributedTo']
    elif isinstance(postJsonObject['attributedTo'], list):
        for entity in postJsonObject['attributedTo']:
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
    postLanguage = systemLanguage
    if postJsonObject.get('language'):
        if isinstance(postJsonObject['language'], dict):
            if postJsonObject['language'].get('identifier'):
                postLanguage = postJsonObject['language']['identifier']

    # check that the attributed actor is not blocked
    postNickname = getNicknameFromActor(attributedTo)
    if not postNickname:
        return None
    postDomain, postDomainPort = getDomainFromActor(attributedTo)
    if not postDomain:
        return None
    postDomainFull = getFullDomain(postDomain, postDomainPort)
    if isBlocked(base_dir, nickname, domain,
                 postNickname, postDomainFull, blockedCache):
        return None

    # check that the content is valid
    if isFiltered(base_dir, nickname, domain, postJsonObject['name']):
        return None
    if isFiltered(base_dir, nickname, domain, postJsonObject['content']):
        return None

    # get the content
    content = '<p><b>' + postJsonObject['name'] + '</b></p>'
    if postJsonObject.get('license'):
        if isinstance(postJsonObject['license'], dict):
            if postJsonObject['license'].get('name'):
                if isFiltered(base_dir, nickname, domain,
                              postJsonObject['license']['name']):
                    return None
                content += '<p>' + postJsonObject['license']['name'] + '</p>'
    content += postJsonObject['content']

    conversationId = removeIdEnding(postJsonObject['id'])

    mediaType = None
    mediaUrl = None
    mediaTorrent = None
    mediaMagnet = None
    for mediaLink in postJsonObject['url']:
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
            'name': postJsonObject['content'],
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

    newPostId = removeIdEnding(postJsonObject['id'])
    newPost = {
        '@context': postJsonObject['@context'],
        'id': newPostId + '/activity',
        'type': 'Create',
        'actor': attributedTo,
        'published': postJsonObject['published'],
        'to': postJsonObject['to'],
        'cc': postJsonObject['cc'],
        'object': {
            'id': newPostId,
            'conversation': conversationId,
            'type': 'Note',
            'summary': None,
            'inReplyTo': None,
            'published': postJsonObject['published'],
            'url': newPostId,
            'attributedTo': attributedTo,
            'to': postJsonObject['to'],
            'cc': postJsonObject['cc'],
            'sensitive': postJsonObject['sensitive'],
            'atomUri': newPostId,
            'inReplyToAtomUri': None,
            'commentsEnabled': postJsonObject['commentsEnabled'],
            'rejectReplies': not postJsonObject['commentsEnabled'],
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
