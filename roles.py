__filename__ = "roles.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson
from utils import saveJson


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
        if not actorJson.get('affiliation'):
            continue
        rolesList = \
            getRolesFromString(actorJson['affiliation']['roleName'])
        if role in rolesList:
            rolesList.remove(role)
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


def clearModeratorStatus(baseDir: str) -> None:
    """Removes moderator status from all accounts
    This could be slow if there are many users, but only happens
    rarely when moderators are appointed or removed
    """
    _clearRoleStatus(baseDir, 'moderator')


def _addRole(baseDir: str, nickname: str, domain: str,
             roleFilename: str) -> None:
    """Adds a role nickname to the file
    """
    if ':' in domain:
        domain = domain.split(':')[0]
    roleFile = baseDir + '/accounts/' + roleFilename
    if os.path.isfile(roleFile):
        # is this nickname already in the file?
        with open(roleFile, "r") as f:
            lines = f.readlines()
        for roleNickname in lines:
            roleNickname = roleNickname.strip('\n').strip('\r')
            if roleNickname == nickname:
                return
        lines.append(nickname)
        with open(roleFile, 'w+') as f:
            for roleNickname in lines:
                roleNickname = roleNickname.strip('\n').strip('\r')
                if len(roleNickname) > 1:
                    if os.path.isdir(baseDir + '/accounts/' +
                                     roleNickname + '@' + domain):
                        f.write(roleNickname + '\n')
    else:
        with open(roleFile, "w+") as f:
            if os.path.isdir(baseDir + '/accounts/' +
                             nickname + '@' + domain):
                f.write(nickname + '\n')


def _removeRole(baseDir: str, nickname: str, roleFilename: str) -> None:
    """Removes a role nickname from the file
    """
    roleFile = baseDir + '/accounts/' + roleFilename
    if not os.path.isfile(roleFile):
        return
    with open(roleFile, "r") as f:
        lines = f.readlines()
    with open(roleFile, 'w+') as f:
        for roleNickname in lines:
            roleNickname = roleNickname.strip('\n').strip('\r')
            if len(roleNickname) > 1 and roleNickname != nickname:
                f.write(roleNickname + '\n')


def setRolesFromList(actorJson: {}, rolesList: []) -> None:
    """Sets roles from a list
    """
    if actorJson.get('affiliation'):
        actorJson['affiliation']['roleName'] = rolesList.copy()


def getRolesFromString(rolesStr: str) -> []:
    """Returns a list of roles from a string
    """
    if isinstance(rolesStr, list):
        rolesList = rolesStr
    else:
        rolesList = rolesStr.split(',')
    rolesResult = []
    for roleName in rolesList:
        rolesResult.append(roleName.strip().lower())
    return rolesResult


def setRole(baseDir: str, nickname: str, domain: str,
            role: str) -> bool:
    """Set a person's role
    Setting the role to an empty string or None will remove it
    """
    # avoid giant strings
    if len(role) > 128:
        return False
    actorFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '.json'
    if not os.path.isfile(actorFilename):
        return False

    roleFiles = {
        "moderator": "moderators.txt",
        "editor": "editors.txt",
        "counselor": "counselors.txt"
    }

    actorJson = loadJson(actorFilename)
    if actorJson:
        if not actorJson.get('affiliation'):
            return False
        rolesList = \
            getRolesFromString(actorJson['affiliation']['roleName'])
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
