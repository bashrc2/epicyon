__filename__ = "collections.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

from src.utils import acct_dir
from src.utils import valid_nickname
from src.utils import get_full_domain
from src.utils import local_actor_url
from src.utils import remove_domain_port
from src.utils import remove_html
from src.utils import file_last_modified
from src.utils import file_created_date
from src.utils import get_nickname_from_actor
from src.utils import get_domain_from_actor
from src.data import is_a_file
from src.data import load_list


def _get_no_of_featured_collections(base_dir: str,
                                    nickname: str, domain: str) -> int:
    """Returns the number of featured collections
    """
    ending: str = '/featured_collections'
    accounts_dir: str = acct_dir(base_dir, nickname, domain)
    collection_filename: str = accounts_dir + ending + '.txt'
    if not is_a_file(collection_filename):
        return 0
    lines: list[str] = load_list(collection_filename,
                                 '_get_no_of_featured_collections ' +
                                 'unable to load list')
    if not lines:
        return 0
    ctr = 0
    for text in lines:
        if text.startswith('# '):
            ctr += 1
    return ctr


def _text_to_number(url: str) -> str:
    """converts text to a number string used as an id
    """
    result = ''
    for char in url:
        num = ord(char)
        if num > 99:
            continue
        if num > 9:
            result = str(num) + result
        else:
            result = '0' + str(num) + result
    num = (7439 + int(result)) % 99999999999999999999
    return str(num)


def _update_collections(collection_name: str, collection_items: [],
                        collection: [],
                        http_prefix: str, domain: str,
                        actor: str, published: str,
                        updated: str):
    """Updates featured collections
    """
    if not collection_name or not collection_items:
        collection_items.clear()
        return
    # create an id number for the collection
    collection_id = _text_to_number(collection_name)
    collection_url = \
        http_prefix + '://' + domain + '/collections/' + collection_id
    collection_dict = {
        'attributedTo': actor,
        'discoverable': True,
        'id': actor + '/collections/' + collection_id,
        'name': collection_name,
        'orderedItems': collection_items.copy(),
        'published': published,
        'sensitive': False,
        'summaryMap': {'en': ''},
        'totalItems': len(collection_items),
        'type': 'FeaturedCollection',
        'updated': updated,
        'url': collection_url
    }
    collection['items'].append(collection_dict)
    collection_items.clear()


def get_featured_collections_feed(base_dir: str,
                                  nickname: str, domain: str, port: int,
                                  path: str, http_prefix: str,
                                  authorized: bool) -> {}:
    """Returns the featured collections feed from GET requests.
    Example: https://mastodon.social/ap/users/1/featured_collections?page=1
    """
    ending: str = '/featured_collections'
    if ending not in path:
        return None

    # handle page numbers
    header_only: bool = True
    page_number: int = None
    if '?page=' in path:
        page_number = path.split('?page=')[1]
        if len(page_number) > 5:
            page_number = "1"
        if page_number == 'true' or not authorized:
            page_number = 1
        else:
            try:
                page_number = int(page_number)
            except BaseException:
                print('EX: get_collections_feed unable to convert to int ' +
                      str(page_number))
        path = path.split('?page=')[0]
        header_only: bool = False

    if not path.endswith(ending):
        return None
    nickname = None
    if path.startswith('/users/'):
        nickname = \
            path.replace('/users/', '', 1).replace(ending, '')
    if path.startswith('/@'):
        nickname = path.replace('/@', '', 1).replace(ending, '')
    if not nickname:
        return None
    if not valid_nickname(domain, nickname):
        return None

    domain = get_full_domain(domain, port)

    id_str = \
        local_actor_url(http_prefix, nickname, domain) + ending
    if header_only:
        first_str = \
            local_actor_url(http_prefix, nickname, domain) + \
            ending + '?page=1'
        total_str = \
            _get_no_of_featured_collections(base_dir, nickname, domain)
        collection = {
            "@context": [
                'https://www.w3.org/ns/activitystreams',
                'https://w3id.org/security/v1'
            ],
            'first': first_str,
            'id': id_str,
            'totalItems': total_str,
            'type': 'Collection'
        }
        return collection

    if not page_number:
        page_number = 1

    collection_of_actor = local_actor_url(http_prefix, nickname, domain)
    part_of_str = collection_of_actor + ending
    collection_id = part_of_str + '?page=' + str(page_number)
    collection = {
        "@context": [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1'
        ],
        'id': collection_id,
        'items': [],
        'partOf': part_of_str,
        'totalItems': 0,
        'type': 'CollectionPage'
    }

    handle_domain = domain
    handle_domain = remove_domain_port(handle_domain)
    accounts_dir = acct_dir(base_dir, nickname, handle_domain)
    collection_filename = accounts_dir + ending + '.txt'
    if not is_a_file(collection_filename):
        return collection
    curr_page: int = 1
    lines: list[str] = load_list(collection_filename,
                                 'get_featured_collections_feed ' +
                                 'unable to load list')
    if not lines:
        return collection

    # get file creation date
    published = file_created_date(collection_filename)
    updated = file_last_modified(collection_filename)

    fep_url = 'https://w3id.org/fep/7aa9'
    collection_context = {
        'FeatureAuthorization': fep_url + '#FeatureAuthorization',
        'FeatureRequest': fep_url + '#FeatureRequest',
        'FeaturedCollection': fep_url + '#FeaturedCollection',
        'FeaturedItem': fep_url + '#FeaturedItem',
        'Hashtag': 'as:Hashtag',
        'discoverable': 'toot:discoverable',
        'featureAuthorization': {
            '@id': fep_url + '#featureAuthorization',
            '@type': '@id'
        },
        'featuredObject': {
            '@id': fep_url + '#featuredObject',
            '@type': '@id'
        },
        'sensitive': 'as:sensitive',
        'toot': 'http://joinmastodon.org/ns#',
        'topic': {
            '@id': fep_url + '#topic',
            '@type': '@id'
        }
    }

    collection = {
        '@context': [
            'https://www.w3.org/ns/activitystreams',
            collection_context
        ],
        'id': id_str + '?page=' + str(curr_page),
        'items': [],
        'next': id_str,
        'partOf': id_str,
        'prev': id_str,
        'totalItems': 0,
        'type': 'CollectionPage'
    }

    actor = http_prefix + '://' + domain + '/users/' + nickname

    collection_name = ''
    collection_items: list[dict] = []
    for text in lines:
        if not text:
            continue
        if text.startswith('# '):
            # store the current collection
            _update_collections(collection_name, collection_items,
                                collection,
                                http_prefix, domain,
                                actor, published,
                                updated)
            # get the new collection name
            new_collection_name = text.split('# ', 1)[1]
            collection_name = remove_html(new_collection_name).strip()
            continue
        if not collection_name:
            continue
        # add a collection item
        item_url = ''
        text = remove_html(text)
        if '/tags/' in text:
            # hashtag url
            item_url = text
        else:
            # check that this is an actor url
            item_nickname = get_nickname_from_actor(text)
            item_domain, _ = get_domain_from_actor(text)
            if item_nickname and item_domain:
                item_url = text
        if item_url:
            # id for collection item
            collection_item_id = _text_to_number(item_url)
            # authorization link
            feature_authorization = \
                actor + '/feature_authorizations/' + collection_item_id
            collection_item_dict = {
                'featureAuthorization': feature_authorization,
                'featuredObject': item_url,
                'id': actor + '/collection_items/' + collection_item_id,
                'published': published,
                'type': 'FeaturedItem'
            }
            collection_items.append(collection_item_dict)
    # store the current collection
    _update_collections(collection_name, collection_items,
                        collection,
                        http_prefix, domain,
                        actor, published,
                        updated)

    for collection_dict in lines:
        if not isinstance(collection_dict, dict):
            continue
        collection['items'].append(collection_dict)
        collection['totalItems'] = collection['totalItems'] + 1
    return collection
