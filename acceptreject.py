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

def createAcceptReject(baseDir: str,federationList: [],username: str,domain: str,port: int,toUrl: str,ccUrl: str,https: bool,objectUrl: str,acceptType: str) -> {}:
    """Accepts or rejects something (eg. a follow request)
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and the followers url
    objectUrl is typically the url of the message, corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl,federationList):
        return None

    prefix='https'
    if not https:
        prefix='http'

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    newAccept = {
        'type': acceptType,
        'actor': prefix+'://'+domain+'/users/'+username,
        'to': [toUrl],
        'cc': [],
        'object': objectUrl
    }
    if ccUrl:
        if len(ccUrl)>0:
            newAccept['cc']=ccUrl
    return newAccept

def createAccept(baseDir: str,federationList: [],username: str,domain: str,port: int,toUrl: str,ccUrl: str,https: bool,objectUrl: str) -> {}:
    return createAcceptReject(baseDir,federationList,username,domain,port,toUrl,ccUrl,https,objectUrl,'Accept')

def createReject(baseDir: str,federationList: [],username: str,domain: str,port: int,toUrl: str,ccUrl: str,https: bool,objectUrl: str) -> {}:
    return createAcceptReject(baseDir,federationList,username,domain,port,toUrl,ccUrl,https,objectUrl,'Reject')
