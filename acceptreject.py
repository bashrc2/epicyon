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
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import domainPermitted

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

def receiveAcceptReject(session,baseDir: str,httpPrefix: str,port: int,sendThreads: [],postLog: [],cachedWebfingers: {},personCache: {},messageJson: {},federationList: [],capsList: [],debug : bool) -> bool:
    """Receives an Accept or Reject within the POST section of HTTPServer
    """
    if messageJson['type']!='Accept' and messageJson['type']!='Reject':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no actor')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in '+messageJson['type'])
        return False
    domain,tempPort=getDomainFromActor(messageJson['actor'])
    if not domainPermitted(domain,federationList):
        if debug:
            print('DEBUG: '+messageJson['type']+' from domain not permitted - '+domain)
        return False
    nickname=getNicknameFromActor(messageJson['actor'])
    if not nickname:
        if debug:
            print('DEBUG: '+messageJson['type']+' does not contain a nickname')
        return False
    handle=nickname.lower()+'@'+domain.lower()
    if '/users/' not in messageJson['object']:
        if debug:
            print('DEBUG: "users" not found within object of '+messageJson['type'])
        return False
    if debug:
        print('DEBUG: Uh, '+messageJson['type']+', I guess')
    return True
