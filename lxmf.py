__filename__ = "lxmf.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


from utils import get_attachment_property_value
from utils import remove_html

VALID_LXMF_CHARS = set('0123456789abcdefghijklmnopqrstuvwxyz')


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
        property_value[prop_value_name] = \
            property_value[prop_value_name].strip()
        if len(property_value[prop_value_name]) != 76:
            continue
        if property_value[prop_value_name].upper() != \
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


def set_lxmf_address(actor_json: {}, lxmf_address: str) -> None:
    """Sets an lxmf address for the given actor
    """
    lxmf_address = lxmf_address.strip()
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
