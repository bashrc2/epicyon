__filename__ = "delete.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import json
import commentjson
from utils import getStatusNumber
from utils import createOutboxDir
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import deletePost
from utils import removeModerationPostFromIndex
from posts import sendSignedJson
from session import postJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox

def createDelete(session,baseDir: str,federationList: [], \
                 nickname: str, domain: str, port: int, \
                 toUrl: str, ccUrl: str, httpPrefix: str, \
                 objectUrl: str,clientToServer: bool, \
                 sendThreads: [],postLog: [], \
                 personCache: {},cachedWebfingers: {}, \
                 debug: bool) -> {}:
    """Creates a delete message
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person whose post is to be deleted
    objectUrl is typically the url of the message, corresponding to url
    or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl,federationList,"inbox:write"):
        return None

    if ':' in domain:
        domain=domain.split(':')[0]
        fullDomain=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fullDomain=domain+':'+str(port)

    statusNumber,published = getStatusNumber()
    newDeleteId= \
        httpPrefix+'://'+fullDomain+'/users/'+nickname+'/statuses/'+statusNumber
    newDelete = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
        'atomUri': httpPrefix+'://'+fullDomain+'/users/'+nickname+'/statuses/'+statusNumber,
        'cc': [],
        'id': newDeleteId+'/activity',
        'object': objectUrl,
        'published': published,
        'to': [toUrl],
        'type': 'Delete'
    }
    if ccUrl:
        if len(ccUrl)>0:
            newDelete['cc']=[ccUrl]

    deleteNickname=None
    deleteDomain=None
    deletePort=None
    if '/users/' in objectUrl or '/profile/' in objectUrl:
        deleteNickname=getNicknameFromActor(objectUrl)
        deleteDomain,deletePort=getDomainFromActor(objectUrl)

    if deleteNickname and deleteDomain:
        sendSignedJson(newDelete,session,baseDir, \
                       nickname,domain,port, \
                       deleteNickname,deleteDomain,deletePort, \
                       'https://www.w3.org/ns/activitystreams#Public', \
                       httpPrefix,True,clientToServer,federationList, \
                       sendThreads,postLog,cachedWebfingers,personCache,debug)
        
    return newDelete

def sendDeleteViaServer(baseDir: str,session, \
                        fromNickname: str,password: str, \
                        fromDomain: str,fromPort: int, \
                        httpPrefix: str,deleteObjectUrl: str, \
                        cachedWebfingers: {},personCache: {}, \
                        debug: bool,projectVersion: str) -> {}:
    """Creates a delete request message via c2s
    """
    if not session:
        print('WARN: No session for sendDeleteViaServer')
        return 6

    fromDomainFull=fromDomain
    if fromPort:
        if fromPort!=80 and fromPort!=443:
            if ':' not in fromDomain:
                fromDomainFull=fromDomain+':'+str(fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomainFull+'/users/'+fromNickname+'/followers'

    newDeleteJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname,
        'cc': [ccUrl],
        'object': deleteObjectUrl,
        'to': [toUrl],
        'type': 'Delete'
    }

    handle=httpPrefix+'://'+fromDomainFull+'/@'+fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                                fromDomain,projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl,displayName = \
        getPersonBox(baseDir,session,wfRequest,personCache, \
                     projectVersion,httpPrefix,fromDomain,postToBox)
                     
    if not inboxUrl:
        if debug:
            print('DEBUG: No '+postToBox+' was found for '+handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for '+handle)
        return 4
    
    authHeader=createBasicAuthHeader(fromNickname,password)
     
    headers = {'host': fromDomain, \
               'Content-type': 'application/json', \
               'Authorization': authHeader}
    postResult = \
        postJson(session,newDeleteJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST delete request success')

    return newDeleteJson

def deletePublic(session,baseDir: str,federationList: [], \
                 nickname: str, domain: str, port: int, httpPrefix: str, \
                 objectUrl: str,clientToServer: bool, \
                 sendThreads: [],postLog: [], \
                 personCache: {},cachedWebfingers: {}, \
                 debug: bool) -> {}:
    """Makes a public delete activity
    """
    fromDomain=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fromDomain=domain+':'+str(port)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomain+'/users/'+nickname+'/followers'
    return createDelete(session,baseDir,federationList, \
                        nickname,domain,port, \
                        toUrl,ccUrl,httpPrefix, \
                        objectUrl,clientToServer, \
                        sendThreads,postLog, \
                        personCache,cachedWebfingers, \
                        debug)

def deletePostPub(session,baseDir: str,federationList: [], \
                  nickname: str, domain: str, port: int, httpPrefix: str, \
                  deleteNickname: str, deleteDomain: str, \
                  deletePort: int, deleteHttpsPrefix: str, \
                  deleteStatusNumber: int,clientToServer: bool, \
                  sendThreads: [],postLog: [], \
                  personCache: {},cachedWebfingers: {}, \
                  debug: bool) -> {}:
    """Deletes a given status post
    """
    deletedDomain=deleteDomain
    if deletePort:
        if deletePort!=80 and deletePort!=443:
            if ':' not in deletedDomain:
                deletedDomain=deletedDomain+':'+str(deletePort)

    objectUrl = deleteHttpsPrefix + '://'+deletedDomain+'/users/'+ \
        deleteNickname+'/statuses/'+str(deleteStatusNumber)

    return deletePublic(session,baseDir,federationList, \
                        nickname,domain,port,httpPrefix, \
                        objectUrl,clientToServer, \
                        sendThreads,postLog, \
                        personCache,cachedWebfingers, \
                        debug)

def outboxDelete(baseDir: str,httpPrefix: str, \
                 nickname: str,domain: str, \
                 messageJson: {},debug: bool,
                 allowDeletion: bool) -> None:
    """ When a delete request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: delete - no type')
        return
    if not messageJson['type']=='Delete':
        if debug:
            print('DEBUG: not a delete')
        return
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in delete')
        return
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: delete object is not string')
        return
    if debug:
        print('DEBUG: c2s delete request arrived in outbox')
    deletePrefix=httpPrefix+'://'+domain
    if not allowDeletion and \
       (not messageJson['object'].startswith(deletePrefix) or \
        not messageJson['actor'].startswith(deletePrefix)):
        if debug:
            print('DEBUG: delete not permitted from other instances')
        return
    messageId=messageJson['object'].replace('/activity','')
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s delete object is not a status')
        return
    if '/users/' not in messageId:
        if debug:
            print('DEBUG: c2s delete object has no nickname')
        return
    deleteNickname=getNicknameFromActor(messageId)
    if deleteNickname!=nickname:
        if debug:
            print("DEBUG: you can't delete a post which wasn't created by you (nickname does not match)")
        return        
    deleteDomain,deletePort=getDomainFromActor(messageId)
    if ':' in domain:
        domain=domain.split(':')[0]
    if deleteDomain!=domain:
        if debug:
            print("DEBUG: you can't delete a post which wasn't created by you (domain does not match)")
        return        
    removeModerationPostFromIndex(baseDir,messageId,debug)
    postFilename=locatePost(baseDir,deleteNickname,deleteDomain,messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s delete post not found in inbox or outbox')
            print(messageId)
        return True
    deletePost(baseDir,httpPrefix,deleteNickname,deleteDomain,postFilename,debug)
    if debug:
        print('DEBUG: post deleted via c2s - '+postFilename)
