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
from utils import urlPermitted
from utils import createInboxQueueDir

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

def savePostToInboxQueue(baseDir: str,httpPrefix: str,keyId: str,nickname: str, domain: str,postJson: {}) -> str:
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
    newBufferItem = {
        'published': published,
        'keyId': keyid,
        'post': postJson
    }
    
    inboxQueueDir = createInboxQueueDir(nickname,domain,baseDir)
    filename=inboxQueueDir+'/'+postId.replace('/','#')+'.json'
    with open(filename, 'w') as fp:
        commentjson.dump(newQueueItem, fp, indent=4, sort_keys=False)
    return filename
