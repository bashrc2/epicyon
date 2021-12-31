__filename__ = "schedule.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Calendar"

import os
import time
import datetime
from utils import has_object_dict
from utils import get_status_number
from utils import load_json
from utils import is_account_dir
from utils import acct_dir
from outbox import post_message_to_outbox


def _update_post_schedule(base_dir: str, handle: str, httpd,
                          max_scheduled_posts: int) -> None:
    """Checks if posts are due to be delivered and if so moves them to the outbox
    """
    schedule_index_filename = \
        base_dir + '/accounts/' + handle + '/schedule.index'
    if not os.path.isfile(schedule_index_filename):
        return

    # get the current time as an int
    curr_time = datetime.datetime.utcnow()
    days_since_epoch = (curr_time - datetime.datetime(1970, 1, 1)).days

    schedule_dir = base_dir + '/accounts/' + handle + '/scheduled/'
    index_lines = []
    delete_schedule_post = False
    nickname = handle.split('@')[0]
    with open(schedule_index_filename, 'r') as sched_file:
        for line in sched_file:
            if ' ' not in line:
                continue
            date_str = line.split(' ')[0]
            if 'T' not in date_str:
                continue
            post_id = line.split(' ', 1)[1].replace('\n', '').replace('\r', '')
            post_filename = schedule_dir + post_id + '.json'
            if delete_schedule_post:
                # delete extraneous scheduled posts
                if os.path.isfile(post_filename):
                    try:
                        os.remove(post_filename)
                    except OSError:
                        print('EX: _update_post_schedule unable to delete ' +
                              str(post_filename))
                continue
            # create the new index file
            index_lines.append(line)
            # convert string date to int
            post_time = \
                datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
            post_time = post_time.replace(tzinfo=None)
            post_days_since_epoch = \
                (post_time - datetime.datetime(1970, 1, 1)).days
            if days_since_epoch < post_days_since_epoch:
                continue
            if days_since_epoch == post_days_since_epoch:
                if curr_time.time().hour < post_time.time().hour:
                    continue
                if curr_time.time().minute < post_time.time().minute:
                    continue
            if not os.path.isfile(post_filename):
                print('WARN: schedule missing post_filename=' + post_filename)
                index_lines.remove(line)
                continue
            # load post
            post_json_object = load_json(post_filename)
            if not post_json_object:
                print('WARN: schedule json not loaded')
                index_lines.remove(line)
                continue

            # set the published time
            # If this is not recent then http checks on the receiving side
            # will reject it
            _, published = get_status_number()
            if post_json_object.get('published'):
                post_json_object['published'] = published
            if has_object_dict(post_json_object):
                if post_json_object['object'].get('published'):
                    post_json_object['published'] = published

            print('Sending scheduled post ' + post_id)

            if nickname:
                httpd.postToNickname = nickname
            if not post_message_to_outbox(httpd.session,
                                          httpd.translate,
                                          post_json_object, nickname,
                                          httpd, base_dir,
                                          httpd.http_prefix,
                                          httpd.domain,
                                          httpd.domain_full,
                                          httpd.onion_domain,
                                          httpd.i2p_domain,
                                          httpd.port,
                                          httpd.recent_posts_cache,
                                          httpd.followers_threads,
                                          httpd.federation_list,
                                          httpd.send_threads,
                                          httpd.postLog,
                                          httpd.cached_webfingers,
                                          httpd.person_cache,
                                          httpd.allow_deletion,
                                          httpd.proxy_type,
                                          httpd.project_version,
                                          httpd.debug,
                                          httpd.yt_replace_domain,
                                          httpd.twitter_replacement_domain,
                                          httpd.show_published_date_only,
                                          httpd.allow_local_network_access,
                                          httpd.city, httpd.system_language,
                                          httpd.shared_items_federated_domains,
                                          httpd.sharedItemFederationTokens,
                                          httpd.low_bandwidth,
                                          httpd.signing_priv_key_pem,
                                          httpd.peertube_instances,
                                          httpd.theme_name,
                                          httpd.max_like_count,
                                          httpd.max_recent_posts,
                                          httpd.cw_lists,
                                          httpd.lists_enabled,
                                          httpd.content_license_url):
                index_lines.remove(line)
                try:
                    os.remove(post_filename)
                except OSError:
                    print('EX: _update_post_schedule unable to delete ' +
                          str(post_filename))
                continue

            # move to the outbox
            outbox_post_filename = \
                post_filename.replace('/scheduled/', '/outbox/')
            os.rename(post_filename, outbox_post_filename)

            print('Scheduled post sent ' + post_id)

            index_lines.remove(line)
            if len(index_lines) > max_scheduled_posts:
                delete_schedule_post = True

    # write the new schedule index file
    schedule_index_file = \
        base_dir + '/accounts/' + handle + '/schedule.index'
    with open(schedule_index_file, 'w+') as schedule_file:
        for line in index_lines:
            schedule_file.write(line)


def run_post_schedule(base_dir: str, httpd, max_scheduled_posts: int):
    """Dispatches scheduled posts
    """
    while True:
        time.sleep(60)
        # for each account
        for _, dirs, _ in os.walk(base_dir + '/accounts'):
            for account in dirs:
                if '@' not in account:
                    continue
                if not is_account_dir(account):
                    continue
                # scheduled posts index for this account
                schedule_index_filename = \
                    base_dir + '/accounts/' + account + '/schedule.index'
                if not os.path.isfile(schedule_index_filename):
                    continue
                _update_post_schedule(base_dir, account,
                                      httpd, max_scheduled_posts)
            break


def run_post_schedule_watchdog(project_version: str, httpd) -> None:
    """This tries to keep the scheduled post thread running even if it dies
    """
    print('Starting scheduled post watchdog')
    post_schedule_original = \
        httpd.thrPostSchedule.clone(run_post_schedule)
    httpd.thrPostSchedule.start()
    while True:
        time.sleep(20)
        if httpd.thrPostSchedule.is_alive():
            continue
        httpd.thrPostSchedule.kill()
        httpd.thrPostSchedule = \
            post_schedule_original.clone(run_post_schedule)
        httpd.thrPostSchedule.start()
        print('Restarting scheduled posts...')


def remove_scheduled_posts(base_dir: str, nickname: str, domain: str) -> None:
    """Removes any scheduled posts
    """
    # remove the index
    schedule_index_filename = \
        acct_dir(base_dir, nickname, domain) + '/schedule.index'
    if os.path.isfile(schedule_index_filename):
        try:
            os.remove(schedule_index_filename)
        except OSError:
            print('EX: remove_scheduled_posts unable to delete ' +
                  schedule_index_filename)
    # remove the scheduled posts
    scheduled_dir = acct_dir(base_dir, nickname, domain) + '/scheduled'
    if not os.path.isdir(scheduled_dir):
        return
    for scheduled_post_filename in os.listdir(scheduled_dir):
        file_path = os.path.join(scheduled_dir, scheduled_post_filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                print('EX: remove_scheduled_posts unable to delete ' +
                      file_path)
