__filename__ = "ssb.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"


def getSSBAddress(actorJson: {}) -> str:
    """Returns ssb address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('ssb'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = propertyValue['value'].strip()
        if not propertyValue['value'].startswith('@'):
            continue
        if '=.' not in propertyValue['value']:
            continue
        if '"' in propertyValue['value']:
            continue
        if ' ' in propertyValue['value']:
            continue
        if ',' in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''


def setSSBAddress(actorJson: {}, ssbAddress: str) -> None:
    """Sets an ssb address for the given actor
    """
    notSSBAddress = False
    if not ssbAddress.startswith('@'):
        notSSBAddress = True
    if '=.' not in ssbAddress:
        notSSBAddress = True
    if '"' in ssbAddress:
        notSSBAddress = True
    if ' ' in ssbAddress:
        notSSBAddress = True
    if ',' in ssbAddress:
        notSSBAddress = True
    if '<' in ssbAddress:
        notSSBAddress = True

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('ssb'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)
    if notSSBAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('ssb'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = ssbAddress
        return

    newSSBAddress = {
        "name": "SSB",
        "type": "PropertyValue",
        "value": ssbAddress
    }
    actorJson['attachment'].append(newSSBAddress)
