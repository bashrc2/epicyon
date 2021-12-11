__filename__ = "enigma.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def getEnigmaPubKey(actorJson: {}) -> str:
    """Returns Enigma public key for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('enigma'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        return propertyValue['value']
    return ''


def setEnigmaPubKey(actorJson: {}, enigmaPubKey: str) -> None:
    """Sets a Enigma public key for the given actor
    """
    removeKey = False
    if not enigmaPubKey:
        removeKey = True

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('enigma'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyValue)
    if removeKey:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('enigma'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = enigmaPubKey
        return

    newenigmaPubKey = {
        "name": "Enigma",
        "type": "PropertyValue",
        "value": enigmaPubKey
    }
    actorJson['attachment'].append(newenigmaPubKey)
