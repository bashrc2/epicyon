__filename__ = "tox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def get_tox_address(actor_json: {}) -> str:
    """Returns tox address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('tox'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = property_value['value'].strip()
        if len(property_value['value']) != 76:
            continue
        if property_value['value'].upper() != property_value['value']:
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


def set_tox_address(actor_json: {}, tox_address: str) -> None:
    """Sets an tox address for the given actor
    """
    notToxAddress = False

    if len(tox_address) != 76:
        notToxAddress = True
    if tox_address.upper() != tox_address:
        notToxAddress = True
    if '"' in tox_address:
        notToxAddress = True
    if ' ' in tox_address:
        notToxAddress = True
    if '.' in tox_address:
        notToxAddress = True
    if ',' in tox_address:
        notToxAddress = True
    if '<' in tox_address:
        notToxAddress = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('tox'):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if notToxAddress:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('tox'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = tox_address
        return

    newToxAddress = {
        "name": "Tox",
        "type": "PropertyValue",
        "value": tox_address
    }
    actor_json['attachment'].append(newToxAddress)
