__filename__ = "capabilities.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from auth import createPassword

def sendCapabilitiesRequest(baseDir: str,httpPrefix: str,requestedDomain: str,nickname=None) -> None:
    # This is sent to the capabilities endpoint /caps/new
    # which could be instance wide or for a particular person
    capId=createPassword(32)
    capRequest = {
        "id": httpPrefix+"://"+requestedDomain+"/caps/request/"+capId,
        "type": "Request",
        "capability": {
            "inbox": "write",
            "objects": "read"
        },
        "actor": httpPrefix+"://"+requestedDomain
    }
    # requesting for a particular person
    if nickname:
        # does the account exist for this person?
        if os.path.isdir(baseDir+'/accounts/'+nickname+'@'+requestedDomain):
            capRequest['scope']=httpPrefix+"://"+requestedDomain+'/users/'+nickname
    #TODO

def sendCapabilitiesAccept(baseDir: str,httpPrefix: str,domain: str,acceptedDomain: str,nickname=None) -> None:
    # This gets returned to capabilities requester
    capId=createPassword(32)
    capAccept = {
        "id": httpPrefix+"://"+domain+"/caps/"+capId,
        "type": "Capability",
        "capability": {
            "inbox": "write",
            "objects": "read"
        },
        "scope": httpPrefix+"://"+acceptedDomain,
        "actor": httpPrefix+"://"+domain
    }

    # accepting for a particular person
    if nickname:
        # does the account exist for this person?
        if os.path.isdir(baseDir+'/accounts/'+nickname+'@'+acceptedDomain):
            capAccept['scope']=httpPrefix+"://"+acceptedDomain+'/users/'+nickname
    #TODO

def isCapable(actor: str,capsJson: []) -> bool:
    # is the given actor capable of using the current resource?
    for cap in capsJson:
        if cap['scope'] in actor:
            return True
    return False
