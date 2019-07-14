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
