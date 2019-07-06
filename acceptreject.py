__filename__ = "acceptreject.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
from utils import getStatusNumber
from utils import createOutboxDir
from utils import urlPermitted

def createAcceptReject(baseDir: str,federationList: [],capsList: [],nickname: str,domain: str,port: int,toUrl: str,ccUrl: str,httpPrefix: str,objectUrl: str,acceptType: str) -> {}:
    """Accepts or rejects something (eg. a follow request)
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and the followers url
    objectUrl is typically the url of the message, corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl,federationList,capsList,"inbox:write"):
        return None

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    newAccept = {
        'type': acceptType,
        'actor': httpPrefix+'://'+domain+'/users/'+nickname,
        'to': [toUrl],
        'cc': [],
        'object': objectUrl
    }
    if ccUrl:
        if len(ccUrl)>0:
            newAccept['cc']=ccUrl
    return newAccept

def createAccept(baseDir: str,federationList: [],capsList: [],nickname: str,domain: str,port: int,toUrl: str,ccUrl: str,httpPrefix: str,objectUrl: str) -> {}:
    return createAcceptReject(baseDir,federationList,capsList,nickname,domain,port,toUrl,ccUrl,httpPrefix,objectUrl,'Accept')

def createReject(baseDir: str,federationList: [],capsList: [],nickname: str,domain: str,port: int,toUrl: str,ccUrl: str,httpPrefix: str,objectUrl: str) -> {}:
    return createAcceptReject(baseDir,federationList,capsList,nickname,domain,port,toUrl,ccUrl,httpPrefix,objectUrl,'Reject')
