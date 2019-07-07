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

def getOcapFilename(baseDir :str,nickname: str,domain: str,actor :str,subdir: str) -> str:
    return baseDir+'/ocap/'+subdir+'/'+domain+':'+nickname+':'+actor.replace('/','#')+'.json'

def capabilitiesMakeDirs(baseDir: str):
    if not os.path.isdir(baseDir+'/ocap'):
        os.mkdir(baseDir+'/ocap')
    # for capabilities accepted by this instance
    if not os.path.isdir(baseDir+'/ocap/accept'):
        os.mkdir(baseDir+'/ocap/accept')
    # for capabilities granted to this instance
    if not os.path.isdir(baseDir+'/ocap/granted'):
        os.mkdir(baseDir+'/ocap/granted')

def capabilitiesRequest(baseDir: str,httpPrefix: str,domain: str, \
                        requestedActor: str, \
                        requestedCaps=["inbox:write","objects:read"]) -> {}:
    # This is sent to the capabilities endpoint /caps/new
    # which could be instance wide or for a particular person
    # This could also be added to a follow activity
    capabilitiesMakeDirs(baseDir)

    ocapId=createPassword(32)
    ocapRequest = {
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
    if port!=80 and port !=443:
        fullDomain=domain+':'+str(port)
    
    # make directories to store capabilities
    capabilitiesMakeDirs(baseDir)
    ocapFilename=getOcapFilename(baseDir,nickname,fullDomain,acceptedActor,'accept')
    ocapAccept=None

    # if the capability already exists then load it from file
    if os.path.isfile(ocapFilename):
        with open(ocapFilename, 'r') as fp:
            ocapAccept=commentjson.load(fp)
    # otherwise create a new capability    
    if not ocapAccept:
        ocapId=createPassword(32)
        ocapAccept = {
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
    capabilitiesMakeDirs(baseDir)
    ocapFilename=getOcapFilename(baseDir,nickname,domain,ocap['actor'],'granted')
    with open(ocapFilename, 'w') as fp:
        commentjson.dump(ocap, fp, indent=4, sort_keys=False)
    return True

def isCapable(actor: str,ocapGranted: {},capability: str) -> bool:
    # is the given actor capable of using the current resource?
    for id,ocap in ocapGranted.items():
        if ocap['scope'] in actor:
            if capability in ocap['capability']:
                return True
    return False

def isCapableId(id: str,ocapGranted: {},capability: str) -> bool:
    # is the given id capable of using the current resource?
    if ocapGranted.get(id):
        if ocapGranted['id']['scope'] in actor:
            if capability in ocapGranted['id']['capability']:
                return True
    return False
