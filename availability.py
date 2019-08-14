__filename__ = "availability.py"
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

def setAvailability(baseDir: str,nickname: str,domain: str, \
                    status: str) -> bool:
    """Set an availability status
    """
    # avoid giant strings
    if len(status)>128:
        return False
    actorFilename=baseDir+'/accounts/'+nickname+'@'+domain+'.json'
    if not os.path.isfile(actorFilename):
        return False
    with open(actorFilename, 'r') as fp:
        actorJson=commentjson.load(fp)
        actorJson['availability']=status
        with open(actorFilename, 'w') as fp:
            commentjson.dump(actorJson, fp, indent=4, sort_keys=False)    
    return True

def getAvailability(baseDir: str,nickname: str,domain: str) -> str:
    """Returns the availability for a given person
    """
    actorFilename=baseDir+'/accounts/'+nickname+'@'+domain+'.json'
    if not os.path.isfile(actorFilename):
        return False
    with open(actorFilename, 'r') as fp:
        actorJson=commentjson.load(fp)
        if not actorJson.get('availability'):
            return None
        return actorJson['availability']
    return None

def outboxAvailability(baseDir: str,nickname: str,messageJson: {},debug: bool) -> bool:
    """Handles receiving an availability update
    """
    if not messageJson.get('type'):
        return False
    if not messageJson['type']=='Availability':
        return False
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], str):
        return False

    actorNickname=getNicknameFromActor(messageJson['actor'])
    if actorNickname!=nickname:
        return False
    domain,port=getDomainFromActor(messageJson['actor'])
    status=messageJson['object'].replace('"','')

    return setAvailability(baseDir,nickname,domain,status)

def sendAvailabilityViaServer(session,nickname: str,password: str,
                              domain: str,port: int, \
                              httpPrefix: str, \
                              status: str, \
                              cachedWebfingers: {},personCache: {}, \
                              debug: bool,projectVersion: str) -> {}:
    """Sets the availability for a person via c2s
    """
    if not session:
        print('WARN: No session for sendAvailabilityViaServer')
        return 6

    domainFull=domain
    if port!=80 and port!=443:
        domainFull=domain+':'+str(port)
        
    toUrl = httpPrefix+'://'+domainFull+'/users/'+nickname
    ccUrl = httpPrefix+'://'+domainFull+'/users/'+nickname+'/followers'

    newAvailabilityJson = {
        'type': 'Availability',
        'actor': httpPrefix+'://'+domainFull+'/users/'+nickname,
        'object': '"'+status+'"',
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle=httpPrefix+'://'+domainFull+'/@'+nickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                                domain,projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl,preferredName = \
        getPersonBox(session,wfRequest,personCache, \
                     projectVersion,httpPrefix,domain,postToBox)
                     
    if not inboxUrl:
        if debug:
            print('DEBUG: No '+postToBox+' was found for '+handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for '+handle)
        return 4
    
    authHeader=createBasicAuthHeader(Nickname,password)
     
    headers = {'host': domain, \
               'Content-type': 'application/json', \
               'Authorization': authHeader}
    postResult = \
        postJson(session,newAvailabilityJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST availability success')

    return newAvailabilityJson
