__filename__ = "announce.py"
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

def createAnnounce(baseDir: str,username: str, domain: str, port: int,toUrl: str, ccUrl: str, https: bool, objectUrl: str, saveToFile: bool) -> {}:
    """Creates an announce message
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and the followers url
    objectUrl is typically the url of the message, corresponding to url or atomUri in createPostBase
    """
    prefix='https'
    if not https:
        prefix='http'

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    statusNumber,published = getStatusNumber()
    newAnnounceId=prefix+'://'+domain+'/users/'+username+'/statuses/'+statusNumber
    newAnnounce = {
        'actor': prefix+'://'+domain+'/users/'+username,
        'atomUri': prefix+'://'+domain+'/users/'+username+'/statuses/'+statusNumber,
        'cc': [],
        'id': newAnnounceId+'/activity',
        'object': objectUrl,
        'published': published,
        'to': [toUrl],
        'type': 'Announce'
    }
    if ccUrl:
        if len(ccUrl)>0:
            newAnnounce['cc']=ccUrl
    if saveToFile:
        if ':' in domain:
            domain=domain.split(':')[0]
        outboxDir = createOutboxDir(username,domain,baseDir)
        filename=outboxDir+'/'+newAnnounceId.replace('/','#')+'.json'
        with open(filename, 'w') as fp:
            commentjson.dump(newAnnounce, fp, indent=4, sort_keys=False)
    return newAnnounce

def announcePublic(baseDir: str,username: str, domain: str, port: int, https: bool, objectUrl: str, saveToFile: bool) -> {}:
    """Makes a public announcement
    """
    prefix='https'
    if not https:
        prefix='http'

    fromDomain=domain
    if port!=80 and port!=443:
        fromDomain=fromDomain+':'+str(port)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = prefix + '://'+fromDomain+'/users/'+username+'/followers'
    return createAnnounce(baseDir,username, domain, port,toUrl, ccUrl, https, objectUrl, saveToFile)

