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
    for propertyValue in actor_json['attachment']:
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
    for propertyValue in actor_json['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('briar'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notBriarAddress:
        return

    for propertyValue in actor_json['attachment']:
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
    actor_json['attachment'].append(newBriarAddress)
