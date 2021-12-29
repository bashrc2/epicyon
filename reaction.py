__filename__ = "reaction.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
import re
import urllib.parse
from pprint import pprint
from utils import has_object_string
from utils import has_object_string_object
from utils import has_object_stringType
from utils import remove_domain_port
from utils import has_object_dict
from utils import has_users_path
from utils import get_full_domain
from utils import remove_id_ending
from utils import url_permitted
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import locate_post
from utils import undo_reaction_collection_entry
from utils import has_group_type
from utils import local_actor_url
from utils import load_json
from utils import save_json
from utils import remove_post_from_cache
from utils import get_cached_post_filename
from utils import contains_invalid_chars
from posts import send_signed_json
from session import post_json
from webfinger import webfinger_handle
from auth import create_basic_auth_header
from posts import get_person_box

# the maximum number of reactions from individual actors which can be
# added to a post. Hence an adversary can't bombard you with sockpuppet
# generated reactions and make the post infeasibly large
maxActorReactionsPerPost = 64

# regex defining permissable emoji icon range
emojiRegex = re.compile(r'[\u263a-\U0001f645]')


def valid_emoji_content(emojiContent: str) -> bool:
    """Is the given emoji content valid?
    """
    if not emojiContent:
        return False
    if len(emojiContent) > 2:
        return False
    if len(emojiRegex.findall(emojiContent)) == 0:
        return False
    if contains_invalid_chars(emojiContent):
        return False
    return True


def _reactionpost(recent_posts_cache: {},
                  session, base_dir: str, federation_list: [],
                  nickname: str, domain: str, port: int,
                  ccList: [], http_prefix: str,
                  objectUrl: str, emojiContent: str,
                  actorReaction: str,
                  client_to_server: bool,
                  send_threads: [], postLog: [],
                  person_cache: {}, cached_webfingers: {},
                  debug: bool, project_version: str,
                  signing_priv_key_pem: str) -> {}:
    """Creates an emoji reaction
    actor is the person doing the reacting
    'to' might be a specific person (actor) whose post was reaction
    object is typically the url of the message which was reaction
    """
    if not url_permitted(objectUrl, federation_list):
        return None
    if not valid_emoji_content(emojiContent):
        print('_reaction: Invalid emoji reaction: "' + emojiContent + '"')
        return

    fullDomain = get_full_domain(domain, port)

    newReactionJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'EmojiReact',
        'actor': local_actor_url(http_prefix, nickname, fullDomain),
        'object': objectUrl,
        'content': emojiContent
    }
    if ccList:
        if len(ccList) > 0:
            newReactionJson['cc'] = ccList

    # Extract the domain and nickname from a statuses link
    reaction_postNickname = None
    reaction_postDomain = None
    reaction_postPort = None
    group_account = False
    if actorReaction:
        reaction_postNickname = get_nickname_from_actor(actorReaction)
        reaction_postDomain, reaction_postPort = \
            get_domain_from_actor(actorReaction)
        group_account = has_group_type(base_dir, actorReaction, person_cache)
    else:
        if has_users_path(objectUrl):
            reaction_postNickname = get_nickname_from_actor(objectUrl)
            reaction_postDomain, reaction_postPort = \
                get_domain_from_actor(objectUrl)
            if '/' + str(reaction_postNickname) + '/' in objectUrl:
                actorReaction = \
                    objectUrl.split('/' + reaction_postNickname + '/')[0] + \
                    '/' + reaction_postNickname
                group_account = \
                    has_group_type(base_dir, actorReaction, person_cache)

    if reaction_postNickname:
        post_filename = locate_post(base_dir, nickname, domain, objectUrl)
        if not post_filename:
            print('DEBUG: reaction base_dir: ' + base_dir)
            print('DEBUG: reaction nickname: ' + nickname)
            print('DEBUG: reaction domain: ' + domain)
            print('DEBUG: reaction objectUrl: ' + objectUrl)
            return None

        update_reaction_collection(recent_posts_cache,
                                   base_dir, post_filename, objectUrl,
                                   newReactionJson['actor'],
                                   nickname, domain, debug, None,
                                   emojiContent)

        send_signed_json(newReactionJson, session, base_dir,
                         nickname, domain, port,
                         reaction_postNickname,
                         reaction_postDomain, reaction_postPort,
                         'https://www.w3.org/ns/activitystreams#Public',
                         http_prefix, True, client_to_server, federation_list,
                         send_threads, postLog, cached_webfingers,
                         person_cache,
                         debug, project_version, None, group_account,
                         signing_priv_key_pem, 7165392)

    return newReactionJson


def reaction_post(recent_posts_cache: {},
                  session, base_dir: str, federation_list: [],
                  nickname: str, domain: str, port: int, http_prefix: str,
                  reactionNickname: str, reactionDomain: str,
                  reactionPort: int, ccList: [],
                  reactionStatusNumber: int, emojiContent: str,
                  client_to_server: bool,
                  send_threads: [], postLog: [],
                  person_cache: {}, cached_webfingers: {},
                  debug: bool, project_version: str,
                  signing_priv_key_pem: str) -> {}:
    """Adds a reaction to a given status post. This is only used by unit tests
    """
    reactionDomain = get_full_domain(reactionDomain, reactionPort)

    actorReaction = \
        local_actor_url(http_prefix, reactionNickname, reactionDomain)
    objectUrl = actorReaction + '/statuses/' + str(reactionStatusNumber)

    return _reactionpost(recent_posts_cache,
                         session, base_dir, federation_list,
                         nickname, domain, port,
                         ccList, http_prefix, objectUrl, emojiContent,
                         actorReaction, client_to_server,
                         send_threads, postLog, person_cache,
                         cached_webfingers,
                         debug, project_version, signing_priv_key_pem)


def send_reaction_via_server(base_dir: str, session,
                             fromNickname: str, password: str,
                             fromDomain: str, fromPort: int,
                             http_prefix: str, reactionUrl: str,
                             emojiContent: str,
                             cached_webfingers: {}, person_cache: {},
                             debug: bool, project_version: str,
                             signing_priv_key_pem: str) -> {}:
    """Creates a reaction via c2s
    """
    if not session:
        print('WARN: No session for send_reaction_via_server')
        return 6
    if not valid_emoji_content(emojiContent):
        print('send_reaction_via_server: Invalid emoji reaction: "' +
              emojiContent + '"')
        return 7

    fromDomainFull = get_full_domain(fromDomain, fromPort)

    actor = local_actor_url(http_prefix, fromNickname, fromDomainFull)

    newReactionJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'EmojiReact',
        'actor': actor,
        'object': reactionUrl,
        'content': emojiContent
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfinger_handle(session, handle, http_prefix,
                                 cached_webfingers,
                                 fromDomain, project_version, debug, False,
                                 signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: reaction webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: reaction webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = get_person_box(signing_priv_key_pem,
                                      originDomain,
                                      base_dir, session, wfRequest,
                                      person_cache,
                                      project_version, http_prefix,
                                      fromNickname, fromDomain,
                                      postToBox, 72873)

    if not inboxUrl:
        if debug:
            print('DEBUG: reaction no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: reaction no actor was found for ' + handle)
        return 4

    authHeader = create_basic_auth_header(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = post_json(http_prefix, fromDomainFull,
                           session, newReactionJson, [], inboxUrl,
                           headers, 3, True)
    if not postResult:
        if debug:
            print('WARN: POST reaction failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST reaction success')

    return newReactionJson


def send_undo_reaction_via_server(base_dir: str, session,
                                  fromNickname: str, password: str,
                                  fromDomain: str, fromPort: int,
                                  http_prefix: str, reactionUrl: str,
                                  emojiContent: str,
                                  cached_webfingers: {}, person_cache: {},
                                  debug: bool, project_version: str,
                                  signing_priv_key_pem: str) -> {}:
    """Undo a reaction via c2s
    """
    if not session:
        print('WARN: No session for send_undo_reaction_via_server')
        return 6

    fromDomainFull = get_full_domain(fromDomain, fromPort)

    actor = local_actor_url(http_prefix, fromNickname, fromDomainFull)

    newUndoReactionJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': actor,
        'object': {
            'type': 'EmojiReact',
            'actor': actor,
            'object': reactionUrl,
            'content': emojiContent
        }
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfinger_handle(session, handle, http_prefix,
                                 cached_webfingers,
                                 fromDomain, project_version, debug, False,
                                 signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: unreaction webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        if debug:
            print('WARN: unreaction webfinger for ' + handle +
                  ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = get_person_box(signing_priv_key_pem,
                                      originDomain,
                                      base_dir, session, wfRequest,
                                      person_cache, project_version,
                                      http_prefix, fromNickname,
                                      fromDomain, postToBox,
                                      72625)

    if not inboxUrl:
        if debug:
            print('DEBUG: unreaction no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: unreaction no actor was found for ' + handle)
        return 4

    authHeader = create_basic_auth_header(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = post_json(http_prefix, fromDomainFull,
                           session, newUndoReactionJson, [], inboxUrl,
                           headers, 3, True)
    if not postResult:
        if debug:
            print('WARN: POST unreaction failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST unreaction success')

    return newUndoReactionJson


def outbox_reaction(recent_posts_cache: {},
                    base_dir: str, http_prefix: str,
                    nickname: str, domain: str, port: int,
                    message_json: {}, debug: bool) -> None:
    """ When a reaction request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        if debug:
            print('DEBUG: reaction - no type')
        return
    if not message_json['type'] == 'EmojiReact':
        if debug:
            print('DEBUG: not a reaction')
        return
    if not has_object_string(message_json, debug):
        return
    if not message_json.get('content'):
        return
    if not isinstance(message_json['content'], str):
        return
    if not valid_emoji_content(message_json['content']):
        print('outbox_reaction: Invalid emoji reaction: "' +
              message_json['content'] + '"')
        return
    if debug:
        print('DEBUG: c2s reaction request arrived in outbox')

    messageId = remove_id_ending(message_json['object'])
    domain = remove_domain_port(domain)
    emojiContent = message_json['content']
    post_filename = locate_post(base_dir, nickname, domain, messageId)
    if not post_filename:
        if debug:
            print('DEBUG: c2s reaction post not found in inbox or outbox')
            print(messageId)
        return True
    update_reaction_collection(recent_posts_cache,
                               base_dir, post_filename, messageId,
                               message_json['actor'],
                               nickname, domain, debug, None, emojiContent)
    if debug:
        print('DEBUG: post reaction via c2s - ' + post_filename)


def outbox_undo_reaction(recent_posts_cache: {},
                         base_dir: str, http_prefix: str,
                         nickname: str, domain: str, port: int,
                         message_json: {}, debug: bool) -> None:
    """ When an undo reaction request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if not message_json['type'] == 'Undo':
        return
    if not has_object_stringType(message_json, debug):
        return
    if not message_json['object']['type'] == 'EmojiReact':
        if debug:
            print('DEBUG: not a undo reaction')
        return
    if not message_json['object'].get('content'):
        return
    if not isinstance(message_json['object']['content'], str):
        return
    if not has_object_string_object(message_json, debug):
        return
    if debug:
        print('DEBUG: c2s undo reaction request arrived in outbox')

    messageId = remove_id_ending(message_json['object']['object'])
    emojiContent = message_json['object']['content']
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, messageId)
    if not post_filename:
        if debug:
            print('DEBUG: c2s undo reaction post not found in inbox or outbox')
            print(messageId)
        return True
    undo_reaction_collection_entry(recent_posts_cache, base_dir, post_filename,
                                   messageId, message_json['actor'],
                                   domain, debug, None, emojiContent)
    if debug:
        print('DEBUG: post undo reaction via c2s - ' + post_filename)


def update_reaction_collection(recent_posts_cache: {},
                               base_dir: str, post_filename: str,
                               objectUrl: str, actor: str,
                               nickname: str, domain: str, debug: bool,
                               post_json_object: {},
                               emojiContent: str) -> None:
    """Updates the reactions collection within a post
    """
    if not post_json_object:
        post_json_object = load_json(post_filename)
    if not post_json_object:
        return

    # remove any cached version of this post so that the
    # reaction icon is changed
    remove_post_from_cache(post_json_object, recent_posts_cache)
    cachedPostFilename = \
        get_cached_post_filename(base_dir, nickname,
                                 domain, post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                print('EX: update_reaction_collection unable to delete ' +
                      cachedPostFilename)

    obj = post_json_object
    if has_object_dict(post_json_object):
        obj = post_json_object['object']

    if not objectUrl.endswith('/reactions'):
        objectUrl = objectUrl + '/reactions'
    if not obj.get('reactions'):
        if debug:
            print('DEBUG: Adding initial emoji reaction to ' + objectUrl)
        reactionsJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'id': objectUrl,
            'type': 'Collection',
            "totalItems": 1,
            'items': [{
                'type': 'EmojiReact',
                'actor': actor,
                'content': emojiContent
            }]
        }
        obj['reactions'] = reactionsJson
    else:
        if not obj['reactions'].get('items'):
            obj['reactions']['items'] = []
        # upper limit for the number of reactions on a post
        if len(obj['reactions']['items']) >= maxActorReactionsPerPost:
            return
        for reactionItem in obj['reactions']['items']:
            if reactionItem.get('actor') and reactionItem.get('content'):
                if reactionItem['actor'] == actor and \
                   reactionItem['content'] == emojiContent:
                    # already reaction
                    return
        newReaction = {
            'type': 'EmojiReact',
            'actor': actor,
            'content': emojiContent
        }
        obj['reactions']['items'].append(newReaction)
        itlen = len(obj['reactions']['items'])
        obj['reactions']['totalItems'] = itlen

    if debug:
        print('DEBUG: saving post with emoji reaction added')
        pprint(post_json_object)
    save_json(post_json_object, post_filename)


def html_emoji_reactions(post_json_object: {}, interactive: bool,
                         actor: str, maxReactionTypes: int,
                         boxName: str, pageNumber: int) -> str:
    """html containing row of emoji reactions
    displayed at the bottom of posts, above the icons
    """
    if not has_object_dict(post_json_object):
        return ''
    if not post_json_object.get('actor'):
        return ''
    if not post_json_object['object'].get('reactions'):
        return ''
    if not post_json_object['object']['reactions'].get('items'):
        return ''
    reactions = {}
    reactedToByThisActor = []
    for item in post_json_object['object']['reactions']['items']:
        emojiContent = item['content']
        emojiActor = item['actor']
        emojiNickname = get_nickname_from_actor(emojiActor)
        emojiDomain, _ = get_domain_from_actor(emojiActor)
        emojiHandle = emojiNickname + '@' + emojiDomain
        if emojiActor == actor:
            if emojiContent not in reactedToByThisActor:
                reactedToByThisActor.append(emojiContent)
        if not reactions.get(emojiContent):
            if len(reactions.items()) < maxReactionTypes:
                reactions[emojiContent] = {
                    "handles": [emojiHandle],
                    "count": 1
                }
        else:
            reactions[emojiContent]['count'] += 1
            if len(reactions[emojiContent]['handles']) < 32:
                reactions[emojiContent]['handles'].append(emojiHandle)
    if len(reactions.items()) == 0:
        return ''
    reactBy = remove_id_ending(post_json_object['object']['id'])
    htmlStr = '<div class="emojiReactionBar">\n'
    for emojiContent, item in reactions.items():
        count = item['count']

        # get the handles of actors who reacted
        handlesStr = ''
        item['handles'].sort()
        for handle in item['handles']:
            if handlesStr:
                handlesStr += '&#10;'
            handlesStr += handle

        if emojiContent not in reactedToByThisActor:
            baseUrl = actor + '?react=' + reactBy
        else:
            baseUrl = actor + '?unreact=' + reactBy
        baseUrl += '?actor=' + post_json_object['actor']
        baseUrl += '?tl=' + boxName
        baseUrl += '?page=' + str(pageNumber)
        baseUrl += '?emojreact='

        htmlStr += '  <div class="emojiReactionButton">\n'
        if count < 100:
            countStr = str(count)
        else:
            countStr = '99+'
        emojiContentStr = emojiContent + countStr
        if interactive:
            # urlencode the emoji
            emojiContentEncoded = urllib.parse.quote_plus(emojiContent)
            emojiContentStr = \
                '    <a href="' + baseUrl + emojiContentEncoded + \
                '" title="' + handlesStr + '">' + \
                emojiContentStr + '</a>\n'
        htmlStr += emojiContentStr
        htmlStr += '  </div>\n'
    htmlStr += '</div>\n'
    return htmlStr
