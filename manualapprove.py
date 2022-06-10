__filename__ = "manualapprove.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from follow import followed_account_accepts
from follow import followed_account_rejects
from follow import remove_from_follow_requests
from utils import load_json
from utils import remove_domain_port
from utils import get_port_from_domain
from utils import get_user_paths
from utils import acct_dir
from utils import text_in_file
from threads import thread_with_trace
from session import create_session


def manual_deny_follow_request(session, session_onion, session_i2p,
                               onion_domain: str, i2p_domain: str,
                               base_dir: str, http_prefix: str,
                               nickname: str, domain: str, port: int,
                               deny_handle: str,
                               federation_list: [],
                               send_threads: [], post_log: [],
                               cached_webfingers: {}, person_cache: {},
                               debug: bool,
                               project_version: str,
                               signing_priv_key_pem: str) -> None:
    """Manually deny a follow request
    """
    accounts_dir = acct_dir(base_dir, nickname, domain)

    # has this handle already been rejected?
    rejected_follows_filename = accounts_dir + '/followrejects.txt'
    if os.path.isfile(rejected_follows_filename):
        if text_in_file(deny_handle, rejected_follows_filename):
            remove_from_follow_requests(base_dir, nickname, domain,
                                        deny_handle, debug)
            print(deny_handle +
                  ' has already been rejected as a follower of ' + nickname)
            return

    remove_from_follow_requests(base_dir, nickname, domain, deny_handle, debug)

    # Store rejected follows
    try:
        with open(rejected_follows_filename, 'a+',
                  encoding='utf-8') as rejects_file:
            rejects_file.write(deny_handle + '\n')
    except OSError:
        print('EX: unable to append ' + rejected_follows_filename)

    deny_nickname = deny_handle.split('@')[0]
    deny_domain = \
        deny_handle.split('@')[1].replace('\n', '').replace('\r', '')
    deny_port = port
    if ':' in deny_domain:
        deny_port = get_port_from_domain(deny_domain)
        deny_domain = remove_domain_port(deny_domain)
    followed_account_rejects(session, session_onion, session_i2p,
                             onion_domain, i2p_domain,
                             base_dir, http_prefix,
                             nickname, domain, port,
                             deny_nickname, deny_domain, deny_port,
                             federation_list,
                             send_threads, post_log,
                             cached_webfingers, person_cache,
                             debug, project_version,
                             signing_priv_key_pem)

    print('Follow request from ' + deny_handle + ' was denied.')


def manual_deny_follow_request_thread(session, session_onion, session_i2p,
                                      onion_domain: str, i2p_domain: str,
                                      base_dir: str, http_prefix: str,
                                      nickname: str, domain: str, port: int,
                                      deny_handle: str,
                                      federation_list: [],
                                      send_threads: [], post_log: [],
                                      cached_webfingers: {}, person_cache: {},
                                      debug: bool,
                                      project_version: str,
                                      signing_priv_key_pem: str) -> None:
    """Manually deny a follow request, within a thread so that the
    user interface doesn't lag
    """
    print('THREAD: manual_deny_follow_request')
    thr = \
        thread_with_trace(target=manual_deny_follow_request,
                          args=(session, session_onion, session_i2p,
                                onion_domain, i2p_domain,
                                base_dir, http_prefix,
                                nickname, domain, port,
                                deny_handle,
                                federation_list,
                                send_threads, post_log,
                                cached_webfingers, person_cache,
                                debug,
                                project_version,
                                signing_priv_key_pem), daemon=True)
    thr.start()
    send_threads.append(thr)


def _approve_follower_handle(account_dir: str, approve_handle: str) -> None:
    """ Record manually approved handles so that if they unfollow and then
     re-follow later then they don't need to be manually approved again
    """
    approved_filename = account_dir + '/approved.txt'
    if os.path.isfile(approved_filename):
        if not text_in_file(approve_handle, approved_filename):
            try:
                with open(approved_filename, 'a+',
                          encoding='utf-8') as approved_file:
                    approved_file.write(approve_handle + '\n')
            except OSError:
                print('EX: unable to append ' + approved_filename)
    else:
        try:
            with open(approved_filename, 'w+',
                      encoding='utf-8') as approved_file:
                approved_file.write(approve_handle + '\n')
        except OSError:
            print('EX: unable to write ' + approved_filename)


def manual_approve_follow_request(session, session_onion, session_i2p,
                                  onion_domain: str, i2p_domain: str,
                                  base_dir: str, http_prefix: str,
                                  nickname: str, domain: str, port: int,
                                  approve_handle: str,
                                  federation_list: [],
                                  send_threads: [], post_log: [],
                                  cached_webfingers: {}, person_cache: {},
                                  debug: bool,
                                  project_version: str,
                                  signing_priv_key_pem: str,
                                  proxy_type: str) -> None:
    """Manually approve a follow request
    """
    handle = nickname + '@' + domain
    print('Manual follow accept: ' + handle +
          ' approving follow request from ' + approve_handle)
    account_dir = base_dir + '/accounts/' + handle
    approve_follows_filename = account_dir + '/followrequests.txt'
    if not os.path.isfile(approve_follows_filename):
        print('Manual follow accept: follow requests file ' +
              approve_follows_filename + ' not found')
        return

    # is the handle in the requests file?
    approve_follows_str = ''
    with open(approve_follows_filename, 'r', encoding='utf-8') as fp_foll:
        approve_follows_str = fp_foll.read()
    exists = False
    approve_handle_full = approve_handle
    if approve_handle in approve_follows_str:
        exists = True
    elif '@' in approve_handle:
        group_account = False
        if approve_handle.startswith('!'):
            group_account = True
        req_nick = approve_handle.split('@')[0].replace('!', '')
        req_domain = approve_handle.split('@')[1].strip()
        req_prefix = http_prefix + '://' + req_domain
        paths = get_user_paths()
        for user_path in paths:
            if req_prefix + user_path + req_nick in approve_follows_str:
                exists = True
                approve_handle_full = req_prefix + user_path + req_nick
                if group_account:
                    approve_handle_full = '!' + approve_handle_full
                break
    if not exists:
        print('Manual follow accept: ' + approve_handle_full +
              ' not in requests file "' +
              approve_follows_str.replace('\n', ' ') +
              '" ' + approve_follows_filename)
        return

    with open(approve_follows_filename + '.new', 'w+',
              encoding='utf-8') as approvefilenew:
        update_approved_followers = False
        follow_activity_filename = None
        with open(approve_follows_filename, 'r',
                  encoding='utf-8') as approvefile:
            for handle_of_follow_requester in approvefile:
                # is this the approved follow?
                if handle_of_follow_requester.startswith(approve_handle_full):
                    handle_of_follow_requester = \
                        handle_of_follow_requester.replace('\n', '')
                    handle_of_follow_requester = \
                        handle_of_follow_requester.replace('\r', '')
                    port2 = port
                    if ':' in handle_of_follow_requester:
                        port2 = \
                            get_port_from_domain(handle_of_follow_requester)
                    requests_dir = account_dir + '/requests'
                    follow_activity_filename = \
                        requests_dir + '/' + \
                        handle_of_follow_requester + '.follow'
                    if os.path.isfile(follow_activity_filename):
                        follow_json = load_json(follow_activity_filename)
                        if follow_json:
                            approve_nickname = approve_handle.split('@')[0]
                            approve_domain = approve_handle.split('@')[1]
                            approve_domain = \
                                approve_domain.replace('\n', '')
                            approve_domain = \
                                approve_domain.replace('\r', '')
                            approve_port = port2
                            if ':' in approve_domain:
                                approve_port = \
                                    get_port_from_domain(approve_domain)
                                approve_domain = \
                                    remove_domain_port(approve_domain)

                            curr_domain = domain
                            curr_port = port
                            curr_session = session
                            curr_http_prefix = http_prefix
                            curr_proxy_type = proxy_type
                            if onion_domain and \
                               not curr_domain.endswith('.onion') and \
                               approve_domain.endswith('.onion'):
                                curr_domain = onion_domain
                                curr_port = 80
                                approve_port = 80
                                curr_session = session_onion
                                curr_http_prefix = 'http'
                                curr_proxy_type = 'tor'
                            elif (i2p_domain and
                                  not curr_domain.endswith('.i2p') and
                                  approve_domain.endswith('.i2p')):
                                curr_domain = i2p_domain
                                curr_port = 80
                                approve_port = 80
                                curr_session = session_i2p
                                curr_http_prefix = 'http'
                                curr_proxy_type = 'i2p'

                            if not curr_session:
                                curr_session = create_session(curr_proxy_type)

                            print('Manual follow accept: Sending Accept for ' +
                                  handle + ' follow request from ' +
                                  approve_nickname + '@' + approve_domain)
                            followed_account_accepts(curr_session, base_dir,
                                                     curr_http_prefix,
                                                     nickname,
                                                     curr_domain, curr_port,
                                                     approve_nickname,
                                                     approve_domain,
                                                     approve_port,
                                                     follow_json['actor'],
                                                     federation_list,
                                                     follow_json,
                                                     send_threads, post_log,
                                                     cached_webfingers,
                                                     person_cache,
                                                     debug,
                                                     project_version, False,
                                                     signing_priv_key_pem,
                                                     domain,
                                                     onion_domain,
                                                     i2p_domain)
                    update_approved_followers = True
                else:
                    # this isn't the approved follow so it will remain
                    # in the requests file
                    approvefilenew.write(handle_of_follow_requester)

    followers_filename = account_dir + '/followers.txt'
    if update_approved_followers:
        # update the followers
        print('Manual follow accept: updating ' + followers_filename)
        if os.path.isfile(followers_filename):
            if not text_in_file(approve_handle_full, followers_filename):
                try:
                    with open(followers_filename, 'r+',
                              encoding='utf-8') as followers_file:
                        content = followers_file.read()
                        if approve_handle_full + '\n' not in content:
                            followers_file.seek(0, 0)
                            followers_file.write(approve_handle_full + '\n' +
                                                 content)
                except Exception as ex:
                    print('WARN: Manual follow accept. ' +
                          'Failed to write entry to followers file ' + str(ex))
            else:
                print('WARN: Manual follow accept: ' + approve_handle_full +
                      ' already exists in ' + followers_filename)
        else:
            print('Manual follow accept: first follower accepted for ' +
                  handle + ' is ' + approve_handle_full)
            try:
                with open(followers_filename, 'w+',
                          encoding='utf-8') as followers_file:
                    followers_file.write(approve_handle_full + '\n')
            except OSError:
                print('EX: unable to write ' + followers_filename)

    # only update the follow requests file if the follow is confirmed to be
    # in followers.txt
    if text_in_file(approve_handle_full, followers_filename):
        # mark this handle as approved for following
        _approve_follower_handle(account_dir, approve_handle)
        # update the follow requests with the handles not yet approved
        os.rename(approve_follows_filename + '.new', approve_follows_filename)
        # remove the .follow file
        if follow_activity_filename:
            if os.path.isfile(follow_activity_filename):
                try:
                    os.remove(follow_activity_filename)
                except OSError:
                    print('EX: manual_approve_follow_request ' +
                          'unable to delete ' + follow_activity_filename)
    else:
        try:
            os.remove(approve_follows_filename + '.new')
        except OSError:
            print('EX: manual_approve_follow_request unable to delete ' +
                  approve_follows_filename + '.new')


def manual_approve_follow_request_thread(session, session_onion, session_i2p,
                                         onion_domain: str, i2p_domain: str,
                                         base_dir: str, http_prefix: str,
                                         nickname: str, domain: str, port: int,
                                         approve_handle: str,
                                         federation_list: [],
                                         send_threads: [], post_log: [],
                                         cached_webfingers: {},
                                         person_cache: {},
                                         debug: bool,
                                         project_version: str,
                                         signing_priv_key_pem: str,
                                         proxy_type: str) -> None:
    """Manually approve a follow request, in a thread so as not to cause
    the UI to lag
    """
    print('THREAD: manual_approve_follow_request')
    thr = \
        thread_with_trace(target=manual_approve_follow_request,
                          args=(session, session_onion, session_i2p,
                                onion_domain, i2p_domain,
                                base_dir, http_prefix,
                                nickname, domain, port,
                                approve_handle,
                                federation_list,
                                send_threads, post_log,
                                cached_webfingers, person_cache,
                                debug,
                                project_version,
                                signing_priv_key_pem,
                                proxy_type), daemon=True)
    thr.start()
    send_threads.append(thr)
