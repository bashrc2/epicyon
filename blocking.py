__filename__ = "blocking.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import json
import time
from datetime import datetime
from utils import has_object_string
from utils import has_object_string_object
from utils import has_object_string_type
from utils import remove_domain_port
from utils import has_object_dict
from utils import is_account_dir
from utils import get_cached_post_filename
from utils import load_json
from utils import save_json
from utils import file_last_modified
from utils import set_config_param
from utils import has_users_path
from utils import get_full_domain
from utils import remove_id_ending
from utils import is_evil
from utils import locate_post
from utils import evil_incarnate
from utils import get_domain_from_actor
from utils import get_nickname_from_actor
from utils import acct_dir
from utils import local_actor_url
from utils import has_actor
from utils import text_in_file
from conversation import mute_conversation
from conversation import unmute_conversation


def add_global_block(base_dir: str,
                     block_nickname: str, block_domain: str) -> bool:
    """Global block which applies to all accounts
    """
    blocking_filename = base_dir + '/accounts/blocking.txt'
    if not block_nickname.startswith('#'):
        # is the handle already blocked?
        block_handle = block_nickname + '@' + block_domain
        if os.path.isfile(blocking_filename):
            if text_in_file(block_handle, blocking_filename):
                return False
        # block an account handle or domain
        try:
            with open(blocking_filename, 'a+', encoding='utf-8') as block_file:
                block_file.write(block_handle + '\n')
        except OSError:
            print('EX: unable to save blocked handle ' + block_handle)
            return False
    else:
        block_hashtag = block_nickname
        # is the hashtag already blocked?
        if os.path.isfile(blocking_filename):
            if text_in_file(block_hashtag + '\n', blocking_filename):
                return False
        # block a hashtag
        try:
            with open(blocking_filename, 'a+', encoding='utf-8') as block_file:
                block_file.write(block_hashtag + '\n')
        except OSError:
            print('EX: unable to save blocked hashtag ' + block_hashtag)
            return False
    return True


def add_block(base_dir: str, nickname: str, domain: str,
              block_nickname: str, block_domain: str) -> bool:
    """Block the given account
    """
    if block_domain.startswith(domain) and nickname == block_nickname:
        # don't block self
        return False

    domain = remove_domain_port(domain)
    blocking_filename = acct_dir(base_dir, nickname, domain) + '/blocking.txt'
    block_handle = block_nickname + '@' + block_domain
    if os.path.isfile(blocking_filename):
        if text_in_file(block_handle + '\n', blocking_filename):
            return False

    # if we are following then unfollow
    following_filename = \
        acct_dir(base_dir, nickname, domain) + '/following.txt'
    if os.path.isfile(following_filename):
        if text_in_file(block_handle + '\n', following_filename):
            following_str = ''
            try:
                with open(following_filename, 'r',
                          encoding='utf-8') as foll_file:
                    following_str = foll_file.read()
            except OSError:
                print('EX: Unable to read following ' + following_filename)
                return False

            if following_str:
                following_str = following_str.replace(block_handle + '\n', '')

            try:
                with open(following_filename, 'w+',
                          encoding='utf-8') as foll_file:
                    foll_file.write(following_str)
            except OSError:
                print('EX: Unable to write following ' + following_str)
                return False

    # if they are a follower then remove them
    followers_filename = \
        acct_dir(base_dir, nickname, domain) + '/followers.txt'
    if os.path.isfile(followers_filename):
        if text_in_file(block_handle + '\n', followers_filename):
            followers_str = ''
            try:
                with open(followers_filename, 'r',
                          encoding='utf-8') as foll_file:
                    followers_str = foll_file.read()
            except OSError:
                print('EX: Unable to read followers ' + followers_filename)
                return False

            if followers_str:
                followers_str = followers_str.replace(block_handle + '\n', '')

            try:
                with open(followers_filename, 'w+',
                          encoding='utf-8') as foll_file:
                    foll_file.write(followers_str)
            except OSError:
                print('EX: Unable to write followers ' + followers_str)
                return False

    try:
        with open(blocking_filename, 'a+', encoding='utf-8') as block_file:
            block_file.write(block_handle + '\n')
    except OSError:
        print('EX: unable to append block handle ' + block_handle)
        return False
    return True


def remove_global_block(base_dir: str,
                        unblock_nickname: str,
                        unblock_domain: str) -> bool:
    """Unblock the given global block
    """
    unblocking_filename = base_dir + '/accounts/blocking.txt'
    if not unblock_nickname.startswith('#'):
        unblock_handle = unblock_nickname + '@' + unblock_domain
        if os.path.isfile(unblocking_filename):
            if text_in_file(unblock_handle, unblocking_filename):
                try:
                    with open(unblocking_filename, 'r',
                              encoding='utf-8') as fp_unblock:
                        with open(unblocking_filename + '.new', 'w+',
                                  encoding='utf-8') as fpnew:
                            for line in fp_unblock:
                                handle = \
                                    line.replace('\n', '').replace('\r', '')
                                if unblock_handle not in line:
                                    fpnew.write(handle + '\n')
                except OSError as ex:
                    print('EX: failed to remove global block ' +
                          unblocking_filename + ' ' + str(ex))
                    return False

                if os.path.isfile(unblocking_filename + '.new'):
                    try:
                        os.rename(unblocking_filename + '.new',
                                  unblocking_filename)
                    except OSError:
                        print('EX: unable to rename ' + unblocking_filename)
                        return False
                    return True
    else:
        unblock_hashtag = unblock_nickname
        if os.path.isfile(unblocking_filename):
            if text_in_file(unblock_hashtag + '\n', unblocking_filename):
                try:
                    with open(unblocking_filename, 'r',
                              encoding='utf-8') as fp_unblock:
                        with open(unblocking_filename + '.new', 'w+',
                                  encoding='utf-8') as fpnew:
                            for line in fp_unblock:
                                block_line = \
                                    line.replace('\n', '').replace('\r', '')
                                if unblock_hashtag not in line:
                                    fpnew.write(block_line + '\n')
                except OSError as ex:
                    print('EX: failed to remove global hashtag block ' +
                          unblocking_filename + ' ' + str(ex))
                    return False

                if os.path.isfile(unblocking_filename + '.new'):
                    try:
                        os.rename(unblocking_filename + '.new',
                                  unblocking_filename)
                    except OSError:
                        print('EX: unable to rename 2 ' + unblocking_filename)
                        return False
                    return True
    return False


def remove_block(base_dir: str, nickname: str, domain: str,
                 unblock_nickname: str, unblock_domain: str) -> bool:
    """Unblock the given account
    """
    domain = remove_domain_port(domain)
    unblocking_filename = \
        acct_dir(base_dir, nickname, domain) + '/blocking.txt'
    unblock_handle = unblock_nickname + '@' + unblock_domain
    if os.path.isfile(unblocking_filename):
        if text_in_file(unblock_handle, unblocking_filename):
            try:
                with open(unblocking_filename, 'r',
                          encoding='utf-8') as fp_unblock:
                    with open(unblocking_filename + '.new', 'w+',
                              encoding='utf-8') as fpnew:
                        for line in fp_unblock:
                            handle = line.replace('\n', '').replace('\r', '')
                            if unblock_handle not in line:
                                fpnew.write(handle + '\n')
            except OSError as ex:
                print('EX: failed to remove block ' +
                      unblocking_filename + ' ' + str(ex))
                return False

            if os.path.isfile(unblocking_filename + '.new'):
                try:
                    os.rename(unblocking_filename + '.new',
                              unblocking_filename)
                except OSError:
                    print('EX: unable to rename 3 ' + unblocking_filename)
                    return False
                return True
    return False


def is_blocked_hashtag(base_dir: str, hashtag: str) -> bool:
    """Is the given hashtag blocked?
    """
    # avoid very long hashtags
    if len(hashtag) > 32:
        return True
    global_blocking_filename = base_dir + '/accounts/blocking.txt'
    if os.path.isfile(global_blocking_filename):
        hashtag = hashtag.strip('\n').strip('\r')
        if not hashtag.startswith('#'):
            hashtag = '#' + hashtag
        if text_in_file(hashtag + '\n', global_blocking_filename):
            return True
    return False


def get_domain_blocklist(base_dir: str) -> str:
    """Returns all globally blocked domains as a string
    This can be used for fast matching to mitigate flooding
    """
    blocked_str = ''

    evil_domains = evil_incarnate()
    for evil in evil_domains:
        blocked_str += evil + '\n'

    global_blocking_filename = base_dir + '/accounts/blocking.txt'
    if not os.path.isfile(global_blocking_filename):
        return blocked_str
    try:
        with open(global_blocking_filename, 'r',
                  encoding='utf-8') as fp_blocked:
            blocked_str += fp_blocked.read()
    except OSError:
        print('EX: unable to read ' + global_blocking_filename)
    return blocked_str


def update_blocked_cache(base_dir: str,
                         blocked_cache: [],
                         blocked_cache_last_updated: int,
                         blocked_cache_update_secs: int) -> int:
    """Updates the cache of globally blocked domains held in memory
    """
    curr_time = int(time.time())
    if blocked_cache_last_updated > curr_time:
        print('WARN: Cache updated in the future')
        blocked_cache_last_updated = 0
    seconds_since_last_update = curr_time - blocked_cache_last_updated
    if seconds_since_last_update < blocked_cache_update_secs:
        return blocked_cache_last_updated
    global_blocking_filename = base_dir + '/accounts/blocking.txt'
    if not os.path.isfile(global_blocking_filename):
        return blocked_cache_last_updated
    try:
        with open(global_blocking_filename, 'r',
                  encoding='utf-8') as fp_blocked:
            blocked_lines = fp_blocked.readlines()
            # remove newlines
            for index, _ in enumerate(blocked_lines):
                blocked_lines[index] = blocked_lines[index].replace('\n', '')
            # update the cache
            blocked_cache.clear()
            blocked_cache += blocked_lines
    except OSError as ex:
        print('EX: unable to read ' + global_blocking_filename + ' ' + str(ex))
    return curr_time


def _get_short_domain(domain: str) -> str:
    """ by checking a shorter version we can thwart adversaries
    who constantly change their subdomain
    e.g. subdomain123.mydomain.com becomes mydomain.com
    """
    sections = domain.split('.')
    no_of_sections = len(sections)
    if no_of_sections > 2:
        return sections[no_of_sections-2] + '.' + sections[-1]
    return None


def is_blocked_domain(base_dir: str, domain: str,
                      blocked_cache: [] = None) -> bool:
    """Is the given domain blocked?
    """
    if '.' not in domain:
        return False

    if is_evil(domain):
        return True

    short_domain = _get_short_domain(domain)

    if not broch_mode_is_active(base_dir):
        if blocked_cache:
            for blocked_str in blocked_cache:
                if blocked_str == '*@' + domain:
                    return True
                if short_domain:
                    if blocked_str == '*@' + short_domain:
                        return True
        else:
            # instance block list
            global_blocking_filename = base_dir + '/accounts/blocking.txt'
            if os.path.isfile(global_blocking_filename):
                try:
                    with open(global_blocking_filename, 'r',
                              encoding='utf-8') as fp_blocked:
                        blocked_str = fp_blocked.read()
                        if '*@' + domain + '\n' in blocked_str:
                            return True
                        if short_domain:
                            if '*@' + short_domain + '\n' in blocked_str:
                                return True
                except OSError as ex:
                    print('EX: unable to read ' + global_blocking_filename +
                          ' ' + str(ex))
    else:
        allow_filename = base_dir + '/accounts/allowedinstances.txt'
        # instance allow list
        if not short_domain:
            if not text_in_file(domain, allow_filename):
                return True
        else:
            if not text_in_file(short_domain, allow_filename):
                return True

    return False


def is_blocked(base_dir: str, nickname: str, domain: str,
               block_nickname: str, block_domain: str,
               blocked_cache: [] = None) -> bool:
    """Is the given nickname blocked?
    """
    if is_evil(block_domain):
        return True

    block_handle = None
    if block_nickname and block_domain:
        block_handle = block_nickname + '@' + block_domain

    if not broch_mode_is_active(base_dir):
        # instance level block list
        if blocked_cache:
            for blocked_str in blocked_cache:
                if '*@' + domain in blocked_str:
                    return True
                if block_handle:
                    if blocked_str == block_handle:
                        return True
        else:
            global_blocks_filename = base_dir + '/accounts/blocking.txt'
            if os.path.isfile(global_blocks_filename):
                if text_in_file('*@' + block_domain, global_blocks_filename):
                    return True
                if block_handle:
                    block_str = block_handle + '\n'
                    if text_in_file(block_str, global_blocks_filename):
                        return True
    else:
        # instance allow list
        allow_filename = base_dir + '/accounts/allowedinstances.txt'
        short_domain = _get_short_domain(block_domain)
        if not short_domain:
            if not text_in_file(block_domain + '\n', allow_filename):
                return True
        else:
            if not text_in_file(short_domain + '\n', allow_filename):
                return True

    # account level allow list
    account_dir = acct_dir(base_dir, nickname, domain)
    allow_filename = account_dir + '/allowedinstances.txt'
    if os.path.isfile(allow_filename):
        if not text_in_file(block_domain + '\n', allow_filename):
            return True

    # account level block list
    blocking_filename = account_dir + '/blocking.txt'
    if os.path.isfile(blocking_filename):
        if text_in_file('*@' + block_domain + '\n', blocking_filename):
            return True
        if block_handle:
            if text_in_file(block_handle + '\n', blocking_filename):
                return True
    return False


def outbox_block(base_dir: str, nickname: str, domain: str,
                 message_json: {}, debug: bool) -> bool:
    """ When a block request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        if debug:
            print('DEBUG: block - no type')
        return False
    if not message_json['type'] == 'Block':
        if debug:
            print('DEBUG: not a block')
        return False
    if not has_object_string(message_json, debug):
        return False
    if debug:
        print('DEBUG: c2s block request arrived in outbox')

    message_id = remove_id_ending(message_json['object'])
    if '/statuses/' not in message_id:
        if debug:
            print('DEBUG: c2s block object is not a status')
        return False
    if not has_users_path(message_id):
        if debug:
            print('DEBUG: c2s block object has no nickname')
        return False
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, message_id)
    if not post_filename:
        if debug:
            print('DEBUG: c2s block post not found in inbox or outbox')
            print(message_id)
        return False
    nickname_blocked = get_nickname_from_actor(message_json['object'])
    if not nickname_blocked:
        print('WARN: unable to find nickname in ' + message_json['object'])
        return False
    domain_blocked, port_blocked = \
        get_domain_from_actor(message_json['object'])
    domain_blocked_full = get_full_domain(domain_blocked, port_blocked)

    add_block(base_dir, nickname, domain,
              nickname_blocked, domain_blocked_full)

    if debug:
        print('DEBUG: post blocked via c2s - ' + post_filename)
    return True


def outbox_undo_block(base_dir: str, nickname: str, domain: str,
                      message_json: {}, debug: bool) -> None:
    """ When an undo block request is received by the outbox from c2s
    """
    if not message_json.get('type'):
        if debug:
            print('DEBUG: undo block - no type')
        return
    if not message_json['type'] == 'Undo':
        if debug:
            print('DEBUG: not an undo block')
        return

    if not has_object_string_type(message_json, debug):
        return
    if not message_json['object']['type'] == 'Block':
        if debug:
            print('DEBUG: not an undo block')
        return
    if not has_object_string_object(message_json, debug):
        return
    if debug:
        print('DEBUG: c2s undo block request arrived in outbox')

    message_id = remove_id_ending(message_json['object']['object'])
    if '/statuses/' not in message_id:
        if debug:
            print('DEBUG: c2s undo block object is not a status')
        return
    if not has_users_path(message_id):
        if debug:
            print('DEBUG: c2s undo block object has no nickname')
        return
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, message_id)
    if not post_filename:
        if debug:
            print('DEBUG: c2s undo block post not found in inbox or outbox')
            print(message_id)
        return
    nickname_blocked = \
        get_nickname_from_actor(message_json['object']['object'])
    if not nickname_blocked:
        print('WARN: unable to find nickname in ' +
              message_json['object']['object'])
        return
    domain_object = message_json['object']['object']
    domain_blocked, port_blocked = get_domain_from_actor(domain_object)
    domain_blocked_full = get_full_domain(domain_blocked, port_blocked)

    remove_block(base_dir, nickname, domain,
                 nickname_blocked, domain_blocked_full)
    if debug:
        print('DEBUG: post undo blocked via c2s - ' + post_filename)


def mute_post(base_dir: str, nickname: str, domain: str, port: int,
              http_prefix: str, post_id: str, recent_posts_cache: {},
              debug: bool) -> None:
    """ Mutes the given post
    """
    print('mute_post: post_id ' + post_id)
    post_filename = locate_post(base_dir, nickname, domain, post_id)
    if not post_filename:
        print('mute_post: file not found ' + post_id)
        return
    post_json_object = load_json(post_filename)
    if not post_json_object:
        print('mute_post: object not loaded ' + post_id)
        return
    print('mute_post: ' + str(post_json_object))

    post_json_obj = post_json_object
    also_update_post_id = None
    if has_object_dict(post_json_object):
        post_json_obj = post_json_object['object']
    else:
        if has_object_string(post_json_object, debug):
            also_update_post_id = remove_id_ending(post_json_object['object'])

    domain_full = get_full_domain(domain, port)
    actor = local_actor_url(http_prefix, nickname, domain_full)

    if post_json_obj.get('conversation'):
        mute_conversation(base_dir, nickname, domain,
                          post_json_obj['conversation'])

    # does this post have ignores on it from differenent actors?
    if not post_json_obj.get('ignores'):
        if debug:
            print('DEBUG: Adding initial mute to ' + post_id)
        ignores_json = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'id': post_id,
            'type': 'Collection',
            "totalItems": 1,
            'items': [{
                'type': 'Ignore',
                'actor': actor
            }]
        }
        post_json_obj['ignores'] = ignores_json
    else:
        if not post_json_obj['ignores'].get('items'):
            post_json_obj['ignores']['items'] = []
        items_list = post_json_obj['ignores']['items']
        for ignores_item in items_list:
            if ignores_item.get('actor'):
                if ignores_item['actor'] == actor:
                    return
        new_ignore = {
            'type': 'Ignore',
            'actor': actor
        }
        ig_it = len(items_list)
        items_list.append(new_ignore)
        post_json_obj['ignores']['totalItems'] = ig_it
    post_json_obj['muted'] = True
    if save_json(post_json_object, post_filename):
        print('mute_post: saved ' + post_filename)

    # remove cached post so that the muted version gets recreated
    # without its content text and/or image
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain, post_json_object)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
                print('MUTE: cached post removed ' + cached_post_filename)
            except OSError:
                print('EX: MUTE cached post not removed ' +
                      cached_post_filename)
        else:
            print('MUTE: cached post not found ' + cached_post_filename)

    try:
        with open(post_filename + '.muted', 'w+',
                  encoding='utf-8') as mute_file:
            mute_file.write('\n')
    except OSError:
        print('EX: Failed to save mute file ' + post_filename + '.muted')
        return
    print('MUTE: ' + post_filename + '.muted file added')

    # if the post is in the recent posts cache then mark it as muted
    if recent_posts_cache.get('index'):
        post_id = \
            remove_id_ending(post_json_object['id']).replace('/', '#')
        if post_id in recent_posts_cache['index']:
            print('MUTE: ' + post_id + ' is in recent posts cache')
        if recent_posts_cache.get('json'):
            recent_posts_cache['json'][post_id] = json.dumps(post_json_object)
            print('MUTE: ' + post_id +
                  ' marked as muted in recent posts memory cache')
        if recent_posts_cache.get('html'):
            if recent_posts_cache['html'].get(post_id):
                del recent_posts_cache['html'][post_id]
                print('MUTE: ' + post_id + ' removed cached html')

    if also_update_post_id:
        post_filename = locate_post(base_dir, nickname, domain,
                                    also_update_post_id)
        if os.path.isfile(post_filename):
            post_json_obj = load_json(post_filename)
            cached_post_filename = \
                get_cached_post_filename(base_dir, nickname, domain,
                                         post_json_obj)
            if cached_post_filename:
                if os.path.isfile(cached_post_filename):
                    try:
                        os.remove(cached_post_filename)
                        print('MUTE: cached referenced post removed ' +
                              cached_post_filename)
                    except OSError:
                        print('EX: ' +
                              'MUTE cached referenced post not removed ' +
                              cached_post_filename)

        if recent_posts_cache.get('json'):
            if recent_posts_cache['json'].get(also_update_post_id):
                del recent_posts_cache['json'][also_update_post_id]
                print('MUTE: ' + also_update_post_id +
                      ' removed referenced json')
        if recent_posts_cache.get('html'):
            if recent_posts_cache['html'].get(also_update_post_id):
                del recent_posts_cache['html'][also_update_post_id]
                print('MUTE: ' + also_update_post_id +
                      ' removed referenced html')


def unmute_post(base_dir: str, nickname: str, domain: str, port: int,
                http_prefix: str, post_id: str, recent_posts_cache: {},
                debug: bool) -> None:
    """ Unmutes the given post
    """
    post_filename = locate_post(base_dir, nickname, domain, post_id)
    if not post_filename:
        return
    post_json_object = load_json(post_filename)
    if not post_json_object:
        return

    mute_filename = post_filename + '.muted'
    if os.path.isfile(mute_filename):
        try:
            os.remove(mute_filename)
        except OSError:
            if debug:
                print('EX: unmute_post mute filename not deleted ' +
                      str(mute_filename))
        print('UNMUTE: ' + mute_filename + ' file removed')

    post_json_obj = post_json_object
    also_update_post_id = None
    if has_object_dict(post_json_object):
        post_json_obj = post_json_object['object']
    else:
        if has_object_string(post_json_object, debug):
            also_update_post_id = remove_id_ending(post_json_object['object'])

    if post_json_obj.get('conversation'):
        unmute_conversation(base_dir, nickname, domain,
                            post_json_obj['conversation'])

    if post_json_obj.get('ignores'):
        domain_full = get_full_domain(domain, port)
        actor = local_actor_url(http_prefix, nickname, domain_full)
        total_items = 0
        if post_json_obj['ignores'].get('totalItems'):
            total_items = post_json_obj['ignores']['totalItems']
        items_list = post_json_obj['ignores']['items']
        for ignores_item in items_list:
            if ignores_item.get('actor'):
                if ignores_item['actor'] == actor:
                    if debug:
                        print('DEBUG: mute was removed for ' + actor)
                    items_list.remove(ignores_item)
                    break
        if total_items == 1:
            if debug:
                print('DEBUG: mute was removed from post')
            del post_json_obj['ignores']
        else:
            ig_it_len = len(post_json_obj['ignores']['items'])
            post_json_obj['ignores']['totalItems'] = ig_it_len
    post_json_obj['muted'] = False
    save_json(post_json_object, post_filename)

    # remove cached post so that the muted version gets recreated
    # with its content text and/or image
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain, post_json_object)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                if debug:
                    print('EX: unmute_post cached post not deleted ' +
                          str(cached_post_filename))

    # if the post is in the recent posts cache then mark it as unmuted
    if recent_posts_cache.get('index'):
        post_id = \
            remove_id_ending(post_json_object['id']).replace('/', '#')
        if post_id in recent_posts_cache['index']:
            print('UNMUTE: ' + post_id + ' is in recent posts cache')
        if recent_posts_cache.get('json'):
            recent_posts_cache['json'][post_id] = json.dumps(post_json_object)
            print('UNMUTE: ' + post_id +
                  ' marked as unmuted in recent posts cache')
        if recent_posts_cache.get('html'):
            if recent_posts_cache['html'].get(post_id):
                del recent_posts_cache['html'][post_id]
                print('UNMUTE: ' + post_id + ' removed cached html')
    if also_update_post_id:
        post_filename = locate_post(base_dir, nickname, domain,
                                    also_update_post_id)
        if os.path.isfile(post_filename):
            post_json_obj = load_json(post_filename)
            cached_post_filename = \
                get_cached_post_filename(base_dir, nickname, domain,
                                         post_json_obj)
            if cached_post_filename:
                if os.path.isfile(cached_post_filename):
                    try:
                        os.remove(cached_post_filename)
                        print('MUTE: cached referenced post removed ' +
                              cached_post_filename)
                    except OSError:
                        if debug:
                            print('EX: ' +
                                  'unmute_post cached ref post not removed ' +
                                  str(cached_post_filename))

        if recent_posts_cache.get('json'):
            if recent_posts_cache['json'].get(also_update_post_id):
                del recent_posts_cache['json'][also_update_post_id]
                print('UNMUTE: ' +
                      also_update_post_id + ' removed referenced json')
        if recent_posts_cache.get('html'):
            if recent_posts_cache['html'].get(also_update_post_id):
                del recent_posts_cache['html'][also_update_post_id]
                print('UNMUTE: ' +
                      also_update_post_id + ' removed referenced html')


def outbox_mute(base_dir: str, http_prefix: str,
                nickname: str, domain: str, port: int,
                message_json: {}, debug: bool,
                recent_posts_cache: {}) -> None:
    """When a mute is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if not has_actor(message_json, debug):
        return
    domain_full = get_full_domain(domain, port)
    if not message_json['actor'].endswith(domain_full + '/users/' + nickname):
        return
    if not message_json['type'] == 'Ignore':
        return
    if not has_object_string(message_json, debug):
        return
    if debug:
        print('DEBUG: c2s mute request arrived in outbox')

    message_id = remove_id_ending(message_json['object'])
    if '/statuses/' not in message_id:
        if debug:
            print('DEBUG: c2s mute object is not a status')
        return
    if not has_users_path(message_id):
        if debug:
            print('DEBUG: c2s mute object has no nickname')
        return
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, message_id)
    if not post_filename:
        if debug:
            print('DEBUG: c2s mute post not found in inbox or outbox')
            print(message_id)
        return
    nickname_muted = get_nickname_from_actor(message_json['object'])
    if not nickname_muted:
        print('WARN: unable to find nickname in ' + message_json['object'])
        return

    mute_post(base_dir, nickname, domain, port,
              http_prefix, message_json['object'], recent_posts_cache,
              debug)

    if debug:
        print('DEBUG: post muted via c2s - ' + post_filename)


def outbox_undo_mute(base_dir: str, http_prefix: str,
                     nickname: str, domain: str, port: int,
                     message_json: {}, debug: bool,
                     recent_posts_cache: {}) -> None:
    """When an undo mute is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if not has_actor(message_json, debug):
        return
    domain_full = get_full_domain(domain, port)
    if not message_json['actor'].endswith(domain_full + '/users/' + nickname):
        return
    if not message_json['type'] == 'Undo':
        return
    if not has_object_string_type(message_json, debug):
        return
    if message_json['object']['type'] != 'Ignore':
        return
    if not isinstance(message_json['object']['object'], str):
        if debug:
            print('DEBUG: undo mute object is not a string')
        return
    if debug:
        print('DEBUG: c2s undo mute request arrived in outbox')

    message_id = remove_id_ending(message_json['object']['object'])
    if '/statuses/' not in message_id:
        if debug:
            print('DEBUG: c2s undo mute object is not a status')
        return
    if not has_users_path(message_id):
        if debug:
            print('DEBUG: c2s undo mute object has no nickname')
        return
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, message_id)
    if not post_filename:
        if debug:
            print('DEBUG: c2s undo mute post not found in inbox or outbox')
            print(message_id)
        return
    nickname_muted = get_nickname_from_actor(message_json['object']['object'])
    if not nickname_muted:
        print('WARN: unable to find nickname in ' +
              message_json['object']['object'])
        return

    unmute_post(base_dir, nickname, domain, port,
                http_prefix, message_json['object']['object'],
                recent_posts_cache, debug)

    if debug:
        print('DEBUG: post undo mute via c2s - ' + post_filename)


def broch_mode_is_active(base_dir: str) -> bool:
    """Returns true if broch mode is active
    """
    allow_filename = base_dir + '/accounts/allowedinstances.txt'
    return os.path.isfile(allow_filename)


def set_broch_mode(base_dir: str, domain_full: str, enabled: bool) -> None:
    """Broch mode can be used to lock down the instance during
    a period of time when it is temporarily under attack.
    For example, where an adversary is constantly spinning up new
    instances.
    It surveys the following lists of all accounts and uses that
    to construct an instance level allow list. Anything arriving
    which is then not from one of the allowed domains will be dropped
    """
    allow_filename = base_dir + '/accounts/allowedinstances.txt'

    if not enabled:
        # remove instance allow list
        if os.path.isfile(allow_filename):
            try:
                os.remove(allow_filename)
            except OSError:
                print('EX: set_broch_mode allow file not deleted ' +
                      str(allow_filename))
            print('Broch mode turned off')
    else:
        if os.path.isfile(allow_filename):
            last_modified = file_last_modified(allow_filename)
            print('Broch mode already activated ' + last_modified)
            return
        # generate instance allow list
        allowed_domains = [domain_full]
        follow_files = ('following.txt', 'followers.txt')
        for _, dirs, _ in os.walk(base_dir + '/accounts'):
            for acct in dirs:
                if not is_account_dir(acct):
                    continue
                account_dir = os.path.join(base_dir + '/accounts', acct)
                for follow_file_type in follow_files:
                    following_filename = account_dir + '/' + follow_file_type
                    if not os.path.isfile(following_filename):
                        continue
                    try:
                        with open(following_filename, 'r',
                                  encoding='utf-8') as foll_file:
                            follow_list = foll_file.readlines()
                            for handle in follow_list:
                                if '@' not in handle:
                                    continue
                                handle = handle.replace('\n', '')
                                handle_domain = handle.split('@')[1]
                                if handle_domain not in allowed_domains:
                                    allowed_domains.append(handle_domain)
                    except OSError as ex:
                        print('EX: failed to read ' + following_filename +
                              ' ' + str(ex))
            break

        # write the allow file
        try:
            with open(allow_filename, 'w+',
                      encoding='utf-8') as allow_file:
                allow_file.write(domain_full + '\n')
                for allowed in allowed_domains:
                    allow_file.write(allowed + '\n')
                print('Broch mode enabled')
        except OSError as ex:
            print('EX: Broch mode not enabled due to file write ' + str(ex))
            return

    set_config_param(base_dir, "brochMode", enabled)


def broch_modeLapses(base_dir: str, lapseDays: int) -> bool:
    """After broch mode is enabled it automatically
    elapses after a period of time
    """
    allow_filename = base_dir + '/accounts/allowedinstances.txt'
    if not os.path.isfile(allow_filename):
        return False
    last_modified = file_last_modified(allow_filename)
    modified_date = None
    try:
        modified_date = \
            datetime.strptime(last_modified, "%Y-%m-%dT%H:%M:%SZ")
    except BaseException:
        print('EX: broch_modeLapses date not parsed ' + str(last_modified))
        return False
    if not modified_date:
        return False
    curr_time = datetime.datetime.utcnow()
    days_since_broch = (curr_time - modified_date).days
    if days_since_broch >= lapseDays:
        removed = False
        try:
            os.remove(allow_filename)
            removed = True
        except OSError:
            print('EX: broch_modeLapses allow file not deleted ' +
                  str(allow_filename))
        if removed:
            set_config_param(base_dir, "brochMode", False)
            print('Broch mode has elapsed')
            return True
    return False


def load_cw_lists(base_dir: str, verbose: bool) -> {}:
    """Load lists used for content warnings
    """
    if not os.path.isdir(base_dir + '/cwlists'):
        return {}
    result = {}
    for _, _, files in os.walk(base_dir + '/cwlists'):
        for fname in files:
            if not fname.endswith('.json'):
                continue
            list_filename = os.path.join(base_dir + '/cwlists', fname)
            print('list_filename: ' + list_filename)
            list_json = load_json(list_filename, 0, 1)
            if not list_json:
                continue
            if not list_json.get('name'):
                continue
            if not list_json.get('words') and not list_json.get('domains'):
                continue
            name = list_json['name']
            if verbose:
                print('List: ' + name)
            result[name] = list_json
    return result


def add_cw_from_lists(post_json_object: {}, cw_lists: {}, translate: {},
                      lists_enabled: str, system_language: str) -> None:
    """Adds content warnings by matching the post content
    against domains or keywords
    """
    if not lists_enabled:
        return
    if not post_json_object['object'].get('content'):
        if not post_json_object['object'].get('contentMap'):
            return
    cw_text = ''
    if post_json_object['object'].get('summary'):
        cw_text = post_json_object['object']['summary']

    content = None
    if post_json_object['object'].get('contentMap'):
        if post_json_object['object']['contentMap'].get(system_language):
            content = \
                post_json_object['object']['contentMap'][system_language]
    if not content:
        if post_json_object['object'].get('content'):
            content = post_json_object['object']['content']
    if not content:
        return
    for name, item in cw_lists.items():
        if name not in lists_enabled:
            continue
        if not item.get('warning'):
            continue
        warning = item['warning']

        # is there a translated version of the warning?
        if translate.get(warning):
            warning = translate[warning]

        # is the warning already in the CW?
        if warning in cw_text:
            continue

        matched = False

        # match domains within the content
        if item.get('domains'):
            for domain in item['domains']:
                if domain in content:
                    if cw_text:
                        cw_text = warning + ' / ' + cw_text
                    else:
                        cw_text = warning
                    matched = True
                    break

        if matched:
            continue

        # match words within the content
        if item.get('words'):
            for word_str in item['words']:
                if word_str in content:
                    if cw_text:
                        cw_text = warning + ' / ' + cw_text
                    else:
                        cw_text = warning
                    break
    if cw_text:
        post_json_object['object']['summary'] = cw_text
        post_json_object['object']['sensitive'] = True


def get_cw_list_variable(list_name: str) -> str:
    """Returns the variable associated with a CW list
    """
    return 'list' + list_name.replace(' ', '').replace("'", '')
