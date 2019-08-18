__filename__ = "capabilities.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import datetime
import time
import json
import commentjson
from auth import createPassword
from utils import getNicknameFromActor
from utils import getDomainFromActor

def getOcapFilename(baseDir :str,nickname: str,domain: str,actor :str,subdir: str) -> str:
    """Returns the filename for a particular capability accepted or granted
    Also creates directories as needed
    """
    if ':' in domain:
        domain=domain.split(':')[0]

    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')

    ocDir=baseDir+'/accounts/'+nickname+'@'+domain
    if not os.path.isdir(ocDir):
        os.mkdir(ocDir)

    ocDir=baseDir+'/accounts/'+nickname+'@'+domain+'/ocap'
    if not os.path.isdir(ocDir):
        os.mkdir(ocDir)

    ocDir=baseDir+'/accounts/'+nickname+'@'+domain+'/ocap/'+subdir
    if not os.path.isdir(ocDir):
        os.mkdir(ocDir)

    return baseDir+'/accounts/'+nickname+'@'+domain+'/ocap/'+subdir+'/'+actor.replace('/','#')+'.json'

def CapablePost(postJson: {}, capabilityList: [], debug :bool) -> bool:
    """Determines whether a post arriving in the inbox
    should be accepted accoring to the list of capabilities
    """
    if postJson.get('type'):
        # No announces/repeats
        if postJson['type']=='Announce':
            if 'inbox:noannounce' in capabilityList:
                if debug:
                    print('DEBUG: inbox post rejected because inbox:noannounce')
                return False
        # No likes
        if postJson['type']=='Like':
            if 'inbox:nolike' in capabilityList:
                if debug:
                    print('DEBUG: inbox post rejected because inbox:nolike')
                return False
        if postJson['type']=='Create':
            if postJson.get('object'):
                # Does this have a reply?
                if postJson['object'].get('inReplyTo'):
                    if postJson['object']['inReplyTo']:
                        if 'inbox:noreply' in capabilityList:
                            if debug:
                                print('DEBUG: inbox post rejected because inbox:noreply')
                            return False
                # are content warnings enforced?
                if postJson['object'].get('sensitive'):
                    if not postJson['object']['sensitive']:
                        if 'inbox:cw' in capabilityList:
                            if debug:
                                print('DEBUG: inbox post rejected because inbox:cw')
                            return False
                # content warning must have non-zero summary
                if postJson['object'].get('summary'):
                    if len(postJson['object']['summary'])<2:
                        if 'inbox:cw' in capabilityList:
                            if debug:
                                print('DEBUG: inbox post rejected because inbox:cw, summary missing')
                            return False                        
    if 'inbox:write' in capabilityList:
        return True
    return True

def capabilitiesRequest(baseDir: str,httpPrefix: str,domain: str, \
                        requestedActor: str, \
                        requestedCaps=["inbox:write","objects:read"]) -> {}:
    # This is sent to the capabilities endpoint /caps/new
    # which could be instance wide or for a particular person
    # This could also be added to a follow activity
    ocapId=createPassword(32)
    ocapRequest = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": httpPrefix+"://"+requestedDomain+"/caps/request/"+ocapId,
        "type": "Request",
        "capability": requestedCaps,
        "actor": requestedActor
    }
    return ocapRequest
 
def capabilitiesAccept(baseDir: str,httpPrefix: str, \
                       nickname: str,domain: str, port: int, \
                       acceptedActor: str, saveToFile: bool, \
                       acceptedCaps=["inbox:write","objects:read"]) -> {}:
    # This gets returned to capabilities requester
    # This could also be added to a follow Accept activity

    # reject excessively long actors
    if len(acceptedActor)>256:
        return None

    fullDomain=domain
    if port:
        if port!=80 and port !=443:
            if ':' not in domain:
                fullDomain=domain+':'+str(port)
    
    # make directories to store capabilities
    ocapFilename=getOcapFilename(baseDir,nickname,fullDomain,acceptedActor,'accept')
    ocapAccept=None

    # if the capability already exists then load it from file
    if os.path.isfile(ocapFilename):
        with open(ocapFilename, 'r') as fp:
            ocapAccept=commentjson.load(fp)
    # otherwise create a new capability    
    if not ocapAccept:
        acceptedActorNickname=getNicknameFromActor(acceptedActor)
        acceptedActorDomain,acceptedActorPort=getDomainFromActor(acceptedActor)
        if acceptedActorPort:            
            ocapId=acceptedActorNickname+'@'+acceptedActorDomain+':'+str(acceptedActorPort)+'#'+createPassword(32)
        else:
            ocapId=acceptedActorNickname+'@'+acceptedActorDomain+'#'+createPassword(32)
        ocapAccept = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": httpPrefix+"://"+fullDomain+"/caps/"+ocapId,
            "type": "Capability",
            "capability": acceptedCaps,
            "scope": acceptedActor,
            "actor": httpPrefix+"://"+fullDomain
        }
        if nickname:
            ocapAccept['actor']=httpPrefix+"://"+fullDomain+'/users/'+nickname

    if saveToFile:
        with open(ocapFilename, 'w') as fp:
            commentjson.dump(ocapAccept, fp, indent=4, sort_keys=False)
    return ocapAccept

def capabilitiesGrantedSave(baseDir :str,nickname :str,domain :str,ocap: {}) -> bool:
    """A capabilities accept is received, so stor it for
    reference when sending to the actor
    """
    if not ocap.get('actor'):
        return False
    ocapFilename=getOcapFilename(baseDir,nickname,domain,ocap['actor'],'granted')
    with open(ocapFilename, 'w') as fp:
        commentjson.dump(ocap, fp, indent=4, sort_keys=False)
    return True

def capabilitiesUpdate(baseDir: str,httpPrefix: str, \
                       nickname: str,domain: str, port: int, \
                       updateActor: str, \
                       updateCaps: []) -> {}:
    """Used to sends an update for a change of object capabilities
    Note that the capability id gets changed with a new random token
    so that the old capabilities can't continue to be used
    """

    # reject excessively long actors
    if len(updateActor)>256:
        return None

    fullDomain=domain
    if port:
        if port!=80 and port !=443:
            if ':' not in domain:
                fullDomain=domain+':'+str(port)
    
    # Get the filename of the capability
    ocapFilename=getOcapFilename(baseDir,nickname,fullDomain,updateActor,'accept')

    # The capability should already exist for it to be updated
    if not os.path.isfile(ocapFilename):
        return None

    # create an update activity
    ocapUpdate = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Update',
        'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
        'to': [updateActor],
        'cc': [],
        'object': {}
    }

    # read the existing capability
    with open(ocapFilename, 'r') as fp:
        ocapJson=commentjson.load(fp)

    # set the new capabilities list. eg. ["inbox:write","objects:read"]
    ocapJson['capability']=updateCaps

    # change the id, so that the old capabilities can't continue to be used
    updateActorNickname=getNicknameFromActor(updateActor)
    updateActorDomain,updateActorPort=getDomainFromActor(updateActor)
    if updateActorPort:
        ocapId=updateActorNickname+'@'+updateActorDomain+':'+str(updateActorPort)+'#'+createPassword(32)
    else:
        ocapId=updateActorNickname+'@'+updateActorDomain+'#'+createPassword(32)
    ocapJson['id']=httpPrefix+"://"+fullDomain+"/caps/"+ocapId
    ocapUpdate['object']=ocapJson

    # save it again
    with open(ocapFilename, 'w') as fp:
        commentjson.dump(ocapJson, fp, indent=4, sort_keys=False)
    
    return ocapUpdate

def capabilitiesReceiveUpdate(baseDir :str, \
                              nickname :str,domain :str,port :int, \
                              actor :str, \
                              newCapabilitiesId :str, \
                              capabilityList :[], debug :bool) -> bool:
    """An update for a capability or the given actor has arrived
    """
    ocapFilename= \
        getOcapFilename(baseDir,nickname,domain,actor,'granted')
    if not os.path.isfile(ocapFilename):
        if debug:
            print('DEBUG: capabilities file not found during update')
            print(ocapFilename)
        return False

    with open(ocapFilename, 'r') as fp:
        ocapJson=commentjson.load(fp)
        ocapJson['id']=newCapabilitiesId
        ocapJson['capability']=capabilityList
    
        with open(ocapFilename, 'w') as fp:
            commentjson.dump(ocapJson, fp, indent=4, sort_keys=False)
            return True
    return False
