__filename__="utils.py"
__author__="Bob Mottram"
__license__="AGPL3+"
__version__="1.1.0"
__maintainer__="Bob Mottram"
__email__="bob@freedombone.net"
__status__="Production"

import os
import time
import shutil
import datetime
import json
from calendar import monthrange

def removeAvatarFromCache(baseDir: str,actorStr: str) -> None:
    """Removes any existing avatar entries from the cache
    This avoids duplicate entries with differing extensions
    """
    avatarFilenameExtensions=('png','jpg','gif','webp')
    for extension in avatarFilenameExtensions:
        avatarFilename=baseDir+'/cache/avatars/'+actorStr+'.'+extension
        if os.path.isfile(avatarFilename):
            os.remove(avatarFilename)

def saveJson(jsonObject: {},filename: str) -> bool:
    """Saves json to a file
    """
    tries=0
    while tries<5:
        try:
            with open(filename, 'w') as fp:
                fp.write(json.dumps(jsonObject))
                return True
        except:
            print('WARN: saveJson '+str(tries))
            time.sleep(1)
            tries+=1
    return False

def loadJson(filename: str,delaySec=2) -> {}:
    """Makes a few attempts to load a json formatted file
    """
    jsonObject=None
    tries=0
    while tries<5:
        try:
            with open(filename, 'r') as fp:
                data=fp.read()
                jsonObject=json.loads(data)
                break
        except:
            print('WARN: loadJson exception')
            if delaySec>0:
                time.sleep(delaySec)
            tries+=1
    return jsonObject

def loadJsonOnionify(filename: str,domain: str,onionDomain: str,delaySec=2) -> {}:
    """Makes a few attempts to load a json formatted file
    This also converts the domain name to the onion domain
    """
    jsonObject=None
    tries=0
    while tries<5:
        try:
            with open(filename, 'r') as fp:
                data=fp.read()
                if data:
                    data=data.replace(domain,onionDomain).replace('https:','http:')
                    print('*****data: '+data)
                jsonObject=json.loads(data)
                break
        except:
            print('WARN: loadJson exception')
            if delaySec>0:
                time.sleep(delaySec)
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
    if not isinstance(domain, str):
        print('WARN: Malformed domain '+str(domain))
        return True
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
        cachedActorFilename=baseDir+'/cache/actors/'+(actor.replace('/','#'))+'.json'
        if os.path.isfile(cachedActorFilename):
            actorJson=loadJson(cachedActorFilename,1)
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
        domain= \
            actor.split('/profile/')[0].replace('https://','').replace('http://','').replace('i2p://','').replace('dat://','')
    else:
        if '/channel/' in actor:
            domain= \
                actor.split('/channel/')[0].replace('https://','').replace('http://','').replace('i2p://','').replace('dat://','')
        else:
            if '/users/' not in actor:
                domain= \
                    actor.replace('https://','').replace('http://','').replace('i2p://','').replace('dat://','')
                if '/' in actor:
                    domain=domain.split('/')[0]
            else:
                domain= \
                    actor.split('/users/')[0].replace('https://','').replace('http://','').replace('i2p://','').replace('dat://','')
    if ':' in domain:
        portStr=domain.split(':')[1]
        if not portStr.isdigit():
            return None,None
        port=int(portStr)
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

    if not os.path.isdir(baseDir+'/accounts/'+handle):
        print('WARN: account for '+handle+' does not exist')
        return False

    if ':' in followDomain:
        handleToFollow=followNickname+'@'+followDomain.split(':')[0]
    else:
        handleToFollow=followNickname+'@'+followDomain

    # was this person previously unfollowed?
    unfollowedFilename=baseDir+'/accounts/'+handle+'/unfollowed.txt'
    if os.path.isfile(unfollowedFilename):
        if handleToFollow in open(unfollowedFilename).read():
            # remove them from the unfollowed file
            newLines=''
            with open(unfollowedFilename, "r") as f:
                lines=f.readlines()
                for line in lines:
                    if handleToFollow not in line:
                        newLines+=line
            with open(unfollowedFilename, "w") as f:
                f.write(newLines)

    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')
    handleToFollow=followNickname+'@'+followDomain
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        if handleToFollow in open(filename).read():
            if debug:
                print('DEBUG: follow already exists')
            return True
        # prepend to follow file
        try:
            with open(filename, 'r+') as followFile:
                content=followFile.read()
                followFile.seek(0, 0)
                followFile.write(handleToFollow+'\n'+content)
                if debug:
                    print('DEBUG: follow added')
                return True
        except Exception as e:
            print('WARN: Failed to write entry to follow file '+filename+' '+str(e))
    if debug:
        print('DEBUG: creating new following file to follow '+handleToFollow)
    with open(filename, "w") as followfile:
        followfile.write(handleToFollow+'\n')
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
    postUrl=postUrl.replace('/','#').replace('/activity','').strip()

    boxName='inbox'
    postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl+'.'+extension
    if os.path.isfile(postFilename):
        return postFilename

    boxName='outbox'
    postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl+'.'+extension
    if os.path.isfile(postFilename):
        return postFilename

    boxName='tlblogs'
    postFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+boxName+'/'+postUrl+'.'+extension
    if os.path.isfile(postFilename):
        return postFilename

    postFilename=baseDir+'/cache/announce/'+nickname+'/'+postUrl+'.'+extension
    if os.path.isfile(postFilename):
        return postFilename
    print('WARN: unable to locate '+nickname+' '+postUrl+'.'+extension)
    return None

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
    etagFilename=mediaFilename+'.etag'
    if os.path.isfile(etagFilename):
        os.remove(etagFilename)
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
            lines=f.readlines()
            with open(moderationIndexFile, "w+") as f:
                for line in lines:
                    if line.strip("\n") != postId:
                        f.write(line)
                    else:
                        if debug:
                            print('DEBUG: removed '+postId+' from moderation index')

def deletePost(baseDir: str,httpPrefix: str,nickname: str,domain: str,postFilename: str,debug: bool) -> None:
    """Recursively deletes a post and its replies and attachments
    """
    postJsonObject=loadJson(postFilename,1)
    if postJsonObject:
        # don't allow deletion of bookmarked posts
        bookmarksIndexFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/bookmarks.index'
        if os.path.isfile(bookmarksIndexFilename):
            bookmarkIndex=postFilename.split('/')[-1]+'\n'
            if bookmarkIndex in open(bookmarksIndexFilename).read():
                return

        # remove any attachment
        removeAttachment(baseDir,httpPrefix,domain,postJsonObject)

        # remove any mute file
        muteFilename=postFilename+'.muted'
        if os.path.isfile(muteFilename):
            os.remove(muteFilename)

        # remove cached html version of the post
        cachedPostFilename= \
            getCachedPostFilename(baseDir,nickname,domain,postJsonObject)
        if cachedPostFilename:
            if os.path.isfile(cachedPostFilename):
                os.remove(cachedPostFilename)
        #removePostFromCache(postJsonObject,recentPostsCache)

        hasObject=False
        if postJsonObject.get('object'):
            hasObject=True

        # remove from moderation index file
        if hasObject:
            if isinstance(postJsonObject['object'], dict):
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
                    if not tag.get('name'):
                        continue
                    # find the index file for this tag
                    tagIndexFilename=baseDir+'/tags/'+tag['name'][1:]+'.txt'
                    if not os.path.isfile(tagIndexFilename):
                        continue
                    # remove postId from the tag index file
                    lines=None
                    with open(tagIndexFilename, "r") as f:
                        lines=f.readlines()
                    if lines:
                        newlines=''
                        for l in lines:
                            if postId in l:
                                continue
                            newlines+=l
                        if not newlines.strip():
                            # if there are no lines then remove the hashtag file
                            os.remove(tagIndexFilename)
                        else:
                            with open(tagIndexFilename, "w+") as f:
                                f.write(newlines)

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
                        deletePost(baseDir,httpPrefix,nickname,domain,replyFile,debug)
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
    reservedNames=['inbox','dm','outbox','following','public','followers','profile','channel','capabilities','calendar','tlreplies','tlmedia','tlblogs','moderation','activity','undo','reply','replies','question','like','likes','users','statuses','updates','repeat','announce','shares']
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
                            lastUsed=lastUsedFile.read()
                            if lastUsed.isdigit():
                                timeDiff=(currTime-int(lastUsed))
                                if timeDiff<monthSeconds:
                                    accountCtr+=1
    return accountCtr

def isPublicPostFromUrl(baseDir: str,nickname: str,domain: str,postUrl: str) -> bool:
    """Returns whether the given url is a public post
    """
    postFilename=locatePost(baseDir,nickname,domain,postUrl)
    if not postFilename:
        return False
    postJsonObject=loadJson(postFilename,1)
    if not postJsonObject:
        return False
    return isPublicPost(postJsonObject)

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
        s=os.path.join(src, item)
        d=os.path.join(dst, item)
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
    cachedPostDir=getCachedPostDirectory(baseDir,nickname,domain)
    if not os.path.isdir(cachedPostDir):
        #print('ERROR: invalid html cache directory '+cachedPostDir)
        return None
    if '@' not in cachedPostDir:
        #print('ERROR: invalid html cache directory '+cachedPostDir)
        return None
    cachedPostFilename= \
        cachedPostDir+ \
        '/'+postJsonObject['id'].replace('/activity','').replace('/','#')
    cachedPostFilename=cachedPostFilename+'.html'
    return cachedPostFilename

def removePostFromCache(postJsonObject: {},recentPostsCache: {}):
    """ if the post exists in the recent posts cache then remove it
    """
    if not postJsonObject.get('id'):
        return

    if not recentPostsCache.get('index'):
        return

    postId=postJsonObject['id']
    if '#' in postId:
        postId=postId.split('#',1)[0]
    postId=postId.replace('/activity','').replace('/','#')
    if postId not in recentPostsCache['index']:
        return

    if recentPostsCache['json'].get(postId):
        del recentPostsCache['json'][postId]
    if recentPostsCache['html'].get(postId):
        del recentPostsCache['html'][postId]
    recentPostsCache['index'].remove(postId)

def updateRecentPostsCache(recentPostsCache: {},maxRecentPosts: int, \
                           postJsonObject: {},htmlStr: str) -> None:
    """Store recent posts in memory so that they can be quickly recalled
    """
    if not postJsonObject.get('id'):
        return
    postId=postJsonObject['id']
    if '#' in postId:
        postId=postId.split('#',1)[0]
    postId=postId.replace('/activity','').replace('/','#')
    if recentPostsCache.get('index'):
        if postId in recentPostsCache['index']:
            return
        recentPostsCache['index'].append(postId)
        postJsonObject['muted']=False
        recentPostsCache['json'][postId]=json.dumps(postJsonObject)
        recentPostsCache['html'][postId]=htmlStr

        while len(recentPostsCache['html'].items())>maxRecentPosts:
            recentPostsCache['index'].pop(0)
            del recentPostsCache['json'][postId]
            del recentPostsCache['html'][postId]
    else:
        recentPostsCache['index']=[postId]
        recentPostsCache['json']={}
        recentPostsCache['html']={}
        recentPostsCache['json'][postId]=json.dumps(postJsonObject)
        recentPostsCache['html'][postId]=htmlStr

def fileLastModified(filename: str) -> str:
    """Returns the date when a file was last modified
    """
    t=os.path.getmtime(filename)
    modifiedTime=datetime.datetime.fromtimestamp(t)
    return modifiedTime.strftime("%Y-%m-%dT%H:%M:%SZ")

def daysInMonth(year: int,monthNumber: int) -> int:
    """Returns the number of days in the month
    """
    if monthNumber<1 or monthNumber>12:
        return None
    daysRange=monthrange(year, monthNumber)
    return daysRange[1]

def mergeDicts(dict1: {}, dict2: {}) -> {}:
    """Merges two dictionaries
    """
    res={**dict1,**dict2}
    return res

def isBlogPost(postJsonObject: {}) -> bool:
    """Is the given post a blog post?
    """
    if postJsonObject['type']!='Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if not postJsonObject['object'].get('type'):
        return False
    if not postJsonObject['object'].get('content'):
        return False
    if postJsonObject['object']['type']!='Article':
        return False
    return True
