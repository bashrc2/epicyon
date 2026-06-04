__filename__ = "loops.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


from src.utils import get_attachment_property_value
from src.utils import remove_html
from src.utils import string_contains

loops_fieldnames = ['loops']


def get_loops(actor_json: {}) -> str:
    """Returns Loops for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    if not isinstance(actor_json['attachment'], list):
        return ''
    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value: str = None
        if property_value.get('name'):
            if isinstance(property_value['name'], str):
                name_value = property_value['name'].lower()
        elif property_value.get('schema:name'):
            if isinstance(property_value['schema:name'], str):
                name_value = property_value['schema:name'].lower()
        if not name_value:
            continue
        if not string_contains(name_value, loops_fieldnames):
            continue
        if not property_value.get('type'):
            continue
        if not isinstance(property_value['type'], str):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        loops_text = property_value[prop_value_name]
        return remove_html(loops_text)

    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        if not property_value.get('type'):
            continue
        if not isinstance(property_value['type'], str):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        loops_text: str = property_value[prop_value_name]
        if '//loops.' not in loops_text:
            continue
        return remove_html(loops_text)
    return ''


def set_loops(actor_json: {}, loops: str) -> None:
    """Sets Loops for the given actor
    """
    if not actor_json.get('attachment'):
        actor_json['attachment']: list[dict] = []

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value: str = None
        if property_value.get('name'):
            if isinstance(property_value['name'], str):
                name_value = property_value['name'].lower()
        elif property_value.get('schema:name'):
            if isinstance(property_value['schema:name'], str):
                name_value = property_value['schema:name'].lower()
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not string_contains(name_value, loops_fieldnames):
            continue
        property_found = property_value
        break

    if property_found:
        actor_json['attachment'].remove(property_found)

    for property_value in actor_json['attachment']:
        if not isinstance(property_value, dict):
            print("WARN: actor attachment is not dict: " + str(property_value))
            continue
        name_value: str = None
        if property_value.get('name'):
            if isinstance(property_value['name'], str):
                name_value = property_value['name']
        elif property_value.get('schema:name'):
            if isinstance(property_value['schema:name'], str):
                name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not isinstance(property_value['type'], str):
            continue
        name_value = name_value.lower()
        if not string_contains(name_value, loops_fieldnames):
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        property_value[prop_value_name] = remove_html(loops)
        return

    new_loops = {
        "type": "PropertyValue",
        "name": "Loops",
        "value": remove_html(loops)
    }
    actor_json['attachment'].append(new_loops)
