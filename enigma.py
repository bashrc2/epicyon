__filename__ = "enigma.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def getEnigmaPubKey(actor_json: {}) -> str:
    """Returns Enigma public key for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('enigma'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        return property_value['value']
    return ''


def setEnigmaPubKey(actor_json: {}, enigmaPubKey: str) -> None:
    """Sets a Enigma public key for the given actor
    """
    removeKey = False
    if not enigmaPubKey:
        removeKey = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('enigma'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(property_value)
    if removeKey:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('enigma'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = enigmaPubKey
        return

    newenigmaPubKey = {
        "name": "Enigma",
        "type": "PropertyValue",
        "value": enigmaPubKey
    }
    actor_json['attachment'].append(newenigmaPubKey)
