__filename__ = "bookmarks.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from pprint import pprint
from webfinger import webfingerHandle
from auth import create_basic_auth_header
from utils import remove_domain_port
from utils import has_users_path
from utils import get_full_domain
from utils import remove_id_ending
from utils import remove_post_from_cache
from utils import url_permitted
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import locate_post
from utils import get_cached_post_filename
from utils import load_json
from utils import save_json
from utils import has_object_dict
from utils import acct_dir
from utils import local_actor_url
from utils import has_actor
from utils import has_object_stringType
from posts import getPersonBox
from session import postJson


def undoBookmarksCollectionEntry(recent_posts_cache: {},
                                 base_dir: str, post_filename: str,
                                 objectUrl: str,
                                 actor: str, domain: str, debug: bool) -> None:
    """Undoes a bookmark for a particular actor
    """
    post_json_object = load_json(post_filename)
    if not post_json_object:
        return

    # remove any cached version of this post so that the
    # bookmark icon is changed
    nickname = get_nickname_from_actor(actor)
    cachedPostFilename = \
        get_cached_post_filename(base_dir, nickname,
                                 domain, post_json_object)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            try:
                os.remove(cachedPostFilename)
            except OSError:
                if debug:
                    print('EX: undoBookmarksCollectionEntry ' +
                          'unable to delete cached post file ' +
                          str(cachedPostFilename))
    remove_post_from_cache(post_json_object, recent_posts_cache)

    # remove from the index
    bookmarksIndexFilename = \
        acct_dir(base_dir, nickname, domain) + '/bookmarks.index'
    if not os.path.isfile(bookmarksIndexFilename):
        return
    if '/' in post_filename:
        bookmarkIndex = post_filename.split('/')[-1].strip()
    else:
        bookmarkIndex = post_filename.strip()
    bookmarkIndex = bookmarkIndex.replace('\n', '').replace('\r', '')
    if bookmarkIndex not in open(bookmarksIndexFilename).read():
        return
    indexStr = ''
    try:
        with open(bookmarksIndexFilename, 'r') as indexFile:
            indexStr = indexFile.read().replace(bookmarkIndex + '\n', '')
    except OSError:
        print('EX: unable to read ' + bookmarksIndexFilename)
    if indexStr:
        try:
            with open(bookmarksIndexFilename, 'w+') as bookmarksIndexFile:
                bookmarksIndexFile.write(indexStr)
        except OSError:
            print('EX: unable to write bookmarks index ' +
                  bookmarksIndexFilename)
    if not post_json_object.get('type'):
        return
    if post_json_object['type'] != 'Create':
        return
    if not has_object_dict(post_json_object):
        if debug:
            print('DEBUG: bookmarked post has no object ' +
                  str(post_json_object))
        return
    if not post_json_object['object'].get('bookmarks'):
        return
    if not isinstance(post_json_object['object']['bookmarks'], dict):
        return
    if not post_json_object['object']['bookmarks'].get('items'):
        return
    totalItems = 0
    if post_json_object['object']['bookmarks'].get('totalItems'):
        totalItems = post_json_object['object']['bookmarks']['totalItems']
        itemFound = False
    for bookmarkItem in post_json_object['object']['bookmarks']['items']:
        if bookmarkItem.get('actor'):
            if bookmarkItem['actor'] == actor:
                if debug:
                    print('DEBUG: bookmark was removed for ' + actor)
                bmIt = bookmarkItem
                post_json_object['object']['bookmarks']['items'].remove(bmIt)
                itemFound = True
                break

    if not itemFound:
        return

    if totalItems == 1:
        if debug:
            print('DEBUG: bookmarks was removed from post')
        del post_json_object['object']['bookmarks']
    else:
        bmItLen = len(post_json_object['object']['bookmarks']['items'])
        post_json_object['object']['bookmarks']['totalItems'] = bmItLen
    save_json(post_json_object, post_filename)


def bookmarkedByPerson(post_json_object: {},
                       nickname: str, domain: str) -> bool:
    """Returns True if the given post is bookmarked by the given person
    """
    if _noOfBookmarks(post_json_object) == 0:
        return False
    actorMatch = domain + '/users/' + nickname
    for item in post_json_object['object']['bookmarks']['items']:
        if item['actor'].endswith(actorMatch):
            return True
    return False


def _noOfBookmarks(post_json_object: {}) -> int:
    """Returns the number of bookmarks ona  given post
    """
    if not has_object_dict(post_json_object):
        return 0
    if not post_json_object['object'].get('bookmarks'):
        return 0
    if not isinstance(post_json_object['object']['bookmarks'], dict):
        return 0
    if not post_json_object['object']['bookmarks'].get('items'):
        post_json_object['object']['bookmarks']['items'] = []
        post_json_object['object']['bookmarks']['totalItems'] = 0
    return len(post_json_object['object']['bookmarks']['items'])


def updateBookmarksCollection(recent_posts_cache: {},
                              base_dir: str, post_filename: str,
                              objectUrl: str,
                              actor: str, domain: str, debug: bool) -> None:
    """Updates the bookmarks collection within a post
    """
    post_json_object = load_json(post_filename)
    if post_json_object:
        # remove any cached version of this post so that the
        # bookmark icon is changed
        nickname = get_nickname_from_actor(actor)
        cachedPostFilename = \
            get_cached_post_filename(base_dir, nickname,
                                     domain, post_json_object)
        if cachedPostFilename:
            if os.path.isfile(cachedPostFilename):
                try:
                    os.remove(cachedPostFilename)
                except OSError:
                    if debug:
                        print('EX: updateBookmarksCollection ' +
                              'unable to delete cached post ' +
                              str(cachedPostFilename))
        remove_post_from_cache(post_json_object, recent_posts_cache)

        if not post_json_object.get('object'):
            if debug:
                print('DEBUG: no object in bookmarked post ' +
                      str(post_json_object))
            return
        if not objectUrl.endswith('/bookmarks'):
            objectUrl = objectUrl + '/bookmarks'
        # does this post have bookmarks on it from differenent actors?
        if not post_json_object['object'].get('bookmarks'):
            if debug:
                print('DEBUG: Adding initial bookmarks to ' + objectUrl)
            bookmarksJson = {
                "@context": "https://www.w3.org/ns/activitystreams",
                'id': objectUrl,
                'type': 'Collection',
                "totalItems": 1,
                'items': [{
                    'type': 'Bookmark',
                    'actor': actor
                }]
            }
            post_json_object['object']['bookmarks'] = bookmarksJson
        else:
            if not post_json_object['object']['bookmarks'].get('items'):
                post_json_object['object']['bookmarks']['items'] = []
            bm_items = post_json_object['object']['bookmarks']['items']
            for bookmarkItem in bm_items:
                if bookmarkItem.get('actor'):
                    if bookmarkItem['actor'] == actor:
                        return
            newBookmark = {
                'type': 'Bookmark',
                'actor': actor
            }
            nb = newBookmark
            bmIt = len(post_json_object['object']['bookmarks']['items'])
            post_json_object['object']['bookmarks']['items'].append(nb)
            post_json_object['object']['bookmarks']['totalItems'] = bmIt

        if debug:
            print('DEBUG: saving post with bookmarks added')
            pprint(post_json_object)

        save_json(post_json_object, post_filename)

        # prepend to the index
        bookmarksIndexFilename = \
            acct_dir(base_dir, nickname, domain) + '/bookmarks.index'
        bookmarkIndex = post_filename.split('/')[-1]
        if os.path.isfile(bookmarksIndexFilename):
            if bookmarkIndex not in open(bookmarksIndexFilename).read():
                try:
                    with open(bookmarksIndexFilename, 'r+') as bmIndexFile:
                        content = bmIndexFile.read()
                        if bookmarkIndex + '\n' not in content:
                            bmIndexFile.seek(0, 0)
                            bmIndexFile.write(bookmarkIndex + '\n' + content)
                            if debug:
                                print('DEBUG: bookmark added to index')
                except Exception as ex:
                    print('WARN: Failed to write entry to bookmarks index ' +
                          bookmarksIndexFilename + ' ' + str(ex))
        else:
            try:
                with open(bookmarksIndexFilename, 'w+') as bookmarksIndexFile:
                    bookmarksIndexFile.write(bookmarkIndex + '\n')
            except OSError:
                print('EX: unable to write bookmarks index ' +
                      bookmarksIndexFilename)


def bookmark(recent_posts_cache: {},
             session, base_dir: str, federation_list: [],
             nickname: str, domain: str, port: int,
             ccList: [], http_prefix: str,
             objectUrl: str, actorBookmarked: str,
             client_to_server: bool,
             send_threads: [], postLog: [],
             person_cache: {}, cached_webfingers: {},
             debug: bool, project_version: str) -> {}:
    """Creates a bookmark
    actor is the person doing the bookmarking
    'to' might be a specific person (actor) whose post was bookmarked
    object is typically the url of the message which was bookmarked
    """
    if not url_permitted(objectUrl, federation_list):
        return None

    fullDomain = get_full_domain(domain, port)

    newBookmarkJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Bookmark',
        'actor': local_actor_url(http_prefix, nickname, fullDomain),
        'object': objectUrl
    }
    if ccList:
        if len(ccList) > 0:
            newBookmarkJson['cc'] = ccList

    # Extract the domain and nickname from a statuses link
    bookmarkedPostNickname = None
    bookmarkedPostDomain = None
    bookmarkedPostPort = None
    if actorBookmarked:
        acBm = actorBookmarked
        bookmarkedPostNickname = get_nickname_from_actor(acBm)
        bookmarkedPostDomain, bookmarkedPostPort = get_domain_from_actor(acBm)
    else:
        if has_users_path(objectUrl):
            ou = objectUrl
            bookmarkedPostNickname = get_nickname_from_actor(ou)
            bookmarkedPostDomain, bookmarkedPostPort = \
                get_domain_from_actor(ou)

    if bookmarkedPostNickname:
        post_filename = locate_post(base_dir, nickname, domain, objectUrl)
        if not post_filename:
            print('DEBUG: bookmark base_dir: ' + base_dir)
            print('DEBUG: bookmark nickname: ' + nickname)
            print('DEBUG: bookmark domain: ' + domain)
            print('DEBUG: bookmark objectUrl: ' + objectUrl)
            return None

        updateBookmarksCollection(recent_posts_cache,
                                  base_dir, post_filename, objectUrl,
                                  newBookmarkJson['actor'], domain, debug)

    return newBookmarkJson


def undoBookmark(recent_posts_cache: {},
                 session, base_dir: str, federation_list: [],
                 nickname: str, domain: str, port: int,
                 ccList: [], http_prefix: str,
                 objectUrl: str, actorBookmarked: str,
                 client_to_server: bool,
                 send_threads: [], postLog: [],
                 person_cache: {}, cached_webfingers: {},
                 debug: bool, project_version: str) -> {}:
    """Removes a bookmark
    actor is the person doing the bookmarking
    'to' might be a specific person (actor) whose post was bookmarked
    object is typically the url of the message which was bookmarked
    """
    if not url_permitted(objectUrl, federation_list):
        return None

    fullDomain = get_full_domain(domain, port)

    newUndoBookmarkJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': local_actor_url(http_prefix, nickname, fullDomain),
        'object': {
            'type': 'Bookmark',
            'actor': local_actor_url(http_prefix, nickname, fullDomain),
            'object': objectUrl
        }
    }
    if ccList:
        if len(ccList) > 0:
            newUndoBookmarkJson['cc'] = ccList
            newUndoBookmarkJson['object']['cc'] = ccList

    # Extract the domain and nickname from a statuses link
    bookmarkedPostNickname = None
    bookmarkedPostDomain = None
    bookmarkedPostPort = None
    if actorBookmarked:
        acBm = actorBookmarked
        bookmarkedPostNickname = get_nickname_from_actor(acBm)
        bookmarkedPostDomain, bookmarkedPostPort = get_domain_from_actor(acBm)
    else:
        if has_users_path(objectUrl):
            ou = objectUrl
            bookmarkedPostNickname = get_nickname_from_actor(ou)
            bookmarkedPostDomain, bookmarkedPostPort = \
                get_domain_from_actor(ou)

    if bookmarkedPostNickname:
        post_filename = locate_post(base_dir, nickname, domain, objectUrl)
        if not post_filename:
            return None

        undoBookmarksCollectionEntry(recent_posts_cache,
                                     base_dir, post_filename, objectUrl,
                                     newUndoBookmarkJson['actor'],
                                     domain, debug)
    else:
        return None

    return newUndoBookmarkJson


def sendBookmarkViaServer(base_dir: str, session,
                          nickname: str, password: str,
                          domain: str, fromPort: int,
                          http_prefix: str, bookmarkUrl: str,
                          cached_webfingers: {}, person_cache: {},
                          debug: bool, project_version: str,
                          signing_priv_key_pem: str) -> {}:
    """Creates a bookmark via c2s
    """
    if not session:
        print('WARN: No session for sendBookmarkViaServer')
        return 6

    domain_full = get_full_domain(domain, fromPort)

    actor = local_actor_url(http_prefix, nickname, domain_full)

    newBookmarkJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Add",
        "actor": actor,
        "to": [actor],
        "object": {
            "type": "Document",
            "url": bookmarkUrl,
            "to": [actor]
        },
        "target": actor + "/tlbookmarks"
    }

    handle = http_prefix + '://' + domain_full + '/@' + nickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cached_webfingers,
                                domain, project_version, debug, False,
                                signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: bookmark webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: bookmark webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = domain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache,
                                    project_version, http_prefix,
                                    nickname, domain,
                                    postToBox, 58391)

    if not inboxUrl:
        if debug:
            print('DEBUG: bookmark no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: bookmark no actor was found for ' + handle)
        return 4

    authHeader = create_basic_auth_header(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(http_prefix, domain_full,
                          session, newBookmarkJson, [], inboxUrl,
                          headers, 3, True)
    if not postResult:
        if debug:
            print('WARN: POST bookmark failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST bookmark success')

    return newBookmarkJson


def sendUndoBookmarkViaServer(base_dir: str, session,
                              nickname: str, password: str,
                              domain: str, fromPort: int,
                              http_prefix: str, bookmarkUrl: str,
                              cached_webfingers: {}, person_cache: {},
                              debug: bool, project_version: str,
                              signing_priv_key_pem: str) -> {}:
    """Removes a bookmark via c2s
    """
    if not session:
        print('WARN: No session for sendUndoBookmarkViaServer')
        return 6

    domain_full = get_full_domain(domain, fromPort)

    actor = local_actor_url(http_prefix, nickname, domain_full)

    newBookmarkJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Remove",
        "actor": actor,
        "to": [actor],
        "object": {
            "type": "Document",
            "url": bookmarkUrl,
            "to": [actor]
        },
        "target": actor + "/tlbookmarks"
    }

    handle = http_prefix + '://' + domain_full + '/@' + nickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, http_prefix,
                                cached_webfingers,
                                domain, project_version, debug, False,
                                signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: unbookmark webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: unbookmark webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = domain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache,
                                    project_version, http_prefix,
                                    nickname, domain,
                                    postToBox, 52594)

    if not inboxUrl:
        if debug:
            print('DEBUG: unbookmark no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: unbookmark no actor was found for ' + handle)
        return 4

    authHeader = create_basic_auth_header(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = postJson(http_prefix, domain_full,
                          session, newBookmarkJson, [], inboxUrl,
                          headers, 3, True)
    if not postResult:
        if debug:
            print('WARN: POST unbookmark failed for c2s to ' + inboxUrl)
        return 5

    if debug:
        print('DEBUG: c2s POST unbookmark success')

    return newBookmarkJson


def outboxBookmark(recent_posts_cache: {},
                   base_dir: str, http_prefix: str,
                   nickname: str, domain: str, port: int,
                   message_json: {}, debug: bool) -> None:
    """ When a bookmark request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if message_json['type'] != 'Add':
        return
    if not has_actor(message_json, debug):
        return
    if not message_json.get('target'):
        if debug:
            print('DEBUG: no target in bookmark Add')
        return
    if not has_object_stringType(message_json, debug):
        return
    if not isinstance(message_json['target'], str):
        if debug:
            print('DEBUG: bookmark Add target is not string')
        return
    domain_full = get_full_domain(domain, port)
    if not message_json['target'].endswith('://' + domain_full +
                                           '/users/' + nickname +
                                           '/tlbookmarks'):
        if debug:
            print('DEBUG: bookmark Add target invalid ' +
                  message_json['target'])
        return
    if message_json['object']['type'] != 'Document':
        if debug:
            print('DEBUG: bookmark Add type is not Document')
        return
    if not message_json['object'].get('url'):
        if debug:
            print('DEBUG: bookmark Add missing url')
        return
    if debug:
        print('DEBUG: c2s bookmark Add request arrived in outbox')

    messageUrl = remove_id_ending(message_json['object']['url'])
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, messageUrl)
    if not post_filename:
        if debug:
            print('DEBUG: c2s like post not found in inbox or outbox')
            print(messageUrl)
        return True
    updateBookmarksCollection(recent_posts_cache,
                              base_dir, post_filename, messageUrl,
                              message_json['actor'], domain, debug)
    if debug:
        print('DEBUG: post bookmarked via c2s - ' + post_filename)


def outboxUndoBookmark(recent_posts_cache: {},
                       base_dir: str, http_prefix: str,
                       nickname: str, domain: str, port: int,
                       message_json: {}, debug: bool) -> None:
    """ When an undo bookmark request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if message_json['type'] != 'Remove':
        return
    if not has_actor(message_json, debug):
        return
    if not message_json.get('target'):
        if debug:
            print('DEBUG: no target in unbookmark Remove')
        return
    if not has_object_stringType(message_json, debug):
        return
    if not isinstance(message_json['target'], str):
        if debug:
            print('DEBUG: unbookmark Remove target is not string')
        return
    domain_full = get_full_domain(domain, port)
    if not message_json['target'].endswith('://' + domain_full +
                                           '/users/' + nickname +
                                           '/tlbookmarks'):
        if debug:
            print('DEBUG: unbookmark Remove target invalid ' +
                  message_json['target'])
        return
    if message_json['object']['type'] != 'Document':
        if debug:
            print('DEBUG: unbookmark Remove type is not Document')
        return
    if not message_json['object'].get('url'):
        if debug:
            print('DEBUG: unbookmark Remove missing url')
        return
    if debug:
        print('DEBUG: c2s unbookmark Remove request arrived in outbox')

    messageUrl = remove_id_ending(message_json['object']['url'])
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, messageUrl)
    if not post_filename:
        if debug:
            print('DEBUG: c2s unbookmark post not found in inbox or outbox')
            print(messageUrl)
        return True
    updateBookmarksCollection(recent_posts_cache,
                              base_dir, post_filename, messageUrl,
                              message_json['actor'], domain, debug)
    if debug:
        print('DEBUG: post unbookmarked via c2s - ' + post_filename)
