__filename__ = "sendC2S.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import json
from utils import replace_users_with_at
from utils import get_full_domain
from utils import local_actor_url
from webfinger import webfinger_handle
from posts import get_person_box
from posts import create_post_base
from auth import create_basic_auth_header
from session import post_image
from session import post_json_string
from session import post_json


def send_post_via_server(signing_priv_key_pem: str, project_version: str,
                         base_dir: str, session,
                         from_nickname: str, password: str,
                         from_domain: str, from_port: int,
                         to_nickname: str, to_domain: str, to_port: int,
                         cc_str: str,
                         http_prefix: str, content: str,
                         comments_enabled: bool,
                         attach_image_filename: str, media_type: str,
                         image_description: str, video_transcript: str,
                         city: str, cached_webfingers: {}, person_cache: {},
                         is_article: bool, system_language: str,
                         languages_understood: [],
                         low_bandwidth: bool,
                         content_license_url: str,
                         media_license_url: str, media_creator: str,
                         event_date: str, event_time: str, event_end_time: str,
                         event_category: str,
                         location: str, translate: {},
                         buy_url: str, chat_url: str, auto_cw_cache: {},
                         debug: bool, in_reply_to: str,
                         in_reply_to_atom_uri: str,
                         conversation_id: str, convthread_id: str,
                         subject: str, searchable_by: [],
                         mitm_servers: []) -> int:
    """Send a post via a proxy (c2s)
    """
    if not session:
        print('WARN: No session for send_post_via_server')
        return 6

    from_domain_full = get_full_domain(from_domain, from_port)

    handle = http_prefix + '://' + from_domain_full + '/@' + from_nickname

    # lookup the inbox for the To handle
    wf_request = \
        webfinger_handle(session, handle, http_prefix, cached_webfingers,
                         from_domain_full, project_version, debug, False,
                         signing_priv_key_pem, mitm_servers)
    if not wf_request:
        if debug:
            print('DEBUG: post webfinger failed for ' + handle)
        return 1
    if not isinstance(wf_request, dict):
        print('WARN: post webfinger for ' + handle +
              ' did not return a dict. ' + str(wf_request))
        return 1

    post_to_box = 'outbox'
    if is_article:
        post_to_box = 'tlblogs'

    # get the actor inbox for the To handle
    origin_domain = from_domain
    (inbox_url, _, _, from_person_id, _, _,
     _, _) = get_person_box(signing_priv_key_pem,
                            origin_domain,
                            base_dir, session, wf_request,
                            person_cache,
                            project_version, http_prefix,
                            from_nickname,
                            from_domain_full, post_to_box,
                            82796, system_language,
                            mitm_servers)
    if not inbox_url:
        if debug:
            print('DEBUG: post no ' + post_to_box +
                  ' was found for ' + handle)
        return 3
    if not from_person_id:
        if debug:
            print('DEBUG: post no actor was found for ' + handle)
        return 4

    # Get the json for the c2s post, not saving anything to file
    # Note that base_dir is set to None
    save_to_file = False
    client_to_server = True
    if to_domain.lower().endswith('public'):
        to_person_id = 'https://www.w3.org/ns/activitystreams#Public'
        cc_str = \
            local_actor_url(http_prefix, from_nickname, from_domain_full) + \
            '/followers'
        automatic_quote_approval = \
            "https://www.w3.org/ns/activitystreams#Public"
    else:
        if to_domain.lower().endswith('followers') or \
           to_domain.lower().endswith('followersonly'):
            from_local_actor = \
                local_actor_url(http_prefix, from_nickname, from_domain_full)
            to_person_id = from_local_actor + '/followers'
            automatic_quote_approval = from_local_actor + '/following'
        else:
            to_domain_full = get_full_domain(to_domain, to_port)
            to_person_id = \
                local_actor_url(http_prefix, to_nickname, to_domain_full)
            automatic_quote_approval = \
                local_actor_url(http_prefix,
                                from_nickname, from_domain_full)

    is_moderation_report = False
    schedule_post = False
    event_uuid = category = join_mode = None
    maximum_attendee_capacity = None
    replies_moderation_option = None
    anonymous_participation_enabled = None
    event_status = ticket_url = None
    post_json_object = \
        create_post_base(base_dir,
                         from_nickname, from_domain, from_port,
                         to_person_id, cc_str, http_prefix, content,
                         save_to_file, client_to_server,
                         comments_enabled,
                         attach_image_filename, media_type,
                         image_description, video_transcript, city,
                         is_moderation_report, is_article, in_reply_to,
                         in_reply_to_atom_uri, subject, schedule_post,
                         event_date, event_time, location,
                         event_uuid, category, join_mode,
                         event_date, event_end_time,
                         event_category,
                         maximum_attendee_capacity,
                         replies_moderation_option,
                         anonymous_participation_enabled,
                         event_status, ticket_url, system_language,
                         conversation_id, convthread_id, low_bandwidth,
                         content_license_url,
                         media_license_url, media_creator,
                         languages_understood,
                         translate, buy_url, chat_url, auto_cw_cache,
                         searchable_by, session,
                         automatic_quote_approval)

    auth_header = create_basic_auth_header(from_nickname, password)

    if attach_image_filename:
        headers = {
            'host': from_domain_full,
            'Authorization': auth_header
        }
        post_result = \
            post_image(session, attach_image_filename, [],
                       inbox_url, headers, http_prefix, from_domain_full)
        if not post_result:
            if debug:
                print('DEBUG: post failed to upload image')
#            return 9

    headers = {
        'host': from_domain_full,
        'Content-type': 'application/json',
        'Authorization': auth_header
    }
    post_dumps = json.dumps(post_json_object)
    post_result, unauthorized, return_code = \
        post_json_string(session, post_dumps, [],
                         inbox_url, headers, debug,
                         http_prefix, from_domain_full,
                         5, True)
    if not post_result:
        if debug:
            if unauthorized:
                print('DEBUG: POST failed for c2s to ' +
                      inbox_url + ' unathorized')
            else:
                print('DEBUG: POST failed for c2s to ' +
                      inbox_url + ' return code ' + str(return_code))
        return 5

    if debug:
        print('DEBUG: c2s POST success')
    return 0


def send_block_via_server(base_dir: str, session,
                          from_nickname: str, password: str,
                          from_domain: str, from_port: int,
                          http_prefix: str, blocked_url: str,
                          cached_webfingers: {}, person_cache: {},
                          debug: bool, project_version: str,
                          signing_priv_key_pem: str,
                          system_language: str,
                          mitm_servers: []) -> {}:
    """Creates a block via c2s
    """
    if not session:
        print('WARN: No session for send_block_via_server')
        return 6

    from_domain_full = get_full_domain(from_domain, from_port)

    block_actor = local_actor_url(http_prefix, from_nickname, from_domain_full)
    to_url = 'https://www.w3.org/ns/activitystreams#Public'
    cc_url = block_actor + '/followers'

    new_block_json = {
        "@context": [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1'
        ],
        'type': 'Block',
        'actor': block_actor,
        'object': blocked_url,
        'to': [to_url],
        'cc': [cc_url]
    }

    handle = http_prefix + '://' + from_domain_full + '/@' + from_nickname

    # lookup the inbox for the To handle
    wf_request = webfinger_handle(session, handle, http_prefix,
                                  cached_webfingers,
                                  from_domain, project_version, debug, False,
                                  signing_priv_key_pem, mitm_servers)
    if not wf_request:
        if debug:
            print('DEBUG: block webfinger failed for ' + handle)
        return 1
    if not isinstance(wf_request, dict):
        print('WARN: block Webfinger for ' + handle +
              ' did not return a dict. ' + str(wf_request))
        return 1

    post_to_box = 'outbox'

    # get the actor inbox for the To handle
    origin_domain = from_domain
    (inbox_url, _, _, from_person_id, _, _,
     _, _) = get_person_box(signing_priv_key_pem,
                            origin_domain,
                            base_dir, session, wf_request,
                            person_cache,
                            project_version, http_prefix,
                            from_nickname,
                            from_domain, post_to_box, 72652,
                            system_language, mitm_servers)

    if not inbox_url:
        if debug:
            print('DEBUG: block no ' + post_to_box +
                  ' was found for ' + handle)
        return 3
    if not from_person_id:
        if debug:
            print('DEBUG: block no actor was found for ' + handle)
        return 4

    auth_header = create_basic_auth_header(from_nickname, password)

    headers = {
        'host': from_domain,
        'Content-type': 'application/json',
        'Authorization': auth_header
    }
    post_result = post_json(http_prefix, from_domain_full,
                            session, new_block_json, [], inbox_url,
                            headers, 30, True)
    if not post_result:
        print('WARN: block unable to post')

    if debug:
        print('DEBUG: c2s POST block success')

    return new_block_json


def send_mute_via_server(base_dir: str, session,
                         from_nickname: str, password: str,
                         from_domain: str, from_port: int,
                         http_prefix: str, muted_url: str,
                         cached_webfingers: {}, person_cache: {},
                         debug: bool, project_version: str,
                         signing_priv_key_pem: str,
                         system_language: str,
                         mitm_servers: []) -> {}:
    """Creates a mute via c2s
    """
    if not session:
        print('WARN: No session for send_mute_via_server')
        return 6

    from_domain_full = get_full_domain(from_domain, from_port)

    actor = local_actor_url(http_prefix, from_nickname, from_domain_full)
    handle = replace_users_with_at(actor)

    new_mute_json = {
        "@context": [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1'
        ],
        'type': 'Ignore',
        'actor': actor,
        'to': [actor],
        'object': muted_url
    }

    # lookup the inbox for the To handle
    wf_request = webfinger_handle(session, handle, http_prefix,
                                  cached_webfingers,
                                  from_domain, project_version, debug, False,
                                  signing_priv_key_pem, mitm_servers)
    if not wf_request:
        if debug:
            print('DEBUG: mute webfinger failed for ' + handle)
        return 1
    if not isinstance(wf_request, dict):
        print('WARN: mute Webfinger for ' + handle +
              ' did not return a dict. ' + str(wf_request))
        return 1

    post_to_box = 'outbox'

    # get the actor inbox for the To handle
    origin_domain = from_domain
    (inbox_url, _, _, from_person_id, _, _,
     _, _) = get_person_box(signing_priv_key_pem,
                            origin_domain,
                            base_dir, session, wf_request,
                            person_cache,
                            project_version, http_prefix,
                            from_nickname,
                            from_domain, post_to_box, 72652,
                            system_language, mitm_servers)

    if not inbox_url:
        if debug:
            print('DEBUG: mute no ' + post_to_box + ' was found for ' + handle)
        return 3
    if not from_person_id:
        if debug:
            print('DEBUG: mute no actor was found for ' + handle)
        return 4

    auth_header = create_basic_auth_header(from_nickname, password)

    headers = {
        'host': from_domain,
        'Content-type': 'application/json',
        'Authorization': auth_header
    }
    post_result = post_json(http_prefix, from_domain_full,
                            session, new_mute_json, [], inbox_url,
                            headers, 3, True)
    if post_result is None:
        print('WARN: mute unable to post')

    if debug:
        print('DEBUG: c2s POST mute success')

    return new_mute_json


def send_undo_mute_via_server(base_dir: str, session,
                              from_nickname: str, password: str,
                              from_domain: str, from_port: int,
                              http_prefix: str, muted_url: str,
                              cached_webfingers: {}, person_cache: {},
                              debug: bool, project_version: str,
                              signing_priv_key_pem: str,
                              system_language: str,
                              mitm_servers: []) -> {}:
    """Undoes a mute via c2s
    """
    if not session:
        print('WARN: No session for send_undo_mute_via_server')
        return 6

    from_domain_full = get_full_domain(from_domain, from_port)

    actor = local_actor_url(http_prefix, from_nickname, from_domain_full)
    handle = replace_users_with_at(actor)

    undo_mute_json = {
        "@context": [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1'
        ],
        'type': 'Undo',
        'actor': actor,
        'to': [actor],
        'object': {
            'type': 'Ignore',
            'actor': actor,
            'to': [actor],
            'object': muted_url
        }
    }

    # lookup the inbox for the To handle
    wf_request = webfinger_handle(session, handle, http_prefix,
                                  cached_webfingers,
                                  from_domain, project_version, debug, False,
                                  signing_priv_key_pem, mitm_servers)
    if not wf_request:
        if debug:
            print('DEBUG: undo mute webfinger failed for ' + handle)
        return 1
    if not isinstance(wf_request, dict):
        print('WARN: undo mute Webfinger for ' + handle +
              ' did not return a dict. ' + str(wf_request))
        return 1

    post_to_box = 'outbox'

    # get the actor inbox for the To handle
    origin_domain = from_domain
    (inbox_url, _, _, from_person_id, _, _,
     _, _) = get_person_box(signing_priv_key_pem,
                            origin_domain,
                            base_dir, session, wf_request,
                            person_cache,
                            project_version, http_prefix,
                            from_nickname,
                            from_domain, post_to_box, 72652,
                            system_language, mitm_servers)

    if not inbox_url:
        if debug:
            print('DEBUG: undo mute no ' + post_to_box +
                  ' was found for ' + handle)
        return 3
    if not from_person_id:
        if debug:
            print('DEBUG: undo mute no actor was found for ' + handle)
        return 4

    auth_header = create_basic_auth_header(from_nickname, password)

    headers = {
        'host': from_domain,
        'Content-type': 'application/json',
        'Authorization': auth_header
    }
    post_result = post_json(http_prefix, from_domain_full,
                            session, undo_mute_json, [], inbox_url,
                            headers, 3, True)
    if post_result is None:
        print('WARN: undo mute unable to post')

    if debug:
        print('DEBUG: c2s POST undo mute success')

    return undo_mute_json


def send_undo_block_via_server(base_dir: str, session,
                               from_nickname: str, password: str,
                               from_domain: str, from_port: int,
                               http_prefix: str, blocked_url: str,
                               cached_webfingers: {}, person_cache: {},
                               debug: bool, project_version: str,
                               signing_priv_key_pem: str,
                               system_language: str,
                               mitm_servers: []) -> {}:
    """Creates a block via c2s
    """
    if not session:
        print('WARN: No session for send_block_via_server')
        return 6

    from_domain_full = get_full_domain(from_domain, from_port)

    block_actor = local_actor_url(http_prefix, from_nickname, from_domain_full)
    to_url = 'https://www.w3.org/ns/activitystreams#Public'
    cc_url = block_actor + '/followers'

    new_block_json = {
        "@context": [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1'
        ],
        'type': 'Undo',
        'actor': block_actor,
        'object': {
            'type': 'Block',
            'actor': block_actor,
            'object': blocked_url,
            'to': [to_url],
            'cc': [cc_url]
        }
    }

    handle = http_prefix + '://' + from_domain_full + '/@' + from_nickname

    # lookup the inbox for the To handle
    wf_request = webfinger_handle(session, handle, http_prefix,
                                  cached_webfingers,
                                  from_domain, project_version, debug, False,
                                  signing_priv_key_pem, mitm_servers)
    if not wf_request:
        if debug:
            print('DEBUG: unblock webfinger failed for ' + handle)
        return 1
    if not isinstance(wf_request, dict):
        print('WARN: unblock webfinger for ' + handle +
              ' did not return a dict. ' + str(wf_request))
        return 1

    post_to_box = 'outbox'

    # get the actor inbox for the To handle
    origin_domain = from_domain
    (inbox_url, _, _, from_person_id, _, _,
     _, _) = get_person_box(signing_priv_key_pem,
                            origin_domain,
                            base_dir, session, wf_request,
                            person_cache,
                            project_version, http_prefix,
                            from_nickname,
                            from_domain, post_to_box, 53892,
                            system_language, mitm_servers)

    if not inbox_url:
        if debug:
            print('DEBUG: unblock no ' + post_to_box +
                  ' was found for ' + handle)
        return 3
    if not from_person_id:
        if debug:
            print('DEBUG: unblock no actor was found for ' + handle)
        return 4

    auth_header = create_basic_auth_header(from_nickname, password)

    headers = {
        'host': from_domain,
        'Content-type': 'application/json',
        'Authorization': auth_header
    }
    post_result = post_json(http_prefix, from_domain_full,
                            session, new_block_json, [], inbox_url,
                            headers, 30, True)
    if not post_result:
        print('WARN: unblock unable to post')

    if debug:
        print('DEBUG: c2s POST unblock success')

    return new_block_json
