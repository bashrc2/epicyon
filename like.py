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

def like(baseDir: str,federationList: [],username: str,domain: str,port: int,toUrl: str,ccUrl: str,https: bool,objectUrl: str,saveToFile: bool) -> {}:
    """Creates a like
    Typically toUrl will be a followers collection
    and ccUrl might be a specific person whose post was liked
    objectUrl is typically the url of the message, corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl,federationList):
        return None

    prefix='https'
    if not https:
        prefix='http'

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    newLike = {
        'type': 'Like',
        'actor': prefix+'://'+domain+'/users/'+username,
        'object': objectUrl,
        'to': [toUrl],
        'cc': [],
        'published': published
    }
    if ccUrl:
        if len(ccUrl)>0:
            newLike['cc']=ccUrl
    if saveToFile:
        if ':' in domain:
            domain=domain.split(':')[0]
        # TODO update likes collection
    return newLike

def likePost(baseDir: str,federationList: [],username: str, domain: str, port: int, https: bool, likeUsername: str, likeDomain: str, likePort: int, likeStatusNumber: int, likeHttps: bool,saveToFile: bool) -> {}:
    """Likes a given status post
    """
    prefix='https'
    if not likeHttps:
        prefix='http'

    likeDomain=likeDomain
    if likePort!=80 and likePort!=443:
        likeDomain=likeDomain+':'+str(likePort)

    objectUrl = prefix + '://'+likeDomain+'/users/'+likeUsername+'/statuses/'+str(likeStatusNumber)

    return like(baseDir,federationList,username,domain,port,toUrl,ccUrl,https,objectUrl,saveToFile)
