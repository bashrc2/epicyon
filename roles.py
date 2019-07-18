__filename__ = "roles.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
import os
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox
from session import postJson
from utils import getNicknameFromActor
from utils import getDomainFromActor

def setRole(baseDir: str,nickname: str,domain: str, \
            project: str,role: str) -> bool:
    """Set a person's role within a project
    Setting the role to an empty string or None will remove it
    """
    # avoid giant strings
    if len(role)>128 or len(project)>128:
        return False
    actorFilename=baseDir+'/accounts/'+nickname+'@'+domain+'.json'
    if not os.path.isfile(actorFilename):
        return False
    with open(actorFilename, 'r') as fp:
        actorJson=commentjson.load(fp)
        if role:
            if actorJson['roles'].get(project):
                if role not in actorJson['roles'][project]:
                    actorJson['roles'][project].append(role)
            else:
                actorJson['roles'][project]=[role]
        else:
            if actorJson['roles'].get(project):
                actorJson['roles'][project].remove(role)
                # if the project contains no roles then remove it
                if len(actorJson['roles'][project])==0:
                    del actorJson['roles'][project]
        with open(actorFilename, 'w') as fp:
            commentjson.dump(actorJson, fp, indent=4, sort_keys=False)    
    return True

def getRoles(baseDir: str,nickname: str,domain: str, \
             project: str) -> []:
    """Returns the roles for a given person on a given project
    """
    actorFilename=baseDir+'/accounts/'+nickname+'@'+domain+'.json'
    if not os.path.isfile(actorFilename):
        return False
    with open(actorFilename, 'r') as fp:
        actorJson=commentjson.load(fp)
        if not actorJson.get('roles'):
            return None
        if not actorJson['roles'].get(project):
            return None
        return actorJson['roles'][project]
    return None

def outboxDelegate(baseDir: str,messageJson: {},debug: bool) -> None:
    """Handles receiving a delegation request
    """
    if not messageJson.get('type'):
        return
    if not messageJson['type']=='Delegate':
        return
    if not messageJson.get('object'):
        return
    if not isinstance(messageJson['object'], dict):
        return
    if not messageJson['object'].get('type'):
        return
    if not messageJson['object']['type']=='Role':
        return
    if not messageJson['object'].get('object'):
        return
    if not messageJson['object'].get('actor'):
        return
    if not isinstance(messageJson['object']['object'], str):
        return
    if ';' not in messageJson['object']['object']:
        print('WARN: No ; separator between project and role')
        return
    if debug:
        print('DEBUG: delegate activity arrived in outbox')

    delegatorNickname=getNicknameFromActor(messageJson['actor'])
    domain,port=getDomainFromActor(messageJson['actor'])
    project=messageJson['object']['object'].split(';')[0].strip()

    # does the delegator have capability to delegate in this project?
    delegatorRoles=getRoles(baseDir,delegatorNickname, \
                            domain,project)
    if delegatorRoles:
        if 'delegator' not in delegatorRoles:
            # instance delegators can delagate to other projects
            # than their own
            delegatorRoles=getRoles(baseDir,delegatorNickname, \
                                    domain,'instance')
            if 'delegator' not in delegatorRoles:
                return
    
    nickname=getNicknameFromActor(messageJson['object']['actor'])
    domainFull=domain
    if port:
        if port!=80 and port!=443:
            domainFull=domain+':'+str(port)
    role=messageJson['object']['object'].split(';')[1].strip().lower()

    # what roles is this person already assigned to?
    existingRoles=getRoles(baseDir,nickname,domain,project)
    if existingRoles:
        if role in existingRoles:
            print(nickname+'@'+domain+' is already assigned to the role '+role+' within the project '+project)            
            return
    setRole(baseDir,nickname,domain,project,role)
    print(nickname+'@'+domain+' assigned to the role '+role+' within the project '+project)            

def sendRoleViaServer(session,delegatorNickname: str,password: str,
                      delegatorDomain: str,delegatorPort: int, \
                      httpPrefix: str,nickname: str, \
                      project: str,role: str, \
                      cachedWebfingers: {},personCache: {}, \
                      debug: bool) -> {}:
    """A delegator creates a role for a person via c2s
    """
    if not session:
        print('WARN: No session for sendRoleViaServer')
        return 6

    delegatorDomainFull=delegatorDomain
    if fromPort!=80 and fromPort!=443:
        delegatorDomainFull=delegatorDomain+':'+str(fromPort)
        
    toUrl = httpPrefix+'://'+delegatorDomainFull+'/users/'+nickname
    ccUrl = httpPrefix+'://'+delegatorDomainFull+'/users/'+delegatorNickname+'/followers'

    newRoleJson = {
        'type': 'Delegate',
        'actor': httpPrefix+'://'+delegatorDomainFull+'/users/'+delegatorNickname,
        'object': {
            'type': 'Role',
            'actor': httpPrefix+'://'+delegatorDomainFull+'/users/'+nickname,
            'object': project.lower()+';'+role.lower(),
            'to': [toUrl],
            'cc': [ccUrl]            
        },
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle=httpPrefix+'://'+delegatorDomainFull+'/@'+delegatorNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition = \
        getPersonBox(session,wfRequest,personCache,postToBox)
                     
    if not inboxUrl:
        if debug:
            print('DEBUG: No '+postToBox+' was found for '+handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for '+handle)
        return 4
    
    authHeader=createBasicAuthHeader(delegatorNickname,password)
     
    headers = {'host': delegatorDomain, \
               'Content-type': 'application/json', \
               'Authorization': authHeader}
    postResult = \
        postJson(session,newRoleJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST role success')

    return newRoleJson
