__filename__ = "cwtch.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import re


def getCwtchAddress(actorJson: {}) -> str:
    """Returns cwtch address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('cwtch'):
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


def setCwtchAddress(actorJson: {}, cwtchAddress: str) -> None:
    """Sets an cwtch address for the given actor
    """
    notCwtchAddress = False

    if len(cwtchAddress) < 56:
        notCwtchAddress = True
    if cwtchAddress != cwtchAddress.lower():
        notCwtchAddress = True
    if not re.match("^[a-z0-9]*$", cwtchAddress):
        notCwtchAddress = True

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('cwtch'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)
    if notCwtchAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('cwtch'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = cwtchAddress
        return

    newCwtchAddress = {
        "name": "Cwtch",
        "type": "PropertyValue",
        "value": cwtchAddress
    }
    actorJson['attachment'].append(newCwtchAddress)
