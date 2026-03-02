__filename__ = "lxmf.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


import os
import pyqrcode
from utils import get_attachment_property_value
from utils import acct_dir
from utils import load_json

VALID_LXMF_CHARS = set('0123456789abcdefghijklmnopqrstuvwxyz')


def _is_valid_lxmf_address(lxmf_address: str) -> bool:
    """Is the given LXMF address valid?
    """
    if len(lxmf_address) != 32:
        return False
    if lxmf_address.lower() != lxmf_address:
        return False
    if not set(lxmf_address).issubset(VALID_LXMF_CHARS):
        return False
    return True


def _save_lxmf_qrcode(base_dir: str,
                      nickname: str, domain: str,
                      scale: int = 6) -> bool:
    """Saves a qrcode image for the handle of the person
    This helps to transfer onion or i2p handles to a mobile device
    """
    qrcode_filename = acct_dir(base_dir, nickname, domain) + '/qrcode_lxmf.png'
    if os.path.isfile(qrcode_filename):
        return False
    actor_filename = \
        acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actor_filename):
        return False
    actor_json = load_json(actor_filename)
    if not actor_json:
        return False
    lxmf_address = get_lxmf_address(actor_json)
    if not lxmf_address:
        return False
    url = pyqrcode.create(lxmf_address)
    try:
        url.png(qrcode_filename, scale)
        return True
    except ModuleNotFoundError:
        print('EX: save_lxmf_qrcode pyqrcode png module not found')
    return False


def get_lxmf_address(actor_json: {}) -> str:
    """Returns lxmf address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    if not isinstance(actor_json['attachment'], list):
        return ''
    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not name_value.lower().startswith('lxmf'):
            continue
        if not property_value.get('type'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        lxmf_address = property_value[prop_value_name].strip()

        # remove any prefix
        if lxmf_address.startswith('lxmf://'):
            lxmf_address = lxmf_address.replace('lxmf://', '')
        elif lxmf_address.startswith('lxmf:'):
            lxmf_address = lxmf_address.replace('lxmf:', '')

        if not _is_valid_lxmf_address(lxmf_address):
            continue
        return lxmf_address
    return ''


def set_lxmf_address(base_dir: str, nickname: str, domain: str,
                     actor_json: {}, lxmf_address: str,
                     qrcode_scale: int) -> None:
    """Sets an lxmf address for the given actor
    """
    if not lxmf_address:
        qrcode_filename = \
            acct_dir(base_dir, nickname, domain) + '/qrcode_lxmf.png'
        if os.path.isfile(qrcode_filename):
            try:
                os.remove(qrcode_filename)
            except OSError:
                print('EX: cannot remove lxmf qrcode ' + qrcode_filename)

    lxmf_address = lxmf_address.strip()

    # remove any prefix
    if lxmf_address.startswith('lxmf://'):
        lxmf_address = lxmf_address.replace('lxmf://', '')
    elif lxmf_address.startswith('lxmf:'):
        lxmf_address = lxmf_address.replace('lxmf:', '')

    is_lxmfaddress = _is_valid_lxmf_address(lxmf_address)

    if not actor_json.get('attachment'):
        actor_json['attachment']: list[dict] = []

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not name_value.lower().startswith('lxmf'):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not is_lxmfaddress:
        return

    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not name_value.lower().startswith('lxmf'):
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        property_value[prop_value_name] = lxmf_address
        return

    new_lxmf_address = {
        "name": "LXMF",
        "type": "PropertyValue",
        "value": lxmf_address
    }
    actor_json['attachment'].append(new_lxmf_address)
    _save_lxmf_qrcode(base_dir,
                      nickname, domain,
                      qrcode_scale)
