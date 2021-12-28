__filename__ = "matrix.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def get_matrix_address(actor_json: {}) -> str:
    """Returns matrix address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('matrix'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        if '@' not in property_value['value']:
            continue
        if not property_value['value'].startswith('@'):
            continue
        if ':' not in property_value['value']:
            continue
        if '"' in property_value['value']:
            continue
        return property_value['value']
    return ''


def set_matrix_address(actor_json: {}, matrixAddress: str) -> None:
    """Sets an matrix address for the given actor
    """
    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('matrix'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)

    if '@' not in matrixAddress:
        return
    if not matrixAddress.startswith('@'):
        return
    if '.' not in matrixAddress:
        return
    if '"' in matrixAddress:
        return
    if '<' in matrixAddress:
        return
    if ':' not in matrixAddress:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('matrix'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = matrixAddress
        return

    newMatrixAddress = {
        "name": "Matrix",
        "type": "PropertyValue",
        "value": matrixAddress
    }
    actor_json['attachment'].append(newMatrixAddress)
