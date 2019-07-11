__filename__ = "delete.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
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
from posts import sendSignedJson

def createDelete(session,baseDir: str,federationList: [], \
                 nickname: str, domain: str, port: int, \
                 toUrl: str, ccUrl: str, httpPrefix: str, \
                 objectUrl: str,clientToServer: bool, \
                 sendThreads: [],postLog: [], \
                 personCache: {},cachedWebfingers: {}, \
                 debug: bool) -> {}:
    """Creates an delete message
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
    if port!=80 and port!=443:
        fullDomain=domain+':'+str(port)

    statusNumber,published = getStatusNumber()
    newDeleteId= \
        httpPrefix+'://'+fullDomain+'/users/'+nickname+'/statuses/'+statusNumber
    newDelete = {
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
    if '/users/' in objectUrl:
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

def deletePublic(session,baseDir: str,federationList: [], \
                 nickname: str, domain: str, port: int, httpPrefix: str, \
                 objectUrl: str,clientToServer: bool, \
                 sendThreads: [],postLog: [], \
                 personCache: {},cachedWebfingers: {}, \
                 debug: bool) -> {}:
    """Makes a public delete activity
    """
    fromDomain=domain
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

def deletePost(session,baseDir: str,federationList: [], \
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

