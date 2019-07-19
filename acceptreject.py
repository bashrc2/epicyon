__filename__ = "acceptreject.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
from capabilities import capabilitiesAccept
from capabilities import capabilitiesGrantedSave
from utils import getStatusNumber
from utils import createOutboxDir
from utils import urlPermitted
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import domainPermitted
from utils import followPerson

def createAcceptReject(baseDir: str,federationList: [], \
                       nickname: str,domain: str,port: int, \
                       toUrl: str,ccUrl: str,httpPrefix: str, \
                       objectJson: {},ocapJson,acceptType: str) -> {}:
    """Accepts or rejects something (eg. a follow request or offer)
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and
    the followers url objectUrl is typically the url of the message,
    corresponding to url or atomUri in createPostBase
    """
    if not objectJson.get('actor'):
        return None

    if not urlPermitted(objectJson['actor'],federationList,"inbox:write"):
        return None

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    newAccept = {
        'type': acceptType,
        'actor': httpPrefix+'://'+domain+'/users/'+nickname,
        'to': [toUrl],
        'cc': [],
        'object': objectJson
    }
    if ccUrl:
        if len(ccUrl)>0:
            newAccept['cc']=[ccUrl]
    # attach capabilities for follow accept
    if ocapJson:
        newAccept['capabilities']=ocapJson
    return newAccept

def createAccept(baseDir: str,federationList: [], \
                 nickname: str,domain: str,port: int, \
                 toUrl: str,ccUrl: str,httpPrefix: str, \
                 objectJson: {},acceptedCaps=["inbox:write","objects:read"]) -> {}:
    # create capabilities accept
    ocapNew=capabilitiesAccept(baseDir,httpPrefix,nickname,domain,port,toUrl,True,acceptedCaps)
    return createAcceptReject(baseDir,federationList, \
                              nickname,domain,port, \
                              toUrl,ccUrl,httpPrefix, \
                              objectJson,ocapNew,'Accept')

def createReject(baseDir: str,federationList: [], \
                 nickname: str,domain: str,port: int, \
                 toUrl: str,ccUrl: str,httpPrefix: str, \
                 objectJson: {}) -> {}:
    return createAcceptReject(baseDir,federationList, \
                              nickname,domain,port, \
                              toUrl,ccUrl, \
                              httpPrefix,objectJson,None,'Reject')

def acceptFollow(baseDir: str,domain : str,messageJson: {}, \
                 federationList: [],debug : bool) -> None:
    if not messageJson.get('object'):
        return
    if not messageJson['object'].get('type'):
        return 
    if not messageJson['object'].get('actor'):
        return
    # no, this isn't a mistake
    if not messageJson['object'].get('object'):
        return 
    if not messageJson['object']['type']=='Follow':
        return
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: No "to" parameter in follow Accept')
        return
    if len(messageJson['object']['to'])!=1:
        if debug:
            print('DEBUG: "to" does not contain a single recipient')
            print(str(messageJson['object']['to']))
        return        
    if debug:
        print('DEBUG: follow Accept received')
    thisActor=messageJson['object']['actor']
    nickname=getNicknameFromActor(thisActor)
    acceptedDomain,acceptedPort=getDomainFromActor(thisActor)
    if not acceptedDomain:
        if debug:
            print('DEBUG: domain not found in '+thisActor)
        return
    #if acceptedDomain != domain:
    #    if debug:
    #        print('DEBUG: domain mismatch '+acceptedDomain+' != '+domain)
    #    return
    if not nickname:
        if debug:
            print('DEBUG: nickname not found in '+thisActor)        
        return
    if acceptedPort:
        if not '/'+acceptedDomain+':'+str(acceptedPort)+'/users/'+nickname in thisActor:
            if debug:
                print('Port: '+str(acceptedPort))
                print('Expected: /'+acceptedDomain+':'+str(acceptedPort)+'/users/'+nickname)
                print('Actual:   '+thisActor)
                print('DEBUG: unrecognized actor '+thisActor)
            return
    else:
        if not '/'+acceptedDomain+'/users/'+nickname in thisActor:
            if debug:
                print('Expected: /'+acceptedDomain+'/users/'+nickname)
                print('Actual:   '+thisActor)
                print('DEBUG: unrecognized actor '+thisActor)
            return    
    followedActor=messageJson['object']['object']
    followedDomain,port=getDomainFromActor(followedActor)
    if not followedDomain:
        return
    followedDomainFull=followedDomain
    if port:
        followedDomainFull=followedDomain+':'+str(port)
    followedNickname=getNicknameFromActor(followedActor)
    if not followedNickname:
        return

    acceptedDomainFull=acceptedDomain
    if acceptedPort:
        acceptedDomainFull=acceptedDomain+':'+str(acceptedPort)

    # are capabilities attached? If so then store them
    if messageJson.get('capabilities'):
        if isinstance(messageJson['capabilities'], dict):
            capabilitiesGrantedSave(baseDir, \
                                    nickname,acceptedDomainFull, \
                                    messageJson['capabilities'])

    if followPerson(baseDir, \
                    nickname,acceptedDomainFull, \
                    followedNickname,followedDomainFull, \
                    federationList,debug):
        if debug:
            print('DEBUG: '+nickname+'@'+acceptedDomainFull+' followed '+followedNickname+'@'+followedDomainFull)
    else:
        if debug:
            print('DEBUG: Unable to create follow - '+nickname+'@'+acceptedDomain+' -> '+followedNickname+'@'+followedDomain)

def receiveAcceptReject(session,baseDir: str, \
                        httpPrefix: str,domain :str,port: int, \
                        sendThreads: [],postLog: [],cachedWebfingers: {}, \
                        personCache: {},messageJson: {},federationList: [], \
                        debug : bool) -> bool:
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
    acceptFollow(baseDir,domain,messageJson,federationList,debug)
    if debug:
        print('DEBUG: Uh, '+messageJson['type']+', I guess')
    return True
