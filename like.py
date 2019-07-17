__filename__ = "like.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
from pprint import pprint
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from posts import sendSignedJson
from session import postJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox

def undoLikesCollectionEntry(postFilename: str,objectUrl: str, actor: str,debug: bool) -> None:
    """Undoes a like for a particular actor
    """
    with open(postFilename, 'r') as fp:
        postJsonObject=commentjson.load(fp)
        if not postJsonObject.get('type'):
            if postJsonObject['type']!='Create':
                return
            return
        if not postJsonObject.get('object'):
            if debug:
                pprint(postJsonObject)
                print('DEBUG: post '+objectUrl+' has no object')
            return
        if not postJsonObject['object'].get('likes'):
            return
        if not postJsonObject['object']['likes'].get('items'):
            return
        totalItems=0
        if postJsonObject['object']['likes'].get('totalItems'):
            totalItems=postJsonObject['object']['likes']['totalItems']
        itemFound=False
        for likeItem in postJsonObject['object']['likes']['items']:
            if likeItem.get('actor'):
                if likeItem['actor']==actor:
                    if debug:
                        print('DEBUG: like was removed for '+actor)
                    postJsonObject['object']['likes']['items'].remove(likeItem)
                    itemFound=True
                    break
        if itemFound:
            if totalItems==1:
                if debug:
                    print('DEBUG: likes was removed from post')
                postJsonObject['object'].remove(postJsonObject['object']['likes'])
            else:
                postJsonObject['object']['likes']['totalItems']=len(postJsonObject['likes']['items'])
            with open(postFilename, 'w') as fp:
                commentjson.dump(postJsonObject, fp, indent=4, sort_keys=True)            

def updateLikesCollection(postFilename: str,objectUrl: str, actor: str,debug: bool) -> None:
    """Updates the likes collection within a post
    """
    with open(postFilename, 'r') as fp:
        postJsonObject=commentjson.load(fp)
        if not postJsonObject.get('object'):
            if debug:
                pprint(postJsonObject)
                print('DEBUG: post '+objectUrl+' has no object')
            return
        if not objectUrl.endswith('/likes'):
            objectUrl=objectUrl+'/likes'
        if not postJsonObject['object'].get('likes'):
            if debug:
                print('DEBUG: Adding initial likes to '+objectUrl)
            likesJson = {
                'id': objectUrl,
                'type': 'Collection',
                "totalItems": 1,
                'items': [{
                    'type': 'Like',
                    'actor': actor
                    
                }]                
            }
            postJsonObject['object']['likes']=likesJson
        else:
            if postJsonObject['object']['likes'].get('items'):
                for likeItem in postJsonObject['likes']['items']:
                    if likeItem.get('actor'):
                        if likeItem['actor']==actor:
                            return
                newLike={
                    'type': 'Like',
                    'actor': actor
                }
                postJsonObject['object']['likes']['items'].append(newLike)
                postJsonObject['object']['likes']['totalItems']=len(postJsonObject['likes']['items'])
            else:
                if debug:
                    print('DEBUG: likes section of post has no items list')

        if debug:
            print('DEBUG: saving post with likes added')
        with open(postFilename, 'w') as fp:
            commentjson.dump(postJsonObject, fp, indent=4, sort_keys=True)

def like(session,baseDir: str,federationList: [],nickname: str,domain: str,port: int, \
         ccList: [],httpPrefix: str,objectUrl: str,clientToServer: bool, \
         sendThreads: [],postLog: [],personCache: {},cachedWebfingers: {}, \
         debug: bool) -> {}:
    """Creates a like
    actor is the person doing the liking
    'to' might be a specific person (actor) whose post was liked
    object is typically the url of the message which was liked
    """
    if not urlPermitted(objectUrl,federationList,"inbox:write"):
        return None

    fullDomain=domain
    if port!=80 and port!=443:
        if ':' not in domain:
            fullDomain=domain+':'+str(port)

    newLikeJson = {
        'type': 'Like',
        'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
        'object': objectUrl,
        'to': [httpPrefix+'://'+fullDomain+'/users/'+nickname+'/followers'],
        'cc': []
    }
    if ccList:
        if len(ccList)>0:
            newLikeJson['cc']=ccList

    # Extract the domain and nickname from a statuses link
    likedPostNickname=None
    likedPostDomain=None
    likedPostPort=None
    if '/users/' in objectUrl:
        likedPostNickname=getNicknameFromActor(objectUrl)
        likedPostDomain,likedPostPort=getDomainFromActor(objectUrl)

    if likedPostNickname:
        postFilename=locatePost(baseDir,nickname,domain,objectUrl)
        if not postFilename:
            return None
        
        updateLikesCollection(postFilename,objectUrl,newLikeJson['actor'],debug)
        
        sendSignedJson(newLikeJson,session,baseDir, \
                       nickname,domain,port, \
                       likedPostNickname,likedPostDomain,likedPostPort, \
                       'https://www.w3.org/ns/activitystreams#Public', \
                       httpPrefix,True,clientToServer,federationList, \
                       sendThreads,postLog,cachedWebfingers,personCache,debug)

    return newLikeJson

def likePost(session,baseDir: str,federationList: [], \
             nickname: str,domain: str,port: int,httpPrefix: str, \
             likeNickname: str,likeDomain: str,likePort: int, \
             ccList: [], \
             likeStatusNumber: int,clientToServer: bool, \
             sendThreads: [],postLog: [], \
             personCache: {},cachedWebfingers: {}, \
             debug: bool) -> {}:
    """Likes a given status post
    """
    likeDomain=likeDomain
    if likePort!=80 and likePort!=443:
        likeDomain=likeDomain+':'+str(likePort)

    objectUrl = \
        httpPrefix + '://'+likeDomain+'/users/'+likeNickname+ \
        '/statuses/'+str(likeStatusNumber)

    if likePort!=80 and likePort!=443:
        ccUrl=httpPrefix+'://'+likeDomain+':'+str(likePort)+'/users/'+likeNickname
    else:
        ccUrl=httpPrefix+'://'+likeDomain+'/users/'+likeNickname
        
    return like(session,baseDir,federationList,nickname,domain,port, \
                ccList,httpPrefix,objectUrl,clientToServer, \
                sendThreads,postLog,personCache,cachedWebfingers,debug)

def undolike(session,baseDir: str,federationList: [],nickname: str,domain: str,port: int, \
             ccList: [],httpPrefix: str,objectUrl: str,clientToServer: bool, \
             sendThreads: [],postLog: [],personCache: {},cachedWebfingers: {}, \
             debug: bool) -> {}:
    """Removes a like
    actor is the person doing the liking
    'to' might be a specific person (actor) whose post was liked
    object is typically the url of the message which was liked
    """
    if not urlPermitted(objectUrl,federationList,"inbox:write"):
        return None

    fullDomain=domain
    if port!=80 and port!=443:
        if ':' not in domain:
            fullDomain=domain+':'+str(port)

    newUndoLikeJson = {
        'type': 'Undo',
        'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
        'object': {
            'type': 'Like',
            'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
            'object': objectUrl,
            'to': [httpPrefix+'://'+fullDomain+'/users/'+nickname+'/followers'],
            'cc': []
        },
        'to': [httpPrefix+'://'+fullDomain+'/users/'+nickname+'/followers'],
        'cc': []
    }
    if ccList:
        if len(ccList)>0:
            newUndoLikeJson['cc']=ccList
            newUndoLikeJson['object']['cc']=ccList

    # Extract the domain and nickname from a statuses link
    likedPostNickname=None
    likedPostDomain=None
    likedPostPort=None
    if '/users/' in objectUrl:
        likedPostNickname=getNicknameFromActor(objectUrl)
        likedPostDomain,likedPostPort=getDomainFromActor(objectUrl)

    if likedPostNickname:
        postFilename=locatePost(baseDir,nickname,domain,objectUrl)
        if not postFilename:
            return None

        undoLikesCollectionEntry(postFilename,objectUrl,newLikeJson['actor'],debug)
        
        sendSignedJson(newUndoLikeJson,session,baseDir, \
                       nickname,domain,port, \
                       likedPostNickname,likedPostDomain,likedPostPort, \
                       'https://www.w3.org/ns/activitystreams#Public', \
                       httpPrefix,True,clientToServer,federationList, \
                       sendThreads,postLog,cachedWebfingers,personCache,debug)
    else:
        return None

    return newUndoLikeJson

def undoLikePost(session,baseDir: str,federationList: [], \
                 nickname: str,domain: str,port: int,httpPrefix: str, \
                 likeNickname: str,likeDomain: str,likePort: int, \
                 ccList: [], \
                 likeStatusNumber: int,clientToServer: bool, \
                 sendThreads: [],postLog: [], \
                 personCache: {},cachedWebfingers: {}, \
                 debug: bool) -> {}:
    """Removes a liked post
    """
    likeDomain=likeDomain
    if likePort!=80 and likePort!=443:
        likeDomain=likeDomain+':'+str(likePort)

    objectUrl = \
        httpPrefix + '://'+likeDomain+'/users/'+likeNickname+ \
        '/statuses/'+str(likeStatusNumber)

    if likePort!=80 and likePort!=443:
        ccUrl=httpPrefix+'://'+likeDomain+':'+str(likePort)+'/users/'+likeNickname
    else:
        ccUrl=httpPrefix+'://'+likeDomain+'/users/'+likeNickname
        
    return undoLike(session,baseDir,federationList,nickname,domain,port, \
                    ccList,httpPrefix,objectUrl,clientToServer, \
                    sendThreads,postLog,personCache,cachedWebfingers,debug)

def sendLikeViaServer(session,fromNickname: str,password: str,
                      fromDomain: str,fromPort: int, \
                      httpPrefix: str,likeUrl: str, \
                      cachedWebfingers: {},personCache: {}, \
                      debug: bool) -> {}:
    """Creates a like via c2s
    """
    if not session:
        print('WARN: No session for sendLikeViaServer')
        return 6

    fromDomainFull=fromDomain
    if fromPort!=80 and fromPort!=443:
        fromDomainFull=fromDomain+':'+str(fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomainFull+'/users/'+fromNickname+'/followers'

    newLikeJson = {
        'type': 'Like',
        'actor': httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname,
        'object': likeUrl,
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle=httpPrefix+'://'+fromDomainFull+'/@'+fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition = \
        getPersonBox(session,wfRequest,personCache,postToBox)
                     
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
        postJson(session,newLikeJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST like success')

    return newLikeJson

def sendUndoLikeViaServer(session,fromNickname: str,password: str,
                          fromDomain: str,fromPort: int, \
                          httpPrefix: str,likeUrl: str, \
                          cachedWebfingers: {},personCache: {}, \
                          debug: bool) -> {}:
    """Undo a like via c2s
    """
    if not session:
        print('WARN: No session for sendUndoLikeViaServer')
        return 6

    fromDomainFull=fromDomain
    if fromPort!=80 and fromPort!=443:
        fromDomainFull=fromDomain+':'+str(fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomainFull+'/users/'+fromNickname+'/followers'

    newUndoLikeJson = {
        'type': 'Undo',
        'actor': httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname,
        'object': {
            'type': 'Like',
            'actor': httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname,
            'object': likeUrl,
            'to': [toUrl],
            'cc': [ccUrl]
        }
    }

    handle=httpPrefix+'://'+fromDomainFull+'/@'+fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition = \
        getPersonBox(session,wfRequest,personCache,postToBox)
                     
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
        postJson(session,newUndoLikeJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST undo like success')

    return newUndoLikeJson

def outboxLike(baseDir: str,httpPrefix: str, \
               nickname: str,domain: str,port: int, \
               messageJson: {},debug: bool) -> None:
    """ When a like request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: like - no type')
        return
    if not messageJson['type']=='Like':
        if debug:
            print('DEBUG: not a like')
        return
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in like')
        return
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: like object is not string')
        return
    if debug:
        print('DEBUG: c2s like request arrived in outbox')

    messageId=messageJson['object'].replace('/activity','')
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s like object is not a status')
        return
    if '/users/' not in messageId:
        if debug:
            print('DEBUG: c2s like object has no nickname')
        return
    likeNickname=getNicknameFromActor(messageId)
    likeDomain,likePort=getDomainFromActor(messageId)
    if ':' in domain:
        domain=domain.split(':')[0]
    postFilename=locatePost(baseDir,likeNickname,likeDomain,messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s like post not found in inbox or outbox')
            print(messageId)
        return True
    updateLikesCollection(postFilename,messageId,messageJson['actor'],debug)
    if debug:
        print('DEBUG: post liked via c2s - '+postFilename)
