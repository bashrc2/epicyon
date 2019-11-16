__filename__ = "utils.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
import shutil
import datetime
import commentjson

def saveJson(jsonObject: {},filename: str) -> bool:
    """Saves json to a file
    """
    tries=0
    while tries<5:
        try:
            with open(filename, 'w') as fp:
                commentjson.dump(jsonObject, fp, indent=2, sort_keys=False)
                return True
        except:
            print('WARN: saveJson '+str(tries))
            time.sleep(1)
            tries+=1
    return False

def loadJson(filename: str) -> {}:
    """Makes a few attempts to load a json formatted file
    """
    jsonObject=None
    tries=0
    while tries<5:
        try:
            with open(filename, 'r') as fp:
                jsonObject=commentjson.load(fp)
                break
        except:
            print('WARN: loadJson exception')
            time.sleep(2)
            tries+=1
    return jsonObject

def getStatusNumber() -> (str,str):
    """Returns the status number and published date
    """
    currTime=datetime.datetime.utcnow()
    daysSinceEpoch=(currTime - datetime.datetime(1970,1,1)).days
    # status is the number of seconds since epoch
    statusNumber=str(((daysSinceEpoch*24*60*60) + (currTime.hour*60*60) + (currTime.minute*60) + currTime.second)*1000 + int(currTime.microsecond/1000))
    # See https://github.com/tootsuite/mastodon/blob/995f8b389a66ab76ec92d9a240de376f1fc13a38/lib/mastodon/snowflake.rb
    # use the leftover microseconds as the sequence number
    sequenceId=currTime.microsecond % 1000
    # shift by 16bits "sequence data"
    statusNumber=str((int(statusNumber)<<16)+sequenceId)
    published=currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    return statusNumber,published

def isEvil(domain: str) -> bool:
    # https://www.youtube.com/watch?v=5qw1hcevmdU
    evilDomains=('gab.com','gabfed.com','spinster.xyz','kiwifarms.cc','djitter.com')
    for concentratedEvil in evilDomains:
        if domain.endswith(concentratedEvil):
            return True
    return False

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

def urlPermitted(url: str,federationList: [],capability: str):
    if isEvil(url):
        return False
    if not federationList:
        return True
    for domain in federationList:
        if domain in url:
            return True
    return False

def getDisplayName(baseDir: str,actor: str,personCache: {}) -> str:
    """Returns the display name for the given actor
    """
    if '/statuses/' in actor:
        actor=actor.split('/statuses/')[0]
    if not personCache.get(actor):
        return None
    if personCache[actor].get('actor'):
        if personCache[actor]['actor'].get('name'):
            return personCache[actor]['actor']['name']
    else:
        # Try to obtain from the cached actors
        cachedActorFilename=baseDir+'/cache/actors/'+actor.replace('/','#')+'.json'
        if os.path.isfile(cachedActorFilename):
            actorJson=None
            tries=0
            while tries<5:
                try:
                    with open(cachedActorFilename, 'r') as fp:
                        actorJson=commentjson.load(fp)
                        break
                except:
                    print('WARN: getDisplayName')
                    time.sleep(1)
                    tries+=1
            if actorJson:
                if actorJson.get('name'):
                    return(actorJson['name'])
    return None

def getNicknameFromActor(actor: str) -> str:
    """Returns the nickname from an actor url
    """
    if '/users/' not in actor:
        if '/profile/' in actor:
            nickStr=actor.split('/profile/')[1].replace('@','')
            if '/' not in nickStr:
                return nickStr
            else:
                return nickStr.split('/')[0]
        if '/channel/' in actor:
            nickStr=actor.split('/channel/')[1].replace('@','')
            if '/' not in nickStr:
                return nickStr
            else:
                return nickStr.split('/')[0]
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
    if '/profile/' in actor:
        domain = actor.split('/profile/')[0].replace('https://','').replace('http://','').replace('dat://','')
    else:
        if '/channel/' in actor:
            domain = actor.split('/channel/')[0].replace('https://','').replace('http://','').replace('dat://','')
        else:
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
        # prepend to follow file
        try:
            with open(filename, 'r+') as followFile:
                content = followFile.read()
                followFile.seek(0, 0)
                followFile.write(followNickname+'@'+followDomain+'\n'+content)
                if debug:
                    print('DEBUG: follow added')
                return True
        except Exception as e:
            print('WARN: Failed to write entry to follow file '+filename+' '+str(e))        
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
    postUrl=postUrl.replace('/','#')
    postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl+'.'+extension
    if not os.path.isfile(postFilename):
        boxName='outbox'
        postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl+'.'+extension
        if not os.path.isfile(postFilename):
            # if this post in the inbox of the person?
            boxName='inbox'
            postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl+'.'+extension
            if not os.path.isfile(postFilename):
                postFilename=baseDir+'/cache/announce/'+nickname+'/'+postUrl+'.'+extension
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
    postJsonObject=None
    tries=0
    while tries<5:
        try:
            with open(postFilename, 'r') as fp:
                postJsonObject=commentjson.load(fp)
                break
        except:
            print('WARN: deletePost')
            time.sleep(1)
            tries+=1

    if postJsonObject:
        # remove any attachment
        removeAttachment(baseDir,httpPrefix,domain,postJsonObject)

        hasObject=False
        if postJsonObject.get('object'):
            hasObject=True

        # remove from moderation index file
        if hasObject:
            if postJsonObject['object'].get('moderationStatus'):
                if postJsonObject.get('id'):
                    postId=postJsonObject['id'].replace('/activity','')
                    removeModerationPostFromIndex(baseDir,postId,debug)

        # remove any hashtags index entries
        removeHashtagIndex=False
        if hasObject:
            if hasObject and isinstance(postJsonObject['object'], dict):
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

def validNickname(domain: str,nickname: str) -> bool:
    forbiddenChars=['.',' ','/','?',':',';','@']
    for c in forbiddenChars:
        if c in nickname:
            return False
    if nickname==domain:
        return False
    reservedNames=['inbox','dm','outbox','following','public','followers','profile','channel','capabilities','calendar','tlreplies','tlmedia','moderation']
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
                if not account.startswith('inbox@'):
                    accountCtr+=1
    return accountCtr

def noOfActiveAccountsMonthly(baseDir: str,months: int) -> bool:
    """Returns the number of accounts on the system this month
    """
    accountCtr=0
    currTime=int(time.time())
    monthSeconds=int(60*60*24*30*months)
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for account in dirs:
            if '@' in account:
                if not account.startswith('inbox@'):
                    lastUsedFilename=baseDir+'/accounts/'+account+'/.lastUsed'
                    if os.path.isfile(lastUsedFilename):
                        with open(lastUsedFilename, 'r') as lastUsedFile:
                            lastUsed = lastUsedFile.read()
                            if lastUsed.isdigit():
                                timeDiff=(currTime-int(lastUsed))
                                if timeDiff<monthSeconds:
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

def copytree(src: str, dst: str, symlinks=False, ignore=None):
    """Copy a directory
    """
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

def getCachedPostDirectory(baseDir: str,nickname: str,domain: str) -> str:
    """Returns the directory where the html post cache exists
    """
    htmlPostCacheDir=baseDir+'/accounts/'+nickname+'@'+domain+'/postcache'
    return htmlPostCacheDir

def getCachedPostFilename(baseDir: str,nickname: str,domain: str, \
                          postJsonObject: {}) -> str:
    """Returns the html cache filename for the given post
    """
    cachedPostFilename= \
        getCachedPostDirectory(baseDir,nickname,domain)+ \
        '/'+postJsonObject['id'].replace('/activity','').replace('/','#')+'.html'
    return cachedPostFilename
