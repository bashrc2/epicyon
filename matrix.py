__filename__ = "matrix.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"


def getMatrixAddress(actorJson: {}) -> str:
    """Returns matrix address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('matrix'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        if '@' not in propertyValue['value']:
            continue
        if not propertyValue['value'].startswith('@'):
            continue
        if ':' not in propertyValue['value']:
            continue
        if '"' in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''


def setMatrixAddress(actorJson: {}, matrixAddress: str) -> None:
    """Sets an matrix address for the given actor
    """
    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('matrix'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)

    if '@' not in matrixAddress:
        return
    if not matrixAddress.startswith('@'):
        return
    if '.' not in matrixAddress:
        return
    if '"' in matrixAddress:
        return
    if '<' in matrixAddress:
        return
    if ':' not in matrixAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('matrix'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = matrixAddress
        return

    newMatrixAddress = {
        "name": "Matrix",
        "type": "PropertyValue",
        "value": matrixAddress
    }
    actorJson['attachment'].append(newMatrixAddress)
