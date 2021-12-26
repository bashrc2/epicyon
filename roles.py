__filename__ = "roles.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import os
from utils import loadJson
from utils import save_json
from utils import getStatusNumber
from utils import removeDomainPort
from utils import acct_dir


def _clearRoleStatus(base_dir: str, role: str) -> None:
    """Removes role status from all accounts
    This could be slow if there are many users, but only happens
    rarely when roles are appointed or removed
    """
    directory = os.fsencode(base_dir + '/accounts/')
    for f in os.scandir(directory):
        f = f.name
        filename = os.fsdecode(f)
        if '@' not in filename:
            continue
        if not filename.endswith(".json"):
            continue
        filename = os.path.join(base_dir + '/accounts/', filename)
        if '"' + role + '"' not in open(filename).read():
            continue
        actor_json = loadJson(filename)
        if not actor_json:
            continue
        rolesList = getActorRolesList(actor_json)
        if role in rolesList:
            rolesList.remove(role)
            setRolesFromList(actor_json, rolesList)
            save_json(actor_json, filename)


def clearEditorStatus(base_dir: str) -> None:
    """Removes editor status from all accounts
    This could be slow if there are many users, but only happens
    rarely when editors are appointed or removed
    """
    _clearRoleStatus(base_dir, 'editor')


def clearCounselorStatus(base_dir: str) -> None:
    """Removes counselor status from all accounts
    This could be slow if there are many users, but only happens
    rarely when counselors are appointed or removed
    """
    _clearRoleStatus(base_dir, 'editor')


def clearArtistStatus(base_dir: str) -> None:
    """Removes artist status from all accounts
    This could be slow if there are many users, but only happens
    rarely when artists are appointed or removed
    """
    _clearRoleStatus(base_dir, 'artist')


def clearModeratorStatus(base_dir: str) -> None:
    """Removes moderator status from all accounts
    This could be slow if there are many users, but only happens
    rarely when moderators are appointed or removed
    """
    _clearRoleStatus(base_dir, 'moderator')


def _addRole(base_dir: str, nickname: str, domain: str,
             roleFilename: str) -> None:
    """Adds a role nickname to the file.
    This is a file containing the nicknames of accounts having this role
    """
    domain = removeDomainPort(domain)
    roleFile = base_dir + '/accounts/' + roleFilename
    if os.path.isfile(roleFile):
        # is this nickname already in the file?
        with open(roleFile, 'r') as f:
            lines = f.readlines()
        for roleNickname in lines:
            roleNickname = roleNickname.strip('\n').strip('\r')
            if roleNickname == nickname:
                return
        lines.append(nickname)
        with open(roleFile, 'w+') as f:
            for roleNickname in lines:
                roleNickname = roleNickname.strip('\n').strip('\r')
                if len(roleNickname) < 2:
                    continue
                if os.path.isdir(base_dir + '/accounts/' +
                                 roleNickname + '@' + domain):
                    f.write(roleNickname + '\n')
    else:
        with open(roleFile, 'w+') as f:
            accountDir = acct_dir(base_dir, nickname, domain)
            if os.path.isdir(accountDir):
                f.write(nickname + '\n')


def _removeRole(base_dir: str, nickname: str, roleFilename: str) -> None:
    """Removes a role nickname from the file.
    This is a file containing the nicknames of accounts having this role
    """
    roleFile = base_dir + '/accounts/' + roleFilename
    if not os.path.isfile(roleFile):
        return
    with open(roleFile, 'r') as f:
        lines = f.readlines()
    with open(roleFile, 'w+') as f:
        for roleNickname in lines:
            roleNickname = roleNickname.strip('\n').strip('\r')
            if len(roleNickname) > 1 and roleNickname != nickname:
                f.write(roleNickname + '\n')


def _setActorRole(actor_json: {}, roleName: str) -> bool:
    """Sets a role for an actor
    """
    if not actor_json.get('hasOccupation'):
        return False
    if not isinstance(actor_json['hasOccupation'], list):
        return False

    # occupation category from www.onetonline.org
    category = None
    if 'admin' in roleName:
        category = '15-1299.01'
    elif 'moderator' in roleName:
        category = '11-9199.02'
    elif 'editor' in roleName:
        category = '27-3041.00'
    elif 'counselor' in roleName:
        category = '23-1022.00'
    elif 'artist' in roleName:
        category = '27-1024.00'
    if not category:
        return False

    for index in range(len(actor_json['hasOccupation'])):
        occupationItem = actor_json['hasOccupation'][index]
        if not isinstance(occupationItem, dict):
            continue
        if not occupationItem.get('@type'):
            continue
        if occupationItem['@type'] != 'Role':
            continue
        if occupationItem['hasOccupation']['name'] == roleName:
            return True
    statusNumber, published = getStatusNumber()
    newRole = {
        "@type": "Role",
        "hasOccupation": {
            "@type": "Occupation",
            "name": roleName,
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
    actor_json['hasOccupation'].append(newRole)
    return True


def setRolesFromList(actor_json: {}, rolesList: []) -> None:
    """Sets roles from a list
    """
    # clear Roles from the occupation list
    emptyRolesList = []
    for occupationItem in actor_json['hasOccupation']:
        if not isinstance(occupationItem, dict):
            continue
        if not occupationItem.get('@type'):
            continue
        if occupationItem['@type'] == 'Role':
            continue
        emptyRolesList.append(occupationItem)
    actor_json['hasOccupation'] = emptyRolesList

    # create the new list
    for roleName in rolesList:
        _setActorRole(actor_json, roleName)


def getActorRolesList(actor_json: {}) -> []:
    """Gets a list of role names from an actor
    """
    if not actor_json.get('hasOccupation'):
        return []
    if not isinstance(actor_json['hasOccupation'], list):
        return []
    rolesList = []
    for occupationItem in actor_json['hasOccupation']:
        if not isinstance(occupationItem, dict):
            continue
        if not occupationItem.get('@type'):
            continue
        if occupationItem['@type'] != 'Role':
            continue
        roleName = occupationItem['hasOccupation']['name']
        if roleName not in rolesList:
            rolesList.append(roleName)
    return rolesList


def setRole(base_dir: str, nickname: str, domain: str,
            role: str) -> bool:
    """Set a person's role
    Setting the role to an empty string or None will remove it
    """
    # avoid giant strings
    if len(role) > 128:
        return False
    actorFilename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        return False

    roleFiles = {
        "moderator": "moderators.txt",
        "editor": "editors.txt",
        "counselor": "counselors.txt",
        "artist": "artists.txt"
    }

    actor_json = loadJson(actorFilename)
    if actor_json:
        if not actor_json.get('hasOccupation'):
            return False
        rolesList = getActorRolesList(actor_json)
        actorChanged = False
        if role:
            # add the role
            if roleFiles.get(role):
                _addRole(base_dir, nickname, domain, roleFiles[role])
            if role not in rolesList:
                rolesList.append(role)
                rolesList.sort()
                setRolesFromList(actor_json, rolesList)
                actorChanged = True
        else:
            # remove the role
            if roleFiles.get(role):
                _removeRole(base_dir, nickname, roleFiles[role])
            if role in rolesList:
                rolesList.remove(role)
                setRolesFromList(actor_json, rolesList)
                actorChanged = True
        if actorChanged:
            save_json(actor_json, actorFilename)
    return True


def actorHasRole(actor_json: {}, roleName: str) -> bool:
    """Returns true if the given actor has the given role
    """
    rolesList = getActorRolesList(actor_json)
    return roleName in rolesList
