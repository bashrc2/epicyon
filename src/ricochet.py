__filename__ = "ricochet.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


import pyqrcode
from src.utils import load_json
from src.utils import acct_dir
from src.utils import get_attachment_property_value
from src.utils import remove_html
from src.data import is_a_file
from src.data import erase_file


def get_ricochet_address(actor_json: {}) -> str:
    """Returns ricochet address for the given actor
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
        if not name_value.lower().startswith('ricochet'):
            continue
        if not property_value.get('type'):
            continue
        if not isinstance(property_value['type'], str):
            continue
        prop_value_name, prop_value = \
            get_attachment_property_value(property_value)
        if not prop_value:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        property_value[prop_value_name] = prop_value.strip()
        if len(property_value[prop_value_name]) < 60:
            continue
        if not property_value[prop_value_name].startswith('ricochet:'):
            continue
        if property_value[prop_value_name].lower() != \
           property_value[prop_value_name]:
            continue
        if '"' in property_value[prop_value_name]:
            continue
        if ' ' in property_value[prop_value_name]:
            continue
        if ',' in property_value[prop_value_name]:
            continue
        if '.' in property_value[prop_value_name]:
            continue
        return remove_html(property_value[prop_value_name])
    return ''


def save_ricochet_qrcode(base_dir: str,
                         nickname: str, domain: str,
                         scale: int = 6) -> bool:
    """Saves a qrcode image for the ricochet address of the person
    This helps to transfer onion or i2p handles to a mobile device
    """
    qrcode_filename = \
        acct_dir(base_dir, nickname, domain) + '/qrcode_ricochet.png'
    if is_a_file(qrcode_filename):
        return False
    actor_filename = \
        acct_dir(base_dir, nickname, domain) + '.json'
    if not is_a_file(actor_filename):
        return False
    actor_json = load_json(actor_filename)
    if not actor_json:
        return False
    ricochet_address = get_ricochet_address(actor_json)
    if not ricochet_address:
        return False
    url = pyqrcode.create(ricochet_address)
    try:
        url.png(qrcode_filename, scale)
        return True
    except ModuleNotFoundError:
        print('EX: save_ricochet_qrcode pyqrcode png module not found')
    return False


def set_ricochet_address(base_dir: str, nickname: str, domain: str,
                         actor_json: {}, ricochet_address: str,
                         qrcode_scale: int) -> None:
    """Sets an ricochet address for the given actor
    """
    if not ricochet_address:
        qrcode_filename = \
            acct_dir(base_dir, nickname, domain) + '/qrcode_ricochet.png'
        if is_a_file(qrcode_filename):
            erase_file(qrcode_filename,
                       'EX: cannot remove ricochet qrcode ' + qrcode_filename)

    not_ricochet_address: bool = False

    if len(ricochet_address) < 60:
        not_ricochet_address = True
    if not ricochet_address.startswith('ricochet:'):
        not_ricochet_address = True
    if ricochet_address.lower() != ricochet_address:
        not_ricochet_address = True
    if '"' in ricochet_address:
        not_ricochet_address = True
    if ' ' in ricochet_address:
        not_ricochet_address = True
    if '.' in ricochet_address:
        not_ricochet_address = True
    if ',' in ricochet_address:
        not_ricochet_address = True
    if '<' in ricochet_address:
        not_ricochet_address = True
    if '(' in ricochet_address:
        not_ricochet_address = True

    if not actor_json.get('attachment'):
        actor_json['attachment']: list[dict] = []

    # remove any existing value
    property_found: dict = None
    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value: str = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not name_value.lower().startswith('ricochet'):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not_ricochet_address:
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
        if not name_value.lower().startswith('ricochet'):
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        property_value[prop_value_name] = ricochet_address
        return

    new_ricochet_address = {
        "name": "Ricochet",
        "type": "PropertyValue",
        "value": ricochet_address
    }
    actor_json['attachment'].append(new_ricochet_address)
    save_ricochet_qrcode(base_dir, nickname, domain, qrcode_scale)
