__filename__ = "enigma.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


import pyqrcode
from src.utils import acct_dir
from src.utils import load_json
from src.utils import get_attachment_property_value
from src.utils import remove_html
from src.data import is_a_file
from src.data import erase_file


def get_enigma_pub_key(actor_json: {}) -> str:
    """Returns Enigma public key for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    if not isinstance(actor_json['attachment'], list):
        return ''
    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value: str = None
        if property_value.get('name'):
            if isinstance(property_value['name'], str):
                name_value = property_value['name']
        elif property_value.get('schema:name'):
            if isinstance(property_value['schema:name'], str):
                name_value = property_value['schema:name']
        if not name_value:
            continue
        if not name_value.lower().startswith('enigma'):
            continue
        if not property_value.get('type'):
            continue
        if not isinstance(property_value['type'], str):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        return remove_html(property_value[prop_value_name])
    return ''


def save_enigma_qrcode(base_dir: str,
                       nickname: str, domain: str,
                       scale: int = 6) -> bool:
    """Saves a qrcode image for the enigma public key
    This helps to transfer onion or i2p handles to a mobile device
    """
    qrcode_filename = \
        acct_dir(base_dir, nickname, domain) + '/qrcode_enigma.png'
    if is_a_file(qrcode_filename):
        return False
    actor_filename = \
        acct_dir(base_dir, nickname, domain) + '.json'
    if not is_a_file(actor_filename):
        return False
    actor_json = load_json(actor_filename)
    if not actor_json:
        return False
    enigma_address = get_enigma_pub_key(actor_json)
    if not enigma_address:
        return False
    url = pyqrcode.create(enigma_address)
    try:
        url.png(qrcode_filename, scale)
        return True
    except ModuleNotFoundError:
        print('EX: save_enigma_qrcode pyqrcode png module not found')
    return False


def set_enigma_pub_key(base_dir: str, nickname: str, domain: str,
                       actor_json: {}, enigma_pub_key: str,
                       qrcode_scale: int) -> None:
    """Sets a Enigma public key for the given actor
    """
    if not enigma_pub_key:
        qrcode_filename = \
            acct_dir(base_dir, nickname, domain) + '/qrcode_enigma.png'
        if is_a_file(qrcode_filename):
            erase_file(qrcode_filename,
                       'EX: cannot remove enigma qrcode ' + qrcode_filename)

    remove_key: bool = False
    if not enigma_pub_key:
        remove_key = True

    if not actor_json.get('attachment'):
        actor_json['attachment']: list[dict] = []

    # remove any existing value
    property_found: str = None
    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value: str = None
        if property_value.get('name'):
            if isinstance(property_value['name'], str):
                name_value = property_value['name']
        elif property_value.get('schema:name'):
            if isinstance(property_value['schema:name'], str):
                name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not name_value.lower().startswith('enigma'):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if remove_key:
        return

    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value: str = None
        if property_value.get('name'):
            if isinstance(property_value['name'], str):
                name_value = property_value['name']
        elif property_value.get('schema:name'):
            if isinstance(property_value['schema:name'], str):
                name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not isinstance(property_value['type'], str):
            continue
        if not name_value.lower().startswith('enigma'):
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        property_value[prop_value_name] = enigma_pub_key
        return

    new_enigma_pub_key = {
        "name": "Enigma",
        "type": "PropertyValue",
        "value": enigma_pub_key
    }
    actor_json['attachment'].append(new_enigma_pub_key)
    save_enigma_qrcode(base_dir, nickname, domain, qrcode_scale)
