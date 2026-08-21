__filename__ = "content_labels.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Daemon POST"

from src.utils import remove_html
from src.utils import resembles_url
from src.utils import has_object_dict

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
                    label_str = label_str.strip()
                    label_str = remove_html(label_str)
                    if label_str:
                        if len(labels) >= MAX_CONTENT_LABELS:
                            break
                        labels.append(label_str)
                # limit the number of labels
                if len(labels) >= MAX_CONTENT_LABELS:
                    break
            elif tag_dict['name'] == 'Label':
                label_str = tag_dict['value'].strip()
                label_str = remove_html(label_str)
                if label_str:
                    if 'href' in tag_dict:
                        if isinstance(tag_dict['href'], str):
                            if resembles_url(tag_dict['href']):
                                label_str += '###' + tag_dict['href']
                    labels.append(label_str)
                # limit the number of labels
                if len(labels) >= MAX_CONTENT_LABELS:
                    break
        elif tag_dict['type'] == 'Label':
            label_str = remove_html(tag_dict['name'])
            if label_str:
                if 'href' in tag_dict:
                    if isinstance(tag_dict['href'], str):
                        if resembles_url(tag_dict['href']):
                            label_str += '###' + tag_dict['href']
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
        label_url = ''
        if '###' in label:
            label_url = label.split('###')[1]
            label = label.split('###')[0]
        if labels_str:
            labels_str += ' '
        if not label_url:
            labels_str += '<mark>' + label + '</mark>'
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
    obj['attachment'].append(labels_dict)
