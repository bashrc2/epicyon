__filename__ = "inbox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import json
import os
import datetime
import time
import random
from shutil import copyfile
from linked_data_sig import verify_json_signature
from languages import understood_post_language
from like import update_likes_collection
from reaction import update_reaction_collection
from reaction import valid_emoji_content
from utils import remove_eol
from utils import text_in_file
from utils import get_media_descriptions_from_post
from utils import get_summary_from_post
from utils import delete_cached_html
from utils import get_account_timezone
from utils import domain_permitted
from utils import is_group_account
from utils import is_system_account
from utils import invalid_ciphertext
from utils import remove_html
from utils import file_last_modified
from utils import has_object_string
from utils import has_object_string_object
from utils import get_reply_interval_hours
from utils import can_reply_to
from utils import get_user_paths
from utils import get_base_content_from_post
from utils import acct_dir
from utils import remove_domain_port
from utils import get_port_from_domain
from utils import has_object_dict
from utils import dm_allowed_from_domain
from utils import is_recent_post
from utils import get_config_param
from utils import has_users_path
from utils import valid_post_date
from utils import get_full_domain
from utils import remove_id_ending
from utils import get_protocol_prefixes
from utils import is_blog_post
from utils import remove_avatar_from_cache
from utils import is_public_post
from utils import get_cached_post_filename
from utils import remove_post_from_cache
from utils import url_permitted
from utils import create_inbox_queue_dir
from utils import get_status_number
from utils import get_domain_from_actor
from utils import get_nickname_from_actor
from utils import locate_post
from utils import delete_post
from utils import remove_moderation_post_from_index
from utils import load_json
from utils import save_json
from utils import undo_likes_collection_entry
from utils import undo_reaction_collection_entry
from utils import has_group_type
from utils import local_actor_url
from utils import has_object_string_type
from utils import valid_hash_tag
from categories import get_hashtag_categories
from categories import set_hashtag_category
from httpsig import get_digest_algorithm_from_headers
from httpsig import verify_post_headers
from session import create_session
from session import download_image
from follow import follower_approval_active
from follow import is_following_actor
from follow import get_followers_of_actor
from follow import unfollower_of_account
from follow import is_follower_of_person
from follow import followed_account_accepts
from follow import store_follow_request
from follow import no_of_follow_requests
from follow import get_no_of_followers
from follow import follow_approval_required
from pprint import pprint
from cache import store_person_in_cache
from cache import get_person_pub_key
from acceptreject import receive_accept_reject
from bookmarks import update_bookmarks_collection
from bookmarks import undo_bookmarks_collection_entry
from blocking import is_blocked
from blocking import is_blocked_domain
from blocking import broch_modeLapses
from filters import is_filtered
from utils import update_announce_collection
from utils import undo_announce_collection_entry
from utils import dangerous_markup
from utils import is_dm
from utils import is_reply
from utils import has_actor
from httpsig import message_content_digest
from posts import edited_post_filename
from posts import save_post_to_box
from posts import is_create_inside_announce
from posts import create_direct_message_post
from posts import valid_content_warning
from posts import download_announce
from posts import is_muted_conv
from posts import is_image_media
from posts import send_signed_json
from posts import send_to_followers_thread
from webapp_post import individual_post_as_html
from question import question_update_votes
from media import replace_you_tube
from media import replace_twitter
from git import is_git_patch
from git import receive_git_patch
from followingCalendar import receiving_calendar_events
from happening import save_event_post
from delete import remove_old_hashtags
from categories import guess_hashtag_category
from context import has_valid_context
from speaker import update_speaker
from announce import is_self_announce
from announce import create_announce
from notifyOnPost import notify_when_person_posts
from conversation import update_conversation
from webapp_hashtagswarm import html_hash_tag_swarm
from person import valid_sending_actor
from fitnessFunctions import fitness_performance
from content import reject_twitter_summary
from content import load_dogwhistles
from content import valid_url_lengths
from content import remove_script
from threads import begin_thread
from maps import get_map_links_from_post_content
from maps import get_location_from_tags
from maps import add_tag_map_links
from maps import geocoords_from_map_link


def cache_svg_images(session, base_dir: str, http_prefix: str,
                     nickname: str, domain: str, domain_full: str,
                     onion_domain: str, i2p_domain: str,
                     post_json_object: {},
                     federation_list: [], debug: bool,
                     test_image_filename: str) -> bool:
    """Creates a local copy of a remote svg file
    """
    if has_object_dict(post_json_object):
        obj = post_json_object['object']
    else:
        obj = post_json_object
    if not obj.get('id'):
        return False
    if not obj.get('attachment'):
        return False
    if not isinstance(obj['attachment'], list):
        return False
    cached = False
    post_id = remove_id_ending(obj['id']).replace('/', '--')
    actor = 'unknown'
    if obj.get('attributedTo'):
        actor = obj['attributedTo']
    log_filename = base_dir + '/accounts/svg_scripts_log.txt'
    for index in range(len(obj['attachment'])):
        attach = obj['attachment'][index]
        if not attach.get('mediaType'):
            continue
        if not attach.get('url'):
            continue
        if attach['url'].endswith('.svg') or \
           'svg' in attach['mediaType']:
            url = attach['url']
            if not url_permitted(url, federation_list):
                continue
            # if this is a local image then it has already been
            # validated on upload
            if '://' + domain in url:
                continue
            if onion_domain:
                if '://' + onion_domain in url:
                    continue
            if i2p_domain:
                if '://' + i2p_domain in url:
                    continue
            if '/' in url:
                filename = url.split('/')[-1]
            else:
                filename = url
            if not test_image_filename:
                image_filename = \
                    base_dir + '/media/' + post_id + '_' + filename
                if not download_image(session, url,
                                      image_filename, debug):
                    continue
            else:
                image_filename = test_image_filename
            image_data = None
            try:
                with open(image_filename, 'rb') as fp_svg:
                    image_data = fp_svg.read()
            except OSError:
                print('EX: unable to read svg file data')
            if not image_data:
                continue
            image_data = image_data.decode()
            cleaned_up = \
                remove_script(image_data, log_filename, actor, url)
            if cleaned_up != image_data:
                # write the cleaned up svg image
                svg_written = False
                cleaned_up = cleaned_up.encode('utf-8')
                try:
                    with open(image_filename, 'wb') as im_file:
                        im_file.write(cleaned_up)
                        svg_written = True
                except OSError:
                    print('EX: unable to write cleaned up svg ' + url)
                if svg_written:
                    # change the url to be the local version
                    obj['attachment'][index]['url'] = \
                        http_prefix + '://' + domain_full + '/media/' + \
                        post_id + '_' + filename
                    cached = True
            else:
                cached = True
    return cached


def _store_last_post_id(base_dir: str, nickname: str, domain: str,
                        post_json_object: {}) -> None:
    """Stores the id of the last post made by an actor
    When a new post arrives this allows it to be compared against the last
    to see if it is an edited post.
    It would be great if edited posts contained a back reference id to the
    source but we don't live in that ideal world.
    """
    actor = post_id = None
    if has_object_dict(post_json_object):
        if post_json_object['object'].get('attributedTo'):
            if isinstance(post_json_object['object']['attributedTo'], str):
                actor = post_json_object['object']['attributedTo']
                post_id = remove_id_ending(post_json_object['object']['id'])
    if not actor:
        actor = post_json_object['actor']
        post_id = remove_id_ending(post_json_object['id'])
    if not actor:
        return
    lastpost_dir = acct_dir(base_dir, nickname, domain) + '/lastpost'
    if not os.path.isdir(lastpost_dir):
        os.mkdir(lastpost_dir)
    actor_filename = lastpost_dir + '/' + actor.replace('/', '#')
    try:
        with open(actor_filename, 'w+', encoding='utf-8') as fp_actor:
            fp_actor.write(post_id)
    except OSError:
        print('EX: Unable to write last post id to ' + actor_filename)


def _update_cached_hashtag_swarm(base_dir: str, nickname: str, domain: str,
                                 http_prefix: str, domain_full: str,
                                 translate: {}) -> bool:
    """Updates the hashtag swarm stored as a file
    """
    cached_hashtag_swarm_filename = \
        acct_dir(base_dir, nickname, domain) + '/.hashtagSwarm'
    save_swarm = True
    if os.path.isfile(cached_hashtag_swarm_filename):
        last_modified = file_last_modified(cached_hashtag_swarm_filename)
        modified_date = None
        try:
            modified_date = \
                datetime.datetime.strptime(last_modified, "%Y-%m-%dT%H:%M:%SZ")
        except BaseException:
            print('EX: unable to parse last modified cache date ' +
                  str(last_modified))
        if modified_date:
            curr_date = datetime.datetime.utcnow()
            time_diff = curr_date - modified_date
            diff_mins = int(time_diff.total_seconds() / 60)
            if diff_mins < 30:
                # was saved recently, so don't save again
                # This avoids too much disk I/O
                save_swarm = False
                print('Not updating hashtag swarm')
            else:
                print('Updating cached hashtag swarm, last changed ' +
                      str(diff_mins) + ' minutes ago')
        else:
            print('WARN: no modified date for ' + str(last_modified))
    if save_swarm:
        actor = local_actor_url(http_prefix, nickname, domain_full)
        new_swarm_str = html_hash_tag_swarm(base_dir, actor, translate)
        if new_swarm_str:
            try:
                with open(cached_hashtag_swarm_filename, 'w+',
                          encoding='utf-8') as fp_swarm:
                    fp_swarm.write(new_swarm_str)
                    return True
            except OSError:
                print('EX: unable to write cached hashtag swarm ' +
                      cached_hashtag_swarm_filename)
        remove_old_hashtags(base_dir, 3)
    return False


def store_hash_tags(base_dir: str, nickname: str, domain: str,
                    http_prefix: str, domain_full: str,
                    post_json_object: {}, translate: {}) -> None:
    """Extracts hashtags from an incoming post and updates the
    relevant tags files.
    """
    if not is_public_post(post_json_object):
        return
    if not has_object_dict(post_json_object):
        return
    if not post_json_object['object'].get('tag'):
        return
    if not post_json_object.get('id'):
        return
    if not isinstance(post_json_object['object']['tag'], list):
        return
    tags_dir = base_dir + '/tags'

    # add tags directory if it doesn't exist
    if not os.path.isdir(tags_dir):
        print('Creating tags directory')
        os.mkdir(tags_dir)

    # obtain any map links and these can be associated with hashtags
    # get geolocations from content
    map_links = []
    published = None
    if post_json_object['object'].get('content'):
        published = post_json_object['object']['published']
        post_content = post_json_object['object']['content']
        map_links += get_map_links_from_post_content(post_content)
    # get geolocation from tags
    location_str = \
        get_location_from_tags(post_json_object['object']['tag'])
    if location_str:
        if '://' in location_str and '.' in location_str:
            zoom, latitude, longitude = geocoords_from_map_link(location_str)
            if latitude and longitude and zoom and \
               location_str not in map_links:
                map_links.append(location_str)
    tag_maps_dir = base_dir + '/tagmaps'
    if map_links:
        # add tagmaps directory if it doesn't exist
        if not os.path.isdir(tag_maps_dir):
            print('Creating tagmaps directory')
            os.mkdir(tag_maps_dir)

    post_url = remove_id_ending(post_json_object['id'])
    post_url = post_url.replace('/', '#')

    hashtags_ctr = 0
    for tag in post_json_object['object']['tag']:
        if not tag.get('type'):
            continue
        if not isinstance(tag['type'], str):
            continue
        if tag['type'] != 'Hashtag':
            continue
        if not tag.get('name'):
            continue
        tag_name = tag['name'].replace('#', '').strip()
        if not valid_hash_tag(tag_name):
            continue
        tags_filename = tags_dir + '/' + tag_name + '.txt'
        days_diff = datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
        days_since_epoch = days_diff.days
        tag_line = \
            str(days_since_epoch) + '  ' + nickname + '  ' + post_url + '\n'
        if map_links and published:
            add_tag_map_links(tag_maps_dir, tag_name, map_links,
                              published, post_url)
        hashtag_added = False
        print('**** tag_line ' + tag_line.replace('\n', '<CR>'))
        if not os.path.isfile(tags_filename):
            try:
                with open(tags_filename, 'w+', encoding='utf-8') as tags_file:
                    tags_file.write(tag_line)
                    hashtag_added = True
            except OSError:
                print('EX: unable to write ' + tags_filename)
        else:
            content = ''
            try:
                with open(tags_filename, 'r', encoding='utf-8') as tags_file:
                    content = tags_file.read()
            except OSError:
                pass
            if post_url not in content:
                print('**** tag_line2 ' + content.replace('\n', '<CR>'))
                content = tag_line + content
                try:
                    with open(tags_filename, 'w+',
                              encoding='utf-8') as tags_file:
                        tags_file.write(content)
                        hashtag_added = True
                except OSError as ex:
                    print('EX: Failed to write entry to tags file ' +
                          tags_filename + ' ' + str(ex))

        if hashtag_added:
            hashtags_ctr += 1

            # automatically assign a category to the tag if possible
            category_filename = tags_dir + '/' + tag_name + '.category'
            if not os.path.isfile(category_filename):
                hashtag_categories = get_hashtag_categories(base_dir)
                category_str = \
                    guess_hashtag_category(tag_name, hashtag_categories)
                if category_str:
                    set_hashtag_category(base_dir, tag_name,
                                         category_str, False)

    # if some hashtags were found then recalculate the swarm
    # ready for later display
    if hashtags_ctr > 0:
        _update_cached_hashtag_swarm(base_dir, nickname, domain,
                                     http_prefix, domain_full, translate)


def _inbox_store_post_to_html_cache(recent_posts_cache: {},
                                    max_recent_posts: int,
                                    translate: {},
                                    base_dir: str, http_prefix: str,
                                    session, cached_webfingers: {},
                                    person_cache: {},
                                    nickname: str, domain: str, port: int,
                                    post_json_object: {},
                                    allow_deletion: bool, boxname: str,
                                    show_published_date_only: bool,
                                    peertube_instances: [],
                                    allow_local_network_access: bool,
                                    theme_name: str, system_language: str,
                                    max_like_count: int,
                                    signing_priv_key_pem: str,
                                    cw_lists: {},
                                    lists_enabled: str,
                                    timezone: str,
                                    mitm: bool,
                                    bold_reading: bool,
                                    dogwhistles: {}) -> None:
    """Converts the json post into html and stores it in a cache
    This enables the post to be quickly displayed later
    """
    page_number = -999
    avatar_url = None
    if boxname != 'outbox':
        boxname = 'inbox'

    not_dm = not is_dm(post_json_object)
    yt_replace_domain = get_config_param(base_dir, 'youtubedomain')
    twitter_replacement_domain = get_config_param(base_dir, 'twitterdomain')
    individual_post_as_html(signing_priv_key_pem,
                            True, recent_posts_cache, max_recent_posts,
                            translate, page_number,
                            base_dir, session, cached_webfingers,
                            person_cache,
                            nickname, domain, port, post_json_object,
                            avatar_url, True, allow_deletion,
                            http_prefix, __version__, boxname,
                            yt_replace_domain, twitter_replacement_domain,
                            show_published_date_only,
                            peertube_instances, allow_local_network_access,
                            theme_name, system_language, max_like_count,
                            not_dm, True, True, False, True, False,
                            cw_lists, lists_enabled, timezone, mitm,
                            bold_reading, dogwhistles)


def valid_inbox(base_dir: str, nickname: str, domain: str) -> bool:
    """Checks whether files were correctly saved to the inbox
    """
    domain = remove_domain_port(domain)
    inbox_dir = acct_dir(base_dir, nickname, domain) + '/inbox'
    if not os.path.isdir(inbox_dir):
        return True
    for subdir, _, files in os.walk(inbox_dir):
        for fname in files:
            filename = os.path.join(subdir, fname)
            if not os.path.isfile(filename):
                print('filename: ' + filename)
                return False
            if text_in_file('postNickname', filename):
                print('queue file incorrectly saved to ' + filename)
                return False
        break
    return True


def valid_inbox_filenames(base_dir: str, nickname: str, domain: str,
                          expected_domain: str, expected_port: int) -> bool:
    """Used by unit tests to check that the port number gets appended to
    domain names within saved post filenames
    """
    domain = remove_domain_port(domain)
    inbox_dir = acct_dir(base_dir, nickname, domain) + '/inbox'
    if not os.path.isdir(inbox_dir):
        print('Not an inbox directory: ' + inbox_dir)
        return True
    expected_str = expected_domain + ':' + str(expected_port)
    expected_found = False
    ctr = 0
    for subdir, _, files in os.walk(inbox_dir):
        for fname in files:
            filename = os.path.join(subdir, fname)
            ctr += 1
            if not os.path.isfile(filename):
                print('filename: ' + filename)
                return False
            if expected_str in filename:
                expected_found = True
        break
    if ctr == 0:
        return True
    if not expected_found:
        print('Expected file was not found: ' + expected_str)
        for subdir, _, files in os.walk(inbox_dir):
            for fname in files:
                filename = os.path.join(subdir, fname)
                print(filename)
            break
        return False
    return True


def inbox_message_has_params(message_json: {}) -> bool:
    """Checks whether an incoming message contains expected parameters
    """
    expected_params = ['actor', 'type', 'object']
    for param in expected_params:
        if not message_json.get(param):
            # print('inbox_message_has_params: ' +
            #       param + ' ' + str(message_json))
            return False

    # actor should be a string
    if not isinstance(message_json['actor'], str):
        print('WARN: actor should be a string, but is actually: ' +
              str(message_json['actor']))
        pprint(message_json)
        return False

    # type should be a string
    if not isinstance(message_json['type'], str):
        print('WARN: type from ' + str(message_json['actor']) +
              ' should be a string, but is actually: ' +
              str(message_json['type']))
        return False

    # object should be a dict or a string
    if not has_object_dict(message_json):
        if not isinstance(message_json['object'], str):
            print('WARN: object from ' + str(message_json['actor']) +
                  ' should be a dict or string, but is actually: ' +
                  str(message_json['object']))
            return False

    if not message_json.get('to'):
        allowed_without_to_param = ['Like', 'EmojiReact',
                                    'Follow', 'Join', 'Request',
                                    'Accept', 'Capability', 'Undo']
        if message_json['type'] not in allowed_without_to_param:
            return False
    return True


def inbox_permitted_message(domain: str, message_json: {},
                            federation_list: []) -> bool:
    """ check that we are receiving from a permitted domain
    """
    if not has_actor(message_json, False):
        return False

    actor = message_json['actor']
    # always allow the local domain
    if domain in actor:
        return True

    if not url_permitted(actor, federation_list):
        return False

    always_allowed_types = (
        'Follow', 'Join', 'Like', 'EmojiReact', 'Delete', 'Announce'
    )
    if message_json['type'] not in always_allowed_types:
        if not has_object_dict(message_json):
            return True
        if message_json['object'].get('inReplyTo'):
            in_reply_to = message_json['object']['inReplyTo']
            if not isinstance(in_reply_to, str):
                return False
            if not url_permitted(in_reply_to, federation_list):
                return False

    return True


def save_post_to_inbox_queue(base_dir: str, http_prefix: str,
                             nickname: str, domain: str,
                             post_json_object: {},
                             original_post_json_object: {},
                             message_bytes: str,
                             http_headers: {},
                             post_path: str, debug: bool,
                             blocked_cache: [], system_language: str,
                             mitm: bool) -> str:
    """Saves the given json to the inbox queue for the person
    key_id specifies the actor sending the post
    """
    if len(message_bytes) > 10240:
        print('WARN: inbox message too long ' +
              str(len(message_bytes)) + ' bytes')
        return None
    original_domain = domain
    domain = remove_domain_port(domain)

    # block at the ealiest stage possible, which means the data
    # isn't written to file
    post_nickname = None
    post_domain = None
    actor = None
    if post_json_object.get('actor'):
        if not isinstance(post_json_object['actor'], str):
            return None
        actor = post_json_object['actor']
        post_nickname = get_nickname_from_actor(post_json_object['actor'])
        if not post_nickname:
            print('No post Nickname in actor ' + post_json_object['actor'])
            return None
        post_domain, post_port = \
            get_domain_from_actor(post_json_object['actor'])
        if not post_domain:
            if debug:
                pprint(post_json_object)
            print('No post Domain in actor')
            return None
        if is_blocked(base_dir, nickname, domain,
                      post_nickname, post_domain, blocked_cache):
            if debug:
                print('DEBUG: post from ' + post_nickname + ' blocked')
            return None
        post_domain = get_full_domain(post_domain, post_port)

    if has_object_dict(post_json_object):
        if post_json_object['object'].get('inReplyTo'):
            if isinstance(post_json_object['object']['inReplyTo'], str):
                in_reply_to = \
                    post_json_object['object']['inReplyTo']
                reply_domain, _ = \
                    get_domain_from_actor(in_reply_to)
                if is_blocked_domain(base_dir, reply_domain, blocked_cache):
                    if debug:
                        print('WARN: post contains reply from ' +
                              str(actor) +
                              ' to a blocked domain: ' + reply_domain)
                    return None

                reply_nickname = \
                    get_nickname_from_actor(in_reply_to)
                if reply_nickname and reply_domain:
                    if is_blocked(base_dir, nickname, domain,
                                  reply_nickname, reply_domain,
                                  blocked_cache):
                        if debug:
                            print('WARN: post contains reply from ' +
                                  str(actor) +
                                  ' to a blocked account: ' +
                                  reply_nickname + '@' + reply_domain)
                        return None

    # filter on the content of the post
    content_str = \
        get_base_content_from_post(post_json_object, system_language)
    if content_str:
        summary_str = \
            get_summary_from_post(post_json_object,
                                  system_language, [])
        media_descriptions = \
            get_media_descriptions_from_post(post_json_object)
        content_all = \
            summary_str + ' ' + content_str + ' ' + media_descriptions
        if is_filtered(base_dir, nickname, domain, content_all):
            if debug:
                print('WARN: post was filtered out due to content')
            return None
        if reject_twitter_summary(base_dir, nickname, domain,
                                  summary_str):
            if debug:
                print('WARN: post was filtered out due to ' +
                      'twitter summary')
            return None

    original_post_id = None
    if post_json_object.get('id'):
        if not isinstance(post_json_object['id'], str):
            return None
        original_post_id = remove_id_ending(post_json_object['id'])

    curr_time = datetime.datetime.utcnow()

    post_id = None
    if post_json_object.get('id'):
        post_id = remove_id_ending(post_json_object['id'])
        published = curr_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not post_id:
        status_number, published = get_status_number()
        if actor:
            post_id = actor + '/statuses/' + status_number
        else:
            post_id = \
                local_actor_url(http_prefix, nickname, original_domain) + \
                '/statuses/' + status_number

    # NOTE: don't change post_json_object['id'] before signature check

    inbox_queue_dir = create_inbox_queue_dir(nickname, domain, base_dir)

    handle = nickname + '@' + domain
    destination = base_dir + '/accounts/' + \
        handle + '/inbox/' + post_id.replace('/', '#') + '.json'
    filename = inbox_queue_dir + '/' + post_id.replace('/', '#') + '.json'

    shared_inbox_item = False
    if nickname == 'inbox':
        nickname = original_domain
        shared_inbox_item = True

    digest_start_time = time.time()
    digest_algorithm = get_digest_algorithm_from_headers(http_headers)
    digest = message_content_digest(message_bytes, digest_algorithm)
    time_diff_str = str(int((time.time() - digest_start_time) * 1000))
    if debug:
        while len(time_diff_str) < 6:
            time_diff_str = '0' + time_diff_str
        print('DIGEST|' + time_diff_str + '|' + filename)

    new_queue_item = {
        'originalId': original_post_id,
        'id': post_id,
        'actor': actor,
        'nickname': nickname,
        'domain': domain,
        'postNickname': post_nickname,
        'postDomain': post_domain,
        'sharedInbox': shared_inbox_item,
        'published': published,
        'httpHeaders': http_headers,
        'path': post_path,
        'post': post_json_object,
        'original': original_post_json_object,
        'digest': digest,
        'filename': filename,
        'destination': destination,
        'mitm': mitm
    }

    if debug:
        print('Inbox queue item created')
    save_json(new_queue_item, filename)
    return filename


def _inbox_post_recipients_add(base_dir: str, http_prefix: str, to_list: [],
                               recipients_dict: {},
                               domain_match: str, domain: str,
                               actor: str, debug: bool,
                               onion_domain: str, i2p_domain: str) -> bool:
    """Given a list of post recipients (to_list) from 'to' or 'cc' parameters
    populate a recipients_dict with the handle for each
    """
    follower_recipients = False
    for recipient in to_list:
        if not recipient:
            continue
        # if the recipient is an onion or i2p address then
        # is it an account on a clearnet instance?
        # If so then change the onion/i2p to the account domain
        if onion_domain:
            if onion_domain + '/' in recipient:
                recipient = recipient.replace(onion_domain, domain)
        if i2p_domain:
            if i2p_domain + '/' in recipient:
                recipient = recipient.replace(i2p_domain, domain)
        # is this a to an account on this instance?
        if domain_match in recipient:
            # get the handle for the account on this instance
            nickname = recipient.split(domain_match)[1]
            handle = nickname + '@' + domain
            if os.path.isdir(base_dir + '/accounts/' + handle):
                recipients_dict[handle] = None
            else:
                if debug:
                    print('DEBUG: ' + base_dir + '/accounts/' +
                          handle + ' does not exist')
        else:
            if debug:
                if recipient.endswith('#Public'):
                    print('DEBUG: #Public recipient is too non-specific. ' +
                          recipient + ' ' + domain_match)
                else:
                    print('DEBUG: ' + recipient + ' is not local to ' +
                          domain_match)
                print(str(to_list))
        if recipient.endswith('followers'):
            if debug:
                print('DEBUG: followers detected as post recipients')
            follower_recipients = True
    return follower_recipients, recipients_dict


def _inbox_post_recipients(base_dir: str, post_json_object: {},
                           http_prefix: str, domain: str, port: int,
                           debug: bool,
                           onion_domain: str, i2p_domain: str) -> ([], []):
    """Returns dictionaries containing the recipients of the given post
    The shared dictionary contains followers
    """
    recipients_dict = {}
    recipients_dict_followers = {}

    if not post_json_object.get('actor'):
        if debug:
            pprint(post_json_object)
            print('WARNING: inbox post has no actor')
        return recipients_dict, recipients_dict_followers

    domain = remove_domain_port(domain)
    domain_base = domain
    domain = get_full_domain(domain, port)
    domain_match = '/' + domain + '/users/'

    actor = post_json_object['actor']
    # first get any specific people which the post is addressed to

    follower_recipients = False
    if has_object_dict(post_json_object):
        if post_json_object['object'].get('to'):
            if isinstance(post_json_object['object']['to'], list):
                recipients_list = post_json_object['object']['to']
            else:
                recipients_list = [post_json_object['object']['to']]
            if debug:
                print('DEBUG: resolving "to"')
            includes_followers, recipients_dict = \
                _inbox_post_recipients_add(base_dir, http_prefix,
                                           recipients_list,
                                           recipients_dict,
                                           domain_match, domain_base,
                                           actor, debug,
                                           onion_domain, i2p_domain)
            if includes_followers:
                follower_recipients = True
        else:
            if debug:
                print('DEBUG: inbox post has no "to"')

        if post_json_object['object'].get('cc'):
            if isinstance(post_json_object['object']['cc'], list):
                recipients_list = post_json_object['object']['cc']
            else:
                recipients_list = [post_json_object['object']['cc']]
            includes_followers, recipients_dict = \
                _inbox_post_recipients_add(base_dir, http_prefix,
                                           recipients_list,
                                           recipients_dict,
                                           domain_match, domain_base,
                                           actor, debug,
                                           onion_domain, i2p_domain)
            if includes_followers:
                follower_recipients = True
        else:
            if debug:
                print('DEBUG: inbox post has no cc')
    else:
        if debug and post_json_object.get('object'):
            if isinstance(post_json_object['object'], str):
                if '/statuses/' in post_json_object['object']:
                    print('DEBUG: inbox item is a link to a post')
                else:
                    if '/users/' in post_json_object['object']:
                        print('DEBUG: inbox item is a link to an actor')

    if post_json_object.get('to'):
        if isinstance(post_json_object['to'], list):
            recipients_list = post_json_object['to']
        else:
            recipients_list = [post_json_object['to']]
        includes_followers, recipients_dict = \
            _inbox_post_recipients_add(base_dir, http_prefix,
                                       recipients_list,
                                       recipients_dict,
                                       domain_match, domain_base,
                                       actor, debug,
                                       onion_domain, i2p_domain)
        if includes_followers:
            follower_recipients = True

    if post_json_object.get('cc'):
        if isinstance(post_json_object['cc'], list):
            recipients_list = post_json_object['cc']
        else:
            recipients_list = [post_json_object['cc']]
        includes_followers, recipients_dict = \
            _inbox_post_recipients_add(base_dir, http_prefix,
                                       recipients_list,
                                       recipients_dict,
                                       domain_match, domain_base,
                                       actor, debug,
                                       onion_domain, i2p_domain)
        if includes_followers:
            follower_recipients = True

    if not follower_recipients:
        if debug:
            print('DEBUG: no followers were resolved')
        return recipients_dict, recipients_dict_followers

    # now resolve the followers
    recipients_dict_followers = \
        get_followers_of_actor(base_dir, actor, debug)

    return recipients_dict, recipients_dict_followers


def _receive_undo_follow(base_dir: str, message_json: {},
                         debug: bool, domain: str,
                         onion_domain: str, i2p_domain: str) -> bool:
    if not message_json['object'].get('actor'):
        if debug:
            print('DEBUG: follow request has no actor within object')
        return False
    if not has_users_path(message_json['object']['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing ' +
                  'from actor within object')
        return False
    if message_json['object']['actor'] != message_json['actor']:
        if debug:
            print('DEBUG: actors do not match')
        return False

    nickname_follower = \
        get_nickname_from_actor(message_json['object']['actor'])
    if not nickname_follower:
        print('WARN: unable to find nickname in ' +
              message_json['object']['actor'])
        return False
    domain_follower, port_follower = \
        get_domain_from_actor(message_json['object']['actor'])
    domain_follower_full = get_full_domain(domain_follower, port_follower)

    nickname_following = \
        get_nickname_from_actor(message_json['object']['object'])
    if not nickname_following:
        print('WARN: unable to find nickname in ' +
              message_json['object']['object'])
        return False
    domain_following, port_following = \
        get_domain_from_actor(message_json['object']['object'])
    if onion_domain:
        if domain_following.endswith(onion_domain):
            domain_following = domain
    if i2p_domain:
        if domain_following.endswith(i2p_domain):
            domain_following = domain
    domain_following_full = get_full_domain(domain_following, port_following)

    group_account = \
        has_group_type(base_dir, message_json['object']['actor'], None)
    if unfollower_of_account(base_dir,
                             nickname_following, domain_following_full,
                             nickname_follower, domain_follower_full,
                             debug, group_account):
        print(nickname_following + '@' + domain_following_full + ': '
              'Follower ' + nickname_follower + '@' + domain_follower_full +
              ' was removed')
        return True

    if debug:
        print('DEBUG: Follower ' +
              nickname_follower + '@' + domain_follower_full +
              ' was not removed')
    return False


def _receive_undo(base_dir: str, message_json: {}, debug: bool,
                  domain: str, onion_domain: str, i2p_domain: str) -> bool:
    """Receives an undo request within the POST section of HTTPServer
    """
    if not message_json['type'].startswith('Undo'):
        return False
    if debug:
        print('DEBUG: Undo activity received')
    if not has_actor(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor')
        return False
    if not has_object_string_type(message_json, debug):
        return False
    if not has_object_string_object(message_json, debug):
        return False
    if message_json['object']['type'] == 'Follow' or \
       message_json['object']['type'] == 'Join':
        return _receive_undo_follow(base_dir, message_json,
                                    debug, domain, onion_domain, i2p_domain)
    return False


def _person_receive_update(base_dir: str,
                           domain: str, port: int,
                           update_nickname: str, update_domain: str,
                           update_port: int,
                           person_json: {}, person_cache: {},
                           debug: bool) -> bool:
    """Changes an actor. eg: avatar or display name change
    """
    if debug:
        print('Receiving actor update for ' + person_json['url'] +
              ' ' + str(person_json))
    domain_full = get_full_domain(domain, port)
    update_domain_full = get_full_domain(update_domain, update_port)
    users_paths = get_user_paths()
    users_str_found = False
    for users_str in users_paths:
        actor = update_domain_full + users_str + update_nickname
        if actor in person_json['id']:
            users_str_found = True
            break
    if not users_str_found:
        if debug:
            print('actor: ' + actor)
            print('id: ' + person_json['id'])
            print('DEBUG: Actor does not match id')
        return False
    if update_domain_full == domain_full:
        if debug:
            print('DEBUG: You can only receive actor updates ' +
                  'for domains other than your own')
        return False
    if not person_json.get('publicKey'):
        if debug:
            print('DEBUG: actor update does not contain a public key')
        return False
    if not person_json['publicKey'].get('publicKeyPem'):
        if debug:
            print('DEBUG: actor update does not contain a public key Pem')
        return False
    actor_filename = base_dir + '/cache/actors/' + \
        person_json['id'].replace('/', '#') + '.json'
    # check that the public keys match.
    # If they don't then this may be a nefarious attempt to hack an account
    idx = person_json['id']
    if person_cache.get(idx):
        if person_cache[idx]['actor']['publicKey']['publicKeyPem'] != \
           person_json['publicKey']['publicKeyPem']:
            if debug:
                print('WARN: Public key does not match when updating actor')
            return False
    else:
        if os.path.isfile(actor_filename):
            existing_person_json = load_json(actor_filename)
            if existing_person_json:
                if existing_person_json['publicKey']['publicKeyPem'] != \
                   person_json['publicKey']['publicKeyPem']:
                    if debug:
                        print('WARN: Public key does not match ' +
                              'cached actor when updating')
                    return False
    # save to cache in memory
    store_person_in_cache(base_dir, person_json['id'], person_json,
                          person_cache, True)
    # save to cache on file
    if save_json(person_json, actor_filename):
        if debug:
            print('actor updated for ' + person_json['id'])

    # remove avatar if it exists so that it will be refreshed later
    # when a timeline is constructed
    actor_str = person_json['id'].replace('/', '-')
    remove_avatar_from_cache(base_dir, actor_str)
    return True


def _receive_update_to_question(recent_posts_cache: {}, message_json: {},
                                base_dir: str,
                                nickname: str, domain: str) -> None:
    """Updating a question as new votes arrive
    """
    # message url of the question
    if not message_json.get('id'):
        return
    if not has_actor(message_json, False):
        return
    message_id = remove_id_ending(message_json['id'])
    if '#' in message_id:
        message_id = message_id.split('#', 1)[0]
    # find the question post
    post_filename = locate_post(base_dir, nickname, domain, message_id)
    if not post_filename:
        return
    # load the json for the question
    post_json_object = load_json(post_filename, 1)
    if not post_json_object:
        return
    if not post_json_object.get('actor'):
        return
    # does the actor match?
    if post_json_object['actor'] != message_json['actor']:
        return
    save_json(message_json, post_filename)
    # ensure that the cached post is removed if it exists, so
    # that it then will be recreated
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain, message_json)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                print('EX: _receive_update_to_question unable to delete ' +
                      cached_post_filename)
    # remove from memory cache
    remove_post_from_cache(message_json, recent_posts_cache)


def _receive_edit_to_post(recent_posts_cache: {}, message_json: {},
                          base_dir: str,
                          nickname: str, domain: str,
                          max_mentions: int, max_emoji: int,
                          allow_local_network_access: bool,
                          debug: bool,
                          system_language: str, http_prefix: str,
                          domain_full: str, person_cache: {},
                          signing_priv_key_pem: str,
                          max_recent_posts: int, translate: {},
                          session, cached_webfingers: {}, port: int,
                          allow_deletion: bool,
                          yt_replace_domain: str,
                          twitter_replacement_domain: str,
                          show_published_date_only: bool,
                          peertube_instances: [],
                          theme_name: str, max_like_count: int,
                          cw_lists: {}, dogwhistles: {}) -> bool:
    """A post was edited
    """
    if not has_object_dict(message_json):
        return False
    # message url of the question
    if not message_json['object'].get('id'):
        return False
    if not message_json.get('actor'):
        return False
    if not has_actor(message_json, False):
        return False
    if not has_actor(message_json['object'], False):
        return False
    message_id = remove_id_ending(message_json['object']['id'])
    if '#' in message_id:
        message_id = message_id.split('#', 1)[0]
    # find the post which was edited
    post_filename = locate_post(base_dir, nickname, domain, message_id)
    if not post_filename:
        print('EDITPOST: ' + message_id + ' has already expired')
        return False
    if not _valid_post_content(base_dir, nickname, domain,
                               message_json, max_mentions, max_emoji,
                               allow_local_network_access, debug,
                               system_language, http_prefix,
                               domain_full, person_cache):
        print('EDITPOST: contains invalid content' + str(message_json))
        return False

    # load the json for the post
    post_json_object = load_json(post_filename, 1)
    if not post_json_object:
        return False
    if not post_json_object.get('actor'):
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('content'):
        return False
    if not message_json['object'].get('content'):
        return False
    # does the actor match?
    if post_json_object['actor'] != message_json['actor']:
        print('EDITPOST: actors do not match ' +
              post_json_object['actor'] + ' != ' + message_json['actor'])
        return False
    # has the content changed?
    if post_json_object['object']['content'] == \
       message_json['object']['content']:
        # same content
        if 'summary' in post_json_object['object'] and \
           'summary' in message_json['object']:
            if post_json_object['object']['summary'] == \
               message_json['object']['summary']:
                return False
        else:
            return False
    # save the edit history to file
    post_history_filename = post_filename.replace('.json', '') + '.edits'
    post_history_json = {}
    if os.path.isfile(post_history_filename):
        post_history_json = load_json(post_history_filename, 1)
    if post_json_object['object'].get('updated'):
        published_str = post_json_object['object']['updated']
    else:
        published_str = post_json_object['object']['published']
    if not post_history_json.get(published_str):
        post_history_json[published_str] = post_json_object
        save_json(post_history_json, post_history_filename)
    # Change Update to Create
    message_json['type'] = 'Create'
    save_json(message_json, post_filename)
    # ensure that the cached post is removed if it exists, so
    # that it then will be recreated
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain, message_json)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                print('EX: _receive_edit_to_post unable to delete ' +
                      cached_post_filename)
    # remove any cached html for the post which was edited
    delete_cached_html(base_dir, nickname, domain, post_json_object)
    # remove from memory cache
    remove_post_from_cache(message_json, recent_posts_cache)
    # regenerate html for the post
    page_number = 1
    show_published_date_only = False
    show_individual_post_icons = True
    manually_approve_followers = \
        follower_approval_active(base_dir, nickname, domain)
    not_dm = not is_dm(message_json)
    timezone = get_account_timezone(base_dir, nickname, domain)
    mitm = False
    if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
        mitm = True
    bold_reading = False
    bold_reading_filename = \
        base_dir + '/accounts/' + nickname + '@' + domain + '/.boldReading'
    if os.path.isfile(bold_reading_filename):
        bold_reading = True
    timezone = get_account_timezone(base_dir, nickname, domain)
    lists_enabled = get_config_param(base_dir, "listsEnabled")
    individual_post_as_html(signing_priv_key_pem, False,
                            recent_posts_cache, max_recent_posts,
                            translate, page_number, base_dir,
                            session, cached_webfingers, person_cache,
                            nickname, domain, port, message_json,
                            None, True, allow_deletion,
                            http_prefix, __version__, 'inbox',
                            yt_replace_domain,
                            twitter_replacement_domain,
                            show_published_date_only,
                            peertube_instances,
                            allow_local_network_access,
                            theme_name, system_language,
                            max_like_count, not_dm,
                            show_individual_post_icons,
                            manually_approve_followers,
                            False, True, False, cw_lists,
                            lists_enabled, timezone, mitm,
                            bold_reading, dogwhistles)
    return True


def _receive_update_activity(recent_posts_cache: {}, session, base_dir: str,
                             http_prefix: str, domain: str, port: int,
                             cached_webfingers: {},
                             person_cache: {}, message_json: {},
                             nickname: str, debug: bool,
                             max_mentions: int, max_emoji: int,
                             allow_local_network_access: bool,
                             system_language: str,
                             signing_priv_key_pem: str,
                             max_recent_posts: int, translate: {},
                             allow_deletion: bool,
                             yt_replace_domain: str,
                             twitter_replacement_domain: str,
                             show_published_date_only: bool,
                             peertube_instances: [],
                             theme_name: str, max_like_count: int,
                             cw_lists: {}, dogwhistles: {}) -> bool:

    """Receives an Update activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Update':
        return False
    if not has_actor(message_json, debug):
        return False
    if not has_object_string_type(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False

    if message_json['object']['type'] == 'Question':
        _receive_update_to_question(recent_posts_cache, message_json,
                                    base_dir, nickname, domain)
        if debug:
            print('DEBUG: Question update was received')
        return True
    elif message_json['object']['type'] == 'Note':
        if message_json['object'].get('id'):
            domain_full = get_full_domain(domain, port)
            if _receive_edit_to_post(recent_posts_cache, message_json,
                                     base_dir, nickname, domain,
                                     max_mentions, max_emoji,
                                     allow_local_network_access,
                                     debug, system_language, http_prefix,
                                     domain_full, person_cache,
                                     signing_priv_key_pem,
                                     max_recent_posts, translate,
                                     session, cached_webfingers, port,
                                     allow_deletion,
                                     yt_replace_domain,
                                     twitter_replacement_domain,
                                     show_published_date_only,
                                     peertube_instances,
                                     theme_name, max_like_count,
                                     cw_lists, dogwhistles):
                print('EDITPOST: received ' + message_json['object']['id'])
                return True
        else:
            print('EDITPOST: rejected ' + str(message_json))
            return False

    if message_json['object']['type'] == 'Person' or \
       message_json['object']['type'] == 'Application' or \
       message_json['object']['type'] == 'Group' or \
       message_json['object']['type'] == 'Service':
        if message_json['object'].get('url') and \
           message_json['object'].get('id'):
            if debug:
                print('Request to update actor: ' + str(message_json))
            update_nickname = get_nickname_from_actor(message_json['actor'])
            if update_nickname:
                update_domain, update_port = \
                    get_domain_from_actor(message_json['actor'])
                if _person_receive_update(base_dir,
                                          domain, port,
                                          update_nickname, update_domain,
                                          update_port,
                                          message_json['object'],
                                          person_cache, debug):
                    print('Person Update: ' + str(message_json))
                    if debug:
                        print('DEBUG: Profile update was received for ' +
                              message_json['object']['url'])
                        return True
    return False


def _receive_like(recent_posts_cache: {},
                  session, handle: str, base_dir: str,
                  http_prefix: str, domain: str, port: int,
                  onion_domain: str, i2p_domain: str,
                  cached_webfingers: {},
                  person_cache: {}, message_json: {},
                  debug: bool,
                  signing_priv_key_pem: str,
                  max_recent_posts: int, translate: {},
                  allow_deletion: bool,
                  yt_replace_domain: str,
                  twitter_replacement_domain: str,
                  peertube_instances: [],
                  allow_local_network_access: bool,
                  theme_name: str, system_language: str,
                  max_like_count: int, cw_lists: {},
                  lists_enabled: str,
                  bold_reading: bool, dogwhistles: {}) -> bool:
    """Receives a Like activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Like':
        return False
    if not has_actor(message_json, debug):
        return False
    if not has_object_string(message_json, debug):
        return False
    if not message_json.get('to'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "to" list')
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False
    if '/statuses/' not in message_json['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  message_json['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of like - ' + handle)
    # if this post in the outbox of the person?
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]
    post_liked_id = message_json['object']
    post_filename = \
        locate_post(base_dir, handle_name, handle_dom, post_liked_id)
    if not post_filename:
        if debug:
            print('DEBUG: post not found in inbox or outbox')
            print(post_liked_id)
        return True
    if debug:
        print('DEBUG: liked post found in inbox')

    like_actor = message_json['actor']
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]
    if not _already_liked(base_dir,
                          handle_name, handle_dom,
                          post_liked_id,
                          like_actor):
        _like_notify(base_dir, domain, onion_domain, i2p_domain, handle,
                     like_actor, post_liked_id)
    update_likes_collection(recent_posts_cache, base_dir, post_filename,
                            post_liked_id, like_actor,
                            handle_name, domain, debug, None)
    # regenerate the html
    liked_post_json = load_json(post_filename, 0, 1)
    if liked_post_json:
        if liked_post_json.get('type'):
            if liked_post_json['type'] == 'Announce' and \
               liked_post_json.get('object'):
                if isinstance(liked_post_json['object'], str):
                    announce_like_url = liked_post_json['object']
                    announce_liked_filename = \
                        locate_post(base_dir, handle_name,
                                    domain, announce_like_url)
                    if announce_liked_filename:
                        post_liked_id = announce_like_url
                        post_filename = announce_liked_filename
                        update_likes_collection(recent_posts_cache,
                                                base_dir,
                                                post_filename,
                                                post_liked_id,
                                                like_actor,
                                                handle_name,
                                                domain, debug, None)
        if liked_post_json:
            if debug:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, handle_name, domain,
                                             liked_post_json)
                print('Liked post json: ' + str(liked_post_json))
                print('Liked post nickname: ' + handle_name + ' ' + domain)
                print('Liked post cache: ' + str(cached_post_filename))
            page_number = 1
            show_published_date_only = False
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir, handle_name, domain)
            not_dm = not is_dm(liked_post_json)
            timezone = get_account_timezone(base_dir, handle_name, domain)
            mitm = False
            if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
                mitm = True
            individual_post_as_html(signing_priv_key_pem, False,
                                    recent_posts_cache, max_recent_posts,
                                    translate, page_number, base_dir,
                                    session, cached_webfingers, person_cache,
                                    handle_name, domain, port, liked_post_json,
                                    None, True, allow_deletion,
                                    http_prefix, __version__,
                                    'inbox',
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    show_published_date_only,
                                    peertube_instances,
                                    allow_local_network_access,
                                    theme_name, system_language,
                                    max_like_count, not_dm,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False, cw_lists,
                                    lists_enabled, timezone, mitm,
                                    bold_reading, dogwhistles)
    return True


def _receive_undo_like(recent_posts_cache: {},
                       session, handle: str, base_dir: str,
                       http_prefix: str, domain: str, port: int,
                       cached_webfingers: {},
                       person_cache: {}, message_json: {},
                       debug: bool,
                       signing_priv_key_pem: str,
                       max_recent_posts: int, translate: {},
                       allow_deletion: bool,
                       yt_replace_domain: str,
                       twitter_replacement_domain: str,
                       peertube_instances: [],
                       allow_local_network_access: bool,
                       theme_name: str, system_language: str,
                       max_like_count: int, cw_lists: {},
                       lists_enabled: str,
                       bold_reading: bool, dogwhistles: {}) -> bool:
    """Receives an undo like activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Undo':
        return False
    if not has_actor(message_json, debug):
        return False
    if not has_object_string_type(message_json, debug):
        return False
    if message_json['object']['type'] != 'Like':
        return False
    if not has_object_string_object(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + ' like')
        return False
    if '/statuses/' not in message_json['object']['object']:
        if debug:
            print('DEBUG: "statuses" missing from like object in ' +
                  message_json['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of undo like - ' + handle)
    # if this post in the outbox of the person?
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]
    post_filename = \
        locate_post(base_dir, handle_name, handle_dom,
                    message_json['object']['object'])
    if not post_filename:
        if debug:
            print('DEBUG: unliked post not found in inbox or outbox')
            print(message_json['object']['object'])
        return True
    if debug:
        print('DEBUG: liked post found in inbox. Now undoing.')
    like_actor = message_json['actor']
    post_liked_id = message_json['object']
    undo_likes_collection_entry(recent_posts_cache, base_dir, post_filename,
                                post_liked_id, like_actor, domain, debug, None)
    # regenerate the html
    liked_post_json = load_json(post_filename, 0, 1)
    if liked_post_json:
        if liked_post_json.get('type'):
            if liked_post_json['type'] == 'Announce' and \
               liked_post_json.get('object'):
                if isinstance(liked_post_json['object'], str):
                    announce_like_url = liked_post_json['object']
                    announce_liked_filename = \
                        locate_post(base_dir, handle_name,
                                    domain, announce_like_url)
                    if announce_liked_filename:
                        post_liked_id = announce_like_url
                        post_filename = announce_liked_filename
                        undo_likes_collection_entry(recent_posts_cache,
                                                    base_dir,
                                                    post_filename,
                                                    post_liked_id,
                                                    like_actor, domain, debug,
                                                    None)
        if liked_post_json:
            if debug:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, handle_name, domain,
                                             liked_post_json)
                print('Unliked post json: ' + str(liked_post_json))
                print('Unliked post nickname: ' + handle_name + ' ' + domain)
                print('Unliked post cache: ' + str(cached_post_filename))
            page_number = 1
            show_published_date_only = False
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir, handle_name, domain)
            not_dm = not is_dm(liked_post_json)
            timezone = get_account_timezone(base_dir, handle_name, domain)
            mitm = False
            if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
                mitm = True
            individual_post_as_html(signing_priv_key_pem, False,
                                    recent_posts_cache, max_recent_posts,
                                    translate, page_number, base_dir,
                                    session, cached_webfingers, person_cache,
                                    handle_name, domain, port, liked_post_json,
                                    None, True, allow_deletion,
                                    http_prefix, __version__,
                                    'inbox',
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    show_published_date_only,
                                    peertube_instances,
                                    allow_local_network_access,
                                    theme_name, system_language,
                                    max_like_count, not_dm,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False, cw_lists,
                                    lists_enabled, timezone, mitm,
                                    bold_reading, dogwhistles)
    return True


def _receive_reaction(recent_posts_cache: {},
                      session, handle: str, base_dir: str,
                      http_prefix: str, domain: str, port: int,
                      onion_domain: str,
                      cached_webfingers: {},
                      person_cache: {}, message_json: {},
                      debug: bool,
                      signing_priv_key_pem: str,
                      max_recent_posts: int, translate: {},
                      allow_deletion: bool,
                      yt_replace_domain: str,
                      twitter_replacement_domain: str,
                      peertube_instances: [],
                      allow_local_network_access: bool,
                      theme_name: str, system_language: str,
                      max_like_count: int, cw_lists: {},
                      lists_enabled: str, bold_reading: bool,
                      dogwhistles: {}) -> bool:
    """Receives an emoji reaction within the POST section of HTTPServer
    """
    if message_json['type'] != 'EmojiReact':
        return False
    if not has_actor(message_json, debug):
        return False
    if not has_object_string(message_json, debug):
        return False
    if not message_json.get('content'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "content"')
        return False
    if not isinstance(message_json['content'], str):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' content is not string')
        return False
    if not valid_emoji_content(message_json['content']):
        print('_receive_reaction: Invalid emoji reaction: "' +
              message_json['content'] + '" from ' + message_json['actor'])
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False
    if '/statuses/' not in message_json['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  message_json['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of emoji reaction - ' + handle)
    if os.path.isfile(base_dir + '/accounts/' + handle +
                      '/.hideReactionButton'):
        print('Emoji reaction rejected by ' + handle +
              ' due to their settings')
        return True
    # if this post in the outbox of the person?
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]

    post_reaction_id = message_json['object']
    emoji_content = remove_html(message_json['content'])
    if not emoji_content:
        if debug:
            print('DEBUG: emoji reaction has no content')
        return True
    post_filename = locate_post(base_dir, handle_name, handle_dom,
                                post_reaction_id)
    if not post_filename:
        if debug:
            print('DEBUG: emoji reaction post not found in inbox or outbox')
            print(post_reaction_id)
        return True
    if debug:
        print('DEBUG: emoji reaction post found in inbox')

    reaction_actor = message_json['actor']
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]
    if not _already_reacted(base_dir,
                            handle_name, handle_dom,
                            post_reaction_id,
                            reaction_actor,
                            emoji_content):
        _reaction_notify(base_dir, domain, onion_domain, handle,
                         reaction_actor, post_reaction_id, emoji_content)
    update_reaction_collection(recent_posts_cache, base_dir, post_filename,
                               post_reaction_id, reaction_actor,
                               handle_name, domain, debug, None, emoji_content)
    # regenerate the html
    reaction_post_json = load_json(post_filename, 0, 1)
    if reaction_post_json:
        if reaction_post_json.get('type'):
            if reaction_post_json['type'] == 'Announce' and \
               reaction_post_json.get('object'):
                if isinstance(reaction_post_json['object'], str):
                    announce_reaction_url = reaction_post_json['object']
                    announce_reaction_filename = \
                        locate_post(base_dir, handle_name,
                                    domain, announce_reaction_url)
                    if announce_reaction_filename:
                        post_reaction_id = announce_reaction_url
                        post_filename = announce_reaction_filename
                        update_reaction_collection(recent_posts_cache,
                                                   base_dir,
                                                   post_filename,
                                                   post_reaction_id,
                                                   reaction_actor,
                                                   handle_name,
                                                   domain, debug, None,
                                                   emoji_content)
        if reaction_post_json:
            if debug:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, handle_name, domain,
                                             reaction_post_json)
                print('Reaction post json: ' + str(reaction_post_json))
                print('Reaction post nickname: ' + handle_name + ' ' + domain)
                print('Reaction post cache: ' + str(cached_post_filename))
            page_number = 1
            show_published_date_only = False
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir, handle_name, domain)
            not_dm = not is_dm(reaction_post_json)
            timezone = get_account_timezone(base_dir, handle_name, domain)
            mitm = False
            if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
                mitm = True
            individual_post_as_html(signing_priv_key_pem, False,
                                    recent_posts_cache, max_recent_posts,
                                    translate, page_number, base_dir,
                                    session, cached_webfingers, person_cache,
                                    handle_name, domain, port,
                                    reaction_post_json,
                                    None, True, allow_deletion,
                                    http_prefix, __version__,
                                    'inbox',
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    show_published_date_only,
                                    peertube_instances,
                                    allow_local_network_access,
                                    theme_name, system_language,
                                    max_like_count, not_dm,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False, cw_lists,
                                    lists_enabled, timezone, mitm,
                                    bold_reading, dogwhistles)
    return True


def _receive_zot_reaction(recent_posts_cache: {},
                          session, handle: str, base_dir: str,
                          http_prefix: str, domain: str, port: int,
                          onion_domain: str,
                          cached_webfingers: {},
                          person_cache: {}, message_json: {},
                          debug: bool,
                          signing_priv_key_pem: str,
                          max_recent_posts: int, translate: {},
                          allow_deletion: bool,
                          yt_replace_domain: str,
                          twitter_replacement_domain: str,
                          peertube_instances: [],
                          allow_local_network_access: bool,
                          theme_name: str, system_language: str,
                          max_like_count: int, cw_lists: {},
                          lists_enabled: str, bold_reading: bool,
                          dogwhistles: {}) -> bool:
    """Receives an zot-style emoji reaction within the POST section of HTTPServer
    A zot style emoji reaction is an ordinary reply Note whose content is
    exactly one emoji
    """
    if not has_actor(message_json, debug):
        return False
    if not has_object_dict(message_json):
        return False
    if not message_json['object'].get('type'):
        return False
    if not isinstance(message_json['object']['type'], str):
        return False
    if message_json['object']['type'] != 'Note':
        return False
    if not message_json['object'].get('content'):
        if debug:
            print('DEBUG: ' + message_json['object']['type'] +
                  ' has no "content"')
        return False
    if not message_json['object'].get('inReplyTo'):
        if debug:
            print('DEBUG: ' + message_json['object']['type'] +
                  ' has no "inReplyTo"')
        return False
    if not isinstance(message_json['object']['content'], str):
        if debug:
            print('DEBUG: ' + message_json['object']['type'] +
                  ' content is not string')
        return False
    if len(message_json['object']['content']) > 4:
        if debug:
            print('DEBUG: content is too long to be an emoji reaction')
        return False
    if not isinstance(message_json['object']['inReplyTo'], str):
        if debug:
            print('DEBUG: ' + message_json['object']['type'] +
                  ' inReplyTo is not string')
        return False
    if not valid_emoji_content(message_json['object']['content']):
        print('_receive_zot_reaction: Invalid emoji reaction: "' +
              message_json['object']['content'] + '" from ' +
              message_json['actor'])
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['object']['type'])
        return False
    if '/statuses/' not in message_json['object']['inReplyTo']:
        if debug:
            print('DEBUG: "statuses" missing from inReplyTo in ' +
                  message_json['object']['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of zot emoji reaction - ' + handle)
    if os.path.isfile(base_dir + '/accounts/' + handle +
                      '/.hideReactionButton'):
        print('Zot emoji reaction rejected by ' + handle +
              ' due to their settings')
        return True
    # if this post in the outbox of the person?
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]

    post_reaction_id = message_json['object']['inReplyTo']
    emoji_content = remove_html(message_json['object']['content'])
    if not emoji_content:
        if debug:
            print('DEBUG: zot emoji reaction has no content')
        return True
    post_filename = locate_post(base_dir, handle_name, handle_dom,
                                post_reaction_id)
    if not post_filename:
        if debug:
            print('DEBUG: ' +
                  'zot emoji reaction post not found in inbox or outbox')
            print(post_reaction_id)
        return True
    if debug:
        print('DEBUG: zot emoji reaction post found in inbox')

    reaction_actor = message_json['actor']
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]
    if not _already_reacted(base_dir,
                            handle_name, handle_dom,
                            post_reaction_id,
                            reaction_actor,
                            emoji_content):
        _reaction_notify(base_dir, domain, onion_domain, handle,
                         reaction_actor, post_reaction_id, emoji_content)
    update_reaction_collection(recent_posts_cache, base_dir, post_filename,
                               post_reaction_id, reaction_actor,
                               handle_name, domain, debug, None, emoji_content)
    # regenerate the html
    reaction_post_json = load_json(post_filename, 0, 1)
    if reaction_post_json:
        if reaction_post_json.get('type'):
            if reaction_post_json['type'] == 'Announce' and \
               reaction_post_json.get('object'):
                if isinstance(reaction_post_json['object'], str):
                    announce_reaction_url = reaction_post_json['object']
                    announce_reaction_filename = \
                        locate_post(base_dir, handle_name,
                                    domain, announce_reaction_url)
                    if announce_reaction_filename:
                        post_reaction_id = announce_reaction_url
                        post_filename = announce_reaction_filename
                        update_reaction_collection(recent_posts_cache,
                                                   base_dir,
                                                   post_filename,
                                                   post_reaction_id,
                                                   reaction_actor,
                                                   handle_name,
                                                   domain, debug, None,
                                                   emoji_content)
        if reaction_post_json:
            if debug:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, handle_name, domain,
                                             reaction_post_json)
                print('Reaction post json: ' + str(reaction_post_json))
                print('Reaction post nickname: ' + handle_name + ' ' + domain)
                print('Reaction post cache: ' + str(cached_post_filename))
            page_number = 1
            show_published_date_only = False
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir, handle_name, domain)
            not_dm = not is_dm(reaction_post_json)
            timezone = get_account_timezone(base_dir, handle_name, domain)
            mitm = False
            if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
                mitm = True
            individual_post_as_html(signing_priv_key_pem, False,
                                    recent_posts_cache, max_recent_posts,
                                    translate, page_number, base_dir,
                                    session, cached_webfingers, person_cache,
                                    handle_name, domain, port,
                                    reaction_post_json,
                                    None, True, allow_deletion,
                                    http_prefix, __version__,
                                    'inbox',
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    show_published_date_only,
                                    peertube_instances,
                                    allow_local_network_access,
                                    theme_name, system_language,
                                    max_like_count, not_dm,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False, cw_lists,
                                    lists_enabled, timezone, mitm,
                                    bold_reading, dogwhistles)
    return True


def _receive_undo_reaction(recent_posts_cache: {},
                           session, handle: str, is_group: bool, base_dir: str,
                           http_prefix: str, domain: str, port: int,
                           send_threads: [], post_log: [],
                           cached_webfingers: {},
                           person_cache: {}, message_json: {},
                           federation_list: [],
                           debug: bool,
                           signing_priv_key_pem: str,
                           max_recent_posts: int, translate: {},
                           allow_deletion: bool,
                           yt_replace_domain: str,
                           twitter_replacement_domain: str,
                           peertube_instances: [],
                           allow_local_network_access: bool,
                           theme_name: str, system_language: str,
                           max_like_count: int, cw_lists: {},
                           lists_enabled: str,
                           bold_reading: bool, dogwhistles: {}) -> bool:
    """Receives an undo emoji reaction within the POST section of HTTPServer
    """
    if message_json['type'] != 'Undo':
        return False
    if not has_actor(message_json, debug):
        return False
    if not has_object_string_type(message_json, debug):
        return False
    if message_json['object']['type'] != 'EmojiReact':
        return False
    if not has_object_string_object(message_json, debug):
        return False
    if not message_json['object'].get('content'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "content"')
        return False
    if not isinstance(message_json['object']['content'], str):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' content is not string')
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + ' reaction')
        return False
    if '/statuses/' not in message_json['object']['object']:
        if debug:
            print('DEBUG: "statuses" missing from reaction object in ' +
                  message_json['type'])
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of undo reaction - ' + handle)
    # if this post in the outbox of the person?
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]
    post_filename = \
        locate_post(base_dir, handle_name, handle_dom,
                    message_json['object']['object'])
    if not post_filename:
        if debug:
            print('DEBUG: unreaction post not found in inbox or outbox')
            print(message_json['object']['object'])
        return True
    if debug:
        print('DEBUG: reaction post found in inbox. Now undoing.')
    reaction_actor = message_json['actor']
    post_reaction_id = message_json['object']
    emoji_content = remove_html(message_json['object']['content'])
    if not emoji_content:
        if debug:
            print('DEBUG: unreaction has no content')
        return True
    undo_reaction_collection_entry(recent_posts_cache, base_dir, post_filename,
                                   post_reaction_id, reaction_actor, domain,
                                   debug, None, emoji_content)
    # regenerate the html
    reaction_post_json = load_json(post_filename, 0, 1)
    if reaction_post_json:
        if reaction_post_json.get('type'):
            if reaction_post_json['type'] == 'Announce' and \
               reaction_post_json.get('object'):
                if isinstance(reaction_post_json['object'], str):
                    announce_reaction_url = reaction_post_json['object']
                    announce_reaction_filename = \
                        locate_post(base_dir, handle_name,
                                    domain, announce_reaction_url)
                    if announce_reaction_filename:
                        post_reaction_id = announce_reaction_url
                        post_filename = announce_reaction_filename
                        undo_reaction_collection_entry(recent_posts_cache,
                                                       base_dir,
                                                       post_filename,
                                                       post_reaction_id,
                                                       reaction_actor,
                                                       domain,
                                                       debug, None,
                                                       emoji_content)
        if reaction_post_json:
            if debug:
                cached_post_filename = \
                    get_cached_post_filename(base_dir, handle_name, domain,
                                             reaction_post_json)
                print('Unreaction post json: ' + str(reaction_post_json))
                print('Unreaction post nickname: ' +
                      handle_name + ' ' + domain)
                print('Unreaction post cache: ' + str(cached_post_filename))
            page_number = 1
            show_published_date_only = False
            show_individual_post_icons = True
            manually_approve_followers = \
                follower_approval_active(base_dir, handle_name, domain)
            not_dm = not is_dm(reaction_post_json)
            timezone = get_account_timezone(base_dir, handle_name, domain)
            mitm = False
            if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
                mitm = True
            individual_post_as_html(signing_priv_key_pem, False,
                                    recent_posts_cache, max_recent_posts,
                                    translate, page_number, base_dir,
                                    session, cached_webfingers, person_cache,
                                    handle_name, domain, port,
                                    reaction_post_json,
                                    None, True, allow_deletion,
                                    http_prefix, __version__,
                                    'inbox',
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    show_published_date_only,
                                    peertube_instances,
                                    allow_local_network_access,
                                    theme_name, system_language,
                                    max_like_count, not_dm,
                                    show_individual_post_icons,
                                    manually_approve_followers,
                                    False, True, False, cw_lists,
                                    lists_enabled, timezone, mitm,
                                    bold_reading, dogwhistles)
    return True


def _receive_bookmark(recent_posts_cache: {},
                      session, handle: str, is_group: bool, base_dir: str,
                      http_prefix: str, domain: str, port: int,
                      send_threads: [], post_log: [], cached_webfingers: {},
                      person_cache: {}, message_json: {}, federation_list: [],
                      debug: bool, signing_priv_key_pem: str,
                      max_recent_posts: int, translate: {},
                      allow_deletion: bool,
                      yt_replace_domain: str,
                      twitter_replacement_domain: str,
                      peertube_instances: [],
                      allow_local_network_access: bool,
                      theme_name: str, system_language: str,
                      max_like_count: int, cw_lists: {},
                      lists_enabled: {}, bold_reading: bool,
                      dogwhistles: {}) -> bool:
    """Receives a bookmark activity within the POST section of HTTPServer
    """
    if not message_json.get('type'):
        return False
    if message_json['type'] != 'Add':
        return False
    if not has_actor(message_json, debug):
        return False
    if not message_json.get('target'):
        if debug:
            print('DEBUG: no target in inbox bookmark Add')
        return False
    if not has_object_string_type(message_json, debug):
        return False
    if not isinstance(message_json['target'], str):
        if debug:
            print('DEBUG: inbox bookmark Add target is not string')
        return False
    domain_full = get_full_domain(domain, port)
    nickname = handle.split('@')[0]
    if not message_json['actor'].endswith(domain_full + '/users/' + nickname):
        if debug:
            print('DEBUG: inbox bookmark Add unexpected actor')
        return False
    if not message_json['target'].endswith(message_json['actor'] +
                                           '/tlbookmarks'):
        if debug:
            print('DEBUG: inbox bookmark Add target invalid ' +
                  message_json['target'])
        return False
    if message_json['object']['type'] != 'Document':
        if debug:
            print('DEBUG: inbox bookmark Add type is not Document')
        return False
    if not message_json['object'].get('url'):
        if debug:
            print('DEBUG: inbox bookmark Add missing url')
        return False
    if '/statuses/' not in message_json['object']['url']:
        if debug:
            print('DEBUG: inbox bookmark Add missing statuses un url')
        return False
    if debug:
        print('DEBUG: c2s inbox bookmark Add request arrived in outbox')

    message_url = remove_id_ending(message_json['object']['url'])
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, message_url)
    if not post_filename:
        if debug:
            print('DEBUG: c2s inbox like post not found in inbox or outbox')
            print(message_url)
        return True

    update_bookmarks_collection(recent_posts_cache, base_dir, post_filename,
                                message_json['object']['url'],
                                message_json['actor'], domain, debug)
    # regenerate the html
    bookmarked_post_json = load_json(post_filename, 0, 1)
    if bookmarked_post_json:
        if debug:
            cached_post_filename = \
                get_cached_post_filename(base_dir, nickname, domain,
                                         bookmarked_post_json)
            print('Bookmarked post json: ' + str(bookmarked_post_json))
            print('Bookmarked post nickname: ' + nickname + ' ' + domain)
            print('Bookmarked post cache: ' + str(cached_post_filename))
        page_number = 1
        show_published_date_only = False
        show_individual_post_icons = True
        manually_approve_followers = \
            follower_approval_active(base_dir, nickname, domain)
        not_dm = not is_dm(bookmarked_post_json)
        timezone = get_account_timezone(base_dir, nickname, domain)
        mitm = False
        if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
            mitm = True
        individual_post_as_html(signing_priv_key_pem, False,
                                recent_posts_cache, max_recent_posts,
                                translate, page_number, base_dir,
                                session, cached_webfingers, person_cache,
                                nickname, domain, port, bookmarked_post_json,
                                None, True, allow_deletion,
                                http_prefix, __version__,
                                'inbox',
                                yt_replace_domain,
                                twitter_replacement_domain,
                                show_published_date_only,
                                peertube_instances,
                                allow_local_network_access,
                                theme_name, system_language,
                                max_like_count, not_dm,
                                show_individual_post_icons,
                                manually_approve_followers,
                                False, True, False, cw_lists,
                                lists_enabled, timezone, mitm,
                                bold_reading, dogwhistles)
    return True


def _receive_undo_bookmark(recent_posts_cache: {},
                           session, handle: str, is_group: bool, base_dir: str,
                           http_prefix: str, domain: str, port: int,
                           send_threads: [], post_log: [],
                           cached_webfingers: {},
                           person_cache: {}, message_json: {},
                           federation_list: [],
                           debug: bool, signing_priv_key_pem: str,
                           max_recent_posts: int, translate: {},
                           allow_deletion: bool,
                           yt_replace_domain: str,
                           twitter_replacement_domain: str,
                           peertube_instances: [],
                           allow_local_network_access: bool,
                           theme_name: str, system_language: str,
                           max_like_count: int, cw_lists: {},
                           lists_enabled: str, bold_reading: bool,
                           dogwhistles: {}) -> bool:
    """Receives an undo bookmark activity within the POST section of HTTPServer
    """
    if not message_json.get('type'):
        return False
    if message_json['type'] != 'Remove':
        return False
    if not has_actor(message_json, debug):
        return False
    if not message_json.get('target'):
        if debug:
            print('DEBUG: no target in inbox undo bookmark Remove')
        return False
    if not has_object_string_type(message_json, debug):
        return False
    if not isinstance(message_json['target'], str):
        if debug:
            print('DEBUG: inbox Remove bookmark target is not string')
        return False
    domain_full = get_full_domain(domain, port)
    nickname = handle.split('@')[0]
    if not message_json['actor'].endswith(domain_full + '/users/' + nickname):
        if debug:
            print('DEBUG: inbox undo bookmark Remove unexpected actor')
        return False
    if not message_json['target'].endswith(message_json['actor'] +
                                           '/tlbookmarks'):
        if debug:
            print('DEBUG: inbox undo bookmark Remove target invalid ' +
                  message_json['target'])
        return False
    if message_json['object']['type'] != 'Document':
        if debug:
            print('DEBUG: inbox undo bookmark Remove type is not Document')
        return False
    if not message_json['object'].get('url'):
        if debug:
            print('DEBUG: inbox undo bookmark Remove missing url')
        return False
    if '/statuses/' not in message_json['object']['url']:
        if debug:
            print('DEBUG: inbox undo bookmark Remove missing statuses un url')
        return False
    if debug:
        print('DEBUG: c2s inbox Remove bookmark ' +
              'request arrived in outbox')

    message_url = remove_id_ending(message_json['object']['url'])
    domain = remove_domain_port(domain)
    post_filename = locate_post(base_dir, nickname, domain, message_url)
    if not post_filename:
        if debug:
            print('DEBUG: c2s inbox like post not found in inbox or outbox')
            print(message_url)
        return True

    undo_bookmarks_collection_entry(recent_posts_cache, base_dir,
                                    post_filename,
                                    message_json['actor'], domain, debug)
    # regenerate the html
    bookmarked_post_json = load_json(post_filename, 0, 1)
    if bookmarked_post_json:
        if debug:
            cached_post_filename = \
                get_cached_post_filename(base_dir, nickname, domain,
                                         bookmarked_post_json)
            print('Unbookmarked post json: ' + str(bookmarked_post_json))
            print('Unbookmarked post nickname: ' + nickname + ' ' + domain)
            print('Unbookmarked post cache: ' + str(cached_post_filename))
        page_number = 1
        show_published_date_only = False
        show_individual_post_icons = True
        manually_approve_followers = \
            follower_approval_active(base_dir, nickname, domain)
        not_dm = not is_dm(bookmarked_post_json)
        timezone = get_account_timezone(base_dir, nickname, domain)
        mitm = False
        if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
            mitm = True
        individual_post_as_html(signing_priv_key_pem, False,
                                recent_posts_cache, max_recent_posts,
                                translate, page_number, base_dir,
                                session, cached_webfingers, person_cache,
                                nickname, domain, port, bookmarked_post_json,
                                None, True, allow_deletion,
                                http_prefix, __version__,
                                'inbox',
                                yt_replace_domain,
                                twitter_replacement_domain,
                                show_published_date_only,
                                peertube_instances,
                                allow_local_network_access,
                                theme_name, system_language,
                                max_like_count, not_dm,
                                show_individual_post_icons,
                                manually_approve_followers,
                                False, True, False, cw_lists, lists_enabled,
                                timezone, mitm, bold_reading,
                                dogwhistles)
    return True


def _receive_delete(session, handle: str, is_group: bool, base_dir: str,
                    http_prefix: str, domain: str, port: int,
                    send_threads: [], post_log: [], cached_webfingers: {},
                    person_cache: {}, message_json: {}, federation_list: [],
                    debug: bool, allow_deletion: bool,
                    recent_posts_cache: {}) -> bool:
    """Receives a Delete activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Delete':
        return False
    if not has_actor(message_json, debug):
        return False
    if debug:
        print('DEBUG: Delete activity arrived')
    if not has_object_string(message_json, debug):
        return False
    domain_full = get_full_domain(domain, port)
    delete_prefix = http_prefix + '://' + domain_full + '/'
    if (not allow_deletion and
        (not message_json['object'].startswith(delete_prefix) or
         not message_json['actor'].startswith(delete_prefix))):
        if debug:
            print('DEBUG: delete not permitted from other instances')
        return False
    if not message_json.get('to'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "to" list')
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: ' +
                  '"users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False
    if '/statuses/' not in message_json['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in ' +
                  message_json['type'])
        return False
    if message_json['actor'] not in message_json['object']:
        if debug:
            print('DEBUG: actor is not the owner of the post to be deleted')
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of like - ' + handle)
    # if this post in the outbox of the person?
    message_id = remove_id_ending(message_json['object'])
    remove_moderation_post_from_index(base_dir, message_id, debug)
    handle_nickname = handle.split('@')[0]
    handle_domain = handle.split('@')[1]
    post_filename = locate_post(base_dir, handle_nickname,
                                handle_domain, message_id)
    if not post_filename:
        if debug:
            print('DEBUG: delete post not found in inbox or outbox')
            print(message_id)
        return True
    delete_post(base_dir, http_prefix, handle_nickname,
                handle_domain, post_filename, debug,
                recent_posts_cache, True)
    if debug:
        print('DEBUG: post deleted - ' + post_filename)

    # also delete any local blogs saved to the news actor
    if handle_nickname != 'news' and handle_domain == domain_full:
        post_filename = locate_post(base_dir, 'news',
                                    handle_domain, message_id)
        if post_filename:
            delete_post(base_dir, http_prefix, 'news',
                        handle_domain, post_filename, debug,
                        recent_posts_cache, True)
            if debug:
                print('DEBUG: blog post deleted - ' + post_filename)
    return True


def _receive_announce(recent_posts_cache: {},
                      session, handle: str, is_group: bool, base_dir: str,
                      http_prefix: str,
                      domain: str,
                      onion_domain: str, i2p_domain: str, port: int,
                      send_threads: [], post_log: [], cached_webfingers: {},
                      person_cache: {}, message_json: {}, federation_list: [],
                      debug: bool, translate: {},
                      yt_replace_domain: str,
                      twitter_replacement_domain: str,
                      allow_local_network_access: bool,
                      theme_name: str, system_language: str,
                      signing_priv_key_pem: str,
                      max_recent_posts: int,
                      allow_deletion: bool,
                      peertube_instances: [],
                      max_like_count: int, cw_lists: {},
                      lists_enabled: str, bold_reading: bool,
                      dogwhistles: {}) -> bool:
    """Receives an announce activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Announce':
        return False
    if '@' not in handle:
        if debug:
            print('DEBUG: bad handle ' + handle)
        return False
    if not has_actor(message_json, debug):
        return False
    if debug:
        print('DEBUG: receiving announce on ' + handle)
    if not has_object_string(message_json, debug):
        return False
    if not message_json.get('to'):
        if debug:
            print('DEBUG: ' + message_json['type'] + ' has no "to" list')
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: ' +
                  '"users" or "profile" missing from actor in ' +
                  message_json['type'])
        return False
    if is_self_announce(message_json):
        if debug:
            print('DEBUG: self-boost rejected')
        return False
    if not has_users_path(message_json['object']):
        if debug:
            print('DEBUG: ' +
                  '"users", "channel" or "profile" missing in ' +
                  message_json['type'])
        return False

    blocked_cache = {}
    prefixes = get_protocol_prefixes()
    # is the domain of the announce actor blocked?
    object_domain = message_json['object']
    for prefix in prefixes:
        object_domain = object_domain.replace(prefix, '')
    if '/' in object_domain:
        object_domain = object_domain.split('/')[0]
    if is_blocked_domain(base_dir, object_domain):
        if debug:
            print('DEBUG: announced domain is blocked')
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of announce - ' + handle)

    # is the announce actor blocked?
    nickname = handle.split('@')[0]
    actor_nickname = get_nickname_from_actor(message_json['actor'])
    if not actor_nickname:
        print('WARN: _receive_announce no actor_nickname')
        return False
    actor_domain, _ = get_domain_from_actor(message_json['actor'])
    if is_blocked(base_dir, nickname, domain, actor_nickname, actor_domain):
        print('Receive announce blocked for actor: ' +
              actor_nickname + '@' + actor_domain)
        return False

    # also check the actor for the url being announced
    announced_actor_nickname = get_nickname_from_actor(message_json['object'])
    if not announced_actor_nickname:
        print('WARN: _receive_announce no announced_actor_nickname')
        return False
    announced_actor_domain, _ = get_domain_from_actor(message_json['object'])
    if is_blocked(base_dir, nickname, domain,
                  announced_actor_nickname, announced_actor_domain):
        print('Receive announce object blocked for actor: ' +
              announced_actor_nickname + '@' + announced_actor_domain)
        return False

    # is this post in the outbox of the person?
    post_filename = locate_post(base_dir, nickname, domain,
                                message_json['object'])
    if not post_filename:
        if debug:
            print('DEBUG: announce post not found in inbox or outbox')
            print(message_json['object'])
        return True
    update_announce_collection(recent_posts_cache, base_dir, post_filename,
                               message_json['actor'], nickname, domain, debug)
    if debug:
        print('DEBUG: Downloading announce post ' + message_json['actor'] +
              ' -> ' + message_json['object'])
    domain_full = get_full_domain(domain, port)

    # Generate html. This also downloads the announced post.
    page_number = 1
    show_published_date_only = False
    show_individual_post_icons = True
    manually_approve_followers = \
        follower_approval_active(base_dir, nickname, domain)
    not_dm = True
    if debug:
        print('Generating html for announce ' + message_json['id'])
    timezone = get_account_timezone(base_dir, nickname, domain)
    mitm = False
    if os.path.isfile(post_filename.replace('.json', '') + '.mitm'):
        mitm = True
    announce_html = \
        individual_post_as_html(signing_priv_key_pem, True,
                                recent_posts_cache, max_recent_posts,
                                translate, page_number, base_dir,
                                session, cached_webfingers, person_cache,
                                nickname, domain, port, message_json,
                                None, True, allow_deletion,
                                http_prefix, __version__,
                                'inbox',
                                yt_replace_domain,
                                twitter_replacement_domain,
                                show_published_date_only,
                                peertube_instances,
                                allow_local_network_access,
                                theme_name, system_language,
                                max_like_count, not_dm,
                                show_individual_post_icons,
                                manually_approve_followers,
                                False, True, False, cw_lists,
                                lists_enabled, timezone, mitm,
                                bold_reading, dogwhistles)
    if not announce_html:
        print('WARN: Unable to generate html for announce ' +
              str(message_json))
    else:
        if debug:
            announce_html2 = remove_eol(announce_html)
            print('Generated announce html ' + announce_html2)

    post_json_object = download_announce(session, base_dir,
                                         http_prefix,
                                         nickname, domain,
                                         message_json,
                                         __version__,
                                         yt_replace_domain,
                                         twitter_replacement_domain,
                                         allow_local_network_access,
                                         recent_posts_cache, debug,
                                         system_language,
                                         domain_full, person_cache,
                                         signing_priv_key_pem,
                                         blocked_cache, bold_reading)
    if not post_json_object:
        print('WARN: unable to download announce: ' + str(message_json))
        not_in_onion = True
        if onion_domain:
            if onion_domain in message_json['object']:
                not_in_onion = False
        if domain not in message_json['object'] and not_in_onion:
            if os.path.isfile(post_filename):
                # if the announce can't be downloaded then remove it
                try:
                    os.remove(post_filename)
                except OSError:
                    print('EX: _receive_announce unable to delete ' +
                          str(post_filename))
    else:
        if debug:
            print('DEBUG: Announce post downloaded for ' +
                  message_json['actor'] + ' -> ' + message_json['object'])
        store_hash_tags(base_dir, nickname, domain,
                        http_prefix, domain_full,
                        post_json_object, translate)
        # Try to obtain the actor for this person
        # so that their avatar can be shown
        lookup_actor = None
        if post_json_object.get('attributedTo'):
            if isinstance(post_json_object['attributedTo'], str):
                lookup_actor = post_json_object['attributedTo']
        else:
            if has_object_dict(post_json_object):
                if post_json_object['object'].get('attributedTo'):
                    attrib = post_json_object['object']['attributedTo']
                    if isinstance(attrib, str):
                        lookup_actor = attrib
        if lookup_actor:
            if has_users_path(lookup_actor):
                if '/statuses/' in lookup_actor:
                    lookup_actor = lookup_actor.split('/statuses/')[0]

                if is_recent_post(post_json_object, 3):
                    if not os.path.isfile(post_filename + '.tts'):
                        domain_full = get_full_domain(domain, port)
                        update_speaker(base_dir, http_prefix,
                                       nickname, domain, domain_full,
                                       post_json_object, person_cache,
                                       translate, lookup_actor,
                                       theme_name, system_language,
                                       'inbox')
                        try:
                            with open(post_filename + '.tts', 'w+',
                                      encoding='utf-8') as ttsfile:
                                ttsfile.write('\n')
                        except OSError:
                            print('EX: unable to write recent post ' +
                                  post_filename)

                if debug:
                    print('DEBUG: Obtaining actor for announce post ' +
                          lookup_actor)
                for tries in range(6):
                    pub_key = \
                        get_person_pub_key(base_dir, session, lookup_actor,
                                           person_cache, debug,
                                           __version__, http_prefix,
                                           domain, onion_domain,
                                           i2p_domain,
                                           signing_priv_key_pem)
                    if pub_key:
                        if debug:
                            print('DEBUG: public key obtained for announce: ' +
                                  lookup_actor)
                        break

                    if debug:
                        print('DEBUG: Retry ' + str(tries + 1) +
                              ' obtaining actor for ' + lookup_actor)
                    time.sleep(5)
        if debug:
            print('DEBUG: announced/repeated post arrived in inbox')
    return True


def _receive_undo_announce(recent_posts_cache: {},
                           session, handle: str, is_group: bool, base_dir: str,
                           http_prefix: str, domain: str, port: int,
                           send_threads: [], post_log: [],
                           cached_webfingers: {},
                           person_cache: {}, message_json: {},
                           federation_list: [],
                           debug: bool) -> bool:
    """Receives an undo announce activity within the POST section of HTTPServer
    """
    if message_json['type'] != 'Undo':
        return False
    if not has_actor(message_json, debug):
        return False
    if not has_object_dict(message_json):
        return False
    if not has_object_string_object(message_json, debug):
        return False
    if message_json['object']['type'] != 'Announce':
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  message_json['type'] + ' announce')
        return False
    if not os.path.isdir(base_dir + '/accounts/' + handle):
        print('DEBUG: unknown recipient of undo announce - ' + handle)
    # if this post in the outbox of the person?
    handle_name = handle.split('@')[0]
    handle_dom = handle.split('@')[1]
    post_filename = locate_post(base_dir, handle_name, handle_dom,
                                message_json['object']['object'])
    if not post_filename:
        if debug:
            print('DEBUG: undo announce post not found in inbox or outbox')
            print(message_json['object']['object'])
        return True
    if debug:
        print('DEBUG: announced/repeated post to be undone found in inbox')

    post_json_object = load_json(post_filename)
    if post_json_object:
        if not post_json_object.get('type'):
            if post_json_object['type'] != 'Announce':
                if debug:
                    print("DEBUG: Attempt to undo something " +
                          "which isn't an announcement")
                return False
    undo_announce_collection_entry(recent_posts_cache, base_dir, post_filename,
                                   message_json['actor'], domain, debug)
    if os.path.isfile(post_filename):
        try:
            os.remove(post_filename)
        except OSError:
            print('EX: _receive_undo_announce unable to delete ' +
                  str(post_filename))
    return True


def json_post_allows_comments(post_json_object: {}) -> bool:
    """Returns true if the given post allows comments/replies
    """
    if 'commentsEnabled' in post_json_object:
        return post_json_object['commentsEnabled']
    if 'rejectReplies' in post_json_object:
        return not post_json_object['rejectReplies']
    if post_json_object.get('object'):
        if not has_object_dict(post_json_object):
            return False
        if 'commentsEnabled' in post_json_object['object']:
            return post_json_object['object']['commentsEnabled']
        if 'rejectReplies' in post_json_object['object']:
            return not post_json_object['object']['rejectReplies']
    return True


def _post_allow_comments(post_filename: str) -> bool:
    """Returns true if the given post allows comments/replies
    """
    post_json_object = load_json(post_filename)
    if not post_json_object:
        return False
    return json_post_allows_comments(post_json_object)


def populate_replies(base_dir: str, http_prefix: str, domain: str,
                     message_json: {}, max_replies: int, debug: bool) -> bool:
    """Updates the list of replies for a post on this domain if
    a reply to it arrives
    """
    if not message_json.get('id'):
        return False
    if not has_object_dict(message_json):
        return False
    if not message_json['object'].get('inReplyTo'):
        return False
    if not message_json['object'].get('to'):
        return False
    reply_to = message_json['object']['inReplyTo']
    if not isinstance(reply_to, str):
        return False
    if debug:
        print('DEBUG: post contains a reply')
    # is this a reply to a post on this domain?
    if not reply_to.startswith(http_prefix + '://' + domain + '/'):
        if debug:
            print('DEBUG: post is a reply to another not on this domain')
            print(reply_to)
            print('Expected: ' + http_prefix + '://' + domain + '/')
        return False
    reply_to_nickname = get_nickname_from_actor(reply_to)
    if not reply_to_nickname:
        print('DEBUG: no nickname found for ' + reply_to)
        return False
    reply_to_domain, _ = get_domain_from_actor(reply_to)
    if not reply_to_domain:
        if debug:
            print('DEBUG: no domain found for ' + reply_to)
        return False

    post_filename = locate_post(base_dir, reply_to_nickname,
                                reply_to_domain, reply_to)
    if not post_filename:
        if debug:
            print('DEBUG: post may have expired - ' + reply_to)
        return False

    if not _post_allow_comments(post_filename):
        if debug:
            print('DEBUG: post does not allow comments - ' + reply_to)
        return False
    # populate a text file containing the ids of replies
    post_replies_filename = post_filename.replace('.json', '.replies')
    message_id = remove_id_ending(message_json['id'])
    if os.path.isfile(post_replies_filename):
        num_lines = sum(1 for line in open(post_replies_filename,
                                           encoding='utf-8'))
        if num_lines > max_replies:
            return False
        if not text_in_file(message_id, post_replies_filename):
            try:
                with open(post_replies_filename, 'a+',
                          encoding='utf-8') as replies_file:
                    replies_file.write(message_id + '\n')
            except OSError:
                print('EX: unable to append ' + post_replies_filename)
    else:
        try:
            with open(post_replies_filename, 'w+',
                      encoding='utf-8') as replies_file:
                replies_file.write(message_id + '\n')
        except OSError:
            print('EX: unable to write ' + post_replies_filename)
    return True


def _estimate_number_of_mentions(content: str) -> int:
    """Returns a rough estimate of the number of mentions
    """
    return content.count('>@<')


def _estimate_number_of_emoji(content: str) -> int:
    """Returns a rough estimate of the number of emoji
    """
    return content.count(' :')


def _valid_post_content(base_dir: str, nickname: str, domain: str,
                        message_json: {}, max_mentions: int, max_emoji: int,
                        allow_local_network_access: bool, debug: bool,
                        system_language: str,
                        http_prefix: str, domain_full: str,
                        person_cache: {}) -> bool:
    """Is the content of a received post valid?
    Check for bad html
    Check for hellthreads
    Check that the language is understood
    Check if it's a git patch
    Check number of tags and mentions is reasonable
    """
    if not has_object_dict(message_json):
        return True
    if not message_json['object'].get('content'):
        return True

    if not message_json['object'].get('published'):
        return False
    published = message_json['object']['published']
    if 'T' not in published:
        return False
    if 'Z' not in published:
        print('REJECT inbox post does not use Zulu time format. ' +
              published)
        return False
    if '.' in published:
        # converts 2022-03-30T17:37:58.734Z into 2022-03-30T17:37:58Z
        published = published.split('.')[0] + 'Z'
        message_json['object']['published'] = published
    if not valid_post_date(published, 90, debug):
        return False

    # if the post has been edited then check its edit date
    if message_json['object'].get('updated'):
        published_update = message_json['object']['updated']
        if 'T' not in published_update:
            return False
        if 'Z' not in published_update:
            return False
        if '.' in published_update:
            # converts 2022-03-30T17:37:58.734Z into 2022-03-30T17:37:58Z
            published_update = published_update.split('.')[0] + 'Z'
            message_json['object']['updated'] = published_update
        if not valid_post_date(published_update, 90, debug):
            return False

    summary = None
    if message_json['object'].get('summary'):
        summary = message_json['object']['summary']
        if not isinstance(summary, str):
            print('WARN: content warning is not a string')
            return False
        if summary != valid_content_warning(summary):
            print('WARN: invalid content warning ' + summary)
            return False
        if dangerous_markup(summary, allow_local_network_access):
            if message_json['object'].get('id'):
                print('REJECT ARBITRARY HTML: ' + message_json['object']['id'])
            print('REJECT ARBITRARY HTML: bad string in summary - ' +
                  summary)
            return False

    # check for patches before dangeousMarkup, which excludes code
    if is_git_patch(base_dir, nickname, domain,
                    message_json['object']['type'],
                    summary,
                    message_json['object']['content']):
        return True

    content_str = get_base_content_from_post(message_json, system_language)
    if dangerous_markup(content_str, allow_local_network_access):
        if message_json['object'].get('id'):
            print('REJECT ARBITRARY HTML: ' + message_json['object']['id'])
        print('REJECT ARBITRARY HTML: bad string in post - ' +
              content_str)
        return False

    # check (rough) number of mentions
    mentions_est = _estimate_number_of_mentions(content_str)
    if mentions_est > max_mentions:
        if message_json['object'].get('id'):
            print('REJECT HELLTHREAD: ' + message_json['object']['id'])
        print('REJECT HELLTHREAD: Too many mentions in post - ' +
              content_str)
        return False
    if _estimate_number_of_emoji(content_str) > max_emoji:
        if message_json['object'].get('id'):
            print('REJECT EMOJI OVERLOAD: ' + message_json['object']['id'])
        print('REJECT EMOJI OVERLOAD: Too many emoji in post - ' +
              content_str)
        return False
    # check number of tags
    if message_json['object'].get('tag'):
        if not isinstance(message_json['object']['tag'], list):
            message_json['object']['tag'] = []
        else:
            if len(message_json['object']['tag']) > int(max_mentions * 2):
                if message_json['object'].get('id'):
                    print('REJECT: ' + message_json['object']['id'])
                print('REJECT: Too many tags in post - ' +
                      message_json['object']['tag'])
                return False
    # check that the post is in a language suitable for this account
    if not understood_post_language(base_dir, nickname,
                                    message_json, system_language,
                                    http_prefix, domain_full,
                                    person_cache):
        return False

    # check for urls which are too long
    if not valid_url_lengths(content_str, 2048):
        print('REJECT: url within content too long')
        return False

    # check for filtered content
    media_descriptions = get_media_descriptions_from_post(message_json)
    content_all = content_str
    if summary:
        content_all = summary + ' ' + content_str + ' ' + media_descriptions
    if is_filtered(base_dir, nickname, domain, content_all):
        print('REJECT: content filtered')
        return False
    if message_json['object'].get('inReplyTo'):
        if isinstance(message_json['object']['inReplyTo'], str):
            original_post_id = message_json['object']['inReplyTo']
            post_post_filename = locate_post(base_dir, nickname, domain,
                                             original_post_id)
            if post_post_filename:
                if not _post_allow_comments(post_post_filename):
                    print('REJECT: reply to post which does not ' +
                          'allow comments: ' + original_post_id)
                    return False
    if invalid_ciphertext(message_json['object']['content']):
        print('REJECT: malformed ciphertext in content')
        return False
    if debug:
        print('ACCEPT: post content is valid')
    return True


def _obtain_avatar_for_reply_post(session, base_dir: str, http_prefix: str,
                                  domain: str, onion_domain: str,
                                  i2p_domain: str,
                                  person_cache: {},
                                  post_json_object: {}, debug: bool,
                                  signing_priv_key_pem: str) -> None:
    """Tries to obtain the actor for the person being replied to
    so that their avatar can later be shown
    """
    if not has_object_dict(post_json_object):
        return

    if not post_json_object['object'].get('inReplyTo'):
        return

    lookup_actor = post_json_object['object']['inReplyTo']
    if not lookup_actor:
        return

    if not isinstance(lookup_actor, str):
        return

    if not has_users_path(lookup_actor):
        return

    if '/statuses/' in lookup_actor:
        lookup_actor = lookup_actor.split('/statuses/')[0]

    if debug:
        print('DEBUG: Obtaining actor for reply post ' + lookup_actor)

    for tries in range(6):
        pub_key = \
            get_person_pub_key(base_dir, session, lookup_actor,
                               person_cache, debug,
                               __version__, http_prefix,
                               domain, onion_domain, i2p_domain,
                               signing_priv_key_pem)
        if pub_key:
            if debug:
                print('DEBUG: public key obtained for reply: ' + lookup_actor)
            break

        if debug:
            print('DEBUG: Retry ' + str(tries + 1) +
                  ' obtaining actor for ' + lookup_actor)
        time.sleep(5)


def _dm_notify(base_dir: str, handle: str, url: str) -> None:
    """Creates a notification that a new DM has arrived
    """
    account_dir = base_dir + '/accounts/' + handle
    if not os.path.isdir(account_dir):
        return
    dm_file = account_dir + '/.newDM'
    if not os.path.isfile(dm_file):
        try:
            with open(dm_file, 'w+', encoding='utf-8') as fp_dm:
                fp_dm.write(url)
        except OSError:
            print('EX: unable to write ' + dm_file)


def _already_liked(base_dir: str, nickname: str, domain: str,
                   post_url: str, liker_actor: str) -> bool:
    """Is the given post already liked by the given handle?
    """
    post_filename = \
        locate_post(base_dir, nickname, domain, post_url)
    if not post_filename:
        return False
    post_json_object = load_json(post_filename, 1)
    if not post_json_object:
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('likes'):
        return False
    if not post_json_object['object']['likes'].get('items'):
        return False
    for like in post_json_object['object']['likes']['items']:
        if not like.get('type'):
            continue
        if not like.get('actor'):
            continue
        if like['type'] != 'Like':
            continue
        if like['actor'] == liker_actor:
            return True
    return False


def _already_reacted(base_dir: str, nickname: str, domain: str,
                     post_url: str, reaction_actor: str,
                     emoji_content: str) -> bool:
    """Is the given post already emoji reacted by the given handle?
    """
    post_filename = \
        locate_post(base_dir, nickname, domain, post_url)
    if not post_filename:
        return False
    post_json_object = load_json(post_filename, 1)
    if not post_json_object:
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('reactions'):
        return False
    if not post_json_object['object']['reactions'].get('items'):
        return False
    for react in post_json_object['object']['reactions']['items']:
        if not react.get('type'):
            continue
        if not react.get('content'):
            continue
        if not react.get('actor'):
            continue
        if react['type'] != 'EmojiReact':
            continue
        if react['content'] != emoji_content:
            continue
        if react['actor'] == reaction_actor:
            return True
    return False


def _like_notify(base_dir: str, domain: str,
                 onion_domain: str, i2p_domain: str,
                 handle: str, actor: str, url: str) -> None:
    """Creates a notification that a like has arrived
    """
    # This is not you liking your own post
    if actor in url:
        return

    # check that the liked post was by this handle
    nickname = handle.split('@')[0]
    if '/' + domain + '/users/' + nickname not in url:
        if onion_domain:
            if '/' + onion_domain + '/users/' + nickname not in url:
                return
        if i2p_domain:
            if '/' + i2p_domain + '/users/' + nickname not in url:
                return
        if not i2p_domain and not onion_domain:
            return

    account_dir = base_dir + '/accounts/' + handle

    # are like notifications enabled?
    notify_likes_enabled_filename = account_dir + '/.notifyLikes'
    if not os.path.isfile(notify_likes_enabled_filename):
        return

    like_file = account_dir + '/.newLike'
    if os.path.isfile(like_file):
        if not text_in_file('##sent##', like_file):
            return

    liker_nickname = get_nickname_from_actor(actor)
    liker_domain, _ = get_domain_from_actor(actor)
    if liker_nickname and liker_domain:
        liker_handle = liker_nickname + '@' + liker_domain
    else:
        print('_like_notify liker_handle: ' +
              str(liker_nickname) + '@' + str(liker_domain))
        liker_handle = actor
    if liker_handle == handle:
        return
    like_str = liker_handle + ' ' + url + '?likedBy=' + actor
    prev_like_file = account_dir + '/.prevLike'
    # was there a previous like notification?
    if os.path.isfile(prev_like_file):
        # is it the same as the current notification ?
        with open(prev_like_file, 'r', encoding='utf-8') as fp_like:
            prev_like_str = fp_like.read()
            if prev_like_str == like_str:
                return
    try:
        with open(prev_like_file, 'w+', encoding='utf-8') as fp_like:
            fp_like.write(like_str)
    except OSError:
        print('EX: ERROR: unable to save previous like notification ' +
              prev_like_file)

    try:
        with open(like_file, 'w+', encoding='utf-8') as fp_like:
            fp_like.write(like_str)
    except OSError:
        print('EX: ERROR: unable to write like notification file ' +
              like_file)


def _reaction_notify(base_dir: str, domain: str, onion_domain: str,
                     handle: str, actor: str,
                     url: str, emoji_content: str) -> None:
    """Creates a notification that an emoji reaction has arrived
    """
    # This is not you reacting to your own post
    if actor in url:
        return

    # check that the reaction post was by this handle
    nickname = handle.split('@')[0]
    if '/' + domain + '/users/' + nickname not in url:
        if not onion_domain:
            return
        if '/' + onion_domain + '/users/' + nickname not in url:
            return

    account_dir = base_dir + '/accounts/' + handle

    # are reaction notifications enabled?
    notify_reaction_enabled_filename = account_dir + '/.notifyReactions'
    if not os.path.isfile(notify_reaction_enabled_filename):
        return

    reaction_file = account_dir + '/.newReaction'
    if os.path.isfile(reaction_file):
        if not text_in_file('##sent##', reaction_file):
            return

    reaction_nickname = get_nickname_from_actor(actor)
    reaction_domain, _ = get_domain_from_actor(actor)
    if reaction_nickname and reaction_domain:
        reaction_handle = reaction_nickname + '@' + reaction_domain
    else:
        print('_reaction_notify reaction_handle: ' +
              str(reaction_nickname) + '@' + str(reaction_domain))
        reaction_handle = actor
    if reaction_handle == handle:
        return
    reaction_str = \
        reaction_handle + ' ' + url + '?reactBy=' + actor + \
        ';emoj=' + emoji_content
    prev_reaction_file = account_dir + '/.prevReaction'
    # was there a previous reaction notification?
    if os.path.isfile(prev_reaction_file):
        # is it the same as the current notification ?
        with open(prev_reaction_file, 'r', encoding='utf-8') as fp_react:
            prev_reaction_str = fp_react.read()
            if prev_reaction_str == reaction_str:
                return
    try:
        with open(prev_reaction_file, 'w+', encoding='utf-8') as fp_react:
            fp_react.write(reaction_str)
    except OSError:
        print('EX: ERROR: unable to save previous reaction notification ' +
              prev_reaction_file)

    try:
        with open(reaction_file, 'w+', encoding='utf-8') as fp_react:
            fp_react.write(reaction_str)
    except OSError:
        print('EX: ERROR: unable to write reaction notification file ' +
              reaction_file)


def _notify_post_arrival(base_dir: str, handle: str, url: str) -> None:
    """Creates a notification that a new post has arrived.
    This is for followed accounts with the notify checkbox enabled
    on the person options screen
    """
    account_dir = base_dir + '/accounts/' + handle
    if not os.path.isdir(account_dir):
        return
    notify_file = account_dir + '/.newNotifiedPost'
    if os.path.isfile(notify_file):
        # check that the same notification is not repeatedly sent
        with open(notify_file, 'r', encoding='utf-8') as fp_notify:
            existing_notification_message = fp_notify.read()
            if url in existing_notification_message:
                return
    try:
        with open(notify_file, 'w+', encoding='utf-8') as fp_notify:
            fp_notify.write(url)
    except OSError:
        print('EX: unable to write ' + notify_file)


def _reply_notify(base_dir: str, handle: str, url: str) -> None:
    """Creates a notification that a new reply has arrived
    """
    account_dir = base_dir + '/accounts/' + handle
    if not os.path.isdir(account_dir):
        return
    reply_file = account_dir + '/.newReply'
    if not os.path.isfile(reply_file):
        try:
            with open(reply_file, 'w+', encoding='utf-8') as fp_reply:
                fp_reply.write(url)
        except OSError:
            print('EX: unable to write ' + reply_file)


def _git_patch_notify(base_dir: str, handle: str, subject: str,
                      from_nickname: str, from_domain: str) -> None:
    """Creates a notification that a new git patch has arrived
    """
    account_dir = base_dir + '/accounts/' + handle
    if not os.path.isdir(account_dir):
        return
    patch_file = account_dir + '/.newPatch'
    subject = subject.replace('[PATCH]', '').strip()
    handle = '@' + from_nickname + '@' + from_domain
    try:
        with open(patch_file, 'w+', encoding='utf-8') as fp_patch:
            fp_patch.write('git ' + handle + ' ' + subject)
    except OSError:
        print('EX: unable to write ' + patch_file)


def _group_handle(base_dir: str, handle: str) -> bool:
    """Is the given account handle a group?
    """
    actor_file = base_dir + '/accounts/' + handle + '.json'
    if not os.path.isfile(actor_file):
        return False
    actor_json = load_json(actor_file)
    if not actor_json:
        return False
    if not actor_json.get('type'):
        return False
    return actor_json['type'] == 'Group'


def _send_to_group_members(server, session, session_onion, session_i2p,
                           base_dir: str, handle: str, port: int,
                           post_json_object: {},
                           http_prefix: str, federation_list: [],
                           send_threads: [], post_log: [],
                           cached_webfingers: {},
                           person_cache: {}, debug: bool,
                           curr_domain: str,
                           onion_domain: str, i2p_domain: str,
                           signing_priv_key_pem: str) -> None:
    """When a post arrives for a group send it out to the group members
    """
    if debug:
        print('\n\n=========================================================')
        print(handle + ' sending to group members')

    shared_item_federation_tokens = {}
    shared_items_federated_domains = []
    shared_items_federated_domains_str = \
        get_config_param(base_dir, 'shared_items_federated_domains')
    if shared_items_federated_domains_str:
        si_federated_domains_list = \
            shared_items_federated_domains_str.split(',')
        for shared_federated_domain in si_federated_domains_list:
            domain_str = shared_federated_domain.strip()
            shared_items_federated_domains.append(domain_str)

    followers_file = base_dir + '/accounts/' + handle + '/followers.txt'
    if not os.path.isfile(followers_file):
        return
    if not post_json_object.get('to'):
        return
    if not post_json_object.get('object'):
        return
    if not has_object_dict(post_json_object):
        return
    nickname = handle.split('@')[0].replace('!', '')
    domain = handle.split('@')[1]
    domain_full = get_full_domain(domain, port)
    group_actor = local_actor_url(http_prefix, nickname, domain_full)
    if group_actor not in post_json_object['to']:
        return
    cc_str = ''
    nickname = handle.split('@')[0].replace('!', '')

    # save to the group outbox so that replies will be to the group
    # rather than the original sender
    save_post_to_box(base_dir, http_prefix, None,
                     nickname, domain, post_json_object, 'outbox')

    post_id = remove_id_ending(post_json_object['object']['id'])
    if debug:
        print('Group announce: ' + post_id)
    announce_json = \
        create_announce(session, base_dir, federation_list,
                        nickname, domain, port,
                        group_actor + '/followers', cc_str,
                        http_prefix, post_id, False, False,
                        send_threads, post_log,
                        person_cache, cached_webfingers,
                        debug, __version__, signing_priv_key_pem,
                        curr_domain, onion_domain, i2p_domain)

    send_to_followers_thread(server, session, session_onion, session_i2p,
                             base_dir, nickname, domain,
                             onion_domain, i2p_domain, port,
                             http_prefix, federation_list,
                             send_threads, post_log,
                             cached_webfingers, person_cache,
                             announce_json, debug, __version__,
                             shared_items_federated_domains,
                             shared_item_federation_tokens,
                             signing_priv_key_pem)


def _inbox_update_calendar(base_dir: str, handle: str,
                           post_json_object: {}) -> None:
    """Detects whether the tag list on a post contains calendar events
    and if so saves the post id to a file in the calendar directory
    for the account
    """
    if not post_json_object.get('actor'):
        return
    if not has_object_dict(post_json_object):
        return
    if not post_json_object['object'].get('tag'):
        return
    if not isinstance(post_json_object['object']['tag'], list):
        return

    actor = post_json_object['actor']
    actor_nickname = get_nickname_from_actor(actor)
    if not actor_nickname:
        return
    actor_domain, _ = get_domain_from_actor(actor)
    handle_nickname = handle.split('@')[0]
    handle_domain = handle.split('@')[1]
    if not receiving_calendar_events(base_dir,
                                     handle_nickname, handle_domain,
                                     actor_nickname, actor_domain):
        return

    post_id = remove_id_ending(post_json_object['id']).replace('/', '#')

    # look for events within the tags list
    for tag_dict in post_json_object['object']['tag']:
        if not tag_dict.get('type'):
            continue
        if tag_dict['type'] != 'Event':
            continue
        if not tag_dict.get('startTime'):
            continue
        save_event_post(base_dir, handle, post_id, tag_dict)


def inbox_update_index(boxname: str, base_dir: str, handle: str,
                       destination_filename: str, debug: bool) -> bool:
    """Updates the index of received posts
    The new entry is added to the top of the file
    """
    index_filename = \
        base_dir + '/accounts/' + handle + '/' + boxname + '.index'
    if debug:
        print('DEBUG: Updating index ' + index_filename)

    if '/' + boxname + '/' in destination_filename:
        destination_filename = \
            destination_filename.split('/' + boxname + '/')[1]

    # remove the path
    if '/' in destination_filename:
        destination_filename = destination_filename.split('/')[-1]

    written = False
    if os.path.isfile(index_filename):
        try:
            with open(index_filename, 'r+', encoding='utf-8') as index_file:
                content = index_file.read()
                if destination_filename + '\n' not in content:
                    index_file.seek(0, 0)
                    index_file.write(destination_filename + '\n' + content)
                written = True
                return True
        except OSError as ex:
            print('EX: Failed to write entry to index ' + str(ex))
    else:
        try:
            with open(index_filename, 'w+', encoding='utf-8') as index_file:
                index_file.write(destination_filename + '\n')
                written = True
        except OSError as ex:
            print('EX: Failed to write initial entry to index ' + str(ex))

    return written


def _update_last_seen(base_dir: str, handle: str, actor: str) -> None:
    """Updates the time when the given handle last saw the given actor
    This can later be used to indicate if accounts are dormant/abandoned/moved
    """
    if '@' not in handle:
        return
    nickname = handle.split('@')[0]
    domain = handle.split('@')[1]
    domain = remove_domain_port(domain)
    account_path = acct_dir(base_dir, nickname, domain)
    if not os.path.isdir(account_path):
        return
    if not is_following_actor(base_dir, nickname, domain, actor):
        return
    last_seen_path = account_path + '/lastseen'
    if not os.path.isdir(last_seen_path):
        os.mkdir(last_seen_path)
    last_seen_filename = \
        last_seen_path + '/' + actor.replace('/', '#') + '.txt'
    curr_time = datetime.datetime.utcnow()
    days_since_epoch = (curr_time - datetime.datetime(1970, 1, 1)).days
    # has the value changed?
    if os.path.isfile(last_seen_filename):
        with open(last_seen_filename, 'r',
                  encoding='utf-8') as last_seen_file:
            days_since_epoch_file = last_seen_file.read()
            if int(days_since_epoch_file) == days_since_epoch:
                # value hasn't changed, so we can save writing anything to file
                return
    try:
        with open(last_seen_filename, 'w+',
                  encoding='utf-8') as last_seen_file:
            last_seen_file.write(str(days_since_epoch))
    except OSError:
        print('EX: unable to write ' + last_seen_filename)


def _bounce_dm(sender_post_id: str, session, http_prefix: str,
               base_dir: str, nickname: str, domain: str, port: int,
               sending_handle: str, federation_list: [],
               send_threads: [], post_log: [],
               cached_webfingers: {}, person_cache: {},
               translate: {}, debug: bool,
               last_bounce_message: [], system_language: str,
               signing_priv_key_pem: str,
               content_license_url: str,
               languages_understood: [],
               bounce_is_chat: bool,
               curr_domain: str, onion_domain: str, i2p_domain: str) -> bool:
    """Sends a bounce message back to the sending handle
    if a DM has been rejected
    """
    print(nickname + '@' + domain +
          ' cannot receive DM from ' + sending_handle +
          ' because they do not follow them')

    # Don't send out bounce messages too frequently.
    # Otherwise an adversary could try to DoS your instance
    # by continuously sending DMs to you
    curr_time = int(time.time())
    if curr_time - last_bounce_message[0] < 60:
        return False

    # record the last time that a bounce was generated
    last_bounce_message[0] = curr_time

    sender_nickname = sending_handle.split('@')[0]
    group_account = False
    if sending_handle.startswith('!'):
        sending_handle = sending_handle[1:]
        group_account = True
    sender_domain = sending_handle.split('@')[1]
    sender_port = port
    if ':' in sender_domain:
        sender_port = get_port_from_domain(sender_domain)
        sender_domain = remove_domain_port(sender_domain)

    # create the bounce DM
    subject = None
    content = translate['DM bounce']
    save_to_file = False
    client_to_server = False
    comments_enabled = False
    attach_image_filename = None
    media_type = None
    image_description = ''
    city = 'London, England'
    in_reply_to = remove_id_ending(sender_post_id)
    in_reply_to_atom_uri = None
    schedule_post = False
    event_date = None
    event_time = None
    event_end_time = None
    location = None
    conversation_id = None
    low_bandwidth = False
    post_json_object = \
        create_direct_message_post(base_dir, nickname, domain, port,
                                   http_prefix, content,
                                   save_to_file, client_to_server,
                                   comments_enabled,
                                   attach_image_filename, media_type,
                                   image_description, city,
                                   in_reply_to, in_reply_to_atom_uri,
                                   subject, debug, schedule_post,
                                   event_date, event_time, event_end_time,
                                   location, system_language, conversation_id,
                                   low_bandwidth,
                                   content_license_url,
                                   languages_understood, bounce_is_chat,
                                   translate)
    if not post_json_object:
        print('WARN: unable to create bounce message to ' + sending_handle)
        return False
    # bounce DM goes back to the sender
    print('Sending bounce DM to ' + sending_handle)
    send_signed_json(post_json_object, session, base_dir,
                     nickname, domain, port,
                     sender_nickname, sender_domain, sender_port,
                     http_prefix, False, federation_list,
                     send_threads, post_log, cached_webfingers,
                     person_cache, debug, __version__, None, group_account,
                     signing_priv_key_pem, 7238634,
                     curr_domain, onion_domain, i2p_domain)
    return True


def _is_valid_dm(base_dir: str, nickname: str, domain: str, port: int,
                 post_json_object: {}, update_index_list: [],
                 session, http_prefix: str,
                 federation_list: [],
                 send_threads: [], post_log: [],
                 cached_webfingers: {},
                 person_cache: {},
                 translate: {}, debug: bool,
                 last_bounce_message: [],
                 handle: str, system_language: str,
                 signing_priv_key_pem: str,
                 content_license_url: str,
                 languages_understood: [],
                 curr_domain: str, onion_domain: str, i2p_domain: str) -> bool:
    """Is the given message a valid DM?
    """
    if nickname == 'inbox':
        # going to the shared inbox
        return True

    # check for the flag file which indicates to
    # only receive DMs from people you are following
    follow_dms_filename = acct_dir(base_dir, nickname, domain) + '/.followDMs'
    if not os.path.isfile(follow_dms_filename):
        # dm index will be updated
        update_index_list.append('dm')
        act_url = local_actor_url(http_prefix, nickname, domain)
        _dm_notify(base_dir, handle, act_url + '/dm')
        return True

    # get the file containing following handles
    following_filename = \
        acct_dir(base_dir, nickname, domain) + '/following.txt'
    # who is sending a DM?
    if not post_json_object.get('actor'):
        return False
    sending_actor = post_json_object['actor']
    sending_actor_nickname = \
        get_nickname_from_actor(sending_actor)
    if not sending_actor_nickname:
        return False
    sending_actor_domain, _ = \
        get_domain_from_actor(sending_actor)
    if not sending_actor_domain:
        return False
    # Is this DM to yourself? eg. a reminder
    sending_to_self = False
    if sending_actor_nickname == nickname and \
       sending_actor_domain == domain:
        sending_to_self = True

    # check that the following file exists
    if not sending_to_self:
        if not os.path.isfile(following_filename):
            print('No following.txt file exists for ' +
                  nickname + '@' + domain +
                  ' so not accepting DM from ' +
                  sending_actor_nickname + '@' +
                  sending_actor_domain)
            return False

    # Not sending to yourself
    if not sending_to_self:
        # get the handle of the DM sender
        send_h = sending_actor_nickname + '@' + sending_actor_domain
        # check the follow
        if not is_following_actor(base_dir, nickname, domain, send_h):
            # DMs may always be allowed from some domains
            if not dm_allowed_from_domain(base_dir,
                                          nickname, domain,
                                          sending_actor_domain):
                # send back a bounce DM
                if post_json_object.get('id') and \
                   post_json_object.get('object'):
                    # don't send bounces back to
                    # replies to bounce messages
                    obj = post_json_object['object']
                    if isinstance(obj, dict):
                        if not obj.get('inReplyTo'):
                            bounced_id = \
                                remove_id_ending(post_json_object['id'])
                            bounce_chat = False
                            if obj.get('type'):
                                if obj['type'] == 'ChatMessage':
                                    bounce_chat = True
                            _bounce_dm(bounced_id,
                                       session, http_prefix,
                                       base_dir,
                                       nickname, domain,
                                       port, send_h,
                                       federation_list,
                                       send_threads, post_log,
                                       cached_webfingers,
                                       person_cache,
                                       translate, debug,
                                       last_bounce_message,
                                       system_language,
                                       signing_priv_key_pem,
                                       content_license_url,
                                       languages_understood,
                                       bounce_chat,
                                       curr_domain,
                                       onion_domain, i2p_domain)
                return False

    # dm index will be updated
    update_index_list.append('dm')
    act_url = local_actor_url(http_prefix, nickname, domain)
    _dm_notify(base_dir, handle, act_url + '/dm')
    return True


def _receive_question_vote(server, base_dir: str, nickname: str, domain: str,
                           http_prefix: str, handle: str, debug: bool,
                           post_json_object: {}, recent_posts_cache: {},
                           session, session_onion, session_i2p,
                           onion_domain: str, i2p_domain: str, port: int,
                           federation_list: [], send_threads: [], post_log: [],
                           cached_webfingers: {}, person_cache: {},
                           signing_priv_key_pem: str,
                           max_recent_posts: int, translate: {},
                           allow_deletion: bool,
                           yt_replace_domain: str,
                           twitter_replacement_domain: str,
                           peertube_instances: [],
                           allow_local_network_access: bool,
                           theme_name: str, system_language: str,
                           max_like_count: int,
                           cw_lists: {}, lists_enabled: bool,
                           bold_reading: bool, dogwhistles: {}) -> None:
    """Updates the votes on a Question/poll
    """
    # if this is a reply to a question then update the votes
    question_json, question_post_filename = \
        question_update_votes(base_dir, nickname, domain, post_json_object)
    if not question_json:
        return
    if not question_post_filename:
        return

    remove_post_from_cache(question_json, recent_posts_cache)
    # ensure that the cached post is removed if it exists, so
    # that it then will be recreated
    cached_post_filename = \
        get_cached_post_filename(base_dir, nickname, domain, question_json)
    if cached_post_filename:
        if os.path.isfile(cached_post_filename):
            try:
                os.remove(cached_post_filename)
            except OSError:
                print('EX: replytoQuestion unable to delete ' +
                      cached_post_filename)

    page_number = 1
    show_published_date_only = False
    show_individual_post_icons = True
    manually_approve_followers = \
        follower_approval_active(base_dir, nickname, domain)
    not_dm = not is_dm(question_json)
    timezone = get_account_timezone(base_dir, nickname, domain)
    mitm = False
    if os.path.isfile(question_post_filename.replace('.json', '') + '.mitm'):
        mitm = True
    individual_post_as_html(signing_priv_key_pem, False,
                            recent_posts_cache, max_recent_posts,
                            translate, page_number, base_dir,
                            session, cached_webfingers, person_cache,
                            nickname, domain, port, question_json,
                            None, True, allow_deletion,
                            http_prefix, __version__,
                            'inbox',
                            yt_replace_domain,
                            twitter_replacement_domain,
                            show_published_date_only,
                            peertube_instances,
                            allow_local_network_access,
                            theme_name, system_language,
                            max_like_count, not_dm,
                            show_individual_post_icons,
                            manually_approve_followers,
                            False, True, False, cw_lists,
                            lists_enabled, timezone, mitm,
                            bold_reading, dogwhistles)

    # add id to inbox index
    inbox_update_index('inbox', base_dir, handle,
                       question_post_filename, debug)

    # Is this a question created by this instance?
    id_prefix = http_prefix + '://' + domain
    if not question_json['object']['id'].startswith(id_prefix):
        return
    # if the votes on a question have changed then
    # send out an update
    question_json['type'] = 'Update'
    shared_items_federated_domains = []
    shared_item_federation_tokens = {}
    send_to_followers_thread(server, session, session_onion, session_i2p,
                             base_dir, nickname, domain,
                             onion_domain, i2p_domain, port,
                             http_prefix, federation_list,
                             send_threads, post_log,
                             cached_webfingers, person_cache,
                             post_json_object, debug, __version__,
                             shared_items_federated_domains,
                             shared_item_federation_tokens,
                             signing_priv_key_pem)


def _create_reply_notification_file(base_dir: str, nickname: str, domain: str,
                                    handle: str, debug: bool, post_is_dm: bool,
                                    post_json_object: {}, actor: str,
                                    update_index_list: [], http_prefix: str,
                                    default_reply_interval_hrs: int) -> bool:
    """Generates a file indicating that a new reply has arrived
    The file can then be used by other systems to create a notification
    xmpp, matrix, email, etc
    """
    is_reply_to_muted_post = False
    if post_is_dm:
        return is_reply_to_muted_post
    if not is_reply(post_json_object, actor):
        return is_reply_to_muted_post
    if nickname == 'inbox':
        return is_reply_to_muted_post
    # replies index will be updated
    update_index_list.append('tlreplies')

    conversation_id = None
    if post_json_object['object'].get('conversation'):
        conversation_id = post_json_object['object']['conversation']

    if not post_json_object['object'].get('inReplyTo'):
        return is_reply_to_muted_post
    in_reply_to = post_json_object['object']['inReplyTo']
    if not in_reply_to:
        return is_reply_to_muted_post
    if not isinstance(in_reply_to, str):
        return is_reply_to_muted_post
    if not is_muted_conv(base_dir, nickname, domain, in_reply_to,
                         conversation_id):
        # check if the reply is within the allowed time period
        # after publication
        reply_interval_hours = \
            get_reply_interval_hours(base_dir, nickname, domain,
                                     default_reply_interval_hrs)
        if can_reply_to(base_dir, nickname, domain, in_reply_to,
                        reply_interval_hours):
            act_url = local_actor_url(http_prefix, nickname, domain)
            _reply_notify(base_dir, handle, act_url + '/tlreplies')
        else:
            if debug:
                print('Reply to ' + in_reply_to + ' is outside of the ' +
                      'permitted interval of ' + str(reply_interval_hours) +
                      ' hours')
            return False
    else:
        is_reply_to_muted_post = True
    return is_reply_to_muted_post


def _low_frequency_post_notification(base_dir: str, http_prefix: str,
                                     nickname: str, domain: str,
                                     port: int, handle: str,
                                     post_is_dm: bool, json_obj: {}) -> None:
    """Should we notify that a post from this person has arrived?
    This is for cases where the notify checkbox is enabled on the
    person options screen
    """
    if post_is_dm:
        return
    if not json_obj:
        return
    if not json_obj.get('attributedTo'):
        return
    if not json_obj.get('id'):
        return
    attributed_to = json_obj['attributedTo']
    if not isinstance(attributed_to, str):
        return
    from_nickname = get_nickname_from_actor(attributed_to)
    if not from_nickname:
        return
    from_domain, from_port = get_domain_from_actor(attributed_to)
    from_domain_full = get_full_domain(from_domain, from_port)
    if notify_when_person_posts(base_dir, nickname, domain,
                                from_nickname, from_domain_full):
        post_id = remove_id_ending(json_obj['id'])
        dom_full = get_full_domain(domain, port)
        post_link = \
            local_actor_url(http_prefix, nickname, dom_full) + \
            '?notifypost=' + post_id.replace('/', '-')
        _notify_post_arrival(base_dir, handle, post_link)


def _check_for_git_patches(base_dir: str, nickname: str, domain: str,
                           handle: str, json_obj: {}) -> int:
    """check for incoming git patches
    """
    if not json_obj:
        return 0
    if not json_obj.get('content'):
        return 0
    if not json_obj.get('summary'):
        return 0
    if not json_obj.get('attributedTo'):
        return 0
    attributed_to = json_obj['attributedTo']
    if not isinstance(attributed_to, str):
        return 0
    from_nickname = get_nickname_from_actor(attributed_to)
    if not from_nickname:
        return 0
    from_domain, from_port = get_domain_from_actor(attributed_to)
    from_domain_full = get_full_domain(from_domain, from_port)
    if receive_git_patch(base_dir, nickname, domain,
                         json_obj['type'], json_obj['summary'],
                         json_obj['content'],
                         from_nickname, from_domain_full):
        _git_patch_notify(base_dir, handle, json_obj['summary'],
                          from_nickname, from_domain_full)
        return 1
    if '[PATCH]' in json_obj['content']:
        print('WARN: git patch not accepted - ' + json_obj['summary'])
        return 2
    return 0


def _inbox_after_initial(server, inbox_start_time,
                         recent_posts_cache: {}, max_recent_posts: int,
                         session, session_onion, session_i2p,
                         key_id: str, handle: str, message_json: {},
                         base_dir: str, http_prefix: str, send_threads: [],
                         post_log: [], cached_webfingers: {}, person_cache: {},
                         domain: str, onion_domain: str, i2p_domain: str,
                         port: int, federation_list: [], debug: bool,
                         queue_filename: str, destination_filename: str,
                         max_replies: int, allow_deletion: bool,
                         max_mentions: int, max_emoji: int, translate: {},
                         unit_test: bool,
                         yt_replace_domain: str,
                         twitter_replacement_domain: str,
                         show_published_date_only: bool,
                         allow_local_network_access: bool,
                         peertube_instances: [],
                         last_bounce_message: [],
                         theme_name: str, system_language: str,
                         max_like_count: int,
                         signing_priv_key_pem: str,
                         default_reply_interval_hrs: int,
                         cw_lists: {}, lists_enabled: str,
                         content_license_url: str,
                         languages_understood: [],
                         mitm: bool, bold_reading: bool,
                         dogwhistles: {}) -> bool:
    """ Anything which needs to be done after initial checks have passed
    """
    # if this is a clearnet instance then replace any onion/i2p
    # domains with the account domain
    if onion_domain or i2p_domain:
        message_str = json.dumps(message_json, ensure_ascii=False)
        if onion_domain:
            if onion_domain in message_str:
                message_str = message_str.replace(onion_domain, domain)
                message_json = json.loads(message_str)
        if i2p_domain:
            if i2p_domain in message_str:
                message_str = message_str.replace(i2p_domain, domain)
                message_json = json.loads(message_str)

    actor = key_id
    if '#' in actor:
        actor = key_id.split('#')[0]

    _update_last_seen(base_dir, handle, actor)

    post_is_dm = False
    is_group = _group_handle(base_dir, handle)
    fitness_performance(inbox_start_time, server.fitness,
                        'INBOX', '_group_handle',
                        debug)
    inbox_start_time = time.time()

    handle_name = handle.split('@')[0]

    if _receive_like(recent_posts_cache,
                     session, handle,
                     base_dir, http_prefix,
                     domain, port,
                     onion_domain, i2p_domain,
                     cached_webfingers,
                     person_cache,
                     message_json,
                     debug, signing_priv_key_pem,
                     max_recent_posts, translate,
                     allow_deletion,
                     yt_replace_domain,
                     twitter_replacement_domain,
                     peertube_instances,
                     allow_local_network_access,
                     theme_name, system_language,
                     max_like_count, cw_lists, lists_enabled,
                     bold_reading, dogwhistles):
        if debug:
            print('DEBUG: Like accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_like',
                            debug)
        inbox_start_time = time.time()
        return False

    if _receive_undo_like(recent_posts_cache,
                          session, handle,
                          base_dir, http_prefix,
                          domain, port,
                          cached_webfingers,
                          person_cache,
                          message_json,
                          debug, signing_priv_key_pem,
                          max_recent_posts, translate,
                          allow_deletion,
                          yt_replace_domain,
                          twitter_replacement_domain,
                          peertube_instances,
                          allow_local_network_access,
                          theme_name, system_language,
                          max_like_count, cw_lists, lists_enabled,
                          bold_reading, dogwhistles):
        if debug:
            print('DEBUG: Undo like accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_undo_like',
                            debug)
        inbox_start_time = time.time()
        return False

    if _receive_reaction(recent_posts_cache,
                         session, handle,
                         base_dir, http_prefix,
                         domain, port,
                         onion_domain,
                         cached_webfingers,
                         person_cache,
                         message_json,
                         debug, signing_priv_key_pem,
                         max_recent_posts, translate,
                         allow_deletion,
                         yt_replace_domain,
                         twitter_replacement_domain,
                         peertube_instances,
                         allow_local_network_access,
                         theme_name, system_language,
                         max_like_count, cw_lists, lists_enabled,
                         bold_reading, dogwhistles):
        if debug:
            print('DEBUG: Reaction accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_reaction',
                            debug)
        inbox_start_time = time.time()
        return False

    if _receive_zot_reaction(recent_posts_cache,
                             session, handle,
                             base_dir, http_prefix,
                             domain, port,
                             onion_domain,
                             cached_webfingers,
                             person_cache,
                             message_json,
                             debug, signing_priv_key_pem,
                             max_recent_posts, translate,
                             allow_deletion,
                             yt_replace_domain,
                             twitter_replacement_domain,
                             peertube_instances,
                             allow_local_network_access,
                             theme_name, system_language,
                             max_like_count, cw_lists, lists_enabled,
                             bold_reading, dogwhistles):
        if debug:
            print('DEBUG: Zot reaction accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_zot_reaction',
                            debug)
        inbox_start_time = time.time()
        return False

    if _receive_undo_reaction(recent_posts_cache,
                              session, handle, is_group,
                              base_dir, http_prefix,
                              domain, port,
                              send_threads, post_log,
                              cached_webfingers,
                              person_cache,
                              message_json,
                              federation_list,
                              debug, signing_priv_key_pem,
                              max_recent_posts, translate,
                              allow_deletion,
                              yt_replace_domain,
                              twitter_replacement_domain,
                              peertube_instances,
                              allow_local_network_access,
                              theme_name, system_language,
                              max_like_count, cw_lists, lists_enabled,
                              bold_reading, dogwhistles):
        if debug:
            print('DEBUG: Undo reaction accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_undo_reaction',
                            debug)
        inbox_start_time = time.time()
        return False

    if _receive_bookmark(recent_posts_cache,
                         session, handle, is_group,
                         base_dir, http_prefix,
                         domain, port,
                         send_threads, post_log,
                         cached_webfingers,
                         person_cache,
                         message_json,
                         federation_list,
                         debug, signing_priv_key_pem,
                         max_recent_posts, translate,
                         allow_deletion,
                         yt_replace_domain,
                         twitter_replacement_domain,
                         peertube_instances,
                         allow_local_network_access,
                         theme_name, system_language,
                         max_like_count, cw_lists, lists_enabled,
                         bold_reading, dogwhistles):
        if debug:
            print('DEBUG: Bookmark accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_bookmark',
                            debug)
        inbox_start_time = time.time()
        return False

    if _receive_undo_bookmark(recent_posts_cache,
                              session, handle, is_group,
                              base_dir, http_prefix,
                              domain, port,
                              send_threads, post_log,
                              cached_webfingers,
                              person_cache,
                              message_json,
                              federation_list,
                              debug, signing_priv_key_pem,
                              max_recent_posts, translate,
                              allow_deletion,
                              yt_replace_domain,
                              twitter_replacement_domain,
                              peertube_instances,
                              allow_local_network_access,
                              theme_name, system_language,
                              max_like_count, cw_lists, lists_enabled,
                              bold_reading, dogwhistles):
        if debug:
            print('DEBUG: Undo bookmark accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_undo_bookmark',
                            debug)
        inbox_start_time = time.time()
        return False

    if is_create_inside_announce(message_json):
        message_json = message_json['object']
    fitness_performance(inbox_start_time, server.fitness,
                        'INBOX', 'is_create_inside_announce',
                        debug)
    inbox_start_time = time.time()

    if _receive_announce(recent_posts_cache,
                         session, handle, is_group,
                         base_dir, http_prefix,
                         domain, onion_domain, i2p_domain, port,
                         send_threads, post_log,
                         cached_webfingers,
                         person_cache,
                         message_json,
                         federation_list,
                         debug, translate,
                         yt_replace_domain,
                         twitter_replacement_domain,
                         allow_local_network_access,
                         theme_name, system_language,
                         signing_priv_key_pem,
                         max_recent_posts,
                         allow_deletion,
                         peertube_instances,
                         max_like_count, cw_lists, lists_enabled,
                         bold_reading, dogwhistles):
        if debug:
            print('DEBUG: Announce accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_announce',
                            debug)
        inbox_start_time = time.time()

    if _receive_undo_announce(recent_posts_cache,
                              session, handle, is_group,
                              base_dir, http_prefix,
                              domain, port,
                              send_threads, post_log,
                              cached_webfingers,
                              person_cache,
                              message_json,
                              federation_list,
                              debug):
        if debug:
            print('DEBUG: Undo announce accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_undo_announce',
                            debug)
        inbox_start_time = time.time()
        return False

    if _receive_delete(session, handle, is_group,
                       base_dir, http_prefix,
                       domain, port,
                       send_threads, post_log,
                       cached_webfingers,
                       person_cache,
                       message_json,
                       federation_list,
                       debug, allow_deletion,
                       recent_posts_cache):
        if debug:
            print('DEBUG: Delete accepted from ' + actor)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_delete',
                            debug)
        inbox_start_time = time.time()
        return False

    if debug:
        print('DEBUG: initial checks passed')
        print('copy queue file from ' + queue_filename +
              ' to ' + destination_filename)

    if os.path.isfile(destination_filename):
        return True

    if message_json.get('postNickname'):
        post_json_object = message_json['post']
    else:
        post_json_object = message_json

    nickname = handle.split('@')[0]
    json_obj = None
    domain_full = get_full_domain(domain, port)
    if _valid_post_content(base_dir, nickname, domain,
                           post_json_object, max_mentions, max_emoji,
                           allow_local_network_access, debug,
                           system_language, http_prefix,
                           domain_full, person_cache):
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_valid_post_content',
                            debug)
        inbox_start_time = time.time()
        # is the sending actor valid?
        if not valid_sending_actor(session, base_dir, nickname, domain,
                                   person_cache, post_json_object,
                                   signing_priv_key_pem, debug, unit_test):
            if debug:
                print('Inbox sending actor is not valid ' +
                      str(post_json_object))
                fitness_performance(inbox_start_time, server.fitness,
                                    'INBOX', 'not_valid_sending_actor',
                                    debug)
                inbox_start_time = time.time()
            return False
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'valid_sending_actor',
                            debug)
        inbox_start_time = time.time()

        if post_json_object.get('object'):
            json_obj = post_json_object['object']
            if not isinstance(json_obj, dict):
                json_obj = None
        else:
            json_obj = post_json_object

        if _check_for_git_patches(base_dir, nickname, domain,
                                  handle, json_obj) == 2:
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', '_check_for_git_patches',
                                debug)
            inbox_start_time = time.time()
            return False

        # replace YouTube links, so they get less tracking data
        replace_you_tube(post_json_object, yt_replace_domain, system_language)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'replace_you_tube',
                            debug)
        inbox_start_time = time.time()
        # replace twitter link domains, so that you can view twitter posts
        # without having an account
        replace_twitter(post_json_object, twitter_replacement_domain,
                        system_language)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'replace_you_twitter',
                            debug)
        inbox_start_time = time.time()

        # list of indexes to be updated
        update_index_list = ['inbox']
        populate_replies(base_dir, http_prefix, domain, post_json_object,
                         max_replies, debug)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'populate_replies',
                            debug)
        inbox_start_time = time.time()

        _receive_question_vote(server, base_dir, nickname, domain,
                               http_prefix, handle, debug,
                               post_json_object, recent_posts_cache,
                               session, session_onion, session_i2p,
                               onion_domain, i2p_domain, port,
                               federation_list, send_threads, post_log,
                               cached_webfingers, person_cache,
                               signing_priv_key_pem,
                               max_recent_posts, translate,
                               allow_deletion,
                               yt_replace_domain,
                               twitter_replacement_domain,
                               peertube_instances,
                               allow_local_network_access,
                               theme_name, system_language,
                               max_like_count,
                               cw_lists, lists_enabled,
                               bold_reading, dogwhistles)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_receive_question_vote',
                            debug)
        inbox_start_time = time.time()

        is_reply_to_muted_post = False

        if not is_group:
            # create a DM notification file if needed
            post_is_dm = is_dm(post_json_object)
            if post_is_dm:
                if not _is_valid_dm(base_dir, nickname, domain, port,
                                    post_json_object, update_index_list,
                                    session, http_prefix,
                                    federation_list,
                                    send_threads, post_log,
                                    cached_webfingers,
                                    person_cache,
                                    translate, debug,
                                    last_bounce_message,
                                    handle, system_language,
                                    signing_priv_key_pem,
                                    content_license_url,
                                    languages_understood,
                                    domain,
                                    onion_domain, i2p_domain):
                    if debug:
                        print('Invalid DM ' + str(post_json_object))
                    return False
                fitness_performance(inbox_start_time, server.fitness,
                                    'INBOX', '_is_valid_dm',
                                    debug)
                inbox_start_time = time.time()

            # get the actor being replied to
            actor = local_actor_url(http_prefix, nickname, domain_full)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'local_actor_url',
                                debug)
            inbox_start_time = time.time()

            # create a reply notification file if needed
            is_reply_to_muted_post = \
                _create_reply_notification_file(base_dir, nickname, domain,
                                                handle, debug, post_is_dm,
                                                post_json_object, actor,
                                                update_index_list, http_prefix,
                                                default_reply_interval_hrs)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', '_create_reply_notification_file',
                                debug)
            inbox_start_time = time.time()

            if is_image_media(session, base_dir, http_prefix,
                              nickname, domain, post_json_object,
                              yt_replace_domain,
                              twitter_replacement_domain,
                              allow_local_network_access,
                              recent_posts_cache, debug, system_language,
                              domain_full, person_cache, signing_priv_key_pem,
                              bold_reading):
                # media index will be updated
                update_index_list.append('tlmedia')
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'is_image_media',
                                debug)
            inbox_start_time = time.time()
            if is_blog_post(post_json_object):
                # blogs index will be updated
                update_index_list.append('tlblogs')

        # get the avatar for a reply/announce
        _obtain_avatar_for_reply_post(session, base_dir,
                                      http_prefix, domain,
                                      onion_domain, i2p_domain,
                                      person_cache, post_json_object, debug,
                                      signing_priv_key_pem)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_obtain_avatar_for_reply_post',
                            debug)

        # cache any svg image attachments locally
        # This is so that any scripts can be removed
        cache_svg_images(session, base_dir, http_prefix,
                         nickname, domain, domain_full,
                         onion_domain, i2p_domain,
                         post_json_object,
                         federation_list, debug, None)

        inbox_start_time = time.time()

        # save the post to file
        if save_json(post_json_object, destination_filename):
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'save_json',
                                debug)
            inbox_start_time = time.time()
            if mitm:
                # write a file to indicate that this post was delivered
                # via a third party
                destination_filename_mitm = \
                    destination_filename.replace('.json', '') + '.mitm'
                try:
                    with open(destination_filename_mitm, 'w+',
                              encoding='utf-8') as mitm_file:
                        mitm_file.write('\n')
                except OSError:
                    print('EX: unable to write ' + destination_filename_mitm)

            _low_frequency_post_notification(base_dir, http_prefix,
                                             nickname, domain, port,
                                             handle, post_is_dm, json_obj)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', '_low_frequency_post_notification',
                                debug)
            inbox_start_time = time.time()

            # If this is a reply to a muted post then also mute it.
            # This enables you to ignore a threat that's getting boring
            if is_reply_to_muted_post:
                print('MUTE REPLY: ' + destination_filename)
                destination_filename_muted = destination_filename + '.muted'
                try:
                    with open(destination_filename_muted, 'w+',
                              encoding='utf-8') as mute_file:
                        mute_file.write('\n')
                except OSError:
                    print('EX: unable to write ' + destination_filename_muted)

            # is this an edit of a previous post?
            # in Mastodon "delete and redraft"
            # NOTE: this must be done before update_conversation is called
            edited_filename, edited_json = \
                edited_post_filename(base_dir, handle_name, domain,
                                     post_json_object, debug, 300,
                                     system_language)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'edited_post_filename',
                                debug)
            inbox_start_time = time.time()

            # If this was an edit then update the edits json file and
            # delete the previous version of the post
            if edited_filename and edited_json:
                prev_edits_filename = \
                    edited_filename.replace('.json', '.edits')
                edits_filename = \
                    destination_filename.replace('.json', '.edits')
                modified = edited_json['object']['published']
                if os.path.isfile(edits_filename):
                    edits_json = load_json(edits_filename)
                    if edits_json:
                        if not edits_json.get(modified):
                            edits_json[modified] = edited_json
                            save_json(edits_json, edits_filename)
                else:
                    if os.path.isfile(prev_edits_filename):
                        if prev_edits_filename != edits_filename:
                            try:
                                copyfile(prev_edits_filename, edits_filename)
                            except OSError:
                                print('EX: failed to copy edits file')
                        edits_json = load_json(edits_filename)
                        if edits_json:
                            if not edits_json.get(modified):
                                edits_json[modified] = edited_json
                                save_json(edits_json, edits_filename)
                    else:
                        edits_json = {
                            modified: edited_json
                        }
                        save_json(edits_json, edits_filename)

                if edited_filename != destination_filename:
                    delete_post(base_dir, http_prefix,
                                nickname, domain, edited_filename,
                                debug, recent_posts_cache, True)

            # update the indexes for different timelines
            for boxname in update_index_list:
                fitness_performance(inbox_start_time,
                                    server.fitness,
                                    'INBOX', 'box_' + boxname,
                                    debug)
                inbox_start_time = time.time()
                if not inbox_update_index(boxname, base_dir, handle,
                                          destination_filename, debug):
                    fitness_performance(inbox_start_time,
                                        server.fitness,
                                        'INBOX', 'inbox_update_index',
                                        debug)
                    inbox_start_time = time.time()
                    print('ERROR: unable to update ' + boxname + ' index')
                else:
                    if boxname == 'inbox':
                        if is_recent_post(post_json_object, 3):
                            domain_full = get_full_domain(domain, port)
                            update_speaker(base_dir, http_prefix,
                                           nickname, domain, domain_full,
                                           post_json_object, person_cache,
                                           translate, None, theme_name,
                                           system_language, boxname)
                            fitness_performance(inbox_start_time,
                                                server.fitness,
                                                'INBOX', 'update_speaker',
                                                debug)
                            inbox_start_time = time.time()
                    if not unit_test:
                        if debug:
                            print('Saving inbox post as html to cache')

                        html_cache_start_time = time.time()
                        allow_local_net_access = allow_local_network_access
                        show_pub_date_only = show_published_date_only
                        timezone = \
                            get_account_timezone(base_dir, handle_name, domain)
                        fitness_performance(inbox_start_time,
                                            server.fitness,
                                            'INBOX', 'get_account_timezone',
                                            debug)
                        inbox_start_time = time.time()
                        _inbox_store_post_to_html_cache(recent_posts_cache,
                                                        max_recent_posts,
                                                        translate, base_dir,
                                                        http_prefix,
                                                        session,
                                                        cached_webfingers,
                                                        person_cache,
                                                        handle_name,
                                                        domain, port,
                                                        post_json_object,
                                                        allow_deletion,
                                                        boxname,
                                                        show_pub_date_only,
                                                        peertube_instances,
                                                        allow_local_net_access,
                                                        theme_name,
                                                        system_language,
                                                        max_like_count,
                                                        signing_priv_key_pem,
                                                        cw_lists,
                                                        lists_enabled,
                                                        timezone, mitm,
                                                        bold_reading,
                                                        dogwhistles)
                        fitness_performance(inbox_start_time,
                                            server.fitness,
                                            'INBOX',
                                            '_inbox_store_post_to_html_cache',
                                            debug)
                        inbox_start_time = time.time()
                        if debug:
                            time_diff = \
                                str(int((time.time() - html_cache_start_time) *
                                        1000))
                            print('Saved ' +
                                  boxname + ' post as html to cache in ' +
                                  time_diff + ' mS')

            update_conversation(base_dir, handle_name, domain,
                                post_json_object)
            fitness_performance(inbox_start_time,
                                server.fitness,
                                'INBOX', 'update_conversation',
                                debug)
            inbox_start_time = time.time()

            # store the id of the last post made by this actor
            _store_last_post_id(base_dir, nickname, domain, post_json_object)
            fitness_performance(inbox_start_time,
                                server.fitness,
                                'INBOX', '_store_last_post_id',
                                debug)
            inbox_start_time = time.time()

            _inbox_update_calendar(base_dir, handle, post_json_object)
            fitness_performance(inbox_start_time,
                                server.fitness,
                                'INBOX', '_inbox_update_calendar',
                                debug)
            inbox_start_time = time.time()

            store_hash_tags(base_dir, handle_name, domain,
                            http_prefix, domain_full,
                            post_json_object, translate)
            fitness_performance(inbox_start_time,
                                server.fitness,
                                'INBOX', 'store_hash_tags',
                                debug)
            inbox_start_time = time.time()

            # send the post out to group members
            if is_group:
                _send_to_group_members(server,
                                       session, session_onion, session_i2p,
                                       base_dir, handle, port,
                                       post_json_object,
                                       http_prefix, federation_list,
                                       send_threads,
                                       post_log, cached_webfingers,
                                       person_cache, debug,
                                       domain, onion_domain, i2p_domain,
                                       signing_priv_key_pem)
                fitness_performance(inbox_start_time,
                                    server.fitness,
                                    'INBOX', '_send_to_group_members',
                                    debug)
                inbox_start_time = time.time()
    else:
        if debug:
            print("Inbox post is not valid " + str(post_json_object))
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'invalid_post',
                            debug)
        inbox_start_time = time.time()

    # if the post wasn't saved
    if not os.path.isfile(destination_filename):
        if debug:
            print("Inbox post was not saved " + destination_filename)
        return False
    fitness_performance(inbox_start_time,
                        server.fitness,
                        'INBOX', 'end_after_initial',
                        debug)
    inbox_start_time = time.time()

    return True


def clear_queue_items(base_dir: str, queue: []) -> None:
    """Clears the queue for each account
    """
    ctr = 0
    queue.clear()
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for account in dirs:
            queue_dir = base_dir + '/accounts/' + account + '/queue'
            if not os.path.isdir(queue_dir):
                continue
            for _, _, queuefiles in os.walk(queue_dir):
                for qfile in queuefiles:
                    try:
                        os.remove(os.path.join(queue_dir, qfile))
                        ctr += 1
                    except OSError:
                        print('EX: clear_queue_items unable to delete ' +
                              qfile)
                break
        break
    if ctr > 0:
        print('Removed ' + str(ctr) + ' inbox queue items')


def _restore_queue_items(base_dir: str, queue: []) -> None:
    """Checks the queue for each account and appends filenames
    """
    queue.clear()
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for account in dirs:
            queue_dir = base_dir + '/accounts/' + account + '/queue'
            if not os.path.isdir(queue_dir):
                continue
            for _, _, queuefiles in os.walk(queue_dir):
                for qfile in queuefiles:
                    queue.append(os.path.join(queue_dir, qfile))
                break
        break
    if len(queue) > 0:
        print('Restored ' + str(len(queue)) + ' inbox queue items')


def run_inbox_queue_watchdog(project_version: str, httpd) -> None:
    """This tries to keep the inbox thread running even if it dies
    """
    print('THREAD: Starting inbox queue watchdog ' + project_version)
    inbox_queue_original = httpd.thrInboxQueue.clone(run_inbox_queue)
    begin_thread(httpd.thrInboxQueue, 'run_inbox_queue_watchdog')
    while True:
        time.sleep(20)
        if not httpd.thrInboxQueue.is_alive() or httpd.restart_inbox_queue:
            httpd.restart_inbox_queue_in_progress = True
            httpd.thrInboxQueue.kill()
            print('THREAD: restarting inbox queue watchdog')
            httpd.thrInboxQueue = inbox_queue_original.clone(run_inbox_queue)
            httpd.inbox_queue.clear()
            begin_thread(httpd.thrInboxQueue, 'run_inbox_queue_watchdog 2')
            print('Restarting inbox queue...')
            httpd.restart_inbox_queue_in_progress = False
            httpd.restart_inbox_queue = False


def _inbox_quota_exceeded(queue: {}, queue_filename: str,
                          queue_json: {}, quotas_daily: {}, quotas_per_min: {},
                          domain_max_posts_per_day: int,
                          account_max_posts_per_day: int,
                          debug: bool) -> bool:
    """limit the number of posts which can arrive per domain per day
    """
    post_domain = queue_json['postDomain']
    if not post_domain:
        return False

    if domain_max_posts_per_day > 0:
        if quotas_daily['domains'].get(post_domain):
            if quotas_daily['domains'][post_domain] > \
               domain_max_posts_per_day:
                print('Queue: Quota per day - Maximum posts for ' +
                      post_domain + ' reached (' +
                      str(domain_max_posts_per_day) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queue_filename)
                    except OSError:
                        print('EX: _inbox_quota_exceeded unable to delete ' +
                              str(queue_filename))
                    queue.pop(0)
                return True
            quotas_daily['domains'][post_domain] += 1
        else:
            quotas_daily['domains'][post_domain] = 1

        if quotas_per_min['domains'].get(post_domain):
            domain_max_posts_per_min = \
                int(domain_max_posts_per_day / (24 * 60))
            if domain_max_posts_per_min < 5:
                domain_max_posts_per_min = 5
            if quotas_per_min['domains'][post_domain] > \
               domain_max_posts_per_min:
                print('Queue: Quota per min - Maximum posts for ' +
                      post_domain + ' reached (' +
                      str(domain_max_posts_per_min) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queue_filename)
                    except OSError:
                        print('EX: _inbox_quota_exceeded unable to delete ' +
                              str(queue_filename))
                    queue.pop(0)
                return True
            quotas_per_min['domains'][post_domain] += 1
        else:
            quotas_per_min['domains'][post_domain] = 1

    if account_max_posts_per_day > 0:
        post_handle = queue_json['postNickname'] + '@' + post_domain
        if quotas_daily['accounts'].get(post_handle):
            if quotas_daily['accounts'][post_handle] > \
               account_max_posts_per_day:
                print('Queue: Quota account posts per day -' +
                      ' Maximum posts for ' +
                      post_handle + ' reached (' +
                      str(account_max_posts_per_day) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queue_filename)
                    except OSError:
                        print('EX: _inbox_quota_exceeded unable to delete ' +
                              str(queue_filename))
                    queue.pop(0)
                return True
            quotas_daily['accounts'][post_handle] += 1
        else:
            quotas_daily['accounts'][post_handle] = 1

        if quotas_per_min['accounts'].get(post_handle):
            account_max_posts_per_min = \
                int(account_max_posts_per_day / (24 * 60))
            account_max_posts_per_min = max(account_max_posts_per_min, 5)
            if quotas_per_min['accounts'][post_handle] > \
               account_max_posts_per_min:
                print('Queue: Quota account posts per min -' +
                      ' Maximum posts for ' +
                      post_handle + ' reached (' +
                      str(account_max_posts_per_min) + ')')
                if len(queue) > 0:
                    try:
                        os.remove(queue_filename)
                    except OSError:
                        print('EX: _inbox_quota_exceeded unable to delete ' +
                              str(queue_filename))
                    queue.pop(0)
                return True
            quotas_per_min['accounts'][post_handle] += 1
        else:
            quotas_per_min['accounts'][post_handle] = 1

    if debug:
        if account_max_posts_per_day > 0 or domain_max_posts_per_day > 0:
            pprint(quotas_daily)
    return False


def _check_json_signature(base_dir: str, queue_json: {}) -> (bool, bool):
    """check if a json signature exists on this post
    """
    has_json_signature = False
    jwebsig_type = None
    original_json = queue_json['original']
    if not original_json.get('@context') or \
       not original_json.get('signature'):
        return has_json_signature, jwebsig_type
    if not isinstance(original_json['signature'], dict):
        return has_json_signature, jwebsig_type
    # see https://tools.ietf.org/html/rfc7515
    jwebsig = original_json['signature']
    # signature exists and is of the expected type
    if not jwebsig.get('type') or \
       not jwebsig.get('signatureValue'):
        return has_json_signature, jwebsig_type
    jwebsig_type = jwebsig['type']
    if jwebsig_type == 'RsaSignature2017':
        if has_valid_context(original_json):
            has_json_signature = True
        else:
            unknown_contexts_file = \
                base_dir + '/accounts/unknownContexts.txt'
            unknown_context = str(original_json['@context'])

            print('unrecognized @context: ' + unknown_context)

            already_unknown = False
            if os.path.isfile(unknown_contexts_file):
                if text_in_file(unknown_context, unknown_contexts_file):
                    already_unknown = True

            if not already_unknown:
                try:
                    with open(unknown_contexts_file, 'a+',
                              encoding='utf-8') as unknown_file:
                        unknown_file.write(unknown_context + '\n')
                except OSError:
                    print('EX: unable to append ' + unknown_contexts_file)
    else:
        print('Unrecognized jsonld signature type: ' + jwebsig_type)

        unknown_signatures_file = \
            base_dir + '/accounts/unknownJsonSignatures.txt'

        already_unknown = False
        if os.path.isfile(unknown_signatures_file):
            if text_in_file(jwebsig_type, unknown_signatures_file):
                already_unknown = True

        if not already_unknown:
            try:
                with open(unknown_signatures_file, 'a+',
                          encoding='utf-8') as unknown_file:
                    unknown_file.write(jwebsig_type + '\n')
            except OSError:
                print('EX: unable to append ' + unknown_signatures_file)
    return has_json_signature, jwebsig_type


def _receive_follow_request(session, session_onion, session_i2p,
                            base_dir: str, http_prefix: str,
                            port: int, send_threads: [], post_log: [],
                            cached_webfingers: {}, person_cache: {},
                            message_json: {}, federation_list: [],
                            debug: bool, project_version: str,
                            max_followers: int,
                            this_domain: str, onion_domain: str,
                            i2p_domain: str, signing_priv_key_pem: str,
                            unit_test: bool) -> bool:
    """Receives a follow request within the POST section of HTTPServer
    """
    if not message_json['type'].startswith('Follow'):
        if not message_json['type'].startswith('Join'):
            return False
    print('Receiving follow request')
    if not has_actor(message_json, debug):
        return False
    if not has_users_path(message_json['actor']):
        if debug:
            print('DEBUG: ' +
                  'users/profile/author/accounts/channel missing from actor')
        return False
    domain, temp_port = get_domain_from_actor(message_json['actor'])
    from_port = port
    domain_full = get_full_domain(domain, temp_port)
    if temp_port:
        from_port = temp_port
    if not domain_permitted(domain, federation_list):
        if debug:
            print('DEBUG: follower from domain not permitted - ' + domain)
        return False
    nickname = get_nickname_from_actor(message_json['actor'])
    if not nickname:
        # single user instance
        nickname = 'dev'
        if debug:
            print('DEBUG: follow request does not contain a ' +
                  'nickname. Assuming single user instance.')
    if not message_json.get('to'):
        message_json['to'] = message_json['object']
    if not has_users_path(message_json['object']):
        if debug:
            print('DEBUG: users/profile/author/channel/accounts ' +
                  'not found within object')
        return False
    domain_to_follow, temp_port = get_domain_from_actor(message_json['object'])
    # switch to the local domain rather than its onion or i2p version
    if onion_domain:
        if domain_to_follow.endswith(onion_domain):
            domain_to_follow = this_domain
    if i2p_domain:
        if domain_to_follow.endswith(i2p_domain):
            domain_to_follow = this_domain
    if not domain_permitted(domain_to_follow, federation_list):
        if debug:
            print('DEBUG: follow domain not permitted ' + domain_to_follow)
        return True
    domain_to_follow_full = get_full_domain(domain_to_follow, temp_port)
    nickname_to_follow = get_nickname_from_actor(message_json['object'])
    if not nickname_to_follow:
        if debug:
            print('DEBUG: follow request does not contain a ' +
                  'nickname for the account followed')
        return True
    if is_system_account(nickname_to_follow):
        if debug:
            print('DEBUG: Cannot follow system account - ' +
                  nickname_to_follow)
        return True
    if max_followers > 0:
        if get_no_of_followers(base_dir, nickname_to_follow,
                               domain_to_follow) > max_followers:
            print('WARN: ' + nickname_to_follow +
                  ' has reached their maximum number of followers')
            return True
    handle_to_follow = nickname_to_follow + '@' + domain_to_follow
    if domain_to_follow == domain:
        if not os.path.isdir(base_dir + '/accounts/' + handle_to_follow):
            if debug:
                print('DEBUG: followed account not found - ' +
                      base_dir + '/accounts/' + handle_to_follow)
            return True

    is_already_follower = False
    if is_follower_of_person(base_dir,
                             nickname_to_follow, domain_to_follow_full,
                             nickname, domain_full):
        if debug:
            print('DEBUG: ' + nickname + '@' + domain +
                  ' is already a follower of ' +
                  nickname_to_follow + '@' + domain_to_follow)
        is_already_follower = True

    approve_handle = nickname + '@' + domain_full

    curr_session = session
    curr_http_prefix = http_prefix
    curr_domain = domain
    curr_port = from_port
    if onion_domain and \
       not curr_domain.endswith('.onion') and \
       domain_to_follow.endswith('.onion'):
        curr_session = session_onion
        curr_http_prefix = 'http'
        curr_domain = onion_domain
        curr_port = 80
        port = 80
        if debug:
            print('Domain switched from ' + domain + ' to ' + curr_domain)
    elif (i2p_domain and
          not curr_domain.endswith('.i2p') and
          domain_to_follow.endswith('.i2p')):
        curr_session = session_i2p
        curr_http_prefix = 'http'
        curr_domain = i2p_domain
        curr_port = 80
        port = 80
        if debug:
            print('Domain switched from ' + domain + ' to ' + curr_domain)

    # is the actor sending the request valid?
    if not valid_sending_actor(curr_session, base_dir,
                               nickname_to_follow, domain_to_follow,
                               person_cache, message_json,
                               signing_priv_key_pem, debug, unit_test):
        print('REJECT spam follow request ' + approve_handle)
        return False

    # what is the followers policy?
    if not is_already_follower and \
       follow_approval_required(base_dir, nickname_to_follow,
                                domain_to_follow, debug, approve_handle):
        print('Follow approval is required')
        if domain.endswith('.onion'):
            if no_of_follow_requests(base_dir,
                                     nickname_to_follow, domain_to_follow,
                                     'onion') > 5:
                print('Too many follow requests from onion addresses')
                return False
        elif domain.endswith('.i2p'):
            if no_of_follow_requests(base_dir,
                                     nickname_to_follow, domain_to_follow,
                                     'i2p') > 5:
                print('Too many follow requests from i2p addresses')
                return False
        else:
            if no_of_follow_requests(base_dir,
                                     nickname_to_follow, domain_to_follow,
                                     '') > 10:
                print('Too many follow requests')
                return False

        # Get the actor for the follower and add it to the cache.
        # Getting their public key has the same result
        if debug:
            print('Obtaining the following actor: ' + message_json['actor'])
        if not get_person_pub_key(base_dir, curr_session,
                                  message_json['actor'],
                                  person_cache, debug, project_version,
                                  curr_http_prefix,
                                  this_domain, onion_domain,
                                  i2p_domain, signing_priv_key_pem):
            if debug:
                print('Unable to obtain following actor: ' +
                      message_json['actor'])

        group_account = \
            has_group_type(base_dir, message_json['actor'], person_cache)
        if group_account and is_group_account(base_dir, nickname, domain):
            print('Group cannot follow a group')
            return False

        print('Storing follow request for approval')
        return store_follow_request(base_dir,
                                    nickname_to_follow, domain_to_follow, port,
                                    nickname, domain, from_port,
                                    message_json, debug, message_json['actor'],
                                    group_account)
    else:
        if is_already_follower:
            print(approve_handle + ' is already a follower. ' +
                  'Re-sending Accept.')
        else:
            print('Follow request does not require approval ' +
                  approve_handle)
        # update the followers
        account_to_be_followed = \
            acct_dir(base_dir, nickname_to_follow, domain_to_follow)
        if os.path.isdir(account_to_be_followed):
            followers_filename = account_to_be_followed + '/followers.txt'

            # for actors which don't follow the mastodon
            # /users/ path convention store the full actor
            if '/users/' not in message_json['actor']:
                approve_handle = message_json['actor']

            # Get the actor for the follower and add it to the cache.
            # Getting their public key has the same result
            if debug:
                print('Obtaining the following actor: ' +
                      message_json['actor'])
            if not get_person_pub_key(base_dir, curr_session,
                                      message_json['actor'],
                                      person_cache, debug, project_version,
                                      curr_http_prefix, this_domain,
                                      onion_domain, i2p_domain,
                                      signing_priv_key_pem):
                if debug:
                    print('Unable to obtain following actor: ' +
                          message_json['actor'])

            print('Updating followers file: ' +
                  followers_filename + ' adding ' + approve_handle)
            if os.path.isfile(followers_filename):
                if not text_in_file(approve_handle, followers_filename):
                    group_account = \
                        has_group_type(base_dir,
                                       message_json['actor'], person_cache)
                    if debug:
                        print(approve_handle + ' / ' + message_json['actor'] +
                              ' is Group: ' + str(group_account))
                    if group_account and \
                       is_group_account(base_dir, nickname, domain):
                        print('Group cannot follow a group')
                        return False
                    try:
                        with open(followers_filename, 'r+',
                                  encoding='utf-8') as followers_file:
                            content = followers_file.read()
                            if approve_handle + '\n' not in content:
                                followers_file.seek(0, 0)
                                if not group_account:
                                    followers_file.write(approve_handle +
                                                         '\n' + content)
                                else:
                                    followers_file.write('!' + approve_handle +
                                                         '\n' + content)
                    except OSError as ex:
                        print('WARN: ' +
                              'Failed to write entry to followers file ' +
                              str(ex))
            else:
                try:
                    with open(followers_filename, 'w+',
                              encoding='utf-8') as followers_file:
                        followers_file.write(approve_handle + '\n')
                except OSError:
                    print('EX: unable to write ' + followers_filename)
        else:
            print('ACCEPT: Follow Accept account directory not found: ' +
                  account_to_be_followed)

    print('Beginning follow accept')
    return followed_account_accepts(curr_session, base_dir, curr_http_prefix,
                                    nickname_to_follow, domain_to_follow, port,
                                    nickname, curr_domain, curr_port,
                                    message_json['actor'], federation_list,
                                    message_json, send_threads, post_log,
                                    cached_webfingers, person_cache,
                                    debug, project_version, True,
                                    signing_priv_key_pem,
                                    this_domain, onion_domain, i2p_domain)


def run_inbox_queue(server,
                    recent_posts_cache: {}, max_recent_posts: int,
                    project_version: str,
                    base_dir: str, http_prefix: str,
                    send_threads: [], post_log: [],
                    cached_webfingers: {}, person_cache: {}, queue: [],
                    domain: str,
                    onion_domain: str, i2p_domain: str,
                    port: int, proxy_type: str,
                    federation_list: [], max_replies: int,
                    domain_max_posts_per_day: int,
                    account_max_posts_per_day: int,
                    allow_deletion: bool, debug: bool, max_mentions: int,
                    max_emoji: int, translate: {}, unit_test: bool,
                    yt_replace_domain: str,
                    twitter_replacement_domain: str,
                    show_published_date_only: bool,
                    max_followers: int,
                    allow_local_network_access: bool,
                    peertube_instances: [],
                    verify_all_signatures: bool,
                    theme_name: str, system_language: str,
                    max_like_count: int, signing_priv_key_pem: str,
                    default_reply_interval_hrs: int,
                    cw_lists: {}) -> None:
    """Processes received items and moves them to the appropriate
    directories
    """
    inbox_start_time = time.time()
    print('Starting new session when starting inbox queue')
    fitness_performance(inbox_start_time, server.fitness,
                        'INBOX', 'start', debug)
    inbox_start_time = time.time()

    curr_session_time = int(time.time())
    session_last_update = 0
    session = create_session(proxy_type)
    if session:
        session_last_update = curr_session_time

    # is this is a clearnet instance then optionally start sessions
    # for onion and i2p domains
    session_onion = None
    session_i2p = None
    session_last_update_onion = 0
    session_last_update_i2p = 0
    if proxy_type != 'tor' and onion_domain:
        print('Starting onion session when starting inbox queue')
        session_onion = create_session('tor')
        if session_onion:
            session_onion = curr_session_time
    if proxy_type != 'i2p' and i2p_domain:
        print('Starting i2p session when starting inbox queue')
        session_i2p = create_session('i2p')
        if session_i2p:
            session_i2p = curr_session_time

    inbox_handle = 'inbox@' + domain
    if debug:
        print('DEBUG: Inbox queue running')

    # if queue processing was interrupted (eg server crash)
    # then this loads any outstanding items back into the queue
    _restore_queue_items(base_dir, queue)
    fitness_performance(inbox_start_time, server.fitness,
                        'INBOX', '_restore_queue_items', debug)
    inbox_start_time = time.time()

    # keep track of numbers of incoming posts per day
    quotas_last_update_daily = int(time.time())
    quotas_daily = {
        'domains': {},
        'accounts': {}
    }
    quotas_last_update_per_min = int(time.time())
    quotas_per_min = {
        'domains': {},
        'accounts': {}
    }

    heart_beat_ctr = 0
    queue_restore_ctr = 0

    # time when the last DM bounce message was sent
    # This is in a list so that it can be changed by reference
    # within _bounce_dm
    last_bounce_message = [int(time.time())]

    # how long it takes for broch mode to lapse
    broch_lapse_days = random.randrange(7, 14)

    fitness_performance(inbox_start_time, server.fitness,
                        'INBOX', 'while_loop_start', debug)
    inbox_start_time = time.time()
    while True:
        time.sleep(1)
        inbox_start_time = time.time()
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'while_loop_itteration', debug)
        inbox_start_time = time.time()

        # heartbeat to monitor whether the inbox queue is running
        heart_beat_ctr += 1
        if heart_beat_ctr >= 10:
            # turn off broch mode after it has timed out
            if broch_modeLapses(base_dir, broch_lapse_days):
                broch_lapse_days = random.randrange(7, 14)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'broch_modeLapses', debug)
            inbox_start_time = time.time()
            print('>>> Heartbeat Q:' + str(len(queue)) + ' ' +
                  '{:%F %T}'.format(datetime.datetime.now()))
            heart_beat_ctr = 0

        if len(queue) == 0:
            # restore any remaining queue items
            queue_restore_ctr += 1
            if queue_restore_ctr >= 30:
                queue_restore_ctr = 0
                _restore_queue_items(base_dir, queue)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'restore_queue', debug)
            inbox_start_time = time.time()
            continue

        # oldest item first
        queue.sort()
        queue_filename = queue[0]
        if not os.path.isfile(queue_filename):
            print("Queue: queue item rejected because it has no file: " +
                  queue_filename)
            if len(queue) > 0:
                queue.pop(0)
            continue

        if debug:
            print('Loading queue item ' + queue_filename)

        # Load the queue json
        queue_json = load_json(queue_filename, 1)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'load_queue_json', debug)
        inbox_start_time = time.time()
        if not queue_json:
            print('Queue: run_inbox_queue failed to load inbox queue item ' +
                  queue_filename)
            # Assume that the file is probably corrupt/unreadable
            if len(queue) > 0:
                queue.pop(0)
            # delete the queue file
            if os.path.isfile(queue_filename):
                try:
                    os.remove(queue_filename)
                except OSError:
                    print('EX: run_inbox_queue 1 unable to delete ' +
                          str(queue_filename))
            continue

        curr_time = int(time.time())

        # clear the daily quotas for maximum numbers of received posts
        if curr_time - quotas_last_update_daily > 60 * 60 * 24:
            quotas_daily = {
                'domains': {},
                'accounts': {}
            }
            quotas_last_update_daily = curr_time

        if curr_time - quotas_last_update_per_min > 60:
            # clear the per minute quotas for maximum numbers of received posts
            quotas_per_min = {
                'domains': {},
                'accounts': {}
            }
            # also check if the json signature enforcement has changed
            verify_all_sigs = get_config_param(base_dir, "verifyAllSignatures")
            if verify_all_sigs is not None:
                verify_all_signatures = verify_all_sigs
            # change the last time that this was done
            quotas_last_update_per_min = curr_time

        if _inbox_quota_exceeded(queue, queue_filename,
                                 queue_json, quotas_daily, quotas_per_min,
                                 domain_max_posts_per_day,
                                 account_max_posts_per_day, debug):
            continue
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_inbox_quota_exceeded', debug)
        inbox_start_time = time.time()

        # recreate the session periodically
        if not session or curr_time - session_last_update > 21600:
            print('Regenerating inbox queue session at 6hr interval')
            session = create_session(proxy_type)
            if session:
                session_last_update = curr_time
            else:
                print('WARN: inbox session not created')
                continue
        if onion_domain:
            if not session_onion or \
               curr_time - session_last_update_onion > 21600:
                print('Regenerating inbox queue onion session at 6hr interval')
                session_onion = create_session('tor')
                if session_onion:
                    session_last_update_onion = curr_time
                else:
                    print('WARN: inbox onion session not created')
                    continue
        if i2p_domain:
            if not session_i2p or curr_time - session_last_update_i2p > 21600:
                print('Regenerating inbox queue i2p session at 6hr interval')
                session_i2p = create_session('i2p')
                if session_i2p:
                    session_last_update_i2p = curr_time
                else:
                    print('WARN: inbox i2p session not created')
                    continue
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'recreate_session', debug)
        inbox_start_time = time.time()

        curr_session = session
        if queue_json.get('actor'):
            if isinstance(queue_json['actor'], str):
                sender_domain, _ = get_domain_from_actor(queue_json['actor'])
                if sender_domain.endswith('.onion') and \
                   session_onion and proxy_type != 'tor':
                    curr_session = session_onion
                elif (sender_domain.endswith('.i2p') and
                      session_i2p and proxy_type != 'i2p'):
                    curr_session = session_i2p

        if debug and queue_json.get('actor'):
            print('Obtaining public key for actor ' + queue_json['actor'])

        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'start_get_pubkey', debug)
        inbox_start_time = time.time()
        # Try a few times to obtain the public key
        pub_key = None
        key_id = None
        for tries in range(8):
            key_id = None
            signature_params = \
                queue_json['httpHeaders']['signature'].split(',')
            for signature_item in signature_params:
                if signature_item.startswith('keyId='):
                    if '"' in signature_item:
                        key_id = signature_item.split('"')[1]
                        break
            if not key_id:
                print('Queue: No keyId in signature: ' +
                      queue_json['httpHeaders']['signature'])
                pub_key = None
                break

            pub_key = \
                get_person_pub_key(base_dir, curr_session, key_id,
                                   person_cache, debug,
                                   project_version, http_prefix,
                                   domain, onion_domain, i2p_domain,
                                   signing_priv_key_pem)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'get_person_pub_key', debug)
            inbox_start_time = time.time()
            if pub_key:
                if debug:
                    print('DEBUG: public key: ' + str(pub_key))
                break

            if debug:
                print('DEBUG: Retry ' + str(tries+1) +
                      ' obtaining public key for ' + key_id)
            time.sleep(1)

        if not pub_key:
            if debug:
                print('Queue: public key could not be obtained from ' + key_id)
            if os.path.isfile(queue_filename):
                try:
                    os.remove(queue_filename)
                except OSError:
                    print('EX: run_inbox_queue 2 unable to delete ' +
                          str(queue_filename))
            if len(queue) > 0:
                queue.pop(0)
            continue

        # check the http header signature
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'begin_check_signature', debug)
        inbox_start_time = time.time()
        if debug:
            print('DEBUG: checking http header signature')
            pprint(queue_json['httpHeaders'])
        post_str = json.dumps(queue_json['post'])
        http_signature_failed = False
        if not verify_post_headers(http_prefix, pub_key,
                                   queue_json['httpHeaders'],
                                   queue_json['path'], False,
                                   queue_json['digest'],
                                   post_str, debug):
            http_signature_failed = True
            print('Queue: Header signature check failed')
            pprint(queue_json['httpHeaders'])
        else:
            if debug:
                print('DEBUG: http header signature check success')
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'verify_post_headers', debug)
        inbox_start_time = time.time()

        # check if a json signature exists on this post
        has_json_signature, jwebsig_type = \
            _check_json_signature(base_dir, queue_json)
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_check_json_signature', debug)
        inbox_start_time = time.time()

        # strict enforcement of json signatures
        if not has_json_signature:
            if http_signature_failed:
                if jwebsig_type:
                    print('Queue: Header signature check failed and does ' +
                          'not have a recognised jsonld signature type ' +
                          jwebsig_type)
                else:
                    print('Queue: Header signature check failed and ' +
                          'does not have jsonld signature')
                if debug:
                    pprint(queue_json['httpHeaders'])

            if verify_all_signatures:
                original_json = queue_json['original']
                print('Queue: inbox post does not have a jsonld signature ' +
                      key_id + ' ' + str(original_json))

            if http_signature_failed or verify_all_signatures:
                if os.path.isfile(queue_filename):
                    try:
                        os.remove(queue_filename)
                    except OSError:
                        print('EX: run_inbox_queue 3 unable to delete ' +
                              str(queue_filename))
                if len(queue) > 0:
                    queue.pop(0)
                continue
        else:
            if http_signature_failed or verify_all_signatures:
                # use the original json message received, not one which
                # may have been modified along the way
                original_json = queue_json['original']
                if not verify_json_signature(original_json, pub_key):
                    if debug:
                        print('WARN: jsonld inbox signature check failed ' +
                              key_id + ' ' + pub_key + ' ' +
                              str(original_json))
                    else:
                        print('WARN: jsonld inbox signature check failed ' +
                              key_id)
                    if os.path.isfile(queue_filename):
                        try:
                            os.remove(queue_filename)
                        except OSError:
                            print('EX: run_inbox_queue 4 unable to delete ' +
                                  str(queue_filename))
                    if len(queue) > 0:
                        queue.pop(0)
                    fitness_performance(inbox_start_time, server.fitness,
                                        'INBOX', 'not_verify_signature',
                                        debug)
                    inbox_start_time = time.time()
                    continue

                if http_signature_failed:
                    print('jsonld inbox signature check success ' +
                          'via relay ' + key_id)
                else:
                    print('jsonld inbox signature check success ' + key_id)
                fitness_performance(inbox_start_time, server.fitness,
                                    'INBOX', 'verify_signature_success',
                                    debug)
                inbox_start_time = time.time()

        dogwhistles_filename = base_dir + '/accounts/dogwhistles.txt'
        if not os.path.isfile(dogwhistles_filename):
            dogwhistles_filename = base_dir + '/default_dogwhistles.txt'
        dogwhistles = load_dogwhistles(dogwhistles_filename)

        # set the id to the same as the post filename
        # This makes the filename and the id consistent
        # if queue_json['post'].get('id'):
        #     queue_json['post']['id'] = queue_json['id']

        if _receive_undo(base_dir, queue_json['post'],
                         debug, domain, onion_domain, i2p_domain):
            print('Queue: Undo accepted from ' + key_id)
            if os.path.isfile(queue_filename):
                try:
                    os.remove(queue_filename)
                except OSError:
                    print('EX: run_inbox_queue 5 unable to delete ' +
                          str(queue_filename))
            if len(queue) > 0:
                queue.pop(0)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', '_receive_undo',
                                debug)
            inbox_start_time = time.time()
            continue

        if debug:
            print('DEBUG: checking for follow requests')
        if _receive_follow_request(curr_session, session_onion, session_i2p,
                                   base_dir, http_prefix, port,
                                   send_threads, post_log,
                                   cached_webfingers,
                                   person_cache,
                                   queue_json['post'],
                                   federation_list,
                                   debug, project_version,
                                   max_followers, domain,
                                   onion_domain, i2p_domain,
                                   signing_priv_key_pem, unit_test):
            if os.path.isfile(queue_filename):
                try:
                    os.remove(queue_filename)
                except OSError:
                    print('EX: run_inbox_queue 6 unable to delete ' +
                          str(queue_filename))
            if len(queue) > 0:
                queue.pop(0)
            print('Queue: Follow activity for ' + key_id +
                  ' removed from queue')
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', '_receive_follow_request',
                                debug)
            inbox_start_time = time.time()
            continue

        if debug:
            print('DEBUG: No follow requests')

        if receive_accept_reject(base_dir, domain, queue_json['post'],
                                 federation_list, debug,
                                 domain, onion_domain, i2p_domain):
            print('Queue: Accept/Reject received from ' + key_id)
            if os.path.isfile(queue_filename):
                try:
                    os.remove(queue_filename)
                except OSError:
                    print('EX: run_inbox_queue 7 unable to delete ' +
                          str(queue_filename))
            if len(queue) > 0:
                queue.pop(0)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'receive_accept_reject',
                                debug)
            inbox_start_time = time.time()
            continue

        if _receive_update_activity(recent_posts_cache, curr_session,
                                    base_dir, http_prefix,
                                    domain, port,
                                    cached_webfingers,
                                    person_cache,
                                    queue_json['post'],
                                    queue_json['postNickname'],
                                    debug,
                                    max_mentions, max_emoji,
                                    allow_local_network_access,
                                    system_language,
                                    signing_priv_key_pem,
                                    max_recent_posts, translate,
                                    allow_deletion,
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    show_published_date_only,
                                    peertube_instances,
                                    theme_name, max_like_count,
                                    cw_lists, dogwhistles):
            if debug:
                print('Queue: Update accepted from ' + key_id)
            if os.path.isfile(queue_filename):
                try:
                    os.remove(queue_filename)
                except OSError:
                    print('EX: run_inbox_queue 8 unable to delete ' +
                          str(queue_filename))
            if len(queue) > 0:
                queue.pop(0)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', '_receive_update_activity',
                                debug)
            inbox_start_time = time.time()
            continue

        # get recipients list
        recipients_dict, recipients_dict_followers = \
            _inbox_post_recipients(base_dir, queue_json['post'],
                                   http_prefix, domain, port, debug,
                                   onion_domain, i2p_domain)
        if len(recipients_dict.items()) == 0 and \
           len(recipients_dict_followers.items()) == 0:
            if debug:
                print('Queue: no recipients were resolved ' +
                      'for post arriving in inbox')
            if os.path.isfile(queue_filename):
                try:
                    os.remove(queue_filename)
                except OSError:
                    print('EX: run_inbox_queue 9 unable to delete ' +
                          str(queue_filename))
            if len(queue) > 0:
                queue.pop(0)
            continue
        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', '_post_recipients',
                            debug)
        inbox_start_time = time.time()

        # if there are only a small number of followers then
        # process them as if they were specifically
        # addresses to particular accounts
        no_of_follow_items = len(recipients_dict_followers.items())
        if no_of_follow_items > 0:
            # always deliver to individual inboxes
            if no_of_follow_items < 999999:
                if debug:
                    print('DEBUG: moving ' + str(no_of_follow_items) +
                          ' inbox posts addressed to followers')
                for handle, post_item in recipients_dict_followers.items():
                    recipients_dict[handle] = post_item
                recipients_dict_followers = {}
#            recipients_list = [recipients_dict, recipients_dict_followers]

        if debug:
            print('*************************************')
            print('Resolved recipients list:')
            pprint(recipients_dict)
            print('Resolved followers list:')
            pprint(recipients_dict_followers)
            print('*************************************')

        # Copy any posts addressed to followers into the shared inbox
        # this avoid copying file multiple times to potentially many
        # individual inboxes
        if len(recipients_dict_followers) > 0:
            shared_inbox_post_filename = \
                queue_json['destination'].replace(inbox_handle, inbox_handle)
            if not os.path.isfile(shared_inbox_post_filename):
                save_json(queue_json['post'], shared_inbox_post_filename)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'shared_inbox_save',
                                debug)
            inbox_start_time = time.time()

        lists_enabled = get_config_param(base_dir, "listsEnabled")
        content_license_url = get_config_param(base_dir, "contentLicenseUrl")

        fitness_performance(inbox_start_time, server.fitness,
                            'INBOX', 'distribute_post',
                            debug)
        inbox_start_time = time.time()

        # for posts addressed to specific accounts
        for handle, _ in recipients_dict.items():
            destination = \
                queue_json['destination'].replace(inbox_handle, handle)
            languages_understood = []
            mitm = False
            if queue_json.get('mitm'):
                mitm = True
            bold_reading = False
            bold_reading_filename = \
                base_dir + '/accounts/' + handle + '/.boldReading'
            if os.path.isfile(bold_reading_filename):
                bold_reading = True
            _inbox_after_initial(server, inbox_start_time,
                                 recent_posts_cache,
                                 max_recent_posts,
                                 session, session_onion, session_i2p,
                                 key_id, handle,
                                 queue_json['post'],
                                 base_dir, http_prefix,
                                 send_threads, post_log,
                                 cached_webfingers,
                                 person_cache, domain,
                                 onion_domain, i2p_domain,
                                 port, federation_list,
                                 debug,
                                 queue_filename, destination,
                                 max_replies, allow_deletion,
                                 max_mentions, max_emoji,
                                 translate, unit_test,
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 show_published_date_only,
                                 allow_local_network_access,
                                 peertube_instances,
                                 last_bounce_message,
                                 theme_name, system_language,
                                 max_like_count,
                                 signing_priv_key_pem,
                                 default_reply_interval_hrs,
                                 cw_lists, lists_enabled,
                                 content_license_url,
                                 languages_understood, mitm,
                                 bold_reading, dogwhistles)
            fitness_performance(inbox_start_time, server.fitness,
                                'INBOX', 'handle_after_initial',
                                debug)
            inbox_start_time = time.time()
            if debug:
                pprint(queue_json['post'])
                print('Queue: Queue post accepted')
        if os.path.isfile(queue_filename):
            try:
                os.remove(queue_filename)
            except OSError:
                print('EX: run_inbox_queue 10 unable to delete ' +
                      str(queue_filename))
        if len(queue) > 0:
            queue.pop(0)
