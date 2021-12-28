__filename__ = "jami.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def get_jami_address(actor_json: {}) -> str:
    """Returns jami address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('jami'):
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


def set_jami_address(actor_json: {}, jamiAddress: str) -> None:
    """Sets an jami address for the given actor
    """
    notJamiAddress = False

    if len(jamiAddress) < 2:
        notJamiAddress = True
    if '"' in jamiAddress:
        notJamiAddress = True
    if ' ' in jamiAddress:
        notJamiAddress = True
    if '.' in jamiAddress:
        notJamiAddress = True
    if ',' in jamiAddress:
        notJamiAddress = True
    if '<' in jamiAddress:
        notJamiAddress = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('jami'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notJamiAddress:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('jami'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = jamiAddress
        return

    newJamiAddress = {
        "name": "Jami",
        "type": "PropertyValue",
        "value": jamiAddress
    }
    actor_json['attachment'].append(newJamiAddress)
