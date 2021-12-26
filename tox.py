__filename__ = "tox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def getToxAddress(actor_json: {}) -> str:
    """Returns tox address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for propertyValue in actor_json['attachment']:
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


def setToxAddress(actor_json: {}, toxAddress: str) -> None:
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

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actor_json['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('tox'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notToxAddress:
        return

    for propertyValue in actor_json['attachment']:
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
    actor_json['attachment'].append(newToxAddress)
