__filename__ = "roles.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox
from session import postJson
from utils import getFullDomain
from utils import getNicknameFromActor
from utils import getDomainFromActor
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
        if actorJson['roles'].get('instance'):
            if role in actorJson['roles']['instance']:
                actorJson['roles']['instance'].remove(role)
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


def setRole(baseDir: str, nickname: str, domain: str,
            project: str, role: str) -> bool:
    """Set a person's role within a project
    Setting the role to an empty string or None will remove it
    """
    # avoid giant strings
    if len(role) > 128 or len(project) > 128:
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
        if role:
            # add the role
            if project == 'instance':
                if roleFiles.get(role):
                    _addRole(baseDir, nickname, domain, roleFiles[role])
            if actorJson['roles'].get(project):
                if role not in actorJson['roles'][project]:
                    actorJson['roles'][project].append(role)
            else:
                actorJson['roles'][project] = [role]
        else:
            # remove the role
            if project == 'instance':
                if roleFiles.get(role):
                    _removeRole(baseDir, nickname, roleFiles[role])
            if actorJson['roles'].get(project):
                actorJson['roles'][project].remove(role)
                # if the project contains no roles then remove it
                if len(actorJson['roles'][project]) == 0:
                    del actorJson['roles'][project]
        saveJson(actorJson, actorFilename)
    return True


def _getRoles(baseDir: str, nickname: str, domain: str,
              project: str) -> []:
    """Returns the roles for a given person on a given project
    """
    actorFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '.json'
    if not os.path.isfile(actorFilename):
        return False

    actorJson = loadJson(actorFilename)
    if actorJson:
        if not actorJson.get('roles'):
            return None
        if not actorJson['roles'].get(project):
            return None
        return actorJson['roles'][project]
    return None


def outboxDelegate(baseDir: str, authenticatedNickname: str,
                   messageJson: {}, debug: bool) -> bool:
    """Handles receiving a delegation request
    """
    if not messageJson.get('type'):
        return False
    if not messageJson['type'] == 'Delegate':
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
        return False
    if not messageJson['object'].get('type'):
        return False
    if not messageJson['object']['type'] == 'Role':
        return False
    if not messageJson['object'].get('object'):
        return False
    if not messageJson['object'].get('actor'):
        return False
    if not isinstance(messageJson['object']['object'], str):
        return False
    if ';' not in messageJson['object']['object']:
        print('WARN: No ; separator between project and role')
        return False

    delegatorNickname = getNicknameFromActor(messageJson['actor'])
    if delegatorNickname != authenticatedNickname:
        return
    domain, port = getDomainFromActor(messageJson['actor'])
    project = messageJson['object']['object'].split(';')[0].strip()

    # instance delegators can delagate to other projects
    # than their own
    canDelegate = False
    delegatorRoles = _getRoles(baseDir, delegatorNickname,
                               domain, 'instance')
    if delegatorRoles:
        if 'delegator' in delegatorRoles:
            canDelegate = True

    if not canDelegate:
        canDelegate = True
        # non-instance delegators can only delegate within their project
        delegatorRoles = _getRoles(baseDir, delegatorNickname,
                                   domain, project)
        if delegatorRoles:
            if 'delegator' not in delegatorRoles:
                return False
        else:
            return False

    if not canDelegate:
        return False
    nickname = getNicknameFromActor(messageJson['object']['actor'])
    if not nickname:
        print('WARN: unable to find nickname in ' +
              messageJson['object']['actor'])
        return False
    role = \
        messageJson['object']['object'].split(';')[1].strip().lower()

    if not role:
        setRole(baseDir, nickname, domain, project, None)
        return True

    # what roles is this person already assigned to?
    existingRoles = _getRoles(baseDir, nickname, domain, project)
    if existingRoles:
        if role in existingRoles:
            if debug:
                print(nickname + '@' + domain +
                      ' is already assigned to the role ' +
                      role + ' within the project ' + project)
            return False
    setRole(baseDir, nickname, domain, project, role)
    if debug:
        print(nickname + '@' + domain +
              ' assigned to the role ' + role +
              ' within the project ' + project)
    return True


def sendRoleViaServer(baseDir: str, session,
                      delegatorNickname: str, password: str,
                      delegatorDomain: str, delegatorPort: int,
                      httpPrefix: str, nickname: str,
                      project: str, role: str,
                      cachedWebfingers: {}, personCache: {},
                      debug: bool, projectVersion: str) -> {}:
    """A delegator creates a role for a person via c2s
    Setting role to an empty string or None removes the role
    """
    if not session:
        print('WARN: No session for sendRoleViaServer')
        return 6

    delegatorDomainFull = getFullDomain(delegatorDomain, delegatorPort)

    toUrl = \
        httpPrefix + '://' + delegatorDomainFull + '/users/' + nickname
    ccUrl = \
        httpPrefix + '://' + delegatorDomainFull + '/users/' + \
        delegatorNickname + '/followers'

    if role:
        roleStr = project.lower() + ';' + role.lower()
    else:
        roleStr = project.lower() + ';'
    actor = \
        httpPrefix + '://' + delegatorDomainFull + \
        '/users/' + delegatorNickname
    delegateActor = \
        httpPrefix + '://' + delegatorDomainFull + '/users/' + nickname
    newRoleJson = {
        'type': 'Delegate',
        'actor': actor,
        'object': {
            'type': 'Role',
            'actor': delegateActor,
            'object': roleStr,
            'to': [toUrl],
            'cc': [ccUrl]
        },
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = \
        httpPrefix + '://' + delegatorDomainFull + '/@' + delegatorNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session, handle, httpPrefix,
                                cachedWebfingers,
                                delegatorDomain, projectVersion, debug)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session,
                                            wfRequest, personCache,
                                            projectVersion, httpPrefix,
                                            delegatorNickname,
                                            delegatorDomain, postToBox,
                                            765672)

    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(delegatorNickname, password)

    headers = {
        'host': delegatorDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(session, newRoleJson, [], inboxUrl, headers, 30, True)
    if not postResult:
        if debug:
            print('DEBUG: POST announce failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST role success')

    return newRoleJson
