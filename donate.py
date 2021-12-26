__filename__ = "donate.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def _getDonationTypes() -> []:
    return ('patreon', 'paypal', 'gofundme', 'liberapay',
            'kickstarter', 'indiegogo', 'crowdsupply',
            'subscribestar')


def _getWebsiteStrings() -> []:
    return ['www', 'website', 'web', 'homepage']


def getDonationUrl(actor_json: {}) -> str:
    """Returns a link used for donations
    """
    if not actor_json.get('attachment'):
        return ''
    donationType = _getDonationTypes()
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if property_value['name'].lower() not in donationType:
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        if '<a href="' not in property_value['value']:
            continue
        donateUrl = property_value['value'].split('<a href="')[1]
        if '"' in donateUrl:
            return donateUrl.split('"')[0]
    return ''


def getWebsite(actor_json: {}, translate: {}) -> str:
    """Returns a web address link
    """
    if not actor_json.get('attachment'):
        return ''
    matchStrings = _getWebsiteStrings()
    matchStrings.append(translate['Website'].lower())
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if property_value['name'].lower() not in matchStrings:
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        return property_value['value']
    return ''


def setDonationUrl(actor_json: {}, donateUrl: str) -> None:
    """Sets a link used for donations
    """
    notUrl = False
    if '.' not in donateUrl:
        notUrl = True
    if '://' not in donateUrl:
        notUrl = True
    if ' ' in donateUrl:
        notUrl = True
    if '<' in donateUrl:
        notUrl = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    donationType = _getDonationTypes()
    donateName = None
    for paymentService in donationType:
        if paymentService in donateUrl:
            donateName = paymentService
    if not donateName:
        return

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower() != donateName:
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notUrl:
        return

    donateValue = \
        '<a href="' + donateUrl + \
        '" rel="me nofollow noopener noreferrer" target="_blank">' + \
        donateUrl + '</a>'

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if property_value['name'].lower() != donateName:
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = donateValue
        return

    newDonate = {
        "name": donateName,
        "type": "PropertyValue",
        "value": donateValue
    }
    actor_json['attachment'].append(newDonate)


def setWebsite(actor_json: {}, websiteUrl: str, translate: {}) -> None:
    """Sets a web address
    """
    websiteUrl = websiteUrl.strip()
    notUrl = False
    if '.' not in websiteUrl:
        notUrl = True
    if '://' not in websiteUrl:
        notUrl = True
    if ' ' in websiteUrl:
        notUrl = True
    if '<' in websiteUrl:
        notUrl = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    matchStrings = _getWebsiteStrings()
    matchStrings.append(translate['Website'].lower())

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if property_value['name'].lower() not in matchStrings:
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notUrl:
        return

    newEntry = {
        "name": 'Website',
        "type": "PropertyValue",
        "value": websiteUrl
    }
    actor_json['attachment'].append(newEntry)
