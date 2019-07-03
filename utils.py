__filename__ = "utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import datetime

def getStatusNumber() -> (str,str):
    """Returns the status number and published date
    """
    currTime=datetime.datetime.utcnow()
    daysSinceEpoch=(currTime - datetime.datetime(1970,1,1)).days
    # status is the number of seconds since epoch
    statusNumber=str(((daysSinceEpoch*24*60*60) + (currTime.hour*60*60) + (currTime.minute*60) + currTime.second)*1000000 + currTime.microsecond)
    published=currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    conversationDate=currTime.strftime("%Y-%m-%d")
    return statusNumber,published

def createOutboxDir(nickname: str,domain: str,baseDir: str) -> str:
    """Create an outbox for a person and returns the feed filename and directory
    """
    handle=nickname.lower()+'@'+domain.lower()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    outboxDir=baseDir+'/accounts/'+handle+'/outbox'
    if not os.path.isdir(outboxDir):
        os.mkdir(outboxDir)
    return outboxDir

def domainPermitted(domain: str, federationList: []):
    if len(federationList)==0:
        return True
    if domain in federationList:
        return True
    return False

def urlPermitted(url: str, federationList: []):
    if len(federationList)==0:
        return True
    for domain in federationList:
        if domain in url:
            return True
    return False
