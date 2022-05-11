__filename__ = "enigma.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def get_enigma_pub_key(actor_json: {}) -> str:
    """Returns Enigma public key for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not name_value.lower().startswith('enigma'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        return property_value['value']
    return ''


def set_enigma_pub_key(actor_json: {}, enigma_pub_key: str) -> None:
    """Sets a Enigma public key for the given actor
    """
    remove_key = False
    if not enigma_pub_key:
        remove_key = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
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
        actor_json['attachment'].remove(property_value)
    if remove_key:
        return

    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not name_value.lower().startswith('enigma'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = enigma_pub_key
        return

    new_enigma_pub_key = {
        "name": "Enigma",
        "type": "PropertyValue",
        "value": enigma_pub_key
    }
    actor_json['attachment'].append(new_enigma_pub_key)
