__filename__ = "ssb.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def getSSBAddress(actor_json: {}) -> str:
    """Returns ssb address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for propertyValue in actor_json['attachment']:
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


def setSSBAddress(actor_json: {}, ssbAddress: str) -> None:
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

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actor_json['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('ssb'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notSSBAddress:
        return

    for propertyValue in actor_json['attachment']:
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
    actor_json['attachment'].append(newSSBAddress)
