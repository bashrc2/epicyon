__filename__ = "xmpp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


from utils import get_attachment_property_value
from utils import remove_html


def get_xmpp_address(actor_json: {}) -> str:
    """Returns xmpp address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    if not isinstance(actor_json['attachment'], list):
        return ''
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name'].lower()
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name'].lower()
        if not name_value:
            continue
        if not (name_value.startswith('xmpp') or
                name_value.startswith('jabber') or
                name_value == 'chat'):
            continue
        if not property_value.get('type'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue') and \
           not property_value['type'] == 'Link':
            continue
        if '@' not in property_value[prop_value_name]:
            continue
        if '"' in property_value[prop_value_name]:
            continue
        if property_value[prop_value_name].startswith('xmpp://'):
            property_value[prop_value_name] = \
                property_value[prop_value_name].split('xmpp://', 1)[1]
        return remove_html(property_value[prop_value_name])
    return ''


def set_xmpp_address(actor_json: {}, xmpp_address: str) -> None:
    """Sets an xmpp address for the given actor
    """
    not_xmpp_address = False
    if '@' not in xmpp_address:
        not_xmpp_address = True
    if '.' not in xmpp_address:
        not_xmpp_address = True
    if '"' in xmpp_address:
        not_xmpp_address = True
    if '<' in xmpp_address:
        not_xmpp_address = True

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
        if not (name_value.lower().startswith('xmpp') or
                name_value.lower().startswith('jabber') or
                name_value == 'chat'):
            continue
        if name_value == 'chat':
            if not property_value.get('href'):
                continue
            if not isinstance(property_value['href'], str):
                continue
            if not property_value['href'].startswith('xmpp://'):
                continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not_xmpp_address:
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
        name_value = name_value.lower()
        if not (name_value.startswith('xmpp') or
                name_value.startswith('jabber') or
                name_value == 'chat'):
            continue
        if not property_value['type'].endswith('PropertyValue') and \
           not property_value['type'] == 'Link':
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        property_value[prop_value_name] = xmpp_address
        return

    if not xmpp_address.startswith('xmpp://'):
        xmpp_address = 'xmpp://' + xmpp_address

    # https://codeberg.org/fediverse/fep/src/branch/main/fep/1970/fep-1970.md
    new_xmpp_address = {
        "type": "Link",
        "name": "Chat",
        "rel": "discussion",
        "href": xmpp_address
    }
    actor_json['attachment'].append(new_xmpp_address)
