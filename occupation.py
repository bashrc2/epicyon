__filename__ = "occupation.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"


def get_occupation_skills(actor_json: {}) -> []:
    """Returns the list of skills for an actor
    """
    if 'hasOccupation' not in actor_json:
        return []
    if not isinstance(actor_json['hasOccupation'], list):
        return []
    for occupation_item in actor_json['hasOccupation']:
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if not occupation_item['@type'] == 'Occupation':
            continue
        if not occupation_item.get('skills'):
            continue
        if isinstance(occupation_item['skills'], list):
            return occupation_item['skills']
        if isinstance(occupation_item['skills'], str):
            return [occupation_item['skills']]
        break
    return []


def get_occupation_name(actor_json: {}) -> str:
    """Returns the occupation name an actor
    """
    if not actor_json.get('hasOccupation'):
        return ""
    if not isinstance(actor_json['hasOccupation'], list):
        return ""
    for occupation_item in actor_json['hasOccupation']:
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] != 'Occupation':
            continue
        if not occupation_item.get('name'):
            continue
        if isinstance(occupation_item['name'], str):
            return occupation_item['name']
        break
    return ""


def set_occupation_name(actor_json: {}, name: str) -> bool:
    """Sets the occupation name of an actor
    """
    if not actor_json.get('hasOccupation'):
        return False
    if not isinstance(actor_json['hasOccupation'], list):
        return False
    for index, _ in enumerate(actor_json['hasOccupation']):
        occupation_item = actor_json['hasOccupation'][index]
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] != 'Occupation':
            continue
        occupation_item['name'] = name
        return True
    return False


def set_occupation_skills_list(actor_json: {}, skills_list: []) -> bool:
    """Sets the occupation skills for an actor
    """
    if 'hasOccupation' not in actor_json:
        return False
    if not isinstance(actor_json['hasOccupation'], list):
        return False
    for index, _ in enumerate(actor_json['hasOccupation']):
        occupation_item = actor_json['hasOccupation'][index]
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] != 'Occupation':
            continue
        occupation_item['skills'] = skills_list
        return True
    return False
