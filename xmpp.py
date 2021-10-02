__filename__ = "xmpp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def getXmppAddress(actorJson: {}) -> str:
    """Returns xmpp address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        nameLower = propertyValue['name'].lower()
        if not (nameLower.startswith('xmpp') or
                nameLower.startswith('jabber')):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        if '@' not in propertyValue['value']:
            continue
        if '"' in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''


def setXmppAddress(actorJson: {}, xmppAddress: str) -> None:
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

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not (propertyValue['name'].lower().startswith('xmpp') or
                propertyValue['name'].lower().startswith('jabber')):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)
    if notXmppAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        nameLower = propertyValue['name'].lower()
        if not (nameLower.startswith('xmpp') or
                nameLower.startswith('jabber')):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = xmppAddress
        return

    newXmppAddress = {
        "name": "XMPP",
        "type": "PropertyValue",
        "value": xmppAddress
    }
    actorJson['attachment'].append(newXmppAddress)
