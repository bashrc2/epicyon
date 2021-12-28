__filename__ = "xmpp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def get_xmpp_address(actor_json: {}) -> str:
    """Returns xmpp address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        nameLower = property_value['name'].lower()
        if not (nameLower.startswith('xmpp') or
                nameLower.startswith('jabber')):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        if '@' not in property_value['value']:
            continue
        if '"' in property_value['value']:
            continue
        return property_value['value']
    return ''


def set_xmpp_address(actor_json: {}, xmppAddress: str) -> None:
    """Sets an xmpp address for the given actor
    """
    notXmppAddress = False
    if '@' not in xmppAddress:
        notXmppAddress = True
    if '.' not in xmppAddress:
        notXmppAddress = True
    if '"' in xmppAddress:
        notXmppAddress = True
    if '<' in xmppAddress:
        notXmppAddress = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not (property_value['name'].lower().startswith('xmpp') or
                property_value['name'].lower().startswith('jabber')):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notXmppAddress:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        nameLower = property_value['name'].lower()
        if not (nameLower.startswith('xmpp') or
                nameLower.startswith('jabber')):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = xmppAddress
        return

    newXmppAddress = {
        "name": "XMPP",
        "type": "PropertyValue",
        "value": xmppAddress
    }
    actor_json['attachment'].append(newXmppAddress)
