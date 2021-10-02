__filename__ = "jami.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def getJamiAddress(actorJson: {}) -> str:
    """Returns jami address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('jami'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = propertyValue['value'].strip()
        if len(propertyValue['value']) < 2:
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


def setJamiAddress(actorJson: {}, jamiAddress: str) -> None:
    """Sets an jami address for the given actor
    """
    notJamiAddress = False

    if len(jamiAddress) < 2:
        notJamiAddress = True
    if '"' in jamiAddress:
        notJamiAddress = True
    if ' ' in jamiAddress:
        notJamiAddress = True
    if '.' in jamiAddress:
        notJamiAddress = True
    if ',' in jamiAddress:
        notJamiAddress = True
    if '<' in jamiAddress:
        notJamiAddress = True

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('jami'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)
    if notJamiAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('jami'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = jamiAddress
        return

    newJamiAddress = {
        "name": "Jami",
        "type": "PropertyValue",
        "value": jamiAddress
    }
    actorJson['attachment'].append(newJamiAddress)
