__filename__ = "cwtch.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import re


def get_cwtch_address(actor_json: {}) -> str:
    """Returns cwtch address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('cwtch'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = property_value['value'].strip()
        if len(property_value['value']) < 2:
            continue
        if '"' in property_value['value']:
            continue
        if ' ' in property_value['value']:
            continue
        if ',' in property_value['value']:
            continue
        if '.' in property_value['value']:
            continue
        return property_value['value']
    return ''


def set_cwtch_address(actor_json: {}, cwtch_address: str) -> None:
    """Sets an cwtch address for the given actor
    """
    not_cwtch_address = False

    if len(cwtch_address) < 56:
        not_cwtch_address = True
    if cwtch_address != cwtch_address.lower():
        not_cwtch_address = True
    if not re.match("^[a-z0-9]*$", cwtch_address):
        not_cwtch_address = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('cwtch'):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not_cwtch_address:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('cwtch'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = cwtch_address
        return

    new_cwtch_address = {
        "name": "Cwtch",
        "type": "PropertyValue",
        "value": cwtch_address
    }
    actor_json['attachment'].append(new_cwtch_address)
