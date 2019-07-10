__filename__ = "like.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor

def like(session,baseDir: str,federationList: [],nickname: str,domain: str,port: int, \
         ccUrl: str,httpPrefix: str,objectUrl: str,clientToServer: bool, \
         sendThreads: [],postLog: [],personCache: {},cachedWebfingers: {}) -> {}:
    """Creates a like
    ccUrl might be a specific person whose post was liked
    objectUrl is typically the url of the message, corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl,federationList,"inbox:write"):
        return None

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    newLikeJson = {
        'type': 'Like',
        'actor': httpPrefix+'://'+domain+'/users/'+nickname,
        'object': objectUrl,
        'to': [httpPrefix+'://'+domain+'/users/'+nickname+'/followers'],
        'cc': []
    }
    if ccUrl:
        if len(ccUrl)>0:
            newLikeJson['cc']=ccUrl

    # Extract the domain and nickname from a statuses link
    likedPostNickname=None
    likedPostDomain=None
    likedPostPort=None
    if '/users/' in objectUrl:
        likedPostNickname=getNicknameFromActor(objectUrl)
        likedPostDomain,likedPostPort=getDomainFromActor(objectUrl)

    if likedPostNickname:
        sendSignedJson(newlikeJson,session,baseDir, \
                       nickname,domain,port, \
                       likedPostNickname,likedPostDomain,likedPostPort, \
                       'https://www.w3.org/ns/activitystreams#Public', \
                       httpPrefix,True,clientToServer,federationList, \
                       sendThreads,postLog,cachedWebfingers,personCache,debug)

    return newLikeJson

def likePost(session,baseDir: str,federationList: [], \
             nickname: str, domain: str, port: int, httpPrefix: str, \
             likeNickname: str, likeDomain: str, likePort: int, \
             likeHttps: bool, likeStatusNumber: int, \
             clientToServer: bool,sendThreads: [],postLog: [], \
             personCache: {},cachedWebfingers: {}) -> {}:
    """Likes a given status post
    """
    likeDomain=likeDomain
    if likePort!=80 and likePort!=443:
        likeDomain=likeDomain+':'+str(likePort)

    objectUrl = \
        httpPrefix + '://'+likeDomain+'/users/'+likeNickname+ \
        '/statuses/'+str(likeStatusNumber)

    return like(session,baseDir,federationList,nickname,domain,port, \
                ccUrl,httpPrefix,objectUrl,clientToServer, \
                sendThreads,postLog,personCache,cachedWebfingers)

def updateLikesCollection(postFilename: str,objectUrl: str, actor: str) -> None:
    """Updates the likes collection within a post
    """
    with open(postFilename, 'r') as fp:
        postJson=commentjson.load(fp)
        if not objectUrl.endswith('/likes'):
            objectUrl=objectUrl+'/likes'
        if not postJson.get('likes'):
            likesJson = {
                'id': objectUrl,
                'type': 'Collection',
                "totalItems": 1,
                'items': [actor]                
            }
            postJson['likes']=likesJson
        else:
            if postJson['likes'].get('items'):
                if actor not in postJson['likes']['items']:
                    postJson['likes']['items'].append(actor)
                postJson['likes']['totalItems']=len(postJson['likes']['items'])
        with open(postFilename, 'w') as fp:
            commentjson.dump(postJson, fp, indent=4, sort_keys=True)
