__filename__ = "donate.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"


def _getDonationTypes() -> str:
    return ('patreon', 'paypal', 'gofundme', 'liberapay',
            'kickstarter', 'indiegogo', 'crowdsupply',
            'subscribestar')


def getDonationUrl(actorJson: {}) -> str:
    """Returns a link used for donations
    """
    if not actorJson.get('attachment'):
        return ''
    donationType = _getDonationTypes()
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if propertyValue['name'].lower() not in donationType:
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        if '<a href="' not in propertyValue['value']:
            continue
        donateUrl = propertyValue['value'].split('<a href="')[1]
        if '"' in donateUrl:
            return donateUrl.split('"')[0]
    return ''


def setDonationUrl(actorJson: {}, donateUrl: str) -> None:
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

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    donationType = _getDonationTypes()
    donateName = None
    for paymentService in donationType:
        if paymentService in donateUrl:
            donateName = paymentService
    if not donateName:
        return

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower() != donateName:
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)
    if notUrl:
        return

    donateValue = \
        '<a href="' + donateUrl + \
        '" rel="me nofollow noopener noreferrer" target="_blank">' + \
        donateUrl + '</a>'

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if propertyValue['name'].lower() != donateName:
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = donateValue
        return

    newDonate = {
        "name": donateName,
        "type": "PropertyValue",
        "value": donateValue
    }
    actorJson['attachment'].append(newDonate)
