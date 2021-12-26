__filename__ = "cwtch.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import re


def getCwtchAddress(actor_json: {}) -> str:
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


def setCwtchAddress(actor_json: {}, cwtchAddress: str) -> None:
    """Sets an cwtch address for the given actor
    """
    notCwtchAddress = False

    if len(cwtchAddress) < 56:
        notCwtchAddress = True
    if cwtchAddress != cwtchAddress.lower():
        notCwtchAddress = True
    if not re.match("^[a-z0-9]*$", cwtchAddress):
        notCwtchAddress = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('cwtch'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notCwtchAddress:
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
        property_value['value'] = cwtchAddress
        return

    newCwtchAddress = {
        "name": "Cwtch",
        "type": "PropertyValue",
        "value": cwtchAddress
    }
    actor_json['attachment'].append(newCwtchAddress)
