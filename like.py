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

def like(baseDir: str,federationList: [],nickname: str,domain: str,port: int, \
         toUrl: str,ccUrl: str,httpPrefix: str,objectUrl: str,saveToFile: bool) -> {}:
    """Creates a like
    Typically toUrl will be a followers collection
    and ccUrl might be a specific person whose post was liked
    objectUrl is typically the url of the message, corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl,federationList,capsList,"inbox:write"):
        return None

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    newLike = {
        'type': 'Like',
        'actor': httpPrefix+'://'+domain+'/users/'+nickname,
        'object': objectUrl,
        'to': [toUrl],
        'cc': []
    }
    if ccUrl:
        if len(ccUrl)>0:
            newLike['cc']=ccUrl
    if saveToFile:
        if ':' in domain:
            domain=domain.split(':')[0]
        # TODO update likes collection
    return newLike

def likePost(baseDir: str,federationList: [], \
             nickname: str, domain: str, port: int, httpPrefix: str, \n
             likeNickname: str, likeDomain: str, likePort: int, likeHttps: bool, \n
             likeStatusNumber: int,saveToFile: bool) -> {}:
    """Likes a given status post
    """
    likeDomain=likeDomain
    if likePort!=80 and likePort!=443:
        likeDomain=likeDomain+':'+str(likePort)

    objectUrl = httpPrefix + '://'+likeDomain+'/users/'+likeNickname+'/statuses/'+str(likeStatusNumber)

    return like(baseDir,federationList,nickname,domain,port,toUrl,ccUrl,httpPrefix,objectUrl,saveToFile)
