__filename__ = "inbox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import os
import datetime
import time
import json
import commentjson
from utils import urlPermitted
from utils import createInboxQueueDir
from posts import getPersonPubKey
from httpsig import verifyPostHeaders
from session import createSession
from follow import receiveFollowRequest

def inboxMessageHasParams(messageJson: {}) -> bool:
    """Checks whether an incoming message contains expected parameters
    """
    expectedParams=['type','to','actor','object']
    for param in expectedParams:
        if not messageJson.get(param):
            return False
    return True

def inboxPermittedMessage(domain: str,messageJson: {},federationList: []) -> bool:
    """ check that we are receiving from a permitted domain
    """
    testParam='actor'
    if not messageJson.get(testParam):
        return False
    actor=messageJson[testParam]
    # always allow the local domain
    if domain in actor:
        return True

    if not urlPermitted(actor,federationList):
        return False

    if messageJson.get('object'):
        if messageJson['object'].get('inReplyTo'):
            inReplyTo=messageJson['object']['inReplyTo']
            if not urlPermitted(inReplyTo, federationList):
                return False

    return True

def validPublishedDate(published) -> bool:
    currTime=datetime.datetime.utcnow()
    pubDate=datetime.datetime.strptime(published,"%Y-%m-%dT%H:%M:%SZ")
    daysSincePublished = (currTime - pubTime).days
    if daysSincePublished>30:
        return False
    return True

def savePostToInboxQueue(baseDir: str,httpPrefix: str,keyId: str,nickname: str, domain: str,postJson: {},headers: {}) -> str:
    """Saves the give json to the inbox queue for the person
    keyId specifies the actor sending the post
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    if not keyId:
        return None
    if not postJson.get('id'):
        return None
    postId=postJson['id'].replace('/activity','')

    currTime=datetime.datetime.utcnow()
    published=currTime.strftime("%Y-%m-%dT%H:%M:%SZ")

    inboxQueueDir = createInboxQueueDir(nickname,domain,baseDir)

    handle=nickname+'@'+domain
    destination=baseDir+'/accounts/'+handle+'/inbox/'+postId.replace('/','#')+'.json'
    if os.path.isfile(destination):
        # inbox item already exists
        return None
    filename=inboxQueueDir+'/'+postId.replace('/','#')+'.json'

    newBufferItem = {
        'published': published,
        'keyId': keyid,
        'headers': headers,
        'post': postJson,
        'filename': filename,
        'destination': destination
    }
    
    with open(filename, 'w') as fp:
        commentjson.dump(newQueueItem, fp, indent=4, sort_keys=False)
    return filename

def runInboxQueue(baseDir: str,httpPrefix: str,personCache: {},queue: [],domain: str,port: int,useTor: bool,federationList: [],debug: bool) -> None:
    """Processes received items and moves them to
    the appropriate directories
    """
    currSessionTime=int(time.time())
    sessionLastUpdate=currSessionTime
    session=createSession(domain,port,useTor)
    if debug:
        print('DEBUG: Inbox queue running')

    while True:
        if len(queue)>0:
            currSessionTime=int(time.time())
            if currSessionTime-sessionLastUpdate>1200:
                session=createSession(domain,port,useTor)
                sessionLastUpdate=currSessionTime

            # oldest item first
            queue.sort()
            queueFilename=queue[0]
            if not os.path.isfile(queueFilename):
                if debug:
                    print("DEBUG: queue item rejected becase it has no file: "+queueFilename)
                queue.pop(0)
                continue

            # Load the queue json
            with open(queueFilename, 'r') as fp:
                queueJson=commentjson.load(fp)

            # Try a few times to obtain teh public key
            pubKey=None
            for tries in range(5):
                pubKey=getPersonPubKey(session,queueJson['keyId'],personCache)
                if not pubKey:
                    if debug:
                        print('DEBUG: Retry '+str(tries+1)+' obtaining public key for '+queueJson['keyId'])
                    time.sleep(5)
            if not pubKey:
                if debug:
                    print('DEBUG: public key could not be obtained from '+queueJson['keyId'])
                os.remove(queueFilename)
                queue.pop(0)
                continue

            # check the signature
            if not verifyPostHeaders(httpPrefix, \
                                     pubKey, queueJson.headers, \
                                     '/inbox', False, \
                                     json.dumps(messageJson)):
                if debug:
                    print('DEBUG: Header signature check failed')
                os.remove(queueFilename)
                queue.pop(0)
                continue

            if receiveFollowRequest(baseDir, \
                                    queueJson.post, \
                                    federationList):
            
                if debug:
                    print('DEBUG: Follow accepted from '+queueJson['keyId'])
                    os.remove(queueFilename)
                    queue.pop(0)
                    continue
                    
            if debug:
                print('DEBUG: Queue post accepted')
            # move to the destination inbox
            os.rename(queueFilename,queueJson['destination'])
            queue.pop(0)
        time.sleep(2)
