__filename__ = "briar.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"


def getBriarAddress(actorJson: {}) -> str:
    """Returns briar address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('briar'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = propertyValue['value'].strip()
        if len(propertyValue['value']) < 50:
            continue
        if not propertyValue['value'].startswith('briar://'):
            continue
        if propertyValue['value'].lower() != propertyValue['value']:
            continue
        if '"' in propertyValue['value']:
            continue
        if ' ' in propertyValue['value']:
            continue
        if ',' in propertyValue['value']:
            continue
        if '.' in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''


def setBriarAddress(actorJson: {}, briarAddress: str) -> None:
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

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('briar'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)
    if notBriarAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('briar'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = briarAddress
        return

    newBriarAddress = {
        "name": "Briar",
        "type": "PropertyValue",
        "value": briarAddress
    }
    actorJson['attachment'].append(newBriarAddress)
