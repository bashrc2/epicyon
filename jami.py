__filename__ = "jami.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
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


def set_jami_address(actor_json: {}, jami_address: str) -> None:
    """Sets an jami address for the given actor
    """
    not_jami_address = False

    if len(jami_address) < 2:
        not_jami_address = True
    if '"' in jami_address:
        not_jami_address = True
    if ' ' in jami_address:
        not_jami_address = True
    if '.' in jami_address:
        not_jami_address = True
    if ',' in jami_address:
        not_jami_address = True
    if '<' in jami_address:
        not_jami_address = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('jami'):
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not_jami_address:
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
        property_value['value'] = jami_address
        return

    new_jami_address = {
        "name": "Jami",
        "type": "PropertyValue",
        "value": jami_address
    }
    actor_json['attachment'].append(new_jami_address)
