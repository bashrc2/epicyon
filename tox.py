__filename__ = "tox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"


def getToxAddress(actorJson: {}) -> str:
    """Returns tox address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('tox'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = propertyValue['value'].strip()
        if len(propertyValue['value']) != 76:
            continue
        if propertyValue['value'].upper() != propertyValue['value']:
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


def setToxAddress(actorJson: {}, toxAddress: str) -> None:
    """Sets an tox address for the given actor
    """
    notToxAddress = False

    if len(toxAddress) != 76:
        notToxAddress = True
    if toxAddress.upper() != toxAddress:
        notToxAddress = True
    if '"' in toxAddress:
        notToxAddress = True
    if ' ' in toxAddress:
        notToxAddress = True
    if '.' in toxAddress:
        notToxAddress = True
    if ',' in toxAddress:
        notToxAddress = True
    if '<' in toxAddress:
        notToxAddress = True

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('tox'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)
    if notToxAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('tox'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = toxAddress
        return

    newToxAddress = {
        "name": "Tox",
        "type": "PropertyValue",
        "value": toxAddress
    }
    actorJson['attachment'].append(newToxAddress)
