__filename__ = "content_labels.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Daemon POST"

import os
from datetime import datetime, timezone
from src.utils import string_contains
from src.utils import data_dir
from src.utils import local_actor_url
from src.utils import file_last_modified
from src.utils import acct_dir
from src.utils import valid_content_label
from src.utils import remove_id_ending
from src.utils import remove_html
from src.utils import resembles_url
from src.utils import has_object_dict
from src.data import load_line
from src.data import load_string
from src.data import is_a_dir
from src.data import makedir
from src.data import is_a_file
from src.data import save_string
from src.maps import get_map_links_from_post_content
from src.maps import get_location_from_post
from src.maps import geocoords_from_map_link
from src.maps import add_label_map_links
from src.timeFunctions import date_utcnow
from src.timeFunctions import date_epoch
from src.timeFunctions import date_from_string_format
# from src.delete import remove_old_labels

MAX_CONTENT_LABELS = 10


def get_labels_from_json(json_object: {}) -> []:
    """Returns labels attached to an actor or post
    """
    tags_list: list[dict] = []
    obj: dict = json_object
    if has_object_dict(json_object):
        obj = json_object['object']
    if 'tag' in obj:
        if isinstance(obj['tag'], list):
            tags_list = obj['tag']
    if 'attachment' in json_object:
        if isinstance(json_object['attachment'], list):
            tags_list = json_object['attachment']
    if not tags_list:
        return []
    labels: list[str] = []
    for tag_dict in tags_list:
        if not isinstance(tag_dict, dict):
            continue
        if 'type' not in tag_dict or 'name' not in tag_dict:
            continue
        if 'value' not in tag_dict and 'href' not in tag_dict:
            continue
        if not isinstance(tag_dict['type'], str):
            continue
        if not isinstance(tag_dict['name'], str):
            continue
        if tag_dict['type'] == 'PropertyValue' and \
           'value' in tag_dict:
            if not isinstance(tag_dict['value'], str):
                continue
            if tag_dict['name'] == 'Labels':
                if ',' in tag_dict['value']:
                    labels_list = tag_dict['value'].split(',')
                else:
                    labels_list = tag_dict['value'].split('/')
                for label_str in labels_list:
                    if not valid_content_label(label_str):
                        break
                    label_str = label_str.strip()
                    label_str = remove_html(label_str)
                    if label_str:
                        if len(labels) >= MAX_CONTENT_LABELS:
                            break
                        if label_str not in labels:
                            labels.append(label_str)
                # limit the number of labels
                if len(labels) >= MAX_CONTENT_LABELS:
                    break
            elif tag_dict['name'] == 'Label':
                label_str = tag_dict['value'].strip()
                label_str = remove_html(label_str)
                if label_str:
                    if not valid_content_label(label_str):
                        break
                    if 'href' in tag_dict:
                        if isinstance(tag_dict['href'], str):
                            if resembles_url(tag_dict['href']):
                                label_str += '###' + tag_dict['href']
                    if label_str not in labels:
                        labels.append(label_str)
                # limit the number of labels
                if len(labels) >= MAX_CONTENT_LABELS:
                    break
        elif tag_dict['type'] == 'Label':
            label_str = remove_html(tag_dict['name'])
            if label_str:
                if not valid_content_label(label_str):
                    break
                if 'href' in tag_dict:
                    if isinstance(tag_dict['href'], str):
                        if resembles_url(tag_dict['href']):
                            label_str += '###' + tag_dict['href']
                if label_str not in labels:
                    labels.append(label_str)
            # limit the number of labels
            if len(labels) >= MAX_CONTENT_LABELS:
                break
    return labels


def labels_list_html(labels_list: []) -> str:
    """Returns html for a list of labels for an actor or post
    """
    labels_str = ''
    for label in labels_list:
        if not valid_content_label(label):
            continue
        label_url = ''
        if '###' in label:
            label_url = label.split('###')[1]
            label = label.split('###')[0]
        if labels_str:
            labels_str += ' '
        if not label_url:
            label_in_path = label.replace(' ', '_')
            labels_str += '<mark><a href="/labels/' + label_in_path + \
                '" target="_blank" rel="nofollow noopener noreferrer">' + \
                label + '</a></mark>'
        else:
            labels_str += '<mark><a href="' + label_url + \
                '" target="_blank" rel="nofollow noopener noreferrer">' + \
                label + '</a></mark>'
    if labels_str:
        labels_str = '<p>' + labels_str + '</p>\n'
    return labels_str


def get_actor_content_labels(actor_json: {}) -> str:
    """Returns a string containing comma separated content labels
    from the given account actor
    """
    labels_list: list[str] = get_labels_from_json(actor_json)
    labels_str = ''
    for lbl in labels_list:
        if '###' in lbl:
            lbl = lbl.split('###')[0]
        if labels_str:
            labels_str += ', '
        labels_str += lbl
    return labels_str


def set_actor_content_labels(actor_json: {}, labels: str) -> None:
    """Sets a string containing comma separated content labels
    within the given account actor
    """
    labels = remove_html(labels)

    if 'attachment' not in actor_json:
        actor_json['attachment'] = []

    for tag_dict in actor_json['attachment']:
        if 'name' not in tag_dict:
            continue
        if not isinstance(tag_dict['name'], str):
            continue
        if tag_dict['name'] == 'Labels':
            tag_dict['value'] = labels
            return

    labels_dict = {
        'type': 'PropertyValue',
        'name': 'Labels',
        'value': labels
    }
    actor_json['attachment'].append(labels_dict)


def set_post_content_labels(post_json_object: {}, labels: str) -> None:
    """Sets a string containing comma separated content labels
    within the given post
    """
    if not labels:
        return

    labels = remove_html(labels)

    obj = post_json_object
    if has_object_dict(post_json_object):
        obj = post_json_object['object']

    if 'tag' not in obj:
        obj['tag'] = []

    for tag_dict in obj['tag']:
        if 'name' not in tag_dict:
            continue
        if not isinstance(tag_dict['name'], str):
            continue
        if tag_dict['name'] == 'Labels':
            tag_dict['value'] = labels
            return

    labels_dict = {
        'type': 'PropertyValue',
        'name': 'Labels',
        'value': labels
    }
    obj['tag'].append(labels_dict)


def _store_content_label(nickname: str,
                         label: str, labels_dir: str, post_url: str,
                         map_links: [], published: str,
                         labels_maps_dir: str) -> bool:
    """stores an individual content_label
    """
    if not valid_content_label(label):
        return False
    labels_filename = labels_dir + '/' + label + '.txt'
    days_diff = date_utcnow() - date_epoch()
    days_since_epoch = days_diff.days
    label_line = \
        str(days_since_epoch) + '  ' + nickname + '  ' + post_url + '\n'
    if map_links and published:
        add_label_map_links(labels_maps_dir, label, map_links,
                            published, post_url)
    label_added: bool = False
    if not is_a_file(labels_filename):
        if save_string(label_line, labels_filename,
                       'EX: _store_content_label unable to write ' +
                       labels_filename):
            label_added = True
    else:
        content = load_string(labels_filename,
                              'EX: _store_content_label failed to read ' +
                              labels_filename)
        if content is None:
            content: str = ''
        if post_url not in content:
            content = label_line + content
            if save_string(content, labels_filename,
                           'EX: Failed to write entry to labels file ' +
                           labels_filename + ' [ex]'):
                label_added = True

    if not label_added:
        return False

    return True


def _html_labels_swarm(base_dir: str, actor: str) -> str:
    """Returns a labels swarm of today's labels
    """
    max_label_length = 42
    curr_time = date_utcnow()
    prev_time_epoch = date_epoch()
    days_since_epoch = (curr_time - prev_time_epoch).days
    days_since_epoch_str = str(days_since_epoch) + ' '
    days_since_epoch_str2 = str(days_since_epoch - 1) + ' '
    recently = days_since_epoch - 1
    labels_swarm: list[str] = []
    domain_histogram = {}

    # Load the blocked labels into memory.
    # This avoids needing to repeatedly load the blocked file for each label
    blocked_str: str = ''
    global_blocking_filename = data_dir(base_dir) + '/blocking.txt'
    if is_a_file(global_blocking_filename):
        blocked_str = \
            load_string(global_blocking_filename,
                        'EX: _html_labels_swarm unable to read ' +
                        global_blocking_filename)
        if blocked_str is None:
            blocked_str: str = ''

    for _, _, files in os.walk(base_dir + '/labels'):
        for fname in files:
            if not fname.endswith('.txt'):
                continue
            labels_filename = os.path.join(base_dir + '/labels', fname)
            if not is_a_file(labels_filename):
                continue

            # get last modified datetime
            mod_time_since_epoc = os.path.getmtime(labels_filename)
            last_modified_date = \
                datetime.fromtimestamp(mod_time_since_epoc,
                                       timezone.utc)
            file_days_since_epoch = \
                (last_modified_date - prev_time_epoch).days

            # check if the file was last modified within the previous
            # two days
            if file_days_since_epoch < recently:
                continue

            label = fname.replace('.txt', '')
            if len(label) > max_label_length:
                continue
            if string_contains(label, ['#', '&', '"', "'"]):
                continue
            if label + '\n' in blocked_str:
                continue

            last_label = \
                load_line(labels_filename,
                          'EX: _html_labels_swarm unable to read 2 ' +
                          labels_filename)
            if last_label is None:
                continue
            if not last_label.startswith(days_since_epoch_str):
                if not last_label.startswith(days_since_epoch_str2):
                    continue

            try:
                with open(labels_filename, 'r', encoding='utf-8') as fp_labels:
                    while True:
                        line = fp_labels.readline()
                        if not line:
                            break
                        if '  ' not in line:
                            break
                        sections: list[str] = line.split('  ')
                        if len(sections) != 3:
                            break
                        post_days_since_epoch_str = sections[0]
                        if not post_days_since_epoch_str.isdigit():
                            break
                        post_days_since_epoch = int(post_days_since_epoch_str)
                        if post_days_since_epoch < recently:
                            break
                        post_url = sections[2]
                        if '##' not in post_url:
                            break
                        post_domain = post_url.split('##')[1]
                        if '#' in post_domain:
                            post_domain = post_domain.split('#')[0]

                        if domain_histogram.get(post_domain):
                            domain_histogram[post_domain] = \
                                domain_histogram[post_domain] + 1
                        else:
                            domain_histogram[post_domain] = 1
                        labels_swarm.append(label)
                        break
            except OSError as exc:
                print('EX: _html_labels_swarm unable to read ' +
                      labels_filename + ' ' + str(exc))
        break

    if not labels_swarm:
        return ''
    labels_swarm.sort()

    # swarm of labels
    labels_swarm_str: str = ''
    for label in labels_swarm:
        label_display_name = label
        labels_map_filename = \
            os.path.join(base_dir + '/labelsmaps', label + '.txt')
        if is_a_file(labels_map_filename):
            label_display_name = '📌' + label
        label_in_path = label.replace(' ', '_')
        labels_swarm_str += \
            '<a href="' + actor + '/labels/' + label_in_path + \
            '" class="hashtagswarm">' + label_display_name + '</a>\n'

    labels_swarm_html = labels_swarm_str.strip() + '\n'
    return labels_swarm_html


def _update_cached_labels_swarm(base_dir: str, nickname: str, domain: str,
                                http_prefix: str, domain_full: str) -> bool:
    """Updates the labels swarm stored as a file
    """
    cached_labels_swarm_filename = \
        acct_dir(base_dir, nickname, domain) + '/.labelsSwarm'
    save_swarm = True
    if is_a_file(cached_labels_swarm_filename):
        last_modified = file_last_modified(cached_labels_swarm_filename)
        modified_date = None
        try:
            modified_date = \
                date_from_string_format(last_modified, ["%Y-%m-%dT%H:%M:%S%z"])
        except BaseException:
            print('EX: unable to parse last modified cache date ' +
                  str(last_modified))
        if modified_date:
            curr_date = date_utcnow()
            time_diff = curr_date - modified_date
            diff_mins = int(time_diff.total_seconds() / 60)
            if diff_mins < 30:
                # was saved recently, so don't save again
                # This avoids too much disk I/O
                save_swarm: bool = False
                print('Not updating labels swarm')
            else:
                print('Updating cached labels swarm, last changed ' +
                      str(diff_mins) + ' minutes ago')
        else:
            print('WARN: no modified date for ' + str(last_modified))
    if save_swarm:
        actor = local_actor_url(http_prefix, nickname, domain_full)
        new_swarm_str = _html_labels_swarm(base_dir, actor)
        if new_swarm_str:
            if save_string(new_swarm_str, cached_labels_swarm_filename,
                           'EX: unable to write cached labels swarm ' +
                           cached_labels_swarm_filename):
                return True
        # remove_old_labels(base_dir, 3)
    return False


def store_content_labels(base_dir: str, nickname: str, domain: str,
                         http_prefix: str, domain_full: str,
                         post_json_object: {},
                         session) -> None:
    """Extracts content labels from an incoming post and updates the
    relevant label files.
    """
    labels_list: list[str] = get_labels_from_json(post_json_object)
    if not labels_list:
        return

    labels_dir = base_dir + '/labels'

    # add labels directory if it doesn't exist
    if not is_a_dir(labels_dir):
        print('Creating content labels directory')
        makedir(labels_dir)

    # obtain any map links and these can be associated with labelss
    # get geolocations from content
    map_links: list[str] = []
    published = None
    if 'content' in post_json_object['object']:
        published = post_json_object['object']['published']
        post_content = post_json_object['object']['content']
        map_links += get_map_links_from_post_content(post_content, session)
    # get geolocation from labels
    location_str = get_location_from_post(post_json_object)
    if location_str:
        # remove address if needed
        if '<br><address>' in location_str:
            location_str = location_str.split('<br><address>')[0].strip()
        if resembles_url(location_str):
            zoom, latitude, longitude = \
                geocoords_from_map_link(location_str,
                                        'openstreetmap.org', session)
            if latitude and longitude and zoom and \
               location_str not in map_links:
                map_links.append(location_str)
    labels_maps_dir = base_dir + '/labelsmaps'
    if map_links:
        # add labelsmaps directory if it doesn't exist
        if not is_a_dir(labels_maps_dir):
            print('Creating labelsmaps directory')
            makedir(labels_maps_dir)

    post_url = remove_id_ending(post_json_object['id'])
    post_url = post_url.replace('/', '#')
    labels_ctr: int = 0
    for label in labels_list:
        if _store_content_label(nickname,
                                label, labels_dir, post_url,
                                map_links, published,
                                labels_maps_dir):
            labels_ctr += 1

    # if some labels were found then recalculate the swarm
    # ready for later display
    if labels_ctr > 0:
        _update_cached_labels_swarm(base_dir, nickname, domain,
                                    http_prefix, domain_full)
