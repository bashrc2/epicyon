__filename__ = "briar.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def getBriarAddress(actor_json: {}) -> str:
    """Returns briar address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('briar'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = property_value['value'].strip()
        if len(property_value['value']) < 50:
            continue
        if not property_value['value'].startswith('briar://'):
            continue
        if property_value['value'].lower() != property_value['value']:
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


def setBriarAddress(actor_json: {}, briarAddress: str) -> None:
    """Sets an briar address for the given actor
    """
    notBriarAddress = False

    if len(briarAddress) < 50:
        notBriarAddress = True
    if not briarAddress.startswith('briar://'):
        notBriarAddress = True
    if briarAddress.lower() != briarAddress:
        notBriarAddress = True
    if '"' in briarAddress:
        notBriarAddress = True
    if ' ' in briarAddress:
        notBriarAddress = True
    if '.' in briarAddress:
        notBriarAddress = True
    if ',' in briarAddress:
        notBriarAddress = True
    if '<' in briarAddress:
        notBriarAddress = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('briar'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notBriarAddress:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('briar'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = briarAddress
        return

    newBriarAddress = {
        "name": "Briar",
        "type": "PropertyValue",
        "value": briarAddress
    }
    actor_json['attachment'].append(newBriarAddress)
