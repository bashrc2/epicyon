__filename__ = "briar.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def get_briar_address(actor_json: {}) -> str:
    """Returns briar address for the given actor
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
        if not name_value.lower().startswith('briar'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if not property_value['type'].endswith('PropertyValue'):
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


def set_briar_address(actor_json: {}, briar_address: str) -> None:
    """Sets an briar address for the given actor
    """
    not_briar_address = False

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
        if not name_value.lower().startswith('briar'):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not_briar_address:
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
        if not name_value.lower().startswith('briar'):
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        property_value['value'] = briar_address
        return

    new_briar_address = {
        "name": "Briar",
        "type": "PropertyValue",
        "value": briar_address
    }
    actor_json['attachment'].append(new_briar_address)
