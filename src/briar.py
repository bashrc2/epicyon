__filename__ = "briar.py"
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


def get_briar_address(actor_json: {}) -> str:
    """Returns briar address for the given actor
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
        if not name_value.lower().startswith('briar'):
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
        if len(property_value[prop_value_name]) < 50:
            continue
        if not property_value[prop_value_name].startswith('briar://'):
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


def save_briar_qrcode(base_dir: str,
                      nickname: str, domain: str,
                      scale: int = 6) -> bool:
    """Saves a qrcode image for the briar address of the person
    This helps to transfer onion or i2p handles to a mobile device
    """
    qrcode_filename = \
        acct_dir(base_dir, nickname, domain) + '/qrcode_briar.png'
    if is_a_file(qrcode_filename):
        return False
    actor_filename = \
        acct_dir(base_dir, nickname, domain) + '.json'
    if not is_a_file(actor_filename):
        return False
    actor_json = load_json(actor_filename)
    if not actor_json:
        return False
    briar_address = get_briar_address(actor_json)
    if not briar_address:
        return False
    url = pyqrcode.create(briar_address)
    try:
        url.png(qrcode_filename, scale)
        return True
    except ModuleNotFoundError:
        print('EX: save_briar_qrcode pyqrcode png module not found')
    return False


def set_briar_address(base_dir: str, nickname: str, domain: str,
                      actor_json: {}, briar_address: str,
                      qrcode_scale: int) -> None:
    """Sets an briar address for the given actor
    """
    if not briar_address:
        qrcode_filename = \
            acct_dir(base_dir, nickname, domain) + '/qrcode_briar.png'
        if is_a_file(qrcode_filename):
            erase_file(qrcode_filename,
                       'EX: cannot remove briar qrcode ' + qrcode_filename)

    not_briar_address: bool = False

    if len(briar_address) < 50:
        not_briar_address = True
    if not briar_address.startswith('briar://'):
        not_briar_address = True
    if briar_address.lower() != briar_address:
        not_briar_address = True
    if '"' in briar_address:
        not_briar_address = True
    if ' ' in briar_address:
        not_briar_address = True
    if '.' in briar_address:
        not_briar_address = True
    if ',' in briar_address:
        not_briar_address = True
    if '<' in briar_address:
        not_briar_address = True

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
        if not name_value.lower().startswith('briar'):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not_briar_address:
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
        if not name_value.lower().startswith('briar'):
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        property_value[prop_value_name] = briar_address
        return

    new_briar_address = {
        "name": "Briar",
        "type": "PropertyValue",
        "value": briar_address
    }
    actor_json['attachment'].append(new_briar_address)
    save_briar_qrcode(base_dir, nickname, domain, qrcode_scale)
