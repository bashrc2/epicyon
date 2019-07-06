__filename__ = "capabilities.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from auth import createPassword

def sendCapabilitiesRequest(baseDir: str,httpPrefix: str,domain: str, \
                            requestedActor: str, \
                            requestedCaps=["inbox:write","objects:read"]) -> None:
    # This is sent to the capabilities endpoint /caps/new
    # which could be instance wide or for a particular person
    capId=createPassword(32)
    capRequest = {
        "id": httpPrefix+"://"+requestedDomain+"/caps/request/"+capId,
        "type": "Request",
        "capability": requestedCaps,
        "actor": requestedActor
    }
    #TODO

def sendCapabilitiesAccept(baseDir: str,httpPrefix: str,nickname: str,domain: str, \
                           acceptedActor: str, \
                           acceptedCaps=["inbox:write","objects:read"]) -> None:
    # This gets returned to capabilities requester
    capId=createPassword(32)
    capAccept = {
        "id": httpPrefix+"://"+domain+"/caps/"+capId,
        "type": "Capability",
        "capability": acceptedCaps,
        "scope": acceptedActor,
        "actor": httpPrefix+"://"+domain
    }
    if nickname:
        capAccept['actor']=httpPrefix+"://"+domain+'/users/'+nickname
    #TODO

def isCapable(actor: str,capsJson: [],capability: str) -> bool:
    # is the given actor capable of using the current resource?
    for cap in capsJson:
        if cap['scope'] in actor:
            if capability in cap['capability']:
                return True
    return False
