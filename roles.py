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
from utils import saveJson
from utils import getStatusNumber
from utils import removeDomainPort
from utils import acctDir


def _clearRoleStatus(baseDir: str, role: str) -> None:
    """Removes role status from all accounts
    This could be slow if there are many users, but only happens
    rarely when roles are appointed or removed
    """
    directory = os.fsencode(baseDir + '/accounts/')
    for f in os.scandir(directory):
        f = f.name
        filename = os.fsdecode(f)
        if '@' not in filename:
            continue
        if not filename.endswith(".json"):
            continue
        filename = os.path.join(baseDir + '/accounts/', filename)
        if '"' + role + '"' not in open(filename).read():
            continue
        actorJson = loadJson(filename)
        if not actorJson:
            continue
        rolesList = getActorRolesList(actorJson)
        if role in rolesList:
            rolesList.remove(role)
            setRolesFromList(actorJson, rolesList)
            saveJson(actorJson, filename)


def clearEditorStatus(baseDir: str) -> None:
    """Removes editor status from all accounts
    This could be slow if there are many users, but only happens
    rarely when editors are appointed or removed
    """
    _clearRoleStatus(baseDir, 'editor')


def clearCounselorStatus(baseDir: str) -> None:
    """Removes counselor status from all accounts
    This could be slow if there are many users, but only happens
    rarely when counselors are appointed or removed
    """
    _clearRoleStatus(baseDir, 'editor')


def clearArtistStatus(baseDir: str) -> None:
    """Removes artist status from all accounts
    This could be slow if there are many users, but only happens
    rarely when artists are appointed or removed
    """
    _clearRoleStatus(baseDir, 'artist')


def clearModeratorStatus(baseDir: str) -> None:
    """Removes moderator status from all accounts
    This could be slow if there are many users, but only happens
    rarely when moderators are appointed or removed
    """
    _clearRoleStatus(baseDir, 'moderator')


def _addRole(baseDir: str, nickname: str, domain: str,
             roleFilename: str) -> None:
    """Adds a role nickname to the file.
    This is a file containing the nicknames of accounts having this role
    """
    domain = removeDomainPort(domain)
    roleFile = baseDir + '/accounts/' + roleFilename
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
                if os.path.isdir(baseDir + '/accounts/' +
                                 roleNickname + '@' + domain):
                    f.write(roleNickname + '\n')
    else:
        with open(roleFile, 'w+') as f:
            accountDir = acctDir(baseDir, nickname, domain)
            if os.path.isdir(accountDir):
                f.write(nickname + '\n')


def _removeRole(baseDir: str, nickname: str, roleFilename: str) -> None:
    """Removes a role nickname from the file.
    This is a file containing the nicknames of accounts having this role
    """
    roleFile = baseDir + '/accounts/' + roleFilename
    if not os.path.isfile(roleFile):
        return
    with open(roleFile, 'r') as f:
        lines = f.readlines()
    with open(roleFile, 'w+') as f:
        for roleNickname in lines:
            roleNickname = roleNickname.strip('\n').strip('\r')
            if len(roleNickname) > 1 and roleNickname != nickname:
                f.write(roleNickname + '\n')


def _setActorRole(actorJson: {}, roleName: str) -> bool:
    """Sets a role for an actor
    """
    if not actorJson.get('hasOccupation'):
        return False
    if not isinstance(actorJson['hasOccupation'], list):
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

    for index in range(len(actorJson['hasOccupation'])):
        occupationItem = actorJson['hasOccupation'][index]
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
    actorJson['hasOccupation'].append(newRole)
    return True


def setRolesFromList(actorJson: {}, rolesList: []) -> None:
    """Sets roles from a list
    """
    # clear Roles from the occupation list
    emptyRolesList = []
    for occupationItem in actorJson['hasOccupation']:
        if not isinstance(occupationItem, dict):
            continue
        if not occupationItem.get('@type'):
            continue
        if occupationItem['@type'] == 'Role':
            continue
        emptyRolesList.append(occupationItem)
    actorJson['hasOccupation'] = emptyRolesList

    # create the new list
    for roleName in rolesList:
        _setActorRole(actorJson, roleName)


def getActorRolesList(actorJson: {}) -> []:
    """Gets a list of role names from an actor
    """
    if not actorJson.get('hasOccupation'):
        return []
    if not isinstance(actorJson['hasOccupation'], list):
        return []
    rolesList = []
    for occupationItem in actorJson['hasOccupation']:
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


def setRole(baseDir: str, nickname: str, domain: str,
            role: str) -> bool:
    """Set a person's role
    Setting the role to an empty string or None will remove it
    """
    # avoid giant strings
    if len(role) > 128:
        return False
    actorFilename = acctDir(baseDir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        return False

    roleFiles = {
        "moderator": "moderators.txt",
        "editor": "editors.txt",
        "counselor": "counselors.txt",
        "artist": "artists.txt"
    }

    actorJson = loadJson(actorFilename)
    if actorJson:
        if not actorJson.get('hasOccupation'):
            return False
        rolesList = getActorRolesList(actorJson)
        actorChanged = False
        if role:
            # add the role
            if roleFiles.get(role):
                _addRole(baseDir, nickname, domain, roleFiles[role])
            if role not in rolesList:
                rolesList.append(role)
                rolesList.sort()
                setRolesFromList(actorJson, rolesList)
                actorChanged = True
        else:
            # remove the role
            if roleFiles.get(role):
                _removeRole(baseDir, nickname, roleFiles[role])
            if role in rolesList:
                rolesList.remove(role)
                setRolesFromList(actorJson, rolesList)
                actorChanged = True
        if actorChanged:
            saveJson(actorJson, actorFilename)
    return True


def actorHasRole(actorJson: {}, roleName: str) -> bool:
    """Returns true if the given actor has the given role
    """
    rolesList = getActorRolesList(actorJson)
    return roleName in rolesList
