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
from webfinger import webfinger_handle
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
from posts import get_person_box
from session import post_json


def undo_bookmarks_collection_entry(recent_posts_cache: {},
                                    base_dir: str, post_filename: str,
                                    object_url: str,
                                    actor: str, domain: str,
                                    debug: bool) -> None:
    """Undoes a bookmark for a particular actor
    """
    post_json_object = load_json(post_filename)
    if not post_json_object:
        return

    # remove any cached version of this post so that the
    # bookmark icon is changed
    nickname = get_nickname_from_actor(actor)
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname,
                                 domain, post_json_object)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                if debug:
                    print('EX: undo_bookmarks_collection_entry ' +
                          'unable to delete cached post file ' +
                          str(cached_post_filename))
    remove_post_from_cache(post_json_object, recent_posts_cache)

    # remove from the index
    bookmarks_index_filename = \
        acct_dir(base_dir, nickname, domain) + '/bookmarks.index'
    if not os.path.isfile(bookmarks_index_filename):
        return
    if '/' in post_filename:
        bookmark_index = post_filename.split('/')[-1].strip()
    else:
        bookmark_index = post_filename.strip()
    bookmark_index = bookmark_index.replace('\n', '').replace('\r', '')
    if bookmark_index not in open(bookmarks_index_filename).read():
        return
    index_str = ''
    try:
        with open(bookmarks_index_filename, 'r') as index_file:
            index_str = index_file.read().replace(bookmark_index + '\n', '')
    except OSError:
        print('EX: unable to read ' + bookmarks_index_filename)
    if index_str:
        try:
            with open(bookmarks_index_filename, 'w+') as bmi_file:
                bmi_file.write(index_str)
        except OSError:
            print('EX: unable to write bookmarks index ' +
                  bookmarks_index_filename)
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
    total_items = 0
    if post_json_object['object']['bookmarks'].get('totalItems'):
        total_items = post_json_object['object']['bookmarks']['totalItems']
    item_found = False
    for bookmark_item in post_json_object['object']['bookmarks']['items']:
        if bookmark_item.get('actor'):
            if bookmark_item['actor'] == actor:
                if debug:
                    print('DEBUG: bookmark was removed for ' + actor)
                bm_it = bookmark_item
                post_json_object['object']['bookmarks']['items'].remove(bm_it)
                item_found = True
                break

    if not item_found:
        return

    if total_items == 1:
        if debug:
            print('DEBUG: bookmarks was removed from post')
        del post_json_object['object']['bookmarks']
    else:
        bm_it_len = len(post_json_object['object']['bookmarks']['items'])
        post_json_object['object']['bookmarks']['totalItems'] = bm_it_len
    save_json(post_json_object, post_filename)


def bookmarked_by_person(post_json_object: {},
                         nickname: str, domain: str) -> bool:
    """Returns True if the given post is bookmarked by the given person
    """
    if _no_of_bookmarks(post_json_object) == 0:
        return False
    actor_match = domain + '/users/' + nickname
    for item in post_json_object['object']['bookmarks']['items']:
        if item['actor'].endswith(actor_match):
            return True
    return False


def _no_of_bookmarks(post_json_object: {}) -> int:
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


def update_bookmarks_collection(recent_posts_cache: {},
                                base_dir: str, post_filename: str,
                                object_url: str,
                                actor: str, domain: str, debug: bool) -> None:
    """Updates the bookmarks collection within a post
    """
    post_json_object = load_json(post_filename)
    if post_json_object:
        # remove any cached version of this post so that the
        # bookmark icon is changed
        nickname = get_nickname_from_actor(actor)
        cached_post_filename = \
            get_cached_post_filename(base_dir, nickname,
                                     domain, post_json_object)
        if cached_post_filename:
            if os.path.isfile(cached_post_filename):
                try:
                    os.remove(cached_post_filename)
                except OSError:
                    if debug:
                        print('EX: update_bookmarks_collection ' +
                              'unable to delete cached post ' +
                              str(cached_post_filename))
        remove_post_from_cache(post_json_object, recent_posts_cache)

        if not post_json_object.get('object'):
            if debug:
                print('DEBUG: no object in bookmarked post ' +
                      str(post_json_object))
            return
        if not object_url.endswith('/bookmarks'):
            object_url = object_url + '/bookmarks'
        # does this post have bookmarks on it from differenent actors?
        if not post_json_object['object'].get('bookmarks'):
            if debug:
                print('DEBUG: Adding initial bookmarks to ' + object_url)
            bookmarks_json = {
                "@context": "https://www.w3.org/ns/activitystreams",
                'id': object_url,
                'type': 'Collection',
                "totalItems": 1,
                'items': [{
                    'type': 'Bookmark',
                    'actor': actor
                }]
            }
            post_json_object['object']['bookmarks'] = bookmarks_json
        else:
            if not post_json_object['object']['bookmarks'].get('items'):
                post_json_object['object']['bookmarks']['items'] = []
            bm_items = post_json_object['object']['bookmarks']['items']
            for bookmark_item in bm_items:
                if bookmark_item.get('actor'):
                    if bookmark_item['actor'] == actor:
                        return
            new_bookmark = {
                'type': 'Bookmark',
                'actor': actor
            }
            nbook = new_bookmark
            bm_it = len(post_json_object['object']['bookmarks']['items'])
            post_json_object['object']['bookmarks']['items'].append(nbook)
            post_json_object['object']['bookmarks']['totalItems'] = bm_it

        if debug:
            print('DEBUG: saving post with bookmarks added')
            pprint(post_json_object)

        save_json(post_json_object, post_filename)

        # prepend to the index
        bookmarks_index_filename = \
            acct_dir(base_dir, nickname, domain) + '/bookmarks.index'
        bookmark_index = post_filename.split('/')[-1]
        if os.path.isfile(bookmarks_index_filename):
            if bookmark_index not in open(bookmarks_index_filename).read():
                try:
                    with open(bookmarks_index_filename, 'r+') as bmi_file:
                        content = bmi_file.read()
                        if bookmark_index + '\n' not in content:
                            bmi_file.seek(0, 0)
                            bmi_file.write(bookmark_index + '\n' + content)
                            if debug:
                                print('DEBUG: bookmark added to index')
                except OSError as ex:
                    print('WARN: Failed to write entry to bookmarks index ' +
                          bookmarks_index_filename + ' ' + str(ex))
        else:
            try:
                with open(bookmarks_index_filename, 'w+') as bm_file:
                    bm_file.write(bookmark_index + '\n')
            except OSError:
                print('EX: unable to write bookmarks index ' +
                      bookmarks_index_filename)


def bookmark_post(recent_posts_cache: {},
                  session, base_dir: str, federation_list: [],
                  nickname: str, domain: str, port: int,
                  ccList: [], http_prefix: str,
                  object_url: str, actorBookmarked: str,
                  client_to_server: bool,
                  send_threads: [], post_log: [],
                  person_cache: {}, cached_webfingers: {},
                  debug: bool, project_version: str) -> {}:
    """Creates a bookmark
    actor is the person doing the bookmarking
    'to' might be a specific person (actor) whose post was bookmarked
    object is typically the url of the message which was bookmarked
    """
    if not url_permitted(object_url, federation_list):
        return None

    full_domain = get_full_domain(domain, port)

    new_bookmark_json = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Bookmark',
        'actor': local_actor_url(http_prefix, nickname, full_domain),
        'object': object_url
    }
    if ccList:
        if len(ccList) > 0:
            new_bookmark_json['cc'] = ccList

    # Extract the domain and nickname from a statuses link
    bookmarked_post_nickname = None
    if actorBookmarked:
        ac_bm = actorBookmarked
        bookmarked_post_nickname = get_nickname_from_actor(ac_bm)
        _, _ = get_domain_from_actor(ac_bm)
    else:
        if has_users_path(object_url):
            ourl = object_url
            bookmarked_post_nickname = get_nickname_from_actor(ourl)
            _, _ = get_domain_from_actor(ourl)

    if bookmarked_post_nickname:
        post_filename = locate_post(base_dir, nickname, domain, object_url)
        if not post_filename:
            print('DEBUG: bookmark base_dir: ' + base_dir)
            print('DEBUG: bookmark nickname: ' + nickname)
            print('DEBUG: bookmark domain: ' + domain)
            print('DEBUG: bookmark object_url: ' + object_url)
            return None

        update_bookmarks_collection(recent_posts_cache,
                                    base_dir, post_filename, object_url,
                                    new_bookmark_json['actor'], domain, debug)

    return new_bookmark_json


def undo_bookmark_post(recent_posts_cache: {},
                       session, base_dir: str, federation_list: [],
                       nickname: str, domain: str, port: int,
                       ccList: [], http_prefix: str,
                       object_url: str, actorBookmarked: str,
                       client_to_server: bool,
                       send_threads: [], post_log: [],
                       person_cache: {}, cached_webfingers: {},
                       debug: bool, project_version: str) -> {}:
    """Removes a bookmark
    actor is the person doing the bookmarking
    'to' might be a specific person (actor) whose post was bookmarked
    object is typically the url of the message which was bookmarked
    """
    if not url_permitted(object_url, federation_list):
        return None

    full_domain = get_full_domain(domain, port)

    new_undo_bookmark_json = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': local_actor_url(http_prefix, nickname, full_domain),
        'object': {
            'type': 'Bookmark',
            'actor': local_actor_url(http_prefix, nickname, full_domain),
            'object': object_url
        }
    }
    if ccList:
        if len(ccList) > 0:
            new_undo_bookmark_json['cc'] = ccList
            new_undo_bookmark_json['object']['cc'] = ccList

    # Extract the domain and nickname from a statuses link
    bookmarked_post_nickname = None
    if actorBookmarked:
        ac_bm = actorBookmarked
        bookmarked_post_nickname = get_nickname_from_actor(ac_bm)
        _, _ = get_domain_from_actor(ac_bm)
    else:
        if has_users_path(object_url):
            ourl = object_url
            bookmarked_post_nickname = get_nickname_from_actor(ourl)
            _, _ = get_domain_from_actor(ourl)

    if bookmarked_post_nickname:
        post_filename = locate_post(base_dir, nickname, domain, object_url)
        if not post_filename:
            return None

        undo_bookmarks_collection_entry(recent_posts_cache,
                                        base_dir, post_filename, object_url,
                                        new_undo_bookmark_json['actor'],
                                        domain, debug)
    else:
        return None

    return new_undo_bookmark_json


def send_bookmark_via_server(base_dir: str, session,
                             nickname: str, password: str,
                             domain: str, fromPort: int,
                             http_prefix: str, bookmarkUrl: str,
                             cached_webfingers: {}, person_cache: {},
                             debug: bool, project_version: str,
                             signing_priv_key_pem: str) -> {}:
    """Creates a bookmark via c2s
    """
    if not session:
        print('WARN: No session for send_bookmark_via_server')
        return 6

    domain_full = get_full_domain(domain, fromPort)

    actor = local_actor_url(http_prefix, nickname, domain_full)

    new_bookmark_json = {
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
    wf_request = \
        webfinger_handle(session, handle, http_prefix,
                         cached_webfingers,
                         domain, project_version, debug, False,
                         signing_priv_key_pem)
    if not wf_request:
        if debug:
            print('DEBUG: bookmark webfinger failed for ' + handle)
        return 1
    if not isinstance(wf_request, dict):
        print('WARN: bookmark webfinger for ' + handle +
              ' did not return a dict. ' + str(wf_request))
        return 1

    post_to_box = 'outbox'

    # get the actor inbox for the To handle
    origin_domain = domain
    (inbox_url, _, _, from_person_id, _, _,
     _, _) = get_person_box(signing_priv_key_pem,
                            origin_domain,
                            base_dir, session, wf_request,
                            person_cache,
                            project_version, http_prefix,
                            nickname, domain,
                            post_to_box, 58391)

    if not inbox_url:
        if debug:
            print('DEBUG: bookmark no ' + post_to_box +
                  ' was found for ' + handle)
        return 3
    if not from_person_id:
        if debug:
            print('DEBUG: bookmark no actor was found for ' + handle)
        return 4

    auth_header = create_basic_auth_header(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': auth_header
    }
    post_result = post_json(http_prefix, domain_full,
                            session, new_bookmark_json, [], inbox_url,
                            headers, 3, True)
    if not post_result:
        if debug:
            print('WARN: POST bookmark failed for c2s to ' + inbox_url)
        return 5

    if debug:
        print('DEBUG: c2s POST bookmark success')

    return new_bookmark_json


def send_undo_bookmark_via_server(base_dir: str, session,
                                  nickname: str, password: str,
                                  domain: str, fromPort: int,
                                  http_prefix: str, bookmarkUrl: str,
                                  cached_webfingers: {}, person_cache: {},
                                  debug: bool, project_version: str,
                                  signing_priv_key_pem: str) -> {}:
    """Removes a bookmark via c2s
    """
    if not session:
        print('WARN: No session for send_undo_bookmark_via_server')
        return 6

    domain_full = get_full_domain(domain, fromPort)

    actor = local_actor_url(http_prefix, nickname, domain_full)

    new_bookmark_json = {
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
    wf_request = \
        webfinger_handle(session, handle, http_prefix,
                         cached_webfingers,
                         domain, project_version, debug, False,
                         signing_priv_key_pem)
    if not wf_request:
        if debug:
            print('DEBUG: unbookmark webfinger failed for ' + handle)
        return 1
    if not isinstance(wf_request, dict):
        print('WARN: unbookmark webfinger for ' + handle +
              ' did not return a dict. ' + str(wf_request))
        return 1

    post_to_box = 'outbox'

    # get the actor inbox for the To handle
    origin_domain = domain
    (inbox_url, _, _, from_person_id, _, _,
     _, _) = get_person_box(signing_priv_key_pem,
                            origin_domain,
                            base_dir, session, wf_request,
                            person_cache,
                            project_version, http_prefix,
                            nickname, domain,
                            post_to_box, 52594)

    if not inbox_url:
        if debug:
            print('DEBUG: unbookmark no ' + post_to_box +
                  ' was found for ' + handle)
        return 3
    if not from_person_id:
        if debug:
            print('DEBUG: unbookmark no actor was found for ' + handle)
        return 4

    auth_header = create_basic_auth_header(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': auth_header
    }
    post_result = post_json(http_prefix, domain_full,
                            session, new_bookmark_json, [], inbox_url,
                            headers, 3, True)
    if not post_result:
        if debug:
            print('WARN: POST unbookmark failed for c2s to ' + inbox_url)
        return 5

    if debug:
        print('DEBUG: c2s POST unbookmark success')

    return new_bookmark_json


def outbox_bookmark(recent_posts_cache: {},
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

    message_url = remove_id_ending(message_json['object']['url'])
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, message_url)
    if not post_filename:
        if debug:
            print('DEBUG: c2s like post not found in inbox or outbox')
            print(message_url)
        return True
    update_bookmarks_collection(recent_posts_cache,
                                base_dir, post_filename, message_url,
                                message_json['actor'], domain, debug)
    if debug:
        print('DEBUG: post bookmarked via c2s - ' + post_filename)


def outbox_undo_bookmark(recent_posts_cache: {},
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

    message_url = remove_id_ending(message_json['object']['url'])
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, message_url)
    if not post_filename:
        if debug:
            print('DEBUG: c2s unbookmark post not found in inbox or outbox')
            print(message_url)
        return True
    update_bookmarks_collection(recent_posts_cache,
                                base_dir, post_filename, message_url,
                                message_json['actor'], domain, debug)
    if debug:
        print('DEBUG: post unbookmarked via c2s - ' + post_filename)
