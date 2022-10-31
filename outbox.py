__filename__ = "outbox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from shutil import copyfile
from auth import create_password
from posts import is_image_media
from posts import outbox_message_create_wrap
from posts import save_post_to_box
from posts import send_to_followers_thread
from posts import send_to_named_addresses_thread
from utils import get_attachment_property_value
from utils import get_account_timezone
from utils import has_object_string_type
from utils import get_base_content_from_post
from utils import has_object_dict
from utils import get_local_network_addresses
from utils import get_full_domain
from utils import remove_id_ending
from utils import get_domain_from_actor
from utils import dangerous_markup
from utils import is_featured_writer
from utils import load_json
from utils import save_json
from utils import acct_dir
from utils import local_actor_url
from utils import has_actor
from blocking import is_blocked_domain
from blocking import outbox_block
from blocking import outbox_undo_block
from blocking import outbox_mute
from blocking import outbox_undo_mute
from media import replace_you_tube
from media import replace_twitter
from media import get_media_path
from media import create_media_dirs
from inbox import store_hash_tags
from inbox import inbox_update_index
from announce import outbox_announce
from announce import outbox_undo_announce
from follow import outbox_undo_follow
from follow import follower_approval_active
from skills import outbox_skills
from availability import outbox_availability
from like import outbox_like
from like import outbox_undo_like
from reaction import outbox_reaction
from reaction import outbox_undo_reaction
from bookmarks import outbox_bookmark
from bookmarks import outbox_undo_bookmark
from delete import outbox_delete
from shares import outbox_share_upload
from shares import outbox_undo_share_upload
from webapp_post import individual_post_as_html
from speaker import update_speaker


def _person_receive_update_outbox(base_dir: str, http_prefix: str,
                                  nickname: str, domain: str, port: int,
                                  message_json: {}, debug: bool) -> None:
    """ Receive an actor update from c2s
    For example, setting the PGP key from the desktop client
    """
    # these attachments are updatable via c2s
    updatable_attachments = ('PGP', 'OpenPGP', 'Email')

    if not message_json.get('type'):
        return
    if not isinstance(message_json['type'], str):
        if debug:
            print('DEBUG: c2s actor update type is not a string')
        return
    if message_json['type'] != 'Update':
        return
    if not has_object_string_type(message_json, debug):
        return
    if not isinstance(message_json['object']['type'], str):
        if debug:
            print('DEBUG: c2s actor update object type is not a string')
        return
    if message_json['object']['type'] != 'Person':
        if debug:
            print('DEBUG: not a c2s actor update')
        return
    if not message_json.get('to'):
        if debug:
            print('DEBUG: c2s actor update has no "to" field')
        return
    if not has_actor(message_json, debug):
        return
    if not message_json.get('id'):
        if debug:
            print('DEBUG: c2s actor update has no id field')
        return
    if not isinstance(message_json['id'], str):
        if debug:
            print('DEBUG: c2s actor update id is not a string')
        return
    domain_full = get_full_domain(domain, port)
    actor = local_actor_url(http_prefix, nickname, domain_full)
    if len(message_json['to']) != 1:
        if debug:
            print('DEBUG: c2s actor update - to does not contain one actor ' +
                  str(message_json['to']))
        return
    if message_json['to'][0] != actor:
        if debug:
            print('DEBUG: c2s actor update - to does not contain actor ' +
                  str(message_json['to']) + ' ' + actor)
        return
    if not message_json['id'].startswith(actor + '#updates/'):
        if debug:
            print('DEBUG: c2s actor update - unexpected id ' +
                  message_json['id'])
        return
    updated_actor_json = message_json['object']
    # load actor from file
    actor_filename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actor_filename):
        print('actor_filename not found: ' + actor_filename)
        return
    actor_json = load_json(actor_filename)
    if not actor_json:
        return
    actor_changed = False
    # update fields within actor
    if 'attachment' in updated_actor_json:
        for new_property_value in updated_actor_json['attachment']:
            name_value = None
            if new_property_value.get('name'):
                name_value = new_property_value['name']
            elif new_property_value.get('schema:name'):
                name_value = new_property_value['schema:name']
            if not name_value:
                continue
            if name_value not in updatable_attachments:
                continue
            if not new_property_value.get('type'):
                continue
            prop_value_name, _ = \
                get_attachment_property_value(new_property_value)
            if not prop_value_name:
                continue
            if not new_property_value['type'].endswith('PropertyValue'):
                continue
            if 'attachment' not in actor_json:
                continue
            found = False
            for attach_idx, _ in enumerate(actor_json['attachment']):
                attach_type = actor_json['attachment'][attach_idx]['type']
                if not attach_type.endswith('PropertyValue'):
                    continue
                attach_name = ''
                if actor_json['attachment'][attach_idx].get('name'):
                    attach_name = \
                        actor_json['attachment'][attach_idx]['name']
                elif actor_json['attachment'][attach_idx].get('schema:name'):
                    attach_name = \
                        actor_json['attachment'][attach_idx]['schema:name']
                if attach_name != name_value:
                    continue
                if actor_json['attachment'][attach_idx][prop_value_name] != \
                   new_property_value[prop_value_name]:
                    actor_json['attachment'][attach_idx][prop_value_name] = \
                        new_property_value[prop_value_name]
                    actor_changed = True
                found = True
                break
            if not found:
                actor_json['attachment'].append({
                    "name": name_value,
                    "type": "PropertyValue",
                    "value": new_property_value[prop_value_name]
                })
                actor_changed = True
    # save actor to file
    if actor_changed:
        save_json(actor_json, actor_filename)
        if debug:
            print('actor saved: ' + actor_filename)
    if debug:
        print('New attachment: ' + str(actor_json['attachment']))
    message_json['object'] = actor_json
    if debug:
        print('DEBUG: actor update via c2s - ' + nickname + '@' + domain)


def _capitalize_hashtag(content: str, message_json: {},
                        system_language: str, translate: {},
                        original_tag: str,
                        capitalized_tag: str) -> None:
    """If a nowplaying hashtag exists then ensure it is capitalized
    """
    if translate.get(original_tag) and \
       translate.get(capitalized_tag):
        original_tag = translate[original_tag].replace(' ', '_')
        capitalized_tag = translate[capitalized_tag].replace(' ', '_')

    if '#' + original_tag not in content:
        return
    content = content.replace('#' + original_tag, '#' + capitalized_tag)
    if message_json['object'].get('contentMap'):
        if message_json['object']['contentMap'].get(system_language):
            message_json['object']['contentMap'][system_language] = content
    message_json['object']['contentMap'][system_language] = content


def post_message_to_outbox(session, translate: {},
                           message_json: {}, post_to_nickname: str,
                           server, base_dir: str, http_prefix: str,
                           domain: str, domain_full: str,
                           onion_domain: str, i2p_domain: str, port: int,
                           recent_posts_cache: {}, followers_threads: [],
                           federation_list: [], send_threads: [],
                           post_log: [], cached_webfingers: {},
                           person_cache: {}, allow_deletion: bool,
                           proxy_type: str, version: str, debug: bool,
                           yt_replace_domain: str,
                           twitter_replacement_domain: str,
                           show_published_date_only: bool,
                           allow_local_network_access: bool,
                           city: str, system_language: str,
                           shared_items_federated_domains: [],
                           shared_item_federation_tokens: {},
                           low_bandwidth: bool,
                           signing_priv_key_pem: str,
                           peertube_instances: str, theme: str,
                           max_like_count: int,
                           max_recent_posts: int, cw_lists: {},
                           lists_enabled: str,
                           content_license_url: str,
                           dogwhistles: {}) -> bool:
    """post is received by the outbox
    Client to server message post
    https://www.w3.org/TR/activitypub/#client-to-server-outbox-delivery
    """
    if not message_json.get('type'):
        if debug:
            print('DEBUG: POST to outbox has no "type" parameter')
        return False
    if not message_json.get('object') and message_json.get('content'):
        if message_json['type'] != 'Create':
            # https://www.w3.org/TR/activitypub/#object-without-create
            if debug:
                print('DEBUG: POST to outbox - adding Create wrapper')
            message_json = \
                outbox_message_create_wrap(http_prefix,
                                           post_to_nickname,
                                           domain, port,
                                           message_json)

    bold_reading = False
    if server.bold_reading.get(post_to_nickname):
        bold_reading = True

    # check that the outgoing post doesn't contain any markup
    # which can be used to implement exploits
    if has_object_dict(message_json):
        content_str = get_base_content_from_post(message_json, system_language)
        if content_str:
            _capitalize_hashtag(content_str, message_json,
                                system_language, translate,
                                'nowplaying', 'NowPlaying')

            if dangerous_markup(content_str, allow_local_network_access):
                print('POST to outbox contains dangerous markup: ' +
                      str(message_json))
                return False

    if message_json['type'] == 'Create':
        if not (message_json.get('id') and
                message_json.get('type') and
                message_json.get('actor') and
                message_json.get('object') and
                message_json.get('to')):
            if not message_json.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the id parameter ' +
                          str(message_json))
            elif not message_json.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the type parameter ' +
                          str(message_json))
            elif not message_json.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the actor parameter ' +
                          str(message_json))
            elif not message_json.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the object parameter ' +
                          str(message_json))
            else:
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the "to" parameter ' +
                          str(message_json))
            return False

        # actor should be a string
        if not isinstance(message_json['actor'], str):
            return False

        # actor should look like a url
        if '://' not in message_json['actor'] or \
           '.' not in message_json['actor']:
            return False

        # sent by an actor on a local network address?
        if not allow_local_network_access:
            local_network_pattern_list = get_local_network_addresses()
            for local_network_pattern in local_network_pattern_list:
                if local_network_pattern in message_json['actor']:
                    return False

        test_domain, test_port = get_domain_from_actor(message_json['actor'])
        test_domain = get_full_domain(test_domain, test_port)
        if is_blocked_domain(base_dir, test_domain):
            if debug:
                print('DEBUG: domain is blocked: ' + message_json['actor'])
            return False
        # replace youtube, so that google gets less tracking data
        replace_you_tube(message_json, yt_replace_domain, system_language)
        # replace twitter, so that twitter posts can be shown without
        # having a twitter account
        replace_twitter(message_json, twitter_replacement_domain,
                        system_language)
        # https://www.w3.org/TR/activitypub/#create-activity-outbox
        message_json['object']['attributedTo'] = message_json['actor']
        if message_json['object'].get('attachment'):
            attachment_index = 0
            attach = message_json['object']['attachment'][attachment_index]
            if attach.get('mediaType'):
                file_extension = 'png'
                media_type_str = \
                    attach['mediaType']

                extensions = {
                    "jpeg": "jpg",
                    "jxl": "jxl",
                    "gif": "gif",
                    "svg": "svg",
                    "webp": "webp",
                    "avif": "avif",
                    "heic": "heic",
                    "audio/mpeg": "mp3",
                    "ogg": "ogg",
                    "audio/wav": "wav",
                    "audio/x-wav": "wav",
                    "audio/x-pn-wave": "wav",
                    "audio/vnd.wave": "wav",
                    "flac": "flac",
                    "opus": "opus",
                    "audio/speex": "spx",
                    "audio/x-speex": "spx",
                    "mp4": "mp4",
                    "webm": "webm",
                    "ogv": "ogv"
                }
                for match_ext, ext in extensions.items():
                    if media_type_str.endswith(match_ext):
                        file_extension = ext
                        break

                media_dir = \
                    base_dir + '/accounts/' + \
                    post_to_nickname + '@' + domain
                upload_media_filename = media_dir + '/upload.' + file_extension
                if not os.path.isfile(upload_media_filename):
                    del message_json['object']['attachment']
                else:
                    # generate a path for the uploaded image
                    mpath = get_media_path()
                    media_path = mpath + '/' + \
                        create_password(16).lower() + '.' + file_extension
                    create_media_dirs(base_dir, mpath)
                    media_filename = base_dir + '/' + media_path
                    # move the uploaded image to its new path
                    os.rename(upload_media_filename, media_filename)
                    # change the url of the attachment
                    attach['url'] = \
                        http_prefix + '://' + domain_full + '/' + media_path
                    attach['url'] = \
                        attach['url'].replace('/media/',
                                              '/system/' +
                                              'media_attachments/files/')

    permitted_outbox_types = (
        'Create', 'Announce', 'Like', 'EmojiReact', 'Follow', 'Undo',
        'Update', 'Add', 'Remove', 'Block', 'Delete', 'Skill', 'Ignore'
    )
    if message_json['type'] not in permitted_outbox_types:
        if debug:
            print('DEBUG: POST to outbox - ' + message_json['type'] +
                  ' is not a permitted activity type')
        return False
    if message_json.get('id'):
        post_id = remove_id_ending(message_json['id'])
        if debug:
            print('DEBUG: id attribute exists within POST to outbox')
    else:
        if debug:
            print('DEBUG: No id attribute within POST to outbox')
        post_id = None
    if debug:
        print('DEBUG: save_post_to_box')
    if message_json['type'] != 'Upgrade':
        outbox_name = 'outbox'

        store_hash_tags(base_dir, post_to_nickname, domain,
                        http_prefix, domain_full,
                        message_json, translate)

        # if this is a blog post or an event then save to its own box
        if message_json['type'] == 'Create':
            if has_object_dict(message_json):
                if message_json['object'].get('type'):
                    if message_json['object']['type'] == 'Article':
                        outbox_name = 'tlblogs'

        saved_filename = \
            save_post_to_box(base_dir,
                             http_prefix,
                             post_id,
                             post_to_nickname, domain_full,
                             message_json, outbox_name)
        if not saved_filename:
            print('WARN: post not saved to outbox ' + outbox_name)
            return False

        update_speaker(base_dir, http_prefix,
                       post_to_nickname, domain, domain_full,
                       message_json, person_cache,
                       translate, message_json['actor'],
                       theme, system_language,
                       outbox_name)

        # save all instance blogs to the news actor
        if post_to_nickname != 'news' and outbox_name == 'tlblogs':
            if '/' in saved_filename:
                if is_featured_writer(base_dir, post_to_nickname, domain):
                    saved_post_id = saved_filename.split('/')[-1]
                    blogs_dir = \
                        base_dir + '/accounts/news@' + domain + '/tlblogs'
                    if not os.path.isdir(blogs_dir):
                        os.mkdir(blogs_dir)
                    copyfile(saved_filename, blogs_dir + '/' + saved_post_id)
                    inbox_update_index('tlblogs', base_dir,
                                       'news@' + domain,
                                       saved_filename, debug)

                # clear the citations file if it exists
                citations_filename = \
                    base_dir + '/accounts/' + \
                    post_to_nickname + '@' + domain + '/.citations.txt'
                if os.path.isfile(citations_filename):
                    try:
                        os.remove(citations_filename)
                    except OSError:
                        print('EX: post_message_to_outbox unable to delete ' +
                              citations_filename)

        # The following activity types get added to the index files
        indexed_activities = (
            'Create', 'Question', 'Note', 'EncryptedMessage', 'Article',
            'Patch', 'Announce', 'ChatMessage'
        )
        if message_json['type'] in indexed_activities:
            indexes = [outbox_name, "inbox"]
            self_actor = \
                local_actor_url(http_prefix, post_to_nickname, domain_full)
            for box_name_index in indexes:
                if not box_name_index:
                    continue

                # should this also go to the media timeline?
                if box_name_index == 'inbox':
                    if is_image_media(session, base_dir, http_prefix,
                                      post_to_nickname, domain,
                                      message_json,
                                      yt_replace_domain,
                                      twitter_replacement_domain,
                                      allow_local_network_access,
                                      recent_posts_cache, debug,
                                      system_language,
                                      domain_full, person_cache,
                                      signing_priv_key_pem,
                                      bold_reading):
                        inbox_update_index('tlmedia', base_dir,
                                           post_to_nickname + '@' + domain,
                                           saved_filename, debug)

                if box_name_index == 'inbox' and outbox_name == 'tlblogs':
                    continue

                # avoid duplicates of the message if already going
                # back to the inbox of the same account
                if self_actor not in message_json['to']:
                    # show sent post within the inbox,
                    # as is the typical convention
                    inbox_update_index(box_name_index, base_dir,
                                       post_to_nickname + '@' + domain,
                                       saved_filename, debug)

                    # regenerate the html
                    use_cache_only = False
                    page_number = 1
                    show_individual_post_icons = True
                    manually_approve_followers = \
                        follower_approval_active(base_dir,
                                                 post_to_nickname, domain)
                    timezone = \
                        get_account_timezone(base_dir,
                                             post_to_nickname, domain)
                    mitm = False
                    if os.path.isfile(saved_filename.replace('.json', '') +
                                      '.mitm'):
                        mitm = True
                    individual_post_as_html(signing_priv_key_pem,
                                            False, recent_posts_cache,
                                            max_recent_posts,
                                            translate, page_number,
                                            base_dir, session,
                                            cached_webfingers,
                                            person_cache,
                                            post_to_nickname, domain, port,
                                            message_json, None, True,
                                            allow_deletion,
                                            http_prefix, __version__,
                                            box_name_index,
                                            yt_replace_domain,
                                            twitter_replacement_domain,
                                            show_published_date_only,
                                            peertube_instances,
                                            allow_local_network_access,
                                            theme, system_language,
                                            max_like_count,
                                            box_name_index != 'dm',
                                            show_individual_post_icons,
                                            manually_approve_followers,
                                            False, True, use_cache_only,
                                            cw_lists, lists_enabled,
                                            timezone, mitm,
                                            bold_reading, dogwhistles)

    if outbox_announce(recent_posts_cache,
                       base_dir, message_json, debug):
        if debug:
            print('DEBUG: Updated announcements (shares) collection ' +
                  'for the post associated with the Announce activity')
    if debug:
        print('DEBUG: sending c2s post to followers')
    # remove inactive threads
    inactive_follower_threads = []
    for thr in followers_threads:
        if not thr.is_alive():
            inactive_follower_threads.append(thr)
    for thr in inactive_follower_threads:
        followers_threads.remove(thr)
    if debug:
        print('DEBUG: ' + str(len(followers_threads)) +
              ' followers threads active')
    # retain up to 200 threads
    if len(followers_threads) > 200:
        # kill the thread if it is still alive
        if followers_threads[0].is_alive():
            followers_threads[0].kill()
        # remove it from the list
        followers_threads.pop(0)
    # create a thread to send the post to followers
    followers_thread = \
        send_to_followers_thread(server, server.session,
                                 server.session_onion,
                                 server.session_i2p,
                                 base_dir,
                                 post_to_nickname,
                                 domain, onion_domain, i2p_domain,
                                 port, http_prefix,
                                 federation_list,
                                 send_threads,
                                 post_log,
                                 cached_webfingers,
                                 person_cache,
                                 message_json, debug,
                                 version,
                                 shared_items_federated_domains,
                                 shared_item_federation_tokens,
                                 signing_priv_key_pem)
    followers_threads.append(followers_thread)

    if debug:
        print('DEBUG: handle any unfollow requests')
    outbox_undo_follow(base_dir, message_json, debug)

    if debug:
        print('DEBUG: handle skills changes requests')
    outbox_skills(base_dir, post_to_nickname, message_json, debug)

    if debug:
        print('DEBUG: handle availability changes requests')
    outbox_availability(base_dir, post_to_nickname, message_json, debug)

    if debug:
        print('DEBUG: handle any like requests')
    outbox_like(recent_posts_cache,
                base_dir, post_to_nickname, domain,
                message_json, debug)
    if debug:
        print('DEBUG: handle any undo like requests')
    outbox_undo_like(recent_posts_cache,
                     base_dir, post_to_nickname, domain,
                     message_json, debug)

    if debug:
        print('DEBUG: handle any emoji reaction requests')
    outbox_reaction(recent_posts_cache,
                    base_dir, post_to_nickname, domain,
                    message_json, debug)
    if debug:
        print('DEBUG: handle any undo emoji reaction requests')
    outbox_undo_reaction(recent_posts_cache,
                         base_dir, post_to_nickname, domain,
                         message_json, debug)

    if debug:
        print('DEBUG: handle any undo announce requests')
    outbox_undo_announce(recent_posts_cache,
                         base_dir, post_to_nickname, domain,
                         message_json, debug)

    if debug:
        print('DEBUG: handle any bookmark requests')
    outbox_bookmark(recent_posts_cache,
                    base_dir, http_prefix,
                    post_to_nickname, domain, port,
                    message_json, debug)
    if debug:
        print('DEBUG: handle any undo bookmark requests')
    outbox_undo_bookmark(recent_posts_cache,
                         base_dir, http_prefix,
                         post_to_nickname, domain, port,
                         message_json, debug)

    if debug:
        print('DEBUG: handle delete requests')
    outbox_delete(base_dir, http_prefix,
                  post_to_nickname, domain,
                  message_json, debug,
                  allow_deletion,
                  recent_posts_cache)

    if debug:
        print('DEBUG: handle block requests')
    outbox_block(base_dir, post_to_nickname, domain,
                 message_json, debug)

    if debug:
        print('DEBUG: handle undo block requests')
    outbox_undo_block(base_dir, post_to_nickname, domain, message_json, debug)

    if debug:
        print('DEBUG: handle mute requests')
    outbox_mute(base_dir, http_prefix,
                post_to_nickname, domain,
                port,
                message_json, debug,
                recent_posts_cache)

    if debug:
        print('DEBUG: handle undo mute requests')
    outbox_undo_mute(base_dir, http_prefix,
                     post_to_nickname, domain,
                     port,
                     message_json, debug,
                     recent_posts_cache)

    if debug:
        print('DEBUG: handle share uploads')
    outbox_share_upload(base_dir, http_prefix, post_to_nickname, domain,
                        port, message_json, debug, city,
                        system_language, translate, low_bandwidth,
                        content_license_url)

    if debug:
        print('DEBUG: handle undo share uploads')
    outbox_undo_share_upload(base_dir, post_to_nickname, domain,
                             message_json, debug)

    if debug:
        print('DEBUG: handle actor updates from c2s')
    _person_receive_update_outbox(base_dir, http_prefix,
                                  post_to_nickname, domain, port,
                                  message_json, debug)

    if debug:
        print('DEBUG: sending c2s post to named addresses')
        if message_json.get('to'):
            print('c2s sender: ' +
                  post_to_nickname + '@' + domain + ':' + str(port) +
                  ' recipient: ' + str(message_json['to']))
        else:
            print('c2s sender: ' +
                  post_to_nickname + '@' + domain + ':' + str(port))
    named_addresses_thread = \
        send_to_named_addresses_thread(server, server.session,
                                       server.session_onion,
                                       server.session_i2p,
                                       base_dir, post_to_nickname,
                                       domain, onion_domain, i2p_domain, port,
                                       http_prefix,
                                       federation_list,
                                       send_threads,
                                       post_log,
                                       cached_webfingers,
                                       person_cache,
                                       message_json, debug,
                                       version,
                                       shared_items_federated_domains,
                                       shared_item_federation_tokens,
                                       signing_priv_key_pem,
                                       proxy_type)
    followers_threads.append(named_addresses_thread)
    return True
