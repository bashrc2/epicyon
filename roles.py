__filename__ = "roles.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import os
from utils import load_json
from utils import save_json
from utils import get_status_number
from utils import remove_domain_port
from utils import acct_dir


def _clear_role_status(base_dir: str, role: str) -> None:
    """Removes role status from all accounts
    This could be slow if there are many users, but only happens
    rarely when roles are appointed or removed
    """
    directory = os.fsencode(base_dir + '/accounts/')
    for fname in os.scandir(directory):
        filename = os.fsdecode(fname.name)
        if '@' not in filename:
            continue
        if not filename.endswith(".json"):
            continue
        filename = os.path.join(base_dir + '/accounts/', filename)
        if '"' + role + '"' not in open(filename).read():
            continue
        actor_json = load_json(filename)
        if not actor_json:
            continue
        roles_list = get_actor_roles_list(actor_json)
        if role in roles_list:
            roles_list.remove(role)
            set_rolesFromList(actor_json, roles_list)
            save_json(actor_json, filename)


def clear_editor_status(base_dir: str) -> None:
    """Removes editor status from all accounts
    This could be slow if there are many users, but only happens
    rarely when editors are appointed or removed
    """
    _clear_role_status(base_dir, 'editor')


def clear_counselor_status(base_dir: str) -> None:
    """Removes counselor status from all accounts
    This could be slow if there are many users, but only happens
    rarely when counselors are appointed or removed
    """
    _clear_role_status(base_dir, 'editor')


def clear_artist_status(base_dir: str) -> None:
    """Removes artist status from all accounts
    This could be slow if there are many users, but only happens
    rarely when artists are appointed or removed
    """
    _clear_role_status(base_dir, 'artist')


def clear_moderator_status(base_dir: str) -> None:
    """Removes moderator status from all accounts
    This could be slow if there are many users, but only happens
    rarely when moderators are appointed or removed
    """
    _clear_role_status(base_dir, 'moderator')


def _add_role(base_dir: str, nickname: str, domain: str,
              role_filename: str) -> None:
    """Adds a role nickname to the file.
    This is a file containing the nicknames of accounts having this role
    """
    domain = remove_domain_port(domain)
    role_file = base_dir + '/accounts/' + role_filename
    if os.path.isfile(role_file):
        # is this nickname already in the file?

        lines = []
        try:
            with open(role_file, 'r') as fp_role:
                lines = fp_role.readlines()
        except OSError:
            print('EX: _add_role, failed to read roles file ' + role_file)

        for role_nickname in lines:
            role_nickname = role_nickname.strip('\n').strip('\r')
            if role_nickname == nickname:
                return
        lines.append(nickname)

        try:
            with open(role_file, 'w+') as fp_role:
                for role_nickname in lines:
                    role_nickname = role_nickname.strip('\n').strip('\r')
                    if len(role_nickname) < 2:
                        continue
                    if os.path.isdir(base_dir + '/accounts/' +
                                     role_nickname + '@' + domain):
                        fp_role.write(role_nickname + '\n')
        except OSError:
            print('EX: _add_role, failed to write roles file1 ' + role_file)
    else:
        try:
            with open(role_file, 'w+') as fp_role:
                account_dir = acct_dir(base_dir, nickname, domain)
                if os.path.isdir(account_dir):
                    fp_role.write(nickname + '\n')
        except OSError:
            print('EX: _add_role, failed to write roles file2 ' + role_file)


def _remove_role(base_dir: str, nickname: str, role_filename: str) -> None:
    """Removes a role nickname from the file.
    This is a file containing the nicknames of accounts having this role
    """
    role_file = base_dir + '/accounts/' + role_filename
    if not os.path.isfile(role_file):
        return

    try:
        with open(role_file, 'r') as fp_role:
            lines = fp_role.readlines()
    except OSError:
        print('EX: _remove_role, failed to read roles file ' + role_file)

    try:
        with open(role_file, 'w+') as fp_role:
            for role_nickname in lines:
                role_nickname = role_nickname.strip('\n').strip('\r')
                if len(role_nickname) > 1 and role_nickname != nickname:
                    fp_role.write(role_nickname + '\n')
    except OSError:
        print('EX: _remove_role, failed to regenerate roles file ' + role_file)


def _set_actor_role(actor_json: {}, role_name: str) -> bool:
    """Sets a role for an actor
    """
    if not actor_json.get('hasOccupation'):
        return False
    if not isinstance(actor_json['hasOccupation'], list):
        return False

    # occupation category from www.onetonline.org
    category = None
    if 'admin' in role_name:
        category = '15-1299.01'
    elif 'moderator' in role_name:
        category = '11-9199.02'
    elif 'editor' in role_name:
        category = '27-3041.00'
    elif 'counselor' in role_name:
        category = '23-1022.00'
    elif 'artist' in role_name:
        category = '27-1024.00'
    if not category:
        return False

    for index in range(len(actor_json['hasOccupation'])):
        occupation_item = actor_json['hasOccupation'][index]
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] != 'Role':
            continue
        if occupation_item['hasOccupation']['name'] == role_name:
            return True
    _, published = get_status_number()
    new_role = {
        "@type": "Role",
        "hasOccupation": {
            "@type": "Occupation",
            "name": role_name,
            "description": "Fediverse instance role",
            "occupationLocation": {
                "@type": "City",
                "url": "Fediverse"
            },
            "occupationalCategory": {
                "@type": "CategoryCode",
                "inCodeSet": {
                    "@type": "CategoryCodeSet",
                    "name": "O*Net-SOC",
                    "dateModified": "2019",
                    "url": "https://www.onetonline.org/"
                },
                "codeValue": category,
                "url": "https://www.onetonline.org/link/summary/" + category
            }
        },
        "startDate": published
    }
    actor_json['hasOccupation'].append(new_role)
    return True


def set_rolesFromList(actor_json: {}, roles_list: []) -> None:
    """Sets roles from a list
    """
    # clear Roles from the occupation list
    empty_roles_list = []
    for occupation_item in actor_json['hasOccupation']:
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] == 'Role':
            continue
        empty_roles_list.append(occupation_item)
    actor_json['hasOccupation'] = empty_roles_list

    # create the new list
    for role_name in roles_list:
        _set_actor_role(actor_json, role_name)


def get_actor_roles_list(actor_json: {}) -> []:
    """Gets a list of role names from an actor
    """
    if not actor_json.get('hasOccupation'):
        return []
    if not isinstance(actor_json['hasOccupation'], list):
        return []
    roles_list = []
    for occupation_item in actor_json['hasOccupation']:
        if not isinstance(occupation_item, dict):
            continue
        if not occupation_item.get('@type'):
            continue
        if occupation_item['@type'] != 'Role':
            continue
        role_name = occupation_item['hasOccupation']['name']
        if role_name not in roles_list:
            roles_list.append(role_name)
    return roles_list


def set_role(base_dir: str, nickname: str, domain: str,
             role: str) -> bool:
    """Set a person's role
    Setting the role to an empty string or None will remove it
    """
    # avoid giant strings
    if len(role) > 128:
        return False
    actor_filename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actor_filename):
        return False

    role_files = {
        "moderator": "moderators.txt",
        "editor": "editors.txt",
        "counselor": "counselors.txt",
        "artist": "artists.txt"
    }

    actor_json = load_json(actor_filename)
    if actor_json:
        if not actor_json.get('hasOccupation'):
            return False
        roles_list = get_actor_roles_list(actor_json)
        actor_changed = False
        if role:
            # add the role
            if role_files.get(role):
                _add_role(base_dir, nickname, domain, role_files[role])
            if role not in roles_list:
                roles_list.append(role)
                roles_list.sort()
                set_rolesFromList(actor_json, roles_list)
                actor_changed = True
        else:
            # remove the role
            if role_files.get(role):
                _remove_role(base_dir, nickname, role_files[role])
            if role in roles_list:
                roles_list.remove(role)
                set_rolesFromList(actor_json, roles_list)
                actor_changed = True
        if actor_changed:
            save_json(actor_json, actor_filename)
    return True


def actor_has_role(actor_json: {}, role_name: str) -> bool:
    """Returns true if the given actor has the given role
    """
    roles_list = get_actor_roles_list(actor_json)
    return role_name in roles_list
