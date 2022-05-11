__filename__ = "donate.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


def _get_donation_types() -> []:
    return ('patreon', 'paypal', 'gofundme', 'liberapay',
            'kickstarter', 'indiegogo', 'crowdsupply',
            'subscribestar')


def _get_website_strings() -> []:
    return ['www', 'website', 'web', 'homepage']


def get_donation_url(actor_json: {}) -> str:
    """Returns a link used for donations
    """
    if not actor_json.get('attachment'):
        return ''
    donation_type = _get_donation_types()
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if name_value.lower() not in donation_type:
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        if '<a href="' not in property_value['value']:
            continue
        donate_url = property_value['value'].split('<a href="')[1]
        if '"' in donate_url:
            return donate_url.split('"')[0]
    return ''


def get_website(actor_json: {}, translate: {}) -> str:
    """Returns a web address link
    """
    if not actor_json.get('attachment'):
        return ''
    match_strings = _get_website_strings()
    match_strings.append(translate['Website'].lower())
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if name_value.lower() not in match_strings:
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        return property_value['value']
    return ''


def set_donation_url(actor_json: {}, donate_url: str) -> None:
    """Sets a link used for donations
    """
    not_url = False
    if '.' not in donate_url:
        not_url = True
    if '://' not in donate_url:
        not_url = True
    if ' ' in donate_url:
        not_url = True
    if '<' in donate_url:
        not_url = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    donation_type = _get_donation_types()
    donate_name = None
    for payment_service in donation_type:
        if payment_service in donate_url:
            donate_name = payment_service
    if not donate_name:
        return

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if not name_value.lower() != donate_name:
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not_url:
        return

    donate_value = \
        '<a href="' + donate_url + \
        '" rel="me nofollow noopener noreferrer" target="_blank">' + \
        donate_url + '</a>'

    for property_value in actor_json['attachment']:
        name_value = None
        if property_value.get('name'):
            name_value = property_value['name']
        elif property_value.get('schema:name'):
            name_value = property_value['schema:name']
        if not name_value:
            continue
        if not property_value.get('type'):
            continue
        if name_value.lower() != donate_name:
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = donate_value
        return

    new_donate = {
        "name": donate_name,
        "type": "PropertyValue",
        "value": donate_value
    }
    actor_json['attachment'].append(new_donate)


def set_website(actor_json: {}, website_url: str, translate: {}) -> None:
    """Sets a web address
    """
    website_url = website_url.strip()
    not_url = False
    if '.' not in website_url:
        not_url = True
    if '://' not in website_url:
        not_url = True
    if ' ' in website_url:
        not_url = True
    if '<' in website_url:
        not_url = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    match_strings = _get_website_strings()
    match_strings.append(translate['Website'].lower())

    # remove any existing value
    property_found = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if property_value['name'].lower() not in match_strings:
            continue
        property_found = property_value
        break
    if property_found:
        actor_json['attachment'].remove(property_found)
    if not_url:
        return

    new_entry = {
        "name": 'Website',
        "type": "PropertyValue",
        "value": website_url
    }
    actor_json['attachment'].append(new_entry)
