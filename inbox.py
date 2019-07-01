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

def inboxPermittedMessage(messageJson: {},federationList: []) -> bool:
    """ check that we are receiving from a permitted domain
    """
    testParam='actor'
    if not messageJson.get(testParam):
        return False
    actor=messageJson[testParam]
    # always allow the local domain
    if thisDomain in actor:
        return True

    permittedDomain=False
    for domain in federationList:
        if domain in actor:
            permittedDomain=True
            break
    if not permittedDomain:
        return False

    if messageJson.get('object'):
        if messageJson['object'].get('inReplyTo'):
            inReplyTo=messageJson['object']['inReplyTo']
            permittedReplyDomain=False
            for domain in federationList:
                if domain in inReplyTo:
                    permittedReplyDomain=True
                    break
            if not permittedReplyDomain:
                return False

    return True

def receivePublicMessage(message: {}) -> bool:
    print("TODO")

def validPublishedDate(published):
    currTime=datetime.datetime.utcnow()
    pubDate=datetime.datetime.strptime(published,"%Y-%m-%dT%H:%M:%SZ")
    daysSincePublished = (currTime - pubTime).days
    if daysSincePublished>30:
        return False
    return True

def receiveMessage(message: {},baseDir: str):
    if not message.get('type'):
        return
    if message['type']!='Create':
        return
    if not message.get('published'):
        return
    # is the message too old?
    if not validPublishedDate(message['published']):
        return
    if not message.get('to'):
        return
    if not message.get('id'):
        return
    for recipient in message['to']:
        if recipient.endswith('/activitystreams#Public'):
            receivePublicMessage(message)
            continue
        
        username=''
        domain=''
        messageId=message['id'].replace('/','_')
        handle=username.lower()+'@'+domain.lower()
        if not os.path.isdir(baseDir+'/accounts/'+handle):
            os.mkdir(baseDir+'/accounts/'+handle)
        if not os.path.isdir(baseDir+'/accounts/'+handle+'/inbox'):
            os.mkdir(baseDir+'/accounts/'+handle+'/inbox')
            filename=baseDir+'/accounts/'+handle+'/inbox/'+messageId+'.json'
            with open(filename, 'w') as fp:
                commentjson.dump(personJson, fp, indent=4, sort_keys=False)
