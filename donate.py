__filename__ = "donate.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"


from utils import get_attachment_property_value
from utils import remove_html


def _get_donation_types() -> []:
    return ('patreon', 'paypal', 'gofundme', 'liberapay',
            'kickstarter', 'indiegogo', 'crowdsupply',
            'subscribestar', 'kofi')


def _get_website_strings() -> []:
    return ['www', 'website', 'web', 'homepage', 'contact']


def _get_gemini_strings() -> []:
    return ['gemini', 'capsule', 'gemlog']


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
        prop_value_name, prop_value = \
            get_attachment_property_value(property_value)
        if not prop_value:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        if '<a href="' not in property_value[prop_value_name]:
            continue
        donate_url = property_value[prop_value_name].split('<a href="')[1]
        if '"' in donate_url:
            donate_url = donate_url.split('"')[0]
            return remove_html(donate_url)
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
        found = False
        for possible_str in match_strings:
            if possible_str in name_value.lower():
                found = True
                break
        if not found:
            continue
        if not property_value.get('type'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        value_str = remove_html(property_value[prop_value_name])
        if 'https://' not in value_str and \
           'http://' not in value_str:
            continue
        return value_str
    return ''


def get_gemini_link(actor_json: {}, translate: {}) -> str:
    """Returns a gemini link
    """
    if not actor_json.get('attachment'):
        return ''
    match_strings = _get_gemini_strings()
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
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        if not property_value['type'].endswith('PropertyValue'):
            continue
        return remove_html(property_value[prop_value_name])
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
        if not property_value['type'].endswith('PropertyValue'):
            continue
        prop_value_name, _ = \
            get_attachment_property_value(property_value)
        if not prop_value_name:
            continue
        property_value[prop_value_name] = donate_value
        return

    new_donate = {
        "name": donate_name,
        "type": "PropertyValue",
        "value": donate_value,
        "rel": "payment"
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


def set_gemini_link(actor_json: {}, gemini_link: str, translate: {}) -> None:
    """Sets a gemini link
    """
    gemini_link = gemini_link.strip()
    not_link = False
    if '.' not in gemini_link:
        not_link = True
    if '://' not in gemini_link:
        not_link = True
    if ' ' in gemini_link:
        not_link = True
    if '<' in gemini_link:
        not_link = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    match_strings = _get_gemini_strings()

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
    if not_link:
        return

    new_entry = {
        "name": 'Gemini',
        "type": "PropertyValue",
        "value": gemini_link
    }
    actor_json['attachment'].append(new_entry)
