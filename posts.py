__filename__ = "posts.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import requests
import json
import html
from random import randint
from session import getJson
try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

def permitted(url: str,allowedDomains) -> bool:
    """Is a url from one of the permitted domains?
    """
    for domain in allowedDomains:
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
    feed = getJson(session,feedUrl,asHeader,None)

    if 'orderedItems' in feed:
        for item in feed['orderedItems']:
            yield item

    nextUrl = None
    if 'first' in feed:
        nextUrl = feed['first']
    elif 'next' in feed:
        nextUrl = feed['next']

    if nextUrl:
        for item in parseUserFeed(session,nextUrl,asHeader):
            yield item

def getUserPosts(session,wfRequest,maxPosts,maxMentions,maxEmoji,maxAttachments,allowedDomains) -> {}:
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
                                if permitted(tagItem['icon']['url'],allowedDomains):
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
                    if not permitted(item['object']['inReplyTo'],allowedDomains):
                        continue
                    inReplyTo = item['object']['inReplyTo']

            conversation = ''
            if item['object'].get('conversation'):
                if item['object']['conversation']:
                    # no conversations originated in non-permitted domains
                    if permitted(item['object']['conversation'],allowedDomains):                        
                        conversation = item['object']['conversation']

            attachment = []
            if item['object'].get('attachment'):
                if item['object']['attachment']:
                    for attach in item['object']['attachment']:
                        if attach.get('name') and attach.get('url'):
                            # no attachments from non-permitted domains
                            if permitted(attach['url'],allowedDomains):
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

def createPublicPost(username: str, domain: str, https: bool, content: str, followersOnly: bool) -> {}:
    prefix='https'
    if not https:
        prefix='http'
    statusNumber=str(randint(100000000000000000,999999999999999999))
    currTime=datetime.datetime.utcnow()
    published=currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    conversationDate=currTime.strftime("%Y-%m-%d")
    conversationId=str(randint(100000000,999999999))
    postTo='https://www.w3.org/ns/activitystreams#Public'
    postCC=prefix+'://'+domain+'/users/'+username+'/followers'
    if followersOnly:
        postTo=postCC
        postCC=''
    newPost = {
        'id': prefix+'://'+domain+'/users/'+username+'/statuses/'+statusNumber+'/activity',
        'type': 'Create',
        'actor': prefix+'://'+domain+'/users/'+username,
        'published': published,
        'to': ['https://www.w3.org/ns/activitystreams#Public'],
        'cc': [prefix+'://'+domain+'/users/'+username+'/followers'],
        'object': {'id': prefix+'://'+domain+'/users/'+username+'/statuses/'+statusNumber,
                   'type': 'Note',
                   'summary': None,
                   'inReplyTo': None,
                   'published': published,
                   'url': prefix+'://'+domain+'/@'+username+'/'+statusNumber,
                   'attributedTo': prefix+'://'+domain+'/users/'+username,
                   'to': ['https://www.w3.org/ns/activitystreams#Public'],
                   'cc': [prefix+'://'+domain+'/users/'+username+'/followers'],
                   'sensitive': False,
                   'atomUri': prefix+'://'+domain+'/users/'+username+'/statuses/'+statusNumber,
                   'inReplyToAtomUri': None,
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
    return newPost
