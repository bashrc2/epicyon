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
from threads import threadWithTrace
from cache import storePersonInCache
from cache import getPersonFromCache
from pprint import pprint
from random import randint
from session import getJson
from session import postJson
try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

# Contains threads for posts being sent
sendThreads = []

# stores the results from recent post sending attempts
postLog = []

def getPersonKey(username: str,domain: str,keyType='public'):
    """Returns the public or private key of a person
    """
    handle=username+'@'+domain
    baseDir=os.getcwd()
    keyFilename=baseDir+'/keys/'+keyType+'/'+handle.lower()+'.key'
    if not os.path.isfile(keyFilename):
        return ''
    keyPem=''
    with open(keyFilename, "r") as pemFile:
        keyPem=pemFile.read()
    if len(keyPem)<20:
        return ''
    return keyPem

def permitted(url: str,federationList) -> bool:
    """Is a url from one of the permitted domains?
    """
    for domain in federationList:
        if domain in url:
            return True
    return False
    
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

def parseUserFeed(session,feedUrl,asHeader) -> None:
    feedJson = getJson(session,feedUrl,asHeader,None)
    pprint(feedJson)

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
    
def getPersonBox(session,wfRequest,boxName='inbox'):
    asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
    personUrl = getUserUrl(wfRequest)
    if not personUrl:
        return None
    personJson = getPersonFromCache(personUrl)
    if not personJson:
        personJson = getJson(session,personUrl,asHeader,None)
    if not personJson.get(boxName):
        return personPosts
    personId=None
    if personJson.get('id'):
        personId=personJson['id']
    pubKey=None
    if personJson.get('publicKey'):
        if personJson['publicKey'].get('publicKeyPem'):
            pubKey=personJson['publicKey']['publicKeyPem']

    storePersonInCache(personUrl,personJson)

    return personJson[boxName],pubKey,personId

def getUserPosts(session,wfRequest,maxPosts,maxMentions,maxEmoji,maxAttachments,federationList) -> {}:
    userPosts={}
    feedUrl,pubKey,personId = getPersonBox(session,wfRequest,'outbox')
    if not feedUrl:
        return userPosts

    i = 0
    for item in parseUserFeed(session,feedUrl,asHeader):
        if not item.get('type'):
            continue
        if item['type'] != 'Create':
            continue
        if not item.get('object'):
            continue
        published = item['object']['published']
        if not userPosts.get(published):
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
                                if permitted(tagItem['icon']['url'],federationList):
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
                    if not permitted(item['object']['inReplyTo'],federationList):
                        continue
                    inReplyTo = item['object']['inReplyTo']

            conversation = ''
            if item['object'].get('conversation'):
                if item['object']['conversation']:
                    # no conversations originated in non-permitted domains
                    if permitted(item['object']['conversation'],federationList):                        
                        conversation = item['object']['conversation']

            attachment = []
            if item['object'].get('attachment'):
                if item['object']['attachment']:
                    for attach in item['object']['attachment']:
                        if attach.get('name') and attach.get('url'):
                            # no attachments from non-permitted domains
                            if permitted(attach['url'],federationList):
                                attachment.append([attach['name'],attach['url']])

            sensitive = False
            if item['object'].get('sensitive'):
                sensitive = item['object']['sensitive']
            
            userPosts[published] = {
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
            #print(str(item)+'\n')
        i += 1

        if i == maxPosts:
            break
    return userPosts

def createOutboxDir(username: str,domain: str) -> str:
    """Create an outbox for a person and returns the feed filename and directory
    """
    handle=username.lower()+'@'+domain.lower()
    baseDir=os.getcwd()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    outboxDir=baseDir+'/accounts/'+handle+'/outbox'
    if not os.path.isdir(outboxDir):
        os.mkdir(outboxDir)
    return outboxDir

def createOutboxArchive(username: str,domain: str) -> str:
    """Creates an archive directory for outbox posts
    """
    handle=username.lower()+'@'+domain.lower()
    baseDir=os.getcwd()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    outboxArchiveDir=baseDir+'/accounts/'+handle+'/outboxarchive'
    if not os.path.isdir(outboxArchiveDir):
        os.mkdir(outboxArchiveDir)
    return outboxArchiveDir

def deleteAllPosts(username: str, domain: str) -> None:
    """Deletes all posts for a person
    """
    outboxDir = createOutboxDir(username,domain)
    for deleteFilename in os.listdir(outboxDir):
        filePath = os.path.join(outboxDir, deleteFilename)
        try:
            if os.path.isfile(filePath):
                os.unlink(filePath)
            elif os.path.isdir(filePath): shutil.rmtree(filePath)
        except Exception as e:
            print(e)

def getStatusNumber() -> (str,str):
    """Returns the status number and published date
    """
    currTime=datetime.datetime.utcnow()
    daysSinceEpoch=(currTime - datetime.datetime(1970,1,1)).days
    # status is the number of seconds since epoch
    statusNumber=str((daysSinceEpoch*24*60*60) + (currTime.hour*60*60) + (currTime.minute*60) + currTime.second)
    published=currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    conversationDate=currTime.strftime("%Y-%m-%d")
    return statusNumber,published
            
def createPostBase(username: str, domain: str, toUrl: str, ccUrl: str, https: bool, content: str, followersOnly: bool, saveToFile: bool, inReplyTo=None, inReplyToAtomUri=None, subject=None) -> {}:
    """Creates a public post
    """
    prefix='https'
    if not https:
        prefix='http'
    statusNumber,published = getStatusNumber()
    conversationDate=published.split('T')[0]
    conversationId=statusNumber
    postTo='https://www.w3.org/ns/activitystreams#Public'
    postCC=prefix+'://'+domain+'/users/'+username+'/followers'
    if followersOnly:
        postTo=postCC
        postCC=''
    newPostId=prefix+'://'+domain+'/users/'+username+'/statuses/'+statusNumber
    sensitive=False
    if subject:
        summary=subject
        sensitive=True
    newPost = {
        'id': newPostId+'/activity',
        'type': 'Create',
        'actor': prefix+'://'+domain+'/users/'+username,
        'published': published,
        'to': [toUrl],
        'cc': [ccUrl],
        'object': {'id': newPostId,
                   'type': 'Note',
                   'summary': summary,
                   'inReplyTo': inReplyTo,
                   'published': published,
                   'url': prefix+'://'+domain+'/@'+username+'/'+statusNumber,
                   'attributedTo': prefix+'://'+domain+'/users/'+username,
                   'to': [toUrl],
                   'cc': [ccUrl],
                   'sensitive': sensitive,
                   'atomUri': prefix+'://'+domain+'/users/'+username+'/statuses/'+statusNumber,
                   'inReplyToAtomUri': inReplyToAtomUri,
                   'conversation': 'tag:'+domain+','+conversationDate+':objectId='+conversationId+':objectType=Conversation',
                   'content': content,
                   'contentMap': {
                       'en': content
                   },
                   'attachment': [],
                   'tag': [],
                   'replies': {}
                   #    'id': 'https://'+domain+'/users/'+username+'/statuses/'+statusNumber+'/replies',
                   #    'type': 'Collection',
                   #    'first': {
                   #        'type': 'CollectionPage',
                   #        'partOf': 'https://'+domain+'/users/'+username+'/statuses/'+statusNumber+'/replies',
                   #        'items': []
                   #    }
                   #}
        }
    }
    if saveToFile:
        outboxDir = createOutboxDir(username,domain)
        filename=outboxDir+'/'+newPostId.replace('/','#')+'.json'
        with open(filename, 'w') as fp:
            commentjson.dump(newPost, fp, indent=4, sort_keys=False)
    return newPost

def createPublicPost(username: str, domain: str, https: bool, content: str, followersOnly: bool, saveToFile: bool, inReplyTo=None, inReplyToAtomUri=None, subject=None) -> {}:
    """Public post to the outbox
    """
    prefix='https'
    if not https:
        prefix='http'
    return createPostBase(username, domain, 'https://www.w3.org/ns/activitystreams#Public', prefix+'://'+domain+'/users/'+username+'/followers', https, content, followersOnly, saveToFile, inReplyTo, inReplyToAtomUri, subject)

def threadSendPost(session,postJsonObject,federationList,inboxUrl: str,signatureHeader) -> None:
    """Sends a post with exponential backoff
    """
    tries=0
    backoffTime=60
    for attempt in range(20):
        postResult = postJson(session,postJsonObject,federationList,inboxUrl,signatureHeader)
        if postResult:
            postLog.append(postJsonObject['published']+' '+postResult+'\n')
            # keep the length of the log finite
            # Don't accumulate massive files on systems with limited resources
            while len(postLog)>64:
                postlog.pop(0)
            # save the log file
            baseDir=os.getcwd()
            filename=baseDir+'/post.log'
            with open(filename, "w") as logFile:
                for line in postLog:
                    print(line, file=logFile)
            # our work here is done
            break
        time.sleep(backoffTime)
        backoffTime *= 2

def sendPost(session,username: str, domain: str, toUsername: str, toDomain: str, cc: str, https: bool, content: str, followersOnly: bool, saveToFile: bool, federationList, inReplyTo=None, inReplyToAtomUri=None, subject=None) -> int:
    """Post to another inbox
    """
    prefix='https'
    if not https:
        prefix='http'

    # lookup the inbox
    handle=prefix+'://'+domain+'/@'+username
    wfRequest = webfingerHandle(session,handle,True)
    if not wfRequest:
        return 1

    inboxUrl,pubKey,toPersonId = getPersonBox(session,wfRequest,'inbox')
    if not inboxUrl:
        return 2
    if not pubKey:
        return 3
    if not toPersonId:
        return 4

    postJsonObject=createPostBase(username, domain, toPersonId, cc, https, content, followersOnly, saveToFile, inReplyTo, inReplyToAtomUri, subject)

    privateKeyPem=getPersonKey(username,domain,'private')
    if len(privateKeyPem)==0:
        return 5

    # construct the http header
    signatureHeader = signPostHeaders(privateKeyPem, username, domain, '/inbox', https, postJsonObject)
    signatureHeader['Content-type'] = 'application/json'

    # Keep the number of threads being used small
    while len(sendThreads)>10:
        sendThreads[0].kill()
        sendThreads.pop(0)
    thr = threadWithTrace(target=threadSendPost,args=(session,postJsonObject.copy(),federationList,inboxUrl,signatureHeader.copy()),daemon=True)
    sendThreads.append(thr)
    thr.start()
    return 0

def createOutbox(username: str,domain: str,port: int,https: bool,itemsPerPage: int,headerOnly: bool,pageNumber=None) -> {}:
    """Constructs the outbox feed
    """
    prefix='https'
    if not https:
        prefix='http'

    outboxDir = createOutboxDir(username,domain)

    if port!=80 and port!=443:
        domain = domain+':'+str(port)
        
    pageStr='?page=true'
    if pageNumber:
        try:
            pageStr='?page='+str(pageNumber)
        except:
            pass
    outboxHeader = {'@context': 'https://www.w3.org/ns/activitystreams',
                    'first': prefix+'://'+domain+'/users/'+username+'/outbox?page=true',
                    'id': prefix+'://'+domain+'/users/'+username+'/outbox',
                    'last': prefix+'://'+domain+'/users/'+username+'/outbox?page=true',
                    'totalItems': 0,
                    'type': 'OrderedCollection'}
    outboxItems = {'@context': 'https://www.w3.org/ns/activitystreams',
                   'id': prefix+'://'+domain+'/users/'+username+'/outbox'+pageStr,
                   'orderedItems': [
                   ],
                   'partOf': prefix+'://'+domain+'/users/'+username+'/outbox',
                   'type': 'OrderedCollectionPage'}

    # counter for posts loop
    postsOnPageCtr=0

    # post filenames sorted in descending order
    postsInOutbox=sorted(os.listdir(outboxDir), reverse=True)

    # number of posts in outbox
    outboxHeader['totalItems']=len(postsInOutbox)
    prevPostFilename=None

    if not pageNumber:
        pageNumber=1

    # Generate first and last entries within header
    if len(postsInOutbox)>0:
        lastPage=int(len(postsInOutbox)/itemsPerPage)
        if lastPage<1:
            lastPage=1
        outboxHeader['last']= \
            prefix+'://'+domain+'/users/'+username+'/outbox?page='+str(lastPage)

    # Insert posts
    currPage=1
    postsCtr=0
    for postFilename in postsInOutbox:
        # Are we at the starting page yet?
        if prevPostFilename and currPage==pageNumber and postsCtr==0:
            # update the prev entry for the last message id
            postId = prevPostFilename.split('#statuses#')[1].replace('#activity','')
            outboxHeader['prev']= \
                prefix+'://'+domain+'/users/'+username+'/outbox?min_id='+postId+'&page=true'
        # get the full path of the post file
        filePath = os.path.join(outboxDir, postFilename)
        try:
            if os.path.isfile(filePath):
                if currPage == pageNumber and postsOnPageCtr <= itemsPerPage:
                    # get the post as json
                    with open(filePath, 'r') as fp:
                        p=commentjson.load(fp)
                        # insert it into the outbox feed
                        if postsOnPageCtr < itemsPerPage:
                            if not headerOnly:
                                outboxItems['orderedItems'].append(p)
                        elif postsOnPageCtr == itemsPerPage:
                            # if this is the last post update the next message ID
                            if '/statuses/' in p['id']:
                                postId = p['id'].split('/statuses/')[1].replace('/activity','')
                                outboxHeader['next']= \
                                    prefix+'://'+domain+'/users/'+ \
                                    username+'/outbox?max_id='+ \
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
        return outboxHeader
    return outboxItems

def archivePosts(username: str,domain: str,maxPostsInOutbox=256) -> None:
    """Retain a maximum number of posts within the outbox
    Move any others to an archive directory
    """
    outboxDir = createOutboxDir(username,domain)
    archiveDir = createOutboxArchive(username,domain)
    postsInOutbox=sorted(os.listdir(outboxDir), reverse=False)
    noOfPosts=len(postsInOutbox)
    if noOfPosts<=maxPostsInOutbox:
        return
    
    for postFilename in postsInOutbox:
        filePath = os.path.join(outboxDir, postFilename)
        if os.path.isfile(filePath):
            archivePath = os.path.join(archiveDir, postFilename)
            os.rename(filePath,archivePath)
            # TODO: possibly archive any associated media files
            noOfPosts -= 1
            if noOfPosts <= maxPostsInOutbox:
                break
