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
import os, shutil
from pprint import pprint
from random import randint
from session import getJson
try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

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

def getUserPosts(session,wfRequest,maxPosts,maxMentions,maxEmoji,maxAttachments,federationList) -> {}:
    userPosts={}
    asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
    userUrl = getUserUrl(wfRequest)
    if not userUrl:
        return userPosts
    userJson = getJson(session,userUrl,asHeader,None)
    if not userJson.get('outbox'):
        return userPosts
    feedUrl = userJson['outbox']

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

def createOutboxDir(username: str,domain: str) -> (str,str):
    """Create an outbox for a person and returns the feed filename and directory
    """
    handle=username.lower()+'@'+domain.lower()
    baseDir=os.getcwd()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    outboxDir=baseDir+'/accounts/'+handle+'/outbox'
    if not os.path.isdir(outboxDir):
        os.mkdir(outboxDir)
    outboxJsonFilename=baseDir+'/accounts/'+handle+'/outbox.json'
    return outboxJsonFilename,outboxDir

def deleteAllPosts(username: str, domain: str) -> None:
    """Deletes all posts for a person
    """
    outboxJsonFilename,outboxDir = createOutboxDir(username,domain)
    for deleteFilename in os.listdir(outboxDir):
        filePath = os.path.join(outboxDir, deleteFilename)
        try:
            if os.path.isfile(filePath):
                os.unlink(filePath)
            elif os.path.isdir(filePath): shutil.rmtree(filePath)
        except Exception as e:
            print(e)
    # TODO update output feed

def createPublicPost(username: str, domain: str, https: bool, content: str, followersOnly: bool, saveToFile: bool, inReplyTo=None, inReplyToAtomUri=None, subject=None) -> {}:
    """Creates a public post
    """
    prefix='https'
    if not https:
        prefix='http'
    currTime=datetime.datetime.utcnow()
    daysSinceEpoch=(currTime - datetime.datetime(1970,1,1)).days
    # status is the number of seconds since epoch
    statusNumber=str((daysSinceEpoch*24*60*60) + (currTime.hour*60*60) + (currTime.minute*60) + currTime.second)
    published=currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    conversationDate=currTime.strftime("%Y-%m-%d")
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
        'to': ['https://www.w3.org/ns/activitystreams#Public'],
        'cc': [prefix+'://'+domain+'/users/'+username+'/followers'],
        'object': {'id': newPostId,
                   'type': 'Note',
                   'summary': summary,
                   'inReplyTo': inReplyTo,
                   'published': published,
                   'url': prefix+'://'+domain+'/@'+username+'/'+statusNumber,
                   'attributedTo': prefix+'://'+domain+'/users/'+username,
                   'to': ['https://www.w3.org/ns/activitystreams#Public'],
                   'cc': [prefix+'://'+domain+'/users/'+username+'/followers'],
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
        outboxJsonFilename,outboxDir = createOutboxDir(username,domain)
        filename=outboxDir+'/'+newPostId.replace('/','#')+'.json'
        with open(filename, 'w') as fp:
            commentjson.dump(newPost, fp, indent=4, sort_keys=False)
        # TODO update output feed
    return newPost

def createOutbox(username: str,domain: str,https: bool,noOfItems: int,startMessageId=None) -> ({},{}):
    """Constructs the outbox feed
    """
    prefix='https'
    if not https:
        prefix='http'
    outboxJsonFilename,outboxDir = createOutboxDir(username,domain)
    outboxHeader = {'@context': 'https://www.w3.org/ns/activitystreams',
                    'first': prefix+'://'+domain+'/users/'+username+'/outbox?page=true',
                    'id': prefix+'://'+domain+'/users/'+username+'/outbox',
                    'last': prefix+'://'+domain+'/users/'+username+'/outbox?min_id=0&page=true',
                    'totalItems': 0,
                    'type': 'OrderedCollection'}
    outboxItems = {'@context': 'https://www.w3.org/ns/activitystreams',
                   'id': prefix+'://'+domain+'/users/'+username+'/outbox?page=true',
                   'orderedItems': [
                   ],
                   'partOf': prefix+'://'+domain+'/users/'+username+'/outbox',
                   'type': 'OrderedCollectionPage'}

    # counter for posts loop
    postCtr=0

    # post filenames sorted in descending order
    postsInOutbox=sorted(os.listdir(outboxDir), reverse=True)

    # number of posts in outbox
    outboxHeader['totalItems']=len(postsInOutbox)
    prevPostFilename=None

    # Generate first and last entries within header
    if len(postsInOutbox)>0:
        postId = postsInOutbox[len(postsInOutbox)-1].split('#statuses#')[1].replace('#activity','')
        outboxHeader['last']= \
            prefix+'://'+domain+'/users/'+username+'/outbox?min_id='+postId+'&page=true'
        postId = postsInOutbox[0].split('#statuses#')[1].replace('#activity','')
        outboxHeader['first']= \
            prefix+'://'+domain+'/users/'+username+'/outbox?max_id='+postId+'&page=true'

    # Insert posts
    for postFilename in postsInOutbox:
        if startMessageId and prevPostFilename:
            if '#statuses#'+startMessageId in postFilename:
                postId = prevPostFilename.split('#statuses#')[1].replace('#activity','')
                outboxHeader['prev']= \
                    prefix+'://'+domain+'/users/'+username+'/outbox?min_id='+postId+'&page=true'
        filePath = os.path.join(outboxDir, postFilename)
        try:
            if os.path.isfile(filePath):
                if postCtr <= noOfItems:
                    with open(filePath, 'r') as fp:
                        p=commentjson.load(fp)
                        if postCtr < noOfItems:
                            outboxItems['orderedItems'].append(p)
                        elif postCtr == noOfItems:
                            if '/statuses/' in p['id']:
                                postId = p['id'].split('/statuses/')[1].replace('/activity','')
                                outboxHeader['next']= \
                                    prefix+'://'+domain+'/users/'+ \
                                    username+'/outbox?max_id='+ \
                                    postId+'&page=true'
                        postCtr += 1
                prevPostFilename = postFilename
                if postCtr > noOfItems:
                    break
        except Exception as e:
            print(e)
    return outboxHeader,outboxItems
