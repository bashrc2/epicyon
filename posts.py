__filename__ = "posts.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import requests
import json
import commentjson
import html
import datetime
import os
import shutil
import threading
import sys
import trace
import time
from threads import threadWithTrace
from cache import storePersonInCache
from cache import getPersonFromCache
from pprint import pprint
from random import randint
from session import createSession
from session import getJson
from session import postJson
from webfinger import webfingerHandle
from httpsig import createSignedHeader
from utils import getStatusNumber
from utils import createPersonDir
from utils import urlPermitted
try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

def getPersonKey(nickname: str,domain: str,baseDir: str,keyType='public'):
    """Returns the public or private key of a person
    """
    handle=nickname+'@'+domain
    keyFilename=baseDir+'/keys/'+keyType+'/'+handle.lower()+'.key'
    if not os.path.isfile(keyFilename):
        return ''
    keyPem=''
    with open(keyFilename, "r") as pemFile:
        keyPem=pemFile.read()
    if len(keyPem)<20:
        return ''
    return keyPem
    
def cleanHtml(rawHtml: str) -> str:
    text = BeautifulSoup(rawHtml, 'html.parser').get_text()
    return html.unescape(text)

def getUserUrl(wfRequest) -> str:
    if wfRequest.get('links'):
        for link in wfRequest['links']:
            if link.get('type') and link.get('href'):
                if link['type'] == 'application/activity+json':
                    return link['href']
    return None

def parseUserFeed(session,feedUrl: str,asHeader: {}) -> None:
    feedJson = getJson(session,feedUrl,asHeader,None)
    if not feedJson:
        return

    if 'orderedItems' in feedJson:
        for item in feedJson['orderedItems']:
            yield item

    nextUrl = None
    if 'first' in feedJson:
        nextUrl = feedJson['first']
    elif 'next' in feedJson:
        nextUrl = feedJson['next']

    if nextUrl:
        for item in parseUserFeed(session,nextUrl,asHeader):
            yield item
    
def getPersonBox(session,wfRequest: {},personCache: {},boxName='inbox') -> (str,str,str,str):
    asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
    personUrl = getUserUrl(wfRequest)
    if not personUrl:
        return None
    print('**********personUrl: '+personUrl)
    personJson = getPersonFromCache(personUrl,personCache)
    if not personJson:
        personJson = getJson(session,personUrl,asHeader,None)
        if not personJson:
            return None
    if not personJson.get(boxName):
        return personPosts
    personId=None
    if personJson.get('id'):
        personId=personJson['id']
    pubKeyId=None
    pubKey=None
    if personJson.get('publicKey'):
        if personJson['publicKey'].get('id'):
            pubKeyId=personJson['publicKey']['id']
        if personJson['publicKey'].get('publicKeyPem'):
            pubKey=personJson['publicKey']['publicKeyPem']

    storePersonInCache(personUrl,personJson,personCache)

    return personJson[boxName],pubKeyId,pubKey,personId

def getPosts(session,outboxUrl: str,maxPosts: int,maxMentions: int, \
             maxEmoji: int,maxAttachments: int,federationList: [], \
             personCache: {},raw: bool,simple: bool) -> {}:
    personPosts={}
    if not outboxUrl:
        return personPosts

    asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
    if raw:
        result = []
        i = 0
        for item in parseUserFeed(session,outboxUrl,asHeader):
            result.append(item)
            i += 1
            if i == maxPosts:
                break
        pprint(result)
        return None

    i = 0
    for item in parseUserFeed(session,outboxUrl,asHeader):
        if not item.get('type'):
            continue
        if item['type'] != 'Create':
            continue
        if not item.get('object'):
            continue
        published = item['object']['published']
        if not personPosts.get(published):
            content = item['object']['content']

            mentions=[]
            emoji={}
            if item['object'].get('tag'):
                for tagItem in item['object']['tag']:
                    tagType=tagItem['type'].lower()
                    if tagType=='emoji':
                        if tagItem.get('name') and tagItem.get('icon'):
                            if tagItem['icon'].get('url'):
                                # No emoji from non-permitted domains
                                if urlPermitted(tagItem['icon']['url'],federationList):
                                    emojiName=tagItem['name']
                                    emojiIcon=tagItem['icon']['url']
                                    emoji[emojiName]=emojiIcon
                    if tagType=='mention':
                        if tagItem.get('name'):
                            if tagItem['name'] not in mentions:
                                mentions.append(tagItem['name'])
            if len(mentions)>maxMentions:
                continue
            if len(emoji)>maxEmoji:
                continue

            summary = ''
            if item['object'].get('summary'):
                if item['object']['summary']:
                    summary = item['object']['summary']

            inReplyTo = ''
            if item['object'].get('inReplyTo'):
                if item['object']['inReplyTo']:
                    # No replies to non-permitted domains
                    if not urlPermitted(item['object']['inReplyTo'],federationList):
                        continue
                    inReplyTo = item['object']['inReplyTo']

            conversation = ''
            if item['object'].get('conversation'):
                if item['object']['conversation']:
                    # no conversations originated in non-permitted domains
                    if urlPermitted(item['object']['conversation'],federationList):                        
                        conversation = item['object']['conversation']

            attachment = []
            if item['object'].get('attachment'):
                if item['object']['attachment']:
                    for attach in item['object']['attachment']:
                        if attach.get('name') and attach.get('url'):
                            # no attachments from non-permitted domains
                            if urlPermitted(attach['url'],federationList):
                                attachment.append([attach['name'],attach['url']])

            sensitive = False
            if item['object'].get('sensitive'):
                sensitive = item['object']['sensitive']

            if simple:
                print(cleanHtml(content)+'\n')
            else:
                personPosts[published] = {
                    "sensitive": sensitive,
                    "inreplyto": inReplyTo,
                    "summary": summary,
                    "html": content,
                    "plaintext": cleanHtml(content),
                    "attachment": attachment,
                    "mentions": mentions,
                    "emoji": emoji,
                    "conversation": conversation
                }
        i += 1

        if i == maxPosts:
            break
    return personPosts

def createBoxArchive(nickname: str,domain: str,baseDir: str,boxname: str) -> str:
    """Creates an archive directory for inbox/outbox posts
    """
    handle=nickname.lower()+'@'+domain.lower()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    boxArchiveDir=baseDir+'/accounts/'+handle+'/'+boxname+'archive'
    if not os.path.isdir(boxArchiveDir):
        os.mkdir(boxArchiveDir)
    return boxArchiveDir

def deleteAllPosts(baseDir: str,nickname: str, domain: str,boxname: str) -> None:
    """Deletes all posts for a person from inbox or outbox
    """
    if boxname!='inbox' and boxname!='outbox':
        return
    boxDir = createPersonDir(nickname,domain,baseDir,boxname)
    for deleteFilename in os.listdir(boxDir):
        filePath = os.path.join(boxDir, deleteFilename)
        try:
            if os.path.isfile(filePath):
                os.unlink(filePath)
            elif os.path.isdir(filePath): shutil.rmtree(filePath)
        except Exception as e:
            print(e)

def savePostToBox(baseDir: str,httpPrefix: str,postId: str,nickname: str, domain: str,postJson: {},boxname: str) -> None:
    """Saves the give json to the give box
    """
    if boxname!='inbox' and boxname!='outbox':
        return
    if ':' in domain:
        domain=domain.split(':')[0]

    if not postId:
        statusNumber,published = getStatusNumber()
        postId=httpPrefix+'://'+domain+'/users/'+nickname+'/statuses/'+statusNumber
        postJson['id']=postId+'/activity'
    if postJson.get('object'):
        postJson['object']['id']=postId
        postJson['object']['atomUri']=postId
         
    boxDir = createPersonDir(nickname,domain,baseDir,boxname)
    filename=boxDir+'/'+postId.replace('/','#')+'.json'
    with open(filename, 'w') as fp:
        commentjson.dump(postJson, fp, indent=4, sort_keys=False)

def createPostBase(baseDir: str,nickname: str, domain: str, port: int, \
                   toUrl: str, ccUrl: str, httpPrefix: str, content: str, \
                   followersOnly: bool, saveToFile: bool, clientToServer: bool, \
                   inReplyTo=None, inReplyToAtomUri=None, subject=None) -> {}:
    """Creates a message
    """
    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    statusNumber,published = getStatusNumber()
    conversationDate=published.split('T')[0]
    conversationId=statusNumber
    postTo='https://www.w3.org/ns/activitystreams#Public'
    postCC=httpPrefix+'://'+domain+'/users/'+nickname+'/followers'
    if followersOnly:
        postTo=postCC
        postCC=''
    newPostId=httpPrefix+'://'+domain+'/users/'+nickname+'/statuses/'+statusNumber
    sensitive=False
    summary=None
    if subject:
        summary=subject
        sensitive=True
    if not clientToServer:
        newPost = {
            'id': newPostId+'/activity',
            'type': 'Create',
            'actor': httpPrefix+'://'+domain+'/users/'+nickname,
            'published': published,
            'to': [toUrl],
            'cc': [],
            'object': {
                'id': newPostId,
                'type': 'Note',
                'summary': summary,
                'inReplyTo': inReplyTo,
                'published': published,
                'url': httpPrefix+'://'+domain+'/@'+nickname+'/'+statusNumber,
                'attributedTo': httpPrefix+'://'+domain+'/users/'+nickname,
                'to': [toUrl],
                'cc': [],
                'sensitive': sensitive,
                'atomUri': newPostId,
                'inReplyToAtomUri': inReplyToAtomUri,
                'conversation': 'tag:'+domain+','+conversationDate+':objectId='+conversationId+':objectType=Conversation',
                'content': content,
                'contentMap': {
                    'en': content
                },
                'attachment': [],
                'tag': [],
                'replies': {}
                #    'id': 'https://'+domain+'/users/'+nickname+'/statuses/'+statusNumber+'/replies',
                #    'type': 'Collection',
                #    'first': {
                #        'type': 'CollectionPage',
                #        'partOf': 'https://'+domain+'/users/'+nickname+'/statuses/'+statusNumber+'/replies',
                #        'items': []
                #    }
                #}
            }
        }
    else:
        newPost = {
            'id': newPostId,
            'type': 'Note',
            'summary': summary,
            'inReplyTo': inReplyTo,
            'published': published,
            'url': httpPrefix+'://'+domain+'/@'+nickname+'/'+statusNumber,
            'attributedTo': httpPrefix+'://'+domain+'/users/'+nickname,
            'to': [toUrl],
            'cc': [],
            'sensitive': sensitive,
            'atomUri': newPostId,
            'inReplyToAtomUri': inReplyToAtomUri,
            'conversation': 'tag:'+domain+','+conversationDate+':objectId='+conversationId+':objectType=Conversation',
            'content': content,
            'contentMap': {
                'en': content
            },
            'attachment': [],
            'tag': [],
            'replies': {}
        }
    if ccUrl:
        if len(ccUrl)>0:
            newPost['cc']=ccUrl
            newPost['object']['cc']=ccUrl
    if saveToFile:
        savePostToBox(baseDir,httpPrefix,newPostId,nickname,domain,newPost,'outbox')
    return newPost

def outboxMessageCreateWrap(httpPrefix: str,nickname: str,domain: str,messageJson: {}) -> {}:
    """Wraps a received message in a Create
    https://www.w3.org/TR/activitypub/#object-without-create
    """

    statusNumber,published = getStatusNumber()
    if messageJson.get('published'):
        published = messageJson['published']
    newPostId=httpPrefix+'://'+domain+'/users/'+nickname+'/statuses/'+statusNumber
    cc=[]
    if messageJson.get('cc'):
        cc=messageJson['cc']
    newPost = {
        'id': newPostId+'/activity',
        'type': 'Create',
        'actor': httpPrefix+'://'+domain+'/users/'+nickname,
        'published': published,
        'to': messageJson['to'],
        'cc': cc,
        'object': messageJson
    }
    newPost['object']['id']=newPost['id']
    newPost['object']['url']=httpPrefix+'://'+domain+'/@'+nickname+'/'+statusNumber
    newPost['object']['atomUri']=httpPrefix+'://'+domain+'/users/'+nickname+'/statuses/'+statusNumber
    return newPost

def createPublicPost(baseDir: str,
                     nickname: str, domain: str, port: int,httpPrefix: str, \
                     content: str, followersOnly: bool, saveToFile: bool,
                     clientToServer: bool, \
                     inReplyTo=None, inReplyToAtomUri=None, subject=None) -> {}:
    """Public post to the outbox
    """
    return createPostBase(baseDir,nickname, domain, port, \
                          'https://www.w3.org/ns/activitystreams#Public', \
                          httpPrefix+'://'+domain+'/users/'+nickname+'/followers', \
                          httpPrefix, content, followersOnly, saveToFile, clientToServer, \
                          inReplyTo, inReplyToAtomUri, subject)

def threadSendPost(session,postJsonObject: {},federationList: [],inboxUrl: str, \
                   baseDir: str,signatureHeaderJson: {},postLog: []) -> None:
    """Sends a post with exponential backoff
    """
    tries=0
    backoffTime=60
    for attempt in range(20):
        postResult = postJson(session,postJsonObject,federationList, \
                              inboxUrl,signatureHeaderJson)
        if postResult:
            postLog.append(postJsonObject['published']+' '+postResult+'\n')
            # keep the length of the log finite
            # Don't accumulate massive files on systems with limited resources
            while len(postLog)>64:
                postlog.pop(0)
            # save the log file
            filename=baseDir+'/post.log'
            with open(filename, "w") as logFile:
                for line in postLog:
                    print(line, file=logFile)
            # our work here is done
            break
        time.sleep(backoffTime)
        backoffTime *= 2

def sendPost(session,baseDir: str,nickname: str, domain: str, port: int, \
             toNickname: str, toDomain: str, toPort: int, cc: str, \
             httpPrefix: str, content: str, followersOnly: bool, \
             saveToFile: bool, clientToServer: bool, federationList: [], \
             sendThreads: [], postLog: [], cachedWebfingers: {},personCache: {}, \
             inReplyTo=None, inReplyToAtomUri=None, subject=None) -> int:
    """Post to another inbox
    """
    withDigest=True

    if toPort!=80 and toPort!=443:
        toDomain=toDomain+':'+str(toPort)        

    handle=httpPrefix+'://'+toDomain+'/@'+toNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers)
    if not wfRequest:
        return 1

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,toPersonId = \
        getPersonBox(session,wfRequest,personCache,'inbox')
    if not inboxUrl:
        return 2
    if not pubKey:
        return 3
    if not toPersonId:
        return 4

    postJsonObject = \
            createPostBase(baseDir,nickname,domain,port, \
                           toPersonId,cc,httpPrefix,content, \
                           followersOnly,saveToFile,clientToServer, \
                           inReplyTo,inReplyToAtomUri, \
                           subject)

    # get the senders private key
    privateKeyPem=getPersonKey(nickname,domain,baseDir,'private')
    if len(privateKeyPem)==0:
        return 5

    if not clientToServer:
        postPath='/inbox'
    else:
        postPath='/outbox'
            
    # construct the http header
    signatureHeaderJson = \
        createSignedHeader(privateKeyPem, nickname, domain, port, \
                           postPath, httpPrefix, withDigest, postJsonObject)

    # Keep the number of threads being used small
    while len(sendThreads)>10:
        sendThreads[0].kill()
        sendThreads.pop(0)
    thr = threadWithTrace(target=threadSendPost,args=(session, \
                                                      postJsonObject.copy(), \
                                                      federationList, \
                                                      inboxUrl,baseDir, \
                                                      signatureHeaderJson.copy(), \
                                                      postLog),daemon=True)
    sendThreads.append(thr)
    thr.start()
    return 0

def createInbox(baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                 itemsPerPage: int,headerOnly: bool,pageNumber=None) -> {}:
    return createBoxBase(baseDir,'inbox',nickname,domain,port,httpPrefix, \
                  itemsPerPage,headerOnly,pageNumber)
def createOutbox(baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                 itemsPerPage: int,headerOnly: bool,pageNumber=None) -> {}:
    return createBoxBase(baseDir,'outbox',nickname,domain,port,httpPrefix, \
                  itemsPerPage,headerOnly,pageNumber)

def createBoxBase(baseDir: str,boxname: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                  itemsPerPage: int,headerOnly: bool,pageNumber=None) -> {}:
    """Constructs the box feed
    """
    if boxname!='inbox' and boxname!='outbox':
        return None
    boxDir = createPersonDir(nickname,domain,baseDir,boxname)

    if port!=80 and port!=443:
        domain = domain+':'+str(port)
        
    pageStr='?page=true'
    if pageNumber:
        try:
            pageStr='?page='+str(pageNumber)
        except:
            pass
    boxHeader = {'@context': 'https://www.w3.org/ns/activitystreams',
                 'first': httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname+'?page=true',
                 'id': httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname,
                 'last': httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname+'?page=true',
                 'totalItems': 0,
                 'type': 'OrderedCollection'}
    boxItems = {'@context': 'https://www.w3.org/ns/activitystreams',
                'id': httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname+pageStr,
                'orderedItems': [
                ],
                'partOf': httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname,
                'type': 'OrderedCollectionPage'}

    # counter for posts loop
    postsOnPageCtr=0

    # post filenames sorted in descending order
    postsInBox=sorted(os.listdir(boxDir), reverse=True)

    # number of posts in box
    boxHeader['totalItems']=len(postsInBox)
    prevPostFilename=None

    if not pageNumber:
        pageNumber=1

    # Generate first and last entries within header
    if len(postsInBox)>0:
        lastPage=int(len(postsInBox)/itemsPerPage)
        if lastPage<1:
            lastPage=1
        boxHeader['last']= \
            httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname+'?page='+str(lastPage)

    # Insert posts
    currPage=1
    postsCtr=0
    for postFilename in postsInBox:
        # Are we at the starting page yet?
        if prevPostFilename and currPage==pageNumber and postsCtr==0:
            # update the prev entry for the last message id
            postId = prevPostFilename.split('#statuses#')[1].replace('#activity','')
            boxHeader['prev']= \
                httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname+'?min_id='+postId+'&page=true'
        # get the full path of the post file
        filePath = os.path.join(boxDir, postFilename)
        try:
            if os.path.isfile(filePath):
                if currPage == pageNumber and postsOnPageCtr <= itemsPerPage:
                    # get the post as json
                    with open(filePath, 'r') as fp:
                        p=commentjson.load(fp)
                        # insert it into the box feed
                        if postsOnPageCtr < itemsPerPage:
                            if not headerOnly:
                                boxItems['orderedItems'].append(p)
                        elif postsOnPageCtr == itemsPerPage:
                            # if this is the last post update the next message ID
                            if '/statuses/' in p['id']:
                                postId = p['id'].split('/statuses/')[1].replace('/activity','')
                                boxHeader['next']= \
                                    httpPrefix+'://'+domain+'/users/'+ \
                                    nickname+'/'+boxname+'?max_id='+ \
                                    postId+'&page=true'
                        postsOnPageCtr += 1
                # remember the last post filename for use with prev
                prevPostFilename = postFilename
                if postsOnPageCtr > itemsPerPage:
                    break
                # count the pages
                postsCtr += 1
                if postsCtr >= itemsPerPage:
                    postsCtr = 0
                    currPage += 1
        except Exception as e:
            print(e)
    if headerOnly:
        return boxHeader
    return boxItems

def archivePosts(nickname: str,domain: str,baseDir: str, \
                 boxname: str,maxPostsInBox=256) -> None:
    """Retain a maximum number of posts within the given box
    Move any others to an archive directory
    """
    if boxname!='inbox' and boxname!='outbox':
        return
    boxDir = createPersonDir(nickname,domain,baseDir,boxname)
    archiveDir = createBoxArchive(nickname,domain,baseDir,boxname)
    postsInBox=sorted(os.listdir(boxDir), reverse=False)
    noOfPosts=len(postsInBox)
    if noOfPosts<=maxPostsInBox:
        return
    
    for postFilename in postsInBox:
        filePath = os.path.join(boxDir, postFilename)
        if os.path.isfile(filePath):
            archivePath = os.path.join(archiveDir, postFilename)
            os.rename(filePath,archivePath)
            # TODO: possibly archive any associated media files
            noOfPosts -= 1
            if noOfPosts <= maxPostsInBox:
                break

def getPublicPostsOfPerson(nickname,domain,raw,simple):
    """ This is really just for test purposes
    """
    useTor=True
    port=443
    session = createSession(domain,port,useTor)
    personCache={}
    cachedWebfingers={}
    federationList=[]

    httpPrefix='https'
    handle=httpPrefix+"://"+domain+"/@"+nickname
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers)
    if not wfRequest:
        sys.exit()

    personUrl,pubKeyId,pubKey,personId=getPersonBox(session,wfRequest,personCache,'outbox')
    wfResult = json.dumps(wfRequest, indent=4, sort_keys=True)

    maxMentions=10
    maxEmoji=10
    maxAttachments=5
    userPosts = getPosts(session,personUrl,30,maxMentions,maxEmoji,maxAttachments,federationList,personCache,raw,simple)
    #print(str(userPosts))
