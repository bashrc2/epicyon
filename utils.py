__filename__ = "utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import datetime
import commentjson

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

def createPersonDir(nickname: str,domain: str,baseDir: str,dirname: str) -> str:
    """Create a directory for a person
    """
    handle=nickname+'@'+domain
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    boxDir=baseDir+'/accounts/'+handle+'/'+dirname
    if not os.path.isdir(boxDir):
        os.mkdir(boxDir)
    return boxDir

def createOutboxDir(nickname: str,domain: str,baseDir: str) -> str:
    """Create an outbox for a person
    """
    return createPersonDir(nickname,domain,baseDir,'outbox')

def createInboxQueueDir(nickname: str,domain: str,baseDir: str) -> str:
    """Create an inbox queue and returns the feed filename and directory
    """
    return createPersonDir(nickname,domain,baseDir,'queue')

def domainPermitted(domain: str, federationList: []):
    if len(federationList)==0:
        return True
    if ':' in domain:
        domain=domain.split(':')[0]
    if domain in federationList:
        return True
    return False

def urlPermitted(url: str, federationList: [],capability: str):
    if url.endswith('gab.com') or url.endswith('gabfed.com'):
        return False
    if len(federationList)==0:
        return True
    for domain in federationList:
        if domain in url:
            return True
    return False

def getPreferredName(actor: str,personCache: {}) -> str:
    """Returns the preferred name for the given actor
    """
    if not personCache.get(actor):
        return None
    if personCache[actor].get('preferredUsername'):
        return personCache[actor]['preferredUsername']
    return None

def getNicknameFromActor(actor: str) -> str:
    """Returns the nickname from an actor url
    """
    if '/users/' not in actor:
        # https://domain/@nick
        if '/@' in actor:
            nickStr=actor.split('/@')[1]
            if '/' in nickStr:
                nickStr=nickStr.split('/')[0]
            return nickStr
        return None
    nickStr=actor.split('/users/')[1].replace('@','')
    if '/' not in nickStr:
        return nickStr
    else:
        return nickStr.split('/')[0]

def getDomainFromActor(actor: str) -> (str,int):
    """Returns the domain name from an actor url
    """
    port=None
    if '/users/' not in actor:
        domain = actor.replace('https://','').replace('http://','').replace('dat://','')
        if '/' in actor:
            domain=domain.split('/')[0]
    else:
        domain = actor.split('/users/')[0].replace('https://','').replace('http://','').replace('dat://','')
    if ':' in domain:
        port=int(domain.split(':')[1])
        domain=domain.split(':')[0]
    return domain,port
    
def followPerson(baseDir: str,nickname: str, domain: str, \
                 followNickname: str, followDomain: str, \
                 federationList: [],debug: bool, \
                 followFile='following.txt') -> bool:
    """Adds a person to the follow list
    """
    if not domainPermitted(followDomain.lower().replace('\n',''), \
                           federationList):
        if debug:
            print('DEBUG: follow of domain '+followDomain+' not permitted')
        return False
    if debug:
        print('DEBUG: follow of domain '+followDomain)

    if ':' in domain:
        handle=nickname+'@'+domain.split(':')[0].lower()
    else:
        handle=nickname+'@'+domain.lower()
        
    if ':' in followDomain:
        handleToFollow=followNickname+'@'+followDomain.split(':')[0].lower()
    else:
        handleToFollow=followNickname+'@'+followDomain.lower()
    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        if handleToFollow in open(filename).read():
            if debug:
                print('DEBUG: follow already exists')
            return True
        with open(filename, "a") as followfile:
            followfile.write(followNickname+'@'+followDomain+'\n')
            if debug:
                print('DEBUG: follow added')
            return True
    if debug:
        print('DEBUG: creating new following file')
    with open(filename, "w") as followfile:
        followfile.write(followNickname+'@'+followDomain+'\n')
    return True

def locatePost(baseDir: str,nickname: str,domain: str,postUrl: str,replies=False) -> str:
    """Returns the filename for the given status post url
    """
    if not replies:
        extension='json'
    else:
        extension='replies'
    # if this post in the shared inbox?
    handle='inbox@'+domain
    boxName='inbox'
    postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl.replace('/','#')+'.'+extension
    if not os.path.isfile(postFilename):
        boxName='outbox'
        postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl.replace('/','#')+'.'+extension
        if not os.path.isfile(postFilename):
            # if this post in the inbox of the person?
            boxName='inbox'
            postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl.replace('/','#')+'.'+extension
            if not os.path.isfile(postFilename):
                postFilename=None
    return postFilename

def removeAttachment(baseDir: str,httpPrefix: str,domain: str,postJson: {}):
    if not postJson.get('attachment'):
        return
    if not postJson['attachment'][0].get('url'):
        return
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)
    attachmentUrl=postJson['attachment'][0]['url']
    if not attachmentUrl:
        return
    mediaFilename=baseDir+'/'+attachmentUrl.replace(httpPrefix+'://'+domain+'/','')
    if os.path.isfile(mediaFilename):
        os.remove(mediaFilename)
    postJson['attachment']=[]

def removeModerationPostFromIndex(baseDir: str,postUrl: str,debug: bool) -> None:
    """Removes a url from the moderation index
    """
    moderationIndexFile=baseDir+'/accounts/moderation.txt'
    if not os.path.isfile(moderationIndexFile):
        return
    postId=postUrl.replace('/activity','')
    if postId in open(moderationIndexFile).read():
        with open(moderationIndexFile, "r") as f:
            lines = f.readlines()
            with open(moderationIndexFile, "w+") as f:
                for line in lines:
                    if line.strip("\n") != postId:
                        f.write(line)
                    else:
                        if debug:
                            print('DEBUG: removed '+postId+' from moderation index')

def deletePost(baseDir: str,httpPrefix: str,nickname: str,domain: str,postFilename: str,debug: bool):
    """Recursively deletes a post and its replies and attachments
    """
    with open(postFilename, 'r') as fp:
        postJsonObject=commentjson.load(fp)

        # remove any attachment
        removeAttachment(baseDir,httpPrefix,domain,postJsonObject)
        
        # remove from moderation index file
        if postJsonObject.get('moderationStatus'):
            if postJsonObject.get('object'):
                if isinstance(postJsonObject['object'], dict):
                    if postJsonObject['object'].get('id'):
                        postId=postJsonObject['object']['id'].replace('/activity','')
                        removeModerationPostFromIndex(baseDir,postId,debug)

        # remove any hashtags index entries
        removeHashtagIndex=False
        if postJsonObject.get('object'):
            if isinstance(postJsonObject['object'], dict):
                if postJsonObject['object'].get('content'):
                    if '#' in postJsonObject['object']['content']:
                        removeHashtagIndex=True
        if removeHashtagIndex:
            if postJsonObject['object'].get('id') and postJsonObject['object'].get('tag'):
                # get the id of the post
                postId=postJsonObject['object']['id'].replace('/activity','')
                for tag in postJsonObject['object']['tag']:
                    if tag['type']!='Hashtag':
                        continue
                    # find the index file for this tag
                    tagIndexFilename=baseDir+'/tags/'+tag['name'][1:]+'.txt'
                    if not os.path.isfile(tagIndexFilename):
                        continue
                    # remove postId from the tag index file
                    with open(tagIndexFilename, "r") as f:
                        lines = f.readlines()
                    with open(tagIndexFilename, "w+") as f:
                        for line in lines:
                            if line.strip("\n") != postId:
                                f.write(line)

    # remove any replies
    repliesFilename=postFilename.replace('.json','.replies')
    if os.path.isfile(repliesFilename):
        if debug:
            print('DEBUG: removing replies to '+postFilename)
        with open(repliesFilename,'r') as f:
            for replyId in f:
                replyFile=locatePost(baseDir,nickname,domain,replyId)
                if replyFile:
                    if os.path.isfile(replyFile):
                        deletePost(baseDir,nickname,domain,replyFile,debug)
        # remove the replies file
        os.remove(repliesFilename)
    # finally, remove the post itself
    os.remove(postFilename)    

def validNickname(nickname: str) -> bool:
    forbiddenChars=['.',' ','/','?',':',';','@']
    for c in forbiddenChars:
        if c in nickname:
            return False
    reservedNames=['inbox','outbox','following','followers','capabilities']
    if nickname in reservedNames:
        return False
    return True

def noOfAccounts(baseDir: str) -> bool:
    """Returns the number of accounts on the system
    """
    accountCtr=0
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for account in dirs:
            if '@' in account:
                if not account.startswith('inbox'):
                    accountCtr+=1
    return accountCtr

def isPublicPost(postJsonObject: {}) -> bool:
    """Returns true if the given post is public
    """
    if not postJsonObject.get('type'):
        return False
    if postJsonObject['type']!='Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if not postJsonObject['object'].get('to'):
        return False
    for recipient in postJsonObject['object']['to']:
        if recipient.endswith('#Public'):
            return True
    return False
