__filename__ = "pgp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json

def getEmailAddress(actorJson: {}) -> str:
    """Returns the email address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('email'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type']!='PropertyValue':
            continue
        if '@' not in propertyValue['value']:
            continue
        if '.' not in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''

def getPGPpubKey(actorJson: {}) -> str:
    """Returns PGP public key for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('pgp'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type']!='PropertyValue':
            continue
        if '-BEGIN PUBLIC KEY-' not in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''

def setEmailAddress(actorJson: {},emailAddress: str) -> None:
    """Sets the email address for the given actor
    """
    if not actorJson.get('attachment'):
        actorJson['attachment']=[]

    if '@' not in emailAddress:
        return
    if '.' not in emailAddress:
        return
    if emailAddress.startswith('@'):
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('email'):
            continue
        if propertyValue['type']!='PropertyValue':
            continue
        propertyValue['value']=emailAddress
        return

    newEmailAddress={
        "name": "Email",
        "type": "PropertyValue",
        "value": emailAddress
    }
    actorJson['attachment'].append(newEmailAddress)

def setPGPpubKey(actorJson: {},PGPpubKey: str) -> None:
    """Sets a PGP public key for the given actor
    """
    if not actorJson.get('attachment'):
        actorJson['attachment']=[]

    if '-BEGIN PUBLIC KEY-' not in PGPpubKey:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('pgp'):
            continue
        if propertyValue['type']!='PropertyValue':
            continue
        propertyValue['value']=PGPpubKey
        return

    newPGPpubKey={
        "name": "PGP",
        "type": "PropertyValue",
        "value": PGPpubKey
    }
    actorJson['attachment'].append(newPGPpubKey)
